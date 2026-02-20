"""Knowledge graph endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException

from second_brain.deps import BrainDeps
from second_brain.api.deps import get_deps
from second_brain.api.schemas import GraphSearchRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/graph", tags=["Graph"])


@router.get("/health")
async def graph_health(deps: BrainDeps = Depends(get_deps)):
    """Get knowledge graph health status."""
    if not deps.graphiti_service:
        return {"status": "disabled", "backend": "none"}
    health = await deps.graphiti_service.health_check()
    return health


@router.post("/search")
async def graph_search(body: GraphSearchRequest, deps: BrainDeps = Depends(get_deps)):
    """Search knowledge graph for relationships."""
    if not deps.graphiti_service:
        raise HTTPException(404, detail="Knowledge graph not enabled")
    results = await deps.graphiti_service.search(body.query, limit=body.limit)
    return {"query": body.query, "results": results, "count": len(results)}


@router.get("/episodes")
async def graph_episodes(group_id: str | None = None, deps: BrainDeps = Depends(get_deps)):
    """List graph episodes."""
    if not deps.graphiti_service:
        raise HTTPException(404, detail="Knowledge graph not enabled")
    episodes = await deps.graphiti_service.get_episodes(group_id=group_id)
    return {"episodes": episodes, "count": len(episodes)}


@router.get("/episode-count")
async def graph_episode_count(group_id: str | None = None, deps: BrainDeps = Depends(get_deps)):
    """Get total episode count."""
    if not deps.graphiti_service:
        raise HTTPException(404, detail="Knowledge graph not enabled")
    count = await deps.graphiti_service.get_episode_count(group_id=group_id)
    return {"count": count}
