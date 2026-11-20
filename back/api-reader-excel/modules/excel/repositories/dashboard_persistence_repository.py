from hashlib import sha256

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.excel.entities.academic import (
    AcademicProgram,
    AcademicResult,
    AcademicStudent,
    DashboardState,
    ExcelImport,
    TdProgramasReference,
)
from modules.excel.entities.dashboard import DashboardImportData
from modules.security.entities.base import utcnow

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

    def get_active_import(self, db: Session) -> ExcelImport | None:
        state = db.get(DashboardState, 1)
        if state is None or state.active_import_id is None:
            return None
        return db.get(ExcelImport, state.active_import_id)

    def get_active_import_id(self, db: Session) -> str | None:
        state = db.get(DashboardState, 1)
        return state.active_import_id if state is not None else None

    def list_imports(self, db: Session, limit: int) -> list[ExcelImport]:
        return list(
            db.scalars(
                select(ExcelImport)
                .where(
                    ExcelImport.status.in_(
                        ("ACTIVE", "HISTORICAL", "FAILED")
                    )
                )
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
        program_keys = {record.program_raw_name_key for record in records}

        students = {
            student.document_key: student
            for student in db.scalars(
                select(AcademicStudent).where(
                    AcademicStudent.document_key.in_(document_keys)
                )
            )
        } if document_keys else {}
        programs = {
            program.raw_name_key: program
            for program in db.scalars(
                select(AcademicProgram).where(
                    AcademicProgram.raw_name_key.in_(program_keys)
                )
            )
        } if program_keys else {}

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

            program = programs.get(record.program_raw_name_key)
            if program is None:
                program = AcademicProgram(
                    canonical_name=record.program_name,
                    raw_name_key=record.program_raw_name_key,
                    normalized_key=record.program_normalized_key,
                    is_active=True,
                )
                programs[record.program_raw_name_key] = program
                db.add(program)

        db.flush()
        results: list[AcademicResult] = []
        for record in records:
            student_id = None
            if record.document is not None:
                student_id = students[
                    sha256(record.document.encode("utf-8")).hexdigest()
                ].id
            program = programs[record.program_raw_name_key]
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
                    reading_score=record.scores[0],
                    writing_score=record.scores[1],
                    citizenship_score=record.scores[2],
                    quantitative_score=record.scores[3],
                    english_score=record.scores[4],
                    global_raw=record.global_raw,
                    global_score=record.global_score,
                    global_calculated_score=record.global_calculated_score,
                    moment_raw=record.moment,
                    assessment_type=record.test_type,
                    assessment_type_key=record.test_type_key,
                    semester_raw=record.semester,
                    semester_key=record.semester_key,
                    year=record.year,
                    simulation_name=record.simulation,
                    simulation_key=record.simulation_key,
                    reading_level=record.levels[0],
                    writing_level=record.levels[1],
                    citizenship_level=record.levels[2],
                    quantitative_level=record.levels[3],
                    english_level=record.levels[4],
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
                reading_average=record.averages[0],
                writing_average=record.averages[1],
                citizenship_average=record.averages[2],
                quantitative_average=record.averages[3],
                english_average=record.averages[4],
                global_average_from_records=record.averages[5],
                average_of_competency_averages=record.averages[6],
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
        }
