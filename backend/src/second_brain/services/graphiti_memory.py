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


def _relations_to_memories(relations: list[dict]) -> list[dict]:
    """Convert graph relation dicts to memory-format dicts.

    Memory format: {"memory": str, "score": float, "metadata": dict}
    This enables format_memories() and rerank_memories() to work with graph results.
    """
    return [
        {
            "memory": f"{r.get('source', '?')} {r.get('relationship', '?')} {r.get('target', '?')}",
            "score": 1.0,
            "metadata": {"source": "graphiti", "type": "relation"},
        }
        for r in relations
    ]


class GraphitiMemoryAdapter(MemoryServiceBase):
    """Adapts GraphitiService to the MemoryServiceBase interface.

    Uses config.brain_user_id as the Graphiti group_id for multi-user isolation.
    All MemoryServiceBase methods are implemented except enable_project_graph
    (Mem0-specific, documented no-op).
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

    async def add_multimodal(
        self,
        content_blocks: list[dict],
        metadata: dict | None = None,
        enable_graph: bool | None = None,
    ) -> dict:
        """Add multimodal content — extracts text blocks only (Graphiti is text-only).

        Non-text content blocks (images, PDFs, videos) are skipped with a debug log.
        """
        text_parts = []
        for block in content_blocks:
            block_type = block.get("type", "")
            if block_type == "text":
                text_parts.append(block.get("text", ""))
            else:
                logger.debug(
                    "GraphitiMemoryAdapter.add_multimodal: skipping %s block (text-only)",
                    block_type,
                )

        if not text_parts:
            logger.debug("GraphitiMemoryAdapter.add_multimodal: no text blocks, skipping")
            return {}

        combined_text = "\n".join(text_parts)
        return await self.add(combined_text, metadata=metadata)

    async def search(
        self,
        query: str,
        limit: int | None = None,
        enable_graph: bool | None = None,
    ) -> SearchResult:
        """Semantic search via GraphitiService with user-scoped group_id.

        Populates BOTH memories (for reranking/formatting) and relations (for graph display).
        """
        try:
            relations = await self._graphiti.search(
                query, limit=limit or 10, group_id=self.user_id
            )
            return SearchResult(
                memories=_relations_to_memories(relations),
                relations=relations,
            )
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
        """Search with metadata filters approximated via query augmentation.

        Supports common filter patterns:
        - {"category": "pattern"} → prepends category to query
        - {"AND": [{"key": "val"}, ...]} → extracts values, prepends to query
        - {"key": {"in": [...]}} → joins list values, prepends to query
        """
        augmented_query = query
        if metadata_filters:
            parts: list[str] = []
            for key, value in metadata_filters.items():
                if key == "AND" and isinstance(value, list):
                    for clause in value:
                        if isinstance(clause, dict):
                            parts.extend(str(v) for v in clause.values())
                elif isinstance(value, dict) and "in" in value:
                    parts.extend(str(v) for v in value["in"])
                elif isinstance(value, dict):
                    parts.extend(str(v) for v in value.values())
                else:
                    parts.append(str(value))
            if parts:
                augmented_query = f"{' '.join(parts)} {query}"
                logger.debug(
                    "GraphitiMemoryAdapter.search_with_filters: augmented query: %r",
                    augmented_query,
                )
        try:
            relations = await self._graphiti.search(
                augmented_query, limit=limit, group_id=self.user_id
            )
            return SearchResult(
                memories=_relations_to_memories(relations),
                relations=relations,
                search_filters=metadata_filters or {},
            )
        except Exception as e:
            logger.debug("GraphitiMemoryAdapter.search_with_filters error: %s", e)
            return SearchResult(search_filters=metadata_filters or {})

    async def search_by_category(
        self, category: str, query: str, limit: int = 10
    ) -> SearchResult:
        """Search by category by prepending category to query string."""
        try:
            combined = f"{category} {query}"
            relations = await self._graphiti.search(
                combined, limit=limit, group_id=self.user_id
            )
            return SearchResult(
                memories=_relations_to_memories(relations),
                relations=relations,
            )
        except Exception as e:
            logger.debug("GraphitiMemoryAdapter.search_by_category error: %s", e)
            return SearchResult()

    async def get_all(self) -> list[dict]:
        """Retrieve all episodes for the current user's group."""
        try:
            episodes = await self._graphiti.get_episodes(self.user_id)
            return [
                {
                    "id": ep.get("id", ""),
                    "memory": ep.get("content", ""),
                    "metadata": {
                        "source": ep.get("source", "unknown"),
                        "created_at": ep.get("created_at"),
                    },
                }
                for ep in episodes
            ]
        except Exception as e:
            logger.warning("GraphitiMemoryAdapter.get_all failed: %s", type(e).__name__)
            logger.debug("GraphitiMemoryAdapter.get_all error detail: %s", e)
            return []

    async def get_memory_count(self) -> int:
        """Count episodes for the current user's group."""
        try:
            return await self._graphiti.get_episode_count(self.user_id)
        except Exception as e:
            logger.warning("GraphitiMemoryAdapter.get_memory_count failed: %s", type(e).__name__)
            logger.debug("GraphitiMemoryAdapter.get_memory_count error detail: %s", e)
            return 0

    async def update_memory(
        self, memory_id: str, content: str | None = None, metadata: dict | None = None
    ) -> None:
        """Update a memory by deleting the old episode and adding a new one."""
        if not content:
            logger.debug("GraphitiMemoryAdapter.update_memory: no content provided, skipping")
            return
        try:
            await self.delete(memory_id)
            await self.add(content, metadata=metadata)
            logger.debug("GraphitiMemoryAdapter.update_memory: replaced episode %s", memory_id)
        except Exception as e:
            logger.warning("GraphitiMemoryAdapter.update_memory failed: %s", type(e).__name__)
            logger.debug("GraphitiMemoryAdapter.update_memory error detail: %s", e)

    async def delete(self, memory_id: str) -> None:
        """Delete a memory (episode) by its UUID."""
        try:
            success = await self._graphiti.remove_episode(memory_id)
            if not success:
                logger.debug("GraphitiMemoryAdapter.delete: remove_episode returned False for %s", memory_id)
        except Exception as e:
            logger.warning("GraphitiMemoryAdapter.delete failed: %s", type(e).__name__)
            logger.debug("GraphitiMemoryAdapter.delete error detail: %s", e)

    async def get_by_id(self, memory_id: str) -> dict | None:
        """Retrieve a specific episode by UUID."""
        try:
            ep = await self._graphiti.get_episode_by_id(memory_id)
            if ep is None:
                return None
            return {
                "id": ep.get("id", ""),
                "memory": ep.get("content", ""),
                "metadata": {
                    "source": ep.get("source", "unknown"),
                    "created_at": ep.get("created_at"),
                },
            }
        except Exception as e:
            logger.warning("GraphitiMemoryAdapter.get_by_id failed: %s", type(e).__name__)
            logger.debug("GraphitiMemoryAdapter.get_by_id error detail: %s", e)
            return None

    async def delete_all(self) -> int:
        """Delete all episodes for the current user's group."""
        try:
            return await self._graphiti.delete_group_data(self.user_id)
        except Exception as e:
            logger.warning("GraphitiMemoryAdapter.delete_all failed: %s", type(e).__name__)
            logger.debug("GraphitiMemoryAdapter.delete_all error detail: %s", e)
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
