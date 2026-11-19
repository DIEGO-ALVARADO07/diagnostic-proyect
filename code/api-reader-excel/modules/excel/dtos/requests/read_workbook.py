from pydantic import BaseModel


class ReadWorkbookRequest(BaseModel):
    filename: str
    content: bytes
    sheet_name: str | None = None
