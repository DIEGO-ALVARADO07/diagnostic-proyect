"""Punto de entrada del dashboard: compone los servicios y comparte la caché.

``DashboardService`` mantiene la interfaz que usan las rutas y las pruebas y
delega cada caso de uso:

- ``DashboardImportService``: importar, listar y desactivar importaciones.
- ``DashboardQueryService``: overview, programa, estudiante e importación activa.

Ambos comparten el mismo ``DashboardDatasetLoader`` (y su caché), de modo que una
importación recién cargada queda disponible para las consultas y una
desactivación libera su entrada.
"""

from sqlalchemy.orm import Session

from modules.excel.dtos.requests.dashboard import DashboardFilterQuery
from modules.excel.dtos.requests.read_workbook import ReadWorkbookRequest
from modules.excel.dtos.responses.dashboard import (
    DashboardImportListResponse,
    DashboardImportResponse,
    DashboardOverviewResponse,
    DashboardProgramResponse,
    DashboardStudentResponse,
)
from modules.excel.repositories.dashboard_persistence_repository import (
    DashboardPersistenceRepository,
)
from modules.excel.repositories.dashboard_repository import (
    DashboardWorkbookRepository,
)
from modules.excel.services.dashboard_cache import DashboardDatasetCache
from modules.excel.services.dashboard_dataset_loader import DashboardDatasetLoader
from modules.excel.services.dashboard_import_service import DashboardImportService
from modules.excel.services.dashboard_processor import DashboardProcessor
from modules.excel.services.dashboard_query_service import (
    MAX_PAGE_SIZE,
    DashboardQueryService,
)
from modules.excel.services.excel_service import ExcelService
from modules.security.entities import Account

__all__ = ["MAX_PAGE_SIZE", "DashboardService"]


class DashboardService:
    def __init__(
        self,
        repository: DashboardWorkbookRepository | None = None,
        processor: DashboardProcessor | None = None,
        persistence: DashboardPersistenceRepository | None = None,
        excel_service: ExcelService | None = None,
        dataset_cache: DashboardDatasetCache | None = None,
    ) -> None:
        persistence = persistence or DashboardPersistenceRepository()
        self.loader = DashboardDatasetLoader(dataset_cache)
        self.queries = DashboardQueryService(persistence, self.loader)
        self.imports = DashboardImportService(
            repository=repository or DashboardWorkbookRepository(),
            processor=processor or DashboardProcessor(),
            persistence=persistence,
            excel_service=excel_service or ExcelService(),
            loader=self.loader,
            queries=self.queries,
        )

    @property
    def dataset_cache(self) -> DashboardDatasetCache:
        return self.loader.cache

    # --- Escritura ------------------------------------------------------------

    def validate_upload(self, filename: str, account: Account) -> str:
        return self.imports.validate_upload(filename, account)

    def import_workbook(
        self, request: ReadWorkbookRequest, account: Account, db: Session
    ) -> DashboardImportResponse:
        return self.imports.import_workbook(request, account, db)

    def list_imports(self, db: Session, limit: int) -> DashboardImportListResponse:
        return self.imports.list_imports(db, limit)

    def list_admin_imports(
        self, db: Session, limit: int
    ) -> DashboardImportListResponse:
        return self.imports.list_admin_imports(db, limit)

    def delete_import(self, db: Session, import_id: str) -> None:
        self.imports.delete_import(db, import_id)

    # --- Consulta -------------------------------------------------------------

    def get_active_import(
        self, db: Session, slot: str = "ESE"
    ) -> DashboardImportResponse:
        return self.queries.get_active_import(db, slot)

    def get_overview(
        self,
        db: Session,
        import_id: str,
        filters: DashboardFilterQuery,
        page: int,
        page_size: int,
        account: Account | None = None,
    ) -> DashboardOverviewResponse:
        return self.queries.get_overview(
            db, import_id, filters, page, page_size, account
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
        return self.queries.get_program(
            db, import_id, program_id, filters, search, page, page_size, account
        )

    def get_student(
        self,
        db: Session,
        import_id: str,
        document: str,
        account: Account | None = None,
    ) -> DashboardStudentResponse:
        return self.queries.get_student(db, import_id, document, account)
