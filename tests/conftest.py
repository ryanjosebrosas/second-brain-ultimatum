"""Shared test fixtures for Second Brain tests."""

import json

import pytest
from unittest.mock import MagicMock, AsyncMock

from second_brain.config import BrainConfig
from second_brain.deps import BrainDeps
from second_brain.services.search_result import SearchResult


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
    return storage


@pytest.fixture
def mock_graphiti():
    """Create a mocked GraphitiService."""
    graphiti = MagicMock()
    graphiti.search = AsyncMock(return_value=[
        {"source": "Pattern A", "relationship": "relates_to", "target": "Topic B"},
    ])
    graphiti.add_episode = AsyncMock(return_value=None)
    graphiti.add_episodes_batch = AsyncMock(return_value=1)
    graphiti.health_check = AsyncMock(return_value={
        "status": "healthy",
        "backend": "neo4j",
    })
    graphiti.is_available = True
    graphiti.backend = "neo4j"
    graphiti.close = AsyncMock(return_value=None)
    return graphiti


@pytest.fixture
def mock_deps(brain_config, mock_memory, mock_storage):
    """Create a BrainDeps with all mocked services."""
    return BrainDeps(
        config=brain_config,
        memory_service=mock_memory,
        storage_service=mock_storage,
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
