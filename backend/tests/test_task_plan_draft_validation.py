import unittest

from course_agent.agent_runtime import _validate_generated_task_plan_draft


class TaskPlanDraftValidationTests(unittest.TestCase):
    def test_short_model_estimate_is_raised_to_minimum(self):
        draft = _validate_generated_task_plan_draft(
            {
                "goal": "完成协议分析实验",
                "prerequisite_knowledge": [],
                "steps": [
                    {
                        "title": "整理抓包文件",
                        "description": "保存并标注关键报文。",
                        "estimated_minutes": 3,
                        "deliverable": "标注后的抓包文件",
                        "acceptance_criteria": "可定位一组请求和响应。",
                    }
                ],
            }
        )

        self.assertEqual(draft.steps[0].estimated_minutes, 5)

    def test_large_model_estimate_is_capped_at_maximum(self):
        draft = _validate_generated_task_plan_draft(
            {
                "goal": "完成协议分析实验",
                "prerequisite_knowledge": [],
                "steps": [
                    {
                        "title": "整理实验报告",
                        "description": "汇总步骤、截图和结论。",
                        "estimated_minutes": "600",
                        "deliverable": "实验报告初稿",
                        "acceptance_criteria": "包含环境、分析与结论。",
                    }
                ],
            }
        )

        self.assertEqual(draft.steps[0].estimated_minutes, 480)

    def test_other_invalid_plan_fields_still_return_safe_error(self):
        with self.assertRaisesRegex(ValueError, "学习计划草案格式无效"):
            _validate_generated_task_plan_draft({"goal": "缺少步骤"})


if __name__ == "__main__":
    unittest.main()
