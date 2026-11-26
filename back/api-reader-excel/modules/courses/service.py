"""Cursos por nivel y materia (fase 13b).

Reglas (decisión del 26/11/2026):

- Estructura: **Nivel → Curso → Estudiantes**. Cada curso es de un nivel (1–4)
  y de una de las 4 materias evaluadas (Lectura crítica, Competencias
  ciudadanas, Razonamiento cuantitativo o Inglés), y tiene nombre, descripción
  y metodología. El nombre no se repite en el mismo nivel y materia (sin
  importar tildes o mayúsculas).
- **"Agregar estudiantes"** inscribe en bloque a todos los que, en un periodo
  (por defecto el último), tienen **en la materia del curso** el nivel del
  curso. Ejemplo: Inglés de Nivel 1 recibe a los que tienen A1 en Inglés,
  aunque su nivel general sea otro. Los que ya estaban no se repiten; nadie se
  inscribe a mano.
- La inscripción guarda el nivel y el periodo de ese momento; la lista del curso
  muestra además el nivel actual en la materia, por si cambió después.
- **Eliminar es lógico** (instructor y superadmin): queda quién y cuándo, y el
  curso conserva sus inscripciones. **Solo el superadmin** ve los eliminados y
  los **restaura** (también queda quién y cuándo). Un curso eliminado no recibe
  estudiantes ni cambios.
"""

from collections import Counter
from collections.abc import Iterable
from http import HTTPStatus

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.exceptions import ApplicationError
from core.orm import utcnow
from modules.courses.dtos import (
    CompetencyOptionResponse,
    CourseEnrollResponse,
    CourseLevelResponse,
    CourseListResponse,
    CourseResponse,
    CourseStudentResponse,
    CourseStudentsResponse,
    DeletedCoursesResponse,
)
from modules.courses.entities import (
    COURSE_COMPETENCIES,
    COURSE_LEVELS,
    Course,
    CourseEnrollment,
)
from modules.excel.dtos.responses.dashboard import StudentLevelItemResponse
from modules.excel.entities.academic import AcademicStudent
from modules.excel.entities.competency import level_number
from modules.excel.services.dashboard_normalizer import normalized_key
from modules.excel.services.student_levels_service import (
    ALL_PERIODS,
    StudentLevelsService,
)
from modules.security.entities import Account


def competency_level(item: StudentLevelItemResponse, competency: str) -> int | None:
    """Nivel 1–4 del estudiante en una materia (``None`` si no tiene puntaje)."""
    return level_number(
        COURSE_COMPETENCIES[competency], item.competency_levels.get(competency)
    )


def _clean(text: str) -> str:
    """Quita espacios sobrantes al inicio y al final de cada línea."""
    return "\n".join(line.strip() for line in text.strip().splitlines()).strip()


class CourseService:
    def __init__(self, student_levels: StudentLevelsService) -> None:
        self.student_levels = student_levels

    # --- Cursos ----------------------------------------------------------------

    def list_courses(self, db: Session) -> CourseListResponse:
        """Cursos activos en los 4 niveles; los eliminados van aparte (superadmin)."""
        period, periods, students = self.student_levels.students_in(db)
        available = Counter(
            (level, key)
            for item in students
            for key in COURSE_COMPETENCIES
            if (level := competency_level(item, key)) is not None
        )
        courses = list(
            db.scalars(
                select(Course)
                .where(Course.deleted_at.is_(None))
                .order_by(Course.level, Course.competency, Course.name)
            )
        )
        counts = self._enrollment_counts(db)
        names = self._user_names(db, courses)
        return CourseListResponse(
            period=period,
            periods=periods,
            competencies=[
                CompetencyOptionResponse(key=key, label=competency.label)
                for key, competency in COURSE_COMPETENCIES.items()
            ],
            levels=[
                CourseLevelResponse(
                    level=level,
                    label=f"Nivel {level}",
                    courses=[
                        self._course(course, counts, names)
                        for course in courses
                        if course.level == level
                    ],
                    available_students={
                        key: available[(level, key)] for key in COURSE_COMPETENCIES
                    },
                )
                for level in COURSE_LEVELS
            ],
        )

    def deleted_courses(self, db: Session) -> DeletedCoursesResponse:
        courses = list(
            db.scalars(
                select(Course)
                .where(Course.deleted_at.is_not(None))
                .order_by(Course.deleted_at.desc(), Course.id.desc())
            )
        )
        counts = self._enrollment_counts(db)
        names = self._user_names(db, courses)
        return DeletedCoursesResponse(
            courses=[self._course(course, counts, names) for course in courses]
        )

    def create_course(
        self,
        db: Session,
        account: Account,
        name: str,
        level: int,
        competency: str,
        description: str,
        methodology: str,
    ) -> CourseResponse:
        if competency not in COURSE_COMPETENCIES:
            raise ApplicationError(
                HTTPStatus.UNPROCESSABLE_ENTITY, "Elige una de las 4 materias evaluadas."
            )
        clean_name = " ".join(name.split())
        clean_description = _clean(description)
        clean_methodology = _clean(methodology)
        if len(clean_name) < 3:
            raise ApplicationError(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                "El nombre del curso debe tener al menos 3 caracteres.",
            )
        if len(clean_description) < 10 or len(clean_methodology) < 10:
            raise ApplicationError(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                "Escribe la descripción y la metodología (al menos 10 caracteres cada una).",
            )
        name_key = normalized_key(clean_name)
        existing = db.scalar(
            select(Course).where(
                Course.level == level,
                Course.competency == competency,
                Course.name_key == name_key,
            )
        )
        if existing is not None:
            raise self._duplicate(existing, clean_name)
        course = Course(
            name=clean_name,
            name_key=name_key,
            level=level,
            competency=competency,
            description=clean_description,
            methodology=clean_methodology,
            created_by_user_id=account.id,
        )
        db.add(course)
        try:
            db.commit()
        except IntegrityError as error:
            db.rollback()
            raise ApplicationError(
                HTTPStatus.CONFLICT,
                f"Ya existe el curso \"{clean_name}\" de "
                f"{COURSE_COMPETENCIES[competency].label} en el Nivel {level}.",
            ) from error
        db.refresh(course)
        return self._course(course, {}, self._user_names(db, [course]))

    def delete_course(self, db: Session, course_id: int, account: Account) -> CourseResponse:
        """Eliminación lógica: se marca y se conserva con sus inscripciones."""
        course = self._get(db, course_id)
        if course.deleted_at is None:
            course.deleted_at = utcnow()
            course.deleted_by_user_id = account.id
            db.commit()
        return self._course(
            course, self._enrollment_counts(db), self._user_names(db, [course])
        )

    def restore_course(self, db: Session, course_id: int, account: Account) -> CourseResponse:
        """Vuelve a habilitar un curso eliminado, con sus mismas inscripciones."""
        course = self._get(db, course_id)
        if course.deleted_at is None:
            raise ApplicationError(HTTPStatus.CONFLICT, "El curso no está eliminado.")
        course.deleted_at = None
        course.deleted_by_user_id = None
        course.restored_at = utcnow()
        course.restored_by_user_id = account.id
        db.commit()
        return self._course(
            course, self._enrollment_counts(db), self._user_names(db, [course])
        )

    # --- Estudiantes del curso -------------------------------------------------

    def course_students(self, db: Session, course_id: int) -> CourseStudentsResponse:
        """Lista del curso; también de un curso eliminado (para auditoría)."""
        course = self._get(db, course_id)
        rows = db.execute(
            select(CourseEnrollment, AcademicStudent)
            .join(AcademicStudent, AcademicStudent.id == CourseEnrollment.student_id)
            .where(CourseEnrollment.course_id == course.id)
        ).all()
        _, _, history = self.student_levels.students_in(db, ALL_PERIODS)
        current = {item.student_id: item for item in history if item.student_id}

        students: list[CourseStudentResponse] = []
        for enrollment, student in rows:
            item = current.get(student.id)
            fallback_name = " ".join(
                part for part in (student.first_name, student.last_name) if part
            )
            students.append(
                CourseStudentResponse(
                    student_id=student.id,
                    name=item.name if item else fallback_name or "Nombre no disponible",
                    document=(item.document if item else None) or student.document_number,
                    email=(item.email if item else None) or student.email,
                    program=item.program if item else "Sin programa",
                    enrolled_level=enrollment.level,
                    enrolled_period=enrollment.period,
                    current_level=(
                        competency_level(item, course.competency) if item else None
                    ),
                    current_period=item.level_period if item else None,
                    enrolled_at=enrollment.enrolled_at,
                )
            )
        students.sort(key=lambda item: (normalized_key(item.name), item.student_id))
        return CourseStudentsResponse(
            course=self._course(
                course, {course.id: len(students)}, self._user_names(db, [course])
            ),
            students=students,
        )

    def enroll_level(
        self,
        db: Session,
        course_id: int,
        account: Account,
        period: str | None = None,
    ) -> CourseEnrollResponse:
        """Inscribe a los que tienen el nivel del curso en su materia, en ``period``."""
        course = self._get_active(db, course_id)
        period, _, students = self.student_levels.students_in(db, period)
        candidates = {
            item.student_id: item
            for item in students
            if item.student_id is not None
            and competency_level(item, course.competency) == course.level
        }
        enrolled = set(
            db.scalars(
                select(CourseEnrollment.student_id).where(
                    CourseEnrollment.course_id == course.id
                )
            )
        )
        new_ids = [sid for sid in candidates if sid not in enrolled]
        db.add_all(
            CourseEnrollment(
                course_id=course.id,
                student_id=student_id,
                level=course.level,
                period=period,
                enrolled_by_user_id=account.id,
            )
            for student_id in new_ids
        )
        db.commit()
        return CourseEnrollResponse(
            course=self._course(
                course, self._enrollment_counts(db), self._user_names(db, [course])
            ),
            period=period,
            added=len(new_ids),
            already_enrolled=len(candidates) - len(new_ids),
            level_students=len(candidates),
        )

    def remove_student(self, db: Session, course_id: int, student_id: int) -> None:
        course = self._get_active(db, course_id)
        enrollment = db.scalar(
            select(CourseEnrollment).where(
                CourseEnrollment.course_id == course.id,
                CourseEnrollment.student_id == student_id,
            )
        )
        if enrollment is None:
            raise ApplicationError(
                HTTPStatus.NOT_FOUND, "El estudiante no está inscrito en este curso."
            )
        db.delete(enrollment)
        db.commit()

    # --- Ayudas ----------------------------------------------------------------

    @staticmethod
    def _get(db: Session, course_id: int) -> Course:
        course = db.get(Course, course_id)
        if course is None:
            raise ApplicationError(HTTPStatus.NOT_FOUND, "El curso no existe.")
        return course

    def _get_active(self, db: Session, course_id: int) -> Course:
        course = self._get(db, course_id)
        if course.deleted_at is not None:
            raise ApplicationError(
                HTTPStatus.CONFLICT,
                f"El curso \"{course.name}\" está eliminado. "
                "Solo el administrador puede habilitarlo de nuevo.",
            )
        return course

    @staticmethod
    def _duplicate(existing: Course, name: str) -> ApplicationError:
        where = (
            f"de {COURSE_COMPETENCIES[existing.competency].label} "
            f"en el Nivel {existing.level}"
        )
        if existing.deleted_at is not None:
            return ApplicationError(
                HTTPStatus.CONFLICT,
                f"El curso \"{existing.name}\" {where} está eliminado. "
                "Pídele al administrador que lo habilite en vez de crearlo de nuevo.",
            )
        return ApplicationError(
            HTTPStatus.CONFLICT, f"Ya existe el curso \"{name}\" {where}."
        )

    @staticmethod
    def _enrollment_counts(db: Session) -> dict[int, int]:
        return dict(
            db.execute(
                select(CourseEnrollment.course_id, func.count())
                .group_by(CourseEnrollment.course_id)
            ).all()
        )

    @staticmethod
    def _user_names(db: Session, courses: Iterable[Course]) -> dict[int, str]:
        """Nombre de cada usuario que creó, eliminó o restauró alguno de los cursos."""
        ids = {
            user_id
            for course in courses
            for user_id in (
                course.created_by_user_id,
                course.deleted_by_user_id,
                course.restored_by_user_id,
            )
            if user_id is not None
        }
        if not ids:
            return {}
        return {
            account.id: account.full_name or account.username
            for account in db.scalars(select(Account).where(Account.id.in_(ids)))
        }

    @staticmethod
    def _course(
        course: Course, counts: dict[int, int], names: dict[int, str]
    ) -> CourseResponse:
        def name_of(user_id: int | None) -> str | None:
            return names.get(user_id) if user_id is not None else None

        return CourseResponse(
            id=course.id,
            name=course.name,
            level=course.level,
            competency=course.competency,
            competency_label=COURSE_COMPETENCIES[course.competency].label,
            description=course.description,
            methodology=course.methodology,
            students=counts.get(course.id, 0),
            created_at=course.created_at,
            created_by=name_of(course.created_by_user_id),
            deleted_at=course.deleted_at,
            deleted_by=name_of(course.deleted_by_user_id),
            restored_at=course.restored_at,
            restored_by=name_of(course.restored_by_user_id),
        )
