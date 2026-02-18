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
    # Graphiti status
    graphiti_status: str = "disabled"  # disabled, healthy, degraded, unavailable
    graphiti_backend: str = "none"  # neo4j, falkordb, none
    errors: list[str] = field(default_factory=list)


class HealthService:
    """Compute brain health and growth metrics."""

    async def compute(self, deps: "BrainDeps") -> HealthMetrics:
        """Compute current health metrics from all services."""
        errors: list[str] = []

        try:
            patterns = await deps.storage_service.get_patterns()
        except Exception as e:
            logger.warning("Health: patterns unavailable: %s", type(e).__name__)
            patterns = []
            errors.append(f"patterns: {type(e).__name__}")

        try:
            experiences = await deps.storage_service.get_experiences()
        except Exception as e:
            logger.warning("Health: experiences unavailable: %s", type(e).__name__)
            experiences = []
            errors.append(f"experiences: {type(e).__name__}")

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
        except Exception as e:
            memory_count = "unavailable"
            errors.append(f"memory_count: {type(e).__name__}")

        latest = patterns[0].get("date_updated", "unknown") if patterns else "none"
        graph = deps.config.graph_provider or "disabled"
        status = "GROWING" if total > 5 else "BUILDING"

        # Graphiti health
        graphiti_status = "disabled"
        graphiti_backend = "none"
        if deps.graphiti_service:
            try:
                health = await deps.graphiti_service.health_check()
                graphiti_status = health.get("status", "unavailable")
                graphiti_backend = health.get("backend", "none")
            except Exception as e:
                graphiti_status = "unavailable"
                errors.append(f"graphiti: {type(e).__name__}")

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
            graphiti_status=graphiti_status,
            graphiti_backend=graphiti_backend,
            errors=errors,
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
        except Exception as e:
            logger.debug("Growth event counts unavailable: %s", type(e).__name__)
            metrics.errors.append(f"growth_events: {type(e).__name__}")

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
        except Exception as e:
            logger.debug("Review history unavailable: %s", type(e).__name__)
            metrics.errors.append(f"review_history: {type(e).__name__}")

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
        except Exception as e:
            logger.debug("Stale pattern detection failed: %s", type(e).__name__)
            metrics.errors.append(f"stale_patterns: {type(e).__name__}")

        return metrics

    async def compute_milestones(self, deps: "BrainDeps") -> dict:
        """Compute brain growth level and milestone progress."""
        from second_brain.schemas import (
            BRAIN_MILESTONES, BRAIN_LEVEL_THRESHOLDS,
            BrainMilestone,
        )

        # Get current metrics
        metrics = await self.compute(deps)
        growth = await self.compute_growth(deps)

        # Compute milestone completion
        milestones = []
        for m in BRAIN_MILESTONES:
            reqs = m["requires"]
            completed = True
            if "min_patterns" in reqs and metrics.total_patterns < reqs["min_patterns"]:
                completed = False
            if "min_medium" in reqs and metrics.medium_confidence < reqs["min_medium"]:
                completed = False
            if "min_high" in reqs and metrics.high_confidence < reqs["min_high"]:
                completed = False
            if "min_experiences" in reqs and metrics.experience_count < reqs["min_experiences"]:
                completed = False
            if "min_avg_score" in reqs and growth.avg_review_score < reqs["min_avg_score"]:
                completed = False
            milestones.append(BrainMilestone(
                name=m["name"],
                description=m["description"],
                completed=completed,
            ))

        # Determine brain level (check from most restrictive downward)
        level = "EMPTY"
        for lvl in ["EXPERT", "COMPOUND", "GROWTH", "FOUNDATION"]:
            reqs = BRAIN_LEVEL_THRESHOLDS[lvl]
            meets = True
            if "min_patterns" in reqs and metrics.total_patterns < reqs["min_patterns"]:
                meets = False
            if "min_medium" in reqs and metrics.medium_confidence < reqs["min_medium"]:
                meets = False
            if "min_high" in reqs and metrics.high_confidence < reqs["min_high"]:
                meets = False
            if "min_experiences" in reqs and metrics.experience_count < reqs["min_experiences"]:
                meets = False
            if "min_avg_score" in reqs and growth.avg_review_score < reqs["min_avg_score"]:
                meets = False
            if meets:
                level = lvl
                break

        level_descriptions = {
            "EMPTY": "No patterns or experiences yet — start with /plan and /learn",
            "FOUNDATION": "Building first patterns — keep learning from each project",
            "GROWTH": "Patterns reaching MEDIUM confidence — compound returns emerging",
            "COMPOUND": "HIGH confidence patterns active — significant time savings",
            "EXPERT": "Multiple HIGH patterns, consistent quality — brain is thriving",
        }

        # Find next unachieved milestone
        next_milestone = None
        for m in milestones:
            if not m.completed:
                next_milestone = m.description
                break

        return {
            "level": level,
            "level_description": level_descriptions[level],
            "milestones": [m.model_dump() for m in milestones],
            "milestones_completed": sum(1 for m in milestones if m.completed),
            "milestones_total": len(milestones),
            "next_milestone": next_milestone,
            "patterns_total": metrics.total_patterns,
            "high_confidence_count": metrics.high_confidence,
            "experiences_total": metrics.experience_count,
            "avg_review_score": growth.avg_review_score,
        }

    async def compute_quality_trend(self, deps: "BrainDeps", days: int = 30) -> dict:
        """Compute quality trend from review history."""
        trending_data = await deps.storage_service.get_quality_trending(days=days)

        # Compute dimensional trends
        by_dimension = []
        for dim, data in trending_data.get("by_dimension", {}).items():
            by_dimension.append({
                "dimension": dim,
                "avg_score": round(data["avg_score"], 2),
                "review_count": data["count"],
                "trend": "stable",
            })

        # Compute score trend (compare first half vs second half of period)
        score_trend = "stable"
        total = trending_data.get("total_reviews", 0)
        if total >= 4:
            reviews = await deps.storage_service.get_review_history(limit=total)
            if len(reviews) >= 4:
                mid = len(reviews) // 2
                recent_avg = sum(r.get("overall_score", 0) for r in reviews[:mid]) / mid
                older_avg = sum(r.get("overall_score", 0) for r in reviews[mid:]) / (len(reviews) - mid)
                if recent_avg > older_avg + 0.5:
                    score_trend = "improving"
                elif recent_avg < older_avg - 0.5:
                    score_trend = "declining"

        return {
            "period_days": days,
            "total_reviews": trending_data.get("total_reviews", 0),
            "avg_score": trending_data.get("avg_score", 0.0),
            "score_trend": score_trend,
            "by_dimension": by_dimension,
            "by_content_type": trending_data.get("by_content_type", {}),
            "recurring_issues": trending_data.get("recurring_issues", []),
            "excellence_count": trending_data.get("excellence_count", 0),
            "needs_work_count": trending_data.get("needs_work_count", 0),
        }

    async def check_confidence_downgrades(self, deps: "BrainDeps") -> list[dict]:
        """Check for patterns that should be downgraded due to consecutive failures."""
        downgrades = []
        try:
            patterns = await deps.storage_service.get_patterns()
            threshold = deps.config.confidence_downgrade_consecutive

            for p in patterns:
                failures = p.get("consecutive_failures", 0)
                if failures >= threshold and p.get("confidence", "LOW") != "LOW":
                    result = await deps.storage_service.downgrade_pattern_confidence(p["id"])
                    if result:
                        old_conf = p["confidence"]
                        new_conf = result.get("confidence", old_conf)
                        downgrades.append({
                            "pattern_name": p["name"],
                            "old_confidence": old_conf,
                            "new_confidence": new_conf,
                            "consecutive_failures": failures,
                        })
                        # Record growth event
                        try:
                            await deps.storage_service.add_growth_event({
                                "event_type": "confidence_downgraded",
                                "pattern_name": p["name"],
                                "pattern_topic": p.get("topic", ""),
                                "details": {
                                    "from": old_conf,
                                    "to": new_conf,
                                    "failures": failures,
                                },
                            })
                        except Exception:
                            logger.debug("Growth event recording failed (non-critical)")
                        # Record confidence transition
                        try:
                            await deps.storage_service.add_confidence_transition({
                                "pattern_name": p["name"],
                                "pattern_topic": p.get("topic", ""),
                                "from_confidence": old_conf,
                                "to_confidence": new_conf,
                                "use_count": p.get("use_count", 0),
                                "reason": f"Downgraded after {failures} consecutive failures below score {deps.config.confidence_downgrade_threshold}",
                            })
                        except Exception:
                            logger.debug("Confidence transition recording failed (non-critical)")
        except Exception as e:
            logger.warning("Confidence downgrade check failed: %s", type(e).__name__)
            logger.debug("Downgrade check error detail: %s", e)

        return downgrades

    async def compute_setup_status(self, deps: "BrainDeps") -> dict:
        """Check brain onboarding/setup completion status."""
        status = await deps.storage_service.get_setup_status()

        steps = [
            {
                "name": "company_context",
                "description": "Add company info (products, positioning, differentiators)",
                "completed": "company" in status.get("populated_categories", []),
            },
            {
                "name": "customer_context",
                "description": "Add customer intelligence (ICP, pain points, objections)",
                "completed": "customers" in status.get("populated_categories", []),
            },
            {
                "name": "personal_context",
                "description": "Add personal info (bio, expertise, services)",
                "completed": "personal" in status.get("populated_categories", []),
            },
            {
                "name": "audience_context",
                "description": "Add audience/target client profile",
                "completed": "audience" in status.get("populated_categories", []),
            },
            {
                "name": "style_voice",
                "description": "Add style and voice guide (tone, vocabulary, structure)",
                "completed": "style-voice" in status.get("populated_categories", []),
            },
            {
                "name": "values_beliefs",
                "description": "Add values, principles, and POVs",
                "completed": "values-beliefs" in status.get("populated_categories", []),
            },
            {
                "name": "first_pattern",
                "description": "Extract your first pattern with /learn",
                "completed": status.get("has_patterns", False),
            },
            {
                "name": "first_example",
                "description": "Add your first content example",
                "completed": status.get("has_examples", False),
            },
        ]

        return {
            "is_complete": all(s["completed"] for s in steps),
            "steps": steps,
            "completed_count": sum(1 for s in steps if s["completed"]),
            "total_steps": len(steps),
            "missing_categories": status.get("missing_categories", []),
            "total_memory_entries": status.get("total_memory_entries", 0),
        }
