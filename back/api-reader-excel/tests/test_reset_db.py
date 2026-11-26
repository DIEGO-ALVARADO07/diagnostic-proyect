"""Vaciar la base para el recorrido desde cero (``tasks.ps1 reset``)."""

import unittest

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from core.orm import Base
from modules.courses.entities import Course, CourseEnrollment  # noqa: F401 (registra tablas)
from modules.excel.entities.academic import (
    AcademicProgram,
    AcademicStudent,
    DashboardState,
)
from modules.security.entities import AccessToken, Account  # noqa: F401 (registra tablas)
from modules.security.entities.role import Role
from scripts import reset_db


class ResetDbTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as db:
            admin = Account(
                id=1, username="admin", email="admin@example.com", full_name="Admin",
                password_hash="unused", role=Role.SUPERADMIN.value, is_active=True,
            )
            program = AcademicProgram(
                canonical_name="Sistemas", raw_name_key="sistemas", normalized_key="sistemas"
            )
            db.add_all([admin, DashboardState(id=1), program])
            db.flush()
            student = AcademicStudent(first_name="Ana", email="ana@x.co")
            db.add(student)
            db.flush()
            course = Course(
                name="Inglés", name_key="ingles", level=1, competency="ingles",
                description="Descripción del curso", methodology="Metodología del curso",
                created_by_user_id=admin.id,
            )
            db.add(course)
            db.flush()
            db.add(CourseEnrollment(course_id=course.id, student_id=student.id, level=1))
            db.commit()

    def tearDown(self) -> None:
        self.engine.dispose()

    def _count(self, model) -> int:
        with Session(self.engine) as db:
            return db.scalar(select(func.count()).select_from(model))

    def test_every_table_is_either_emptied_or_kept_on_purpose(self) -> None:
        # Si se agrega una tabla nueva, hay que decidir si se vacía o no.
        classified = set(reset_db.ACADEMIC_TABLES) | set(reset_db.USER_TABLES) | set(
            reset_db.KEPT_TABLES
        )
        self.assertEqual(set(Base.metadata.tables) - classified, set())

    def test_empties_academic_data_and_keeps_accounts(self) -> None:
        counts = reset_db.empty_tables(self.engine, reset_db.tables_to_empty(False))

        self.assertEqual(counts["courses"], 1)
        self.assertEqual(counts["course_enrollments"], 1)
        self.assertEqual(counts["academic_students"], 1)
        self.assertEqual(counts["academic_programs"], 1)
        for model in (Course, CourseEnrollment, AcademicStudent, AcademicProgram):
            self.assertEqual(self._count(model), 0)
        # Se puede seguir iniciando sesión y el dashboard tiene su estado inicial.
        self.assertEqual(self._count(Account), 1)
        self.assertEqual(self._count(DashboardState), 1)

    def test_include_users_also_empties_accounts(self) -> None:
        counts = reset_db.empty_tables(self.engine, reset_db.tables_to_empty(True))

        self.assertEqual(counts["api_users"], 1)
        self.assertEqual(self._count(Account), 0)
        self.assertEqual(self._count(DashboardState), 1)

    def test_wrong_confirmation_deletes_nothing(self) -> None:
        # La confirmación se compara con la base configurada antes de tocar nada.
        self.assertEqual(reset_db.main(["--confirm", "otra_base", "--skip-backup"]), 2)


if __name__ == "__main__":
    unittest.main()
