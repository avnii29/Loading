"""008 donation centres directory

Revision ID: b9c3e0a12d34
Revises: a8b2d9f01c23
Create Date: 2026-10-10 02:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "b9c3e0a12d34"
down_revision: Union[str, Sequence[str], None] = "a8b2d9f01c23"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "donation_centres",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(240), nullable=False),
        sa.Column("facility_type", sa.String(160)),
        sa.Column("district", sa.String(160)),
        sa.Column("address", sa.String(400)),
        sa.Column("city", sa.String(120)),
        sa.Column("phone", sa.String(40)),
        sa.Column("provides", sa.Text()),
        sa.Column("capacity_notes", sa.Text()),
        sa.Column("donate_notes", sa.Text()),
        sa.Column("source_url", sa.Text()),
        sa.Column("caveat", sa.Text()),
        sa.Column("listing", sa.String(24), nullable=False),
        sa.Column("latitude", sa.Numeric(9, 6)),
        sa.Column("longitude", sa.Numeric(9, 6)),
        sa.Column("location_provider", sa.String(40)),
        sa.Column("approximate", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("accepted_categories", postgresql.JSONB()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("donation_centres")
