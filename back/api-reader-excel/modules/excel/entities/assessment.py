"""Fuente de la prueba, periodo del año y momento de la carrera.

- **Fuente:** ``ESE`` (empresa contratada, momentos 1, 2 y 3) o ``CORHUILA``
  (prueba institucional, momento único).
- **Periodo:** ``AAAA-1`` (antes de junio) o ``AAAA-2`` (después de junio). En
  ESE sale de la columna ``SIM`` (``SIMULACRO 2026-1 MOMENTO 3``).
- **Momento:** etapa de la carrera. En ESE sale de ``SIM`` y se confirma con
  ``GRUPO`` (``MOMENTO 3``). No depende del periodo del año.

Desde 2025 el Excel de ESE casi no trae la columna ``SEMESTRE``, así que el
rango de semestres se deduce del momento. El semestre exacto de un estudiante
solo se conoce cuando el archivo lo trae (consulta por estudiante).
"""

import re
from dataclasses import dataclass
from enum import StrEnum


class Source(StrEnum):
    ESE = "ESE"
    CORHUILA = "CORHUILA"


class ProgramResolution(StrEnum):
    """De dónde salió el programa de una fila de CORHUILA (que no lo trae)."""

    ESE = "ESE"
    """Programa del registro de ESE más reciente del estudiante (cualquier momento)."""
    MANUAL = "MANUAL"
    """Asignado a mano (revisado contra la base institucional). Siempre manda."""
    SIN_PROGRAMA = "SIN_PROGRAMA"
    """El estudiante no está en el histórico de ESE ni tiene programa manual."""


SIN_PROGRAMA_LABEL = "Sin programa"
SIN_PROGRAMA_ID = "sin-programa"
"""``program_id`` del subprograma que agrupa las filas sin programa."""


class StudentMatch(StrEnum):
    """Cómo se encontró en ESE al estudiante de una fila de CORHUILA."""

    DOCUMENTO = "DOCUMENTO"
    """Mismo documento de identidad (regla principal)."""
    CORREO = "CORREO"
    """Alguno de los correos del estudiante en ESE coincide."""
    NOMBRE = "NOMBRE"
    """El nombre completo coincide con un solo estudiante de ESE."""
    AMBIGUO = "AMBIGUO"
    """El nombre completo coincide con dos o más estudiantes: no se asigna."""
    SIN_COINCIDENCIA = "SIN_COINCIDENCIA"
    """No hay documento, correo ni nombre que coincida."""


@dataclass(frozen=True)
class SemesterRange:
    first: int
    last: int | None
    """``None`` = hasta el final de la carrera."""

    @property
    def label(self) -> str:
        if self.last is None:
            return f"{self.first} en adelante"
        return f"{self.first}–{self.last}"


ESE_MOMENT_SEMESTERS: dict[int, SemesterRange] = {
    1: SemesterRange(1, 3),
    2: SemesterRange(4, 6),
    3: SemesterRange(7, None),
    4: SemesterRange(8, 10),
}
"""Semestres que mide cada momento de ESE.

El Momento 4 solo existe en el histórico de 2024 (semestres 8–10). Desde 2025
ESE aplica como máximo el Momento 3.
"""

CURRENT_ESE_MOMENTS: tuple[int, ...] = (1, 2, 3)
"""Momentos del esquema actual: los que entran en la métrica de crecimiento
(M1 → M2 → CORHUILA → M3). El Momento 4 queda solo en el histórico."""

CORHUILA_SEMESTERS = SemesterRange(5, 6)
"""Semestres que mide la prueba institucional (momento único)."""

_PERIOD_PATTERN = re.compile(r"(?<!\d)(\d{4})\s*-\s*([12])(?!\d)")
_MOMENT_PATTERN = re.compile(r"momento\s*(\d+)", re.IGNORECASE)


def parse_period(value: str | None) -> str | None:
    """``"SIMULACRO 2026-1 MOMENTO 3"`` → ``"2026-1"``; ``None`` si no lo trae."""
    if not value:
        return None
    match = _PERIOD_PATTERN.search(value)
    return f"{match.group(1)}-{match.group(2)}" if match else None


def parse_moment(value: str | None) -> int | None:
    """``"MOMENTO 3"`` → ``3``; ``None`` si no es un momento de ESE (1–4)."""
    if not value:
        return None
    match = _MOMENT_PATTERN.search(value)
    if match is None:
        return None
    moment = int(match.group(1))
    return moment if moment in ESE_MOMENT_SEMESTERS else None


def resolve_ese_moment(simulation: str | None, group: str | None) -> int | None:
    """Momento de una fila de ESE: el de ``SIM``; si no lo trae, el de ``GRUPO``."""
    moment = parse_moment(simulation)
    return moment if moment is not None else parse_moment(group)


def semester_range(source: Source, moment: int | None) -> SemesterRange | None:
    if source is Source.CORHUILA:
        return CORHUILA_SEMESTERS
    return ESE_MOMENT_SEMESTERS.get(moment) if moment is not None else None


def active_slot(source: Source, period: str | None) -> str:
    """Espacio de importación activa.

    ESE manda siempre toda la historia, así que tiene un solo activo. CORHUILA
    manda un archivo por periodo, así que tiene un activo por periodo.
    """
    if source is Source.ESE:
        return Source.ESE.value
    if period is None:
        raise ValueError("Una importación de CORHUILA requiere periodo.")
    return f"{Source.CORHUILA.value}:{period}"


def source_sql_check() -> str:
    values = ", ".join(f"'{source.value}'" for source in Source)
    return f"source IN ({values})"
