"""Tests for MCP server tool functions."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from second_brain.schemas import (
    RecallResult, AskResult, MemoryMatch, Relation, LearnResult, PatternExtract,
    CreateResult, DimensionScore, ReviewResult, ContentTypeConfig,
    CoachSession, PMOResult, PriorityScore, EmailAction,
    SpecialistAnswer, ClarityResult, ClarityFinding,
    SynthesizerResult, SynthesizerTheme, TemplateBuilderResult, TemplateOpportunity,
)
from second_brain.services.health import HealthMetrics


def _mock_deps(**overrides):
    """Create a MagicMock deps with proper config values for timeout tests."""
    deps = MagicMock()
    deps.config.api_timeout_seconds = 30
    deps.config.mcp_review_timeout_multiplier = 2
    deps.config.max_input_length = 10000
    deps.config.complex_query_word_threshold = 8
    deps.config.retrieval_oversample_factor = 3
    deps.config.voyage_rerank_top_k = 10
    for k, v in overrides.items():
        setattr(deps, k, v)
    return deps


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
        mock_deps_fn.return_value = _mock_deps()
        mock_model_fn.return_value = MagicMock()

        result = await recall(query="content patterns")
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
        mock_deps_fn.return_value = _mock_deps()
        mock_model_fn.return_value = MagicMock()

        result = await ask(question="Help me write a follow-up email")
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

        result = await brain_health()
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
        mock_deps_fn.return_value = _mock_deps()
        mock_model_fn.return_value = MagicMock()

        result = await recall(query="nonexistent topic")
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

        result = await brain_health()
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
        mock_deps_fn.return_value = _mock_deps()
        mock_model_fn.return_value = MagicMock()

        result = await recall(query="content strategy")
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
        mock_deps_fn.return_value = _mock_deps()
        mock_model_fn.return_value = MagicMock()

        result = await learn(content="Session notes about LinkedIn writing...", category="content")
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

        result = await brain_health()
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

        result = await brain_health()
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

        result = await brain_health()
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

        result = await search_examples()
        assert "linkedin" in result
        assert "Hooks That Work" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_search_examples_empty(self, mock_deps_fn):
        from second_brain.mcp_server import search_examples

        mock_deps = MagicMock()
        mock_deps.storage_service.get_examples = AsyncMock(return_value=[])
        mock_deps_fn.return_value = mock_deps

        result = await search_examples()
        assert "No content examples found" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_search_knowledge_tool(self, mock_deps_fn):
        from second_brain.mcp_server import search_knowledge

        mock_deps = MagicMock()
        mock_deps.storage_service.get_knowledge = AsyncMock(return_value=[
            {"category": "frameworks", "title": "Value Ladder", "content": "Framework..."},
        ])
        mock_deps_fn.return_value = mock_deps

        result = await search_knowledge()
        assert "frameworks" in result
        assert "Value Ladder" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_search_knowledge_empty(self, mock_deps_fn):
        from second_brain.mcp_server import search_knowledge

        mock_deps = MagicMock()
        mock_deps.storage_service.get_knowledge = AsyncMock(return_value=[])
        mock_deps_fn.return_value = mock_deps

        result = await search_knowledge()
        assert "No knowledge entries found" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_delete_item_tool(self, mock_deps_fn):
        from second_brain.mcp_server import delete_item

        mock_deps = MagicMock()
        mock_deps.storage_service.delete_pattern = AsyncMock(return_value=True)
        mock_deps_fn.return_value = mock_deps

        result = await delete_item(table="pattern", item_id="uuid-123")
        assert "Deleted pattern" in result
        assert "uuid-123" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_delete_item_not_found(self, mock_deps_fn):
        from second_brain.mcp_server import delete_item

        mock_deps = MagicMock()
        mock_deps.storage_service.delete_experience = AsyncMock(return_value=False)
        mock_deps_fn.return_value = mock_deps

        result = await delete_item(table="experience", item_id="nonexistent")
        assert "No experience found" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_delete_item_invalid_table(self, mock_deps_fn):
        from second_brain.mcp_server import delete_item

        mock_deps_fn.return_value = MagicMock()

        result = await delete_item(table="invalid", item_id="uuid-123")
        assert "Invalid table" in result

    @patch("second_brain.mcp_server._get_model")
    @patch("second_brain.mcp_server._get_deps")
    @patch("second_brain.mcp_server.create_agent")
    async def test_create_content_tool(self, mock_agent, mock_deps_fn, mock_model_fn):
        from second_brain.mcp_server import create_content

        mock_result = MagicMock()
        mock_result.output = CreateResult(
            draft="Check out our new AI automation platform...",
            content_type="linkedin",
            mode="casual",
            voice_elements=["direct", "conversational"],
            patterns_applied=["Hook First"],
            examples_referenced=["Q3 Launch Post"],
            word_count=85,
            notes="Verify the product name",
        )
        mock_agent.run = AsyncMock(return_value=mock_result)

        linkedin_config = ContentTypeConfig(
            name="LinkedIn Post", default_mode="casual",
            structure_hint="Hook -> Body -> CTA", example_type="linkedin",
            max_words=300, is_builtin=True,
        )
        mock_registry = MagicMock()
        mock_registry.get = AsyncMock(return_value=linkedin_config)

        mock_deps = _mock_deps()
        mock_deps.get_content_type_registry.return_value = mock_registry
        mock_deps.storage_service.get_memory_content = AsyncMock(return_value=[])
        mock_deps.storage_service.get_examples = AsyncMock(return_value=[])
        mock_deps_fn.return_value = mock_deps
        mock_model_fn.return_value = MagicMock()

        result = await create_content(
            prompt="Announce our new AI automation product",
            content_type="linkedin",
        )
        assert "AI automation" in result
        assert "85" in result

    @patch("second_brain.mcp_server._get_model")
    @patch("second_brain.mcp_server._get_deps")
    async def test_create_content_invalid_type(self, mock_deps_fn, mock_model_fn):
        from second_brain.mcp_server import create_content

        mock_registry = MagicMock()
        mock_registry.get = AsyncMock(return_value=None)
        mock_registry.slugs = AsyncMock(return_value=["linkedin", "email"])

        mock_deps = MagicMock()
        mock_deps.get_content_type_registry.return_value = mock_registry
        mock_deps_fn.return_value = mock_deps
        mock_model_fn.return_value = MagicMock()

        result = await create_content(
            prompt="test",
            content_type="invalid-type",
        )
        assert "Unknown content type" in result
        assert "linkedin" in result

    @patch("second_brain.mcp_server._get_model")
    @patch("second_brain.mcp_server._get_deps")
    @patch("second_brain.mcp_server.create_agent")
    async def test_create_content_simplified_prompt(self, mock_agent, mock_deps_fn, mock_model_fn):
        """create_content passes simplified prompt to agent (no pre-loading)."""
        from second_brain.mcp_server import create_content
        mock_result = MagicMock()
        mock_result.output = CreateResult(
            draft="Test draft content",
            content_type="linkedin",
            mode="casual",
            word_count=50,
        )
        mock_agent.run = AsyncMock(return_value=mock_result)
        linkedin_config = ContentTypeConfig(
            name="LinkedIn Post", default_mode="casual",
            structure_hint="Hook -> Body -> CTA", example_type="linkedin",
            max_words=300, is_builtin=True,
        )
        mock_registry = MagicMock()
        mock_registry.get = AsyncMock(return_value=linkedin_config)
        mock_deps = _mock_deps()
        mock_deps.get_content_type_registry.return_value = mock_registry
        mock_deps_fn.return_value = mock_deps
        mock_model_fn.return_value = MagicMock()
        result = await create_content(prompt="Write about AI", content_type="linkedin")
        assert "Test draft" in result
        call_args = mock_agent.run.call_args[0][0]
        assert "LinkedIn Post" in call_args
        assert "Write about AI" in call_args

    @patch("second_brain.mcp_server._get_model")
    @patch("second_brain.mcp_server._get_deps")
    @patch("second_brain.mcp_server.create_agent")
    async def test_create_content_includes_length_guidance(
        self, mock_agent, mock_deps_fn, mock_model_fn
    ):
        """create_content includes length guidance in prompt when available."""
        from second_brain.mcp_server import create_content
        mock_result = MagicMock()
        mock_result.output = CreateResult(
            draft="Draft text here", content_type="linkedin",
            mode="casual", word_count=50,
        )
        mock_agent.run = AsyncMock(return_value=mock_result)
        linkedin_config = ContentTypeConfig(
            name="LinkedIn Post", default_mode="casual",
            structure_hint="Hook -> Body -> CTA", example_type="linkedin",
            max_words=300, is_builtin=True,
            length_guidance="150-300 words, punchy and scannable",
        )
        mock_registry = MagicMock()
        mock_registry.get = AsyncMock(return_value=linkedin_config)
        mock_deps = _mock_deps()
        mock_deps.get_content_type_registry.return_value = mock_registry
        mock_deps_fn.return_value = mock_deps
        mock_model_fn.return_value = MagicMock()
        result = await create_content(prompt="Write about AI", content_type="linkedin")
        assert "Draft text" in result
        call_args = mock_agent.run.call_args[0][0]
        assert "150-300 words" in call_args

    @patch("second_brain.mcp_server._get_model")
    @patch("second_brain.mcp_server._get_deps")
    @patch("second_brain.mcp_server.create_agent")
    async def test_create_content_includes_max_words_fallback(
        self, mock_agent, mock_deps_fn, mock_model_fn
    ):
        """create_content falls back to max_words when no length_guidance."""
        from second_brain.mcp_server import create_content
        mock_result = MagicMock()
        mock_result.output = CreateResult(
            draft="Draft text here", content_type="linkedin",
            mode="casual", word_count=50,
        )
        mock_agent.run = AsyncMock(return_value=mock_result)
        linkedin_config = ContentTypeConfig(
            name="LinkedIn Post", default_mode="casual",
            structure_hint="Hook -> Body -> CTA", example_type="linkedin",
            max_words=300, is_builtin=True,
        )
        mock_registry = MagicMock()
        mock_registry.get = AsyncMock(return_value=linkedin_config)
        mock_deps = _mock_deps()
        mock_deps.get_content_type_registry.return_value = mock_registry
        mock_deps_fn.return_value = mock_deps
        mock_model_fn.return_value = MagicMock()
        result = await create_content(prompt="Write about AI", content_type="linkedin")
        assert "Draft text" in result
        call_args = mock_agent.run.call_args[0][0]
        assert "300 words" in call_args

    @patch("second_brain.mcp_server._get_model")
    @patch("second_brain.mcp_server._get_deps")
    @patch("second_brain.mcp_server.create_agent")
    async def test_create_content_delegates_voice_to_agent(
        self, mock_agent, mock_deps_fn, mock_model_fn
    ):
        """create_content does NOT pre-load voice — agent tools handle it."""
        from second_brain.mcp_server import create_content
        mock_result = MagicMock()
        mock_result.output = CreateResult(
            draft="Draft text here", content_type="linkedin",
            mode="casual", word_count=50,
        )
        mock_agent.run = AsyncMock(return_value=mock_result)
        linkedin_config = ContentTypeConfig(
            name="LinkedIn Post", default_mode="casual",
            structure_hint="Hook -> Body -> CTA", example_type="linkedin",
            max_words=300, is_builtin=True,
        )
        mock_registry = MagicMock()
        mock_registry.get = AsyncMock(return_value=linkedin_config)
        mock_deps = _mock_deps()
        mock_deps.get_content_type_registry.return_value = mock_registry
        mock_deps_fn.return_value = mock_deps
        mock_model_fn.return_value = MagicMock()
        result = await create_content(prompt="Write about AI", content_type="linkedin")
        assert "Draft text" in result
        call_args = mock_agent.run.call_args[0][0]
        # No pre-loaded voice or examples in prompt — agent fetches via its tools
        assert "Voice & Tone Guide" not in call_args
        assert "Reference Examples" not in call_args

    def test_review_content_tool_exists(self):
        from second_brain.mcp_server import server
        tool_names = list(server._tool_manager._tools.keys())
        assert "review_content" in tool_names

    @patch("second_brain.mcp_server._get_model")
    @patch("second_brain.mcp_server._get_deps")
    @patch("second_brain.mcp_server.run_full_review")
    async def test_review_content_tool(self, mock_review, mock_deps_fn, mock_model_fn):
        from second_brain.mcp_server import review_content

        mock_review.return_value = ReviewResult(
            scores=[
                DimensionScore(dimension="Messaging", score=8, status="pass", strengths=["Clear value prop"]),
                DimensionScore(dimension="Brand Voice", score=6, status="warning", suggestions=["Add personality"]),
            ],
            overall_score=7.0,
            verdict="NEEDS REVISION",
            summary="Content scores 7.0/10 overall and needs targeted revisions.",
            top_strengths=["Clear value prop"],
            critical_issues=[],
            next_steps=["Consider improvements in: Brand Voice"],
        )
        mock_deps_fn.return_value = _mock_deps()
        mock_model_fn.return_value = MagicMock()

        result = await review_content(content="Test content", content_type="linkedin")
        assert "7.0" in result
        assert "NEEDS REVISION" in result
        assert "Messaging" in result
        assert "Brand Voice" in result
        assert "Clear value prop" in result


class TestQuickRecall:
    """Tests for the quick_recall MCP tool."""

    async def test_quick_recall_exists(self):
        """Verify quick_recall is registered as an MCP tool."""
        from second_brain.mcp_server import server
        tools = server._tool_manager._tools
        assert "quick_recall" in tools

    @patch("second_brain.mcp_server._deps_failed", False)
    @patch("second_brain.mcp_server._get_deps")
    async def test_quick_recall_returns_string(self, mock_deps_fn):
        """quick_recall should return a formatted string result."""
        from second_brain.mcp_server import quick_recall

        deps = _mock_deps()
        deps.memory_service = MagicMock()
        deps.memory_service.search = AsyncMock(return_value=MagicMock(
            memories=[{"memory": "Test memory content", "score": 0.9}],
            relations=[],
        ))
        deps.embedding_service = None  # skip hybrid search
        deps.voyage_service = None  # skip reranking
        mock_deps_fn.return_value = deps

        result = await quick_recall(query="test query")
        assert isinstance(result, str)

    @patch("second_brain.mcp_server._deps_failed", False)
    @patch("second_brain.mcp_server._get_deps")
    async def test_quick_recall_empty_query_rejected(self, mock_deps_fn):
        """Empty query should return validation error."""
        from second_brain.mcp_server import quick_recall

        mock_deps_fn.return_value = _mock_deps()
        result = await quick_recall(query="")
        assert "empty" in result.lower() or "cannot be empty" in result.lower()

    @patch("second_brain.mcp_server._deps_failed", False)
    @patch("second_brain.mcp_server._get_deps")
    async def test_quick_recall_no_results_message(self, mock_deps_fn):
        """When no results found, should suggest using recall() instead."""
        from second_brain.mcp_server import quick_recall
        from second_brain.services.search_result import SearchResult

        deps = _mock_deps()
        deps.memory_service = MagicMock()
        deps.memory_service.search = AsyncMock(return_value=SearchResult(
            memories=[], relations=[],
        ))
        deps.embedding_service = None
        deps.voyage_service = None
        mock_deps_fn.return_value = deps

        result = await quick_recall(query="nonexistent topic")
        assert "no results" in result.lower() or "recall()" in result.lower()

    @patch("second_brain.mcp_server._deps_failed", False)
    @patch("second_brain.mcp_server._get_deps")
    async def test_quick_recall_includes_header(self, mock_deps_fn):
        """Results should include the Quick Recall header."""
        from second_brain.mcp_server import quick_recall

        deps = _mock_deps()
        deps.memory_service = MagicMock()
        deps.memory_service.search = AsyncMock(return_value=MagicMock(
            memories=[{"memory": "content patterns", "score": 0.9}],
            relations=[],
        ))
        deps.embedding_service = None
        deps.voyage_service = None
        mock_deps_fn.return_value = deps

        result = await quick_recall(query="content patterns")
        assert "# Quick Recall" in result


class TestParallelQuickRecall:
    """Tests for parallel quick_recall with Mem0 + hybrid concurrent execution."""

    @patch("second_brain.mcp_server._deps_failed", False)
    @patch("second_brain.mcp_server._get_deps")
    async def test_quick_recall_parallel_with_hybrid(self, mock_deps_fn):
        """quick_recall runs Mem0 and hybrid in parallel when embedding available."""
        from second_brain.mcp_server import quick_recall

        deps = _mock_deps()
        deps.memory_service = MagicMock()
        deps.memory_service.search = AsyncMock(return_value=MagicMock(
            memories=[{"memory": "Test memory", "score": 0.9}],
            relations=[],
        ))
        deps.embedding_service = MagicMock()
        deps.embedding_service.embed_query = AsyncMock(return_value=[0.1] * 1024)
        deps.storage_service = MagicMock()
        deps.storage_service.hybrid_search = AsyncMock(return_value=[
            {"content": "hybrid result", "similarity": 0.85},
        ])
        deps.voyage_service = None
        deps.graphiti_service = None
        deps.config.retrieval_oversample_factor = 2
        mock_deps_fn.return_value = deps

        result = await quick_recall(query="test patterns", limit=5)
        assert isinstance(result, str)
        deps.memory_service.search.assert_called_once()
        deps.storage_service.hybrid_search.assert_called_once()
        deps.embedding_service.embed_query.assert_called_once()

    @patch("second_brain.mcp_server._deps_failed", False)
    @patch("second_brain.mcp_server._get_deps")
    async def test_quick_recall_includes_sources_in_footer(self, mock_deps_fn):
        """quick_recall output footer includes search source names."""
        from second_brain.mcp_server import quick_recall

        deps = _mock_deps()
        deps.memory_service = MagicMock()
        deps.memory_service.search = AsyncMock(return_value=MagicMock(
            memories=[{"memory": "Test content", "score": 0.9}],
            relations=[],
        ))
        deps.embedding_service = None
        deps.voyage_service = None
        deps.graphiti_service = None
        deps.config.retrieval_oversample_factor = 2
        mock_deps_fn.return_value = deps

        result = await quick_recall(query="test")
        assert "sources:" in result.lower()
        assert "mem0" in result

    @patch("second_brain.mcp_server._deps_failed", False)
    @patch("second_brain.mcp_server._get_deps")
    async def test_quick_recall_handles_mem0_failure(self, mock_deps_fn):
        """quick_recall should handle Mem0 failure gracefully when hybrid succeeds."""
        from second_brain.mcp_server import quick_recall

        deps = _mock_deps()
        deps.memory_service = MagicMock()
        deps.memory_service.search = AsyncMock(side_effect=ConnectionError("mem0 down"))
        deps.embedding_service = MagicMock()
        deps.embedding_service.embed_query = AsyncMock(return_value=[0.1] * 1024)
        deps.storage_service = MagicMock()
        deps.storage_service.hybrid_search = AsyncMock(return_value=[
            {"content": "hybrid fallback", "similarity": 0.8},
        ])
        deps.voyage_service = None
        deps.graphiti_service = None
        deps.config.retrieval_oversample_factor = 2
        mock_deps_fn.return_value = deps

        result = await quick_recall(query="test")
        assert isinstance(result, str)
        # Should still return something — hybrid succeeded
        assert "hybrid:memory_content" in result or "No results" in result


class TestMCPAgentFailures:
    """Tests for MCP tool behavior when agents fail."""

    @patch("second_brain.mcp_server._get_model")
    @patch("second_brain.mcp_server._get_deps")
    @patch("second_brain.mcp_server.recall_agent")
    async def test_recall_agent_timeout(self, mock_agent, mock_deps_fn, mock_model_fn):
        """Recall tool returns timeout message when agent hangs."""
        from second_brain.mcp_server import recall

        mock_agent.run = AsyncMock(side_effect=TimeoutError())
        mock_deps_fn.return_value = _mock_deps()
        mock_model_fn.return_value = MagicMock()

        result = await recall(query="test query")
        assert "timed out" in result.lower()

    @patch("second_brain.mcp_server._get_model")
    @patch("second_brain.mcp_server._get_deps")
    @patch("second_brain.mcp_server.ask_agent")
    async def test_ask_agent_timeout(self, mock_agent, mock_deps_fn, mock_model_fn):
        """Ask tool returns timeout message when agent hangs."""
        from second_brain.mcp_server import ask

        mock_agent.run = AsyncMock(side_effect=TimeoutError())
        mock_deps_fn.return_value = _mock_deps()
        mock_model_fn.return_value = MagicMock()

        result = await ask(question="test question")
        assert "timed out" in result.lower()

    @patch("second_brain.mcp_server._get_model")
    @patch("second_brain.mcp_server._get_deps")
    @patch("second_brain.mcp_server.learn_agent")
    async def test_learn_agent_timeout(self, mock_agent, mock_deps_fn, mock_model_fn):
        """Learn tool returns timeout message when agent hangs."""
        from second_brain.mcp_server import learn

        mock_agent.run = AsyncMock(side_effect=TimeoutError())
        mock_deps_fn.return_value = _mock_deps()
        mock_model_fn.return_value = MagicMock()

        result = await learn(content="test content")
        assert "timed out" in result.lower()

    @patch("second_brain.mcp_server._get_model")
    @patch("second_brain.mcp_server._get_deps")
    @patch("second_brain.mcp_server.create_agent")
    async def test_create_agent_timeout(self, mock_agent, mock_deps_fn, mock_model_fn):
        """Create tool returns timeout message when agent hangs."""
        from second_brain.mcp_server import create_content

        mock_agent.run = AsyncMock(side_effect=TimeoutError())

        linkedin_config = ContentTypeConfig(
            name="LinkedIn Post", default_mode="casual",
            structure_hint="Hook -> Body -> CTA", example_type="linkedin",
            max_words=300, is_builtin=True,
        )
        mock_registry = MagicMock()
        mock_registry.get = AsyncMock(return_value=linkedin_config)
        mock_deps = _mock_deps()
        mock_deps.get_content_type_registry.return_value = mock_registry
        mock_deps.storage_service.get_memory_content = AsyncMock(return_value=[])
        mock_deps.storage_service.get_examples = AsyncMock(return_value=[])
        mock_deps_fn.return_value = mock_deps
        mock_model_fn.return_value = MagicMock()

        result = await create_content(prompt="Write about AI", content_type="linkedin")
        assert "timed out" in result.lower()

    async def test_deps_circuit_breaker(self):
        """After first deps failure, subsequent calls fail fast."""
        import second_brain.mcp_server as mcp_mod

        # Save original state
        orig_deps = mcp_mod._deps
        orig_failed = mcp_mod._deps_failed
        orig_error = mcp_mod._deps_error

        try:
            mcp_mod._deps = None
            mcp_mod._deps_failed = False
            mcp_mod._deps_error = ""

            with patch("second_brain.mcp_server.create_deps", side_effect=RuntimeError("DB down")):
                # First call should raise
                with pytest.raises(RuntimeError, match="initialization failed"):
                    mcp_mod._get_deps()

                # Second call should fail fast (circuit breaker)
                with pytest.raises(RuntimeError, match="initialization failed"):
                    mcp_mod._get_deps()
        finally:
            # Restore state
            mcp_mod._deps = orig_deps
            mcp_mod._deps_failed = orig_failed
            mcp_mod._deps_error = orig_error

    @patch("second_brain.mcp_server._get_deps")
    async def test_vector_search_no_embedding_service(self, mock_get_deps):
        """Vector search returns message when OPENAI_API_KEY not set."""
        from second_brain.mcp_server import vector_search

        mock_deps = MagicMock()
        mock_deps.embedding_service = None
        mock_get_deps.return_value = mock_deps

        result = await vector_search(query="test")
        assert "unavailable" in result.lower()

    @patch("second_brain.mcp_server._get_model")
    @patch("second_brain.mcp_server._get_deps")
    @patch("second_brain.mcp_server.run_full_review")
    async def test_review_timeout(self, mock_review, mock_deps_fn, mock_model_fn):
        """Review tool returns timeout message when review hangs."""
        from second_brain.mcp_server import review_content

        mock_review.side_effect = TimeoutError()
        mock_deps_fn.return_value = _mock_deps()
        mock_model_fn.return_value = MagicMock()

        result = await review_content(content="Test content")
        assert "timed out" in result.lower()


class TestMCPInputValidation:
    """Test input validation on MCP tools."""

    async def test_recall_empty_query_returns_error(self):
        from second_brain.mcp_server import recall
        result = await recall(query="")
        assert "empty" in result.lower()

    async def test_recall_long_query_returns_error(self):
        from second_brain.mcp_server import recall
        result = await recall(query="x" * 15000)
        assert "too long" in result.lower()

    async def test_ask_whitespace_returns_error(self):
        from second_brain.mcp_server import ask
        result = await ask(question="   ")
        assert "empty" in result.lower()

    async def test_learn_empty_content_returns_error(self):
        from second_brain.mcp_server import learn
        result = await learn(content="")
        assert "empty" in result.lower()

    async def test_create_content_empty_prompt_returns_error(self):
        from second_brain.mcp_server import create_content
        result = await create_content(prompt="")
        assert "empty" in result.lower()

    async def test_review_content_empty_returns_error(self):
        from second_brain.mcp_server import review_content
        result = await review_content(content="   ")
        assert "empty" in result.lower()

    async def test_delete_item_empty_id_returns_error(self):
        from second_brain.mcp_server import delete_item
        result = await delete_item(table="pattern", item_id="")
        assert "empty" in result.lower()

    async def test_manage_content_type_empty_slug_returns_error(self):
        from second_brain.mcp_server import manage_content_type
        result = await manage_content_type(action="add", slug="")
        assert "empty" in result.lower()


class TestMCPGraphSearch:
    """Test graph_search MCP tool."""

    @patch("second_brain.mcp_server._get_deps")
    async def test_graph_search_not_enabled(self, mock_get_deps):
        mock_deps = MagicMock()
        mock_deps.graphiti_service = None
        mock_get_deps.return_value = mock_deps

        from second_brain.mcp_server import graph_search
        result = await graph_search(query="test")
        assert "not enabled" in result.lower()

    @patch("second_brain.mcp_server._get_deps")
    async def test_graph_search_no_results(self, mock_get_deps):
        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])
        mock_deps = MagicMock()
        mock_deps.graphiti_service = mock_graphiti
        mock_get_deps.return_value = mock_deps

        from second_brain.mcp_server import graph_search
        result = await graph_search(query="unknown")
        assert "no graph relationships" in result.lower()

    @patch("second_brain.mcp_server._get_deps")
    async def test_graph_search_returns_relationships(self, mock_get_deps):
        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[
            {"source": "Pattern A", "relationship": "relates_to", "target": "Topic B"},
        ])
        mock_deps = MagicMock()
        mock_deps.graphiti_service = mock_graphiti
        mock_get_deps.return_value = mock_deps

        from second_brain.mcp_server import graph_search
        result = await graph_search(query="patterns")
        assert "Pattern A" in result
        assert "relates_to" in result
        assert "Topic B" in result


class TestGraphHealth:
    """Test graph_health MCP tool."""

    @patch("second_brain.mcp_server._get_deps")
    async def test_graph_health_not_enabled(self, mock_get_deps):
        mock_deps = MagicMock()
        mock_deps.graphiti_service = None
        mock_get_deps.return_value = mock_deps
        from second_brain.mcp_server import graph_health
        result = await graph_health()
        assert "not enabled" in result.lower()

    @patch("second_brain.mcp_server._get_deps")
    async def test_graph_health_healthy(self, mock_get_deps):
        mock_graphiti = AsyncMock()
        mock_graphiti.health_check = AsyncMock(return_value={
            "status": "healthy",
            "backend": "neo4j",
        })
        mock_deps = MagicMock()
        mock_deps.graphiti_service = mock_graphiti
        mock_get_deps.return_value = mock_deps
        from second_brain.mcp_server import graph_health
        result = await graph_health()
        assert "healthy" in result
        assert "neo4j" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_graph_health_with_error(self, mock_get_deps):
        mock_graphiti = AsyncMock()
        mock_graphiti.health_check = AsyncMock(return_value={
            "status": "degraded",
            "backend": "falkordb",
            "error": "Connection timeout",
        })
        mock_deps = MagicMock()
        mock_deps.graphiti_service = mock_graphiti
        mock_get_deps.return_value = mock_deps
        from second_brain.mcp_server import graph_health
        result = await graph_health()
        assert "degraded" in result
        assert "falkordb" in result
        assert "Connection timeout" in result


class TestGraphEntitySearch:
    """Test graph_entity_search MCP tool."""

    @patch("second_brain.mcp_server._get_deps")
    async def test_unavailable_without_graphiti(self, mock_get_deps):
        mock_deps = _mock_deps()
        mock_deps.graphiti_service = None
        mock_get_deps.return_value = mock_deps
        from second_brain.mcp_server import graph_entity_search
        result = await graph_entity_search(query="test")
        assert "unavailable" in result.lower()

    @patch("second_brain.mcp_server._get_deps")
    async def test_returns_formatted_entities(self, mock_get_deps):
        mock_graphiti = AsyncMock()
        mock_graphiti.search_entities = AsyncMock(return_value=[
            {"name": "Alice", "summary": "A person", "labels": ["Person"], "uuid": "e1", "created_at": None},
        ])
        mock_deps = _mock_deps(graphiti_service=mock_graphiti)
        mock_get_deps.return_value = mock_deps
        from second_brain.mcp_server import graph_entity_search
        result = await graph_entity_search(query="Alice")
        assert "Alice" in result
        assert "A person" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_empty_results(self, mock_get_deps):
        mock_graphiti = AsyncMock()
        mock_graphiti.search_entities = AsyncMock(return_value=[])
        mock_deps = _mock_deps(graphiti_service=mock_graphiti)
        mock_get_deps.return_value = mock_deps
        from second_brain.mcp_server import graph_entity_search
        result = await graph_entity_search(query="nothing")
        assert "no entities" in result.lower()


class TestGraphEntityContext:
    """Test graph_entity_context MCP tool."""

    @patch("second_brain.mcp_server._get_deps")
    async def test_unavailable_without_graphiti(self, mock_get_deps):
        mock_deps = _mock_deps()
        mock_deps.graphiti_service = None
        mock_get_deps.return_value = mock_deps
        from second_brain.mcp_server import graph_entity_context
        result = await graph_entity_context(entity_uuid="e1")
        assert "unavailable" in result.lower()

    @patch("second_brain.mcp_server._get_deps")
    async def test_returns_entity_with_relationships(self, mock_get_deps):
        mock_graphiti = AsyncMock()
        mock_graphiti.get_entity_context = AsyncMock(return_value={
            "entity": {"uuid": "e1", "name": "Alice", "summary": "A person"},
            "relationships": [
                {"direction": "outgoing", "type": "KNOWS", "fact": "friends", "connected_entity": "Bob", "connected_uuid": "e2"},
            ],
        })
        mock_deps = _mock_deps(graphiti_service=mock_graphiti)
        mock_get_deps.return_value = mock_deps
        from second_brain.mcp_server import graph_entity_context
        result = await graph_entity_context(entity_uuid="e1")
        assert "Alice" in result
        assert "Bob" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_entity_not_found(self, mock_get_deps):
        mock_graphiti = AsyncMock()
        mock_graphiti.get_entity_context = AsyncMock(return_value={
            "entity": None, "relationships": [],
        })
        mock_deps = _mock_deps(graphiti_service=mock_graphiti)
        mock_get_deps.return_value = mock_deps
        from second_brain.mcp_server import graph_entity_context
        result = await graph_entity_context(entity_uuid="nonexistent")
        assert "not found" in result.lower()


class TestGraphTraverse:
    """Test graph_traverse MCP tool."""

    @patch("second_brain.mcp_server._get_deps")
    async def test_unavailable_without_graphiti(self, mock_get_deps):
        mock_deps = _mock_deps()
        mock_deps.graphiti_service = None
        mock_get_deps.return_value = mock_deps
        from second_brain.mcp_server import graph_traverse
        result = await graph_traverse(entity_uuid="e1")
        assert "unavailable" in result.lower()

    @patch("second_brain.mcp_server._get_deps")
    async def test_returns_traversal_results(self, mock_get_deps):
        mock_graphiti = AsyncMock()
        mock_graphiti.traverse_neighbors = AsyncMock(return_value=[
            {"source": "Alice", "relationship": "knows", "target": "Bob"},
        ])
        mock_deps = _mock_deps(graphiti_service=mock_graphiti)
        mock_get_deps.return_value = mock_deps
        from second_brain.mcp_server import graph_traverse
        result = await graph_traverse(entity_uuid="e1")
        assert "Alice" in result
        assert "knows" in result
        assert "Bob" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_no_connections(self, mock_get_deps):
        mock_graphiti = AsyncMock()
        mock_graphiti.traverse_neighbors = AsyncMock(return_value=[])
        mock_deps = _mock_deps(graphiti_service=mock_graphiti)
        mock_get_deps.return_value = mock_deps
        from second_brain.mcp_server import graph_traverse
        result = await graph_traverse(entity_uuid="e1")
        assert "no connections" in result.lower()


class TestGraphCommunities:
    """Test graph_communities MCP tool."""

    @patch("second_brain.mcp_server._get_deps")
    async def test_unavailable_without_graphiti(self, mock_get_deps):
        mock_deps = _mock_deps()
        mock_deps.graphiti_service = None
        mock_get_deps.return_value = mock_deps
        from second_brain.mcp_server import graph_communities
        result = await graph_communities()
        assert "unavailable" in result.lower()

    @patch("second_brain.mcp_server._get_deps")
    async def test_returns_communities(self, mock_get_deps):
        mock_graphiti = AsyncMock()
        mock_graphiti.search_communities = AsyncMock(return_value=[
            {"uuid": "c1", "name": "Engineering", "summary": "The engineering team"},
        ])
        mock_deps = _mock_deps(graphiti_service=mock_graphiti)
        mock_get_deps.return_value = mock_deps
        from second_brain.mcp_server import graph_communities
        result = await graph_communities(query="engineering")
        assert "Engineering" in result
        assert "engineering team" in result.lower()

    @patch("second_brain.mcp_server._get_deps")
    async def test_no_communities(self, mock_get_deps):
        mock_graphiti = AsyncMock()
        mock_graphiti.search_communities = AsyncMock(return_value=[])
        mock_deps = _mock_deps(graphiti_service=mock_graphiti)
        mock_get_deps.return_value = mock_deps
        from second_brain.mcp_server import graph_communities
        result = await graph_communities()
        assert "no communities" in result.lower()


class TestGraphAdvancedSearch:
    """Test graph_advanced_search MCP tool."""

    @patch("second_brain.mcp_server._get_deps")
    async def test_unavailable_without_graphiti(self, mock_get_deps):
        mock_deps = _mock_deps()
        mock_deps.graphiti_service = None
        mock_get_deps.return_value = mock_deps
        from second_brain.mcp_server import graph_advanced_search
        result = await graph_advanced_search(query="test")
        assert "unavailable" in result.lower()

    @patch("second_brain.mcp_server._get_deps")
    async def test_returns_edges_nodes_communities(self, mock_get_deps):
        mock_graphiti = AsyncMock()
        mock_graphiti.advanced_search = AsyncMock(return_value={
            "edges": [{"source": "A", "relationship": "knows", "target": "B"}],
            "nodes": [{"name": "NodeA", "summary": "A node", "uuid": "n1"}],
            "communities": [{"name": "CommA", "summary": "A community", "uuid": "c1"}],
        })
        mock_deps = _mock_deps(graphiti_service=mock_graphiti)
        mock_get_deps.return_value = mock_deps
        from second_brain.mcp_server import graph_advanced_search
        result = await graph_advanced_search(query="test")
        assert "Relationships" in result
        assert "A --[knows]--> B" in result
        assert "NodeA" in result
        assert "CommA" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_no_results(self, mock_get_deps):
        mock_graphiti = AsyncMock()
        mock_graphiti.advanced_search = AsyncMock(return_value={
            "edges": [], "nodes": [], "communities": [],
        })
        mock_deps = _mock_deps(graphiti_service=mock_graphiti)
        mock_get_deps.return_value = mock_deps
        from second_brain.mcp_server import graph_advanced_search
        result = await graph_advanced_search(query="nothing")
        assert "no results" in result.lower()


class TestConsolidateBrain:
    @patch("second_brain.mcp_server._get_model")
    @patch("second_brain.mcp_server._get_deps")
    @patch("second_brain.mcp_server.learn_agent")
    async def test_consolidate_brain(self, mock_agent, mock_deps_fn, mock_model_fn):
        from second_brain.mcp_server import consolidate_brain

        mock_output = MagicMock()
        mock_output.input_summary = "Reviewed 10 memories"
        mock_output.patterns_extracted = [
            PatternExtract(
                name="Hook First", topic="Content",
                pattern_text="Start with a hook", evidence=["Post v3"],
            ),
        ]
        mock_output.patterns_new = 2
        mock_output.patterns_reinforced = 1
        mock_agent.run = AsyncMock(return_value=MagicMock(output=mock_output))
        mock_deps_fn.return_value = _mock_deps()
        mock_model_fn.return_value = MagicMock()

        result = await consolidate_brain()
        assert "Consolidation" in result
        assert "2 new" in result
        assert "1 reinforced" in result
        assert "Hook First" in result

    @patch("second_brain.mcp_server._get_model")
    @patch("second_brain.mcp_server._get_deps")
    @patch("second_brain.mcp_server.learn_agent")
    async def test_consolidate_brain_custom_cluster_size(self, mock_agent, mock_deps_fn, mock_model_fn):
        from second_brain.mcp_server import consolidate_brain

        mock_output = MagicMock()
        mock_output.input_summary = "Reviewed 5 memories"
        mock_output.patterns_extracted = []
        mock_output.patterns_new = 0
        mock_output.patterns_reinforced = 0
        mock_agent.run = AsyncMock(return_value=MagicMock(output=mock_output))
        mock_deps_fn.return_value = _mock_deps()
        mock_model_fn.return_value = MagicMock()

        result = await consolidate_brain(min_cluster_size=5)
        assert "Consolidation" in result
        assert "0 new" in result


class TestGrowthReport:
    @patch("second_brain.mcp_server._get_deps")
    @patch("second_brain.services.health.HealthService")
    async def test_growth_report(self, mock_hs_cls, mock_deps_fn):
        from second_brain.mcp_server import growth_report

        mock_metrics = HealthMetrics(
            memory_count=50,
            total_patterns=10,
            high_confidence=3,
            medium_confidence=5,
            low_confidence=2,
            experience_count=8,
            graph_provider="none",
            latest_update="2026-02-15",
            status="GROWING",
            growth_events_total=15,
            patterns_created_period=5,
            patterns_reinforced_period=8,
            confidence_upgrades_period=2,
            reviews_completed_period=0,
            stale_patterns=[],
            topics={"Content": 5},
        )
        mock_hs_cls.return_value.compute_growth = AsyncMock(return_value=mock_metrics)
        mock_deps_fn.return_value = MagicMock()

        result = await growth_report(days=30)
        assert "Growth Report" in result
        assert "GROWING" in result
        assert "Patterns created: 5" in result
        assert "Patterns reinforced: 8" in result

    @patch("second_brain.mcp_server._get_deps")
    @patch("second_brain.services.health.HealthService")
    async def test_growth_report_with_reviews(self, mock_hs_cls, mock_deps_fn):
        from second_brain.mcp_server import growth_report

        mock_metrics = HealthMetrics(
            memory_count=50, total_patterns=10, high_confidence=3,
            medium_confidence=5, low_confidence=2, experience_count=8,
            graph_provider="none", latest_update="2026-02-15", status="GROWING",
            reviews_completed_period=4, avg_review_score=8.2,
            review_score_trend="improving",
        )
        mock_hs_cls.return_value.compute_growth = AsyncMock(return_value=mock_metrics)
        mock_deps_fn.return_value = MagicMock()

        result = await growth_report(days=7)
        assert "Quality Metrics" in result
        assert "8.2" in result
        assert "improving" in result

    @patch("second_brain.mcp_server._get_deps")
    @patch("second_brain.services.health.HealthService")
    async def test_growth_report_with_stale_patterns(self, mock_hs_cls, mock_deps_fn):
        from second_brain.mcp_server import growth_report
        mock_metrics = HealthMetrics(
            memory_count=50, total_patterns=10, high_confidence=3,
            medium_confidence=5, low_confidence=2, experience_count=8,
            graph_provider="none", latest_update="2026-02-15", status="GROWING",
            stale_patterns=["Old Pattern", "Forgotten Rule"],
        )
        mock_hs_cls.return_value.compute_growth = AsyncMock(return_value=mock_metrics)
        mock_deps_fn.return_value = MagicMock()
        result = await growth_report(days=30)
        assert "Stale Patterns" in result
        assert "Old Pattern" in result
        assert "Forgotten Rule" in result

    @patch("second_brain.mcp_server._get_deps")
    @patch("second_brain.services.health.HealthService")
    async def test_growth_report_with_topics(self, mock_hs_cls, mock_deps_fn):
        from second_brain.mcp_server import growth_report
        mock_metrics = HealthMetrics(
            memory_count=50, total_patterns=10, high_confidence=3,
            medium_confidence=5, low_confidence=2, experience_count=8,
            graph_provider="none", latest_update="2026-02-15", status="GROWING",
            topics={"Content": 5, "Messaging": 3},
        )
        mock_hs_cls.return_value.compute_growth = AsyncMock(return_value=mock_metrics)
        mock_deps_fn.return_value = MagicMock()
        result = await growth_report(days=30)
        assert "Content" in result
        assert "Messaging" in result


class TestListContentTypes:
    @patch("second_brain.mcp_server._get_deps")
    async def test_list_content_types(self, mock_deps_fn):
        from second_brain.mcp_server import list_content_types

        linkedin_config = ContentTypeConfig(
            name="LinkedIn Post", default_mode="casual",
            structure_hint="Hook -> Body -> CTA", example_type="linkedin",
            max_words=300, is_builtin=True,
        )
        mock_registry = MagicMock()
        mock_registry.get_all = AsyncMock(return_value={"linkedin": linkedin_config})
        mock_deps = MagicMock()
        mock_deps.get_content_type_registry.return_value = mock_registry
        mock_deps_fn.return_value = mock_deps

        result = await list_content_types()
        assert "Content Types" in result
        assert "linkedin" in result
        assert "LinkedIn Post" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_list_content_types_empty(self, mock_deps_fn):
        from second_brain.mcp_server import list_content_types

        mock_registry = MagicMock()
        mock_registry.get_all = AsyncMock(return_value={})
        mock_deps = MagicMock()
        mock_deps.get_content_type_registry.return_value = mock_registry
        mock_deps_fn.return_value = mock_deps

        result = await list_content_types()
        assert "No content types available" in result


class TestManageContentType:
    @patch("second_brain.mcp_server._get_deps")
    async def test_add_content_type(self, mock_deps_fn):
        from second_brain.mcp_server import manage_content_type

        mock_registry = MagicMock()
        mock_deps = MagicMock()
        mock_deps.get_content_type_registry.return_value = mock_registry
        mock_deps.storage_service.upsert_content_type = AsyncMock(return_value={"slug": "newsletter"})
        mock_deps_fn.return_value = mock_deps

        result = await manage_content_type(
            action="add", slug="newsletter", name="Newsletter",
            structure_hint="Intro -> Body -> CTA",
        )
        assert "Added" in result
        assert "newsletter" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_add_missing_required_fields(self, mock_deps_fn):
        from second_brain.mcp_server import manage_content_type

        mock_deps = MagicMock()
        mock_deps.get_content_type_registry.return_value = MagicMock()
        mock_deps_fn.return_value = mock_deps

        result = await manage_content_type(action="add", slug="test")
        assert "required" in result.lower()

    @patch("second_brain.mcp_server._get_deps")
    async def test_remove_content_type(self, mock_deps_fn):
        from second_brain.mcp_server import manage_content_type

        mock_registry = MagicMock()
        mock_deps = MagicMock()
        mock_deps.get_content_type_registry.return_value = mock_registry
        mock_deps.storage_service.get_content_type_by_slug = AsyncMock(
            return_value={"slug": "newsletter", "is_builtin": False}
        )
        mock_deps.storage_service.delete_content_type = AsyncMock(return_value=True)
        mock_deps_fn.return_value = mock_deps

        result = await manage_content_type(action="remove", slug="newsletter")
        assert "Removed" in result
        assert "newsletter" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_remove_not_found(self, mock_deps_fn):
        from second_brain.mcp_server import manage_content_type

        mock_deps = MagicMock()
        mock_deps.get_content_type_registry.return_value = MagicMock()
        mock_deps.storage_service.get_content_type_by_slug = AsyncMock(return_value=None)
        mock_deps_fn.return_value = mock_deps

        result = await manage_content_type(action="remove", slug="nonexistent")
        assert "No content type found" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_invalid_action(self, mock_deps_fn):
        from second_brain.mcp_server import manage_content_type

        mock_deps = MagicMock()
        mock_deps.get_content_type_registry.return_value = MagicMock()
        mock_deps_fn.return_value = mock_deps

        result = await manage_content_type(action="invalid", slug="test")
        assert "Unknown action" in result


class TestProjectMCPTools:
    """Test project lifecycle MCP tools."""

    @patch("second_brain.mcp_server._get_deps")
    async def test_create_project(self, mock_deps_fn):
        from second_brain.mcp_server import create_project

        mock_deps = MagicMock()
        mock_deps.storage_service.create_project = AsyncMock(
            return_value={"id": "proj-1", "name": "Test"}
        )
        mock_deps_fn.return_value = mock_deps

        result = await create_project(name="Test", category="content")
        assert "Project created" in result
        assert "Test" in result
        assert "proj-1" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_create_project_failure(self, mock_deps_fn):
        from second_brain.mcp_server import create_project

        mock_deps = MagicMock()
        mock_deps.storage_service.create_project = AsyncMock(return_value=None)
        mock_deps_fn.return_value = mock_deps

        result = await create_project(name="Fail")
        assert "Failed" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_project_status(self, mock_deps_fn):
        from second_brain.mcp_server import project_status

        mock_deps = MagicMock()
        mock_deps.storage_service.get_project = AsyncMock(return_value={
            "name": "My Project", "lifecycle_stage": "executing",
            "category": "content", "project_artifacts": [],
        })
        mock_deps_fn.return_value = mock_deps

        result = await project_status(project_id="proj-1")
        assert "My Project" in result
        assert "executing" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_project_status_not_found(self, mock_deps_fn):
        from second_brain.mcp_server import project_status

        mock_deps = MagicMock()
        mock_deps.storage_service.get_project = AsyncMock(return_value=None)
        mock_deps_fn.return_value = mock_deps

        result = await project_status(project_id="missing")
        assert "not found" in result.lower()

    @patch("second_brain.services.health.HealthService")
    @patch("second_brain.mcp_server._get_deps")
    async def test_brain_setup(self, mock_deps_fn, mock_hs):
        from second_brain.mcp_server import brain_setup

        mock_deps = MagicMock()
        mock_deps.config.api_timeout_seconds = 30
        mock_deps_fn.return_value = mock_deps

        mock_instance = MagicMock()
        mock_instance.compute_setup_status = AsyncMock(return_value={
            "completed_count": 6, "total_steps": 8, "is_complete": False,
            "missing_categories": ["voice_guide"],
            "steps": [
                {"description": "Patterns loaded", "completed": True},
                {"description": "Voice guide", "completed": False},
            ],
        })
        mock_hs.return_value = mock_instance

        result = await brain_setup()
        assert "Brain Setup" in result
        assert "75%" in result
        assert "[x]" in result
        assert "[ ]" in result

    @patch("second_brain.agents.utils.format_pattern_registry")
    @patch("second_brain.mcp_server._get_deps")
    async def test_pattern_registry(self, mock_deps_fn, mock_format):
        from second_brain.mcp_server import pattern_registry

        mock_deps = MagicMock()
        mock_deps.config.api_timeout_seconds = 30
        mock_deps.storage_service.get_pattern_registry = AsyncMock(return_value=[
            {"name": "Hook", "confidence": "HIGH"},
        ])
        mock_deps_fn.return_value = mock_deps
        mock_format.return_value = "| Hook | HIGH |\nTotal: 1 patterns"

        result = await pattern_registry()
        assert "Hook" in result
        assert "Total: 1" in result


class TestNewMCPTools:
    """Tests for gap-remediation MCP tools (service-direct Pattern A)."""

    @patch("second_brain.mcp_server._get_deps")
    async def test_list_projects_returns_projects(self, mock_deps_fn):
        from second_brain.mcp_server import list_projects
        mock_deps = _mock_deps()
        mock_deps.storage_service.list_projects = AsyncMock(return_value=[
            {"id": "proj-1", "name": "Q1 Campaign", "lifecycle_stage": "executing",
             "category": "content", "description": "Our Q1 push"},
        ])
        mock_deps_fn.return_value = mock_deps
        result = await list_projects()
        assert "Q1 Campaign" in result
        assert "executing" in result
        assert "proj-1" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_list_projects_empty(self, mock_deps_fn):
        from second_brain.mcp_server import list_projects
        mock_deps = _mock_deps()
        mock_deps.storage_service.list_projects = AsyncMock(return_value=[])
        mock_deps_fn.return_value = mock_deps
        result = await list_projects()
        assert "No projects found" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_update_project_success(self, mock_deps_fn):
        from second_brain.mcp_server import update_project
        mock_deps = _mock_deps()
        mock_deps.storage_service.update_project = AsyncMock(
            return_value={"id": "proj-1", "name": "New Name"}
        )
        mock_deps_fn.return_value = mock_deps
        result = await update_project(project_id="proj-1", name="New Name")
        assert "New Name" in result
        assert "Changed" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_update_project_no_fields(self, mock_deps_fn):
        from second_brain.mcp_server import update_project
        mock_deps_fn.return_value = _mock_deps()
        result = await update_project(project_id="proj-1")
        assert "No fields" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_update_project_not_found(self, mock_deps_fn):
        from second_brain.mcp_server import update_project
        mock_deps = _mock_deps()
        mock_deps.storage_service.update_project = AsyncMock(return_value=None)
        mock_deps_fn.return_value = mock_deps
        result = await update_project(project_id="proj-1", name="X")
        assert "not found" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_delete_project_success(self, mock_deps_fn):
        from second_brain.mcp_server import delete_project
        mock_deps = _mock_deps()
        mock_deps.storage_service.get_project = AsyncMock(
            return_value={"id": "proj-1", "name": "Old Campaign"}
        )
        mock_deps.storage_service.delete_project = AsyncMock(return_value=True)
        mock_deps_fn.return_value = mock_deps
        result = await delete_project(project_id="proj-1")
        assert "Deleted" in result
        assert "Old Campaign" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_delete_project_not_found(self, mock_deps_fn):
        from second_brain.mcp_server import delete_project
        mock_deps = _mock_deps()
        mock_deps.storage_service.get_project = AsyncMock(return_value=None)
        mock_deps_fn.return_value = mock_deps
        result = await delete_project(project_id="proj-nonexistent")
        assert "not found" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_add_artifact_success(self, mock_deps_fn):
        from second_brain.mcp_server import add_artifact
        mock_deps = _mock_deps()
        mock_deps.storage_service.add_project_artifact = AsyncMock(
            return_value={"id": "art-1", "artifact_type": "plan"}
        )
        mock_deps_fn.return_value = mock_deps
        result = await add_artifact(
            project_id="proj-1", artifact_type="plan", title="Feature Plan"
        )
        assert "plan" in result
        assert "art-1" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_add_artifact_invalid_type(self, mock_deps_fn):
        from second_brain.mcp_server import add_artifact
        mock_deps_fn.return_value = _mock_deps()
        result = await add_artifact(project_id="proj-1", artifact_type="invalid")
        assert "Invalid artifact_type" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_delete_artifact_success(self, mock_deps_fn):
        from second_brain.mcp_server import delete_artifact
        mock_deps = _mock_deps()
        mock_deps.storage_service.delete_project_artifact = AsyncMock(return_value=True)
        mock_deps_fn.return_value = mock_deps
        result = await delete_artifact(artifact_id="art-1")
        assert "Deleted" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_delete_artifact_not_found(self, mock_deps_fn):
        from second_brain.mcp_server import delete_artifact
        mock_deps = _mock_deps()
        mock_deps.storage_service.delete_project_artifact = AsyncMock(return_value=False)
        mock_deps_fn.return_value = mock_deps
        result = await delete_artifact(artifact_id="art-nonexistent")
        assert "not found" in result.lower()

    @patch("second_brain.mcp_server._get_deps")
    async def test_search_experiences_returns_results(self, mock_deps_fn):
        from second_brain.mcp_server import search_experiences
        mock_deps = _mock_deps()
        mock_deps.storage_service.get_experiences = AsyncMock(return_value=[
            {"id": "exp-1", "title": "Client Win", "category": "client-work",
             "date": "2026-02-01", "description": "Closed enterprise deal"},
        ])
        mock_deps_fn.return_value = mock_deps
        result = await search_experiences()
        assert "Client Win" in result
        assert "exp-1" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_search_experiences_empty(self, mock_deps_fn):
        from second_brain.mcp_server import search_experiences
        mock_deps = _mock_deps()
        mock_deps.storage_service.get_experiences = AsyncMock(return_value=[])
        mock_deps_fn.return_value = mock_deps
        result = await search_experiences(category="nonexistent")
        assert "No experiences found" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_search_patterns_with_keyword(self, mock_deps_fn):
        from second_brain.mcp_server import search_patterns
        mock_deps = _mock_deps()
        mock_deps.storage_service.get_patterns = AsyncMock(return_value=[
            {"id": "pat-1", "name": "Direct CTA Pattern", "confidence": "HIGH",
             "topic": "messaging", "pattern_text": "Use one clear call to action"},
            {"id": "pat-2", "name": "Story Arc", "confidence": "MEDIUM",
             "topic": "content", "pattern_text": "Open with conflict"},
        ])
        mock_deps_fn.return_value = mock_deps
        result = await search_patterns(keyword="cta")
        assert "Direct CTA Pattern" in result
        assert "Story Arc" not in result  # filtered out by keyword

    @patch("second_brain.mcp_server._get_deps")
    async def test_search_patterns_empty(self, mock_deps_fn):
        from second_brain.mcp_server import search_patterns
        mock_deps = _mock_deps()
        mock_deps.storage_service.get_patterns = AsyncMock(return_value=[])
        mock_deps_fn.return_value = mock_deps
        result = await search_patterns(topic="nonexistent")
        assert "No patterns found" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_ingest_example_success(self, mock_deps_fn):
        from second_brain.mcp_server import ingest_example
        mock_deps = _mock_deps()
        mock_deps.storage_service.upsert_example = AsyncMock(
            return_value={"id": "ex-new", "title": "Great LinkedIn Post"}
        )
        mock_deps_fn.return_value = mock_deps
        result = await ingest_example(
            content_type="linkedin",
            title="Great LinkedIn Post",
            content="We just hit 100 customers...",
        )
        assert "Great LinkedIn Post" in result
        assert "ex-new" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_ingest_example_empty_content(self, mock_deps_fn):
        from second_brain.mcp_server import ingest_example
        mock_deps_fn.return_value = _mock_deps()
        result = await ingest_example(
            content_type="linkedin",
            title="Valid Title",
            content="   ",  # whitespace only — validation should catch
        )
        assert "cannot be empty" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_ingest_knowledge_with_tags(self, mock_deps_fn):
        from second_brain.mcp_server import ingest_knowledge
        mock_deps = _mock_deps()
        mock_deps.storage_service.upsert_knowledge = AsyncMock(
            return_value={"id": "kn-new", "title": "Enterprise Buyer Profile"}
        )
        mock_deps_fn.return_value = mock_deps
        result = await ingest_knowledge(
            category="audience",
            title="Enterprise Buyer Profile",
            content="Our ICP is VP of Engineering...",
            tags="enterprise, b2b, technical",
        )
        assert "Enterprise Buyer Profile" in result
        # Verify tags were split (check the service call args)
        call_args = mock_deps.storage_service.upsert_knowledge.call_args[0][0]
        assert isinstance(call_args.get("tags"), list)
        assert "enterprise" in call_args["tags"]


class TestMultimodalMCPTools:
    """Tests for multimodal MCP tools."""

    @patch("second_brain.mcp_server._get_deps")
    async def test_learn_image_stores_to_memory(self, mock_deps_fn):
        from second_brain.mcp_server import learn_image

        deps = _mock_deps(
            memory_service=MagicMock(
                add_multimodal=AsyncMock(return_value={"id": "img-123"})
            ),
            embedding_service=None,
        )
        mock_deps_fn.return_value = deps

        result = await learn_image(
            image_url="https://example.com/photo.jpg",
            context="Team photo",
            category="visual",
        )
        assert "Learn Image" in result
        assert "Memory stored" in result
        deps.memory_service.add_multimodal.assert_awaited_once()

    @patch("second_brain.mcp_server._get_deps")
    async def test_learn_image_empty_url_returns_error(self, mock_deps_fn):
        from second_brain.mcp_server import learn_image

        result = await learn_image(image_url="", context="test")
        assert "cannot be empty" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_learn_document_pdf(self, mock_deps_fn):
        from second_brain.mcp_server import learn_document

        deps = _mock_deps(
            memory_service=MagicMock(
                add_multimodal=AsyncMock(return_value={"id": "doc-123"})
            ),
        )
        mock_deps_fn.return_value = deps

        result = await learn_document(
            document_url="https://example.com/report.pdf",
            document_type="pdf",
        )
        assert "Learn Document" in result
        assert "PDF" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_learn_document_invalid_type(self, mock_deps_fn):
        from second_brain.mcp_server import learn_document

        deps = _mock_deps()
        mock_deps_fn.return_value = deps

        result = await learn_document(
            document_url="https://example.com/file", document_type="xlsx"
        )
        assert "Invalid document_type" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_learn_document_empty_url(self, mock_deps_fn):
        from second_brain.mcp_server import learn_document

        result = await learn_document(document_url="")
        assert "cannot be empty" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_learn_video_requires_voyage(self, mock_deps_fn):
        from second_brain.mcp_server import learn_video

        deps = _mock_deps(embedding_service=None)
        mock_deps_fn.return_value = deps

        result = await learn_video(video_url="https://example.com/vid.mp4")
        assert "unavailable" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_learn_video_empty_url(self, mock_deps_fn):
        from second_brain.mcp_server import learn_video

        result = await learn_video(video_url="")
        assert "cannot be empty" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_multimodal_vector_search_with_text(self, mock_deps_fn):
        from second_brain.mcp_server import multimodal_vector_search

        mock_embedding = MagicMock()
        mock_embedding.embed_multimodal = AsyncMock(return_value=[[0.1] * 1024])
        mock_storage = MagicMock()
        mock_storage.vector_search = AsyncMock(return_value=[
            {"title": "Test Pattern", "content": "Found content", "similarity": 0.85}
        ])
        deps = _mock_deps(
            embedding_service=mock_embedding,
            storage_service=mock_storage,
        )
        mock_deps_fn.return_value = deps

        result = await multimodal_vector_search(query="test query", table="patterns")
        assert "Multimodal Search" in result
        assert "Test Pattern" in result
        assert "0.850" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_multimodal_search_requires_input(self, mock_deps_fn):
        from second_brain.mcp_server import multimodal_vector_search

        result = await multimodal_vector_search(query="", image_url="")
        assert "Provide at least one" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_multimodal_search_no_embedding_service(self, mock_deps_fn):
        from second_brain.mcp_server import multimodal_vector_search

        deps = _mock_deps(embedding_service=None)
        mock_deps_fn.return_value = deps

        result = await multimodal_vector_search(query="test")
        assert "unavailable" in result


class TestOperationsMCPTools:
    """Tests for the 9 previously untested operation/pipeline MCP tools."""

    # --- advance_project (service-direct) ---

    @patch("second_brain.mcp_server._get_deps")
    async def test_advance_project_success(self, mock_deps_fn):
        from second_brain.mcp_server import advance_project

        mock_deps = _mock_deps()
        mock_deps.storage_service.get_project = AsyncMock(
            return_value={"id": "proj-1", "name": "My Project", "lifecycle_stage": "planning"}
        )
        mock_deps.storage_service.update_project_stage = AsyncMock(
            return_value={"id": "proj-1", "lifecycle_stage": "executing"}
        )
        mock_deps_fn.return_value = mock_deps

        result = await advance_project(project_id="proj-1")
        assert "My Project" in result
        assert "planning" in result
        assert "executing" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_advance_project_empty_input(self, mock_deps_fn):
        from second_brain.mcp_server import advance_project

        result = await advance_project(project_id="")
        assert "cannot be empty" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_advance_project_not_found(self, mock_deps_fn):
        from second_brain.mcp_server import advance_project

        mock_deps = _mock_deps()
        mock_deps.storage_service.get_project = AsyncMock(return_value=None)
        mock_deps_fn.return_value = mock_deps

        result = await advance_project(project_id="nonexistent")
        assert "not found" in result.lower()

    # --- coaching_session ---

    @patch("second_brain.mcp_server._get_model")
    @patch("second_brain.mcp_server._get_deps")
    async def test_coaching_session_success(self, mock_deps_fn, mock_model_fn):
        from second_brain.mcp_server import coaching_session

        with patch("second_brain.agents.coach.coach_agent") as mock_agent:
            mock_result = MagicMock()
            mock_result.output = CoachSession(
                session_type="morning",
                next_action="Start with top priority",
                coaching_notes="Stay focused today",
            )
            mock_agent.run = AsyncMock(return_value=mock_result)
            mock_deps_fn.return_value = _mock_deps()
            mock_model_fn.return_value = MagicMock()

            result = await coaching_session(request="Help me plan today")
            assert isinstance(result, str)
            assert "morning" in result.lower()

    @patch("second_brain.mcp_server._get_model")
    @patch("second_brain.mcp_server._get_deps")
    async def test_coaching_session_empty_input(self, mock_deps_fn, mock_model_fn):
        from second_brain.mcp_server import coaching_session

        result = await coaching_session(request="")
        assert "cannot be empty" in result

    @patch("second_brain.mcp_server._get_model")
    @patch("second_brain.mcp_server._get_deps")
    async def test_coaching_session_timeout(self, mock_deps_fn, mock_model_fn):
        from second_brain.mcp_server import coaching_session

        with patch("second_brain.agents.coach.coach_agent") as mock_agent:
            mock_agent.run = AsyncMock(side_effect=TimeoutError())
            mock_deps_fn.return_value = _mock_deps()
            mock_model_fn.return_value = MagicMock()

            result = await coaching_session(request="test")
            assert "timed out" in result.lower()

    # --- prioritize_tasks ---

    @patch("second_brain.mcp_server._get_model")
    @patch("second_brain.mcp_server._get_deps")
    async def test_prioritize_tasks_success(self, mock_deps_fn, mock_model_fn):
        from second_brain.mcp_server import prioritize_tasks

        with patch("second_brain.agents.pmo.pmo_agent") as mock_agent:
            mock_result = MagicMock()
            mock_result.output = PMOResult(
                coaching_message="Focus on high-impact tasks",
                scored_tasks=[
                    PriorityScore(task_name="Write tests", total_score=85.0, category="development"),
                ],
            )
            mock_agent.run = AsyncMock(return_value=mock_result)
            mock_deps_fn.return_value = _mock_deps()
            mock_model_fn.return_value = MagicMock()

            result = await prioritize_tasks(tasks="Write tests, Fix bugs")
            assert isinstance(result, str)
            assert "Write tests" in result

    @patch("second_brain.mcp_server._get_model")
    @patch("second_brain.mcp_server._get_deps")
    async def test_prioritize_tasks_empty_input(self, mock_deps_fn, mock_model_fn):
        from second_brain.mcp_server import prioritize_tasks

        result = await prioritize_tasks(tasks="")
        assert "cannot be empty" in result

    @patch("second_brain.mcp_server._get_model")
    @patch("second_brain.mcp_server._get_deps")
    async def test_prioritize_tasks_timeout(self, mock_deps_fn, mock_model_fn):
        from second_brain.mcp_server import prioritize_tasks

        with patch("second_brain.agents.pmo.pmo_agent") as mock_agent:
            mock_agent.run = AsyncMock(side_effect=TimeoutError())
            mock_deps_fn.return_value = _mock_deps()
            mock_model_fn.return_value = MagicMock()

            result = await prioritize_tasks(tasks="task1, task2")
            assert "timed out" in result.lower()

    # --- compose_email ---

    @patch("second_brain.mcp_server._get_model")
    @patch("second_brain.mcp_server._get_deps")
    async def test_compose_email_success(self, mock_deps_fn, mock_model_fn):
        from second_brain.mcp_server import compose_email

        with patch("second_brain.agents.email_agent.email_agent") as mock_agent:
            mock_result = MagicMock()
            mock_result.output = EmailAction(
                action_type="draft",
                subject="Follow-up on proposal",
                body="Hi John, following up on our conversation...",
                status="draft",
            )
            mock_agent.run = AsyncMock(return_value=mock_result)
            mock_deps_fn.return_value = _mock_deps()
            mock_model_fn.return_value = MagicMock()

            result = await compose_email(request="Draft follow-up to John")
            assert "Subject:" in result
            assert "Follow-up" in result

    @patch("second_brain.mcp_server._get_model")
    @patch("second_brain.mcp_server._get_deps")
    async def test_compose_email_empty_input(self, mock_deps_fn, mock_model_fn):
        from second_brain.mcp_server import compose_email

        result = await compose_email(request="")
        assert "cannot be empty" in result

    @patch("second_brain.mcp_server._get_model")
    @patch("second_brain.mcp_server._get_deps")
    async def test_compose_email_timeout(self, mock_deps_fn, mock_model_fn):
        from second_brain.mcp_server import compose_email

        with patch("second_brain.agents.email_agent.email_agent") as mock_agent:
            mock_agent.run = AsyncMock(side_effect=TimeoutError())
            mock_deps_fn.return_value = _mock_deps()
            mock_model_fn.return_value = MagicMock()

            result = await compose_email(request="test email")
            assert "timed out" in result.lower()

    # --- ask_claude_specialist ---

    @patch("second_brain.mcp_server._get_model")
    @patch("second_brain.mcp_server._get_deps")
    async def test_ask_claude_specialist_success(self, mock_deps_fn, mock_model_fn):
        from second_brain.mcp_server import ask_claude_specialist

        with patch("second_brain.agents.specialist.specialist_agent") as mock_agent:
            mock_result = MagicMock()
            mock_result.output = SpecialistAnswer(
                answer="Use the Agent class with deps_type parameter.",
                confidence_level="VERIFIED",
            )
            mock_agent.run = AsyncMock(return_value=mock_result)
            mock_deps_fn.return_value = _mock_deps()
            mock_model_fn.return_value = MagicMock()

            result = await ask_claude_specialist(question="How to create a Pydantic AI agent?")
            assert "VERIFIED" in result
            assert "Agent class" in result

    @patch("second_brain.mcp_server._get_model")
    @patch("second_brain.mcp_server._get_deps")
    async def test_ask_claude_specialist_empty_input(self, mock_deps_fn, mock_model_fn):
        from second_brain.mcp_server import ask_claude_specialist

        result = await ask_claude_specialist(question="")
        assert "cannot be empty" in result

    @patch("second_brain.mcp_server._get_model")
    @patch("second_brain.mcp_server._get_deps")
    async def test_ask_claude_specialist_timeout(self, mock_deps_fn, mock_model_fn):
        from second_brain.mcp_server import ask_claude_specialist

        with patch("second_brain.agents.specialist.specialist_agent") as mock_agent:
            mock_agent.run = AsyncMock(side_effect=TimeoutError())
            mock_deps_fn.return_value = _mock_deps()
            mock_model_fn.return_value = MagicMock()

            result = await ask_claude_specialist(question="test question")
            assert "timed out" in result.lower()

    # --- run_brain_pipeline ---

    @patch("second_brain.mcp_server._get_model")
    @patch("second_brain.mcp_server._get_deps")
    async def test_run_brain_pipeline_with_steps(self, mock_deps_fn, mock_model_fn):
        from second_brain.mcp_server import run_brain_pipeline

        with patch("second_brain.agents.utils.run_pipeline") as mock_pipeline:
            mock_pipeline.return_value = {"final": "Pipeline output result"}
            mock_deps_fn.return_value = _mock_deps()
            mock_model_fn.return_value = MagicMock()

            result = await run_brain_pipeline(request="Analyze my content", steps="recall,create")
            assert "Pipeline output result" in result

    @patch("second_brain.mcp_server._get_model")
    @patch("second_brain.mcp_server._get_deps")
    async def test_run_brain_pipeline_empty_input(self, mock_deps_fn, mock_model_fn):
        from second_brain.mcp_server import run_brain_pipeline

        result = await run_brain_pipeline(request="")
        assert "cannot be empty" in result

    @patch("second_brain.mcp_server._get_model")
    @patch("second_brain.mcp_server._get_deps")
    async def test_run_brain_pipeline_timeout(self, mock_deps_fn, mock_model_fn):
        from second_brain.mcp_server import run_brain_pipeline

        with patch("second_brain.agents.chief_of_staff.chief_of_staff") as mock_cos:
            mock_cos.run = AsyncMock(side_effect=TimeoutError())
            mock_deps_fn.return_value = _mock_deps()
            mock_model_fn.return_value = MagicMock()

            result = await run_brain_pipeline(request="test pipeline")
            assert "timed out" in result.lower()

    # --- analyze_clarity ---

    @patch("second_brain.mcp_server._get_model")
    @patch("second_brain.mcp_server._get_deps")
    async def test_analyze_clarity_success(self, mock_deps_fn, mock_model_fn):
        from second_brain.mcp_server import analyze_clarity

        with patch("second_brain.agents.clarity.clarity_agent") as mock_agent:
            mock_result = MagicMock()
            mock_result.output = ClarityResult(
                overall_readability="HIGH",
                critical_count=1,
                findings=[
                    ClarityFinding(
                        severity="CRITICAL",
                        location="Paragraph 1",
                        issue="Run-on sentence",
                        suggestion="Split into two sentences",
                    ),
                ],
            )
            mock_agent.run = AsyncMock(return_value=mock_result)
            mock_deps_fn.return_value = _mock_deps()
            mock_model_fn.return_value = MagicMock()

            result = await analyze_clarity(content="Some content to analyze")
            assert "HIGH" in result
            assert "critical" in result.lower()

    @patch("second_brain.mcp_server._get_model")
    @patch("second_brain.mcp_server._get_deps")
    async def test_analyze_clarity_empty_input(self, mock_deps_fn, mock_model_fn):
        from second_brain.mcp_server import analyze_clarity

        result = await analyze_clarity(content="")
        assert "cannot be empty" in result

    @patch("second_brain.mcp_server._get_model")
    @patch("second_brain.mcp_server._get_deps")
    async def test_analyze_clarity_timeout(self, mock_deps_fn, mock_model_fn):
        from second_brain.mcp_server import analyze_clarity

        with patch("second_brain.agents.clarity.clarity_agent") as mock_agent:
            mock_agent.run = AsyncMock(side_effect=TimeoutError())
            mock_deps_fn.return_value = _mock_deps()
            mock_model_fn.return_value = MagicMock()

            result = await analyze_clarity(content="test content")
            assert "timed out" in result.lower()

    # --- synthesize_feedback ---

    @patch("second_brain.mcp_server._get_model")
    @patch("second_brain.mcp_server._get_deps")
    async def test_synthesize_feedback_success(self, mock_deps_fn, mock_model_fn):
        from second_brain.mcp_server import synthesize_feedback

        with patch("second_brain.agents.synthesizer.synthesizer_agent") as mock_agent:
            mock_result = MagicMock()
            mock_result.output = SynthesizerResult(
                total_themes_output=2,
                implementation_hours=3.5,
                themes=[
                    SynthesizerTheme(
                        priority="HIGH",
                        title="Improve clarity",
                        effort_minutes=90,
                        action="Rewrite introduction",
                    ),
                ],
            )
            mock_agent.run = AsyncMock(return_value=mock_result)
            mock_deps_fn.return_value = _mock_deps()
            mock_model_fn.return_value = MagicMock()

            result = await synthesize_feedback(findings="Review findings here")
            assert "2 themes" in result
            assert "3.5h" in result
            assert "Improve clarity" in result

    @patch("second_brain.mcp_server._get_model")
    @patch("second_brain.mcp_server._get_deps")
    async def test_synthesize_feedback_empty_input(self, mock_deps_fn, mock_model_fn):
        from second_brain.mcp_server import synthesize_feedback

        result = await synthesize_feedback(findings="")
        assert "cannot be empty" in result

    @patch("second_brain.mcp_server._get_model")
    @patch("second_brain.mcp_server._get_deps")
    async def test_synthesize_feedback_timeout(self, mock_deps_fn, mock_model_fn):
        from second_brain.mcp_server import synthesize_feedback

        with patch("second_brain.agents.synthesizer.synthesizer_agent") as mock_agent:
            mock_agent.run = AsyncMock(side_effect=TimeoutError())
            mock_deps_fn.return_value = _mock_deps()
            mock_model_fn.return_value = MagicMock()

            result = await synthesize_feedback(findings="test")
            assert "timed out" in result.lower()

    # --- find_template_opportunities ---

    @patch("second_brain.mcp_server._get_model")
    @patch("second_brain.mcp_server._get_deps")
    async def test_find_template_opportunities_success(self, mock_deps_fn, mock_model_fn):
        from second_brain.mcp_server import find_template_opportunities

        with patch("second_brain.agents.template_builder.template_builder_agent") as mock_agent:
            mock_result = MagicMock()
            mock_result.output = TemplateBuilderResult(
                templates_created=2,
                opportunities=[
                    TemplateOpportunity(
                        name="Blog Post Template",
                        when_to_use="For weekly blog content",
                        source_deliverable="blog post about AI",
                        structure="Introduction -> Body -> Conclusion",
                    ),
                ],
            )
            mock_agent.run = AsyncMock(return_value=mock_result)
            mock_deps_fn.return_value = _mock_deps()
            mock_model_fn.return_value = MagicMock()

            result = await find_template_opportunities(deliverable="A blog post about AI")
            assert "2 template" in result
            assert "Blog Post Template" in result

    @patch("second_brain.mcp_server._get_model")
    @patch("second_brain.mcp_server._get_deps")
    async def test_find_template_opportunities_empty_input(self, mock_deps_fn, mock_model_fn):
        from second_brain.mcp_server import find_template_opportunities

        result = await find_template_opportunities(deliverable="")
        assert "cannot be empty" in result

    @patch("second_brain.mcp_server._get_model")
    @patch("second_brain.mcp_server._get_deps")
    async def test_find_template_opportunities_timeout(self, mock_deps_fn, mock_model_fn):
        from second_brain.mcp_server import find_template_opportunities

        with patch("second_brain.agents.template_builder.template_builder_agent") as mock_agent:
            mock_agent.run = AsyncMock(side_effect=TimeoutError())
            mock_deps_fn.return_value = _mock_deps()
            mock_model_fn.return_value = MagicMock()

            result = await find_template_opportunities(deliverable="test")
            assert "timed out" in result.lower()


class TestPerAgentModel:
    """Smoke tests for per-agent model selection in MCP tools."""

    @patch("second_brain.mcp_server._get_model")
    @patch("second_brain.mcp_server._get_deps")
    @patch("second_brain.mcp_server.recall_agent")
    async def test_recall_passes_agent_name(self, mock_agent, mock_deps_fn, mock_model_fn):
        """recall tool calls _get_model('recall')."""
        from second_brain.mcp_server import recall

        mock_result = MagicMock()
        mock_result.output = RecallResult(
            query="test",
            matches=[],
            patterns=[],
            summary="No matches.",
        )
        mock_agent.run = AsyncMock(return_value=mock_result)
        mock_deps_fn.return_value = _mock_deps()
        mock_model_fn.return_value = MagicMock()

        await recall(query="test")

        mock_model_fn.assert_called_with("recall")

    @patch("second_brain.mcp_server._get_model")
    @patch("second_brain.mcp_server._get_deps")
    @patch("second_brain.mcp_server.ask_agent")
    async def test_ask_passes_agent_name(self, mock_agent, mock_deps_fn, mock_model_fn):
        """ask tool calls _get_model('ask')."""
        from second_brain.mcp_server import ask

        mock_result = MagicMock()
        mock_result.output = AskResult(
            answer="Test answer.",
            confidence="HIGH",
            sources=[],
        )
        mock_agent.run = AsyncMock(return_value=mock_result)
        mock_deps_fn.return_value = _mock_deps()
        mock_model_fn.return_value = MagicMock()

        await ask(question="test?")

        mock_model_fn.assert_called_with("ask")


class TestToolDescriptionQuality:
    """Verify all MCP tool descriptions follow quality standards."""

    def _get_tools(self):
        from second_brain.mcp_server import server
        return server._tool_manager._tools

    def test_all_tools_have_descriptions(self):
        """Every tool must have a non-empty description."""
        tools = self._get_tools()
        for name, tool in tools.items():
            desc = tool.description or ""
            assert len(desc) > 20, f"Tool '{name}' has too-short description: {desc[:50]}"

    def test_all_tools_have_when_to_use(self):
        """Every tool description should include 'When to use' guidance."""
        tools = self._get_tools()
        missing = []
        for name, tool in tools.items():
            desc = (tool.description or "").lower()
            if "when to use" not in desc:
                missing.append(name)
        assert not missing, f"Tools missing 'When to use': {missing}"

    def test_recall_tools_differentiated(self):
        """recall, quick_recall, and recall_deep should have distinct descriptions."""
        tools = self._get_tools()
        recall_desc = tools["recall"].description or ""
        quick_desc = tools["quick_recall"].description or ""
        assert "agent" in recall_desc.lower() or "llm" in recall_desc.lower()
        assert "fast" in quick_desc.lower() or "parallel" in quick_desc.lower()
        if "recall_deep" in tools:
            deep_desc = tools["recall_deep"].description or ""
            assert "parallel" in deep_desc.lower() or "all" in deep_desc.lower()

    def test_search_tools_differentiated(self):
        """Search tools should explain when to use each one."""
        tools = self._get_tools()
        for name in ["search_examples", "search_knowledge", "search_patterns",
                     "search_experiences", "vector_search"]:
            if name in tools:
                desc = (tools[name].description or "").lower()
                assert "when to use" in desc, f"'{name}' missing When-to-use"

    def test_descriptions_start_with_action_verb(self):
        """Tool descriptions should start with an action verb, not 'This tool'."""
        tools = self._get_tools()
        bad_starts = []
        for name, tool in tools.items():
            desc = (tool.description or "").strip()
            if desc.lower().startswith("this tool"):
                bad_starts.append(name)
        assert not bad_starts, f"Tools starting with 'This tool': {bad_starts}"

    def test_no_empty_descriptions(self):
        """No tool should have an empty or None description."""
        tools = self._get_tools()
        empty = [name for name, tool in tools.items()
                 if not (tool.description or "").strip()]
        assert not empty, f"Tools with empty descriptions: {empty}"


class TestQuickRecallExceptionHandler:
    """Tests that quick_recall handles unexpected exceptions gracefully."""

    @patch("second_brain.mcp_server._deps_failed", False)
    @patch("second_brain.mcp_server._get_deps")
    async def test_unexpected_exception_returns_error_string(self, mock_deps_fn):
        """General exceptions return a user-friendly error string, not crash."""
        from second_brain.mcp_server import quick_recall

        deps = _mock_deps()
        deps.memory_service = MagicMock()
        # Trigger RuntimeError inside the try block (during search)
        deps.memory_service.search = AsyncMock(side_effect=RuntimeError("unexpected"))
        deps.embedding_service = None
        deps.voyage_service = None
        mock_deps_fn.return_value = deps

        result = await quick_recall(query="test query")
        assert isinstance(result, str)
        assert "error" in result.lower() or "RuntimeError" in result

    @patch("second_brain.mcp_server._deps_failed", False)
    @patch("second_brain.mcp_server._get_deps")
    async def test_timeout_returns_timeout_message(self, mock_deps_fn):
        """TimeoutError returns specific timeout message."""
        from second_brain.mcp_server import quick_recall

        deps = _mock_deps()
        deps.config.api_timeout_seconds = 0.001
        deps.memory_service = MagicMock()
        deps.memory_service.search = AsyncMock(side_effect=TimeoutError())
        deps.embedding_service = None
        deps.voyage_service = None
        mock_deps_fn.return_value = deps

        result = await quick_recall(query="test query")
        assert isinstance(result, str)
        assert "timed out" in result.lower() or "error" in result.lower()


class TestMultimodalVectorSearchExceptionHandler:
    """Tests that multimodal_vector_search handles unexpected exceptions."""

    @patch("second_brain.mcp_server._deps_failed", False)
    @patch("second_brain.mcp_server._get_deps")
    async def test_unexpected_exception_returns_error_string(self, mock_deps_fn):
        from second_brain.mcp_server import multimodal_vector_search

        deps = _mock_deps()
        deps.embedding_service = MagicMock()
        deps.embedding_service.embed_multimodal = AsyncMock(
            side_effect=RuntimeError("GPU error")
        )
        mock_deps_fn.return_value = deps

        result = await multimodal_vector_search(query="test")
        assert isinstance(result, str)
        assert "error" in result.lower() or "RuntimeError" in result

    @patch("second_brain.mcp_server._deps_failed", False)
    @patch("second_brain.mcp_server._get_deps")
    async def test_timeout_returns_timeout_message(self, mock_deps_fn):
        from second_brain.mcp_server import multimodal_vector_search

        deps = _mock_deps()
        deps.config.api_timeout_seconds = 0.001
        deps.embedding_service = MagicMock()
        deps.embedding_service.embed_multimodal = AsyncMock(
            side_effect=TimeoutError()
        )
        mock_deps_fn.return_value = deps

        result = await multimodal_vector_search(query="test")
        assert isinstance(result, str)
        assert "timed out" in result.lower()


class TestRunBrainPipelineTimeout:
    """Tests that run_brain_pipeline handles timeouts."""

    @patch("second_brain.mcp_server._get_model")
    @patch("second_brain.mcp_server._get_deps")
    async def test_pipeline_timeout_returns_message(self, mock_deps_fn, mock_model_fn):
        from second_brain.mcp_server import run_brain_pipeline

        deps = _mock_deps()
        deps.config.api_timeout_seconds = 0.001
        mock_deps_fn.return_value = deps
        mock_model_fn.return_value = MagicMock()

        with patch("second_brain.agents.utils.run_pipeline", new_callable=AsyncMock) as mock_pipeline:
            mock_pipeline.side_effect = TimeoutError()
            result = await run_brain_pipeline(request="test", steps="recall,create")
            assert isinstance(result, str)
            assert "timed out" in result.lower() or "Pipeline" in result


class TestLearnImageImportError:
    """Tests that learn_image handles PIL ImportError."""

    @patch("second_brain.mcp_server._get_deps")
    async def test_pil_import_error_returns_actionable_message(self, mock_deps_fn):
        from second_brain.mcp_server import learn_image

        deps = _mock_deps(
            memory_service=MagicMock(
                add_multimodal=AsyncMock(return_value={"id": "img-123"})
            ),
            embedding_service=MagicMock(),
        )
        mock_deps_fn.return_value = deps

        with patch.dict("sys.modules", {"PIL": None, "PIL.Image": None}):
            result = await learn_image(
                image_url="data:image/png;base64,iVBORw0KGgoAAAANS",
                context="Test image",
            )
        assert isinstance(result, str)
        # Should contain either the PIL error message or still succeed with embedding skipped
        assert "Learn Image" in result
