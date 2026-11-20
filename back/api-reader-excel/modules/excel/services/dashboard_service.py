from collections import Counter
from hashlib import sha256
from http import HTTPStatus
from typing import Any
from uuid import uuid4

import fastexcel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.exceptions import ApplicationError
from modules.excel.entities.academic import (
    AcademicProgram,
    AcademicResult,
    DashboardState,
    ExcelImport,
    TdProgramasReference,
)
from modules.excel.dtos.requests.dashboard import DashboardFilterQuery
from modules.excel.dtos.requests.read_workbook import ReadWorkbookRequest
from modules.excel.dtos.responses.dashboard import (
    DashboardAuditDifferenceResponse,
    DashboardFilterOptionsResponse,
    DashboardImportListItemResponse,
    DashboardImportListResponse,
    DashboardImportResponse,
    DashboardKpisResponse,
    DashboardMetricsResponse,
    DashboardOverviewResponse,
    DashboardProgramResponse,
    DashboardProgramStudentResponse,
    DashboardSelectedFiltersResponse,
    DashboardSourceAuditResponse,
    DashboardStudentAttemptResponse,
    DashboardStudentResponse,
    ProgramOptionResponse,
    ProgramSummaryResponse,
)
from modules.excel.entities.dashboard import (
    DashboardDataset,
    DashboardRecord,
)
from modules.excel.repositories.dashboard_repository import (
    DashboardWorkbookError,
    DashboardWorkbookRepository,
)
from modules.excel.repositories.dashboard_persistence_repository import (
    DashboardPersistenceRepository,
)
from modules.excel.services.dashboard_metrics import (
    COMPETENCIES,
    calculate_metrics,
)
from modules.excel.services.dashboard_normalizer import (
    clean_text,
    document_value,
    normalized_key,
)
from modules.excel.services.dashboard_processor import DashboardProcessor
from modules.excel.services.excel_service import MAX_UPLOAD_BYTES, ExcelService
from modules.security.entities import Account
from modules.security.entities.base import utcnow
from modules.security.entities.role import Role

MAX_PAGE_SIZE = 50


class DashboardService:
    def __init__(
        self,
        repository: DashboardWorkbookRepository | None = None,
        processor: DashboardProcessor | None = None,
        persistence: DashboardPersistenceRepository | None = None,
        excel_service: ExcelService | None = None,
    ) -> None:
        self.repository = repository or DashboardWorkbookRepository()
        self.processor = processor or DashboardProcessor()
        self.persistence = persistence or DashboardPersistenceRepository()
        self.excel_service = excel_service or ExcelService()

    def validate_upload(self, filename: str, account: Account) -> str:
        return self.excel_service.validate_upload(filename, account)

    def import_workbook(
        self,
        request: ReadWorkbookRequest,
        account: Account,
        db: Session,
    ) -> DashboardImportResponse:
        safe_filename = self.validate_upload(request.filename, account)
        if len(request.content) > MAX_UPLOAD_BYTES:
            raise ApplicationError(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                "El archivo supera el límite de 30 MB.",
            )
        file_hash = sha256(request.content).hexdigest()
        existing = self.persistence.find_import_by_hash(db, file_hash)
        if existing is not None:
            if existing.deleted_at is not None:
                raise ApplicationError(
                    HTTPStatus.CONFLICT,
                    "Este archivo fue desactivado y no se puede importar de nuevo.",
                )
            if existing.status in {"ACTIVE", "HISTORICAL"}:
                return self._import_response(db, existing)
            raise ApplicationError(
                HTTPStatus.CONFLICT,
                "Este archivo ya fue procesado y no puede volver a importarse.",
            )

        import_row = ExcelImport(
            id=str(uuid4()),
            filename=safe_filename,
            file_sha256=file_hash,
            imported_by_user_id=account.id,
            status="PROCESSING",
            dataset_mode="SNAPSHOT",
            bd_gen_row_count=0,
            td_programas_row_count=0,
            inserted_count=0,
            rejected_count=0,
        )
        db.add(import_row)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            existing = self.persistence.find_import_by_hash(db, file_hash)
            if (
                existing is not None
                and existing.deleted_at is None
                and existing.status in {"ACTIVE", "HISTORICAL"}
            ):
                return self._import_response(db, existing)
            raise ApplicationError(
                HTTPStatus.CONFLICT,
                "Este archivo ya fue procesado o está en proceso.",
            ) from None

        try:
            sheets = self.repository.read_sheets(request.content)
            data = self.processor.process(safe_filename, sheets)
            self.persistence.persist_snapshot(db, import_row, data)
            import_row.status = "VALIDATED"
            db.flush()
            dashboard_state = db.scalar(
                select(DashboardState)
                .where(DashboardState.id == 1)
                .with_for_update()
            )
            if dashboard_state is None:
                raise RuntimeError(
                    "No existe el estado inicial del dashboard; "
                    "aplica las migraciones Alembic."
                )
            active_import = (
                db.get(ExcelImport, dashboard_state.active_import_id)
                if dashboard_state.active_import_id is not None
                else None
            )
            if active_import is not None:
                active_import.status = "HISTORICAL"
            import_row.status = "ACTIVE"
            import_row.activated_at = utcnow()
            dashboard_state.active_import_id = import_row.id
            db.commit()
        except DashboardWorkbookError as error:
            self._mark_failed(db, import_row.id, error)
            raise ApplicationError(
                HTTPStatus.UNPROCESSABLE_ENTITY, str(error)
            ) from None
        except (fastexcel.FastExcelError, ValueError) as error:
            self._mark_failed(db, import_row.id, error)
            raise ApplicationError(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                "No se pudo leer el libro Excel o su estructura no es válida.",
            ) from None
        except Exception as error:
            self._mark_failed(db, import_row.id, error)
            raise

        return self._import_response(db, import_row)

    def get_active_import(self, db: Session) -> DashboardImportResponse:
        import_row = self.persistence.get_active_import(db)
        if import_row is None or import_row.deleted_at is not None:
            raise ApplicationError(
                HTTPStatus.NOT_FOUND, "No hay una importación activa."
            )
        return self._import_response(db, import_row)

    def list_imports(self, db: Session, limit: int) -> DashboardImportListResponse:
        imports = self.persistence.list_imports(db, limit)
        return DashboardImportListResponse(
            active_import_id=self.persistence.get_active_import_id(db),
            imports=[
                DashboardImportListItemResponse(
                    import_id=item.id,
                    filename=item.filename,
                    status=(
                        "DELETED" if item.deleted_at is not None else item.status
                    ),
                    imported_at=item.imported_at,
                    activated_at=item.activated_at,
                    bd_gen_row_count=item.bd_gen_row_count,
                    td_programas_row_count=item.td_programas_row_count,
                    td_programas_selected_year=item.td_programas_selected_year,
                    deleted_at=item.deleted_at,
                )
                for item in imports
            ],
        )

    def list_admin_imports(
        self, db: Session, limit: int
    ) -> DashboardImportListResponse:
        imports = self.persistence.list_all_imports(db, limit)
        return DashboardImportListResponse(
            active_import_id=self.persistence.get_active_import_id(db),
            imports=[
                DashboardImportListItemResponse(
                    import_id=item.id,
                    filename=item.filename,
                    status=(
                        "DELETED" if item.deleted_at is not None else item.status
                    ),
                    imported_at=item.imported_at,
                    activated_at=item.activated_at,
                    bd_gen_row_count=item.bd_gen_row_count,
                    td_programas_row_count=item.td_programas_row_count,
                    td_programas_selected_year=item.td_programas_selected_year,
                    deleted_at=item.deleted_at,
                )
                for item in imports
            ],
        )

    def delete_import(self, db: Session, import_id: str) -> None:
        dashboard_state = db.scalar(
            select(DashboardState)
            .where(DashboardState.id == 1)
            .with_for_update()
        )
        if dashboard_state is None:
            raise ApplicationError(
                HTTPStatus.CONFLICT,
                "No se pudo verificar la importación activa.",
            )

        import_row = db.scalar(
            select(ExcelImport)
            .where(ExcelImport.id == import_id)
            .with_for_update()
        )
        if import_row is None:
            raise ApplicationError(
                HTTPStatus.NOT_FOUND, "La importación no existe."
            )
        if import_row.deleted_at is not None:
            return
        if import_row.status not in {"ACTIVE", "HISTORICAL", "FAILED"}:
            raise ApplicationError(
                HTTPStatus.CONFLICT,
                "Solo se pueden desactivar importaciones activas, históricas o fallidas.",
            )

        if dashboard_state.active_import_id == import_id:
            dashboard_state.active_import_id = None
        import_row.deleted_at = utcnow()
        db.commit()

    def _import_response(
        self, db: Session, import_row: ExcelImport
    ) -> DashboardImportResponse:
        dataset = self._load_dataset(db, import_row)
        filters = self._filter_options(dataset)
        overview = self._overview(
            dataset,
            DashboardFilterQuery(),
            page=1,
            page_size=MAX_PAGE_SIZE,
            filter_options=filters,
        )
        audit = self._source_audit(dataset)
        return DashboardImportResponse(
            import_id=import_row.id,
            filename=import_row.filename,
            status=import_row.status,
            imported_at=import_row.imported_at,
            filters=filters,
            source_audit=audit,
            overview=overview,
        )

    @staticmethod
    def _mark_failed(db: Session, import_id: str, error: Exception) -> None:
        db.rollback()
        import_row = db.get(ExcelImport, import_id)
        if import_row is None:
            raise RuntimeError(
                "No se pudo recuperar el registro de importación fallido."
            ) from error
        import_row.status = "FAILED"
        import_row.validation_summary = {
            "status": "failed",
            "error_type": type(error).__name__,
        }
        db.commit()

    def get_overview(
        self,
        db: Session,
        import_id: str,
        filters: DashboardFilterQuery,
        page: int,
        page_size: int,
        account: Account | None = None,
    ) -> DashboardOverviewResponse:
        dataset = self._get_dataset(db, import_id, account)
        self._validate_page(page, page_size)
        return self._overview(
            dataset,
            filters,
            page,
            page_size,
            self._filter_options(dataset),
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
        dataset = self._get_dataset(db, import_id, account)
        self._validate_page(page, page_size)
        program_name = dataset.program_names.get(program_id)
        if program_name is None:
            raise ApplicationError(
                HTTPStatus.NOT_FOUND, "El programa no existe en esta importación."
            )

        filtered_records = [
            record
            for record in dataset.records_by_program.get(program_id, ())
            if self._matches(record, filters)
        ]
        matching_records = self._search_students(filtered_records, search)
        matching_records.sort(key=self._student_sort_key)
        total_records = len(matching_records)
        start = (page - 1) * page_size
        students = [
            self._program_student(record)
            for record in matching_records[start : start + page_size]
        ]
        institutional_records = [
            record
            for record in dataset.records
            if self._matches(record, filters)
        ]
        program = ProgramOptionResponse(
            program_id=program_id,
            name=program_name,
        )
        return DashboardProgramResponse(
            import_id=dataset.import_id,
            program=program,
            filters=self._filter_options(dataset),
            selected_filters=self._selected_filters(filters),
            metrics=self._metrics(filtered_records),
            institutional_comparison=self._metrics(institutional_records),
            students=students,
            page=page,
            page_size=page_size,
            total_records=total_records,
            total_pages=self._total_pages(total_records, page_size),
        )

    def get_student(
        self,
        db: Session,
        import_id: str,
        document: str,
        account: Account | None = None,
    ) -> DashboardStudentResponse:
        dataset = self._get_dataset(db, import_id, account)
        normalized_document = document_value(document)
        records = (
            dataset.records_by_student.get(normalized_document, ())
            if normalized_document is not None
            else ()
        )
        if not records:
            raise ApplicationError(
                HTTPStatus.NOT_FOUND,
                "No se encontró el estudiante en esta importación.",
            )

        ordered_records = sorted(records, key=self._history_sort_key)
        programs = {
            record.program_id: dataset.program_names[record.program_id]
            for record in ordered_records
        }
        comparison_cache: dict[tuple[Any, ...], float | None] = {}
        history: list[DashboardStudentAttemptResponse] = []
        for record in ordered_records:
            comparison_key = self._comparison_key(record)
            if comparison_key not in comparison_cache:
                comparable_records = [
                    candidate
                    for candidate in dataset.records_by_program[record.program_id]
                    if self._comparison_key(candidate) == comparison_key
                ]
                comparison_cache[comparison_key] = self._metrics(
                    list(comparable_records)
                ).average_global
            history.append(
                DashboardStudentAttemptResponse(
                    year=record.year,
                    simulation=record.simulation,
                    group=record.group,
                    semester=record.semester,
                    test_type=record.test_type,
                    program_id=record.program_id,
                    program=record.program_name,
                    presented=record.presented,
                    global_score=record.global_score,
                    program_average_global=comparison_cache[comparison_key],
                    scores=self._scores(record),
                    levels=self._levels(record),
                    ent=record.ent,
                )
            )

        presented_history = [
            record for record in ordered_records if record.presented
        ]
        return DashboardStudentResponse(
            document=next(
                record.document
                for record in reversed(ordered_records)
                if record.document is not None
            ),
            name=next(
                (record.name for record in reversed(ordered_records) if record.name),
                "",
            ),
            email=next(
                (
                    record.email
                    for record in reversed(ordered_records)
                    if record.email
                ),
                None,
            ),
            programs=[
                ProgramOptionResponse(program_id=key, name=name)
                for key, name in sorted(
                    programs.items(), key=lambda item: item[1].casefold()
                )
            ],
            history=history,
            changes=self._changes(presented_history),
        )

    def _overview(
        self,
        dataset: DashboardDataset,
        filters: DashboardFilterQuery,
        page: int,
        page_size: int,
        filter_options: DashboardFilterOptionsResponse,
    ) -> DashboardOverviewResponse:
        filtered_records = [
            record for record in dataset.records if self._matches(record, filters)
        ]
        program_records: dict[str, list[DashboardRecord]] = {}
        for record in filtered_records:
            program_records.setdefault(record.program_id, []).append(record)

        summaries = [
            ProgramSummaryResponse(
                program_id=program_id,
                name=dataset.program_names[program_id],
                metrics=self._metrics(records),
            )
            for program_id, records in program_records.items()
        ]
        summaries.sort(
            key=lambda item: (
                item.metrics.average_global is None,
                -(item.metrics.average_global or 0),
                normalized_key(item.name),
            )
        )
        total_programs = len(summaries)
        start = (page - 1) * page_size
        kpis = self._metrics(filtered_records).model_dump()
        kpis["programs"] = total_programs
        return DashboardOverviewResponse(
            import_id=dataset.import_id,
            filters=filter_options,
            selected_filters=self._selected_filters(filters),
            kpis=DashboardKpisResponse.model_validate(kpis),
            programs=summaries[start : start + page_size],
            page=page,
            page_size=page_size,
            total_programs=total_programs,
            total_pages=self._total_pages(total_programs, page_size),
        )

    @staticmethod
    def _matches(
        record: DashboardRecord, filters: DashboardFilterQuery
    ) -> bool:
        if filters.year is not None and record.year != filters.year:
            return False
        if filters.simulation is not None and normalized_key(
            record.simulation
        ) != normalized_key(filters.simulation):
            return False
        if filters.group is not None and normalized_key(
            record.group
        ) != normalized_key(filters.group):
            return False
        if filters.semester is not None and normalized_key(
            record.semester
        ) != normalized_key(filters.semester):
            return False
        if filters.test_type is not None and normalized_key(
            record.test_type
        ) != normalized_key(filters.test_type):
            return False
        return filters.presented is None or record.presented == filters.presented

    @staticmethod
    def _filter_options(
        dataset: DashboardDataset,
    ) -> DashboardFilterOptionsResponse:
        def values_for(attribute: str) -> list[str]:
            variants: dict[str, Counter[str]] = {}
            for record in dataset.records:
                value = getattr(record, attribute)
                if value is None:
                    continue
                variants.setdefault(normalized_key(value), Counter())[value] += 1
            return [
                sorted(
                    counter,
                    key=lambda value: (-counter[value], value.casefold()),
                )[0]
                for _, counter in sorted(variants.items())
            ]

        return DashboardFilterOptionsResponse(
            years=sorted({record.year for record in dataset.records}),
            simulations=values_for("simulation"),
            groups=values_for("group"),
            programs=[
                ProgramOptionResponse(program_id=program_id, name=name)
                for program_id, name in sorted(
                    dataset.program_names.items(),
                    key=lambda item: normalized_key(item[1]),
                )
            ],
            semesters=values_for("semester"),
            test_types=values_for("test_type"),
            presented=[
                value
                for value in (False, True, None)
                if any(record.presented is value for record in dataset.records)
            ],
        )

    @staticmethod
    def _selected_filters(
        filters: DashboardFilterQuery,
    ) -> DashboardSelectedFiltersResponse:
        return DashboardSelectedFiltersResponse(**filters.model_dump())

    @staticmethod
    def _metrics(
        records: list[DashboardRecord],
    ) -> DashboardMetricsResponse:
        return DashboardMetricsResponse.model_validate(
            calculate_metrics(records)
        )

    @staticmethod
    def _program_student(
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
            scores=DashboardService._scores(record),
            levels=DashboardService._levels(record),
            ent=record.ent,
        )

    @staticmethod
    def _scores(record: DashboardRecord) -> dict[str, float | None]:
        return {
            competency.key: record.scores[index]
            for index, competency in enumerate(COMPETENCIES)
        }

    @staticmethod
    def _levels(record: DashboardRecord) -> dict[str, str]:
        return {
            competency.key: record.levels[index] or "Sin resultado"
            for index, competency in enumerate(COMPETENCIES)
        }

    @staticmethod
    def _search_students(
        records: list[DashboardRecord],
        search: str | None,
    ) -> list[DashboardRecord]:
        query = clean_text(search)
        if query is None:
            return records
        normalized_query = normalized_key(query)
        return [
            record
            for record in records
            if normalized_query in normalized_key(record.document)
            or normalized_query in normalized_key(record.name)
        ]

    @staticmethod
    def _student_sort_key(record: DashboardRecord) -> tuple[Any, ...]:
        return (
            normalized_key(record.name),
            record.document or "",
            record.year,
            normalized_key(record.simulation),
            normalized_key(record.group),
        )

    @staticmethod
    def _history_sort_key(record: DashboardRecord) -> tuple[Any, ...]:
        return (
            record.year,
            normalized_key(record.simulation),
            normalized_key(record.group),
            normalized_key(record.program_name),
        )

    @staticmethod
    def _comparison_key(record: DashboardRecord) -> tuple[Any, ...]:
        return (
            record.program_id,
            record.year,
            normalized_key(record.simulation),
            normalized_key(record.group),
            normalized_key(record.semester),
            normalized_key(record.test_type),
        )

    @staticmethod
    def _changes(
        records: list[DashboardRecord],
    ) -> dict[str, str]:
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
        for index, competency in enumerate(COMPETENCIES):
            changes[competency.key] = compare(
                [
                    record.scores[index]
                    for record in records
                    if record.scores[index] is not None
                ]
            )
        return changes

    def _source_audit(
        self,
        dataset: DashboardDataset,
    ) -> DashboardSourceAuditResponse:
        years = sorted({record.year for record in dataset.records})
        compared_rows = 0
        compared_metrics = 0
        differences: list[DashboardAuditDifferenceResponse] = []
        difference_count = 0
        if dataset.td_programs_year is not None:
            program_id_by_name = {
                name: program_id
                for program_id, name in dataset.program_names.items()
            }
            for (simulation_key, program_key), td_values in (
                dataset.td_programs_summary.items()
            ):
                program_id = program_id_by_name.get(program_key)
                if program_id is None:
                    continue
                matched = [
                    record
                    for record in dataset.records_by_program[program_id]
                    if record.year == dataset.td_programs_year
                    and normalized_key(record.simulation) == simulation_key
                ]
                if not matched:
                    continue
                calculated = DashboardMetricsResponse.model_validate(
                    calculate_metrics(matched)
                )
                calculated_values: dict[str, float | None] = {
                    key: item.average
                    for key, item in calculated.competencies.items()
                }
                calculated_values.update(
                    {
                        "average_global": calculated.average_global,
                        "simple_competence_average": (
                            calculated.simple_competence_average
                        ),
                    }
                )
                compared_rows += 1
                for metric, td_value in td_values.items():
                    calculated_value = calculated_values[metric]
                    if td_value is None or calculated_value is None:
                        continue
                    compared_metrics += 1
                    difference = abs(td_value - calculated_value)
                    if difference > 0.0001:
                        difference_count += 1
                        if len(differences) < 100:
                            differences.append(
                                DashboardAuditDifferenceResponse(
                                    simulation=next(
                                        record.simulation
                                        for record in matched
                                    ),
                                    program=dataset.program_names[program_id],
                                    metric=metric,
                                    td_programas_value=td_value,
                                    bd_gen_value=calculated_value,
                                    absolute_difference=difference,
                                )
                            )
        return DashboardSourceAuditResponse(
            years_in_bd_gen=years,
            td_programas_visible_year=dataset.td_programs_year,
            records_without_document=dataset.records_without_document,
            compared_program_rows=compared_rows,
            compared_metrics=compared_metrics,
            difference_count=difference_count,
            differences=differences,
        )

    def _get_dataset(
        self,
        db: Session,
        import_id: str,
        account: Account | None = None,
    ) -> DashboardDataset:
        import_row = self.persistence.get_import(db, import_id)
        if (
            import_row is None
            or import_row.deleted_at is not None
            or import_row.status not in {"ACTIVE", "HISTORICAL"}
            or (
                account is not None
                and Role(account.role) is not Role.SUPERADMIN
                and import_row.status != "ACTIVE"
            )
        ):
            raise ApplicationError(
                HTTPStatus.NOT_FOUND,
                "La importación no existe o no está disponible.",
            )
        return self._load_dataset(db, import_row)

    @staticmethod
    def _load_dataset(
        db: Session, import_row: ExcelImport
    ) -> DashboardDataset:
        results = list(
            db.scalars(
                select(AcademicResult)
                .where(AcademicResult.import_id == import_row.id)
                .order_by(AcademicResult.source_row_number)
            )
        )
        program_ids = {
            result.program_id
            for result in results
            if result.program_id is not None
        }
        programs = {
            str(program.id): program.canonical_name
            for program in db.scalars(
                select(AcademicProgram).where(
                    AcademicProgram.id.in_(program_ids)
                )
            )
        } if program_ids else {}

        def as_float(value: Any) -> float | None:
            return float(value) if value is not None else None

        records: list[DashboardRecord] = []
        records_by_program: dict[str, list[DashboardRecord]] = {}
        records_by_student: dict[str, list[DashboardRecord]] = {}
        for result in results:
            program_id = str(result.program_id) if result.program_id else ""
            program_name = programs.get(program_id, result.program_name_raw)
            name = " ".join(
                value
                for value in (result.first_name_source, result.last_name_source)
                if value
            )
            record = DashboardRecord(
                source_row_number=result.source_row_number,
                document=result.document_number_source,
                name=name,
                email=result.email_source,
                program_id=program_id,
                program_name=program_name,
                scores=(
                    as_float(result.reading_score),
                    as_float(result.writing_score),
                    as_float(result.citizenship_score),
                    as_float(result.quantitative_score),
                    as_float(result.english_score),
                ),
                global_score=as_float(result.global_score),
                moment=result.moment_raw,
                test_type=result.assessment_type,
                semester=result.semester_raw,
                year=result.year,
                simulation=result.simulation_name,
                group=result.group_name,
                presented=result.applies_simulacro,
                levels=(
                    result.reading_level,
                    result.writing_level,
                    result.citizenship_level,
                    result.quantitative_level,
                    result.english_level,
                ),
                ent=result.ent_raw,
            )
            records.append(record)
            records_by_program.setdefault(program_id, []).append(record)
            if record.document is not None:
                records_by_student.setdefault(record.document, []).append(record)

        td_summary: dict[
            tuple[str, str], dict[str, float | None]
        ] = {}
        references = db.scalars(
            select(TdProgramasReference).where(
                TdProgramasReference.import_id == import_row.id
            )
        )
        for reference in references:
            td_summary[
                (reference.simulation_key, reference.program_name_raw)
            ] = {
                competency.key: as_float(value)
                for competency, value in zip(
                    COMPETENCIES,
                    (
                        reference.reading_average,
                        reference.writing_average,
                        reference.citizenship_average,
                        reference.quantitative_average,
                        reference.english_average,
                    ),
                )
            } | {
                "average_global": as_float(
                    reference.global_average_from_records
                ),
                "simple_competence_average": as_float(
                    reference.average_of_competency_averages
                ),
            }

        program_names = {
            program_id: records_for_program[0].program_name
            for program_id, records_for_program in records_by_program.items()
        }
        return DashboardDataset(
            import_id=import_row.id,
            filename=import_row.filename,
            records=records,
            records_by_program=records_by_program,
            records_by_student=records_by_student,
            program_names=program_names,
            td_programs_year=import_row.td_programas_selected_year,
            td_programs_summary=td_summary,
            records_without_document=sum(
                record.document is None for record in records
            ),
        )

    @staticmethod
    def _validate_page(page: int, page_size: int) -> None:
        if page < 1:
            raise ApplicationError(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                "El número de página debe ser mayor o igual a 1.",
            )
        if page_size < 1 or page_size > MAX_PAGE_SIZE:
            raise ApplicationError(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                "El tamaño de página debe estar entre 1 y 50.",
            )

    @staticmethod
    def _total_pages(total_items: int, page_size: int) -> int:
        return (total_items + page_size - 1) // page_size
