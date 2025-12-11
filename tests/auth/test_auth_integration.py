import pytest
from fastapi import status
from app import models, enums
from datetime import datetime, timedelta, timezone
import uuid
from unittest.mock import patch, AsyncMock


class TestLoginEndpoint:
    """Test cases for POST /login"""
    
    def test_login_success(self, client, db_session, test_user):
        db_session.query(models.User).filter(
            models.User.id == test_user.id
        ).update({"confirmed": True})
        db_session.commit()
        
        response = client.post(
            "/login",
            data={
                "username": test_user.email,
                "password": "Abc123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == status.HTTP_200_OK
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_login_invalid_email(self, client, db_session):
        """Test login with non-existent email"""
        response = client.post(
            "/login",
            data={
                "username": "nonexistent@example.com",
                "password": "Password123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == status.HTTP_403_FORBIDDEN
        assert data["message"] == "Invalid Credentials"
    
    def test_login_unconfirmed_email(self, client, db_session, test_user):
        """Test login with unconfirmed email"""
        db_session.query(models.User).filter(
            models.User.id == test_user.id
        ).update({"confirmed": False})
        db_session.commit()
        
        response = client.post(
            "/login",
            data={
                "username": test_user.email,
                "password": "Abc123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == status.HTTP_403_FORBIDDEN
        assert data["message"] == "Email has not been verified yet"


class TestResetPasswordEndpoint:
    """Test cases for PATCH /resetPassword"""
    
    @pytest.fixture
    def reset_code(self, db_session, test_user):
        """Create a valid reset code"""
        code = models.ResetCode(
            email=test_user.email,
            reset_code=str(uuid.uuid4()),
            status=enums.CodeStatus.Pending,
            created_on=datetime.now(timezone.utc)
        )
        db_session.add(code)
        db_session.commit()
        db_session.refresh(code)
        return code
    
    @patch("app.routers.auth.hash_password")
    def test_reset_password_success(self, mock_hash, client, db_session, test_user, reset_code):
        """Test successful password reset"""
        mock_hash.return_value = "hashed_new_password"
        
        response = client.patch(
            "/resetPassword",
            json={
                "reset_password_token": reset_code.reset_code,
                "new_password": "NewPassword123",
                "confirm_new_password": "NewPassword123"
            }
        )
        
        data = response.json()
        assert data["status"] == status.HTTP_200_OK
        assert data["message"] == "Password reset successfully"

        updated_code = db_session.query(models.ResetCode).filter(
            models.ResetCode.reset_code == reset_code.reset_code
        ).first()
        assert updated_code.status == enums.CodeStatus.Used
    
    def test_reset_password_invalid_token(self, client, db_session):
        """Test reset with invalid token"""
        response = client.patch(
            "/resetPassword",
            json={
                "reset_password_token": "invalid-token",
                "new_password": "NewPassword123",
                "confirm_new_password": "NewPassword123"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == status.HTTP_400_BAD_REQUEST
        assert data["message"] == "Reset link does not exist"
    
    def test_reset_password_already_used(self, client, db_session, test_user, reset_code):
        """Test reset with already used token"""
        db_session.query(models.ResetCode).filter(
            models.ResetCode.reset_code == reset_code.reset_code
        ).update({"status": enums.CodeStatus.Used})
        db_session.commit()
        
        response = client.patch(
            "/resetPassword",
            json={
                "reset_password_token": reset_code.reset_code,
                "new_password": "NewPassword123",
                "confirm_new_password": "NewPassword123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == status.HTTP_400_BAD_REQUEST
        assert data["message"] == "Code Already used"
    
    def test_reset_password_expired_token(self, client, db_session, test_user):
        """Test reset with expired token"""
        expired_code = models.ResetCode(
            email=test_user.email,
            reset_code=str(uuid.uuid4()),
            status=enums.CodeStatus.Pending,
            created_on=datetime.now(timezone.utc) - timedelta(minutes=120)
        )
        db_session.add(expired_code)
        db_session.commit()
        
        response = client.patch(
            "/resetPassword",
            json={
                "reset_password_token": expired_code.reset_code,
                "new_password": "NewPassword123",
                "confirm_new_password": "NewPassword123"
            }
        )
        data = response.json()
        print(data)
        assert data["status"] == status.HTTP_400_BAD_REQUEST
        assert data["message"] == "Code expired"
    
    def test_reset_password_mismatch(self, client, db_session, reset_code):
        """Test reset with mismatched passwords"""
        response = client.patch(
            "/resetPassword",
            json={
                "reset_password_token": reset_code.reset_code,
                "new_password": "NewPassword123",
                "confirm_new_password": "DifferentPassword123"
            }
        )
    
        data = response.json()
        print(data)
        assert data["status"] == status.HTTP_400_BAD_REQUEST
        assert data["message"] == "Passwords do not match"


class TestConfirmAccountEndpoint:
    """Test cases for PATCH /confirmAccount"""
    
    @pytest.fixture
    def confirmation_code(self, db_session, test_user):
        """Create a valid confirmation code"""
        code = models.ConfirmationCode(
            email=test_user.email,
            code=str(uuid.uuid4()),
            status=enums.CodeStatus.Pending,
            user_id=test_user.id,
            created_on=datetime.now(timezone.utc)
        )
        db_session.add(code)
        db_session.commit()
        db_session.refresh(code)
        return code
    
    def test_confirm_account_success(self, client, db_session, test_user, confirmation_code):
        """Test successful account confirmation"""
        db_session.query(models.User).filter(
            models.User.id == test_user.id
        ).update({"confirmed": False})
        db_session.commit()
        
        response = client.patch(
            "/confirmAccount",
            json={
                "code": confirmation_code.code
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == status.HTTP_200_OK
        assert data["message"] == "Account Confirmed"
        
        user = db_session.query(models.User).filter(
            models.User.id == test_user.id
        ).first()
        assert user.confirmed is True        
        code = db_session.query(models.ConfirmationCode).filter(
            models.ConfirmationCode.code == confirmation_code.code
        ).first()
        assert code.status == enums.CodeStatus.Used
    
    def test_confirm_account_invalid_code(self, client, db_session):
        """Test confirmation with invalid code"""
        response = client.patch(
            "/confirmAccount",
            json={
                "code": "invalid-code"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == status.HTTP_400_BAD_REQUEST
        assert data["message"] == "Confirmation code does not exist"
    
    def test_confirm_account_already_used(self, client, db_session, confirmation_code):
        """Test confirmation with already used code"""
        db_session.query(models.ConfirmationCode).filter(
            models.ConfirmationCode.code == confirmation_code.code
        ).update({"status": enums.CodeStatus.Used})
        db_session.commit()
        
        response = client.patch(
            "/confirmAccount",
            json={
                "code": confirmation_code.code
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == status.HTTP_400_BAD_REQUEST
        assert data["message"] == "Account Already Confirmed"


class TestLogoutEndpoint:
    """Test cases for GET /logout"""
    
    def test_logout_success(self, client, db_session, test_user):
        """Test successful logout"""
        db_session.query(models.User).filter(
            models.User.id == test_user.id
        ).update({"confirmed": True})
        db_session.commit()
        
        login_response = client.post(
            "/login",
            data={
                "username": test_user.email,
                "password": "Abc123"
            }
        )
        token = login_response.json()["access_token"]
        
        response = client.get(
            "/logout",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == status.HTTP_200_OK
        assert data["message"] == "Logout successfully"
        
        blacklisted = db_session.query(models.JWTblacklist).filter(
            models.JWTblacklist.token == token
        ).first()
        assert blacklisted is not None


class TestForgotPasswordEndpoint:
    """Test cases for POST /forgotPassword"""
    
    @patch('app.routers.resetCode.send_email', new_callable=AsyncMock)
    def test_forgot_password_success(self, mock_send_email, client, db_session, test_user):
        """Test successful forgot password request"""
        response = client.post(
            "/forgotPassword",
            json={
                "email": test_user.email
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == status.HTTP_200_OK
        assert data["message"] == "email sent!"

        reset_code = db_session.query(models.ResetCode).filter(
            models.ResetCode.email == test_user.email
        ).first()
        assert reset_code is not None
        assert reset_code.status == enums.CodeStatus.Pending
        
        mock_send_email.assert_called_once()
    
    def test_forgot_password_invalid_email(self, client, db_session):
        """Test forgot password with non-existent email"""
        response = client.post(
            "/forgotPassword",
            json={
                "email": "nonexistent@example.com"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == status.HTTP_404_NOT_FOUND
        assert data["message"] == "No account with this email"
