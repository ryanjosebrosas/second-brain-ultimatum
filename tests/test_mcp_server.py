"""Tests for MCP server tool functions."""

from unittest.mock import MagicMock, AsyncMock, patch

from second_brain.schemas import (
    RecallResult, AskResult, MemoryMatch, Relation, LearnResult, PatternExtract,
)


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
            {"confidence": "HIGH", "topic": "content", "date_updated": "2026-02-15"},
            {"confidence": "MEDIUM", "topic": "messaging", "date_updated": "2026-02-14"},
            {"confidence": "LOW", "topic": "content", "date_updated": "2026-02-13"},
        ])
        mock_deps.storage_service.get_experiences = AsyncMock(return_value=[
            {"name": "test"}
        ])
        mock_deps.memory_service.get_memory_count = AsyncMock(return_value=42)
        mock_deps.config.graph_provider = "none"
        mock_deps_fn.return_value = mock_deps

        result = await brain_health.fn()
        assert "Patterns: 3" in result
        assert "Experiences: 1" in result
        assert "Memories: 42" in result
        assert "Graph: none" in result
        assert "Last updated: 2026-02-15" in result

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
            {"confidence": "HIGH", "topic": "content", "date_updated": "2026-02-15"}
            for _ in range(10)
        ])
        mock_deps.storage_service.get_experiences = AsyncMock(return_value=[])
        mock_deps.memory_service.get_memory_count = AsyncMock(return_value=5)
        mock_deps.config.graph_provider = "none"
        mock_deps_fn.return_value = mock_deps

        result = await brain_health.fn()
        assert "GROWING" in result
        assert "Patterns: 10" in result

    @patch("second_brain.mcp_server._get_model")
    @patch("second_brain.mcp_server._get_deps")
    @patch("second_brain.mcp_server.recall_agent")
    async def test_recall_with_graph_relations(self, mock_agent, mock_deps_fn, mock_model_fn):
        from second_brain.mcp_server import recall

        mock_result = MagicMock()
        mock_result.output = RecallResult(
            query="content strategy",
            matches=[MemoryMatch(content="LinkedIn tips", source="mem0")],
            relations=[
                Relation(source="LinkedIn", relationship="uses", target="content strategy"),
            ],
        )
        mock_agent.run = AsyncMock(return_value=mock_result)
        mock_deps_fn.return_value = MagicMock()
        mock_model_fn.return_value = MagicMock()

        result = await recall.fn(query="content strategy")
        assert "Graph Relationships" in result
        assert "LinkedIn --[uses]--> content strategy" in result

    @patch("second_brain.mcp_server._get_model")
    @patch("second_brain.mcp_server._get_deps")
    @patch("second_brain.mcp_server.learn_agent")
    async def test_learn_tool(self, mock_agent, mock_deps_fn, mock_model_fn):
        from second_brain.mcp_server import learn

        mock_result = MagicMock()
        mock_result.output = LearnResult(
            input_summary="LinkedIn post session",
            patterns_extracted=[
                PatternExtract(
                    name="Use Exact Words",
                    topic="Content",
                    pattern_text="Use the user's exact words, don't polish",
                    evidence=["Draft v3 was rejected for being too AI"],
                )
            ],
            insights=["Raw voice performs better than polished"],
            patterns_new=1,
            patterns_reinforced=0,
            storage_summary="1 pattern stored in registry, 1 insight added to memory",
        )
        mock_agent.run = AsyncMock(return_value=mock_result)
        mock_deps_fn.return_value = MagicMock()
        mock_model_fn.return_value = MagicMock()

        result = await learn.fn(content="Session notes about LinkedIn writing...", category="content")
        assert "LinkedIn post session" in result
        assert "Use Exact Words" in result
        assert "New: 1" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_brain_health_with_topics(self, mock_deps_fn):
        from second_brain.mcp_server import brain_health

        mock_deps = MagicMock()
        mock_deps.storage_service.get_patterns = AsyncMock(return_value=[
            {"confidence": "HIGH", "topic": "content", "date_updated": "2026-02-15"},
            {"confidence": "LOW", "topic": "content", "date_updated": "2026-02-14"},
            {"confidence": "MEDIUM", "topic": "messaging", "date_updated": "2026-02-13"},
        ])
        mock_deps.storage_service.get_experiences = AsyncMock(return_value=[])
        mock_deps.memory_service.get_memory_count = AsyncMock(return_value=10)
        mock_deps.config.graph_provider = "mem0"
        mock_deps_fn.return_value = mock_deps

        result = await brain_health.fn()
        assert "content: 2" in result
        assert "messaging: 1" in result
        assert "Graph: mem0" in result
        assert "Last updated: 2026-02-15" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_brain_health_with_memory_count(self, mock_deps_fn):
        from second_brain.mcp_server import brain_health

        mock_deps = MagicMock()
        mock_deps.storage_service.get_patterns = AsyncMock(return_value=[])
        mock_deps.storage_service.get_experiences = AsyncMock(return_value=[])
        mock_deps.memory_service.get_memory_count = AsyncMock(return_value=99)
        mock_deps.config.graph_provider = None
        mock_deps_fn.return_value = mock_deps

        result = await brain_health.fn()
        assert "Memories: 99" in result
        assert "Graph: disabled" in result
        assert "Last updated: none" in result
        assert "BUILDING" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_brain_health_memory_unavailable(self, mock_deps_fn):
        from second_brain.mcp_server import brain_health

        mock_deps = MagicMock()
        mock_deps.storage_service.get_patterns = AsyncMock(return_value=[
            {"confidence": "HIGH", "topic": "content", "date_updated": "2026-02-15"},
        ])
        mock_deps.storage_service.get_experiences = AsyncMock(return_value=[])
        mock_deps.memory_service.get_memory_count = AsyncMock(
            side_effect=Exception("Mem0 unavailable")
        )
        mock_deps.config.graph_provider = "none"
        mock_deps_fn.return_value = mock_deps

        result = await brain_health.fn()
        assert "Memories: unavailable" in result
        assert "Patterns: 1" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_search_examples_tool(self, mock_deps_fn):
        from second_brain.mcp_server import search_examples

        mock_deps = MagicMock()
        mock_deps.storage_service.get_examples = AsyncMock(return_value=[
            {"content_type": "linkedin", "title": "Hooks That Work", "content": "5 hooks..."},
        ])
        mock_deps_fn.return_value = mock_deps

        result = await search_examples.fn()
        assert "linkedin" in result
        assert "Hooks That Work" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_search_examples_empty(self, mock_deps_fn):
        from second_brain.mcp_server import search_examples

        mock_deps = MagicMock()
        mock_deps.storage_service.get_examples = AsyncMock(return_value=[])
        mock_deps_fn.return_value = mock_deps

        result = await search_examples.fn()
        assert "No content examples found" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_search_knowledge_tool(self, mock_deps_fn):
        from second_brain.mcp_server import search_knowledge

        mock_deps = MagicMock()
        mock_deps.storage_service.get_knowledge = AsyncMock(return_value=[
            {"category": "frameworks", "title": "Value Ladder", "content": "Framework..."},
        ])
        mock_deps_fn.return_value = mock_deps

        result = await search_knowledge.fn()
        assert "frameworks" in result
        assert "Value Ladder" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_search_knowledge_empty(self, mock_deps_fn):
        from second_brain.mcp_server import search_knowledge

        mock_deps = MagicMock()
        mock_deps.storage_service.get_knowledge = AsyncMock(return_value=[])
        mock_deps_fn.return_value = mock_deps

        result = await search_knowledge.fn()
        assert "No knowledge entries found" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_delete_item_tool(self, mock_deps_fn):
        from second_brain.mcp_server import delete_item

        mock_deps = MagicMock()
        mock_deps.storage_service.delete_pattern = AsyncMock(return_value=True)
        mock_deps_fn.return_value = mock_deps

        result = await delete_item.fn(table="pattern", item_id="uuid-123")
        assert "Deleted pattern" in result
        assert "uuid-123" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_delete_item_not_found(self, mock_deps_fn):
        from second_brain.mcp_server import delete_item

        mock_deps = MagicMock()
        mock_deps.storage_service.delete_experience = AsyncMock(return_value=False)
        mock_deps_fn.return_value = mock_deps

        result = await delete_item.fn(table="experience", item_id="nonexistent")
        assert "No experience found" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_delete_item_invalid_table(self, mock_deps_fn):
        from second_brain.mcp_server import delete_item

        mock_deps_fn.return_value = MagicMock()

        result = await delete_item.fn(table="invalid", item_id="uuid-123")
        assert "Invalid table" in result
