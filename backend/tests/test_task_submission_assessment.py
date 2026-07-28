"""Regression coverage for bounded Agent assignment-review output."""

import unittest

from course_agent.agent_runtime import _validate_task_submission_assessment


class TaskSubmissionAssessmentValidationTests(unittest.TestCase):
    def test_valid_assessment_is_accepted(self):
        assessment = _validate_task_submission_assessment(
            {
                "verdict": "needs_revision",
                "summary": "作业已说明抓包步骤，但未展示分析结论。",
                "requirement_checks": [
                    {
                        "requirement": "分析 HTTP 请求头字段",
                        "status": "partially_met",
                        "evidence": "正文列出了 Host 和 User-Agent。",
                        "recommendation": "补充每个字段的作用与抓包截图。",
                    }
                ],
                "strengths": ["已给出抓包流程。"],
                "improvements": ["补充字段分析结论。"],
                "limitations": [],
            }
        )

        self.assertEqual(assessment.verdict.value, "needs_revision")
        self.assertEqual(len(assessment.requirement_checks), 1)

    def test_malformed_assessment_returns_safe_error(self):
        with self.assertRaisesRegex(ValueError, "作业评估结果格式无效"):
            _validate_task_submission_assessment(
                {
                    "verdict": "needs_revision",
                    "summary": "缺少逐项检查。",
                    "requirement_checks": [],
                }
            )


if __name__ == "__main__":
    unittest.main()
