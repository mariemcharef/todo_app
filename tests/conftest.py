from app.config import settings
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, quoted_name, text
from sqlalchemy.orm import sessionmaker, Session
from app.main import app
from app.database import Base, get_db
from app.oauth2 import get_current_user
from app import models, utils

TEST_SQLALCHEMY_DATABASE_URL = f'postgresql://{settings.database_username}:{settings.database_password}@{settings.database_hostname}/{settings.test_database_name}'
TEST_DATABASE_URL = f'postgresql://{settings.database_username}:{settings.database_password}@{settings.database_hostname}/postgres'


@pytest.fixture(scope="session", autouse=True)
def create_test_database():
    """Create test database if it doesn't exist"""
    admin_engine = create_engine(TEST_DATABASE_URL, isolation_level="AUTOCOMMIT")

    with admin_engine.connect() as conn:
        db = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :db_name;"),
            {"db_name": settings.test_database_name}
        ).fetchone()
        if not db:
            dbname = quoted_name(settings.test_database_name, quote=True)
            conn.execute(text(f'CREATE DATABASE {dbname}'))

    yield
    
    with admin_engine.connect() as conn:
        conn.execute(text(f"""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = :db_name
            AND pid <> pg_backend_pid();
        """), {"db_name": settings.test_database_name})
        
        dbname = quoted_name(settings.test_database_name, quote=True)
        conn.execute(text(f'DROP DATABASE IF EXISTS {dbname}'))


@pytest.fixture(scope="session")
def test_engine():
    """Create test database engine and tables"""
    _engine = create_engine(TEST_SQLALCHEMY_DATABASE_URL)

    Base.metadata.create_all(bind=_engine)

    yield _engine

    Base.metadata.drop_all(bind=_engine)


@pytest.fixture
def db_session(test_engine):
    """
    Create a transactional database session for each test.
    All changes are rolled back after the test.
    """
    connection = test_engine.connect()
    transaction = connection.begin()

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    session = SessionLocal()

    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(sess, trans):
        """Automatically restart savepoint after each commit"""
        if trans.nested and not trans._parent.nested:
            session.expire_all()
            connection.begin_nested()

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def test_user(db_session):
    """Create a test user for authentication"""
    hashed_password = utils.hash_password("Abc123")
    user = models.User(
        email="testuser@example.com",
        first_name="John",
        last_name="Doe",
        password=hashed_password,
        confirmed=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def client(db_session, test_user):
    """
    Create a test client with database session and authentication overrides.
    This fixture combines both the database session and authentication.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    def override_get_current_user():
        return test_user
    
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def unauthenticated_client(db_session):
    """
    Create a test client without authentication override.
    Useful for testing endpoints that don't require authentication.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def test_user_unconfirmed(db_session):
    """Create an unconfirmed test user"""
    hashed_password = utils.hash_password("Password123")
    user = models.User(
        email="unconfirmed@example.com",
        first_name="Unconfirmed",
        last_name="User",
        password=hashed_password,
        confirmed=False
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def multiple_test_users(db_session):
    """Create multiple test users"""
    users = []
    for i in range(5):
        hashed_password = utils.hash_password(f"Password{i}")
        user = models.User(
            email=f"user{i}@example.com",
            first_name=f"User{i}",
            last_name=f"Test{i}",
            password=hashed_password,
            confirmed=True
        )
        db_session.add(user)
        users.append(user)
    
    db_session.commit()
    for user in users:
        db_session.refresh(user)
    
    return users

def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )


def pytest_collection_modifyitems(config, items):
    """Automatically mark all tests in certain directories"""
    for item in items:
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
