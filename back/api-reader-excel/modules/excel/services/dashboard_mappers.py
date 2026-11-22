"""Conversión de registros y filas ORM a DTOs de respuesta del dashboard."""

from collections.abc import Sequence

from modules.excel.dtos.responses.dashboard import (
    DashboardImportListItemResponse,
    DashboardMetricsResponse,
    DashboardProgramStudentResponse,
)
from modules.excel.entities.academic import ExcelImport
from modules.excel.entities.competency import COMPETENCIES
from modules.excel.entities.dashboard import DashboardRecord
from modules.excel.entities.import_status import DELETED_STATUS_LABEL
from modules.excel.services.dashboard_metrics import calculate_metrics

NO_RESULT_LEVEL = "Sin resultado"


def metrics_response(
    records: Sequence[DashboardRecord],
) -> DashboardMetricsResponse:
    return DashboardMetricsResponse.model_validate(calculate_metrics(records))


def scores(record: DashboardRecord) -> dict[str, float | None]:
    return {
        competency.key: record.scores[competency.key]
        for competency in COMPETENCIES
    }


def levels(record: DashboardRecord) -> dict[str, str]:
    return {
        competency.key: record.levels[competency.key] or NO_RESULT_LEVEL
        for competency in COMPETENCIES
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
        simulation=record.simulation,
        group=record.group,
        semester=record.semester,
        presented=record.presented,
        global_score=record.global_score,
        scores=scores(record),
        levels=levels(record),
        ent=record.ent,
    )


def import_list_item_response(
    item: ExcelImport,
) -> DashboardImportListItemResponse:
    return DashboardImportListItemResponse(
        import_id=item.id,
        filename=item.filename,
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


def total_pages(total_items: int, page_size: int) -> int:
    return (total_items + page_size - 1) // page_size
