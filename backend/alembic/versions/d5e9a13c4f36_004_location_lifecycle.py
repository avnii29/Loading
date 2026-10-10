"""004 location lifecycle timestamps and landmark

Revision ID: d5e9a13c4f36
Revises: c4d8f02b3e25
Create Date: 2026-10-09 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d5e9a13c4f36"
down_revision: Union[str, Sequence[str], None] = "c4d8f02b3e25"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "donations",
        "location_source",
        existing_type=sa.String(length=20),
        type_=sa.String(length=40),
        existing_nullable=True,
    )
    op.add_column("donations", sa.Column("location_captured_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("donations", sa.Column("location_confirmed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("donations", sa.Column("pickup_landmark", sa.String(length=240), nullable=True))


def downgrade() -> None:
    op.drop_column("donations", "pickup_landmark")
    op.drop_column("donations", "location_confirmed_at")
    op.drop_column("donations", "location_captured_at")
    op.alter_column(
        "donations",
        "location_source",
        existing_type=sa.String(length=40),
        type_=sa.String(length=20),
        existing_nullable=True,
    )
