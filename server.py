"""Compatibility ASGI entrypoint.

New tooling should use ``course_agent.main:app``. Keeping this module lets
existing local commands continue to run during the package-layout migration.
"""

from course_agent.main import app

__all__ = ["app"]
