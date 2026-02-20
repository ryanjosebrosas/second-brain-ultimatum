"""FastAPI application for Second Brain REST API."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from second_brain.config import BrainConfig
from second_brain.deps import create_deps
from second_brain.models import get_model

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize BrainDeps on startup, cleanup on shutdown."""
    config = BrainConfig()
    logger.info("Initializing Second Brain deps for API...")
    try:
        deps = create_deps()
        model = get_model(config)
        app.state.deps = deps
        app.state.model = model
        logger.info("Second Brain API initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize deps: %s", e)
        app.state.deps = None
        app.state.model = None
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

    # CORS — allow Streamlit frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[config.frontend_url, "http://localhost:8501"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    from second_brain.api.routers.agents import router as agents_router
    from second_brain.api.routers.memory import router as memory_router
    from second_brain.api.routers.health import router as health_router
    from second_brain.api.routers.projects import router as projects_router
    from second_brain.api.routers.graph import router as graph_router
    from second_brain.api.routers.settings import router as settings_router

    app.include_router(agents_router, prefix="/api")
    app.include_router(memory_router, prefix="/api")
    app.include_router(health_router, prefix="/api")
    app.include_router(projects_router, prefix="/api")
    app.include_router(graph_router, prefix="/api")
    app.include_router(settings_router, prefix="/api")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    config = BrainConfig()
    uvicorn.run(
        "second_brain.api.main:app",
        host="0.0.0.0",
        port=config.api_port,
        reload=True,
    )
