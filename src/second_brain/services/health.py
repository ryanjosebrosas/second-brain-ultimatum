"""Brain health metrics computation."""

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from second_brain.deps import BrainDeps

logger = logging.getLogger(__name__)


@dataclass
class HealthMetrics:
    """Structured health metrics for the brain."""

    memory_count: int | str
    total_patterns: int
    high_confidence: int
    medium_confidence: int
    low_confidence: int
    experience_count: int
    graph_provider: str
    latest_update: str
    topics: dict[str, int] = field(default_factory=dict)
    status: str = "BUILDING"


class HealthService:
    """Compute brain health and growth metrics."""

    async def compute(self, deps: "BrainDeps") -> HealthMetrics:
        """Compute current health metrics from all services."""
        patterns = await deps.storage_service.get_patterns()
        experiences = await deps.storage_service.get_experiences()

        total = len(patterns)
        high = len([p for p in patterns if p.get("confidence") == "HIGH"])
        medium = len([p for p in patterns if p.get("confidence") == "MEDIUM"])
        low = len([p for p in patterns if p.get("confidence") == "LOW"])

        topics: dict[str, int] = {}
        for p in patterns:
            t = p.get("topic", "uncategorized")
            topics[t] = topics.get(t, 0) + 1

        try:
            memory_count: int | str = await deps.memory_service.get_memory_count()
        except Exception:
            memory_count = "unavailable"

        latest = patterns[0].get("date_updated", "unknown") if patterns else "none"
        graph = deps.config.graph_provider or "disabled"
        status = "GROWING" if total > 5 else "BUILDING"

        return HealthMetrics(
            memory_count=memory_count,
            total_patterns=total,
            high_confidence=high,
            medium_confidence=medium,
            low_confidence=low,
            experience_count=len(experiences),
            graph_provider=graph,
            latest_update=latest,
            topics=topics,
            status=status,
        )
