import json
from pathlib import Path

from .database import get_connection, init_database


PROJECT_ROOT = Path(__file__).resolve().parents[3]
JSON_PATH = PROJECT_ROOT / "data" / "tasks.json"


def import_data() -> None:
    if not JSON_PATH.exists():
        raise FileNotFoundError(f"找不到数据文件：{JSON_PATH}")

    with JSON_PATH.open("r", encoding="utf-8") as file:
        data = json.load(file)

    courses = data.get("courses", [])
    tasks = data.get("tasks", [])

    init_database()

    conn = get_connection()

    try:
        cursor = conn.cursor()

        for course in courses:
            cursor.execute(
                """
                INSERT OR REPLACE INTO courses(
                    id,
                    name,
                    teacher
                )
                VALUES (?, ?, ?)
                """,
                (
                    course["id"],
                    course["name"],
                    course["teacher"],
                ),
            )

        for task in tasks:
            cursor.execute(
                """
                INSERT OR REPLACE INTO tasks(
                    id,
                    course_id,
                    title,
                    deadline,
                    status,
                    priority,
                    description
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task["id"],
                    task["course_id"],
                    task["title"],
                    task["deadline"],
                    task["status"],
                    task["priority"],
                    task["description"],
                ),
            )

        conn.commit()

        print(f"导入课程：{len(courses)} 条")
        print(f"导入任务：{len(tasks)} 条")

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    import_data()
