from dataclasses import dataclass
from typing import Any

import fastexcel


class DashboardWorkbookError(ValueError):
    pass


@dataclass(frozen=True)
class DashboardWorkbookSheets:
    available_sheets: list[str]
    bd_gen_rows: list[dict[str, Any]]
    td_programas_rows: list[tuple[int, tuple[Any, ...]]]


BD_GEN_REQUIRED_HEADERS = {
    "usuario",
    "nombre",
    "apellido(s)",
    "dirección de correo",
    "lectura crítica",
    "comunicación escrita",
    "competencias ciudadanas",
    "razonamiento cuantitativo",
    "inglés",
    "global",
    "programa",
    "momento",
    "tipo",
    "semestre",
    "año",
    "sim",
    "n: lectura crítica",
    "n: comunicación escrita",
    "n: competencias ciudadanas",
    "n: razonamiento cuantitativo",
    "n: inglés",
    "sede",
    "grupo",
    "aplica simulacro",
    "aplico entrenamiento",
    "ent",
}
TD_PROGRAMAS_HEADER = (
    "programa",
    "lc",
    "ce",
    "cc",
    "rc",
    "i",
    "gl",
    "gl",
)


def _normalize_header(value: str) -> str:
    return " ".join(value.strip().casefold().split())


class DashboardWorkbookRepository:
    def read_sheets(self, content: bytes) -> DashboardWorkbookSheets:
        workbook = fastexcel.read_excel(content)
        available_sheets = workbook.sheet_names
        missing_sheets = {
            "BD GEN",
            "TD PROGRAMAS",
        }.difference(available_sheets)
        if missing_sheets:
            missing = ", ".join(sorted(missing_sheets))
            raise DashboardWorkbookError(
                f"Faltan las hojas requeridas: {missing}."
            )

        bd_gen = workbook.load_sheet("BD GEN").to_polars()
        td_programas = workbook.load_sheet("TD PROGRAMAS").to_polars()

        normalized_headers = [_normalize_header(str(name)) for name in bd_gen.columns]
        if len(normalized_headers) != len(set(normalized_headers)):
            raise DashboardWorkbookError(
                "La hoja 'BD GEN' contiene encabezados duplicados."
            )
        missing_headers = BD_GEN_REQUIRED_HEADERS.difference(normalized_headers)
        if missing_headers:
            missing = ", ".join(sorted(missing_headers))
            raise DashboardWorkbookError(
                f"Faltan columnas requeridas en 'BD GEN': {missing}."
            )

        header_row_found = any(
            tuple(
                _normalize_header(str(value or ""))
                for value in row
            )
            == TD_PROGRAMAS_HEADER
            for row in td_programas.iter_rows()
        )
        if not header_row_found:
            raise DashboardWorkbookError(
                "No se encontró el encabezado esperado de 'TD PROGRAMAS' "
                "(PROGRAMA, LC, CE, CC, RC, I, GL, GL)."
            )

        header_names = [
            _normalize_header(str(name)) for name in bd_gen.columns
        ]
        bd_gen_rows = [
            dict(zip(header_names, row.values()))
            for row in bd_gen.to_dicts()
        ]
        td_programas_rows = [
            (row_number, tuple(row.values()))
            for row_number, row in enumerate(td_programas.to_dicts(), start=2)
        ]
        return DashboardWorkbookSheets(
            available_sheets=available_sheets,
            bd_gen_rows=bd_gen_rows,
            td_programas_rows=td_programas_rows,
        )
