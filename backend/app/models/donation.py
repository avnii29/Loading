import uuid
from decimal import Decimal

from sqlalchemy import (
    String,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Text,
    Numeric,
    Integer,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import (
    DonationStream,
    DonationCategory,
    DonationStatus,
    QualityStage,
    QualityResult,
)


class Donation(Base):
    __tablename__ = "donations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reference_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    donor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    stream: Mapped[DonationStream] = mapped_column(
        Enum(DonationStream, name="donation_stream"),
        nullable=False,
    )
    category: Mapped[DonationCategory] = mapped_column(
        Enum(DonationCategory, name="donation_category"),
        nullable=False,
        index=True,
    )
    status: Mapped[DonationStatus] = mapped_column(
        Enum(DonationStatus, name="donation_status"),
        default=DonationStatus.SUBMITTED,
        nullable=False,
        index=True,
    )
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    unit: Mapped[str] = mapped_column(String(40), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    pickup_address: Mapped[str | None] = mapped_column(String(400), nullable=True)
    pickup_latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    pickup_longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    location_accuracy_m: Mapped[int | None] = mapped_column(Integer, nullable=True)
    location_source: Mapped[str | None] = mapped_column(String(40), nullable=True)
    location_provider: Mapped[str | None] = mapped_column(String(40), nullable=True)
    mappls_pin: Mapped[str | None] = mapped_column(String(12), nullable=True)
    provider_place_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    geocode_precision: Mapped[str | None] = mapped_column(String(40), nullable=True)
    location_captured_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    location_confirmed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pickup_landmark: Mapped[str | None] = mapped_column(String(240), nullable=True)
    pickup_pincode: Mapped[str | None] = mapped_column(String(6), nullable=True)
    food_source: Mapped[str | None] = mapped_column(String(40), nullable=True)
    packaging_state: Mapped[str | None] = mapped_column(String(40), nullable=True)
    diet_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    urgency: Mapped[str | None] = mapped_column(String(20), nullable=True)
    priority_score: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    priority_class: Mapped[str | None] = mapped_column(String(8), nullable=True)
    dispatch_status: Mapped[str | None] = mapped_column(String(24), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    prepared_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pickup_deadline: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    distribution_deadline: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expired_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verification_code_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    cluster_window: Mapped[str | None] = mapped_column(String(80), nullable=True)
    cluster_sector: Mapped[str | None] = mapped_column(String(40), nullable=True)
    preferred_centre_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("donation_centres.id", ondelete="SET NULL"),
        nullable=True,
    )
    preferred_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    proposed_centre_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("donation_centres.id", ondelete="SET NULL"),
        nullable=True,
    )
    proposal_reason: Mapped[str | None] = mapped_column(String(80), nullable=True)
    destination_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("destinations.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    donor = relationship("User")
    items = relationship("DonationItem", back_populates="donation", cascade="all, delete-orphan")
    photos = relationship("DonationPhoto", back_populates="donation", cascade="all, delete-orphan")
    quality_checks = relationship(
        "DonationQualityCheck", back_populates="donation", cascade="all, delete-orphan"
    )
    status_history = relationship(
        "DonationStatusHistory", back_populates="donation", cascade="all, delete-orphan"
    )
    commercial_details = relationship(
        "CommercialDonationDetails",
        back_populates="donation",
        uselist=False,
        cascade="all, delete-orphan",
    )


class DonationItem(Base):
    __tablename__ = "donation_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    donation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("donations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    unit: Mapped[str] = mapped_column(String(40), nullable=False)
    condition: Mapped[str | None] = mapped_column(String(40), nullable=True)

    donation = relationship("Donation", back_populates="items")


class DonationPhoto(Base):
    __tablename__ = "donation_photos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    donation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("donations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(80), nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    donation = relationship("Donation", back_populates="photos")


class DonationQualityCheck(Base):
    __tablename__ = "donation_quality_checks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    donation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("donations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    checked_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    stage: Mapped[QualityStage] = mapped_column(
        Enum(QualityStage, name="quality_stage"),
        nullable=False,
    )
    result: Mapped[QualityResult] = mapped_column(
        Enum(QualityResult, name="quality_result"),
        default=QualityResult.PENDING,
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    checklist_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    responses: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    photo_ids: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    donation = relationship("Donation", back_populates="quality_checks")


class DonationStatusHistory(Base):
    __tablename__ = "donation_status_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    donation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("donations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_status: Mapped[DonationStatus | None] = mapped_column(
        Enum(DonationStatus, name="donation_status"),
        nullable=True,
    )
    to_status: Mapped[DonationStatus] = mapped_column(
        Enum(DonationStatus, name="donation_status"),
        nullable=False,
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    donation = relationship("Donation", back_populates="status_history")


class CommercialDonationDetails(Base):
    __tablename__ = "commercial_donation_details"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    donation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("donations.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    event_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    estimated_servings: Mapped[int | None] = mapped_column(Integer, nullable=True)
    packaging_state: Mapped[str | None] = mapped_column(String(80), nullable=True)
    pickup_window_start: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pickup_window_end: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    donation = relationship("Donation", back_populates="commercial_details")
