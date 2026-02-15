"""Tests for MCP server tool functions."""

from unittest.mock import MagicMock, AsyncMock, patch

from second_brain.schemas import RecallResult, AskResult, MemoryMatch


class TestMCPTools:
    """Test MCP server tool functions directly (without MCP transport).

    FastMCP's @server.tool() wraps functions in FunctionTool objects.
    Access the original function via .fn attribute for direct testing.
    """

    @patch("second_brain.mcp_server._get_model")
    @patch("second_brain.mcp_server._get_deps")
    @patch("second_brain.mcp_server.recall_agent")
    async def test_recall_tool(self, mock_agent, mock_deps_fn, mock_model_fn):
        from second_brain.mcp_server import recall

        mock_result = MagicMock()
        mock_result.output = RecallResult(
            query="content patterns",
            matches=[MemoryMatch(
                content="Use exact user words",
                source="content-patterns.md",
                relevance="HIGH",
            )],
            patterns=["Short > Structured"],
            summary="Found content creation patterns.",
        )
        mock_agent.run = AsyncMock(return_value=mock_result)
        mock_deps_fn.return_value = MagicMock()
        mock_model_fn.return_value = MagicMock()

        result = await recall.fn(query="content patterns")
        assert "content patterns" in result
        assert "Use exact user words" in result

    @patch("second_brain.mcp_server._get_model")
    @patch("second_brain.mcp_server._get_deps")
    @patch("second_brain.mcp_server.ask_agent")
    async def test_ask_tool(self, mock_agent, mock_deps_fn, mock_model_fn):
        from second_brain.mcp_server import ask

        mock_result = MagicMock()
        mock_result.output = AskResult(
            answer="Here's a draft follow-up email...",
            context_used=["company/products"],
            patterns_applied=["Short > Structured"],
            confidence="HIGH",
        )
        mock_agent.run = AsyncMock(return_value=mock_result)
        mock_deps_fn.return_value = MagicMock()
        mock_model_fn.return_value = MagicMock()

        result = await ask.fn(question="Help me write a follow-up email")
        assert "follow-up email" in result
        assert "company/products" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_brain_health_tool(self, mock_deps_fn):
        from second_brain.mcp_server import brain_health

        mock_deps = MagicMock()
        mock_deps.storage_service.get_patterns = AsyncMock(return_value=[
            {"confidence": "HIGH"}, {"confidence": "MEDIUM"}, {"confidence": "LOW"}
        ])
        mock_deps.storage_service.get_experiences = AsyncMock(return_value=[
            {"name": "test"}
        ])
        mock_deps.storage_service.get_health_history = AsyncMock(return_value=[])
        mock_deps_fn.return_value = mock_deps

        result = await brain_health.fn()
        assert "Patterns: 3" in result
        assert "Experiences: 1" in result

    @patch("second_brain.mcp_server._get_model")
    @patch("second_brain.mcp_server._get_deps")
    @patch("second_brain.mcp_server.recall_agent")
    async def test_recall_empty_results(self, mock_agent, mock_deps_fn, mock_model_fn):
        from second_brain.mcp_server import recall

        mock_result = MagicMock()
        mock_result.output = RecallResult(query="nonexistent topic")
        mock_agent.run = AsyncMock(return_value=mock_result)
        mock_deps_fn.return_value = MagicMock()
        mock_model_fn.return_value = MagicMock()

        result = await recall.fn(query="nonexistent topic")
        assert "nonexistent topic" in result
        assert "Matches" not in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_brain_health_growing_status(self, mock_deps_fn):
        from second_brain.mcp_server import brain_health

        mock_deps = MagicMock()
        mock_deps.storage_service.get_patterns = AsyncMock(return_value=[
            {"confidence": "HIGH"} for _ in range(10)
        ])
        mock_deps.storage_service.get_experiences = AsyncMock(return_value=[])
        mock_deps.storage_service.get_health_history = AsyncMock(return_value=[])
        mock_deps_fn.return_value = mock_deps

        result = await brain_health.fn()
        assert "GROWING" in result
        assert "Patterns: 10" in result
