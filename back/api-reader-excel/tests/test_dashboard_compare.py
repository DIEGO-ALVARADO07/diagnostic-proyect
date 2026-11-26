"""Fase 11: dashboard comparativo y programa manual de los estudiantes por revisar."""

import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from core.exceptions import ApplicationError
from core.orm import Base
from modules.excel.dtos.requests.dashboard import DashboardFilterQuery
from modules.excel.dtos.requests.read_workbook import ReadWorkbookRequest
from modules.excel.entities.academic import (
    AcademicProgram,
    AcademicResult,
    AcademicStudent,
    DashboardState,
)
from modules.excel.entities.assessment import SIN_PROGRAMA_ID, Source
from modules.excel.services.dashboard_data_quality import assess_data_quality
from modules.excel.services.dashboard_service import DashboardService
from modules.excel.services.program_resolution import students_without_program
from modules.security.entities import Account
from modules.security.entities.role import Role
from tests.test_corhuila_import import CORHUILA_ROWS, make_corhuila_workbook
from tests.test_dashboard import make_dashboard_workbook
from tests.test_document_identity import EXTRA_ROWS


class CompareDashboardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.admin = Account(
            id=1,
            username="admin",
            email="admin@example.com",
            full_name="Admin",
            password_hash="unused",
            role=Role.SUPERADMIN.value,
            is_active=True,
        )
        self.db.add_all([self.admin, DashboardState(id=1)])
        self.db.commit()
        self.service = DashboardService()

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def _import_ese(self, period: str = "2026-1", global_score: object = 90):
        return self.service.import_workbook(
            ReadWorkbookRequest(
                filename="ese.xlsx",
                content=make_dashboard_workbook(
                    global_score=global_score, extra_records=EXTRA_ROWS
                ),
            ),
            self.admin,
            self.db,
            Source.ESE,
            period,
        )

    def _import_corhuila(self, period: str, rows: list | None = None):
        return self.service.import_workbook(
            ReadWorkbookRequest(
                filename=f"corhuila-{period}.xlsx",
                content=make_corhuila_workbook(rows),
            ),
            self.admin,
            self.db,
            Source.CORHUILA,
            period,
        )

    def _program_id(self, name: str) -> int:
        return self.db.scalar(
            select(AcademicProgram.id).where(
                AcademicProgram.normalized_key == name.lower()
            )
        )

    # --- Periodo actual -------------------------------------------------------

    def test_empty_dashboard_without_imports(self) -> None:
        response = self.service.compare(self.db)
        self.assertIsNone(response.period)
        self.assertIsNone(response.ese)
        self.assertIsNone(response.corhuila)
        self.assertIn("Comunicación escrita", response.note)

    def test_only_ese_rows_of_the_upload_period(self) -> None:
        self._import_ese("2026-1")

        response = self.service.compare(self.db)

        self.assertEqual(response.period, "2026-1")
        self.assertIsNone(response.corhuila)  # A la espera de CORHUILA.
        # 2026-1: Ana (M2), Carlos (M2) y los dos Mario (M2); no el histórico.
        self.assertEqual(response.ese.kpis.presentations, 4)
        self.assertEqual(response.filters.moments, [2])
        self.assertNotIn("comunicacion_escrita", response.ese.kpis.competencies)
        self.assertEqual(response.ese.weakest_competency.key, "lectura_critica")
        self.assertEqual(response.lowest_common_competency.key, "lectura_critica")
        self.assertIsNone(response.lowest_common_competency.corhuila_average)
        self.assertEqual(response.worst_program.name.upper(), "PROGRAMA B")
        self.assertEqual(response.worst_program.ese_average_level, 2)

    def test_both_tests_of_the_same_period(self) -> None:
        self._import_ese("2026-1")
        self._import_corhuila("2026-1")

        response = self.service.compare(self.db)

        self.assertEqual(response.period, "2026-1")
        self.assertEqual(response.corhuila.kpis.presentations, 4)
        # CORHUILA no trae documento: se cuentan personas por estudiante o correo.
        # Carlos aparece en dos filas (dos correos) y cuenta una sola vez.
        self.assertEqual(response.corhuila.kpis.unique_students, 3)
        names =[program.name.upper() for program in response.corhuila.programs]
        # "Sin programa" es un subprograma más y va al final.
        self.assertEqual(names[-1], "SIN PROGRAMA")
        self.assertEqual(response.corhuila.programs[-1].program_id, SIN_PROGRAMA_ID)
        self.assertEqual(response.filters.programs[-1].program_id, SIN_PROGRAMA_ID)
        self.assertIsNotNone(response.lowest_common_competency.corhuila_average)
        self.assertNotEqual(response.worst_program.program_id, SIN_PROGRAMA_ID)

    def test_new_period_shows_only_what_was_uploaded(self) -> None:
        self._import_ese("2026-1")
        self._import_corhuila("2026-1")
        self._import_corhuila("2026-2", CORHUILA_ROWS[:3])

        response = self.service.compare(self.db)

        # En 2026-2 solo se subió CORHUILA: ESE queda a la espera.
        self.assertEqual(response.period, "2026-2")
        self.assertIsNone(response.ese)
        self.assertEqual(response.corhuila.period, "2026-2")

    def test_choose_another_period(self) -> None:
        self._import_ese("2026-1")
        self._import_corhuila("2026-1")

        latest = self.service.compare(self.db)
        # Periodos con datos, del más reciente al más antiguo (ESE trae el histórico).
        self.assertEqual(latest.filters.periods, ["2026-1", "2025-2", "2025-1", "2024-1"])
        self.assertEqual(latest.selected_filters.period, "2026-1")
        self.assertEqual(latest.filters.corhuila_periods, ["2026-1"])

        older = self.service.compare(self.db, period="2025-1")
        self.assertEqual(older.period, "2025-1")
        self.assertEqual(older.selected_filters.period, "2025-1")
        self.assertEqual(older.ese.kpis.presentations, 2)
        self.assertIsNone(older.corhuila)  # No hay CORHUILA de 2025-1.
        # Solo se ofrecen los momentos del periodo elegido.
        self.assertEqual(older.filters.moments, [1])
        # La lista de periodos no cambia al elegir uno.
        self.assertEqual(older.filters.periods, latest.filters.periods)

        empty = self.service.compare(self.db, period="2030-1")
        self.assertIsNone(empty.ese)
        self.assertIsNone(empty.corhuila)
        self.assertEqual(empty.filters.moments, [])

    def test_ese_simulations_grouped_by_year(self) -> None:
        """El filtro de simulacro del módulo ESE solo ofrece los del año elegido."""
        self._import_ese("2026-1")

        filters = self.service.get_active_import(self.db).filters

        self.assertEqual(
            filters.simulations_by_year,
            {
                2024: ["SIMULACRO 2024-1 MOMENTO 4"],
                2025: ["SIMULACRO 2025-1 MOMENTO 1", "SIMULACRO 2025-2 MOMENTO 2"],
                2026: ["SIMULACRO 2026-1 MOMENTO 2"],
            },
        )
        # La lista completa sigue disponible para "Todos los años".
        self.assertEqual(
            sorted(filters.simulations),
            sorted(s for group in filters.simulations_by_year.values() for s in group),
        )

    def test_filters_by_moment_and_program(self) -> None:
        self._import_ese("2026-1")
        self._import_corhuila("2026-1")
        program_b = str(self._program_id("programa b"))

        by_program = self.service.compare(self.db, program_id=program_b)
        self.assertEqual(
            {p.name.upper() for p in by_program.ese.programs}, {"PROGRAMA B"}
        )
        self.assertEqual(
            {p.name.upper() for p in by_program.corhuila.programs}, {"PROGRAMA B"}
        )
        # El momento solo filtra ESE (CORHUILA tiene momento único).
        by_moment = self.service.compare(self.db, moment=1)
        self.assertEqual(by_moment.ese.kpis.presentations, 0)
        self.assertEqual(by_moment.corhuila.kpis.presentations, 4)

        without_program = self.service.compare(self.db, program_id=SIN_PROGRAMA_ID)
        self.assertEqual(without_program.ese.programs, [])
        self.assertEqual(
            [p.program_id for p in without_program.corhuila.programs],
            [SIN_PROGRAMA_ID],
        )

    def test_without_program_card_lists_its_students(self) -> None:
        self._import_ese("2026-1")
        corhuila = self._import_corhuila("2026-1")

        detail = self.service.get_program(
            self.db,
            corhuila.import_id,
            SIN_PROGRAMA_ID,
            DashboardFilterQuery(),
            None,
            1,
            50,
        )
        self.assertEqual(
            sorted(student.email for student in detail.students),
            ["mlopez@corhuila.edu.co", "nueva-2026a@corhuila.edu.co"],
        )

    # --- Programa manual ------------------------------------------------------

    def _corhuila_row(self, import_id: str, email: str) -> AcademicResult:
        return self.db.scalar(
            select(AcademicResult).where(
                AcademicResult.import_id == import_id,
                AcademicResult.email_source == email,
            )
        )

    def test_manual_program_resolves_a_pending_student(self) -> None:
        self._import_ese("2026-1")
        corhuila = self._import_corhuila("2026-2")
        pending = self._corhuila_row(corhuila.import_id, "nueva-2026a@corhuila.edu.co")
        program_a = self._program_id("programa a")
        self.service.compare(self.db)  # Llena la caché.

        result = self.service.assign_student_program(
            self.db, pending.student_id, program_a, self.admin
        )

        self.assertEqual((result.changed_rows, result.without_program), (1, 1))
        self.db.refresh(pending)
        self.assertEqual(
            (pending.program_id, pending.program_resolution), (program_a, "MANUAL")
        )
        student = self.db.get(AcademicStudent, pending.student_id)
        self.assertEqual(student.assigned_program_by_user_id, self.admin.id)
        # La caché se limpió: el dashboard ya lo muestra en su programa.
        names = {p.name.upper() for p in self.service.compare(self.db).corhuila.programs}
        self.assertIn("PROGRAMA A", names)
        self.assertEqual(
            [row.email_source for row in students_without_program(self.db)],
            ["mlopez@corhuila.edu.co"],
        )

    def test_manual_program_wins_over_ese_until_removed(self) -> None:
        self._import_ese("2026-1")
        corhuila = self._import_corhuila("2026-2")
        carlos = self._corhuila_row(corhuila.import_id, "otro@corhuila.edu.co")
        program_a = self._program_id("programa a")
        program_b = self._program_id("programa b")
        self.assertEqual(carlos.program_id, program_b)

        self.service.assign_student_program(
            self.db, carlos.student_id, program_a, self.admin
        )
        # Un ESE nuevo no lo pisa.
        self._import_ese("2026-1", global_score=91)
        self.db.refresh(carlos)
        self.assertEqual(
            (carlos.program_id, carlos.program_resolution), (program_a, "MANUAL")
        )

        self.service.assign_student_program(self.db, carlos.student_id, None, self.admin)
        self.db.refresh(carlos)
        self.assertEqual(
            (carlos.program_id, carlos.program_resolution), (program_b, "ESE")
        )

    def test_manual_program_rejects_unknown_ids(self) -> None:
        self._import_ese("2026-1")
        with self.assertRaises(ApplicationError) as error:
            self.service.assign_student_program(self.db, 9999, None, self.admin)
        self.assertEqual(error.exception.status_code, 404)
        some_student = self.db.scalar(select(AcademicStudent.id))
        with self.assertRaises(ApplicationError):
            self.service.assign_student_program(self.db, some_student, 9999, self.admin)

    def test_program_catalog_and_resolve(self) -> None:
        self._import_ese("2026-1")
        self._import_corhuila("2026-2")

        catalog = self.service.program_catalog(self.db)
        self.assertEqual(
            [p.name.upper() for p in catalog.programs], ["PROGRAMA A", "PROGRAMA B"]
        )
        result = self.service.resolve_corhuila(self.db)
        self.assertEqual((result.changed_rows, result.without_program), (0, 2))


class ProgramChangeQualityTests(unittest.TestCase):
    def test_counts_students_with_more_than_one_program(self) -> None:
        report = assess_data_quality(
            [
                {"usuario": "1", "programa": "VETERINARIA"},
                {"usuario": "1", "programa": "Ingeniería de Software"},
                {"usuario": "2", "programa": "MEDICINA"},
                {"usuario": "2", "programa": "medicina"},
            ]
        )
        self.assertEqual(report["identity"]["documents_with_multiple_programs"], 1)


if __name__ == "__main__":
    unittest.main()
