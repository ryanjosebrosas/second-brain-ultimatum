"""Tests for GraphitiMemoryAdapter."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from second_brain.services.graphiti_memory import GraphitiMemoryAdapter
from second_brain.services.abstract import MemoryServiceBase
from second_brain.services.search_result import SearchResult


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.brain_user_id = "test-user"
    return config


@pytest.fixture
def mock_graphiti():
    """A mocked GraphitiService instance."""
    gs = AsyncMock()
    # GraphitiService.search returns list[dict], NOT SearchResult
    gs.search = AsyncMock(return_value=[
        {"source": "test fact", "relationship": "relates_to", "target": "topic"},
    ])
    gs.add_episode = AsyncMock(return_value=None)
    return gs


@pytest.fixture
def adapter(mock_config, mock_graphiti):
    """GraphitiMemoryAdapter with mocked GraphitiService."""
    # Patch at source module — GraphitiService is lazy-imported inside __init__
    with patch(
        "second_brain.services.graphiti.GraphitiService",
        return_value=mock_graphiti,
    ):
        a = GraphitiMemoryAdapter(mock_config)
    return a


class TestGraphitiMemoryAdapter:
    """Unit tests for GraphitiMemoryAdapter."""

    def test_is_subclass_of_memory_service_base(self):
        """GraphitiMemoryAdapter must be a MemoryServiceBase subclass."""
        assert issubclass(GraphitiMemoryAdapter, MemoryServiceBase)

    def test_user_id_set_from_config(self, adapter):
        """user_id is pulled from config.brain_user_id."""
        assert adapter.user_id == "test-user"

    async def test_add_calls_add_episode_with_group_id(self, adapter, mock_graphiti):
        """add() delegates to GraphitiService.add_episode with user_id as group_id."""
        await adapter.add("hello world", metadata={"source": "test"})
        mock_graphiti.add_episode.assert_awaited_once_with(
            "hello world", metadata={"source": "test"}, group_id="test-user"
        )

    async def test_add_returns_ok_dict(self, adapter):
        """add() returns {'status': 'ok'} on success."""
        result = await adapter.add("content")
        assert result == {"status": "ok"}

    async def test_add_with_metadata_delegates_to_add_episode(self, adapter, mock_graphiti):
        """add_with_metadata() calls add_episode with the metadata argument."""
        await adapter.add_with_metadata("content", {"tag": "x"})
        mock_graphiti.add_episode.assert_awaited()

    async def test_search_returns_search_result(self, adapter):
        """search() returns a SearchResult instance."""
        result = await adapter.search("test query")
        assert isinstance(result, SearchResult)

    async def test_search_passes_group_id(self, adapter, mock_graphiti):
        """search() passes user_id as group_id to GraphitiService.search."""
        await adapter.search("query", limit=5)
        mock_graphiti.search.assert_awaited_once_with(
            "query", limit=5, group_id="test-user"
        )

    async def test_search_with_filters_appends_filter_terms(self, adapter, mock_graphiti):
        """search_with_filters() appends metadata filter values to query string."""
        await adapter.search_with_filters("react hooks", {"category": "pattern"}, limit=10)
        call_args = mock_graphiti.search.call_args
        query_arg = call_args.args[0] if call_args.args else call_args.kwargs.get("query", "")
        assert "pattern" in query_arg

    async def test_search_by_category_prepends_category(self, adapter, mock_graphiti):
        """search_by_category() prepends category to query string."""
        await adapter.search_by_category("patterns", "react hooks", limit=5)
        call_args = mock_graphiti.search.call_args
        query_arg = call_args.args[0] if call_args.args else call_args.kwargs.get("query", "")
        assert "patterns" in query_arg
        assert "react hooks" in query_arg

    async def test_get_all_returns_empty_list(self, adapter):
        """get_all() returns [] — not supported by Graphiti."""
        result = await adapter.get_all()
        assert result == []

    async def test_get_memory_count_returns_zero(self, adapter):
        """get_memory_count() returns 0 — not supported by Graphiti."""
        result = await adapter.get_memory_count()
        assert result == 0

    async def test_delete_returns_none(self, adapter):
        """delete() is a no-op returning None."""
        result = await adapter.delete("some-id")
        assert result is None

    async def test_get_by_id_returns_none(self, adapter):
        """get_by_id() returns None — not supported by Graphiti."""
        result = await adapter.get_by_id("some-id")
        assert result is None

    async def test_delete_all_returns_zero(self, adapter):
        """delete_all() returns 0 — not supported by Graphiti."""
        result = await adapter.delete_all()
        assert result == 0

    async def test_add_returns_empty_dict_on_error(self, adapter, mock_graphiti):
        """add() catches exceptions and returns {} instead of raising."""
        mock_graphiti.add_episode.side_effect = RuntimeError("connection failed")
        result = await adapter.add("content")
        assert result == {}

    async def test_enable_project_graph_is_noop(self, adapter):
        """enable_project_graph() completes without error (Mem0-specific, ignored)."""
        result = await adapter.enable_project_graph()
        assert result is None

    async def test_close_completes_without_error(self, adapter):
        """close() completes without error."""
        result = await adapter.close()
        assert result is None

    async def test_update_memory_is_noop(self, adapter):
        """update_memory() is a no-op returning None."""
        result = await adapter.update_memory("some-id", "new content")
        assert result is None

    async def test_search_default_limit(self, adapter, mock_graphiti):
        """search() uses default limit=10 when no limit provided."""
        await adapter.search("query")
        mock_graphiti.search.assert_awaited_once_with(
            "query", limit=10, group_id="test-user"
        )

    async def test_search_returns_empty_search_result_on_error(self, adapter, mock_graphiti):
        """search() catches exceptions and returns empty SearchResult."""
        mock_graphiti.search.side_effect = RuntimeError("connection refused")
        result = await adapter.search("test query")
        assert isinstance(result, SearchResult)
        assert result.memories == []
        assert result.relations == []

    async def test_search_with_filters_returns_empty_on_error(self, adapter, mock_graphiti):
        """search_with_filters() catches exceptions and returns empty SearchResult."""
        mock_graphiti.search.side_effect = RuntimeError("timeout")
        result = await adapter.search_with_filters("query", {"cat": "pattern"})
        assert isinstance(result, SearchResult)

    async def test_search_by_category_returns_empty_on_error(self, adapter, mock_graphiti):
        """search_by_category() catches exceptions and returns empty SearchResult."""
        mock_graphiti.search.side_effect = RuntimeError("network error")
        result = await adapter.search_by_category("patterns", "react")
        assert isinstance(result, SearchResult)
