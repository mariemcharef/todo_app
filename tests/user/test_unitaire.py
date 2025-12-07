import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app import models, oauth2
from app.oauth2 import get_current_user

import pytest
from unittest.mock import MagicMock, patch
from fastapi import status
from app.routers import user
from app import schemas, enums

# -----------------------------
# Fixtures
# -----------------------------

@pytest.fixture
def fake_user():
    u = MagicMock()
    u.id = 1
    u.first_name = "Test"
    u.last_name = "User"
    u.email = "test@example.com"
    u.password = "hashedpassword"
    return u

@pytest.fixture
def fake_user_data():
    return schemas.User(
        first_name="Test",
        last_name="User",
        email="test@example.com",
        password="password",
        confirm_password="password"
    )

class MockQuery:
    def __init__(self, obj=None):
        self.obj = obj

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.obj

    def all(self):
        return [self.obj] if self.obj else []

    def count(self):
        return 1 if self.obj else 0

    def limit(self, n):
        return self

    def offset(self, n):
        return self

    def update(self, values):
        for k, v in values.items():
            setattr(self.obj, k, v)

    def commit(self):
        return None

    def refresh(self, obj):
        return None

# -----------------------------
# Tests
# -----------------------------

@pytest.mark.asyncio
async def test_create_user_success(fake_user_data):
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None
    mock_db.add.return_value = None
    mock_db.flush.return_value = None
    mock_db.commit.return_value = None

    with patch("app.routers.user.register_user", return_value=fake_user_data), \
         patch("app.routers.user.sendConfirmationMail", new_callable=MagicMock), \
         patch("app.routers.user.schemas.UserOut", side_effect=lambda **kwargs: kwargs):
        result = await user.create_user(fake_user_data, db=mock_db)

    assert result["status"] == status.HTTP_201_CREATED
    assert "User created successfully" in result["message"]
    assert result["email"] == fake_user_data.email

@pytest.mark.asyncio
async def test_create_user_email_exists(fake_user_data):
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = fake_user_data

    with patch("app.routers.user.schemas.UserOut", side_effect=lambda **kwargs: kwargs):
        result = await user.create_user(fake_user_data, db=mock_db)

    assert result["status"] == status.HTTP_400_BAD_REQUEST
    assert "Email already used" in result["message"]

def test_get_current_user_success(fake_user):
    mock_db = MagicMock()
    mock_db.query.return_value = MockQuery(fake_user)

    with patch("app.routers.user.schemas.UserOut", side_effect=lambda **kwargs: kwargs):
        result = user.get_current_user(db=mock_db, current_user=fake_user)

    assert result["status"] == status.HTTP_200_OK
    assert result["id"] == fake_user.id

def test_get_users_list_success(fake_user):
    mock_db = MagicMock()
    mock_db.query.return_value = MockQuery(fake_user)

    with patch("app.routers.user.schemas.UsersOut", side_effect=lambda **kwargs: kwargs):
        result = user.get_users(db=mock_db, current_user=fake_user)

    assert result["status"] == status.HTTP_200_OK
    print(result)
    assert result == {
        'total_pages': 1, 
        'total_records': 1, 
        'page_number': 1, 
        'page_size': 10, 
        'list': [schemas.UserOut(message=None, status=None, id=1, first_name='Test', last_name='User', email='test@example.com', confirmed=None, created_on=None, new_token=None)], 'message': 'All users', 'status': 200}


def test_update_user_authorized_success(fake_user):
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = fake_user

    edit_data = schemas.EditUser(first_name="NewName", last_name="NewLast", email="test@example.com")

    with patch("app.routers.user.oauth2.create_access_token", return_value="token123"), \
         patch("app.routers.user.schemas.UserOut", side_effect=lambda **kwargs: kwargs):
        result = user.update_user(fake_user.id, edit_data, db=mock_db, current_user=fake_user)
    print(result)
    assert result["status"] == status.HTTP_200_OK
    assert "User updated successfully" in result["message"]
    assert result["new_token"] == "token123"

def test_update_user_unauthorized(fake_user):
    mock_db = MagicMock()

    edit_data = schemas.EditUser(first_name="Hack", last_name="User")

    with patch("app.routers.user.schemas.UserOut", side_effect=lambda **kwargs: kwargs):
        result = user.update_user(999, edit_data, db=mock_db, current_user=fake_user)

    assert result["status"] == status.HTTP_401_UNAUTHORIZED
    assert "not authorized" in result["message"]
