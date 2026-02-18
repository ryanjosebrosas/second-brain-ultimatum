"""Voyage AI embedding and reranking service."""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from second_brain.config import BrainConfig

logger = logging.getLogger(__name__)


class VoyageService:
    """Voyage AI embeddings + reranking via voyageai Python SDK.

    Provides embed(), embed_batch() for vector generation and
    rerank() for post-retrieval relevance scoring.
    """

    def __init__(self, config: "BrainConfig"):
        self.config = config
        self._client = None
        self._embed_model = config.voyage_embedding_model
        self._rerank_model = config.voyage_rerank_model
        self._dimensions = config.embedding_dimensions

    def _get_client(self):
        """Lazy-init Voyage client."""
        if self._client is None:
            if not self.config.voyage_api_key:
                raise ValueError(
                    "VOYAGE_API_KEY required for Voyage AI. "
                    "Set it in .env or pass via config."
                )
            import voyageai
            self._client = voyageai.Client(api_key=self.config.voyage_api_key)
        return self._client

    async def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text string."""
        from second_brain.services.retry import async_retry
        client = self._get_client()

        def _call():
            result = client.embed(
                [text],
                model=self._embed_model,
                input_type="document",
                output_dimension=self._dimensions,
            )
            return result.embeddings[0]

        return await async_retry(_call)

    async def embed_query(self, text: str) -> list[float]:
        """Generate embedding for a search query (uses input_type='query')."""
        from second_brain.services.retry import async_retry
        client = self._get_client()

        def _call():
            result = client.embed(
                [text],
                model=self._embed_model,
                input_type="query",
                output_dimension=self._dimensions,
            )
            return result.embeddings[0]

        return await async_retry(_call)

    async def embed_batch(
        self, texts: list[str], input_type: str = "document"
    ) -> list[list[float]]:
        """Generate embeddings for a batch of texts.

        Respects Voyage batch limit of 128 items per request.
        """
        from second_brain.services.retry import async_retry
        client = self._get_client()
        batch_size = min(self.config.embedding_batch_size, 128)
        all_embeddings: list[list[float]] = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            def _call(b=batch):
                result = client.embed(
                    b,
                    model=self._embed_model,
                    input_type=input_type,
                    output_dimension=self._dimensions,
                )
                return result.embeddings

            embeddings = await async_retry(_call)
            all_embeddings.extend(embeddings)

        return all_embeddings

    async def rerank(
        self,
        query: str,
        documents: list[str],
        top_k: int | None = None,
    ) -> list[dict]:
        """Rerank documents by relevance to query.

        Args:
            query: The search query.
            documents: List of document strings to rerank.
            top_k: Number of top results. None = use config default.

        Returns:
            List of dicts with 'index', 'document', 'relevance_score',
            sorted by descending relevance.
        """
        if not documents:
            return []

        from second_brain.services.retry import async_retry
        client = self._get_client()
        k = top_k or self.config.voyage_rerank_top_k

        def _call():
            result = client.rerank(
                query,
                documents,
                model=self._rerank_model,
                top_k=k,
            )
            return [
                {
                    "index": r.index,
                    "document": r.document,
                    "relevance_score": r.relevance_score,
                }
                for r in result.results
            ]

        return await async_retry(_call)

    async def close(self) -> None:
        """Release Voyage client resources."""
        self._client = None
