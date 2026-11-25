from collections import defaultdict
from hashlib import sha256

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.excel.entities.academic import (
    AcademicProgram,
    ActiveImport,
    AcademicProgramAlias,
    AcademicResult,
    AcademicStudent,
    DashboardState,
    ExcelImport,
    TdProgramasReference,
)
from modules.excel.entities.competency import COMPETENCIES
from modules.excel.entities.dashboard import DashboardImportData
from modules.excel.entities.import_status import (
    DASHBOARD_STATE_ID,
    DEACTIVATABLE_STATUSES,
)
from core.orm import utcnow

_INSERT_BATCH_SIZE = 500


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
        document_keys = {
            sha256(record.document.encode("utf-8")).hexdigest()
            for record in records
            if record.document is not None
        }

        students = {
            student.document_key: student
            for student in db.scalars(
                select(AcademicStudent).where(
                    AcademicStudent.document_key.in_(document_keys)
                )
            )
        } if document_keys else {}
        programs = self._sync_programs(db, data)

        now = utcnow()
        for record in records:
            if record.document is not None:
                document_key = sha256(record.document.encode("utf-8")).hexdigest()
                student = students.get(document_key)
                if student is None:
                    student = AcademicStudent(
                        document_key=document_key,
                        document_number=record.document,
                        first_name=record.first_name,
                        last_name=record.last_name,
                        email=record.email,
                        created_at=now,
                        updated_at=now,
                    )
                    students[document_key] = student
                    db.add(student)
                else:
                    student.document_number = record.document
                    student.first_name = record.first_name or student.first_name
                    student.last_name = record.last_name or student.last_name
                    student.email = record.email or student.email
                    student.updated_at = now

        db.flush()
        results: list[AcademicResult] = []
        for record in records:
            student_id = None
            if record.document is not None:
                student_id = students[
                    sha256(record.document.encode("utf-8")).hexdigest()
                ].id
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
