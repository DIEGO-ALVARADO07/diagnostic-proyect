import logging
from time import perf_counter
from typing import Any

import fastexcel

from modules.excel.entities.workbook import WorkbookRead

logger = logging.getLogger(__name__)


class SheetSelectionError(ValueError):
    def __init__(self, sheet_name: str, available_sheets: list[str]) -> None:
        self.sheet_name = sheet_name
        self.available_sheets = available_sheets
        super().__init__(f"La hoja '{sheet_name}' no existe en el libro.")


class WorkbookRepository:
    def read_sheet(
        self, content: bytes, filename: str, sheet_name: str | None
    ) -> WorkbookRead:
        started = perf_counter()
        workbook = fastexcel.read_excel(content)
        logger.info(
            "Excel workbook opened: bytes=%d elapsed_seconds=%.3f",
            len(content),
            perf_counter() - started,
        )
        sheet_names = workbook.sheet_names
        if not sheet_names:
            raise ValueError("El libro de Excel no contiene hojas.")

        selected_sheet = sheet_names[0] if sheet_name is None else sheet_name
        if selected_sheet not in sheet_names:
            raise SheetSelectionError(selected_sheet, sheet_names)

        started = perf_counter()
        frame = workbook.load_sheet(selected_sheet).to_polars()
        logger.info(
            "Excel sheet converted: rows=%d columns=%d elapsed_seconds=%.3f",
            frame.height,
            frame.width,
            perf_counter() - started,
        )

        started = perf_counter()
        rows: list[dict[str, Any]] = frame.to_dicts()
        logger.info(
            "Excel rows materialized: rows=%d elapsed_seconds=%.3f",
            len(rows),
            perf_counter() - started,
        )
        return WorkbookRead(
            filename=filename,
            available_sheets=sheet_names,
            sheet_read=selected_sheet,
            data=rows,
        )
