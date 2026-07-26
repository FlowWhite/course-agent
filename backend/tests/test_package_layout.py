"""Regression checks for the packaged backend entrypoints."""

import unittest

from course_agent.main import app
from course_agent.paths import POSTGRES_SCHEMA_PATH, PROJECT_ROOT


class PackageLayoutTests(unittest.TestCase):
    def test_packaged_application_uses_project_resources(self):
        self.assertEqual(app.title, "Course Agent API")
        self.assertTrue((PROJECT_ROOT / "pyproject.toml").exists())
        self.assertTrue(POSTGRES_SCHEMA_PATH.exists())

    def test_legacy_asgi_entrypoint_remains_compatible(self):
        from server import app as legacy_app

        self.assertIs(legacy_app, app)


if __name__ == "__main__":
    unittest.main()
