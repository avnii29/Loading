"""006 live location heading and speed

Revision ID: f7a1c8e90b12
Revises: e6f0b24d5a47
Create Date: 2026-10-10 00:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f7a1c8e90b12"
down_revision: Union[str, Sequence[str], None] = "e6f0b24d5a47"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("location_updates", sa.Column("heading_deg", sa.Numeric(6, 2), nullable=True))
    op.add_column("location_updates", sa.Column("speed_mps", sa.Numeric(8, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("location_updates", "speed_mps")
    op.drop_column("location_updates", "heading_deg")
