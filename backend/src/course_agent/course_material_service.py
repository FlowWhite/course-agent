"""Persistence, search, and storage helpers for user-scoped course materials."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4

from psycopg.rows import dict_row

from .document_parser import ParsedChunk
from .embedding_service import (
    EMBEDDING_DIMENSION,
    EmbeddingConfigurationError,
    EmbeddingServiceError,
    EmbeddingSettings,
    embed_texts,
    get_embedding_settings,
)
from .models import (
    DocumentEmbeddingStatus,
    CourseFileRecord,
    DocumentParseStatus,
    DocumentSearchResult,
)
from .paths import UPLOAD_ROOT
from .postgres_database import get_postgres_connection

MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_EMBEDDING_CHUNKS_PER_FILE = 512
MIN_VECTOR_RELEVANCE = 0.25
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
        f.embedding_status,
        f.embedding_error,
        f.embedding_model,
        f.embedding_dimension,
        f.embedded_at,
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


def _assert_course_exists(cursor, user_id: int, course_id: str) -> None:
    cursor.execute(
        "SELECT 1 FROM courses WHERE id = %s AND user_id = %s",
        (course_id, user_id),
    )
    if cursor.fetchone() is None:
        raise ValueError("没有找到对应课程。")


def _resolve_course_id(cursor, user_id: int, course: str) -> str:
    normalized = course.strip()
    if not normalized:
        raise ValueError("课程不能为空。")

    cursor.execute(
        """
        SELECT id
        FROM courses
        WHERE user_id = %s
          AND (id = %s OR name = %s)
        """,
        (user_id, normalized, normalized),
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
            _assert_course_exists(cursor, user_id, course_id)
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
                    embedding_status = %s,
                    embedding_error = NULL,
                    embedding_model = NULL,
                    embedding_dimension = NULL,
                    embedded_at = NULL,
                    extracted_char_count = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND user_id = %s
                """,
                (
                    DocumentParseStatus.PARSED.value,
                    DocumentEmbeddingStatus.NOT_INDEXED.value,
                    extracted_char_count,
                    file_id,
                    user_id,
                ),
            )
            fetched = _fetch_file_by_cursor(cursor, user_id, file_id)

    if fetched is None:
        raise RuntimeError("解析内容已保存，但无法读取文件。")
    return fetched[0]


def index_course_file_embeddings_data(
    *,
    user_id: int,
    file_id: str,
) -> CourseFileRecord:
    """Create or retry one owned file's vector index without holding a DB transaction."""
    existing = get_course_file_data(user_id, file_id)
    if existing is None:
        raise ValueError("没有找到可建立索引的文件。")
    if existing.parse_status is not DocumentParseStatus.PARSED:
        raise ValueError("文件尚未完成解析，无法建立向量索引。")
    if existing.embedding_status is DocumentEmbeddingStatus.READY:
        return existing

    try:
        settings = get_embedding_settings()
        if not _set_embedding_indexing_data(user_id=user_id, file_id=file_id):
            current = get_course_file_data(user_id, file_id)
            if current is None:
                raise ValueError("没有找到可建立索引的文件。")
            return current
        chunks = _get_owned_chunks_for_embedding(user_id=user_id, file_id=file_id)
        if not chunks:
            raise EmbeddingServiceError("文件没有可建立索引的文本块。")
        if len(chunks) > MAX_EMBEDDING_CHUNKS_PER_FILE:
            raise EmbeddingServiceError(
                "文件文本块过多，无法在第一版中建立向量索引，请拆分文件后重试。"
            )

        embeddings = embed_texts(
            [str(chunk["content"]) for chunk in chunks],
            settings=settings,
        )
        if len(embeddings) != len(chunks):
            raise EmbeddingServiceError("Embedding 服务返回的向量数量不完整。")

        return _save_file_embeddings_data(
            user_id=user_id,
            file_id=file_id,
            chunks=chunks,
            embeddings=embeddings,
            settings=settings,
        )
    except (EmbeddingConfigurationError, EmbeddingServiceError) as exc:
        return _set_embedding_failed_data(
            user_id=user_id,
            file_id=file_id,
            error=str(exc),
        )
    except ValueError:
        raise
    except Exception:
        return _set_embedding_failed_data(
            user_id=user_id,
            file_id=file_id,
            error="建立课程资料向量索引失败，请稍后重试。",
        )


def _set_embedding_indexing_data(*, user_id: int, file_id: str) -> bool:
    with _get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE course_files
                SET
                    embedding_status = %s,
                    embedding_error = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE
                    id = %s
                    AND user_id = %s
                    AND parse_status = %s
                    AND embedding_status IN (%s, %s)
                """,
                (
                    DocumentEmbeddingStatus.INDEXING.value,
                    file_id,
                    user_id,
                    DocumentParseStatus.PARSED.value,
                    DocumentEmbeddingStatus.NOT_INDEXED.value,
                    DocumentEmbeddingStatus.FAILED.value,
                ),
            )
            if cursor.rowcount == 1:
                return True

    current = get_course_file_data(user_id, file_id)
    if current is None:
        raise ValueError("没有找到可建立索引的文件。")
    if current.embedding_status is DocumentEmbeddingStatus.INDEXING:
        raise ValueError("文件正在建立向量索引，请稍后刷新。")
    if current.embedding_status is DocumentEmbeddingStatus.READY:
        return False
    raise ValueError("文件当前无法建立向量索引。")


def _get_owned_chunks_for_embedding(*, user_id: int, file_id: str) -> list[dict[str, Any]]:
    with _get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT dc.id, dc.content
                FROM document_chunks AS dc
                JOIN course_files AS cf ON cf.id = dc.file_id
                WHERE dc.file_id = %s AND cf.user_id = %s AND cf.parse_status = %s
                ORDER BY dc.chunk_index ASC
                """,
                (file_id, user_id, DocumentParseStatus.PARSED.value),
            )
            return list(cursor.fetchall())


def _save_file_embeddings_data(
    *,
    user_id: int,
    file_id: str,
    chunks: list[dict[str, Any]],
    embeddings: list[list[float]],
    settings: EmbeddingSettings,
) -> CourseFileRecord:
    with _get_connection() as connection:
        with connection.cursor() as cursor:
            for chunk, embedding in zip(chunks, embeddings, strict=True):
                cursor.execute(
                    """
                    UPDATE document_chunks AS dc
                    SET embedding = %s::vector
                    FROM course_files AS cf
                    WHERE dc.id = %s
                      AND dc.file_id = %s
                      AND cf.id = dc.file_id
                      AND cf.user_id = %s
                    """,
                    (
                        _vector_literal(embedding),
                        str(chunk["id"]),
                        file_id,
                        user_id,
                    ),
                )
                if cursor.rowcount != 1:
                    raise RuntimeError("写入课程资料向量时发生并发变更。")

            cursor.execute(
                """
                UPDATE course_files
                SET
                    embedding_status = %s,
                    embedding_error = NULL,
                    embedding_model = %s,
                    embedding_dimension = %s,
                    embedded_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND user_id = %s
                """,
                (
                    DocumentEmbeddingStatus.READY.value,
                    settings.model,
                    settings.dimension,
                    file_id,
                    user_id,
                ),
            )
            if cursor.rowcount != 1:
                raise RuntimeError("课程资料索引状态更新失败。")
            fetched = _fetch_file_by_cursor(cursor, user_id, file_id)

    if fetched is None:
        raise RuntimeError("课程资料向量已写入，但无法读取文件。")
    return fetched[0]


def _set_embedding_failed_data(
    *,
    user_id: int,
    file_id: str,
    error: str,
) -> CourseFileRecord:
    with _get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE course_files
                SET
                    embedding_status = %s,
                    embedding_error = %s,
                    embedding_model = NULL,
                    embedding_dimension = NULL,
                    embedded_at = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND user_id = %s
                """,
                (
                    DocumentEmbeddingStatus.FAILED.value,
                    error[:1_000],
                    file_id,
                    user_id,
                ),
            )
            if cursor.rowcount != 1:
                raise ValueError("没有找到可更新的文件。")
            fetched = _fetch_file_by_cursor(cursor, user_id, file_id)

    if fetched is None:
        raise RuntimeError("课程资料索引失败状态已更新，但无法读取文件。")
    return fetched[0]


def _vector_literal(values: list[float]) -> str:
    if len(values) != EMBEDDING_DIMENSION:
        raise EmbeddingServiceError("Embedding 向量维度无效。")
    return "[" + ",".join(format(value, ".12g") for value in values) + "]"


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

    with _get_connection() as connection:
        with connection.cursor() as cursor:
            course_id = _resolve_course_id(cursor, user_id, course)
            cursor.execute(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM document_chunks AS dc
                    JOIN course_files AS cf ON cf.id = dc.file_id
                    WHERE cf.user_id = %s
                      AND cf.course_id = %s
                      AND cf.parse_status = %s
                      AND cf.embedding_status = %s
                      AND dc.embedding IS NOT NULL
                ) AS has_embeddings
                """,
                (
                    user_id,
                    course_id,
                    DocumentParseStatus.PARSED.value,
                    DocumentEmbeddingStatus.READY.value,
                ),
            )
            has_embeddings = bool(cursor.fetchone()["has_embeddings"])

    if has_embeddings:
        try:
            query_embedding = embed_texts([normalized_query])[0]
            vector_results = _search_course_documents_by_vector(
                user_id=user_id,
                course_id=course_id,
                query_embedding=query_embedding,
                limit=limit,
            )
            if vector_results:
                return vector_results
        except (EmbeddingConfigurationError, EmbeddingServiceError):
            # Full-text search keeps existing materials usable if the provider
            # is unavailable or its configuration is intentionally absent.
            pass

    return _search_course_documents_by_full_text(
        user_id=user_id,
        course_id=course_id,
        query=normalized_query,
        limit=limit,
    )


def _search_course_documents_by_vector(
    *,
    user_id: int,
    course_id: str,
    query_embedding: list[float],
    limit: int,
) -> list[DocumentSearchResult]:
    vector_literal = _vector_literal(query_embedding)
    bounded_limit = max(1, min(limit, 12))
    with _get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    dc.id AS chunk_id,
                    dc.chunk_index,
                    cf.id AS file_id,
                    cf.original_filename AS file_name,
                    dc.page_number AS page,
                    dc.content,
                    GREATEST(0.0, 1.0 - (dc.embedding <=> %s::vector)) AS relevance
                FROM document_chunks AS dc
                JOIN course_files AS cf
                    ON cf.id = dc.file_id
                WHERE
                    cf.user_id = %s
                    AND cf.course_id = %s
                    AND cf.parse_status = 'parsed'
                    AND cf.embedding_status = 'ready'
                    AND dc.embedding IS NOT NULL
                ORDER BY dc.embedding <=> %s::vector, cf.created_at DESC, dc.chunk_index ASC
                LIMIT %s
                """,
                (vector_literal, user_id, course_id, vector_literal, bounded_limit),
            )
            rows = cursor.fetchall()

    return [
        DocumentSearchResult.model_validate(row)
        for row in rows
        if float(row["relevance"]) >= MIN_VECTOR_RELEVANCE
    ]


def _search_course_documents_by_full_text(
    *,
    user_id: int,
    course_id: str,
    query: str,
    limit: int,
) -> list[DocumentSearchResult]:
    terms = [term for term in query.split(" ") if term][:8]
    if not terms:
        raise ValueError("检索内容不能为空。")

    like_conditions = " OR ".join("dc.content ILIKE %s" for _ in terms)
    parameters: list[Any] = [
        query,
        query,
        user_id,
        course_id,
        *[f"%{term}%" for term in terms],
        max(1, min(limit, 12)),
    ]
    with _get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT
                    dc.id AS chunk_id,
                    dc.chunk_index,
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

    return [DocumentSearchResult.model_validate(row) for row in rows]
