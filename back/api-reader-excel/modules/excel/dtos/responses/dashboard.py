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
    simple_competence_average: float | None
    competencies: dict[str, CompetencyMetricsResponse]


class DashboardKpisResponse(DashboardMetricsResponse):
    programs: int


class ProgramOptionResponse(BaseModel):
    program_id: str
    name: str


class DashboardFilterOptionsResponse(BaseModel):
    years: list[int]
    simulations: list[str]
    groups: list[str]
    programs: list[ProgramOptionResponse]
    semesters: list[str]
    test_types: list[str]
    presented: list[bool | None]


class DashboardSelectedFiltersResponse(BaseModel):
    year: int | None
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


class DashboardDataQualityResponse(BaseModel):
    """Hallazgos de BD GEN que no impiden importar, por clave de competencia."""

    score_codes: dict[str, dict[str, int]] = {}
    """Textos no numéricos en el puntaje, p. ej. {"comunicacion_escrita": {"N": 254}}."""
    levels_without_numeric_score: dict[str, int] = {}
    """Filas con un nivel válido pero sin puntaje numérico."""
    unknown_levels: dict[str, dict[str, int]] = {}
    """Niveles que no son válidos ni un código conocido, p. ej. {"ingles": {"false": 2}}."""


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
    status: str
    imported_at: datetime
    filters: DashboardFilterOptionsResponse
    source_audit: DashboardSourceAuditResponse
    overview: DashboardOverviewResponse


class DashboardImportListItemResponse(BaseModel):
    import_id: str
    filename: str
    status: str
    imported_at: datetime
    activated_at: datetime | None
    bd_gen_row_count: int
    td_programas_row_count: int
    td_programas_selected_year: int | None
    deleted_at: datetime | None = None


class DashboardImportListResponse(BaseModel):
    active_import_id: str | None
    imports: list[DashboardImportListItemResponse]


class DashboardStudentAttemptResponse(BaseModel):
    year: int
    simulation: str
    group: str | None
    semester: str | None
    test_type: str | None
    program_id: str
    program: str
    presented: bool | None
    global_score: float | None
    program_average_global: float | None
    scores: dict[str, float | None]
    levels: dict[str, str]
    ent: str | None


class DashboardStudentResponse(BaseModel):
    document: str
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
