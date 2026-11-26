"""Manual program assignment for students; program taken from the whole ESE history.

Upgrade:
1. ``academic_students``: ``assigned_program_id`` (manual program, wins over
   ESE), ``assigned_program_by_user_id`` and ``assigned_program_at``.
2. ``academic_results.program_resolution``: ``ESE_M2`` becomes ``ESE``. The
   program now comes from the latest ESE row of any moment; run
   ``POST /excel/dashboard/corhuila/resolve`` (or import ESE) to recalculate it.

Downgrade drops the columns and turns ``ESE``/``MANUAL`` back into
``ESE_M2``/``SIN_PROGRAMA``.
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_manual_program"
down_revision: str | None = "0007_document_identity"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_PROGRAM_FK = "fk_academic_students_assigned_program"
_USER_FK = "fk_academic_students_assigned_program_by"

_results = sa.table(
    "academic_results",
    sa.column("program_resolution", sa.String),
    sa.column("program_id", sa.Integer),
)


def upgrade() -> None:
    with op.batch_alter_table("academic_students") as batch:
        batch.add_column(sa.Column("assigned_program_id", sa.Integer(), nullable=True))
        batch.add_column(
            sa.Column("assigned_program_by_user_id", sa.Integer(), nullable=True)
        )
        batch.add_column(sa.Column("assigned_program_at", sa.DateTime(), nullable=True))
        batch.create_foreign_key(
            _PROGRAM_FK,
            "academic_programs",
            ["assigned_program_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch.create_foreign_key(
            _USER_FK,
            "api_users",
            ["assigned_program_by_user_id"],
            ["id"],
            ondelete="SET NULL",
        )
    op.get_bind().execute(
        _results.update()
        .where(_results.c.program_resolution == "ESE_M2")
        .values(program_resolution="ESE")
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        _results.update()
        .where(_results.c.program_resolution == "ESE")
        .values(program_resolution="ESE_M2")
    )
    bind.execute(
        _results.update()
        .where(_results.c.program_resolution == "MANUAL")
        .values(program_resolution="SIN_PROGRAMA", program_id=None)
    )
    with op.batch_alter_table("academic_students") as batch:
        batch.drop_constraint(_USER_FK, type_="foreignkey")
        batch.drop_constraint(_PROGRAM_FK, type_="foreignkey")
        batch.drop_column("assigned_program_at")
        batch.drop_column("assigned_program_by_user_id")
        batch.drop_column("assigned_program_id")
