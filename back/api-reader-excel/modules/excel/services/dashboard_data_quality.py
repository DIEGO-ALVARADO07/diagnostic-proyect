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
    document_value,
    email_key,
    normalized_key,
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
    periodo no es del mismo año que ``AÑO``. En ``identity`` cuenta filas sin
    correo, correos con más de un documento y documentos con más de un correo
    y nombres completos con más de un documento (la identidad es el documento;
    los correos son alias y el nombre es respaldo para CORHUILA).
    """
    score_codes: dict[str, Counter[str]] = defaultdict(Counter)
    levels_without_score: Counter[str] = Counter()
    level_mismatches: Counter[str] = Counter()
    level_values: dict[str, Counter[str]] = defaultdict(Counter)
    period_moment: Counter[str] = Counter()
    rows_without_email = 0
    documents_by_email: dict[str, set[str]] = defaultdict(set)
    emails_by_document: dict[str, set[str]] = defaultdict(set)
    documents_by_name: dict[str, set[str]] = defaultdict(set)

    for row in rows:
        _count_period_and_moment(row, period_moment)
        email = email_key(row.get("dirección de correo"))
        document = document_value(row.get("usuario"))
        name = normalized_key(
            " ".join(
                part
                for part in (
                    clean_text(row.get("nombre")),
                    clean_text(row.get("apellido(s)")),
                )
                if part
            )
        )
        if name and document is not None:
            documents_by_name[name].add(document)
        if email is None:
            rows_without_email += 1
        elif document is not None:
            documents_by_email[email].add(document)
            emails_by_document[document].add(email)
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
        "identity": {
            "rows_without_email": rows_without_email,
            "emails_with_multiple_documents": sum(
                len(documents) > 1 for documents in documents_by_email.values()
            ),
            "documents_with_multiple_emails": sum(
                len(emails) > 1 for emails in emails_by_document.values()
            ),
            "names_with_multiple_documents": sum(
                len(documents) > 1 for documents in documents_by_name.values()
            ),
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
