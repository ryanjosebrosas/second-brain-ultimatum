"""Semantic memory via Mem0 Cloud."""

import asyncio
import logging
import time

from second_brain.config import BrainConfig
from second_brain.services.retry import _MEM0_RETRY
from second_brain.services.abstract import MemoryServiceBase
from second_brain.services.search_result import SearchResult

logger = logging.getLogger(__name__)

# Mem0 v2 API built-in filter keys — anything else is custom metadata
_V2_BUILTIN_KEYS = frozenset({
    "user_id", "agent_id", "app_id", "run_id",
    "created_at", "updated_at", "timestamp", "text",
    "categories", "metadata", "keywords_search",
    "memory_ids", "keywords", "AND", "OR", "NOT",
})


def _wrap_metadata_filter(condition: dict) -> dict:
    """Wrap custom metadata keys for Mem0 v2 API.

    Mem0 v2 only accepts built-in keys as top-level filters.
    Custom keys like {"category": "pattern"} must become
    {"metadata": {"category": "pattern"}}.
    """
    if not condition or not isinstance(condition, dict):
        return condition
    key = next(iter(condition))
    # Logical operators — recurse into their condition lists
    if key in ("AND", "OR", "NOT"):
        return {key: [_wrap_metadata_filter(c) for c in condition[key]]}
    # Built-in key — pass through
    if key in _V2_BUILTIN_KEYS:
        return condition
    # Custom metadata key — wrap
    return {"metadata": condition}


class MemoryService(MemoryServiceBase):
    """Semantic memory via Mem0 Cloud. Requires mem0_api_key."""

    def __init__(self, config: BrainConfig):
        self.config = config
        self.user_id = config.brain_user_id
        self.enable_graph = config.graph_provider == "mem0"
        self._timeout = config.service_timeout_seconds
        self._last_activity: float = time.monotonic()
        self._idle_threshold: int = 240  # 4 minutes (< 5 min Mem0 timeout)
        self._client = self._init_client()

    def _init_client(self):
        """Initialize Mem0 cloud client. Requires mem0_api_key."""
        if not self.config.mem0_api_key:
            raise ValueError(
                "mem0_api_key is required for MemoryService. "
                "Set MEM0_API_KEY in .env or use MEMORY_PROVIDER=graphiti for OSS fallback."
            )
        from mem0 import MemoryClient

        client = MemoryClient(api_key=self.config.mem0_api_key)
        logger.info("Mem0 cloud client initialized")
        return client

    async def add(self, content: str, metadata: dict | None = None,
                  enable_graph: bool | None = None) -> dict:
        """Add a memory. Content is auto-extracted into facts by Mem0."""
        self._check_idle_reconnect()
        messages = [{"role": "user", "content": content}]
        kwargs: dict = {
            "user_id": self.user_id,
            "metadata": metadata or {},
        }
        use_graph = enable_graph if enable_graph is not None else self.enable_graph
        if use_graph:
            kwargs["enable_graph"] = True
        try:
            @_MEM0_RETRY
            def _add():
                return self._client.add(messages, **kwargs)

            async with asyncio.timeout(self._timeout):
                result = await asyncio.to_thread(_add)
            return result
        except Exception as e:
            logger.warning("Mem0 add failed: %s", type(e).__name__)
            logger.debug("Mem0 add error detail: %s", e)
            return {}

    async def add_with_metadata(
        self,
        content: str,
        metadata: dict,
        enable_graph: bool | None = None,
    ) -> dict:
        """Add a memory with required structured metadata for filtered retrieval.

        Unlike add(), this method requires metadata and formats the content
        as a declarative statement (not a conversation) for better extraction.

        Args:
            content: The memory content as a declarative statement.
            metadata: Required metadata dict (category, etc.). Must be <2KB.
            enable_graph: Override graph setting. None = use config default.
        """
        self._check_idle_reconnect()
        messages = [{"role": "user", "content": content}]
        kwargs: dict = {
            "user_id": self.user_id,
            "metadata": metadata,
        }
        use_graph = enable_graph if enable_graph is not None else self.enable_graph
        if use_graph:
            kwargs["enable_graph"] = True
        try:
            @_MEM0_RETRY
            def _add():
                return self._client.add(messages, **kwargs)

            async with asyncio.timeout(self._timeout):
                result = await asyncio.to_thread(_add)
            return result
        except Exception as e:
            logger.warning("Mem0 add_with_metadata failed: %s", type(e).__name__)
            logger.debug("Mem0 add_with_metadata error detail: %s", e)
            return {}

    async def add_multimodal(
        self,
        content_blocks: list[dict],
        metadata: dict | None = None,
        enable_graph: bool | None = None,
    ) -> dict:
        """Add a multimodal memory (images, PDFs, documents).

        Constructs Mem0 multimodal messages from content blocks and stores them.

        Args:
            content_blocks: List of content block dicts. Each has a 'type' and
                type-specific nested dict. Supported types:
                - {"type": "image_url", "image_url": {"url": "https://... or data:image/...;base64,..."}}
                - {"type": "pdf_url", "pdf_url": {"url": "https://..."}}
                - {"type": "mdx_url", "mdx_url": {"url": "https://... or raw_base64_string"}}
                - {"type": "text", "text": "descriptive context"}
            metadata: Optional metadata dict.
            enable_graph: Override graph setting. None = use config default.

        Returns:
            Result dict from Mem0 (may be empty on failure).
        """
        self._check_idle_reconnect()
        messages = []
        for block in content_blocks:
            block_type = block.get("type", "")
            if block_type == "text":
                messages.append({"role": "user", "content": block.get("text", "")})
            elif block_type in ("image_url", "pdf_url", "mdx_url"):
                messages.append({"role": "user", "content": block})
            else:
                logger.warning("Unsupported multimodal block type: %s", block_type)
                continue

        if not messages:
            logger.warning("No valid multimodal content blocks provided")
            return {}

        kwargs: dict = {
            "user_id": self.user_id,
            "metadata": metadata or {},
        }
        use_graph = enable_graph if enable_graph is not None else self.enable_graph
        if use_graph:
            kwargs["enable_graph"] = True

        try:
            @_MEM0_RETRY
            def _add():
                return self._client.add(messages, **kwargs)

            async with asyncio.timeout(self._timeout):
                result = await asyncio.to_thread(_add)
            return result
        except Exception as e:
            logger.warning("Mem0 add_multimodal failed: %s", type(e).__name__)
            logger.debug("Mem0 add_multimodal error detail: %s", e)
            return {}

    def _effective_user_id(self, override: str | None = None) -> str:
        """Return override if provided, else self.user_id (from config)."""
        return override if override else self.user_id

    def _check_idle_reconnect(self) -> None:
        """Re-instantiate client if idle for too long (Mem0 timeout workaround)."""
        elapsed = time.monotonic() - self._last_activity
        if elapsed > self._idle_threshold:
            logger.debug("Mem0 idle for %.0fs, re-instantiating client", elapsed)
            self._client = self._init_client()
        self._last_activity = time.monotonic()

    async def enable_project_graph(self) -> None:
        """Enable graph memory at Mem0 Cloud project level."""
        if not self.enable_graph:
            logger.warning("Graph provider is not 'mem0' — skipping project graph enablement")
            return
        try:
            await asyncio.to_thread(lambda: self._client.project.update(enable_graph=True))
            logger.info("Enabled graph memory at Mem0 project level")
        except Exception as e:
            logger.error("Failed to enable project-level graph: %s", e)

    async def search(self, query: str, limit: int | None = None,
                     enable_graph: bool | None = None,
                     override_user_id: str | None = None) -> SearchResult:
        """Semantic search across memories."""
        self._check_idle_reconnect()
        limit = limit if limit is not None else self.config.memory_search_limit
        uid = self._effective_user_id(override_user_id)
        kwargs: dict = {
            "filters": {"AND": [{"user_id": uid}]},
            "top_k": limit,
        }
        if self.config.mem0_keyword_search:
            kwargs["keyword_search"] = True
        if self.config.mem0_rerank:
            kwargs["rerank"] = True
        try:
            logger.debug("Mem0 search kwargs: %s", {k: v for k, v in kwargs.items() if k != "filters"})

            @_MEM0_RETRY
            def _search():
                return self._client.search(query, version="v2", **kwargs)

            async with asyncio.timeout(self._timeout):
                results = await asyncio.to_thread(_search)
        except Exception as e:
            logger.warning("Mem0 search failed: %s — kwargs keys: %s", type(e).__name__, list(kwargs.keys()))
            logger.debug("Mem0 search error detail: %s", e)
            return SearchResult(memories=[], relations=[])
        if isinstance(results, dict):
            memories = results.get("results", [])
            relations = results.get("relations", [])
            memories = memories[:limit] if isinstance(memories, list) else []
            return SearchResult(memories=memories, relations=relations)
        memories = results[:limit] if isinstance(results, list) else []
        return SearchResult(memories=memories, relations=[])

    async def search_with_filters(
        self,
        query: str,
        metadata_filters: dict | None = None,
        limit: int | None = None,
        enable_graph: bool | None = None,
        override_user_id: str | None = None,
    ) -> SearchResult:
        """Semantic search with metadata filtering.

        Args:
            query: The semantic search query.
            metadata_filters: Mem0 metadata filter dict. Supports operators:
                Simple: {"category": "pattern"}
                Comparison: {"priority": {"gte": 7}}
                List: {"category": {"in": ["pattern", "experience"]}}
                Logical: {"AND": [{"category": "pattern"}, {"topic": "Content"}]}
            limit: Max results (defaults to config.memory_search_limit).
            enable_graph: Override graph setting. None = use config default.
            override_user_id: Override user_id for scoping to a different user.
        """
        self._check_idle_reconnect()
        limit = limit if limit is not None else self.config.memory_search_limit
        uid = self._effective_user_id(override_user_id)

        # Platform API v2: user_id inside filters, custom metadata wrapped
        conditions: list[dict] = [{"user_id": uid}]
        if metadata_filters:
            # Flatten caller's AND conditions to avoid double-nesting
            if isinstance(metadata_filters, dict) and len(metadata_filters) == 1:
                key = next(iter(metadata_filters))
                if key == "AND" and isinstance(metadata_filters[key], list):
                    conditions.extend(
                        _wrap_metadata_filter(c) for c in metadata_filters[key]
                    )
                else:
                    conditions.append(_wrap_metadata_filter(metadata_filters))
            else:
                conditions.append(_wrap_metadata_filter(metadata_filters))
        kwargs: dict = {
            "filters": {"AND": conditions},
            "top_k": limit,
        }
        if self.config.mem0_keyword_search:
            kwargs["keyword_search"] = True
        if self.config.mem0_rerank:
            kwargs["rerank"] = True

        try:
            logger.debug("Mem0 search_with_filters kwargs: %s", {k: v for k, v in kwargs.items() if k != "filters"})

            @_MEM0_RETRY
            def _search():
                return self._client.search(query, version="v2", **kwargs)

            @_MEM0_RETRY
            def _search_no_filters():
                kw = {k: v for k, v in kwargs.items() if k != "filters"}
                return self._client.search(query, version="v2", **kw)

            try:
                async with asyncio.timeout(self._timeout):
                    results = await asyncio.to_thread(_search)
            except TypeError:
                logger.warning("Mem0 client doesn't support filters, falling back to unfiltered search")
                async with asyncio.timeout(self._timeout):
                    results = await asyncio.to_thread(_search_no_filters)
        except Exception as e:
            logger.warning("Mem0 search_with_filters failed: %s — kwargs keys: %s", type(e).__name__, list(kwargs.keys()))
            logger.debug("Mem0 search_with_filters error detail: %s", e)
            return SearchResult(memories=[], relations=[], search_filters=metadata_filters or {})

        if isinstance(results, dict):
            memories = results.get("results", [])
            relations = results.get("relations", [])
            memories = memories[:limit] if isinstance(memories, list) else []
            return SearchResult(
                memories=memories,
                relations=relations,
                search_filters=metadata_filters or {},
            )
        memories = results[:limit] if isinstance(results, list) else []
        return SearchResult(
            memories=memories,
            relations=[],
            search_filters=metadata_filters or {},
        )

    async def update_memory(
        self,
        memory_id: str,
        content: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        """Update an existing memory's content and/or metadata.

        Args:
            memory_id: The Mem0 memory ID to update.
            content: New content text (None = keep existing).
            metadata: New metadata dict (None = keep existing).
        """
        self._check_idle_reconnect()
        try:
            kwargs: dict = {}
            if content is not None:
                kwargs["text"] = content
            if metadata is not None:
                kwargs["metadata"] = metadata
            if kwargs:
                @_MEM0_RETRY
                def _update():
                    return self._client.update(memory_id=memory_id, **kwargs)

                async with asyncio.timeout(self._timeout):
                    await asyncio.to_thread(_update)
        except Exception as e:
            logger.warning("Mem0 update_memory failed: %s", type(e).__name__)
            logger.debug("Mem0 update_memory error detail: %s", e)

    async def get_all(self) -> list[dict]:
        """Get all memories for the user."""
        self._check_idle_reconnect()
        try:
            kwargs: dict = {"user_id": self.user_id}
            logger.debug("Mem0 get_all kwargs: %s", {k: v for k, v in kwargs.items() if k != "filters"})

            @_MEM0_RETRY
            def _get_all():
                return self._client.get_all(**kwargs)

            async with asyncio.timeout(self._timeout):
                results = await asyncio.to_thread(_get_all)

            if isinstance(results, dict):
                return results.get("results", [])
            return results
        except Exception as e:
            logger.warning("Mem0 get_all failed: %s — kwargs keys: %s", type(e).__name__, list(kwargs.keys()))
            logger.debug("Mem0 get_all error detail: %s", e)
            return []

    async def get_memory_count(self) -> int:
        """Get total memory count for the user."""
        try:
            memories = await self.get_all()
            return len(memories)
        except Exception as e:
            logger.warning("Mem0 get_memory_count failed: %s", type(e).__name__)
            logger.debug("Mem0 get_memory_count error detail: %s", e)
            return 0

    async def delete(self, memory_id: str) -> None:
        """Delete a specific memory."""
        self._check_idle_reconnect()
        try:
            @_MEM0_RETRY
            def _delete():
                return self._client.delete(memory_id)

            async with asyncio.timeout(self._timeout):
                await asyncio.to_thread(_delete)
        except Exception as e:
            logger.warning("Mem0 delete failed: %s", type(e).__name__)
            logger.debug("Mem0 delete error detail: %s", e)

    async def get_by_id(self, memory_id: str) -> dict | None:
        """Get a single memory by ID. Fetches all and filters locally (Mem0 limitation).

        Args:
            memory_id: The Mem0 memory UUID

        Returns:
            Memory dict or None if not found.
        """
        try:
            all_memories = await self.get_all()
            for mem in all_memories:
                if mem.get("id") == memory_id:
                    return mem
            return None
        except Exception as e:
            logger.warning("Mem0 get_by_id failed: %s", type(e).__name__)
            logger.debug("Mem0 error detail: %s", e)
            return None

    async def delete_all(self) -> int:
        """Delete all memories. Use with caution — irreversible.

        Returns:
            Count of memories deleted.
        """
        try:
            all_memories = await self.get_all()
            count = 0
            for mem in all_memories:
                if mem_id := mem.get("id"):
                    await self.delete(mem_id)
                    count += 1
            return count
        except Exception as e:
            logger.warning("Mem0 delete_all failed: %s", type(e).__name__)
            logger.debug("Mem0 error detail: %s", e)
            return 0

    async def search_by_category(
        self,
        category: str,
        query: str = "",
        limit: int = 10,
        override_user_id: str | None = None,
    ) -> SearchResult:
        """Convenience wrapper — search memories filtered by category metadata.

        Args:
            category: Category to filter by (e.g., voice, content, clients)
            query: Natural language search query (defaults to category name if empty)
            limit: Maximum results
            override_user_id: Override user_id for scoping to a different user.

        Returns:
            SearchResult with matches in this category.
        """
        return await self.search_with_filters(
            query=query or category,
            metadata_filters={"category": category},
            limit=limit,
            override_user_id=override_user_id,
        )

    async def close(self) -> None:
        """Release Mem0 client resources."""
        if hasattr(self._client, "close"):
            await asyncio.to_thread(self._client.close)
        self._client = None
