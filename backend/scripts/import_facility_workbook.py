"""Reimport the facility workbook without geocoding or inventing contacts."""

from pathlib import Path

from app.database import SessionLocal
from app.services.centre_import import import_workbook

SOURCE = Path(r"C:\Users\ravni\Downloads\DONATION_CENTRES.xlsx")


def main() -> None:
    db = SessionLocal()
    try:
        report = import_workbook(db, SOURCE)
        db.commit()
    finally:
        db.close()
    print(
        {
            "imported": report.imported,
            "updated": report.updated,
            "skipped": report.skipped,
            "duplicates": report.duplicates,
            "unresolved": report.unresolved,
            "invalid": report.invalid,
            "leads_kept_separate": report.leads_kept_separate,
            "removed_not_activated": report.removed_not_activated,
            "notes": report.notes,
        }
    )


if __name__ == "__main__":
    main()
