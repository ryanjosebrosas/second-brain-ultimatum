"""Structured storage via Supabase for patterns, experiences, metrics."""

import logging
import time
from datetime import date, timedelta

from supabase import create_client, Client

from second_brain.config import BrainConfig
from second_brain.schemas import (
    ConfidenceLevel, ContentTypeConfig, DEFAULT_CONTENT_TYPES, content_type_from_row,
)

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

    async def get_patterns_for_content_type(
        self, content_type_slug: str
    ) -> list[dict]:
        """Get patterns applicable to a specific content type.
        Returns patterns where applicable_content_types contains the slug,
        OR where applicable_content_types is NULL (universal patterns)."""
        all_patterns = await self.get_patterns()
        return [
            p for p in all_patterns
            if p.get("applicable_content_types") is None
            or content_type_slug in (p.get("applicable_content_types") or [])
        ]

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

    # --- Content Types ---

    async def get_content_types(self) -> list[dict]:
        """Get all content types ordered by name."""
        result = (
            self._client.table("content_types")
            .select("*")
            .order("name")
            .execute()
        )
        return result.data

    async def get_content_type_by_slug(self, slug: str) -> dict | None:
        """Get a content type by its slug (e.g., 'linkedin', 'newsletter')."""
        result = (
            self._client.table("content_types")
            .select("*")
            .eq("slug", slug)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    async def upsert_content_type(self, content_type: dict) -> dict:
        """Create or update a content type. Uses slug as the conflict key."""
        result = (
            self._client.table("content_types")
            .upsert(content_type, on_conflict="slug")
            .execute()
        )
        return result.data[0] if result.data else {}

    async def delete_content_type(self, slug: str) -> bool:
        """Delete a content type by slug. Returns True if deleted."""
        result = (
            self._client.table("content_types")
            .delete()
            .eq("slug", slug)
            .execute()
        )
        return len(result.data) > 0


class ContentTypeRegistry:
    """Cached content type registry with DB-first, fallback-to-defaults strategy.

    Loads content types from Supabase on first access, caches for `ttl` seconds.
    Falls back to DEFAULT_CONTENT_TYPES if DB is empty or unreachable.
    """

    def __init__(self, storage: "StorageService", ttl: int = 300):
        self._storage = storage
        self._ttl = ttl
        self._cache: dict[str, ContentTypeConfig] | None = None
        self._cache_time: float = 0.0

    def _is_stale(self) -> bool:
        return self._cache is None or (time.time() - self._cache_time) > self._ttl

    def invalidate(self):
        """Force cache refresh on next access."""
        self._cache = None
        self._cache_time = 0.0

    async def get_all(self) -> dict[str, ContentTypeConfig]:
        """Get all content types as {slug: ContentTypeConfig} dict."""
        if not self._is_stale() and self._cache is not None:
            return self._cache

        try:
            rows = await self._storage.get_content_types()
            if rows:
                self._cache = {
                    row["slug"]: content_type_from_row(row)
                    for row in rows
                }
                self._cache_time = time.time()
                return self._cache
        except Exception:
            logger.warning("Failed to load content types from DB, using defaults")

        # Fallback to hardcoded defaults
        self._cache = dict(DEFAULT_CONTENT_TYPES)
        self._cache_time = time.time()
        return self._cache

    async def get(self, slug: str) -> ContentTypeConfig | None:
        """Get a single content type by slug."""
        all_types = await self.get_all()
        return all_types.get(slug)

    async def slugs(self) -> list[str]:
        """Get all available content type slugs."""
        all_types = await self.get_all()
        return sorted(all_types.keys())
