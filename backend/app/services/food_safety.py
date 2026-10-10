"""Declarations and observations. A full set of Yes answers is not a safety certificate."""

from __future__ import annotations

from app.models.enums import QualityResult

# Cooked food held past 2 hours at unknown or room temperature is not cleared for dispatch.
# Over 4 hours is refused. Hot/Cold without a measured temperature is not treated as safe.


def _norm(value) -> str:
    if value is True:
        return "YES"
    if value is False:
        return "NO"
    return str(value or "").strip().upper().replace(" ", "_").replace("–", "-")


def donor_food_result(responses: dict, handling: str) -> QualityResult:
    handling = handling.upper()
    stored = _norm(responses.get("stored_safely"))
    covered = _norm(responses.get("covered"))
    if stored == "NO" or covered == "NO":
        return QualityResult.REJECTED
    if handling == "DRY_RATIONS":
        if stored == "YES" and covered == "YES":
            return QualityResult.ACCEPTABLE
        return QualityResult.REQUIRES_REVIEW

    fresh = _norm(responses.get("freshly_prepared"))
    age = _norm(responses.get("time_since_cooking"))
    if fresh == "NO" or age in {"OVER_4H", "OVER_4_H"}:
        return QualityResult.REJECTED
    if fresh == "YES" and stored == "YES" and covered == "YES" and age == "UNDER_2H":
        return QualityResult.ACCEPTABLE
    return QualityResult.REQUIRES_REVIEW


def pickup_food_result(responses: dict) -> QualityResult:
    looks = _norm(responses.get("looks_normal"))
    smell = _norm(responses.get("unusual_smell"))
    spill = _norm(responses.get("spillage"))
    seal = _norm(responses.get("seal_intact"))
    temp = _norm(responses.get("temperature"))
    if looks == "NO" or smell == "YES" or spill == "YES" or seal == "NO":
        return QualityResult.REQUIRES_REVIEW
    if looks == "YES" and smell == "NO" and spill == "NO" and seal in {"YES", "NA", "N/A"} and temp in {"HOT", "COLD", "ROOM_TEMP"}:
        # Observed condition only. Room temperature still needs the donor time window to have passed.
        return QualityResult.ACCEPTABLE
    return QualityResult.REQUIRES_REVIEW


def intake_food_result(responses: dict) -> QualityResult:
    decision = _norm(responses.get("accepted"))
    looks = _norm(responses.get("looks_normal"))
    pack = _norm(responses.get("packaging_intact"))
    qty = _norm(responses.get("quantity_received"))
    if decision == "REJECT" or looks == "NO" or pack == "NO":
        return QualityResult.REJECTED if decision == "REJECT" or looks == "NO" else QualityResult.REQUIRES_REVIEW
    if decision in {"HOLD", "REJECT"} or qty in {"PARTIAL", "MISMATCH"} or looks != "YES" or pack not in {"YES", "NA", "N/A"}:
        return QualityResult.REQUIRES_REVIEW
    if decision == "ACCEPT" and looks == "YES" and pack in {"YES", "NA", "N/A"} and qty == "FULL":
        return QualityResult.ACCEPTABLE
    return QualityResult.REQUIRES_REVIEW
