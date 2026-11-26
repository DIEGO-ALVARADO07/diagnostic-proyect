"""Lectura del Excel de la prueba institucional de CORHUILA.

Es una exportación de calificaciones de Moodle: una hoja ``Calificaciones`` con
``Nombre``, ``Apellido(s)``, ``Número de ID`` (casi siempre vacío por ahora),
``Dirección de correo`` y una columna ``Cuestionario:<competencia> (Real)`` por
competencia. No trae programa, semestre ni periodo.
"""

import re
from dataclasses import dataclass
from typing import Any

import fastexcel

from modules.excel.entities.competency import COMPARABLE_COMPETENCIES
from modules.excel.repositories.dashboard_repository import DashboardWorkbookError
from modules.excel.services.dashboard_normalizer import normalized_key

CORHUILA_SHEET = "Calificaciones"

# "Cuestionario:Lectura crítica (Real)" → "lectura critica"
_QUIZ_HEADER = re.compile(r"^cuestionario\s*:\s*(.+?)\s*(\(real\))?$")

FIRST_NAME = "nombre"
LAST_NAME = "apellido(s)"
DOCUMENT = "numero de id"
EMAIL = "direccion de correo"


@dataclass(frozen=True)
class CorhuilaWorkbookRows:
    sheet_name: str
    rows: list[dict[str, Any]]
    """Filas con claves normalizadas: ``nombre``, ``apellido(s)``,
    ``numero de id``, ``direccion de correo`` y ``Competency.key`` para los
    puntajes."""


def _header_key(header: str) -> str:
    """Encabezado normalizado; los de cuestionario pasan a ``Competency.key``."""
    key = normalized_key(str(header))
    match = _QUIZ_HEADER.match(key)
    if match is None:
        return key
    quiz = match.group(1)
    for competency in COMPARABLE_COMPETENCIES:
        if quiz == normalized_key(competency.label):
            return competency.key
    return key


def _required_headers() -> set[str]:
    return {
        FIRST_NAME,
        LAST_NAME,
        EMAIL,
        *(competency.key for competency in COMPARABLE_COMPETENCIES),
    }


class CorhuilaWorkbookRepository:
    def read_rows(self, content: bytes) -> CorhuilaWorkbookRows:
        """Lee ``Calificaciones``; si no existe, la primera hoja con los encabezados."""
        workbook = fastexcel.read_excel(content)
        names = workbook.sheet_names
        ordered = [CORHUILA_SHEET] if CORHUILA_SHEET in names else []
        ordered += [name for name in names if name != CORHUILA_SHEET]

        required = _required_headers()
        missing_in_preferred: set[str] | None = None
        for name in ordered:
            frame = workbook.load_sheet(name).to_polars()
            keys = {column: _header_key(column) for column in frame.columns}
            missing = required - set(keys.values())
            if not missing:
                rows = [
                    {keys[column]: value for column, value in row.items()}
                    for row in frame.to_dicts()
                ]
                return CorhuilaWorkbookRows(sheet_name=name, rows=rows)
            if missing_in_preferred is None:
                missing_in_preferred = missing

        detail = (
            ", ".join(sorted(missing_in_preferred))
            if missing_in_preferred
            else "todas"
        )
        raise DashboardWorkbookError(
            "El libro no tiene la hoja de CORHUILA "
            f"('{CORHUILA_SHEET}') con sus encabezados. Faltan: {detail}."
        )
