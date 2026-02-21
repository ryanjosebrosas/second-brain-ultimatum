"""Tests for GraphitiMemoryAdapter."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from second_brain.services.graphiti_memory import GraphitiMemoryAdapter
from second_brain.services.abstract import MemoryServiceBase
from second_brain.services.search_result import SearchResult


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.brain_user_id = "test-user"
    config.service_timeout_seconds = 30
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
    gs.remove_episode = AsyncMock(return_value=True)
    gs.get_episodes = AsyncMock(return_value=[
        {
            "id": "ep-uuid-1",
            "content": "first episode content",
            "source": "learn_agent",
            "created_at": "2026-02-20T00:00:00",
        },
        {
            "id": "ep-uuid-2",
            "content": "second episode content",
            "source": "ask_agent",
            "created_at": "2026-02-20T01:00:00",
        },
    ])
    gs.get_episode_by_id = AsyncMock(return_value={
        "id": "ep-uuid-2",
        "content": "second episode content",
        "source": "ask_agent",
        "created_at": "2026-02-20T01:00:00",
    })
    gs.get_episode_count = AsyncMock(return_value=2)
    gs.delete_group_data = AsyncMock(return_value=3)
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

    async def test_search_accepts_filter_memories_param(self, adapter):
        """GraphitiMemoryAdapter.search() accepts filter_memories but ignores it."""
        # Should not raise, even though Graphiti doesn't support filter_memories
        result = await adapter.search("test", filter_memories=True)
        assert isinstance(result, SearchResult)

    async def test_search_with_filters_accepts_filter_memories_param(self, adapter):
        """GraphitiMemoryAdapter.search_with_filters() accepts filter_memories but ignores it."""
        # Should not raise, even though Graphiti doesn't support filter_memories
        result = await adapter.search_with_filters("test", filter_memories=True)
        assert isinstance(result, SearchResult)

    async def test_search_with_filters_appends_filter_terms(self, adapter, mock_graphiti):
        """search_with_filters() prepends metadata filter values to query string."""
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

    # --- get_all ---

    async def test_get_all_returns_episodes(self, adapter, mock_graphiti):
        """get_all() returns episodes in Mem0-compatible format."""
        result = await adapter.get_all()
        assert len(result) == 2
        assert result[0]["id"] == "ep-uuid-1"
        assert result[0]["memory"] == "first episode content"
        assert result[0]["metadata"]["source"] == "learn_agent"
        mock_graphiti.get_episodes.assert_awaited_once_with("test-user")

    async def test_get_all_returns_empty_on_error(self, adapter, mock_graphiti):
        """get_all() returns [] on error."""
        mock_graphiti.get_episodes.side_effect = RuntimeError("connection failed")
        result = await adapter.get_all()
        assert result == []

    # --- get_memory_count ---

    async def test_get_memory_count_returns_real_count(self, adapter, mock_graphiti):
        """get_memory_count() returns real count from GraphitiService."""
        result = await adapter.get_memory_count()
        assert result == 2
        mock_graphiti.get_episode_count.assert_awaited_once_with("test-user")

    async def test_get_memory_count_returns_zero_on_error(self, adapter, mock_graphiti):
        """get_memory_count() returns 0 on error."""
        mock_graphiti.get_episode_count.side_effect = RuntimeError("fail")
        result = await adapter.get_memory_count()
        assert result == 0

    # --- delete ---

    async def test_delete_calls_remove_episode(self, adapter, mock_graphiti):
        """delete() delegates to GraphitiService.remove_episode."""
        result = await adapter.delete("ep-uuid-1")
        assert result is None
        mock_graphiti.remove_episode.assert_awaited_once_with("ep-uuid-1")

    async def test_delete_handles_remove_failure(self, adapter, mock_graphiti):
        """delete() handles remove_episode returning False gracefully."""
        mock_graphiti.remove_episode.return_value = False
        result = await adapter.delete("nonexistent-id")
        assert result is None

    async def test_delete_handles_exception(self, adapter, mock_graphiti):
        """delete() catches exceptions without raising."""
        mock_graphiti.remove_episode.side_effect = RuntimeError("network error")
        result = await adapter.delete("ep-uuid-1")
        assert result is None

    # --- get_by_id ---

    async def test_get_by_id_returns_matching_episode(self, adapter, mock_graphiti):
        """get_by_id() returns the matching episode in Mem0 format."""
        result = await adapter.get_by_id("ep-uuid-2")
        assert result is not None
        assert result["id"] == "ep-uuid-2"
        assert result["memory"] == "second episode content"
        assert result["metadata"]["source"] == "ask_agent"

    async def test_get_by_id_returns_none_when_not_found(self, adapter, mock_graphiti):
        """get_by_id() returns None when ID doesn't match any episode."""
        mock_graphiti.get_episode_by_id = AsyncMock(return_value=None)
        result = await adapter.get_by_id("nonexistent-id")
        assert result is None

    async def test_get_by_id_returns_none_on_error(self, adapter, mock_graphiti):
        """get_by_id() returns None on error."""
        mock_graphiti.get_episode_by_id.side_effect = RuntimeError("fail")
        result = await adapter.get_by_id("ep-uuid-1")
        assert result is None

    # --- delete_all ---

    async def test_delete_all_returns_count(self, adapter, mock_graphiti):
        """delete_all() returns count from GraphitiService.delete_group_data."""
        result = await adapter.delete_all()
        assert result == 3
        mock_graphiti.delete_group_data.assert_awaited_once_with("test-user")

    async def test_delete_all_returns_zero_on_error(self, adapter, mock_graphiti):
        """delete_all() returns 0 on error."""
        mock_graphiti.delete_group_data.side_effect = RuntimeError("fail")
        result = await adapter.delete_all()
        assert result == 0

    # --- update_memory ---

    async def test_update_memory_deletes_then_adds(self, adapter, mock_graphiti):
        """update_memory() deletes old episode and adds new one."""
        await adapter.update_memory("ep-uuid-1", "updated content", {"tag": "new"})
        mock_graphiti.remove_episode.assert_awaited_once_with("ep-uuid-1")
        mock_graphiti.add_episode.assert_awaited_once_with(
            "updated content", metadata={"tag": "new"}, group_id="test-user"
        )

    async def test_update_memory_skips_when_no_content(self, adapter, mock_graphiti):
        """update_memory() skips when content is None."""
        await adapter.update_memory("ep-uuid-1", None)
        mock_graphiti.remove_episode.assert_not_awaited()
        mock_graphiti.add_episode.assert_not_awaited()

    async def test_update_memory_skips_when_empty_content(self, adapter, mock_graphiti):
        """update_memory() skips when content is empty string."""
        await adapter.update_memory("ep-uuid-1", "")
        mock_graphiti.remove_episode.assert_not_awaited()
        mock_graphiti.add_episode.assert_not_awaited()

    async def test_update_memory_handles_error(self, adapter, mock_graphiti):
        """update_memory() catches exceptions without raising."""
        mock_graphiti.remove_episode.side_effect = RuntimeError("fail")
        # Should not raise
        await adapter.update_memory("ep-uuid-1", "new content")

    # --- search_with_filters improvements ---

    async def test_search_with_filters_and_filter(self, adapter, mock_graphiti):
        """search_with_filters() handles AND filter pattern."""
        filters = {"AND": [{"category": "pattern"}, {"source": "learn_agent"}]}
        await adapter.search_with_filters("react", filters, limit=5)
        call_args = mock_graphiti.search.call_args
        query_arg = call_args.args[0] if call_args.args else call_args.kwargs.get("query", "")
        assert "pattern" in query_arg
        assert "learn_agent" in query_arg
        assert "react" in query_arg

    async def test_search_with_filters_in_pattern(self, adapter, mock_graphiti):
        """search_with_filters() handles 'in' filter pattern."""
        filters = {"category": {"in": ["pattern", "insight"]}}
        await adapter.search_with_filters("hooks", filters, limit=5)
        call_args = mock_graphiti.search.call_args
        query_arg = call_args.args[0] if call_args.args else call_args.kwargs.get("query", "")
        assert "pattern" in query_arg
        assert "insight" in query_arg
        assert "hooks" in query_arg

    async def test_search_with_filters_no_filters(self, adapter, mock_graphiti):
        """search_with_filters() passes query unchanged when no filters."""
        await adapter.search_with_filters("react hooks", None, limit=10)
        call_args = mock_graphiti.search.call_args
        query_arg = call_args.args[0] if call_args.args else call_args.kwargs.get("query", "")
        assert query_arg == "react hooks"

    # --- error handling (existing) ---

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

    # --- Criteria Retrieval (Mem0-specific, no-op) ---

    async def test_setup_criteria_retrieval_is_noop(self, adapter):
        """setup_criteria_retrieval() returns True (Mem0-specific, no-op for Graphiti)."""
        result = await adapter.setup_criteria_retrieval()
        assert result is True

    async def test_setup_criteria_retrieval_accepts_criteria_param(self, adapter):
        """setup_criteria_retrieval() accepts criteria param without error."""
        custom_criteria = [{"name": "test", "description": "Test", "weight": 1}]
        result = await adapter.setup_criteria_retrieval(criteria=custom_criteria)
        assert result is True

    async def test_search_accepts_use_criteria_param(self, adapter):
        """search() accepts use_criteria param without error."""
        result = await adapter.search("test", use_criteria=False)
        assert isinstance(result, SearchResult)

    async def test_search_with_filters_accepts_use_criteria_param(self, adapter):
        """search_with_filters() accepts use_criteria param without error."""
        result = await adapter.search_with_filters("test", use_criteria=False)
        assert isinstance(result, SearchResult)

    # --- Custom Instructions (Mem0-specific, no-op) ---

    async def test_setup_custom_instructions_is_noop(self, adapter):
        """setup_custom_instructions() returns True (Mem0-specific, no-op for Graphiti)."""
        result = await adapter.setup_custom_instructions()
        assert result is True

    async def test_setup_custom_instructions_with_custom_is_noop(self, adapter):
        """setup_custom_instructions() accepts custom instructions (no-op)."""
        result = await adapter.setup_custom_instructions(instructions="Custom rules")
        assert result is True


class TestGraphitiMemoryTimeout:
    """Tests for timeout protection in GraphitiMemoryAdapter."""

    @pytest.fixture
    def mock_config(self):
        config = MagicMock()
        config.brain_user_id = "test-user"
        config.service_timeout_seconds = 0.01  # Very short timeout for tests
        return config

    @pytest.fixture
    def slow_graphiti(self):
        """GraphitiService that times out."""
        gs = AsyncMock()

        async def slow_search(*args, **kwargs):
            await asyncio.sleep(100)  # Will be cancelled by timeout
            return []

        gs.search = slow_search
        return gs

    @patch("second_brain.services.graphiti.GraphitiService")
    async def test_search_returns_empty_on_timeout(
        self, mock_gs_cls, mock_config, slow_graphiti
    ):
        """search() returns empty SearchResult on timeout."""
        mock_gs_cls.return_value = slow_graphiti

        adapter = GraphitiMemoryAdapter(mock_config)
        result = await adapter.search("test query")

        assert result.memories == []
        assert result.relations == []

    @patch("second_brain.services.graphiti.GraphitiService")
    async def test_add_returns_empty_on_timeout(self, mock_gs_cls, mock_config):
        """add() returns empty dict on timeout."""
        slow_graphiti = AsyncMock()

        async def slow_add(*args, **kwargs):
            await asyncio.sleep(100)

        slow_graphiti.add_episode = slow_add
        mock_gs_cls.return_value = slow_graphiti

        adapter = GraphitiMemoryAdapter(mock_config)
        result = await adapter.add("test content")

        assert result == {}

    @patch("second_brain.services.graphiti.GraphitiService")
    def test_timeout_uses_config_value(self, mock_gs_cls):
        """Adapter uses service_timeout_seconds from config."""
        config = MagicMock()
        config.brain_user_id = "test-user"
        config.service_timeout_seconds = 42.0
        mock_gs_cls.return_value = AsyncMock()

        adapter = GraphitiMemoryAdapter(config)

        assert adapter._timeout == 42.0


class TestGraphitiMemoryOverrideUserId:
    """Tests for override_user_id in GraphitiMemoryAdapter."""

    @pytest.fixture
    def mock_config(self):
        config = MagicMock()
        config.brain_user_id = "default-user"
        config.service_timeout_seconds = 30
        return config

    @patch("second_brain.services.graphiti.GraphitiService")
    async def test_search_uses_override_user_id(self, mock_gs_cls, mock_config):
        """search() passes override_user_id to GraphitiService."""
        mock_gs = AsyncMock()
        mock_gs.search.return_value = []
        mock_gs_cls.return_value = mock_gs

        adapter = GraphitiMemoryAdapter(mock_config)
        await adapter.search("test query", override_user_id="override-user")

        call_kwargs = mock_gs.search.call_args.kwargs
        assert call_kwargs.get("group_id") == "override-user"

    @patch("second_brain.services.graphiti.GraphitiService")
    async def test_search_uses_default_when_no_override(self, mock_gs_cls, mock_config):
        """search() uses brain_user_id when no override."""
        mock_gs = AsyncMock()
        mock_gs.search.return_value = []
        mock_gs_cls.return_value = mock_gs

        adapter = GraphitiMemoryAdapter(mock_config)
        await adapter.search("test query")

        call_kwargs = mock_gs.search.call_args.kwargs
        assert call_kwargs.get("group_id") == "default-user"

    @patch("second_brain.services.graphiti.GraphitiService")
    async def test_search_with_filters_uses_override(self, mock_gs_cls, mock_config):
        """search_with_filters() respects override_user_id."""
        mock_gs = AsyncMock()
        mock_gs.search.return_value = []
        mock_gs_cls.return_value = mock_gs

        adapter = GraphitiMemoryAdapter(mock_config)
        await adapter.search_with_filters("test", override_user_id="uttam")

        call_kwargs = mock_gs.search.call_args.kwargs
        assert call_kwargs.get("group_id") == "uttam"

    @patch("second_brain.services.graphiti.GraphitiService")
    def test_effective_user_id_helper(self, mock_gs_cls, mock_config):
        """_effective_user_id returns correct user."""
        mock_gs_cls.return_value = AsyncMock()

        adapter = GraphitiMemoryAdapter(mock_config)

        assert adapter._effective_user_id("override") == "override"
        assert adapter._effective_user_id(None) == "default-user"
        assert adapter._effective_user_id("") == "default-user"


class TestGraphitiMemoryIdleReconnect:
    """Tests for idle reconnect logic in GraphitiMemoryAdapter."""

    @pytest.fixture
    def mock_config(self):
        config = MagicMock()
        config.brain_user_id = "test-user"
        config.service_timeout_seconds = 30
        return config

    @patch("time.monotonic")
    @patch("second_brain.services.graphiti.GraphitiService")
    async def test_reconnects_after_idle_threshold(
        self, mock_gs_cls, mock_time, mock_config
    ):
        """Client is re-instantiated after idle threshold exceeded."""
        # First call at t=0
        mock_time.return_value = 0
        mock_gs = AsyncMock()
        mock_gs.search = AsyncMock(return_value=[])
        mock_gs_cls.return_value = mock_gs

        adapter = GraphitiMemoryAdapter(mock_config)
        initial_call_count = mock_gs_cls.call_count

        # Simulate 5 minutes (300s) passing — exceeds 240s threshold
        mock_time.return_value = 300

        await adapter.search("test")

        # Client should have been re-instantiated (2 total: init + reconnect)
        assert mock_gs_cls.call_count == initial_call_count + 1

    @patch("time.monotonic")
    @patch("second_brain.services.graphiti.GraphitiService")
    async def test_no_reconnect_when_recent_activity(
        self, mock_gs_cls, mock_time, mock_config
    ):
        """Client is NOT re-instantiated when activity is recent."""
        mock_time.return_value = 0
        mock_gs = AsyncMock()
        mock_gs.search = AsyncMock(return_value=[])
        mock_gs_cls.return_value = mock_gs

        adapter = GraphitiMemoryAdapter(mock_config)
        initial_call_count = mock_gs_cls.call_count

        # Simulate only 60s passing — well under 240s threshold
        mock_time.return_value = 60

        await adapter.search("test")

        # No reconnect — same call count
        assert mock_gs_cls.call_count == initial_call_count

    @patch("time.monotonic")
    @patch("second_brain.services.graphiti.GraphitiService")
    async def test_activity_updates_on_every_call(
        self, mock_gs_cls, mock_time, mock_config
    ):
        """_last_activity is updated on every method call."""
        mock_time.return_value = 0
        mock_gs = AsyncMock()
        mock_gs.search = AsyncMock(return_value=[])
        mock_gs.add_episode = AsyncMock(return_value=None)
        mock_gs_cls.return_value = mock_gs

        adapter = GraphitiMemoryAdapter(mock_config)

        # First search at t=100
        mock_time.return_value = 100
        await adapter.search("test")

        # Add at t=200 (only 100s since last activity, not 200s since init)
        mock_time.return_value = 200
        await adapter.add("content")

        # Search at t=300 (only 100s since last activity)
        mock_time.return_value = 300
        await adapter.search("test2")

        # No reconnect because each call updates activity timestamp
        # Only 1 GraphitiService instantiation (the initial one)
        assert mock_gs_cls.call_count == 1


class TestGraphitiMemoryRetry:
    """Tests for GraphitiMemoryAdapter retry behavior."""

    @pytest.fixture
    def mock_config(self):
        config = MagicMock()
        config.brain_user_id = "test-user"
        config.service_timeout_seconds = 30  # Normal timeout for retry tests
        return config

    @patch("second_brain.services.graphiti.GraphitiService")
    async def test_search_retries_on_connection_error(self, mock_gs_cls, mock_config):
        """search() retries on ConnectionError and succeeds."""
        mock_graphiti = AsyncMock()
        mock_graphiti.search.side_effect = [
            ConnectionError("transient"),
            [{"source": "A", "relationship": "rel", "target": "B"}],
        ]
        mock_gs_cls.return_value = mock_graphiti

        adapter = GraphitiMemoryAdapter(mock_config)
        result = await adapter.search("test query")

        assert len(result.memories) == 1
        assert mock_graphiti.search.call_count == 2

    @patch("second_brain.services.graphiti.GraphitiService")
    async def test_add_retries_on_os_error(self, mock_gs_cls, mock_config):
        """add() retries on OSError and succeeds."""
        mock_graphiti = AsyncMock()
        mock_graphiti.add_episode.side_effect = [
            OSError("network blip"),
            None,  # Success
        ]
        mock_gs_cls.return_value = mock_graphiti

        adapter = GraphitiMemoryAdapter(mock_config)
        result = await adapter.add("test content")

        assert result == {"status": "ok"}
        assert mock_graphiti.add_episode.call_count == 2

    @patch("second_brain.services.graphiti.GraphitiService")
    async def test_search_returns_empty_after_retry_exhaustion(self, mock_gs_cls, mock_config):
        """search() returns empty after all retries exhausted."""
        mock_graphiti = AsyncMock()
        mock_graphiti.search.side_effect = ConnectionError("persistent")
        mock_gs_cls.return_value = mock_graphiti

        adapter = GraphitiMemoryAdapter(mock_config)
        result = await adapter.search("test query")

        assert result.memories == []
        assert mock_graphiti.search.call_count == 3  # max_attempts

    @patch("second_brain.services.graphiti.GraphitiService")
    async def test_no_retry_on_value_error(self, mock_gs_cls, mock_config):
        """Non-retryable errors are not retried."""
        mock_graphiti = AsyncMock()
        mock_graphiti.search.side_effect = ValueError("bad query")
        mock_gs_cls.return_value = mock_graphiti

        adapter = GraphitiMemoryAdapter(mock_config)
        result = await adapter.search("test query")

        assert result.memories == []
        assert mock_graphiti.search.call_count == 1  # NOT retried

    @patch("second_brain.services.graphiti.GraphitiService")
    async def test_delete_retries_on_timeout_error(self, mock_gs_cls, mock_config):
        """delete() retries on TimeoutError."""
        mock_graphiti = AsyncMock()
        mock_graphiti.remove_episode.side_effect = [
            TimeoutError("slow network"),
            True,  # Success
        ]
        mock_gs_cls.return_value = mock_graphiti

        adapter = GraphitiMemoryAdapter(mock_config)
        await adapter.delete("mem-123")

        assert mock_graphiti.remove_episode.call_count == 2

    @patch("second_brain.services.graphiti.GraphitiService")
    async def test_get_all_retries_on_connection_error(self, mock_gs_cls, mock_config):
        """get_all() retries on ConnectionError and succeeds."""
        mock_graphiti = AsyncMock()
        mock_graphiti.get_episodes.side_effect = [
            ConnectionError("transient"),
            [{"id": "ep-1", "content": "test", "source": "user", "created_at": "2024-01-01"}],
        ]
        mock_gs_cls.return_value = mock_graphiti

        adapter = GraphitiMemoryAdapter(mock_config)
        result = await adapter.get_all()

        assert len(result) == 1
        assert mock_graphiti.get_episodes.call_count == 2

    @patch("second_brain.services.graphiti.GraphitiService")
    async def test_get_memory_count_retries_on_os_error(self, mock_gs_cls, mock_config):
        """get_memory_count() retries on OSError and succeeds."""
        mock_graphiti = AsyncMock()
        mock_graphiti.get_episode_count.side_effect = [
            OSError("network blip"),
            42,
        ]
        mock_gs_cls.return_value = mock_graphiti

        adapter = GraphitiMemoryAdapter(mock_config)
        result = await adapter.get_memory_count()

        assert result == 42
        assert mock_graphiti.get_episode_count.call_count == 2

    @patch("second_brain.services.graphiti.GraphitiService")
    async def test_delete_all_retries_on_connection_error(self, mock_gs_cls, mock_config):
        """delete_all() retries on ConnectionError and succeeds."""
        mock_graphiti = AsyncMock()
        mock_graphiti.delete_group_data.side_effect = [
            ConnectionError("transient"),
            5,  # Deleted count
        ]
        mock_gs_cls.return_value = mock_graphiti

        adapter = GraphitiMemoryAdapter(mock_config)
        result = await adapter.delete_all()

        assert result == 5
        assert mock_graphiti.delete_group_data.call_count == 2


class TestGraphitiAdapterRetryConfig:
    """Tests for GraphitiAdapterRetryConfig validation."""

    def test_retry_config_exists(self):
        """GraphitiAdapterRetryConfig is importable and configured."""
        from second_brain.services.retry import GRAPHITI_ADAPTER_RETRY_CONFIG
        assert GRAPHITI_ADAPTER_RETRY_CONFIG.max_attempts == 3

    def test_retry_has_correct_exceptions(self):
        """Retry covers expected exception types."""
        from second_brain.services.retry import GRAPHITI_ADAPTER_RETRY_CONFIG
        assert ConnectionError in GRAPHITI_ADAPTER_RETRY_CONFIG.retry_on
        assert TimeoutError in GRAPHITI_ADAPTER_RETRY_CONFIG.retry_on
        assert OSError in GRAPHITI_ADAPTER_RETRY_CONFIG.retry_on

    def test_retry_has_no_jitter(self):
        """Graphiti uses no jitter (self-hosted, no thundering herd)."""
        from second_brain.services.retry import GRAPHITI_ADAPTER_RETRY_CONFIG
        assert GRAPHITI_ADAPTER_RETRY_CONFIG.use_jitter is False

    def test_retry_backoff_is_shorter_than_mem0(self):
        """Graphiti uses shorter backoff than Mem0 (faster recovery)."""
        from second_brain.services.retry import GRAPHITI_ADAPTER_RETRY_CONFIG, MEM0_RETRY_CONFIG
        assert GRAPHITI_ADAPTER_RETRY_CONFIG.max_wait < MEM0_RETRY_CONFIG.max_wait

    def test_retry_decorator_exists(self):
        """_GRAPHITI_ADAPTER_RETRY decorator is importable."""
        from second_brain.services.retry import _GRAPHITI_ADAPTER_RETRY
        assert _GRAPHITI_ADAPTER_RETRY is not None
