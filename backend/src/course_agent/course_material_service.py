"""Persistence, search, and storage helpers for user-scoped course materials."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4

from psycopg.rows import dict_row

from .document_parser import ParsedChunk
from .models import (
    CourseFileRecord,
    DocumentParseStatus,
    DocumentSearchResult,
)
from .paths import UPLOAD_ROOT
from .postgres_database import get_postgres_connection

MAX_UPLOAD_BYTES = 20 * 1024 * 1024
ALLOWED_FILE_TYPES = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".txt": "txt",
    ".md": "md",
}

_FILE_SELECT = """
    SELECT
        f.id,
        f.course_id,
        f.original_filename,
        f.storage_filename,
        f.file_type,
        f.file_size,
        f.sha256,
        f.parse_status,
        f.parse_error,
        f.extracted_char_count,
        f.created_at,
        COUNT(c.id) AS chunk_count
    FROM course_files AS f
    LEFT JOIN document_chunks AS c
        ON c.file_id = f.id
"""


def _get_connection():
    connection = get_postgres_connection()
    connection.row_factory = dict_row
    return connection


def sanitize_original_filename(filename: str | None) -> tuple[str, str]:
    """Return metadata-safe name and supported type without using it as a path."""
    if not filename:
        raise ValueError("请选择要上传的课程文件。")

    normalized = filename.replace("\\", "/").split("/")[-1].strip()
    if not normalized or normalized in {".", ".."}:
        raise ValueError("文件名无效。")

    extension = Path(normalized).suffix.lower()
    file_type = ALLOWED_FILE_TYPES.get(extension)
    if file_type is None:
        raise ValueError("仅支持 PDF、DOCX、TXT 和 MD 文件。")

    return normalized[:255], file_type


def create_storage_name(file_type: str) -> str:
    return f"{uuid4().hex}.{file_type}"


def user_upload_directory(user_id: int) -> Path:
    directory = (UPLOAD_ROOT / str(user_id)).resolve()
    root = UPLOAD_ROOT.resolve()
    if root not in directory.parents:
        raise RuntimeError("上传目录无效。")
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def storage_path_for(user_id: int, storage_filename: str) -> Path:
    filename = Path(storage_filename).name
    if filename != storage_filename:
        raise ValueError("存储文件名无效。")

    path = (user_upload_directory(user_id) / filename).resolve()
    user_directory = user_upload_directory(user_id).resolve()
    if path.parent != user_directory:
        raise ValueError("存储路径无效。")
    return path


def calculate_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as uploaded_file:
        for block in iter(lambda: uploaded_file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _assert_course_exists(cursor, course_id: str) -> None:
    cursor.execute(
        "SELECT 1 FROM courses WHERE id = %s",
        (course_id,),
    )
    if cursor.fetchone() is None:
        raise ValueError("没有找到对应课程。")


def _resolve_course_id(cursor, course: str) -> str:
    normalized = course.strip()
    if not normalized:
        raise ValueError("课程不能为空。")

    cursor.execute(
        """
        SELECT id
        FROM courses
        WHERE id = %s OR name = %s
        """,
        (normalized, normalized),
    )
    rows = cursor.fetchall()

    if not rows:
        raise ValueError(f"没有找到课程：{normalized}")
    if len(rows) > 1:
        raise ValueError("课程名称不唯一，请使用课程 ID。")
    return str(rows[0]["id"])


def _row_to_file_record(row: dict[str, Any]) -> CourseFileRecord:
    public_row = dict(row)
    public_row.pop("storage_filename", None)
    return CourseFileRecord.model_validate(public_row)


def _fetch_file_by_cursor(
    cursor,
    user_id: int,
    file_id: str,
) -> tuple[CourseFileRecord, str] | None:
    cursor.execute(
        _FILE_SELECT
        + """
        WHERE f.id = %s AND f.user_id = %s
        GROUP BY f.id
        """,
        (file_id, user_id),
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return _row_to_file_record(row), str(row["storage_filename"])


def create_course_file_data(
    *,
    user_id: int,
    course_id: str,
    original_filename: str,
    storage_filename: str,
    file_type: str,
    file_size: int,
    file_sha256: str,
) -> CourseFileRecord:
    file_id = uuid4().hex

    with _get_connection() as connection:
        with connection.cursor() as cursor:
            _assert_course_exists(cursor, course_id)
            cursor.execute(
                """
                INSERT INTO course_files (
                    id, user_id, course_id, original_filename,
                    storage_filename, file_type, file_size, sha256,
                    parse_status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    file_id,
                    user_id,
                    course_id,
                    original_filename,
                    storage_filename,
                    file_type,
                    file_size,
                    file_sha256,
                    DocumentParseStatus.PENDING.value,
                ),
            )
            fetched = _fetch_file_by_cursor(cursor, user_id, file_id)

    if fetched is None:
        raise RuntimeError("文件元数据已写入，但无法读取。")
    return fetched[0]


def set_course_file_parsing_data(user_id: int, file_id: str) -> None:
    _update_parse_state(
        user_id=user_id,
        file_id=file_id,
        status=DocumentParseStatus.PARSING,
    )


def set_course_file_parse_failed_data(
    *,
    user_id: int,
    file_id: str,
    error: str,
) -> CourseFileRecord:
    _update_parse_state(
        user_id=user_id,
        file_id=file_id,
        status=DocumentParseStatus.FAILED,
        error=error[:1_000],
    )
    result = get_course_file_data(user_id, file_id)
    if result is None:
        raise RuntimeError("文件解析状态已更新，但无法读取文件。")
    return result


def _update_parse_state(
    *,
    user_id: int,
    file_id: str,
    status: DocumentParseStatus,
    error: str | None = None,
    extracted_char_count: int | None = None,
) -> None:
    with _get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE course_files
                SET
                    parse_status = %s,
                    parse_error = %s,
                    extracted_char_count = COALESCE(%s, extracted_char_count),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND user_id = %s
                """,
                (
                    status.value,
                    error,
                    extracted_char_count,
                    file_id,
                    user_id,
                ),
            )
            if cursor.rowcount != 1:
                raise ValueError("没有找到可操作的文件。")


def replace_document_chunks_data(
    *,
    user_id: int,
    file_id: str,
    chunks: Iterable[ParsedChunk],
) -> CourseFileRecord:
    prepared_chunks = list(chunks)
    if not prepared_chunks:
        raise ValueError("没有可保存的解析文本。")

    with _get_connection() as connection:
        with connection.cursor() as cursor:
            fetched = _fetch_file_by_cursor(cursor, user_id, file_id)
            if fetched is None:
                raise ValueError("没有找到可操作的文件。")

            cursor.execute(
                "DELETE FROM document_chunks WHERE file_id = %s",
                (file_id,),
            )

            for chunk_index, chunk in enumerate(prepared_chunks):
                cursor.execute(
                    """
                    INSERT INTO document_chunks (
                        id, file_id, page_number, chunk_index, content, search_vector
                    )
                    VALUES (
                        %s, %s, %s, %s, %s,
                        to_tsvector('simple', %s)
                    )
                    """,
                    (
                        uuid4().hex,
                        file_id,
                        chunk.page_number,
                        chunk_index,
                        chunk.content,
                        chunk.content,
                    ),
                )

            extracted_char_count = sum(
                len(chunk.content)
                for chunk in prepared_chunks
            )
            cursor.execute(
                """
                UPDATE course_files
                SET
                    parse_status = %s,
                    parse_error = NULL,
                    extracted_char_count = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND user_id = %s
                """,
                (
                    DocumentParseStatus.PARSED.value,
                    extracted_char_count,
                    file_id,
                    user_id,
                ),
            )
            fetched = _fetch_file_by_cursor(cursor, user_id, file_id)

    if fetched is None:
        raise RuntimeError("解析内容已保存，但无法读取文件。")
    return fetched[0]


def list_course_files_data(
    user_id: int,
    course_id: str | None = None,
) -> list[CourseFileRecord]:
    normalized_course_id = (course_id or "").strip()
    parameters: list[Any] = [user_id]
    where = "WHERE f.user_id = %s"
    if normalized_course_id:
        where += " AND f.course_id = %s"
        parameters.append(normalized_course_id)

    with _get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                _FILE_SELECT
                + f"""
                {where}
                GROUP BY f.id
                ORDER BY f.created_at DESC
                """,
                parameters,
            )
            rows = cursor.fetchall()

    return [_row_to_file_record(row) for row in rows]


def get_course_file_data(
    user_id: int,
    file_id: str,
) -> CourseFileRecord | None:
    with _get_connection() as connection:
        with connection.cursor() as cursor:
            fetched = _fetch_file_by_cursor(cursor, user_id, file_id)
    return fetched[0] if fetched is not None else None


def get_owned_file_storage_data(
    user_id: int,
    file_id: str,
) -> tuple[CourseFileRecord, str] | None:
    with _get_connection() as connection:
        with connection.cursor() as cursor:
            return _fetch_file_by_cursor(cursor, user_id, file_id)


def delete_course_file_data(
    user_id: int,
    file_id: str,
) -> CourseFileRecord:
    with _get_connection() as connection:
        with connection.cursor() as cursor:
            fetched = _fetch_file_by_cursor(cursor, user_id, file_id)
            if fetched is None:
                raise ValueError("没有找到可删除的文件。")

            cursor.execute(
                """
                DELETE FROM course_files
                WHERE id = %s AND user_id = %s
                """,
                (file_id, user_id),
            )
            if cursor.rowcount != 1:
                raise RuntimeError("文件删除失败。")
    return fetched[0]


def search_course_documents_data(
    *,
    user_id: int,
    course: str,
    query: str,
    limit: int = 6,
) -> list[DocumentSearchResult]:
    normalized_query = " ".join(query.split())
    if not normalized_query:
        raise ValueError("检索内容不能为空。")

    terms = [term for term in normalized_query.split(" ") if term][:8]
    if not terms:
        raise ValueError("检索内容不能为空。")

    with _get_connection() as connection:
        with connection.cursor() as cursor:
            course_id = _resolve_course_id(cursor, course)
            like_conditions = " OR ".join(
                "dc.content ILIKE %s"
                for _ in terms
            )
            parameters: list[Any] = [
                normalized_query,
                normalized_query,
                user_id,
                course_id,
                *[f"%{term}%" for term in terms],
                max(1, min(limit, 12)),
            ]
            cursor.execute(
                f"""
                SELECT
                    cf.id AS file_id,
                    cf.original_filename AS file_name,
                    dc.page_number AS page,
                    dc.content,
                    (
                        CASE
                            WHEN dc.content ILIKE %s THEN 1.0
                            ELSE 0.0
                        END
                        + ts_rank_cd(
                            dc.search_vector,
                            websearch_to_tsquery('simple', %s)
                        )
                    ) AS relevance
                FROM document_chunks AS dc
                JOIN course_files AS cf
                    ON cf.id = dc.file_id
                WHERE
                    cf.user_id = %s
                    AND cf.course_id = %s
                    AND cf.parse_status = 'parsed'
                    AND ({like_conditions})
                ORDER BY relevance DESC, cf.created_at DESC, dc.chunk_index ASC
                LIMIT %s
                """,
                parameters,
            )
            rows = cursor.fetchall()

    return [
        DocumentSearchResult.model_validate(row)
        for row in rows
    ]
