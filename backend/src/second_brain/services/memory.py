"""Semantic memory via Mem0 (cloud primary, local fallback)."""

import asyncio
import logging
import time

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from second_brain.config import BrainConfig
from second_brain.services.abstract import MemoryServiceBase
from second_brain.services.search_result import SearchResult

logger = logging.getLogger(__name__)

# Retry config for Mem0 cloud calls — transient errors only
_MEM0_RETRY = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((ConnectionError, TimeoutError, OSError)),
    reraise=True,
)


class MemoryService(MemoryServiceBase):
    """Semantic memory via Mem0 (cloud primary, local fallback)."""

    def __init__(self, config: BrainConfig):
        self.config = config
        self.user_id = config.brain_user_id
        self.enable_graph = config.graph_provider == "mem0"
        self._timeout = config.service_timeout_seconds
        self._last_activity: float = time.monotonic()
        self._idle_threshold: int = 240  # 4 minutes (< 5 min Mem0 timeout)
        self._client = self._init_client()

    def _init_client(self):
        """Initialize Mem0 -- try cloud first, fall back to local OSS."""
        if self.config.mem0_api_key:
            try:
                from mem0 import MemoryClient

                client = MemoryClient(api_key=self.config.mem0_api_key)
                logger.info("Using Mem0 cloud client")
                return client
            except Exception as e:
                logger.warning(f"Mem0 cloud unavailable: {e}")

        from mem0 import Memory

        mem0_config = {
            "llm": {
                "provider": "anthropic",
                "config": {
                    "model": "claude-sonnet-4-5-20250929",
                    "temperature": 0.1,
                    "max_tokens": 2000,
                    "api_key": self.config.anthropic_api_key,
                },
            }
        }
        if self.enable_graph and self.config.neo4j_url:
            mem0_config["graph_store"] = {
                "provider": "neo4j",
                "config": {
                    "url": self.config.neo4j_url,
                    "username": self.config.neo4j_username,
                    "password": self.config.neo4j_password,
                },
            }
        try:
            logger.info("Using Mem0 local client")
            return Memory.from_config(mem0_config)
        except Exception as e:
            logger.error("Failed to initialize Mem0 local client: %s", e)
            raise

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
        if use_graph and self._is_cloud:
            kwargs["enable_graph"] = True
        try:
            if self._is_cloud:
                @_MEM0_RETRY
                def _add():
                    return self._client.add(messages, **kwargs)
            else:
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
        messages = [{"role": "user", "content": content}]
        kwargs: dict = {
            "user_id": self.user_id,
            "metadata": metadata,
        }
        use_graph = enable_graph if enable_graph is not None else self.enable_graph
        if use_graph and self._is_cloud:
            kwargs["enable_graph"] = True
        try:
            result = await asyncio.to_thread(self._client.add, messages, **kwargs)
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
        if use_graph and self._is_cloud:
            kwargs["enable_graph"] = True

        try:
            result = await asyncio.to_thread(self._client.add, messages, **kwargs)
            return result
        except Exception as e:
            logger.warning("Mem0 add_multimodal failed: %s", type(e).__name__)
            logger.debug("Mem0 add_multimodal error detail: %s", e)
            return {}

    @property
    def _is_cloud(self) -> bool:
        return type(self._client).__name__ == "MemoryClient"

    def _check_idle_reconnect(self) -> None:
        """Re-instantiate client if idle for too long (Mem0 timeout workaround)."""
        elapsed = time.monotonic() - self._last_activity
        if elapsed > self._idle_threshold and self._is_cloud:
            logger.debug("Mem0 idle for %.0fs, re-instantiating client", elapsed)
            self._client = self._init_client()
        self._last_activity = time.monotonic()

    async def enable_project_graph(self) -> None:
        """Enable graph memory at Mem0 Cloud project level."""
        if not self._is_cloud:
            logger.warning("Project-level graph requires Mem0 Cloud client — skipping")
            return
        if not self.enable_graph:
            logger.warning("Graph provider is not 'mem0' — skipping project graph enablement")
            return
        try:
            await asyncio.to_thread(lambda: self._client.project.update(enable_graph=True))
            logger.info("Enabled graph memory at Mem0 project level")
        except Exception as e:
            logger.error(f"Failed to enable project-level graph: {e}")

    async def search(self, query: str, limit: int | None = None,
                     enable_graph: bool | None = None) -> SearchResult:
        """Semantic search across memories."""
        self._check_idle_reconnect()
        limit = limit if limit is not None else self.config.memory_search_limit
        kwargs: dict = {"user_id": self.user_id}
        use_graph = enable_graph if enable_graph is not None else self.enable_graph
        if self._is_cloud:
            kwargs["filters"] = {"user_id": self.user_id}
            if use_graph:
                kwargs["enable_graph"] = True
        try:
            if self._is_cloud:
                @_MEM0_RETRY
                def _search():
                    return self._client.search(query, **kwargs)
            else:
                def _search():
                    return self._client.search(query, **kwargs)

            async with asyncio.timeout(self._timeout):
                results = await asyncio.to_thread(_search)
        except Exception as e:
            logger.warning("Mem0 search failed: %s", type(e).__name__)
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
        """
        self._check_idle_reconnect()
        limit = limit if limit is not None else self.config.memory_search_limit
        kwargs: dict = {"user_id": self.user_id}
        use_graph = enable_graph if enable_graph is not None else self.enable_graph

        if self._is_cloud:
            # Cloud client merges user_id into filters
            base_filters: dict = {"user_id": self.user_id}
            if metadata_filters:
                # Combine user filter with metadata filters using AND
                base_filters = {
                    "AND": [
                        {"user_id": self.user_id},
                        metadata_filters,
                    ]
                }
            kwargs["filters"] = base_filters
            if use_graph:
                kwargs["enable_graph"] = True
        else:
            # Local client: pass filters directly if supported
            if metadata_filters:
                kwargs["filters"] = metadata_filters

        try:
            if self._is_cloud:
                @_MEM0_RETRY
                def _search():
                    return self._client.search(query, **kwargs)

                @_MEM0_RETRY
                def _search_no_filters():
                    kw = {k: v for k, v in kwargs.items() if k != "filters"}
                    return self._client.search(query, **kw)
            else:
                def _search():
                    return self._client.search(query, **kwargs)

                def _search_no_filters():
                    kw = {k: v for k, v in kwargs.items() if k != "filters"}
                    return self._client.search(query, **kw)

            try:
                async with asyncio.timeout(self._timeout):
                    results = await asyncio.to_thread(_search)
            except TypeError:
                logger.warning("Mem0 client doesn't support filters, falling back to unfiltered search")
                async with asyncio.timeout(self._timeout):
                    results = await asyncio.to_thread(_search_no_filters)
        except Exception as e:
            logger.warning("Mem0 search_with_filters failed: %s", type(e).__name__)
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
        try:
            if self._is_cloud:
                kwargs: dict = {}
                if content is not None:
                    kwargs["text"] = content
                if metadata is not None:
                    kwargs["metadata"] = metadata
                if kwargs:
                    await asyncio.to_thread(
                        self._client.update, memory_id=memory_id, **kwargs
                    )
            else:
                # Local client only supports data= parameter
                if content is not None:
                    await asyncio.to_thread(
                        self._client.update, memory_id=memory_id, data=content
                    )
                elif metadata is not None:
                    logger.warning("Local Mem0 client doesn't support metadata-only updates")
        except Exception as e:
            logger.warning("Mem0 update_memory failed: %s", type(e).__name__)
            logger.debug("Mem0 update_memory error detail: %s", e)

    async def get_all(self) -> list[dict]:
        """Get all memories for the user."""
        try:
            kwargs: dict = {"user_id": self.user_id}
            if self._is_cloud:
                kwargs["filters"] = {"user_id": self.user_id}
            results = await asyncio.to_thread(self._client.get_all, **kwargs)
            if isinstance(results, dict):
                return results.get("results", [])
            return results
        except Exception as e:
            logger.warning("Mem0 get_all failed: %s", type(e).__name__)
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
        try:
            await asyncio.to_thread(self._client.delete, memory_id)
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
    ) -> SearchResult:
        """Convenience wrapper — search memories filtered by category metadata.

        Args:
            category: Category to filter by (e.g., voice, content, clients)
            query: Natural language search query (defaults to category name if empty)
            limit: Maximum results

        Returns:
            SearchResult with matches in this category.
        """
        return await self.search_with_filters(
            query=query or category,
            metadata_filters={"category": category},
            limit=limit,
        )

    async def close(self) -> None:
        """Release Mem0 client resources."""
        if hasattr(self._client, "close"):
            await asyncio.to_thread(self._client.close)
        self._client = None
