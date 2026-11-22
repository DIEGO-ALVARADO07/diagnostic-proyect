"""Casos de uso de escritura del dashboard: importar, listar y desactivar."""

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
)
from modules.excel.entities.academic import ExcelImport
from modules.excel.entities.import_status import (
    DEACTIVATABLE_STATUSES,
    SNAPSHOT_DATASET_MODE,
    SNAPSHOT_STATUSES,
    ImportStatus,
)
from modules.excel.repositories.dashboard_persistence_repository import (
    DashboardPersistenceRepository,
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

    def validate_upload(self, filename: str, account: Account) -> str:
        return self.excel_service.validate_upload(filename, account)

    def import_workbook(
        self,
        request: ReadWorkbookRequest,
        account: Account,
        db: Session,
    ) -> DashboardImportResponse:
        """Importa el libro como nueva instantánea activa.

        Un mismo archivo (mismo SHA-256) no se procesa dos veces: si ya está
        activo o histórico se devuelve su resumen; si falló o fue desactivado
        se rechaza.
        """
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
            sheets = self.repository.read_sheets(request.content)
            data = self.processor.process(safe_filename, sheets)
            self.persistence.persist_snapshot(db, import_row, data)
            import_row.status = ImportStatus.VALIDATED
            db.flush()
            self._activate(db, import_row)
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

        return self.queries.import_response(db, import_row)

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

    def delete_import(self, db: Session, import_id: str) -> None:
        """Desactivación lógica: marca ``deleted_at`` y conserva la instantánea."""
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

        if dashboard_state.active_import_id == import_id:
            dashboard_state.active_import_id = None
        import_row.deleted_at = utcnow()
        db.commit()
        # Libera memoria; la visibilidad ya la garantiza la consulta con deleted_at.
        self.loader.evict(import_id)

    def _activate(self, db: Session, import_row: ExcelImport) -> None:
        """La nueva importación pasa a ACTIVE y la anterior a HISTORICAL."""
        dashboard_state = self.persistence.lock_dashboard_state(db)
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
            active_import.status = ImportStatus.HISTORICAL
        import_row.status = ImportStatus.ACTIVE
        import_row.activated_at = utcnow()
        dashboard_state.active_import_id = import_row.id

    def _import_list_response(
        self, db: Session, imports: list[ExcelImport]
    ) -> DashboardImportListResponse:
        return DashboardImportListResponse(
            active_import_id=self.persistence.get_active_import_id(db),
            imports=[mappers.import_list_item_response(item) for item in imports],
        )

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
