"""Graphiti-backed memory adapter implementing MemoryServiceBase.

Maps the MemoryServiceBase interface to GraphitiService (Neo4j/FalkorDB).
Used when MEMORY_PROVIDER=graphiti in config.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from second_brain.services.abstract import MemoryServiceBase
from second_brain.services.search_result import SearchResult

if TYPE_CHECKING:
    from second_brain.config import BrainConfig
    from second_brain.services.graphiti import GraphitiService

logger = logging.getLogger(__name__)


class GraphitiMemoryAdapter(MemoryServiceBase):
    """Adapts GraphitiService to the MemoryServiceBase interface.

    Uses config.brain_user_id as the Graphiti group_id for multi-user isolation.
    Methods not supported by Graphiti (get_all, update_memory, delete, get_by_id,
    delete_all) return empty/zero/None values with a debug log.
    """

    def __init__(self, config: "BrainConfig") -> None:
        from second_brain.services.graphiti import GraphitiService
        self._graphiti: GraphitiService = GraphitiService(config)
        self.user_id: str = config.brain_user_id

    async def add(
        self,
        content: str,
        metadata: dict | None = None,
        enable_graph: bool | None = None,
    ) -> dict:
        """Add content as a Graphiti episode. Returns status dict."""
        try:
            await self._graphiti.add_episode(
                content, metadata=metadata, group_id=self.user_id
            )
            return {"status": "ok"}
        except Exception as e:
            logger.debug("GraphitiMemoryAdapter.add error: %s", e)
            return {}

    async def add_with_metadata(
        self,
        content: str,
        metadata: dict,
        enable_graph: bool | None = None,
    ) -> dict:
        """Add content with metadata. Delegates to add()."""
        return await self.add(content, metadata=metadata)

    async def search(
        self,
        query: str,
        limit: int | None = None,
        enable_graph: bool | None = None,
    ) -> SearchResult:
        """Semantic search via GraphitiService with user-scoped group_id."""
        try:
            relations = await self._graphiti.search(
                query, limit=limit or 10, group_id=self.user_id
            )
            return SearchResult(relations=relations)
        except Exception as e:
            logger.debug("GraphitiMemoryAdapter.search error: %s", e)
            return SearchResult()

    async def search_with_filters(
        self,
        query: str,
        metadata_filters: dict | None = None,
        limit: int = 10,
        enable_graph: bool | None = None,
    ) -> SearchResult:
        """Search with metadata filters approximated by appending filter values to query."""
        try:
            if metadata_filters:
                extra = " ".join(str(v) for v in metadata_filters.values())
                query = f"{query} {extra}"
                logger.debug(
                    "GraphitiMemoryAdapter.search_with_filters: no native filter support — "
                    "appending filter terms to query: %r",
                    extra,
                )
            relations = await self._graphiti.search(
                query, limit=limit, group_id=self.user_id
            )
            return SearchResult(relations=relations)
        except Exception as e:
            logger.debug("GraphitiMemoryAdapter.search_with_filters error: %s", e)
            return SearchResult()

    async def search_by_category(
        self, category: str, query: str, limit: int = 10
    ) -> SearchResult:
        """Search by category by prepending category to query string."""
        try:
            combined = f"{category} {query}"
            relations = await self._graphiti.search(
                combined, limit=limit, group_id=self.user_id
            )
            return SearchResult(relations=relations)
        except Exception as e:
            logger.debug("GraphitiMemoryAdapter.search_by_category error: %s", e)
            return SearchResult()

    async def get_all(self) -> list[dict]:
        """Not supported by Graphiti. Returns empty list."""
        logger.debug("GraphitiMemoryAdapter.get_all: not supported by Graphiti, returning []")
        return []

    async def get_memory_count(self) -> int:
        """Not supported by Graphiti. Returns 0."""
        logger.debug(
            "GraphitiMemoryAdapter.get_memory_count: not supported by Graphiti, returning 0"
        )
        return 0

    async def update_memory(
        self, memory_id: str, content: str, metadata: dict | None = None
    ) -> None:
        """Not supported by Graphiti. No-op."""
        logger.debug(
            "GraphitiMemoryAdapter.update_memory(%r): not supported by Graphiti, no-op",
            memory_id,
        )
        return None

    async def delete(self, memory_id: str) -> None:
        """Not supported by Graphiti. No-op."""
        logger.debug(
            "GraphitiMemoryAdapter.delete(%r): not supported by Graphiti, no-op", memory_id
        )
        return None

    async def get_by_id(self, memory_id: str) -> dict | None:
        """Not supported by Graphiti. Returns None."""
        logger.debug(
            "GraphitiMemoryAdapter.get_by_id(%r): not supported by Graphiti, returning None",
            memory_id,
        )
        return None

    async def delete_all(self) -> int:
        """Not supported by Graphiti. Returns 0."""
        logger.debug(
            "GraphitiMemoryAdapter.delete_all: not supported by Graphiti, returning 0"
        )
        return 0

    async def enable_project_graph(self) -> None:
        """Mem0-specific. No-op for Graphiti backend."""
        return None

    async def close(self) -> None:
        """Close underlying Graphiti client if possible."""
        try:
            if hasattr(self._graphiti, "close"):
                await self._graphiti.close()
        except Exception as e:
            logger.debug("GraphitiMemoryAdapter.close error: %s", e)
        return None
