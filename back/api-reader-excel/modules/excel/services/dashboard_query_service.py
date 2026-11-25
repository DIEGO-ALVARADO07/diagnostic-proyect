"""Casos de uso de consulta del dashboard (solo lectura)."""

from http import HTTPStatus
from typing import Any

from sqlalchemy.orm import Session

from core.exceptions import ApplicationError
from modules.excel.dtos.requests.dashboard import DashboardFilterQuery
from modules.excel.dtos.responses.dashboard import (
    DashboardFilterOptionsResponse,
    DashboardImportResponse,
    DashboardKpisResponse,
    DashboardMetricsResponse,
    DashboardOverviewResponse,
    DashboardProgramResponse,
    DashboardStudentAttemptResponse,
    DashboardStudentResponse,
    ProgramOptionResponse,
    ProgramSummaryResponse,
)
from modules.excel.entities.academic import ExcelImport
from modules.excel.entities.assessment import Source
from modules.excel.entities.competency import COMPARABLE_COMPETENCIES
from modules.excel.entities.dashboard import DashboardDataset, DashboardRecord
from modules.excel.entities.import_status import SNAPSHOT_STATUSES, ImportStatus
from modules.excel.repositories.dashboard_persistence_repository import (
    DashboardPersistenceRepository,
)
from modules.excel.services import dashboard_filters as filters_
from modules.excel.services import dashboard_mappers as mappers
from modules.excel.services.dashboard_audit import build_source_audit
from modules.excel.services.dashboard_dataset_loader import DashboardDatasetLoader
from modules.excel.services.dashboard_normalizer import (
    document_value,
    email_key,
    normalized_key,
)
from modules.security.entities import Account
from modules.security.entities.role import Role

MAX_PAGE_SIZE = 50


class DashboardQueryService:
    def __init__(
        self,
        persistence: DashboardPersistenceRepository,
        loader: DashboardDatasetLoader,
    ) -> None:
        self.persistence = persistence
        self.loader = loader

    # --- Casos de uso -----------------------------------------------------

    def get_active_import(
        self, db: Session, slot: str = Source.ESE.value
    ) -> DashboardImportResponse:
        import_row = self.persistence.get_active_import(db, slot)
        if import_row is None or import_row.deleted_at is not None:
            raise ApplicationError(
                HTTPStatus.NOT_FOUND, "No hay una importación activa."
            )
        return self.import_response(db, import_row)

    def import_response(
        self, db: Session, import_row: ExcelImport
    ) -> DashboardImportResponse:
        """Resumen completo de una importación: filtros, auditoría y overview."""
        dataset = self.loader.load(db, import_row)
        options = filters_.filter_options(dataset)
        return DashboardImportResponse(
            import_id=import_row.id,
            filename=import_row.filename,
            source=import_row.source,
            period=import_row.period,
            status=import_row.status,
            imported_at=import_row.imported_at,
            filters=options,
            source_audit=build_source_audit(dataset),
            overview=self._overview(
                dataset,
                DashboardFilterQuery(),
                page=1,
                page_size=MAX_PAGE_SIZE,
                filter_options=options,
            ),
        )

    def get_overview(
        self,
        db: Session,
        import_id: str,
        filters: DashboardFilterQuery,
        page: int,
        page_size: int,
        account: Account | None = None,
    ) -> DashboardOverviewResponse:
        dataset = self._visible_dataset(db, import_id, account)
        _validate_page(page, page_size)
        return self._overview(
            dataset,
            filters,
            page,
            page_size,
            filters_.filter_options(dataset),
        )

    def get_program(
        self,
        db: Session,
        import_id: str,
        program_id: str,
        filters: DashboardFilterQuery,
        search: str | None,
        page: int,
        page_size: int,
        account: Account | None = None,
    ) -> DashboardProgramResponse:
        dataset = self._visible_dataset(db, import_id, account)
        _validate_page(page, page_size)
        program_name = dataset.program_names.get(program_id)
        if program_name is None:
            raise ApplicationError(
                HTTPStatus.NOT_FOUND, "El programa no existe en esta importación."
            )

        filtered_records = filters_.filter_records(
            dataset.records_by_program.get(program_id, ()), filters
        )
        matching_records = filters_.search_students(filtered_records, search)
        matching_records.sort(key=_student_sort_key)
        total_records = len(matching_records)
        start = (page - 1) * page_size
        return DashboardProgramResponse(
            import_id=dataset.import_id,
            program=ProgramOptionResponse(
                program_id=program_id,
                name=program_name,
            ),
            filters=filters_.filter_options(dataset),
            selected_filters=filters_.selected_filters(filters),
            metrics=mappers.metrics_response(filtered_records),
            institutional_comparison=mappers.metrics_response(
                filters_.filter_records(dataset.records, filters)
            ),
            students=[
                mappers.program_student_response(record)
                for record in matching_records[start : start + page_size]
            ],
            page=page,
            page_size=page_size,
            total_records=total_records,
            total_pages=mappers.total_pages(total_records, page_size),
        )

    def get_student(
        self,
        db: Session,
        import_id: str,
        document: str,
        account: Account | None = None,
    ) -> DashboardStudentResponse:
        dataset = self._visible_dataset(db, import_id, account)
        # Se acepta el correo (identidad del estudiante) o el documento.
        student_key = (
            email_key(document) if "@" in document else document_value(document)
        )
        records = (
            dataset.records_by_student.get(student_key, ())
            if student_key is not None
            else ()
        )
        if not records:
            raise ApplicationError(
                HTTPStatus.NOT_FOUND,
                "No se encontró el estudiante en esta importación.",
            )

        ordered_records = sorted(records, key=_history_sort_key)
        programs = {
            record.program_id: dataset.program_names[record.program_id]
            for record in ordered_records
        }
        # Promedios del mismo programa y aplicación, calculados una vez por grupo.
        comparison_cache: dict[tuple[Any, ...], DashboardMetricsResponse] = {}
        history: list[DashboardStudentAttemptResponse] = []
        for record in ordered_records:
            comparison_key = _comparison_key(record)
            if comparison_key not in comparison_cache:
                comparable_records = [
                    candidate
                    for candidate in dataset.records_by_program[record.program_id]
                    if _comparison_key(candidate) == comparison_key
                ]
                comparison_cache[comparison_key] = mappers.metrics_response(
                    comparable_records
                )
            comparison_metrics = comparison_cache[comparison_key]
            history.append(
                DashboardStudentAttemptResponse(
                    year=record.year,
                    period=record.period,
                    moment=record.moment_number,
                    semester_range=mappers.semester_range_label(record),
                    simulation=record.simulation,
                    group=record.group,
                    semester=record.semester,
                    test_type=record.test_type,
                    program_id=record.program_id,
                    program=record.program_name,
                    presented=record.presented,
                    global_score=record.global_score,
                    program_average_global=comparison_metrics.average_global,
                    program_average_general=comparison_metrics.average_general,
                    scores=mappers.scores(record),
                    levels=mappers.levels(record),
                    ent=record.ent,
                )
            )

        latest_first = list(reversed(ordered_records))
        return DashboardStudentResponse(
            document=next(
                (
                    record.document
                    for record in latest_first
                    if record.document is not None
                ),
                None,
            ),
            name=next(
                (record.name for record in latest_first if record.name), ""
            ),
            email=next(
                (record.email for record in latest_first if record.email),
                None,
            ),
            programs=[
                ProgramOptionResponse(program_id=key, name=name)
                for key, name in sorted(
                    programs.items(), key=lambda item: item[1].casefold()
                )
            ],
            history=history,
            changes=_changes(
                [record for record in ordered_records if record.presented]
            ),
        )

    # --- Apoyo --------------------------------------------------------------

    def _visible_dataset(
        self,
        db: Session,
        import_id: str,
        account: Account | None = None,
    ) -> DashboardDataset:
        """Valida contra la base que la importación es visible y devuelve sus datos.

        Esta comprobación se hace en cada petición, también con caché: así una
        importación desactivada deja de servirse en todos los procesos.
        """
        import_row = self.persistence.get_import(db, import_id)
        if (
            import_row is None
            or import_row.deleted_at is not None
            or import_row.status not in SNAPSHOT_STATUSES
            or (
                account is not None
                and Role(account.role) is not Role.SUPERADMIN
                and import_row.status != ImportStatus.ACTIVE
            )
        ):
            raise ApplicationError(
                HTTPStatus.NOT_FOUND,
                "La importación no existe o no está disponible.",
            )
        return self.loader.load(db, import_row)

    @staticmethod
    def _overview(
        dataset: DashboardDataset,
        filters: DashboardFilterQuery,
        page: int,
        page_size: int,
        filter_options: DashboardFilterOptionsResponse,
    ) -> DashboardOverviewResponse:
        filtered_records = filters_.filter_records(dataset.records, filters)
        program_records: dict[str, list[DashboardRecord]] = {}
        for record in filtered_records:
            program_records.setdefault(record.program_id, []).append(record)

        summaries = [
            ProgramSummaryResponse(
                program_id=program_id,
                name=dataset.program_names[program_id],
                metrics=mappers.metrics_response(records),
            )
            for program_id, records in program_records.items()
        ]
        # Mejor promedio general primero; los programas sin promedio, al final.
        summaries.sort(
            key=lambda item: (
                item.metrics.average_general is None,
                -(item.metrics.average_general or 0),
                normalized_key(item.name),
            )
        )
        total_programs = len(summaries)
        start = (page - 1) * page_size
        kpis = mappers.metrics_response(filtered_records).model_dump()
        kpis["programs"] = total_programs
        return DashboardOverviewResponse(
            import_id=dataset.import_id,
            filters=filter_options,
            selected_filters=filters_.selected_filters(filters),
            kpis=DashboardKpisResponse.model_validate(kpis),
            programs=summaries[start : start + page_size],
            page=page,
            page_size=page_size,
            total_programs=total_programs,
            total_pages=mappers.total_pages(total_programs, page_size),
        )


def _validate_page(page: int, page_size: int) -> None:
    if page < 1:
        raise ApplicationError(
            HTTPStatus.UNPROCESSABLE_ENTITY,
            "El número de página debe ser mayor o igual a 1.",
        )
    if page_size < 1 or page_size > MAX_PAGE_SIZE:
        raise ApplicationError(
            HTTPStatus.UNPROCESSABLE_ENTITY,
            f"El tamaño de página debe estar entre 1 y {MAX_PAGE_SIZE}.",
        )


def _student_sort_key(record: DashboardRecord) -> tuple[Any, ...]:
    return (
        normalized_key(record.name),
        record.document or "",
        record.year,
        normalized_key(record.simulation),
        normalized_key(record.group),
    )


def _history_sort_key(record: DashboardRecord) -> tuple[Any, ...]:
    return (
        record.year,
        normalized_key(record.simulation),
        normalized_key(record.group),
        normalized_key(record.program_name),
    )


def _comparison_key(record: DashboardRecord) -> tuple[Any, ...]:
    """Mismo programa, año, simulacro, grupo, semestre y tipo de prueba."""
    return (
        record.program_id,
        record.year,
        normalized_key(record.simulation),
        normalized_key(record.group),
        normalized_key(record.semester),
        normalized_key(record.test_type),
    )


def _changes(records: list[DashboardRecord]) -> dict[str, str]:
    """Compara el primer y el último intento presentado (global y por competencia)."""

    def compare(values: list[float]) -> str:
        if len(values) < 2:
            return "datos_insuficientes"
        difference = values[-1] - values[0]
        if difference > 0:
            return "mejora"
        if difference < 0:
            return "retroceso"
        return "sin_cambio"

    changes = {
        "global": compare(
            [
                record.global_score
                for record in records
                if record.global_score is not None
            ]
        )
    }
    for competency in COMPARABLE_COMPETENCIES:
        changes[competency.key] = compare(
            [
                score
                for record in records
                if (score := record.scores[competency.key]) is not None
            ]
        )
    return changes
