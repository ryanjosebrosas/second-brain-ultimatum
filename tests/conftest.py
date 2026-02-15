"""Shared test fixtures for Second Brain tests."""

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
    return storage


@pytest.fixture
def mock_deps(brain_config, mock_memory, mock_storage):
    """Create a BrainDeps with all mocked services."""
    return BrainDeps(
        config=brain_config,
        memory_service=mock_memory,
        storage_service=mock_storage,
    )
