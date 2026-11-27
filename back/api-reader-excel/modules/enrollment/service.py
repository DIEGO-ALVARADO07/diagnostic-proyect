"""Carga y consulta del archivo de matriculados (solo superadmin).

Reglas:

- Un archivo por periodo (``2026-2``). Si trae ``COD_PERIODO`` (``20262``),
  debe coincidir con el periodo elegido.
- Se guardan todas las columnas. Cada fila es un estudiante en un programa: si
  el mismo documento aparece en dos programas, quedan las dos filas (doble
  programa). Una fila repetida (mismo documento y programa) se omite.
- Al subir otro archivo del mismo periodo, el anterior queda ``REPLACED``: se
  conserva quién y cuándo lo subió, pero sus filas se borran.
- Al subirlo se vuelve a cruzar CORHUILA (programa, documento y semestre salen
  de aquí; ver ``program_resolution``).
"""

import re
from collections import Counter
from collections.abc import Callable
from datetime import date, datetime
from hashlib import sha256
from http import HTTPStatus
from pathlib import Path
from typing import Any
from uuid import uuid4

import fastexcel
from sqlalchemy import delete, func, insert, select
from sqlalchemy.orm import Session

from core.exceptions import ApplicationError
from core.orm import utcnow
from modules.enrollment.dtos import (
    EnrollmentFiltersResponse,
    EnrollmentListResponse,
    EnrollmentRecordResponse,
    EnrollmentUploadResponse,
    OptionCountResponse,
)
from modules.enrollment.entities import (
    UPLOAD_ACTIVE,
    UPLOAD_REPLACED,
    EnrollmentRecord,
    EnrollmentUpload,
)
from modules.excel.entities.academic import AcademicStudent
from modules.excel.services.dashboard_normalizer import (
    clean_text,
    email_key,
    normalized_key,
)
from modules.excel.services.excel_service import ALLOWED_EXTENSIONS, MAX_UPLOAD_BYTES
from modules.excel.services.program_resolution import refresh_corhuila_programs
from modules.security.entities import Account

MAX_PAGE_SIZE = 200

# Encabezado normalizado del archivo → campo interno.
COLUMNS = {
    "cod_periodo": "period_code",
    "cod_pensum": "pensum_code",
    "programa": "program",
    "semestre": "semester",
    "tip_identificacion": "document_type",
    "identificacion": "document",
    "codigo": "code",
    "nombres": "first_names",
    "apellidos": "last_names",
    "estrato": "stratum",
    "genero": "gender",
    "fnacimiento": "birth_date",
    "telefono": "phone",
    "movil": "mobile",
    "email_personal": "personal_email",
    "email_institucional": "institutional_email",
}
REQUIRED_COLUMNS = ("programa", "identificacion", "nombres", "apellidos")

DOCUMENT_TYPE_LABELS = {
    "C": "Cédula de ciudadanía",
    "CC": "Cédula de ciudadanía",
    "T": "Tarjeta de identidad",
    "TI": "Tarjeta de identidad",
    "E": "Cédula de extranjería",
    "CE": "Cédula de extranjería",
    "P": "Pasaporte",
    "PPT": "Permiso por protección temporal",
}
GENDER_LABELS = {"M": "Masculino", "F": "Femenino"}

_PERIOD_CODE = re.compile(r"^(\d{4})\s*-?\s*([12])$")
_INTEGER_TEXT = re.compile(r"^(\d+)\.0+$")


def _header_key(header: Any) -> str:
    """``COD_PERIODO``, ``Cod Periodo`` y ``cod-periodo`` → ``cod_periodo``."""
    return re.sub(r"[\s\-]+", "_", normalized_key(str(header)))


def _text(value: Any, max_length: int) -> str | None:
    """Texto limpio; ``1075.0`` (número leído como decimal) → ``1075``."""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    text = clean_text(value)
    if text is None:
        return None
    match = _INTEGER_TEXT.match(text)
    if match:
        text = match.group(1)
    return text[:max_length]


def _integer(value: Any) -> int | None:
    text = _text(value, 10)
    if text is None or not text.isdigit():
        return None
    return int(text)


def _date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = clean_text(value)
    if text is None:
        return None
    for pattern, length in (("%Y-%m-%d", 10), ("%d/%m/%Y", 10)):
        try:
            return datetime.strptime(text[:length], pattern).date()
        except ValueError:
            continue
    return None


def _document(value: Any) -> str | None:
    text = _text(value, 40)
    return "".join(text.split()) if text else None


def period_from_code(value: Any) -> str | None:
    """``20262`` o ``2026-2`` → ``2026-2``."""
    text = _text(value, 10)
    if text is None:
        return None
    match = _PERIOD_CODE.match(text)
    return f"{match.group(1)}-{match.group(2)}" if match else None


def document_key(document: str) -> str:
    """Igual que ``academic_students.document_key``: SHA-256 del documento."""
    return sha256(document.encode("utf-8")).hexdigest()


class EnrollmentService:
    def __init__(self, on_change: Callable[[], None] | None = None) -> None:
        self.on_change = on_change
        """Se llama después de guardar (limpia la caché del dashboard)."""

    # --- Carga ---------------------------------------------------------------

    def validate_filename(self, filename: str) -> str:
        safe = Path(filename).name
        if Path(safe).suffix.casefold() not in ALLOWED_EXTENSIONS:
            raise ApplicationError(
                HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
                "Formato no válido. Usa .xlsx, .xlsm, .xls o .ods.",
            )
        return safe

    def _read_rows(self, content: bytes) -> list[dict[str, Any]]:
        """Filas de la primera hoja que tenga los encabezados obligatorios."""
        try:
            workbook = fastexcel.read_excel(content)
        except Exception as error:  # noqa: BLE001 (archivo corrupto o no Excel)
            raise ApplicationError(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                "No se pudo leer el archivo. Verifica que sea un Excel válido.",
            ) from error

        missing_first: list[str] | None = None
        for name in workbook.sheet_names:
            frame = workbook.load_sheet(name, dtypes="string").to_polars()
            keys = {column: _header_key(column) for column in frame.columns}
            missing = [key for key in REQUIRED_COLUMNS if key not in keys.values()]
            if not missing:
                return [
                    {
                        COLUMNS[keys[column]]: value
                        for column, value in row.items()
                        if keys[column] in COLUMNS
                    }
                    for row in frame.to_dicts()
                ]
            if missing_first is None:
                missing_first = missing
        raise ApplicationError(
            HTTPStatus.UNPROCESSABLE_ENTITY,
            "El archivo no tiene las columnas de matriculados. Faltan: "
            + ", ".join(key.upper() for key in (missing_first or REQUIRED_COLUMNS))
            + ".",
        )

    def import_file(
        self,
        db: Session,
        account: Account,
        filename: str,
        content: bytes,
        period: str,
    ) -> EnrollmentUploadResponse:
        safe_filename = self.validate_filename(filename)
        if len(content) > MAX_UPLOAD_BYTES:
            raise ApplicationError(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                "El archivo supera el límite de 30 MB.",
            )
        if not content:
            raise ApplicationError(HTTPStatus.UNPROCESSABLE_ENTITY, "El archivo está vacío.")

        rows = self._read_rows(content)

        file_periods = {
            code
            for code in (period_from_code(row.get("period_code")) for row in rows)
            if code is not None
        }
        if file_periods and file_periods != {period}:
            found = ", ".join(sorted(file_periods))
            raise ApplicationError(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                f"El archivo es del periodo {found}, pero elegiste {period}. "
                "Revisa el periodo antes de subirlo.",
            )

        digest = sha256(content).hexdigest()
        previous = db.scalar(
            select(EnrollmentUpload).where(
                EnrollmentUpload.period == period,
                EnrollmentUpload.status == UPLOAD_ACTIVE,
            )
        )
        if previous is not None and previous.file_sha256 == digest:
            raise ApplicationError(
                HTTPStatus.CONFLICT,
                f"Este archivo ya es el cargado para {period}. No hay nada que actualizar.",
            )

        upload_id = str(uuid4())
        records: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        rejected = duplicates = 0
        for index, row in enumerate(rows, start=2):  # fila 1 = encabezados
            if all(clean_text(value) is None for value in row.values()):
                continue
            document = _document(row.get("document"))
            program = _text(row.get("program"), 255)
            if document is None or program is None:
                rejected += 1
                continue
            doc_key = document_key(document)
            program_key = normalized_key(program)
            if (doc_key, program_key) in seen:
                duplicates += 1
                continue
            seen.add((doc_key, program_key))

            first_names = _text(row.get("first_names"), 200)
            last_names = _text(row.get("last_names"), 200)
            code = _text(row.get("code"), 40)
            personal_email = _text(row.get("personal_email"), 320)
            institutional_email = _text(row.get("institutional_email"), 320)
            records.append(
                {
                    "upload_id": upload_id,
                    "period": period,
                    "source_row_number": index,
                    "pensum_code": _text(row.get("pensum_code"), 20),
                    "program_name": program,
                    "program_key": program_key,
                    "semester": _integer(row.get("semester")),
                    "document_type": (_text(row.get("document_type"), 10) or "").upper() or None,
                    "document_number": document,
                    "document_key": doc_key,
                    "student_code": code,
                    "first_names": first_names,
                    "last_names": last_names,
                    "stratum": _integer(row.get("stratum")),
                    "gender": (_text(row.get("gender"), 10) or "").upper() or None,
                    "birth_date": _date(row.get("birth_date")),
                    "phone": _text(row.get("phone"), 40),
                    "mobile": _text(row.get("mobile"), 40),
                    "personal_email": personal_email,
                    "personal_email_key": email_key(personal_email),
                    "institutional_email": institutional_email,
                    "institutional_email_key": email_key(institutional_email),
                    "search_text": normalized_key(
                        " ".join(
                            part
                            for part in (
                                first_names, last_names, document, code,
                                personal_email, institutional_email,
                            )
                            if part
                        )
                    )[:1200],
                }
            )

        if not records:
            raise ApplicationError(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                "El archivo no tiene estudiantes con documento y programa.",
            )

        programs_by_student = Counter(record["document_key"] for record in records)
        now = utcnow()
        if previous is not None:
            previous.status = UPLOAD_REPLACED
            previous.replaced_at = now
            db.execute(
                delete(EnrollmentRecord).where(EnrollmentRecord.upload_id == previous.id)
            )
            db.flush()

        upload = EnrollmentUpload(
            id=upload_id,
            period=period,
            filename=safe_filename,
            file_sha256=digest,
            status=UPLOAD_ACTIVE,
            row_count=len(records),
            student_count=len(programs_by_student),
            rejected_count=rejected,
            duplicate_count=duplicates,
            uploaded_by_user_id=account.id,
            uploaded_at=now,
        )
        db.add(upload)
        db.flush()
        for start in range(0, len(records), 500):
            db.execute(insert(EnrollmentRecord), records[start:start + 500])
        db.flush()
        self._fill_document_types(db, records)
        corhuila_rows = refresh_corhuila_programs(db)
        db.commit()
        if self.on_change is not None:
            self.on_change()

        response = self._upload(
            upload,
            sum(1 for count in programs_by_student.values() if count > 1),
            account.full_name or account.username,
        )
        response.replaced_previous = previous is not None
        response.corhuila_rows_updated = corhuila_rows
        return response

    @staticmethod
    def _fill_document_types(db: Session, records: list[dict[str, Any]]) -> None:
        """Completa el tipo de documento de los estudiantes que ya existen (ESE)."""
        types = {
            record["document_key"]: record["document_type"]
            for record in records
            if record["document_type"]
        }
        keys = list(types)
        for start in range(0, len(keys), 500):
            for student in db.scalars(
                select(AcademicStudent).where(
                    AcademicStudent.document_key.in_(keys[start:start + 500])
                )
            ):
                if student.document_type != types[student.document_key]:
                    student.document_type = types[student.document_key]

    # --- Consulta ------------------------------------------------------------

    @staticmethod
    def _upload(
        upload: EnrollmentUpload, double_program: int, uploaded_by: str | None
    ) -> EnrollmentUploadResponse:
        return EnrollmentUploadResponse(
            id=upload.id,
            period=upload.period,
            filename=upload.filename,
            status=upload.status,
            rows=upload.row_count,
            students=upload.student_count,
            double_program=double_program,
            rejected=upload.rejected_count,
            duplicates=upload.duplicate_count,
            uploaded_at=upload.uploaded_at,
            uploaded_by=uploaded_by,
        )

    @staticmethod
    def _double_program(db: Session, upload_id: str) -> int:
        per_student = (
            select(EnrollmentRecord.document_key)
            .where(EnrollmentRecord.upload_id == upload_id)
            .group_by(EnrollmentRecord.document_key)
            .having(func.count() > 1)
            .subquery()
        )
        return db.scalar(select(func.count()).select_from(per_student)) or 0

    def _active_uploads(self, db: Session) -> list[EnrollmentUploadResponse]:
        uploads = db.scalars(
            select(EnrollmentUpload)
            .where(EnrollmentUpload.status == UPLOAD_ACTIVE)
            .order_by(EnrollmentUpload.period.desc())
        ).all()
        user_ids = {u.uploaded_by_user_id for u in uploads if u.uploaded_by_user_id}
        names = {
            account.id: account.full_name or account.username
            for account in db.scalars(select(Account).where(Account.id.in_(user_ids)))
        } if user_ids else {}
        return [
            self._upload(
                upload,
                self._double_program(db, upload.id),
                names.get(upload.uploaded_by_user_id),
            )
            for upload in uploads
        ]

    @staticmethod
    def _options(
        db: Session, upload_id: str, column: Any, label: Any
    ) -> list[OptionCountResponse]:
        rows = db.execute(
            select(column, func.count())
            .where(EnrollmentRecord.upload_id == upload_id, column.is_not(None))
            .group_by(column)
            .order_by(column)
        ).all()
        return [
            OptionCountResponse(value=str(value), label=label(value), count=count)
            for value, count in rows
        ]

    def _filters(self, db: Session, upload_id: str) -> EnrollmentFiltersResponse:
        programs = db.execute(
            select(
                EnrollmentRecord.program_key,
                func.min(EnrollmentRecord.program_name),
                func.count(),
            )
            .where(EnrollmentRecord.upload_id == upload_id)
            .group_by(EnrollmentRecord.program_key)
            .order_by(EnrollmentRecord.program_key)
        ).all()
        return EnrollmentFiltersResponse(
            programs=[
                OptionCountResponse(value=key, label=name, count=count)
                for key, name, count in programs
            ],
            semesters=self._options(
                db, upload_id, EnrollmentRecord.semester, lambda v: f"Semestre {v}"
            ),
            document_types=self._options(
                db, upload_id, EnrollmentRecord.document_type,
                lambda v: DOCUMENT_TYPE_LABELS.get(v, v),
            ),
            genders=self._options(
                db, upload_id, EnrollmentRecord.gender,
                lambda v: GENDER_LABELS.get(v, v),
            ),
            strata=self._options(
                db, upload_id, EnrollmentRecord.stratum, lambda v: f"Estrato {v}"
            ),
        )

    def list_records(
        self,
        db: Session,
        period: str | None = None,
        program: str | None = None,
        semester: int | None = None,
        document_type: str | None = None,
        gender: str | None = None,
        stratum: int | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> EnrollmentListResponse:
        uploads = self._active_uploads(db)
        if period is None and uploads:
            period = uploads[0].period
        upload = next((item for item in uploads if item.period == period), None)
        empty_filters = EnrollmentFiltersResponse(
            programs=[], semesters=[], document_types=[], genders=[], strata=[]
        )
        if upload is None:
            return EnrollmentListResponse(
                period=period, uploads=uploads, filters=empty_filters, items=[],
                filtered_total=0, filtered_students=0, page=1, page_size=page_size,
            )

        conditions = [EnrollmentRecord.upload_id == upload.id]
        if program:
            conditions.append(EnrollmentRecord.program_key == program)
        if semester is not None:
            conditions.append(EnrollmentRecord.semester == semester)
        if document_type:
            conditions.append(EnrollmentRecord.document_type == document_type)
        if gender:
            conditions.append(EnrollmentRecord.gender == gender)
        if stratum is not None:
            conditions.append(EnrollmentRecord.stratum == stratum)
        for token in normalized_key(search or "").split():
            conditions.append(EnrollmentRecord.search_text.contains(token, autoescape=True))

        filtered_total, filtered_students = db.execute(
            select(func.count(), func.count(EnrollmentRecord.document_key.distinct()))
            .where(*conditions)
        ).one()
        pages = max(1, -(-filtered_total // page_size))
        page = min(max(1, page), pages)
        records = db.scalars(
            select(EnrollmentRecord)
            .where(*conditions)
            .order_by(
                EnrollmentRecord.last_names,
                EnrollmentRecord.first_names,
                EnrollmentRecord.program_name,
                EnrollmentRecord.id,
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()

        keys = {record.document_key for record in records}
        programs_count = dict(
            db.execute(
                select(EnrollmentRecord.document_key, func.count())
                .where(
                    EnrollmentRecord.upload_id == upload.id,
                    EnrollmentRecord.document_key.in_(keys),
                )
                .group_by(EnrollmentRecord.document_key)
            ).all()
        ) if keys else {}

        return EnrollmentListResponse(
            period=period,
            uploads=uploads,
            filters=self._filters(db, upload.id),
            items=[
                EnrollmentRecordResponse(
                    id=record.id,
                    period=record.period,
                    pensum_code=record.pensum_code,
                    program=record.program_name,
                    semester=record.semester,
                    document_type=record.document_type,
                    document_number=record.document_number,
                    student_code=record.student_code,
                    first_names=record.first_names,
                    last_names=record.last_names,
                    stratum=record.stratum,
                    gender=record.gender,
                    birth_date=record.birth_date,
                    phone=record.phone,
                    mobile=record.mobile,
                    personal_email=record.personal_email,
                    institutional_email=record.institutional_email,
                    programs_count=programs_count.get(record.document_key, 1),
                )
                for record in records
            ],
            filtered_total=filtered_total,
            filtered_students=filtered_students,
            page=page,
            page_size=page_size,
        )
