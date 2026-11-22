from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import MetaData, inspect
from sqlalchemy.engine import Engine

from core.orm import Base

_SECURITY_TABLES = {"api_users", "api_access_tokens"}
_ACADEMIC_TABLES = {
    "excel_imports",
    "academic_students",
    "academic_programs",
    "academic_program_aliases",
    "academic_results",
    "td_programas_reference",
    "excel_dashboard_state",
}


def _security_metadata() -> MetaData:
    metadata = MetaData()
    for table_name in _SECURITY_TABLES:
        Base.metadata.tables[table_name].to_metadata(metadata)
    return metadata


def _include_security_tables(
    name: str | None, object_type: str, parent_names: dict[str, str]
) -> bool:
    if object_type == "schema":
        return name is None
    if object_type == "table":
        return name in _SECURITY_TABLES
    return parent_names.get("table_name") in _SECURITY_TABLES


class DatabaseMigrationService:
    def __init__(self, config: Config, engine: Engine) -> None:
        self.config = config
        self.engine = engine

    def upgrade(self) -> None:
        with self.engine.connect() as connection:
            tables = set(inspect(connection).get_table_names())

            existing_security_tables = tables & _SECURITY_TABLES
            if "alembic_version" not in tables and existing_security_tables:
                if existing_security_tables != _SECURITY_TABLES:
                    raise RuntimeError(
                        "El esquema de seguridad está incompleto; revisa la base antes "
                        "de aplicar migraciones."
                    )
                if tables & _ACADEMIC_TABLES:
                    raise RuntimeError(
                        "El esquema académico existe sin historial Alembic; "
                        "verifica la base antes de aplicar migraciones."
                    )

                differences = compare_metadata(
                    MigrationContext.configure(
                        connection,
                        opts={"include_name": _include_security_tables},
                    ),
                    _security_metadata(),
                )
                if differences:
                    raise RuntimeError(
                        "El esquema existente no coincide con los modelos de seguridad; "
                        "no se aplicó ni marcó ninguna migración."
                    )

        if "alembic_version" not in tables and existing_security_tables:
            command.stamp(self.config, "0001_security_tables")
        command.upgrade(self.config, "head")
