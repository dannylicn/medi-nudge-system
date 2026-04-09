"""
conftest.py — shared test fixtures using in-memory SQLite.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.main import app
from app.models.models import User, Patient, Medication, PatientMedication

TEST_DATABASE_URL = "sqlite:///:memory:"
# Pre-computed bcrypt hash of "testpass" — avoids passlib/bcrypt version mismatch
_HASHED_TESTPASS = "$2b$12$nEtDwxYfbCTMee3b6KNmdu9j0s39itR4ZIO0ZYlDSxv7Y9DsTrGOW"


@pytest.fixture(scope="function")
def engine():
    eng = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # All connections share the same in-memory DB
    )
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)


@pytest.fixture()
def db(engine):
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def auth_token(db):
    """Create a test user and return a valid JWT."""
    existing = db.query(User).filter(User.email == "testcoord@test.com").first()
    if not existing:
        user = User(
            email="testcoord@test.com",
            hashed_password=_HASHED_TESTPASS,
            full_name="Test Coordinator",
        )
        db.add(user)
        db.commit()
    return create_access_token({"sub": "testcoord@test.com"})


@pytest.fixture()
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture()
def test_patient(db):
    """Create a reusable test patient."""
    p = Patient(
        full_name="Tan Ah Kow",
        phone_number="+6591234567",
        language_preference="en",
        risk_level="low",
        is_active=True,
        onboarding_state="complete",
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@pytest.fixture()
def test_medication(db):
    """Create a reusable test medication."""
    m = Medication(
        name="Metformin 500mg",
        generic_name="Metformin",
        default_refill_days=30,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return m

