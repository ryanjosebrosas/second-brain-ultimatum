"""Embedding generation service — Voyage AI primary, OpenAI fallback."""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from second_brain.config import BrainConfig

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Generate text embeddings.

    Uses Voyage AI (voyage-4-lite) when VOYAGE_API_KEY is set.
    Falls back to OpenAI text-embedding-3-small when only OPENAI_API_KEY is set.
    """

    def __init__(self, config: "BrainConfig"):
        self.config = config
        self._voyage = None
        self._openai_client = None
        self._model = config.embedding_model
        self._dimensions = config.embedding_dimensions

        # Determine backend
        if config.voyage_api_key:
            from second_brain.services.voyage import VoyageService
            self._voyage = VoyageService(config)
            logger.info("EmbeddingService using Voyage AI (%s)", config.voyage_embedding_model)
        elif config.openai_api_key:
            logger.info("EmbeddingService using OpenAI fallback (%s)", config.embedding_model)
        else:
            raise ValueError(
                "Either VOYAGE_API_KEY or OPENAI_API_KEY required for embeddings."
            )

    def _get_openai_client(self):
        """Lazy-init OpenAI client (fallback only)."""
        if self._openai_client is None:
            from openai import OpenAI
            self._openai_client = OpenAI(api_key=self.config.openai_api_key)
        return self._openai_client

    async def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text string."""
        if self._voyage:
            return await self._voyage.embed(text)

        from second_brain.services.retry import async_retry
        client = self._get_openai_client()

        def _call():
            response = client.embeddings.create(
                input=text, model=self._model, dimensions=self._dimensions,
            )
            return response.data[0].embedding

        return await async_retry(_call)

    async def embed_query(self, text: str) -> list[float]:
        """Generate embedding optimized for search queries.

        Uses Voyage input_type='query' for better retrieval.
        Falls back to standard embed() for OpenAI.
        """
        if self._voyage:
            return await self._voyage.embed_query(text)
        return await self.embed(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a batch of texts."""
        if self._voyage:
            return await self._voyage.embed_batch(texts)

        from second_brain.services.retry import async_retry
        client = self._get_openai_client()
        batch_size = self.config.embedding_batch_size
        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            def _call(b=batch):
                response = client.embeddings.create(
                    input=b, model=self._model, dimensions=self._dimensions,
                )
                return [item.embedding for item in response.data]

            embeddings = await async_retry(_call)
            all_embeddings.extend(embeddings)
        return all_embeddings

    async def close(self) -> None:
        """Release client resources."""
        if self._voyage:
            await self._voyage.close()
        self._openai_client = None
