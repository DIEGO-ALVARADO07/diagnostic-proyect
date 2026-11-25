from collections import defaultdict
from collections.abc import Sequence
from hashlib import sha256

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.excel.entities.academic import (
    AcademicProgram,
    AcademicStudentEmail,
    ActiveImport,
    AcademicProgramAlias,
    AcademicResult,
    AcademicStudent,
    DashboardState,
    ExcelImport,
    TdProgramasReference,
)
from modules.excel.entities.competency import COMPETENCIES
from modules.excel.entities.dashboard import (
    DashboardImportData,
    DashboardImportRecord,
)
from modules.excel.entities.import_status import (
    DASHBOARD_STATE_ID,
    DEACTIVATABLE_STATUSES,
)
from core.orm import utcnow

_INSERT_BATCH_SIZE = 500
INSTITUTIONAL_EMAIL_DOMAIN = "@corhuila.edu.co"


def _document_key(document: str) -> str:
    return sha256(document.encode("utf-8")).hexdigest()


class DashboardPersistenceRepository:
    def find_import_by_hash(
        self, db: Session, file_sha256: str
    ) -> ExcelImport | None:
        return db.scalar(
            select(ExcelImport).where(ExcelImport.file_sha256 == file_sha256)
        )

    def get_import(self, db: Session, import_id: str) -> ExcelImport | None:
        return db.get(ExcelImport, import_id)

    def get_active_import(self, db: Session, slot: str) -> ExcelImport | None:
        """Importación activa de un espacio (``ESE`` o ``CORHUILA:<periodo>``)."""
        active = db.get(ActiveImport, slot)
        return db.get(ExcelImport, active.import_id) if active is not None else None

    def lock_dashboard_state(self, db: Session) -> DashboardState | None:
        """Bloquea (SELECT ... FOR UPDATE) la fila única del estado del dashboard.

        Serializa activaciones y desactivaciones concurrentes de importaciones,
        de cualquier espacio.
        """
        return db.scalar(
            select(DashboardState)
            .where(DashboardState.id == DASHBOARD_STATE_ID)
            .with_for_update()
        )

    def get_active_import_id(self, db: Session, slot: str) -> str | None:
        active = db.get(ActiveImport, slot)
        return active.import_id if active is not None else None

    def list_active_imports(self, db: Session) -> list[ActiveImport]:
        return list(db.scalars(select(ActiveImport).order_by(ActiveImport.slot)))

    def set_active_import(self, db: Session, slot: str, import_id: str) -> None:
        """Debe llamarse con ``lock_dashboard_state`` tomado."""
        active = db.get(ActiveImport, slot)
        if active is None:
            db.add(ActiveImport(slot=slot, import_id=import_id))
        else:
            active.import_id = import_id

    def clear_active_import(self, db: Session, import_id: str) -> None:
        """Quita la importación de su espacio activo, si lo tiene."""
        active = db.scalar(
            select(ActiveImport).where(ActiveImport.import_id == import_id)
        )
        if active is not None:
            db.delete(active)

    def list_imports(self, db: Session, limit: int) -> list[ExcelImport]:
        return list(
            db.scalars(
                select(ExcelImport)
                .where(
                    ExcelImport.deleted_at.is_(None),
                    ExcelImport.status.in_(
                        [status.value for status in DEACTIVATABLE_STATUSES]
                    ),
                )
                .order_by(ExcelImport.imported_at.desc())
                .limit(limit)
            )
        )

    def list_all_imports(self, db: Session, limit: int) -> list[ExcelImport]:
        return list(
            db.scalars(
                select(ExcelImport)
                .order_by(ExcelImport.imported_at.desc())
                .limit(limit)
            )
        )

    def persist_snapshot(
        self,
        db: Session,
        import_row: ExcelImport,
        data: DashboardImportData,
    ) -> None:
        records = data.records
        record_students = self._sync_students(db, records)
        programs = self._sync_programs(db, data)

        db.flush()
        results: list[AcademicResult] = []
        for record, student in zip(records, record_students):
            student_id = student.id if student is not None else None
            program = programs[record.program_normalized_key]
            results.append(
                AcademicResult(
                    import_id=import_row.id,
                    source_row_number=record.source_row_number,
                    student_id=student_id,
                    document_number_source=record.document,
                    first_name_source=record.first_name,
                    last_name_source=record.last_name,
                    email_source=record.email,
                    email_key=record.email_key,
                    student_search_name=record.student_search_name,
                    program_id=program.id,
                    program_name_raw=record.program_name,
                    **{
                        competency.score_column: record.scores[competency.key]
                        for competency in COMPETENCIES
                    },
                    global_raw=record.global_raw,
                    global_score=record.global_score,
                    global_calculated_score=record.global_calculated_score,
                    moment_raw=record.moment,
                    period=record.period,
                    moment=record.moment_number,
                    assessment_type=record.test_type,
                    assessment_type_key=record.test_type_key,
                    semester_raw=record.semester,
                    semester_key=record.semester_key,
                    year=record.year,
                    simulation_name=record.simulation,
                    simulation_key=record.simulation_key,
                    **{
                        competency.level_column: record.levels[competency.key]
                        for competency in COMPETENCIES
                    },
                    campus_raw=record.campus,
                    group_name=record.group,
                    group_key=record.group_key,
                    applies_simulacro=record.presented,
                    applies_simulacro_raw=record.presented_raw,
                    training_applied_raw=record.training_applied,
                    ent_raw=record.ent,
                    source_payload=record.source_payload,
                )
            )
            if len(results) >= _INSERT_BATCH_SIZE:
                db.add_all(results)
                db.flush()
                results.clear()
        if results:
            db.add_all(results)

        references = [
            TdProgramasReference(
                import_id=import_row.id,
                source_row_number=record.source_row_number,
                selected_year=record.selected_year,
                simulation_name=record.simulation,
                simulation_key=record.simulation_key,
                program_name_raw=record.program_name,
                program_normalized_key=record.program_normalized_key,
                **{
                    competency.average_column: record.competency_averages[
                        competency.key
                    ]
                    for competency in COMPETENCIES
                },
                global_average_from_records=record.global_average,
                average_of_competency_averages=record.competency_mean,
                source_payload=record.source_payload,
            )
            for record in data.td_programas_records
        ]
        for offset in range(0, len(references), _INSERT_BATCH_SIZE):
            db.add_all(references[offset : offset + _INSERT_BATCH_SIZE])
            db.flush()

        import_row.bd_gen_row_count = len(data.records)
        import_row.td_programas_row_count = len(data.td_programas_records)
        import_row.inserted_count = len(data.records)
        import_row.rejected_count = 0
        import_row.td_programas_selected_year = data.td_programas_year
        import_row.validation_summary = {
            "status": "validated",
            "rows_without_document": sum(
                record.document is None for record in records
            ),
            "data_quality": dict(data.data_quality),
        }

    @staticmethod
    def _sync_students(
        db: Session, records: Sequence[DashboardImportRecord]
    ) -> list[AcademicStudent | None]:
        """Estudiante de cada registro. La identidad es el **documento**.

        - Con documento: se busca por documento. Si no existe, se adopta el
          estudiante sin documento que tenga ese correo (por ejemplo, uno creado
          desde CORHUILA) o se crea uno nuevo.
        - Sin documento: se busca por cualquiera de sus correos (alias).
        - Cada correo de la fila queda como alias del estudiante. Si el correo ya
          es de otro estudiante, no se mueve (``data_quality.identity``).
        - El correo principal es el institucional más reciente.
        """
        email_keys = {record.email_key for record in records if record.email_key}
        document_keys = {
            _document_key(record.document)
            for record in records
            if record.document is not None
        }
        by_document: dict[str, AcademicStudent] = {
            student.document_key: student
            for student in db.scalars(
                select(AcademicStudent).where(
                    AcademicStudent.document_key.in_(document_keys)
                )
            )
            if student.document_key is not None
        } if document_keys else {}
        by_email: dict[str, AcademicStudent] = {
            email: student
            for email, student in db.execute(
                select(AcademicStudentEmail.email_key, AcademicStudent)
                .join(
                    AcademicStudent,
                    AcademicStudent.id == AcademicStudentEmail.student_id,
                )
                .where(AcademicStudentEmail.email_key.in_(email_keys))
            )
        } if email_keys else {}
        known_aliases = set(by_email)

        now = utcnow()
        assigned: list[AcademicStudent | None] = []
        new_aliases: list[tuple[str, AcademicStudent]] = []
        for record in records:
            document_key = (
                _document_key(record.document)
                if record.document is not None
                else None
            )
            student: AcademicStudent | None = None
            if document_key is not None:
                student = by_document.get(document_key)
                if student is None and record.email_key is not None:
                    candidate = by_email.get(record.email_key)
                    if candidate is not None and candidate.document_key is None:
                        student = candidate
            elif record.email_key is not None:
                student = by_email.get(record.email_key)
            else:
                assigned.append(None)
                continue

            if student is None:
                student = AcademicStudent(
                    first_name=record.first_name,
                    last_name=record.last_name,
                    email=record.email,
                    created_at=now,
                    updated_at=now,
                )
                db.add(student)
            else:
                student.first_name = record.first_name or student.first_name
                student.last_name = record.last_name or student.last_name
                student.updated_at = now

            if document_key is not None and student.document_key is None:
                student.document_key = document_key
                by_document[document_key] = student
            if document_key is not None and student.document_key == document_key:
                student.document_number = record.document

            if record.email_key is not None:
                if record.email_key not in by_email:
                    by_email[record.email_key] = student
                    new_aliases.append((record.email_key, student))
                if by_email[record.email_key] is student and (
                    record.email_key.endswith(INSTITUTIONAL_EMAIL_DOMAIN)
                    or student.email_key is None
                    or not student.email_key.endswith(INSTITUTIONAL_EMAIL_DOMAIN)
                ):
                    student.email_key = record.email_key
                    student.email = record.email or student.email
            assigned.append(student)

        if new_aliases:
            db.flush()
            db.add_all(
                AcademicStudentEmail(email_key=email, student_id=student.id)
                for email, student in new_aliases
                if email not in known_aliases
            )
        return assigned

    @staticmethod
    def _sync_programs(
        db: Session, data: DashboardImportData
    ) -> dict[str, AcademicProgram]:
        """Un programa por clave normalizada; registra cada escritura como alias.

        El nombre visible se actualiza con el elegido en esta importación
        (``data.program_names``), así todas las importaciones lo comparten.
        """
        variants_by_key: dict[str, set[str]] = defaultdict(set)
        for record in data.records:
            variants_by_key[record.program_normalized_key].add(record.program_name)
        keys = sorted(variants_by_key)
        programs = {
            program.normalized_key: program
            for program in db.scalars(
                select(AcademicProgram).where(
                    AcademicProgram.normalized_key.in_(keys)
                )
            )
        } if keys else {}

        for key in keys:
            name = data.program_names[key]
            program = programs.get(key)
            if program is None:
                program = AcademicProgram(
                    canonical_name=name,
                    # Columna heredada (antes: hash del nombre crudo). Se mantiene
                    # única derivándola de la clave normalizada.
                    raw_name_key=sha256(key.encode("utf-8")).hexdigest(),
                    normalized_key=key,
                    is_active=True,
                )
                programs[key] = program
                db.add(program)
            else:
                program.canonical_name = name
        db.flush()

        # Se compara en Python: en MySQL la colación ignora tildes y mayúsculas.
        known_aliases = {
            (alias.program_id, alias.raw_name)
            for alias in db.scalars(
                select(AcademicProgramAlias).where(
                    AcademicProgramAlias.program_id.in_(
                        [program.id for program in programs.values()]
                    )
                )
            )
        } if programs else set()
        for key in keys:
            program = programs[key]
            for raw_name in sorted(variants_by_key[key]):
                if (program.id, raw_name) not in known_aliases:
                    db.add(
                        AcademicProgramAlias(
                            program_id=program.id,
                            raw_name=raw_name,
                            normalized_name=key,
                        )
                    )
        return programs
