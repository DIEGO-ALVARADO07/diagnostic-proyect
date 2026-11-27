"""Vacía los datos de la base para empezar el recorrido desde cero.

Uso (desde ``tasks.ps1 reset``)::

    python -m scripts.reset_db --confirm excel_reader [--include-users] [--skip-backup]

- **Primero hace una copia de seguridad** (``tasks.ps1 backup`` con la
  etiqueta ``antes-vaciar``). Si la copia falla, no se borra nada. Para volver
  al estado anterior basta con restaurar esa copia.
- Borra **todos los datos académicos**: importaciones de Excel (ESE y
  CORHUILA), resultados, estudiantes y sus correos, programas y sus alias,
  referencia de TD PROGRAMAS, cursos e inscripciones.
- **Conserva** la estructura (tablas y migraciones aplicadas), el estado del
  dashboard y, por defecto, las **cuentas de usuario**, para poder iniciar
  sesión y mostrar el recorrido. Con ``--include-users`` borra también cuentas
  y sesiones; después hay que crear el superadmin con ``tasks.ps1 bootstrap``.
- Los contadores de id vuelven a empezar en 1.
- Exige ``--confirm`` con el nombre exacto de la base, para no vaciar otra por
  error.
"""

import argparse
import sys
from collections.abc import Iterable

from sqlalchemy import Engine, MetaData, Table, delete, func, inspect, select, text

ACADEMIC_TABLES = (
    "enrollment_records",
    "enrollment_uploads",
    "course_enrollments",
    "courses",
    "academic_result_programs",
    "academic_results",
    "td_programas_reference",
    "excel_active_imports",
    "excel_imports",
    "academic_student_emails",
    "academic_students",
    "academic_program_aliases",
    "academic_programs",
)
"""Datos que se vacían, en orden seguro para las llaves foráneas."""

USER_TABLES = ("api_access_tokens", "api_users")
"""Solo con ``--include-users``."""

KEPT_TABLES = ("excel_dashboard_state", "alembic_version")
"""Nunca se vacían: estado inicial del dashboard y versión de las migraciones."""


def tables_to_empty(include_users: bool) -> tuple[str, ...]:
    return ACADEMIC_TABLES + (USER_TABLES if include_users else ())


def empty_tables(engine: Engine, tables: Iterable[str]) -> dict[str, int]:
    """Borra las filas de ``tables`` (en ese orden) en una transacción.

    Devuelve cuántas filas tenía cada tabla. Las tablas que no existen se omiten.
    """
    metadata = MetaData()
    counts: dict[str, int] = {}
    with engine.begin() as connection:
        existing = set(inspect(connection).get_table_names())
        for name in tables:
            if name not in existing:
                continue
            table = Table(name, metadata, autoload_with=connection)
            counts[name] = connection.scalar(select(func.count()).select_from(table)) or 0
            connection.execute(delete(table))
        if engine.dialect.name == "mysql":
            for name in counts:
                connection.execute(text(f"ALTER TABLE `{name}` AUTO_INCREMENT = 1"))
    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--confirm", required=True, help="Nombre exacto de la base.")
    parser.add_argument("--include-users", action="store_true")
    parser.add_argument(
        "--skip-backup",
        action="store_true",
        help="No hace la copia previa (no recomendado).",
    )
    args = parser.parse_args(argv)

    from core.config import settings  # Carga y descifra core/.env.
    from core.database import engine

    if args.confirm != settings.DB_NAME:
        print(
            f"La confirmación no coincide con la base configurada ({settings.DB_NAME}). "
            "No se borró nada.",
            file=sys.stderr,
        )
        return 2

    if not args.skip_backup:
        from scripts import backup_db

        if backup_db.main(["--label", "antes-vaciar"]) != 0:
            print("La copia de seguridad falló: no se borró nada.", file=sys.stderr)
            return 1

    counts = empty_tables(engine, tables_to_empty(args.include_users))
    total = sum(counts.values())
    print(f"Base {settings.DB_NAME} vaciada: {total} filas borradas.")
    for name, count in counts.items():
        print(f"  {name}: {count}")
    if args.include_users:
        print("También se borraron las cuentas: crea el superadmin con .\\tasks.ps1 bootstrap")
    else:
        print("Se conservaron las cuentas de usuario.")
    print("Reinicia la API (.\\tasks.ps1 run) para que no muestre datos guardados en memoria.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
