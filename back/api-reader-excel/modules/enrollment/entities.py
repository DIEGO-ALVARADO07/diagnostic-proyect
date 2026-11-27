from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from core.orm import Base, utcnow

UPLOAD_ACTIVE = "ACTIVE"
UPLOAD_REPLACED = "REPLACED"


class EnrollmentUpload(Base):
    """Una carga del archivo de matriculados de un periodo.

    Cada periodo tiene una sola carga ``ACTIVE``. Al subir otra, la anterior
    pasa a ``REPLACED``: se conserva quién la subió y cuándo, pero sus filas se
    borran para no guardar dos copias de los datos personales.
    """

    __tablename__ = "enrollment_uploads"
    __table_args__ = (
        CheckConstraint(
            f"status IN ('{UPLOAD_ACTIVE}', '{UPLOAD_REPLACED}')",
            name="ck_enrollment_uploads_status",
        ),
        Index("ix_enrollment_uploads_period_status", "period", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    period: Mapped[str] = mapped_column(String(7), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    """Filas guardadas (una por estudiante y programa)."""
    student_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    """Estudiantes distintos (por documento)."""
    rejected_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    """Filas sin documento o sin programa."""
    duplicate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    """Filas repetidas (mismo documento y mismo programa)."""
    uploaded_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("api_users.id", ondelete="SET NULL"), nullable=True
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow
    )
    replaced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class EnrollmentRecord(Base):
    """Un estudiante matriculado en un programa, tal como viene en el archivo."""

    __tablename__ = "enrollment_records"
    __table_args__ = (
        UniqueConstraint(
            "upload_id",
            "document_key",
            "program_key",
            name="uq_enrollment_records_student_program",
        ),
        Index("ix_enrollment_records_period_program", "period", "program_key"),
        Index("ix_enrollment_records_document_key", "document_key"),
        Index("ix_enrollment_records_institutional_email", "institutional_email_key"),
        Index("ix_enrollment_records_personal_email", "personal_email_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    upload_id: Mapped[str] = mapped_column(
        ForeignKey("enrollment_uploads.id", ondelete="CASCADE"), nullable=False
    )
    period: Mapped[str] = mapped_column(String(7), nullable=False)
    source_row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    pensum_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    program_name: Mapped[str] = mapped_column(String(255), nullable=False)
    program_key: Mapped[str] = mapped_column(String(255), nullable=False)
    """Programa sin mayúsculas, tildes ni espacios extra (``normalized_key``)."""
    semester: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    """Semestre en el que está el estudiante en este periodo."""
    document_type: Mapped[str | None] = mapped_column(String(10), nullable=True)
    document_number: Mapped[str] = mapped_column(String(40), nullable=False)
    document_key: Mapped[str] = mapped_column(String(64), nullable=False)
    """SHA-256 del documento, igual que ``academic_students.document_key``."""
    student_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    first_names: Mapped[str | None] = mapped_column(String(200), nullable=True)
    last_names: Mapped[str | None] = mapped_column(String(200), nullable=True)
    stratum: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(10), nullable=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    mobile: Mapped[str | None] = mapped_column(String(40), nullable=True)
    personal_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    personal_email_key: Mapped[str | None] = mapped_column(String(320), nullable=True)
    institutional_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    institutional_email_key: Mapped[str | None] = mapped_column(
        String(320), nullable=True
    )
    search_text: Mapped[str] = mapped_column(String(1200), nullable=False)
    """Nombre, documento, código y correos normalizados, para la búsqueda."""
