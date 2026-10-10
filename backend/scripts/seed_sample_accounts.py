"""Idempotent sample accounts for local/demo sign-in.

Short ids resolve to *@anuvarthan.test
"""

from decimal import Decimal

from app.database import SessionLocal
from app.models.enums import DonorType, UserRole, VerificationStatus
from app.models.organization import Destination, Organization, RecoveryPartner
from app.models.user import Profile, User
from app.services.auth import hash_password

ORG_ADDRESS = "12-2-417/A, Mehdipatnam, Hyderabad"
ORG_CITY = "Hyderabad"
ORG_LAT = Decimal("17.394800")
ORG_LNG = Decimal("78.437400")

SAMPLES = [
    {
        "email": "abc@anuvarthan.test",
        "password": "abc123",
        "full_name": "Household Donor",
        "role": UserRole.DONOR,
        "donor_type": DonorType.HOUSEHOLD,
    },
    {
        "email": "def@anuvarthan.test",
        "password": "def123",
        "full_name": "Function Hall Donor",
        "role": UserRole.DONOR,
        "donor_type": DonorType.FUNCTION_HALL,
    },
    {
        "email": "ghi@anuvarthan.test",
        "password": "ghi123",
        "full_name": "NSS Volunteer",
        "role": UserRole.VOLUNTEER,
    },
    {
        "email": "jkl@anuvarthan.test",
        "password": "jkl123",
        "full_name": "Gig Rider",
        "role": UserRole.DRIVER,
    },
    {
        "email": "mno@anuvarthan.test",
        "password": "mno123",
        "full_name": "Poultry Farm Operator",
        "role": UserRole.FARM_OPERATOR,
        "organization_name": "Sample Poultry Farm",
    },
    {
        "email": "org@anuvarthan.test",
        "password": "org123",
        "full_name": "Organisation NGO",
        "role": UserRole.ORGANIZATION,
        "organization_name": "Mehdipatnam Community NGO",
    },
]


def upsert_sample(db, spec: dict) -> None:
    email = spec["email"]
    user = db.query(User).filter(User.email == email).one_or_none()
    if user is None:
        # Prefer renaming the previous demo domain over creating a duplicate short-id user.
        legacy = email.replace("@anuvarthan.test", "@dilsedaan.test")
        user = db.query(User).filter(User.email == legacy).one_or_none()
        if user is not None:
            user.email = email
        else:
            user = User(email=email, password_hash=hash_password(spec["password"]), role=spec["role"])
            db.add(user)
            db.flush()
    if user.id is None:
        db.flush()
    user.password_hash = hash_password(spec["password"])
    user.role = spec["role"]
    user.is_active = True

    if user.profile is None:
        db.add(
            Profile(
                user_id=user.id,
                full_name=spec["full_name"],
                donor_type=spec.get("donor_type"),
            )
        )
    else:
        user.profile.full_name = spec["full_name"]
        user.profile.donor_type = spec.get("donor_type")

    if spec["role"] == UserRole.ORGANIZATION:
        org = user.organization
        if org is None:
            org = Organization(user_id=user.id, name=spec["organization_name"])
            db.add(org)
            db.flush()
        org.name = spec["organization_name"]
        org.address = ORG_ADDRESS
        org.city = ORG_CITY
        org.latitude = ORG_LAT
        org.longitude = ORG_LNG
        org.verification_status = VerificationStatus.VERIFIED
        org.is_active = True
        org.is_demo = False
        org.accepted_categories = ["FOOD", "CLOTHES", "BOOKS", "TOYS", "OTHER"]
        dest = db.query(Destination).filter(Destination.organization_id == org.id).first()
        if dest is None:
            dest = Destination(organization_id=org.id, name=org.name)
            db.add(dest)
            db.flush()
        dest.name = org.name
        dest.address = ORG_ADDRESS
        dest.city = ORG_CITY
        dest.latitude = ORG_LAT
        dest.longitude = ORG_LNG
        dest.is_active = True

    if spec["role"] == UserRole.FARM_OPERATOR:
        partner = user.recovery_partner
        if partner is None:
            partner = RecoveryPartner(user_id=user.id, name=spec["organization_name"])
            db.add(partner)
            db.flush()
        partner.name = spec["organization_name"]
        partner.verification_status = VerificationStatus.VERIFIED
        partner.is_active = True
        partner.is_demo = False


def main() -> None:
    db = SessionLocal()
    try:
        for spec in SAMPLES:
            upsert_sample(db, spec)
        db.commit()
        print("Sample accounts ready:")
        for spec in SAMPLES:
            short = spec["email"].split("@")[0]
            print(f"  {short:4} / {spec['password']:6}  →  {spec['email']}  ({spec['role'].value})")
        print(f"Org pin: {ORG_ADDRESS}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
