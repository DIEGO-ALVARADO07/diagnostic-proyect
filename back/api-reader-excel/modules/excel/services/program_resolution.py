"""Estudiante y programa de las filas de CORHUILA, que el archivo no trae.

1. **Estudiante** (``StudentMatch``), buscado en el ESE activo en este orden:
   a. mismo **documento** (cuando el archivo de CORHUILA lo traiga);
   b. alguno de los **correos** del estudiante (institucional o personal);
   c. el **nombre completo** coincide con **un solo** estudiante de ESE.
      Si coincide con varios, queda ``AMBIGUO`` y no se asigna.
2. **Programa** (``ProgramResolution``): el de la fila de ESE **Momento 2** de
   ese estudiante más reciente con periodo **igual o anterior** al de
   CORHUILA (las de M2 sin periodo solo cuentan si no hay otra). Si no hay,
   ``SIN_PROGRAMA``.

Todo **se guarda** en la fila de CORHUILA (``student_id``, ``student_match``,
``program_id``, ``program_resolution``, ``program_resolved_import_id``,
``program_resolved_period``): el dashboard no repite el cruce en cada consulta.
Se recalcula al importar CORHUILA y al activar un ESE nuevo.
"""

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from hashlib import sha256

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.excel.entities.academic import (
    AcademicProgram,
    AcademicResult,
    AcademicStudent,
    AcademicStudentEmail,
    ActiveImport,
    ExcelImport,
)
from modules.excel.entities.assessment import (
    ProgramResolution,
    Source,
    StudentMatch,
)
from modules.excel.entities.import_status import ImportStatus
from modules.excel.services.dashboard_normalizer import (
    clean_text,
    document_value,
    email_key,
    normalized_key,
)

ESE_PROGRAM_MOMENT = 2
"""Momento de ESE del que se toma el programa de CORHUILA."""


@dataclass(frozen=True)
class MomentTwoRow:
    period: str | None
    source_row_number: int
    program_id: int | None


@dataclass
class EseIndex:
    """Lo necesario del ESE activo para encontrar estudiantes y su programa."""

    import_id: str | None = None
    by_document: dict[str, int] = field(default_factory=dict)
    """``document_key`` → estudiante."""
    by_email: dict[str, int] = field(default_factory=dict)
    """Correo (alias) → estudiante, solo estudiantes presentes en el ESE activo."""
    by_name: dict[str, set[int]] = field(default_factory=lambda: defaultdict(set))
    """Nombre completo normalizado → estudiantes."""
    moment_two: dict[int, list[MomentTwoRow]] = field(
        default_factory=lambda: defaultdict(list)
    )
    """Filas de Momento 2 por estudiante."""


def active_ese_import_id(db: Session) -> str | None:
    active = db.get(ActiveImport, Source.ESE.value)
    return active.import_id if active is not None else None


def build_ese_index(db: Session, ese_import_id: str | None) -> EseIndex:
    index = EseIndex(import_id=ese_import_id)
    if ese_import_id is None:
        return index
    student_ids: set[int] = set()
    for student_id, search_name, moment, period, row_number, program_id in db.execute(
        select(
            AcademicResult.student_id,
            AcademicResult.student_search_name,
            AcademicResult.moment,
            AcademicResult.period,
            AcademicResult.source_row_number,
            AcademicResult.program_id,
        ).where(
            AcademicResult.import_id == ese_import_id,
            AcademicResult.student_id.is_not(None),
        )
    ):
        student_ids.add(student_id)
        if search_name:
            index.by_name[search_name].add(student_id)
        if moment == ESE_PROGRAM_MOMENT:
            index.moment_two[student_id].append(
                MomentTwoRow(period, row_number, program_id)
            )
    if not student_ids:
        return index
    for student_id, document_key in db.execute(
        select(AcademicStudent.id, AcademicStudent.document_key).where(
            AcademicStudent.id.in_(student_ids),
            AcademicStudent.document_key.is_not(None),
        )
    ):
        index.by_document[document_key] = student_id
    for email, student_id in db.execute(
        select(AcademicStudentEmail.email_key, AcademicStudentEmail.student_id).where(
            AcademicStudentEmail.student_id.in_(student_ids)
        )
    ):
        index.by_email[email] = student_id
    return index


def match_student(
    index: EseIndex,
    document: str | None,
    email: str | None,
    name_key: str | None,
) -> tuple[int | None, StudentMatch]:
    """Estudiante de ESE para unos datos de CORHUILA y cómo se encontró."""
    document = document_value(document)
    if document is not None:
        student_id = index.by_document.get(
            sha256(document.encode("utf-8")).hexdigest()
        )
        if student_id is not None:
            return student_id, StudentMatch.DOCUMENTO
    email = email_key(email)
    if email is not None and email in index.by_email:
        return index.by_email[email], StudentMatch.CORREO
    if name_key:
        candidates = index.by_name.get(name_key, set())
        if len(candidates) == 1:
            return next(iter(candidates)), StudentMatch.NOMBRE
        if len(candidates) > 1:
            return None, StudentMatch.AMBIGUO
    return None, StudentMatch.SIN_COINCIDENCIA


def choose_moment_two(
    candidates: Iterable[MomentTwoRow], corhuila_period: str | None
) -> MomentTwoRow | None:
    """La fila de Momento 2 más reciente con periodo igual o anterior a CORHUILA.

    Los periodos ``AAAA-N`` se comparan como texto (``"2025-2" < "2026-1"``).
    """
    candidates = list(candidates)
    eligible = [
        row
        for row in candidates
        if row.program_id is not None
        and row.period is not None
        and (corhuila_period is None or row.period <= corhuila_period)
    ]
    if eligible:
        return max(eligible, key=lambda row: (row.period, row.source_row_number))
    undated = [
        row
        for row in candidates
        if row.program_id is not None and row.period is None
    ]
    return max(undated, key=lambda row: row.source_row_number) if undated else None


def resolve_results(
    db: Session,
    results: Iterable[AcademicResult],
    corhuila_period: str | None,
    index: EseIndex | None = None,
) -> int:
    """Encuentra y guarda estudiante y programa de filas de CORHUILA.

    Devuelve cuántas filas cambiaron.
    """
    if index is None:
        index = build_ese_index(db, active_ese_import_id(db))
    changed = 0
    for result in results:
        student_id, match = match_student(
            index,
            result.document_number_source,
            result.email_key,
            result.student_search_name,
        )
        row = (
            choose_moment_two(index.moment_two.get(student_id, ()), corhuila_period)
            if student_id is not None
            else None
        )
        values = (
            student_id if student_id is not None else result.student_id,
            match.value,
            row.program_id if row is not None else None,
            (
                ProgramResolution.ESE_M2.value
                if row is not None
                else ProgramResolution.SIN_PROGRAMA.value
            ),
            index.import_id if row is not None else None,
            row.period if row is not None else None,
        )
        current = (
            result.student_id,
            result.student_match,
            result.program_id,
            result.program_resolution,
            result.program_resolved_import_id,
            result.program_resolved_period,
        )
        if current != values:
            (
                result.student_id,
                result.student_match,
                result.program_id,
                result.program_resolution,
                result.program_resolved_import_id,
                result.program_resolved_period,
            ) = values
            changed += 1
    return changed


def refresh_corhuila_programs(db: Session) -> int:
    """Recalcula estudiante y programa de todas las importaciones de CORHUILA visibles.

    Se llama al activar un ESE nuevo, dentro de la misma transacción.
    """
    index = build_ese_index(db, active_ese_import_id(db))
    corhuila_imports = db.scalars(
        select(ExcelImport).where(
            ExcelImport.source == Source.CORHUILA.value,
            ExcelImport.deleted_at.is_(None),
            ExcelImport.status.in_(
                [ImportStatus.ACTIVE.value, ImportStatus.HISTORICAL.value]
            ),
        )
    ).all()
    changed = 0
    for corhuila_import in corhuila_imports:
        results = db.scalars(
            select(AcademicResult).where(
                AcademicResult.import_id == corhuila_import.id
            )
        )
        changed += resolve_results(db, results, corhuila_import.period, index)
    return changed


@dataclass(frozen=True)
class ProgramLookup:
    match: StudentMatch
    student_id: int | None
    name: str | None
    document: str | None
    emails: list[str]
    program_id: int | None
    program: str | None
    moment_two_period: str | None
    ese_import_id: str | None


def lookup_program(
    db: Session,
    document: str | None = None,
    email: str | None = None,
    full_name: str | None = None,
    corhuila_period: str | None = None,
) -> ProgramLookup:
    """Consulta: qué estudiante y qué programa se asignarían a estos datos."""
    index = build_ese_index(db, active_ese_import_id(db))
    student_id, match = match_student(
        index, document, email, normalized_key(clean_text(full_name)) or None
    )
    student = db.get(AcademicStudent, student_id) if student_id else None
    row = (
        choose_moment_two(index.moment_two.get(student_id, ()), corhuila_period)
        if student_id is not None
        else None
    )
    program = (
        db.get(AcademicProgram, row.program_id)
        if row is not None and row.program_id is not None
        else None
    )
    emails = (
        sorted(
            db.scalars(
                select(AcademicStudentEmail.email_key).where(
                    AcademicStudentEmail.student_id == student_id
                )
            )
        )
        if student_id is not None
        else []
    )
    return ProgramLookup(
        match=match,
        student_id=student_id,
        name=(
            " ".join(
                part for part in (student.first_name, student.last_name) if part
            )
            if student is not None
            else None
        ),
        document=student.document_number if student is not None else None,
        emails=emails,
        program_id=program.id if program is not None else None,
        program=program.canonical_name if program is not None else None,
        moment_two_period=row.period if row is not None else None,
        ese_import_id=index.import_id,
    )


def students_without_program(
    db: Session, period: str | None = None
) -> list[AcademicResult]:
    """Filas de CORHUILA activas que quedaron sin programa: lista "por revisar".

    Son estudiantes que no se encontraron en ESE, cuyo nombre es ambiguo, o que
    se encontraron pero no tienen un Momento 2 válido. Se resuelven solas al
    importar un ESE que los traiga; si no, hay que revisarlos en la base
    institucional.
    """
    query = (
        select(AcademicResult)
        .join(ExcelImport, ExcelImport.id == AcademicResult.import_id)
        .where(
            ExcelImport.source == Source.CORHUILA.value,
            ExcelImport.deleted_at.is_(None),
            ExcelImport.status == ImportStatus.ACTIVE.value,
            AcademicResult.program_resolution
            == ProgramResolution.SIN_PROGRAMA.value,
        )
        .order_by(
            AcademicResult.period,
            AcademicResult.last_name_source,
            AcademicResult.first_name_source,
        )
    )
    if period is not None:
        query = query.where(AcademicResult.period == period)
    return list(db.scalars(query))
