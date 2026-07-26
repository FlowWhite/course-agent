import json
from datetime import datetime
from pathlib import Path
from typing import Any

from psycopg.rows import dict_row

from .models import (
    CourseSummary,
    TaskCreate,
    TaskRecord,
    TaskStatusUpdate,
    TaskUpdate,
)
from .paths import BACKUP_DIR
from .postgres_database import get_postgres_connection


def _get_connection():
    conn = get_postgres_connection()
    conn.row_factory = dict_row
    return conn
def backup_postgres_data() -> Path:
    BACKUP_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d-%H%M%S-%f"
    )

    backup_path = (
        BACKUP_DIR
        / f"postgres-{timestamp}.json"
    )

    with _get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, user_id, name, teacher
                FROM courses
                ORDER BY id
                """
            )
            courses = cursor.fetchall()

            cursor.execute(
                """
                SELECT
                    id,
                    user_id,
                    course_id,
                    title,
                    deadline,
                    status,
                    priority,
                    description
                FROM tasks
                ORDER BY id
                """
            )
            tasks = cursor.fetchall()

    payload = {
        "created_at": datetime.now().isoformat(),
        "courses": courses,
        "tasks": tasks,
    }

    backup_path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    return backup_path

def list_courses_data(user_id: int) -> list[CourseSummary]:
    with _get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    c.id,
                    c.name,
                    c.teacher,
                    COUNT(t.id) AS todo_count
                FROM courses AS c
                LEFT JOIN tasks AS t
                    ON c.id = t.course_id
                    AND t.user_id = c.user_id
                    AND t.status = 'todo'
                WHERE c.user_id = %s
                GROUP BY
                    c.id,
                    c.name,
                    c.teacher
                ORDER BY c.name
                """,
                (user_id,),
            )

            rows = cursor.fetchall()

    return [
        CourseSummary.model_validate(row)
        for row in rows
    ]


def list_tasks_data(
    user_id: int,
    course: str,
    status: str,
) -> list[TaskRecord]:
    normalized_course = course.strip()
    normalized_status = status.strip().lower()

    if normalized_status not in {"all", "todo", "done"}:
        raise ValueError("status 只能是 all、todo 或 done。")

    conditions: list[str] = ["t.user_id = %s"]
    parameters: list[Any] = [user_id]

    if normalized_course:
        conditions.append(
            "(c.id = %s OR c.name LIKE %s)"
        )
        parameters.extend(
            [
                normalized_course,
                f"%{normalized_course}%",
            ]
        )

    if normalized_status != "all":
        conditions.append("t.status = %s")
        parameters.append(normalized_status)

    where_clause = ""

    if conditions:
        where_clause = (
            "WHERE " + " AND ".join(conditions)
        )

    with _get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT
                    t.id,
                    t.course_id,
                    c.name AS course_name,
                    t.title,
                    t.deadline,
                    t.status,
                    t.priority,
                    t.description
                FROM tasks AS t
                JOIN courses AS c
                    ON t.course_id = c.id
                    AND t.user_id = c.user_id
                {where_clause}
                ORDER BY t.deadline ASC
                """,
                parameters,
            )

            rows = cursor.fetchall()

    return [
        TaskRecord.model_validate(row)
        for row in rows
    ]


def get_task_detail_data(
    user_id: int,
    task_id: str,
) -> TaskRecord | None:
    normalized_task_id = task_id.strip()

    with _get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    t.id,
                    t.course_id,
                    c.name AS course_name,
                    t.title,
                    t.deadline,
                    t.status,
                    t.priority,
                    t.description
                FROM tasks AS t
                JOIN courses AS c
                    ON t.course_id = c.id
                    AND t.user_id = c.user_id
                WHERE t.user_id = %s AND t.id = %s
                """,
                (user_id, normalized_task_id),
            )

            row = cursor.fetchone()

    if row is None:
        return None

    return TaskRecord.model_validate(row)
def _resolve_course_id(
    cursor,
    user_id: int,
    course: str,
) -> str:
    normalized_course = course.strip()

    if not normalized_course:
        raise ValueError("课程不能为空。")

    cursor.execute(
        """
        SELECT id, name
        FROM courses
        WHERE user_id = %s
          AND (id = %s OR name = %s)
        """,
        (
            user_id,
            normalized_course,
            normalized_course,
        ),
    )

    rows = cursor.fetchall()

    if not rows:
        raise ValueError(
            f"没有找到课程：{normalized_course}"
        )

    if len(rows) > 1:
        raise ValueError(
            "课程名称不唯一，请改用课程 ID。"
        )

    return str(rows[0]["id"])


def _fetch_task_by_cursor(
    cursor,
    user_id: int,
    task_id: str,
) -> TaskRecord | None:
    cursor.execute(
        """
        SELECT
            t.id,
            t.course_id,
            c.name AS course_name,
            t.title,
            t.deadline,
            t.status,
            t.priority,
            t.description
        FROM tasks AS t
        JOIN courses AS c
            ON t.course_id = c.id
            AND t.user_id = c.user_id
        WHERE t.user_id = %s AND t.id = %s
        """,
        (user_id, task_id),
    )

    row = cursor.fetchone()

    if row is None:
        return None

    return TaskRecord.model_validate(row)


def create_task_data(
    user_id: int,
    task_id: str,
    course: str,
    title: str,
    deadline: str,
    priority: str,
    description: str,
) -> TaskRecord:
    with _get_connection() as conn:
        with conn.cursor() as cursor:
            course_id = _resolve_course_id(
                cursor,
                user_id,
                course,
            )

            task = TaskCreate(
                id=task_id,
                course_id=course_id,
                title=title,
                deadline=deadline,
                priority=priority,
                description=description,
            )

            cursor.execute(
                "SELECT 1 FROM tasks WHERE id = %s",
                (task.id,),
            )

            if cursor.fetchone() is not None:
                raise ValueError(
                    f"任务 ID 已存在：{task.id}"
                )

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
                """,
                (
                    task.id,
                    user_id,
                    task.course_id,
                    task.title,
                    task.deadline,
                    task.status.value,
                    task.priority.value,
                    task.description,
                ),
            )

            result = _fetch_task_by_cursor(
                cursor,
                user_id,
                task.id,
            )

            if result is None:
                raise RuntimeError(
                    "任务已经写入，但读取不到新增任务。"
                )

            return result
def update_task_data(
    user_id: int,
    task_id: str,
    title: str | None = None,
    deadline: str | None = None,
    priority: str | None = None,
    description: str | None = None,
) -> TaskRecord:
    normalized_task_id = task_id.strip()

    if not normalized_task_id:
        raise ValueError("任务 ID 不能为空。")

    update = TaskUpdate(
        title=title,
        deadline=deadline,
        priority=priority,
        description=description,
    )

    changes = update.model_dump(
        exclude_none=True,
        mode="json",
    )

    field_names = list(changes.keys())

    set_clause = ", ".join(
        f"{field_name} = %s"
        for field_name in field_names
    )

    values = [
        changes[field_name]
        for field_name in field_names
    ]

    values.extend([user_id, normalized_task_id])

    with _get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM tasks WHERE user_id = %s AND id = %s",
                (user_id, normalized_task_id),
            )

            if cursor.fetchone() is None:
                raise ValueError(
                    f"没有找到任务：{normalized_task_id}"
                )

            cursor.execute(
                f"""
                UPDATE tasks
                SET {set_clause}
                WHERE user_id = %s AND id = %s
                """,
                values,
            )

            result = _fetch_task_by_cursor(
                cursor,
                user_id,
                normalized_task_id,
            )

            if result is None:
                raise RuntimeError(
                    "任务已经更新，但读取不到更新后的任务。"
                )

            return result
def update_task_status_data(
    user_id: int,
    task_id: str,
    status: str,
) -> TaskRecord:
    normalized_task_id = task_id.strip()

    if not normalized_task_id:
        raise ValueError("任务 ID 不能为空。")

    status_update = TaskStatusUpdate(
        status=status.strip().lower(),
    )

    with _get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM tasks WHERE user_id = %s AND id = %s",
                (user_id, normalized_task_id),
            )

            if cursor.fetchone() is None:
                raise ValueError(
                    f"没有找到任务：{normalized_task_id}"
                )

            cursor.execute(
                """
                UPDATE tasks
                SET status = %s
                WHERE user_id = %s AND id = %s
                """,
                (
                    status_update.status.value,
                    user_id,
                    normalized_task_id,
                ),
            )

            result = _fetch_task_by_cursor(
                cursor,
                user_id,
                normalized_task_id,
            )

            if result is None:
                raise RuntimeError(
                    "任务状态已经更新，但读取不到任务。"
                )

            return result
def delete_task_data(
    user_id: int,
    task_id: str,
) -> TaskRecord:
    normalized_task_id = task_id.strip()

    if not normalized_task_id:
        raise ValueError("任务 ID 不能为空。")

    with _get_connection() as conn:
        with conn.cursor() as cursor:
            task = _fetch_task_by_cursor(
                cursor,
                user_id,
                normalized_task_id,
            )

            if task is None:
                raise ValueError(
                    f"没有找到任务：{normalized_task_id}"
                )
            backup_path = backup_postgres_data()
            cursor.execute(
                """
                DELETE FROM tasks
                WHERE user_id = %s AND id = %s
                """,
                (user_id, normalized_task_id),
            )

            if cursor.rowcount != 1:
                raise RuntimeError("任务删除失败。")
            print(
                f"删除前 PostgreSQL 备份已创建：{backup_path}"
            )
            return task
