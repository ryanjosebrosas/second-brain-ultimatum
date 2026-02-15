"""Semantic memory via Mem0 (cloud primary, local fallback)."""

import logging

from second_brain.config import BrainConfig
from second_brain.services.search_result import SearchResult

logger = logging.getLogger(__name__)


class MemoryService:
    """Semantic memory via Mem0 (cloud primary, local fallback)."""

    def __init__(self, config: BrainConfig):
        self.config = config
        self.user_id = config.brain_user_id
        self.enable_graph = config.graph_provider == "mem0"
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
                    "model": "claude-sonnet-4-20250514",
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
        logger.info("Using Mem0 local client")
        return Memory.from_config(mem0_config)

    async def add(self, content: str, metadata: dict | None = None,
                  enable_graph: bool | None = None) -> dict:
        """Add a memory. Content is auto-extracted into facts by Mem0."""
        messages = [{"role": "user", "content": content}]
        kwargs: dict = {
            "user_id": self.user_id,
            "metadata": metadata or {},
        }
        use_graph = enable_graph if enable_graph is not None else self.enable_graph
        if use_graph and self._is_cloud:
            kwargs["enable_graph"] = True
        result = self._client.add(messages, **kwargs)
        return result

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
        result = self._client.add(messages, **kwargs)
        return result

    @property
    def _is_cloud(self) -> bool:
        return type(self._client).__name__ == "MemoryClient"

    async def enable_project_graph(self) -> None:
        """Enable graph memory at Mem0 Cloud project level."""
        if not self._is_cloud:
            logger.warning("Project-level graph requires Mem0 Cloud client — skipping")
            return
        if not self.enable_graph:
            logger.warning("Graph provider is not 'mem0' — skipping project graph enablement")
            return
        try:
            self._client.project.update(enable_graph=True)
            logger.info("Enabled graph memory at Mem0 project level")
        except Exception as e:
            logger.error(f"Failed to enable project-level graph: {e}")

    async def search(self, query: str, limit: int | None = None,
                     enable_graph: bool | None = None) -> SearchResult:
        """Semantic search across memories."""
        limit = limit if limit is not None else self.config.memory_search_limit
        kwargs: dict = {"user_id": self.user_id}
        use_graph = enable_graph if enable_graph is not None else self.enable_graph
        if self._is_cloud:
            kwargs["filters"] = {"user_id": self.user_id}
            if use_graph:
                kwargs["enable_graph"] = True
        results = self._client.search(query, **kwargs)
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
            results = self._client.search(query, **kwargs)
        except TypeError:
            logger.warning("Mem0 client doesn't support filters, falling back to unfiltered search")
            kwargs.pop("filters", None)
            results = self._client.search(query, **kwargs)

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
        if self._is_cloud:
            kwargs: dict = {}
            if content is not None:
                kwargs["text"] = content
            if metadata is not None:
                kwargs["metadata"] = metadata
            if kwargs:
                self._client.update(memory_id=memory_id, **kwargs)
        else:
            # Local client only supports data= parameter
            if content is not None:
                self._client.update(memory_id=memory_id, data=content)
            elif metadata is not None:
                logger.warning("Local Mem0 client doesn't support metadata-only updates")

    async def get_all(self) -> list[dict]:
        """Get all memories for the user."""
        kwargs: dict = {"user_id": self.user_id}
        if self._is_cloud:
            kwargs["filters"] = {"user_id": self.user_id}
        results = self._client.get_all(**kwargs)
        if isinstance(results, dict):
            return results.get("results", [])
        return results

    async def get_memory_count(self) -> int:
        """Get total memory count for the user."""
        memories = await self.get_all()
        return len(memories)

    async def delete(self, memory_id: str) -> None:
        """Delete a specific memory."""
        self._client.delete(memory_id)
