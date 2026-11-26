"""Dashboard principal: ESE frente a CORHUILA en el **último periodo cargado**.

Reglas (decisión del 26/11/2026):

- **Periodo actual:** el más reciente entre el periodo de la carga de ESE
  activa (el que se eligió al subir) y los periodos de CORHUILA activos. Si en
  2026-2 solo se subió ESE, se muestra ESE de 2026-2 y CORHUILA queda "a la
  espera"; no se mezclan datos de 2026-1.
- **ESE** trae toda la historia: aquí solo entran sus filas de ese periodo. El
  histórico se consulta en el módulo ESE (``/excel/dashboard/{import_id}``).
- **Filtros:** momento (solo ESE: CORHUILA tiene momento único) y programa
  (ambas). No hay filtro de semestre ni de año.
- **"Sin programa"** es un subprograma más: entra en los promedios y su lista
  de estudiantes está en ``/excel/dashboard/review/without-program``.
- Se usan las 4 competencias comunes (sin Comunicación escrita).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from statistics import fmean

from sqlalchemy.orm import Session

from modules.excel.dtos.responses.dashboard import (
    CommonCompetencyResponse,
    CompareFiltersResponse,
    CompareSelectedFiltersResponse,
    CompareSideResponse,
    CompetencyHighlightResponse,
    DashboardCompareResponse,
    ProgramOptionResponse,
    ProgramSummaryResponse,
    WorstProgramResponse,
)
from modules.excel.entities.academic import ExcelImport
from modules.excel.entities.assessment import SIN_PROGRAMA_ID, Source
from modules.excel.entities.competency import COMPARABLE_COMPETENCIES
from modules.excel.entities.dashboard import DashboardDataset, DashboardRecord
from modules.excel.repositories.dashboard_persistence_repository import (
    DashboardPersistenceRepository,
)
from modules.excel.services import dashboard_mappers as mappers
from modules.excel.services.dashboard_dataset_loader import DashboardDatasetLoader
from modules.excel.services.dashboard_normalizer import normalized_key

COMPETENCY_NOTE = (
    "Los promedios usan solo las 4 competencias comunes a ESE y CORHUILA "
    "(sin Comunicación escrita); por eso el de ESE puede diferir del promedio "
    "del Excel de ESE."
)


@dataclass(frozen=True)
class _Side:
    source: Source
    import_row: ExcelImport
    dataset: DashboardDataset
    records: list[DashboardRecord]
    """Filas del periodo actual, antes de aplicar los filtros."""


class DashboardCompareService:
    def __init__(
        self,
        persistence: DashboardPersistenceRepository,
        loader: DashboardDatasetLoader,
    ) -> None:
        self.persistence = persistence
        self.loader = loader

    def compare(
        self,
        db: Session,
        moment: int | None = None,
        program_id: str | None = None,
    ) -> DashboardCompareResponse:
        ese_import = self._visible(
            self.persistence.get_active_import(db, Source.ESE.value)
        )
        corhuila_imports: dict[str, ExcelImport] = {}
        for active in self.persistence.list_active_imports(db):
            if active.slot.startswith(f"{Source.CORHUILA.value}:"):
                row = self._visible(db.get(ExcelImport, active.import_id))
                if row is not None and row.period is not None:
                    corhuila_imports[row.period] = row

        ese_dataset = (
            self.loader.load(db, ese_import) if ese_import is not None else None
        )
        candidates = set(corhuila_imports)
        if ese_dataset is not None:
            ese_period = ese_import.period or max(
                (record.period for record in ese_dataset.records if record.period),
                default=None,
            )
            if ese_period is not None:
                candidates.add(ese_period)
        period = max(candidates, default=None)

        sides: dict[Source, _Side] = {}
        if period is not None and ese_dataset is not None:
            records = [r for r in ese_dataset.records if r.period == period]
            if records:
                sides[Source.ESE] = _Side(
                    Source.ESE, ese_import, ese_dataset, records
                )
        if period in corhuila_imports:
            row = corhuila_imports[period]
            dataset = self.loader.load(db, row)
            sides[Source.CORHUILA] = _Side(
                Source.CORHUILA, row, dataset, list(dataset.records)
            )

        program_names: dict[str, str] = {}
        for side in sides.values():
            for record in side.records:
                program_names.setdefault(
                    record.program_id, side.dataset.program_names[record.program_id]
                )

        filtered: dict[Source, list[DashboardRecord]] = {}
        for source, side in sides.items():
            records = side.records
            if moment is not None and source is Source.ESE:
                records = [r for r in records if r.moment_number == moment]
            if program_id is not None:
                records = [r for r in records if r.program_id == program_id]
            filtered[source] = records

        side_responses = {
            source: self._side_response(side, filtered[source])
            for source, side in sides.items()
        }
        return DashboardCompareResponse(
            period=period,
            filters=CompareFiltersResponse(
                moments=sorted(
                    {
                        r.moment_number
                        for r in (sides[Source.ESE].records if Source.ESE in sides else [])
                        if r.moment_number is not None
                    }
                ),
                programs=[
                    ProgramOptionResponse(program_id=key, name=name)
                    for key, name in sorted(
                        program_names.items(),
                        key=lambda item: (
                            item[0] == SIN_PROGRAMA_ID,
                            normalized_key(item[1]),
                        ),
                    )
                ],
            ),
            selected_filters=CompareSelectedFiltersResponse(
                moment=moment, program_id=program_id
            ),
            ese=side_responses.get(Source.ESE),
            corhuila=side_responses.get(Source.CORHUILA),
            worst_program=_worst_program(filtered, program_names),
            lowest_common_competency=_lowest_common_competency(side_responses),
            note=COMPETENCY_NOTE,
        )

    @staticmethod
    def _visible(row: ExcelImport | None) -> ExcelImport | None:
        return row if row is not None and row.deleted_at is None else None

    @staticmethod
    def _side_response(
        side: _Side, records: Sequence[DashboardRecord]
    ) -> CompareSideResponse:
        by_program: dict[str, list[DashboardRecord]] = {}
        for record in records:
            by_program.setdefault(record.program_id, []).append(record)
        programs = [
            ProgramSummaryResponse(
                program_id=key,
                name=side.dataset.program_names[key],
                metrics=mappers.metrics_response(items),
            )
            for key, items in by_program.items()
        ]
        # Mejor promedio general primero; "Sin programa" y los vacíos al final.
        programs.sort(
            key=lambda item: (
                item.program_id == SIN_PROGRAMA_ID,
                item.metrics.average_general is None,
                -(item.metrics.average_general or 0),
                normalized_key(item.name),
            )
        )
        kpis = mappers.metrics_response(records)
        return CompareSideResponse(
            source=side.source.value,
            import_id=side.import_row.id,
            filename=side.import_row.filename,
            period=side.import_row.period,
            kpis=kpis,
            programs=programs,
            weakest_competency=_weakest(kpis.competencies),
        )


def _weakest(competencies) -> CompetencyHighlightResponse | None:
    available = [
        (key, item) for key, item in competencies.items() if item.average is not None
    ]
    if not available:
        return None
    key, item = min(available, key=lambda pair: pair[1].average)
    return CompetencyHighlightResponse(key=key, label=item.label, average=item.average)


def _worst_program(
    filtered: dict[Source, list[DashboardRecord]], names: dict[str, str]
) -> WorstProgramResponse | None:
    """Programa con el menor nivel promedio (1–4), uniendo ambas pruebas.

    "Sin programa" no compite: no es un programa real.
    """
    combined: dict[str, list[DashboardRecord]] = {}
    per_source: dict[tuple[Source, str], list[DashboardRecord]] = {}
    for source, records in filtered.items():
        for record in records:
            if record.program_id == SIN_PROGRAMA_ID:
                continue
            combined.setdefault(record.program_id, []).append(record)
            per_source.setdefault((source, record.program_id), []).append(record)
    levels = {
        key: mappers.metrics_response(items).average_level
        for key, items in combined.items()
    }
    levels = {key: value for key, value in levels.items() if value is not None}
    if not levels:
        return None
    key = min(levels, key=lambda item: (levels[item], normalized_key(names[item])))

    def side_level(source: Source) -> float | None:
        items = per_source.get((source, key))
        return mappers.metrics_response(items).average_level if items else None

    return WorstProgramResponse(
        program_id=key,
        name=names[key],
        average_level=levels[key],
        ese_average_level=side_level(Source.ESE),
        corhuila_average_level=side_level(Source.CORHUILA),
    )


def _lowest_common_competency(
    sides: dict[Source, CompareSideResponse],
) -> CommonCompetencyResponse | None:
    """Competencia con el promedio más bajo entre ambas pruebas.

    Se promedian los promedios de cada prueba (cada una pesa lo mismo); si solo
    hay una prueba cargada, se usa esa.
    """
    best: CommonCompetencyResponse | None = None
    for competency in COMPARABLE_COMPETENCIES:
        averages = {
            source: side.kpis.competencies[competency.key].average
            for source, side in sides.items()
            if competency.key in side.kpis.competencies
        }
        values = [value for value in averages.values() if value is not None]
        if not values:
            continue
        candidate = CommonCompetencyResponse(
            key=competency.key,
            label=competency.label,
            average=fmean(values),
            ese_average=averages.get(Source.ESE),
            corhuila_average=averages.get(Source.CORHUILA),
        )
        if best is None or candidate.average < best.average:
            best = candidate
    return best
