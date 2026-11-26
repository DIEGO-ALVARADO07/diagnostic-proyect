from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from core.orm import Base, utcnow
from modules.excel.entities.competency import COMPARABLE_COMPETENCIES

COURSE_LEVELS = (1, 2, 3, 4)
COURSE_COMPETENCIES = {competency.key: competency for competency in COMPARABLE_COMPETENCIES}
"""Las 4 materias evaluadas en ESE y CORHUILA; cada curso es de una."""

_COMPETENCY_CHECK = "competency IN ({})".format(
    ", ".join(f"'{key}'" for key in COURSE_COMPETENCIES)
)


class Course(Base):
    """Curso de una materia para los estudiantes de un nivel (1–4) en esa materia."""

    __tablename__ = "courses"
    __table_args__ = (
        CheckConstraint("level BETWEEN 1 AND 4", name="ck_courses_level"),
        CheckConstraint(_COMPETENCY_CHECK, name="ck_courses_competency"),
        UniqueConstraint(
            "level", "competency", "name_key", name="uq_courses_level_competency_name"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    name_key: Mapped[str] = mapped_column(String(150), nullable=False)
    """Nombre normalizado: no se repite en el mismo nivel y materia."""
    level: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    competency: Mapped[str] = mapped_column(String(40), nullable=False)
    """Materia (``Competency.key``): ``lectura_critica``, ``ingles``…"""
    description: Mapped[str] = mapped_column(Text, nullable=False)
    methodology: Mapped[str] = mapped_column(Text, nullable=False)
    created_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("api_users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow
    )
    # Eliminación lógica con auditoría: el curso y sus inscripciones se
    # conservan y se pueden restaurar.
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    deleted_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("api_users.id", ondelete="SET NULL", name="fk_courses_deleted_by"),
        nullable=True,
    )
    restored_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    """Última restauración (``None`` si nunca se eliminó o no se ha restaurado)."""
    restored_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("api_users.id", ondelete="SET NULL", name="fk_courses_restored_by"),
        nullable=True,
    )


class CourseEnrollment(Base):
    """Estudiante inscrito en un curso, con el nivel y periodo de la inscripción."""

    __tablename__ = "course_enrollments"
    __table_args__ = (
        UniqueConstraint(
            "course_id", "student_id", name="uq_course_enrollments_student"
        ),
        Index("ix_course_enrollments_student_id", "student_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), nullable=False
    )
    student_id: Mapped[int] = mapped_column(
        ForeignKey("academic_students.id", ondelete="CASCADE"), nullable=False
    )
    level: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    """Nivel que tenía al inscribirse."""
    period: Mapped[str | None] = mapped_column(String(7), nullable=True)
    """Periodo del que salió el nivel (``2026-2``; ``all`` = histórico)."""
    enrolled_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("api_users.id", ondelete="SET NULL"), nullable=True
    )
    enrolled_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow
    )
