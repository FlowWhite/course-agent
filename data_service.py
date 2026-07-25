import sqlite3
from typing import Any

from database import backup_database, get_connection
from models import (
    CourseSummary,
    TaskCreate,
    TaskRecord,
    TaskStatusUpdate,
    TaskUpdate,
)


def list_courses_data() -> list[CourseSummary]:
    conn = get_connection()
    conn.row_factory = sqlite3.Row

    try:
        cursor = conn.cursor()

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
                AND t.status = 'todo'
            GROUP BY
                c.id,
                c.name,
                c.teacher
            ORDER BY c.name
            """
        )

        return [
            CourseSummary.model_validate(dict(row))
            for row in cursor.fetchall()
        ]

    finally:
        conn.close()


def list_tasks_data(
    course: str,
    status: str,
) -> list[TaskRecord]:
    normalized_course = course.strip()
    normalized_status = status.strip().lower()

    if normalized_status not in {"all", "todo", "done"}:
        raise ValueError("status 只能是 all、todo 或 done。")

    conn = get_connection()
    conn.row_factory = sqlite3.Row

    try:
        cursor = conn.cursor()

        sql = """
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
            WHERE 1 = 1
        """

        parameters: list[Any] = []

        if normalized_course:
            sql += """
                AND (
                    c.id = ?
                    OR c.name LIKE ?
                )
            """
            parameters.extend(
                [
                    normalized_course,
                    f"%{normalized_course}%",
                ]
            )

        if normalized_status != "all":
            sql += " AND t.status = ?"
            parameters.append(normalized_status)

        sql += " ORDER BY t.deadline ASC"

        cursor.execute(sql, parameters)

        return [
            TaskRecord.model_validate(dict(row))
            for row in cursor.fetchall()
        ]

    finally:
        conn.close()


def get_task_detail_data(
    task_id: str,
) -> TaskRecord | None:
    normalized_task_id = task_id.strip()

    conn = get_connection()
    conn.row_factory = sqlite3.Row

    try:
        cursor = conn.cursor()

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
            WHERE t.id = ?
            """,
            (normalized_task_id,),
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return TaskRecord.model_validate(dict(row))

    finally:
        conn.close()
def _resolve_course_id(
    cursor: sqlite3.Cursor,
    course: str,
) -> str:
    """根据课程 ID 或课程名称解析课程 ID。"""
    normalized_course = course.strip()

    if not normalized_course:
        raise ValueError("课程不能为空。")

    cursor.execute(
        """
        SELECT id, name
        FROM courses
        WHERE id = ? OR name = ?
        """,
        (normalized_course, normalized_course),
    )

    rows = cursor.fetchall()

    if not rows:
        raise ValueError(f"没有找到课程：{normalized_course}")

    if len(rows) > 1:
        raise ValueError("课程名称不唯一，请改用课程 ID。")

    return str(rows[0]["id"])


def _fetch_task_by_cursor(
    cursor: sqlite3.Cursor,
    task_id: str,
) -> TaskRecord | None:
    """使用当前数据库连接查询完整任务。"""
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
        WHERE t.id = ?
        """,
        (task_id,),
    )

    row = cursor.fetchone()

    if row is None:
        return None

    return TaskRecord.model_validate(dict(row))


def create_task_data(
    task_id: str,
    course: str,
    title: str,
    deadline: str,
    priority: str,
    description: str,
) -> TaskRecord:
    """新增任务并返回新增后的完整任务。"""
    conn = get_connection()
    conn.row_factory = sqlite3.Row

    try:
        cursor = conn.cursor()

        course_id = _resolve_course_id(cursor, course)

        task = TaskCreate(
            id=task_id,
            course_id=course_id,
            title=title,
            deadline=deadline,
            priority=priority,
            description=description,
        )

        cursor.execute(
            "SELECT 1 FROM tasks WHERE id = ?",
            (task.id,),
        )

        if cursor.fetchone() is not None:
            raise ValueError(f"任务 ID 已存在：{task.id}")

        cursor.execute(
            """
            INSERT INTO tasks(
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
                task.id,
                task.course_id,
                task.title,
                task.deadline.isoformat(),
                task.status.value,
                task.priority.value,
                task.description,
            ),
        )

        conn.commit()

        result = _fetch_task_by_cursor(cursor, task.id)

        if result is None:
            raise RuntimeError("任务已经写入，但读取不到新增任务。")

        return result

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def update_task_data(
    task_id: str,
    title: str | None = None,
    deadline: str | None = None,
    priority: str | None = None,
    description: str | None = None,
) -> TaskRecord:
    """修改任务普通字段，不修改任务 ID、课程和状态。"""
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

    conn = get_connection()
    conn.row_factory = sqlite3.Row

    try:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT 1 FROM tasks WHERE id = ?",
            (normalized_task_id,),
        )

        if cursor.fetchone() is None:
            raise ValueError(f"没有找到任务：{normalized_task_id}")

        field_names = list(changes.keys())
        set_clause = ", ".join(
            f"{field_name} = ?"
            for field_name in field_names
        )

        values = [
            changes[field_name]
            for field_name in field_names
        ]
        values.append(normalized_task_id)

        cursor.execute(
            f"""
            UPDATE tasks
            SET {set_clause}
            WHERE id = ?
            """,
            values,
        )

        conn.commit()

        result = _fetch_task_by_cursor(
            cursor,
            normalized_task_id,
        )

        if result is None:
            raise RuntimeError("任务已经更新，但读取不到更新后的任务。")

        return result

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def update_task_status_data(
    task_id: str,
    status: str,
) -> TaskRecord:
    """切换任务状态，只允许 todo 或 done。"""
    normalized_task_id = task_id.strip()

    if not normalized_task_id:
        raise ValueError("任务 ID 不能为空。")

    status_update = TaskStatusUpdate(
        status=status.strip().lower(),
    )

    conn = get_connection()
    conn.row_factory = sqlite3.Row

    try:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT 1 FROM tasks WHERE id = ?",
            (normalized_task_id,),
        )

        if cursor.fetchone() is None:
            raise ValueError(f"没有找到任务：{normalized_task_id}")

        cursor.execute(
            """
            UPDATE tasks
            SET status = ?
            WHERE id = ?
            """,
            (
                status_update.status.value,
                normalized_task_id,
            ),
        )

        conn.commit()

        result = _fetch_task_by_cursor(
            cursor,
            normalized_task_id,
        )

        if result is None:
            raise RuntimeError("任务状态已经更新，但读取不到任务。")

        return result

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()
def delete_task_data(
    task_id: str,
) -> TaskRecord:
    """备份数据库后删除指定任务，并返回被删除的任务。"""
    normalized_task_id = task_id.strip()

    if not normalized_task_id:
        raise ValueError("任务 ID 不能为空。")

    conn = get_connection()
    conn.row_factory = sqlite3.Row

    try:
        cursor = conn.cursor()

        task = _fetch_task_by_cursor(
            cursor,
            normalized_task_id,
        )

        if task is None:
            raise ValueError(
                f"没有找到任务：{normalized_task_id}"
            )

        backup_path = backup_database()

        cursor.execute(
            """
            DELETE FROM tasks
            WHERE id = ?
            """,
            (normalized_task_id,),
        )

        if cursor.rowcount != 1:
            raise RuntimeError("任务删除失败。")

        conn.commit()

        print(f"删除前备份已创建：{backup_path}")

        return task

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()