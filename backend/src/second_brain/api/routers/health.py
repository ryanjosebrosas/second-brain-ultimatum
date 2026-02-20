"""Health, growth, and dashboard endpoints."""

import dataclasses
import json
import logging
import time

from fastapi import APIRouter, Depends, Query, Request, Response

from second_brain.deps import BrainDeps
from second_brain.api.deps import get_deps

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/health", tags=["Health"])

_START_TIME = time.monotonic()


@router.get("/live")
async def liveness():
    """Liveness probe — is the event loop running? No I/O."""
    return {"status": "ok", "uptime_seconds": round(time.monotonic() - _START_TIME, 1)}


@router.get("/ready")
async def readiness(request: Request):
    """Readiness probe — can the app serve agent requests?"""
    deps = getattr(request.app.state, "deps", None)
    model = getattr(request.app.state, "model", None)
    init_error = getattr(request.app.state, "init_error", None)
    if deps is None:
        return Response(
            content=f'{{"status":"not_ready","reason":"deps not initialized","error":{json.dumps(init_error)}}}',
            media_type="application/json",
            status_code=503,
        )
    return {
        "status": "ready",
        "deps": "ok",
        "model": "ok" if model is not None else "unavailable",
    }


@router.get("/metrics")
async def brain_health(deps: BrainDeps = Depends(get_deps)):
    """Get brain health metrics."""
    from second_brain.services.health import HealthService
    metrics = await HealthService().compute(deps)
    return dataclasses.asdict(metrics)


@router.get("/growth")
async def growth_report(days: int = Query(default=30, ge=1, le=365), deps: BrainDeps = Depends(get_deps)):
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
async def quality_trend(days: int = Query(default=30, ge=1, le=365), deps: BrainDeps = Depends(get_deps)):
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
