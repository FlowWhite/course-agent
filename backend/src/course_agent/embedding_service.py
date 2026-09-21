"""OpenAI-compatible embedding client kept separate from the DeepSeek Agent client."""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Sequence

from openai import OpenAI

from .environment import load_project_env


EMBEDDING_DIMENSION = 1024
MAX_EMBEDDING_BATCH_SIZE = 128


class EmbeddingConfigurationError(ValueError):
    """Raised when the local embedding configuration is incomplete or unsafe."""


class EmbeddingServiceError(RuntimeError):
    """Raised when an embedding request returns an invalid or unusable result."""


@dataclass(frozen=True)
class EmbeddingSettings:
    base_url: str
    api_key: str
    model: str
    dimension: int
    batch_size: int
    timeout_seconds: float


def get_embedding_settings() -> EmbeddingSettings:
    """Read and validate the dedicated embedding-provider settings."""
    load_project_env()

    base_url = os.getenv("EMBEDDING_BASE_URL", "").strip()
    api_key = os.getenv("EMBEDDING_API_KEY", "").strip()
    model = os.getenv("EMBEDDING_MODEL", "text-embedding-v4").strip()

    if not base_url:
        raise EmbeddingConfigurationError("未配置 EMBEDDING_BASE_URL。")
    if not api_key:
        raise EmbeddingConfigurationError("未配置 EMBEDDING_API_KEY。")
    if not model:
        raise EmbeddingConfigurationError("未配置 EMBEDDING_MODEL。")

    dimension = _read_int("EMBEDDING_DIMENSION", EMBEDDING_DIMENSION)
    if dimension != EMBEDDING_DIMENSION:
        raise EmbeddingConfigurationError(
            f"第一版仅支持 {EMBEDDING_DIMENSION} 维 Embedding。"
        )

    batch_size = _read_int("EMBEDDING_BATCH_SIZE", 16)
    if not 1 <= batch_size <= MAX_EMBEDDING_BATCH_SIZE:
        raise EmbeddingConfigurationError(
            f"EMBEDDING_BATCH_SIZE 必须在 1 到 {MAX_EMBEDDING_BATCH_SIZE} 之间。"
        )

    timeout_seconds = _read_float("EMBEDDING_TIMEOUT_SECONDS", 30.0)
    if not 1 <= timeout_seconds <= 120:
        raise EmbeddingConfigurationError(
            "EMBEDDING_TIMEOUT_SECONDS 必须在 1 到 120 秒之间。"
        )

    return EmbeddingSettings(
        base_url=base_url,
        api_key=api_key,
        model=model,
        dimension=dimension,
        batch_size=batch_size,
        timeout_seconds=timeout_seconds,
    )


def embed_texts(
    texts: Sequence[str],
    *,
    settings: EmbeddingSettings | None = None,
    client: object | None = None,
) -> list[list[float]]:
    """Embed ordered text inputs in bounded batches and validate every vector."""
    normalized_texts = [text.strip() for text in texts]
    if not normalized_texts:
        return []
    if any(not text for text in normalized_texts):
        raise EmbeddingServiceError("待嵌入文本不能为空。")

    resolved_settings = settings or get_embedding_settings()
    resolved_client = client or OpenAI(
        api_key=resolved_settings.api_key,
        base_url=resolved_settings.base_url,
        timeout=resolved_settings.timeout_seconds,
    )
    embeddings: list[list[float]] = []

    for start in range(0, len(normalized_texts), resolved_settings.batch_size):
        batch = normalized_texts[start : start + resolved_settings.batch_size]
        try:
            response = resolved_client.embeddings.create(
                model=resolved_settings.model,
                input=batch,
            )
        except EmbeddingServiceError:
            raise
        except Exception as exc:
            raise EmbeddingServiceError("Embedding 服务请求失败。") from exc

        embeddings.extend(
            _ordered_valid_vectors(
                response.data,
                expected_count=len(batch),
                dimension=resolved_settings.dimension,
            )
        )

    return embeddings


def _ordered_valid_vectors(
    items: Sequence[object],
    *,
    expected_count: int,
    dimension: int,
) -> list[list[float]]:
    indexed: dict[int, list[float]] = {}
    for item in items:
        try:
            index = int(item.index)
            values = [float(value) for value in item.embedding]
        except (AttributeError, TypeError, ValueError) as exc:
            raise EmbeddingServiceError("Embedding 服务返回格式无效。") from exc

        if index < 0 or index >= expected_count or index in indexed:
            raise EmbeddingServiceError("Embedding 服务返回了无效的结果序号。")
        if len(values) != dimension or not all(math.isfinite(value) for value in values):
            raise EmbeddingServiceError("Embedding 向量维度或数值无效。")
        indexed[index] = values

    if len(indexed) != expected_count:
        raise EmbeddingServiceError("Embedding 服务返回的向量数量不完整。")
    return [indexed[index] for index in range(expected_count)]


def _read_int(name: str, default: int) -> int:
    raw_value = os.getenv(name, str(default)).strip()
    try:
        return int(raw_value)
    except ValueError as exc:
        raise EmbeddingConfigurationError(f"{name} 必须是整数。") from exc


def _read_float(name: str, default: float) -> float:
    raw_value = os.getenv(name, str(default)).strip()
    try:
        return float(raw_value)
    except ValueError as exc:
        raise EmbeddingConfigurationError(f"{name} 必须是数字。") from exc
