"""Regla de identidad y nombre de los programas académicos.

Dos nombres son el mismo programa si coinciden sin tener en cuenta mayúsculas,
tildes ni espacios (``normalized_key``). Por ejemplo, ``INGENIERIA DE SISTEMAS``
e ``INGENIERÍA DE SISTEMAS`` son un único programa.
"""

from collections import Counter, defaultdict
from collections.abc import Iterable

from modules.excel.services.dashboard_normalizer import (
    accent_count,
    clean_text,
    normalized_key,
)


def choose_program_names(
    bd_gen_names: Iterable[str],
    td_programas_names: Iterable[str] = (),
) -> dict[str, str]:
    """Nombre a mostrar por clave normalizada.

    Prioridad: 1) el nombre que usa TD PROGRAMAS (nombre institucional);
    2) la variante con más tildes (escritura correcta en español);
    3) la variante más frecuente; 4) orden alfabético, para que sea determinista.
    """
    def best(variants: Counter[str]) -> str:
        return min(
            variants,
            key=lambda name: (-accent_count(name), -variants[name], name),
        )

    td_variants: dict[str, Counter[str]] = defaultdict(Counter)
    for name in td_programas_names:
        text = clean_text(name)
        if text is not None:
            td_variants[normalized_key(text)][text] += 1

    bd_variants: dict[str, Counter[str]] = defaultdict(Counter)
    for name in bd_gen_names:
        text = clean_text(name)
        if text is not None:
            bd_variants[normalized_key(text)][text] += 1

    return {
        key: best(td_variants[key]) if key in td_variants else best(variants)
        for key, variants in bd_variants.items()
    }
