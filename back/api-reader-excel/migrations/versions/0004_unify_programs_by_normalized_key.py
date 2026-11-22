"""Unify academic programs that differ only in accents, case or spacing.

Before this revision a program was identified by the hash of its raw name, so
"INGENIERIA DE SISTEMAS" and "INGENIERÍA DE SISTEMAS" were two programs. From
now on ``academic_programs.normalized_key`` is the identity (unique index).

Upgrade, for each ``normalized_key`` with more than one program:
1. keep the program with the lowest id;
2. point ``academic_results`` and ``academic_program_aliases`` of the others to it;
3. record every merged name as an alias and delete the duplicates.
Then every remaining program gets an alias for its own name, and the index on
``normalized_key`` becomes unique.

Downgrade only restores the non-unique index: merged programs are NOT split
again (the original split was an error, and results keep ``program_name_raw``).
"""

from collections import defaultdict
from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_unify_programs"
down_revision: str | None = "0003_soft_delete_excel_imports"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_INDEX = "ix_academic_programs_normalized_key"

_programs = sa.table(
    "academic_programs",
    sa.column("id", sa.Integer),
    sa.column("canonical_name", sa.String),
    sa.column("normalized_key", sa.String),
)
_aliases = sa.table(
    "academic_program_aliases",
    sa.column("id", sa.Integer),
    sa.column("program_id", sa.Integer),
    sa.column("raw_name", sa.String),
    sa.column("normalized_name", sa.String),
)
_results = sa.table(
    "academic_results",
    sa.column("program_id", sa.Integer),
)


def upgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.select(
            _programs.c.id, _programs.c.canonical_name, _programs.c.normalized_key
        ).order_by(_programs.c.id)
    ).all()

    by_key: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for program_id, name, key in rows:
        by_key[key].append((program_id, name))

    # Alias existentes, comparados en Python (la colación de MySQL ignora tildes).
    known_aliases = {
        (program_id, raw_name)
        for program_id, raw_name in bind.execute(
            sa.select(_aliases.c.program_id, _aliases.c.raw_name)
        ).all()
    }

    def add_alias(program_id: int, raw_name: str, key: str) -> None:
        if (program_id, raw_name) in known_aliases:
            return
        bind.execute(
            _aliases.insert().values(
                program_id=program_id, raw_name=raw_name, normalized_name=key
            )
        )
        known_aliases.add((program_id, raw_name))

    for key, programs in by_key.items():
        keep_id, keep_name = programs[0]
        add_alias(keep_id, keep_name, key)
        for duplicate_id, duplicate_name in programs[1:]:
            bind.execute(
                _results.update()
                .where(_results.c.program_id == duplicate_id)
                .values(program_id=keep_id)
            )
            duplicate_aliases = bind.execute(
                sa.select(_aliases.c.id, _aliases.c.raw_name).where(
                    _aliases.c.program_id == duplicate_id
                )
            ).all()
            for alias_id, raw_name in duplicate_aliases:
                known_aliases.discard((duplicate_id, raw_name))
                if (keep_id, raw_name) in known_aliases:
                    bind.execute(_aliases.delete().where(_aliases.c.id == alias_id))
                else:
                    bind.execute(
                        _aliases.update()
                        .where(_aliases.c.id == alias_id)
                        .values(program_id=keep_id)
                    )
                    known_aliases.add((keep_id, raw_name))
            add_alias(keep_id, duplicate_name, key)
            bind.execute(
                _programs.delete().where(_programs.c.id == duplicate_id)
            )

    op.drop_index(_INDEX, table_name="academic_programs")
    op.create_index(
        _INDEX, "academic_programs", ["normalized_key"], unique=True
    )


def downgrade() -> None:
    op.drop_index(_INDEX, table_name="academic_programs")
    op.create_index(
        _INDEX, "academic_programs", ["normalized_key"], unique=False
    )
