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
    DashboardState,
    ExcelImport,
    TdProgramasReference,
)
from modules.security.entities import AuthBase
from modules.security.services.migration_service import SecurityMigrationService

_ACADEMIC_MODELS = (
    AcademicProgram,
    AcademicProgramAlias,
    AcademicResult,
    AcademicStudent,
    DashboardState,
    ExcelImport,
    TdProgramasReference,
)


def security_metadata() -> MetaData:
    metadata = MetaData()
    for table_name in ("api_users", "api_access_tokens"):
        AuthBase.metadata.tables[table_name].to_metadata(metadata)
    return metadata


class SecurityMigrationTests(unittest.TestCase):
    def test_migration_chain_matches_models_and_downgrades(self) -> None:
        self.assertTrue(
            all(
                model.__tablename__ in AuthBase.metadata.tables
                for model in _ACADEMIC_MODELS
            )
        )
        migration_path = (
            Path(__file__).resolve().parents[1]
            / "modules"
            / "security"
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

        engine = create_engine("sqlite://")
        try:
            with engine.begin() as connection:
                context = MigrationContext.configure(connection)
                with Operations.context(context):
                    migration.upgrade()
                    academic_migration.upgrade()
                    soft_delete_migration.upgrade()

                self.assertEqual(
                    set(inspect(connection).get_table_names()),
                    set(AuthBase.metadata.tables),
                )
                self.assertEqual(
                    compare_metadata(context, AuthBase.metadata), []
                )

                with Operations.context(context):
                    soft_delete_migration.downgrade()
                    academic_migration.downgrade()
                    migration.downgrade()
                self.assertEqual(inspect(connection).get_table_names(), [])
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
            migration_service = SecurityMigrationService(Config(), engine)

            with patch(
                "modules.security.services.migration_service.command.stamp"
            ) as stamp:
                with patch(
                    "modules.security.services.migration_service.command.upgrade"
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
            migration_service = SecurityMigrationService(Config(), engine)

            with patch(
                "modules.security.services.migration_service.command.stamp"
            ) as stamp:
                with self.assertRaises(RuntimeError):
                    migration_service.upgrade()

            stamp.assert_not_called()
        finally:
            engine.dispose()
