import pytest
from fastapi import status
from app import models, enums
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, AsyncMock
import uuid


class TestCompleteUserJourney:
    """Test complete user journey from registration to task management"""
    
    @patch('app.routers.user.send_email', new_callable=AsyncMock)
    def test_complete_user_journey(self, mock_send_email, unauthenticated_client, db_session):
        """
        Test complete flow:
        1. User registration
        2. Email confirmation
        3. Login
        4. Create tasks
        5. Update tasks
        6. Delete tasks
        7. Logout
        """
        # Step 1: Register user
        registration_response = unauthenticated_client.post(
            "/users/",
            json={
                "email": "journey@example.com",
                "first_name": "Journey",
                "last_name": "User",
                "password": "Password123",
                "confirm_password": "Password123"
            }
        )
        assert registration_response.status_code == 201
        assert registration_response.json()["status"] == status.HTTP_201_CREATED
        
        # Step 2: Get confirmation code and confirm account
        confirmation_code = db_session.query(models.ConfirmationCode).filter(
            models.ConfirmationCode.email == "journey@example.com"
        ).first()
        
        confirm_response = unauthenticated_client.patch(
            "/confirmAccount",
            json={"code": confirmation_code.code}
        )
        assert confirm_response.status_code == 200
        assert confirm_response.json()["message"] == "Account Confirmed"
        
        # Step 3: Login
        login_response = unauthenticated_client.post(
            "/login",
            data={
                "username": "journey@example.com",
                "password": "Password123"
            }
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        
        # Create authenticated client
        headers = {"Authorization": f"Bearer {token}"}
        
        # Step 4: Create tasks
        task1_response = unauthenticated_client.post(
            "/task/",
            json={
                "title": "First Task",
                "description": "My first task",
                "state": "todo",
                "tag": "important"
            },
            headers=headers
        )
        assert task1_response.status_code == 200
        task1_id = task1_response.json()["id"]
        
        # Step 5: Update task
        update_response = unauthenticated_client.put(
            f"/task/{task1_id}",
            json={
                "title": "Updated First Task",
                "state": "doing"
            },
            headers=headers
        )
        assert update_response.status_code == 200
        assert update_response.json()["title"] == "Updated First Task"
        
        # Step 6: Mark task as done
        done_response = unauthenticated_client.put(
            f"/task/mark_as_done/{task1_id}",
            headers=headers
        )
        assert done_response.status_code == 200
        assert done_response.json()["state"] == "done"
        
        # Step 7: Get statistics
        stats_response = unauthenticated_client.get(
            "/task/stats/summary",
            headers=headers
        )
        assert stats_response.status_code == 200
        stats = stats_response.json()["data"]
        assert stats["total"] == 1
        assert stats["done"] == 1
        
        # Step 8: Logout
        logout_response = unauthenticated_client.get(
            "/logout",
            headers=headers
        )
        assert logout_response.status_code == 200


class TestPasswordResetFlow:
    """Test complete password reset flow"""
    
    @patch('app.routers.resetCode.send_email', new_callable=AsyncMock)
    @patch('app.routers.auth.hash_password')
    def test_forgot_password_to_reset_flow(self, mock_hash, mock_send_email, 
                                           unauthenticated_client, db_session, test_user):
        """Test complete password reset flow"""
        mock_hash.return_value = "new_hashed_password"
        
        # Step 1: Request password reset
        forgot_response = unauthenticated_client.post(
            "/forgotPassword",
            json={"email": test_user.email}
        )
        assert forgot_response.status_code == 200
        assert forgot_response.json()["message"] == "email sent!"
        
        # Step 2: Get reset code from database
        reset_code = db_session.query(models.ResetCode).filter(
            models.ResetCode.email == test_user.email
        ).first()
        assert reset_code is not None
        
        # Step 3: Reset password
        reset_response = unauthenticated_client.patch(
            "/resetPassword",
            json={
                "reset_password_token": reset_code.reset_code,
                "new_password": "NewPassword123",
                "confirm_new_password": "NewPassword123"
            }
        )
        assert reset_response.status_code == 200
        assert reset_response.json()["message"] == "Password reset successfully"
        
        # Step 4: Verify reset code is marked as used
        updated_code = db_session.query(models.ResetCode).filter(
            models.ResetCode.reset_code == reset_code.reset_code
        ).first()
        assert updated_code.status == enums.CodeStatus.Used

class TestConcurrentOperations:
    """Test concurrent operations and race conditions"""
    
    def test_concurrent_task_updates(self, client, db_session, test_user):
        """Test updating the same task concurrently"""
        # Create a task
        task = models.Task(
            title="Concurrent Task",
            state=enums.State.todo,
            user_id=test_user.id
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)
        
        # Simulate two concurrent updates
        response1 = client.put(
            f"/task/{task.id}",
            json={"title": "Update 1"}
        )
        
        response2 = client.put(
            f"/task/{task.id}",
            json={"title": "Update 2"}
        )
        
        # Both should succeed (last write wins)
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Verify final state
        final_task = db_session.query(models.Task).filter(
            models.Task.id == task.id
        ).first()
        assert final_task.title == "Update 2"


class TestDataValidation:
    """Test data validation and edge cases"""
    
    def test_create_task_with_past_due_date(self, client, db_session):
        """Test creating task with past due date"""
        response = client.post(
            "/task/",
            json={
                "title": "Past Due Task",
                "state": "todo",
                "due_date": (datetime.now() - timedelta(days=1)).isoformat()
            }
        )
        # Should still create the task (business logic decision)
        assert response.status_code == 200
    
 
    def test_update_user_with_invalid_email_format(self, client, db_session, test_user):
        """Test updating user with invalid email format"""
        response = client.put(
            f"/users/{test_user.id}",
            json={
                "email": "invalid-email-format",
                "first_name": "Test"
            }
        )
        assert response.status_code == 422

class TestAuthenticationEdgeCases:
    """Test authentication edge cases"""
    
    def test_login_with_blacklisted_token(self, client, db_session, test_user):
        """Test using a blacklisted token"""
        login_response = client.post(
            "/login",
            data={
                "username": test_user.email,
                "password": "Abc123"
            }
        )
        token = login_response.json()["access_token"]
        
        logout_response = client.get(
            "/logout",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert logout_response.status_code == 200

        blacklisted = db_session.query(models.JWTblacklist).filter(
            models.JWTblacklist.token == token
        ).first()
        assert blacklisted is not None
    
    def test_multiple_confirmation_attempts(self, unauthenticated_client, 
                                           db_session, test_user_unconfirmed):
        """Test multiple confirmation attempts with same code"""

        code = models.ConfirmationCode(
            email=test_user_unconfirmed.email,
            code=str(uuid.uuid4()),
            status=enums.CodeStatus.Pending,
            user_id=test_user_unconfirmed.id
        )
        db_session.add(code)
        db_session.commit()
        
        # First confirmation should succeed
        response1 = unauthenticated_client.patch(
            "/confirmAccount",
            json={"code": code.code}
        )
        assert response1.status_code == 200
        assert response1.json()["message"] == "Account Confirmed"
        
        # Second attempt should fail
        response2 = unauthenticated_client.patch(
            "/confirmAccount",
            json={"code": code.code}
        )
        assert response2.status_code == 200
        assert response2.json()["message"] == "Account Already Confirmed"


class TestFilteringAndSorting:
    """Test advanced filtering and sorting scenarios"""
    
    @pytest.fixture
    def complex_task_set(self, db_session, test_user):
        """Create a complex set of tasks for filtering tests"""
        tasks = [
            models.Task(
                title="Urgent Bug Fix",
                description="Critical production issue",
                state=enums.State.todo,
                tag=enums.Tag.urgent,
                user_id=test_user.id,
                due_date=datetime.now() + timedelta(hours=2),
                created_on=datetime.now()
            ),
            models.Task(
                title="Code Review",
                description="Review pull requests",
                state=enums.State.doing,
                tag=enums.Tag.important,
                user_id=test_user.id,
                due_date=datetime.now() + timedelta(days=1),
                created_on=datetime.now() - timedelta(hours=1)
            ),
            models.Task(
                title="Grocery Shopping",
                description="Buy groceries for the week",
                state=enums.State.todo,
                tag=enums.Tag.optional,
                user_id=test_user.id,
                due_date=datetime.now() + timedelta(days=3),
                created_on=datetime.now() - timedelta(hours=2)
            ),
            models.Task(
                title="Meeting Preparation",
                description="Prepare slides",
                state=enums.State.done,
                tag=enums.Tag.important,
                user_id=test_user.id,
                due_date=datetime.now() - timedelta(days=1),
                created_on=datetime.now() - timedelta(days=2)
            ),
        ]
        
        for task in tasks:
            db_session.add(task)
        db_session.commit()
        return tasks
    
    def test_filter_by_multiple_criteria(self, client, db_session, complex_task_set):
        """Test filtering by state AND tag"""
        response = client.get("/task/?state=doing&tag=important")
        
        assert response.status_code == 200
        data = response.json()
        assert all(
            task["state"] == "doing" and task["tag"] == "important"
            for task in data["list"]
        )
    
    def test_search_across_title_and_description(self, client, db_session, complex_task_set):
        """Test search functionality"""
        response = client.get("/task/?search=review")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["list"]) >= 1

    
    def test_sort_by_due_date_with_nulls(self, client, db_session, test_user):
        """Test sorting when some tasks have null due dates"""
        task_with_date = models.Task(
            title="With Date",
            state=enums.State.todo,
            user_id=test_user.id,
            due_date=datetime.now() + timedelta(days=1)
        )
        task_without_date = models.Task(
            title="Without Date",
            state=enums.State.todo,
            user_id=test_user.id,
            due_date=None
        )
        db_session.add(task_with_date)
        db_session.add(task_without_date)
        db_session.commit()
        
        response = client.get("/task/?sort_by=due_date&sort_order=asc")
        assert response.status_code == 200


class TestErrorHandling:
    """Test error handling scenarios"""    
    def test_missing_required_fields(self, client, db_session):
        """Test creating task without required fields"""
        response = client.post(
            "/task/",
            json={}  
        )
        assert response.status_code == 422
