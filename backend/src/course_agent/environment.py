"""Small, dependency-free helpers for local project configuration."""

from __future__ import annotations

import os

from .paths import PROJECT_ROOT


def load_project_env() -> None:
    """Load project-root ``.env`` values without overriding process settings."""
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", maxsplit=1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)
