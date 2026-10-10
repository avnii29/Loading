from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_roles
from app.models.enums import UserRole, VerificationStatus
from app.models.organization import DonationCentre, Organization
from app.models.user import User
from app.schemas.organization import DestinationRecommendation, OrganizationPublic, OrganizationUpdate, RecommendationList
from app.services.recommendations import recommend_centres
from app.services.location.coords import validate_lat_lng
from app.services.location.errors import LocationError
from app.services.serializers import haversine_km, serialize_org

router = APIRouter(prefix="/api/organizations", tags=["organizations"])

# When the caller sends a real position, do not return distant cities as "nearby".
DEFAULT_NEARBY_KM = 40.0


def nearby_only(items: list[OrganizationPublic], radius_km: float) -> list[OrganizationPublic]:
    """Keep organisations that have real coordinates inside the radius. No guessed pins."""
    kept = [
        item
        for item in items
        if item.latitude is not None
        and item.longitude is not None
        and item.distance_km is not None
        and item.distance_km <= radius_km
    ]
    kept.sort(key=lambda item: item.distance_km or 0)
    return kept


@router.get("", response_model=list[OrganizationPublic])
def list_verified(
    lat: float | None = None,
    lng: float | None = None,
    radius_km: float = Query(default=DEFAULT_NEARBY_KM, ge=1, le=150),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    rows = list(
        db.scalars(
            select(Organization).where(
                Organization.verification_status == VerificationStatus.VERIFIED,
                Organization.is_active.is_(True),
                Organization.is_demo.is_(False),
            )
        )
    )
    origin = None
    if lat is not None or lng is not None:
        if lat is None or lng is None:
            raise HTTPException(status_code=422, detail="Latitude and longitude must be sent together.")
        try:
            point = validate_lat_lng(lat, lng)
        except LocationError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
        origin = (point.latitude, point.longitude)
    items = [serialize_org(row, origin) for row in rows]
    centres = list(db.scalars(select(DonationCentre).where(DonationCentre.is_active.is_(True))))
    for centre in centres:
        distance = None
        if origin and centre.latitude is not None and centre.longitude is not None:
            distance = haversine_km(origin[0], origin[1], float(centre.latitude), float(centre.longitude))
        items.append(
            OrganizationPublic(
                id=str(centre.id),
                name=centre.name,
                description=centre.caveat or centre.provides,
                verification_status="DIRECTORY" if centre.listing == "published" else "UNCONFIRMED",
                intake_status="OPEN",
                address=centre.address,
                city=centre.city or centre.district,
                latitude=centre.latitude,
                longitude=centre.longitude,
                location_provider=centre.location_provider,
                accepted_categories=centre.accepted_categories,
                distance_km=distance,
                phone=centre.phone,
                source_note=centre.source_url,
                approximate=centre.approximate,
            )
        )
    if origin:
        return nearby_only(items, radius_km)
    return items


def _recommendation_payload(items, search: str) -> RecommendationList:
    return RecommendationList(
        search=search,
        distance_kind="straight_line",
        note=(
            "Distances are straight-line kilometres, not road distance or travel time. "
            "These facilities are research listings, not confirmed Anuvartan destinations."
        ),
        options=[
            DestinationRecommendation(
                id=str(item.centre.id),
                name=item.centre.name,
                facility_type=item.centre.facility_type,
                address=item.centre.address,
                locality=item.centre.district or item.centre.city,
                distance_km=item.distance_km,
                approximate=bool(item.centre.approximate),
                operational_status=item.centre.operational_status,
                category_hint=item.category_hint,
                caveat=item.centre.caveat,
            )
            for item in items
        ],
    )


@router.get("/recommendations", response_model=RecommendationList)
def recommendations(
    lat: float,
    lng: float,
    category: str | None = None,
    limit: int = Query(default=3, ge=1, le=10),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    try:
        point = validate_lat_lng(lat, lng)
    except LocationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    items, search = recommend_centres(
        db,
        latitude=point.latitude,
        longitude=point.longitude,
        category=category,
        limit=limit,
    )
    return _recommendation_payload(items, search)


@router.get("/me", response_model=OrganizationPublic)
def my_org(
    user: User = Depends(require_roles(UserRole.ORGANIZATION)),
    db: Session = Depends(get_db),
):
    org = db.scalar(select(Organization).where(Organization.user_id == user.id))
    if org is None:
        raise HTTPException(status_code=404, detail="Organisation profile not found.")
    return serialize_org(org)


@router.patch("/me", response_model=OrganizationPublic)
def update_mine(
    data: OrganizationUpdate,
    user: User = Depends(require_roles(UserRole.ORGANIZATION)),
    db: Session = Depends(get_db),
):
    org = db.scalar(select(Organization).where(Organization.user_id == user.id))
    if org is None:
        raise HTTPException(status_code=404, detail="Organisation profile not found.")
    updates = data.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(org, key, value)
    db.add(org)
    db.commit()
    db.refresh(org)
    return serialize_org(org)
