"""Compatibility imports for the former Excel service module."""

from modules.excel.repositories.workbook_repository import (
    SheetSelectionError,
    WorkbookRepository,
)
from modules.excel.dtos.requests.read_workbook import ReadWorkbookRequest
from modules.excel.services.excel_service import ExcelService


def read_first_sheet(
    content: bytes, filename: str, sheet_name: str | None = None
) -> dict[str, object]:
    request = ReadWorkbookRequest(
        filename=filename, content=content, sheet_name=sheet_name
    )
    workbook = WorkbookRepository().read_sheet(
        request.content, request.filename, request.sheet_name
    )
    return ExcelService.response_from_entity(workbook).model_dump()
