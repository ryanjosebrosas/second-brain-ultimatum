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
    # Growth tracking (populated by compute_growth)
    growth_events_total: int = 0
    patterns_created_period: int = 0
    patterns_reinforced_period: int = 0
    confidence_upgrades_period: int = 0
    experiences_recorded_period: int = 0
    reviews_completed_period: int = 0
    avg_review_score: float = 0.0
    review_score_trend: str = "stable"
    stale_patterns: list[str] = field(default_factory=list)


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

    async def compute_growth(self, deps: "BrainDeps", days: int = 30) -> HealthMetrics:
        """Compute health metrics enhanced with growth tracking data."""
        # Start with base metrics
        metrics = await self.compute(deps)

        # Get growth event counts
        try:
            counts = await deps.storage_service.get_growth_event_counts(days=days)
            metrics.growth_events_total = sum(counts.values())
            metrics.patterns_created_period = counts.get("pattern_created", 0)
            metrics.patterns_reinforced_period = counts.get("pattern_reinforced", 0)
            metrics.confidence_upgrades_period = counts.get("confidence_upgraded", 0)
            metrics.experiences_recorded_period = counts.get("experience_recorded", 0)
        except Exception:
            logger.debug("Growth event counts unavailable")

        # Get review score trending
        try:
            reviews = await deps.storage_service.get_review_history(limit=20)
            metrics.reviews_completed_period = len(reviews)
            if reviews:
                scores = [r["overall_score"] for r in reviews if "overall_score" in r]
                if scores:
                    metrics.avg_review_score = round(sum(scores) / len(scores), 1)
                    # Trend: compare first half vs second half
                    if len(scores) >= 4:
                        mid = len(scores) // 2
                        recent_avg = sum(scores[:mid]) / mid
                        older_avg = sum(scores[mid:]) / (len(scores) - mid)
                        if recent_avg > older_avg + 0.5:
                            metrics.review_score_trend = "improving"
                        elif recent_avg < older_avg - 0.5:
                            metrics.review_score_trend = "declining"
        except Exception:
            logger.debug("Review history unavailable")

        # Detect stale patterns (not reinforced in 30+ days)
        try:
            patterns = await deps.storage_service.get_patterns()
            from datetime import date, timedelta
            cutoff = str(date.today() - timedelta(days=30))
            stale = [
                p["name"] for p in patterns
                if p.get("date_updated", "") < cutoff and p.get("confidence") != "HIGH"
            ]
            metrics.stale_patterns = stale[:10]  # cap at 10
        except Exception:
            logger.debug("Stale pattern detection failed")

        return metrics
