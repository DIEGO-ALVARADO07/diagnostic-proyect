import unittest

from modules.excel.entities.assessment import (
    Source,
    active_slot,
    parse_moment,
    parse_period,
    resolve_ese_moment,
    semester_range,
)


class PeriodAndMomentTests(unittest.TestCase):
    def test_period_comes_from_sim(self) -> None:
        self.assertEqual(parse_period("SIMULACRO 2026-1 MOMENTO 3"), "2026-1")
        self.assertEqual(parse_period("simulacro 2025 - 2 momento 1"), "2025-2")
        self.assertIsNone(parse_period("SIMULACRO MOMENTO 1"))
        self.assertIsNone(parse_period("SIMULACRO 2026-3"))
        self.assertIsNone(parse_period(None))

    def test_moment_is_one_to_four(self) -> None:
        self.assertEqual(parse_moment("MOMENTO 3"), 3)
        self.assertEqual(parse_moment("simulacro 2026-1 momento 1"), 1)
        # Momento 4: histórico de 2024 (semestres 8–10).
        self.assertEqual(parse_moment("SIMULACRO 2024-1 MOMENTO 4"), 4)
        self.assertIsNone(parse_moment("MOMENTO 5"))
        self.assertIsNone(parse_moment("GRUPO A"))

    def test_sim_wins_and_group_is_the_fallback(self) -> None:
        self.assertEqual(
            resolve_ese_moment("SIMULACRO 2026-1 MOMENTO 2", "MOMENTO 3"), 2
        )
        self.assertEqual(resolve_ese_moment("SIMULACRO 2026-1", "MOMENTO 3"), 3)
        self.assertIsNone(resolve_ese_moment("SIMULACRO 2026-1", None))

    def test_semester_range_follows_the_moment(self) -> None:
        labels = {
            moment: semester_range(Source.ESE, moment).label
            for moment in (1, 2, 3)
        }
        self.assertEqual(labels, {1: "1–3", 2: "4–6", 3: "7 en adelante"})
        self.assertEqual(semester_range(Source.ESE, 4).label, "8–10")
        self.assertEqual(semester_range(Source.CORHUILA, None).label, "5–6")
        self.assertIsNone(semester_range(Source.ESE, None))

    def test_ese_has_one_slot_and_corhuila_one_per_period(self) -> None:
        self.assertEqual(active_slot(Source.ESE, None), "ESE")
        self.assertEqual(active_slot(Source.ESE, "2026-1"), "ESE")
        self.assertEqual(
            active_slot(Source.CORHUILA, "2026-2"), "CORHUILA:2026-2"
        )
        with self.assertRaises(ValueError):
            active_slot(Source.CORHUILA, None)


if __name__ == "__main__":
    unittest.main()
