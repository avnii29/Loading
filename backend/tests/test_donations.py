from app.models.enums import DonationStatus
from app.services.status import assert_transition
from tests.conftest import cleanup_user
from tests.test_auth import register_payload


def scheduled_window() -> dict:
    from datetime import datetime, timedelta, timezone

    start = datetime.now(timezone.utc) + timedelta(days=2)
    end = start + timedelta(hours=4)
    return {
        "pickup_window_start": start.isoformat(),
        "pickup_window_end": end.isoformat(),
    }


def _auth(client, email):
    created = client.post("/api/auth/register", json=register_payload(email))
    assert created.status_code == 201, created.text
    login = client.post("/api/auth/login", json={"email": email, "password": "StrongPass1"})
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_donation_requires_auth(client):
    response = client.post(
        "/api/donations",
        json={"category": "BOOKS", "quantity": 2, "unit": "books", "description": "School readers"},
    )
    assert response.status_code == 401


def test_volunteer_can_donate_without_losing_volunteer_access(client, unique_email):
    from datetime import datetime, timedelta, timezone
    from uuid import UUID

    from app.database import SessionLocal
    from app.models.dispatch import VolunteerOffer

    owner_email = unique_email
    other_email = f"other-{unique_email}"
    client.post("/api/auth/register", json=register_payload(owner_email, role="VOLUNTEER", donor_type=None))
    client.post("/api/auth/register", json=register_payload(other_email, role="VOLUNTEER", donor_type=None))
    owner_login = client.post("/api/auth/login", json={"email": owner_email, "password": "StrongPass1"})
    other_login = client.post("/api/auth/login", json={"email": other_email, "password": "StrongPass1"})
    owner = {"Authorization": f"Bearer {owner_login.json()['access_token']}"}
    other = {"Authorization": f"Bearer {other_login.json()['access_token']}"}
    me = client.get("/api/auth/me", headers=owner)
    assert me.status_code == 200
    assert me.json()["role"] == "VOLUNTEER"
    owner_id = me.json()["id"]

    asap = client.post(
        "/api/donations",
        headers=owner,
        json={"category": "BOOKS", "quantity": 2, "unit": "books", "description": "Readers", "urgency": "ASAP"},
    )
    assert asap.status_code == 422, asap.text

    start = datetime.now(timezone.utc) + timedelta(days=2)
    end = start + timedelta(hours=4)
    created = client.post(
        "/api/donations",
        headers=owner,
        json={
            "category": "BOOKS",
            "quantity": 3,
            "unit": "books",
            "description": "Volunteer textbooks",
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
    donation_id = created.json()["id"]
    assert created.json()["is_donor"] is True
    try:
        still = client.get("/api/auth/me", headers=owner)
        assert still.json()["role"] == "VOLUNTEER"
        mine = client.get("/api/donations", headers=owner)
        assert mine.status_code == 200
        assert any(row["id"] == donation_id and row["is_donor"] for row in mine.json())
        offers = client.get("/api/logistics/offers", headers=owner)
        assert offers.status_code == 200
        assert not any(row["donation_id"] == donation_id and row["status"] == "PENDING" for row in offers.json())
        assignments = client.get("/api/logistics/assignments", headers=owner)
        assert assignments.status_code == 200

        other_offers = client.get("/api/logistics/offers", headers=other)
        pending = [row for row in other_offers.json() if row["donation_id"] == donation_id and row["status"] == "PENDING"]
        assert pending, other_offers.json()
        blocked = client.post(
            "/api/donations",
            headers=other,
            json={"category": "CLOTHES", "quantity": 1, "unit": "bags", "urgency": "ASAP", "cluster_window": "ASAP"},
        )
        assert blocked.status_code == 422

        db = SessionLocal()
        try:
            planted = VolunteerOffer(
                donation_id=UUID(donation_id),
                volunteer_id=UUID(owner_id),
                status="PENDING",
                summary="self",
                area_label="area",
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
            )
            db.add(planted)
            db.commit()
            planted_id = str(planted.id)
        finally:
            db.close()
        hidden = client.get("/api/logistics/offers", headers=owner)
        assert not any(row["donation_id"] == donation_id for row in hidden.json())
        self_accept = client.post(f"/api/logistics/offers/{planted_id}/accept", headers=owner)
        assert self_accept.status_code == 409, self_accept.text

        accepted = client.post(f"/api/logistics/offers/{pending[0]['id']}/accept", headers=other)
        assert accepted.status_code == 200, accepted.text
        cancel = client.post(f"/api/donations/{donation_id}/cancel", headers=other)
        assert cancel.status_code == 403, cancel.text

        again = client.post("/api/auth/login", json={"email": owner_email, "password": "StrongPass1"})
        owner_again = {"Authorization": f"Bearer {again.json()['access_token']}"}
        me_again = client.get("/api/auth/me", headers=owner_again)
        assert me_again.json()["role"] == "VOLUNTEER"
        mine_again = client.get("/api/donations", headers=owner_again)
        assert any(row["id"] == donation_id for row in mine_again.json())
        assert client.get("/api/logistics/offers", headers=owner_again).status_code == 200
    finally:
        cleanup_user(owner_email)
        cleanup_user(other_email)


def test_donation_persistence_and_status_history(client, unique_email):
    from datetime import datetime, timedelta, timezone

    headers = _auth(client, unique_email)
    start = datetime.now(timezone.utc) + timedelta(days=2)
    response = client.post(
        "/api/donations",
        headers=headers,
        json={
            "category": "BOOKS",
            "quantity": 4,
            "unit": "books",
            "description": "Gently used storybooks",
            "pickup_address": "Banjara Hills",
            "commercial": {
                "pickup_window_start": start.isoformat(),
                "pickup_window_end": (start + timedelta(hours=4)).isoformat(),
            },
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["reference_code"].startswith("DS-")
    assert body["status"] in {"ASSESSING", "MATCHING"}
    assert body["verification_code"]
    assert body["stream"] == "HUMAN_CONSUMPTION"
    assert len(body["history"]) >= 2

    listed = client.get("/api/donations", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    cleanup_user(unique_email)


def test_invalid_status_transition_rejection():
    try:
        assert_transition(DonationStatus.DRAFT, DonationStatus.COMPLETED)
        raise AssertionError("expected rejection")
    except ValueError:
        pass


def test_organization_cannot_self_verify(client, unique_email):
    created = client.post(
        "/api/auth/register",
        json=register_payload(
            unique_email,
            role="ORGANIZATION",
            donor_type=None,
            organization_name="Hope Kitchen",
        ),
    )
    assert created.status_code == 201, created.text
    assert created.json()["verification_status"] == "UNVERIFIED"

    login = client.post("/api/auth/login", json={"email": unique_email, "password": "StrongPass1"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    forbidden = client.post(
        "/api/admin/organizations/00000000-0000-0000-0000-000000000000/verification",
        headers=headers,
        json={"status": "VERIFIED"},
    )
    assert forbidden.status_code == 403

    public = client.get("/api/organizations", headers=headers)
    assert public.status_code == 200
    rows = public.json()
    # Self-registration stays off the public list. Research directory rows may
    # appear, but they must not be labeled as verified accounts.
    assert all(row["name"] != "Hope Kitchen" for row in rows)
    assert all(row["verification_status"] != "VERIFIED" or row["name"] != "Hope Kitchen" for row in rows)
    assert all(row["verification_status"] in {"VERIFIED", "DIRECTORY", "UNCONFIRMED"} for row in rows)

    cleanup_user(unique_email)
