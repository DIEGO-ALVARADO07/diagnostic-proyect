"""Convierte las filas del Excel de CORHUILA en registros listos para guardar.

Mismas reglas que ESE: ``-`` o vacío = sin puntaje; ``0`` cuenta. Presentó si
tiene al menos un puntaje numérico. Comunicación escrita no se evalúa.
El programa no viene en el archivo: se toma de ESE (``program_resolution``).
"""

from collections import Counter
from dataclasses import dataclass

from modules.excel.entities.assessment import Source
from modules.excel.entities.competency import COMPARABLE_COMPETENCIES, COMPETENCIES
from modules.excel.entities.dashboard import DashboardImportRecord
from modules.excel.repositories.corhuila_workbook_repository import (
    DOCUMENT,
    EMAIL,
    FIRST_NAME,
    LAST_NAME,
    CorhuilaWorkbookRows,
)
from modules.excel.repositories.dashboard_repository import DashboardWorkbookError
from modules.excel.services.dashboard_normalizer import (
    clean_text,
    decimal_value,
    document_value,
    email_key,
    normalized_key,
)
from modules.excel.services.dashboard_processor import _json_value, _raw_text


@dataclass(frozen=True)
class CorhuilaImportData:
    filename: str
    period: str
    sheet_name: str
    records: tuple[DashboardImportRecord, ...]
    file_quality: dict[str, int]
    """Hallazgos del archivo (sin el cruce con ESE)."""


def simulation_name(period: str) -> str:
    return f"{Source.CORHUILA.value} {period}"


class CorhuilaProcessor:
    def process(
        self, filename: str, period: str, workbook: CorhuilaWorkbookRows
    ) -> CorhuilaImportData:
        records: list[DashboardImportRecord] = []
        quality: Counter[str] = Counter()
        emails: Counter[str] = Counter()
        simulation = simulation_name(period)
        year = int(period[:4])

        # Fila 1 = encabezados.
        for row_number, row in enumerate(workbook.rows, start=2):
            if not any(clean_text(value) for value in row.values()):
                continue
            scores = {
                competency.key: (
                    decimal_value(row.get(competency.key))
                    if competency.comparable
                    else None
                )
                for competency in COMPETENCIES
            }
            answered = sum(
                scores[competency.key] is not None
                for competency in COMPARABLE_COMPETENCIES
            )
            presented = answered > 0
            first_name = _raw_text(row.get(FIRST_NAME))
            last_name = _raw_text(row.get(LAST_NAME))
            name_parts = [
                clean_text(value) for value in (first_name, last_name) if clean_text(value)
            ]
            email = _raw_text(row.get(EMAIL))
            key = email_key(email)

            quality["rows"] += 1
            if not presented:
                quality["not_presented"] += 1
            elif answered < len(COMPARABLE_COMPETENCIES):
                quality["partially_presented"] += 1
            if key is None:
                quality["rows_without_email"] += 1
            else:
                emails[key] += 1
            if document_value(row.get(DOCUMENT)) is not None:
                quality["rows_with_document"] += 1

            records.append(
                DashboardImportRecord(
                    source_row_number=row_number,
                    document=document_value(row.get(DOCUMENT)),
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    email_key=key,
                    student_search_name=normalized_key(" ".join(name_parts)) or None,
                    # El archivo no trae programa: se resuelve con ESE.
                    program_name="",
                    program_normalized_key="",
                    scores=scores,
                    global_raw=None,
                    global_score=None,
                    global_calculated_score=None,
                    moment=None,
                    period=period,
                    moment_number=None,
                    test_type=None,
                    test_type_key=None,
                    semester=None,
                    semester_key=None,
                    year=year,
                    simulation=simulation,
                    simulation_key=normalized_key(simulation),
                    group=None,
                    group_key=None,
                    presented=presented,
                    presented_raw=None,
                    levels={competency.key: None for competency in COMPETENCIES},
                    campus=None,
                    training_applied=None,
                    ent=None,
                    source_payload={
                        str(column): _json_value(value) for column, value in row.items()
                    },
                )
            )

        if not records:
            raise DashboardWorkbookError(
                "El archivo de CORHUILA no contiene estudiantes."
            )
        quality["presented"] = quality["rows"] - quality["not_presented"]
        quality["duplicated_emails"] = sum(count > 1 for count in emails.values())
        keys = (
            "rows",
            "presented",
            "not_presented",
            "partially_presented",
            "rows_without_email",
            "rows_with_document",
            "duplicated_emails",
        )
        return CorhuilaImportData(
            filename=filename,
            period=period,
            sheet_name=workbook.sheet_name,
            records=tuple(records),
            file_quality={key: quality[key] for key in keys},
        )
