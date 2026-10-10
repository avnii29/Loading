from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import DonationCategory, DonationStream, QualityResult, QualityStage


class CommercialDetailsIn(BaseModel):
    event_type: str | None = None
    estimated_servings: int | None = Field(default=None, ge=1, le=100000)
    packaging_state: str | None = None
    pickup_window_start: datetime | None = None
    pickup_window_end: datetime | None = None


class DonationCreateRequest(BaseModel):
    category: DonationCategory
    stream: DonationStream | None = None
    title: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    quantity: Decimal = Field(gt=0, le=100000)
    unit: str = Field(min_length=1, max_length=40)
    notes: str | None = Field(default=None, max_length=2000)
    condition: str | None = Field(default=None, max_length=40)
    pickup_address: str | None = Field(default=None, max_length=400)
    pickup_latitude: Decimal | None = Field(default=None, ge=-90, le=90)
    pickup_longitude: Decimal | None = Field(default=None, ge=-180, le=180)
    location_accuracy_m: int | None = Field(default=None, ge=0, le=50000)
    location_source: str | None = Field(default=None, max_length=40)
    location_provider: str | None = Field(default=None, max_length=40)
    mappls_pin: str | None = Field(default=None, max_length=12)
    provider_place_id: str | None = Field(default=None, max_length=64)
    geocode_precision: str | None = Field(default=None, max_length=40)
    location_captured_at: datetime | None = None
    location_confirmed_at: datetime | None = None
    pickup_landmark: str | None = Field(default=None, max_length=240)
    pickup_pincode: str | None = Field(default=None, min_length=6, max_length=6, pattern=r"^\d{6}$")
    food_source: str | None = Field(default=None, max_length=40)
    packaging_state: str | None = Field(default=None, max_length=40)
    diet_type: str | None = Field(default=None, max_length=40)
    urgency: str | None = Field(default=None, max_length=20)
    prepared_at: datetime | None = None
    pickup_deadline: datetime | None = None
    distribution_deadline: datetime | None = None
    cluster_window: str | None = Field(default=None, max_length=80)
    cluster_sector: str | None = Field(default=None, max_length=40)
    commercial: CommercialDetailsIn | None = None
    quality_notes: str | None = Field(default=None, max_length=1000)
    quality_checklist: dict[str, str | bool] | None = None
    idempotency_key: str | None = Field(default=None, max_length=64)
    preferred_centre_id: UUID | None = None


class StatusHistoryOut(BaseModel):
    from_status: str | None
    to_status: str
    note: str | None
    created_at: datetime


class PhotoOut(BaseModel):
    id: str
    url: str
    mime_type: str
    created_at: datetime


class QualityOut(BaseModel):
    id: str
    stage: str
    result: str
    notes: str | None
    created_at: datetime


class DonationOut(BaseModel):
    id: str
    reference_code: str
    stream: str
    category: str
    status: str
    status_label: str
    title: str | None
    description: str | None
    quantity: Decimal
    unit: str
    notes: str | None
    pickup_address: str | None
    pickup_latitude: Decimal | None
    pickup_longitude: Decimal | None
    location_accuracy_m: int | None
    location_source: str | None
    location_provider: str | None = None
    mappls_pin: str | None = None
    provider_place_id: str | None = None
    geocode_precision: str | None = None
    location_captured_at: datetime | None = None
    location_confirmed_at: datetime | None = None
    pickup_landmark: str | None = None
    prepared_at: datetime | None
    pickup_deadline: datetime | None
    distribution_deadline: datetime | None
    cluster_window: str | None = None
    destination_id: str | None
    created_at: datetime
    updated_at: datetime
    photos: list[PhotoOut] = []
    history: list[StatusHistoryOut] = []
    quality_checks: list[QualityOut] = []
    verification_code: str | None = None
    assignee_name: str | None = None
    eta_minutes: int | None = None
    is_donor: bool = False
    preferred_centre_id: str | None = None
    proposed_centre_id: str | None = None
    proposal_reason: str | None = None


class DonationCreatedOut(DonationOut):
    verification_code: str


class QualityCheckIn(BaseModel):
    result: QualityResult
    notes: str | None = None
    stage: QualityStage | None = None
    checklist_version: str | None = Field(default="donor-food-v1", max_length=40)
    responses: dict[str, str | bool] | None = None


class AdminTransitionIn(BaseModel):
    status: str
    note: str | None = None
