"""Real collector GPS fixes. Coordinates come only from the client device; nothing is simulated."""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import AssignmentStatus, UserRole
from app.models.logistics import LocationUpdate, LogisticsAssignment
from app.models.organization import Destination, Organization
from app.models.user import User

LIVE_SECONDS = 45
RECENT_SECONDS = 180
MIN_MOVE_M = 12
MIN_INTERVAL = timedelta(seconds=8)
ACTIVE = {AssignmentStatus.ACCEPTED, AssignmentStatus.EN_ROUTE}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def freshness(recorded_at: datetime, now: datetime | None = None) -> str:
    now = now or _now()
    if recorded_at.tzinfo is None:
        recorded_at = recorded_at.replace(tzinfo=timezone.utc)
    age = (now - recorded_at).total_seconds()
    if age <= LIVE_SECONDS:
        return "live"
    if age <= RECENT_SECONDS:
        return "recent"
    return "stale"


def _meters(a_lat: float, a_lng: float, b_lat: float, b_lng: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    dlat = math.radians(b_lat - a_lat)
    dlng = math.radians(b_lng - a_lng)
    h = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlng / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(h)))


def _assignment(db: Session, assignment_id: uuid.UUID) -> LogisticsAssignment | None:
    return db.scalar(select(LogisticsAssignment).where(LogisticsAssignment.id == assignment_id))


def can_read_collector(db: Session, user: User, assignment: LogisticsAssignment, donation) -> bool:
    if user.role == UserRole.ADMIN:
        return True
    if assignment.assignee_id == user.id:
        return True
    if donation and donation.donor_id == user.id:
        return True
    if user.role == UserRole.ORGANIZATION and donation and donation.destination_id:
        dest = db.get(Destination, donation.destination_id)
        org = db.scalar(select(Organization).where(Organization.user_id == user.id))
        if dest and org and dest.organization_id == org.id:
            return True
    return False


def publish_fix(
    db: Session,
    assignment_id: uuid.UUID,
    actor: User,
    *,
    latitude: float,
    longitude: float,
    accuracy_m: int | None,
    heading_deg: float | None,
    speed_mps: float | None,
) -> tuple[LocationUpdate, bool]:
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise HTTPException(status_code=422, detail="Coordinates are out of range.")
    if latitude == 0 and longitude == 0:
        raise HTTPException(status_code=422, detail="Null Island coordinates are not accepted.")
    if accuracy_m is not None and (accuracy_m < 0 or accuracy_m > 50000):
        raise HTTPException(status_code=422, detail="accuracy_m is out of range.")
    if heading_deg is not None and not (0 <= heading_deg < 360):
        raise HTTPException(status_code=422, detail="heading_deg must be 0–359.")
    if speed_mps is not None and (speed_mps < 0 or speed_mps > 80):
        raise HTTPException(status_code=422, detail="speed_mps is out of range.")

    assignment = _assignment(db, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found.")
    if assignment.assignee_id != actor.id:
        raise HTTPException(status_code=403, detail="You can only publish your own location.")
    if assignment.status not in ACTIVE:
        raise HTTPException(status_code=409, detail="Tracking is only allowed on an active job.")

    latest = db.scalar(
        select(LocationUpdate)
        .where(LocationUpdate.assignment_id == assignment.id)
        .order_by(LocationUpdate.recorded_at.desc())
        .limit(1)
    )
    now = _now()
    if latest is not None:
        recorded = latest.recorded_at
        if recorded.tzinfo is None:
            recorded = recorded.replace(tzinfo=timezone.utc)
        moved = _meters(float(latest.latitude), float(latest.longitude), latitude, longitude)
        if now - recorded < MIN_INTERVAL and moved < MIN_MOVE_M:
            return latest, False

    row = LocationUpdate(
        assignment_id=assignment.id,
        latitude=Decimal(str(round(latitude, 6))),
        longitude=Decimal(str(round(longitude, 6))),
        accuracy_m=accuracy_m,
        heading_deg=Decimal(str(round(heading_deg, 2))) if heading_deg is not None else None,
        speed_mps=Decimal(str(round(speed_mps, 2))) if speed_mps is not None else None,
        recorded_at=now,
    )
    db.add(row)
    db.flush()
    return row, True


def latest_for_donation(db: Session, donation_id: uuid.UUID, actor: User) -> tuple[LocationUpdate, LogisticsAssignment] | None:
    from app.models.donation import Donation

    donation = db.get(Donation, donation_id)
    if donation is None:
        raise HTTPException(status_code=404, detail="Donation not found.")
    assignment = db.scalar(
        select(LogisticsAssignment)
        .where(
            LogisticsAssignment.donation_id == donation.id,
            LogisticsAssignment.status.in_(
                [AssignmentStatus.ACCEPTED, AssignmentStatus.EN_ROUTE, AssignmentStatus.COMPLETED]
            ),
        )
        .order_by(LogisticsAssignment.created_at.desc())
    )
    if assignment is None:
        return None
    if not can_read_collector(db, actor, assignment, donation):
        raise HTTPException(status_code=403, detail="You cannot view this collector location.")
    if assignment.status == AssignmentStatus.COMPLETED:
        # Exact live trail is not readable after the job ends, except the assignee and admin.
        if actor.role != UserRole.ADMIN and assignment.assignee_id != actor.id:
            raise HTTPException(status_code=403, detail="Tracking ended with this job.")
    row = db.scalar(
        select(LocationUpdate)
        .where(LocationUpdate.assignment_id == assignment.id)
        .order_by(LocationUpdate.recorded_at.desc())
        .limit(1)
    )
    if row is None:
        return None
    return row, assignment
