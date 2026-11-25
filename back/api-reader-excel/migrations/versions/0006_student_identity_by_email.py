"""Identify students by institutional email; store CORHUILA program resolution.

Upgrade:
1. ``academic_students.email_key`` (lower-case email without spaces), unique.
   ``document_key`` and ``document_number`` become optional: CORHUILA files
   almost never have a document.
2. Students that share an ``email_key`` are merged into the one with the lowest
   id; their results point to it. No result is deleted or changed otherwise.
   The survivor keeps its document; if it had none, it takes the first one
   found among the merged students.
3. ``academic_results.email_key`` (filled from ``email_source``) and an index
   ``(import_id, email_key, moment)`` to find ESE Momento 2 rows by email.
4. ``academic_results.program_resolution``, ``program_resolved_import_id`` and
   ``program_resolved_period``: where the program of a CORHUILA row came from.

Downgrade drops the new columns and makes documents required again (students
without a document are deleted first; their results keep ``student_id`` NULL).
Merged students are NOT split again.
"""

from collections import defaultdict
from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_student_identity_by_email"
down_revision: str | None = "0005_sources_periods_moments"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_STUDENTS_INDEX = "ix_academic_students_email_key"
_RESULTS_INDEX = "ix_academic_results_import_email_moment"
_RESOLVED_FK = "fk_academic_results_program_resolved_import"
_BATCH_SIZE = 1000

_students = sa.table(
    "academic_students",
    sa.column("id", sa.Integer),
    sa.column("email", sa.String),
    sa.column("email_key", sa.String),
    sa.column("document_key", sa.String),
    sa.column("document_number", sa.String),
)
_results = sa.table(
    "academic_results",
    sa.column("id", sa.Integer),
    sa.column("student_id", sa.Integer),
    sa.column("email_source", sa.String),
    sa.column("email_key", sa.String),
)


def _email_key(value: str | None) -> str | None:
    # Copia de dashboard_normalizer.email_key (sin depender del código de la app).
    if value is None:
        return None
    key = "".join(str(value).split()).casefold()
    return key if "@" in key else None


def _batched_update(bind, statement, rows: list[dict]) -> None:
    for offset in range(0, len(rows), _BATCH_SIZE):
        bind.execute(statement, rows[offset : offset + _BATCH_SIZE])


def upgrade() -> None:
    bind = op.get_bind()

    with op.batch_alter_table("academic_students") as batch:
        batch.add_column(
            sa.Column("email_key", sa.String(length=320), nullable=True)
        )
        batch.alter_column(
            "document_key", existing_type=sa.String(length=64), nullable=True
        )
        batch.alter_column(
            "document_number", existing_type=sa.String(length=80), nullable=True
        )

    # Unir estudiantes con el mismo correo.
    students = bind.execute(
        sa.select(
            _students.c.id,
            _students.c.email,
            _students.c.document_key,
            _students.c.document_number,
        ).order_by(_students.c.id)
    ).all()
    by_email: dict[str, list[tuple[int, str | None, str | None]]] = defaultdict(list)
    for student_id, email, document_key, document_number in students:
        key = _email_key(email)
        if key is not None:
            by_email[key].append((student_id, document_key, document_number))

    survivors: list[dict] = []
    for key, group in by_email.items():
        survivor_id, document_key, document_number = group[0]
        merged_ids = [student_id for student_id, _, _ in group[1:]]
        if document_key is None:
            document_key, document_number = next(
                ((d_key, d_number) for _, d_key, d_number in group if d_key),
                (None, None),
            )
        if merged_ids:
            bind.execute(
                _results.update()
                .where(_results.c.student_id.in_(merged_ids))
                .values(student_id=survivor_id)
            )
            bind.execute(
                _students.delete().where(_students.c.id.in_(merged_ids))
            )
        survivors.append(
            {
                "_id": survivor_id,
                "email_key": key,
                "document_key": document_key,
                "document_number": document_number,
            }
        )
    _batched_update(
        bind,
        _students.update()
        .where(_students.c.id == sa.bindparam("_id"))
        .values(
            email_key=sa.bindparam("email_key"),
            document_key=sa.bindparam("document_key"),
            document_number=sa.bindparam("document_number"),
        ),
        survivors,
    )
    op.create_index(
        _STUDENTS_INDEX, "academic_students", ["email_key"], unique=True
    )

    with op.batch_alter_table("academic_results") as batch:
        batch.add_column(
            sa.Column("email_key", sa.String(length=320), nullable=True)
        )
        batch.add_column(
            sa.Column("program_resolution", sa.String(length=20), nullable=True)
        )
        batch.add_column(
            sa.Column(
                "program_resolved_import_id", sa.String(length=36), nullable=True
            )
        )
        batch.add_column(
            sa.Column("program_resolved_period", sa.String(length=7), nullable=True)
        )
        batch.create_foreign_key(
            _RESOLVED_FK,
            "excel_imports",
            ["program_resolved_import_id"],
            ["id"],
            ondelete="SET NULL",
        )
    op.create_index(
        _RESULTS_INDEX, "academic_results", ["import_id", "email_key", "moment"]
    )

    rows = bind.execute(
        sa.select(_results.c.id, _results.c.email_source).where(
            _results.c.email_source.is_not(None)
        )
    ).all()
    _batched_update(
        bind,
        _results.update()
        .where(_results.c.id == sa.bindparam("_id"))
        .values(email_key=sa.bindparam("email_key")),
        [
            {"_id": result_id, "email_key": _email_key(email)}
            for result_id, email in rows
            if _email_key(email) is not None
        ],
    )


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_index(_RESULTS_INDEX, table_name="academic_results")
    with op.batch_alter_table("academic_results") as batch:
        batch.drop_constraint(_RESOLVED_FK, type_="foreignkey")
        batch.drop_column("program_resolved_period")
        batch.drop_column("program_resolved_import_id")
        batch.drop_column("program_resolution")
        batch.drop_column("email_key")

    without_document = [
        student_id
        for (student_id,) in bind.execute(
            sa.select(_students.c.id).where(_students.c.document_key.is_(None))
        ).all()
    ]
    if without_document:
        bind.execute(
            _results.update()
            .where(_results.c.student_id.in_(without_document))
            .values(student_id=None)
        )
        bind.execute(
            _students.delete().where(_students.c.id.in_(without_document))
        )
    op.drop_index(_STUDENTS_INDEX, table_name="academic_students")
    with op.batch_alter_table("academic_students") as batch:
        batch.alter_column(
            "document_number", existing_type=sa.String(length=80), nullable=False
        )
        batch.alter_column(
            "document_key", existing_type=sa.String(length=64), nullable=False
        )
        batch.drop_column("email_key")
