"""HTTP client wrapper for all FastAPI calls.

All methods are synchronous — Streamlit's runtime is not async.
Uses session_state to cache the httpx client instance.
"""

import logging
from typing import Any

import httpx
import streamlit as st

from config import API_BASE

logger = logging.getLogger(__name__)


def _get_client() -> httpx.Client:
    """Get or create a cached httpx client."""
    if "api_client" not in st.session_state:
        st.session_state.api_client = httpx.Client(
            base_url=API_BASE,
            timeout=120.0,
        )
    return st.session_state.api_client


def check_api_health(timeout: float = 3.0) -> bool:
    """Check if the API server is reachable. Used by app.py sidebar."""
    try:
        response = _get_client().get("/health/metrics", timeout=timeout)
        return response.status_code == 200
    except Exception as e:
        logger.warning("API health check failed: %s", type(e).__name__)
        return False


# --- Agent methods ---

def call_agent(endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Call an agent endpoint with a JSON payload."""
    client = _get_client()
    try:
        response = client.post(endpoint, json=payload)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        logger.error("Agent call to %s failed: %s", endpoint, e.response.status_code)
        return {"error": str(e), "status_code": e.response.status_code}


# --- Memory methods ---

def search_memory(endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Search a memory table with optional filter params."""
    client = _get_client()
    try:
        response = client.get(endpoint, params=params or {})
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        logger.error("Memory search %s failed: %s", endpoint, e.response.status_code)
        return {"error": str(e)}


def semantic_search(query: str) -> dict[str, Any]:
    """Search Mem0 semantic memory via the recall agent."""
    return call_agent("/recall", {"query": query})


def vector_search(query: str, table: str = "memory_content", limit: int = 10) -> dict[str, Any]:
    """Search using vector similarity (pgvector)."""
    client = _get_client()
    try:
        response = client.post("/search/vector", json={
            "query": query, "table": table, "limit": limit,
        })
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as exc:
        return {"error": f"Vector search failed: {exc.response.status_code}"}
    except httpx.RequestError as exc:
        return {"error": f"Vector search connection error: {exc}"}


def delete_item(table: str, item_id: str) -> dict[str, Any]:
    """Delete an item by table and ID."""
    client = _get_client()
    response = client.delete(f"/items/{table}/{item_id}")
    response.raise_for_status()
    return response.json()


# --- Health methods ---

def get_health() -> dict[str, Any]:
    """Get brain health metrics."""
    client = _get_client()
    response = client.get("/health/metrics")
    response.raise_for_status()
    return response.json()


def get_growth(days: int = 30) -> dict[str, Any]:
    """Get growth report."""
    client = _get_client()
    response = client.get("/health/growth", params={"days": days})
    response.raise_for_status()
    return response.json()


def get_milestones() -> dict[str, Any]:
    """Get brain level and milestone progress."""
    client = _get_client()
    response = client.get("/health/milestones")
    response.raise_for_status()
    return response.json()


def get_quality(days: int = 30) -> dict[str, Any]:
    """Get quality trending data."""
    client = _get_client()
    response = client.get("/health/quality", params={"days": days})
    response.raise_for_status()
    return response.json()


def get_setup() -> dict[str, Any]:
    """Check brain setup status."""
    client = _get_client()
    response = client.get("/health/setup")
    response.raise_for_status()
    return response.json()


# --- Project methods ---

def list_projects(lifecycle_stage: str | None = None, category: str | None = None) -> list[dict[str, Any]] | dict[str, Any]:
    """List projects with optional filters."""
    client = _get_client()
    params = {}
    if lifecycle_stage:
        params["lifecycle_stage"] = lifecycle_stage
    if category:
        params["category"] = category
    response = client.get("/projects/", params=params)
    response.raise_for_status()
    return response.json()


def get_project(project_id: str) -> dict[str, Any]:
    """Get project details."""
    client = _get_client()
    response = client.get(f"/projects/{project_id}")
    response.raise_for_status()
    return response.json()


def create_project(name: str, category: str = "content", description: str | None = None) -> dict[str, Any]:
    """Create a new project."""
    client = _get_client()
    payload: dict[str, Any] = {"name": name, "category": category}
    if description:
        payload["description"] = description
    response = client.post("/projects/", json=payload)
    response.raise_for_status()
    return response.json()


def delete_project(project_id: str) -> dict[str, Any]:
    """Delete a project."""
    client = _get_client()
    response = client.delete(f"/projects/{project_id}")
    response.raise_for_status()
    return response.json()


# --- Content type methods ---

def get_content_types() -> list[dict[str, Any]] | dict[str, Any]:
    """List all available content types."""
    client = _get_client()
    response = client.get("/content-types")
    response.raise_for_status()
    return response.json()


# --- Ingest methods ---


def ingest_example(content_type: str, title: str, content: str, notes: str | None = None) -> dict[str, Any]:
    """Add a content example to the example library."""
    client = _get_client()
    payload: dict[str, Any] = {
        "content_type": content_type,
        "title": title,
        "content": content,
    }
    if notes:
        payload["notes"] = notes
    try:
        response = client.post("/ingest/example", json=payload)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        logger.error("Ingest example failed: %s", e.response.status_code)
        return {"error": str(e), "status_code": e.response.status_code}


def ingest_knowledge(category: str, title: str, content: str, tags: str | None = None) -> dict[str, Any]:
    """Add a knowledge entry to the knowledge repository."""
    client = _get_client()
    payload: dict[str, Any] = {
        "category": category,
        "title": title,
        "content": content,
    }
    if tags:
        payload["tags"] = tags
    try:
        response = client.post("/ingest/knowledge", json=payload)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        logger.error("Ingest knowledge failed: %s", e.response.status_code)
        return {"error": str(e), "status_code": e.response.status_code}


def upload_file(
    file_bytes: bytes, filename: str, content_type: str,
    context: str = "", category: str = "general",
) -> dict[str, Any]:
    """Upload a file for ingestion (image, PDF, or text document)."""
    client = _get_client()
    try:
        response = client.post(
            "/ingest/file",
            files={"file": (filename, file_bytes, content_type)},
            data={"context": context, "category": category},
            timeout=180.0,
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        logger.error("File upload failed: %s", e.response.status_code)
        return {"error": str(e), "status_code": e.response.status_code}


# --- Graph methods ---

def graph_search(query: str, limit: int = 10) -> dict[str, Any]:
    """Search knowledge graph."""
    client = _get_client()
    response = client.post("/graph/search", json={"query": query, "limit": limit})
    response.raise_for_status()
    return response.json()


def graph_health() -> dict[str, Any]:
    """Get graph health status."""
    client = _get_client()
    response = client.get("/graph/health")
    response.raise_for_status()
    return response.json()


def graph_episodes(group_id: str | None = None) -> dict[str, Any]:
    """List graph episodes."""
    client = _get_client()
    params = {"group_id": group_id} if group_id else {}
    response = client.get("/graph/episodes", params=params)
    response.raise_for_status()
    return response.json()


# --- Settings methods ---

def get_settings_config() -> dict[str, Any]:
    """Get system config (secrets redacted)."""
    client = _get_client()
    response = client.get("/settings/config")
    response.raise_for_status()
    return response.json()


def get_settings_providers() -> dict[str, Any]:
    """Get active provider information."""
    client = _get_client()
    response = client.get("/settings/providers")
    response.raise_for_status()
    return response.json()
