"""Competencias evaluadas en Saber Pro y cómo se relacionan con el Excel y la base.

Es la única fuente de verdad sobre las competencias: su clave en la API, su
encabezado en ``BD GEN``, el prefijo de sus columnas en la base de datos, si se
comparan entre ESE y CORHUILA y cómo se muestran sus niveles. Los puntajes y
niveles viajan como diccionarios indexados por ``Competency.key``, nunca por
posición.

Escala común (ESE y CORHUILA, todas las competencias): Nivel 1 = 0–125,
Nivel 2 = 126–156, Nivel 3 = 157–198, Nivel 4 = 199–300. Inglés usa los mismos
límites y solo cambia su etiqueta (A1, A2, B1, B2).
"""

from dataclasses import dataclass

LEVEL_THRESHOLDS: tuple[tuple[int, float], ...] = (
    (1, 125),
    (2, 156),
    (3, 198),
    (4, float("inf")),
)
"""(nivel, puntaje máximo inclusive), en orden ascendente. El tope real es 300."""

NUMERIC_LEVEL_LABELS: tuple[str, ...] = ("1", "2", "3", "4")
ENGLISH_LEVEL_LABELS: tuple[str, ...] = ("A1", "A2", "B1", "B2")


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
    comparable: bool = True
    """Se compara entre ESE y CORHUILA y entra en métricas y vistas."""
    level_labels: tuple[str, ...] = NUMERIC_LEVEL_LABELS
    """Etiqueta de pantalla de los niveles 1 a 4."""

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
    ),
    Competency(
        key="comunicacion_escrita",
        label="Comunicación escrita",
        column="writing",
        score_header="comunicación escrita",
        # CORHUILA no la evalúa: se importa, pero no se muestra ni se compara.
        comparable=False,
    ),
    Competency(
        key="competencias_ciudadanas",
        label="Competencias ciudadanas",
        column="citizenship",
        score_header="competencias ciudadanas",
    ),
    Competency(
        key="razonamiento_cuantitativo",
        label="Razonamiento cuantitativo",
        column="quantitative",
        score_header="razonamiento cuantitativo",
    ),
    Competency(
        key="ingles",
        label="Inglés",
        column="english",
        score_header="inglés",
        level_labels=ENGLISH_LEVEL_LABELS,
    ),
)


COMPARABLE_COMPETENCIES: tuple[Competency, ...] = tuple(
    competency for competency in COMPETENCIES if competency.comparable
)
"""Las 4 competencias comunes a ESE y CORHUILA: las únicas en métricas y vistas."""


def classify_level_number(score: float | None) -> int | None:
    """Nivel 1–4 de un puntaje según la escala común. ``0`` es Nivel 1."""
    if score is None:
        return None
    for level, upper_bound in LEVEL_THRESHOLDS:
        if score <= upper_bound:
            return level
    raise ValueError(f"No se pudo asignar nivel al puntaje {score}.")


def classify_level(competency: Competency, score: float | None) -> str | None:
    """Etiqueta de pantalla del nivel de un puntaje (``"1"``… o ``"A1"``…)."""
    level = classify_level_number(score)
    return None if level is None else competency.level_labels[level - 1]


def level_number(competency: Competency, label: str | None) -> int | None:
    """Nivel 1–4 de una etiqueta (``"3"`` o ``"B1"``); ``None`` si no es válida."""
    if label is None or label not in competency.level_labels:
        return None
    return competency.level_labels.index(label) + 1
