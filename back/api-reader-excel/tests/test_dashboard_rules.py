"""Reglas de datos de la fase 5: identidad de programas, semestres y calidad."""

import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from core.orm import Base
from modules.excel.dtos.requests.read_workbook import ReadWorkbookRequest
from modules.excel.entities.academic import (
    AcademicProgram,
    AcademicProgramAlias,
    AcademicResult,
    DashboardState,
)
from modules.excel.services.dashboard_data_quality import assess_data_quality
from modules.excel.services.dashboard_normalizer import canonical_semester
from modules.excel.services.dashboard_service import DashboardService
from modules.excel.services.program_catalog import choose_program_names
from modules.security.entities import Account
from modules.security.entities.role import Role
from tests.test_dashboard import make_dashboard_workbook


class ProgramNameRuleTests(unittest.TestCase):
    def test_td_programas_name_wins(self) -> None:
        names = choose_program_names(
            ["INGENIERIA DE SISTEMAS"] * 5 + ["Ingenieria de sistemas"],
            ["INGENIERÍA DE SISTEMAS"],
        )
        self.assertEqual(
            names, {"ingenieria de sistemas": "INGENIERÍA DE SISTEMAS"}
        )

    def test_without_td_prefers_accents_then_frequency(self) -> None:
        names = choose_program_names(
            ["ADMINISTRACION COMERCIAL"] * 9
            + ["ADMINISTRACIÓN COMERCIAL"]
            + ["MEDICINA", "Medicina", "Medicina"]
        )
        self.assertEqual(
            names,
            {
                "administracion comercial": "ADMINISTRACIÓN COMERCIAL",
                "medicina": "Medicina",
            },
        )

    def test_spaces_and_case_do_not_create_new_programs(self) -> None:
        names = choose_program_names([" Programa  A ", "PROGRAMA A"])
        self.assertEqual(list(names), ["programa a"])


class SemesterRuleTests(unittest.TestCase):
    def test_bare_numbers_become_semester_labels(self) -> None:
        self.assertEqual(canonical_semester("4"), "SEMESTRE 4")
        self.assertEqual(canonical_semester(7.0), "SEMESTRE 7")
        self.assertEqual(canonical_semester(" 10 "), "SEMESTRE 10")

    def test_other_values_are_kept(self) -> None:
        self.assertEqual(canonical_semester("SEMESTRE 4"), "SEMESTRE 4")
        self.assertEqual(canonical_semester("Electiva"), "Electiva")
        self.assertEqual(canonical_semester("0"), "0")
        self.assertIsNone(canonical_semester(None))
        self.assertIsNone(canonical_semester("  "))


class DataQualityTests(unittest.TestCase):
    def test_reports_codes_inconsistent_and_unknown_levels(self) -> None:
        rows = [
            {"comunicación escrita": "N", "n: comunicación escrita": "N"},
            {"comunicación escrita": "N", "n: comunicación escrita": "4"},
            {"comunicación escrita": "P", "n: comunicación escrita": "P"},
            {"comunicación escrita": 150, "n: comunicación escrita": "3"},
            {"inglés": None, "n: inglés": "N/A"},
            {"inglés": 180, "n: inglés": "false"},
        ]

        report = assess_data_quality(rows)

        self.assertEqual(
            report["score_codes"], {"comunicacion_escrita": {"N": 2, "P": 1}}
        )
        self.assertEqual(
            report["levels_without_numeric_score"], {"comunicacion_escrita": 1}
        )
        self.assertEqual(report["unknown_levels"], {"ingles": {"false": 1}})

    def test_clean_rows_report_nothing(self) -> None:
        report = assess_data_quality(
            [
                {
                    "lectura crítica": 150,
                    "n: lectura crítica": "2",
                    "sim": "SIMULACRO 2026-1 MOMENTO 3",
                    "grupo": "MOMENTO 3",
                    "año": 2026,
                    "usuario": "101",
                    "dirección de correo": "ana@corhuila.edu.co",
                }
            ]
        )
        self.assertEqual(
            report,
            {
                "score_codes": {},
                "levels_without_numeric_score": {},
                "unknown_levels": {},
                "source_level_mismatches": {},
                "period_moment": {
                    "rows_without_period": 0,
                    "rows_without_moment": 0,
                    "moment_group_mismatches": 0,
                    "period_year_mismatches": 0,
                },
                "identity": {
                    "rows_without_email": 0,
                    "emails_with_multiple_documents": 0,
                    "documents_with_multiple_emails": 0,
                    "names_with_multiple_documents": 0,
                    "documents_with_multiple_programs": 0,
                },
            },
        )

    def test_reports_period_and_moment_problems(self) -> None:
        report = assess_data_quality(
            [
                # SIM sin periodo; el momento sale de GRUPO.
                {"sim": "SIMULACRO MOMENTO 1", "grupo": "MOMENTO 1", "año": 2025},
                # Sin momento en SIM ni en GRUPO.
                {"sim": "SIMULACRO 2025-2", "grupo": "A", "año": 2025},
                # SIM dice momento 2 y GRUPO momento 3.
                {"sim": "SIMULACRO 2026-1 MOMENTO 2", "grupo": "MOMENTO 3", "año": 2026},
                # El periodo es de 2026 pero AÑO dice 2025.
                {"sim": "SIMULACRO 2026-1 MOMENTO 1", "grupo": "MOMENTO 1", "año": 2025},
            ]
        )
        self.assertEqual(
            report["period_moment"],
            {
                "rows_without_period": 1,
                "rows_without_moment": 1,
                "moment_group_mismatches": 1,
                "period_year_mismatches": 1,
            },
        )

    def test_reports_source_levels_that_differ_from_common_scale(self) -> None:
        report = assess_data_quality(
            [
                # 125 es Nivel 1 en la escala común; el Excel dice 2.
                {"lectura crítica": 125, "n: lectura crítica": "2"},
                # 160 es B1 en la escala común; el Excel dice A2.
                {"inglés": 160, "n: inglés": "A2"},
                # Coincide: no se reporta.
                {"razonamiento cuantitativo": 199, "n: razonamiento cuantitativo": "4"},
                # Comunicación escrita no es comparable: no se reporta.
                {"comunicación escrita": 100, "n: comunicación escrita": "3"},
            ]
        )
        self.assertEqual(
            report["source_level_mismatches"],
            {"lectura_critica": 1, "ingles": 1},
        )


class DashboardRulesIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.admin = Account(
            id=1,
            username="admin",
            email="admin@example.com",
            full_name="Admin",
            password_hash="unused",
            role=Role.SUPERADMIN.value,
            is_active=True,
        )
        self.db.add_all([self.admin, DashboardState(id=1)])
        self.db.commit()
        self.service = DashboardService()

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def _import(self, **workbook_options: object):
        return self.service.import_workbook(
            ReadWorkbookRequest(
                filename="rules.xlsx",
                content=make_dashboard_workbook(**workbook_options),
            ),
            self.admin,
            self.db,
        )

    def test_program_variants_share_one_program_with_aliases(self) -> None:
        response = self._import()

        programs = list(self.db.scalars(select(AcademicProgram)))
        self.assertEqual(len(programs), 1)
        self.assertEqual(programs[0].canonical_name, "PROGRAMA A")
        self.assertEqual(
            sorted(
                alias.raw_name
                for alias in self.db.scalars(select(AcademicProgramAlias))
            ),
            ["PROGRAMA A", "PROGRAMA Á", "Programa A"],
        )
        self.assertEqual(response.overview.kpis.programs, 1)

    def test_reimport_reuses_program_without_duplicate_aliases(self) -> None:
        self._import()
        self._import(global_score=91)

        self.assertEqual(len(list(self.db.scalars(select(AcademicProgram)))), 1)
        self.assertEqual(
            len(list(self.db.scalars(select(AcademicProgramAlias)))), 3
        )

    def test_numeric_semester_is_merged_with_its_label(self) -> None:
        # El semestre ya no es un filtro: solo se muestra en el historial.
        response = self._import(first_semester=7)

        self.assertNotIn("semesters", response.filters.model_dump())
        self.assertEqual(
            self.db.scalar(
                select(AcademicResult.semester_key).where(
                    AcademicResult.import_id == response.import_id,
                    AcademicResult.source_row_number == 2,
                )
            ),
            "semestre 7",
        )

    def test_import_response_includes_data_quality(self) -> None:
        response = self._import()

        quality = response.source_audit.data_quality
        self.assertIsNotNone(quality)
        # El segundo intento de Ana tiene "N" en Comunicación escrita.
        self.assertEqual(quality.score_codes, {"comunicacion_escrita": {"N": 1}})


if __name__ == "__main__":
    unittest.main()
