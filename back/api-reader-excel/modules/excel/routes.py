from collections.abc import Awaitable, Callable
import logging
from time import perf_counter

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from fastapi.routing import APIRoute
from starlette.requests import Request
from starlette.responses import Response

from modules.excel.dtos.requests.dashboard import DashboardFilterQuery
from modules.excel.dtos.requests.read_workbook import ReadWorkbookRequest
from modules.excel.dtos.responses.dashboard import (
    DashboardImportListResponse,
    DashboardImportResponse,
    DashboardOverviewResponse,
    DashboardProgramResponse,
    DashboardStudentResponse,
)
from modules.excel.dtos.responses.read_workbook import ReadWorkbookResponse
from modules.excel.services.excel_service import ExcelService, MAX_UPLOAD_BYTES
from modules.excel.services.dashboard_service import DashboardService, MAX_PAGE_SIZE
from modules.security.dependencies import CurrentAccount, require_roles
from modules.security.dependencies import DbSession
from modules.security.entities.role import Role

logger = logging.getLogger(__name__)


class TimedExcelRoute(APIRoute):
    def get_route_handler(
        self,
    ) -> Callable[[Request], Awaitable[Response]]:
        original_handler = super().get_route_handler()

        async def timed_handler(request: Request) -> Response:
            started = perf_counter()
            response = await original_handler(request)
            logger.info(
                "Excel HTTP request completed: status=%d response_bytes=%s elapsed_seconds=%.3f",
                response.status_code,
                response.headers.get("content-length", "unknown"),
                perf_counter() - started,
            )
            return response

        return timed_handler


router = APIRouter(
    prefix="/excel", tags=["excel"], route_class=TimedExcelRoute
)
dashboard_service = DashboardService()


@router.post(
    "/read",
    status_code=status.HTTP_200_OK,
    response_model=ReadWorkbookResponse,
)
async def upload_and_read_excel(
    account: CurrentAccount,
    file: UploadFile = File(...),
    sheet_name: str | None = Form(default=None),
) -> ReadWorkbookResponse:
    service = ExcelService()
    filename = file.filename or ""
    service.validate_upload(filename, account)
    upload_started = perf_counter()
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    logger.info(
        "Excel upload buffered: bytes=%d elapsed_seconds=%.3f",
        len(content),
        perf_counter() - upload_started,
    )
    request = ReadWorkbookRequest(
        filename=filename,
        content=content,
        sheet_name=sheet_name,
    )
    return await run_in_threadpool(
        service.read,
        request,
        account,
    )


@router.post(
    "/dashboard/import",
    status_code=status.HTTP_200_OK,
    response_model=DashboardImportResponse,
)
async def upload_dashboard_workbook(
    account: CurrentAccount,
    db: DbSession,
    file: UploadFile = File(...),
) -> DashboardImportResponse:
    filename = file.filename or ""
    dashboard_service.validate_upload(filename, account)
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    request = ReadWorkbookRequest(filename=filename, content=content)
    return await run_in_threadpool(
        dashboard_service.import_workbook,
        request,
        account,
        db,
    )


def _dashboard_filters(
    year: int | None,
    simulation: str | None,
    group: str | None,
    semester: str | None,
    test_type: str | None,
    presented: bool | None,
) -> DashboardFilterQuery:
    return DashboardFilterQuery(
        year=year,
        simulation=simulation,
        group=group,
        semester=semester,
        test_type=test_type,
        presented=presented,
    )


@router.get(
    "/dashboard/active",
    response_model=DashboardImportResponse,
    dependencies=[Depends(require_roles(Role.INSTRUCTOR, Role.SUPERADMIN))],
)
async def get_active_dashboard(db: DbSession) -> DashboardImportResponse:
    return await run_in_threadpool(dashboard_service.get_active_import, db)


@router.get(
    "/dashboard/imports",
    response_model=DashboardImportListResponse,
    dependencies=[Depends(require_roles(Role.SUPERADMIN))],
)
async def list_dashboard_imports(
    db: DbSession,
    limit: int = Query(default=20, ge=1, le=100),
) -> DashboardImportListResponse:
    return await run_in_threadpool(dashboard_service.list_imports, db, limit)


@router.get(
    "/dashboard/admin/imports",
    response_model=DashboardImportListResponse,
    dependencies=[Depends(require_roles(Role.SUPERADMIN))],
)
async def list_admin_dashboard_imports(
    db: DbSession,
    limit: int = Query(default=100, ge=1, le=100),
) -> DashboardImportListResponse:
    return await run_in_threadpool(
        dashboard_service.list_admin_imports, db, limit
    )


@router.delete(
    "/dashboard/imports/{import_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    dependencies=[Depends(require_roles(Role.SUPERADMIN))],
)
async def delete_dashboard_import(db: DbSession, import_id: str) -> Response:
    await run_in_threadpool(dashboard_service.delete_import, db, import_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/dashboard/{import_id}",
    response_model=DashboardOverviewResponse,
    dependencies=[Depends(require_roles(Role.INSTRUCTOR, Role.SUPERADMIN))],
)
async def get_dashboard_overview(
    db: DbSession,
    account: CurrentAccount,
    import_id: str,
    year: int | None = None,
    simulation: str | None = None,
    group: str | None = None,
    semester: str | None = None,
    test_type: str | None = None,
    presented: bool | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=MAX_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
) -> DashboardOverviewResponse:
    return await run_in_threadpool(
        dashboard_service.get_overview,
        db,
        import_id,
        _dashboard_filters(
            year, simulation, group, semester, test_type, presented
        ),
        page,
        page_size,
        account,
    )


@router.get(
    "/dashboard/{import_id}/programs/{program_id}",
    response_model=DashboardProgramResponse,
    dependencies=[Depends(require_roles(Role.INSTRUCTOR, Role.SUPERADMIN))],
)
async def get_dashboard_program(
    db: DbSession,
    account: CurrentAccount,
    import_id: str,
    program_id: str,
    year: int | None = None,
    simulation: str | None = None,
    group: str | None = None,
    semester: str | None = None,
    test_type: str | None = None,
    presented: bool | None = None,
    search: str | None = Query(default=None, max_length=200),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=MAX_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
) -> DashboardProgramResponse:
    return await run_in_threadpool(
        dashboard_service.get_program,
        db,
        import_id,
        program_id,
        _dashboard_filters(
            year, simulation, group, semester, test_type, presented
        ),
        search,
        page,
        page_size,
        account,
    )


@router.get(
    "/dashboard/{import_id}/students/{document}",
    response_model=DashboardStudentResponse,
    dependencies=[Depends(require_roles(Role.INSTRUCTOR, Role.SUPERADMIN))],
)
async def get_dashboard_student(
    db: DbSession,
    account: CurrentAccount,
    import_id: str,
    document: str,
) -> DashboardStudentResponse:
    return await run_in_threadpool(
        dashboard_service.get_student,
        db,
        import_id,
        document,
        account,
    )
