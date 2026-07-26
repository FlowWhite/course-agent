"""Create the public, synthetic Computer Networks demo account.

This script is intentionally explicit and idempotent. It never runs as part
of application startup, so production deployments do not receive a public
demo credential by accident.
"""

from __future__ import annotations

import argparse
import os
from datetime import date, timedelta
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("COURSE_AGENT_PROJECT_ROOT", str(PROJECT_ROOT))


def _load_dotenv(path: Path) -> None:
    """Load simple KEY=VALUE settings without adding a dotenv dependency."""
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        os.environ.setdefault(key, value)


_load_dotenv(PROJECT_ROOT / ".env")

from psycopg.rows import dict_row  # noqa: E402
from pwdlib import PasswordHash  # noqa: E402

from course_agent.course_material_service import (  # noqa: E402
    calculate_sha256,
    create_course_file_data,
    replace_document_chunks_data,
    user_upload_directory,
)
from course_agent.document_parser import parse_document  # noqa: E402
from course_agent.postgres_database import (  # noqa: E402
    ensure_application_schema,
    get_postgres_connection,
)


DEMO_USERNAME = os.getenv("DEMO_USERNAME", "demo")
DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "course-agent-demo")
COURSE_ID = "cn-demo-2026"
MATERIAL_FILENAME = "计算机网络实验一-演示资料.md"
MATERIAL_STORAGE_FILENAME = "demo-computer-network-material.md"

DEMO_COURSE = {
    "id": COURSE_ID,
    "name": "计算机网络",
    "teacher": "课程 Agent 演示",
}

DEMO_TASKS = (
    {
        "id": "cn-demo-exp1-capture",
        "title": "实验一：抓包与协议观察",
        "deadline_offset_days": 5,
        "status": "todo",
        "priority": "high",
        "description": (
            "使用 Wireshark 完成一次基础协议观察，记录抓包过滤条件、关键报文和观察结论。"
        ),
    },
    {
        "id": "cn-demo-exp1-http",
        "title": "分析 HTTP 报文头部与消息字段",
        "deadline_offset_days": 10,
        "status": "todo",
        "priority": "high",
        "description": (
            "结合抓包结果说明 HTTP 请求行、响应状态行、常见首部字段以及请求与响应的对应关系。"
        ),
    },
    {
        "id": "cn-demo-exp1-report",
        "title": "整理实验报告与验收清单",
        "deadline_offset_days": 14,
        "status": "todo",
        "priority": "medium",
        "description": (
            "整理实验环境、操作步骤、关键截图、分析结论和问题复盘，提交前逐项核对报告要求。"
        ),
    },
)

DEMO_MATERIAL = """# 计算机网络实验一（公开演示资料）

> 这是 Course Agent 的合成演示资料，用于展示课程资料检索和任务拆解功能，不是任何学校的原始指导书。

## 实验目标

通过 Wireshark 观察网络通信过程，建立对 HTTP 请求与响应、常见报文头部以及协议分层的直观认识。

## 建议步骤

1. 准备浏览器和 Wireshark，选择正确的网络接口并开始抓包。
2. 使用显示过滤器定位 HTTP 流量，记录请求方法、请求地址、状态码和关键首部。
3. 跟踪一个完整会话，比较客户端请求与服务器响应中的字段。
4. 保存必要截图，并在报告中写出观察结果、异常现象和自己的解释。

## 报告验收清单

- 写明实验环境和抓包过滤条件。
- 至少分析一组 HTTP 请求与响应的对应字段。
- 对关键截图添加编号和简短说明。
- 区分观察到的事实与个人推断，无法确认的内容应标记为待核对。
- 提交前检查文件命名、格式和报告完整性。

## 延伸问题

可以继续比较 SMTP、Telnet 等明文协议与加密协议在可观察性上的差异，但演示数据不提供具体课程评分标准。
"""


def _connection():
    connection = get_postgres_connection()
    connection.row_factory = dict_row
    return connection


def _ensure_demo_user() -> int:
    if len(DEMO_USERNAME.strip()) < 3:
        raise ValueError("DEMO_USERNAME 至少需要 3 个字符。")
    if len(DEMO_PASSWORD) < 8:
        raise ValueError("DEMO_PASSWORD 至少需要 8 个字符。")

    with _connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM users WHERE username = %s",
                (DEMO_USERNAME.strip(),),
            )
            row = cursor.fetchone()
            if row is not None:
                return int(row["id"])

            password_hash = PasswordHash.recommended().hash(DEMO_PASSWORD)
            cursor.execute(
                """
                INSERT INTO users (username, password_hash)
                VALUES (%s, %s)
                RETURNING id
                """,
                (DEMO_USERNAME.strip(), password_hash),
            )
            return int(cursor.fetchone()["id"])


def _ensure_demo_course(user_id: int) -> None:
    with _connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT user_id FROM courses WHERE id = %s",
                (COURSE_ID,),
            )
            row = cursor.fetchone()
            if row is not None and int(row["user_id"]) != user_id:
                raise RuntimeError(
                    f"课程 ID {COURSE_ID} 已属于其他用户，未覆盖原数据。"
                )

            cursor.execute(
                """
                INSERT INTO courses (id, user_id, name, teacher)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    teacher = EXCLUDED.teacher
                WHERE courses.user_id = EXCLUDED.user_id
                """,
                (
                    DEMO_COURSE["id"],
                    user_id,
                    DEMO_COURSE["name"],
                    DEMO_COURSE["teacher"],
                ),
            )


def _ensure_demo_tasks(user_id: int) -> None:
    deadline_base = date.today()
    with _connection() as connection:
        with connection.cursor() as cursor:
            for task in DEMO_TASKS:
                cursor.execute(
                    "SELECT user_id FROM tasks WHERE id = %s",
                    (task["id"],),
                )
                row = cursor.fetchone()
                if row is not None and int(row["user_id"]) != user_id:
                    raise RuntimeError(
                        f"任务 ID {task['id']} 已属于其他用户，未覆盖原数据。"
                    )

                deadline = deadline_base + timedelta(
                    days=int(task["deadline_offset_days"])
                )
                cursor.execute(
                    """
                    INSERT INTO tasks (
                        id, user_id, course_id, title, deadline,
                        status, priority, description
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        course_id = EXCLUDED.course_id,
                        title = EXCLUDED.title,
                        deadline = EXCLUDED.deadline,
                        status = EXCLUDED.status,
                        priority = EXCLUDED.priority,
                        description = EXCLUDED.description
                    WHERE tasks.user_id = EXCLUDED.user_id
                    """,
                    (
                        task["id"],
                        user_id,
                        COURSE_ID,
                        task["title"],
                        deadline,
                        task["status"],
                        task["priority"],
                        task["description"],
                    ),
                )


def _ensure_demo_material(user_id: int) -> None:
    upload_directory = user_upload_directory(user_id)
    material_path = upload_directory / MATERIAL_STORAGE_FILENAME
    material_path.write_text(DEMO_MATERIAL, encoding="utf-8")
    file_size = material_path.stat().st_size
    file_sha256 = calculate_sha256(material_path)

    with _connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, storage_filename
                FROM course_files
                WHERE user_id = %s
                  AND course_id = %s
                  AND original_filename = %s
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (user_id, COURSE_ID, MATERIAL_FILENAME),
            )
            row = cursor.fetchone()

    if row is None:
        file_record = create_course_file_data(
            user_id=user_id,
            course_id=COURSE_ID,
            original_filename=MATERIAL_FILENAME,
            storage_filename=MATERIAL_STORAGE_FILENAME,
            file_type="md",
            file_size=file_size,
            file_sha256=file_sha256,
        )
        file_id = file_record.id
    else:
        file_id = str(row["id"])
        existing_storage_path = upload_directory / str(row["storage_filename"])
        if existing_storage_path != material_path:
            existing_storage_path.write_text(DEMO_MATERIAL, encoding="utf-8")
            material_path = existing_storage_path

    chunks = parse_document(material_path, "md")
    replace_document_chunks_data(
        user_id=user_id,
        file_id=file_id,
        chunks=chunks,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="创建公开的计算机网络合成演示账号、课程、任务和资料。"
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="确认写入当前 PostgreSQL 数据库；脚本不会自动执行。",
    )
    args = parser.parse_args()
    if not args.yes:
        parser.error("这是显式写入操作，请确认后添加 --yes。")

    ensure_application_schema()
    user_id = _ensure_demo_user()
    _ensure_demo_course(user_id)
    _ensure_demo_tasks(user_id)
    _ensure_demo_material(user_id)

    print("DEMO SEED OK")
    print(f"username: {DEMO_USERNAME.strip()}")
    if os.getenv("DEMO_PASSWORD"):
        print("password: 使用 DEMO_PASSWORD 环境变量")
    else:
        print(f"password: {DEMO_PASSWORD}")
    print(f"course: {DEMO_COURSE['name']} ({COURSE_ID})")
    print("material: 合成演示资料已解析并写入课程资料库")


if __name__ == "__main__":
    main()
