"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-09-17

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ghosts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("anxiety_level", sa.Integer(), nullable=False),
        sa.Column("favorite_temperature", sa.Float(), nullable=False),
        sa.Column("relocation_deadline", sa.Date(), nullable=False),
        sa.Column("special_conditions", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "locations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("location_type", sa.String(length=100), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("occupied", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lighting", sa.String(length=20), nullable=False),
        sa.Column("noise_level", sa.Integer(), nullable=False),
        sa.Column("humidity", sa.String(length=20), nullable=False),
        sa.Column("ambient_temperature", sa.Float(), nullable=False),
        sa.Column("has_people", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("has_mirrors", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("has_attic", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("restrictions", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ghost_id", sa.Integer(), sa.ForeignKey("ghosts.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("location_id", sa.Integer(), sa.ForeignKey("locations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("explanation", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("manual", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("warnings", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("assignments")
    op.drop_table("locations")
    op.drop_table("ghosts")
