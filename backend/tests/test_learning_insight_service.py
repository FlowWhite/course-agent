import unittest

from course_agent.learning_insight_service import _base_risk_score, _risk_level_from_score
from course_agent.models import RiskLevel, TaskPriority


class DeadlineRiskTests(unittest.TestCase):
    def test_overdue_high_priority_task_is_critical(self):
        score, reasons = _base_risk_score(
            days_remaining=-2,
            priority=TaskPriority.HIGH.value,
        )

        self.assertGreaterEqual(score, 12)
        self.assertIn("已逾期 2 天", reasons)
        self.assertIn("任务优先级为高", reasons)
        self.assertEqual(_risk_level_from_score(score), RiskLevel.CRITICAL)

    def test_weekly_low_priority_task_is_low_risk(self):
        score, reasons = _base_risk_score(
            days_remaining=10,
            priority=TaskPriority.LOW.value,
        )

        self.assertEqual(score, 0)
        self.assertEqual(reasons, ["当前截止日期和优先级处于可控范围"])
        self.assertEqual(_risk_level_from_score(score), RiskLevel.LOW)

    def test_risk_boundaries_are_stable(self):
        self.assertEqual(_risk_level_from_score(4), RiskLevel.MEDIUM)
        self.assertEqual(_risk_level_from_score(7), RiskLevel.HIGH)
        self.assertEqual(_risk_level_from_score(10), RiskLevel.CRITICAL)


if __name__ == "__main__":
    unittest.main()
