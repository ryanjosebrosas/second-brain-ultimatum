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
            result = client.multimodal_embed(
                [[text]],
                model=self._embed_model,
                input_type="document",
            )
            return result.embeddings[0]

        return await async_retry(_call)

    async def embed_query(self, text: str) -> list[float]:
        """Generate embedding for a search query (uses input_type='query')."""
        from second_brain.services.retry import async_retry
        client = self._get_client()

        def _call():
            result = client.multimodal_embed(
                [[text]],
                model=self._embed_model,
                input_type="query",
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
                inputs = [[t] for t in b]
                result = client.multimodal_embed(
                    inputs,
                    model=self._embed_model,
                    input_type=input_type,
                )
                return result.embeddings

            embeddings = await async_retry(_call)
            all_embeddings.extend(embeddings)

        return all_embeddings

    async def multimodal_embed(
        self,
        inputs: list[list],
        input_type: str = "document",
    ) -> list[list[float]]:
        """Generate multimodal embeddings for mixed content (text, images, video).

        Args:
            inputs: List of input sequences. Each sequence is a list of mixed
                content items: str (text), PIL.Image.Image, or
                voyageai.video_utils.Video objects.
                Example: [["description text", PIL.Image.open("photo.jpg")]]
            input_type: "document" for storage, "query" for search.

        Returns:
            List of embedding vectors (one per input sequence).
        """
        from second_brain.services.retry import async_retry
        client = self._get_client()

        def _call():
            result = client.multimodal_embed(
                inputs,
                model=self._embed_model,
                input_type=input_type,
            )
            return result.embeddings

        return await async_retry(_call)

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

    async def rerank_with_instructions(
        self,
        query: str,
        documents: list[str],
        instruction: str | None = None,
        top_k: int | None = None,
    ) -> list[dict]:
        """Rerank with optional instruction prepended to query.

        Uses rerank-2.5/2.5-lite instruction-following: prepend a contextual
        instruction to guide ranking priorities (e.g., "Prioritize recent
        patterns over older observations").

        Args:
            query: The search query.
            documents: List of document strings to rerank.
            instruction: Optional instruction to prepend. None = standard rerank.
            top_k: Number of top results. None = use config default.

        Returns:
            Same format as rerank(): list of dicts with 'index', 'document', 'relevance_score'.
        """
        if instruction:
            full_query = f"{instruction}\n\nQuery: {query}"
        else:
            full_query = query
        return await self.rerank(full_query, documents, top_k=top_k)

    async def close(self) -> None:
        """Release Voyage client resources."""
        self._client = None
