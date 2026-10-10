from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.deps import get_current_user, require_roles
from app.models.donation import Donation
from app.models.enums import AssignmentStatus, UserRole
from app.models.logistics import LogisticsAssignment
from app.models.user import User
from app.services.dispatch import (
    OFFER_TTL_SECONDS,
    accept_offer,
    can_offer_donation,
    decline_offer,
    expire_stale_offers,
    list_offers_for_volunteer,
)
from app.services.schedule import schedule_label
from app.services.donation import get_donation, set_centre_proposal
from app.services.recommendations import recommend_centres
from app.models.organization import DonationCentre
from app.services.handoff import generate_handoff_otp, issue_receipt_on_arrival, verify_handoff_otp
from app.services.live_location import freshness, latest_for_donation, publish_fix

router = APIRouter(prefix="/api/logistics", tags=["logistics"])


class OfferOut(BaseModel):
    id: str
    donation_id: str
    status: str
    priority_class: str | None
    summary: str | None
    area_label: str | None
    created_at: str
    expires_at: str
    seconds_remaining: int
    category: str | None = None
    quantity: str | None = None
    unit: str | None = None
    description: str | None = None
    pickup_schedule: str | None = None
    pickup_latitude: float | None = None
    pickup_longitude: float | None = None
    reference_code: str | None = None


class HandoffIssueIn(BaseModel):
    stage: str = Field(pattern=r"^(PICKUP|DELIVERY)$")


class HandoffVerifyIn(BaseModel):
    stage: str = Field(pattern=r"^(PICKUP|DELIVERY)$")
    code: str = Field(min_length=4, max_length=12)


class LocationFixIn(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy_m: int | None = Field(default=None, ge=0, le=50000)
    heading_deg: float | None = Field(default=None, ge=0, lt=360)
    speed_mps: float | None = Field(default=None, ge=0, le=80)


@router.get("/offers", response_model=list[OfferOut])
def my_offers(
    user: User = Depends(require_roles(UserRole.VOLUNTEER, UserRole.DRIVER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    rows = list_offers_for_volunteer(db, user)
    db.commit()
    out: list[OfferOut] = []
    for row in rows:
        donation = row.donation
        if donation is not None and donation.donor_id == user.id:
            continue
        if row.status == "PENDING" and (donation is None or not can_offer_donation(donation, now)):
            continue
        remaining = int(max(0, (row.expires_at - now).total_seconds())) if row.status == "PENDING" else 0
        description = (donation.description or "").strip() if donation else ""
        if len(description) > 180:
            description = description[:177] + "…"
        lat = float(donation.pickup_latitude) if donation and donation.pickup_latitude is not None else None
        lng = float(donation.pickup_longitude) if donation and donation.pickup_longitude is not None else None
        out.append(
            OfferOut(
                id=str(row.id),
                donation_id=str(row.donation_id),
                status=row.status,
                priority_class=row.priority_class,
                summary=row.summary,
                area_label=row.area_label,
                created_at=row.created_at.isoformat(),
                expires_at=row.expires_at.isoformat(),
                seconds_remaining=remaining,
                category=donation.category.value if donation else None,
                quantity=str(donation.quantity) if donation else None,
                unit=donation.unit if donation else None,
                description=description or None,
                pickup_schedule=schedule_label(donation) if donation else None,
                pickup_latitude=lat,
                pickup_longitude=lng,
                reference_code=donation.reference_code if donation else None,
            )
        )
    return out


@router.get("/offer-config")
def offer_config(user: User = Depends(get_current_user)):
    return {"ttl_seconds": OFFER_TTL_SECONDS}


@router.get("/assignments")
def my_assignments(
    user: User = Depends(require_roles(UserRole.VOLUNTEER, UserRole.DRIVER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    expire_stale_offers(db)
    db.commit()
    stmt = (
        select(LogisticsAssignment)
        .options(selectinload(LogisticsAssignment.donation).selectinload(Donation.commercial_details))
        .where(
            LogisticsAssignment.assignee_id == user.id,
            LogisticsAssignment.status.in_(
                [AssignmentStatus.ACCEPTED, AssignmentStatus.EN_ROUTE, AssignmentStatus.COMPLETED]
            ),
        )
        .order_by(LogisticsAssignment.created_at.desc())
        .limit(40)
    )
    if user.role == UserRole.ADMIN:
        stmt = (
            select(LogisticsAssignment)
            .options(selectinload(LogisticsAssignment.donation).selectinload(Donation.commercial_details))
            .order_by(LogisticsAssignment.created_at.desc())
            .limit(40)
        )
    rows = list(db.scalars(stmt))
    out = []
    for row in rows:
        donation = row.donation
        if user.role != UserRole.ADMIN and donation is not None and donation.donor_id == user.id:
            continue
        out.append(
            {
                "id": str(row.id),
                "donation_id": str(row.donation_id),
                "status": row.status.value,
                "reference_code": donation.reference_code if donation else None,
                "category": donation.category.value if donation else None,
                "quantity": str(donation.quantity) if donation else None,
                "unit": donation.unit if donation else None,
                "pickup_address": donation.pickup_address if donation else None,
                "pickup_latitude": float(donation.pickup_latitude)
                if donation and donation.pickup_latitude is not None
                else None,
                "pickup_longitude": float(donation.pickup_longitude)
                if donation and donation.pickup_longitude is not None
                else None,
                "priority_class": donation.priority_class if donation else None,
                "donation_status": donation.status.value if donation else None,
                "pickup_schedule": schedule_label(donation) if donation else None,
            }
        )
    return out


@router.post("/offers/{offer_id}/accept")
def offer_accept(
    offer_id: UUID,
    user: User = Depends(require_roles(UserRole.VOLUNTEER, UserRole.DRIVER)),
    db: Session = Depends(get_db),
):
    assignment = accept_offer(db, offer_id, user)
    db.commit()
    return {
        "assignment_id": str(assignment.id),
        "donation_id": str(assignment.donation_id),
        "status": assignment.status.value,
    }


@router.post("/offers/{offer_id}/decline")
def offer_decline(
    offer_id: UUID,
    user: User = Depends(require_roles(UserRole.VOLUNTEER, UserRole.DRIVER)),
    db: Session = Depends(get_db),
):
    offer = decline_offer(db, offer_id, user)
    db.commit()
    return {"id": str(offer.id), "status": offer.status}


@router.post("/assignments/{assignment_id}/location")
def post_location(
    assignment_id: UUID,
    data: LocationFixIn,
    user: User = Depends(require_roles(UserRole.VOLUNTEER, UserRole.DRIVER)),
    db: Session = Depends(get_db),
):
    row, stored = publish_fix(
        db,
        assignment_id,
        user,
        latitude=data.latitude,
        longitude=data.longitude,
        accuracy_m=data.accuracy_m,
        heading_deg=data.heading_deg,
        speed_mps=data.speed_mps,
    )
    db.commit()
    return {
        "id": str(row.id),
        "stored": stored,
        "recorded_at": row.recorded_at.isoformat(),
        "freshness": freshness(row.recorded_at),
    }


@router.get("/donations/{donation_id}/collector-location")
def collector_location(
    donation_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    found = latest_for_donation(db, donation_id, user)
    if found is None:
        return {"available": False, "freshness": "unavailable"}
    row, assignment = found
    assignee_name = None
    if assignment.assignee and getattr(assignment.assignee, "profile", None):
        assignee_name = assignment.assignee.profile.full_name
    return {
        "available": True,
        "freshness": freshness(row.recorded_at),
        "latitude": float(row.latitude),
        "longitude": float(row.longitude),
        "accuracy_m": row.accuracy_m,
        "heading_deg": float(row.heading_deg) if row.heading_deg is not None else None,
        "speed_mps": float(row.speed_mps) if row.speed_mps is not None else None,
        "recorded_at": row.recorded_at.isoformat(),
        "assignment_status": assignment.status.value,
        "assignee_name": assignee_name,
    }


class ProposalIn(BaseModel):
    centre_id: UUID
    reason: str = Field(default="closer_eligible", max_length=80)


@router.get("/donations/{donation_id}/destination-options")
def destination_options(
    donation_id: UUID,
    user: User = Depends(require_roles(UserRole.VOLUNTEER, UserRole.DRIVER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    donation = get_donation(db, donation_id)
    if donation is None:
        raise HTTPException(status_code=404, detail="Donation not found.")
    if donation.pickup_latitude is None or donation.pickup_longitude is None:
        return {"search": "no_pickup", "options": [], "preferred_centre_id": None, "note": "This donation has no pickup coordinates."}
    items, search = recommend_centres(
        db,
        latitude=float(donation.pickup_latitude),
        longitude=float(donation.pickup_longitude),
        category=donation.category.value,
        limit=2,
    )
    preferred = str(donation.preferred_centre_id) if donation.preferred_centre_id else None
    options = []
    for item in items:
        options.append(
            {
                "id": str(item.centre.id),
                "name": item.centre.name,
                "locality": item.centre.district or item.centre.address,
                "distance_km": item.distance_km,
                "distance_kind": "straight_line",
                "approximate": bool(item.centre.approximate),
                "operational_status": item.centre.operational_status,
                "donor_preferred": preferred == str(item.centre.id),
                "latitude": float(item.centre.latitude) if item.centre.latitude is not None else None,
                "longitude": float(item.centre.longitude) if item.centre.longitude is not None else None,
                "eligible_as_final_destination": False,
            }
        )
    preferred_centre = db.get(DonationCentre, donation.preferred_centre_id) if donation.preferred_centre_id else None
    return {
        "search": search,
        "distance_kind": "straight_line",
        "preferred_centre_id": preferred,
        "preferred_name": preferred_centre.name if preferred_centre else None,
        "preferred_in_shortlist": any(row["donor_preferred"] for row in options),
        "note": "Two nearest research listings by straight-line distance from the pickup. Not a confirmed destination.",
        "options": options,
    }


@router.post("/donations/{donation_id}/destination-proposal")
def propose_destination(
    donation_id: UUID,
    data: ProposalIn,
    user: User = Depends(require_roles(UserRole.VOLUNTEER, UserRole.DRIVER)),
    db: Session = Depends(get_db),
):
    donation = get_donation(db, donation_id)
    if donation is None:
        raise HTTPException(status_code=404, detail="Donation not found.")
    set_centre_proposal(db, donation, user, data.centre_id, data.reason)
    db.commit()
    return {"ok": True, "proposed_centre_id": str(donation.proposed_centre_id), "confirmed": False}


@router.post("/donations/{donation_id}/handoff/arrived")
def mark_arrived(
    donation_id: UUID,
    user: User = Depends(require_roles(UserRole.VOLUNTEER, UserRole.DRIVER)),
    db: Session = Depends(get_db),
):
    donation = get_donation(db, donation_id)
    if donation is None:
        raise HTTPException(status_code=404, detail="Donation not found.")
    shown = issue_receipt_on_arrival(db, donation, user)
    db.commit()
    return {
        "ok": True,
        "shown_to": "organisation" if shown else "none",
        "message": (
            "The organisation has the receipt code."
            if shown
            else "Pickup is verified, but this destination has no organisation login, so the receipt code could not be delivered."
        ),
    }


@router.post("/donations/{donation_id}/handoff/issue")
def issue_handoff(
    donation_id: UUID,
    data: HandoffIssueIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    donation = get_donation(db, donation_id)
    if donation is None:
        raise HTTPException(status_code=404, detail="Donation not found.")
    code = generate_handoff_otp(db, donation, stage=data.stage, actor=user)
    db.commit()
    return {
        "stage": data.stage,
        "delivery": "in_app",
        "message": "Code issued in-app only. SMS was not sent.",
        "code": code,
        "ttl_seconds": int(__import__("os").getenv("HANDOFF_OTP_TTL_SECONDS", "600")),
    }


@router.post("/donations/{donation_id}/handoff/verify")
def verify_handoff(
    donation_id: UUID,
    data: HandoffVerifyIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    donation = get_donation(db, donation_id)
    if donation is None:
        raise HTTPException(status_code=404, detail="Donation not found.")
    verify_handoff_otp(db, donation, stage=data.stage, code=data.code, actor=user)
    db.commit()
    return {"ok": True, "stage": data.stage, "donation_status": donation.status.value}
