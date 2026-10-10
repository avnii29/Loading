"""Stage-bound handoff OTP — hashed at rest, never logged in plaintext."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.dispatch import HandoffVerification
from app.models.donation import Donation
from app.models.enums import AssignmentStatus, DonationStatus, NotificationType, UserRole
from app.models.logistics import LogisticsAssignment
from app.models.user import User
from app.services.audit import write_audit
from app.services.donation import transition_status
from app.services.notification import create_notification

OTP_TTL_SECONDS = int(os.getenv("HANDOFF_OTP_TTL_SECONDS", "600"))
PICKUP_ACCEPT_TTL_SECONDS = int(os.getenv("PICKUP_OTP_TTL_SECONDS", str(24 * 60 * 60)))
OTP_PEPPER = os.getenv("JWT_SECRET", "dev-pepper")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hash(code: str) -> str:
    return hmac.new(OTP_PEPPER.encode(), code.encode(), hashlib.sha256).hexdigest()


def generate_handoff_otp(
    db: Session,
    donation: Donation,
    *,
    stage: str,
    actor: User,
    ttl_seconds: int | None = None,
    reason: str = "issued",
) -> str:
    stage = stage.upper()
    if stage not in {"PICKUP", "DELIVERY"}:
        raise HTTPException(status_code=422, detail="Unknown handoff stage.")

    assignment = db.scalar(
        select(LogisticsAssignment).where(
            LogisticsAssignment.donation_id == donation.id,
            LogisticsAssignment.status.in_([AssignmentStatus.ACCEPTED, AssignmentStatus.EN_ROUTE]),
        )
    )
    if stage == "PICKUP":
        if reason == "volunteer_accepted":
            if assignment is None:
                raise HTTPException(status_code=409, detail="A volunteer must accept before a pickup code exists.")
        elif actor.role != UserRole.ADMIN and donation.donor_id != actor.id:
            raise HTTPException(status_code=403, detail="Only the donor can see the pickup code.")
        elif assignment is None and actor.role != UserRole.ADMIN:
            raise HTTPException(status_code=409, detail="A pickup code is created when a volunteer accepts, not before.")
        elif donation.status == DonationStatus.IN_TRANSIT:
            raise HTTPException(status_code=409, detail="Pickup is already verified.")
    elif stage == "DELIVERY":
        if donation.status != DonationStatus.IN_TRANSIT and reason != "resend":
            raise HTTPException(
                status_code=409,
                detail="The receipt code is created when the volunteer reaches the organisation.",
            )
        if reason == "arrived":
            if assignment is None or (assignment.assignee_id != actor.id and actor.role != UserRole.ADMIN):
                raise HTTPException(status_code=403, detail="Only the assigned volunteer can mark arrival.")
        elif actor.role not in {UserRole.ADMIN, UserRole.ORGANIZATION}:
            raise HTTPException(status_code=403, detail="Only the receiving organisation can see the receipt code.")

    # Invalidate prior unused codes for this stage
    prior = list(
        db.scalars(
            select(HandoffVerification).where(
                HandoffVerification.donation_id == donation.id,
                HandoffVerification.stage == stage,
                HandoffVerification.consumed_at.is_(None),
            )
        )
    )
    for row in prior:
        row.consumed_at = _now()
        db.add(row)

    code = f"{secrets.randbelow(1_000_000):06d}"
    row = HandoffVerification(
        donation_id=donation.id,
        stage=stage,
        code_hash=_hash(code),
        expires_at=_now() + timedelta(seconds=ttl_seconds or OTP_TTL_SECONDS),
        created_by=actor.id,
    )
    db.add(row)
    write_audit(
        db,
        action="handoff.otp_issued",
        entity_type="donation",
        entity_id=donation.id,
        actor_id=actor.id,
        extra={"stage": stage},
    )
    return code


def verify_handoff_otp(
    db: Session,
    donation: Donation,
    *,
    stage: str,
    code: str,
    actor: User,
) -> HandoffVerification:
    stage = stage.upper()
    row = db.scalar(
        select(HandoffVerification)
        .where(
            HandoffVerification.donation_id == donation.id,
            HandoffVerification.stage == stage,
            HandoffVerification.consumed_at.is_(None),
        )
        .order_by(HandoffVerification.created_at.desc())
        .with_for_update()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="No active verification code.")

    now = _now()
    if row.expires_at <= now:
        raise HTTPException(status_code=409, detail="Verification code expired.")
    if row.attempts >= row.max_attempts:
        raise HTTPException(status_code=429, detail="Too many attempts. Request a new code.")

    row.attempts += 1
    db.add(row)
    if not hmac.compare_digest(row.code_hash, _hash(code.strip())):
        write_audit(
            db,
            action="handoff.otp_failed",
            entity_type="donation",
            entity_id=donation.id,
            actor_id=actor.id,
            extra={"stage": stage},
        )
        raise HTTPException(status_code=401, detail="Incorrect verification code.")

    row.consumed_at = now
    db.add(row)

    if stage == "PICKUP":
        # Volunteer verifies against donor-issued code
        assignment = db.scalar(
            select(LogisticsAssignment).where(
                LogisticsAssignment.donation_id == donation.id,
                LogisticsAssignment.assignee_id == actor.id,
                LogisticsAssignment.status.in_([AssignmentStatus.ACCEPTED, AssignmentStatus.EN_ROUTE]),
            )
        )
        if assignment is None and actor.role != UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="Only the assigned volunteer can verify pickup.")
        if donation.category.value == "FOOD":
            from app.models.enums import QualityResult, QualityStage

            pickup_checks = [c for c in (donation.quality_checks or []) if c.stage == QualityStage.PICKUP]
            if not pickup_checks or max(pickup_checks, key=lambda c: c.created_at).result != QualityResult.ACCEPTABLE:
                raise HTTPException(
                    status_code=409,
                    detail="Pickup is paused. Record food checks with no unresolved concerns before handover.",
                )
        if assignment:
            assignment.status = AssignmentStatus.EN_ROUTE
            db.add(assignment)
        transition_status(db, donation, DonationStatus.IN_TRANSIT, actor, "Pickup verified")
        create_notification(
            db,
            user_id=donation.donor_id,
            ntype=NotificationType.PICKED_UP,
            title="Donation collected",
            body=f"{donation.reference_code} is in transit.",
            entity_type="donation",
            entity_id=donation.id,
        )
        if donation.destination_id:
            from app.models.organization import Destination

            dest = db.get(Destination, donation.destination_id)
            org_user = getattr(getattr(dest, "organization", None), "user_id", None) if dest else None
            if org_user:
                create_notification(
                    db,
                    user_id=org_user,
                    ntype=NotificationType.RECEIVING_REQUIRED,
                    title="Donation in transit",
                    body=f"{donation.quantity} {donation.unit} collected and heading your way.",
                    entity_type="donation",
                    entity_id=donation.id,
                )
    elif stage == "DELIVERY":
        if actor.role not in {UserRole.ORGANIZATION, UserRole.ADMIN}:
            raise HTTPException(status_code=403, detail="Only the receiving organisation can verify delivery.")
        if donation.category.value == "FOOD":
            from app.models.enums import QualityResult, QualityStage

            intake_checks = [c for c in (donation.quality_checks or []) if c.stage == QualityStage.INTAKE]
            if not intake_checks or max(intake_checks, key=lambda c: c.created_at).result != QualityResult.ACCEPTABLE:
                raise HTTPException(
                    status_code=409,
                    detail="Delivery is not marked complete while receipt checks are missing, held, or rejected.",
                )
        transition_status(db, donation, DonationStatus.DELIVERED, actor, "Delivery verified")
        from app.services.points import award_for_delivery

        award_for_delivery(db, donation)
        create_notification(
            db,
            user_id=donation.donor_id,
            ntype=NotificationType.DELIVERED,
            title="Delivery verified",
            body=f"{donation.reference_code} was received. Final acceptance may still be pending.",
            entity_type="donation",
            entity_id=donation.id,
        )

    write_audit(
        db,
        action="handoff.otp_verified",
        entity_type="donation",
        entity_id=donation.id,
        actor_id=actor.id,
        extra={"stage": stage},
    )
    return row


def issue_receipt_on_arrival(db: Session, donation: Donation, actor: User) -> bool:
    """Create the organisation receipt code only once pickup is done and the volunteer has arrived."""
    code = generate_handoff_otp(db, donation, stage="DELIVERY", actor=actor, reason="arrived")
    org_user = None
    if donation.destination_id:
        from app.models.organization import Destination, Organization

        dest = db.get(Destination, donation.destination_id)
        if dest:
            org = db.get(Organization, dest.organization_id)
            org_user = org.user_id if org else None
    if org_user:
        create_notification(
            db,
            user_id=org_user,
            ntype=NotificationType.RECEIVING_REQUIRED,
            title="Receipt code",
            body=(
                f"Receipt code: {code}. The volunteer has reached you with {donation.reference_code}. "
                "Share this code so receipt can be verified. SMS was not sent."
            ),
            entity_type="donation",
            entity_id=donation.id,
        )
        return True
    return False
