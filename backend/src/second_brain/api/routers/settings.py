"""Settings and configuration endpoints."""

import logging

from fastapi import APIRouter, Depends

from second_brain.deps import BrainDeps
from second_brain.api.deps import get_deps

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/settings", tags=["Settings"])

# Fields to NEVER expose (contain secrets)
_SECRET_FIELDS = {
    "anthropic_api_key", "openai_api_key", "groq_api_key", "voyage_api_key",
    "mem0_api_key", "supabase_key", "neo4j_password", "falkordb_password",
    "claude_oauth_token", "ollama_api_key",
}


@router.get("/config")
async def get_config(deps: BrainDeps = Depends(get_deps)):
    """Get current configuration (secrets redacted)."""
    config_dict = deps.config.model_dump()
    safe_config = {}
    for key, value in config_dict.items():
        if key in _SECRET_FIELDS:
            safe_config[key] = "***" if value else None
        else:
            safe_config[key] = value
    return safe_config


@router.get("/providers")
async def get_providers(deps: BrainDeps = Depends(get_deps)):
    """Get active provider information."""
    return {
        "model_provider": deps.config.model_provider,
        "model_name": deps.config.model_name,
        "memory_provider": deps.config.memory_provider,
        "graph_provider": deps.config.graph_provider,
        "graphiti_enabled": deps.config.graphiti_enabled,
        "embedding_model": deps.config.embedding_model,
        "voyage_available": deps.config.voyage_api_key is not None,
        "services": {
            "memory": type(deps.memory_service).__name__,
            "storage": type(deps.storage_service).__name__ if deps.storage_service else None,
            "graphiti": type(deps.graphiti_service).__name__ if deps.graphiti_service else None,
            "embedding": type(deps.embedding_service).__name__ if deps.embedding_service else None,
            "voyage": type(deps.voyage_service).__name__ if deps.voyage_service else None,
            "email": type(deps.email_service).__name__ if deps.email_service else None,
            "calendar": type(deps.calendar_service).__name__ if deps.calendar_service else None,
            "analytics": type(deps.analytics_service).__name__ if deps.analytics_service else None,
            "task": type(deps.task_service).__name__ if deps.task_service else None,
        },
    }
