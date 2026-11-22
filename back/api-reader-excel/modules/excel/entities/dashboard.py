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
    student_search_name: str | None
    program_name: str
    program_raw_name_key: str
    program_normalized_key: str
    scores: tuple[Decimal | None, ...]
    global_raw: str | None
    global_score: Decimal | None
    global_calculated_score: Decimal
    moment: str | None
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
    levels: tuple[str | None, ...]
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
    averages: tuple[Decimal | None, ...]
    source_payload: dict[str, Any]


@dataclass(frozen=True)
class DashboardImportData:
    filename: str
    records: tuple[DashboardImportRecord, ...]
    td_programas_year: int | None
    td_programas_records: tuple[TdProgramasRecord, ...]


@dataclass(frozen=True)
class DashboardRecord:
    source_row_number: int
    document: str | None
    name: str
    email: str | None
    program_id: str
    program_name: str
    scores: tuple[float | None, ...]
    global_score: float | None
    moment: str | None
    test_type: str | None
    semester: str | None
    year: int
    simulation: str
    group: str | None
    presented: bool | None
    levels: tuple[str | None, ...]
    ent: str | None


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
    records_without_document: int
