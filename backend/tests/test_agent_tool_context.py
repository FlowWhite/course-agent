import unittest

from course_agent.agent_runtime import (
    reset_current_agent_course_id,
    reset_current_agent_user_id,
    set_current_agent_course_id,
    set_current_agent_user_id,
)
from course_agent.tools import (
    _current_agent_course_id,
    _current_document_user_id,
)


class AgentToolContextTests(unittest.TestCase):
    def test_tool_helpers_read_the_package_scoped_agent_context(self):
        user_token = set_current_agent_user_id(42)
        course_token = set_current_agent_course_id("cn-demo-2026")
        try:
            self.assertEqual(_current_document_user_id(), 42)
            self.assertEqual(_current_agent_course_id(), "cn-demo-2026")
        finally:
            reset_current_agent_course_id(course_token)
            reset_current_agent_user_id(user_token)


if __name__ == "__main__":
    unittest.main()
