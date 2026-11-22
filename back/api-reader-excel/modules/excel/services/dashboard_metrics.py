from collections.abc import Sequence
from statistics import fmean, pstdev

from modules.excel.entities.competency import COMPETENCIES, classify_level
from modules.excel.entities.dashboard import DashboardRecord


def calculate_metrics(records: Sequence[DashboardRecord]) -> dict[str, object]:
    presented = [record for record in records if record.presented]
    competency_results: dict[str, dict[str, object]] = {}
    competency_averages: list[float] = []

    for competency in COMPETENCIES:
        values = [
            score
            for record in presented
            if (score := record.scores[competency.key]) is not None
        ]
        levels = [classify_level(competency, score) for score in values]
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
