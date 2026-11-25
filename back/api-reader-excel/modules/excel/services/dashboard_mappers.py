"""Conversión de registros y filas ORM a DTOs de respuesta del dashboard."""

from collections.abc import Sequence

from modules.excel.dtos.responses.dashboard import (
    DashboardActiveImportResponse,
    DashboardImportListItemResponse,
    DashboardMetricsResponse,
    DashboardProgramStudentResponse,
)
from modules.excel.entities.academic import ExcelImport
from modules.excel.entities.assessment import Source, semester_range
from modules.excel.entities.competency import (
    COMPARABLE_COMPETENCIES,
    Competency,
    classify_level,
)
from modules.excel.entities.dashboard import DashboardRecord
from modules.excel.entities.import_status import DELETED_STATUS_LABEL
from modules.excel.services.dashboard_metrics import calculate_metrics

NO_RESULT_LEVEL = "Sin resultado"


def metrics_response(
    records: Sequence[DashboardRecord],
    competencies: Sequence[Competency] = COMPARABLE_COMPETENCIES,
) -> DashboardMetricsResponse:
    return DashboardMetricsResponse.model_validate(
        calculate_metrics(records, competencies)
    )


def scores(record: DashboardRecord) -> dict[str, float | None]:
    return {
        competency.key: record.scores[competency.key]
        for competency in COMPARABLE_COMPETENCIES
    }


def levels(record: DashboardRecord) -> dict[str, str]:
    """Nivel calculado con la escala común; el del Excel queda para auditoría."""
    return {
        competency.key: (
            classify_level(competency, record.scores[competency.key])
            or NO_RESULT_LEVEL
        )
        for competency in COMPARABLE_COMPETENCIES
    }


def program_student_response(
    record: DashboardRecord,
) -> DashboardProgramStudentResponse:
    return DashboardProgramStudentResponse(
        document=record.document,
        name=record.name,
        email=record.email,
        program_id=record.program_id,
        program=record.program_name,
        year=record.year,
        period=record.period,
        moment=record.moment_number,
        semester_range=semester_range_label(record),
        simulation=record.simulation,
        group=record.group,
        semester=record.semester,
        presented=record.presented,
        global_score=record.global_score,
        scores=scores(record),
        levels=levels(record),
        ent=record.ent,
    )


def active_import_response(
    slot: str, item: ExcelImport
) -> DashboardActiveImportResponse:
    return DashboardActiveImportResponse(
        slot=slot,
        source=item.source,
        period=item.period,
        import_id=item.id,
        filename=item.filename,
    )


def import_list_item_response(
    item: ExcelImport,
) -> DashboardImportListItemResponse:
    return DashboardImportListItemResponse(
        import_id=item.id,
        filename=item.filename,
        source=item.source,
        period=item.period,
        status=(
            DELETED_STATUS_LABEL if item.deleted_at is not None else item.status
        ),
        imported_at=item.imported_at,
        activated_at=item.activated_at,
        bd_gen_row_count=item.bd_gen_row_count,
        td_programas_row_count=item.td_programas_row_count,
        td_programas_selected_year=item.td_programas_selected_year,
        deleted_at=item.deleted_at,
    )


def semester_range_label(record: DashboardRecord) -> str | None:
    """Semestres que mide la prueba del registro (``"4–6"``), según su momento."""
    measured = semester_range(Source(record.source), record.moment_number)
    return measured.label if measured is not None else None


def total_pages(total_items: int, page_size: int) -> int:
    return (total_items + page_size - 1) // page_size
