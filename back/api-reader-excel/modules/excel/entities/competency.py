"""Competencias evaluadas en Saber Pro y cómo se relacionan con el Excel y la base.

Es la única fuente de verdad sobre las competencias: su clave en la API, su
encabezado en ``BD GEN``, el prefijo de sus columnas en la base de datos y los
umbrales de nivel. Los puntajes y niveles viajan como diccionarios indexados por
``Competency.key``, nunca por posición.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Competency:
    key: str
    """Clave estable en la API y en los diccionarios de puntajes: ``lectura_critica``."""
    label: str
    """Nombre para mostrar."""
    column: str
    """Prefijo de columnas ORM: ``{column}_score``, ``{column}_level``, ``{column}_average``."""
    score_header: str
    """Encabezado normalizado del puntaje en ``BD GEN``."""
    thresholds: tuple[tuple[str, float], ...]
    """(nivel, puntaje máximo inclusive), en orden ascendente."""

    @property
    def level_header(self) -> str:
        """Encabezado normalizado del nivel en ``BD GEN``."""
        return f"n: {self.score_header}"

    @property
    def score_column(self) -> str:
        return f"{self.column}_score"

    @property
    def level_column(self) -> str:
        return f"{self.column}_level"

    @property
    def average_column(self) -> str:
        return f"{self.column}_average"


COMPETENCIES: tuple[Competency, ...] = (
    Competency(
        key="lectura_critica",
        label="Lectura crítica",
        column="reading",
        score_header="lectura crítica",
        thresholds=(("1", 124), ("2", 156), ("3", 198), ("4", float("inf"))),
    ),
    Competency(
        key="comunicacion_escrita",
        label="Comunicación escrita",
        column="writing",
        score_header="comunicación escrita",
        thresholds=(("1", 114), ("2", 148), ("3", 182), ("4", float("inf"))),
    ),
    Competency(
        key="competencias_ciudadanas",
        label="Competencias ciudadanas",
        column="citizenship",
        score_header="competencias ciudadanas",
        thresholds=(("1", 125), ("2", 156), ("3", 198), ("4", float("inf"))),
    ),
    Competency(
        key="razonamiento_cuantitativo",
        label="Razonamiento cuantitativo",
        column="quantitative",
        score_header="razonamiento cuantitativo",
        thresholds=(("1", 125), ("2", 153), ("3", 201), ("4", float("inf"))),
    ),
    Competency(
        key="ingles",
        label="Inglés",
        column="english",
        score_header="inglés",
        thresholds=(("A1", 120), ("A2", 164), ("B1", 195), ("B2", float("inf"))),
    ),
)


def classify_level(competency: Competency, score: float | None) -> str | None:
    """Nivel que corresponde a un puntaje según los umbrales de la competencia."""
    if score is None:
        return None
    for level, upper_bound in competency.thresholds:
        if score <= upper_bound:
            return level
    raise ValueError(f"No se pudo asignar nivel al puntaje {score}.")
