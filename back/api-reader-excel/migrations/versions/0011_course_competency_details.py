"""Courses belong to one of the 4 common competencies and carry a description
and a methodology.

Upgrade adds ``competency`` (``lectura_critica``, ``competencias_ciudadanas``,
``razonamiento_cuantitativo`` or ``ingles``), ``description`` and
``methodology`` to ``courses``. Existing rows get ``lectura_critica`` and empty
texts. The unique name is now per level and competency, so each level can
have a course with the same name for every subject.

Downgrade drops the columns and restores the unique name per level.
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011_course_details"
down_revision: str | None = "0010_soft_delete_audit"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_COMPETENCIES = (
    "'lectura_critica', 'competencias_ciudadanas', "
    "'razonamiento_cuantitativo', 'ingles'"
)

_courses = sa.table(
    "courses",
    sa.column("competency", sa.String),
    sa.column("description", sa.Text),
    sa.column("methodology", sa.Text),
)


def upgrade() -> None:
    with op.batch_alter_table("courses") as batch:
        batch.add_column(sa.Column("competency", sa.String(length=40), nullable=True))
        batch.add_column(sa.Column("description", sa.Text(), nullable=True))
        batch.add_column(sa.Column("methodology", sa.Text(), nullable=True))
    op.get_bind().execute(
        _courses.update().values(
            competency="lectura_critica", description="", methodology=""
        )
    )
    with op.batch_alter_table("courses") as batch:
        batch.alter_column(
            "competency", existing_type=sa.String(length=40), nullable=False
        )
        batch.alter_column("description", existing_type=sa.Text(), nullable=False)
        batch.alter_column("methodology", existing_type=sa.Text(), nullable=False)
        batch.create_check_constraint(
            "ck_courses_competency", f"competency IN ({_COMPETENCIES})"
        )
        batch.drop_constraint("uq_courses_level_name", type_="unique")
        batch.create_unique_constraint(
            "uq_courses_level_competency_name", ["level", "competency", "name_key"]
        )


def downgrade() -> None:
    with op.batch_alter_table("courses") as batch:
        batch.drop_constraint("uq_courses_level_competency_name", type_="unique")
        batch.create_unique_constraint("uq_courses_level_name", ["level", "name_key"])
        batch.drop_constraint("ck_courses_competency", type_="check")
        batch.drop_column("methodology")
        batch.drop_column("description")
        batch.drop_column("competency")
