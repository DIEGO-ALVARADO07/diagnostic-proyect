"""Módulo Estudiantes (fase 13a): todos los estudiantes de los Excel por nivel.

Reglas (decisión del 26/11/2026):

- **Una sola lista:** ESE (todo su histórico) y CORHUILA (todos sus periodos
  activos) juntos; un estudiante aparece una vez aunque esté en ambas pruebas.
  Nadie se crea a mano: la lista sale de las cargas de Excel.
- **Periodo** (como en el dashboard): por defecto, el último con datos; solo
  aparecen los estudiantes de ese periodo y su nivel sale de ese periodo.
  ``period="all"`` es el histórico: todos los estudiantes, cada uno con el
  nivel de su periodo más reciente con puntajes.
- **Un nivel por estudiante** (para inscribir por nivel en el futuro módulo de
  cursos): se toma su periodo más reciente con puntajes. En ese periodo se
  promedia el puntaje de cada competencia común (si presentó ESE y CORHUILA,
  entran ambas), se clasifica cada una con la escala común (1–4) y el nivel del
  estudiante es el promedio de esos niveles **redondeado hacia abajo**.
  Ejemplo: 2, 3, 2 y 3 → 2,5 → Nivel 2.
- **Sin resultado:** nunca presentó o nunca tuvo puntajes.
- Se usan las 4 competencias comunes (sin Comunicación escrita).
"""

from collections.abc import Iterable
from dataclasses import dataclass
from math import floor
from statistics import fmean

from sqlalchemy.orm import Session

from modules.excel.dtos.responses.dashboard import (
    ProgramOptionResponse,
    StudentLevelGroupResponse,
    StudentLevelItemResponse,
    StudentLevelsResponse,
)
from modules.excel.entities.academic import ExcelImport
from modules.excel.entities.assessment import SIN_PROGRAMA_ID, Source
from modules.excel.entities.competency import (
    COMPARABLE_COMPETENCIES,
    classify_level,
    classify_level_number,
)
from modules.excel.entities.dashboard import DashboardRecord
from modules.excel.repositories.dashboard_persistence_repository import (
    DashboardPersistenceRepository,
)
from modules.excel.services.dashboard_dataset_loader import DashboardDatasetLoader
from modules.excel.services.dashboard_normalizer import normalized_key

NO_RESULT_KEY = "sin-resultado"
ALL_PERIODS = "all"
LEVEL_KEYS = ("1", "2", "3", "4", NO_RESULT_KEY)
LEVEL_RULE = (
    "Nivel del estudiante: promedio de los niveles de las 4 competencias "
    "comunes, redondeado hacia abajo, en el periodo elegido (en el histórico, "
    "su periodo más reciente con puntajes). \"Sin resultado\" = no presentó."
)


@dataclass(frozen=True)
class _Entry:
    record: DashboardRecord
    program_name: str


def _level_label(key: str) -> str:
    return "Sin resultado" if key == NO_RESULT_KEY else f"Nivel {key}"


def _period_key(record: DashboardRecord) -> str:
    return record.period or f"{record.year}-0"


def _has_scores(record: DashboardRecord) -> bool:
    return bool(record.presented) and any(
        record.scores[competency.key] is not None
        for competency in COMPARABLE_COMPETENCIES
    )


def student_level(
    records: Iterable[DashboardRecord],
) -> tuple[int | None, str | None, list[DashboardRecord]]:
    """Nivel del estudiante, su periodo y las filas de ese periodo."""
    scored = [record for record in records if _has_scores(record)]
    if not scored:
        return None, None, []
    period = max(_period_key(record) for record in scored)
    rows = [record for record in scored if _period_key(record) == period]
    levels = [
        classify_level_number(average)
        for average in _competency_averages(rows).values()
        if average is not None
    ]
    return floor(fmean(levels)), period, rows


def _competency_averages(
    rows: list[DashboardRecord],
) -> dict[str, float | None]:
    averages: dict[str, float | None] = {}
    for competency in COMPARABLE_COMPETENCIES:
        values = [
            score
            for record in rows
            if (score := record.scores[competency.key]) is not None
        ]
        averages[competency.key] = fmean(values) if values else None
    return averages


class StudentLevelsService:
    def __init__(
        self,
        persistence: DashboardPersistenceRepository,
        loader: DashboardDatasetLoader,
    ) -> None:
        self.persistence = persistence
        self.loader = loader

    def list(
        self,
        db: Session,
        level: str | None = None,
        program_id: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 50,
        period: str | None = None,
    ) -> StudentLevelsResponse:
        period, periods, students = self.students_in(db, period)
        programs = {item.program_id: item.program for item in students}

        if program_id is not None:
            students = [item for item in students if item.program_id == program_id]
        if search:
            needle = normalized_key(search)
            students = [
                item
                for item in students
                if needle
                in normalized_key(
                    " ".join(
                        part
                        for part in (item.name, item.document, item.email)
                        if part
                    )
                )
            ]

        counts = {key: 0 for key in LEVEL_KEYS}
        for item in students:
            counts[_key_of(item)] += 1
        total = len(students)
        if level is not None:
            students = [item for item in students if _key_of(item) == level]
        students.sort(key=lambda item: (normalized_key(item.name), item.student_key))

        start = (page - 1) * page_size
        return StudentLevelsResponse(
            total=total,
            groups=[
                StudentLevelGroupResponse(
                    key=key, label=_level_label(key), count=counts[key]
                )
                for key in LEVEL_KEYS
            ],
            programs=[
                ProgramOptionResponse(program_id=key, name=name)
                for key, name in sorted(
                    programs.items(),
                    key=lambda item: (
                        item[0] == SIN_PROGRAMA_ID,
                        normalized_key(item[1]),
                    ),
                )
            ],
            level=level,
            period=period,
            periods=periods,
            page=page,
            page_size=page_size,
            filtered_total=len(students),
            students=students[start : start + page_size],
            rule=LEVEL_RULE,
        )

    def students_in(
        self, db: Session, period: str | None = None
    ) -> tuple[str, list[str], list[StudentLevelItemResponse]]:
        """Todos los estudiantes del periodo (sin filtros ni páginas).

        Devuelve el periodo usado (el último si ``period`` es ``None``), los
        periodos con datos y los estudiantes. Lo usa también el módulo de cursos
        para inscribir por nivel.
        """
        grouped = self._group(db)
        periods = sorted(
            {
                entry.record.period
                for entries in grouped.values()
                for entry in entries
                if entry.record.period
            },
            reverse=True,
        )
        if period is None:
            period = periods[0] if periods else ALL_PERIODS

        students: list[StudentLevelItemResponse] = []
        for entries in grouped.values():
            selected = (
                entries
                if period == ALL_PERIODS
                else [e for e in entries if e.record.period == period]
            )
            if selected:
                students.append(self._item(selected, entries))
        return period, periods, students

    # --- Carga -----------------------------------------------------------------

    def _group(self, db: Session) -> dict[object, list[_Entry]]:
        """Filas de todas las cargas activas, agrupadas por persona."""
        grouped: dict[object, list[_Entry]] = {}
        for row in self._active_imports(db):
            dataset = self.loader.load(db, row)
            for record in dataset.records:
                identity = record.identity
                if identity is None:
                    continue
                grouped.setdefault(identity, []).append(
                    _Entry(record, dataset.program_names[record.program_id])
                )
        return grouped

    def _active_imports(self, db: Session) -> list[ExcelImport]:
        rows: list[ExcelImport] = []
        for active in self.persistence.list_active_imports(db):
            if not (
                active.slot == Source.ESE.value
                or active.slot.startswith(f"{Source.CORHUILA.value}:")
            ):
                continue
            row = db.get(ExcelImport, active.import_id)
            if row is not None and row.deleted_at is None:
                rows.append(row)
        return rows

    # --- Un estudiante ---------------------------------------------------------

    @staticmethod
    def _item(
        entries: list[_Entry], all_entries: list[_Entry]
    ) -> StudentLevelItemResponse:
        """``entries``: filas del periodo elegido; ``all_entries``: todas."""
        records = [entry.record for entry in entries]
        level, level_period, level_rows = student_level(records)
        # Datos de la fila más reciente; ESE primero porque trae documento.
        latest = max(
            entries,
            key=lambda entry: (
                _period_key(entry.record),
                entry.record.source == Source.ESE.value,
                entry.record.source_row_number,
            ),
        )
        averages = _competency_averages(level_rows)
        values = [value for value in averages.values() if value is not None]
        identity = latest.record.identity
        return StudentLevelItemResponse(
            student_key=(
                f"s{identity[1]}" if isinstance(identity, tuple) else str(identity)
            ),
            student_id=identity[1] if isinstance(identity, tuple) else None,
            name=latest.record.name,
            document=next(
                (e.record.document for e in all_entries if e.record.document),
                None,
            ),
            email=latest.record.email,
            program_id=latest.record.program_id,
            program=latest.program_name,
            level=level,
            level_period=level_period,
            level_sources=sorted({record.source for record in level_rows}),
            competency_levels={
                competency.key: classify_level(competency, averages[competency.key])
                for competency in COMPARABLE_COMPETENCIES
            },
            average=fmean(values) if values else None,
            last_period=max(_period_key(e.record) for e in all_entries),
        )


def _key_of(item: StudentLevelItemResponse) -> str:
    return NO_RESULT_KEY if item.level is None else str(item.level)
