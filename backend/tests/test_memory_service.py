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
