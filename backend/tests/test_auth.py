from tests.conftest import cleanup_user
from app.services.login_identity import resolve_login_email


def register_payload(email: str, **overrides):
    data = {
        "email": email,
        "password": "StrongPass1",
        "full_name": "Test Person",
        "phone": "9876543210",
        "role": "DONOR",
        "donor_type": "HOUSEHOLD",
    }
    data.update(overrides)
    return data


def test_register_validation_short_password(client, unique_email):
    response = client.post(
        "/api/auth/register",
        json=register_payload(unique_email, password="short"),
    )
    assert response.status_code == 422


def test_admin_public_registration_rejected(client, unique_email):
    response = client.post(
        "/api/auth/register",
        json=register_payload(unique_email, role="ADMIN", donor_type=None),
    )
    assert response.status_code == 403
    assert "Admin" in response.json()["error"]["message"]


def test_donor_requires_donor_type(client, unique_email):
    response = client.post(
        "/api/auth/register",
        json=register_payload(unique_email, donor_type=None),
    )
    assert response.status_code == 422


def test_non_donor_donor_type_rejected(client, unique_email):
    response = client.post(
        "/api/auth/register",
        json=register_payload(unique_email, role="VOLUNTEER", donor_type="HOUSEHOLD"),
    )
    assert response.status_code == 422
    cleanup_user(unique_email)


def test_login_failure_and_success_and_me(client, unique_email):
    created = client.post("/api/auth/register", json=register_payload(unique_email))
    assert created.status_code == 201, created.text

    failed = client.post(
        "/api/auth/login",
        json={"email": unique_email, "password": "wrong-password"},
    )
    assert failed.status_code == 401

    login = client.post(
        "/api/auth/login",
        json={"email": unique_email, "password": "StrongPass1"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    assert token

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    body = me.json()
    assert body["email"] == unique_email
    assert body["role"] == "DONOR"
    assert body["donor_type"] == "HOUSEHOLD"

    cleanup_user(unique_email)


def test_short_id_resolves_to_sample_domain():
    assert resolve_login_email("abc") == "abc@anuvarthan.test"
    assert resolve_login_email("ABC") == "abc@anuvarthan.test"
    assert resolve_login_email("org@anuvarthan.test") == "org@anuvarthan.test"
    assert resolve_login_email("  ghi  ") == "ghi@anuvarthan.test"
