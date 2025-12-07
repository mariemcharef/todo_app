from datetime import datetime
from fastapi.testclient import TestClient
import pytest
from app import models
from app.main import app
from app.oauth2 import get_current_user
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.orm import Session


@pytest.fixture
def test_user(db_session):
    user = models.User(
        email="testuser@example.com",
        first_name="John",
        last_name="Doe",
        password = "Abc123",

    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(autouse=True)
def override_dependency_with_real_user(test_user):
    def get_mock_user():
        return test_user

    app.dependency_overrides[get_current_user] = get_mock_user

    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def mock_db():
    """Create a mock database session"""
    db = Mock(spec=pytest.Session)
    db.query = Mock()
    db.add = Mock()
    db.commit = Mock()
    db.rollback = Mock()
    db.flush = Mock()
    db.refresh = Mock()
    return db