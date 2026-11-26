"""Casos de uso de escritura del dashboard: importar, listar y desactivar."""

from collections import Counter
from hashlib import sha256
from http import HTTPStatus
from uuid import uuid4

import fastexcel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.exceptions import ApplicationError
from core.orm import utcnow
from modules.excel.dtos.requests.read_workbook import ReadWorkbookRequest
from modules.excel.dtos.responses.dashboard import (
    DashboardImportListResponse,
    DashboardImportResponse,
    DashboardImportRestoreResponse,
)
from modules.excel.entities.academic import ExcelImport
from modules.excel.entities.assessment import (
    ProgramResolution,
    Source,
    StudentMatch,
    active_slot,
)
from modules.excel.entities.import_status import (
    DEACTIVATABLE_STATUSES,
    SNAPSHOT_DATASET_MODE,
    SNAPSHOT_STATUSES,
    ImportStatus,
)
from modules.excel.repositories.dashboard_persistence_repository import (
    DashboardPersistenceRepository,
)
from modules.excel.repositories.corhuila_workbook_repository import (
    CorhuilaWorkbookRepository,
)
from modules.excel.repositories.dashboard_repository import (
    DashboardWorkbookError,
    DashboardWorkbookRepository,
)
from modules.excel.services import dashboard_mappers as mappers
from modules.excel.services.dashboard_dataset_loader import DashboardDatasetLoader
from modules.excel.services.dashboard_processor import DashboardProcessor
from modules.excel.services.dashboard_query_service import DashboardQueryService
from modules.excel.services.excel_service import MAX_UPLOAD_BYTES, ExcelService
from modules.excel.services.corhuila_processor import CorhuilaProcessor
from modules.excel.services.program_resolution import (
    active_ese_import_id,
    build_ese_index,
    refresh_corhuila_programs,
)
from modules.security.entities import Account


class DashboardImportService:
    def __init__(
        self,
        repository: DashboardWorkbookRepository,
        processor: DashboardProcessor,
        persistence: DashboardPersistenceRepository,
        excel_service: ExcelService,
        loader: DashboardDatasetLoader,
        queries: DashboardQueryService,
    ) -> None:
        self.repository = repository
        self.processor = processor
        self.persistence = persistence
        self.excel_service = excel_service
        self.loader = loader
        self.queries = queries
        self.corhuila_repository = CorhuilaWorkbookRepository()
        self.corhuila_processor = CorhuilaProcessor()

    def validate_upload(self, filename: str, account: Account) -> str:
        return self.excel_service.validate_upload(filename, account)

    def import_workbook(
        self,
        request: ReadWorkbookRequest,
        account: Account,
        db: Session,
        source: Source = Source.ESE,
        period: str | None = None,
    ) -> DashboardImportResponse:
        """Importa el libro como nueva instantánea activa de su espacio.

        ``source`` elige el lector: ESE (``BD GEN`` + ``TD PROGRAMAS``) o
        CORHUILA (``Calificaciones``). ``period`` es el periodo de la carga
        (``2026-2``); la API lo exige siempre y CORHUILA no funciona sin él.

        Un mismo archivo (mismo SHA-256) no se procesa dos veces: si ya está
        activo o histórico se devuelve su resumen; si falló o fue desactivado
        se rechaza.
        """
        if source is Source.CORHUILA and period is None:
            raise ApplicationError(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                "Una importación de CORHUILA requiere el periodo (AAAA-1 o AAAA-2).",
            )
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
                    "Este archivo ya se había importado y está desactivado. "
                    "Restáuralo desde Importaciones en vez de subirlo de nuevo.",
                )
            if existing.status in SNAPSHOT_STATUSES:
                return self.queries.import_response(db, existing)
            raise ApplicationError(
                HTTPStatus.CONFLICT,
                "Este archivo ya fue procesado y no puede volver a importarse.",
            )

        # Se confirma primero el registro PROCESSING: la restricción única del
        # hash impide que dos subidas simultáneas del mismo archivo avancen.
        import_row = ExcelImport(
            id=str(uuid4()),
            filename=safe_filename,
            source=source.value,
            period=period,
            file_sha256=file_hash,
            imported_by_user_id=account.id,
            status=ImportStatus.PROCESSING,
            dataset_mode=SNAPSHOT_DATASET_MODE,
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
                and existing.status in SNAPSHOT_STATUSES
            ):
                return self.queries.import_response(db, existing)
            raise ApplicationError(
                HTTPStatus.CONFLICT,
                "Este archivo ya fue procesado o está en proceso.",
            ) from None

        try:
            if source is Source.CORHUILA:
                self._import_corhuila(db, import_row, request.content, period)
            else:
                self._import_ese(db, import_row, request.content, period)
            db.commit()
            # La importación puede renombrar programas compartidos con otras
            # importaciones (nombre visible), así que se descartan los datasets
            # en caché para que no muestren el nombre anterior.
            self.loader.cache.clear()
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

        return self.queries.import_response(db, import_row)

    def _import_ese(
        self,
        db: Session,
        import_row: ExcelImport,
        content: bytes,
        period: str | None,
    ) -> None:
        sheets = self.repository.read_sheets(content)
        data = self.processor.process(import_row.filename, sheets)
        self.persistence.persist_snapshot(db, import_row, data)
        if period is not None:
            # El archivo de ESE trae toda la historia; se informa cuántas filas
            # son del periodo de la carga (0 = quizá se eligió mal el periodo).
            summary = dict(import_row.validation_summary or {})
            quality = dict(summary.get("data_quality") or {})
            period_moment = dict(quality.get("period_moment") or {})
            period_moment["upload_period_rows"] = sum(
                record.period == period for record in data.records
            )
            quality["period_moment"] = period_moment
            summary["data_quality"] = quality
            import_row.validation_summary = summary
        import_row.status = ImportStatus.VALIDATED
        db.flush()
        self._activate(db, import_row)
        db.flush()
        # Un ESE nuevo puede traer estudiantes que CORHUILA no encontraba: se
        # recalcula y se guarda su estudiante y programa en la misma transacción.
        refresh_corhuila_programs(db)

    def _import_corhuila(
        self,
        db: Session,
        import_row: ExcelImport,
        content: bytes,
        period: str,
    ) -> None:
        workbook = self.corhuila_repository.read_rows(content)
        data = self.corhuila_processor.process(import_row.filename, period, workbook)
        index = build_ese_index(db, active_ese_import_id(db))
        results = self.persistence.persist_corhuila_snapshot(
            db, import_row, data, index
        )
        matches = Counter(result.student_match for result in results)
        import_row.validation_summary = {
            "status": "validated",
            "rows_without_document": sum(
                record.document is None for record in data.records
            ),
            "data_quality": {
                "corhuila": {
                    **data.file_quality,
                    "sheet": data.sheet_name,
                    "matches": {
                        match.value: matches.get(match.value, 0)
                        for match in StudentMatch
                    },
                    "without_program": sum(
                        result.program_resolution
                        == ProgramResolution.SIN_PROGRAMA.value
                        for result in results
                    ),
                    "ese_import_id": index.import_id,
                }
            },
        }
        import_row.status = ImportStatus.VALIDATED
        db.flush()
        self._activate(db, import_row)

    def list_imports(self, db: Session, limit: int) -> DashboardImportListResponse:
        """Importaciones no desactivadas (activa, históricas y fallidas)."""
        return self._import_list_response(
            db, self.persistence.list_imports(db, limit)
        )

    def list_admin_imports(
        self, db: Session, limit: int
    ) -> DashboardImportListResponse:
        """Todas las importaciones; las desactivadas aparecen como DELETED."""
        return self._import_list_response(
            db, self.persistence.list_all_imports(db, limit)
        )

    def delete_import(
        self, db: Session, import_id: str, account: Account | None = None
    ) -> None:
        """Desactivación lógica: marca ``deleted_at`` (y quién) y conserva la instantánea."""
        dashboard_state = self.persistence.lock_dashboard_state(db)
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
        if import_row.status not in DEACTIVATABLE_STATUSES:
            raise ApplicationError(
                HTTPStatus.CONFLICT,
                "Solo se pueden desactivar importaciones activas, históricas o fallidas.",
            )

        self.persistence.clear_active_import(db, import_id)
        import_row.deleted_at = utcnow()
        import_row.deleted_by_user_id = account.id if account is not None else None
        db.commit()
        # Libera memoria; la visibilidad ya la garantiza la consulta con deleted_at.
        self.loader.evict(import_id)

    def restore_import(
        self, db: Session, import_id: str, account: Account
    ) -> DashboardImportRestoreResponse:
        """Deshace la desactivación lógica.

        Si su espacio (ESE, o CORHUILA de ese periodo) quedó sin importación
        activa, vuelve a ser la activa. Si después se subió otra, queda como
        histórica (no reemplaza a la más reciente). Las fallidas siguen fallidas.
        """
        dashboard_state = self.persistence.lock_dashboard_state(db)
        if dashboard_state is None:
            raise ApplicationError(
                HTTPStatus.CONFLICT,
                "No se pudo verificar la importación activa.",
            )
        import_row = db.scalar(
            select(ExcelImport).where(ExcelImport.id == import_id).with_for_update()
        )
        if import_row is None:
            raise ApplicationError(HTTPStatus.NOT_FOUND, "La importación no existe.")
        if import_row.deleted_at is None:
            raise ApplicationError(
                HTTPStatus.CONFLICT, "La importación no está desactivada."
            )

        import_row.deleted_at = None
        import_row.deleted_by_user_id = None
        import_row.restored_at = utcnow()
        import_row.restored_by_user_id = account.id

        activated = False
        if import_row.status != ImportStatus.FAILED:
            slot = active_slot(Source(import_row.source), import_row.period)
            if self.persistence.get_active_import(db, slot) is None:
                import_row.status = ImportStatus.ACTIVE
                import_row.activated_at = utcnow()
                self.persistence.set_active_import(db, slot, import_row.id)
                activated = True
            else:
                import_row.status = ImportStatus.HISTORICAL
        db.flush()
        if activated and import_row.source == Source.ESE.value:
            # Vuelve el histórico de ESE: CORHUILA recupera su cruce de programas.
            refresh_corhuila_programs(db)
        db.commit()
        self.loader.cache.clear()

        if activated:
            message = "La importación se restauró y volvió a ser la activa."
        elif import_row.status == ImportStatus.FAILED:
            message = "La importación se restauró; sigue como fallida."
        else:
            message = (
                "La importación se restauró como histórica: después se subió otra "
                "más reciente, que sigue siendo la activa."
            )
        return DashboardImportRestoreResponse(
            import_id=import_row.id,
            status=ImportStatus(import_row.status).value,
            activated=activated,
            message=message,
        )

    def _activate(self, db: Session, import_row: ExcelImport) -> None:
        """La nueva importación pasa a ACTIVE y la anterior de su espacio a HISTORICAL.

        Cada espacio es independiente: activar ESE no toca CORHUILA y viceversa.
        """
        dashboard_state = self.persistence.lock_dashboard_state(db)
        if dashboard_state is None:
            raise RuntimeError(
                "No existe el estado inicial del dashboard; "
                "aplica las migraciones Alembic."
            )
        slot = active_slot(Source(import_row.source), import_row.period)
        active_import = self.persistence.get_active_import(db, slot)
        if active_import is not None:
            active_import.status = ImportStatus.HISTORICAL
        import_row.status = ImportStatus.ACTIVE
        import_row.activated_at = utcnow()
        self.persistence.set_active_import(db, slot, import_row.id)

    def _import_list_response(
        self, db: Session, imports: list[ExcelImport]
    ) -> DashboardImportListResponse:
        return DashboardImportListResponse(
            active_import_id=self.persistence.get_active_import_id(
                db, Source.ESE.value
            ),
            active_imports=[
                mappers.active_import_response(
                    active.slot, db.get(ExcelImport, active.import_id)
                )
                for active in self.persistence.list_active_imports(db)
            ],
            imports=[
                mappers.import_list_item_response(item, self._user_names(db, imports))
                for item in imports
            ],
        )

    @staticmethod
    def _user_names(db: Session, imports: list[ExcelImport]) -> dict[int, str]:
        """Nombre de quien desactivó o restauró cada importación (auditoría)."""
        ids = {
            user_id
            for item in imports
            for user_id in (item.deleted_by_user_id, item.restored_by_user_id)
            if user_id is not None
        }
        if not ids:
            return {}
        return {
            account.id: account.full_name or account.username
            for account in db.scalars(select(Account).where(Account.id.in_(ids)))
        }

    @staticmethod
    def _mark_failed(db: Session, import_id: str, error: Exception) -> None:
        db.rollback()
        import_row = db.get(ExcelImport, import_id)
        if import_row is None:
            raise RuntimeError(
                "No se pudo recuperar el registro de importación fallido."
            ) from error
        import_row.status = ImportStatus.FAILED
        import_row.validation_summary = {
            "status": "failed",
            "error_type": type(error).__name__,
        }
        db.commit()
