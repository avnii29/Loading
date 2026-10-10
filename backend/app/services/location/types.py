from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.services.location.coords import LatLng


@dataclass(slots=True)
class LocationResult:
    provider: str
    formatted_address: str
    name: str | None = None
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


@dataclass(slots=True)
class RouteResult:
    provider: str
    distance_meters: float
    duration_seconds: float
    geometry: list[LatLng] = field(default_factory=list)
    traffic_aware: bool = False
    generated_at: datetime | None = None


@dataclass(slots=True)
class DistanceResult:
    origin: LatLng
    destination: LatLng
    distance_meters: float
    duration_seconds: float
    provider: str
