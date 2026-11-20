"""Persist Excel imports and academic dashboard results."""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0002_academic_dashboard"
down_revision: str | None = "0001_security_tables"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "excel_imports",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("file_sha256", sa.String(length=64), nullable=False),
        sa.Column("imported_by_user_id", sa.Integer(), nullable=True),
        sa.Column("imported_at", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("dataset_mode", sa.String(length=20), nullable=False),
        sa.Column("bd_gen_row_count", sa.Integer(), nullable=False),
        sa.Column("td_programas_row_count", sa.Integer(), nullable=False),
        sa.Column("inserted_count", sa.Integer(), nullable=False),
        sa.Column("rejected_count", sa.Integer(), nullable=False),
        sa.Column("td_programas_selected_year", sa.SmallInteger(), nullable=True),
        sa.Column("validation_summary", sa.JSON(), nullable=True),
        sa.Column("activated_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "status IN ('PROCESSING', 'VALIDATED', 'ACTIVE', 'HISTORICAL', 'FAILED')",
            name="ck_excel_imports_status",
        ),
        sa.CheckConstraint(
            "dataset_mode = 'SNAPSHOT'",
            name="ck_excel_imports_dataset_mode",
        ),
        sa.ForeignKeyConstraint(
            ["imported_by_user_id"],
            ["api_users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("file_sha256"),
    )
    op.create_index(
        "ix_excel_imports_status_imported_at",
        "excel_imports",
        ["status", "imported_at"],
        unique=False,
    )

    op.create_table(
        "excel_dashboard_state",
        sa.Column("id", sa.SmallInteger(), nullable=False),
        sa.Column("active_import_id", sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(
            ["active_import_id"],
            ["excel_imports.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.bulk_insert(
        sa.table(
            "excel_dashboard_state",
            sa.column("id", sa.SmallInteger()),
            sa.column("active_import_id", sa.String(length=36)),
        ),
        [{"id": 1, "active_import_id": None}],
    )

    op.create_table(
        "academic_students",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("document_key", sa.String(length=64), nullable=False),
        sa.Column("document_number", sa.String(length=80), nullable=False),
        sa.Column("first_name", sa.String(length=200), nullable=True),
        sa.Column("last_name", sa.String(length=200), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_key"),
    )

    op.create_table(
        "academic_programs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("canonical_name", sa.String(length=255), nullable=False),
        sa.Column("raw_name_key", sa.String(length=64), nullable=False),
        sa.Column("normalized_key", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("raw_name_key"),
    )
    op.create_index(
        "ix_academic_programs_normalized_key",
        "academic_programs",
        ["normalized_key"],
        unique=False,
    )

    op.create_table(
        "academic_program_aliases",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("program_id", sa.Integer(), nullable=False),
        sa.Column("raw_name", sa.String(length=255), nullable=False),
        sa.Column("normalized_name", sa.String(length=255), nullable=False),
        sa.Column("confirmed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["confirmed_by_user_id"],
            ["api_users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["program_id"],
            ["academic_programs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_academic_program_aliases_normalized_name",
        "academic_program_aliases",
        ["normalized_name"],
        unique=False,
    )

    op.create_table(
        "academic_results",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("import_id", sa.String(length=36), nullable=False),
        sa.Column("source_row_number", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=True),
        sa.Column("document_number_source", sa.String(length=80), nullable=True),
        sa.Column("first_name_source", sa.String(length=200), nullable=True),
        sa.Column("last_name_source", sa.String(length=200), nullable=True),
        sa.Column("email_source", sa.String(length=320), nullable=True),
        sa.Column("student_search_name", sa.String(length=500), nullable=True),
        sa.Column("program_id", sa.Integer(), nullable=True),
        sa.Column("program_name_raw", sa.String(length=255), nullable=False),
        sa.Column("reading_score", sa.Numeric(precision=16, scale=6), nullable=True),
        sa.Column("writing_score", sa.Numeric(precision=16, scale=6), nullable=True),
        sa.Column("citizenship_score", sa.Numeric(precision=16, scale=6), nullable=True),
        sa.Column("quantitative_score", sa.Numeric(precision=16, scale=6), nullable=True),
        sa.Column("english_score", sa.Numeric(precision=16, scale=6), nullable=True),
        sa.Column("global_raw", sa.Text(), nullable=True),
        sa.Column("global_score", sa.Numeric(precision=16, scale=6), nullable=True),
        sa.Column(
            "global_calculated_score",
            sa.Numeric(precision=16, scale=6),
            nullable=True,
        ),
        sa.Column("moment_raw", sa.String(length=100), nullable=True),
        sa.Column("assessment_type", sa.String(length=100), nullable=True),
        sa.Column("assessment_type_key", sa.String(length=120), nullable=True),
        sa.Column("semester_raw", sa.String(length=100), nullable=True),
        sa.Column("semester_key", sa.String(length=120), nullable=True),
        sa.Column("year", sa.SmallInteger(), nullable=False),
        sa.Column("simulation_name", sa.String(length=255), nullable=False),
        sa.Column("simulation_key", sa.String(length=255), nullable=False),
        sa.Column("reading_level", sa.String(length=16), nullable=True),
        sa.Column("writing_level", sa.String(length=16), nullable=True),
        sa.Column("citizenship_level", sa.String(length=16), nullable=True),
        sa.Column("quantitative_level", sa.String(length=16), nullable=True),
        sa.Column("english_level", sa.String(length=16), nullable=True),
        sa.Column("campus_raw", sa.String(length=150), nullable=True),
        sa.Column("group_name", sa.String(length=100), nullable=True),
        sa.Column("group_key", sa.String(length=120), nullable=True),
        sa.Column("applies_simulacro", sa.Boolean(), nullable=True),
        sa.Column("applies_simulacro_raw", sa.String(length=32), nullable=True),
        sa.Column("training_applied_raw", sa.Text(), nullable=True),
        sa.Column("ent_raw", sa.Text(), nullable=True),
        sa.Column("source_payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["import_id"], ["excel_imports.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["student_id"], ["academic_students.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["program_id"], ["academic_programs.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "import_id",
            "source_row_number",
            name="uq_academic_results_import_source_row",
        ),
    )
    op.create_index(
        "ix_academic_results_import_year_sim_program",
        "academic_results",
        ["import_id", "year", "simulation_key", "program_id"],
        unique=False,
    )
    op.create_index(
        "ix_academic_results_import_student_year",
        "academic_results",
        ["import_id", "student_id", "year"],
        unique=False,
    )
    op.create_index(
        "ix_academic_results_import_document",
        "academic_results",
        ["import_id", "document_number_source"],
        unique=False,
    )
    op.create_index(
        "ix_academic_results_import_presented",
        "academic_results",
        ["import_id", "applies_simulacro"],
        unique=False,
    )
    op.create_index(
        "ix_academic_results_program_year_sim",
        "academic_results",
        ["program_id", "year", "simulation_key"],
        unique=False,
    )
    op.create_index(
        "ix_academic_results_import_search",
        "academic_results",
        ["import_id", "student_search_name"],
        unique=False,
    )

    op.create_table(
        "td_programas_reference",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("import_id", sa.String(length=36), nullable=False),
        sa.Column("source_row_number", sa.Integer(), nullable=False),
        sa.Column("selected_year", sa.SmallInteger(), nullable=True),
        sa.Column("simulation_name", sa.String(length=255), nullable=False),
        sa.Column("simulation_key", sa.String(length=255), nullable=False),
        sa.Column("program_name_raw", sa.String(length=255), nullable=False),
        sa.Column("program_normalized_key", sa.String(length=255), nullable=False),
        sa.Column("reading_average", sa.Numeric(precision=16, scale=6), nullable=True),
        sa.Column("writing_average", sa.Numeric(precision=16, scale=6), nullable=True),
        sa.Column(
            "citizenship_average",
            sa.Numeric(precision=16, scale=6),
            nullable=True,
        ),
        sa.Column(
            "quantitative_average",
            sa.Numeric(precision=16, scale=6),
            nullable=True,
        ),
        sa.Column("english_average", sa.Numeric(precision=16, scale=6), nullable=True),
        sa.Column(
            "global_average_from_records",
            sa.Numeric(precision=16, scale=6),
            nullable=True,
        ),
        sa.Column(
            "average_of_competency_averages",
            sa.Numeric(precision=16, scale=6),
            nullable=True,
        ),
        sa.Column("source_payload", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(
            ["import_id"], ["excel_imports.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "import_id",
            "source_row_number",
            name="uq_td_programas_import_source_row",
        ),
    )
    op.create_index(
        "ix_td_programas_reference_import_year_sim_program",
        "td_programas_reference",
        [
            "import_id",
            "selected_year",
            "simulation_key",
            "program_normalized_key",
        ],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_td_programas_reference_import_year_sim_program",
        table_name="td_programas_reference",
    )
    op.drop_table("td_programas_reference")

    op.drop_index(
        "ix_academic_results_import_search",
        table_name="academic_results",
    )
    op.drop_index(
        "ix_academic_results_program_year_sim",
        table_name="academic_results",
    )
    op.drop_index(
        "ix_academic_results_import_presented",
        table_name="academic_results",
    )
    op.drop_index(
        "ix_academic_results_import_document",
        table_name="academic_results",
    )
    op.drop_index(
        "ix_academic_results_import_student_year",
        table_name="academic_results",
    )
    op.drop_index(
        "ix_academic_results_import_year_sim_program",
        table_name="academic_results",
    )
    op.drop_table("academic_results")

    op.drop_index(
        "ix_academic_program_aliases_normalized_name",
        table_name="academic_program_aliases",
    )
    op.drop_table("academic_program_aliases")

    op.drop_index(
        "ix_academic_programs_normalized_key",
        table_name="academic_programs",
    )
    op.drop_table("academic_programs")
    op.drop_table("academic_students")

    op.drop_index(
        "ix_excel_imports_status_imported_at",
        table_name="excel_imports",
    )
    op.drop_table("excel_dashboard_state")
    op.drop_table("excel_imports")
