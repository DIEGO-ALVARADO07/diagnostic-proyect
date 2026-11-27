"""Fase 14b: CORHUILA toma programa, documento y semestre de matriculados."""

import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from core.orm import Base
from modules.enrollment.service import EnrollmentService
from modules.excel.dtos.requests.read_workbook import ReadWorkbookRequest
from modules.excel.entities.academic import (
    AcademicProgram,
    AcademicResult,
    AcademicResultProgram,
    AcademicStudent,
    DashboardState,
)
from modules.excel.entities.assessment import Source
from modules.excel.services.dashboard_service import DashboardService
from modules.security.entities import Account
from modules.security.entities.role import Role
from tests.test_corhuila_import import make_corhuila_workbook
from tests.test_dashboard import make_dashboard_workbook
from tests.test_document_identity import EXTRA_ROWS
from tests.test_enrollment import make_enrollment_workbook, row


ENROLLMENT_ROWS = [
    # Nueva Persona (no está en ESE): doble programa; su correo de CORHUILA es
    # el institucional.
    row("INGENIERIA DE SISTEMAS", "5", "C", "3001", "2024000010", "NUEVA", "PERSONA",
        "nueva-2026a@corhuila.edu.co"),
    row("MEDICINA VETERINARIA Y ZOOTECNIA", "6", "C", "3001", "2024000010", "NUEVA",
        "PERSONA", "nueva-2026a@corhuila.edu.co"),
    # Sara (documento 401 en ESE, Programa B): en CORHUILA usa este correo, que
    # aquí es el personal. Matriculados manda sobre ESE.
    row("MERCADEO Y PUBLICIDAD", "4", "T", "401", "2025000011", "SARA", "DIAZ",
        "sara.inst@corhuila.edu.co"),
    # Mario: el nombre coincide, pero ningún correo → no se cruza.
    row("INGENIERIA INDUSTRIAL", "3", "C", "3003", "2024000012", "MARIO", "LOPEZ",
        "otro.mario@corhuila.edu.co"),
]


def enrollment_rows() -> list[list[object]]:
    rows = [list(item) for item in ENROLLMENT_ROWS]
    rows[2][14] = "sdiaz-2024b@corhuila.edu.co"  # EMAIL_PERSONAL de Sara
    return rows


class EnrollmentMatchingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.admin = Account(
            id=1, username="admin", email="admin@example.com", full_name="Admin",
            password_hash="unused", role=Role.SUPERADMIN.value, is_active=True,
        )
        self.db.add_all([self.admin, DashboardState(id=1)])
        self.db.commit()
        self.service = DashboardService()
        self.enrollment = EnrollmentService(on_change=self.service.loader.cache.clear)

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def _import_ese(self) -> None:
        self.service.import_workbook(
            ReadWorkbookRequest(
                filename="ese.xlsx",
                content=make_dashboard_workbook(extra_records=EXTRA_ROWS),
            ),
            self.admin, self.db, Source.ESE, "2026-1",
        )

    def _import_corhuila(self):
        return self.service.import_workbook(
            ReadWorkbookRequest(filename="corhuila.xlsx", content=make_corhuila_workbook()),
            self.admin, self.db, Source.CORHUILA, "2026-2",
        )

    def _import_enrollment(self):
        return self.enrollment.import_file(
            self.db, self.admin, "matriculados.xlsx",
            make_enrollment_workbook(enrollment_rows()), "2026-2",
        )

    def _corhuila_row(self, import_id: str, email: str) -> AcademicResult:
        return self.db.scalar(
            select(AcademicResult).where(
                AcademicResult.import_id == import_id,
                AcademicResult.email_key == email,
            )
        )

    def _program_name(self, program_id: int | None) -> str | None:
        program = self.db.get(AcademicProgram, program_id) if program_id else None
        return program.canonical_name if program else None

    def _check_rows(self, import_id: str) -> None:
        nueva = self._corhuila_row(import_id, "nueva-2026a@corhuila.edu.co")
        self.assertEqual(nueva.student_match, "MATRICULADOS")
        self.assertEqual(nueva.program_resolution, "MATRICULADOS")
        self.assertEqual(nueva.program_resolved_period, "2026-2")
        self.assertEqual(self._program_name(nueva.program_id), "INGENIERIA DE SISTEMAS")
        extras = self.db.scalars(
            select(AcademicResultProgram.program_id).where(
                AcademicResultProgram.result_id == nueva.id
            )
        ).all()
        self.assertEqual(
            [self._program_name(extra) for extra in extras],
            ["MEDICINA VETERINARIA Y ZOOTECNIA"],
        )
        self.assertEqual(nueva.semester_raw, "SEMESTRE 5")
        student = self.db.get(AcademicStudent, nueva.student_id)
        self.assertEqual((student.document_type, student.document_number), ("C", "3001"))

        # Sara: su correo de CORHUILA es el personal de matriculados; queda con
        # el mismo estudiante de ESE (documento 401) y el programa de matriculados.
        sara = self._corhuila_row(import_id, "sdiaz-2024b@corhuila.edu.co")
        self.assertEqual(sara.program_resolution, "MATRICULADOS")
        self.assertEqual(self._program_name(sara.program_id), "MERCADEO Y PUBLICIDAD")
        sara_student = self.db.get(AcademicStudent, sara.student_id)
        self.assertEqual(sara_student.document_number, "401")
        self.assertEqual(sara_student.document_type, "T")

        # Mario: nombre sí, correo no → sigue la regla de ESE (nombre ambiguo).
        mario = self._corhuila_row(import_id, "mlopez@corhuila.edu.co")
        self.assertEqual(mario.student_match, "AMBIGUO")
        self.assertEqual(mario.program_resolution, "SIN_PROGRAMA")
        self.assertIsNone(mario.semester_raw)

        # Carlos trae su documento en CORHUILA, pero no está en matriculados: ESE.
        carlos = self.db.scalars(
            select(AcademicResult).where(
                AcademicResult.import_id == import_id,
                AcademicResult.document_number_source == "201",
            )
        ).one()
        self.assertEqual(carlos.program_resolution, "ESE")

    def test_enrollment_first_then_corhuila(self) -> None:
        self._import_ese()
        self._import_enrollment()
        corhuila = self._import_corhuila()
        self._check_rows(corhuila.import_id)

    def test_enrollment_fills_type_of_ese_students(self) -> None:
        self._import_ese()
        rows = enrollment_rows() + [row(
            "INGENIERIA INDUSTRIAL", "8", "C", "501", "2020000001", "ELENA", "MORA",
            "emora@corhuila.edu.co",
        )]
        self.enrollment.import_file(
            self.db, self.admin, "m.xlsx", make_enrollment_workbook(rows), "2026-2"
        )
        elena = self.db.scalar(
            select(AcademicStudent).where(AcademicStudent.document_number == "501")
        )
        self.assertEqual(elena.document_type, "C")

    def test_corhuila_first_then_enrollment_updates_rows(self) -> None:
        self._import_ese()
        corhuila = self._import_corhuila()
        nueva = self._corhuila_row(corhuila.import_id, "nueva-2026a@corhuila.edu.co")
        self.assertEqual(nueva.program_resolution, "SIN_PROGRAMA")

        upload = self._import_enrollment()
        self.assertGreaterEqual(upload.corhuila_rows_updated, 2)
        self.db.expire_all()
        self._check_rows(corhuila.import_id)

    def test_double_program_counts_in_both_programs(self) -> None:
        self._import_ese()
        self._import_enrollment()
        self._import_corhuila()

        compare = self.service.compare(self.db, period="2026-2")
        corhuila_programs = {
            item.name: item for item in compare.corhuila.programs
        }
        self.assertIn("INGENIERIA DE SISTEMAS", corhuila_programs)
        self.assertIn("MEDICINA VETERINARIA Y ZOOTECNIA", corhuila_programs)

        students = self.service.student_levels.list(self.db, period="2026-2")
        nueva = [item for item in students.students if item.document == "3001"]
        self.assertEqual(
            sorted(item.program for item in nueva),
            ["INGENIERIA DE SISTEMAS", "MEDICINA VETERINARIA Y ZOOTECNIA"],
        )
        self.assertEqual({item.level for item in nueva}, {nueva[0].level})
        self.assertEqual({item.document_type for item in nueva}, {"C"})
        # Carlos (ESE, documento 201) no está en matriculados: sin tipo.
        carlos = self.db.scalar(
            select(AcademicStudent).where(AcademicStudent.document_number == "201")
        )
        self.assertIsNone(carlos.document_type)
        self.assertEqual(len({item.student_key for item in nueva}), 2)

    def test_replacing_enrollment_removes_extra_program(self) -> None:
        self._import_ese()
        self._import_enrollment()
        corhuila = self._import_corhuila()
        single = enrollment_rows()
        del single[1]  # Nueva Persona ya solo en Sistemas
        self.enrollment.import_file(
            self.db, self.admin, "matriculados-v2.xlsx",
            make_enrollment_workbook(single), "2026-2",
        )
        self.db.expire_all()
        nueva = self._corhuila_row(corhuila.import_id, "nueva-2026a@corhuila.edu.co")
        self.assertEqual(
            self.db.scalars(
                select(AcademicResultProgram).where(
                    AcademicResultProgram.result_id == nueva.id
                )
            ).all(),
            [],
        )


if __name__ == "__main__":
    unittest.main()
