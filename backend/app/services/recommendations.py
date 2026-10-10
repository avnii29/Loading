"""Straight-line destination recommendations from saved coordinates.

Directory facilities are research records. They can be a donor preference.
They are not a confirmed receiving organisation.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.organization import DonationCentre
from app.services.serializers import haversine_km

RADII_KM = (10.0, 25.0, 50.0)


@dataclass(frozen=True)
class Recommendation:
    centre: DonationCentre
    distance_km: float
    radius_km: float | None
    category_hint: bool


def recommend_centres(
    db: Session,
    *,
    latitude: float,
    longitude: float,
    category: str | None,
    limit: int,
) -> tuple[list[Recommendation], str]:
    rows = list(
        db.scalars(
            select(DonationCentre).where(
                DonationCentre.is_active.is_(True),
                DonationCentre.listing == "published",
                DonationCentre.latitude.is_not(None),
                DonationCentre.longitude.is_not(None),
            )
        )
    )
    scored: list[Recommendation] = []
    for centre in rows:
        suggested = centre.accepted_categories or []
        if category and suggested and category not in suggested:
            continue
        distance = haversine_km(latitude, longitude, float(centre.latitude), float(centre.longitude))
        scored.append(
            Recommendation(
                centre=centre,
                distance_km=distance,
                radius_km=None,
                category_hint=bool(suggested) and (category in suggested if category else True),
            )
        )
    scored.sort(key=lambda item: item.distance_km)
    if not scored:
        return [], "none"
    for radius in RADII_KM:
        within = [item for item in scored if item.distance_km <= radius]
        if len(within) >= min(limit, len(scored)):
            return within[:limit], f"within_{int(radius)}km"
    return scored[:limit], "all_remaining_eligible"
