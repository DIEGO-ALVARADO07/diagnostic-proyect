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
    average_level: float | None = None
    """Promedio de los niveles (1–4) de las 4 competencias comunes."""
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
    simulations_by_year: dict[int, list[str]] = {}
    moments_by_period: dict[str, list[int]] = {}
    """Momentos de ESE de cada periodo, para filtrar en cascada."""
    """Simulacros de cada año: el filtro solo ofrece los del año elegido."""
    groups: list[str]
    programs: list[ProgramOptionResponse]
    test_types: list[str]
    presented: list[bool | None]


class DashboardSelectedFiltersResponse(BaseModel):
    year: int | None
    period: str | None = None
    moment: int | None = None
    simulation: str | None
    group: str | None
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
    upload_period_rows: int | None = None
    """Filas del periodo elegido al subir. ``0`` = quizá se eligió mal el periodo."""


class DashboardIdentityQualityResponse(BaseModel):
    """Identidad del estudiante (correo) en BD GEN; no impide importar."""

    rows_without_email: int = 0
    """Filas sin correo: no se pueden cruzar con CORHUILA."""
    emails_with_multiple_documents: int = 0
    """Correos con documentos distintos: el correo queda en el primer estudiante."""
    documents_with_multiple_emails: int = 0
    """Documentos con varios correos (institucional y personal): un estudiante,
    todos sus correos como alias."""
    documents_with_multiple_programs: int = 0
    """Estudiantes con más de un programa en ESE (cambio u homologación): en
    CORHUILA se usa el del registro más reciente."""
    names_with_multiple_documents: int = 0
    """Nombres completos con documentos distintos: en CORHUILA el nombre no sirve
    para identificarlos (``AMBIGUO``)."""


class DashboardCorhuilaQualityResponse(BaseModel):
    """Archivo de CORHUILA y su cruce con ESE al importarlo."""

    sheet: str
    rows: int
    presented: int
    not_presented: int
    """Sin ningún puntaje (todas las competencias con ``-``)."""
    partially_presented: int
    """Con alguna competencia sin puntaje."""
    rows_without_email: int
    rows_with_document: int
    duplicated_emails: int
    matches: dict[str, int]
    """Cómo se encontró a cada estudiante en ESE (``StudentMatch``)."""
    without_program: int
    """Filas sin programa: ver ``GET /excel/dashboard/review/without-program``."""
    ese_import_id: str | None


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
    corhuila: DashboardCorhuilaQualityResponse | None = None
    """Solo en importaciones de CORHUILA."""


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
    deleted_by: str | None = None
    restored_at: datetime | None = None
    restored_by: str | None = None


class DashboardImportRestoreResponse(BaseModel):
    import_id: str
    status: str
    """``ACTIVE`` si volvió a ser la activa de su espacio; si no, ``HISTORICAL`` o ``FAILED``."""
    activated: bool
    message: str


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
    """Programa actual: el manual o el del registro de ESE más reciente."""
    program_source: str | None
    """``ESE``, ``MANUAL`` o ``None`` (sin programa)."""
    program_period: str | None
    """Periodo de la fila de ESE usada."""
    program_moment: int | None
    """Momento de la fila de ESE usada."""
    ese_import_id: str | None


class ReviewStudentResponse(BaseModel):
    """Estudiante de CORHUILA sin programa: hay que revisarlo."""

    import_id: str
    period: str | None
    source_row_number: int
    student_id: int | None
    name: str
    email: str | None
    document: str | None
    match: str | None
    """Cómo se buscó en ESE: ``AMBIGUO``, ``SIN_COINCIDENCIA``… o, si se
    encontró, ``DOCUMENTO``/``CORREO``/``NOMBRE`` (pero sin Momento 2)."""


class ReviewStudentsResponse(BaseModel):
    total: int
    students: list[ReviewStudentResponse]


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


# --- Dashboard comparativo (ESE frente a CORHUILA) ---------------------------


class CompetencyHighlightResponse(BaseModel):
    key: str
    label: str
    average: float


class CompareSideResponse(BaseModel):
    """Una prueba en el periodo actual."""

    source: str
    import_id: str
    filename: str
    period: str | None
    kpis: DashboardMetricsResponse
    programs: list[ProgramSummaryResponse]
    """Incluye el subprograma "Sin programa" (``program_id = "sin-programa"``)."""
    weakest_competency: CompetencyHighlightResponse | None


class WorstProgramResponse(BaseModel):
    program_id: str
    name: str
    average_level: float
    """Nivel promedio (1–4) uniendo ESE y CORHUILA."""
    ese_average_level: float | None
    corhuila_average_level: float | None


class CommonCompetencyResponse(BaseModel):
    key: str
    label: str
    average: float
    """Promedio de los promedios de cada prueba cargada."""
    ese_average: float | None
    corhuila_average: float | None


class CompareFiltersResponse(BaseModel):
    periods: list[str] = []
    """Periodos con datos (filas de ESE o carga de CORHUILA), del más reciente al más antiguo."""
    corhuila_periods: list[str] = []
    """Periodos con archivo de CORHUILA, del más reciente al más antiguo."""
    moments: list[int]
    """Momentos de ESE en el periodo actual (CORHUILA tiene momento único)."""
    programs: list[ProgramOptionResponse]


class CompareSelectedFiltersResponse(BaseModel):
    period: str | None = None
    moment: int | None
    program_id: str | None


class DashboardCompareResponse(BaseModel):
    period: str | None
    """Periodo mostrado: el pedido o el último cargado. ``None`` si no hay importaciones."""
    filters: CompareFiltersResponse
    selected_filters: CompareSelectedFiltersResponse
    ese: CompareSideResponse | None
    """``None`` = a la espera del archivo de ESE de este periodo."""
    corhuila: CompareSideResponse | None
    """``None`` = a la espera del archivo de CORHUILA de este periodo."""
    worst_program: WorstProgramResponse | None
    lowest_common_competency: CommonCompetencyResponse | None
    note: str


# --- Revisión de CORHUILA -----------------------------------------------------


class ProgramCatalogResponse(BaseModel):
    programs: list[ProgramOptionResponse]


class AssignProgramRequest(BaseModel):
    program_id: int | None
    """``None`` quita la asignación manual."""


class CorhuilaResolveResponse(BaseModel):
    changed_rows: int
    without_program: int


class StudentLevelItemResponse(BaseModel):
    """Un estudiante de los Excel (ESE y CORHUILA juntos) con su nivel actual."""

    student_key: str
    student_id: int | None = None
    """``academic_students.id``; ``None`` si la fila no tiene estudiante resuelto."""
    name: str
    document: str | None
    email: str | None
    program_id: str
    program: str
    level: int | None
    """Nivel 1–4; ``None`` = "Sin resultado"."""
    level_period: str | None
    """Periodo del que sale el nivel (el más reciente con puntajes)."""
    level_sources: list[str]
    """Pruebas de ese periodo (``ESE``, ``CORHUILA``)."""
    competency_levels: dict[str, str | None]
    """Nivel por competencia común en ``level_period`` (``"3"``, ``"B1"``…)."""
    average: float | None
    """Promedio de las 4 competencias comunes en ``level_period``."""
    last_period: str | None
    """Último periodo en que aparece, haya presentado o no."""


class StudentLevelGroupResponse(BaseModel):
    key: str
    """``"1"``…``"4"`` o ``"sin-resultado"``."""
    label: str
    count: int


class StudentLevelsResponse(BaseModel):
    total: int
    """Estudiantes que cumplen búsqueda y programa (antes del filtro de nivel)."""
    groups: list[StudentLevelGroupResponse]
    programs: list[ProgramOptionResponse]
    level: str | None
    period: str
    """Periodo consultado (``2026-2``) o ``"all"`` (histórico)."""
    periods: list[str]
    """Periodos con datos, del más reciente al más antiguo."""
    page: int
    page_size: int
    filtered_total: int
    """Estudiantes del nivel elegido (o ``total`` si no hay nivel)."""
    students: list[StudentLevelItemResponse]
    rule: str
