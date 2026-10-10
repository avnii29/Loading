from app.services.location.coords import LatLng, decode_polyline, is_indian_pincode, validate_lat_lng
from app.services.location.errors import LocationError
from app.services.matching import eligible_destinations
from tests.conftest import cleanup_user
from tests.test_auth import register_payload
from tests.test_donations import _auth, scheduled_window


def test_rejects_invalid_coordinates():
    try:
        validate_lat_lng(91, 78)
        raise AssertionError("expected invalid latitude")
    except LocationError as exc:
        assert exc.code == "INVALID_COORDINATES"


def test_polyline_preserves_lat_lng_order():
    from app.services.location.coords import encode_polyline

    original = [LatLng(latitude=28.552413, longitude=77.131123), LatLng(latitude=17.3948, longitude=78.4374)]
    points = decode_polyline(encode_polyline(original))
    assert abs(points[0].latitude - original[0].latitude) < 0.0001
    assert abs(points[0].longitude - original[0].longitude) < 0.0001
    assert abs(points[1].latitude - original[1].latitude) < 0.0001


def test_pincode_is_approximate():
    assert is_indian_pincode("500001")
    assert not is_indian_pincode("Banjara Hills")


def test_broad_places_are_not_doorsteps():
    from app.services.location.osm import place_is_broad

    assert place_is_broad("suburb")
    assert place_is_broad("postcode")
    assert place_is_broad("attraction", query_is_area=True)
    assert not place_is_broad("attraction")
    assert not place_is_broad("house")


def test_location_search_without_credentials(client, unique_email):
    headers = _auth(client, unique_email)
    response = client.get("/api/location/search", headers=headers, params={"q": "Mehdipatnam"})
    assert response.status_code in {200, 404, 429, 503}
    if response.status_code != 200:
        assert response.json()["error"]["code"] in {
            "LOCATION_NOT_CONFIGURED",
            "LOCATION_SEARCH_UNAVAILABLE",
            "MAP_PROVIDER_AUTH_FAILED",
            "MAP_PROVIDER_RATE_LIMITED",
            "MAP_PROVIDER_TIMEOUT",
            "MAP_PROVIDER_UPSTREAM",
            "NO_LOCATION_RESULTS",
        }
    cleanup_user(unique_email)


def test_invalid_reverse_geocode_rejected(client, unique_email):
    headers = _auth(client, unique_email)
    response = client.post(
        "/api/location/reverse-geocode",
        headers=headers,
        json={"latitude": 120, "longitude": 78},
    )
    assert response.status_code == 422
    cleanup_user(unique_email)


def test_mappls_poi_is_not_an_eligible_destination(client, unique_email):
    headers = _auth(client, unique_email)
    created = client.post(
        "/api/donations",
        headers=headers,
        json={
            "category": "BOOKS",
            "quantity": 2,
            "unit": "books",
            "description": "Readers",
            "commercial": scheduled_window(),
        },
    )
    assert created.status_code == 201
    from app.database import SessionLocal
    from app.models.donation import Donation

    db = SessionLocal()
    try:
        donation = db.query(Donation).filter(Donation.reference_code == created.json()["reference_code"]).one()
        eligible = eligible_destinations(db, donation)
        assert all(org.verification_status.value == "VERIFIED" for _, org in eligible)
        assert not any(org.name.lower() == "mappls poi ngo" for _, org in eligible)
    finally:
        db.close()
    cleanup_user(unique_email)


def test_volunteer_cannot_read_unassigned_donation(client, unique_email):
    donor_headers = _auth(client, unique_email)
    donation = client.post(
        "/api/donations",
        headers=donor_headers,
        json={
            "category": "BOOKS",
            "quantity": 1,
            "unit": "books",
            "description": "Private address",
            "pickup_address": "12-2-417/A",
            "pickup_latitude": 17.3948,
            "pickup_longitude": 78.4374,
            "commercial": scheduled_window(),
        },
    )
    assert donation.status_code == 201
    donation_id = donation.json()["id"]

    volunteer_email = f"vol-{unique_email}"
    client.post(
        "/api/auth/register",
        json=register_payload(volunteer_email, role="VOLUNTEER", donor_type=None),
    )
    login = client.post("/api/auth/login", json={"email": volunteer_email, "password": "StrongPass1"})
    volunteer_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    hidden = client.get(f"/api/donations/{donation_id}", headers=volunteer_headers)
    assert hidden.status_code == 403
    cleanup_user(unique_email)
    cleanup_user(volunteer_email)


def test_location_config_does_not_leak_secrets(client, unique_email):
    headers = _auth(client, unique_email)
    response = client.get("/api/location/config", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert "access_token" not in str(body).lower()
    assert "client_secret" not in str(body).lower()
    cleanup_user(unique_email)


def test_encode_lng_lat_order():
    from app.services.location.coords import encode_lng_lat

    token = encode_lng_lat(LatLng(latitude=17.4, longitude=78.4))
    assert token == "78.4,17.4"


def test_null_island_coordinates_rejected(client, unique_email):
    headers = _auth(client, unique_email)
    response = client.post(
        "/api/donations",
        headers=headers,
        json={
            "category": "BOOKS",
            "quantity": 1,
            "unit": "books",
            "description": "Null island check",
            "pickup_latitude": 0,
            "pickup_longitude": 0,
        },
    )
    assert response.status_code == 422
    cleanup_user(unique_email)


def test_manual_pin_strips_gps_accuracy(client, unique_email):
    headers = _auth(client, unique_email)
    response = client.post(
        "/api/donations",
        headers=headers,
        json={
            "category": "BOOKS",
            "quantity": 1,
            "unit": "books",
            "description": "Manual pin",
            "pickup_latitude": 17.3948,
            "pickup_longitude": 78.4374,
            "location_source": "MANUAL_PIN",
            "location_accuracy_m": 12,
            "pickup_landmark": "Gate B",
            "location_confirmed_at": "2026-10-09T12:00:00+00:00",
            "commercial": scheduled_window(),
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["location_accuracy_m"] is None
    assert body["location_source"] == "MANUAL_PIN"
    assert body["pickup_landmark"] == "Gate B"
    assert body["location_confirmed_at"] is not None
    cleanup_user(unique_email)


def test_device_geolocation_keeps_accuracy_and_captured_at(client, unique_email):
    headers = _auth(client, unique_email)
    response = client.post(
        "/api/donations",
        headers=headers,
        json={
            "category": "CLOTHES",
            "quantity": 2,
            "unit": "bags",
            "description": "Device fix",
            "pickup_latitude": 17.385,
            "pickup_longitude": 78.4867,
            "location_source": "DEVICE_GEOLOCATION",
            "location_accuracy_m": 35,
            "location_captured_at": "2026-10-09T11:55:00+00:00",
            "location_confirmed_at": "2026-10-09T12:00:00+00:00",
            "commercial": scheduled_window(),
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["location_accuracy_m"] == 35
    assert body["location_source"] == "DEVICE_GEOLOCATION"
    assert body["location_captured_at"] is not None
    cleanup_user(unique_email)


def test_haversine_is_straight_line_not_road():
    from app.services.serializers import haversine_km

    # Same point → zero
    assert haversine_km(17.385, 78.4867, 17.385, 78.4867) == 0
    # Rough Hyderabad–Delhi order of magnitude (straight-line, not road)
    km = haversine_km(17.385, 78.4867, 28.6139, 77.209)
    assert 1100 < km < 1400
