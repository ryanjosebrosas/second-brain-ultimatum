"""HTTP client wrapper for all FastAPI calls.

All methods are synchronous — Streamlit's runtime is not async.
Uses session_state to cache the httpx client instance.
"""

import httpx
import streamlit as st

from config import API_BASE


def _get_client() -> httpx.Client:
    """Get or create a cached httpx client."""
    if "api_client" not in st.session_state:
        st.session_state.api_client = httpx.Client(
            base_url=API_BASE,
            timeout=120.0,
        )
    return st.session_state.api_client


# --- Agent methods ---

def call_agent(endpoint: str, payload: dict) -> dict:
    """Call an agent endpoint with a JSON payload."""
    client = _get_client()
    response = client.post(endpoint, json=payload)
    response.raise_for_status()
    return response.json()


# --- Memory methods ---

def search_memory(endpoint: str, params: dict | None = None) -> dict:
    """Search a memory table with optional filter params."""
    client = _get_client()
    response = client.get(endpoint, params=params or {})
    response.raise_for_status()
    return response.json()


def semantic_search(query: str) -> dict:
    """Search Mem0 semantic memory via the recall agent."""
    return call_agent("/recall", {"query": query})


def vector_search(query: str, table: str = "memory_content", limit: int = 10) -> dict:
    """Search using vector similarity (pgvector)."""
    client = _get_client()
    response = client.post("/search/vector", json={
        "query": query, "table": table, "limit": limit,
    })
    response.raise_for_status()
    return response.json()


def delete_item(table: str, item_id: str) -> dict:
    """Delete an item by table and ID."""
    client = _get_client()
    response = client.delete(f"/items/{table}/{item_id}")
    response.raise_for_status()
    return response.json()


# --- Health methods ---

def get_health() -> dict:
    """Get brain health metrics."""
    client = _get_client()
    response = client.get("/health/metrics")
    response.raise_for_status()
    return response.json()


def get_growth(days: int = 30) -> dict:
    """Get growth report."""
    client = _get_client()
    response = client.get("/health/growth", params={"days": days})
    response.raise_for_status()
    return response.json()


def get_milestones() -> dict:
    """Get brain level and milestone progress."""
    client = _get_client()
    response = client.get("/health/milestones")
    response.raise_for_status()
    return response.json()


def get_quality(days: int = 30) -> dict:
    """Get quality trending data."""
    client = _get_client()
    response = client.get("/health/quality", params={"days": days})
    response.raise_for_status()
    return response.json()


def get_setup() -> dict:
    """Check brain setup status."""
    client = _get_client()
    response = client.get("/health/setup")
    response.raise_for_status()
    return response.json()


# --- Project methods ---

def list_projects(lifecycle_stage: str | None = None, category: str | None = None) -> dict:
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


def get_project(project_id: str) -> dict:
    """Get project details."""
    client = _get_client()
    response = client.get(f"/projects/{project_id}")
    response.raise_for_status()
    return response.json()


def create_project(name: str, category: str = "content", description: str | None = None) -> dict:
    """Create a new project."""
    client = _get_client()
    payload: dict = {"name": name, "category": category}
    if description:
        payload["description"] = description
    response = client.post("/projects/", json=payload)
    response.raise_for_status()
    return response.json()


def delete_project(project_id: str) -> dict:
    """Delete a project."""
    client = _get_client()
    response = client.delete(f"/projects/{project_id}")
    response.raise_for_status()
    return response.json()


# --- Content type methods ---

def get_content_types() -> dict:
    """List all available content types."""
    client = _get_client()
    response = client.get("/content-types")
    response.raise_for_status()
    return response.json()


# --- Graph methods ---

def graph_search(query: str, limit: int = 10) -> dict:
    """Search knowledge graph."""
    client = _get_client()
    response = client.post("/graph/search", json={"query": query, "limit": limit})
    response.raise_for_status()
    return response.json()


def graph_health() -> dict:
    """Get graph health status."""
    client = _get_client()
    response = client.get("/graph/health")
    response.raise_for_status()
    return response.json()


def graph_episodes(group_id: str | None = None) -> dict:
    """List graph episodes."""
    client = _get_client()
    params = {"group_id": group_id} if group_id else {}
    response = client.get("/graph/episodes", params=params)
    response.raise_for_status()
    return response.json()


# --- Settings methods ---

def get_settings_config() -> dict:
    """Get system config (secrets redacted)."""
    client = _get_client()
    response = client.get("/settings/config")
    response.raise_for_status()
    return response.json()


def get_settings_providers() -> dict:
    """Get active provider information."""
    client = _get_client()
    response = client.get("/settings/providers")
    response.raise_for_status()
    return response.json()
