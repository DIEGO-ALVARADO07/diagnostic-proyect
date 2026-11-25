"""Add test source, period and moment; one active import per slot.

Upgrade:
1. ``excel_imports``: ``source`` (``ESE``/``CORHUILA``, existing rows = ``ESE``)
   and ``period`` (only CORHUILA files are a single period).
2. New ``excel_active_imports``: the active import of each slot (``ESE``, or
   ``CORHUILA:<period>``). The current active import is copied to ``ESE``.
3. ``excel_dashboard_state`` keeps only its id: it is the lock row that
   serializes activations; ``active_import_id`` moves to the new table.
4. ``academic_results``: ``period`` (``2026-1``) and ``moment`` (1–3), filled
   for existing rows from ``SIM`` (period and moment) and ``GRUPO`` (moment,
   when ``SIM`` does not have one).

Downgrade restores ``active_import_id`` from the ``ESE`` slot; CORHUILA slots
are lost (there were none before this revision).
"""

import re
from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_sources_periods_moments"
down_revision: str | None = "0004_unify_programs"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

_SOURCE_CHECK = "ck_excel_imports_source"
_RESULTS_INDEX = "ix_academic_results_import_period_moment"
_BATCH_SIZE = 1000

# Copia de modules/excel/entities/assessment.py: una migración no debe cambiar
# de comportamiento si el código de la aplicación cambia después.
_PERIOD_PATTERN = re.compile(r"(?<!\d)(\d{4})\s*-\s*([12])(?!\d)")
_MOMENT_PATTERN = re.compile(r"momento\s*(\d+)", re.IGNORECASE)


def _period(value: str | None) -> str | None:
    match = _PERIOD_PATTERN.search(value or "")
    return f"{match.group(1)}-{match.group(2)}" if match else None


def _moment(value: str | None) -> int | None:
    match = _MOMENT_PATTERN.search(value or "")
    if match is None:
        return None
    moment = int(match.group(1))
    return moment if moment in (1, 2, 3) else None


_state = sa.table(
    "excel_dashboard_state",
    sa.column("id", sa.SmallInteger),
    sa.column("active_import_id", sa.String),
)
_active = sa.table(
    "excel_active_imports",
    sa.column("slot", sa.String),
    sa.column("import_id", sa.String),
)
_results = sa.table(
    "academic_results",
    sa.column("id", sa.Integer),
    sa.column("simulation_name", sa.String),
    sa.column("group_name", sa.String),
    sa.column("period", sa.String),
    sa.column("moment", sa.SmallInteger),
)


def _state_foreign_key_names(bind: sa.engine.Connection) -> list[str]:
    return [
        foreign_key["name"]
        for foreign_key in sa.inspect(bind).get_foreign_keys(
            "excel_dashboard_state"
        )
        if foreign_key.get("name")
        and foreign_key["constrained_columns"] == ["active_import_id"]
    ]


def upgrade() -> None:
    bind = op.get_bind()

    with op.batch_alter_table("excel_imports") as batch:
        batch.add_column(
            sa.Column(
                "source",
                sa.String(length=20),
                nullable=False,
                server_default="ESE",
            )
        )
        batch.add_column(sa.Column("period", sa.String(length=7), nullable=True))
        batch.create_check_constraint(
            _SOURCE_CHECK, "source IN ('ESE', 'CORHUILA')"
        )
    with op.batch_alter_table("excel_imports") as batch:
        # El valor por defecto solo sirvió para las filas existentes.
        batch.alter_column(
            "source",
            existing_type=sa.String(length=20),
            existing_nullable=False,
            server_default=None,
        )

    op.create_table(
        "excel_active_imports",
        sa.Column("slot", sa.String(length=40), nullable=False),
        sa.Column("import_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(
            ["import_id"], ["excel_imports.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("slot"),
        sa.UniqueConstraint("import_id"),
    )
    active_import_id = bind.execute(
        sa.select(_state.c.active_import_id).where(_state.c.id == 1)
    ).scalar()
    if active_import_id is not None:
        bind.execute(
            _active.insert().values(slot="ESE", import_id=active_import_id)
        )

    if bind.dialect.name == "sqlite":
        with op.batch_alter_table(
            "excel_dashboard_state", recreate="always"
        ) as batch:
            batch.drop_column("active_import_id")
    else:
        for name in _state_foreign_key_names(bind):
            op.drop_constraint(name, "excel_dashboard_state", type_="foreignkey")
        op.drop_column("excel_dashboard_state", "active_import_id")

    op.add_column(
        "academic_results",
        sa.Column("period", sa.String(length=7), nullable=True),
    )
    op.add_column(
        "academic_results",
        sa.Column("moment", sa.SmallInteger(), nullable=True),
    )
    op.create_index(
        _RESULTS_INDEX, "academic_results", ["import_id", "period", "moment"]
    )

    rows = bind.execute(
        sa.select(
            _results.c.id, _results.c.simulation_name, _results.c.group_name
        )
    ).all()
    updates = []
    for result_id, simulation, group in rows:
        moment = _moment(simulation)
        if moment is None:
            moment = _moment(group)
        period = _period(simulation)
        if period is not None or moment is not None:
            updates.append({"_id": result_id, "period": period, "moment": moment})
    statement = (
        _results.update()
        .where(_results.c.id == sa.bindparam("_id"))
        .values(period=sa.bindparam("period"), moment=sa.bindparam("moment"))
    )
    for offset in range(0, len(updates), _BATCH_SIZE):
        bind.execute(statement, updates[offset : offset + _BATCH_SIZE])


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_index(_RESULTS_INDEX, table_name="academic_results")
    with op.batch_alter_table("academic_results") as batch:
        batch.drop_column("moment")
        batch.drop_column("period")

    with op.batch_alter_table("excel_dashboard_state") as batch:
        batch.add_column(
            sa.Column("active_import_id", sa.String(length=36), nullable=True)
        )
        batch.create_foreign_key(
            "fk_excel_dashboard_state_active_import",
            "excel_imports",
            ["active_import_id"],
            ["id"],
            ondelete="SET NULL",
        )
    ese_import_id = bind.execute(
        sa.select(_active.c.import_id).where(_active.c.slot == "ESE")
    ).scalar()
    bind.execute(
        _state.update()
        .where(_state.c.id == 1)
        .values(active_import_id=ese_import_id)
    )
    op.drop_table("excel_active_imports")

    with op.batch_alter_table("excel_imports") as batch:
        batch.drop_constraint(_SOURCE_CHECK, type_="check")
        batch.drop_column("period")
        batch.drop_column("source")
