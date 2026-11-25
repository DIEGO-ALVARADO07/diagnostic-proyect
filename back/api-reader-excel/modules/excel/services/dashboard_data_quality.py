"""Reporte de calidad de datos de BD GEN que no impide importar.

Hoy los códigos no numéricos en los puntajes (``N``, ``N/A``, ``P``…) se tratan
como "sin puntaje". Este reporte los cuenta para que alguien los revise, junto
con niveles que no cuadran con su puntaje o que no son niveles válidos.
"""

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from typing import Any

from modules.excel.entities.assessment import parse_moment, parse_period
from modules.excel.entities.competency import COMPETENCIES, classify_level
from modules.excel.services.dashboard_normalizer import (
    clean_text,
    decimal_value,
    numeric_value,
)

# Marcador que el Excel usa en los niveles cuando la prueba no aplica.
_NOT_APPLICABLE = "N/A"


def assess_data_quality(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Cuenta, por competencia:

    - ``score_codes``: textos no numéricos en el puntaje (``{"N": 254, …}``);
    - ``levels_without_numeric_score``: filas con un nivel válido (p. ej. ``4``)
      pero sin puntaje numérico;
    - ``unknown_levels``: niveles que no son un nivel válido ni un código conocido
      (p. ej. ``false``);
    - ``source_level_mismatches``: filas cuyo nivel en el Excel (Q:U) no coincide
      con el que calcula la escala común (solo competencias comparables).

    Solo incluye las competencias con algún hallazgo. Además, en
    ``period_moment`` cuenta filas sin periodo o sin momento reconocible, filas
    donde el momento de ``SIM`` no coincide con el de ``GRUPO`` y filas cuyo
    periodo no es del mismo año que ``AÑO``.
    """
    score_codes: dict[str, Counter[str]] = defaultdict(Counter)
    levels_without_score: Counter[str] = Counter()
    level_mismatches: Counter[str] = Counter()
    level_values: dict[str, Counter[str]] = defaultdict(Counter)
    period_moment: Counter[str] = Counter()

    for row in rows:
        _count_period_and_moment(row, period_moment)
        for competency in COMPETENCIES:
            raw_score = clean_text(row.get(competency.score_header))
            numeric_score = decimal_value(raw_score)
            level = clean_text(row.get(competency.level_header))
            valid_levels = set(competency.level_labels)
            if raw_score is not None and numeric_score is None:
                score_codes[competency.key][raw_score] += 1
            if numeric_score is None and level in valid_levels:
                levels_without_score[competency.key] += 1
            if level is not None and level not in valid_levels:
                level_values[competency.key][level] += 1
            if (
                competency.comparable
                and numeric_score is not None
                and level in valid_levels
                and level != classify_level(competency, float(numeric_score))
            ):
                level_mismatches[competency.key] += 1

    known_codes = {_NOT_APPLICABLE} | {
        code for codes in score_codes.values() for code in codes
    }
    unknown_levels = {
        key: {value: count for value, count in sorted(values.items())
              if value not in known_codes}
        for key, values in level_values.items()
    }
    return {
        "score_codes": {
            key: dict(sorted(codes.items())) for key, codes in score_codes.items()
        },
        "levels_without_numeric_score": dict(levels_without_score),
        "unknown_levels": {
            key: values for key, values in unknown_levels.items() if values
        },
        "source_level_mismatches": dict(level_mismatches),
        "period_moment": {
            key: period_moment[key]
            for key in (
                "rows_without_period",
                "rows_without_moment",
                "moment_group_mismatches",
                "period_year_mismatches",
            )
        },
    }


def _count_period_and_moment(row: Mapping[str, Any], counts: Counter[str]) -> None:
    simulation = clean_text(row.get("sim"))
    period = parse_period(simulation)
    simulation_moment = parse_moment(simulation)
    group_moment = parse_moment(clean_text(row.get("grupo")))
    if period is None:
        counts["rows_without_period"] += 1
    else:
        year = numeric_value(row.get("año"))
        if year is not None and int(year) != int(period[:4]):
            counts["period_year_mismatches"] += 1
    if simulation_moment is None and group_moment is None:
        counts["rows_without_moment"] += 1
    if (
        simulation_moment is not None
        and group_moment is not None
        and simulation_moment != group_moment
    ):
        counts["moment_group_mismatches"] += 1
