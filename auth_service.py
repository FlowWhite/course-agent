from typing import Any

import psycopg
from psycopg.rows import dict_row
from pwdlib import PasswordHash

from postgres_database import get_postgres_connection


password_hasher = PasswordHash.recommended()


class UserAlreadyExistsError(ValueError):
    """用户名已经存在。"""


def _public_user(row: dict[str, Any]) -> dict[str, Any]:
    """
    只返回可以暴露给上层的用户信息。
    永远不返回 password_hash。
    """
    created_at = row["created_at"]

    return {
        "id": row["id"],
        "username": row["username"],
        "is_active": row["is_active"],
        "created_at": created_at.isoformat(),
    }


def create_user_data(
    username: str,
    password: str,
) -> dict[str, Any]:
    """
    创建用户，并将密码转换为哈希后保存。
    """
    normalized_username = username.strip()

    if len(normalized_username) < 3:
        raise ValueError("用户名至少需要 3 个字符")

    if len(normalized_username) > 100:
        raise ValueError("用户名不能超过 100 个字符")

    if len(password) < 8:
        raise ValueError("密码至少需要 8 个字符")

    password_hash = password_hasher.hash(password)

    with get_postgres_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            try:
                cursor.execute(
                    """
                    INSERT INTO users (
                        username,
                        password_hash
                    )
                    VALUES (%s, %s)
                    RETURNING
                        id,
                        username,
                        is_active,
                        created_at
                    """,
                    (
                        normalized_username,
                        password_hash,
                    ),
                )

                row = cursor.fetchone()

            except psycopg.errors.UniqueViolation as exc:
                raise UserAlreadyExistsError(
                    "用户名已经存在"
                ) from exc

    return _public_user(row)


def authenticate_user_data(
    username: str,
    password: str,
) -> dict[str, Any] | None:
    """
    验证用户名和密码。

    验证成功返回用户信息；
    验证失败返回 None。
    """
    normalized_username = username.strip()

    with get_postgres_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    username,
                    password_hash,
                    is_active,
                    created_at
                FROM users
                WHERE username = %s
                """,
                (normalized_username,),
            )

            row = cursor.fetchone()

    if row is None:
        return None

    if not row["is_active"]:
        return None

    password_is_valid = password_hasher.verify(
        password,
        row["password_hash"],
    )

    if not password_is_valid:
        return None

    return _public_user(row)
