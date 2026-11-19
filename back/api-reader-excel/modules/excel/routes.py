from collections.abc import Awaitable, Callable
import logging
from time import perf_counter

from fastapi import APIRouter, File, Form, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from fastapi.routing import APIRoute
from starlette.requests import Request
from starlette.responses import Response

from modules.excel.dtos.requests.read_workbook import ReadWorkbookRequest
from modules.excel.dtos.responses.read_workbook import ReadWorkbookResponse
from modules.excel.services.excel_service import ExcelService, MAX_UPLOAD_BYTES
from modules.security.dependencies import CurrentAccount

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
