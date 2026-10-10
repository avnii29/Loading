"""Scheduled pickup rules for non-food household donations.

Uses the existing timezone-aware pickup window on commercial details and
pickup_deadline. Books, clothes, toys, and miscellaneous (OTHER) cannot be ASAP.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from app.models.donation import Donation
from app.models.enums import DonationCategory

SCHEDULED_ONLY = frozenset(
    {
        DonationCategory.BOOKS,
        DonationCategory.CLOTHES,
        DonationCategory.TOYS,
        DonationCategory.OTHER,
    }
)
ASAP_URGENCY = frozenset({"ASAP", "HIGH", "URGENT", "IMMEDIATE"})
ASAP_WINDOW = frozenset({"ASAP", "FLEXIBLE", "TODAY", "TODAY IF AVAILABLE"})
LOCAL_TZ = ZoneInfo("Asia/Kolkata")
MAX_WINDOW = timedelta(hours=12)


def is_scheduled_only(category: DonationCategory) -> bool:
    return category in SCHEDULED_ONLY


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def format_window(start: datetime, end: datetime) -> str:
    start_local = _aware(start).astimezone(LOCAL_TZ)
    end_local = _aware(end).astimezone(LOCAL_TZ)
    if start_local.date() == end_local.date():
        label = f"{start_local:%d %b %Y, %H:%M}–{end_local:%H:%M} IST"
    else:
        label = f"{start_local:%d %b %Y, %H:%M}–{end_local:%d %b %Y, %H:%M} IST"
    return label[:80]


def validate_scheduled_pickup(category: DonationCategory, payload: dict) -> None:
    """Reject ASAP and missing or past windows for scheduled-only categories."""
    if category not in SCHEDULED_ONLY:
        return
    urgency = str(payload.get("urgency") or "").strip().upper()
    label = str(payload.get("cluster_window") or "").strip().upper()
    if urgency in ASAP_URGENCY or label in ASAP_WINDOW:
        raise HTTPException(
            status_code=422,
            detail="Books, clothes, toys, and miscellaneous items need a scheduled pickup. ASAP is not available.",
        )
    commercial = dict(payload.get("commercial") or {})
    start = commercial.get("pickup_window_start")
    end = commercial.get("pickup_window_end")
    if not isinstance(start, datetime) or not isinstance(end, datetime):
        raise HTTPException(
            status_code=422,
            detail="Choose a future pickup date and time window.",
        )
    start = _aware(start)
    end = _aware(end)
    now = datetime.now(timezone.utc)
    if start <= now:
        raise HTTPException(
            status_code=422,
            detail="That pickup window is in the past or has already started. Choose a later window.",
        )
    if end <= start:
        raise HTTPException(status_code=422, detail="Pickup window end must be after the start.")
    if end - start > MAX_WINDOW:
        raise HTTPException(
            status_code=422,
            detail="Choose a shorter pickup window, such as morning, afternoon, or evening.",
        )
    commercial["pickup_window_start"] = start
    commercial["pickup_window_end"] = end
    payload["commercial"] = commercial
    payload["pickup_deadline"] = end
    payload["urgency"] = "SCHEDULED"
    if not str(payload.get("cluster_window") or "").strip():
        payload["cluster_window"] = format_window(start, end)


def window_bounds(donation: Donation) -> tuple[datetime | None, datetime | None]:
    details = donation.commercial_details
    if details is None:
        return None, donation.pickup_deadline
    return details.pickup_window_start, details.pickup_window_end or donation.pickup_deadline


def schedule_label(donation: Donation) -> str | None:
    start, end = window_bounds(donation)
    if start is not None and end is not None:
        return format_window(start, end)
    label = (donation.cluster_window or "").strip()
    if label and label.upper() not in ASAP_WINDOW:
        return label
    if donation.category == DonationCategory.FOOD and (
        (donation.urgency or "").upper() in ASAP_URGENCY or label.upper() == "ASAP"
    ):
        return "ASAP"
    return None


def scheduled_window_is_open(donation: Donation, now: datetime | None = None) -> bool:
    """Non-food pickups stay offerable only while their agreed window has not ended."""
    if donation.category not in SCHEDULED_ONLY:
        return True
    start, end = window_bounds(donation)
    if start is None or end is None:
        return False
    now = now or datetime.now(timezone.utc)
    end_utc = _aware(end)
    return end_utc > now
