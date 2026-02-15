"""Semantic memory via Mem0 (cloud primary, local fallback)."""

import logging

from second_brain.config import BrainConfig

logger = logging.getLogger(__name__)


class MemoryService:
    """Semantic memory via Mem0 (cloud primary, local fallback)."""

    def __init__(self, config: BrainConfig):
        self.config = config
        self.user_id = config.brain_user_id
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
        logger.info("Using Mem0 local client")
        return Memory.from_config(mem0_config)

    async def add(self, content: str, metadata: dict | None = None) -> dict:
        """Add a memory. Content is auto-extracted into facts by Mem0."""
        messages = [{"role": "user", "content": content}]
        result = self._client.add(
            messages,
            user_id=self.user_id,
            metadata=metadata or {},
        )
        return result

    @property
    def _is_cloud(self) -> bool:
        return type(self._client).__name__ == "MemoryClient"

    async def search(self, query: str, limit: int = 10) -> list[dict]:
        """Semantic search across memories."""
        kwargs = {"user_id": self.user_id}
        # Mem0 Cloud v2 requires explicit filters for search
        if self._is_cloud:
            kwargs["filters"] = {"user_id": self.user_id}
        results = self._client.search(query, **kwargs)
        # v2 returns {"results": [...]}, v1 returns a list
        if isinstance(results, dict):
            results = results.get("results", [])
        return results[:limit] if isinstance(results, list) else []

    async def get_all(self) -> list[dict]:
        """Get all memories for the user."""
        return self._client.get_all(user_id=self.user_id)

    async def delete(self, memory_id: str) -> None:
        """Delete a specific memory."""
        self._client.delete(memory_id)
