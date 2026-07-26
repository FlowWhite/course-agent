"""Regression checks for public API routes after router modularization."""

import unittest

from fastapi.testclient import TestClient

from course_agent.main import app


class ApiRouteContractTests(unittest.TestCase):
    def test_public_paths_and_methods_are_preserved(self):
        expected_requests = [
            ("GET", "/health"),
            ("POST", "/api/v1/auth/login"),
            ("POST", "/api/v1/auth/register"),
            ("GET", "/api/v1/files"),
            ("POST", "/api/v1/files"),
            ("GET", "/api/v1/files/test-file"),
            ("DELETE", "/api/v1/files/test-file"),
            ("GET", "/api/v1/courses"),
            ("GET", "/api/v1/tasks"),
            ("POST", "/api/v1/tasks"),
            ("GET", "/api/v1/tasks/test-task"),
            ("PATCH", "/api/v1/tasks/test-task"),
            ("DELETE", "/api/v1/tasks/test-task"),
            ("PATCH", "/api/v1/tasks/test-task/status"),
            ("POST", "/api/v1/tasks/test-task/plan"),
            ("GET", "/api/v1/plans"),
            ("GET", "/api/v1/plans/test-plan"),
            ("POST", "/api/v1/plans/test-plan/confirm"),
            ("POST", "/api/v1/plans/test-plan/pause"),
            ("POST", "/api/v1/plans/test-plan/resume"),
            ("POST", "/api/v1/plans/test-plan/steps/test-step/complete"),
            ("GET", "/api/v1/insights/risks"),
            ("POST", "/api/v1/chat"),
        ]
        client = TestClient(app)
        for method, path in expected_requests:
            with self.subTest(method=method, path=path):
                response = client.request(method, path)
                self.assertNotIn(response.status_code, {404, 405})


if __name__ == "__main__":
    unittest.main()
