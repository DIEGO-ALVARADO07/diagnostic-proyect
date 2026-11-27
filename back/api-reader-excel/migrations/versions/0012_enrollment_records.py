"""Enrollment file per period ("matriculados", phase 14a).

Upgrade creates ``enrollment_uploads`` (one upload per period is ACTIVE; older
ones are REPLACED and keep only their audit data) and ``enrollment_records``
(one row per student and program, with every column of the file). Downgrade
drops both tables.
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_enrollment_records"
down_revision: str | None = "0011_course_details"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "enrollment_uploads",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("period", sa.String(length=7), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("file_sha256", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("student_count", sa.Integer(), nullable=False),
        sa.Column("rejected_count", sa.Integer(), nullable=False),
        sa.Column("duplicate_count", sa.Integer(), nullable=False),
        sa.Column("uploaded_by_user_id", sa.Integer(), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False),
        sa.Column("replaced_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'REPLACED')", name="ck_enrollment_uploads_status"
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by_user_id"], ["api_users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_enrollment_uploads_period_status",
        "enrollment_uploads",
        ["period", "status"],
    )
    op.create_table(
        "enrollment_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("upload_id", sa.String(length=36), nullable=False),
        sa.Column("period", sa.String(length=7), nullable=False),
        sa.Column("source_row_number", sa.Integer(), nullable=False),
        sa.Column("pensum_code", sa.String(length=20), nullable=True),
        sa.Column("program_name", sa.String(length=255), nullable=False),
        sa.Column("program_key", sa.String(length=255), nullable=False),
        sa.Column("semester", sa.SmallInteger(), nullable=True),
        sa.Column("document_type", sa.String(length=10), nullable=True),
        sa.Column("document_number", sa.String(length=40), nullable=False),
        sa.Column("document_key", sa.String(length=64), nullable=False),
        sa.Column("student_code", sa.String(length=40), nullable=True),
        sa.Column("first_names", sa.String(length=200), nullable=True),
        sa.Column("last_names", sa.String(length=200), nullable=True),
        sa.Column("stratum", sa.SmallInteger(), nullable=True),
        sa.Column("gender", sa.String(length=10), nullable=True),
        sa.Column("birth_date", sa.Date(), nullable=True),
        sa.Column("phone", sa.String(length=40), nullable=True),
        sa.Column("mobile", sa.String(length=40), nullable=True),
        sa.Column("personal_email", sa.String(length=320), nullable=True),
        sa.Column("personal_email_key", sa.String(length=320), nullable=True),
        sa.Column("institutional_email", sa.String(length=320), nullable=True),
        sa.Column("institutional_email_key", sa.String(length=320), nullable=True),
        sa.Column("search_text", sa.String(length=1200), nullable=False),
        sa.ForeignKeyConstraint(
            ["upload_id"], ["enrollment_uploads.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "upload_id",
            "document_key",
            "program_key",
            name="uq_enrollment_records_student_program",
        ),
    )
    op.create_index(
        "ix_enrollment_records_period_program",
        "enrollment_records",
        ["period", "program_key"],
    )
    op.create_index(
        "ix_enrollment_records_document_key", "enrollment_records", ["document_key"]
    )
    op.create_index(
        "ix_enrollment_records_institutional_email",
        "enrollment_records",
        ["institutional_email_key"],
    )
    op.create_index(
        "ix_enrollment_records_personal_email",
        "enrollment_records",
        ["personal_email_key"],
    )


def downgrade() -> None:
    op.drop_index("ix_enrollment_records_personal_email", table_name="enrollment_records")
    op.drop_index(
        "ix_enrollment_records_institutional_email", table_name="enrollment_records"
    )
    op.drop_index("ix_enrollment_records_document_key", table_name="enrollment_records")
    op.drop_index("ix_enrollment_records_period_program", table_name="enrollment_records")
    op.drop_table("enrollment_records")
    op.drop_index("ix_enrollment_uploads_period_status", table_name="enrollment_uploads")
    op.drop_table("enrollment_uploads")
