"""Eco-points are credited only after a verified delivery. Catalog items are not redeemable without a partner."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.donation import Donation
from app.models.enums import DonationCategory
from app.models.rewards import PointsEntry

LEVELS = (
    ("Starter", 0, 100),
    ("Contributor", 100, 250),
    ("Changemaker", 250, 500),
    ("Community Hero", 500, 1000),
    ("Anuvarthan Champion", 1000, None),
)

CATALOG = (
    {"id": "eco_chai_pass", "title": "Eco-Chai Pass", "cost": 50, "blurb": "Shown until a café partner is configured."},
    {"id": "rethread_voucher", "title": "Re-Thread Voucher", "cost": 100, "blurb": "Shown until a retail partner is configured."},
    {"id": "student_impact_pass", "title": "Student Impact Pass", "cost": 150, "blurb": "A record of points, not a university certificate."},
)


def calculate_donation_points(donation: Donation) -> tuple[int, str]:
    qty = float(donation.quantity or 0)
    if donation.category == DonationCategory.FOOD:
        if qty >= 80 or (str(donation.unit or "").lower() == "kg" and qty >= 40):
            return 25, "Large food donation delivered"
        return 20, "Food donation delivered"
    return 10, "Item donation delivered"


def award_for_delivery(db: Session, donation: Donation) -> PointsEntry | None:
    existing = db.scalar(select(PointsEntry).where(PointsEntry.donation_id == donation.id))
    if existing:
        return existing
    points, reason = calculate_donation_points(donation)
    row = PointsEntry(user_id=donation.donor_id, donation_id=donation.id, points=points, reason=reason)
    db.add(row)
    db.flush()
    return row


def summary_for_user(db: Session, user_id: uuid.UUID) -> dict:
    balance = db.scalar(select(func.coalesce(func.sum(PointsEntry.points), 0)).where(PointsEntry.user_id == user_id))
    points = int(balance or 0)
    current = LEVELS[0]
    for level in LEVELS:
        if points >= level[1]:
            current = level
    name, minimum, nxt = current
    return {
        "balance": points,
        "level": name,
        "level_min": minimum,
        "next_level_at": nxt,
        "catalog": [{**item, "redeemable": False, "reason": "No partner venue is configured."} for item in CATALOG],
    }
