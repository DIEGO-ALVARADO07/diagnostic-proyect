"""Fase 14a: archivo de matriculados por periodo (solo superadmin)."""

import unittest

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from core.exceptions import ApplicationError
from core.orm import Base
from modules.enrollment.entities import (
    UPLOAD_ACTIVE,
    UPLOAD_REPLACED,
    EnrollmentRecord,
    EnrollmentUpload,
)
from modules.enrollment.service import EnrollmentService, document_key, period_from_code
from modules.security.entities import Account
from modules.security.entities.role import Role
from tests.test_dashboard import make_workbook

HEADERS = [
    "COD_PERIODO", "COD_PENSUM", "PROGRAMA", "SEMESTRE", "TIP_IDENTIFICACION",
    "IDENTIFICACION", "CODIGO", "NOMBRES", "APELLIDOS", "ESTRATO", "GENERO",
    "FNACIMIENTO", "TELEFONO", "MOVIL", "EMAIL_PERSONAL", "EMAIL_INSTITUCIONAL",
]


def row(program, semester, doc_type, document, code, first, last, email, period="20262"):
    return [
        period, "50D", program, semester, doc_type, document, code, first, last,
        "2", "F", "2004-03-15 00:00:00", "6080000000", "3000000000",
        f"{first.lower()}@gmail.com", email,
    ]


ROWS = [
    row("INGENIERIA DE SISTEMAS", "3", "C", "1001", "2024000001", "ANA MARIA", "PEREZ GOMEZ", "aperez-2024a@corhuila.edu.co"),
    # Ana también está en Medicina: doble programa, dos filas.
    row("MEDICINA VETERINARIA Y ZOOTECNIA", "5", "C", "1001", "2024000001", "ANA MARIA", "PEREZ GOMEZ", "aperez-2024a@corhuila.edu.co"),
    row("INGENIERÍA DE SISTEMAS", "1", "T", "1002", "2026000002", "LUIS", "DIAZ", "ldiaz-2026a@corhuila.edu.co"),
    # Fila repetida (mismo documento y programa, con tilde distinta): se omite.
    row("Ingenieria de Sistemas", "1", "T", "1002", "2026000002", "LUIS", "DIAZ", "ldiaz-2026a@corhuila.edu.co"),
    # Sin documento: se rechaza.
    row("INGENIERIA INDUSTRIAL", "2", "C", None, "2025000003", "SIN", "DOCUMENTO", "x@corhuila.edu.co"),
]


def make_enrollment_workbook(rows=None) -> bytes:
    return make_workbook([("Exportar Hoja de Trabajo", [HEADERS, *(rows or ROWS)])])


class EnrollmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.admin = Account(
            id=1, username="admin", email="admin@example.com", full_name="Admin",
            password_hash="unused", role=Role.SUPERADMIN.value, is_active=True,
        )
        self.db.add(self.admin)
        self.db.commit()
        self.service = EnrollmentService()

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def _import(self, content=None, period="2026-2", filename="matriculados.xlsx"):
        return self.service.import_file(
            self.db, self.admin, filename, content or make_enrollment_workbook(), period
        )

    def test_period_code(self) -> None:
        self.assertEqual(period_from_code("20262"), "2026-2")
        self.assertEqual(period_from_code("2026-1"), "2026-1")
        self.assertIsNone(period_from_code("2026"))

    def test_import_keeps_double_program_and_skips_bad_rows(self) -> None:
        upload = self._import()
        self.assertEqual(upload.rows, 3)
        self.assertEqual(upload.students, 2)
        self.assertEqual(upload.double_program, 1)
        self.assertEqual(upload.rejected, 1)
        self.assertEqual(upload.duplicates, 1)
        self.assertFalse(upload.replaced_previous)

        ana = self.db.scalars(
            select(EnrollmentRecord).where(EnrollmentRecord.document_key == document_key("1001"))
        ).all()
        self.assertEqual(len(ana), 2)
        record = ana[0]
        self.assertEqual(record.period, "2026-2")
        self.assertEqual(record.document_type, "C")
        self.assertEqual(record.student_code, "2024000001")
        self.assertEqual(record.stratum, 2)
        self.assertEqual(record.birth_date.isoformat(), "2004-03-15")
        self.assertEqual(record.institutional_email_key, "aperez-2024a@corhuila.edu.co")
        self.assertEqual(record.personal_email_key, "ana maria@gmail.com".replace(" ", ""))

    def test_list_filters_and_search(self) -> None:
        self._import()
        result = self.service.list_records(self.db)
        self.assertEqual(result.period, "2026-2")
        self.assertEqual(result.filtered_total, 3)
        self.assertEqual(result.filtered_students, 2)
        self.assertEqual([u.period for u in result.uploads], ["2026-2"])
        self.assertEqual(
            {option.label: option.count for option in result.filters.programs},
            {"INGENIERIA DE SISTEMAS": 2, "MEDICINA VETERINARIA Y ZOOTECNIA": 1},
        )
        self.assertEqual(
            {option.value: option.label for option in result.filters.document_types},
            {"C": "Cédula de ciudadanía", "T": "Tarjeta de identidad"},
        )
        ana = [item for item in result.items if item.document_number == "1001"]
        self.assertEqual([item.programs_count for item in ana], [2, 2])

        sistemas = self.service.list_records(self.db, program="ingenieria de sistemas")
        self.assertEqual(sistemas.filtered_total, 2)
        first_semester = self.service.list_records(self.db, semester=1)
        self.assertEqual([i.document_number for i in first_semester.items], ["1002"])
        by_name = self.service.list_records(self.db, search="pérez ana")
        self.assertEqual(by_name.filtered_total, 2)
        by_code = self.service.list_records(self.db, search="2026000002")
        self.assertEqual(by_code.filtered_students, 1)
        by_type = self.service.list_records(self.db, document_type="T")
        self.assertEqual(by_type.filtered_total, 1)

    def test_reupload_replaces_previous_and_deletes_its_rows(self) -> None:
        first = self._import()
        second = self._import(make_enrollment_workbook(ROWS[:1]))
        self.assertTrue(second.replaced_previous)
        old = self.db.get(EnrollmentUpload, first.id)
        self.assertEqual(old.status, UPLOAD_REPLACED)
        self.assertIsNotNone(old.replaced_at)
        self.assertEqual(self.db.get(EnrollmentUpload, second.id).status, UPLOAD_ACTIVE)
        self.assertEqual(
            self.db.scalar(select(func.count()).select_from(EnrollmentRecord)), 1
        )

    def test_same_file_twice_is_rejected(self) -> None:
        self._import()
        with self.assertRaises(ApplicationError) as error:
            self._import()
        self.assertEqual(error.exception.status_code, 409)

    def test_period_must_match_file(self) -> None:
        with self.assertRaises(ApplicationError) as error:
            self._import(period="2026-1")
        self.assertEqual(error.exception.status_code, 422)
        self.assertIn("2026-2", error.exception.detail)

    def test_missing_columns_and_bad_extension(self) -> None:
        content = make_workbook([("Hoja", [["NOMBRE", "CORREO", "OTRA"], ["a", "b", "c"]])])
        with self.assertRaises(ApplicationError) as error:
            self._import(content)
        self.assertIn("PROGRAMA", error.exception.detail)
        with self.assertRaises(ApplicationError) as error:
            self._import(filename="datos.csv")
        self.assertEqual(error.exception.status_code, 415)

    def test_periods_are_listed_separately(self) -> None:
        self._import()
        self._import(make_enrollment_workbook([row(
            "INGENIERIA INDUSTRIAL", "4", "C", "2001", "2023000009", "EVA", "RUIZ",
            "eruiz@corhuila.edu.co", period="20261",
        )]), period="2026-1")
        result = self.service.list_records(self.db)
        self.assertEqual([u.period for u in result.uploads], ["2026-2", "2026-1"])
        self.assertEqual(result.period, "2026-2")
        older = self.service.list_records(self.db, period="2026-1")
        self.assertEqual([i.document_number for i in older.items], ["2001"])
        none = self.service.list_records(self.db, period="2025-1")
        self.assertEqual(none.items, [])


class EnrollmentRouteTests(unittest.TestCase):
    def test_routes_are_superadmin_only(self) -> None:
        from app import app
        from modules.enrollment.routes import router

        paths = {
            path: methods
            for path, methods in app.openapi()["paths"].items()
            if path.startswith("/enrollment")
        }
        self.assertEqual(set(paths), {"/enrollment/import", "/enrollment/records"})
        for methods in paths.values():
            for operation in methods.values():
                self.assertIn({"HTTPBearer": []}, operation["security"])

        instructor = Account(
            id=2, username="inst", email="i@example.com", full_name="Inst",
            password_hash="unused", role=Role.INSTRUCTOR.value, is_active=True,
        )
        for route in router.routes:
            with self.subTest(route=route.path):
                guard = route.dependant.dependencies[0].call
                with self.assertRaises(ApplicationError) as error:
                    guard(instructor)
                self.assertEqual(error.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
