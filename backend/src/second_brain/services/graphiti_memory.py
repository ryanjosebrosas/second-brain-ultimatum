"""Graphiti-backed memory adapter implementing MemoryServiceBase.

Maps the MemoryServiceBase interface to GraphitiService (Neo4j/FalkorDB).
Used when MEMORY_PROVIDER=graphiti in config.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING

from second_brain.services.abstract import MemoryServiceBase
from second_brain.services.retry import _GRAPHITI_ADAPTER_RETRY
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
        self._config = config
        self.user_id: str = config.brain_user_id
        self._timeout: int = config.service_timeout_seconds
        self._last_activity: float = time.monotonic()
        self._idle_threshold: int = 240  # 4 minutes (< 5 min typical timeout)
        self._graphiti: "GraphitiService" = self._init_graphiti()

    def _effective_user_id(self, override: str | None = None) -> str:
        """Return override if provided, else self.user_id (from config)."""
        return override if override else self.user_id

    def _init_graphiti(self) -> "GraphitiService":
        """Initialize or re-initialize GraphitiService."""
        from second_brain.services.graphiti import GraphitiService
        logger.info("GraphitiService client initialized")
        return GraphitiService(self._config)

    def _check_idle_reconnect(self) -> None:
        """Re-instantiate GraphitiService if idle for too long."""
        elapsed = time.monotonic() - self._last_activity
        if elapsed > self._idle_threshold:
            logger.debug("Graphiti idle for %.0fs, re-instantiating client", elapsed)
            self._graphiti = self._init_graphiti()
        self._last_activity = time.monotonic()

    async def add(
        self,
        content: str,
        metadata: dict | None = None,
        enable_graph: bool | None = None,
    ) -> dict:
        """Add content as a Graphiti episode. Returns status dict."""
        self._check_idle_reconnect()
        try:
            @_GRAPHITI_ADAPTER_RETRY
            async def _add():
                return await self._graphiti.add_episode(
                    content, metadata=metadata, group_id=self.user_id
                )

            async with asyncio.timeout(self._timeout):
                await _add()
            return {"status": "ok"}
        except asyncio.TimeoutError:
            logger.warning("GraphitiMemoryAdapter.add timed out after %ds", self._timeout)
            return {}
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
        override_user_id: str | None = None,
        filter_memories: bool | None = None,
        use_criteria: bool | None = None,
    ) -> SearchResult:
        """Semantic search via GraphitiService with user-scoped group_id.

        Populates BOTH memories (for reranking/formatting) and relations (for graph display).
        """
        self._check_idle_reconnect()
        try:
            @_GRAPHITI_ADAPTER_RETRY
            async def _search():
                return await self._graphiti.search(
                    query, limit=limit or 10, group_id=self._effective_user_id(override_user_id)
                )

            async with asyncio.timeout(self._timeout):
                relations = await _search()
            return SearchResult(
                memories=_relations_to_memories(relations),
                relations=relations,
            )
        except asyncio.TimeoutError:
            logger.warning("GraphitiMemoryAdapter.search timed out after %ds", self._timeout)
            return SearchResult()
        except Exception as e:
            logger.debug("GraphitiMemoryAdapter.search error: %s", e)
            return SearchResult()

    async def search_with_filters(
        self,
        query: str,
        metadata_filters: dict | None = None,
        limit: int = 10,
        enable_graph: bool | None = None,
        override_user_id: str | None = None,
        filter_memories: bool | None = None,
        use_criteria: bool | None = None,
    ) -> SearchResult:
        """Search with metadata filters approximated via query augmentation.

        Supports common filter patterns:
        - {"category": "pattern"} → prepends category to query
        - {"AND": [{"key": "val"}, ...]} → extracts values, prepends to query
        - {"key": {"in": [...]}} → joins list values, prepends to query
        """
        self._check_idle_reconnect()
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
            @_GRAPHITI_ADAPTER_RETRY
            async def _search():
                return await self._graphiti.search(
                    augmented_query, limit=limit, group_id=self._effective_user_id(override_user_id)
                )

            async with asyncio.timeout(self._timeout):
                relations = await _search()
            return SearchResult(
                memories=_relations_to_memories(relations),
                relations=relations,
                search_filters=metadata_filters or {},
            )
        except asyncio.TimeoutError:
            logger.warning("GraphitiMemoryAdapter.search_with_filters timed out after %ds", self._timeout)
            return SearchResult(search_filters=metadata_filters or {})
        except Exception as e:
            logger.debug("GraphitiMemoryAdapter.search_with_filters error: %s", e)
            return SearchResult(search_filters=metadata_filters or {})

    async def search_by_category(
        self, category: str, query: str = "", limit: int = 10,
        override_user_id: str | None = None,
    ) -> SearchResult:
        """Search by category by prepending category to query string."""
        self._check_idle_reconnect()
        try:
            combined = f"{category} {query}"

            @_GRAPHITI_ADAPTER_RETRY
            async def _search():
                return await self._graphiti.search(
                    combined, limit=limit, group_id=self._effective_user_id(override_user_id)
                )

            async with asyncio.timeout(self._timeout):
                relations = await _search()
            return SearchResult(
                memories=_relations_to_memories(relations),
                relations=relations,
            )
        except asyncio.TimeoutError:
            logger.warning("GraphitiMemoryAdapter.search_by_category timed out after %ds", self._timeout)
            return SearchResult()
        except Exception as e:
            logger.debug("GraphitiMemoryAdapter.search_by_category error: %s", e)
            return SearchResult()

    async def get_all(self) -> list[dict]:
        """Retrieve all episodes for the current user's group."""
        self._check_idle_reconnect()
        try:
            @_GRAPHITI_ADAPTER_RETRY
            async def _get():
                return await self._graphiti.get_episodes(self.user_id)

            async with asyncio.timeout(self._timeout):
                episodes = await _get()
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
        except asyncio.TimeoutError:
            logger.warning("GraphitiMemoryAdapter.get_all timed out after %ds", self._timeout)
            return []
        except Exception as e:
            logger.warning("GraphitiMemoryAdapter.get_all failed: %s", type(e).__name__)
            logger.debug("GraphitiMemoryAdapter.get_all error detail: %s", e)
            return []

    async def get_memory_count(self) -> int:
        """Count episodes for the current user's group."""
        self._check_idle_reconnect()
        try:
            @_GRAPHITI_ADAPTER_RETRY
            async def _count():
                return await self._graphiti.get_episode_count(self.user_id)

            async with asyncio.timeout(self._timeout):
                return await _count()
        except asyncio.TimeoutError:
            logger.warning("GraphitiMemoryAdapter.get_memory_count timed out after %ds", self._timeout)
            return 0
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
        self._check_idle_reconnect()
        try:
            @_GRAPHITI_ADAPTER_RETRY
            async def _delete():
                return await self._graphiti.remove_episode(memory_id)

            async with asyncio.timeout(self._timeout):
                success = await _delete()
            if not success:
                logger.debug("GraphitiMemoryAdapter.delete: remove_episode returned False for %s", memory_id)
        except asyncio.TimeoutError:
            logger.warning("GraphitiMemoryAdapter.delete timed out after %ds", self._timeout)
        except Exception as e:
            logger.warning("GraphitiMemoryAdapter.delete failed: %s", type(e).__name__)
            logger.debug("GraphitiMemoryAdapter.delete error detail: %s", e)

    async def get_by_id(self, memory_id: str) -> dict | None:
        """Retrieve a specific episode by UUID."""
        self._check_idle_reconnect()
        try:
            @_GRAPHITI_ADAPTER_RETRY
            async def _get():
                return await self._graphiti.get_episode_by_id(memory_id)

            async with asyncio.timeout(self._timeout):
                ep = await _get()
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
        except asyncio.TimeoutError:
            logger.warning("GraphitiMemoryAdapter.get_by_id timed out after %ds", self._timeout)
            return None
        except Exception as e:
            logger.warning("GraphitiMemoryAdapter.get_by_id failed: %s", type(e).__name__)
            logger.debug("GraphitiMemoryAdapter.get_by_id error detail: %s", e)
            return None

    async def delete_all(self) -> int:
        """Delete all episodes for the current user's group."""
        self._check_idle_reconnect()
        try:
            @_GRAPHITI_ADAPTER_RETRY
            async def _delete_all():
                return await self._graphiti.delete_group_data(self.user_id)

            async with asyncio.timeout(self._timeout):
                return await _delete_all()
        except asyncio.TimeoutError:
            logger.warning("GraphitiMemoryAdapter.delete_all timed out after %ds", self._timeout)
            return 0
        except Exception as e:
            logger.warning("GraphitiMemoryAdapter.delete_all failed: %s", type(e).__name__)
            logger.debug("GraphitiMemoryAdapter.delete_all error detail: %s", e)
            return 0

    async def enable_project_graph(self) -> None:
        """Mem0-specific. No-op for Graphiti backend."""
        logger.warning(
            "enable_project_graph() called on GraphitiMemoryAdapter — "
            "feature not supported. Graphiti graph is always enabled."
        )
        return None

    async def setup_criteria_retrieval(
        self,
        criteria: list[dict] | None = None,
    ) -> bool:
        """Mem0-specific. No-op for Graphiti backend."""
        logger.warning(
            "setup_criteria_retrieval() called on GraphitiMemoryAdapter — "
            "feature not supported. Criteria retrieval is Mem0-only."
        )
        return True  # Keep return True for compatibility

    async def setup_custom_instructions(
        self,
        instructions: str | None = None,
    ) -> bool:
        """Mem0-specific. No-op for Graphiti backend."""
        logger.warning(
            "setup_custom_instructions() called on GraphitiMemoryAdapter — "
            "feature not supported. Custom instructions are Mem0-only."
        )
        return True  # Keep return True for compatibility

    async def close(self) -> None:
        """Close underlying Graphiti client if possible."""
        try:
            if hasattr(self._graphiti, "close"):
                await self._graphiti.close()
        except Exception as e:
            logger.debug("GraphitiMemoryAdapter.close error: %s", e)
        return None
