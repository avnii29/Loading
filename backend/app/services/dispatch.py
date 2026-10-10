"""Dispatch queue + time-limited volunteer offers with atomic acceptance."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.dispatch import DispatchQueueEntry, VolunteerOffer
from app.models.donation import Donation
from app.models.enums import (
    AssignmentStatus,
    DonationStatus,
    NotificationType,
    UserRole,
)
from app.models.logistics import LogisticsAssignment
from app.models.user import User
from app.services.audit import write_audit
from app.services.donation import transition_status
from app.services.notification import create_notification
from app.services.priority import score_donation
from app.services.schedule import scheduled_window_is_open

OFFER_TTL_SECONDS = int(os.getenv("OFFER_TTL_SECONDS", "10"))
MAX_SIMULTANEOUS_OFFERS = int(os.getenv("MAX_SIMULTANEOUS_OFFERS", "15"))


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _area_label(donation: Donation) -> str:
    if donation.pickup_pincode:
        return f"PIN {donation.pickup_pincode}"
    addr = donation.pickup_address or ""
    if len(addr) > 48:
        return addr[:45] + "…"
    return addr or "Pickup area confirmed"


def enqueue_donation(db: Session, donation: Donation) -> DispatchQueueEntry | None:
    result = score_donation(donation)
    donation.priority_score = result.score
    donation.priority_class = result.priority_class
    if not result.eligible:
        donation.dispatch_status = "HELD"
        entry = db.scalar(select(DispatchQueueEntry).where(DispatchQueueEntry.donation_id == donation.id))
        if entry is None:
            entry = DispatchQueueEntry(
                donation_id=donation.id,
                priority_score=result.score,
                priority_class=result.priority_class,
                status="HELD",
            )
        else:
            entry.status = "HELD"
            entry.priority_score = result.score
            entry.priority_class = result.priority_class
        db.add(entry)
        create_notification(
            db,
            user_id=donation.donor_id,
            ntype=NotificationType.SAFETY_HOLD,
            title="Donation held for review",
            body="Safety checks must pass before volunteers are offered this food.",
            entity_type="donation",
            entity_id=donation.id,
        )
        db.add(donation)
        return entry

    donation.dispatch_status = "QUEUED"
    entry = db.scalar(select(DispatchQueueEntry).where(DispatchQueueEntry.donation_id == donation.id))
    if entry is None:
        entry = DispatchQueueEntry(
            donation_id=donation.id,
            priority_score=result.score,
            priority_class=result.priority_class,
            status="ACTIVE",
        )
        db.add(entry)
    else:
        entry.priority_score = result.score
        entry.priority_class = result.priority_class
        entry.status = "ACTIVE"
        db.add(entry)
    db.add(donation)
    # Advance into matching once the donation is dispatch-eligible.
    if donation.status == DonationStatus.ASSESSING:
        transition_status(db, donation, DonationStatus.MATCHING, None, "Entered dispatch queue")
    return entry


def expire_stale_offers(db: Session) -> int:
    now = _now()
    rows = list(
        db.scalars(
            select(VolunteerOffer).where(
                VolunteerOffer.status == "PENDING",
                VolunteerOffer.expires_at <= now,
            )
        )
    )
    for offer in rows:
        offer.status = "EXPIRED"
        offer.responded_at = now
        db.add(offer)
        create_notification(
            db,
            user_id=offer.volunteer_id,
            ntype=NotificationType.OFFER_EXPIRED,
            title="Offer expired",
            body="A pickup offer timed out. It may still appear in your dashboard if unassigned.",
            entity_type="donation",
            entity_id=offer.donation_id,
        )
    if rows:
        db.flush()
    return len(rows)


def _eligible_volunteers(db: Session) -> list[User]:
    return list(
        db.scalars(
            select(User)
            .where(
                User.is_active.is_(True),
                User.role.in_([UserRole.VOLUNTEER, UserRole.DRIVER]),
            )
            .order_by(User.created_at.desc())
        )
    )


def can_offer_donation(donation: Donation, now: datetime | None = None) -> bool:
    """Eligible for a volunteer offer, and not yet assigned.

    Submitted or held donations stay hidden. Completed, cancelled, and rejected
    donations stay hidden. Non-food items need an open scheduled window.
    """
    now = now or _now()
    if donation.status not in {DonationStatus.MATCHING, DonationStatus.MATCHED}:
        return False
    if (donation.dispatch_status or "") == "HELD":
        return False
    if not score_donation(donation, now=now).eligible:
        return False
    return scheduled_window_is_open(donation, now)


def issue_offers_for_donation(db: Session, donation: Donation) -> list[VolunteerOffer]:
    expire_stale_offers(db)
    if not can_offer_donation(donation):
        return []
    if donation.status in {DonationStatus.CANCELLED, DonationStatus.COMPLETED, DonationStatus.ASSIGNED}:
        return []
    active = db.scalar(
        select(LogisticsAssignment).where(
            LogisticsAssignment.donation_id == donation.id,
            LogisticsAssignment.status.in_([AssignmentStatus.ACCEPTED, AssignmentStatus.EN_ROUTE]),
        )
    )
    if active:
        return []

    existing_pending = list(
        db.scalars(
            select(VolunteerOffer).where(
                VolunteerOffer.donation_id == donation.id,
                VolunteerOffer.status == "PENDING",
                VolunteerOffer.expires_at > _now(),
            )
        )
    )
    if len(existing_pending) >= MAX_SIMULTANEOUS_OFFERS:
        return existing_pending

    already = {o.volunteer_id for o in existing_pending}
    already.add(donation.donor_id)
    already |= {
        o.volunteer_id
        for o in db.scalars(
            select(VolunteerOffer).where(
                VolunteerOffer.donation_id == donation.id,
                VolunteerOffer.status.in_(["ACCEPTED", "DECLINED"]),
            )
        )
    }

    volunteers = [v for v in _eligible_volunteers(db) if v.id not in already][: MAX_SIMULTANEOUS_OFFERS - len(existing_pending)]
    created: list[VolunteerOffer] = []
    expires = _now() + timedelta(seconds=OFFER_TTL_SECONDS)
    summary = f"{donation.category.value} · {donation.quantity} {donation.unit}"
    for volunteer in volunteers:
        offer = VolunteerOffer(
            donation_id=donation.id,
            volunteer_id=volunteer.id,
            status="PENDING",
            priority_class=donation.priority_class,
            summary=summary,
            area_label=_area_label(donation),
            expires_at=expires,
        )
        db.add(offer)
        db.flush()
        create_notification(
            db,
            user_id=volunteer.id,
            ntype=NotificationType.VOLUNTEER_OFFER,
            title="New pickup offer",
            body=f"{summary} near {offer.area_label}. Respond within {OFFER_TTL_SECONDS}s.",
            entity_type="volunteer_offer",
            entity_id=offer.id,
        )
        created.append(offer)

    if not created and not existing_pending and donation.category.value == "FOOD":
        # Escalate unfilled food — notify admins
        admins = list(db.scalars(select(User).where(User.role == UserRole.ADMIN, User.is_active.is_(True))))
        for admin in admins[:5]:
            create_notification(
                db,
                user_id=admin.id,
                ntype=NotificationType.DISPATCH_ESCALATION,
                title="Unfilled food dispatch",
                body=f"No eligible volunteer for {donation.reference_code}.",
                entity_type="donation",
                entity_id=donation.id,
            )
    return created


def _active_assignment(db: Session, donation_id: uuid.UUID) -> LogisticsAssignment | None:
    return db.scalar(
        select(LogisticsAssignment).where(
            LogisticsAssignment.donation_id == donation_id,
            LogisticsAssignment.status.in_([AssignmentStatus.ACCEPTED, AssignmentStatus.EN_ROUTE]),
        )
    )


def retire_self_offers(db: Session, volunteer: User) -> None:
    """A volunteer must not be offered a donation they submitted."""
    now = _now()
    rows = list(
        db.scalars(
            select(VolunteerOffer)
            .join(Donation, Donation.id == VolunteerOffer.donation_id)
            .where(
                VolunteerOffer.volunteer_id == volunteer.id,
                VolunteerOffer.status == "PENDING",
                Donation.donor_id == volunteer.id,
            )
        )
    )
    for offer in rows:
        offer.status = "EXPIRED"
        offer.responded_at = now
        db.add(offer)
    if rows:
        db.flush()


def refresh_offers_for_volunteer(db: Session, volunteer: User) -> list[VolunteerOffer]:
    """Issue a real timed offer for each eligible unassigned donation this volunteer can still take.

    Offers created at submit expire quickly. Opening the volunteer dashboard asks the
    server for a fresh window instead of leaving the donation invisible.
    """
    expire_stale_offers(db)
    retire_self_offers(db, volunteer)
    now = _now()
    donations = list(
        db.scalars(
            select(Donation)
            .options(
                selectinload(Donation.quality_checks),
                selectinload(Donation.commercial_details),
            )
            .where(
                Donation.status.in_([DonationStatus.MATCHING, DonationStatus.MATCHED]),
                or_(Donation.dispatch_status.is_(None), Donation.dispatch_status != "HELD"),
            )
        )
    )
    created: list[VolunteerOffer] = []
    expires = now + timedelta(seconds=OFFER_TTL_SECONDS)
    for donation in donations:
        if donation.donor_id == volunteer.id:
            continue
        if not can_offer_donation(donation, now):
            continue
        if _active_assignment(db, donation.id):
            continue
        blocking = db.scalar(
            select(VolunteerOffer.id).where(
                VolunteerOffer.donation_id == donation.id,
                VolunteerOffer.volunteer_id == volunteer.id,
                or_(
                    VolunteerOffer.status.in_(["ACCEPTED", "DECLINED"]),
                    and_(VolunteerOffer.status == "PENDING", VolunteerOffer.expires_at > now),
                ),
            )
        )
        if blocking is not None:
            continue
        summary = f"{donation.category.value} · {donation.quantity} {donation.unit}"
        offer = VolunteerOffer(
            donation_id=donation.id,
            volunteer_id=volunteer.id,
            status="PENDING",
            priority_class=donation.priority_class,
            summary=summary,
            area_label=_area_label(donation),
            expires_at=expires,
        )
        db.add(offer)
        created.append(offer)
    if created:
        db.flush()
    return created


def list_offers_for_volunteer(db: Session, volunteer: User) -> list[VolunteerOffer]:
    refresh_offers_for_volunteer(db, volunteer)
    return list(
        db.scalars(
            select(VolunteerOffer)
            .options(
                selectinload(VolunteerOffer.donation).selectinload(Donation.commercial_details),
                selectinload(VolunteerOffer.donation).selectinload(Donation.quality_checks),
            )
            .where(VolunteerOffer.volunteer_id == volunteer.id)
            .order_by(VolunteerOffer.created_at.desc())
            .limit(50)
        )
    )


def accept_offer(db: Session, offer_id: uuid.UUID, volunteer: User) -> LogisticsAssignment:
    expire_stale_offers(db)
    offer = db.scalar(
        select(VolunteerOffer)
        .where(VolunteerOffer.id == offer_id)
        .with_for_update()
    )
    if offer is None or offer.volunteer_id != volunteer.id:
        raise HTTPException(status_code=404, detail="Offer not found.")
    now = _now()
    if offer.status != "PENDING" or offer.expires_at <= now:
        raise HTTPException(status_code=409, detail="This offer is no longer available.")

    claimed = db.scalar(
        select(LogisticsAssignment)
        .where(
            LogisticsAssignment.donation_id == offer.donation_id,
            LogisticsAssignment.status.in_([AssignmentStatus.ACCEPTED, AssignmentStatus.EN_ROUTE]),
        )
        .with_for_update()
    )
    if claimed is not None:
        offer.status = "EXPIRED"
        offer.responded_at = now
        db.add(offer)
        raise HTTPException(status_code=409, detail="Another volunteer already claimed this task.")

    donation = db.scalar(
        select(Donation)
        .options(
            selectinload(Donation.quality_checks),
            selectinload(Donation.commercial_details),
        )
        .where(Donation.id == offer.donation_id)
    )
    if donation is None or not can_offer_donation(donation, now):
        raise HTTPException(status_code=409, detail="Donation is no longer eligible.")
    if donation.donor_id == volunteer.id:
        raise HTTPException(
            status_code=409,
            detail="You cannot collect a donation you submitted. Another volunteer must pick it up.",
        )
    own = db.scalar(
        select(LogisticsAssignment)
        .where(
            LogisticsAssignment.assignee_id == volunteer.id,
            LogisticsAssignment.status.in_([AssignmentStatus.ACCEPTED, AssignmentStatus.EN_ROUTE]),
        )
        .with_for_update()
    )
    if own is not None:
        raise HTTPException(status_code=409, detail="You already have an active assignment.")

    assignment = LogisticsAssignment(
        donation_id=donation.id,
        assignee_id=volunteer.id,
        status=AssignmentStatus.ACCEPTED,
        accepted_at=now,
    )
    db.add(assignment)
    db.flush()

    offer.status = "ACCEPTED"
    offer.responded_at = now
    offer.assignment_id = assignment.id
    db.add(offer)

    # Invalidate competing offers
    rivals = list(
        db.scalars(
            select(VolunteerOffer).where(
                VolunteerOffer.donation_id == donation.id,
                VolunteerOffer.status == "PENDING",
                VolunteerOffer.id != offer.id,
            )
        )
    )
    for rival in rivals:
        rival.status = "EXPIRED"
        rival.responded_at = now
        db.add(rival)

    entry = db.scalar(select(DispatchQueueEntry).where(DispatchQueueEntry.donation_id == donation.id))
    if entry:
        entry.status = "ASSIGNED"
        db.add(entry)
    donation.dispatch_status = "ASSIGNED"
    transition_status(db, donation, DonationStatus.ASSIGNED, volunteer, "Volunteer accepted offer")

    from app.services.handoff import PICKUP_ACCEPT_TTL_SECONDS, generate_handoff_otp

    pickup_code = generate_handoff_otp(
        db,
        donation,
        stage="PICKUP",
        actor=volunteer,
        ttl_seconds=PICKUP_ACCEPT_TTL_SECONDS,
        reason="volunteer_accepted",
    )
    create_notification(
        db,
        user_id=donation.donor_id,
        ntype=NotificationType.ASSIGNMENT_ACCEPTED,
        title="Volunteer accepted — pickup code",
        body=(
            f"Pickup code: {pickup_code}. A volunteer accepted {donation.reference_code}. "
            "Share this code at the door. It is not created when they arrive. SMS was not sent."
        ),
        entity_type="donation",
        entity_id=donation.id,
    )

    # Notify organisation if destination known
    if donation.destination_id:
        from app.models.organization import Destination, Organization

        dest = db.get(Destination, donation.destination_id)
        if dest:
            org = db.get(Organization, dest.organization_id)
            if org and org.user_id:
                create_notification(
                    db,
                    user_id=org.user_id,
                    ntype=NotificationType.ASSIGNMENT_ACCEPTED,
                    title="Incoming delivery assigned",
                    body=f"{donation.quantity} {donation.unit} of {donation.category.value} is assigned for pickup.",
                    entity_type="donation",
                    entity_id=donation.id,
                )

    write_audit(
        db,
        action="offer.accept",
        entity_type="volunteer_offer",
        entity_id=offer.id,
        actor_id=volunteer.id,
        extra={"donation_id": str(donation.id)},
    )
    return assignment


def decline_offer(db: Session, offer_id: uuid.UUID, volunteer: User) -> VolunteerOffer:
    expire_stale_offers(db)
    offer = db.scalar(select(VolunteerOffer).where(VolunteerOffer.id == offer_id).with_for_update())
    if offer is None or offer.volunteer_id != volunteer.id:
        raise HTTPException(status_code=404, detail="Offer not found.")
    if offer.status != "PENDING":
        raise HTTPException(status_code=409, detail="Offer is no longer pending.")
    offer.status = "DECLINED"
    offer.responded_at = _now()
    db.add(offer)
    return offer
