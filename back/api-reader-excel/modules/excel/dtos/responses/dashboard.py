from datetime import datetime

from pydantic import BaseModel


class CompetencyMetricsResponse(BaseModel):
    label: str
    average: float | None
    count: int
    standard_deviation: float | None
    distribution_count: int
    level_distribution: dict[str, float]


class DashboardMetricsResponse(BaseModel):
    presentations: int
    unique_students: int
    not_presented_records: int
    average_global: float | None
    global_standard_deviation: float | None
    average_general: float | None
    general_standard_deviation: float | None
    simple_competence_average: float | None
    competencies: dict[str, CompetencyMetricsResponse]


class DashboardKpisResponse(DashboardMetricsResponse):
    programs: int


class ProgramOptionResponse(BaseModel):
    program_id: str
    name: str


class DashboardFilterOptionsResponse(BaseModel):
    years: list[int]
    periods: list[str] = []
    """Periodos del año presentes (``2026-1``, ``2026-2``…)."""
    moments: list[int] = []
    """Momentos de ESE presentes (1, 2, 3)."""
    simulations: list[str]
    groups: list[str]
    programs: list[ProgramOptionResponse]
    semesters: list[str]
    test_types: list[str]
    presented: list[bool | None]


class DashboardSelectedFiltersResponse(BaseModel):
    year: int | None
    period: str | None = None
    moment: int | None = None
    simulation: str | None
    group: str | None
    semester: str | None
    test_type: str | None
    presented: bool | None


class ProgramSummaryResponse(BaseModel):
    program_id: str
    name: str
    metrics: DashboardMetricsResponse


class DashboardOverviewResponse(BaseModel):
    import_id: str
    filters: DashboardFilterOptionsResponse
    selected_filters: DashboardSelectedFiltersResponse
    kpis: DashboardKpisResponse
    programs: list[ProgramSummaryResponse]
    page: int
    page_size: int
    total_programs: int
    total_pages: int


class DashboardAuditDifferenceResponse(BaseModel):
    simulation: str
    program: str
    metric: str
    td_programas_value: float
    bd_gen_value: float
    absolute_difference: float


class DashboardPeriodMomentQualityResponse(BaseModel):
    """Filas de BD GEN con problemas de periodo o momento (no impiden importar)."""

    rows_without_period: int = 0
    """``SIM`` no trae ``AAAA-1``/``AAAA-2``."""
    rows_without_moment: int = 0
    """Ni ``SIM`` ni ``GRUPO`` traen ``MOMENTO 1``–``3``."""
    moment_group_mismatches: int = 0
    """El momento de ``SIM`` no coincide con el de ``GRUPO`` (se usa el de ``SIM``)."""
    period_year_mismatches: int = 0
    """El año del periodo de ``SIM`` no coincide con ``AÑO``."""


class DashboardIdentityQualityResponse(BaseModel):
    """Identidad del estudiante (correo) en BD GEN; no impide importar."""

    rows_without_email: int = 0
    """Filas sin correo: no se pueden cruzar con CORHUILA."""
    emails_with_multiple_documents: int = 0
    """Correos con documentos distintos: el correo queda en el primer estudiante."""
    documents_with_multiple_emails: int = 0
    """Documentos con varios correos (institucional y personal): un estudiante,
    todos sus correos como alias."""
    names_with_multiple_documents: int = 0
    """Nombres completos con documentos distintos: en CORHUILA el nombre no sirve
    para identificarlos (``AMBIGUO``)."""


class DashboardDataQualityResponse(BaseModel):
    """Hallazgos de BD GEN que no impiden importar, por clave de competencia."""

    score_codes: dict[str, dict[str, int]] = {}
    """Textos no numéricos en el puntaje, p. ej. {"comunicacion_escrita": {"N": 254}}."""
    levels_without_numeric_score: dict[str, int] = {}
    """Filas con un nivel válido pero sin puntaje numérico."""
    unknown_levels: dict[str, dict[str, int]] = {}
    """Niveles que no son válidos ni un código conocido, p. ej. {"ingles": {"false": 2}}."""
    source_level_mismatches: dict[str, int] = {}
    """Filas cuyo nivel del Excel difiere del calculado con la escala común."""
    period_moment: DashboardPeriodMomentQualityResponse | None = None
    """Ausente en importaciones anteriores a la fase 8."""
    identity: DashboardIdentityQualityResponse | None = None
    """Ausente en importaciones anteriores a la fase 9."""


class DashboardSourceAuditResponse(BaseModel):
    years_in_bd_gen: list[int]
    td_programas_visible_year: int | None
    records_without_document: int
    compared_program_rows: int
    compared_metrics: int
    difference_count: int
    differences: list[DashboardAuditDifferenceResponse]
    data_quality: DashboardDataQualityResponse | None = None
    """Ausente en importaciones anteriores a la fase 5."""


class DashboardImportResponse(BaseModel):
    import_id: str
    filename: str
    source: str = "ESE"
    period: str | None = None
    status: str
    imported_at: datetime
    filters: DashboardFilterOptionsResponse
    source_audit: DashboardSourceAuditResponse
    overview: DashboardOverviewResponse


class DashboardImportListItemResponse(BaseModel):
    import_id: str
    filename: str
    source: str
    period: str | None
    status: str
    imported_at: datetime
    activated_at: datetime | None
    bd_gen_row_count: int
    td_programas_row_count: int
    td_programas_selected_year: int | None
    deleted_at: datetime | None = None


class DashboardActiveImportResponse(BaseModel):
    slot: str
    """``ESE`` o ``CORHUILA:<periodo>``."""
    source: str
    period: str | None
    import_id: str
    filename: str


class DashboardImportListResponse(BaseModel):
    active_import_id: str | None
    """Importación activa de ESE (compatibilidad con el frontend actual)."""
    active_imports: list[DashboardActiveImportResponse] = []
    """Activas de todos los espacios."""
    imports: list[DashboardImportListItemResponse]


class DashboardStudentAttemptResponse(BaseModel):
    year: int
    period: str | None = None
    moment: int | None = None
    semester_range: str | None = None
    """Semestres que mide la prueba según el momento (``"4–6"``)."""
    simulation: str
    group: str | None
    semester: str | None
    test_type: str | None
    program_id: str
    program: str
    presented: bool | None
    global_score: float | None
    program_average_global: float | None
    program_average_general: float | None
    scores: dict[str, float | None]
    levels: dict[str, str]
    ent: str | None


class ProgramLookupResponse(BaseModel):
    """Qué estudiante de ESE y qué programa se asignarían a unos datos de CORHUILA."""

    match: str
    """``DOCUMENTO``, ``CORREO``, ``NOMBRE``, ``AMBIGUO`` o ``SIN_COINCIDENCIA``."""
    student_id: int | None
    name: str | None
    document: str | None
    emails: list[str]
    program_id: int | None
    program: str | None
    """Programa de ESE Momento 2; ``None`` = sin programa."""
    moment_two_period: str | None
    ese_import_id: str | None


class DashboardStudentResponse(BaseModel):
    document: str | None
    """``None`` si el estudiante solo tiene correo (CORHUILA)."""
    name: str
    email: str | None
    programs: list[ProgramOptionResponse]
    history: list[DashboardStudentAttemptResponse]
    changes: dict[str, str]


class DashboardProgramStudentResponse(BaseModel):
    document: str | None
    name: str
    email: str | None
    program_id: str
    program: str
    year: int
    period: str | None = None
    moment: int | None = None
    semester_range: str | None = None
    simulation: str
    group: str | None
    semester: str | None
    presented: bool | None
    global_score: float | None
    scores: dict[str, float | None]
    levels: dict[str, str]
    ent: str | None


class DashboardProgramResponse(BaseModel):
    import_id: str
    program: ProgramOptionResponse
    filters: DashboardFilterOptionsResponse
    selected_filters: DashboardSelectedFiltersResponse
    metrics: DashboardMetricsResponse
    institutional_comparison: DashboardMetricsResponse
    students: list[DashboardProgramStudentResponse]
    page: int
    page_size: int
    total_records: int
    total_pages: int
