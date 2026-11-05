"""Pytest configuration and test fixtures."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from src.database.database import Base
import src.api.dependencies as api_deps
from src.services.transaction_service import TransactionService
from main import app

# In-memory SQLite for testing isolation
TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="session")
def engine():
    test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=test_engine)
    return test_engine

@pytest.fixture(scope="function")
def db_session(engine):
    """Provides a fresh isolated database session per test function."""
    connection = engine.connect()
    transaction = connection.begin()
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    session = TestingSessionLocal()

    yield session

    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
def client(db_session):
    """FastAPI TestClient with overridden get_db dependency."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[api_deps.get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def sample_csv_data():
    return """date,amount,category,description,transaction_type,payment_method,account
2026-08-01,5000.00,Salary,August Payroll,income,Direct Deposit,Primary Checking
2026-08-02,1500.00,Rent,August Apartment Rent,expense,ACH Transfer,Primary Checking
2026-08-03,120.50,Groceries,Supermarket Food,expense,Credit Card,Rewards Card
2026-08-05,45.00,Dining,Lunch Bistro,expense,Credit Card,Rewards Card
2026-08-10,80.00,Utilities,Electric Bill,expense,Autopay,Primary Checking
2026-08-15,150.00,Groceries,Weekly Groceries,expense,Credit Card,Rewards Card
2026-08-20,600.00,Dining,Expensive VIP Banquet,expense,Credit Card,Rewards Card
"""

@pytest.fixture
def populated_db(db_session, sample_csv_data):
    """Populates test database with sample_csv_data."""
    TransactionService.import_csv(db_session, sample_csv_data)
    return db_session
