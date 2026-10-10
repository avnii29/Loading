from datetime import datetime

from pydantic import BaseModel, Field


class CoordinateIn(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class LocationResultOut(BaseModel):
    provider: str
    name: str | None = None
    formatted_address: str
    locality: str | None = None
    city: str | None = None
    state: str | None = None
    pincode: str | None = None
    landmark: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    mappls_pin: str | None = None
    provider_place_id: str | None = None
    confidence: float | None = None
    precision: str | None = None
    kind: str | None = None
    approximate: bool = False


class ReverseGeocodeIn(CoordinateIn):
    pass


class RoutePreviewIn(BaseModel):
    origin: CoordinateIn
    destination: CoordinateIn
    waypoints: list[CoordinateIn] = []
    origin_mappls_pin: str | None = None
    destination_mappls_pin: str | None = None
    travel_mode: str = "DRIVING"


class RoutePreviewOut(BaseModel):
    provider: str
    distance_meters: float
    duration_seconds: float
    geometry: list[CoordinateIn]
    traffic_aware: bool
    generated_at: datetime | None = None


class MatchCandidateOut(BaseModel):
    destination_id: str
    organization_id: str
    name: str
    verified: bool
    intake_open: bool
    category_compatible: bool
    within_service_area: bool | None
    road_distance_meters: float | None = None
    estimated_duration_seconds: float | None = None
    geo_provider: str | None = None
    reasons: list[str]


class LocationConfigOut(BaseModel):
    provider: str
    configured: bool
    search: bool
    geocoding: bool
    reverse_geocoding: bool
    routing: bool
    distance_matrix: bool
    route_optimisation: str
    service_area_name: str | None
    service_area_center: CoordinateIn | None
    service_area_radius_km: float | None
