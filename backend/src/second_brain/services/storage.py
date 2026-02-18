"""Structured storage via Supabase for patterns, experiences, metrics."""

import asyncio
import logging
import time
from datetime import date, datetime, timedelta, timezone

from supabase import create_client, Client

from second_brain.config import BrainConfig
from second_brain.schemas import (
    ContentTypeConfig, DEFAULT_CONTENT_TYPES, content_type_from_row,
)

logger = logging.getLogger(__name__)


class StorageService:
    """Structured storage via Supabase for patterns, experiences, metrics."""

    def __init__(self, config: BrainConfig):
        self.config = config
        self.user_id = config.brain_user_id
        self._client: Client = create_client(
            config.supabase_url,
            config.supabase_key,
        )

    # --- Patterns ---

    async def get_patterns(
        self, topic: str | None = None, confidence: str | None = None
    ) -> list[dict]:
        try:
            query = self._client.table("patterns").select("*")
            query = query.eq("user_id", self.user_id)
            if topic:
                query = query.eq("topic", topic)
            if confidence:
                query = query.eq("confidence", confidence)
            query = query.order("date_updated", desc=True)
            result = await asyncio.to_thread(query.execute)
            return result.data
        except Exception as e:
            logger.warning("Supabase get_patterns failed: %s", type(e).__name__)
            logger.debug("Supabase error detail: %s", e)
            return []

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
        try:
            data = {**pattern, "user_id": self.user_id}
            query = self._client.table("patterns").upsert(data)
            result = await asyncio.to_thread(query.execute)
            return result.data[0] if result.data else {}
        except Exception as e:
            logger.warning("Supabase upsert_pattern failed: %s", type(e).__name__)
            logger.debug("Supabase error detail: %s", e)
            return {}

    async def insert_pattern(self, pattern: dict) -> dict:
        """Insert a new pattern. Raises on duplicate name (DB UNIQUE constraint)."""
        try:
            data = {**pattern, "user_id": self.user_id}
            query = self._client.table("patterns").insert(data)
            result = await asyncio.to_thread(query.execute)
            return result.data[0] if result.data else {}
        except Exception as e:
            logger.warning("Supabase insert_pattern failed: %s", type(e).__name__)
            logger.debug("Supabase error detail: %s", e)
            return {}

    async def get_pattern_by_name(self, name: str) -> dict | None:
        """Find a pattern by name (case-insensitive). Returns the pattern dict or None."""
        try:
            query = (
                self._client.table("patterns")
                .select("*")
                .eq("user_id", self.user_id)
                .ilike("name", name)
                .limit(1)
            )
            result = await asyncio.to_thread(query.execute)
            return result.data[0] if result.data else None
        except Exception as e:
            logger.warning("Supabase get_pattern_by_name failed: %s", type(e).__name__)
            logger.debug("Supabase error detail: %s", e)
            return None

    async def get_pattern_by_id(self, pattern_id: str) -> dict | None:
        """Fetch a single pattern by UUID (distinct from get_pattern_by_name).

        Args:
            pattern_id: UUID of the pattern

        Returns:
            Pattern row or None if not found.
        """
        try:
            result = await asyncio.to_thread(
                self._client.table("patterns")
                .select("*")
                .eq("user_id", self.user_id)
                .eq("id", pattern_id)
                .execute
            )
            return result.data[0] if result.data else None
        except Exception as e:
            logger.warning("Supabase get_pattern_by_id failed: %s", type(e).__name__)
            logger.debug("Supabase error detail: %s", e)
            return None

    async def reinforce_pattern(
        self, pattern_id: str, new_evidence: list[str] | None = None
    ) -> dict:
        """Atomically reinforce a pattern via DB RPC function."""
        try:
            result = await asyncio.to_thread(
                self._client.rpc(
                    "reinforce_pattern",
                    {"p_pattern_id": pattern_id, "p_new_evidence": new_evidence or []}
                ).execute
            )
            if not result.data:
                raise ValueError(f"Pattern '{pattern_id}' not found for reinforcement")
            logger.info(
                "Reinforced pattern '%s': use_count=%d, confidence=%s",
                result.data[0].get("name", pattern_id),
                result.data[0].get("use_count", 0),
                result.data[0].get("confidence", "?"),
            )
            return result.data[0]
        except Exception as e:
            if "not found" in str(e).lower():
                raise ValueError(f"Pattern '{pattern_id}' not found for reinforcement") from e
            logger.warning("Supabase reinforce_pattern RPC failed: %s", type(e).__name__)
            logger.debug("Supabase error detail: %s", e)
            raise ValueError("Failed to reinforce pattern") from e

    async def delete_pattern(self, pattern_id: str) -> bool:
        """Delete a pattern by ID."""
        try:
            query = (
                self._client.table("patterns")
                .delete()
                .eq("id", pattern_id)
                .eq("user_id", self.user_id)
            )
            result = await asyncio.to_thread(query.execute)
            return len(result.data) > 0
        except Exception as e:
            logger.warning("Supabase delete_pattern failed: %s", type(e).__name__)
            logger.debug("Supabase error detail: %s", e)
            return False

    # --- Experiences ---

    async def add_experience(self, experience: dict) -> dict:
        try:
            data = {**experience, "user_id": self.user_id}
            query = self._client.table("experiences").insert(data)
            result = await asyncio.to_thread(query.execute)
            return result.data[0] if result.data else {}
        except Exception as e:
            logger.warning("Supabase add_experience failed: %s", type(e).__name__)
            logger.debug("Supabase error detail: %s", e)
            return {}

    async def get_experiences(
        self, category: str | None = None, limit: int = 20
    ) -> list[dict]:
        try:
            query = self._client.table("experiences").select("*")
            query = query.eq("user_id", self.user_id)
            if category:
                query = query.eq("category", category)
            query = query.order("created_at", desc=True).limit(limit)
            result = await asyncio.to_thread(query.execute)
            return result.data
        except Exception as e:
            logger.warning("Supabase get_experiences failed: %s", type(e).__name__)
            logger.debug("Supabase error detail: %s", e)
            return []

    async def delete_experience(self, experience_id: str) -> bool:
        """Delete an experience by ID."""
        try:
            query = (
                self._client.table("experiences")
                .delete()
                .eq("id", experience_id)
                .eq("user_id", self.user_id)
            )
            result = await asyncio.to_thread(query.execute)
            return len(result.data) > 0
        except Exception as e:
            logger.warning("Supabase delete_experience failed: %s", type(e).__name__)
            logger.debug("Supabase error detail: %s", e)
            return False

    async def get_experience_by_id(self, experience_id: str) -> dict | None:
        """Fetch a single experience by UUID.

        Args:
            experience_id: UUID of the experience

        Returns:
            Experience row or None if not found.
        """
        try:
            result = await asyncio.to_thread(
                self._client.table("experiences")
                .select("*")
                .eq("user_id", self.user_id)
                .eq("id", experience_id)
                .execute
            )
            return result.data[0] if result.data else None
        except Exception as e:
            logger.warning("Supabase get_experience_by_id failed: %s", type(e).__name__)
            logger.debug("Supabase error detail: %s", e)
            return None

    # --- Brain Health ---

    async def add_health_snapshot(self, snapshot: dict) -> dict:
        try:
            data = {**snapshot, "user_id": self.user_id}
            query = self._client.table("brain_health").insert(data)
            result = await asyncio.to_thread(query.execute)
            return result.data[0] if result.data else {}
        except Exception as e:
            logger.warning("Supabase add_health_snapshot failed: %s", type(e).__name__)
            logger.debug("Supabase error detail: %s", e)
            return {}

    async def get_health_history(self, limit: int = 30) -> list[dict]:
        try:
            query = (
                self._client.table("brain_health")
                .select("*")
                .eq("user_id", self.user_id)
                .order("date", desc=True)
                .limit(limit)
            )
            result = await asyncio.to_thread(query.execute)
            return result.data
        except Exception as e:
            logger.warning("Supabase get_health_history failed: %s", type(e).__name__)
            logger.debug("Supabase error detail: %s", e)
            return []

    # --- Growth Log ---

    async def add_growth_event(self, event: dict) -> dict:
        """Record a brain growth event."""
        try:
            data = {**event, "user_id": self.user_id}
            query = self._client.table("growth_log").insert(data)
            result = await asyncio.to_thread(query.execute)
            return result.data[0] if result.data else {}
        except Exception as e:
            logger.warning("Supabase add_growth_event failed: %s", type(e).__name__)
            logger.debug("Supabase error detail: %s", e)
            return {}

    async def get_growth_events(
        self,
        event_type: str | None = None,
        days: int = 30,
    ) -> list[dict]:
        """Get growth events, optionally filtered by type, within the last N days."""
        try:
            cutoff = str(date.today() - timedelta(days=days))
            query = self._client.table("growth_log").select("*")
            query = query.eq("user_id", self.user_id)
            if event_type:
                query = query.eq("event_type", event_type)
            query = query.gte("event_date", cutoff).order("event_date", desc=True)
            result = await asyncio.to_thread(query.execute)
            return result.data
        except Exception as e:
            logger.warning("Supabase get_growth_events failed: %s", type(e).__name__)
            logger.debug("Supabase error detail: %s", e)
            return []

    async def get_growth_event_counts(self, days: int = 30) -> dict[str, int]:
        """Get counts of each event type within the last N days."""
        try:
            events = await self.get_growth_events(days=days)
            counts: dict[str, int] = {}
            for e in events:
                t = e.get("event_type", "unknown")
                counts[t] = counts.get(t, 0) + 1
            return counts
        except Exception as e:
            logger.warning("Supabase get_growth_event_counts failed: %s", type(e).__name__)
            logger.debug("Supabase error detail: %s", e)
            return {}

    # --- Review History ---

    async def add_review_history(self, entry: dict) -> dict:
        """Record a review result for quality trending."""
        try:
            data = {**entry, "user_id": self.user_id}
            query = self._client.table("review_history").insert(data)
            result = await asyncio.to_thread(query.execute)
            return result.data[0] if result.data else {}
        except Exception as e:
            logger.warning("Supabase add_review_history failed: %s", type(e).__name__)
            logger.debug("Supabase error detail: %s", e)
            return {}

    async def get_review_history(
        self,
        content_type: str | None = None,
        limit: int = 30,
    ) -> list[dict]:
        """Get review history, optionally filtered by content type."""
        try:
            query = self._client.table("review_history").select("*")
            query = query.eq("user_id", self.user_id)
            if content_type:
                query = query.eq("content_type", content_type)
            query = query.order("review_date", desc=True).limit(limit)
            result = await asyncio.to_thread(query.execute)
            return result.data
        except Exception as e:
            logger.warning("Supabase get_review_history failed: %s", type(e).__name__)
            logger.debug("Supabase error detail: %s", e)
            return []

    # --- Confidence History ---

    async def add_confidence_transition(self, transition: dict) -> dict:
        """Record a confidence level change."""
        try:
            data = {**transition, "user_id": self.user_id}
            query = self._client.table("confidence_history").insert(data)
            result = await asyncio.to_thread(query.execute)
            return result.data[0] if result.data else {}
        except Exception as e:
            logger.warning("Supabase add_confidence_transition failed: %s", type(e).__name__)
            logger.debug("Supabase error detail: %s", e)
            return {}

    async def get_confidence_history(
        self,
        pattern_name: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """Get confidence transitions, optionally for a specific pattern."""
        try:
            query = self._client.table("confidence_history").select("*")
            query = query.eq("user_id", self.user_id)
            if pattern_name:
                query = query.eq("pattern_name", pattern_name)
            query = query.order("transition_date", desc=True).limit(limit)
            result = await asyncio.to_thread(query.execute)
            return result.data
        except Exception as e:
            logger.warning("Supabase get_confidence_history failed: %s", type(e).__name__)
            logger.debug("Supabase error detail: %s", e)
            return []

    # --- Memory Content ---

    async def get_memory_content(
        self, category: str, subcategory: str | None = None
    ) -> list[dict]:
        try:
            query = self._client.table("memory_content").select("*")
            query = query.eq("user_id", self.user_id)
            query = query.eq("category", category)
            if subcategory:
                query = query.eq("subcategory", subcategory)
            result = await asyncio.to_thread(query.execute)
            return result.data
        except Exception as e:
            logger.warning("Supabase get_memory_content failed: %s", type(e).__name__)
            logger.debug("Supabase error detail: %s", e)
            return []

    async def upsert_memory_content(self, content: dict) -> dict:
        try:
            data = {**content, "user_id": self.user_id}
            query = self._client.table("memory_content").upsert(data)
            result = await asyncio.to_thread(query.execute)
            return result.data[0] if result.data else {}
        except Exception as e:
            logger.warning("Supabase upsert_memory_content failed: %s", type(e).__name__)
            logger.debug("Supabase error detail: %s", e)
            return {}

    async def delete_memory_content(
        self, category: str, subcategory: str = "general"
    ) -> bool:
        """Delete a memory content row by category and subcategory.

        Args:
            category: Category name (e.g., voice, audience, product)
            subcategory: Sub-category (default: "general")

        Returns:
            True if found and deleted, False otherwise.
        """
        try:
            result = await asyncio.to_thread(
                self._client.table("memory_content")
                .delete()
                .eq("category", category)
                .eq("subcategory", subcategory)
                .eq("user_id", self.user_id)
                .execute
            )
            return len(result.data) > 0
        except Exception as e:
            logger.warning(
                "Supabase delete_memory_content failed: %s", type(e).__name__
            )
            logger.debug("Supabase error detail: %s", e)
            return False

    # --- Examples ---

    async def get_examples(
        self, content_type: str | None = None
    ) -> list[dict]:
        try:
            query = self._client.table("examples").select("*")
            query = query.eq("user_id", self.user_id)
            if content_type:
                query = query.eq("content_type", content_type)
            query = query.order("created_at", desc=True)
            result = await asyncio.to_thread(query.execute)
            return result.data
        except Exception as e:
            logger.warning("Supabase get_examples failed: %s", type(e).__name__)
            logger.debug("Supabase error detail: %s", e)
            return []

    async def upsert_example(self, example: dict) -> dict:
        try:
            data = {**example, "user_id": self.user_id}
            query = self._client.table("examples").upsert(data)
            result = await asyncio.to_thread(query.execute)
            return result.data[0] if result.data else {}
        except Exception as e:
            logger.warning("Supabase upsert_example failed: %s", type(e).__name__)
            logger.debug("Supabase error detail: %s", e)
            return {}

    async def delete_example(self, example_id: str) -> bool:
        """Delete an example by ID."""
        try:
            query = (
                self._client.table("examples")
                .delete()
                .eq("id", example_id)
                .eq("user_id", self.user_id)
            )
            result = await asyncio.to_thread(query.execute)
            return len(result.data) > 0
        except Exception as e:
            logger.warning("Supabase delete_example failed: %s", type(e).__name__)
            logger.debug("Supabase error detail: %s", e)
            return False

    # --- Knowledge Repo ---

    async def get_knowledge(
        self, category: str | None = None
    ) -> list[dict]:
        try:
            query = self._client.table("knowledge_repo").select("*")
            query = query.eq("user_id", self.user_id)
            if category:
                query = query.eq("category", category)
            query = query.order("created_at", desc=True)
            result = await asyncio.to_thread(query.execute)
            return result.data
        except Exception as e:
            logger.warning("Supabase get_knowledge failed: %s", type(e).__name__)
            logger.debug("Supabase error detail: %s", e)
            return []

    async def upsert_knowledge(self, knowledge: dict) -> dict:
        try:
            data = {**knowledge, "user_id": self.user_id}
            query = self._client.table("knowledge_repo").upsert(data)
            result = await asyncio.to_thread(query.execute)
            return result.data[0] if result.data else {}
        except Exception as e:
            logger.warning("Supabase upsert_knowledge failed: %s", type(e).__name__)
            logger.debug("Supabase error detail: %s", e)
            return {}

    async def delete_knowledge(self, knowledge_id: str) -> bool:
        """Delete a knowledge entry by ID."""
        try:
            query = (
                self._client.table("knowledge_repo")
                .delete()
                .eq("id", knowledge_id)
                .eq("user_id", self.user_id)
            )
            result = await asyncio.to_thread(query.execute)
            return len(result.data) > 0
        except Exception as e:
            logger.warning("Supabase delete_knowledge failed: %s", type(e).__name__)
            logger.debug("Supabase error detail: %s", e)
            return False

    # --- Content Types ---

    async def get_content_types(self) -> list[dict]:
        """Get all content types ordered by name."""
        try:
            query = (
                self._client.table("content_types")
                .select("*")
                .order("name")
            )
            result = await asyncio.to_thread(query.execute)
            return result.data
        except Exception as e:
            logger.warning("Supabase get_content_types failed: %s", type(e).__name__)
            logger.debug("Supabase error detail: %s", e)
            return []

    async def get_content_type_by_slug(self, slug: str) -> dict | None:
        """Get a content type by its slug (e.g., 'linkedin', 'newsletter')."""
        try:
            query = (
                self._client.table("content_types")
                .select("*")
                .eq("slug", slug)
                .limit(1)
            )
            result = await asyncio.to_thread(query.execute)
            return result.data[0] if result.data else None
        except Exception as e:
            logger.warning("Supabase get_content_type_by_slug failed: %s", type(e).__name__)
            logger.debug("Supabase error detail: %s", e)
            return None

    async def upsert_content_type(self, content_type: dict) -> dict:
        """Create or update a content type. Uses slug as the conflict key."""
        try:
            query = (
                self._client.table("content_types")
                .upsert(content_type, on_conflict="slug")
            )
            result = await asyncio.to_thread(query.execute)
            return result.data[0] if result.data else {}
        except Exception as e:
            logger.warning("Supabase upsert_content_type failed: %s", type(e).__name__)
            logger.debug("Supabase error detail: %s", e)
            return {}

    async def delete_content_type(self, slug: str) -> bool:
        """Delete a content type by slug. Returns True if deleted."""
        try:
            query = (
                self._client.table("content_types")
                .delete()
                .eq("slug", slug)
            )
            result = await asyncio.to_thread(query.execute)
            return len(result.data) > 0
        except Exception as e:
            logger.warning("Supabase delete_content_type failed: %s", type(e).__name__)
            logger.debug("Supabase error detail: %s", e)
            return False

    async def vector_search(
        self,
        embedding: list[float],
        table: str = "memory_content",
        limit: int = 10,
        similarity_threshold: float = 0.7,
    ) -> list[dict]:
        """Search by vector similarity using pgvector cosine distance.

        Args:
            embedding: Query embedding vector (1536 dimensions).
            table: Table to search (must have 'embedding' column).
            limit: Maximum results to return.
            similarity_threshold: Minimum cosine similarity (0-1). Default 0.7.

        Returns:
            List of matching rows with similarity score added.
        """
        valid_tables = {"patterns", "memory_content", "examples", "knowledge_repo"}
        if table not in valid_tables:
            raise ValueError(f"Invalid table '{table}'. Must be one of: {valid_tables}")

        try:
            result = await asyncio.to_thread(
                self._client.rpc(
                    "vector_search",
                    {
                        "query_embedding": embedding,
                        "match_table": table,
                        "match_count": limit,
                        "match_threshold": similarity_threshold,
                        "p_user_id": self.user_id,
                    }
                ).execute
            )
            return result.data if result.data else []
        except Exception as e:
            logger.warning("vector_search failed on %s: %s", table, type(e).__name__)
            logger.debug("vector_search error detail: %s", e)
            return []

    # --- Project Lifecycle ---

    async def create_project(self, project: dict) -> dict:
        """Create a new project with lifecycle tracking."""
        try:
            data = {**project, "user_id": self.user_id}
            result = await asyncio.to_thread(
                self._client.table("projects").insert(data).execute
            )
            return result.data[0] if result.data else {}
        except Exception as e:
            logger.warning("Supabase create_project failed: %s", type(e).__name__)
            logger.debug("Supabase error detail: %s", e)
            return {}

    async def get_project(self, project_id: str) -> dict | None:
        """Get a project by ID with its artifacts."""
        try:
            result = await asyncio.to_thread(
                self._client.table("projects")
                .select("*, project_artifacts(*)")
                .eq("user_id", self.user_id)
                .eq("id", project_id)
                .execute
            )
            return result.data[0] if result.data else None
        except Exception as e:
            logger.warning("Supabase get_project failed: %s", type(e).__name__)
            logger.debug("Supabase error detail: %s", e)
            return None

    async def list_projects(
        self, lifecycle_stage: str | None = None, category: str | None = None, limit: int = 20
    ) -> list[dict]:
        """List projects with optional filtering."""
        try:
            query = self._client.table("projects").select("*")
            query = query.eq("user_id", self.user_id)
            if lifecycle_stage:
                query = query.eq("lifecycle_stage", lifecycle_stage)
            if category:
                query = query.eq("category", category)
            result = await asyncio.to_thread(
                query.order("updated_at", desc=True).limit(limit).execute
            )
            return result.data if result.data else []
        except Exception as e:
            logger.warning("Supabase list_projects failed: %s", type(e).__name__)
            logger.debug("Supabase error detail: %s", e)
            return []

    async def update_project_stage(self, project_id: str, stage: str, **kwargs) -> dict:
        """Update project lifecycle stage and optional fields."""
        try:
            update_data = {
                "lifecycle_stage": stage,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            update_data.update(kwargs)
            if stage == "complete":
                update_data["completed_at"] = datetime.now(timezone.utc).isoformat()
            result = await asyncio.to_thread(
                self._client.table("projects")
                .update(update_data)
                .eq("id", project_id)
                .eq("user_id", self.user_id)
                .execute
            )
            return result.data[0] if result.data else {}
        except Exception as e:
            logger.warning("Supabase update_project_stage failed: %s", type(e).__name__)
            logger.debug("Supabase error detail: %s", e)
            return {}

    async def update_project(self, project_id: str, fields: dict) -> dict | None:
        """Update arbitrary project fields by ID.

        Args:
            project_id: UUID of the project to update
            fields: Dict of field names to new values (e.g., {"name": "New Name"})

        Returns:
            Updated project row or None if not found.
        """
        try:
            result = await asyncio.to_thread(
                self._client.table("projects")
                .update(fields)
                .eq("id", project_id)
                .eq("user_id", self.user_id)
                .execute
            )
            return result.data[0] if result.data else None
        except Exception as e:
            logger.warning("Supabase update_project failed: %s", type(e).__name__)
            logger.debug("Supabase error detail: %s", e)
            return None

    async def delete_project(self, project_id: str) -> bool:
        """Delete a project by ID. Associated artifacts are cascade-deleted by the DB.

        Args:
            project_id: UUID of the project to delete

        Returns:
            True if project was found and deleted, False otherwise.
        """
        try:
            result = await asyncio.to_thread(
                self._client.table("projects")
                .delete()
                .eq("id", project_id)
                .eq("user_id", self.user_id)
                .execute
            )
            return len(result.data) > 0
        except Exception as e:
            logger.warning("Supabase delete_project failed: %s", type(e).__name__)
            logger.debug("Supabase error detail: %s", e)
            return False

    async def add_project_artifact(self, artifact: dict) -> dict:
        """Add or update an artifact for a project (upsert by project_id + artifact_type)."""
        try:
            result = await asyncio.to_thread(
                self._client.table("project_artifacts")
                .upsert(artifact, on_conflict="project_id,artifact_type")
                .execute
            )
            return result.data[0] if result.data else {}
        except Exception as e:
            logger.warning("Supabase add_project_artifact failed: %s", type(e).__name__)
            logger.debug("Supabase error detail: %s", e)
            return {}

    async def get_project_artifacts(self, project_id: str) -> list[dict]:
        """Get all artifacts for a project."""
        try:
            result = await asyncio.to_thread(
                self._client.table("project_artifacts")
                .select("*")
                .eq("project_id", project_id)
                .order("created_at")
                .execute
            )
            return result.data if result.data else []
        except Exception as e:
            logger.warning("Supabase get_project_artifacts failed: %s", type(e).__name__)
            logger.debug("Supabase error detail: %s", e)
            return []

    async def delete_project_artifact(self, artifact_id: str) -> bool:
        """Delete a single project artifact by ID.

        Args:
            artifact_id: UUID of the artifact to delete

        Returns:
            True if found and deleted, False otherwise.
        """
        try:
            result = await asyncio.to_thread(
                self._client.table("project_artifacts")
                .delete()
                .eq("id", artifact_id)
                .execute
            )
            return len(result.data) > 0
        except Exception as e:
            logger.warning("Supabase delete_project_artifact failed: %s", type(e).__name__)
            logger.debug("Supabase error detail: %s", e)
            return False

    # --- Pattern Registry & Downgrade ---

    async def update_pattern_failures(self, pattern_id: str, reset: bool = False) -> dict:
        """Increment or reset consecutive_failures on a pattern."""
        try:
            if reset:
                update_data = {"consecutive_failures": 0}
            else:
                current = await asyncio.to_thread(
                    self._client.table("patterns")
                    .select("consecutive_failures")
                    .eq("id", pattern_id)
                    .execute
                )
                current_val = current.data[0].get("consecutive_failures", 0) if current.data else 0
                update_data = {"consecutive_failures": current_val + 1}
            result = await asyncio.to_thread(
                self._client.table("patterns")
                .update(update_data)
                .eq("id", pattern_id)
                .execute
            )
            return result.data[0] if result.data else {}
        except Exception as e:
            logger.warning("Supabase update_pattern_failures failed: %s", type(e).__name__)
            logger.debug("Supabase error detail: %s", e)
            return {}

    async def get_pattern_registry(self) -> list[dict]:
        """Get all patterns formatted for registry view."""
        try:
            result = await asyncio.to_thread(
                self._client.table("patterns")
                .select("name, topic, confidence, use_count, date_added, date_updated, "
                        "consecutive_failures, applicable_content_types")
                .order("confidence", desc=True)
                .order("use_count", desc=True)
                .execute
            )
            return result.data if result.data else []
        except Exception as e:
            logger.warning("Supabase get_pattern_registry failed: %s", type(e).__name__)
            logger.debug("Supabase error detail: %s", e)
            return []

    async def downgrade_pattern_confidence(self, pattern_id: str) -> dict:
        """Downgrade a pattern's confidence level (HIGH->MEDIUM, MEDIUM->LOW)."""
        try:
            current = await asyncio.to_thread(
                self._client.table("patterns")
                .select("name, confidence, consecutive_failures")
                .eq("id", pattern_id)
                .execute
            )
            if not current.data:
                return {}
            pattern = current.data[0]
            conf = pattern["confidence"]
            new_conf = "MEDIUM" if conf == "HIGH" else "LOW" if conf == "MEDIUM" else "LOW"
            if new_conf == conf:
                return pattern  # Already at LOW, can't downgrade further
            result = await asyncio.to_thread(
                self._client.table("patterns")
                .update({"confidence": new_conf, "consecutive_failures": 0})
                .eq("id", pattern_id)
                .execute
            )
            return result.data[0] if result.data else {}
        except Exception as e:
            logger.warning("Supabase downgrade_pattern_confidence failed: %s", type(e).__name__)
            logger.debug("Supabase error detail: %s", e)
            return {}

    # --- Quality Trending ---

    async def get_quality_trending(self, days: int = 30) -> dict:
        """Get quality metrics trending data for the specified period."""
        try:
            result = await asyncio.to_thread(
                self._client.table("review_history")
                .select("*")
                .gte("review_date", (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat())
                .order("review_date", desc=True)
                .execute
            )
            reviews = result.data if result.data else []
            if not reviews:
                return {"total_reviews": 0, "avg_score": 0.0, "by_dimension": {},
                        "by_content_type": {}, "recurring_issues": [],
                        "excellence_count": 0, "needs_work_count": 0}

            scores = [r["overall_score"] for r in reviews if r.get("overall_score")]
            avg_score = sum(scores) / len(scores) if scores else 0.0

            # By content type
            by_type: dict[str, list[float]] = {}
            for r in reviews:
                ct = r.get("content_type", "unknown")
                if r.get("overall_score"):
                    by_type.setdefault(ct, []).append(r["overall_score"])
            by_content_type = {ct: sum(s) / len(s) for ct, s in by_type.items()}

            # By dimension (from dimension_scores JSONB — handle dict or list format)
            dim_scores: dict[str, list[float]] = {}
            for r in reviews:
                ds = r.get("dimension_scores") or r.get("dimension_details") or {}
                if isinstance(ds, dict):
                    for dim, score in ds.items():
                        if isinstance(score, (int, float)):
                            dim_scores.setdefault(dim, []).append(score)
                elif isinstance(ds, list):
                    for item in ds:
                        if isinstance(item, dict) and "dimension" in item and "score" in item:
                            dim_scores.setdefault(item["dimension"], []).append(item["score"])
            by_dimension = {
                dim: {"avg_score": sum(s) / len(s), "count": len(s)}
                for dim, s in dim_scores.items()
            }

            # Recurring issues (from critical_issues JSONB, appearing 3+ times)
            issue_counts: dict[str, int] = {}
            for r in reviews:
                issues = r.get("critical_issues") or []
                if isinstance(issues, list):
                    for issue in issues:
                        issue_str = str(issue) if not isinstance(issue, str) else issue
                        issue_counts[issue_str] = issue_counts.get(issue_str, 0) + 1
            recurring = [issue for issue, count in issue_counts.items() if count >= 3]

            excellence_count = sum(1 for s in scores if s >= 9.0)
            needs_work_count = sum(1 for s in scores if s < 6.0)

            return {
                "total_reviews": len(reviews),
                "avg_score": round(avg_score, 2),
                "by_dimension": by_dimension,
                "by_content_type": {k: round(v, 2) for k, v in by_content_type.items()},
                "recurring_issues": recurring[:10],
                "excellence_count": excellence_count,
                "needs_work_count": needs_work_count,
            }
        except Exception as e:
            logger.warning("Supabase get_quality_trending failed: %s", type(e).__name__)
            logger.debug("Supabase error detail: %s", e)
            return {"total_reviews": 0, "avg_score": 0.0, "by_dimension": {},
                    "by_content_type": {}, "recurring_issues": [],
                    "excellence_count": 0, "needs_work_count": 0}

    # --- Setup Status ---

    async def get_setup_status(self) -> dict:
        """Check brain setup completion — which memory categories are populated."""
        all_categories = {"company", "customers", "audience", "style-voice",
                          "values-beliefs", "personal"}
        try:
            result = await asyncio.to_thread(
                self._client.table("memory_content")
                .select("category, subcategory")
                .execute
            )
            entries = result.data if result.data else []
            populated_categories = set(e["category"] for e in entries if e.get("category"))

            missing = sorted(all_categories - populated_categories)

            pattern_result = await asyncio.to_thread(
                self._client.table("patterns").select("id", count="exact").execute
            )
            has_patterns = bool(pattern_result.count and pattern_result.count > 0)

            example_result = await asyncio.to_thread(
                self._client.table("examples").select("id", count="exact").execute
            )
            has_examples = bool(example_result.count and example_result.count > 0)

            return {
                "total_memory_entries": len(entries),
                "populated_categories": sorted(populated_categories),
                "missing_categories": missing,
                "has_patterns": has_patterns,
                "has_examples": has_examples,
                "is_complete": len(missing) == 0 and has_patterns,
            }
        except Exception as e:
            logger.warning("Supabase get_setup_status failed: %s", type(e).__name__)
            logger.debug("Supabase error detail: %s", e)
            return {"total_memory_entries": 0, "populated_categories": [],
                    "missing_categories": sorted(all_categories), "has_patterns": False,
                    "has_examples": False, "is_complete": False}

    async def close(self) -> None:
        """Release Supabase client resources."""
        # supabase-py Client doesn't have an explicit close,
        # but we null the reference for garbage collection
        self._client = None


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
