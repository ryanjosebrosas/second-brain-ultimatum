"""Structured storage via Supabase for patterns, experiences, metrics."""

import logging
from datetime import date, timedelta

from supabase import create_client, Client

from second_brain.config import BrainConfig
from second_brain.schemas import ConfidenceLevel

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

    async def insert_pattern(self, pattern: dict) -> dict:
        """Insert a new pattern. Raises on duplicate name (DB UNIQUE constraint)."""
        result = self._client.table("patterns").insert(pattern).execute()
        return result.data[0] if result.data else {}

    async def get_pattern_by_name(self, name: str) -> dict | None:
        """Find a pattern by name (case-insensitive). Returns the pattern dict or None."""
        result = (
            self._client.table("patterns")
            .select("*")
            .ilike("name", name)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    async def reinforce_pattern(
        self, pattern_id: str, new_evidence: list[str] | None = None
    ) -> dict:
        """Atomically reinforce a pattern: increment use_count, upgrade confidence, append evidence."""
        # Fetch current state
        current = (
            self._client.table("patterns")
            .select("*")
            .eq("id", pattern_id)
            .limit(1)
            .execute()
        )
        if not current.data:
            logger.warning("reinforce_pattern: pattern_id=%s not found", pattern_id)
            raise ValueError(f"Pattern '{pattern_id}' not found for reinforcement")
        pattern = current.data[0]

        new_use_count = pattern.get("use_count", 1) + 1
        # Confidence thresholds: 1→LOW, 2-4→MEDIUM, 5+→HIGH
        new_confidence: ConfidenceLevel
        if new_use_count >= 5:
            new_confidence = "HIGH"
        elif new_use_count >= 2:
            new_confidence = "MEDIUM"
        else:
            new_confidence = "LOW"

        existing_evidence = pattern.get("evidence") or []
        merged_evidence = existing_evidence + (new_evidence or [])

        update_data = {
            "use_count": new_use_count,
            "confidence": new_confidence,
            "evidence": merged_evidence,
            "date_updated": str(date.today()),
        }
        result = (
            self._client.table("patterns")
            .update(update_data)
            .eq("id", pattern_id)
            .execute()
        )
        if not result.data:
            logger.error("reinforce_pattern: update failed for pattern_id=%s", pattern_id)
            raise ValueError(f"Failed to update pattern '{pattern_id}'")
        logger.info(
            "Reinforced pattern '%s': use_count=%d, confidence=%s",
            pattern.get("name", pattern_id), new_use_count, new_confidence,
        )
        return result.data[0]

    async def delete_pattern(self, pattern_id: str) -> bool:
        """Delete a pattern by ID."""
        result = self._client.table("patterns").delete().eq("id", pattern_id).execute()
        return len(result.data) > 0

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

    async def delete_experience(self, experience_id: str) -> bool:
        """Delete an experience by ID."""
        result = self._client.table("experiences").delete().eq("id", experience_id).execute()
        return len(result.data) > 0

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

    # --- Growth Log ---

    async def add_growth_event(self, event: dict) -> dict:
        """Record a brain growth event."""
        result = self._client.table("growth_log").insert(event).execute()
        return result.data[0] if result.data else {}

    async def get_growth_events(
        self,
        event_type: str | None = None,
        days: int = 30,
    ) -> list[dict]:
        """Get growth events, optionally filtered by type, within the last N days."""
        cutoff = str(date.today() - timedelta(days=days))
        query = self._client.table("growth_log").select("*")
        if event_type:
            query = query.eq("event_type", event_type)
        query = query.gte("event_date", cutoff)
        result = query.order("event_date", desc=True).execute()
        return result.data

    async def get_growth_event_counts(self, days: int = 30) -> dict[str, int]:
        """Get counts of each event type within the last N days."""
        events = await self.get_growth_events(days=days)
        counts: dict[str, int] = {}
        for e in events:
            t = e.get("event_type", "unknown")
            counts[t] = counts.get(t, 0) + 1
        return counts

    # --- Review History ---

    async def add_review_history(self, entry: dict) -> dict:
        """Record a review result for quality trending."""
        result = self._client.table("review_history").insert(entry).execute()
        return result.data[0] if result.data else {}

    async def get_review_history(
        self,
        content_type: str | None = None,
        limit: int = 30,
    ) -> list[dict]:
        """Get review history, optionally filtered by content type."""
        query = self._client.table("review_history").select("*")
        if content_type:
            query = query.eq("content_type", content_type)
        result = query.order("review_date", desc=True).limit(limit).execute()
        return result.data

    # --- Confidence History ---

    async def add_confidence_transition(self, transition: dict) -> dict:
        """Record a confidence level change."""
        result = self._client.table("confidence_history").insert(transition).execute()
        return result.data[0] if result.data else {}

    async def get_confidence_history(
        self,
        pattern_name: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """Get confidence transitions, optionally for a specific pattern."""
        query = self._client.table("confidence_history").select("*")
        if pattern_name:
            query = query.eq("pattern_name", pattern_name)
        result = query.order("transition_date", desc=True).limit(limit).execute()
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

    async def delete_example(self, example_id: str) -> bool:
        """Delete an example by ID."""
        result = self._client.table("examples").delete().eq("id", example_id).execute()
        return len(result.data) > 0

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

    async def delete_knowledge(self, knowledge_id: str) -> bool:
        """Delete a knowledge entry by ID."""
        result = self._client.table("knowledge_repo").delete().eq("id", knowledge_id).execute()
        return len(result.data) > 0
