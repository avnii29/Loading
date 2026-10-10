from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.deps import get_current_user, require_roles
from app.models.donation import Donation
from app.models.enums import DonationCategory, DonationStatus, QualityResult, QualityStage, UserRole
from app.models.logistics import LogisticsAssignment
from app.models.organization import Destination, Organization
from app.models.user import User
from app.schemas.donation import (
    DonationCreateRequest,
    DonationOut,
    DonationCreatedOut,
    QualityCheckIn,
    AdminTransitionIn,
)
from app.services.donation import (
    add_photo,
    add_self_quality_check,
    cancel_donation,
    create_donation,
    get_donation,
    list_donations_for_user,
    rotate_verification_code,
    set_centre_preference,
    transition_status,
)
from app.services.serializers import serialize_donation
from app.services.storage import storage_provider

router = APIRouter(prefix="/api/donations", tags=["donations"])


def _assignment_for(db: Session, donation_id) -> LogisticsAssignment | None:
    return db.scalar(
        select(LogisticsAssignment)
        .options(selectinload(LogisticsAssignment.assignee))
        .where(LogisticsAssignment.donation_id == donation_id)
        .order_by(LogisticsAssignment.created_at.desc())
    )


def _ensure_visible(
    donation: Donation,
    user: User,
    assignment: LogisticsAssignment | None,
    db: Session,
) -> None:
    if user.role == UserRole.ADMIN:
        return
    if donation.donor_id == user.id:
        return
    if assignment and assignment.assignee_id == user.id:
        return
    if user.role == UserRole.ORGANIZATION and donation.destination_id:
        dest = db.get(Destination, donation.destination_id)
        org = db.scalar(select(Organization).where(Organization.user_id == user.id))
        if dest and org and dest.organization_id == org.id:
            return
    raise HTTPException(status_code=403, detail="You cannot view this donation.")


@router.post("", response_model=DonationCreatedOut, status_code=201)
def create(
    data: DonationCreateRequest,
    user: User = Depends(require_roles(UserRole.DONOR, UserRole.VOLUNTEER)),
    db: Session = Depends(get_db),
):
    from app.services.dispatch import enqueue_donation, issue_offers_for_donation

    donation, code = create_donation(db, user, data.model_dump())
    if code:
        # Fresh submit only — idempotent retries must not re-blast offers.
        db.refresh(donation, attribute_names=["quality_checks", "commercial_details"])
        enqueue_donation(db, donation)
        if donation.dispatch_status != "HELD":
            issue_offers_for_donation(db, donation)
    db.commit()
    donation = get_donation(db, donation.id) or donation
    loaded = get_donation(db, donation.id)
    # Only return verification code when freshly generated for this donor session.
    body = serialize_donation(loaded, verification_code=code or None, viewer_id=user.id)
    payload = body.model_dump()
    if not code:
        payload["verification_code"] = ""
    return DonationCreatedOut(**payload)


@router.get("", response_model=list[DonationOut])
def list_mine(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = list_donations_for_user(db, user)
    return [serialize_donation(row, viewer_id=user.id) for row in rows]


@router.get("/{donation_id}", response_model=DonationOut)
def detail(
    donation_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    donation = get_donation(db, donation_id)
    if donation is None:
        raise HTTPException(status_code=404, detail="Donation not found.")
    assignment = _assignment_for(db, donation.id)
    _ensure_visible(donation, user, assignment, db)
    show_code = donation.donor_id == user.id and donation.status in {
        DonationStatus.SUBMITTED,
        DonationStatus.ASSESSING,
        DonationStatus.MATCHING,
        DonationStatus.MATCHED,
        DonationStatus.ASSIGNED,
        DonationStatus.PICKUP_PENDING,
    }
    return serialize_donation(
        donation,
        verification_code=None if not show_code else None,
        assignment=assignment,
        viewer_id=user.id,
    )


class PreferenceIn(BaseModel):
    centre_id: UUID


@router.post("/{donation_id}/preference", response_model=DonationOut)
def prefer_centre(
    donation_id: UUID,
    data: PreferenceIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    donation = get_donation(db, donation_id)
    if donation is None:
        raise HTTPException(status_code=404, detail="Donation not found.")
    set_centre_preference(db, donation, user, data.centre_id)
    db.commit()
    return serialize_donation(get_donation(db, donation_id), viewer_id=user.id)


@router.post("/{donation_id}/cancel", response_model=DonationOut)
def cancel(
    donation_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    donation = get_donation(db, donation_id)
    if donation is None:
        raise HTTPException(status_code=404, detail="Donation not found.")
    cancel_donation(db, donation, user)
    db.commit()
    return serialize_donation(get_donation(db, donation_id), viewer_id=user.id)


@router.post("/{donation_id}/verification-code")
def refresh_code(
    donation_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    donation = get_donation(db, donation_id)
    if donation is None:
        raise HTTPException(status_code=404, detail="Donation not found.")
    code = rotate_verification_code(db, donation, user)
    db.commit()
    return {"verification_code": code, "reference_code": donation.reference_code}


@router.post("/{donation_id}/photos", response_model=DonationOut)
def upload_photo(
    donation_id: UUID,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    donation = get_donation(db, donation_id)
    if donation is None:
        raise HTTPException(status_code=404, detail="Donation not found.")
    if donation.donor_id != user.id and user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="You cannot add photos to this donation.")
    stored = storage_provider.save(file)
    add_photo(db, donation, stored)
    db.commit()
    return serialize_donation(get_donation(db, donation_id), viewer_id=user.id)


@router.post("/{donation_id}/quality-checks", response_model=DonationOut)
def quality(
    donation_id: UUID,
    data: QualityCheckIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    donation = get_donation(db, donation_id)
    if donation is None:
        raise HTTPException(status_code=404, detail="Donation not found.")

    stage = data.stage
    if stage is None:
        if donation.donor_id == user.id:
            stage = QualityStage.DONOR_SELF
        elif user.role == UserRole.ORGANIZATION:
            stage = QualityStage.INTAKE
        elif user.role in {UserRole.VOLUNTEER, UserRole.DRIVER}:
            stage = QualityStage.PICKUP
        else:
            stage = QualityStage.REVIEW

    assignment = _assignment_for(db, donation_id)
    if user.role == UserRole.ADMIN:
        pass
    elif stage == QualityStage.DONOR_SELF and donation.donor_id == user.id:
        pass
    elif stage == QualityStage.PICKUP and assignment and assignment.assignee_id == user.id:
        pass
    elif stage == QualityStage.INTAKE and user.role == UserRole.ORGANIZATION:
        _ensure_visible(donation, user, assignment, db)
    else:
        raise HTTPException(status_code=403, detail="You cannot record this check.")

    result = data.result
    if data.responses and donation.category == DonationCategory.FOOD:
        from app.services.food_safety import intake_food_result, pickup_food_result

        if stage == QualityStage.PICKUP:
            result = pickup_food_result(data.responses)
        elif stage == QualityStage.INTAKE:
            result = intake_food_result(data.responses)
    add_self_quality_check(
        db,
        donation,
        user,
        result,
        data.notes,
        responses=data.responses,
        checklist_version=data.checklist_version,
        stage=stage,
    )
    if stage == QualityStage.INTAKE and donation.category == DonationCategory.FOOD:
        if result == QualityResult.REJECTED:
            transition_status(db, donation, DonationStatus.REJECTED, user, data.notes or "Rejected at receipt")
        elif result == QualityResult.REQUIRES_REVIEW:
            transition_status(db, donation, DonationStatus.UNDER_REVIEW, user, data.notes or "Held at receipt")
    db.commit()
    return serialize_donation(get_donation(db, donation_id), viewer_id=user.id)


@router.post("/{donation_id}/transition", response_model=DonationOut)
def admin_transition(
    donation_id: UUID,
    data: AdminTransitionIn,
    user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    donation = get_donation(db, donation_id)
    if donation is None:
        raise HTTPException(status_code=404, detail="Donation not found.")
    try:
        target = DonationStatus(data.status)
    except ValueError:
        raise HTTPException(status_code=422, detail="Unknown donation status.")
    transition_status(db, donation, target, user, data.note)
    db.commit()
    return serialize_donation(get_donation(db, donation_id), viewer_id=user.id)
