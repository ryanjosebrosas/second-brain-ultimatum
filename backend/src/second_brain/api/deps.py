"""FastAPI dependency injection for BrainDeps and model."""

import logging
from fastapi import HTTPException, Request, Security
from fastapi.security import APIKeyHeader
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


_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(
    request: Request,
    api_key: str | None = Security(_api_key_header),
) -> None:
    """Verify API key if BRAIN_API_KEY is configured. Skip auth if not set."""
    config = getattr(request.app.state, "config", None)
    if config is None:
        return
    expected = config.brain_api_key
    if not expected:
        return
    if api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
