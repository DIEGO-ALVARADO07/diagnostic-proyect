"""Auditoría: compara los promedios de TD PROGRAMAS con los calculados desde BD GEN."""

from modules.excel.dtos.responses.dashboard import (
    DashboardAuditDifferenceResponse,
    DashboardSourceAuditResponse,
)
from modules.excel.entities.dashboard import DashboardDataset
from modules.excel.services.dashboard_mappers import metrics_response
from modules.excel.services.dashboard_normalizer import normalized_key

# Diferencia mínima para considerar que dos promedios no coinciden.
DIFFERENCE_TOLERANCE = 0.0001
# Máximo de diferencias detalladas en la respuesta (el total se cuenta igual).
MAX_REPORTED_DIFFERENCES = 100


def build_source_audit(dataset: DashboardDataset) -> DashboardSourceAuditResponse:
    years = sorted({record.year for record in dataset.records})
    compared_rows = 0
    compared_metrics = 0
    differences: list[DashboardAuditDifferenceResponse] = []
    difference_count = 0
    if dataset.td_programs_year is not None:
        program_id_by_name = {
            name: program_id
            for program_id, name in dataset.program_names.items()
        }
        for (simulation_key, program_key), td_values in (
            dataset.td_programs_summary.items()
        ):
            program_id = program_id_by_name.get(program_key)
            if program_id is None:
                continue
            matched = [
                record
                for record in dataset.records_by_program[program_id]
                if record.year == dataset.td_programs_year
                and normalized_key(record.simulation) == simulation_key
            ]
            if not matched:
                continue
            calculated = metrics_response(matched)
            calculated_values: dict[str, float | None] = {
                key: item.average
                for key, item in calculated.competencies.items()
            }
            calculated_values.update(
                {
                    "average_global": calculated.average_global,
                    "simple_competence_average": (
                        calculated.simple_competence_average
                    ),
                }
            )
            compared_rows += 1
            for metric, td_value in td_values.items():
                calculated_value = calculated_values[metric]
                if td_value is None or calculated_value is None:
                    continue
                compared_metrics += 1
                difference = abs(td_value - calculated_value)
                if difference > DIFFERENCE_TOLERANCE:
                    difference_count += 1
                    if len(differences) < MAX_REPORTED_DIFFERENCES:
                        differences.append(
                            DashboardAuditDifferenceResponse(
                                simulation=matched[0].simulation,
                                program=dataset.program_names[program_id],
                                metric=metric,
                                td_programas_value=td_value,
                                bd_gen_value=calculated_value,
                                absolute_difference=difference,
                            )
                        )
    return DashboardSourceAuditResponse(
        years_in_bd_gen=years,
        td_programas_visible_year=dataset.td_programs_year,
        records_without_document=dataset.records_without_document,
        compared_program_rows=compared_rows,
        compared_metrics=compared_metrics,
        difference_count=difference_count,
        differences=differences,
    )
