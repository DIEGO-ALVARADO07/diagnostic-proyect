import unittest
from statistics import stdev

from modules.excel.dtos.requests.dashboard import DashboardFilterQuery
from modules.excel.entities.competency import COMPETENCIES
from modules.excel.entities.dashboard import DashboardDataset, DashboardRecord
from modules.excel.services import dashboard_filters as filters_
from modules.excel.services.dashboard_metrics import calculate_metrics
from modules.excel.services.dashboard_query_service import DashboardQueryService


def make_record(
    *,
    source_row_number: int = 2,
    program_id: str = "program-a",
    program_name: str = "Programa A",
    scores: dict[str, float | None] | None = None,
    global_score: float | None = 100,
    presented: bool | None = True,
) -> DashboardRecord:
    record_scores = {competency.key: None for competency in COMPETENCIES}
    if scores is not None:
        record_scores.update(scores)
    levels = {competency.key: None for competency in COMPETENCIES}
    return DashboardRecord(
        source_row_number=source_row_number,
        document=str(source_row_number),
        name=f"Estudiante {source_row_number}",
        email=None,
        program_id=program_id,
        program_name=program_name,
        scores=record_scores,
        global_score=global_score,
        moment=None,
        test_type="SABER PRO",
        semester="SEMESTRE 7",
        year=2026,
        simulation="SIMULACRO 2026-2 MOMENTO 1",
        group="MOMENTO 1",
        presented=presented,
        levels=levels,
        ent=None,
    )


class DashboardMetricsTests(unittest.TestCase):
    def test_calculates_general_average_from_non_null_competency_scores(self) -> None:
        first_competency = COMPETENCIES[0].key
        all_hundred = {
            competency.key: 100 for competency in COMPETENCIES
        }
        one_two_hundred = {
            competency.key: None for competency in COMPETENCIES
        }
        one_two_hundred[first_competency] = 200
        no_scores = {competency.key: None for competency in COMPETENCIES}
        records = [
            make_record(source_row_number=2, scores=all_hundred),
            make_record(
                source_row_number=3,
                scores=one_two_hundred,
                global_score=40,
            ),
            make_record(
                source_row_number=4,
                scores=no_scores,
                global_score=None,
                presented=False,
            ),
        ]

        metrics = calculate_metrics(records)

        self.assertEqual(metrics["average_global"], 70)
        # 4 competencias comunes: 4 × 100 + 200 (Comunicación escrita no entra).
        self.assertAlmostEqual(metrics["average_general"], 600 / 5)
        self.assertEqual(metrics["simple_competence_average"], 112.5)
        self.assertAlmostEqual(
            metrics["general_standard_deviation"],
            stdev([100, 100, 100, 100, 200]),
        )
        self.assertEqual(metrics["presentations"], 2)
        self.assertEqual(metrics["not_presented_records"], 1)

    def test_writing_is_not_part_of_metrics(self) -> None:
        scores = {competency.key: 150 for competency in COMPETENCIES}
        scores["comunicacion_escrita"] = 0

        metrics = calculate_metrics([make_record(scores=scores)])

        self.assertNotIn("comunicacion_escrita", metrics["competencies"])
        self.assertEqual(metrics["average_general"], 150)

    def test_zero_counts_but_missing_score_does_not(self) -> None:
        # Regla igual para ESE y CORHUILA: 0 es un puntaje real (Nivel 1);
        # vacío, "-", "N"… llegan como None y no entran.
        with_zero = {competency.key: None for competency in COMPETENCIES}
        with_zero["lectura_critica"] = 0
        without_score = {competency.key: None for competency in COMPETENCIES}
        without_score["lectura_critica"] = 200

        metrics = calculate_metrics(
            [
                make_record(source_row_number=2, scores=with_zero),
                make_record(source_row_number=3, scores=without_score),
            ]
        )

        reading = metrics["competencies"]["lectura_critica"]
        self.assertEqual(reading["count"], 2)
        self.assertEqual(reading["average"], 100)
        self.assertEqual(reading["level_distribution"]["1"], 50)
        self.assertEqual(metrics["competencies"]["ingles"]["count"], 0)

    def test_general_average_is_none_when_presented_records_have_no_scores(self) -> None:
        no_scores = {competency.key: None for competency in COMPETENCIES}

        metrics = calculate_metrics([make_record(scores=no_scores)])

        self.assertIsNone(metrics["average_general"])
        self.assertIsNone(metrics["general_standard_deviation"])

    def test_overview_orders_programs_by_general_average(self) -> None:
        higher_general = make_record(
            source_row_number=2,
            program_id="program-general",
            program_name="Programa promedio general alto",
            scores={competency.key: 150 for competency in COMPETENCIES},
            global_score=90,
        )
        higher_global = make_record(
            source_row_number=3,
            program_id="program-global",
            program_name="Programa promedio global alto",
            scores={competency.key: 100 for competency in COMPETENCIES},
            global_score=100,
        )
        records = (higher_general, higher_global)
        dataset = DashboardDataset(
            import_id="test-import",
            filename="test.xlsx",
            records=records,
            records_by_program={
                "program-general": (higher_general,),
                "program-global": (higher_global,),
            },
            records_by_student={},
            program_names={
                "program-general": "Programa promedio general alto",
                "program-global": "Programa promedio global alto",
            },
            td_programs_year=None,
            td_programs_summary={},
            records_without_document=0,
        )

        overview = DashboardQueryService._overview(
            dataset,
            DashboardFilterQuery(),
            1,
            50,
            filters_.filter_options(dataset),
        )

        self.assertEqual(
            overview.programs[0].program_id,
            "program-general",
        )


if __name__ == "__main__":
    unittest.main()
