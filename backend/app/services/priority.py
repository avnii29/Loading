"""Deterministic food-first dispatch priority scoring.

Scores are application policy weights — not a claim of physical urgency by themselves.
Safety-ineligible donations must not be enqueued as ACTIVE human-consumption food.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from app.models.donation import Donation
from app.models.enums import DonationCategory, DonationStatus, QualityResult, QualityStage


# Configurable weights (documented policy).
W_FOOD = 400
W_FUNCTION_HALL = 120
W_RESTAURANT_EVENT = 80
W_URGENCY_HIGH = 100
W_URGENCY_NORMAL = 20
W_FRESHNESS_MAX = 150
W_WAITING_PER_MIN = 0.5
W_WAITING_CAP = 80
W_NONFOOD_BASE = 40
W_AGING_NONFOOD_PER_HOUR = 3
W_AGING_NONFOOD_CAP = 60


@dataclass(frozen=True)
class PriorityResult:
    score: Decimal
    priority_class: str  # P0..P3
    eligible: bool
    hold_reason: str | None = None


def _minutes_since(dt: datetime | None, now: datetime) -> float:
    if dt is None:
        return 0.0
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return max(0.0, (now - dt).total_seconds() / 60.0)


def donor_quality_blocks_dispatch(donation: Donation) -> bool:
    checks = donation.quality_checks or []
    donor = [c for c in checks if c.stage == QualityStage.DONOR_SELF]
    if not donor:
        # Food requires a donor declaration before dispatch.
        return donation.category == DonationCategory.FOOD
    latest = max(donor, key=lambda c: c.created_at)
    return latest.result in {QualityResult.REJECTED, QualityResult.REQUIRES_REVIEW}


def score_donation(donation: Donation, *, now: datetime | None = None) -> PriorityResult:
    now = now or datetime.now(timezone.utc)
    if donation.status in {
        DonationStatus.CANCELLED,
        DonationStatus.COMPLETED,
        DonationStatus.REJECTED,
        DonationStatus.EXPIRED,
    }:
        return PriorityResult(Decimal("0"), "P3", False, "terminal_status")

    if donation.category == DonationCategory.FOOD and donor_quality_blocks_dispatch(donation):
        return PriorityResult(Decimal("0"), "P2", False, "safety_hold")

    score = 0.0
    food = donation.category == DonationCategory.FOOD
    source = (donation.food_source or "").upper()
    urgency = (donation.urgency or "").upper()
    event = ""
    if donation.commercial_details and donation.commercial_details.event_type:
        event = donation.commercial_details.event_type.upper()

    if food:
        score += W_FOOD
        if source in {"FUNCTION_HALL", "WEDDING"} or "WEDDING" in event or "FUNCTION" in event:
            score += W_FUNCTION_HALL
        elif source in {"RESTAURANT", "EVENT", "HOSTEL", "OFFICE"}:
            score += W_RESTAURANT_EVENT
        if urgency in {"HIGH", "URGENT", "IMMEDIATE"}:
            score += W_URGENCY_HIGH
        else:
            score += W_URGENCY_NORMAL
        # Fresher food (recent prepared_at) gets higher score; stale food loses points.
        if donation.prepared_at:
            age_h = _minutes_since(donation.prepared_at, now) / 60.0
            freshness = max(0.0, W_FRESHNESS_MAX - age_h * 25)
            score += freshness
        waiting = min(W_WAITING_CAP, _minutes_since(donation.created_at, now) * W_WAITING_PER_MIN)
        score += waiting
        # Deadline pressure
        if donation.pickup_deadline:
            mins_left = (donation.pickup_deadline - now).total_seconds() / 60.0
            if mins_left < 60:
                score += 90
            elif mins_left < 180:
                score += 45
        if score >= 700 or (urgency in {"HIGH", "URGENT", "IMMEDIATE"} and source in {"FUNCTION_HALL", "WEDDING"}):
            pclass = "P0"
        elif score >= 520:
            pclass = "P1"
        else:
            pclass = "P2"
    else:
        score += W_NONFOOD_BASE
        aging = min(W_AGING_NONFOOD_CAP, (_minutes_since(donation.created_at, now) / 60.0) * W_AGING_NONFOOD_PER_HOUR)
        score += aging
        pclass = "P3"

    # Deterministic fractional tie-break from creation time (newer slightly lower within class).
    tie = (donation.created_at.timestamp() % 1000) / 10000.0 if donation.created_at else 0.0
    return PriorityResult(Decimal(f"{score + tie:.3f}"), pclass, True, None)
