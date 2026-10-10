"""007 points entries

Revision ID: a8b2d9f01c23
Revises: f7a1c8e90b12
Create Date: 2026-10-10 02:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "a8b2d9f01c23"
down_revision: Union[str, Sequence[str], None] = "f7a1c8e90b12"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "points_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("donation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("donations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(160), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("donation_id"),
    )
    op.create_index("ix_points_entries_user_id", "points_entries", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_points_entries_user_id", table_name="points_entries")
    op.drop_table("points_entries")
