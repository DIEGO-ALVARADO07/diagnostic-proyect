from dataclasses import dataclass
from statistics import fmean, pstdev

from modules.excel.entities.dashboard import DashboardRecord


@dataclass(frozen=True)
class Competency:
    key: str
    label: str
    thresholds: tuple[tuple[str, float], ...]


COMPETENCIES = (
    Competency(
        "lectura_critica",
        "Lectura crítica",
        (("1", 124), ("2", 156), ("3", 198), ("4", float("inf"))),
    ),
    Competency(
        "comunicacion_escrita",
        "Comunicación escrita",
        (("1", 114), ("2", 148), ("3", 182), ("4", float("inf"))),
    ),
    Competency(
        "competencias_ciudadanas",
        "Competencias ciudadanas",
        (("1", 125), ("2", 156), ("3", 198), ("4", float("inf"))),
    ),
    Competency(
        "razonamiento_cuantitativo",
        "Razonamiento cuantitativo",
        (("1", 125), ("2", 153), ("3", 201), ("4", float("inf"))),
    ),
    Competency(
        "ingles",
        "Inglés",
        (("A1", 120), ("A2", 164), ("B1", 195), ("B2", float("inf"))),
    ),
)


def classify_level(
    competency_index: int, score: float | None
) -> str | None:
    if score is None:
        return None
    for level, upper_bound in COMPETENCIES[competency_index].thresholds:
        if score <= upper_bound:
            return level
    raise ValueError(f"No se pudo asignar nivel al puntaje {score}.")


def calculate_metrics(records: list[DashboardRecord]) -> dict[str, object]:
    presented = [record for record in records if record.presented]
    competency_results: dict[str, dict[str, object]] = {}
    competency_averages: list[float] = []

    for index, competency in enumerate(COMPETENCIES):
        values = [
            record.scores[index]
            for record in presented
            if record.scores[index] is not None
        ]
        levels = [
            classify_level(index, score)
            for score in values
        ]
        distribution_counts = {
            level: levels.count(level)
            for level, _ in competency.thresholds
        }
        average = fmean(values) if values else None
        if average is not None:
            competency_averages.append(average)
        competency_results[competency.key] = {
            "label": competency.label,
            "average": average,
            "count": len(values),
            "standard_deviation": pstdev(values) if len(values) >= 2 else None,
            "distribution_count": len(values),
            "level_distribution": {
                level: count * 100 / len(values)
                for level, count in distribution_counts.items()
            }
            if values
            else {},
        }

    global_values = [
        record.global_score
        for record in presented
        if record.global_score is not None
    ]
    return {
        "presentations": len(presented),
        "unique_students": len(
            {record.document for record in presented if record.document}
        ),
        "not_presented_records": len(records) - len(presented),
        "average_global": fmean(global_values) if global_values else None,
        "global_standard_deviation": (
            pstdev(global_values) if len(global_values) >= 2 else None
        ),
        "simple_competence_average": (
            fmean(competency_averages) if competency_averages else None
        ),
        "competencies": competency_results,
    }
