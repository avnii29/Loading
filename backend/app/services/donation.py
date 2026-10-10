import hashlib
import secrets
import string
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.donation import (
    Donation,
    DonationItem,
    DonationPhoto,
    DonationQualityCheck,
    DonationStatusHistory,
    CommercialDonationDetails,
)
from app.models.enums import (
    AssignmentStatus,
    DonationCategory,
    DonationStatus,
    DonationStream,
    NotificationType,
    QualityResult,
    QualityStage,
    UserRole,
)
from app.models.logistics import LogisticsAssignment
from app.models.user import User
from app.services.audit import write_audit
from app.services.notification import create_notification
from app.services.schedule import validate_scheduled_pickup
from app.services.status import DONOR_CANCELABLE, assert_transition


def _now() -> datetime:
    return datetime.now(timezone.utc)


def generate_reference_code() -> str:
    alphabet = string.ascii_uppercase + string.digits
    token = "".join(secrets.choice(alphabet) for _ in range(6))
    return f"DS-{token}"


def generate_verification_code() -> str:
    return "".join(secrets.choice(string.digits) for _ in range(6))


def hash_verification_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def stream_for_category(category: DonationCategory) -> DonationStream:
    if category == DonationCategory.ORGANIC_RECOVERY:
        return DonationStream.RECOVERY
    return DonationStream.HUMAN_CONSUMPTION


def transition_status(
    db: Session,
    donation: Donation,
    target: DonationStatus,
    actor: User | None,
    note: str | None = None,
) -> Donation:
    try:
        assert_transition(donation.status, target)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    history = DonationStatusHistory(
        donation_id=donation.id,
        from_status=donation.status,
        to_status=target,
        actor_id=actor.id if actor else None,
        note=note,
    )
    donation.status = target
    donation.updated_at = _now()
    db.add(donation)
    db.add(history)
    write_audit(
        db,
        action="donation.status_change",
        entity_type="donation",
        entity_id=donation.id,
        actor_id=actor.id if actor else None,
        extra={"from": history.from_status.value if history.from_status else None, "to": target.value},
    )
    return donation


ALLOWED_LOCATION_SOURCES = {
    "DEVICE_GEOLOCATION",
    "MAPPLS_SEARCH",
    "OSM_SEARCH",
    "MANUAL_PIN",
    "MANUAL_ADDRESS",
    "EXISTING_SAVED_LOCATION",
    # legacy clients
    "gps",
    "manual",
}


# Donor food declaration tiles (screenshot MCQ — Yes required on all four).
FOOD_CHECKLIST_REQUIRED = {
    "freshly_cooked",
    "still_warm",
    "stored_properly",
    "covered",
}


def _valid_preference(db: Session, centre_id):
    if not centre_id:
        return None
    from app.models.organization import DonationCentre

    centre = db.get(DonationCentre, centre_id)
    if centre is None or not centre.is_active or centre.listing != "published":
        raise HTTPException(status_code=422, detail="Choose an active facility from the recommendation list.")
    if centre.latitude is None or centre.longitude is None:
        raise HTTPException(status_code=422, detail="That facility does not have coordinates yet.")
    return centre.id


def set_centre_preference(db: Session, donation: Donation, actor: User, centre_id) -> Donation:
    if actor.role != UserRole.ADMIN and donation.donor_id != actor.id:
        raise HTTPException(status_code=403, detail="Only the donor can set a destination preference.")
    donation.preferred_centre_id = _valid_preference(db, centre_id)
    donation.preferred_at = _now()
    db.add(donation)
    write_audit(
        db,
        action="donation.preference",
        entity_type="donation",
        entity_id=donation.id,
        actor_id=actor.id,
        extra={"preferred_centre_id": str(donation.preferred_centre_id)},
    )
    return donation


def set_centre_proposal(db: Session, donation: Donation, actor: User, centre_id, reason: str) -> Donation:
    if actor.role not in {UserRole.VOLUNTEER, UserRole.DRIVER, UserRole.ADMIN}:
        raise HTTPException(status_code=403, detail="Only the assigned volunteer can propose a destination.")
    assignment = db.scalar(
        select(LogisticsAssignment).where(
            LogisticsAssignment.donation_id == donation.id,
            LogisticsAssignment.assignee_id == actor.id,
            LogisticsAssignment.status.in_([AssignmentStatus.ACCEPTED, AssignmentStatus.EN_ROUTE]),
        )
    )
    if assignment is None and actor.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only the assigned volunteer can propose a destination.")
    if donation.donor_id == actor.id:
        raise HTTPException(status_code=409, detail="You cannot choose the destination for a donation you submitted.")
    donation.proposed_centre_id = _valid_preference(db, centre_id)
    donation.proposal_reason = reason
    db.add(donation)
    write_audit(
        db,
        action="donation.destination_proposal",
        entity_type="donation",
        entity_id=donation.id,
        actor_id=actor.id,
        extra={"proposed_centre_id": str(donation.proposed_centre_id), "reason": reason, "preferred_centre_id": str(donation.preferred_centre_id) if donation.preferred_centre_id else None},
    )
    return donation


def create_donation(db: Session, donor: User, payload: dict) -> tuple[Donation, str]:
    if donor.role not in {UserRole.DONOR, UserRole.VOLUNTEER}:
        raise HTTPException(status_code=403, detail="Only donors and volunteers can create donations.")

    idem = payload.get("idempotency_key")
    if idem:
        existing = db.scalar(select(Donation).where(Donation.idempotency_key == idem, Donation.donor_id == donor.id))
        if existing:
            # Return existing commitment — do not create a duplicate.
            return existing, ""

    category = payload["category"]
    stream = payload.get("stream") or stream_for_category(category)

    if category == DonationCategory.FOOD:
        handling = str(payload.get("diet_type") or "").upper()
        if handling in {"", "COOKED_LEFTOVERS", "LEFTOVERS", "STANDARD"}:
            raise HTTPException(
                status_code=422,
                detail="Standard cooked leftovers cannot be accepted. Offer sealed dry rations or a private catered function for 25 or more people.",
            )
        if handling == "PRIVATE_FUNCTION":
            commercial = payload.get("commercial") or {}
            caterer = str(commercial.get("event_type") or "").strip()
            if len(caterer) < 2:
                raise HTTPException(
                    status_code=422,
                    detail="Enter the catering service or cloud kitchen name for a private function.",
                )
            required = FOOD_CHECKLIST_REQUIRED
        elif handling == "DRY_RATIONS":
            required = ("stored_safely", "covered")
        else:
            raise HTTPException(status_code=422, detail="Choose sealed dry rations or a private catered function.")
        checklist = payload.get("quality_checklist") or {}
        if handling == "PRIVATE_FUNCTION":
            required = ("freshly_prepared", "stored_safely", "covered", "time_since_cooking")
        missing = [key for key in required if checklist.get(key) in {None, ""}]
        if missing:
            raise HTTPException(
                status_code=422,
                detail="Complete the food checks before submitting. Not sure is allowed, but every question needs an answer.",
            )
        from app.services.food_safety import donor_food_result

        payload["_donor_quality_result"] = donor_food_result(checklist, handling)
        if payload["_donor_quality_result"] == QualityResult.REJECTED:
            raise HTTPException(
                status_code=422,
                detail="This food cannot be accepted from the answers given. Do not offer it for sharing.",
            )
        prepared = payload.get("prepared_at")
        if prepared and prepared > _now():
            raise HTTPException(status_code=422, detail="Preparation time cannot be in the future.")

    lat = payload.get("pickup_latitude")
    lng = payload.get("pickup_longitude")
    if lat is not None and lng is None:
        raise HTTPException(status_code=422, detail="Longitude is required when latitude is set.")
    if lng is not None and lat is None:
        raise HTTPException(status_code=422, detail="Latitude is required when longitude is set.")
    if lat is not None and lng is not None:
        try:
            flat, flng = float(lat), float(lng)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail="Coordinates must be numeric.") from exc
        if not (-90 <= flat <= 90 and -180 <= flng <= 180):
            raise HTTPException(status_code=422, detail="Coordinates are out of range.")
        if flat == 0.0 and flng == 0.0:
            raise HTTPException(status_code=422, detail="Null Island coordinates are not accepted.")

    source = payload.get("location_source")
    if source and source not in ALLOWED_LOCATION_SOURCES:
        raise HTTPException(status_code=422, detail="Unknown location_source.")

    accuracy = payload.get("location_accuracy_m")
    if accuracy is not None and source not in {None, "DEVICE_GEOLOCATION", "gps"}:
        # Manual / search pins must not carry fabricated GPS accuracy.
        payload["location_accuracy_m"] = None
        accuracy = None
    if accuracy is not None and (accuracy < 0 or accuracy > 50000):
        raise HTTPException(status_code=422, detail="location_accuracy_m is out of range.")

    if category == DonationCategory.ORGANIC_RECOVERY and stream != DonationStream.RECOVERY:
        raise HTTPException(
            status_code=422,
            detail="Organic recovery must stay on the recovery stream.",
        )
    if category != DonationCategory.ORGANIC_RECOVERY and stream == DonationStream.RECOVERY:
        raise HTTPException(
            status_code=422,
            detail="Household categories cannot be submitted on the recovery stream.",
        )

    if (
        category == DonationCategory.FOOD
        and not payload.get("prepared_at")
        and not payload.get("description")
        and not payload.get("food_source")
    ):
        raise HTTPException(
            status_code=422,
            detail="Choose where the food is from, or add when it was prepared.",
        )

    validate_scheduled_pickup(category, payload)

    reference = generate_reference_code()
    while db.scalar(select(Donation).where(Donation.reference_code == reference)):
        reference = generate_reference_code()

    code = generate_verification_code()
    donation = Donation(
        reference_code=reference,
        donor_id=donor.id,
        stream=stream,
        category=category,
        status=DonationStatus.SUBMITTED,
        title=payload.get("title"),
        description=payload.get("description"),
        quantity=payload["quantity"],
        unit=payload["unit"],
        notes=payload.get("notes"),
        pickup_address=payload.get("pickup_address"),
        pickup_latitude=payload.get("pickup_latitude"),
        pickup_longitude=payload.get("pickup_longitude"),
        location_accuracy_m=payload.get("location_accuracy_m"),
        location_source=payload.get("location_source"),
        location_provider=payload.get("location_provider"),
        mappls_pin=payload.get("mappls_pin"),
        provider_place_id=payload.get("provider_place_id"),
        geocode_precision=payload.get("geocode_precision"),
        location_captured_at=payload.get("location_captured_at"),
        location_confirmed_at=payload.get("location_confirmed_at"),
        pickup_landmark=payload.get("pickup_landmark"),
        pickup_pincode=payload.get("pickup_pincode"),
        food_source=payload.get("food_source"),
        packaging_state=payload.get("packaging_state"),
        diet_type=payload.get("diet_type"),
        urgency=payload.get("urgency"),
        idempotency_key=payload.get("idempotency_key"),
        prepared_at=payload.get("prepared_at"),
        pickup_deadline=payload.get("pickup_deadline"),
        distribution_deadline=payload.get("distribution_deadline"),
        cluster_window=payload.get("cluster_window"),
        cluster_sector=payload.get("cluster_sector"),
        preferred_centre_id=_valid_preference(db, payload.get("preferred_centre_id")),
        preferred_at=_now() if payload.get("preferred_centre_id") else None,
        verification_code_hash=hash_verification_code(code),
    )
    db.add(donation)
    db.flush()

    checklist = payload.get("quality_checklist")
    if checklist:
        failed = any(value is False for value in checklist.values())
        stored_result = payload.get("_donor_quality_result")
        if stored_result is None and category == DonationCategory.FOOD:
            from app.services.food_safety import donor_food_result

            stored_result = donor_food_result(checklist, str(payload.get("diet_type") or ""))
        if stored_result is None:
            stored_result = QualityResult.REJECTED if failed else QualityResult.ACCEPTABLE
        check = DonationQualityCheck(
            donation_id=donation.id,
            checked_by=donor.id,
            stage=QualityStage.DONOR_SELF,
            result=stored_result,
            checklist_version="donor-food-v1" if category == DonationCategory.FOOD else "donor-goods-v1",
            responses=checklist,
            notes=payload.get("quality_notes"),
        )
        db.add(check)
        db.flush()
        # Ensure later priority scoring sees this declaration in the same request.
        db.refresh(donation, attribute_names=["quality_checks"])

    item_label = payload.get("title") or category.value.title()
    db.add(
        DonationItem(
            donation_id=donation.id,
            label=item_label,
            quantity=payload["quantity"],
            unit=payload["unit"],
            condition=payload.get("condition"),
        )
    )

    commercial = payload.get("commercial")
    if commercial:
        db.add(
            CommercialDonationDetails(
                donation_id=donation.id,
                event_type=commercial.get("event_type"),
                estimated_servings=commercial.get("estimated_servings"),
                packaging_state=commercial.get("packaging_state"),
                pickup_window_start=commercial.get("pickup_window_start"),
                pickup_window_end=commercial.get("pickup_window_end"),
            )
        )

    db.add(
        DonationStatusHistory(
            donation_id=donation.id,
            from_status=None,
            to_status=DonationStatus.SUBMITTED,
            actor_id=donor.id,
            note="Donation submitted",
        )
    )
    transition_status(db, donation, DonationStatus.ASSESSING, donor, "System assessment started")

    create_notification(
        db,
        user_id=donor.id,
        ntype=NotificationType.DONATION_SUBMITTED,
        title="Donation submitted",
        body=f"Your donation {reference} is in. We're finding the right route.",
        entity_type="donation",
        entity_id=donation.id,
    )
    write_audit(
        db,
        action="donation.create",
        entity_type="donation",
        entity_id=donation.id,
        actor_id=donor.id,
        extra={"category": category.value, "stream": stream.value, "reference": reference},
    )
    return donation, code


def get_donation(db: Session, donation_id: uuid.UUID) -> Donation | None:
    return db.scalar(
        select(Donation)
        .options(
            selectinload(Donation.items),
            selectinload(Donation.photos),
            selectinload(Donation.status_history),
            selectinload(Donation.quality_checks),
            selectinload(Donation.commercial_details),
        )
        .where(Donation.id == donation_id)
    )


def list_donations_for_user(db: Session, user: User) -> list[Donation]:
    stmt = (
        select(Donation)
        .options(
            selectinload(Donation.items),
            selectinload(Donation.photos),
            selectinload(Donation.status_history),
            selectinload(Donation.quality_checks),
        )
        .order_by(Donation.created_at.desc())
    )
    if user.role == UserRole.DONOR:
        stmt = stmt.where(Donation.donor_id == user.id)
    elif user.role == UserRole.ADMIN:
        pass
    elif user.role == UserRole.VOLUNTEER:
        stmt = stmt.where(Donation.donor_id == user.id)
    elif user.role == UserRole.DRIVER:
        stmt = (
            stmt.join(LogisticsAssignment, LogisticsAssignment.donation_id == Donation.id)
            .where(LogisticsAssignment.assignee_id == user.id)
            .distinct()
        )
    elif user.role == UserRole.ORGANIZATION:
        from app.models.organization import Destination, Organization

        org = db.scalar(select(Organization).where(Organization.user_id == user.id))
        if org is None:
            return []
        dest_ids = list(db.scalars(select(Destination.id).where(Destination.organization_id == org.id)))
        if not dest_ids:
            return []
        stmt = stmt.where(Donation.destination_id.in_(dest_ids))
    else:
        return []
    return list(db.scalars(stmt))


def cancel_donation(db: Session, donation: Donation, actor: User) -> Donation:
    if actor.role != UserRole.ADMIN and donation.donor_id != actor.id:
        raise HTTPException(status_code=403, detail="You cannot cancel this donation.")
    if donation.status not in DONOR_CANCELABLE and actor.role != UserRole.ADMIN:
        raise HTTPException(status_code=409, detail="This donation can no longer be cancelled.")
    return transition_status(db, donation, DonationStatus.CANCELLED, actor, "Cancelled by user")


def add_photo(db: Session, donation: Donation, stored) -> DonationPhoto:
    photo = DonationPhoto(
        donation_id=donation.id,
        storage_key=stored.key,
        mime_type=stored.mime_type,
        byte_size=stored.byte_size,
    )
    db.add(photo)
    return photo


def add_self_quality_check(
    db: Session,
    donation: Donation,
    actor: User,
    result: QualityResult,
    notes: str | None,
    *,
    responses: dict | None = None,
    checklist_version: str | None = None,
    stage: QualityStage = QualityStage.DONOR_SELF,
):
    check = DonationQualityCheck(
        donation_id=donation.id,
        checked_by=actor.id,
        stage=stage,
        result=result,
        notes=notes,
        responses=responses,
        checklist_version=checklist_version,
    )
    db.add(check)
    return check


def rotate_verification_code(db: Session, donation: Donation, actor: User) -> str:
    if actor.role != UserRole.ADMIN and donation.donor_id != actor.id:
        raise HTTPException(status_code=403, detail="You cannot refresh this code.")
    if donation.status not in {
        DonationStatus.SUBMITTED,
        DonationStatus.ASSESSING,
        DonationStatus.MATCHING,
        DonationStatus.MATCHED,
        DonationStatus.ASSIGNED,
        DonationStatus.PICKUP_PENDING,
    }:
        raise HTTPException(status_code=409, detail="A new verification code cannot be issued at this stage.")
    code = generate_verification_code()
    donation.verification_code_hash = hash_verification_code(code)
    db.add(donation)
    write_audit(
        db,
        action="donation.verification_rotated",
        entity_type="donation",
        entity_id=donation.id,
        actor_id=actor.id,
    )
    return code
