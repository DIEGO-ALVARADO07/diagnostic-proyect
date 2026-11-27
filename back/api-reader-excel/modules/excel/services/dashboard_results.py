"""Resultados de una importación con filtros y búsqueda (módulo CORHUILA).

Filtros:

* ``program_id``: un programa (``sin-programa`` incluido); sin él, todos.
* ``semester``: ``SEMESTRE 5``…; ``sin-semestre`` = filas sin semestre.
* ``search``: cada palabra debe estar en el nombre, el documento, el correo o
  el programa (sin tildes ni mayúsculas). "ana sistemas" encuentra a Ana en
  Ingeniería de Sistemas.

Las métricas (KPIs y gráfica) usan programa y semestre, no la búsqueda: la
búsqueda solo cambia la tabla. Un estudiante con doble programa sale una vez
por programa, como en el módulo Estudiantes.
"""

from collections.abc import Iterable, Sequence
from http import HTTPStatus
from statistics import fmean

from core.exceptions import ApplicationError
from modules.excel.dtos.responses.dashboard import (
    DashboardResultsResponse,
    ProgramOptionResponse,
    ProgramSummaryResponse,
    ResultOptionResponse,
    ResultStudentResponse,
)
from modules.excel.entities.assessment import SIN_PROGRAMA_ID
from modules.excel.entities.dashboard import DashboardDataset, DashboardRecord
from modules.excel.services import dashboard_mappers as mappers
from modules.excel.services.dashboard_normalizer import normalized_key
from modules.excel.services.student_levels_service import student_level

NO_SEMESTER = "sin-semestre"
NO_SEMESTER_LABEL = "Sin semestre"


def build_results(
    dataset: DashboardDataset,
    program_id: str | None,
    semester: str | None,
    search: str | None,
    page: int,
    page_size: int,
) -> DashboardResultsResponse:
    if program_id is not None and program_id not in dataset.program_names:
        raise ApplicationError(
            HTTPStatus.NOT_FOUND, "El programa no existe en esta importación."
        )
    tokens = normalized_key(search).split() if search else []
    records = dataset.records

    def keep(
        record: DashboardRecord,
        by_program: bool = True,
        by_semester: bool = True,
        by_search: bool = True,
    ) -> bool:
        return (
            (not by_program or program_id is None or record.program_id == program_id)
            and (not by_semester or semester is None or _semester_value(record) == semester)
            and (not by_search or _matches(record, tokens))
        )

    metric_rows = [record for record in records if keep(record, by_search=False)]
    rows = [record for record in metric_rows if _matches(record, tokens)]
    rows.sort(key=_sort_key)
    total = len(rows)
    start = (page - 1) * page_size

    return DashboardResultsResponse(
        import_id=dataset.import_id,
        program=(
            ProgramOptionResponse(
                program_id=program_id, name=dataset.program_names[program_id]
            )
            if program_id is not None
            else None
        ),
        semester=semester,
        search=search or None,
        metrics=mappers.metrics_response(metric_rows),
        programs=_program_summaries(
            dataset, (r for r in records if keep(r, by_program=False, by_search=False))
        ),
        program_options=_program_options(
            dataset, [r for r in records if keep(r, by_program=False)]
        ),
        semester_options=_semester_options(
            [r for r in records if keep(r, by_semester=False)]
        ),
        students=[_student(record) for record in rows[start : start + page_size]],
        page=page,
        page_size=page_size,
        total_records=total,
        total_pages=mappers.total_pages(total, page_size),
    )


def _semester_value(record: DashboardRecord) -> str:
    return record.semester or NO_SEMESTER


def _matches(record: DashboardRecord, tokens: Sequence[str]) -> bool:
    if not tokens:
        return True
    text = normalized_key(
        " ".join(
            part
            for part in (
                record.name,
                record.document,
                record.email,
                record.program_name,
            )
            if part
        )
    )
    return all(token in text for token in tokens)


def _sort_key(record: DashboardRecord) -> tuple[str, str, str]:
    return (
        normalized_key(record.name),
        record.document or "",
        normalized_key(record.program_name),
    )


def _student(record: DashboardRecord) -> ResultStudentResponse:
    scores = mappers.scores(record)
    values = [value for value in scores.values() if value is not None]
    level, _, _ = student_level([record])
    return ResultStudentResponse(
        document=record.document,
        document_type=record.document_type,
        name=record.name,
        email=record.email,
        program_id=record.program_id,
        program=record.program_name,
        semester=record.semester,
        presented=record.presented,
        average=round(fmean(values), 2) if values and record.presented else None,
        level=level,
        scores=scores,
        levels=mappers.levels(record),
    )


def _program_summaries(
    dataset: DashboardDataset, records: Iterable[DashboardRecord]
) -> list[ProgramSummaryResponse]:
    grouped: dict[str, list[DashboardRecord]] = {}
    for record in records:
        grouped.setdefault(record.program_id, []).append(record)
    summaries = [
        ProgramSummaryResponse(
            program_id=key,
            name=dataset.program_names[key],
            metrics=mappers.metrics_response(rows),
        )
        for key, rows in grouped.items()
    ]
    # Mejor promedio primero; sin promedio y "Sin programa", al final.
    summaries.sort(
        key=lambda item: (
            item.program_id == SIN_PROGRAMA_ID,
            item.metrics.average_general is None,
            -(item.metrics.average_general or 0),
            normalized_key(item.name),
        )
    )
    return summaries


def _program_options(
    dataset: DashboardDataset, records: list[DashboardRecord]
) -> list[ResultOptionResponse]:
    counts: dict[str, int] = {}
    for record in records:
        counts[record.program_id] = counts.get(record.program_id, 0) + 1
    options = [
        ResultOptionResponse(value=key, label=dataset.program_names[key], count=count)
        for key, count in counts.items()
    ]
    options.sort(
        key=lambda item: (item.value == SIN_PROGRAMA_ID, normalized_key(item.label))
    )
    return options


def _semester_options(records: list[DashboardRecord]) -> list[ResultOptionResponse]:
    counts: dict[str, int] = {}
    for record in records:
        value = _semester_value(record)
        counts[value] = counts.get(value, 0) + 1

    def order(value: str) -> tuple[int, int, str]:
        if value == NO_SEMESTER:
            return (2, 0, value)
        number = "".join(character for character in value if character.isdigit())
        return (0, int(number), value) if number else (1, 0, normalized_key(value))

    return [
        ResultOptionResponse(
            value=value,
            label=NO_SEMESTER_LABEL if value == NO_SEMESTER else value.capitalize(),
            count=counts[value],
        )
        for value in sorted(counts, key=order)
    ]
