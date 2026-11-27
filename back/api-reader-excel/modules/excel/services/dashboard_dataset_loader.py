"""Construye el ``DashboardDataset`` de una importación (desde caché o desde la base)."""

import logging
from dataclasses import replace
from time import perf_counter
from types import MappingProxyType
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.excel.entities.academic import (
    AcademicProgram,
    AcademicResult,
    AcademicResultProgram,
    AcademicStudent,
    ExcelImport,
    TdProgramasReference,
)
from modules.excel.entities.assessment import SIN_PROGRAMA_ID, SIN_PROGRAMA_LABEL
from modules.excel.entities.competency import COMPETENCIES
from modules.excel.entities.dashboard import DashboardDataset, DashboardRecord
from modules.excel.entities.import_status import SNAPSHOT_STATUSES
from modules.excel.services.dashboard_cache import DashboardDatasetCache
from modules.excel.services.dashboard_normalizer import canonical_semester

logger = logging.getLogger(__name__)


def _as_float(value: Any) -> float | None:
    return float(value) if value is not None else None


class DashboardDatasetLoader:
    def __init__(self, cache: DashboardDatasetCache | None = None) -> None:
        self.cache = cache if cache is not None else DashboardDatasetCache()

    def load(self, db: Session, import_row: ExcelImport) -> DashboardDataset:
        """Devuelve el dataset desde la caché o lo carga de la base de datos.

        Quien llama ya validó que la importación es visible para el usuario.
        Solo se cachean instantáneas inmutables (ACTIVE/HISTORICAL sin borrar).
        """
        cacheable = (
            import_row.deleted_at is None
            and import_row.status in SNAPSHOT_STATUSES
        )
        if cacheable:
            cached = self.cache.get(import_row.id)
            if cached is not None:
                return cached

        started = perf_counter()
        dataset = self.read_from_database(db, import_row)
        logger.info(
            "Dashboard dataset loaded from database: import_id=%s records=%d "
            "elapsed_seconds=%.3f cached=%s",
            import_row.id,
            len(dataset.records),
            perf_counter() - started,
            cacheable,
        )
        if cacheable:
            self.cache.put(dataset)
        return dataset

    def evict(self, import_id: str) -> None:
        self.cache.invalidate(import_id)

    @staticmethod
    def read_from_database(
        db: Session, import_row: ExcelImport
    ) -> DashboardDataset:
        results = list(
            db.scalars(
                select(AcademicResult)
                .where(AcademicResult.import_id == import_row.id)
                .order_by(AcademicResult.source_row_number)
            )
        )
        # Programas adicionales (doble programa): el mismo resultado cuenta en
        # cada uno de ellos.
        extra_programs: dict[int, list[int]] = {}
        result_ids = [result.id for result in results]
        for start in range(0, len(result_ids), 1000):
            for result_id, extra_id in db.execute(
                select(AcademicResultProgram.result_id, AcademicResultProgram.program_id)
                .where(AcademicResultProgram.result_id.in_(result_ids[start:start + 1000]))
                .order_by(AcademicResultProgram.program_id)
            ):
                extra_programs.setdefault(result_id, []).append(extra_id)
        # Documento y tipo del estudiante (los de CORHUILA salen de matriculados).
        student_ids = sorted({r.student_id for r in results if r.student_id is not None})
        student_documents: dict[int, tuple[str | None, str | None]] = {}
        for start in range(0, len(student_ids), 1000):
            for student_id, number, kind in db.execute(
                select(
                    AcademicStudent.id,
                    AcademicStudent.document_number,
                    AcademicStudent.document_type,
                ).where(AcademicStudent.id.in_(student_ids[start:start + 1000]))
            ):
                student_documents[student_id] = (number, kind)
        program_ids = {
            result.program_id
            for result in results
            if result.program_id is not None
        } | {extra for extras in extra_programs.values() for extra in extras}
        programs = {
            str(program.id): program.canonical_name
            for program in db.scalars(
                select(AcademicProgram).where(
                    AcademicProgram.id.in_(program_ids)
                )
            )
        } if program_ids else {}

        records: list[DashboardRecord] = []
        records_by_program: dict[str, list[DashboardRecord]] = {}
        # Filas por estudiante (``student_id``); se consultan por cualquiera de
        # sus correos o por su documento.
        student_rows: dict[object, list[DashboardRecord]] = {}
        student_of_key: dict[str, object] = {}
        for result in results:
            program_id = (
                str(result.program_id) if result.program_id else SIN_PROGRAMA_ID
            )
            # CORHUILA no trae programa: las filas sin programa de ESE se
            # agrupan como "Sin programa".
            program_name = programs.get(program_id) or (
                result.program_name_raw or SIN_PROGRAMA_LABEL
            )
            name = " ".join(
                value
                for value in (result.first_name_source, result.last_name_source)
                if value
            )
            student_document, document_type = student_documents.get(
                result.student_id, (None, None)
            )
            record = DashboardRecord(
                source_row_number=result.source_row_number,
                document=result.document_number_source or student_document,
                name=name,
                email=result.email_source,
                program_id=program_id,
                program_name=program_name,
                scores=MappingProxyType(
                    {
                        competency.key: _as_float(
                            getattr(result, competency.score_column)
                        )
                        for competency in COMPETENCIES
                    }
                ),
                global_score=_as_float(result.global_score),
                moment=result.moment_raw,
                test_type=result.assessment_type,
                semester=canonical_semester(result.semester_raw),
                year=result.year,
                simulation=result.simulation_name,
                group=result.group_name,
                presented=result.applies_simulacro,
                levels=MappingProxyType(
                    {
                        competency.key: getattr(result, competency.level_column)
                        for competency in COMPETENCIES
                    }
                ),
                ent=result.ent_raw,
                period=result.period,
                moment_number=result.moment,
                source=import_row.source,
                email_key=result.email_key,
                program_resolution=result.program_resolution,
                student_id=result.student_id,
                document_type=document_type,
            )
            copies = [record] + [
                replace(
                    record,
                    program_id=str(extra_id),
                    program_name=programs.get(str(extra_id), SIN_PROGRAMA_LABEL),
                )
                for extra_id in extra_programs.get(result.id, ())
            ]
            for copy in copies:
                records.append(copy)
                records_by_program.setdefault(copy.program_id, []).append(copy)
            group = (
                ("student", result.student_id)
                if result.student_id is not None
                else record.student_key
            )
            if group is not None:
                student_rows.setdefault(group, []).extend(copies)
                for key in {record.email_key, record.document} - {None}:
                    student_of_key.setdefault(key, group)

        td_summary: dict[tuple[str, str], dict[str, float | None]] = {}
        references = db.scalars(
            select(TdProgramasReference).where(
                TdProgramasReference.import_id == import_row.id
            )
        )
        for reference in references:
            td_summary[
                (reference.simulation_key, reference.program_normalized_key)
            ] = {
                competency.key: _as_float(
                    getattr(reference, competency.average_column)
                )
                for competency in COMPETENCIES
            } | {
                "average_global": _as_float(
                    reference.global_average_from_records
                ),
                "simple_competence_average": _as_float(
                    reference.average_of_competency_averages
                ),
            }

        program_names = {
            program_id: records_for_program[0].program_name
            for program_id, records_for_program in records_by_program.items()
        }
        # El dataset se comparte vía caché entre peticiones e hilos: se congela.
        return DashboardDataset(
            import_id=import_row.id,
            filename=import_row.filename,
            records=tuple(records),
            records_by_program=MappingProxyType(
                {key: tuple(value) for key, value in records_by_program.items()}
            ),
            records_by_student=MappingProxyType(
                {
                    key: tuple(student_rows[group])
                    for key, group in student_of_key.items()
                }
            ),
            program_names=MappingProxyType(program_names),
            td_programs_year=import_row.td_programas_selected_year,
            td_programs_summary=MappingProxyType(
                {
                    key: MappingProxyType(values)
                    for key, values in td_summary.items()
                }
            ),
            records_without_document=sum(
                record.document is None for record in records
            ),
            data_quality=(import_row.validation_summary or {}).get("data_quality"),
        )
