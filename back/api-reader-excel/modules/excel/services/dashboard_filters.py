"""Filtros del dashboard: qué registros entran y qué opciones se ofrecen."""

from collections import Counter
from collections.abc import Iterable

from modules.excel.dtos.requests.dashboard import DashboardFilterQuery
from modules.excel.dtos.responses.dashboard import (
    DashboardFilterOptionsResponse,
    DashboardSelectedFiltersResponse,
    ProgramOptionResponse,
)
from modules.excel.entities.dashboard import DashboardDataset, DashboardRecord
from modules.excel.services.dashboard_normalizer import clean_text, normalized_key


def matches(record: DashboardRecord, filters: DashboardFilterQuery) -> bool:
    """Los textos se comparan sin mayúsculas, tildes ni espacios extra."""
    if filters.year is not None and record.year != filters.year:
        return False
    if filters.period is not None and record.period != filters.period.strip():
        return False
    if filters.moment is not None and record.moment_number != filters.moment:
        return False
    if filters.simulation is not None and normalized_key(
        record.simulation
    ) != normalized_key(filters.simulation):
        return False
    if filters.group is not None and normalized_key(
        record.group
    ) != normalized_key(filters.group):
        return False
    if filters.test_type is not None and normalized_key(
        record.test_type
    ) != normalized_key(filters.test_type):
        return False
    return filters.presented is None or record.presented == filters.presented


def filter_records(
    records: Iterable[DashboardRecord], filters: DashboardFilterQuery
) -> list[DashboardRecord]:
    return [record for record in records if matches(record, filters)]


def filter_options(dataset: DashboardDataset) -> DashboardFilterOptionsResponse:
    def values_for(attribute: str) -> list[str]:
        # Agrupa variantes de escritura y muestra la más frecuente de cada grupo.
        variants: dict[str, Counter[str]] = {}
        for record in dataset.records:
            value = getattr(record, attribute)
            if value is None:
                continue
            variants.setdefault(normalized_key(value), Counter())[value] += 1
        return [
            sorted(
                counter,
                key=lambda value: (-counter[value], value.casefold()),
            )[0]
            for _, counter in sorted(variants.items())
        ]

    return DashboardFilterOptionsResponse(
        years=sorted({record.year for record in dataset.records}),
        periods=sorted(
            {record.period for record in dataset.records if record.period}
        ),
        moments=sorted(
            {
                record.moment_number
                for record in dataset.records
                if record.moment_number is not None
            }
        ),
        simulations=values_for("simulation"),
        groups=values_for("group"),
        programs=[
            ProgramOptionResponse(program_id=program_id, name=name)
            for program_id, name in sorted(
                dataset.program_names.items(),
                key=lambda item: normalized_key(item[1]),
            )
        ],
        test_types=values_for("test_type"),
        presented=[
            value
            for value in (False, True, None)
            if any(record.presented is value for record in dataset.records)
        ],
    )


def selected_filters(
    filters: DashboardFilterQuery,
) -> DashboardSelectedFiltersResponse:
    return DashboardSelectedFiltersResponse(**filters.model_dump())


def search_students(
    records: list[DashboardRecord], search: str | None
) -> list[DashboardRecord]:
    """Busca por documento, nombre o correo; sin texto devuelve la misma lista."""
    query = clean_text(search)
    if query is None:
        return records
    normalized_query = normalized_key(query)
    return [
        record
        for record in records
        if normalized_query in normalized_key(record.document)
        or normalized_query in normalized_key(record.name)
        or normalized_query in normalized_key(record.email)
    ]
