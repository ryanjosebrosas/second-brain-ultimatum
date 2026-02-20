"""FastAPI application for Second Brain REST API."""

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from second_brain.config import BrainConfig
from second_brain.deps import create_deps
from second_brain.models import get_model as get_model_fn

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize BrainDeps on startup, cleanup on shutdown."""
    config = app.state.config  # Set by create_app before lifespan runs
    logger.info("Initializing Second Brain deps for API...")
    app.state.init_error = None
    try:
        deps = create_deps()
        app.state.deps = deps
        logger.info("Core deps initialized")
    except Exception as e:
        logger.error("Failed to initialize deps: %s", e)
        app.state.deps = None
        app.state.model = None
        app.state.init_error = str(e)
        yield
        return

    try:
        model = get_model_fn(config)
        app.state.model = model
        logger.info("Second Brain API initialized successfully")
    except Exception as e:
        logger.error("LLM model init failed (agents will be unavailable): %s", e)
        app.state.model = None
        app.state.init_error = f"LLM model: {e}"
    yield
    logger.info("Second Brain API shutting down")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    config = BrainConfig()

    app = FastAPI(
        title="Second Brain API",
        description="REST API for the Second Brain MCP backend",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.state.config = config  # Store for auth dependency + lifespan

    # CORS — allow Streamlit frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[config.frontend_url, "http://localhost:8501"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers — health exempt from auth, others require API key
    from second_brain.api.routers.agents import router as agents_router
    from second_brain.api.routers.memory import router as memory_router
    from second_brain.api.routers.health import router as health_router
    from second_brain.api.routers.projects import router as projects_router
    from second_brain.api.routers.graph import router as graph_router
    from second_brain.api.routers.settings import router as settings_router
    from second_brain.api.routers.templates import router as templates_router
    from second_brain.api.deps import verify_api_key

    app.include_router(health_router, prefix="/api")  # No auth — monitoring
    app.include_router(agents_router, prefix="/api", dependencies=[Depends(verify_api_key)])
    app.include_router(memory_router, prefix="/api", dependencies=[Depends(verify_api_key)])
    app.include_router(projects_router, prefix="/api", dependencies=[Depends(verify_api_key)])
    app.include_router(graph_router, prefix="/api", dependencies=[Depends(verify_api_key)])
    app.include_router(settings_router, prefix="/api", dependencies=[Depends(verify_api_key)])
    app.include_router(templates_router, prefix="/api", dependencies=[Depends(verify_api_key)])

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    config = BrainConfig()
    uvicorn.run(
        "second_brain.api.main:app",
        host="127.0.0.1",
        port=config.api_port,
    )
