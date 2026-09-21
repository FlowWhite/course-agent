import unittest

from course_agent.agent_runtime import (
    add_current_agent_document_sources,
    get_current_agent_document_sources,
    reset_current_agent_course_id,
    reset_current_agent_document_sources,
    reset_current_agent_user_id,
    set_current_agent_course_id,
    set_current_agent_document_sources,
    set_current_agent_user_id,
)
from course_agent.models import PlanSource
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

    def test_document_sources_are_scoped_to_one_agent_request(self):
        source_token = set_current_agent_document_sources()
        source = PlanSource(
            chunk_id="chunk-1",
            chunk_index=0,
            file_id="file-1",
            file_name="syllabus.md",
            page=None,
            excerpt="课程要求摘录",
        )
        try:
            add_current_agent_document_sources([source, source])
            self.assertEqual(get_current_agent_document_sources(), [source])
        finally:
            reset_current_agent_document_sources(source_token)

        self.assertEqual(get_current_agent_document_sources(), [])


if __name__ == "__main__":
    unittest.main()
