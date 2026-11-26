"""Fase 10: importación del Excel de CORHUILA."""

import unittest

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from core.exceptions import ApplicationError
from core.orm import Base
from modules.excel.dtos.requests.dashboard import DashboardFilterQuery
from modules.excel.dtos.requests.read_workbook import ReadWorkbookRequest
from modules.excel.entities.academic import (
    AcademicResult,
    AcademicStudent,
    AcademicStudentEmail,
    ActiveImport,
    DashboardState,
    ExcelImport,
)
from modules.excel.entities.assessment import Source
from modules.excel.services.dashboard_service import DashboardService
from modules.excel.services.program_resolution import students_without_program
from modules.security.entities import Account
from modules.security.entities.role import Role
from tests.test_dashboard import make_dashboard_workbook, make_workbook
from tests.test_document_identity import EXTRA_ROWS

CORHUILA_HEADERS = [
    "Nombre",
    "Apellido(s)",
    "Número de ID",
    "Institución",
    "Departamento",
    "Dirección de correo",
    "Cuestionario:Lectura crítica (Real)",
    "Cuestionario:Razonamiento cuantitativo (Real)",
    "Cuestionario:Competencias ciudadanas (Real)",
    "Cuestionario:Inglés (Real)",
    "Última descarga de este curso",
]


def corhuila_row(
    first: str,
    last: str,
    email: str,
    scores: tuple[object, object, object, object],
    document: str | None = None,
) -> list[object]:
    return [first, last, document, "CORHUILA", None, email, *scores, "1795558359"]


CORHUILA_ROWS = [
    # Documento de Carlos (ESE M2 2026-1, Programa B).
    corhuila_row("CARLOS", "RUIZ", "otro@corhuila.edu.co", (200, 120, 0, 300), "201"),
    # Nombre de Carlos (con otro correo) → mismo estudiante.
    corhuila_row("Carlos", "Ruiz", "CRUIZ-2024a@corhuila.edu.co", (180, "-", 150, 160)),
    # Nombre completo único de Sara (ESE M2 2025-2).
    corhuila_row("SARA", "DIAZ", "sdiaz-2024b@corhuila.edu.co", (130, 140, 150, 160)),
    # Nombre repetido en ESE → ambiguo, sin programa.
    corhuila_row("MARIO", "LOPEZ", "mlopez@corhuila.edu.co", ("-", "-", "-", "-")),
    # No está en ESE → se crea, sin programa.
    corhuila_row("NUEVA", "PERSONA", "nueva-2026a@corhuila.edu.co", (90, 100, 110, 120)),
]


def make_corhuila_workbook(rows: list[list[object]] | None = None) -> bytes:
    return make_workbook(
        [("Calificaciones", [CORHUILA_HEADERS, *(rows or CORHUILA_ROWS)])]
    )


class CorhuilaImportTests(unittest.TestCase):
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

    def _import_ese(self, period: str = "2026-1", **options):
        return self.service.import_workbook(
            ReadWorkbookRequest(
                filename="ese.xlsx",
                content=make_dashboard_workbook(extra_records=EXTRA_ROWS, **options),
            ),
            self.admin,
            self.db,
            Source.ESE,
            period,
        )

    def _import_corhuila(self, period: str = "2026-2", content: bytes | None = None):
        return self.service.import_workbook(
            ReadWorkbookRequest(
                filename=f"corhuila-{period}.xlsx",
                content=content or make_corhuila_workbook(),
            ),
            self.admin,
            self.db,
            Source.CORHUILA,
            period,
        )

    def _rows(self, import_id: str) -> list[tuple]:
        return self.db.execute(
            select(
                AcademicResult.source_row_number,
                AcademicResult.student_match,
                AcademicResult.program_resolution,
                AcademicResult.program_resolved_period,
                AcademicResult.applies_simulacro,
            )
            .where(AcademicResult.import_id == import_id)
            .order_by(AcademicResult.source_row_number)
        ).all()

    def test_corhuila_rows_are_stored_with_student_and_program(self) -> None:
        self._import_ese()
        response = self._import_corhuila()

        self.assertEqual(response.source, "CORHUILA")
        self.assertEqual(response.period, "2026-2")
        self.assertEqual(
            self._rows(response.import_id),
            [
                (2, "DOCUMENTO", "ESE", "2026-1", True),
                # El nombre completo es la regla principal (el correo puede variar).
                (3, "NOMBRE", "ESE", "2026-1", True),
                (4, "NOMBRE", "ESE", "2025-2", True),
                (5, "AMBIGUO", "SIN_PROGRAMA", None, False),
                (6, "SIN_COINCIDENCIA", "SIN_PROGRAMA", None, True),
            ],
        )
        quality = response.source_audit.data_quality.corhuila
        self.assertEqual(
            (
                quality.rows,
                quality.presented,
                quality.not_presented,
                quality.partially_presented,
                quality.rows_with_document,
                quality.without_program,
            ),
            (5, 4, 1, 1, 1, 2),
        )
        self.assertEqual(
            quality.matches,
            {
                "DOCUMENTO": 1,
                "CORREO": 0,
                "NOMBRE": 2,
                "AMBIGUO": 1,
                "SIN_COINCIDENCIA": 1,
            },
        )

    def test_scores_follow_the_same_rules_as_ese(self) -> None:
        self._import_ese()
        response = self._import_corhuila()

        overview = self.service.get_overview(
            self.db, response.import_id, DashboardFilterQuery(), 1, 50
        )
        # Mario no presentó (todo "-"); el 0 de Carlos cuenta.
        self.assertEqual(overview.kpis.presentations, 4)
        self.assertEqual(overview.kpis.not_presented_records, 1)
        self.assertNotIn("comunicacion_escrita", overview.kpis.competencies)
        citizenship = overview.kpis.competencies["competencias_ciudadanas"]
        self.assertEqual(citizenship.count, 4)
        self.assertEqual(citizenship.average, (0 + 150 + 150 + 110) / 4)
        quantitative = overview.kpis.competencies["razonamiento_cuantitativo"]
        self.assertEqual(quantitative.count, 3)
        names = {program.name.upper() for program in overview.programs}
        self.assertEqual(names, {"PROGRAMA B", "SIN PROGRAMA"})

    def test_matched_students_are_reused_and_new_ones_created(self) -> None:
        self._import_ese()
        students_before = self.db.scalar(
            select(func.count()).select_from(AcademicStudent)
        )
        self._import_corhuila()

        # Solo se crean Mario (ambiguo) y la persona nueva.
        self.assertEqual(
            self.db.scalar(select(func.count()).select_from(AcademicStudent)),
            students_before + 2,
        )
        carlos_id = self.db.scalar(
            select(AcademicStudent.id).where(AcademicStudent.document_number == "201")
        )
        # El correo de CORHUILA de Carlos queda como alias suyo.
        self.assertEqual(
            self.db.scalar(
                select(AcademicStudentEmail.student_id).where(
                    AcademicStudentEmail.email_key == "otro@corhuila.edu.co"
                )
            ),
            carlos_id,
        )

    def test_review_list_has_students_without_program(self) -> None:
        self._import_ese()
        self._import_corhuila()

        review = students_without_program(self.db)

        self.assertEqual(
            [(row.email_source, row.student_match) for row in review],
            [
                ("mlopez@corhuila.edu.co", "AMBIGUO"),
                ("nueva-2026a@corhuila.edu.co", "SIN_COINCIDENCIA"),
            ],
        )
        self.assertEqual(students_without_program(self.db, "2025-1"), [])

    def test_later_ese_import_resolves_pending_students(self) -> None:
        corhuila = self._import_corhuila()
        # Sin ESE activo, todos quedan por revisar.
        self.assertEqual(len(students_without_program(self.db)), 5)

        self._import_ese()

        self.assertEqual(
            [row[1] for row in self._rows(corhuila.import_id)],
            ["DOCUMENTO", "NOMBRE", "NOMBRE", "AMBIGUO", "SIN_COINCIDENCIA"],
        )
        self.assertEqual(len(students_without_program(self.db)), 2)

    def test_corhuila_and_ese_have_separate_active_slots(self) -> None:
        ese = self._import_ese()
        first = self._import_corhuila("2026-1")
        second = self._import_corhuila(
            "2026-2",
            make_corhuila_workbook(CORHUILA_ROWS[:2]),
        )

        slots = dict(self.db.execute(select(ActiveImport.slot, ActiveImport.import_id)).all())
        self.assertEqual(
            slots,
            {
                "ESE": ese.import_id,
                "CORHUILA:2026-1": first.import_id,
                "CORHUILA:2026-2": second.import_id,
            },
        )
        self.assertEqual(self.db.get(ExcelImport, ese.import_id).period, "2026-1")

    def test_ese_reports_rows_of_the_upload_period(self) -> None:
        response = self._import_ese("2026-1")
        self.assertEqual(
            response.source_audit.data_quality.period_moment.upload_period_rows, 4
        )

    def test_same_file_is_not_imported_twice(self) -> None:
        first = self._import_corhuila()
        again = self._import_corhuila()
        self.assertEqual(first.import_id, again.import_id)

    def test_corhuila_requires_period_and_its_sheet(self) -> None:
        with self.assertRaises(ApplicationError) as missing_period:
            self.service.import_workbook(
                ReadWorkbookRequest(filename="c.xlsx", content=make_corhuila_workbook()),
                self.admin,
                self.db,
                Source.CORHUILA,
                None,
            )
        self.assertEqual(missing_period.exception.status_code, 422)

        with self.assertRaises(ApplicationError) as wrong_file:
            self._import_corhuila(content=make_dashboard_workbook())
        self.assertEqual(wrong_file.exception.status_code, 422)
        self.assertIn("Calificaciones", wrong_file.exception.detail)

    def test_other_sheet_name_with_the_right_headers_is_accepted(self) -> None:
        content = make_workbook(
            [("Notas", [CORHUILA_HEADERS, *CORHUILA_ROWS[:1]])]
        )
        response = self._import_corhuila(content=content)
        self.assertEqual(response.source_audit.data_quality.corhuila.sheet, "Notas")


if __name__ == "__main__":
    unittest.main()
