import os
import sqlite3
from pathlib import Path

import psycopg


SQLITE_PATH = (
    Path(__file__).parent
    / "data"
    / "course.db"
)


def postgres_connection():
    return psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )


def legacy_owner_user_id() -> int:
    raw_user_id = os.getenv("LEGACY_OWNER_USER_ID", "").strip()
    if not raw_user_id:
        raise RuntimeError(
            "迁移前必须设置 LEGACY_OWNER_USER_ID，明确指定旧课程和任务的归属用户。"
        )
    try:
        user_id = int(raw_user_id)
    except ValueError as exc:
        raise RuntimeError("LEGACY_OWNER_USER_ID 必须是正整数。") from exc
    if user_id <= 0:
        raise RuntimeError("LEGACY_OWNER_USER_ID 必须是正整数。")
    return user_id


def main():
    owner_user_id = legacy_owner_user_id()
    if not SQLITE_PATH.exists():
        raise FileNotFoundError(
            f"找不到 SQLite 数据库：{SQLITE_PATH}"
        )

    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row

    try:
        courses = sqlite_conn.execute(
            """
            SELECT id, name, teacher
            FROM courses
            ORDER BY id
            """
        ).fetchall()

        tasks = sqlite_conn.execute(
            """
            SELECT
                id,
                course_id,
                title,
                deadline,
                status,
                priority,
                description
            FROM tasks
            ORDER BY id
            """
        ).fetchall()
    finally:
        sqlite_conn.close()

    with postgres_connection() as postgres_conn:
        with postgres_conn.cursor() as cursor:
            for course in courses:
                cursor.execute(
                    """
                    INSERT INTO courses (
                        id,
                        user_id,
                        name,
                        teacher
                    )
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (id)
                    DO UPDATE SET
                        user_id = EXCLUDED.user_id,
                        name = EXCLUDED.name,
                        teacher = EXCLUDED.teacher
                    """,
                    (
                        course["id"],
                        owner_user_id,
                        course["name"],
                        course["teacher"],
                    ),
                )

            for task in tasks:
                cursor.execute(
                    """
                    INSERT INTO tasks (
                        id,
                        user_id,
                        course_id,
                        title,
                        deadline,
                        status,
                        priority,
                        description
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id)
                    DO UPDATE SET
                        user_id = EXCLUDED.user_id,
                        course_id = EXCLUDED.course_id,
                        title = EXCLUDED.title,
                        deadline = EXCLUDED.deadline,
                        status = EXCLUDED.status,
                        priority = EXCLUDED.priority,
                        description = EXCLUDED.description
                    """,
                    (
                        task["id"],
                        owner_user_id,
                        task["course_id"],
                        task["title"],
                        task["deadline"],
                        task["status"],
                        task["priority"],
                        task["description"],
                    ),
                )

    print("MIGRATION OK")
    print(f"COURSES: {len(courses)}")
    print(f"TASKS: {len(tasks)}")


if __name__ == "__main__":
    main()
