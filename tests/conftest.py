"""Shared test fixtures for Second Brain tests."""

import pytest
from unittest.mock import MagicMock, AsyncMock

from second_brain.config import BrainConfig
from second_brain.deps import BrainDeps


@pytest.fixture
def brain_config(tmp_path):
    """Create a test BrainConfig."""
    return BrainConfig(
        anthropic_api_key="test-key",
        openai_api_key="test-key",
        supabase_url="https://test.supabase.co",
        supabase_key="test-key",
        brain_data_path=tmp_path,
    )


# Alias for backward compatibility with existing tests
mock_config = brain_config


@pytest.fixture
def mock_memory():
    """Create a mocked MemoryService."""
    memory = MagicMock()
    memory.search = AsyncMock(return_value=[
        {"memory": "Test memory content", "score": 0.9}
    ])
    memory.add = AsyncMock(return_value={"id": "test-id"})
    memory.get_all = AsyncMock(return_value=[])
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
    return storage


@pytest.fixture
def mock_deps(brain_config, mock_memory, mock_storage):
    """Create a BrainDeps with all mocked services."""
    return BrainDeps(
        config=brain_config,
        memory_service=mock_memory,
        storage_service=mock_storage,
    )
