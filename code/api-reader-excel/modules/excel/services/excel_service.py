from pathlib import Path
from http import HTTPStatus

import fastexcel

from core.exceptions import ApplicationError
from modules.excel.entities.workbook import WorkbookRead
from modules.excel.dtos.requests.read_workbook import ReadWorkbookRequest
from modules.excel.dtos.responses.read_workbook import ReadWorkbookResponse
from modules.excel.repositories.workbook_repository import (
    SheetSelectionError,
    WorkbookRepository,
)
from modules.security.entities import Account
from modules.security.entities.role import Role

MAX_UPLOAD_BYTES = 30 * 1024 * 1024
ALLOWED_EXTENSIONS = {".xlsx", ".xlsm", ".xls", ".ods"}


class ExcelService:
    def __init__(self, repository: WorkbookRepository | None = None) -> None:
        self.repository = repository or WorkbookRepository()

    def validate_upload(self, filename: str, account: Account) -> str:
        if Role(account.role) not in {Role.INSTRUCTOR, Role.SUPERADMIN}:
            raise ApplicationError(
                HTTPStatus.FORBIDDEN,
                "Solo instructor y superadmin pueden subir archivos Excel.",
            )

        safe_filename = Path(filename).name
        if Path(safe_filename).suffix.casefold() not in ALLOWED_EXTENSIONS:
            raise ApplicationError(
                HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
                "Formato no válido. Usa .xlsx, .xlsm, .xls o .ods.",
            )
        return safe_filename

    def read(
        self,
        request: ReadWorkbookRequest,
        account: Account,
    ) -> ReadWorkbookResponse:
        safe_filename = self.validate_upload(request.filename, account)
        if len(request.content) > MAX_UPLOAD_BYTES:
            raise ApplicationError(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                "El archivo supera el límite de 30 MB.",
            )

        try:
            workbook = self.repository.read_sheet(
                request.content, safe_filename, request.sheet_name
            )
        except SheetSelectionError as error:
            raise ApplicationError(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                {
                    "message": str(error),
                    "available_sheets": error.available_sheets,
                },
            ) from None
        except (fastexcel.FastExcelError, ValueError):
            raise ApplicationError(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                "No se pudo leer el libro Excel o no contiene hojas válidas.",
            ) from None

        return self.response_from_entity(workbook)

    @staticmethod
    def response_from_entity(workbook: WorkbookRead) -> ReadWorkbookResponse:
        return ReadWorkbookResponse(
            filename=workbook.filename,
            available_sheets=workbook.available_sheets,
            sheet_read=workbook.sheet_read,
            total_rows=workbook.total_rows,
            data=workbook.data,
        )
