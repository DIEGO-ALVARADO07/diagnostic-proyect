import math
import unicodedata
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from typing import Any


def clean_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    text = " ".join(str(value).strip().split())
    return text or None


@lru_cache(maxsize=8192)
def normalized_key(value: str | None) -> str:
    """Clave de comparación sin mayúsculas, tildes ni espacios repetidos.

    Es una función pura y se llama por cada registro en cada filtro y en las
    opciones de filtros, casi siempre con pocos valores distintos (simulacros,
    grupos, semestres, tipos), por eso se memoriza.
    """
    if value is None:
        return ""
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    without_accents = "".join(
        character
        for character in decomposed
        if not unicodedata.combining(character)
    )
    return " ".join(without_accents.split())


def numeric_value(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    text = clean_text(value)
    if text is None:
        return None
    if "," in text and "." not in text:
        text = text.replace(",", ".")
    try:
        number = float(text)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def decimal_value(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    text = clean_text(value)
    if text is None:
        return None
    if "," in text and "." not in text:
        text = text.replace(",", ".")
    try:
        number = Decimal(text)
    except InvalidOperation:
        return None
    return number if number.is_finite() else None


def document_value(value: Any) -> str | None:
    text = clean_text(value)
    if text is None:
        return None
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return text


def email_key(value: Any) -> str | None:
    """Identidad del estudiante: correo en minúsculas y sin espacios.

    ``" Ana.Perez@Corhuila.edu.co "`` → ``"ana.perez@corhuila.edu.co"``. Devuelve
    ``None`` si el valor no parece un correo (sin ``@``).
    """
    text = clean_text(value)
    if text is None:
        return None
    key = "".join(text.split()).casefold()
    return key if "@" in key else None


def accent_count(value: str) -> int:
    """Cantidad de letras con tilde o diacrítico (``Í``, ``ñ``…)."""
    return sum(
        1
        for character in unicodedata.normalize("NFKD", value)
        if unicodedata.combining(character)
    )


def canonical_semester(value: Any) -> str | None:
    """Unifica la escritura del semestre: ``"4"`` y ``4.0`` pasan a ``"SEMESTRE 4"``.

    Cualquier otro texto se devuelve limpio y sin cambios (``"SEMESTRE 4"``).
    """
    text = clean_text(value)
    if text is None:
        return None
    number = numeric_value(text)
    if number is not None and number.is_integer() and number > 0:
        return f"SEMESTRE {int(number)}"
    return text
