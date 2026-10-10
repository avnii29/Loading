from __future__ import annotations

from dataclasses import dataclass

from app.config import Settings
from app.services.location.coords import LatLng


@dataclass(frozen=True, slots=True)
class ServiceArea:
    name: str | None
    center: LatLng | None
    radius_km: float | None

    def contains(self, point: LatLng) -> bool | None:
        if self.center is None or self.radius_km is None:
            return None
        from math import atan2, cos, radians, sin, sqrt

        earth = 6371.0
        dlat = radians(point.latitude - self.center.latitude)
        dlng = radians(point.longitude - self.center.longitude)
        a = (
            sin(dlat / 2) ** 2
            + cos(radians(self.center.latitude)) * cos(radians(point.latitude)) * sin(dlng / 2) ** 2
        )
        distance = 2 * earth * atan2(sqrt(a), sqrt(1 - a))
        return distance <= self.radius_km


def service_area_from_settings(settings: Settings) -> ServiceArea:
    center = None
    if settings.service_area_center_lat is not None and settings.service_area_center_lng is not None:
        center = LatLng(
            latitude=settings.service_area_center_lat,
            longitude=settings.service_area_center_lng,
        )
    return ServiceArea(
        name=settings.service_area_name or None,
        center=center,
        radius_km=settings.service_area_radius_km,
    )
