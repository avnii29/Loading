from decimal import Decimal
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import VerificationStatus, IntakeStatus


class OrganizationPublic(BaseModel):
    id: str
    name: str
    description: str | None
    verification_status: str
    intake_status: str
    address: str | None
    city: str | None
    latitude: Decimal | None
    longitude: Decimal | None
    mappls_pin: str | None = None
    location_provider: str | None = None
    accepted_categories: list[str] | None
    distance_km: float | None = None
    phone: str | None = None
    source_note: str | None = None
    approximate: bool = False


class OrganizationSelf(OrganizationPublic):
    user_id: str
    is_active: bool
    created_at: datetime


class DestinationRecommendation(BaseModel):
    id: str
    name: str
    facility_type: str | None = None
    address: str | None = None
    locality: str | None = None
    distance_km: float
    distance_kind: str = "straight_line"
    approximate: bool = True
    operational_status: str
    verification_status: str = "DIRECTORY"
    category_hint: bool = False
    eligible_as_final_destination: bool = False
    caveat: str | None = None
    donor_preferred: bool = False


class RecommendationList(BaseModel):
    search: str
    distance_kind: str = "straight_line"
    note: str
    options: list[DestinationRecommendation]


class OrganizationUpdate(BaseModel):
    description: str | None = Field(default=None, max_length=2000)
    address: str | None = Field(default=None, max_length=400)
    city: str | None = Field(default=None, max_length=120)
    pincode: str | None = Field(default=None, max_length=12)
    latitude: Decimal | None = Field(default=None, ge=-90, le=90)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180)
    mappls_pin: str | None = Field(default=None, max_length=12)
    location_provider: str | None = Field(default=None, max_length=40)
    provider_place_id: str | None = Field(default=None, max_length=64)
    accepted_categories: list[str] | None = None
    intake_status: IntakeStatus | None = None
    capacity_notes: str | None = Field(default=None, max_length=1000)


class VerificationUpdate(BaseModel):
    status: VerificationStatus
    note: str | None = Field(default=None, max_length=500)
