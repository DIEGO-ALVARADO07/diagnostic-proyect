"""Soft delete with audit for courses, and restorable Excel imports.

Upgrade:
1. ``courses``: ``deleted_at``, ``deleted_by_user_id``, ``restored_at`` and
   ``restored_by_user_id``. Deleting a course only marks it; its enrollments
   stay, so it can be restored as it was.
2. ``excel_imports``: ``deleted_by_user_id``, ``restored_at`` and
   ``restored_by_user_id`` (``deleted_at`` already existed), so a deactivated
   import can be restored and the audit shows who did each step.

Downgrade drops the new columns.
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_soft_delete_audit"
down_revision: str | None = "0009_courses"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_COURSE_DELETED_FK = "fk_courses_deleted_by"
_COURSE_RESTORED_FK = "fk_courses_restored_by"
_IMPORT_DELETED_FK = "fk_excel_imports_deleted_by"
_IMPORT_RESTORED_FK = "fk_excel_imports_restored_by"


def upgrade() -> None:
    with op.batch_alter_table("courses") as batch:
        batch.add_column(sa.Column("deleted_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("deleted_by_user_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("restored_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("restored_by_user_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            _COURSE_DELETED_FK, "api_users", ["deleted_by_user_id"], ["id"],
            ondelete="SET NULL",
        )
        batch.create_foreign_key(
            _COURSE_RESTORED_FK, "api_users", ["restored_by_user_id"], ["id"],
            ondelete="SET NULL",
        )
    with op.batch_alter_table("excel_imports") as batch:
        batch.add_column(sa.Column("deleted_by_user_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("restored_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("restored_by_user_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            _IMPORT_DELETED_FK, "api_users", ["deleted_by_user_id"], ["id"],
            ondelete="SET NULL",
        )
        batch.create_foreign_key(
            _IMPORT_RESTORED_FK, "api_users", ["restored_by_user_id"], ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("excel_imports") as batch:
        batch.drop_constraint(_IMPORT_RESTORED_FK, type_="foreignkey")
        batch.drop_constraint(_IMPORT_DELETED_FK, type_="foreignkey")
        batch.drop_column("restored_by_user_id")
        batch.drop_column("restored_at")
        batch.drop_column("deleted_by_user_id")
    with op.batch_alter_table("courses") as batch:
        batch.drop_constraint(_COURSE_RESTORED_FK, type_="foreignkey")
        batch.drop_constraint(_COURSE_DELETED_FK, type_="foreignkey")
        batch.drop_column("restored_by_user_id")
        batch.drop_column("restored_at")
        batch.drop_column("deleted_by_user_id")
        batch.drop_column("deleted_at")
