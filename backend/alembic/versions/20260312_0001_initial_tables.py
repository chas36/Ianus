"""initial tables

Revision ID: 20260312_0001
Revises:
Create Date: 2026-03-12 22:55:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260312_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "imports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("source_format", sa.String(length=50), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "subjects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("asc_id", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("short_name", sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asc_id"),
    )
    op.create_index(op.f("ix_subjects_asc_id"), "subjects", ["asc_id"], unique=True)

    op.create_table(
        "teachers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("asc_id", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("short_name", sa.String(length=100), nullable=False),
        sa.Column("color", sa.String(length=10), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asc_id"),
    )
    op.create_index(op.f("ix_teachers_asc_id"), "teachers", ["asc_id"], unique=True)

    op.create_table(
        "classes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("asc_id", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("short_name", sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asc_id"),
    )
    op.create_index(op.f("ix_classes_asc_id"), "classes", ["asc_id"], unique=True)

    op.create_table(
        "rooms",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("asc_id", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("short_name", sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asc_id"),
    )
    op.create_index(op.f("ix_rooms_asc_id"), "rooms", ["asc_id"], unique=True)

    op.create_table(
        "lessons",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("asc_id", sa.String(length=20), nullable=False),
        sa.Column("subject_id", sa.Integer(), nullable=False),
        sa.Column("teacher_id", sa.Integer(), nullable=True),
        sa.Column("class_id", sa.Integer(), nullable=False),
        sa.Column("group_name", sa.String(length=100), nullable=True),
        sa.Column("periods_per_week", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["class_id"], ["classes.id"]),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"]),
        sa.ForeignKeyConstraint(["teacher_id"], ["teachers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asc_id"),
    )
    op.create_index(op.f("ix_lessons_asc_id"), "lessons", ["asc_id"], unique=True)

    op.create_table(
        "cards",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("lesson_id", sa.Integer(), nullable=False),
        sa.Column("room_id", sa.Integer(), nullable=True),
        sa.Column("day", sa.Integer(), nullable=False),
        sa.Column("period", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"]),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("cards")
    op.drop_index(op.f("ix_lessons_asc_id"), table_name="lessons")
    op.drop_table("lessons")
    op.drop_index(op.f("ix_rooms_asc_id"), table_name="rooms")
    op.drop_table("rooms")
    op.drop_index(op.f("ix_classes_asc_id"), table_name="classes")
    op.drop_table("classes")
    op.drop_index(op.f("ix_teachers_asc_id"), table_name="teachers")
    op.drop_table("teachers")
    op.drop_index(op.f("ix_subjects_asc_id"), table_name="subjects")
    op.drop_table("subjects")
    op.drop_table("imports")
