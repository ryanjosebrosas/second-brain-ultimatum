"""Structured storage via Supabase for patterns, experiences, metrics."""

import logging

from supabase import create_client, Client

from second_brain.config import BrainConfig

logger = logging.getLogger(__name__)


class StorageService:
    """Structured storage via Supabase for patterns, experiences, metrics."""

    def __init__(self, config: BrainConfig):
        self.config = config
        self._client: Client = create_client(
            config.supabase_url,
            config.supabase_key,
        )

    # --- Patterns ---

    async def get_patterns(
        self, topic: str | None = None, confidence: str | None = None
    ) -> list[dict]:
        query = self._client.table("patterns").select("*")
        if topic:
            query = query.eq("topic", topic)
        if confidence:
            query = query.eq("confidence", confidence)
        result = query.order("date_updated", desc=True).execute()
        return result.data

    async def upsert_pattern(self, pattern: dict) -> dict:
        result = self._client.table("patterns").upsert(pattern).execute()
        return result.data[0] if result.data else {}

    # --- Experiences ---

    async def add_experience(self, experience: dict) -> dict:
        result = self._client.table("experiences").insert(experience).execute()
        return result.data[0] if result.data else {}

    async def get_experiences(
        self, category: str | None = None, limit: int = 20
    ) -> list[dict]:
        query = self._client.table("experiences").select("*")
        if category:
            query = query.eq("category", category)
        result = query.order("created_at", desc=True).limit(limit).execute()
        return result.data

    # --- Brain Health ---

    async def add_health_snapshot(self, snapshot: dict) -> dict:
        result = self._client.table("brain_health").insert(snapshot).execute()
        return result.data[0] if result.data else {}

    async def get_health_history(self, limit: int = 30) -> list[dict]:
        result = (
            self._client.table("brain_health")
            .select("*")
            .order("date", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data

    # --- Memory Content ---

    async def get_memory_content(
        self, category: str, subcategory: str | None = None
    ) -> list[dict]:
        query = self._client.table("memory_content").select("*")
        query = query.eq("category", category)
        if subcategory:
            query = query.eq("subcategory", subcategory)
        result = query.execute()
        return result.data

    async def upsert_memory_content(self, content: dict) -> dict:
        result = self._client.table("memory_content").upsert(content).execute()
        return result.data[0] if result.data else {}

    # --- Examples ---

    async def get_examples(
        self, content_type: str | None = None
    ) -> list[dict]:
        query = self._client.table("examples").select("*")
        if content_type:
            query = query.eq("content_type", content_type)
        result = query.order("created_at", desc=True).execute()
        return result.data

    async def upsert_example(self, example: dict) -> dict:
        result = self._client.table("examples").upsert(example).execute()
        return result.data[0] if result.data else {}

    # --- Knowledge Repo ---

    async def get_knowledge(
        self, category: str | None = None
    ) -> list[dict]:
        query = self._client.table("knowledge_repo").select("*")
        if category:
            query = query.eq("category", category)
        result = query.order("created_at", desc=True).execute()
        return result.data

    async def upsert_knowledge(self, knowledge: dict) -> dict:
        result = self._client.table("knowledge_repo").upsert(knowledge).execute()
        return result.data[0] if result.data else {}
