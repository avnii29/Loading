from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.deps import get_current_user, require_roles
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.location import (
    LocationConfigOut,
    LocationResultOut,
    MatchCandidateOut,
    ReverseGeocodeIn,
    RoutePreviewIn,
    RoutePreviewOut,
)
from app.security.rate_limit import client_key, location_limiter
from app.services.donation import get_donation
from app.services.location import mappls_service, service_area
from app.services.location.coords import LatLng, is_indian_pincode, validate_lat_lng
from app.services.matching import evaluate_candidates

router = APIRouter(prefix="/api/location", tags=["location"])
settings = get_settings()


def _out(item) -> LocationResultOut:
    return LocationResultOut(
        provider=item.provider,
        name=item.name,
        formatted_address=item.formatted_address,
        locality=item.locality,
        city=item.city,
        state=item.state,
        pincode=item.pincode,
        landmark=item.landmark,
        latitude=item.latitude,
        longitude=item.longitude,
        mappls_pin=item.mappls_pin,
        provider_place_id=item.provider_place_id,
        confidence=item.confidence,
        precision=item.precision,
        kind=item.kind,
        approximate=item.approximate,
    )


@router.get("/config", response_model=LocationConfigOut)
def location_config(_user: User = Depends(get_current_user)):
    configured = mappls_service.configured()
    center = None
    if service_area.center:
        center = {"latitude": service_area.center.latitude, "longitude": service_area.center.longitude}
    return LocationConfigOut(
        provider=settings.map_provider,
        configured=configured,
        search=configured,
        geocoding=configured,
        reverse_geocoding=configured,
        routing=configured,
        distance_matrix=configured,
        route_optimisation="NOT_ENABLED"
        if not settings.mappls_route_optimization_enabled
        else "CONFIG_REQUIRED",
        service_area_name=service_area.name,
        service_area_center=center,
        service_area_radius_km=service_area.radius_km,
    )


@router.get("/search", response_model=list[LocationResultOut])
def search_places(
    request: Request,
    q: str = Query(min_length=1, max_length=45),
    lat: float | None = None,
    lng: float | None = None,
    resolve: bool = False,
    _user: User = Depends(get_current_user),
):
    location_limiter.check(client_key(request, "location-search"))
    bias = validate_lat_lng(lat, lng) if lat is not None and lng is not None else service_area.center
    results = mappls_service.search_places(q, bias=bias)
    if not results and not is_indian_pincode(q):
        results = mappls_service.geocode(q)
    if resolve:
        results = [mappls_service.resolve_place(item) for item in results]
    return [_out(item) for item in results]


@router.get("/places/{mappls_pin}", response_model=LocationResultOut)
def place_details(
    mappls_pin: str,
    request: Request,
    _user: User = Depends(get_current_user),
):
    location_limiter.check(client_key(request, "location-place"))
    return _out(mappls_service.get_place_details(mappls_pin))


@router.post("/reverse-geocode", response_model=LocationResultOut)
def reverse_geocode(
    data: ReverseGeocodeIn,
    request: Request,
    _user: User = Depends(get_current_user),
):
    location_limiter.check(client_key(request, "location-reverse"))
    point = validate_lat_lng(data.latitude, data.longitude)
    return _out(mappls_service.reverse_geocode(point))


@router.post("/routes/preview", response_model=RoutePreviewOut)
def preview_route(
    data: RoutePreviewIn,
    request: Request,
    _user: User = Depends(get_current_user),
):
    location_limiter.check(client_key(request, "location-route"))
    origin = data.origin_mappls_pin or LatLng(data.origin.latitude, data.origin.longitude)
    destination = data.destination_mappls_pin or LatLng(data.destination.latitude, data.destination.longitude)
    waypoints = [LatLng(item.latitude, item.longitude) for item in data.waypoints]
    result = mappls_service.route(origin, destination, waypoints=waypoints, travel_mode=data.travel_mode)
    return RoutePreviewOut(
        provider=result.provider,
        distance_meters=result.distance_meters,
        duration_seconds=result.duration_seconds,
        geometry=[{"latitude": p.latitude, "longitude": p.longitude} for p in result.geometry],
        traffic_aware=result.traffic_aware,
        generated_at=result.generated_at,
    )


@router.get("/donations/{donation_id}/match-preview", response_model=list[MatchCandidateOut])
def match_preview(
    donation_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN)),
):
    donation = get_donation(db, donation_id)
    if donation is None:
        raise HTTPException(status_code=404, detail="Donation not found.")
    _ = user
    return [
        MatchCandidateOut(
            destination_id=str(item.destination.id),
            organization_id=str(item.organization.id),
            name=item.organization.name,
            verified=item.verified,
            intake_open=item.intake_open,
            category_compatible=item.category_compatible,
            within_service_area=item.within_service_area,
            road_distance_meters=item.road_distance_meters,
            estimated_duration_seconds=item.estimated_duration_seconds,
            geo_provider=item.geo_provider,
            reasons=item.reasons,
        )
        for item in evaluate_candidates(db, donation)
    ]
