import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from sqlalchemy import MetaData, create_engine, inspect

from modules.excel.entities.academic import (
    AcademicProgram,
    AcademicProgramAlias,
    AcademicResult,
    AcademicStudent,
    ActiveImport,
    DashboardState,
    ExcelImport,
    TdProgramasReference,
)
from core.orm import Base
from migrations.runner import DatabaseMigrationService

_ACADEMIC_MODELS = (
    AcademicProgram,
    AcademicProgramAlias,
    AcademicResult,
    AcademicStudent,
    ActiveImport,
    DashboardState,
    ExcelImport,
    TdProgramasReference,
)


_VERSIONS_DIR = Path(__file__).resolve().parents[1] / "migrations" / "versions"


def load_migration(filename: str):
    spec = importlib.util.spec_from_file_location(
        f"migration_{filename.removesuffix('.py')}", _VERSIONS_DIR / filename
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def security_metadata() -> MetaData:
    metadata = MetaData()
    for table_name in ("api_users", "api_access_tokens"):
        Base.metadata.tables[table_name].to_metadata(metadata)
    return metadata


class SecurityMigrationTests(unittest.TestCase):
    def test_migration_chain_matches_models_and_downgrades(self) -> None:
        self.assertTrue(
            all(
                model.__tablename__ in Base.metadata.tables
                for model in _ACADEMIC_MODELS
            )
        )
        migration_path = (
            Path(__file__).resolve().parents[1]
            / "migrations"
            / "versions"
            / "0001_create_security_tables.py"
        )
        spec = importlib.util.spec_from_file_location(
            "security_initial_migration", migration_path
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)

        academic_migration_path = migration_path.with_name(
            "0002_academic_dashboard.py"
        )
        academic_spec = importlib.util.spec_from_file_location(
            "academic_dashboard_migration", academic_migration_path
        )
        self.assertIsNotNone(academic_spec)
        self.assertIsNotNone(academic_spec.loader)
        academic_migration = importlib.util.module_from_spec(academic_spec)
        academic_spec.loader.exec_module(academic_migration)

        soft_delete_migration_path = migration_path.with_name(
            "0003_soft_delete_excel_imports.py"
        )
        soft_delete_spec = importlib.util.spec_from_file_location(
            "soft_delete_excel_imports_migration",
            soft_delete_migration_path,
        )
        self.assertIsNotNone(soft_delete_spec)
        self.assertIsNotNone(soft_delete_spec.loader)
        soft_delete_migration = importlib.util.module_from_spec(
            soft_delete_spec
        )
        soft_delete_spec.loader.exec_module(soft_delete_migration)
        unify_programs_migration = load_migration(
            "0004_unify_programs_by_normalized_key.py"
        )
        sources_migration = load_migration("0005_sources_periods_moments.py")

        engine = create_engine("sqlite://")
        try:
            with engine.begin() as connection:
                context = MigrationContext.configure(connection)
                with Operations.context(context):
                    migration.upgrade()
                    academic_migration.upgrade()
                    soft_delete_migration.upgrade()
                    unify_programs_migration.upgrade()
                    sources_migration.upgrade()

                self.assertEqual(
                    set(inspect(connection).get_table_names()),
                    set(Base.metadata.tables),
                )
                self.assertEqual(
                    compare_metadata(context, Base.metadata), []
                )

                with Operations.context(context):
                    sources_migration.downgrade()
                    unify_programs_migration.downgrade()
                    soft_delete_migration.downgrade()
                    academic_migration.downgrade()
                    migration.downgrade()
                self.assertEqual(inspect(connection).get_table_names(), [])
        finally:
            engine.dispose()

    def test_unify_programs_merges_duplicates_and_keeps_results(self) -> None:
        engine = create_engine("sqlite://")
        try:
            with engine.begin() as connection:
                context = MigrationContext.configure(connection)
                with Operations.context(context):
                    for filename in (
                        "0001_create_security_tables.py",
                        "0002_academic_dashboard.py",
                        "0003_soft_delete_excel_imports.py",
                    ):
                        load_migration(filename).upgrade()

                # Tres escrituras del mismo programa y uno distinto.
                connection.exec_driver_sql(
                    "INSERT INTO academic_programs "
                    "(id, canonical_name, raw_name_key, normalized_key, is_active) VALUES "
                    "(1, 'INGENIERIA DE SISTEMAS', 'k1', 'ingenieria de sistemas', 1), "
                    "(2, 'INGENIERÍA DE SISTEMAS', 'k2', 'ingenieria de sistemas', 1), "
                    "(3, 'Ingeniería de  Sistemas', 'k3', 'ingenieria de sistemas', 1), "
                    "(4, 'MEDICINA', 'k4', 'medicina', 1)"
                )
                for row, program_id in enumerate((1, 2, 3, 3, 4), start=1):
                    connection.exec_driver_sql(
                        "INSERT INTO academic_results (import_id, source_row_number, "
                        "program_id, program_name_raw, year, simulation_name, "
                        "simulation_key, created_at) VALUES "
                        f"('imp', {row}, {program_id}, 'x', 2026, 'S', 's', "
                        "'2026-01-01 00:00:00')"
                    )

                with Operations.context(context):
                    load_migration(
                        "0004_unify_programs_by_normalized_key.py"
                    ).upgrade()

                programs = connection.exec_driver_sql(
                    "SELECT id, normalized_key FROM academic_programs ORDER BY id"
                ).all()
                self.assertEqual(
                    programs,
                    [(1, "ingenieria de sistemas"), (4, "medicina")],
                )
                result_programs = connection.exec_driver_sql(
                    "SELECT program_id, COUNT(*) FROM academic_results "
                    "GROUP BY program_id ORDER BY program_id"
                ).all()
                self.assertEqual(result_programs, [(1, 4), (4, 1)])
                aliases = connection.exec_driver_sql(
                    "SELECT program_id, raw_name FROM academic_program_aliases "
                    "ORDER BY program_id, raw_name"
                ).all()
                self.assertEqual(
                    aliases,
                    [
                        (1, "INGENIERIA DE SISTEMAS"),
                        (1, "INGENIERÍA DE SISTEMAS"),
                        (1, "Ingeniería de  Sistemas"),
                        (4, "MEDICINA"),
                    ],
                )
                unique_index = next(
                    index
                    for index in inspect(connection).get_indexes(
                        "academic_programs"
                    )
                    if index["name"] == "ix_academic_programs_normalized_key"
                )
                self.assertTrue(unique_index["unique"])
        finally:
            engine.dispose()

    def test_sources_migration_fills_period_moment_and_ese_slot(self) -> None:
        engine = create_engine("sqlite://")
        try:
            with engine.begin() as connection:
                context = MigrationContext.configure(connection)
                with Operations.context(context):
                    for filename in (
                        "0001_create_security_tables.py",
                        "0002_academic_dashboard.py",
                        "0003_soft_delete_excel_imports.py",
                        "0004_unify_programs_by_normalized_key.py",
                    ):
                        load_migration(filename).upgrade()

                connection.exec_driver_sql(
                    "INSERT INTO excel_imports (id, filename, file_sha256, "
                    "imported_at, status, dataset_mode, bd_gen_row_count, "
                    "td_programas_row_count, inserted_count, rejected_count) "
                    "VALUES ('imp', 'ese.xlsm', 'hash', '2026-01-01 00:00:00', "
                    "'ACTIVE', 'SNAPSHOT', 3, 0, 3, 0)"
                )
                connection.exec_driver_sql(
                    "UPDATE excel_dashboard_state SET active_import_id = 'imp'"
                )
                rows = (
                    ("SIMULACRO 2026-1 MOMENTO 3", "MOMENTO 3"),
                    ("SIMULACRO 2024", "MOMENTO 2"),
                    ("OTRO", None),
                )
                for row, (simulation, group) in enumerate(rows, start=1):
                    connection.exec_driver_sql(
                        "INSERT INTO academic_results (import_id, "
                        "source_row_number, program_name_raw, year, "
                        "simulation_name, simulation_key, group_name, created_at) "
                        "VALUES (?, ?, 'x', 2026, ?, 's', ?, '2026-01-01 00:00:00')",
                        ("imp", row, simulation, group),
                    )

                with Operations.context(context):
                    load_migration("0005_sources_periods_moments.py").upgrade()

                self.assertEqual(
                    connection.exec_driver_sql(
                        "SELECT source_row_number, period, moment "
                        "FROM academic_results ORDER BY source_row_number"
                    ).all(),
                    [(1, "2026-1", 3), (2, None, 2), (3, None, None)],
                )
                self.assertEqual(
                    connection.exec_driver_sql(
                        "SELECT slot, import_id FROM excel_active_imports"
                    ).all(),
                    [("ESE", "imp")],
                )
                self.assertEqual(
                    connection.exec_driver_sql(
                        "SELECT source, period FROM excel_imports"
                    ).all(),
                    [("ESE", None)],
                )
        finally:
            engine.dispose()

    def test_existing_unversioned_schema_is_stamped_only_when_it_matches(self) -> None:
        engine = create_engine("sqlite://")
        try:
            security_metadata().create_all(engine)
            with engine.begin() as connection:
                connection.exec_driver_sql(
                    "CREATE TABLE unrelated_core_table (id INTEGER PRIMARY KEY)"
                )
            migration_service = DatabaseMigrationService(Config(), engine)

            with patch(
                "migrations.runner.command.stamp"
            ) as stamp:
                with patch(
                    "migrations.runner.command.upgrade"
                ) as upgrade:
                    migration_service.upgrade()

            stamp.assert_called_once_with(
                migration_service.config, "0001_security_tables"
            )
            upgrade.assert_called_once_with(migration_service.config, "head")
        finally:
            engine.dispose()

    def test_partial_legacy_schema_is_not_modified(self) -> None:
        engine = create_engine("sqlite://")
        try:
            with engine.begin() as connection:
                connection.exec_driver_sql("CREATE TABLE api_users (id INTEGER)")
            migration_service = DatabaseMigrationService(Config(), engine)

            with patch(
                "migrations.runner.command.stamp"
            ) as stamp:
                with self.assertRaises(RuntimeError):
                    migration_service.upgrade()

            stamp.assert_not_called()
        finally:
            engine.dispose()
