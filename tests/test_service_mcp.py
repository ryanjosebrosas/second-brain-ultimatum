"""Tests for service-level MCP server tools."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from second_brain.services.search_result import SearchResult


class TestServiceMCPTools:
    """Tests for service MCP tool functions.

    FastMCP's @server.tool() wraps functions in FunctionTool objects.
    Access the original function via .fn attribute for direct testing.
    """

    @patch("second_brain.service_mcp._get_deps")
    async def test_search_memory(self, mock_deps):
        """search_memory returns formatted results."""
        from second_brain.service_mcp import search_memory

        mock_memory = AsyncMock()
        mock_memory.search.return_value = SearchResult(
            memories=[{"memory": "test memory", "score": 0.95}],
            relations=[],
        )
        mock_deps.return_value = MagicMock(memory_service=mock_memory)

        result = await search_memory.fn(query="test query")
        assert "test memory" in result
        assert "0.95" in result

    @patch("second_brain.service_mcp._get_deps")
    async def test_search_memory_no_results(self, mock_deps):
        """search_memory returns message when no results."""
        from second_brain.service_mcp import search_memory

        mock_memory = AsyncMock()
        mock_memory.search.return_value = SearchResult(memories=[], relations=[])
        mock_deps.return_value = MagicMock(memory_service=mock_memory)

        result = await search_memory.fn(query="nothing")
        assert "No semantic matches" in result

    @patch("second_brain.service_mcp._get_deps")
    async def test_get_patterns(self, mock_deps):
        """get_patterns returns formatted patterns."""
        from second_brain.service_mcp import get_patterns

        mock_storage = AsyncMock()
        mock_storage.get_patterns.return_value = [
            {"name": "Test Pattern", "confidence": "HIGH", "pattern_text": "Do X"},
        ]
        mock_deps.return_value = MagicMock(storage_service=mock_storage)

        result = await get_patterns.fn()
        assert "Test Pattern" in result
        assert "HIGH" in result

    @patch("second_brain.service_mcp._get_deps")
    async def test_get_experiences(self, mock_deps):
        """get_experiences returns formatted experiences."""
        from second_brain.service_mcp import get_experiences

        mock_storage = AsyncMock()
        mock_storage.get_experiences.return_value = [
            {"name": "Client call", "category": "clients", "review_score": 8},
        ]
        mock_deps.return_value = MagicMock(storage_service=mock_storage)

        result = await get_experiences.fn()
        assert "Client call" in result
        assert "clients" in result

    @patch("second_brain.service_mcp._get_deps")
    async def test_store_pattern(self, mock_deps):
        """store_pattern stores and returns confirmation."""
        from second_brain.service_mcp import store_pattern

        mock_storage = AsyncMock()
        mock_storage.insert_pattern.return_value = {"id": "test-id"}
        mock_deps.return_value = MagicMock(storage_service=mock_storage)

        result = await store_pattern.fn(
            name="Test", topic="Messaging", pattern_text="Do X always"
        )
        assert "Stored pattern" in result
        assert "Test" in result

    @patch("second_brain.service_mcp._get_deps")
    async def test_graph_search_disabled(self, mock_deps):
        """graph_search returns message when Graphiti is disabled."""
        from second_brain.service_mcp import graph_search

        mock_deps.return_value = MagicMock(graphiti_service=None)

        result = await graph_search.fn(query="test")
        assert "not enabled" in result

    def test_get_service_mcp_config(self):
        """get_service_mcp_config returns valid (name, config) tuple."""
        from second_brain.service_mcp import get_service_mcp_config

        name, config = get_service_mcp_config()
        assert name == "second-brain-services"
        assert "name" not in config
        assert config["command"]
        assert "second_brain.service_mcp" in " ".join(config["args"])

    def test_validate_input_valid(self):
        """_validate_input accepts valid text."""
        from second_brain.service_mcp import _validate_input
        assert _validate_input("hello") == "hello"

    def test_validate_input_empty(self):
        """_validate_input rejects empty text."""
        from second_brain.service_mcp import _validate_input
        with pytest.raises(ValueError, match="cannot be empty"):
            _validate_input("")

    def test_validate_input_too_long(self):
        """_validate_input rejects oversized text."""
        from second_brain.service_mcp import _validate_input
        with pytest.raises(ValueError, match="too long"):
            _validate_input("x" * 20000)

    def test_server_name(self):
        """Service server has distinct name from main server."""
        from second_brain.service_mcp import service_server
        assert service_server.name == "Second Brain Services"
