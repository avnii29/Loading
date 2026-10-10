"""Load DONATION_CENTRES.xlsx into donation_centres and geocode published addresses."""

from __future__ import annotations

import re
import time
import uuid
from decimal import Decimal
from pathlib import Path

import httpx
import openpyxl
from sqlalchemy import select

from app.database import SessionLocal
from app.models.organization import DonationCentre

SOURCE = Path(r"C:\Users\ravni\Downloads\DONATION_CENTRES.xlsx")
USER_AGENT = "Anuvarthan/1.0 (donation centre import)"


def categories(text: str) -> list[str]:
    value = text.lower()
    found = []
    if any(word in value for word in ("food", "meal", "ration", "rice")):
        found.append("FOOD")
    if any(word in value for word in ("cloth", "uniform")):
        found.append("CLOTHES")
    if any(word in value for word in ("book", "school", "librar")):
        found.append("BOOKS")
    if "toy" in value:
        found.append("TOYS")
    return found or ["FOOD"]


def clean_phone(value) -> str | None:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text[:40] or None


def geocode(query: str) -> dict | None:
    response = httpx.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": query, "format": "jsonv2", "limit": "1", "countrycodes": "in", "addressdetails": "1"},
        headers={"User-Agent": USER_AGENT},
        timeout=12,
    )
    response.raise_for_status()
    rows = response.json()
    if not rows:
        return None
    row = rows[0]
    kind = str(row.get("type") or row.get("addresstype") or "")
    return {
        "lat": Decimal(str(round(float(row["lat"]), 6))),
        "lng": Decimal(str(round(float(row["lon"]), 6))),
        "approximate": kind not in {"house", "building"},
        "label": row.get("display_name"),
    }


def main() -> None:
    wb = openpyxl.load_workbook(SOURCE, read_only=True, data_only=True)
    db = SessionLocal()
    added = 0
    geocoded = 0
    try:
        sheets = (
            ("Facilities (verified sites)", "published"),
            ("Unverified leads", "unconfirmed"),
        )
        for sheet_name, listing in sheets:
            ws = wb[sheet_name]
            rows = ws.iter_rows(values_only=True)
            next(rows)
            for row in rows:
                if not row or not row[1]:
                    continue
                name = str(row[1]).strip()
                if listing == "published":
                    facility_type, district, address, phone, provides, capacity, donate, source, caveat = row[2:11]
                else:
                    address, caveat, source = row[2], row[3], row[4]
                    facility_type = district = phone = provides = capacity = donate = None
                address_text = str(address).strip() if address else None
                exists = db.scalar(
                    select(DonationCentre).where(DonationCentre.name == name, DonationCentre.address == address_text)
                )
                if exists:
                    continue
                point = None
                query = ", ".join(part for part in (address_text, "Telangana", "India") if part)
                if address_text:
                    try:
                        point = geocode(query)
                        geocoded += 1 if point else 0
                    except Exception:
                        point = None
                    time.sleep(1.1)
                db.add(
                    DonationCentre(
                        id=uuid.uuid4(),
                        name=name,
                        facility_type=str(facility_type).strip() if facility_type else None,
                        district=str(district).strip() if district else None,
                        address=address_text,
                        city=str(district).split(",")[-1].strip() if district else None,
                        phone=clean_phone(phone),
                        provides=str(provides).strip() if provides else None,
                        capacity_notes=str(capacity).strip() if capacity else None,
                        donate_notes=str(donate).strip() if donate else None,
                        source_url=str(source).strip() if source else None,
                        caveat=str(caveat).strip() if caveat else None,
                        listing=listing,
                        latitude=point["lat"] if point else None,
                        longitude=point["lng"] if point else None,
                        location_provider="nominatim" if point else None,
                        approximate=True if not point else point["approximate"],
                        accepted_categories=categories(f"{donate or ''} {provides or ''}"),
                        is_active=True,
                    )
                )
                added += 1
        db.commit()
    finally:
        db.close()
    print(f"added {added} geocoded {geocoded}")


if __name__ == "__main__":
    main()
