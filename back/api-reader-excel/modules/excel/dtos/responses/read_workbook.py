from typing import Any

from pydantic import BaseModel


class ReadWorkbookResponse(BaseModel):
    filename: str
    available_sheets: list[str]
    sheet_read: str
    total_rows: int
    data: list[dict[str, Any]]
