"""Estudiante y programa de las filas de CORHUILA, que el archivo no trae.

**Fuente principal (fase 14b, 27/11/2026): el archivo de matriculados** del
mismo periodo. Una fila de CORHUILA es de un matriculado si:

- trae el mismo **documento**, o
- su **nombre completo** y **uno de los dos correos** (personal o
  institucional) coinciden con la **misma** persona de matriculados.

Si coincide, la fila toma de matriculados el **documento** (tipo y número, que
quedan en el estudiante), el **programa** y el **semestre**. Si el estudiante
está en **dos programas**, el mismo resultado cuenta en los dos
(``academic_result_programs``). Si no cumple nombre y correo a la vez, sigue la
regla anterior (ESE) y, si tampoco, queda "por revisar".

Regla anterior, que queda como respaldo (decisión del 26/11/2026; el Excel de
CORHUILA no se puede modificar y el correo puede variar):

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
   a2. ``MATRICULADOS``: el (o los) del archivo de matriculados del periodo.
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
from modules.enrollment.entities import (
    UPLOAD_ACTIVE,
    EnrollmentRecord,
    EnrollmentUpload,
)
from modules.excel.entities.academic import (
    AcademicProgram,
    AcademicResult,
    AcademicResultProgram,
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
    canonical_semester,
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


@dataclass
class EnrollmentPerson:
    """Un estudiante del archivo de matriculados (todas sus filas de programa)."""

    document_key: str
    document_number: str
    document_type: str | None
    first_names: str | None
    last_names: str | None
    email: str | None
    programs: list[tuple[str, str, int | None]] = field(default_factory=list)
    """``(program_key, nombre, semestre)`` en el orden del archivo."""


@dataclass
class EnrollmentIndex:
    """Matriculados activos de un periodo, para cruzar las filas de CORHUILA."""

    period: str | None = None
    by_document: dict[str, EnrollmentPerson] = field(default_factory=dict)
    by_name: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    """Nombre completo normalizado → documentos."""
    by_email: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    """Correo personal o institucional → documentos."""


def build_enrollment_index(db: Session, period: str | None) -> EnrollmentIndex:
    index = EnrollmentIndex(period=period)
    if period is None:
        return index
    upload_id = db.scalar(
        select(EnrollmentUpload.id).where(
            EnrollmentUpload.period == period,
            EnrollmentUpload.status == UPLOAD_ACTIVE,
        )
    )
    if upload_id is None:
        return index
    for record in db.scalars(
        select(EnrollmentRecord)
        .where(EnrollmentRecord.upload_id == upload_id)
        .order_by(EnrollmentRecord.source_row_number)
    ):
        person = index.by_document.get(record.document_key)
        if person is None:
            person = EnrollmentPerson(
                document_key=record.document_key,
                document_number=record.document_number,
                document_type=record.document_type,
                first_names=record.first_names,
                last_names=record.last_names,
                email=record.institutional_email or record.personal_email,
            )
            index.by_document[record.document_key] = person
            name_key = normalized_key(
                " ".join(part for part in (record.first_names, record.last_names) if part)
            )
            if name_key:
                index.by_name[name_key].add(record.document_key)
        if record.program_key not in {key for key, _, _ in person.programs}:
            person.programs.append(
                (record.program_key, record.program_name, record.semester)
            )
        for key in (record.personal_email_key, record.institutional_email_key):
            if key:
                index.by_email[key].add(record.document_key)
    return index


def match_enrollment(
    index: EnrollmentIndex,
    document: str | None,
    email: str | None,
    name_key: str | None,
) -> tuple[EnrollmentPerson | None, StudentMatch | None]:
    """Matriculado de una fila de CORHUILA: mismo documento, o nombre + correo."""
    document = document_value(document)
    if document is not None:
        person = index.by_document.get(sha256(document.encode("utf-8")).hexdigest())
        if person is not None:
            return person, StudentMatch.DOCUMENTO
    email = email_key(email)
    if not name_key or email is None:
        return None, None
    candidates = index.by_name.get(name_key, set()) & index.by_email.get(email, set())
    if len(candidates) == 1:
        return index.by_document[next(iter(candidates))], StudentMatch.MATRICULADOS
    return None, None


def ensure_programs(db: Session, names: dict[str, str]) -> dict[str, int]:
    """``program_key`` → id del catálogo; crea los programas que no existen.

    Los nombres de matriculados se toman como vienen (por ejemplo, las sedes y
    modalidades: ``INGENIERIA INDUSTRIAL-PITALITO``).
    """
    if not names:
        return {}
    ids = {
        program.normalized_key: program.id
        for program in db.scalars(
            select(AcademicProgram).where(AcademicProgram.normalized_key.in_(names))
        )
    }
    created = []
    for key, name in names.items():
        if key not in ids:
            program = AcademicProgram(
                canonical_name=name,
                raw_name_key=sha256(key.encode("utf-8")).hexdigest(),
                normalized_key=key,
                is_active=True,
            )
            db.add(program)
            created.append(program)
    if created:
        db.flush()
        ids.update({program.normalized_key: program.id for program in created})
    return ids


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


def _semester_fields(semester: int | None) -> tuple[str | None, str | None]:
    if semester is None:
        return None, None
    text = canonical_semester(str(semester))
    return text, normalized_key(text)


def _student_for_person(
    db: Session,
    person: EnrollmentPerson,
    current_id: int | None,
    by_document: dict[str, AcademicStudent],
    students: dict[int, AcademicStudent],
) -> int:
    """Estudiante con el documento del matriculado.

    1. Si ya hay un estudiante con ese documento, es ese.
    2. Si el estudiante actual de la fila no tiene documento, se le asigna.
    3. Si no (tiene otro documento o no hay), se crea uno con los datos de
       matriculados.
    El tipo de documento siempre se completa.
    """
    student = by_document.get(person.document_key)
    if student is None:
        current = students.get(current_id) if current_id is not None else None
        if current is not None and current.document_key is None:
            student = current
            student.document_key = person.document_key
            student.document_number = person.document_number
        else:
            student = AcademicStudent(
                document_key=person.document_key,
                document_number=person.document_number,
                first_name=person.first_names,
                last_name=person.last_names,
                email=person.email,
                email_key=email_key(person.email),
            )
            db.add(student)
            db.flush()
        by_document[person.document_key] = student
        students[student.id] = student
    if person.document_type and student.document_type != person.document_type:
        student.document_type = person.document_type
    return student.id


def resolve_results(
    db: Session,
    results: Iterable[AcademicResult],
    corhuila_period: str | None = None,
    index: EseIndex | None = None,
    enrollment: dict[str | None, EnrollmentIndex] | None = None,
) -> int:
    """Encuentra y guarda estudiante, programa(s) y semestre de filas de CORHUILA.

    Primero se busca en matriculados del periodo de cada fila (``enrollment``
    guarda los índices ya construidos, uno por periodo); si no aparece, en el
    histórico de ESE. Devuelve cuántas filas cambiaron.
    """
    results = list(results)
    if not results:
        return 0
    if index is None:
        index = build_ese_index(db, active_ese_import_id(db))
    if enrollment is None:
        enrollment = {}

    def enrollment_of(period: str | None) -> EnrollmentIndex:
        if period not in enrollment:
            enrollment[period] = build_enrollment_index(db, period)
        return enrollment[period]

    people = [
        match_enrollment(
            enrollment_of(result.period or corhuila_period),
            result.document_number_source,
            result.email_key,
            result.student_search_name,
        )
        for result in results
    ]
    ese_matches = [
        match_student(
            index,
            result.document_number_source,
            result.email_key,
            result.student_search_name,
        )
        for result in results
    ]

    # Estudiantes que se pueden tocar: los actuales de las filas, los de ESE y
    # los que ya tienen el documento de algún matriculado encontrado.
    person_keys = {person.document_key for person, _ in people if person is not None}
    candidate_ids = {result.student_id for result in results} | {
        student_id for student_id, _ in ese_matches
    }
    candidate_ids.discard(None)
    students = {
        student.id: student
        for student in db.scalars(
            select(AcademicStudent).where(
                (AcademicStudent.id.in_(candidate_ids))
                | (AcademicStudent.document_key.in_(person_keys))
            )
        )
    } if candidate_ids or person_keys else {}
    by_document = {
        student.document_key: student
        for student in students.values()
        if student.document_key is not None
    }

    program_names: dict[str, str] = {}
    for person, _ in people:
        if person is not None:
            for key, name, _ in person.programs:
                program_names.setdefault(key, name)
    program_ids = ensure_programs(db, program_names)

    final_students: list[int | None] = []
    for result, (person, _), (ese_student, _) in zip(results, people, ese_matches):
        if person is not None:
            final_students.append(
                _student_for_person(
                    db,
                    person,
                    ese_student if ese_student is not None else result.student_id,
                    by_document,
                    students,
                )
            )
        else:
            final_students.append(
                ese_student if ese_student is not None else result.student_id
            )

    manual = {
        student.id: student.assigned_program_id
        for student in students.values()
        if student.assigned_program_id is not None
    }
    current_extras: dict[int, set[int]] = defaultdict(set)
    result_ids = [result.id for result in results if result.id is not None]
    if result_ids:
        for result_id, program_id in db.execute(
            select(AcademicResultProgram.result_id, AcademicResultProgram.program_id)
            .where(AcademicResultProgram.result_id.in_(result_ids))
        ):
            current_extras[result_id].add(program_id)

    changed = 0
    for result, (person, person_match), (ese_student, ese_match), final_student in zip(
        results, people, ese_matches, final_students
    ):
        extras: list[int] = []
        semester: int | None = None
        if person is not None:
            match = person_match
            semester = person.programs[0][2]
        else:
            match = ese_match
        row = (
            choose_current_program(index.history.get(ese_student, ()))
            if ese_student is not None
            else None
        )
        if final_student in manual:
            program = (manual[final_student], ProgramResolution.MANUAL.value, None, None)
        elif person is not None:
            ids = [program_ids[key] for key, _, _ in person.programs]
            program = (
                ids[0],
                ProgramResolution.MATRICULADOS.value,
                None,
                enrollment_of(result.period or corhuila_period).period,
            )
            extras = ids[1:]
        elif row is not None:
            program = (
                row.program_id,
                ProgramResolution.ESE.value,
                index.import_id,
                row.period,
            )
        else:
            program = (None, ProgramResolution.SIN_PROGRAMA.value, None, None)
        values = (final_student, match.value, *program, *_semester_fields(semester))
        current = (
            result.student_id,
            result.student_match,
            result.program_id,
            result.program_resolution,
            result.program_resolved_import_id,
            result.program_resolved_period,
            result.semester_raw,
            result.semester_key,
        )
        row_changed = current != values
        if row_changed:
            (
                result.student_id,
                result.student_match,
                result.program_id,
                result.program_resolution,
                result.program_resolved_import_id,
                result.program_resolved_period,
                result.semester_raw,
                result.semester_key,
            ) = values
        wanted = set(extras)
        existing = current_extras.get(result.id, set()) if result.id is not None else set()
        if wanted != existing:
            if result.id is None:
                db.flush()
            for program_id in existing - wanted:
                db.execute(
                    AcademicResultProgram.__table__.delete().where(
                        (AcademicResultProgram.result_id == result.id)
                        & (AcademicResultProgram.program_id == program_id)
                    )
                )
            for program_id in wanted - existing:
                db.add(AcademicResultProgram(result_id=result.id, program_id=program_id))
            row_changed = True
        changed += row_changed
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
    enrollment: dict[str | None, EnrollmentIndex] = {}
    changed = 0
    for corhuila_import in _visible_corhuila_imports(db):
        results = db.scalars(
            select(AcademicResult).where(
                AcademicResult.import_id == corhuila_import.id
            )
        )
        changed += resolve_results(
            db, results, corhuila_import.period, index, enrollment
        )
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
