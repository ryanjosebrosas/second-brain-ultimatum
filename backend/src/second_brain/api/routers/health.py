"""Health, growth, and dashboard endpoints."""

import dataclasses
import logging

from fastapi import APIRouter, Depends

from second_brain.deps import BrainDeps
from second_brain.api.deps import get_deps

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/metrics")
async def brain_health(deps: BrainDeps = Depends(get_deps)):
    """Get brain health metrics."""
    from second_brain.services.health import HealthService
    metrics = await HealthService().compute(deps)
    return dataclasses.asdict(metrics)


@router.get("/growth")
async def growth_report(days: int = 30, deps: BrainDeps = Depends(get_deps)):
    """Get growth report for the brain."""
    from second_brain.services.health import HealthService
    health = HealthService()
    metrics = await health.compute_growth(deps, days=days)
    return dataclasses.asdict(metrics)


@router.get("/milestones")
async def milestones(deps: BrainDeps = Depends(get_deps)):
    """Get brain level and milestone progress."""
    from second_brain.services.health import HealthService
    health = HealthService()
    milestone_data = await health.compute_milestones(deps)
    return milestone_data


@router.get("/quality")
async def quality_trend(days: int = 30, deps: BrainDeps = Depends(get_deps)):
    """Get quality trending data."""
    from second_brain.services.health import HealthService
    health = HealthService()
    quality = await health.compute_quality_trend(deps, days=days)
    return quality


@router.get("/setup")
async def setup_status(deps: BrainDeps = Depends(get_deps)):
    """Check brain setup/onboarding status."""
    from second_brain.services.health import HealthService
    health = HealthService()
    status = await health.compute_setup_status(deps)
    return status


@router.get("/confidence-checks")
async def confidence_checks(deps: BrainDeps = Depends(get_deps)):
    """Check for confidence downgrades based on review scores."""
    from second_brain.services.health import HealthService
    health = HealthService()
    downgrades = await health.check_confidence_downgrades(deps)
    return {"downgrades": downgrades, "count": len(downgrades)}
