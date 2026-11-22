from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from modules.excel.entities.import_status import (
    SNAPSHOT_DATASET_MODE,
    ImportStatus,
    status_sql_check,
)
from modules.security.entities.base import AuthBase, utcnow


class ExcelImport(AuthBase):
    __tablename__ = "excel_imports"
    __table_args__ = (
        CheckConstraint(
            status_sql_check(),
            name="ck_excel_imports_status",
        ),
        CheckConstraint(
            f"dataset_mode = '{SNAPSHOT_DATASET_MODE}'",
            name="ck_excel_imports_dataset_mode",
        ),
        Index("ix_excel_imports_status_imported_at", "status", "imported_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_sha256: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True
    )
    imported_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("api_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    imported_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ImportStatus.PROCESSING.value
    )
    dataset_mode: Mapped[str] = mapped_column(
        String(20), nullable=False, default=SNAPSHOT_DATASET_MODE
    )
    bd_gen_row_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    td_programas_row_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    inserted_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    rejected_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    td_programas_selected_year: Mapped[int | None] = mapped_column(
        SmallInteger, nullable=True
    )
    validation_summary: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )
    activated_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )


class DashboardState(AuthBase):
    __tablename__ = "excel_dashboard_state"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    active_import_id: Mapped[str | None] = mapped_column(
        ForeignKey("excel_imports.id", ondelete="SET NULL"),
        nullable=True,
    )


class AcademicStudent(AuthBase):
    __tablename__ = "academic_students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_key: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True
    )
    document_number: Mapped[str] = mapped_column(
        String(80), nullable=False
    )
    first_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, onupdate=utcnow
    )


class AcademicProgram(AuthBase):
    __tablename__ = "academic_programs"
    __table_args__ = (
        Index("ix_academic_programs_normalized_key", "normalized_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    canonical_name: Mapped[str] = mapped_column(String(255), nullable=False)
    raw_name_key: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True
    )
    normalized_key: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )


class AcademicProgramAlias(AuthBase):
    __tablename__ = "academic_program_aliases"
    __table_args__ = (
        Index("ix_academic_program_aliases_normalized_name", "normalized_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    program_id: Mapped[int] = mapped_column(
        ForeignKey("academic_programs.id", ondelete="CASCADE"),
        nullable=False,
    )
    raw_name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False)
    confirmed_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("api_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )


class AcademicResult(AuthBase):
    __tablename__ = "academic_results"
    __table_args__ = (
        UniqueConstraint(
            "import_id",
            "source_row_number",
            name="uq_academic_results_import_source_row",
        ),
        Index(
            "ix_academic_results_import_year_sim_program",
            "import_id",
            "year",
            "simulation_key",
            "program_id",
        ),
        Index(
            "ix_academic_results_import_student_year",
            "import_id",
            "student_id",
            "year",
        ),
        Index(
            "ix_academic_results_import_document",
            "import_id",
            "document_number_source",
        ),
        Index(
            "ix_academic_results_import_presented",
            "import_id",
            "applies_simulacro",
        ),
        Index(
            "ix_academic_results_program_year_sim",
            "program_id",
            "year",
            "simulation_key",
        ),
        Index(
            "ix_academic_results_import_search",
            "import_id",
            "student_search_name",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    import_id: Mapped[str] = mapped_column(
        ForeignKey("excel_imports.id", ondelete="CASCADE"), nullable=False
    )
    source_row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    student_id: Mapped[int | None] = mapped_column(
        ForeignKey("academic_students.id", ondelete="SET NULL"),
        nullable=True,
    )
    document_number_source: Mapped[str | None] = mapped_column(
        String(80), nullable=True
    )
    first_name_source: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )
    last_name_source: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )
    email_source: Mapped[str | None] = mapped_column(
        String(320), nullable=True
    )
    student_search_name: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    program_id: Mapped[int | None] = mapped_column(
        ForeignKey("academic_programs.id", ondelete="SET NULL"),
        nullable=True,
    )
    program_name_raw: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    reading_score: Mapped[Decimal | None] = mapped_column(
        Numeric(16, 6), nullable=True
    )
    writing_score: Mapped[Decimal | None] = mapped_column(
        Numeric(16, 6), nullable=True
    )
    citizenship_score: Mapped[Decimal | None] = mapped_column(
        Numeric(16, 6), nullable=True
    )
    quantitative_score: Mapped[Decimal | None] = mapped_column(
        Numeric(16, 6), nullable=True
    )
    english_score: Mapped[Decimal | None] = mapped_column(
        Numeric(16, 6), nullable=True
    )
    global_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    global_score: Mapped[Decimal | None] = mapped_column(
        Numeric(16, 6), nullable=True
    )
    global_calculated_score: Mapped[Decimal | None] = mapped_column(
        Numeric(16, 6), nullable=True
    )
    moment_raw: Mapped[str | None] = mapped_column(String(100), nullable=True)
    assessment_type: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    assessment_type_key: Mapped[str | None] = mapped_column(
        String(120), nullable=True
    )
    semester_raw: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    semester_key: Mapped[str | None] = mapped_column(
        String(120), nullable=True
    )
    year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    simulation_name: Mapped[str] = mapped_column(String(255), nullable=False)
    simulation_key: Mapped[str] = mapped_column(String(255), nullable=False)
    reading_level: Mapped[str | None] = mapped_column(String(16), nullable=True)
    writing_level: Mapped[str | None] = mapped_column(String(16), nullable=True)
    citizenship_level: Mapped[str | None] = mapped_column(
        String(16), nullable=True
    )
    quantitative_level: Mapped[str | None] = mapped_column(
        String(16), nullable=True
    )
    english_level: Mapped[str | None] = mapped_column(String(16), nullable=True)
    campus_raw: Mapped[str | None] = mapped_column(String(150), nullable=True)
    group_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    group_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    applies_simulacro: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True
    )
    applies_simulacro_raw: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )
    training_applied_raw: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    ent_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_payload: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow
    )


class TdProgramasReference(AuthBase):
    __tablename__ = "td_programas_reference"
    __table_args__ = (
        UniqueConstraint(
            "import_id",
            "source_row_number",
            name="uq_td_programas_import_source_row",
        ),
        Index(
            "ix_td_programas_reference_import_year_sim_program",
            "import_id",
            "selected_year",
            "simulation_key",
            "program_normalized_key",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    import_id: Mapped[str] = mapped_column(
        ForeignKey("excel_imports.id", ondelete="CASCADE"), nullable=False
    )
    source_row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    selected_year: Mapped[int | None] = mapped_column(
        SmallInteger, nullable=True
    )
    simulation_name: Mapped[str] = mapped_column(String(255), nullable=False)
    simulation_key: Mapped[str] = mapped_column(String(255), nullable=False)
    program_name_raw: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    program_normalized_key: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    reading_average: Mapped[Decimal | None] = mapped_column(
        Numeric(16, 6), nullable=True
    )
    writing_average: Mapped[Decimal | None] = mapped_column(
        Numeric(16, 6), nullable=True
    )
    citizenship_average: Mapped[Decimal | None] = mapped_column(
        Numeric(16, 6), nullable=True
    )
    quantitative_average: Mapped[Decimal | None] = mapped_column(
        Numeric(16, 6), nullable=True
    )
    english_average: Mapped[Decimal | None] = mapped_column(
        Numeric(16, 6), nullable=True
    )
    global_average_from_records: Mapped[Decimal | None] = mapped_column(
        Numeric(16, 6), nullable=True
    )
    average_of_competency_averages: Mapped[Decimal | None] = mapped_column(
        Numeric(16, 6), nullable=True
    )
    source_payload: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )
