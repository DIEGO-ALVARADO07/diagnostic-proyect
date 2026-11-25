"""Fase 9.1: identidad por documento con correos como alias, búsqueda del
estudiante de CORHUILA (documento → correo → nombre completo) y Momento 4."""

import unittest
from uuid import uuid4

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from core.orm import Base, utcnow
from modules.excel.dtos.requests.dashboard import DashboardFilterQuery
from modules.excel.dtos.requests.read_workbook import ReadWorkbookRequest
from modules.excel.entities.academic import (
    AcademicProgram,
    AcademicResult,
    AcademicStudent,
    AcademicStudentEmail,
    ActiveImport,
    DashboardState,
    ExcelImport,
)
from modules.excel.services.dashboard_normalizer import email_key, normalized_key
from modules.excel.services.dashboard_service import DashboardService
from modules.excel.services.program_resolution import lookup_program
from modules.security.entities import Account
from modules.security.entities.role import Role
from tests.test_dashboard import make_dashboard_workbook


def ese_row(
    document: str,
    first_name: str,
    last_name: str,
    email: str,
    program: str,
    simulation: str,
    group: str,
    year: int,
) -> list[object]:
    """Fila de BD GEN en el orden de ``BD_HEADERS``."""
    return [
        document, first_name, last_name, email,
        150, 150, 150, 150, 150, 150,
        program, None, "SABER PRO", None, year, simulation,
        None, None, None, None, None,
        None, group, "Si", None, None,
    ]


EXTRA_ROWS = [
    # Carlos: correo institucional en M1 y personal en M2 (mismo documento).
    ese_row("201", "Carlos", "Ruiz", "CRuiz-2024a@corhuila.edu.co", "Programa B",
            "SIMULACRO 2025-1 MOMENTO 1", "MOMENTO 1", 2025),
    ese_row("201", "Carlos", "Ruiz", "carlos.ruiz@gmail.com", "Programa B",
            "SIMULACRO 2026-1 MOMENTO 2", "MOMENTO 2", 2026),
    # Dos personas con el mismo nombre completo y distinto documento.
    ese_row("301", "Mario", "López", "m1@x.co", "Programa A",
            "SIMULACRO 2026-1 MOMENTO 2", "MOMENTO 2", 2026),
    ese_row("302", "MARIO", "LOPEZ", "m2@x.co", "Programa B",
            "SIMULACRO 2026-1 MOMENTO 2", "MOMENTO 2", 2026),
    ese_row("401", "Sara", "Díaz", "sara@x.co", "Programa B",
            "SIMULACRO 2025-2 MOMENTO 2", "MOMENTO 2", 2025),
    # Momento 4: histórico de 2024.
    ese_row("501", "Elena", "Mora", "elena@x.co", "Programa A",
            "SIMULACRO 2024-1 MOMENTO 4", "MOMENTO 4", 2024),
]


class DocumentIdentityTests(unittest.TestCase):
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

    def _import(self):
        return self.service.import_workbook(
            ReadWorkbookRequest(
                filename="ese.xlsx",
                content=make_dashboard_workbook(extra_records=EXTRA_ROWS),
            ),
            self.admin,
            self.db,
        )

    def _seed_corhuila(self, period: str, rows: list[dict]) -> str:
        import_id = str(uuid4())
        self.db.add(
            ExcelImport(
                id=import_id,
                filename=f"corhuila-{period}.xlsx",
                source="CORHUILA",
                period=period,
                file_sha256=uuid4().hex + uuid4().hex,
                status="ACTIVE",
                activated_at=utcnow(),
            )
        )
        self.db.add(ActiveImport(slot=f"CORHUILA:{period}", import_id=import_id))
        for number, row in enumerate(rows, start=2):
            self.db.add(
                AcademicResult(
                    import_id=import_id,
                    source_row_number=number,
                    document_number_source=row.get("document"),
                    email_source=row.get("email"),
                    email_key=email_key(row.get("email")),
                    student_search_name=normalized_key(row.get("name")) or None,
                    program_name_raw="",
                    year=int(period[:4]),
                    period=period,
                    simulation_name=f"CORHUILA {period}",
                    simulation_key=f"corhuila {period}",
                )
            )
        self.db.commit()
        return import_id

    def _program_name(self, program_id: int | None) -> str | None:
        if program_id is None:
            return None
        return self.db.get(AcademicProgram, program_id).canonical_name.upper()

    def test_one_student_per_document_with_all_emails_as_aliases(self) -> None:
        response = self._import()

        carlos = self.db.scalar(
            select(AcademicStudent).where(AcademicStudent.document_number == "201")
        )
        aliases = set(
            self.db.scalars(
                select(AcademicStudentEmail.email_key).where(
                    AcademicStudentEmail.student_id == carlos.id
                )
            )
        )
        self.assertEqual(
            aliases, {"cruiz-2024a@corhuila.edu.co", "carlos.ruiz@gmail.com"}
        )
        # El correo principal es el institucional.
        self.assertEqual(carlos.email_key, "cruiz-2024a@corhuila.edu.co")
        self.assertEqual(
            self.db.scalar(
                select(func.count())
                .select_from(AcademicStudent)
                .where(AcademicStudent.document_number == "201")
            ),
            1,
        )
        # Con cualquiera de sus correos sale el historial completo.
        by_personal = self.service.get_student(
            self.db, response.import_id, "carlos.ruiz@gmail.com"
        )
        by_institutional = self.service.get_student(
            self.db, response.import_id, "cruiz-2024a@corhuila.edu.co"
        )
        self.assertEqual(len(by_personal.history), 2)
        self.assertEqual(by_personal.history, by_institutional.history)

    def test_reimport_keeps_one_student_and_aliases(self) -> None:
        self._import()
        self.service.import_workbook(
            ReadWorkbookRequest(
                filename="ese-2.xlsx",
                content=make_dashboard_workbook(
                    global_score=91, extra_records=EXTRA_ROWS
                ),
            ),
            self.admin,
            self.db,
        )
        self.assertEqual(
            self.db.scalar(select(func.count()).select_from(AcademicStudent)), 7
        )
        self.assertEqual(
            self.db.scalar(select(func.count()).select_from(AcademicStudentEmail)),
            8,
        )

    def test_names_with_several_documents_are_reported(self) -> None:
        response = self._import()

        identity = response.source_audit.data_quality.identity
        self.assertEqual(identity.names_with_multiple_documents, 1)
        self.assertEqual(identity.documents_with_multiple_emails, 1)

    def test_moment_four_is_kept_as_historical_moment(self) -> None:
        response = self._import()

        self.assertIn(4, response.filters.moments)
        moment_four = self.service.get_overview(
            self.db, response.import_id, DashboardFilterQuery(moment=4), 1, 50
        )
        self.assertEqual(moment_four.kpis.presentations, 1)
        elena = self.service.get_student(self.db, response.import_id, "501")
        self.assertEqual(
            (elena.history[0].moment, elena.history[0].semester_range), (4, "8–10")
        )

    def test_corhuila_rows_match_by_document_then_email_then_name(self) -> None:
        corhuila = self._seed_corhuila(
            "2026-2",
            [
                {"document": "201", "email": "otro@corhuila.edu.co", "name": "X"},
                {"email": "CRUIZ-2024a@corhuila.edu.co", "name": "Otro Nombre"},
                {"email": "sdiaz@corhuila.edu.co", "name": "SARA DIAZ"},
                {"email": "mlopez@corhuila.edu.co", "name": "Mario López"},
                {"email": "nadie@corhuila.edu.co", "name": "Nadie Nunca"},
            ],
        )

        self._import()

        rows = self.db.execute(
            select(
                AcademicResult.source_row_number,
                AcademicResult.student_match,
                AcademicResult.program_id,
                AcademicResult.program_resolution,
                AcademicResult.program_resolved_period,
            )
            .where(AcademicResult.import_id == corhuila)
            .order_by(AcademicResult.source_row_number)
        ).all()
        self.assertEqual(
            [
                (number, match, self._program_name(program), resolution, period)
                for number, match, program, resolution, period in rows
            ],
            [
                (2, "DOCUMENTO", "PROGRAMA B", "ESE_M2", "2026-1"),
                (3, "CORREO", "PROGRAMA B", "ESE_M2", "2026-1"),
                (4, "NOMBRE", "PROGRAMA B", "ESE_M2", "2025-2"),
                (5, "AMBIGUO", None, "SIN_PROGRAMA", None),
                (6, "SIN_COINCIDENCIA", None, "SIN_PROGRAMA", None),
            ],
        )
        carlos_id = self.db.scalar(
            select(AcademicStudent.id).where(AcademicStudent.document_number == "201")
        )
        self.assertEqual(
            self.db.scalar(
                select(AcademicResult.student_id).where(
                    AcademicResult.import_id == corhuila,
                    AcademicResult.source_row_number == 2,
                )
            ),
            carlos_id,
        )

    def test_program_lookup(self) -> None:
        self._import()

        by_document = lookup_program(self.db, document="201", corhuila_period="2026-2")
        self.assertEqual(by_document.match, "DOCUMENTO")
        self.assertEqual(by_document.program.upper(), "PROGRAMA B")
        self.assertEqual(by_document.moment_two_period, "2026-1")
        self.assertEqual(
            by_document.emails,
            ["carlos.ruiz@gmail.com", "cruiz-2024a@corhuila.edu.co"],
        )
        # Antes de 2026-1 aún no tenía Momento 2.
        earlier = lookup_program(self.db, document="201", corhuila_period="2025-2")
        self.assertEqual((earlier.match, earlier.program), ("DOCUMENTO", None))
        by_name = lookup_program(self.db, full_name="sara  DÍAZ")
        self.assertEqual((by_name.match, by_name.document), ("NOMBRE", "401"))
        self.assertEqual(lookup_program(self.db, full_name="Mario Lopez").match, "AMBIGUO")


if __name__ == "__main__":
    unittest.main()
