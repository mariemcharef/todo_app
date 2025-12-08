import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import status
from datetime import datetime, UTC
from app.routers import task
from app import schemas, enums

@pytest.fixture
def fake_user():
    user = MagicMock()
    user.id = 1
    user.email = "test@example.com"
    return user

class MockQuery:
    def __init__(self, task):
        self.task = task
    def filter(self, *args, **kwargs):
        return self
    def first(self):
        return self.task
    def update(self, values):
        for k, v in values.items():
            setattr(self.task, k, v)
    def commit(self):
        return None
    def refresh(self, task):
        return None
        
@pytest.fixture
def fake_task(fake_user):
    t = MagicMock()
    t.id = 1
    t.title = "Test Task"
    t.description = "Testing task"
    t.state = enums.State.todo
    t.tag = enums.Tag.optional
    t.user_id = fake_user.id
    t.created_on = datetime.now(UTC)
    t.updated_on = datetime.now(UTC)
    return t

# -----------------------------
# Tests
# -----------------------------

@pytest.mark.asyncio
async def test_add_task_success(fake_user, fake_task):
    task_data = schemas.taskIn(
        title=fake_task.title,
        description=fake_task.description,
        state=fake_task.state.value,
        tag=fake_task.tag.value
    )
    mock_db = MagicMock()
    mock_db.add.return_value = None
    mock_db.commit.return_value = None
    mock_db.refresh.return_value = None

    with patch('app.routers.task.schemas.taskOut', side_effect=lambda **kwargs: kwargs) as mock_schema:
        result = task.add(task_data, db=mock_db, current_user=fake_user)
        assert result["status"] == status.HTTP_201_CREATED
        assert "Task added successfully" in result["message"]
        assert result["title"] == fake_task.title


@pytest.mark.asyncio
async def test_get_task_success(fake_user, fake_task):
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = fake_task

    with patch('app.routers.task.schemas.taskOut', side_effect=lambda **kwargs: kwargs) as mock_schema:
        result = task.get_task(fake_task.id, db=mock_db, current_user=fake_user)
        assert result["status"] == status.HTTP_200_OK
        assert result["id"] == fake_task.id
        assert result["title"] == fake_task.title

@pytest.mark.asyncio
async def test_delete_task_success(fake_user, fake_task):
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = fake_task
    mock_db.commit.return_value = None

    with patch('app.routers.task.schemas.taskOut', side_effect=lambda **kwargs: kwargs) as mock_schema:
        result = task.delete_task(fake_task.id, db=mock_db, current_user=fake_user)
        assert result["status"] == status.HTTP_200_OK
        assert "Task deleted successfully" in result["message"]

@pytest.mark.asyncio
def test_mark_task_as_done_success(fake_user, fake_task):
    mock_db = MagicMock()
    mock_db.query.return_value = MockQuery(fake_task)

    with patch('app.routers.task.schemas.taskOut', side_effect=lambda **kwargs: kwargs):
        result = task.mark_task_as_done(fake_task.id, db=mock_db, current_user=fake_user)

    assert result["status"] == status.HTTP_200_OK
    assert result["state"] == enums.State.done
    assert "marked as done" in result["message"]

@pytest.mark.asyncio
def test_toggle_task_state_success(fake_user, fake_task):
    mock_db = MagicMock()
    mock_db.query.return_value = MockQuery(fake_task)

    with patch('app.routers.task.schemas.taskOut', side_effect=lambda **kwargs: kwargs) as mock_schema:
        result = task.toggle_task_state(fake_task.id, db=mock_db, current_user=fake_user)
        assert result["status"] == status.HTTP_200_OK
        print(result)
        assert result["state"] == enums.State.doing
        assert "Task state changed" in result["message"]

@pytest.mark.asyncio
async def test_get_task_stats_success(fake_user):
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.count.side_effect = [10, 3, 4, 3, 2]

    result = task.get_task_stats(db=mock_db, current_user=fake_user)
    assert result["status"] == status.HTTP_200_OK
    assert result["data"]["total"] == 10
    assert result["data"]["todo"] == 3
    assert result["data"]["doing"] == 4
    assert result["data"]["done"] == 3
    assert result["data"]["overdue"] == 2
