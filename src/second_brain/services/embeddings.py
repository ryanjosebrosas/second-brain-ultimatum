"""Embedding generation service using OpenAI text-embedding-3-small."""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from second_brain.config import BrainConfig

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Generate text embeddings via OpenAI API.

    Uses text-embedding-3-small by default (1536 dimensions).
    Supports single and batch embedding generation.
    """

    def __init__(self, config: "BrainConfig"):
        self.config = config
        self._client = None
        self._model = config.embedding_model
        self._dimensions = config.embedding_dimensions

    def _get_client(self):
        """Lazy-init OpenAI client."""
        if self._client is None:
            if not self.config.openai_api_key:
                raise ValueError(
                    "OPENAI_API_KEY required for embedding generation. "
                    "Set it in .env or pass via config."
                )
            from openai import OpenAI
            self._client = OpenAI(api_key=self.config.openai_api_key)
        return self._client

    async def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text string."""
        from second_brain.services.retry import async_retry
        client = self._get_client()

        def _call():
            response = client.embeddings.create(
                input=text,
                model=self._model,
                dimensions=self._dimensions,
            )
            return response.data[0].embedding

        return await async_retry(_call)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a batch of texts.

        Respects config.embedding_batch_size for chunking.
        Returns list of embeddings in same order as input texts.
        """
        from second_brain.services.retry import async_retry
        client = self._get_client()
        batch_size = self.config.embedding_batch_size
        all_embeddings: list[list[float]] = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            def _call(b=batch):
                response = client.embeddings.create(
                    input=b,
                    model=self._model,
                    dimensions=self._dimensions,
                )
                return [item.embedding for item in response.data]

            embeddings = await async_retry(_call)
            all_embeddings.extend(embeddings)

        return all_embeddings

    async def close(self) -> None:
        """Release OpenAI client resources."""
        self._client = None
