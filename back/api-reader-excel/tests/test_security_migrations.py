import importlib.util
from hashlib import sha256
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
    AcademicStudentEmail,
    ActiveImport,
    DashboardState,
    ExcelImport,
    TdProgramasReference,
)
from core.orm import Base
from migrations.runner import DatabaseMigrationService
from modules.courses.entities import Course, CourseEnrollment  # noqa: F401 (registra tablas)
from modules.security.entities import AccessToken, Account  # noqa: F401 (registra tablas)

_ACADEMIC_MODELS = (
    AcademicProgram,
    AcademicProgramAlias,
    AcademicResult,
    AcademicStudent,
    AcademicStudentEmail,
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
        identity_migration = load_migration("0006_student_identity_by_email.py")
        aliases_migration = load_migration(
            "0007_document_identity_email_aliases.py"
        )
        manual_migration = load_migration("0008_manual_program_assignment.py")
        courses_migration = load_migration("0009_courses.py")
        audit_migration = load_migration("0010_soft_delete_audit.py")
        details_migration = load_migration("0011_course_competency_details.py")

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
                    identity_migration.upgrade()
                    aliases_migration.upgrade()
                    manual_migration.upgrade()
                    courses_migration.upgrade()
                    audit_migration.upgrade()
                    details_migration.upgrade()

                self.assertEqual(
                    set(inspect(connection).get_table_names()),
                    set(Base.metadata.tables),
                )
                self.assertEqual(
                    compare_metadata(context, Base.metadata), []
                )

                with Operations.context(context):
                    details_migration.downgrade()
                    audit_migration.downgrade()
                    courses_migration.downgrade()
                    manual_migration.downgrade()
                    aliases_migration.downgrade()
                    identity_migration.downgrade()
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

    def test_identity_migration_merges_students_by_email(self) -> None:
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
                        "0005_sources_periods_moments.py",
                    ):
                        load_migration(filename).upgrade()

                # 1 y 2 comparten correo (con distinta escritura); 3 es otra persona.
                connection.exec_driver_sql(
                    "INSERT INTO academic_students (id, document_key, "
                    "document_number, email, created_at, updated_at) VALUES "
                    "(1, 'k1', '101', 'Ana@X.co', '2026-01-01', '2026-01-01'), "
                    "(2, 'k2', '201', ' ana@x.co', '2026-01-01', '2026-01-01'), "
                    "(3, 'k3', '301', NULL, '2026-01-01', '2026-01-01')"
                )
                for row, (student_id, email) in enumerate(
                    ((1, "Ana@X.co"), (2, " ana@x.co"), (3, None)), start=1
                ):
                    connection.exec_driver_sql(
                        "INSERT INTO academic_results (import_id, "
                        "source_row_number, student_id, email_source, "
                        "program_name_raw, year, simulation_name, "
                        "simulation_key, created_at) VALUES "
                        "('imp', ?, ?, ?, 'x', 2026, 'S', 's', '2026-01-01')",
                        (row, student_id, email),
                    )

                with Operations.context(context):
                    load_migration("0006_student_identity_by_email.py").upgrade()

                self.assertEqual(
                    connection.exec_driver_sql(
                        "SELECT id, email_key, document_number "
                        "FROM academic_students ORDER BY id"
                    ).all(),
                    [(1, "ana@x.co", "101"), (3, None, "301")],
                )
                self.assertEqual(
                    connection.exec_driver_sql(
                        "SELECT source_row_number, student_id, email_key "
                        "FROM academic_results ORDER BY source_row_number"
                    ).all(),
                    [(1, 1, "ana@x.co"), (2, 1, "ana@x.co"), (3, 3, None)],
                )
        finally:
            engine.dispose()

    def test_aliases_migration_merges_by_document_and_sets_moment_four(self) -> None:
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
                        "0005_sources_periods_moments.py",
                        "0006_student_identity_by_email.py",
                    ):
                        load_migration(filename).upgrade()

                # Como quedaba tras la 0006: el documento 101 partido en dos
                # estudiantes (correo institucional y personal).
                doc_key = sha256(b"101").hexdigest()
                connection.exec_driver_sql(
                    "INSERT INTO academic_students (id, email_key, document_key, "
                    "document_number, created_at, updated_at) VALUES "
                    f"(1, 'ana@gmail.com', '{doc_key}', '101', '2026-01-01', '2026-01-01'), "
                    "(2, 'ana-2024a@corhuila.edu.co', NULL, NULL, '2026-01-01', '2026-01-01')"
                )
                rows = (
                    (1, "ana@gmail.com", "SIMULACRO 2025-1 MOMENTO 1", "MOMENTO 1", 1),
                    (2, "ana-2024a@corhuila.edu.co", "SIMULACRO 2026-1 MOMENTO 2", "MOMENTO 2", 2),
                    (2, "ana-2024a@corhuila.edu.co", "SIMULACRO 2024-1 MOMENTO 4", "MOMENTO 4", None),
                )
                for row, (student_id, email, simulation, group, moment) in enumerate(
                    rows, start=1
                ):
                    connection.exec_driver_sql(
                        "INSERT INTO academic_results (import_id, "
                        "source_row_number, student_id, document_number_source, "
                        "email_key, program_name_raw, year, simulation_name, "
                        "simulation_key, group_name, moment, created_at) VALUES "
                        "('imp', ?, ?, '101', ?, 'x', 2026, ?, 's', ?, ?, '2026-01-01')",
                        (row, student_id, email, simulation, group, moment),
                    )

                with Operations.context(context):
                    load_migration(
                        "0007_document_identity_email_aliases.py"
                    ).upgrade()

                self.assertEqual(
                    connection.exec_driver_sql(
                        "SELECT id, email_key, document_number FROM academic_students"
                    ).all(),
                    [(1, "ana-2024a@corhuila.edu.co", "101")],
                )
                self.assertEqual(
                    connection.exec_driver_sql(
                        "SELECT email_key, student_id FROM academic_student_emails "
                        "ORDER BY email_key"
                    ).all(),
                    [("ana-2024a@corhuila.edu.co", 1), ("ana@gmail.com", 1)],
                )
                self.assertEqual(
                    connection.exec_driver_sql(
                        "SELECT source_row_number, student_id, moment "
                        "FROM academic_results ORDER BY source_row_number"
                    ).all(),
                    [(1, 1, 1), (2, 1, 2), (3, 1, 4)],
                )
        finally:
            engine.dispose()

    def test_manual_program_migration_renames_ese_m2(self) -> None:
        engine = create_engine("sqlite://")
        try:
            with engine.begin() as connection:
                context = MigrationContext.configure(connection)
                with Operations.context(context):
                    for path in sorted(_VERSIONS_DIR.glob("000[1-7]_*.py")):
                        load_migration(path.name).upgrade()
                connection.exec_driver_sql(
                    "INSERT INTO academic_results (import_id, source_row_number, "
                    "program_name_raw, year, simulation_name, simulation_key, "
                    "program_resolution, created_at) VALUES "
                    "('imp', 1, '', 2026, 'S', 's', 'ESE_M2', '2026-01-01'), "
                    "('imp', 2, '', 2026, 'S', 's', 'SIN_PROGRAMA', '2026-01-01')"
                )
                with Operations.context(context):
                    load_migration("0008_manual_program_assignment.py").upgrade()
                self.assertEqual(
                    connection.exec_driver_sql(
                        "SELECT program_resolution FROM academic_results "
                        "ORDER BY source_row_number"
                    ).all(),
                    [("ESE",), ("SIN_PROGRAMA",)],
                )
                columns = {
                    column["name"]
                    for column in inspect(connection).get_columns("academic_students")
                }
                self.assertIn("assigned_program_id", columns)
        finally:
            engine.dispose()

    def test_revision_ids_fit_alembic_version_column(self) -> None:
        # alembic_version.version_num es VARCHAR(32) en MySQL.
        for path in sorted(_VERSIONS_DIR.glob("0*.py")):
            with self.subTest(migration=path.name):
                self.assertLessEqual(len(load_migration(path.name).revision), 32)

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
