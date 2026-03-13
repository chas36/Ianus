"""add api_keys table

Revision ID: 20260313_0004
Revises: 20260313_0003
Create Date: 2026-03-13 12:30:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260313_0004"
down_revision: str | None = "20260313_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "api_keys",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )
    op.create_index(op.f("ix_api_keys_key"), "api_keys", ["key"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_api_keys_key"), table_name="api_keys")
    op.drop_table("api_keys")
