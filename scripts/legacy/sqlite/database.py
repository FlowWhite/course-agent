import sqlite3
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = PROJECT_ROOT / "data" / "course.db"
BACKUP_DIR = PROJECT_ROOT / "data" / "backups"

def get_connection():
    return sqlite3.connect(DB_PATH)
def backup_database() -> Path:
    """创建当前课程数据库的 SQLite 一致性备份。"""
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"找不到业务数据库：{DB_PATH}"
        )

    BACKUP_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d-%H%M%S-%f"
    )

    backup_path = (
        BACKUP_DIR
        / f"course-{timestamp}.db"
    )

    source_conn = sqlite3.connect(DB_PATH)
    target_conn = None

    try:
        target_conn = sqlite3.connect(backup_path)
        source_conn.backup(target_conn)
        return backup_path

    finally:
        if target_conn is not None:
            target_conn.close()

        source_conn.close()

def init_database():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS courses(
            id TEXT PRIMARY KEY,
            name TEXT,
            teacher TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks(
            id TEXT PRIMARY KEY,
            course_id TEXT,
            title TEXT,
            deadline TEXT,
            status TEXT,
            priority TEXT,
            description TEXT
        )
        """
    )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_database()
    print("数据库初始化完成")
