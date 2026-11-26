"""Fase 13b: cursos por nivel y materia, inscripción en bloque y eliminación lógica."""

import unittest

from core.exceptions import ApplicationError
from modules.courses.service import CourseService
from tests import test_dashboard_compare

DESCRIPTION = "Refuerzo de las bases de la materia evaluada."
METHODOLOGY = "Talleres semanales con simulacros cortos y retroalimentación."


class CourseRouteTests(unittest.TestCase):
    def _operations(self) -> dict[str, dict]:
        from app import app

        return {
            f"{method.upper()} {path}": operation
            for path, methods in app.openapi()["paths"].items()
            if path.startswith("/courses")
            for method, operation in methods.items()
        }

    def test_course_endpoints_require_bearer_authentication(self) -> None:
        operations = self._operations()
        # Listar, crear, eliminados, eliminar, restaurar, ver estudiantes,
        # inscribir y sacar a uno.
        self.assertEqual(len(operations), 8)
        for name, operation in operations.items():
            with self.subTest(operation=name):
                self.assertIn({"HTTPBearer": []}, operation["security"])

    def test_restore_and_deleted_list_are_superadmin_only(self) -> None:
        from modules.courses.routes import router
        from modules.security.entities import Account
        from modules.security.entities.role import Role

        def account(role: Role) -> Account:
            return Account(
                id=9, username=role.value, email=f"{role.value}@example.com",
                full_name=role.value, password_hash="unused", role=role.value,
                is_active=True,
            )

        guarded = {
            ("GET", "/courses/deleted"): True,
            ("POST", "/courses/{course_id}/restore"): True,
            ("DELETE", "/courses/{course_id}"): False,  # El instructor sí elimina.
        }
        for route in router.routes:
            for method in route.methods:
                admin_only = guarded.get((method, route.path))
                if admin_only is None:
                    continue
                with self.subTest(route=f"{method} {route.path}"):
                    role_guard = route.dependant.dependencies[0].call
                    superadmin = account(Role.SUPERADMIN)
                    self.assertIs(role_guard(superadmin), superadmin)
                    instructor = account(Role.INSTRUCTOR)
                    if admin_only:
                        with self.assertRaises(ApplicationError) as error:
                            role_guard(instructor)
                        self.assertEqual(error.exception.status_code, 403)
                    else:
                        self.assertIs(role_guard(instructor), instructor)


class CourseTests(unittest.TestCase):
    """Usa la base y las cargas de las pruebas del dashboard comparativo.

    Con ESE 2026-1 y CORHUILA 2026-2, el último periodo es 2026-2. Niveles por
    materia (Lectura, Ciudadanas, Cuantitativo, Inglés):
    Carlos 3, 1, 1, 4 · Sara 2, 2, 2, 3 · persona nueva 1, 1, 1, 1 · el Mario
    ambiguo no tiene puntajes.
    """

    def setUp(self) -> None:
        self.base = test_dashboard_compare.CompareDashboardTests(
            "test_empty_dashboard_without_imports"
        )
        self.base.setUp()
        self.db = self.base.db
        self.admin = self.base.admin
        self.service = CourseService(self.base.service.student_levels)
        self.base._import_ese("2026-1")
        self.base._import_corhuila("2026-2")

    def tearDown(self) -> None:
        self.base.tearDown()

    def _create(self, name: str, level: int, competency: str = "lectura_critica"):
        return self.service.create_course(
            self.db, self.admin, name, level, competency, DESCRIPTION, METHODOLOGY
        )

    def test_list_shows_four_levels_with_students_per_subject(self) -> None:
        response = self.service.list_courses(self.db)

        self.assertEqual(response.period, "2026-2")
        self.assertEqual([item.level for item in response.levels], [1, 2, 3, 4])
        self.assertEqual(
            [item.key for item in response.competencies],
            ["lectura_critica", "competencias_ciudadanas", "razonamiento_cuantitativo", "ingles"],
        )
        self.assertEqual(
            response.levels[0].available_students,
            {
                "lectura_critica": 1,
                "competencias_ciudadanas": 2,
                "razonamiento_cuantitativo": 2,
                "ingles": 1,
            },
        )
        self.assertEqual(response.levels[3].available_students["ingles"], 1)
        self.assertTrue(all(item.courses == [] for item in response.levels))

    def test_create_course_with_subject_description_and_methodology(self) -> None:
        course = self._create("  Lectura   crítica ", 2)

        self.assertEqual(course.name, "Lectura crítica")
        self.assertEqual((course.level, course.competency), (2, "lectura_critica"))
        self.assertEqual(course.competency_label, "Lectura crítica")
        self.assertEqual(course.description, DESCRIPTION)
        self.assertEqual(course.methodology, METHODOLOGY)
        self.assertEqual(course.created_by, "Admin")

        with self.assertRaises(ApplicationError) as duplicate:
            self._create("LECTURA CRITICA", 2)
        self.assertEqual(duplicate.exception.status_code, 409)

        # El mismo nombre sí vale en otra materia o en otro nivel.
        self.assertEqual(self._create("Lectura crítica", 2, "ingles").competency, "ingles")
        self.assertEqual(self._create("Lectura crítica", 1).level, 1)
        self.assertEqual(len(self.service.list_courses(self.db).levels[1].courses), 2)

        with self.assertRaises(ApplicationError) as short:
            self.service.create_course(
                self.db, self.admin, "Sin texto", 3, "ingles", "corta", METHODOLOGY
            )
        self.assertEqual(short.exception.status_code, 422)
        with self.assertRaises(ApplicationError) as unknown:
            self.service.create_course(
                self.db, self.admin, "Escritura", 3, "comunicacion_escrita",
                DESCRIPTION, METHODOLOGY,
            )
        self.assertEqual(unknown.exception.status_code, 422)

    def test_enroll_uses_the_level_in_the_course_subject(self) -> None:
        # Lectura crítica Nivel 2: solo Sara (Carlos tiene 3 en Lectura).
        reading = self._create("Lectura nivel 2", 2)
        first = self.service.enroll_level(self.db, reading.id, self.admin)
        again = self.service.enroll_level(self.db, reading.id, self.admin)

        self.assertEqual(first.period, "2026-2")
        self.assertEqual((first.added, first.already_enrolled), (1, 0))
        self.assertEqual((again.added, again.already_enrolled), (0, 1))
        students = self.service.course_students(self.db, reading.id).students
        self.assertEqual([s.name for s in students], ["SARA DIAZ"])
        self.assertEqual(students[0].enrolled_level, 2)
        self.assertEqual(students[0].current_level, 2)

        # Inglés Nivel 4: Carlos (B2), aunque su nivel general sea 2.
        english = self._create("Inglés avanzado", 4, "ingles")
        result = self.service.enroll_level(self.db, english.id, self.admin)
        self.assertEqual(result.added, 1)
        carlos = self.service.course_students(self.db, english.id).students[0]
        self.assertEqual(carlos.name.upper(), "CARLOS RUIZ")
        self.assertEqual(carlos.document, "201")
        self.assertEqual(carlos.program.upper(), "PROGRAMA B")
        self.assertEqual((carlos.enrolled_level, carlos.current_level), (4, 4))

        # Ciudadanas Nivel 1: Carlos y la persona nueva.
        citizenship = self._create("Ciudadanas básico", 1, "competencias_ciudadanas")
        self.assertEqual(
            self.service.enroll_level(self.db, citizenship.id, self.admin).added, 2
        )

    def test_enroll_from_another_period(self) -> None:
        course = self._create("Nivelación", 2)

        result = self.service.enroll_level(self.db, course.id, self.admin, "2026-1")

        # En 2026-1 (ESE) Lectura crítica: varios estudiantes en Nivel 2.
        self.assertEqual(result.period, "2026-1")
        self.assertGreater(result.added, 0)
        students = self.service.course_students(self.db, course.id).students
        self.assertTrue(all(s.enrolled_period == "2026-1" for s in students))

    def test_remove_student(self) -> None:
        course = self._create("Inglés básico", 1, "ingles")
        self.service.enroll_level(self.db, course.id, self.admin)
        student = self.service.course_students(self.db, course.id).students[0]
        self.assertEqual(student.name, "NUEVA PERSONA")

        self.service.remove_student(self.db, course.id, student.student_id)
        self.assertEqual(self.service.course_students(self.db, course.id).students, [])
        with self.assertRaises(ApplicationError) as missing:
            self.service.remove_student(self.db, course.id, student.student_id)
        self.assertEqual(missing.exception.status_code, 404)

    def test_soft_delete_keeps_audit_and_restore_brings_it_back(self) -> None:
        course = self._create("Inglés básico", 1, "ingles")
        self.service.enroll_level(self.db, course.id, self.admin)

        deleted = self.service.delete_course(self.db, course.id, self.admin)

        # Eliminación lógica: queda quién y cuándo, y conserva sus inscripciones.
        self.assertIsNotNone(deleted.deleted_at)
        self.assertEqual(deleted.deleted_by, "Admin")
        self.assertEqual(deleted.students, 1)
        listing = self.service.list_courses(self.db)
        self.assertTrue(all(level.courses == [] for level in listing.levels))
        # Los eliminados van aparte, con toda su información (panel del superadmin).
        removed = self.service.deleted_courses(self.db).courses
        self.assertEqual([c.name for c in removed], ["Inglés básico"])
        self.assertEqual(removed[0].description, DESCRIPTION)
        self.assertEqual(removed[0].methodology, METHODOLOGY)
        self.assertEqual(removed[0].competency_label, "Inglés")
        # Su lista se puede consultar (auditoría), pero no recibe cambios.
        self.assertEqual(len(self.service.course_students(self.db, course.id).students), 1)
        for change in (
            lambda: self.service.enroll_level(self.db, course.id, self.admin),
            lambda: self.service.remove_student(self.db, course.id, 1),
        ):
            with self.assertRaises(ApplicationError) as blocked:
                change()
            self.assertEqual(blocked.exception.status_code, 409)
        # No se crea otro igual: se pide al administrador que lo habilite.
        with self.assertRaises(ApplicationError) as duplicate:
            self._create("ingles basico", 1, "ingles")
        self.assertIn("administrador", duplicate.exception.detail)
        # Eliminar dos veces no cambia la auditoría.
        again = self.service.delete_course(self.db, course.id, self.admin)
        self.assertEqual(again.deleted_at, deleted.deleted_at)

        restored = self.service.restore_course(self.db, course.id, self.admin)

        self.assertIsNone(restored.deleted_at)
        self.assertIsNotNone(restored.restored_at)
        self.assertEqual(restored.restored_by, "Admin")
        self.assertEqual(restored.students, 1)
        listing = self.service.list_courses(self.db)
        self.assertEqual([c.name for c in listing.levels[0].courses], ["Inglés básico"])
        self.assertEqual(self.service.deleted_courses(self.db).courses, [])
        with self.assertRaises(ApplicationError) as not_deleted:
            self.service.restore_course(self.db, course.id, self.admin)
        self.assertEqual(not_deleted.exception.status_code, 409)
