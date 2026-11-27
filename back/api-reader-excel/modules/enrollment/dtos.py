from datetime import date, datetime

from pydantic import BaseModel


class EnrollmentUploadResponse(BaseModel):
    id: str
    period: str
    filename: str
    status: str
    rows: int
    """Filas guardadas: una por estudiante y programa."""
    students: int
    """Estudiantes distintos (por documento)."""
    double_program: int
    """Estudiantes que aparecen en dos o más programas."""
    rejected: int
    duplicates: int
    uploaded_at: datetime
    uploaded_by: str | None
    replaced_previous: bool = False
    """``True`` si esta carga reemplazó a la anterior del mismo periodo."""
    corhuila_rows_updated: int = 0
    """Filas de CORHUILA que cambiaron de estudiante, programa o semestre."""


class EnrollmentRecordResponse(BaseModel):
    id: int
    period: str
    pensum_code: str | None
    program: str
    semester: int | None
    document_type: str | None
    document_number: str
    student_code: str | None
    first_names: str | None
    last_names: str | None
    stratum: int | None
    gender: str | None
    birth_date: date | None
    phone: str | None
    mobile: str | None
    personal_email: str | None
    institutional_email: str | None
    programs_count: int
    """En cuántos programas está matriculado este estudiante en el periodo."""


class OptionCountResponse(BaseModel):
    value: str
    label: str
    count: int


class EnrollmentFiltersResponse(BaseModel):
    programs: list[OptionCountResponse]
    semesters: list[OptionCountResponse]
    document_types: list[OptionCountResponse]
    genders: list[OptionCountResponse]
    strata: list[OptionCountResponse]


class EnrollmentListResponse(BaseModel):
    period: str | None
    """Periodo consultado; ``None`` si todavía no hay ningún archivo."""
    uploads: list[EnrollmentUploadResponse]
    """Carga activa de cada periodo, del más reciente al más antiguo."""
    filters: EnrollmentFiltersResponse
    items: list[EnrollmentRecordResponse]
    filtered_total: int
    filtered_students: int
    page: int
    page_size: int
