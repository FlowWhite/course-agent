import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from course_agent.embedding_service import (
    EMBEDDING_DIMENSION,
    EmbeddingConfigurationError,
    EmbeddingServiceError,
    EmbeddingSettings,
    embed_texts,
    get_embedding_settings,
)


class _FakeEmbeddings:
    def __init__(self, batches):
        self.batches = list(batches)
        self.calls = []

    def create(self, *, model, input):
        self.calls.append((model, input))
        return SimpleNamespace(data=self.batches.pop(0))


class _FakeClient:
    def __init__(self, batches):
        self.embeddings = _FakeEmbeddings(batches)


class EmbeddingServiceTests(unittest.TestCase):
    def test_embeds_in_batches_and_restores_provider_indexes(self):
        client = _FakeClient(
            [
                [
                    SimpleNamespace(index=1, embedding=[0.2, 0.3]),
                    SimpleNamespace(index=0, embedding=[0.0, 0.1]),
                ],
                [SimpleNamespace(index=0, embedding=[0.4, 0.5])],
            ]
        )
        settings = EmbeddingSettings(
            base_url="https://example.invalid/v1",
            api_key="test-key",
            model="test-model",
            dimension=2,
            batch_size=2,
            timeout_seconds=30,
        )

        result = embed_texts(
            ["first", "second", "third"],
            settings=settings,
            client=client,
        )

        self.assertEqual(result, [[0.0, 0.1], [0.2, 0.3], [0.4, 0.5]])
        self.assertEqual(
            client.embeddings.calls,
            [("test-model", ["first", "second"]), ("test-model", ["third"])],
        )

    def test_rejects_incomplete_or_wrong_dimension_provider_response(self):
        client = _FakeClient(
            [[SimpleNamespace(index=0, embedding=[0.1])]]
        )
        settings = EmbeddingSettings(
            base_url="https://example.invalid/v1",
            api_key="test-key",
            model="test-model",
            dimension=2,
            batch_size=2,
            timeout_seconds=30,
        )

        with self.assertRaisesRegex(EmbeddingServiceError, "维度"):
            embed_texts(["only"], settings=settings, client=client)

    def test_first_version_rejects_a_non_1024_configured_dimension(self):
        with patch.dict(
            os.environ,
            {
                "EMBEDDING_BASE_URL": "https://example.invalid/v1",
                "EMBEDDING_API_KEY": "test-key",
                "EMBEDDING_MODEL": "text-embedding-v4",
                "EMBEDDING_DIMENSION": "768",
                "EMBEDDING_BATCH_SIZE": "16",
                "EMBEDDING_TIMEOUT_SECONDS": "30",
            },
            clear=False,
        ):
            with self.assertRaisesRegex(
                EmbeddingConfigurationError,
                str(EMBEDDING_DIMENSION),
            ):
                get_embedding_settings()


if __name__ == "__main__":
    unittest.main()
