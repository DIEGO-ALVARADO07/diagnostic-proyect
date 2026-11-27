"""CORHUILA matched against the enrollment file (phase 14b).

Upgrade adds ``academic_students.document_type`` (taken from the enrollment
file) and creates ``academic_result_programs``: the extra programs of a
CORHUILA row whose student is enrolled in two programs, so the same result
counts in both. Downgrade drops both.
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013_enrollment_matching"
down_revision: str | None = "0012_enrollment_records"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("academic_students") as batch:
        batch.add_column(sa.Column("document_type", sa.String(length=10), nullable=True))
    op.create_table(
        "academic_result_programs",
        sa.Column("result_id", sa.Integer(), nullable=False),
        sa.Column("program_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["result_id"], ["academic_results.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["program_id"], ["academic_programs.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("result_id", "program_id"),
    )


def downgrade() -> None:
    op.drop_table("academic_result_programs")
    with op.batch_alter_table("academic_students") as batch:
        batch.drop_column("document_type")
