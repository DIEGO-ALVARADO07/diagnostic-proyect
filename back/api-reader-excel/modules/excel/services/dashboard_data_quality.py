"""Reporte de calidad de datos de BD GEN que no impide importar.

Hoy los códigos no numéricos en los puntajes (``N``, ``N/A``, ``P``…) se tratan
como "sin puntaje". Este reporte los cuenta para que alguien los revise, junto
con niveles que no cuadran con su puntaje o que no son niveles válidos.
"""

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from typing import Any

from modules.excel.entities.competency import COMPETENCIES, classify_level
from modules.excel.services.dashboard_normalizer import clean_text, decimal_value

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

    Solo incluye las competencias con algún hallazgo.
    """
    score_codes: dict[str, Counter[str]] = defaultdict(Counter)
    levels_without_score: Counter[str] = Counter()
    level_mismatches: Counter[str] = Counter()
    level_values: dict[str, Counter[str]] = defaultdict(Counter)

    for row in rows:
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
    }
