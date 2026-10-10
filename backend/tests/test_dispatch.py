from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.models.donation import Donation, DonationQualityCheck
from app.models.enums import (
    DonationCategory,
    DonationStatus,
    DonationStream,
    QualityResult,
    QualityStage,
)
from app.services.priority import score_donation
from tests.conftest import cleanup_user
from tests.test_auth import register_payload
from tests.test_donations import _auth


def test_food_outranks_books_priority():
    now = datetime.now(timezone.utc)
    food = Donation(
        reference_code="DS-FOOD1",
        donor_id=None,  # type: ignore[arg-type]
        stream=DonationStream.HUMAN_CONSUMPTION,
        category=DonationCategory.FOOD,
        status=DonationStatus.ASSESSING,
        quantity=Decimal("10"),
        unit="meals",
        food_source="FUNCTION_HALL",
        urgency="HIGH",
        prepared_at=now - timedelta(minutes=30),
        created_at=now - timedelta(minutes=5),
        quality_checks=[
            DonationQualityCheck(
                stage=QualityStage.DONOR_SELF,
                result=QualityResult.ACCEPTABLE,
                responses={"freshly_cooked": True, "still_warm": True, "stored_properly": True, "covered": True},
                created_at=now,
            )
        ],
    )
    books = Donation(
        reference_code="DS-BOOK1",
        donor_id=None,  # type: ignore[arg-type]
        stream=DonationStream.HUMAN_CONSUMPTION,
        category=DonationCategory.BOOKS,
        status=DonationStatus.ASSESSING,
        quantity=Decimal("20"),
        unit="books",
        created_at=now - timedelta(hours=6),
        quality_checks=[],
    )
    food_score = score_donation(food, now=now)
    books_score = score_donation(books, now=now)
    assert food_score.eligible
    assert books_score.eligible
    assert food_score.score > books_score.score
    assert food_score.priority_class in {"P0", "P1", "P2"}
    assert books_score.priority_class == "P3"


def test_food_without_quality_is_held():
    now = datetime.now(timezone.utc)
    food = Donation(
        reference_code="DS-FOOD2",
        donor_id=None,  # type: ignore[arg-type]
        stream=DonationStream.HUMAN_CONSUMPTION,
        category=DonationCategory.FOOD,
        status=DonationStatus.ASSESSING,
        quantity=Decimal("5"),
        unit="meals",
        created_at=now,
        quality_checks=[],
    )
    result = score_donation(food, now=now)
    assert result.eligible is False
    assert result.hold_reason == "safety_hold"


def test_offer_accept_is_exclusive(client, unique_email):
    # Register volunteers before submit so both receive timed offers.
    vol_a = f"va-{unique_email}"
    vol_b = f"vb-{unique_email}"
    for email in (vol_a, vol_b):
        reg = client.post("/api/auth/register", json=register_payload(email, role="VOLUNTEER", donor_type=None))
        assert reg.status_code in {201, 200}, reg.text
    login_a = client.post("/api/auth/login", json={"email": vol_a, "password": "StrongPass1"})
    login_b = client.post("/api/auth/login", json={"email": vol_b, "password": "StrongPass1"})
    headers_a = {"Authorization": f"Bearer {login_a.json()['access_token']}"}
    headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}

    donor_headers = _auth(client, unique_email)
    checklist = {
        "stored_safely": "YES",
        "covered": "YES",
        "packaging": "PACKED",
    }
    created = client.post(
        "/api/donations",
        headers=donor_headers,
        json={
            "category": "FOOD",
            "quantity": 8,
            "unit": "meals",
            "description": "Wedding surplus rice",
            "food_source": "FUNCTION_HALL",
            "diet_type": "DRY_RATIONS",
            "urgency": "HIGH",
            "prepared_at": datetime.now(timezone.utc).isoformat(),
            "pickup_latitude": 17.3948,
            "pickup_longitude": 78.4374,
            "pickup_address": "Mehdipatnam",
            "location_source": "MANUAL_PIN",
            "quality_checklist": checklist,
        },
    )
    assert created.status_code == 201, created.text
    donation_id = created.json()["id"]

    offers_a = client.get("/api/logistics/offers", headers=headers_a)
    offers_b = client.get("/api/logistics/offers", headers=headers_b)
    assert offers_a.status_code == 200, offers_a.text
    assert offers_b.status_code == 200, offers_b.text
    pending_a = [o for o in offers_a.json() if o["donation_id"] == donation_id and o["status"] == "PENDING"]
    pending_b = [o for o in offers_b.json() if o["donation_id"] == donation_id and o["status"] == "PENDING"]
    assert pending_a, offers_a.json()
    assert pending_b, offers_b.json()
    ok = client.post(f"/api/logistics/offers/{pending_a[0]['id']}/accept", headers=headers_a)
    assert ok.status_code == 200, ok.text
    conflict = client.post(f"/api/logistics/offers/{pending_b[0]['id']}/accept", headers=headers_b)
    assert conflict.status_code == 409

    cleanup_user(unique_email)
    cleanup_user(vol_a)
    cleanup_user(vol_b)


def _future_window():
    start = datetime.now(timezone.utc) + timedelta(days=2, hours=1)
    return start, start + timedelta(hours=4)


def test_expired_offer_is_reissued_and_assignable(client, unique_email):
    vol = f"vr-{unique_email}"
    registered = client.post("/api/auth/register", json=register_payload(vol, role="VOLUNTEER", donor_type=None))
    assert registered.status_code in {201, 200}, registered.text
    login = client.post("/api/auth/login", json={"email": vol, "password": "StrongPass1"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    donor_headers = _auth(client, unique_email)
    created = client.post(
        "/api/donations",
        headers=donor_headers,
        json={
            "category": "FOOD",
            "quantity": 4,
            "unit": "meals",
            "description": "Sealed rice",
            "food_source": "HOME",
            "diet_type": "DRY_RATIONS",
            "urgency": "HIGH",
            "cluster_window": "ASAP",
            "pickup_latitude": 17.3616,
            "pickup_longitude": 78.4746,
            "pickup_address": "Charminar area",
            "quality_checklist": {"stored_safely": "YES", "covered": "YES"},
        },
    )
    assert created.status_code == 201, created.text
    donation_id = created.json()["id"]
    try:
        first = client.get("/api/logistics/offers", headers=headers)
        assert first.status_code == 200, first.text
        pending = [row for row in first.json() if row["donation_id"] == donation_id and row["status"] == "PENDING"]
        assert pending, first.json()
        assignments = client.get("/api/logistics/assignments", headers=headers)
        assert assignments.status_code == 200
        assert not any(row["donation_id"] == donation_id and row["status"] in {"ACCEPTED", "EN_ROUTE"} for row in assignments.json())

        from app.database import SessionLocal
        from app.models.dispatch import VolunteerOffer

        db = SessionLocal()
        try:
            rows = db.query(VolunteerOffer).filter(VolunteerOffer.donation_id == donation_id).all()
            for row in rows:
                row.status = "PENDING"
                row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=5)
            db.commit()
        finally:
            db.close()

        second = client.get("/api/logistics/offers", headers=headers)
        renewed = [row for row in second.json() if row["donation_id"] == donation_id and row["status"] == "PENDING"]
        assert renewed, second.json()
        assert renewed[0]["id"] != pending[0]["id"]
        assert renewed[0]["seconds_remaining"] > 0
        accepted = client.post(f"/api/logistics/offers/{renewed[0]['id']}/accept", headers=headers)
        assert accepted.status_code == 200, accepted.text
        after = client.get("/api/logistics/assignments", headers=headers)
        assert any(row["donation_id"] == donation_id and row["status"] == "ACCEPTED" for row in after.json())
    finally:
        cleanup_user(unique_email)
        cleanup_user(vol)


def test_cancelled_donation_is_not_offered(client, unique_email):
    vol = f"vc-{unique_email}"
    client.post("/api/auth/register", json=register_payload(vol, role="VOLUNTEER", donor_type=None))
    login = client.post("/api/auth/login", json={"email": vol, "password": "StrongPass1"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    donor_headers = _auth(client, unique_email)
    created = client.post(
        "/api/donations",
        headers=donor_headers,
        json={
            "category": "FOOD",
            "quantity": 3,
            "unit": "meals",
            "description": "Dal packets",
            "food_source": "HOME",
            "diet_type": "DRY_RATIONS",
            "urgency": "NORMAL",
            "cluster_window": "TOMORROW_MORNING",
            "quality_checklist": {"stored_safely": "YES", "covered": "YES"},
        },
    )
    assert created.status_code == 201, created.text
    donation_id = created.json()["id"]
    try:
        cancelled = client.post(f"/api/donations/{donation_id}/cancel", headers=donor_headers)
        assert cancelled.status_code == 200, cancelled.text
        offers = client.get("/api/logistics/offers", headers=headers)
        assert not any(row["donation_id"] == donation_id and row["status"] == "PENDING" for row in offers.json())
    finally:
        cleanup_user(unique_email)
        cleanup_user(vol)


def test_nonfood_asap_is_rejected(client, unique_email):
    headers = _auth(client, unique_email)
    try:
        for category in ("BOOKS", "CLOTHES", "TOYS", "OTHER"):
            response = client.post(
                "/api/donations",
                headers=headers,
                json={
                    "category": category,
                    "quantity": 2,
                    "unit": "boxes",
                    "description": "Usable goods",
                    "urgency": "ASAP",
                    "cluster_window": "ASAP",
                },
            )
            assert response.status_code == 422, response.text
            assert "scheduled" in response.json()["error"]["message"].lower()
    finally:
        cleanup_user(unique_email)


def test_nonfood_requires_future_window_and_is_offered_as_scheduled(client, unique_email):
    vol = f"vs-{unique_email}"
    client.post("/api/auth/register", json=register_payload(vol, role="VOLUNTEER", donor_type=None))
    login = client.post("/api/auth/login", json={"email": vol, "password": "StrongPass1"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    donor_headers = _auth(client, unique_email)
    try:
        missing = client.post(
            "/api/donations",
            headers=donor_headers,
            json={"category": "BOOKS", "quantity": 2, "unit": "books", "description": "Textbooks"},
        )
        assert missing.status_code == 422, missing.text
        past = datetime.now(timezone.utc) - timedelta(hours=2)
        rejected = client.post(
            "/api/donations",
            headers=donor_headers,
            json={
                "category": "CLOTHES",
                "quantity": 2,
                "unit": "bags",
                "description": "Winter clothes",
                "commercial": {
                    "pickup_window_start": past.isoformat(),
                    "pickup_window_end": (past + timedelta(hours=3)).isoformat(),
                },
            },
        )
        assert rejected.status_code == 422, rejected.text
        start, end = _future_window()
        for category, unit in (("BOOKS", "books"), ("CLOTHES", "bags"), ("TOYS", "pieces"), ("OTHER", "boxes")):
            created = client.post(
                "/api/donations",
                headers=donor_headers,
                json={
                    "category": category,
                    "quantity": 2,
                    "unit": unit,
                    "description": f"Scheduled {category.lower()}",
                    "pickup_latitude": 17.4,
                    "pickup_longitude": 78.45,
                    "pickup_address": "Mehdipatnam",
                    "commercial": {
                        "pickup_window_start": start.isoformat(),
                        "pickup_window_end": end.isoformat(),
                    },
                },
            )
            assert created.status_code == 201, created.text
            body = created.json()
            assert body["cluster_window"]
            assert "ASAP" not in body["cluster_window"]
            offers = client.get("/api/logistics/offers", headers=headers)
            match = [row for row in offers.json() if row["donation_id"] == body["id"] and row["status"] == "PENDING"]
            assert match, offers.json()
            assert match[0]["pickup_schedule"]
            assert "ASAP" not in match[0]["pickup_schedule"]
            assert match[0]["pickup_latitude"] == 17.4
            assert match[0]["pickup_longitude"] == 78.45
            start = end + timedelta(hours=1)
            end = start + timedelta(hours=4)
    finally:
        cleanup_user(unique_email)
        cleanup_user(vol)


def test_food_checklist_required(client, unique_email):
    headers = _auth(client, unique_email)
    response = client.post(
        "/api/donations",
        headers=headers,
        json={"category": "FOOD", "quantity": 2, "unit": "meals", "description": "Rice"},
    )
    assert response.status_code == 422
    cleanup_user(unique_email)
