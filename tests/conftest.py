from app.config import settings
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, quoted_name, text
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db

TEST_SQLALCHEMY_DATABASE_URL = f'postgresql://{settings.database_username}:{settings.database_password}@{settings.database_hostname}/{settings.test_database_name}'
TEST_DATABASE_URL = f'postgresql://{settings.database_username}:{settings.database_password}@{settings.database_hostname}/postgres'


@pytest.fixture(scope="session", autouse=True)
def create_test_database():
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

@pytest.fixture(scope="session")
def test_engine():
    _engine = create_engine(TEST_SQLALCHEMY_DATABASE_URL)

    Base.metadata.create_all(bind=_engine)

    yield _engine

    Base.metadata.drop_all(bind=_engine)

@pytest.fixture
def db_session(test_engine):
    """
    Per-test:
    - begin a transaction
    - create a nested transaction (savepoint)
    - rollback everything at the end
    """
    connection = test_engine.connect()
    transaction = connection.begin()

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    session = SessionLocal()

    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(conn, trans):
        if trans is nested:
            conn.begin_nested()

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client using the transactional session"""
    def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
 
    app.dependency_overrides.clear()
