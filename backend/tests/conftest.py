import uuid

import pytest
from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models.donation import Donation
from app.models.user import User


@pytest.fixture(autouse=True)
def _isolated_rate_limits():
    """Each test gets a fresh limiter. Production limits stay in place."""
    from app.security.rate_limit import auth_limiter, location_limiter

    auth_limiter.reset()
    location_limiter.reset()
    yield
    auth_limiter.reset()
    location_limiter.reset()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def unique_email():
    return f"test-{uuid.uuid4().hex[:12]}@example.com"


def cleanup_user(email: str) -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).one_or_none()
        if user:
            for donation in db.query(Donation).filter(Donation.donor_id == user.id).all():
                db.delete(donation)
            db.delete(user)
            db.commit()
    finally:
        db.close()
