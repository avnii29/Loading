"""002 product core foundation

Revision ID: b7c3e91a2d14
Revises: 57d85c676060
Create Date: 2026-09-22 21:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "b7c3e91a2d14"
down_revision: Union[str, Sequence[str], None] = "57d85c676060"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _enum(name: str, *values: str, create_type: bool = True):
    return postgresql.ENUM(*values, name=name, create_type=create_type)


NEW_ENUMS = {
    "donation_stream": ("HUMAN_CONSUMPTION", "RECOVERY"),
    "donation_category": ("FOOD", "CLOTHES", "BOOKS", "TOYS", "ORGANIC_RECOVERY", "OTHER"),
    "donation_status": (
        "DRAFT",
        "SUBMITTED",
        "ASSESSING",
        "MATCHING",
        "MATCHED",
        "ASSIGNED",
        "PICKUP_PENDING",
        "IN_TRANSIT",
        "DELIVERED",
        "UNDER_REVIEW",
        "ACCEPTED",
        "REJECTED",
        "RECOVERY_PENDING",
        "RECOVERY_ASSIGNED",
        "RECOVERED",
        "COMPLETED",
        "CANCELLED",
        "EXPIRED",
    ),
    "quality_stage": ("DONOR_SELF", "PICKUP", "INTAKE", "RECOVERY", "REVIEW"),
    "quality_result": ("PENDING", "ACCEPTABLE", "REJECTED", "REQUIRES_REVIEW"),
    "intake_status": ("OPEN", "LIMITED", "CLOSED"),
    "assignment_status": ("OFFERED", "ACCEPTED", "DECLINED", "EN_ROUTE", "COMPLETED", "CANCELLED"),
    "match_status": ("PROPOSED", "CONFIRMED", "SUPERSEDED", "CANCELLED"),
    "notification_type": (
        "DONATION_SUBMITTED",
        "MATCH_CREATED",
        "ASSIGNMENT_ACCEPTED",
        "PICKUP_APPROACHING",
        "PICKED_UP",
        "DELIVERED",
        "ORGANISATION_ACCEPTED",
        "RECOVERY_REQUIRED",
        "COMPLETED",
        "STATUS_CHANGED",
    ),
    "impact_kind": ("MEALS_DISTRIBUTED", "ITEMS_DELIVERED", "KG_RECOVERED", "DONATION_COMPLETED"),
}


def upgrade() -> None:
    bind = op.get_bind()
    enums = {}
    for name, values in NEW_ENUMS.items():
        _enum(name, *values, create_type=True).create(bind, checkfirst=True)
        enums[name] = _enum(name, *values, create_type=False)

    op.add_column("organizations", sa.Column("address", sa.String(length=400), nullable=True))
    op.add_column("organizations", sa.Column("city", sa.String(length=120), nullable=True))
    op.add_column("organizations", sa.Column("pincode", sa.String(length=12), nullable=True))
    op.add_column("organizations", sa.Column("latitude", sa.Numeric(9, 6), nullable=True))
    op.add_column("organizations", sa.Column("longitude", sa.Numeric(9, 6), nullable=True))
    op.add_column("organizations", sa.Column("accepted_categories", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column(
        "organizations",
        sa.Column("intake_status", enums["intake_status"], server_default="OPEN", nullable=False),
    )
    op.add_column("organizations", sa.Column("capacity_notes", sa.Text(), nullable=True))
    op.add_column("organizations", sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.add_column(
        "organizations",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "destinations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("address", sa.String(length=400), nullable=True),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column("pincode", sa.String(length=12), nullable=True),
        sa.Column("latitude", sa.Numeric(9, 6), nullable=True),
        sa.Column("longitude", sa.Numeric(9, 6), nullable=True),
        sa.Column("accepted_categories", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_destinations_organization_id"), "destinations", ["organization_id"], unique=False)

    op.create_table(
        "recovery_partners",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("verification_status", postgresql.ENUM(name="verification_status", create_type=False), nullable=False),
        sa.Column("partner_types", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("address", sa.String(length=400), nullable=True),
        sa.Column("latitude", sa.Numeric(9, 6), nullable=True),
        sa.Column("longitude", sa.Numeric(9, 6), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    op.create_table(
        "donations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("reference_code", sa.String(length=20), nullable=False),
        sa.Column("donor_id", sa.UUID(), nullable=False),
        sa.Column("stream", enums["donation_stream"], nullable=False),
        sa.Column("category", enums["donation_category"], nullable=False),
        sa.Column("status", enums["donation_status"], nullable=False),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("quantity", sa.Numeric(10, 2), nullable=False),
        sa.Column("unit", sa.String(length=40), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("pickup_address", sa.String(length=400), nullable=True),
        sa.Column("pickup_latitude", sa.Numeric(9, 6), nullable=True),
        sa.Column("pickup_longitude", sa.Numeric(9, 6), nullable=True),
        sa.Column("location_accuracy_m", sa.Integer(), nullable=True),
        sa.Column("location_source", sa.String(length=20), nullable=True),
        sa.Column("prepared_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pickup_deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("distribution_deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verification_code_hash", sa.String(length=128), nullable=True),
        sa.Column("cluster_window", sa.String(length=80), nullable=True),
        sa.Column("cluster_sector", sa.String(length=40), nullable=True),
        sa.Column("destination_id", sa.UUID(), nullable=True),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["destination_id"], ["destinations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["donor_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_donations_reference_code"), "donations", ["reference_code"], unique=True)
    op.create_index(op.f("ix_donations_donor_id"), "donations", ["donor_id"], unique=False)
    op.create_index(op.f("ix_donations_category"), "donations", ["category"], unique=False)
    op.create_index(op.f("ix_donations_status"), "donations", ["status"], unique=False)

    op.create_table(
        "donation_items",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("donation_id", sa.UUID(), nullable=False),
        sa.Column("label", sa.String(length=200), nullable=False),
        sa.Column("quantity", sa.Numeric(10, 2), nullable=False),
        sa.Column("unit", sa.String(length=40), nullable=False),
        sa.Column("condition", sa.String(length=40), nullable=True),
        sa.ForeignKeyConstraint(["donation_id"], ["donations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_donation_items_donation_id"), "donation_items", ["donation_id"], unique=False)

    op.create_table(
        "donation_photos",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("donation_id", sa.UUID(), nullable=False),
        sa.Column("storage_key", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=80), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["donation_id"], ["donations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_donation_photos_donation_id"), "donation_photos", ["donation_id"], unique=False)

    op.create_table(
        "donation_quality_checks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("donation_id", sa.UUID(), nullable=False),
        sa.Column("checked_by", sa.UUID(), nullable=True),
        sa.Column("stage", enums["quality_stage"], nullable=False),
        sa.Column("result", enums["quality_result"], nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("photo_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["checked_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["donation_id"], ["donations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_donation_quality_checks_donation_id"), "donation_quality_checks", ["donation_id"], unique=False)

    op.create_table(
        "donation_status_history",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("donation_id", sa.UUID(), nullable=False),
        sa.Column("from_status", enums["donation_status"], nullable=True),
        sa.Column("to_status", enums["donation_status"], nullable=False),
        sa.Column("actor_id", sa.UUID(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["donation_id"], ["donations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_donation_status_history_donation_id"), "donation_status_history", ["donation_id"], unique=False)

    op.create_table(
        "commercial_donation_details",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("donation_id", sa.UUID(), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=True),
        sa.Column("estimated_servings", sa.Integer(), nullable=True),
        sa.Column("packaging_state", sa.String(length=80), nullable=True),
        sa.Column("pickup_window_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pickup_window_end", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["donation_id"], ["donations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("donation_id"),
    )

    op.create_table(
        "matches",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("donation_id", sa.UUID(), nullable=False),
        sa.Column("destination_id", sa.UUID(), nullable=True),
        sa.Column("status", enums["match_status"], nullable=False),
        sa.Column("score", sa.Numeric(8, 3), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["destination_id"], ["destinations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["donation_id"], ["donations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_matches_donation_id"), "matches", ["donation_id"], unique=False)

    op.create_table(
        "logistics_assignments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("donation_id", sa.UUID(), nullable=False),
        sa.Column("assignee_id", sa.UUID(), nullable=False),
        sa.Column("status", enums["assignment_status"], nullable=False),
        sa.Column("cluster_key", sa.String(length=80), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["assignee_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["donation_id"], ["donations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_logistics_assignments_donation_id"), "logistics_assignments", ["donation_id"], unique=False)
    op.create_index(op.f("ix_logistics_assignments_assignee_id"), "logistics_assignments", ["assignee_id"], unique=False)

    op.create_table(
        "location_updates",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("assignment_id", sa.UUID(), nullable=False),
        sa.Column("latitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("longitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("accuracy_m", sa.Integer(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["assignment_id"], ["logistics_assignments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_location_updates_assignment_id"), "location_updates", ["assignment_id"], unique=False)

    op.create_table(
        "recovery_routes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("donation_id", sa.UUID(), nullable=False),
        sa.Column("partner_id", sa.UUID(), nullable=True),
        sa.Column("stream", enums["donation_stream"], nullable=False),
        sa.Column("lane", sa.String(length=80), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["donation_id"], ["donations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["partner_id"], ["recovery_partners.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_recovery_routes_donation_id"), "recovery_routes", ["donation_id"], unique=False)

    op.create_table(
        "organization_intake_checks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("donation_id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("checked_by", sa.UUID(), nullable=True),
        sa.Column("accepted", sa.Boolean(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["checked_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["donation_id"], ["donations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_organization_intake_checks_donation_id"), "organization_intake_checks", ["donation_id"], unique=False)

    op.create_table(
        "payment_intents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("donation_id", sa.UUID(), nullable=True),
        sa.Column("organization_id", sa.UUID(), nullable=True),
        sa.Column("amount_paise", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("provider_ref", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["donation_id"], ["donations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "capacity_reservations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("destination_id", sa.UUID(), nullable=False),
        sa.Column("donation_id", sa.UUID(), nullable=True),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("quantity", sa.Numeric(10, 2), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("extra", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["destination_id"], ["destinations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["donation_id"], ["donations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_capacity_reservations_destination_id"), "capacity_reservations", ["destination_id"], unique=False)

    op.create_table(
        "notifications",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("type", enums["notification_type"], nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.String(length=60), nullable=True),
        sa.Column("entity_id", sa.UUID(), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notifications_user_id"), "notifications", ["user_id"], unique=False)

    op.create_table(
        "impact_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("donation_id", sa.UUID(), nullable=True),
        sa.Column("kind", enums["impact_kind"], nullable=False),
        sa.Column("quantity", sa.Numeric(12, 2), nullable=False),
        sa.Column("unit", sa.String(length=40), nullable=False),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["donation_id"], ["donations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_impact_events_donation_id"), "impact_events", ["donation_id"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("actor_id", sa.UUID(), nullable=True),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("entity_type", sa.String(length=60), nullable=False),
        sa.Column("entity_id", sa.UUID(), nullable=True),
        sa.Column("extra", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_logs_actor_id"), "audit_logs", ["actor_id"], unique=False)
    op.create_index(op.f("ix_audit_logs_action"), "audit_logs", ["action"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_logs_action"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_actor_id"), table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index(op.f("ix_impact_events_donation_id"), table_name="impact_events")
    op.drop_table("impact_events")
    op.drop_index(op.f("ix_notifications_user_id"), table_name="notifications")
    op.drop_table("notifications")
    op.drop_index(op.f("ix_capacity_reservations_destination_id"), table_name="capacity_reservations")
    op.drop_table("capacity_reservations")
    op.drop_table("payment_intents")
    op.drop_index(op.f("ix_organization_intake_checks_donation_id"), table_name="organization_intake_checks")
    op.drop_table("organization_intake_checks")
    op.drop_index(op.f("ix_recovery_routes_donation_id"), table_name="recovery_routes")
    op.drop_table("recovery_routes")
    op.drop_index(op.f("ix_location_updates_assignment_id"), table_name="location_updates")
    op.drop_table("location_updates")
    op.drop_index(op.f("ix_logistics_assignments_assignee_id"), table_name="logistics_assignments")
    op.drop_index(op.f("ix_logistics_assignments_donation_id"), table_name="logistics_assignments")
    op.drop_table("logistics_assignments")
    op.drop_index(op.f("ix_matches_donation_id"), table_name="matches")
    op.drop_table("matches")
    op.drop_table("commercial_donation_details")
    op.drop_index(op.f("ix_donation_status_history_donation_id"), table_name="donation_status_history")
    op.drop_table("donation_status_history")
    op.drop_index(op.f("ix_donation_quality_checks_donation_id"), table_name="donation_quality_checks")
    op.drop_table("donation_quality_checks")
    op.drop_index(op.f("ix_donation_photos_donation_id"), table_name="donation_photos")
    op.drop_table("donation_photos")
    op.drop_index(op.f("ix_donation_items_donation_id"), table_name="donation_items")
    op.drop_table("donation_items")
    op.drop_index(op.f("ix_donations_status"), table_name="donations")
    op.drop_index(op.f("ix_donations_category"), table_name="donations")
    op.drop_index(op.f("ix_donations_donor_id"), table_name="donations")
    op.drop_index(op.f("ix_donations_reference_code"), table_name="donations")
    op.drop_table("donations")
    op.drop_table("recovery_partners")
    op.drop_index(op.f("ix_destinations_organization_id"), table_name="destinations")
    op.drop_table("destinations")

    op.drop_column("organizations", "updated_at")
    op.drop_column("organizations", "is_demo")
    op.drop_column("organizations", "capacity_notes")
    op.drop_column("organizations", "intake_status")
    op.drop_column("organizations", "accepted_categories")
    op.drop_column("organizations", "longitude")
    op.drop_column("organizations", "latitude")
    op.drop_column("organizations", "pincode")
    op.drop_column("organizations", "city")
    op.drop_column("organizations", "address")

    bind = op.get_bind()
    for name, values in NEW_ENUMS.items():
        _enum(name, *values).drop(bind, checkfirst=True)
