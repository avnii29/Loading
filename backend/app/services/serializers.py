from app.models.donation import Donation
from app.models.logistics import LogisticsAssignment
from app.models.organization import Organization
from app.schemas.donation import DonationOut, PhotoOut, QualityOut, StatusHistoryOut
from app.schemas.organization import OrganizationPublic
from app.services.schedule import schedule_label
from app.services.status import STATUS_LABELS


def serialize_donation(
    donation: Donation,
    *,
    verification_code: str | None = None,
    assignment: LogisticsAssignment | None = None,
    viewer_id=None,
) -> DonationOut:
    assignee_name = None
    if assignment and assignment.assignee and assignment.assignee.profile:
        assignee_name = assignment.assignee.profile.full_name

    return DonationOut(
        id=str(donation.id),
        reference_code=donation.reference_code,
        stream=donation.stream.value,
        category=donation.category.value,
        status=donation.status.value,
        status_label=STATUS_LABELS.get(donation.status, donation.status.value),
        title=donation.title,
        description=donation.description,
        quantity=donation.quantity,
        unit=donation.unit,
        notes=donation.notes,
        pickup_address=donation.pickup_address,
        pickup_latitude=donation.pickup_latitude,
        pickup_longitude=donation.pickup_longitude,
        location_accuracy_m=donation.location_accuracy_m,
        location_source=donation.location_source,
        location_provider=donation.location_provider,
        mappls_pin=donation.mappls_pin,
        provider_place_id=donation.provider_place_id,
        geocode_precision=donation.geocode_precision,
        location_captured_at=donation.location_captured_at,
        location_confirmed_at=donation.location_confirmed_at,
        pickup_landmark=donation.pickup_landmark,
        prepared_at=donation.prepared_at,
        pickup_deadline=donation.pickup_deadline,
        distribution_deadline=donation.distribution_deadline,
        cluster_window=schedule_label(donation),
        destination_id=str(donation.destination_id) if donation.destination_id else None,
        created_at=donation.created_at,
        updated_at=donation.updated_at,
        photos=[
            PhotoOut(
                id=str(p.id),
                url=f"/api/uploads/{p.storage_key}",
                mime_type=p.mime_type,
                created_at=p.created_at,
            )
            for p in (donation.photos or [])
        ],
        history=[
            StatusHistoryOut(
                from_status=h.from_status.value if h.from_status else None,
                to_status=h.to_status.value,
                note=h.note,
                created_at=h.created_at,
            )
            for h in sorted(donation.status_history or [], key=lambda x: x.created_at)
        ],
        quality_checks=[
            QualityOut(
                id=str(q.id),
                stage=q.stage.value,
                result=q.result.value,
                notes=q.notes,
                created_at=q.created_at,
            )
            for q in (donation.quality_checks or [])
        ],
        verification_code=verification_code,
        assignee_name=assignee_name,
        eta_minutes=None,
        is_donor=viewer_id is not None and donation.donor_id == viewer_id,
        preferred_centre_id=str(donation.preferred_centre_id) if donation.preferred_centre_id else None,
        proposed_centre_id=str(donation.proposed_centre_id) if donation.proposed_centre_id else None,
        proposal_reason=donation.proposal_reason,
    )


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    from math import atan2, cos, radians, sin, sqrt

    r = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return round(2 * r * atan2(sqrt(a), sqrt(1 - a)), 2)


def serialize_org(org: Organization, origin: tuple[float, float] | None = None) -> OrganizationPublic:
    distance = None
    if origin and org.latitude is not None and org.longitude is not None:
        distance = haversine_km(origin[0], origin[1], float(org.latitude), float(org.longitude))
    return OrganizationPublic(
        id=str(org.id),
        name=org.name,
        description=org.description,
        verification_status=org.verification_status.value,
        intake_status=org.intake_status.value,
        address=org.address,
        city=org.city,
        latitude=org.latitude,
        longitude=org.longitude,
        mappls_pin=org.mappls_pin,
        location_provider=org.location_provider,
        accepted_categories=org.accepted_categories,
        distance_km=distance,
    )
