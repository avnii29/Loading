"""009 centre provenance and destination preference

Revision ID: c1e5f2a34b56
Revises: b9c3e0a12d34
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c1e5f2a34b56"
down_revision: Union[str, Sequence[str], None] = "b9c3e0a12d34"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("donation_centres", sa.Column("source_sheet", sa.String(80), nullable=True))
    op.add_column("donation_centres", sa.Column("source_row", sa.Integer(), nullable=True))
    op.add_column("donation_centres", sa.Column("source_key", sa.String(320), nullable=True))
    op.add_column(
        "donation_centres",
        sa.Column("geocode_status", sa.String(40), nullable=False, server_default="unresolved"),
    )
    op.add_column(
        "donation_centres",
        sa.Column("operational_status", sa.String(40), nullable=False, server_default="research_imported"),
    )
    op.create_index("ix_donation_centres_source_key", "donation_centres", ["source_key"], unique=True)
    op.add_column("donations", sa.Column("preferred_centre_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("donations", sa.Column("preferred_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("donations", sa.Column("proposed_centre_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("donations", sa.Column("proposal_reason", sa.String(80), nullable=True))
    op.create_foreign_key(
        "fk_donations_preferred_centre",
        "donations",
        "donation_centres",
        ["preferred_centre_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_donations_proposed_centre",
        "donations",
        "donation_centres",
        ["proposed_centre_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_donations_proposed_centre", "donations", type_="foreignkey")
    op.drop_constraint("fk_donations_preferred_centre", "donations", type_="foreignkey")
    op.drop_column("donations", "proposal_reason")
    op.drop_column("donations", "proposed_centre_id")
    op.drop_column("donations", "preferred_at")
    op.drop_column("donations", "preferred_centre_id")
    op.drop_index("ix_donation_centres_source_key", table_name="donation_centres")
    op.drop_column("donation_centres", "operational_status")
    op.drop_column("donation_centres", "geocode_status")
    op.drop_column("donation_centres", "source_key")
    op.drop_column("donation_centres", "source_row")
    op.drop_column("donation_centres", "source_sheet")
