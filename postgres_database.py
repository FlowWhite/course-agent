import os
from pathlib import Path

import psycopg


PROJECT_DIR = Path(__file__).parent
SCHEMA_PATH = PROJECT_DIR / "postgres" / "init.sql"


def get_postgres_connection():
    """创建 PostgreSQL 数据库连接。"""
    return psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )


def ensure_application_schema() -> None:
    """Apply the additive PostgreSQL schema on startup.

    Docker's init directory only runs for a brand-new volume. Running this
    idempotent bootstrap also upgrades an existing Phase 4 database without
    requiring users to erase their PostgreSQL volume.
    """
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")

    with get_postgres_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(schema_sql)
