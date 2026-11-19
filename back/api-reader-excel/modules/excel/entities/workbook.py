from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class WorkbookRead:
    filename: str
    available_sheets: list[str]
    sheet_read: str
    data: list[dict[str, Any]]

    @property
    def total_rows(self) -> int:
        return len(self.data)
