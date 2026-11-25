from math import isfinite
from typing import Any

from modules.excel.entities.assessment import parse_period, resolve_ese_moment
from modules.excel.entities.competency import COMPETENCIES
from modules.excel.entities.dashboard import (
    DashboardImportData,
    DashboardImportRecord,
    TdProgramasRecord,
)
from modules.excel.repositories.dashboard_repository import (
    DashboardWorkbookError,
    DashboardWorkbookSheets,
)
from modules.excel.services.dashboard_data_quality import assess_data_quality
from modules.excel.services.dashboard_normalizer import (
    canonical_semester,
    clean_text,
    decimal_value,
    document_value,
    normalized_key,
    numeric_value,
)
from modules.excel.services.program_catalog import choose_program_names

# Columnas de TD PROGRAMAS después de PROGRAMA: una por competencia y dos GL.
_TD_AVERAGE_COLUMNS = len(COMPETENCIES) + 2


def _raw_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, float) and not isfinite(value):
        return None
    return str(value)


def _json_value(value: Any) -> str | int | float | bool | None:
    if value is None:
        return None
    if isinstance(value, float) and not isfinite(value):
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _source_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {key: _json_value(value) for key, value in row.items()}


def _year_value(value: Any, row_number: int, sheet_name: str) -> int:
    number = numeric_value(value)
    if number is None or not number.is_integer():
        raise DashboardWorkbookError(
            f"El año de '{sheet_name}', fila {row_number}, no es válido."
        )
    return int(number)


def _presentation_value(value: Any) -> bool | None:
    key = normalized_key(clean_text(value))
    if key == "si":
        return True
    if key == "no":
        return False
    return None


def _td_programas_records(
    rows: list[tuple[int, tuple[Any, ...]]],
) -> tuple[int | None, tuple[TdProgramasRecord, ...]]:
    selected_year: int | None = None
    current_simulation: str | None = None
    records: list[TdProgramasRecord] = []

    for row_number, values in rows:
        if not values:
            continue
        first_value = clean_text(values[0])
        first_key = normalized_key(first_value)
        if first_key == "ano" and len(values) > 1:
            selected_year = _year_value(
                values[1], row_number, "TD PROGRAMAS"
            )
            continue
        if first_key == "programa":
            continue
        if first_key.startswith("simulacro"):
            current_simulation = _raw_text(values[0])
            continue
        if (
            current_simulation is None
            or first_value is None
            or len(values) < 1 + _TD_AVERAGE_COLUMNS
        ):
            continue

        program_name = _raw_text(values[0])
        if program_name is None:
            continue
        records.append(
            TdProgramasRecord(
                source_row_number=row_number,
                selected_year=selected_year,
                simulation=current_simulation,
                simulation_key=normalized_key(current_simulation),
                program_name=program_name,
                program_normalized_key=normalized_key(program_name),
                competency_averages={
                    competency.key: decimal_value(value)
                    for competency, value in zip(
                        COMPETENCIES, values[1 : 1 + len(COMPETENCIES)]
                    )
                },
                global_average=decimal_value(values[1 + len(COMPETENCIES)]),
                competency_mean=decimal_value(values[2 + len(COMPETENCIES)]),
                source_payload={
                    f"column_{index + 2}": _json_value(value)
                    for index, value in enumerate(values[: 1 + _TD_AVERAGE_COLUMNS])
                },
            )
        )

    if selected_year is None:
        raise DashboardWorkbookError(
            "No se encontró el año seleccionado de 'TD PROGRAMAS'."
        )
    return selected_year, tuple(records)


class DashboardProcessor:
    def process(
        self,
        filename: str,
        workbook: DashboardWorkbookSheets,
    ) -> DashboardImportData:
        records: list[DashboardImportRecord] = []
        data_rows: list[dict[str, Any]] = []
        for row_number, row in enumerate(workbook.bd_gen_rows, start=2):
            if not any(clean_text(value) for value in row.values()):
                continue
            data_rows.append(row)

            program_name = _raw_text(row.get("programa"))
            simulation = _raw_text(row.get("sim"))
            if (
                program_name is None
                or clean_text(program_name) is None
                or simulation is None
                or clean_text(simulation) is None
            ):
                raise DashboardWorkbookError(
                    "'BD GEN' requiere Programa y SIM en "
                    f"la fila {row_number}."
                )

            first_name = _raw_text(row.get("nombre"))
            last_name = _raw_text(row.get("apellido(s)"))
            name_parts = [
                clean_text(value)
                for value in (first_name, last_name)
                if clean_text(value)
            ]
            search_name = normalized_key(" ".join(name_parts)) or None
            scores = {
                competency.key: decimal_value(row.get(competency.score_header))
                for competency in COMPETENCIES
            }
            raw_global = _raw_text(row.get("global"))
            applies_raw = _raw_text(row.get("aplica simulacro"))
            semester = _raw_text(row.get("semestre"))
            assessment_type = _raw_text(row.get("tipo"))
            group = _raw_text(row.get("grupo"))

            records.append(
                DashboardImportRecord(
                    source_row_number=row_number,
                    document=document_value(row.get("usuario")),
                    first_name=first_name,
                    last_name=last_name,
                    email=_raw_text(row.get("dirección de correo")),
                    student_search_name=search_name,
                    program_name=program_name,
                    program_normalized_key=normalized_key(program_name),
                    scores=scores,
                    global_raw=raw_global,
                    global_score=decimal_value(row.get("global")),
                    global_calculated_score=(
                        # Regla del Excel institucional: puntaje vacío cuenta como 0.
                        sum(
                            (score or 0 for score in scores.values()),
                            start=0,
                        )
                        / len(COMPETENCIES)
                    ),
                    moment=_raw_text(row.get("momento")),
                    period=parse_period(simulation),
                    moment_number=resolve_ese_moment(simulation, group),
                    test_type=assessment_type,
                    test_type_key=(
                        normalized_key(assessment_type)
                        if assessment_type is not None
                        else None
                    ),
                    semester=semester,
                    # "4" y "SEMESTRE 4" son el mismo semestre; se guarda el texto original.
                    semester_key=(
                        normalized_key(canonical_semester(semester))
                        if semester is not None
                        else None
                    ),
                    year=_year_value(row.get("año"), row_number, "BD GEN"),
                    simulation=simulation,
                    simulation_key=normalized_key(simulation),
                    group=group,
                    group_key=normalized_key(group) if group is not None else None,
                    presented=_presentation_value(row.get("aplica simulacro")),
                    presented_raw=applies_raw,
                    levels={
                        competency.key: _raw_text(row.get(competency.level_header))
                        for competency in COMPETENCIES
                    },
                    campus=_raw_text(row.get("sede")),
                    training_applied=_raw_text(
                        row.get("aplico entrenamiento")
                    ),
                    ent=_raw_text(row.get("ent")),
                    source_payload=_source_payload(row),
                )
            )

        if not records:
            raise DashboardWorkbookError(
                "'BD GEN' no contiene registros históricos válidos."
            )

        selected_year, td_records = _td_programas_records(
            workbook.td_programas_rows
        )
        return DashboardImportData(
            filename=filename,
            records=tuple(records),
            td_programas_year=selected_year,
            td_programas_records=td_records,
            program_names=choose_program_names(
                (record.program_name for record in records),
                (record.program_name for record in td_records),
            ),
            data_quality=assess_data_quality(data_rows),
        )
