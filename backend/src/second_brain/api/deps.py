"""FastAPI dependency injection for BrainDeps and model."""

import logging
from fastapi import HTTPException, Request
from second_brain.deps import BrainDeps

logger = logging.getLogger(__name__)


def get_deps(request: Request) -> BrainDeps:
    """Get BrainDeps from app state. Raises 503 if not initialized."""
    deps = getattr(request.app.state, "deps", None)
    if deps is None:
        raise HTTPException(status_code=503, detail="Second Brain not initialized")
    return deps


def get_model(request: Request):
    """Get LLM model from app state. Returns None if not set."""
    return getattr(request.app.state, "model", None)
