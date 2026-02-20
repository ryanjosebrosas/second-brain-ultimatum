"""Shared test fixtures for Second Brain tests."""

import json

import pytest
from unittest.mock import MagicMock, AsyncMock

from second_brain.config import BrainConfig
from second_brain.deps import BrainDeps
from second_brain.services.search_result import SearchResult

# ---------------------------------------------------------------------------
# FastMCP 2.x compatibility: @server.tool() returns FunctionTool objects that
# are not directly callable. Patch __call__ to delegate to the wrapped .fn so
# existing tests that do `await recall(query=...)` keep working.
# ---------------------------------------------------------------------------
try:
    from fastmcp.tools.tool import FunctionTool

    FunctionTool.__call__ = lambda self, *args, **kwargs: self.fn(*args, **kwargs)
except ImportError:
    pass


@pytest.fixture
def brain_config(tmp_path):
    """Create a test BrainConfig."""
    return BrainConfig(
        anthropic_api_key="test-key",
        openai_api_key="test-key",
        mem0_api_key=None,
        graph_provider="none",
        neo4j_url=None,
        neo4j_username=None,
        neo4j_password=None,
        supabase_url="https://test.supabase.co",
        supabase_key="test-key",
        brain_data_path=tmp_path,
        _env_file=None,
    )


# Alias for backward compatibility with existing tests
mock_config = brain_config


@pytest.fixture
def brain_config_graph(tmp_path):
    """Create a test BrainConfig with Mem0 graph enabled."""
    return BrainConfig(
        anthropic_api_key="test-key",
        openai_api_key="test-key",
        mem0_api_key="test-cloud-key",
        graph_provider="mem0",
        supabase_url="https://test.supabase.co",
        supabase_key="test-key",
        brain_data_path=tmp_path,
        _env_file=None,
    )


@pytest.fixture
def mock_memory():
    """Create a mocked MemoryService returning SearchResult."""
    memory = MagicMock()
    memory.search = AsyncMock(return_value=SearchResult(
        memories=[{"memory": "Test memory content", "score": 0.9}],
        relations=[],
    ))
    memory.add = AsyncMock(return_value={"id": "test-id"})
    memory.add_with_metadata = AsyncMock(return_value={"id": "test-meta-id"})
    memory.search_with_filters = AsyncMock(return_value=SearchResult(
        memories=[{"memory": "Test pattern memory", "score": 0.85}],
        relations=[],
        search_filters={"category": "pattern"},
    ))
    memory.update_memory = AsyncMock(return_value=None)
    memory.get_all = AsyncMock(return_value=[])
    memory.get_memory_count = AsyncMock(return_value=0)
    memory.delete = AsyncMock(return_value=None)
    memory.get_by_id = AsyncMock(return_value=None)
    memory.delete_all = AsyncMock(return_value=0)
    memory.search_by_category = AsyncMock(return_value=SearchResult(memories=[], relations=[]))
    memory.add_multimodal = AsyncMock(return_value={"id": "test-multimodal-id"})
    return memory


@pytest.fixture
def mock_memory_graph():
    """Create a mocked MemoryService with graph relations."""
    memory = MagicMock()
    memory.search = AsyncMock(return_value=SearchResult(
        memories=[{"memory": "LinkedIn content strategy", "score": 0.9}],
        relations=[
            {"source": "LinkedIn", "relationship": "uses",
             "target": "content strategy"},
            {"source": "content strategy", "relationship": "includes",
             "target": "brand voice"},
        ],
    ))
    memory.add = AsyncMock(return_value={"id": "test-id"})
    memory.add_with_metadata = AsyncMock(return_value={"id": "test-meta-id"})
    memory.search_with_filters = AsyncMock(return_value=SearchResult(
        memories=[{"memory": "Pattern: Hook First for LinkedIn", "score": 0.9}],
        relations=[
            {"source": "Hook First", "relationship": "applies_to", "target": "LinkedIn"},
        ],
        search_filters={"category": "pattern"},
    ))
    memory.update_memory = AsyncMock(return_value=None)
    memory.get_all = AsyncMock(return_value=[])
    memory.get_memory_count = AsyncMock(return_value=0)
    return memory


@pytest.fixture
def mock_storage():
    """Create a mocked StorageService."""
    storage = MagicMock()
    storage.get_patterns = AsyncMock(return_value=[])
    storage.get_experiences = AsyncMock(return_value=[])
    storage.get_health_history = AsyncMock(return_value=[])
    storage.get_memory_content = AsyncMock(return_value=[])
    storage.upsert_pattern = AsyncMock(return_value={})
    storage.insert_pattern = AsyncMock(return_value={
        "id": "pattern-new", "name": "New Pattern",
        "use_count": 1, "confidence": "LOW",
    })
    storage.add_experience = AsyncMock(return_value={})
    storage.upsert_memory_content = AsyncMock(return_value={})
    storage.get_examples = AsyncMock(return_value=[])
    storage.upsert_example = AsyncMock(return_value={})
    storage.get_knowledge = AsyncMock(return_value=[])
    storage.upsert_knowledge = AsyncMock(return_value={})
    storage.get_pattern_by_name = AsyncMock(return_value=None)
    storage.reinforce_pattern = AsyncMock(return_value={
        "id": "pattern-123", "name": "Test Pattern",
        "use_count": 2, "confidence": "MEDIUM",
    })
    storage.delete_pattern = AsyncMock(return_value=True)
    storage.delete_experience = AsyncMock(return_value=True)
    storage.delete_example = AsyncMock(return_value=True)
    storage.delete_knowledge = AsyncMock(return_value=True)
    # Growth tracking mocks
    storage.add_growth_event = AsyncMock(return_value={
        "id": "growth-1", "event_type": "pattern_created", "event_date": "2026-02-15",
    })
    storage.get_growth_events = AsyncMock(return_value=[])
    storage.get_growth_event_counts = AsyncMock(return_value={})
    storage.add_review_history = AsyncMock(return_value={
        "id": "review-1", "overall_score": 8.0, "verdict": "READY TO SEND",
    })
    storage.get_review_history = AsyncMock(return_value=[])
    storage.add_confidence_transition = AsyncMock(return_value={
        "id": "conf-1", "pattern_name": "Test", "from_confidence": "LOW", "to_confidence": "MEDIUM",
    })
    storage.get_confidence_history = AsyncMock(return_value=[])
    # Content type mocks
    storage.get_content_types = AsyncMock(return_value=[
        {
            "id": "ct-1", "slug": "linkedin", "name": "LinkedIn Post",
            "default_mode": "casual", "structure_hint": "Hook -> Body -> CTA",
            "example_type": "linkedin", "max_words": 300, "description": "LinkedIn feed post",
            "review_dimensions": None, "is_builtin": True,
        },
        {
            "id": "ct-2", "slug": "email", "name": "Professional Email",
            "default_mode": "professional", "structure_hint": "Subject -> Body -> Closing",
            "example_type": "email", "max_words": 500, "description": "Client email",
            "review_dimensions": None, "is_builtin": True,
        },
    ])
    storage.get_content_type_by_slug = AsyncMock(return_value={
        "id": "ct-1", "slug": "linkedin", "name": "LinkedIn Post",
        "default_mode": "casual", "structure_hint": "Hook -> Body -> CTA",
        "example_type": "linkedin", "max_words": 300, "is_builtin": True,
        "review_dimensions": None,
    })
    storage.upsert_content_type = AsyncMock(return_value={
        "id": "ct-new", "slug": "newsletter", "name": "Newsletter",
    })
    storage.delete_content_type = AsyncMock(return_value=True)
    storage.get_patterns_for_content_type = AsyncMock(return_value=[])
    # Project lifecycle
    storage.list_projects = AsyncMock(return_value=[])
    storage.get_project = AsyncMock(return_value=None)
    storage.create_project = AsyncMock(
        return_value={"id": "proj-1", "name": "Test Project", "lifecycle_stage": "planning", "category": "content"}
    )
    storage.update_project = AsyncMock(
        return_value={"id": "proj-1", "name": "Updated Project", "lifecycle_stage": "planning"}
    )
    storage.delete_project = AsyncMock(return_value=True)
    storage.update_project_stage = AsyncMock(
        return_value={"id": "proj-1", "name": "Test Project", "lifecycle_stage": "executing"}
    )
    storage.add_project_artifact = AsyncMock(
        return_value={"id": "art-1", "project_id": "proj-1", "artifact_type": "plan"}
    )
    storage.get_project_artifacts = AsyncMock(return_value=[])
    storage.delete_project_artifact = AsyncMock(return_value=True)
    # Experiences
    storage.get_experience_by_id = AsyncMock(return_value=None)
    # Patterns
    storage.get_pattern_by_id = AsyncMock(return_value=None)
    storage.get_pattern_registry = AsyncMock(return_value=[])
    storage.downgrade_pattern_confidence = AsyncMock(return_value=True)
    storage.update_pattern_failures = AsyncMock(return_value=True)
    # Memory content
    storage.delete_memory_content = AsyncMock(return_value=True)
    # Quality & setup
    storage.get_quality_trending = AsyncMock(return_value={})
    storage.get_setup_status = AsyncMock(return_value={})
    # Vector search
    storage.vector_search = AsyncMock(return_value=[])
    return storage


@pytest.fixture
def mock_embedding_service():
    """Create a mocked EmbeddingService for tests."""
    service = MagicMock()
    service.embed = AsyncMock(return_value=[0.1] * 1024)
    service.embed_query = AsyncMock(return_value=[0.1] * 1024)
    service.embed_batch = AsyncMock(return_value=[[0.1] * 1024])
    service.embed_multimodal = AsyncMock(return_value=[[0.1] * 1024])
    service.close = AsyncMock()
    return service


@pytest.fixture
def mock_voyage_service():
    """Create a mocked VoyageService for tests."""
    service = MagicMock()
    service.embed = AsyncMock(return_value=[0.1] * 1024)
    service.embed_query = AsyncMock(return_value=[0.1] * 1024)
    service.embed_batch = AsyncMock(return_value=[[0.1] * 1024])
    service.multimodal_embed = AsyncMock(return_value=[[0.1] * 1024])
    service.rerank = AsyncMock(return_value=[
        {"index": 0, "document": "Test memory content", "relevance_score": 0.95},
    ])
    service.close = AsyncMock()
    return service


@pytest.fixture
def mock_graphiti():
    """Create a mocked GraphitiService."""
    graphiti = MagicMock()
    graphiti.search = AsyncMock(return_value=[
        {"source": "Pattern A", "relationship": "relates_to", "target": "Topic B"},
    ])
    graphiti.add_episode = AsyncMock(return_value=None)
    graphiti.add_episodes_batch = AsyncMock(return_value=1)
    graphiti.add_episodes_chunked = AsyncMock(return_value=3)
    graphiti.health_check = AsyncMock(return_value={
        "status": "healthy",
        "backend": "neo4j",
    })
    graphiti.is_available = True
    graphiti.backend = "neo4j"
    graphiti.close = AsyncMock(return_value=None)
    return graphiti


@pytest.fixture
def mock_deps(brain_config, mock_memory, mock_storage, mock_embedding_service, mock_voyage_service):
    """Create a BrainDeps with all mocked services."""
    return BrainDeps(
        config=brain_config,
        memory_service=mock_memory,
        storage_service=mock_storage,
        embedding_service=mock_embedding_service,
        voyage_service=mock_voyage_service,
    )


@pytest.fixture
def mock_deps_with_graphiti(brain_config, mock_memory, mock_storage, mock_graphiti):
    """Create a BrainDeps with all mocked services including Graphiti."""
    return BrainDeps(
        config=brain_config,
        memory_service=mock_memory,
        storage_service=mock_storage,
        graphiti_service=mock_graphiti,
    )


# --- Subscription auth fixtures ---


@pytest.fixture
def subscription_config(monkeypatch, tmp_path):
    """BrainConfig with subscription auth enabled."""
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "test-key")
    monkeypatch.setenv("BRAIN_DATA_PATH", str(tmp_path))
    monkeypatch.setenv("USE_SUBSCRIPTION", "true")
    monkeypatch.setenv("CLAUDE_OAUTH_TOKEN", "sk-ant-oat01-test-token-here")
    return BrainConfig(_env_file=None)


@pytest.fixture
def mock_claude_sdk():
    """Mock claude-agent-sdk module for testing without installation."""
    mock_sdk = MagicMock()
    mock_client = MagicMock()
    mock_client.process_message.return_value = '{"query": "test", "matches": [], "summary": "No results"}'
    mock_sdk.ClaudeSDKClient.return_value = mock_client
    mock_sdk.ClaudeAgentOptions = MagicMock()
    return mock_sdk


@pytest.fixture
def mock_oauth_token():
    """A valid test OAuth token."""
    return "sk-ant-oat01-test-token-for-testing-purposes-only"


@pytest.fixture
def credentials_file(tmp_path):
    """Create a mock .credentials.json file."""
    creds = {
        "claudeAiOauth": {
            "accessToken": "sk-ant-oat01-from-credentials-file",
            "refreshToken": "test-refresh-token",
            "expiresAt": "2099-01-01T00:00:00Z",
        }
    }
    creds_dir = tmp_path / ".claude"
    creds_dir.mkdir()
    creds_file = creds_dir / ".credentials.json"
    creds_file.write_text(json.dumps(creds))
    return creds_dir


@pytest.fixture
def mock_health_service():
    """Create a mocked HealthService for tools that use it directly."""
    from second_brain.services.health import HealthMetrics
    service = MagicMock()
    service.compute = AsyncMock(return_value=HealthMetrics(
        memory_count=42,
        total_patterns=10,
        high_confidence=3,
        medium_confidence=5,
        low_confidence=2,
        experience_count=8,
        graph_provider="none",
        latest_update="2026-02-18",
        topics={"messaging": 4, "content": 6},
        status="healthy",
        graphiti_status="disabled",
        graphiti_backend="none",
    ))
    service.compute_growth = AsyncMock(return_value={})
    service.compute_setup_status = AsyncMock(return_value={})
    return service


@pytest.fixture
def mock_embedding_service_error():
    """Embedding service that raises RuntimeError — for error path tests."""
    service = MagicMock()
    service.embed_query = AsyncMock(side_effect=RuntimeError("Embedding API unavailable"))
    service.embed_documents = AsyncMock(side_effect=RuntimeError("Embedding API unavailable"))
    return service


@pytest.fixture
def mock_deps_with_graphiti_full(
    brain_config, mock_memory, mock_storage, mock_embedding_service,
    mock_voyage_service, mock_graphiti,
):
    """BrainDeps with Graphiti enabled AND embedding + voyage services.

    Fixes the gap in mock_deps_with_graphiti which omits embedding and voyage.
    """
    return BrainDeps(
        config=brain_config,
        memory_service=mock_memory,
        storage_service=mock_storage,
        embedding_service=mock_embedding_service,
        voyage_service=mock_voyage_service,
        graphiti_service=mock_graphiti,
    )
