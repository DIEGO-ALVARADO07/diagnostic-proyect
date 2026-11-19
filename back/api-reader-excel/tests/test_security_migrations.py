import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from modules.security.models import AuthBase
from modules.security.services.migration_service import SecurityMigrationService


class SecurityMigrationTests(unittest.TestCase):
    def test_initial_migration_matches_security_models_and_downgrades(self) -> None:
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

        engine = create_engine("sqlite://")
        try:
            with engine.begin() as connection:
                context = MigrationContext.configure(connection)
                with Operations.context(context):
                    migration.upgrade()

                self.assertEqual(
                    set(inspect(connection).get_table_names()),
                    {"api_users", "api_access_tokens"},
                )
                self.assertEqual(compare_metadata(context, AuthBase.metadata), [])

                with Operations.context(context):
                    migration.downgrade()
                self.assertEqual(inspect(connection).get_table_names(), [])
        finally:
            engine.dispose()

    def test_existing_unversioned_schema_is_stamped_only_when_it_matches(self) -> None:
        engine = create_engine("sqlite://")
        try:
            AuthBase.metadata.create_all(engine)
            with engine.begin() as connection:
                connection.exec_driver_sql(
                    "CREATE TABLE unrelated_core_table (id INTEGER PRIMARY KEY)"
                )
            migration_service = SecurityMigrationService(Config(), engine)

            with patch(
                "modules.security.services.migration_service.command.stamp"
            ) as stamp:
                migration_service.upgrade()

            stamp.assert_called_once_with(migration_service.config, "head")
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
