"""005 dispatch queue, volunteer offers, handoff OTP, quality responses

Revision ID: e6f0b24d5a47
Revises: d5e9a13c4f36
Create Date: 2026-10-09 21:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "e6f0b24d5a47"
down_revision: Union[str, Sequence[str], None] = "d5e9a13c4f36"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE notification_type ADD VALUE IF NOT EXISTS 'VOLUNTEER_OFFER'")
    op.execute("ALTER TYPE notification_type ADD VALUE IF NOT EXISTS 'OFFER_EXPIRED'")
    op.execute("ALTER TYPE notification_type ADD VALUE IF NOT EXISTS 'DISPATCH_ESCALATION'")
    op.execute("ALTER TYPE notification_type ADD VALUE IF NOT EXISTS 'RECEIVING_REQUIRED'")
    op.execute("ALTER TYPE notification_type ADD VALUE IF NOT EXISTS 'SAFETY_HOLD'")

    op.add_column("donations", sa.Column("pickup_pincode", sa.String(length=6), nullable=True))
    op.add_column("donations", sa.Column("food_source", sa.String(length=40), nullable=True))
    op.add_column("donations", sa.Column("packaging_state", sa.String(length=40), nullable=True))
    op.add_column("donations", sa.Column("diet_type", sa.String(length=40), nullable=True))
    op.add_column("donations", sa.Column("urgency", sa.String(length=20), nullable=True))
    op.add_column("donations", sa.Column("priority_score", sa.Numeric(10, 3), nullable=True))
    op.add_column("donations", sa.Column("priority_class", sa.String(length=8), nullable=True))
    op.add_column("donations", sa.Column("dispatch_status", sa.String(length=24), nullable=True))
    op.add_column("donations", sa.Column("idempotency_key", sa.String(length=64), nullable=True))
    op.create_index("ix_donations_idempotency_key", "donations", ["idempotency_key"], unique=True)

    op.add_column(
        "donation_quality_checks",
        sa.Column("checklist_version", sa.String(length=40), nullable=True),
    )
    op.add_column(
        "donation_quality_checks",
        sa.Column("responses", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    op.create_table(
        "dispatch_queue_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("donation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("donations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("priority_score", sa.Numeric(10, 3), nullable=False),
        sa.Column("priority_class", sa.String(length=8), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="ACTIVE"),
        sa.Column("enqueued_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("donation_id", name="uq_dispatch_queue_donation"),
    )
    op.create_index("ix_dispatch_queue_status_score", "dispatch_queue_entries", ["status", "priority_score"])

    op.create_table(
        "volunteer_offers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("donation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("donations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("volunteer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="PENDING"),
        sa.Column("priority_class", sa.String(length=8), nullable=True),
        sa.Column("summary", sa.String(length=400), nullable=True),
        sa.Column("area_label", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assignment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("logistics_assignments.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_volunteer_offers_volunteer_status", "volunteer_offers", ["volunteer_id", "status"])
    op.create_index("ix_volunteer_offers_donation_status", "volunteer_offers", ["donation_id", "status"])

    op.create_table(
        "handoff_verifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("donation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("donations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stage", sa.String(length=24), nullable=False),
        sa.Column("code_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_handoff_donation_stage", "handoff_verifications", ["donation_id", "stage"])


def downgrade() -> None:
    op.drop_table("handoff_verifications")
    op.drop_table("volunteer_offers")
    op.drop_table("dispatch_queue_entries")
    op.drop_column("donation_quality_checks", "responses")
    op.drop_column("donation_quality_checks", "checklist_version")
    op.drop_index("ix_donations_idempotency_key", table_name="donations")
    for col in (
        "idempotency_key",
        "dispatch_status",
        "priority_class",
        "priority_score",
        "urgency",
        "diet_type",
        "packaging_state",
        "food_source",
        "pickup_pincode",
    ):
        op.drop_column("donations", col)
