"""Students identified by document with email aliases; ESE Momento 4.

Upgrade:
1. ``academic_results.moment = 4`` where ``SIM`` or ``GRUPO`` say ``MOMENTO 4``
   (historical 2024 scheme, semesters 8–10).
2. New ``academic_student_emails``: every email of a student (institutional and
   personal). Each email belongs to one student.
3. Students split by revision 0006 (same document, different emails) are merged
   into the one that holds the document (or the lowest id); their results point
   to it. No result is deleted or changed otherwise.
4. Aliases are filled from the emails of each student's results; the main
   ``email_key`` becomes the latest institutional email (``@corhuila.edu.co``),
   or the latest email when there is no institutional one.
5. ``ix_academic_students_email_key`` stops being unique (uniqueness moves to
   the alias table).
6. ``academic_results.student_match``: how a CORHUILA row was matched to an ESE
   student (document, email or full name).

Downgrade drops the alias table and ``student_match``, clears ``moment = 4`` and
restores the unique index. Merged students are NOT split again.
"""

import re
from collections import defaultdict
from hashlib import sha256
from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_document_identity"
down_revision: str | None = "0006_student_identity_by_email"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_STUDENTS_INDEX = "ix_academic_students_email_key"
_ALIASES_INDEX = "ix_academic_student_emails_student_id"
_INSTITUTIONAL_DOMAIN = "@corhuila.edu.co"
_BATCH_SIZE = 1000
_MOMENT_FOUR = re.compile(r"momento\s*4(?!\d)", re.IGNORECASE)

_students = sa.table(
    "academic_students",
    sa.column("id", sa.Integer),
    sa.column("email_key", sa.String),
    sa.column("document_key", sa.String),
)
_aliases = sa.table(
    "academic_student_emails",
    sa.column("email_key", sa.String),
    sa.column("student_id", sa.Integer),
)
_results = sa.table(
    "academic_results",
    sa.column("id", sa.Integer),
    sa.column("student_id", sa.Integer),
    sa.column("document_number_source", sa.String),
    sa.column("email_key", sa.String),
    sa.column("simulation_name", sa.String),
    sa.column("group_name", sa.String),
    sa.column("moment", sa.SmallInteger),
)


def _document_key(document: str) -> str:
    return sha256(document.encode("utf-8")).hexdigest()


def upgrade() -> None:
    bind = op.get_bind()

    # 1. Momento 4.
    moment_four = [
        {"_id": result_id}
        for result_id, simulation, group in bind.execute(
            sa.select(
                _results.c.id, _results.c.simulation_name, _results.c.group_name
            ).where(_results.c.moment.is_(None))
        )
        if _MOMENT_FOUR.search(simulation or "") or _MOMENT_FOUR.search(group or "")
    ]
    statement = (
        _results.update()
        .where(_results.c.id == sa.bindparam("_id"))
        .values(moment=4)
    )
    for offset in range(0, len(moment_four), _BATCH_SIZE):
        bind.execute(statement, moment_four[offset : offset + _BATCH_SIZE])

    # 2. Tabla de alias.
    op.create_table(
        "academic_student_emails",
        sa.Column("email_key", sa.String(length=320), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["student_id"], ["academic_students.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("email_key"),
    )
    op.create_index(_ALIASES_INDEX, "academic_student_emails", ["student_id"])

    # 3. Unir estudiantes con el mismo documento.
    holder_by_document_key = {
        document_key: student_id
        for student_id, document_key in bind.execute(
            sa.select(_students.c.id, _students.c.document_key).where(
                _students.c.document_key.is_not(None)
            )
        )
    }
    students_by_document: dict[str, set[int]] = defaultdict(set)
    for document, student_id in bind.execute(
        sa.select(
            _results.c.document_number_source, _results.c.student_id
        ).where(
            _results.c.document_number_source.is_not(None),
            _results.c.student_id.is_not(None),
        )
    ):
        students_by_document[document].add(student_id)

    for document, student_ids in students_by_document.items():
        if len(student_ids) < 2:
            continue
        survivor = holder_by_document_key.get(_document_key(document))
        if survivor not in student_ids:
            survivor = min(student_ids)
        merged = sorted(student_ids - {survivor})
        bind.execute(
            _results.update()
            .where(_results.c.student_id.in_(merged))
            .values(student_id=survivor)
        )
        bind.execute(_students.delete().where(_students.c.id.in_(merged)))

    # 4. Alias y correo principal.
    emails_by_student: dict[int, list[str]] = defaultdict(list)
    for student_id, email in bind.execute(
        sa.select(_results.c.student_id, _results.c.email_key)
        .where(
            _results.c.student_id.is_not(None),
            _results.c.email_key.is_not(None),
        )
        .order_by(_results.c.id)
    ):
        if email not in emails_by_student[student_id]:
            emails_by_student[student_id].append(email)
    for student_id, email in bind.execute(
        sa.select(_students.c.id, _students.c.email_key).where(
            _students.c.email_key.is_not(None)
        )
    ):
        if email not in emails_by_student[student_id]:
            emails_by_student[student_id].insert(0, email)

    taken: set[str] = set()
    aliases: list[dict] = []
    main_emails: list[dict] = []
    for student_id in sorted(emails_by_student):
        emails = emails_by_student[student_id]
        for email in emails:
            if email not in taken:
                taken.add(email)
                aliases.append({"email_key": email, "student_id": student_id})
        institutional = [e for e in emails if e.endswith(_INSTITUTIONAL_DOMAIN)]
        main_emails.append(
            {"_id": student_id, "email_key": (institutional or emails)[-1]}
        )
    for offset in range(0, len(aliases), _BATCH_SIZE):
        bind.execute(_aliases.insert(), aliases[offset : offset + _BATCH_SIZE])

    # 5. El correo principal deja de ser único (la unicidad pasa a los alias).
    op.drop_index(_STUDENTS_INDEX, table_name="academic_students")
    statement = (
        _students.update()
        .where(_students.c.id == sa.bindparam("_id"))
        .values(email_key=sa.bindparam("email_key"))
    )
    for offset in range(0, len(main_emails), _BATCH_SIZE):
        bind.execute(statement, main_emails[offset : offset + _BATCH_SIZE])
    op.create_index(_STUDENTS_INDEX, "academic_students", ["email_key"])

    # 6. Cómo se encontró al estudiante de una fila de CORHUILA.
    op.add_column(
        "academic_results",
        sa.Column("student_match", sa.String(length=20), nullable=True),
    )


def downgrade() -> None:
    bind = op.get_bind()
    with op.batch_alter_table("academic_results") as batch:
        batch.drop_column("student_match")
    op.drop_index(_STUDENTS_INDEX, table_name="academic_students")
    # Un correo principal repetido no cabe en el índice único anterior.
    seen: set[str] = set()
    for student_id, email in bind.execute(
        sa.select(_students.c.id, _students.c.email_key)
        .where(_students.c.email_key.is_not(None))
        .order_by(_students.c.id)
    ).all():
        if email in seen:
            bind.execute(
                _students.update()
                .where(_students.c.id == student_id)
                .values(email_key=None)
            )
        seen.add(email)
    op.create_index(
        _STUDENTS_INDEX, "academic_students", ["email_key"], unique=True
    )
    op.drop_index(_ALIASES_INDEX, table_name="academic_student_emails")
    op.drop_table("academic_student_emails")
    bind.execute(
        _results.update().where(_results.c.moment == 4).values(moment=None)
    )
