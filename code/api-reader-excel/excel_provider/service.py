from typing import Any

import fastexcel


class SheetSelectionError(ValueError):
    def __init__(self, sheet_name: str, available_sheets: list[str]) -> None:
        self.sheet_name = sheet_name
        self.available_sheets = available_sheets
        super().__init__(f"La hoja '{sheet_name}' no existe en el libro.")


def read_first_sheet(
    content: bytes, filename: str, sheet_name: str | None = None
) -> dict[str, Any]:
    workbook = fastexcel.read_excel(content)
    sheet_names = workbook.sheet_names
    if not sheet_names:
        raise ValueError("El libro de Excel no contiene hojas.")

    selected_sheet = sheet_names[0] if sheet_name is None else sheet_name
    if selected_sheet not in sheet_names:
        raise SheetSelectionError(selected_sheet, sheet_names)

    rows = workbook.load_sheet(selected_sheet).to_polars().to_dicts()
    return {
        "filename": filename,
        "available_sheets": sheet_names,
        "sheet_read": selected_sheet,
        "total_rows": len(rows),
        "data": rows,
    }
