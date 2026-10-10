"""003 mappls location metadata

Revision ID: c4d8f02b3e25
Revises: b7c3e91a2d14
Create Date: 2026-09-25 18:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c4d8f02b3e25"
down_revision: Union[str, Sequence[str], None] = "b7c3e91a2d14"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("donations", sa.Column("location_provider", sa.String(length=40), nullable=True))
    op.add_column("donations", sa.Column("mappls_pin", sa.String(length=12), nullable=True))
    op.add_column("donations", sa.Column("provider_place_id", sa.String(length=64), nullable=True))
    op.add_column("donations", sa.Column("geocode_precision", sa.String(length=40), nullable=True))

    op.add_column("organizations", sa.Column("location_provider", sa.String(length=40), nullable=True))
    op.add_column("organizations", sa.Column("mappls_pin", sa.String(length=12), nullable=True))
    op.add_column("organizations", sa.Column("provider_place_id", sa.String(length=64), nullable=True))

    op.add_column("destinations", sa.Column("location_provider", sa.String(length=40), nullable=True))
    op.add_column("destinations", sa.Column("mappls_pin", sa.String(length=12), nullable=True))
    op.add_column("destinations", sa.Column("provider_place_id", sa.String(length=64), nullable=True))

    op.add_column("recovery_partners", sa.Column("location_provider", sa.String(length=40), nullable=True))
    op.add_column("recovery_partners", sa.Column("mappls_pin", sa.String(length=12), nullable=True))

    op.add_column("matches", sa.Column("geo_provider", sa.String(length=40), nullable=True))
    op.add_column("matches", sa.Column("geo_distance_m", sa.Numeric(12, 2), nullable=True))
    op.add_column("matches", sa.Column("geo_duration_s", sa.Numeric(12, 2), nullable=True))
    op.add_column("matches", sa.Column("geo_calculated_at", sa.DateTime(timezone=True), nullable=True))

    op.add_column("logistics_assignments", sa.Column("route_provider", sa.String(length=40), nullable=True))
    op.add_column("logistics_assignments", sa.Column("route_distance_m", sa.Numeric(12, 2), nullable=True))
    op.add_column("logistics_assignments", sa.Column("route_duration_s", sa.Numeric(12, 2), nullable=True))
    op.add_column("logistics_assignments", sa.Column("route_generated_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("logistics_assignments", "route_generated_at")
    op.drop_column("logistics_assignments", "route_duration_s")
    op.drop_column("logistics_assignments", "route_distance_m")
    op.drop_column("logistics_assignments", "route_provider")
    op.drop_column("matches", "geo_calculated_at")
    op.drop_column("matches", "geo_duration_s")
    op.drop_column("matches", "geo_distance_m")
    op.drop_column("matches", "geo_provider")
    op.drop_column("recovery_partners", "mappls_pin")
    op.drop_column("recovery_partners", "location_provider")
    op.drop_column("destinations", "provider_place_id")
    op.drop_column("destinations", "mappls_pin")
    op.drop_column("destinations", "location_provider")
    op.drop_column("organizations", "provider_place_id")
    op.drop_column("organizations", "mappls_pin")
    op.drop_column("organizations", "location_provider")
    op.drop_column("donations", "geocode_precision")
    op.drop_column("donations", "provider_place_id")
    op.drop_column("donations", "mappls_pin")
    op.drop_column("donations", "location_provider")
