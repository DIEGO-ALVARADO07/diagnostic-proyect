"""Fase 15: resultados de CORHUILA con filtros de programa, semestre y búsqueda."""

from sqlalchemy import select

from core.exceptions import ApplicationError
from modules.excel.entities.academic import AcademicProgram
from tests.test_enrollment_matching import EnrollmentMatchingTests


class DashboardResultsTests(EnrollmentMatchingTests):
    """Usa el mismo escenario del cruce con matriculados (ESE, matriculados y CORHUILA)."""

    def setUp(self) -> None:
        super().setUp()
        self._import_ese()
        self._import_enrollment()
        self.import_id = self._import_corhuila().import_id

    def _results(self, **filters):
        options = {"program_id": None, "semester": None, "search": None, "page": 1, "page_size": 50}
        options.update(filters)
        return self.service.get_results(
            self.db, self.import_id, options["program_id"], options["semester"],
            options["search"], options["page"], options["page_size"], self.admin,
        )

    def _program_id(self, name: str) -> str:
        return str(self.db.scalar(
            select(AcademicProgram.id).where(AcademicProgram.canonical_name == name)
        ))

    # Las pruebas heredadas del cruce no se repiten aquí.
    test_enrollment_first_then_corhuila = None
    test_enrollment_fills_type_of_ese_students = None
    test_corhuila_first_then_enrollment_updates_rows = None
    test_double_program_counts_in_both_programs = None
    test_replacing_enrollment_removes_extra_program = None

    def test_without_filters_lists_every_row_and_options(self) -> None:
        result = self._results()
        self.assertIsNone(result.program)
        self.assertEqual(result.total_records, len(result.students))
        labels = {option.label for option in result.program_options}
        self.assertIn("INGENIERIA DE SISTEMAS", labels)
        self.assertIn("MEDICINA VETERINARIA Y ZOOTECNIA", labels)
        self.assertEqual(
            sum(option.count for option in result.program_options), result.total_records
        )
        semesters = [option.value for option in result.semester_options]
        self.assertIn("SEMESTRE 5", semesters)
        self.assertEqual(semesters[-1], "sin-semestre")
        # "Sin programa" va al final de la tabla de programas.
        self.assertEqual(result.programs[-1].program_id, "sin-programa")

    def test_search_by_email_document_and_name(self) -> None:
        by_email = self._results(search="NUEVA-2026A@corhuila.edu.co")
        self.assertEqual(
            sorted(item.program for item in by_email.students),
            ["INGENIERIA DE SISTEMAS", "MEDICINA VETERINARIA Y ZOOTECNIA"],
        )
        self.assertEqual({item.document for item in by_email.students}, {"3001"})
        self.assertEqual({item.document_type for item in by_email.students}, {"C"})
        self.assertEqual(self._results(search="3001").total_records, 2)
        # Cada palabra puede estar en un campo distinto (nombre y programa).
        mixed = self._results(search="nueva sistemas")
        self.assertEqual([item.program for item in mixed.students], ["INGENIERIA DE SISTEMAS"])
        self.assertEqual(self._results(search="no-existe-xyz").total_records, 0)

    def test_program_filter_gives_metrics_and_students_of_that_program(self) -> None:
        sistemas = self._program_id("INGENIERIA DE SISTEMAS")
        result = self._results(program_id=sistemas)
        self.assertEqual(result.program.name, "INGENIERIA DE SISTEMAS")
        self.assertTrue(result.students)
        self.assertEqual({item.program_id for item in result.students}, {sistemas})
        self.assertEqual(result.metrics.unique_students, len({
            item.document or item.email for item in result.students
        }))
        # La búsqueda cambia la tabla, no las métricas.
        searched = self._results(program_id=sistemas, search="zzz")
        self.assertEqual(searched.total_records, 0)
        self.assertEqual(searched.metrics, result.metrics)

    def test_without_program_and_semester_filters(self) -> None:
        sin_programa = self._results(program_id="sin-programa")
        self.assertIn("mlopez@corhuila.edu.co", {item.email for item in sin_programa.students})
        fifth = self._results(semester="SEMESTRE 5")
        self.assertTrue(fifth.students)
        self.assertEqual({item.semester for item in fifth.students}, {"SEMESTRE 5"})
        none = self._results(semester="sin-semestre")
        self.assertEqual({item.semester for item in none.students}, {None})

    def test_student_row_has_average_and_level(self) -> None:
        row = self._results(search="3001").students[0]
        values = [value for value in row.scores.values() if value is not None]
        if row.presented and values:
            self.assertAlmostEqual(row.average, round(sum(values) / len(values), 2))
            self.assertIn(row.level, {1, 2, 3, 4})

    def test_pagination_and_unknown_program(self) -> None:
        total = self._results().total_records
        first = self._results(page=1, page_size=2)
        self.assertEqual(len(first.students), min(2, total))
        self.assertEqual(first.total_pages, (total + 1) // 2)
        with self.assertRaises(ApplicationError):
            self._results(program_id="999999")

    def test_route_is_registered_for_instructors(self) -> None:
        from app import app

        operation = app.openapi()["paths"]["/excel/dashboard/{import_id}/results"]["get"]
        params = {param["name"] for param in operation["parameters"]}
        self.assertTrue({"program_id", "semester", "search", "page"} <= params)


del EnrollmentMatchingTests
