"""Second pass: geocode directory rows that still have no pin, using locality or PIN."""

from __future__ import annotations

import re
import time
from decimal import Decimal

import httpx
from sqlalchemy import select

from app.database import SessionLocal
from app.models.organization import DonationCentre

USER_AGENT = "Anuvarthan/1.0 (donation centre import)"


def geocode(query: str) -> dict | None:
    response = httpx.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": query, "format": "jsonv2", "limit": "1", "countrycodes": "in"},
        headers={"User-Agent": USER_AGENT},
        timeout=12,
    )
    if response.status_code != 200:
        return None
    rows = response.json()
    if not rows:
        return None
    row = rows[0]
    return {
        "lat": Decimal(str(round(float(row["lat"]), 6))),
        "lng": Decimal(str(round(float(row["lon"]), 6))),
    }


def queries_for(centre: DonationCentre) -> list[str]:
    address = centre.address or ""
    if "not in source" in address.lower() or "no street" in address.lower():
        address = ""
    found = []
    pin = re.search(r"\b(\d{6})\b", address)
    if pin:
        found.append(f"{pin.group(1)}, India")
    parts = [part.strip(" .") for part in re.split(r"[,;]", address) if len(part.strip()) > 2]
    if len(parts) >= 2:
        found.append(f"{parts[-2]}, {parts[-1]}, Telangana, India")
    if centre.district:
        found.append(f"{centre.district}, Telangana, India")
    if parts:
        found.append(f"{parts[-1]}, Telangana, India")
    return found


def main() -> None:
    db = SessionLocal()
    filled = 0
    try:
        rows = list(db.scalars(select(DonationCentre).where(DonationCentre.latitude.is_(None))))
        for centre in rows:
            point = None
            for query in queries_for(centre):
                try:
                    point = geocode(query)
                except Exception:
                    point = None
                time.sleep(1.1)
                if point:
                    break
            if not point:
                continue
            centre.latitude = point["lat"]
            centre.longitude = point["lng"]
            centre.location_provider = "nominatim"
            centre.approximate = True
            filled += 1
        db.commit()
    finally:
        db.close()
    print(f"filled {filled}")


if __name__ == "__main__":
    main()
