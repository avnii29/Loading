from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_roles
from app.models.donation import Donation
from app.models.enums import UserRole, VerificationStatus
from app.models.organization import Organization, Destination, RecoveryPartner
from app.models.ops import AuditLog
from app.models.user import User
from app.schemas.organization import VerificationUpdate, OrganizationPublic
from app.services.audit import write_audit
from app.services.serializers import serialize_org

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/organizations", response_model=list[OrganizationPublic])
def all_orgs(
    _user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    rows = list(db.scalars(select(Organization).order_by(Organization.created_at.desc())))
    return [serialize_org(row) for row in rows]


@router.post("/organizations/{organization_id}/verification", response_model=OrganizationPublic)
def verify_org(
    organization_id: UUID,
    data: VerificationUpdate,
    user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    org = db.get(Organization, organization_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organisation not found.")
    previous = org.verification_status
    org.verification_status = data.status
    if data.status == VerificationStatus.VERIFIED:
        dests = list(db.scalars(select(Destination).where(Destination.organization_id == org.id)))
        for dest in dests:
            dest.is_active = True
            db.add(dest)
    db.add(org)
    write_audit(
        db,
        action="organization.verification",
        entity_type="organization",
        entity_id=org.id,
        actor_id=user.id,
        extra={"from": previous.value, "to": data.status.value, "note": data.note},
    )
    db.commit()
    db.refresh(org)
    return serialize_org(org)


@router.get("/recovery-partners")
def partners(
    _user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    rows = list(db.scalars(select(RecoveryPartner).order_by(RecoveryPartner.created_at.desc())))
    return [
        {
            "id": str(row.id),
            "name": row.name,
            "verification_status": row.verification_status.value,
            "is_active": row.is_active,
        }
        for row in rows
    ]


@router.post("/recovery-partners/{partner_id}/verification")
def verify_partner(
    partner_id: UUID,
    data: VerificationUpdate,
    user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    partner = db.get(RecoveryPartner, partner_id)
    if partner is None:
        raise HTTPException(status_code=404, detail="Recovery partner not found.")
    previous = partner.verification_status
    partner.verification_status = data.status
    db.add(partner)
    write_audit(
        db,
        action="recovery_partner.verification",
        entity_type="recovery_partner",
        entity_id=partner.id,
        actor_id=user.id,
        extra={"from": previous.value, "to": data.status.value, "note": data.note},
    )
    db.commit()
    return {
        "id": str(partner.id),
        "name": partner.name,
        "verification_status": partner.verification_status.value,
    }


@router.get("/operations-map")
def operations_map(
    _user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    orgs = list(db.scalars(select(Organization).where(Organization.is_demo.is_(False))))
    donations = list(db.scalars(select(Donation).where(Donation.is_demo.is_(False))))
    partners = list(db.scalars(select(RecoveryPartner).where(RecoveryPartner.is_demo.is_(False))))
    return {
        "organizations": [
            {
                "id": str(row.id),
                "kind": "organisation",
                "name": row.name,
                "verification_status": row.verification_status.value,
                "latitude": float(row.latitude) if row.latitude is not None else None,
                "longitude": float(row.longitude) if row.longitude is not None else None,
            }
            for row in orgs
            if row.latitude is not None and row.longitude is not None
        ],
        "donations": [
            {
                "id": str(row.id),
                "kind": "donation",
                "reference": row.reference_code,
                "category": row.category.value,
                "status": row.status.value,
                "deadline": row.distribution_deadline or row.pickup_deadline,
                "latitude": float(row.pickup_latitude) if row.pickup_latitude is not None else None,
                "longitude": float(row.pickup_longitude) if row.pickup_longitude is not None else None,
            }
            for row in donations
            if row.pickup_latitude is not None and row.pickup_longitude is not None
        ],
        "recovery_partners": [
            {
                "id": str(row.id),
                "kind": "recovery",
                "name": row.name,
                "verification_status": row.verification_status.value,
                "latitude": float(row.latitude) if row.latitude is not None else None,
                "longitude": float(row.longitude) if row.longitude is not None else None,
            }
            for row in partners
            if row.latitude is not None and row.longitude is not None
        ],
        "routes": [],
    }


@router.get("/audit")
def audit_feed(
    _user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    rows = list(db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(100)))
    return [
        {
            "id": str(row.id),
            "actor_id": str(row.actor_id) if row.actor_id else None,
            "action": row.action,
            "entity_type": row.entity_type,
            "entity_id": str(row.entity_id) if row.entity_id else None,
            "extra": row.extra,
            "created_at": row.created_at,
        }
        for row in rows
    ]
