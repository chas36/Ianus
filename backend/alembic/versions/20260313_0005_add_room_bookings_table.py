"""add room_bookings table

Revision ID: 20260313_0005
Revises: 20260313_0004
Create Date: 2026-03-13 14:05:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260313_0005"
down_revision: str | None = "20260313_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "room_bookings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("room_id", sa.Integer(), nullable=False),
        sa.Column("day", sa.Integer(), nullable=False),
        sa.Column("period", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("booked_by", sa.String(length=120), nullable=False),
        sa.Column("purpose", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_room_bookings_room_date_period",
        "room_bookings",
        ["room_id", "date", "period"],
        unique=True,
    )
    op.create_index(
        "ix_room_bookings_date_period",
        "room_bookings",
        ["date", "period"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_room_bookings_date_period", table_name="room_bookings")
    op.drop_index("ix_room_bookings_room_date_period", table_name="room_bookings")
    op.drop_table("room_bookings")
