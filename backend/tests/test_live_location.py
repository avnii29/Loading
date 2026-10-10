from app.schemas.organization import OrganizationPublic
from app.routers.organizations import nearby_only
from app.services.live_location import freshness
from datetime import datetime, timedelta, timezone


def test_nearby_filter_drops_other_cities_and_missing_coords():
    items = [
        OrganizationPublic(
            id="near",
            name="Near",
            description=None,
            verification_status="VERIFIED",
            intake_status="OPEN",
            address=None,
            city="Here",
            latitude=17.4,
            longitude=78.4,
            accepted_categories=None,
            distance_km=3.2,
        ),
        OrganizationPublic(
            id="far",
            name="Far",
            description=None,
            verification_status="VERIFIED",
            intake_status="OPEN",
            address=None,
            city="Elsewhere",
            latitude=28.6,
            longitude=77.2,
            accepted_categories=None,
            distance_km=1250,
        ),
        OrganizationPublic(
            id="nocoord",
            name="No pin",
            description=None,
            verification_status="VERIFIED",
            intake_status="OPEN",
            address=None,
            city="Unknown",
            latitude=None,
            longitude=None,
            accepted_categories=None,
            distance_km=None,
        ),
    ]
    kept = nearby_only(items, 40)
    assert [item.id for item in kept] == ["near"]


def test_freshness_bands():
    now = datetime.now(timezone.utc)
    assert freshness(now - timedelta(seconds=10), now) == "live"
    assert freshness(now - timedelta(seconds=90), now) == "recent"
    assert freshness(now - timedelta(minutes=10), now) == "stale"
