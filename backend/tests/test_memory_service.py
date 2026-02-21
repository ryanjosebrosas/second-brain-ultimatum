"""Consolidated tests for MemoryService — semantic memory via Mem0 Cloud.

This file consolidates tests from:
- test_services.py::TestMemoryService*
- test_graph.py::TestMemoryServiceGraph
- test_deps.py::TestCreateDepsMemoryProvider

Focus areas:
1. Retry behavior on transient failures
2. Graceful degradation (empty results, not exceptions)
3. Timeout handling
4. Idle reconnect logic
5. Filter format correctness
"""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from second_brain.config import BrainConfig
from second_brain.services.memory import MemoryService
from second_brain.services.search_result import SearchResult


class TestMemoryServiceInit:
    """Test MemoryService initialization."""

    def test_requires_api_key(self):
        """MemoryService raises ValueError if mem0_api_key is missing."""
        config = MagicMock(spec=BrainConfig)
        config.mem0_api_key = None
        config.brain_user_id = "test-user"
        config.graph_provider = "none"
        config.service_timeout_seconds = 30.0
        with pytest.raises(ValueError, match="mem0_api_key is required"):
            MemoryService(config)

    @patch("mem0.MemoryClient")
    def test_initializes_with_api_key(self, mock_client_cls):
        """MemoryService initializes when api key is provided."""
        config = MagicMock(spec=BrainConfig)
        config.mem0_api_key = "test-key"
        config.brain_user_id = "test-user"
        config.graph_provider = "none"
        config.service_timeout_seconds = 30.0
        svc = MemoryService(config)
        assert svc._client is not None
        mock_client_cls.assert_called_once_with(api_key="test-key")


class TestMemoryServiceRetry:
    """Test retry behavior on transient failures."""

    @pytest.fixture
    def mock_config(self):
        config = MagicMock(spec=BrainConfig)
        config.mem0_api_key = "test-key"
        config.brain_user_id = "test-user"
        config.memory_search_limit = 10
        config.service_timeout_seconds = 30.0
        config.graph_provider = "none"
        config.mem0_keyword_search = False
        config.mem0_rerank = False
        config.mem0_filter_memories = False
        config.mem0_use_criteria = True
        return config

    @patch("mem0.MemoryClient")
    async def test_search_retries_on_connection_error(self, mock_client_cls, mock_config):
        """search() retries on ConnectionError then succeeds."""
        mock_client = mock_client_cls.return_value
        # First call fails, second succeeds
        mock_client.search.side_effect = [
            ConnectionError("transient"),
            {"results": [{"memory": "test"}], "relations": []},
        ]

        svc = MemoryService(mock_config)
        result = await svc.search("test query")

        assert len(result.memories) == 1
        assert mock_client.search.call_count == 2

    @patch("mem0.MemoryClient")
    async def test_search_returns_empty_after_retry_exhaustion(self, mock_client_cls, mock_config):
        """search() returns empty SearchResult after all retries fail."""
        mock_client = mock_client_cls.return_value
        mock_client.search.side_effect = ConnectionError("persistent")

        svc = MemoryService(mock_config)
        result = await svc.search("test query")

        assert result.memories == []
        assert result.relations == []
        # 3 attempts (initial + 2 retries)
        assert mock_client.search.call_count == 3

    @patch("mem0.MemoryClient")
    async def test_add_retries_on_timeout_error(self, mock_client_cls, mock_config):
        """add() retries on TimeoutError."""
        mock_client = mock_client_cls.return_value
        mock_client.add.side_effect = [
            TimeoutError("slow network"),
            {"id": "mem-123"},
        ]

        svc = MemoryService(mock_config)
        result = await svc.add("test content")

        assert result == {"id": "mem-123"}
        assert mock_client.add.call_count == 2

    @patch("mem0.MemoryClient")
    async def test_add_with_metadata_has_retry(self, mock_client_cls, mock_config):
        """add_with_metadata() retries on transient failures."""
        mock_client = mock_client_cls.return_value
        mock_client.add.side_effect = [
            OSError("network blip"),
            {"id": "mem-456"},
        ]

        svc = MemoryService(mock_config)
        result = await svc.add_with_metadata("content", {"category": "test"})

        assert result == {"id": "mem-456"}
        assert mock_client.add.call_count == 2

    @patch("mem0.MemoryClient")
    async def test_get_all_has_retry(self, mock_client_cls, mock_config):
        """get_all() retries on transient failures."""
        mock_client = mock_client_cls.return_value
        mock_client.get_all.side_effect = [
            ConnectionError("transient"),
            {"results": [{"id": "m1"}, {"id": "m2"}]},
        ]

        svc = MemoryService(mock_config)
        result = await svc.get_all()

        assert len(result) == 2
        assert mock_client.get_all.call_count == 2

    @patch("mem0.MemoryClient")
    async def test_delete_has_retry(self, mock_client_cls, mock_config):
        """delete() retries on transient failures."""
        mock_client = mock_client_cls.return_value
        mock_client.delete.side_effect = [
            TimeoutError("slow"),
            None,  # success
        ]

        svc = MemoryService(mock_config)
        await svc.delete("mem-123")  # Should not raise

        assert mock_client.delete.call_count == 2

    @patch("mem0.MemoryClient")
    async def test_update_memory_has_retry(self, mock_client_cls, mock_config):
        """update_memory() retries on transient failures."""
        mock_client = mock_client_cls.return_value
        mock_client.update.side_effect = [
            OSError("network error"),
            None,  # success
        ]

        svc = MemoryService(mock_config)
        await svc.update_memory("mem-123", content="updated")  # Should not raise

        assert mock_client.update.call_count == 2

    @patch("mem0.MemoryClient")
    async def test_update_memory_passes_correct_args(self, mock_client_cls, mock_config):
        """update_memory() passes memory_id, content, and metadata to client."""
        mock_client = mock_client_cls.return_value
        mock_client.update.return_value = {"status": "updated"}

        svc = MemoryService(mock_config)
        await svc.update_memory("mem-123", content="new content", metadata={"key": "val"})

        mock_client.update.assert_called_once()
        call_kwargs = mock_client.update.call_args.kwargs
        assert call_kwargs["memory_id"] == "mem-123"
        assert call_kwargs["text"] == "new content"
        assert call_kwargs["metadata"] == {"key": "val"}

    @patch("mem0.MemoryClient")
    async def test_delete_passes_correct_args(self, mock_client_cls, mock_config):
        """delete() passes memory_id to client.delete()."""
        mock_client = mock_client_cls.return_value
        mock_client.delete.return_value = None

        svc = MemoryService(mock_config)
        await svc.delete("mem-456")

        mock_client.delete.assert_called_once_with("mem-456")


class TestMemoryServiceGracefulDegradation:
    """Test graceful degradation — errors return empty, not raise."""

    @pytest.fixture
    def mock_config(self):
        config = MagicMock(spec=BrainConfig)
        config.mem0_api_key = "test-key"
        config.brain_user_id = "test-user"
        config.memory_search_limit = 10
        config.service_timeout_seconds = 30.0
        config.graph_provider = "none"
        config.mem0_keyword_search = False
        config.mem0_rerank = False
        config.mem0_filter_memories = False
        config.mem0_use_criteria = True
        return config

    @patch("mem0.MemoryClient")
    async def test_search_returns_empty_on_value_error(self, mock_client_cls, mock_config):
        """search() returns empty on ValueError (not retryable)."""
        mock_client = mock_client_cls.return_value
        mock_client.search.side_effect = ValueError("invalid query")

        svc = MemoryService(mock_config)
        result = await svc.search("test")

        assert result.memories == []
        # ValueError is not retried — only 1 call
        assert mock_client.search.call_count == 1

    @patch("mem0.MemoryClient")
    async def test_add_returns_empty_dict_on_failure(self, mock_client_cls, mock_config):
        """add() returns {} on failure, not raises."""
        mock_client = mock_client_cls.return_value
        mock_client.add.side_effect = Exception("unexpected")

        svc = MemoryService(mock_config)
        result = await svc.add("content")

        assert result == {}

    @patch("mem0.MemoryClient")
    async def test_get_all_returns_empty_list_on_failure(self, mock_client_cls, mock_config):
        """get_all() returns [] on failure."""
        mock_client = mock_client_cls.return_value
        mock_client.get_all.side_effect = Exception("boom")

        svc = MemoryService(mock_config)
        result = await svc.get_all()

        assert result == []

    @patch("mem0.MemoryClient")
    async def test_add_with_metadata_returns_empty_on_failure(self, mock_client_cls, mock_config):
        """add_with_metadata() returns {} on failure."""
        mock_client = mock_client_cls.return_value
        mock_client.add.side_effect = Exception("service error")

        svc = MemoryService(mock_config)
        result = await svc.add_with_metadata("content", {"tag": "test"})

        assert result == {}

    @patch("mem0.MemoryClient")
    async def test_add_multimodal_returns_empty_on_failure(self, mock_client_cls, mock_config):
        """add_multimodal() returns {} on failure."""
        mock_client = mock_client_cls.return_value
        mock_client.add.side_effect = Exception("API error")

        svc = MemoryService(mock_config)
        result = await svc.add_multimodal([{"type": "text", "text": "test"}])

        assert result == {}

    @patch("mem0.MemoryClient")
    async def test_delete_all_returns_count(self, mock_client_cls, mock_config):
        """delete_all() returns count of deleted memories."""
        mock_client = mock_client_cls.return_value
        # get_all returns memories to delete
        mock_client.get_all.return_value = [{"id": "m1"}, {"id": "m2"}, {"id": "m3"}]
        mock_client.delete.return_value = None

        svc = MemoryService(mock_config)
        count = await svc.delete_all()

        assert count == 3
        assert mock_client.delete.call_count == 3


class TestMemoryServiceIdleReconnect:
    """Test idle reconnect logic."""

    @pytest.fixture
    def mock_config(self):
        config = MagicMock(spec=BrainConfig)
        config.mem0_api_key = "test-key"
        config.brain_user_id = "test-user"
        config.memory_search_limit = 10
        config.service_timeout_seconds = 30.0
        config.graph_provider = "none"
        config.mem0_keyword_search = False
        config.mem0_rerank = False
        config.mem0_filter_memories = False
        config.mem0_use_criteria = True
        return config

    @patch("time.monotonic")
    @patch("mem0.MemoryClient")
    async def test_reconnects_after_idle_threshold(self, mock_client_cls, mock_time, mock_config):
        """Client is re-instantiated after idle threshold exceeded."""
        # First call at t=0
        mock_time.return_value = 0
        svc = MemoryService(mock_config)
        initial_call_count = mock_client_cls.call_count

        # Simulate 5 minutes (300s) passing — exceeds 240s threshold
        mock_time.return_value = 300
        mock_client_cls.return_value.search.return_value = {"results": [], "relations": []}

        await svc.search("test")

        # Client should have been re-instantiated (2 total: init + reconnect)
        assert mock_client_cls.call_count == initial_call_count + 1


class TestMemoryServiceMultimodal:
    """Test multimodal memory handling."""

    @pytest.fixture
    def mock_config(self):
        config = MagicMock(spec=BrainConfig)
        config.mem0_api_key = "test-key"
        config.brain_user_id = "test-user"
        config.memory_search_limit = 10
        config.service_timeout_seconds = 30.0
        config.graph_provider = "none"
        config.mem0_keyword_search = False
        config.mem0_rerank = False
        config.mem0_filter_memories = False
        config.mem0_use_criteria = True
        return config

    @patch("mem0.MemoryClient")
    async def test_add_multimodal_with_text(self, mock_client_cls, mock_config):
        """add_multimodal() handles text blocks."""
        mock_client = mock_client_cls.return_value
        mock_client.add.return_value = {"id": "multi-1"}

        svc = MemoryService(mock_config)
        result = await svc.add_multimodal([{"type": "text", "text": "hello"}])

        assert result == {"id": "multi-1"}
        mock_client.add.assert_called_once()

    @patch("mem0.MemoryClient")
    async def test_add_multimodal_with_image(self, mock_client_cls, mock_config):
        """add_multimodal() handles image_url blocks."""
        mock_client = mock_client_cls.return_value
        mock_client.add.return_value = {"id": "img-1"}

        svc = MemoryService(mock_config)
        result = await svc.add_multimodal([
            {"type": "image_url", "image_url": {"url": "https://example.com/img.png"}}
        ])

        assert result == {"id": "img-1"}

    @patch("mem0.MemoryClient")
    async def test_add_multimodal_empty_blocks_returns_empty(self, mock_client_cls, mock_config):
        """add_multimodal() returns {} when no valid blocks."""
        svc = MemoryService(mock_config)
        result = await svc.add_multimodal([])

        assert result == {}
        mock_client_cls.return_value.add.assert_not_called()

    @patch("mem0.MemoryClient")
    async def test_add_multimodal_skips_unsupported_types(self, mock_client_cls, mock_config):
        """add_multimodal() skips blocks with unsupported types."""
        mock_client = mock_client_cls.return_value
        mock_client.add.return_value = {"id": "mixed-1"}

        svc = MemoryService(mock_config)
        result = await svc.add_multimodal([
            {"type": "unknown", "data": "ignored"},
            {"type": "text", "text": "kept"},
        ])

        assert result == {"id": "mixed-1"}
        # Only the text block should be in the call
        call_args = mock_client.add.call_args
        messages = call_args[0][0]
        assert len(messages) == 1
        assert messages[0]["content"] == "kept"


class TestMemoryServiceRetryConfig:
    """Test that retry config is properly applied."""

    def test_retry_has_jitter(self):
        """Verify _MEM0_RETRY uses jitter (via MEM0_RETRY_CONFIG)."""
        from second_brain.services.retry import MEM0_RETRY_CONFIG
        assert MEM0_RETRY_CONFIG.use_jitter is True

    def test_retry_has_correct_exceptions(self):
        """Verify retry covers expected exception types."""
        from second_brain.services.retry import MEM0_RETRY_CONFIG
        assert ConnectionError in MEM0_RETRY_CONFIG.retry_on
        assert TimeoutError in MEM0_RETRY_CONFIG.retry_on
        assert OSError in MEM0_RETRY_CONFIG.retry_on

    def test_retry_max_attempts(self):
        """Verify retry attempts is 3."""
        from second_brain.services.retry import MEM0_RETRY_CONFIG
        assert MEM0_RETRY_CONFIG.max_attempts == 3


class TestMemoryServiceClose:
    """Test close() method — resource cleanup."""

    @pytest.fixture
    def mock_config(self):
        config = MagicMock(spec=BrainConfig)
        config.mem0_api_key = "test-key"
        config.brain_user_id = "test-user"
        config.memory_search_limit = 10
        config.service_timeout_seconds = 30.0
        config.graph_provider = "none"
        config.mem0_keyword_search = False
        config.mem0_rerank = False
        config.mem0_filter_memories = False
        config.mem0_use_criteria = True
        return config

    @patch("mem0.MemoryClient")
    async def test_close_calls_client_close(self, mock_client_cls, mock_config):
        """close() calls client.close() when available."""
        mock_client = mock_client_cls.return_value
        mock_client.close = MagicMock()  # sync close method

        svc = MemoryService(mock_config)
        await svc.close()

        mock_client.close.assert_called_once()

    @patch("mem0.MemoryClient")
    async def test_close_handles_missing_close_method(self, mock_client_cls, mock_config):
        """close() gracefully handles client without close method."""
        mock_client = mock_client_cls.return_value
        # Remove close attribute
        del mock_client.close

        svc = MemoryService(mock_config)
        # Should not raise
        await svc.close()

        assert svc._client is None

    @patch("mem0.MemoryClient")
    async def test_close_nullifies_client(self, mock_client_cls, mock_config):
        """close() sets _client to None."""
        mock_client = mock_client_cls.return_value
        mock_client.close = MagicMock()

        svc = MemoryService(mock_config)
        assert svc._client is not None

        await svc.close()

        assert svc._client is None

    @patch("mem0.MemoryClient")
    async def test_close_handles_exception_gracefully(self, mock_client_cls, mock_config):
        """close() doesn't propagate exceptions from client.close()."""
        mock_client = mock_client_cls.return_value
        mock_client.close = MagicMock(side_effect=RuntimeError("close failed"))

        svc = MemoryService(mock_config)
        # Should not raise despite client.close() failing
        await svc.close()

        assert svc._client is None


class TestMemoryServiceFilterMemories:
    """Tests for filter_memories parameter in search methods."""

    @pytest.fixture
    def mock_config(self):
        config = MagicMock(spec=BrainConfig)
        config.mem0_api_key = "test-key"
        config.brain_user_id = "test-user"
        config.memory_search_limit = 10
        config.service_timeout_seconds = 30.0
        config.graph_provider = "none"
        config.mem0_keyword_search = False
        config.mem0_rerank = False
        config.mem0_filter_memories = False
        config.mem0_use_criteria = True
        return config

    # ============================================================
    # Tests for MemoryService.search() — filter_memories
    # ============================================================

    @patch("mem0.MemoryClient")
    async def test_search_passes_filter_memories_when_config_enabled(
        self, mock_client_cls, mock_config
    ):
        """search() passes filter_memories=True when config is enabled."""
        mock_config.mem0_filter_memories = True
        mock_client = mock_client_cls.return_value
        mock_client.search.return_value = {"results": [], "relations": []}

        svc = MemoryService(mock_config)
        await svc.search("test query")

        call_kwargs = mock_client.search.call_args.kwargs
        assert call_kwargs.get("filter_memories") is True

    @patch("mem0.MemoryClient")
    async def test_search_omits_filter_memories_when_config_disabled(
        self, mock_client_cls, mock_config
    ):
        """search() does NOT pass filter_memories when config is disabled."""
        mock_config.mem0_filter_memories = False
        mock_client = mock_client_cls.return_value
        mock_client.search.return_value = {"results": [], "relations": []}

        svc = MemoryService(mock_config)
        await svc.search("test query")

        call_kwargs = mock_client.search.call_args.kwargs
        assert "filter_memories" not in call_kwargs

    @patch("mem0.MemoryClient")
    async def test_search_per_call_filter_memories_overrides_config(
        self, mock_client_cls, mock_config
    ):
        """search() per-call filter_memories=True overrides config=False."""
        mock_config.mem0_filter_memories = False
        mock_client = mock_client_cls.return_value
        mock_client.search.return_value = {"results": [], "relations": []}

        svc = MemoryService(mock_config)
        await svc.search("test query", filter_memories=True)

        call_kwargs = mock_client.search.call_args.kwargs
        assert call_kwargs.get("filter_memories") is True

    @patch("mem0.MemoryClient")
    async def test_search_per_call_filter_memories_false_overrides_config_true(
        self, mock_client_cls, mock_config
    ):
        """search() per-call filter_memories=False overrides config=True."""
        mock_config.mem0_filter_memories = True
        mock_client = mock_client_cls.return_value
        mock_client.search.return_value = {"results": [], "relations": []}

        svc = MemoryService(mock_config)
        await svc.search("test query", filter_memories=False)

        call_kwargs = mock_client.search.call_args.kwargs
        assert "filter_memories" not in call_kwargs

    # ============================================================
    # Tests for MemoryService.search_with_filters() — filter_memories
    # ============================================================

    @patch("mem0.MemoryClient")
    async def test_search_with_filters_passes_filter_memories_when_config_enabled(
        self, mock_client_cls, mock_config
    ):
        """search_with_filters() passes filter_memories=True when config is enabled."""
        mock_config.mem0_filter_memories = True
        mock_client = mock_client_cls.return_value
        mock_client.search.return_value = {"results": [], "relations": []}

        svc = MemoryService(mock_config)
        await svc.search_with_filters("test query", metadata_filters={"category": "test"})

        call_kwargs = mock_client.search.call_args.kwargs
        assert call_kwargs.get("filter_memories") is True

    @patch("mem0.MemoryClient")
    async def test_search_with_filters_omits_filter_memories_when_config_disabled(
        self, mock_client_cls, mock_config
    ):
        """search_with_filters() does NOT pass filter_memories when config is disabled."""
        mock_config.mem0_filter_memories = False
        mock_client = mock_client_cls.return_value
        mock_client.search.return_value = {"results": [], "relations": []}

        svc = MemoryService(mock_config)
        await svc.search_with_filters("test query")

        call_kwargs = mock_client.search.call_args.kwargs
        assert "filter_memories" not in call_kwargs

    @patch("mem0.MemoryClient")
    async def test_search_with_filters_per_call_override(
        self, mock_client_cls, mock_config
    ):
        """search_with_filters() per-call filter_memories=True overrides config=False."""
        mock_config.mem0_filter_memories = False
        mock_client = mock_client_cls.return_value
        mock_client.search.return_value = {"results": [], "relations": []}

        svc = MemoryService(mock_config)
        await svc.search_with_filters("test query", filter_memories=True)

        call_kwargs = mock_client.search.call_args.kwargs
        assert call_kwargs.get("filter_memories") is True


class TestSetupCriteriaRetrieval:
    """Tests for MemoryService.setup_criteria_retrieval()."""

    @pytest.fixture
    def mock_config(self):
        config = MagicMock(spec=BrainConfig)
        config.mem0_api_key = "test-key"
        config.brain_user_id = "test-user"
        config.memory_search_limit = 10
        config.service_timeout_seconds = 30.0
        config.graph_provider = "none"
        config.mem0_keyword_search = False
        config.mem0_rerank = False
        config.mem0_filter_memories = False
        config.mem0_use_criteria = True
        return config

    @patch("mem0.MemoryClient")
    async def test_setup_criteria_retrieval_with_default_criteria(
        self, mock_client_cls, mock_config
    ):
        """setup_criteria_retrieval() calls project.update with default criteria."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        from second_brain.services.memory import DEFAULT_RETRIEVAL_CRITERIA

        svc = MemoryService(mock_config)
        result = await svc.setup_criteria_retrieval()

        assert result is True
        mock_client.project.update.assert_called_once_with(
            retrieval_criteria=DEFAULT_RETRIEVAL_CRITERIA
        )

    @patch("mem0.MemoryClient")
    async def test_setup_criteria_retrieval_with_custom_criteria(
        self, mock_client_cls, mock_config
    ):
        """setup_criteria_retrieval() accepts custom criteria."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        custom_criteria = [{"name": "test", "description": "Test", "weight": 1}]

        svc = MemoryService(mock_config)
        result = await svc.setup_criteria_retrieval(criteria=custom_criteria)

        assert result is True
        mock_client.project.update.assert_called_once_with(
            retrieval_criteria=custom_criteria
        )

    @patch("mem0.MemoryClient")
    async def test_setup_criteria_retrieval_handles_error(
        self, mock_client_cls, mock_config
    ):
        """setup_criteria_retrieval() returns False on error."""
        mock_client = MagicMock()
        mock_client.project.update.side_effect = Exception("API error")
        mock_client_cls.return_value = mock_client

        svc = MemoryService(mock_config)
        result = await svc.setup_criteria_retrieval()

        assert result is False


class TestUseCriteriaBypass:
    """Tests for use_criteria parameter in search methods."""

    @pytest.fixture
    def mock_config(self):
        config = MagicMock(spec=BrainConfig)
        config.mem0_api_key = "test-key"
        config.brain_user_id = "test-user"
        config.memory_search_limit = 10
        config.service_timeout_seconds = 30.0
        config.graph_provider = "none"
        config.mem0_keyword_search = False
        config.mem0_rerank = False
        config.mem0_filter_memories = False
        config.mem0_use_criteria = True
        return config

    @patch("mem0.MemoryClient")
    async def test_search_passes_use_criteria_false_when_config_disabled(
        self, mock_client_cls, mock_config
    ):
        """search() passes use_criteria=False when config is disabled."""
        mock_config.mem0_use_criteria = False
        mock_client = mock_client_cls.return_value
        mock_client.search.return_value = {"results": [], "relations": []}

        svc = MemoryService(mock_config)
        await svc.search("test query")

        call_kwargs = mock_client.search.call_args.kwargs
        assert call_kwargs.get("use_criteria") is False

    @patch("mem0.MemoryClient")
    async def test_search_omits_use_criteria_when_config_enabled(
        self, mock_client_cls, mock_config
    ):
        """search() does NOT pass use_criteria when config is enabled (criteria auto-activate)."""
        mock_config.mem0_use_criteria = True
        mock_client = mock_client_cls.return_value
        mock_client.search.return_value = {"results": [], "relations": []}

        svc = MemoryService(mock_config)
        await svc.search("test query")

        call_kwargs = mock_client.search.call_args.kwargs
        assert "use_criteria" not in call_kwargs

    @patch("mem0.MemoryClient")
    async def test_search_per_call_use_criteria_false_overrides_config(
        self, mock_client_cls, mock_config
    ):
        """search() per-call use_criteria=False overrides config=True."""
        mock_config.mem0_use_criteria = True
        mock_client = mock_client_cls.return_value
        mock_client.search.return_value = {"results": [], "relations": []}

        svc = MemoryService(mock_config)
        await svc.search("test query", use_criteria=False)

        call_kwargs = mock_client.search.call_args.kwargs
        assert call_kwargs.get("use_criteria") is False

    @patch("mem0.MemoryClient")
    async def test_search_with_filters_use_criteria_bypass(
        self, mock_client_cls, mock_config
    ):
        """search_with_filters() passes use_criteria=False when disabled."""
        mock_config.mem0_use_criteria = False
        mock_client = mock_client_cls.return_value
        mock_client.search.return_value = {"results": [], "relations": []}

        svc = MemoryService(mock_config)
        await svc.search_with_filters("test query")

        call_kwargs = mock_client.search.call_args.kwargs
        assert call_kwargs.get("use_criteria") is False

    @patch("mem0.MemoryClient")
    async def test_search_with_filters_omits_use_criteria_when_config_enabled(
        self, mock_client_cls, mock_config
    ):
        """search_with_filters() does NOT pass use_criteria when config is enabled."""
        mock_config.mem0_use_criteria = True
        mock_client = mock_client_cls.return_value
        mock_client.search.return_value = {"results": [], "relations": []}

        svc = MemoryService(mock_config)
        await svc.search_with_filters("test query")

        call_kwargs = mock_client.search.call_args.kwargs
        assert "use_criteria" not in call_kwargs

    @patch("mem0.MemoryClient")
    async def test_search_with_filters_per_call_use_criteria_false_overrides_config(
        self, mock_client_cls, mock_config
    ):
        """search_with_filters() per-call use_criteria=False overrides config=True."""
        mock_config.mem0_use_criteria = True
        mock_client = mock_client_cls.return_value
        mock_client.search.return_value = {"results": [], "relations": []}

        svc = MemoryService(mock_config)
        await svc.search_with_filters("test query", use_criteria=False)

        call_kwargs = mock_client.search.call_args.kwargs
        assert call_kwargs.get("use_criteria") is False


class TestSetupCustomInstructions:
    """Tests for MemoryService.setup_custom_instructions()."""

    @pytest.fixture
    def mock_config(self):
        config = MagicMock(spec=BrainConfig)
        config.mem0_api_key = "test-key"
        config.brain_user_id = "test-user"
        config.memory_search_limit = 10
        config.service_timeout_seconds = 30.0
        config.graph_provider = "none"
        config.mem0_keyword_search = False
        config.mem0_rerank = False
        config.mem0_filter_memories = False
        config.mem0_use_criteria = True
        return config

    @patch("mem0.MemoryClient")
    async def test_setup_custom_instructions_with_default(
        self, mock_client_cls, mock_config
    ):
        """setup_custom_instructions() calls project.update with default instructions."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        from second_brain.services.memory import DEFAULT_CUSTOM_INSTRUCTIONS

        svc = MemoryService(mock_config)
        result = await svc.setup_custom_instructions()

        assert result is True
        mock_client.project.update.assert_called_once_with(
            custom_instructions=DEFAULT_CUSTOM_INSTRUCTIONS
        )

    @patch("mem0.MemoryClient")
    async def test_setup_custom_instructions_with_custom(
        self, mock_client_cls, mock_config
    ):
        """setup_custom_instructions() accepts custom instructions."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        custom = "Only store technical patterns."

        svc = MemoryService(mock_config)
        result = await svc.setup_custom_instructions(instructions=custom)

        assert result is True
        mock_client.project.update.assert_called_once_with(
            custom_instructions=custom
        )

    @patch("mem0.MemoryClient")
    async def test_setup_custom_instructions_handles_error(
        self, mock_client_cls, mock_config
    ):
        """setup_custom_instructions() returns False on error."""
        mock_client = MagicMock()
        mock_client.project.update.side_effect = Exception("API error")
        mock_client_cls.return_value = mock_client

        svc = MemoryService(mock_config)
        result = await svc.setup_custom_instructions()

        assert result is False


class TestMemoryServiceKeywordSearch:
    """Tests for keyword_search feature in MemoryService."""

    @pytest.fixture
    def mock_config_keyword_enabled(self):
        """Config with keyword_search enabled."""
        config = MagicMock(spec=BrainConfig)
        config.mem0_api_key = "test-key"
        config.brain_user_id = "test-user"
        config.memory_search_limit = 10
        config.service_timeout_seconds = 30.0
        config.graph_provider = "none"
        config.mem0_keyword_search = True  # ENABLED
        config.mem0_rerank = False
        config.mem0_filter_memories = False
        config.mem0_use_criteria = False
        return config

    @pytest.fixture
    def mock_config(self):
        """Config with keyword_search disabled."""
        config = MagicMock(spec=BrainConfig)
        config.mem0_api_key = "test-key"
        config.brain_user_id = "test-user"
        config.memory_search_limit = 10
        config.service_timeout_seconds = 30.0
        config.graph_provider = "none"
        config.mem0_keyword_search = False  # DISABLED
        config.mem0_rerank = False
        config.mem0_filter_memories = False
        config.mem0_use_criteria = False
        return config

    @patch("mem0.MemoryClient")
    async def test_search_passes_keyword_search_when_enabled(
        self, mock_client_cls, mock_config_keyword_enabled
    ):
        """search() passes keyword_search=True when config enabled."""
        mock_client = mock_client_cls.return_value
        mock_client.search.return_value = {"results": [], "relations": []}

        svc = MemoryService(mock_config_keyword_enabled)
        await svc.search("test query")

        call_kwargs = mock_client.search.call_args.kwargs
        assert call_kwargs.get("keyword_search") is True

    @patch("mem0.MemoryClient")
    async def test_search_omits_keyword_search_when_disabled(
        self, mock_client_cls, mock_config
    ):
        """search() does not pass keyword_search when config disabled."""
        mock_client = mock_client_cls.return_value
        mock_client.search.return_value = {"results": [], "relations": []}

        svc = MemoryService(mock_config)
        await svc.search("test query")

        call_kwargs = mock_client.search.call_args.kwargs
        assert "keyword_search" not in call_kwargs or call_kwargs.get("keyword_search") is not True

    @patch("mem0.MemoryClient")
    async def test_search_with_filters_passes_keyword_search(
        self, mock_client_cls, mock_config_keyword_enabled
    ):
        """search_with_filters() also passes keyword_search when enabled."""
        mock_client = mock_client_cls.return_value
        mock_client.search.return_value = {"results": [], "relations": []}

        svc = MemoryService(mock_config_keyword_enabled)
        await svc.search_with_filters("test", metadata_filters={"category": "pattern"})

        call_kwargs = mock_client.search.call_args.kwargs
        assert call_kwargs.get("keyword_search") is True


class TestMemoryServiceRerank:
    """Tests for rerank feature in MemoryService."""

    @pytest.fixture
    def mock_config_rerank_enabled(self):
        """Config with rerank enabled."""
        config = MagicMock(spec=BrainConfig)
        config.mem0_api_key = "test-key"
        config.brain_user_id = "test-user"
        config.memory_search_limit = 10
        config.service_timeout_seconds = 30.0
        config.graph_provider = "none"
        config.mem0_keyword_search = False
        config.mem0_rerank = True  # ENABLED
        config.mem0_filter_memories = False
        config.mem0_use_criteria = False
        return config

    @pytest.fixture
    def mock_config(self):
        """Config with rerank disabled."""
        config = MagicMock(spec=BrainConfig)
        config.mem0_api_key = "test-key"
        config.brain_user_id = "test-user"
        config.memory_search_limit = 10
        config.service_timeout_seconds = 30.0
        config.graph_provider = "none"
        config.mem0_keyword_search = False
        config.mem0_rerank = False  # DISABLED
        config.mem0_filter_memories = False
        config.mem0_use_criteria = False
        return config

    @patch("mem0.MemoryClient")
    async def test_search_passes_rerank_when_enabled(
        self, mock_client_cls, mock_config_rerank_enabled
    ):
        """search() passes rerank=True when config enabled."""
        mock_client = mock_client_cls.return_value
        mock_client.search.return_value = {"results": [], "relations": []}

        svc = MemoryService(mock_config_rerank_enabled)
        await svc.search("test query")

        call_kwargs = mock_client.search.call_args.kwargs
        assert call_kwargs.get("rerank") is True

    @patch("mem0.MemoryClient")
    async def test_search_omits_rerank_when_disabled(self, mock_client_cls, mock_config):
        """search() does not pass rerank when config disabled."""
        mock_client = mock_client_cls.return_value
        mock_client.search.return_value = {"results": [], "relations": []}

        svc = MemoryService(mock_config)
        await svc.search("test query")

        call_kwargs = mock_client.search.call_args.kwargs
        assert "rerank" not in call_kwargs or call_kwargs.get("rerank") is not True

    @patch("mem0.MemoryClient")
    async def test_rerank_with_keyword_search_combination(self, mock_client_cls):
        """Both rerank and keyword_search can be enabled together."""
        config = MagicMock(spec=BrainConfig)
        config.mem0_api_key = "test-key"
        config.brain_user_id = "test-user"
        config.memory_search_limit = 10
        config.service_timeout_seconds = 30.0
        config.graph_provider = "none"
        config.mem0_keyword_search = True
        config.mem0_rerank = True
        config.mem0_filter_memories = False
        config.mem0_use_criteria = False

        mock_client = mock_client_cls.return_value
        mock_client.search.return_value = {"results": [], "relations": []}

        svc = MemoryService(config)
        await svc.search("test query")

        call_kwargs = mock_client.search.call_args.kwargs
        assert call_kwargs.get("rerank") is True
        assert call_kwargs.get("keyword_search") is True

    @patch("mem0.MemoryClient")
    async def test_search_with_filters_passes_rerank(self, mock_client_cls, mock_config_rerank_enabled):
        """search_with_filters() also passes rerank when enabled."""
        mock_client = mock_client_cls.return_value
        mock_client.search.return_value = {"results": [], "relations": []}

        svc = MemoryService(mock_config_rerank_enabled)
        await svc.search_with_filters("test", metadata_filters={"category": "pattern"})

        call_kwargs = mock_client.search.call_args.kwargs
        assert call_kwargs.get("rerank") is True


class TestMemoryServiceSearchByCategory:
    """Tests for search_by_category method."""

    @pytest.fixture
    def mock_config(self):
        """Standard config for search_by_category tests."""
        config = MagicMock(spec=BrainConfig)
        config.mem0_api_key = "test-key"
        config.brain_user_id = "test-user"
        config.memory_search_limit = 10
        config.service_timeout_seconds = 30.0
        config.graph_provider = "none"
        config.mem0_keyword_search = False
        config.mem0_rerank = False
        config.mem0_filter_memories = False
        config.mem0_use_criteria = False
        return config

    @patch("mem0.MemoryClient")
    async def test_search_by_category_basic(self, mock_client_cls, mock_config):
        """search_by_category wraps search_with_filters correctly."""
        mock_client = mock_client_cls.return_value
        mock_client.search.return_value = {
            "results": [{"memory": "voice pattern", "score": 0.9}],
            "relations": [],
        }

        svc = MemoryService(mock_config)
        result = await svc.search_by_category("voice", query="brand")

        assert len(result.memories) == 1
        assert result.memories[0]["memory"] == "voice pattern"

    @patch("mem0.MemoryClient")
    async def test_search_by_category_passes_override_user_id(
        self, mock_client_cls, mock_config
    ):
        """search_by_category passes override_user_id to search_with_filters."""
        mock_client = mock_client_cls.return_value
        mock_client.search.return_value = {"results": [], "relations": []}

        svc = MemoryService(mock_config)
        await svc.search_by_category("pattern", override_user_id="uttam")

        call_kwargs = mock_client.search.call_args.kwargs
        filters = call_kwargs.get("filters", {})
        # Verify user_id filter is "uttam" not default
        user_ids = [c.get("user_id") for c in filters.get("AND", []) if "user_id" in c]
        assert "uttam" in user_ids

    @patch("mem0.MemoryClient")
    async def test_search_by_category_empty_query(self, mock_client_cls, mock_config):
        """search_by_category uses category as query when query is empty."""
        mock_client = mock_client_cls.return_value
        mock_client.search.return_value = {"results": [], "relations": []}

        svc = MemoryService(mock_config)
        await svc.search_by_category("experience")

        call_args = mock_client.search.call_args
        query_arg = call_args.args[0] if call_args.args else call_args.kwargs.get("query")
        assert "experience" in query_arg

    @patch("mem0.MemoryClient")
    async def test_search_by_category_uses_limit(self, mock_client_cls, mock_config):
        """search_by_category respects limit parameter."""
        mock_client = mock_client_cls.return_value
        mock_client.search.return_value = {"results": [], "relations": []}

        svc = MemoryService(mock_config)
        await svc.search_by_category("pattern", limit=5)

        call_kwargs = mock_client.search.call_args.kwargs
        assert call_kwargs.get("top_k") == 5


class TestMemoryServiceOverrideUserId:
    """Tests for override_user_id multi-user scoping."""

    @pytest.fixture
    def mock_config(self):
        """Config for override_user_id tests."""
        config = MagicMock(spec=BrainConfig)
        config.mem0_api_key = "test-key"
        config.brain_user_id = "test-user"
        config.memory_search_limit = 10
        config.service_timeout_seconds = 30.0
        config.graph_provider = "none"
        config.mem0_keyword_search = False
        config.mem0_rerank = False
        config.mem0_filter_memories = False
        config.mem0_use_criteria = False
        return config

    @patch("mem0.MemoryClient")
    async def test_search_with_override_user_id(self, mock_client_cls, mock_config):
        """search() uses override_user_id when provided."""
        mock_client = mock_client_cls.return_value
        mock_client.search.return_value = {"results": [{"memory": "test"}], "relations": []}

        svc = MemoryService(mock_config)
        await svc.search("test query", override_user_id="uttam")

        call_kwargs = mock_client.search.call_args.kwargs
        filters = call_kwargs.get("filters", {})
        user_ids = [c.get("user_id") for c in filters.get("AND", []) if "user_id" in c]
        assert "uttam" in user_ids

    @patch("mem0.MemoryClient")
    async def test_search_uses_default_when_no_override(self, mock_client_cls, mock_config):
        """search() uses config.brain_user_id when no override."""
        mock_client = mock_client_cls.return_value
        mock_client.search.return_value = {"results": [], "relations": []}

        svc = MemoryService(mock_config)
        await svc.search("test query")

        call_kwargs = mock_client.search.call_args.kwargs
        filters = call_kwargs.get("filters", {})
        user_ids = [c.get("user_id") for c in filters.get("AND", []) if "user_id" in c]
        assert "test-user" in user_ids  # from mock_config

    @patch("mem0.MemoryClient")
    async def test_search_with_filters_uses_override(self, mock_client_cls, mock_config):
        """search_with_filters() uses override_user_id."""
        mock_client = mock_client_cls.return_value
        mock_client.search.return_value = {"results": [], "relations": []}

        svc = MemoryService(mock_config)
        await svc.search_with_filters(
            "test", metadata_filters={"category": "pattern"}, override_user_id="robert"
        )

        call_kwargs = mock_client.search.call_args.kwargs
        filters = call_kwargs.get("filters", {})
        user_ids = [c.get("user_id") for c in filters.get("AND", []) if "user_id" in c]
        assert "robert" in user_ids

    @patch("mem0.MemoryClient")
    def test_effective_user_id_returns_override(self, mock_client_cls, mock_config):
        """_effective_user_id returns override when provided."""
        svc = MemoryService(mock_config)

        assert svc._effective_user_id("override") == "override"
        assert svc._effective_user_id(None) == "test-user"
        assert svc._effective_user_id("") == "test-user"  # Empty string = default
