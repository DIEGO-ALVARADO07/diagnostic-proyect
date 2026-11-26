"""Fase 13a: todos los estudiantes de los Excel, agrupados por nivel."""

import unittest

from modules.excel.entities.assessment import SIN_PROGRAMA_ID
from tests import test_dashboard_compare


class StudentLevelsTests(unittest.TestCase):
    """Usa la base y las cargas de las pruebas del dashboard comparativo."""

    def setUp(self) -> None:
        self.base = test_dashboard_compare.CompareDashboardTests(
            "test_empty_dashboard_without_imports"
        )
        self.base.setUp()
        self.db = self.base.db
        self.service = self.base.service
        self._import_ese = self.base._import_ese
        self._import_corhuila = self.base._import_corhuila

    def tearDown(self) -> None:
        self.base.tearDown()

    def _groups(self, response) -> dict[str, int]:
        return {group.key: group.count for group in response.groups}

    def _by_name(self, response) -> dict[str, object]:
        return {student.name: student for student in response.students}

    def test_empty_without_imports(self) -> None:
        response = self.service.list_students(self.db)
        self.assertEqual(response.total, 0)
        self.assertEqual(
            self._groups(response),
            {"1": 0, "2": 0, "3": 0, "4": 0, "sin-resultado": 0},
        )
        self.assertEqual(response.students, [])

    def test_history_everyone_once_with_a_single_level(self) -> None:
        self._import_ese("2026-1")
        self._import_corhuila("2026-2")

        response = self.service.list_students(self.db, period="all")

        # ESE (7 personas) y CORHUILA juntos: Carlos y Sara no se repiten; el
        # Mario ambiguo y la persona nueva de CORHUILA sí son estudiantes aparte.
        self.assertEqual(response.total, 9)
        self.assertEqual(sum(self._groups(response).values()), 9)
        self.assertEqual(
            self._groups(response),
            {"1": 1, "2": 6, "3": 0, "4": 0, "sin-resultado": 2},
        )
        names = [student.name for student in response.students]
        self.assertEqual(names.count("Carlos Ruiz"), 1)

        students = self._by_name(response)
        # Ana: su último periodo es 2026-1 (ESE). Niveles 2, 3, 3 y 3 → 2,75 → 2.
        ana = students["Ana Pérez"]
        self.assertEqual(ana.level, 2)
        self.assertEqual(ana.level_period, "2026-1")
        self.assertEqual(ana.level_sources, ["ESE"])
        self.assertEqual(
            ana.competency_levels,
            {
                "lectura_critica": "2",
                "competencias_ciudadanas": "3",
                "razonamiento_cuantitativo": "3",
                "ingles": "B1",
            },
        )
        self.assertNotIn("comunicacion_escrita", ana.competency_levels)

        # Carlos: CORHUILA 2026-2 manda sobre ESE 2026-1. Sus dos filas se
        # promedian por competencia: 3, 1, 1 y 4 → 2,25 → 2. Conserva el
        # documento y el programa que vienen de ESE.
        carlos = students["Carlos Ruiz"]
        self.assertEqual(carlos.level, 2)
        self.assertEqual(carlos.level_period, "2026-2")
        self.assertEqual(carlos.level_sources, ["CORHUILA"])
        self.assertEqual(carlos.document, "201")
        self.assertEqual(carlos.program.upper(), "PROGRAMA B")
        self.assertAlmostEqual(carlos.average, 153.75)

        # Nunca presentó (Luis) o CORHUILA sin puntajes (Mario ambiguo).
        luis = students["Luis Gómez"]
        self.assertIsNone(luis.level)
        self.assertIsNone(luis.level_period)
        self.assertEqual(luis.last_period, "2025-1")

        nueva = students["NUEVA PERSONA"]
        self.assertEqual(nueva.level, 1)
        self.assertEqual(nueva.program_id, SIN_PROGRAMA_ID)

    def test_filter_by_level_program_and_search(self) -> None:
        self._import_ese("2026-1")
        self._import_corhuila("2026-2")

        no_result = self.service.list_students(self.db, period="all", level="sin-resultado")
        self.assertEqual(no_result.filtered_total, 2)
        self.assertEqual(no_result.total, 9)  # Los grupos cuentan a todos.
        self.assertTrue(all(item.level is None for item in no_result.students))

        level_one = self.service.list_students(self.db, period="all", level="1")
        self.assertEqual([s.name for s in level_one.students], ["NUEVA PERSONA"])

        without_program = self.service.list_students(
            self.db, period="all", program_id=SIN_PROGRAMA_ID
        )
        self.assertEqual(without_program.total, 2)
        self.assertEqual(
            self._groups(without_program),
            {"1": 1, "2": 0, "3": 0, "4": 0, "sin-resultado": 1},
        )

        # Sin tildes ni mayúsculas; también por documento.
        by_name = self.service.list_students(self.db, period="all", search="mario lopez")
        self.assertEqual(by_name.total, 3)
        by_document = self.service.list_students(self.db, period="all", search="501")
        self.assertEqual([s.name for s in by_document.students], ["Elena Mora"])

    def test_pagination(self) -> None:
        self._import_ese("2026-1")
        self._import_corhuila("2026-2")

        first = self.service.list_students(self.db, period="all", page=1, page_size=4)
        third = self.service.list_students(self.db, period="all", page=3, page_size=4)

        self.assertEqual(len(first.students), 4)
        self.assertEqual(len(third.students), 1)
        self.assertEqual(first.filtered_total, 9)
        self.assertEqual(first.students[0].name, "Ana Pérez")  # Orden alfabético.

    def test_latest_period_by_default(self) -> None:
        self._import_ese("2026-1")
        self._import_corhuila("2026-2")

        response = self.service.list_students(self.db)

        # Por defecto, el último periodo: solo los 4 de CORHUILA 2026-2 (Carlos,
        # Sara, el Mario ambiguo y la persona nueva), con el nivel de ese periodo.
        self.assertEqual(response.period, "2026-2")
        self.assertEqual(response.periods[0], "2026-2")
        self.assertIn("2024-1", response.periods)
        self.assertEqual(response.total, 4)
        self.assertEqual(
            self._groups(response),
            {"1": 1, "2": 2, "3": 0, "4": 0, "sin-resultado": 1},
        )
        self.assertNotIn("Ana Pérez", self._by_name(response))

    def test_other_period_uses_that_period_level(self) -> None:
        self._import_ese("2026-1")
        self._import_corhuila("2026-2")

        response = self.service.list_students(self.db, period="2026-1")

        # En 2026-1 Carlos tiene el nivel de su ESE de ese periodo, no el de
        # CORHUILA 2026-2; el nivel por nivel sigue funcionando con el periodo.
        students = self._by_name(response)
        self.assertEqual(response.period, "2026-1")
        self.assertEqual(students["Carlos Ruiz"].level_period, "2026-1")
        self.assertEqual(students["Carlos Ruiz"].level_sources, ["ESE"])
        self.assertNotIn("NUEVA PERSONA", students)
        level_two = self.service.list_students(self.db, period="2026-1", level="2")
        self.assertEqual(level_two.period, "2026-1")
        self.assertTrue(all(item.level == 2 for item in level_two.students))

        empty = self.service.list_students(self.db, period="2030-1")
        self.assertEqual(empty.total, 0)
