"""Fase 9: identidad por correo y programa de CORHUILA tomado de ESE Momento 2."""

import unittest
from hashlib import sha256
from uuid import uuid4

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from core.orm import Base, utcnow
from modules.excel.dtos.requests.read_workbook import ReadWorkbookRequest
from modules.excel.entities.academic import (
    AcademicResult,
    AcademicStudent,
    ActiveImport,
    DashboardState,
    ExcelImport,
)
from modules.excel.services.dashboard_data_quality import assess_data_quality
from modules.excel.services.dashboard_normalizer import email_key
from modules.excel.services.dashboard_service import DashboardService
from modules.excel.services.program_resolution import (
    MomentTwoRow,
    choose_moment_two,
)
from modules.security.entities import Account
from modules.security.entities.role import Role
from tests.test_dashboard import make_dashboard_workbook


class EmailRuleTests(unittest.TestCase):
    def test_email_key_is_lower_case_without_spaces(self) -> None:
        self.assertEqual(
            email_key(" Ana.Perez @Corhuila.EDU.co "), "ana.perez@corhuila.edu.co"
        )
        self.assertIsNone(email_key("sin correo"))
        self.assertIsNone(email_key(None))

    def test_identity_quality_counts_conflicts(self) -> None:
        report = assess_data_quality(
            [
                {"usuario": "1", "dirección de correo": "a@x.co"},
                {"usuario": "2", "dirección de correo": "A@x.co"},
                {"usuario": "3", "dirección de correo": "b@x.co"},
                {"usuario": "3", "dirección de correo": "c@x.co"},
                {"usuario": "4", "dirección de correo": None},
            ]
        )
        self.assertEqual(
            report["identity"],
            {
                "rows_without_email": 1,
                "emails_with_multiple_documents": 1,
                "documents_with_multiple_emails": 1,
                "names_with_multiple_documents": 0,
            },
        )


class MomentTwoChoiceTests(unittest.TestCase):
    def test_latest_moment_two_not_after_corhuila(self) -> None:
        rows = [
            MomentTwoRow("2025-1", 10, 1),
            MomentTwoRow("2026-1", 20, 2),
            MomentTwoRow("2026-2", 30, 3),
        ]
        self.assertEqual(choose_moment_two(rows, "2026-1").program_id, 2)
        self.assertEqual(choose_moment_two(rows, "2026-2").program_id, 3)
        self.assertIsNone(choose_moment_two(rows, "2024-2"))

    def test_undated_moment_two_only_when_nothing_else(self) -> None:
        self.assertEqual(
            choose_moment_two([MomentTwoRow(None, 5, 7)], "2026-2").program_id, 7
        )
        self.assertEqual(
            choose_moment_two(
                [MomentTwoRow(None, 5, 7), MomentTwoRow("2026-1", 3, 8)], "2026-2"
            ).program_id,
            8,
        )


class StudentIdentityTests(unittest.TestCase):
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

    def _import(self, global_score: object = 90):
        return self.service.import_workbook(
            ReadWorkbookRequest(
                filename="ese.xlsx",
                content=make_dashboard_workbook(global_score=global_score),
            ),
            self.admin,
            self.db,
        )

    def _seed_corhuila(self, period: str, emails: list[str]) -> str:
        """Importación de CORHUILA con filas sin programa (su lector llega en la fase 10)."""
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
        for row, email in enumerate(emails, start=2):
            self.db.add(
                AcademicResult(
                    import_id=import_id,
                    source_row_number=row,
                    email_source=email,
                    email_key=email_key(email),
                    program_name_raw="",
                    year=int(period[:4]),
                    period=period,
                    simulation_name=f"CORHUILA {period}",
                    simulation_key=f"corhuila {period}",
                )
            )
        self.db.commit()
        return import_id

    def _corhuila_programs(self, import_id: str) -> dict[str, tuple]:
        return {
            email: (resolution, period, program_id is not None)
            for email, resolution, period, program_id in self.db.execute(
                select(
                    AcademicResult.email_key,
                    AcademicResult.program_resolution,
                    AcademicResult.program_resolved_period,
                    AcademicResult.program_id,
                ).where(AcademicResult.import_id == import_id)
            )
        }

    def test_one_student_per_email_across_imports(self) -> None:
        self._import()
        self._import(global_score=91)

        students = self.db.execute(
            select(AcademicStudent.email_key, AcademicStudent.document_number)
            .order_by(AcademicStudent.email_key)
        ).all()
        self.assertEqual(
            students, [("ana@example.com", "101"), ("luis@example.com", "102")]
        )

    def test_student_can_be_queried_by_email_or_document(self) -> None:
        response = self._import()

        by_email = self.service.get_student(
            self.db, response.import_id, "ANA@example.com"
        )
        by_document = self.service.get_student(self.db, response.import_id, "101")

        self.assertEqual(len(by_email.history), 2)
        self.assertEqual(by_email.history, by_document.history)
        self.assertEqual(by_email.document, "101")

    def test_student_without_email_from_before_is_adopted(self) -> None:
        # Estudiante guardado antes de la fase 9: solo documento.
        self.db.add(
            AcademicStudent(
                document_key=sha256(b"101").hexdigest(),
                document_number="101",
                created_at=utcnow(),
                updated_at=utcnow(),
            )
        )
        self.db.commit()

        self._import()

        self.assertEqual(
            self.db.scalar(select(func.count()).select_from(AcademicStudent)), 2
        )
        self.assertEqual(
            self.db.scalar(
                select(AcademicStudent.email_key).where(
                    AcademicStudent.document_number == "101"
                )
            ),
            "ana@example.com",
        )

    def test_new_ese_import_resolves_and_stores_corhuila_programs(self) -> None:
        # Ana: M1 en 2025-1 y M2 en 2026-1 (Programa A). Luis: solo M1.
        current = self._seed_corhuila(
            "2026-2", ["Ana@Example.com", "luis@example.com", "otra@example.com"]
        )
        earlier = self._seed_corhuila("2025-2", ["ana@example.com"])

        ese = self._import()

        self.assertEqual(
            self._corhuila_programs(current),
            {
                "ana@example.com": ("ESE_M2", "2026-1", True),
                "luis@example.com": ("SIN_PROGRAMA", None, False),
                "otra@example.com": ("SIN_PROGRAMA", None, False),
            },
        )
        # En 2025-2 Ana aún no tenía Momento 2.
        self.assertEqual(
            self._corhuila_programs(earlier),
            {"ana@example.com": ("SIN_PROGRAMA", None, False)},
        )
        self.assertEqual(
            self.db.scalar(
                select(AcademicResult.program_resolved_import_id).where(
                    AcademicResult.import_id == current,
                    AcademicResult.email_key == "ana@example.com",
                )
            ),
            ese.import_id,
        )
        ese_program = self.db.scalar(
            select(AcademicResult.program_id).where(
                AcademicResult.import_id == ese.import_id,
                AcademicResult.moment == 2,
            )
        )
        self.assertEqual(
            self.db.scalar(
                select(AcademicResult.program_id).where(
                    AcademicResult.import_id == current,
                    AcademicResult.email_key == "ana@example.com",
                )
            ),
            ese_program,
        )


if __name__ == "__main__":
    unittest.main()
