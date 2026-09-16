"""Unit tests for the prompt-ready summary."""
import unittest
from app.summary import build_summary


class SummaryTest(unittest.TestCase):
    def test_summary_includes_core_fields(self) -> None:
        result = build_summary([
            {"date": "2024-01-01", "value": 2},
            {"date": "2024-01-02", "value": 4},
            {"date": "2024-01-03", "value": 6},
        ])
        self.assertEqual(result["count"], 3)
        self.assertEqual(result["metrics"]["average"], 4)
        self.assertEqual(result["extremes"]["max_date"], "2024-01-03")

    def test_empty_summary_is_safe(self) -> None:
        self.assertEqual(build_summary([])["count"], 0)
