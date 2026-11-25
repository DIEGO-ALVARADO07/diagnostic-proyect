from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class DashboardImportRecord:
    source_row_number: int
    document: str | None
    first_name: str | None
    last_name: str | None
    email: str | None
    email_key: str | None
    """Correo normalizado: identidad del estudiante."""
    student_search_name: str | None
    program_name: str
    """Nombre tal como viene en el Excel."""
    program_normalized_key: str
    """Identidad del programa (sin mayúsculas, tildes ni espacios extra)."""
    scores: Mapping[str, Decimal | None]
    """Puntaje por ``Competency.key``."""
    global_raw: str | None
    global_score: Decimal | None
    global_calculated_score: Decimal
    moment: str | None
    """Texto original de la columna ``Momento``."""
    period: str | None
    """Periodo del año (``2026-1``), de ``SIM``."""
    moment_number: int | None
    """Momento de ESE (1–3), de ``SIM`` o ``GRUPO``."""
    test_type: str | None
    test_type_key: str | None
    semester: str | None
    semester_key: str | None
    year: int
    simulation: str
    simulation_key: str
    group: str | None
    group_key: str | None
    presented: bool | None
    presented_raw: str | None
    levels: Mapping[str, str | None]
    """Nivel del archivo por ``Competency.key``."""
    campus: str | None
    training_applied: str | None
    ent: str | None
    source_payload: dict[str, Any]


@dataclass(frozen=True)
class TdProgramasRecord:
    source_row_number: int
    selected_year: int | None
    simulation: str
    simulation_key: str
    program_name: str
    program_normalized_key: str
    competency_averages: Mapping[str, Decimal | None]
    """Promedio por ``Competency.key`` (columnas LC, CE, CC, RC, I)."""
    global_average: Decimal | None
    """Primera columna GL: promedio del GLOBAL de los registros."""
    competency_mean: Decimal | None
    """Segunda columna GL: promedio de los promedios por competencia."""
    source_payload: dict[str, Any]


@dataclass(frozen=True)
class DashboardImportData:
    filename: str
    records: tuple[DashboardImportRecord, ...]
    td_programas_year: int | None
    td_programas_records: tuple[TdProgramasRecord, ...]
    program_names: Mapping[str, str]
    """Nombre a mostrar por ``program_normalized_key`` (ver ``program_catalog``)."""
    data_quality: Mapping[str, Any]
    """Hallazgos que no impiden importar (ver ``dashboard_data_quality``)."""


@dataclass(frozen=True)
class DashboardRecord:
    source_row_number: int
    document: str | None
    name: str
    email: str | None
    program_id: str
    program_name: str
    scores: Mapping[str, float | None]
    """Puntaje por ``Competency.key``."""
    global_score: float | None
    moment: str | None
    test_type: str | None
    semester: str | None
    year: int
    simulation: str
    group: str | None
    presented: bool | None
    levels: Mapping[str, str | None]
    """Nivel del archivo por ``Competency.key``."""
    ent: str | None
    period: str | None = None
    """Periodo del año (``2026-1``)."""
    moment_number: int | None = None
    """Momento de ESE (1–3); ``None`` si no se pudo determinar o es CORHUILA."""
    source: str = "ESE"
    """Prueba de origen (``Source``)."""
    email_key: str | None = None
    """Correo normalizado: identidad del estudiante."""
    program_resolution: str | None = None
    """Solo CORHUILA: ``ProgramResolution``."""

    @property
    def student_key(self) -> str | None:
        """Clave del estudiante: el correo; si no hay, el documento."""
        return self.email_key or self.document


@dataclass(frozen=True)
class DashboardDataset:
    """Instantánea de solo lectura de una importación.

    Se comparte entre peticiones a través de la caché, así que sus colecciones
    son inmutables (tuplas y ``MappingProxyType``).
    """

    import_id: str
    filename: str
    records: tuple[DashboardRecord, ...]
    records_by_program: Mapping[str, tuple[DashboardRecord, ...]]
    records_by_student: Mapping[str, tuple[DashboardRecord, ...]]
    program_names: Mapping[str, str]
    td_programs_year: int | None
    td_programs_summary: Mapping[tuple[str, str], Mapping[str, float | None]]
    """Promedios de TD PROGRAMAS por (simulacro normalizado, programa normalizado)."""
    records_without_document: int
    data_quality: Mapping[str, Any] | None = None
