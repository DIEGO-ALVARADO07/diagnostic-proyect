"""Estudiante y programa de las filas de CORHUILA, que el archivo no trae.

Regla vigente (decisión del 26/11/2026; el Excel de CORHUILA no se puede
modificar y el correo puede variar):

1. **Estudiante** (``StudentMatch``), buscado en **todo el histórico** del ESE
   activo, en este orden:

   a. mismo **documento** (si algún día el archivo lo trae);
   b. **nombre completo** (sin tildes, mayúsculas ni espacios extra) que
      coincide con **un solo** estudiante de ESE;
   c. si el nombre coincide con **varios**, el **correo** desempata cuando es
      alias de uno de ellos; si no desempata, queda ``AMBIGUO``;
   d. si el nombre no aparece en ESE, el **correo**;
   e. si nada coincide, ``SIN_COINCIDENCIA``.

2. **Programa** (``ProgramResolution``):

   a. ``MANUAL``: asignado a mano al estudiante (revisado contra la base
      institucional). Siempre manda.
   b. ``ESE``: el de su registro de ESE **más reciente** (año y periodo), de
      **cualquier momento** y haya presentado o no. Es el programa en el que
      está ahora (cubre homologaciones y materias adelantadas).
   c. ``SIN_PROGRAMA``: no está en ESE ni tiene programa manual.

Todo **se guarda** en la fila de CORHUILA (``student_id``, ``student_match``,
``program_id``, ``program_resolution``, ``program_resolved_import_id``,
``program_resolved_period``): el dashboard no repite el cruce en cada consulta.
Se recalcula al importar CORHUILA, al activar un ESE nuevo, al asignar un
programa manual y con ``POST /excel/dashboard/corhuila/resolve``.
"""

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from hashlib import sha256

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.orm import utcnow
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


@dataclass(frozen=True)
class EseProgramRow:
    """Una fila de ESE de un estudiante, con lo necesario para elegir programa."""

    year: int
    period: str | None
    moment: int | None
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
    history: dict[int, list[EseProgramRow]] = field(
        default_factory=lambda: defaultdict(list)
    )
    """Todas las filas de ESE de cada estudiante."""


def active_ese_import_id(db: Session) -> str | None:
    active = db.get(ActiveImport, Source.ESE.value)
    return active.import_id if active is not None else None


def build_ese_index(db: Session, ese_import_id: str | None) -> EseIndex:
    index = EseIndex(import_id=ese_import_id)
    if ese_import_id is None:
        return index
    for student_id, search_name, year, period, moment, row_number, program_id in db.execute(
        select(
            AcademicResult.student_id,
            AcademicResult.student_search_name,
            AcademicResult.year,
            AcademicResult.period,
            AcademicResult.moment,
            AcademicResult.source_row_number,
            AcademicResult.program_id,
        ).where(
            AcademicResult.import_id == ese_import_id,
            AcademicResult.student_id.is_not(None),
        )
    ):
        if search_name:
            index.by_name[search_name].add(student_id)
        index.history[student_id].append(
            EseProgramRow(year, period, moment, row_number, program_id)
        )
    student_ids = set(index.history)
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
    email_owner = index.by_email.get(email) if email is not None else None
    candidates = index.by_name.get(name_key, set()) if name_key else set()
    if len(candidates) == 1:
        return next(iter(candidates)), StudentMatch.NOMBRE
    if len(candidates) > 1:
        if email_owner in candidates:
            return email_owner, StudentMatch.CORREO
        return None, StudentMatch.AMBIGUO
    if email_owner is not None:
        return email_owner, StudentMatch.CORREO
    return None, StudentMatch.SIN_COINCIDENCIA


def choose_current_program(rows: Iterable[EseProgramRow]) -> EseProgramRow | None:
    """La fila de ESE más reciente (año, periodo y fila) que tiene programa.

    Es el programa en el que está el estudiante ahora: si en 2024 estaba en
    Veterinaria y en 2026 en Ingeniería de Software, se queda con Ingeniería.
    """
    return max(
        (row for row in rows if row.program_id is not None),
        key=lambda row: (row.year, row.period or "", row.source_row_number),
        default=None,
    )


def resolve_results(
    db: Session,
    results: Iterable[AcademicResult],
    corhuila_period: str | None = None,
    index: EseIndex | None = None,
) -> int:
    """Encuentra y guarda estudiante y programa de filas de CORHUILA.

    ``corhuila_period`` se conserva por compatibilidad: el programa ya no
    depende del periodo de CORHUILA. Devuelve cuántas filas cambiaron.
    """
    results = list(results)
    if index is None:
        index = build_ese_index(db, active_ese_import_id(db))

    matches = [
        match_student(
            index,
            result.document_number_source,
            result.email_key,
            result.student_search_name,
        )
        for result in results
    ]
    final_students = {
        student_id if student_id is not None else result.student_id
        for result, (student_id, _) in zip(results, matches)
    } - {None}
    manual = (
        dict(
            db.execute(
                select(AcademicStudent.id, AcademicStudent.assigned_program_id).where(
                    AcademicStudent.id.in_(final_students),
                    AcademicStudent.assigned_program_id.is_not(None),
                )
            ).all()
        )
        if final_students
        else {}
    )

    changed = 0
    for result, (student_id, match) in zip(results, matches):
        final_student = student_id if student_id is not None else result.student_id
        row = (
            choose_current_program(index.history.get(student_id, ()))
            if student_id is not None
            else None
        )
        if final_student in manual:
            program = (
                manual[final_student],
                ProgramResolution.MANUAL.value,
                None,
                None,
            )
        elif row is not None:
            program = (
                row.program_id,
                ProgramResolution.ESE.value,
                index.import_id,
                row.period,
            )
        else:
            program = (None, ProgramResolution.SIN_PROGRAMA.value, None, None)
        values = (final_student, match.value, *program)
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


def _visible_corhuila_imports(db: Session) -> list[ExcelImport]:
    return list(
        db.scalars(
            select(ExcelImport).where(
                ExcelImport.source == Source.CORHUILA.value,
                ExcelImport.deleted_at.is_(None),
                ExcelImport.status.in_(
                    [ImportStatus.ACTIVE.value, ImportStatus.HISTORICAL.value]
                ),
            )
        )
    )


def refresh_corhuila_programs(db: Session) -> int:
    """Recalcula estudiante y programa de todas las importaciones de CORHUILA visibles.

    Se llama al activar un ESE nuevo, dentro de la misma transacción, y desde
    ``POST /excel/dashboard/corhuila/resolve``.
    """
    index = build_ese_index(db, active_ese_import_id(db))
    changed = 0
    for corhuila_import in _visible_corhuila_imports(db):
        results = db.scalars(
            select(AcademicResult).where(
                AcademicResult.import_id == corhuila_import.id
            )
        )
        changed += resolve_results(db, results, corhuila_import.period, index)
    return changed


class ProgramAssignmentError(ValueError):
    pass


def assign_student_program(
    db: Session,
    student_id: int,
    program_id: int | None,
    user_id: int | None,
) -> int:
    """Asigna (o quita, con ``None``) el programa manual de un estudiante.

    Se usa desde la lista "por revisar" de CORHUILA, después de buscar al
    estudiante en la base institucional. Recalcula y guarda sus filas de
    CORHUILA. Devuelve cuántas filas cambiaron.
    """
    student = db.get(AcademicStudent, student_id)
    if student is None:
        raise ProgramAssignmentError("El estudiante no existe.")
    if program_id is not None and db.get(AcademicProgram, program_id) is None:
        raise ProgramAssignmentError("El programa no existe.")
    student.assigned_program_id = program_id
    student.assigned_program_by_user_id = user_id if program_id is not None else None
    student.assigned_program_at = utcnow() if program_id is not None else None
    db.flush()

    corhuila_ids = [item.id for item in _visible_corhuila_imports(db)]
    if not corhuila_ids:
        return 0
    results = db.scalars(
        select(AcademicResult).where(
            AcademicResult.import_id.in_(corhuila_ids),
            AcademicResult.student_id == student_id,
        )
    )
    return resolve_results(db, results)


@dataclass(frozen=True)
class ProgramLookup:
    match: StudentMatch
    student_id: int | None
    name: str | None
    document: str | None
    emails: list[str]
    program_id: int | None
    program: str | None
    program_source: str | None
    """``ESE``, ``MANUAL`` o ``None`` (sin programa)."""
    program_period: str | None
    """Periodo de la fila de ESE usada."""
    program_moment: int | None
    """Momento de la fila de ESE usada."""
    ese_import_id: str | None


def lookup_program(
    db: Session,
    document: str | None = None,
    email: str | None = None,
    full_name: str | None = None,
) -> ProgramLookup:
    """Consulta: qué estudiante y qué programa se asignarían a estos datos."""
    index = build_ese_index(db, active_ese_import_id(db))
    student_id, match = match_student(
        index, document, email, normalized_key(clean_text(full_name)) or None
    )
    student = db.get(AcademicStudent, student_id) if student_id else None
    row = (
        choose_current_program(index.history.get(student_id, ()))
        if student_id is not None
        else None
    )
    if student is not None and student.assigned_program_id is not None:
        program = db.get(AcademicProgram, student.assigned_program_id)
        source = ProgramResolution.MANUAL.value
        row = None
    elif row is not None:
        program = db.get(AcademicProgram, row.program_id)
        source = ProgramResolution.ESE.value
    else:
        program, source = None, None
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
        program_source=source,
        program_period=row.period if row is not None else None,
        program_moment=row.moment if row is not None else None,
        ese_import_id=index.import_id,
    )


def students_without_program(
    db: Session, period: str | None = None
) -> list[AcademicResult]:
    """Filas de CORHUILA activas que quedaron sin programa: lista "por revisar".

    Son estudiantes que no están en el histórico de ESE o cuyo nombre es
    ambiguo. Se resuelven solos al importar un ESE que los traiga, o al
    asignarles el programa a mano.
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
