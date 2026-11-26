from datetime import datetime

from pydantic import BaseModel, Field

PERIOD_OR_ALL_PATTERN = r"^(\d{4}-[12]|all)$"
COMPETENCY_PATTERN = (
    r"^(lectura_critica|competencias_ciudadanas|razonamiento_cuantitativo|ingles)$"
)


class CourseCreateRequest(BaseModel):
    name: str = Field(min_length=3, max_length=150)
    level: int = Field(ge=1, le=4)
    competency: str = Field(pattern=COMPETENCY_PATTERN)
    """Materia evaluada: ``lectura_critica``, ``competencias_ciudadanas``,
    ``razonamiento_cuantitativo`` o ``ingles``."""
    description: str = Field(min_length=10, max_length=2000)
    methodology: str = Field(min_length=10, max_length=2000)


class CourseEnrollRequest(BaseModel):
    period: str | None = Field(default=None, pattern=PERIOD_OR_ALL_PATTERN)
    """Periodo del nivel (``2026-2``) o ``all``; sin él, el último con datos."""


class CompetencyOptionResponse(BaseModel):
    key: str
    label: str


class CourseResponse(BaseModel):
    id: int
    name: str
    level: int
    competency: str
    competency_label: str
    description: str
    methodology: str
    students: int
    created_at: datetime
    created_by: str | None
    deleted_at: datetime | None = None
    deleted_by: str | None = None
    restored_at: datetime | None = None
    restored_by: str | None = None


class CourseLevelResponse(BaseModel):
    level: int
    label: str
    courses: list[CourseResponse]
    available_students: dict[str, int]
    """Estudiantes con este nivel en cada materia, en ``CourseListResponse.period``."""


class CourseListResponse(BaseModel):
    period: str
    """Periodo del que salen ``available_students`` (el último con datos)."""
    periods: list[str]
    competencies: list[CompetencyOptionResponse]
    levels: list[CourseLevelResponse]


class DeletedCoursesResponse(BaseModel):
    courses: list[CourseResponse]
    """Cursos eliminados (lógicamente), los más recientes primero."""


class CourseStudentResponse(BaseModel):
    student_id: int
    name: str
    document: str | None
    email: str | None
    program: str
    enrolled_level: int | None
    """Nivel en la materia del curso al inscribirse."""
    enrolled_period: str | None
    current_level: int | None
    """Nivel actual en la materia del curso (su periodo más reciente con puntajes)."""
    current_period: str | None
    enrolled_at: datetime


class CourseStudentsResponse(BaseModel):
    course: CourseResponse
    students: list[CourseStudentResponse]


class CourseEnrollResponse(BaseModel):
    course: CourseResponse
    period: str
    added: int
    already_enrolled: int
    level_students: int
    """Estudiantes con el nivel del curso en su materia, en ``period``."""
