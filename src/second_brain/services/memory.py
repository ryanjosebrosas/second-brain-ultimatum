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

    async def search(self, query: str, limit: int = 10,
                     enable_graph: bool | None = None) -> SearchResult:
        """Semantic search across memories."""
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
