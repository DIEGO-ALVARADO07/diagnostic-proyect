"""Courses by level and their enrollments (phase 13b).

Upgrade creates ``courses`` (name, level 1–4) and ``course_enrollments``
(one row per student and course, with the level and period it was enrolled
from). Downgrade drops both tables.
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_courses"
down_revision: str | None = "0008_manual_program"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "courses",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("name_key", sa.String(length=150), nullable=False),
        sa.Column("level", sa.SmallInteger(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("level BETWEEN 1 AND 4", name="ck_courses_level"),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["api_users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("level", "name_key", name="uq_courses_level_name"),
    )
    op.create_table(
        "course_enrollments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("level", sa.SmallInteger(), nullable=True),
        sa.Column("period", sa.String(length=7), nullable=True),
        sa.Column("enrolled_by_user_id", sa.Integer(), nullable=True),
        sa.Column("enrolled_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["student_id"], ["academic_students.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["enrolled_by_user_id"], ["api_users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "course_id", "student_id", name="uq_course_enrollments_student"
        ),
    )
    op.create_index(
        "ix_course_enrollments_student_id", "course_enrollments", ["student_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_course_enrollments_student_id", table_name="course_enrollments")
    op.drop_table("course_enrollments")
    op.drop_table("courses")
