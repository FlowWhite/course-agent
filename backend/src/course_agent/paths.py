"""Stable filesystem locations for the packaged backend."""

import os
from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parent


def _resolve_project_root() -> Path:
    configured_root = os.getenv("COURSE_AGENT_PROJECT_ROOT")
    if configured_root:
        return Path(configured_root).resolve()

    source_root = PACKAGE_DIR.parents[2]
    if (source_root / "pyproject.toml").exists():
        return source_root

    return Path.cwd().resolve()


PROJECT_ROOT = _resolve_project_root()
DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = PROJECT_ROOT / "logs"
BACKUP_DIR = DATA_DIR / "backups"
UPLOAD_ROOT = DATA_DIR / "uploads"
POSTGRES_SCHEMA_PATH = PROJECT_ROOT / "postgres" / "init.sql"
