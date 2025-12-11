import pytest
from fastapi import status
from app import models, enums
from datetime import datetime, timedelta

from app.enums.state import State
from app.enums.tag import Tag


class TestCreateTask:
    """Test cases for POST /task/"""
    
    def test_create_task_success(self, client, db_session, test_user):
        """Test successful task creation"""
        task_data = {
            "title": "Test Task",
            "description": "Test Description",
            "tag": "urgent",
            "due_date": (datetime.now() + timedelta(days=7)).isoformat()
        }
        
        response = client.post("/task/", json=task_data)
        
        data = response.json()
        assert data["status"] == status.HTTP_201_CREATED
        assert data["message"] == "Task added successfully"
        assert data["title"] == "Test Task"
        assert data["description"] == "Test Description"
        assert data["user_id"] == test_user.id
        assert "id" in data

        task = db_session.query(models.Task).filter(
            models.Task.title == "Test Task"
        ).first()
        assert task is not None
        assert task.user_id == test_user.id
    
    def test_create_task_minimal_data(self, client, db_session, test_user):
        """Test creating task with minimal required data"""
        task_data = {
            "title": "Minimal Task",
            "state": "todo"
        }
        
        response = client.post("/task/", json=task_data)
        
  
        data = response.json()
        assert data["status"] == status.HTTP_201_CREATED
        assert data["title"] == "Minimal Task"


class TestGetAllTasks:
    """Test cases for GET /task/"""
    
    @pytest.fixture
    def sample_tasks(self, db_session, test_user):
        """Create sample tasks for testing"""
        tasks = []
        task_data = [
            {"title": "Task 1", "description": "Description 1", "state": enums.State.todo, "tag": enums.Tag.important},
            {"title": "Task 2", "description": "Description 2", "state": enums.State.doing, "tag": enums.Tag.optional},
            {"title": "Task 3", "description": "Description 3", "state": enums.State.done, "tag": enums.Tag.important},
            {"title": "Urgent Task", "description": "Important", "state": enums.State.todo, "tag": enums.Tag.urgent},
        ]
        
        for data in task_data:
            task = models.Task(
                **data,
                user_id=test_user.id,
                due_date=datetime.now() + timedelta(days=7)
            )
            db_session.add(task)
            tasks.append(task)
        
        db_session.commit()
        return tasks
    
    def test_get_all_tasks_default(self, client, db_session, test_user, sample_tasks):
        """Test getting all tasks with default parameters"""
        response = client.get("/task/")
        
        data = response.json()
        print(data)
        assert data["status"] == status.HTTP_200_OK
        assert data["message"] == "Tasks retrieved successfully"
        assert len(data["list"]) == len(sample_tasks)
        assert data["total_records"] == len(sample_tasks)
        assert data["page_size"] == 10
        assert data["page_number"] == 1
    
    def test_get_tasks_with_state_filter(self, client, db_session, sample_tasks):
        """Test filtering tasks by state"""
        response = client.get("/task/?state=todo")
        
 
        data = response.json()
        assert data["status"] == status.HTTP_200_OK
        assert all(task["state"] == "todo" for task in data["list"])
    
    def test_get_tasks_with_tag_filter(self, client, db_session, sample_tasks):
        """Test filtering tasks by tag"""
        response = client.get("/task/?tag=important")
        
        data = response.json()
        print(data)
        assert data["status"] == status.HTTP_200_OK
        assert all(task["tag"] == "important" for task in data["list"])
    
    def test_get_tasks_with_search(self, client, db_session, sample_tasks):
        """Test searching tasks by title/description"""
        response = client.get("/task/?search=Urgent")
        
        data = response.json()
        assert data["status"] == status.HTTP_200_OK
        assert len(data["list"]) >= 1
        assert any("Urgent" in task["title"] for task in data["list"])
    
    def test_get_tasks_with_pagination(self, client, db_session, sample_tasks):
        """Test task pagination"""
        response = client.get("/task/?page_size=2&page_number=1")
        
 
        data = response.json()
        assert data["status"] == status.HTTP_200_OK
        assert len(data["list"]) == 2
        assert data["page_size"] == 2
        assert data["total_pages"] == 2
    
    def test_get_tasks_sort_by_title_asc(self, client, db_session, sample_tasks):
        """Test sorting tasks by title ascending"""
        response = client.get("/task/?sort_by=title&sort_order=asc")
        
 
        data = response.json()
        assert data["status"] == status.HTTP_200_OK
        titles = [task["title"] for task in data["list"]]
        assert titles == sorted(titles)
    
    def test_get_tasks_sort_by_due_date_desc(self, client, db_session, sample_tasks):
        """Test sorting tasks by due date descending"""
        response = client.get("/task/?sort_by=due_date&sort_order=desc")
        
 
        data = response.json()
        assert data["status"] == status.HTTP_200_OK
    
    def test_get_tasks_invalid_state(self, client, db_session, sample_tasks):
        """Test filtering with invalid state"""
        response = client.get("/task/?state=invalid_state")
        
 
        data = response.json()
        assert data["status"] == status.HTTP_400_BAD_REQUEST
        assert "Invalid state" in data["message"]
    
    def test_get_tasks_invalid_tag(self, client, db_session, sample_tasks):
        """Test filtering with invalid tag"""
        response = client.get("/task/?tag=invalid_tag")
        
 
        data = response.json()
        assert data["status"] == status.HTTP_400_BAD_REQUEST
        assert "Invalid tag" in data["message"]


class TestGetTaskById:
    """Test cases for GET /task/{id}"""
    
    @pytest.fixture
    def sample_task(self, db_session, test_user):
        """Create a sample task"""
        task = models.Task(
            title="Sample Task",
            description="Sample Description",
            state=enums.State.todo,
            tag=enums.Tag.important,
            user_id=test_user.id,
            due_date=datetime.now() + timedelta(days=7)
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)
        return task
    
    def test_get_task_by_id_success(self, client, db_session, sample_task):
        """Test getting task by ID"""
        response = client.get(f"/task/{sample_task.id}")
        
 
        data = response.json()
        assert data["status"] == status.HTTP_200_OK
        assert data["message"] == "Task retrieved successfully"
        assert data["id"] == sample_task.id
        assert data["title"] == "Sample Task"
    
    def test_get_task_by_id_not_found(self, client, db_session):
        """Test getting non-existent task"""
        response = client.get("/task/99999")
        
 
        data = response.json()
        assert data["status"] == status.HTTP_404_NOT_FOUND
        assert "does not exist" in data["message"]
    
    def test_get_task_by_id_unauthorized(self, client, db_session):
        """Test getting task owned by another user"""
        other_user = models.User(
            email="otheruser@example.com",
            first_name="Other",
            last_name="User",
            password="hashed",
            confirmed=True
        )
        db_session.add(other_user)
        db_session.commit()
        
        other_task = models.Task(
            title="Other User Task",
            state=enums.State.todo,
            user_id=other_user.id
        )
        db_session.add(other_task)
        db_session.commit()
        db_session.refresh(other_task)
        
        response = client.get(f"/task/{other_task.id}")
        
 
        data = response.json()
        assert data["status"] == status.HTTP_404_NOT_FOUND


class TestDeleteTask:
    """Test cases for DELETE /task/{id}"""
    
    @pytest.fixture
    def sample_task(self, db_session, test_user):
        """Create a sample task"""
        task = models.Task(
            title="Task to Delete",
            state=enums.State.todo,
            user_id=test_user.id
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)
        return task
    
    def test_delete_task_success(self, client, db_session, sample_task):
        """Test successful task deletion"""
        task_id = sample_task.id
        
        response = client.delete(f"/task/{task_id}")
        
 
        data = response.json()
        assert data["status"] == status.HTTP_200_OK
        assert data["message"] == "Task deleted successfully"
        
        deleted_task = db_session.query(models.Task).filter(
            models.Task.id == task_id
        ).first()
        assert deleted_task is None
    
    def test_delete_task_not_found(self, client, db_session):
        """Test deleting non-existent task"""
        response = client.delete("/task/99999")
        
 
        data = response.json()
        assert data["status"] == status.HTTP_404_NOT_FOUND
        assert "does not exist" in data["message"]


class TestMarkTaskAsDone:
    """Test cases for PUT /task/mark_as_done/{id}"""
    
    @pytest.fixture
    def sample_task(self, db_session, test_user):
        """Create a sample task"""
        task = models.Task(
            title="Task to Mark Done",
            state=enums.State.todo,
            user_id=test_user.id
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)
        return task
    
    def test_mark_task_as_done_success(self, client, db_session, sample_task):
        """Test marking task as done"""
        response = client.put(f"/task/mark_as_done/{sample_task.id}")
        
 
        data = response.json()
        assert data["status"] == status.HTTP_200_OK
        assert data["message"] == "Task marked as done successfully"
        assert data["state"] == "done"
        
        updated_task = db_session.query(models.Task).filter(
            models.Task.id == sample_task.id
        ).first()
        assert updated_task.state == enums.State.done
    
    def test_mark_task_as_done_not_found(self, client, db_session):
        """Test marking non-existent task as done"""
        response = client.put("/task/mark_as_done/99999")
        
 
        data = response.json()
        assert data["status"] == status.HTTP_404_NOT_FOUND


class TestToggleTaskState:
    """Test cases for PUT /task/toggle_state/{id}"""
    
    def test_toggle_state_todo_to_doing(self, client, db_session, test_user):
        """Test toggling state from todo to doing"""
        task = models.Task(
            title="Toggle Task",
            state=enums.State.todo,
            user_id=test_user.id
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)
        
        response = client.put(f"/task/toggle_state/{task.id}")
        
 
        data = response.json()
        assert data["status"] == status.HTTP_200_OK
        assert data["state"] == "doing"
    
    def test_toggle_state_doing_to_done(self, client, db_session, test_user):
        """Test toggling state from doing to done"""
        task = models.Task(
            title="Toggle Task",
            state=enums.State.doing,
            user_id=test_user.id
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)
        
        response = client.put(f"/task/toggle_state/{task.id}")
        
 
        data = response.json()
        assert data["status"] == status.HTTP_200_OK
        assert data["state"] == "done"
    
    def test_toggle_state_done_to_todo(self, client, db_session, test_user):
        """Test toggling state from done to todo"""
        task = models.Task(
            title="Toggle Task",
            state=enums.State.done,
            user_id=test_user.id
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)
        
        response = client.put(f"/task/toggle_state/{task.id}")
        
 
        data = response.json()
        assert data["status"] == status.HTTP_200_OK
        assert data["state"] == "todo"


class TestUpdateTask:
    """Test cases for PUT /task/{id}"""
    
    @pytest.fixture
    def sample_task(self, db_session, test_user):
        """Create a sample task"""
        task = models.Task(
            title="Original Title",
            description="Original Description",
            state=enums.State.todo,
            tag=enums.Tag.important,
            user_id=test_user.id
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)
        return task
    
    def test_update_task_success(self, client, db_session, sample_task):
        """Test successful task update"""
        update_data = {
            "title": "Updated Title",
            "description": "Updated Description",
            "state": "doing",
            "tag": "optional"
        }
        
        response = client.put(f"/task/{sample_task.id}", json=update_data)
        
        data = response.json()
        print(data)
        assert data["status"] == status.HTTP_200_OK
        assert data["message"] == "Task updated successfully"
        
        updated_task = db_session.query(models.Task).filter(
            models.Task.id == sample_task.id, models.Task.state==State.doing, models.Task.tag==Tag.optional
        ).first()
        assert updated_task.title == "Updated Title"
        assert updated_task.description == "Updated Description"
    
    def test_update_task_partial(self, client, db_session, sample_task):
        """Test partial task update"""
        update_data = {
            "title": "New Title Only"
        }
        
        response = client.put(f"/task/{sample_task.id}", json=update_data)
        
 
        data = response.json()
        assert data["status"] == status.HTTP_200_OK
        assert data["title"] == "New Title Only"
        assert data["description"] == "Original Description"  
    
    def test_update_task_not_found(self, client, db_session):
        """Test updating non-existent task"""
        update_data = {"title": "New Title"}
        
        response = client.put("/task/99999", json=update_data)
        
  
        data = response.json()
        assert data["status"] == status.HTTP_404_NOT_FOUND


class TestTaskStatistics:
    """Test cases for GET /task/stats/summary"""
    
    @pytest.fixture
    def varied_tasks(self, db_session, test_user):
        """Create tasks with various states"""
        tasks = [
            models.Task(title="Todo 1", state=enums.State.todo, user_id=test_user.id),
            models.Task(title="Todo 2", state=enums.State.todo, user_id=test_user.id),
            models.Task(title="Doing 1", state=enums.State.doing, user_id=test_user.id),
            models.Task(title="Done 1", state=enums.State.done, user_id=test_user.id),
            models.Task(title="Done 2", state=enums.State.done, user_id=test_user.id),
            models.Task(
                title="Overdue", 
                state=enums.State.todo, 
                user_id=test_user.id,
                due_date=datetime.now() - timedelta(days=1)
            ),
        ]
        
        for task in tasks:
            db_session.add(task)
        db_session.commit()
        return tasks
    
    def test_get_task_statistics(self, client, db_session, test_user, varied_tasks):
        """Test getting task statistics"""
        response = client.get("/task/stats/summary")
        
  
        data = response.json()
        assert data["status"] == status.HTTP_200_OK
        assert data["message"] == "Statistics retrieved successfully"
        
        stats = data["data"]
        assert stats["total"] == 6
        assert stats["todo"] == 3  
        assert stats["doing"] == 1
        assert stats["done"] == 2
        assert stats["overdue"] == 1
        assert "completion_rate" in stats
        assert stats["completion_rate"] == round(2/6 * 100, 2) 
    
    def test_get_statistics_empty(self, client, db_session, test_user):
        """Test statistics with no tasks"""
        response = client.get("/task/stats/summary")
        
  
        data = response.json()
        assert data["status"] == status.HTTP_200_OK
        
        stats = data["data"]
        assert stats["total"] == 0
        assert stats["completion_rate"] == 0
