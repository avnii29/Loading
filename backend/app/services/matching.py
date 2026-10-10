from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.donation import Donation
from app.models.enums import IntakeStatus, VerificationStatus
from app.models.organization import Destination, Organization
from app.services.location import mappls_service, service_area
from app.services.location.coords import LatLng
from app.services.location.errors import LocationError
from app.services.serializers import haversine_km


@dataclass(slots=True)
class MatchCandidate:
    destination: Destination
    organization: Organization
    verified: bool
    intake_open: bool
    category_compatible: bool
    within_service_area: bool | None
    road_distance_meters: float | None
    estimated_duration_seconds: float | None
    geo_provider: str | None
    reasons: list[str]


def eligible_destinations(db: Session, donation: Donation) -> list[tuple[Destination, Organization]]:
    """Anuvarthan database rules only. Mappls POIs never enter this list."""
    rows = list(
        db.execute(
            select(Destination, Organization)
            .join(Organization, Destination.organization_id == Organization.id)
            .where(
                Organization.verification_status == VerificationStatus.VERIFIED,
                Organization.is_active.is_(True),
                Organization.is_demo.is_(False),
                Destination.is_active.is_(True),
            )
        )
    )
    eligible: list[tuple[Destination, Organization]] = []
    for dest, org in rows:
        accepted = dest.accepted_categories or org.accepted_categories or []
        if accepted and donation.category.value not in accepted:
            continue
        eligible.append((dest, org))
    return eligible


def evaluate_candidates(db: Session, donation: Donation) -> list[MatchCandidate]:
    origin = None
    if donation.pickup_latitude is not None and donation.pickup_longitude is not None:
        origin = LatLng(float(donation.pickup_latitude), float(donation.pickup_longitude))

    scored: list[MatchCandidate] = []
    eligible = eligible_destinations(db, donation)
    dest_points: list[tuple[Destination, Organization, LatLng]] = []
    for dest, org in eligible:
        lat = dest.latitude if dest.latitude is not None else org.latitude
        lng = dest.longitude if dest.longitude is not None else org.longitude
        point = LatLng(float(lat), float(lng)) if lat is not None and lng is not None else None
        if point:
            dest_points.append((dest, org, point))
        else:
            scored.append(_candidate(dest, org, donation, origin, None, None, None))

    matrix: dict[tuple[float, float], tuple[float, float, str]] = {}
    if origin and dest_points and mappls_service.configured():
        try:
            results = mappls_service.distance_matrix(origin, [item[2] for item in dest_points])
            for item in results:
                matrix[(item.destination.latitude, item.destination.longitude)] = (
                    item.distance_meters,
                    item.duration_seconds,
                    item.provider,
                )
        except LocationError:
            matrix = {}

    for dest, org, point in dest_points:
        road = matrix.get((point.latitude, point.longitude))
        scored.append(
            _candidate(
                dest,
                org,
                donation,
                origin,
                road[0] if road else None,
                road[1] if road else None,
                road[2] if road else None,
                point,
            )
        )
    scored.sort(key=lambda item: item.road_distance_meters if item.road_distance_meters is not None else 10**9)
    return scored


def _candidate(
    dest: Destination,
    org: Organization,
    donation: Donation,
    origin: LatLng | None,
    distance_m: float | None,
    duration_s: float | None,
    geo_provider: str | None,
    dest_point: LatLng | None = None,
) -> MatchCandidate:
    accepted = dest.accepted_categories or org.accepted_categories or []
    category_ok = not accepted or donation.category.value in accepted
    intake_open = org.intake_status == IntakeStatus.OPEN
    verified = org.verification_status == VerificationStatus.VERIFIED
    within = service_area.contains(dest_point) if dest_point else None
    reasons = []
    if verified:
        reasons.append("verified")
    if intake_open:
        reasons.append("intake open")
    else:
        reasons.append("intake limited")
    if category_ok:
        reasons.append("category compatible")
    if within is True:
        reasons.append("within service area")
    elif within is False:
        reasons.append("outside service area")
    if distance_m is not None:
        reasons.append(f"road distance {round(distance_m / 1000, 2)} km")
    elif origin and dest_point:
        reasons.append(f"approx {haversine_km(origin.latitude, origin.longitude, dest_point.latitude, dest_point.longitude)} km aerial")
    if duration_s is not None:
        reasons.append(f"estimated {round(duration_s / 60)} min")
    if donation.distribution_deadline and duration_s is not None:
        remaining = (donation.distribution_deadline - datetime.now(timezone.utc)).total_seconds()
        if remaining < duration_s + 15 * 60:
            reasons.append("freshness window may be tight")
    return MatchCandidate(
        destination=dest,
        organization=org,
        verified=verified,
        intake_open=intake_open,
        category_compatible=category_ok,
        within_service_area=within,
        road_distance_meters=distance_m,
        estimated_duration_seconds=duration_s,
        geo_provider=geo_provider,
        reasons=reasons,
    )
