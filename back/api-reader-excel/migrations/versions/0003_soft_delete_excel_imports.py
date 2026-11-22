"""Add soft deletion metadata to Excel imports."""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0003_soft_delete_excel_imports"
down_revision: str | None = "0002_academic_dashboard"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "excel_imports",
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("excel_imports", "deleted_at")
