"""Tests for agent schemas and registration."""

import pytest
from unittest.mock import MagicMock, AsyncMock

from second_brain.schemas import (
    RecallResult, AskResult, MemoryMatch, LearnResult, PatternExtract,
)


class TestSchemas:
    def test_recall_result_with_matches(self):
        result = RecallResult(
            query="test",
            matches=[MemoryMatch(content="test memory", source="mem0")],
            patterns=["Test Pattern"],
            summary="Found one match.",
        )
        assert len(result.matches) == 1
        assert result.matches[0].content == "test memory"
        assert result.matches[0].source == "mem0"

    def test_recall_result_defaults(self):
        result = RecallResult(query="empty search")
        assert result.matches == []
        assert result.patterns == []
        assert result.summary == ""

    def test_memory_match_defaults(self):
        match = MemoryMatch(content="some content")
        assert match.source == ""
        assert match.relevance == "MEDIUM"

    def test_ask_result(self):
        result = AskResult(
            answer="Here's your answer.",
            context_used=["company/products"],
            patterns_applied=["Short > Structured"],
            confidence="HIGH",
        )
        assert result.confidence == "HIGH"
        assert result.answer == "Here's your answer."

    def test_ask_result_defaults(self):
        result = AskResult(answer="Minimal answer.")
        assert result.context_used == []
        assert result.patterns_applied == []
        assert result.confidence == "MEDIUM"
        assert result.next_action == ""


class TestRecallAgent:
    def test_agent_exists(self):
        from second_brain.agents.recall import recall_agent
        assert recall_agent is not None

    def test_agent_output_type(self):
        from second_brain.agents.recall import recall_agent
        assert recall_agent.output_type is RecallResult

    def test_agent_has_tools(self):
        from second_brain.agents.recall import recall_agent
        tool_names = list(recall_agent._function_toolset.tools)
        assert "search_semantic_memory" in tool_names
        assert "search_patterns" in tool_names
        assert "search_experiences" in tool_names
        assert "search_examples" in tool_names

    def test_agent_has_examples_tool(self):
        from second_brain.agents.recall import recall_agent
        tool_names = list(recall_agent._function_toolset.tools.keys())
        assert "search_examples" in tool_names


class TestAskAgent:
    def test_agent_exists(self):
        from second_brain.agents.ask import ask_agent
        assert ask_agent is not None

    def test_agent_output_type(self):
        from second_brain.agents.ask import ask_agent
        assert ask_agent.output_type is AskResult

    def test_agent_has_tools(self):
        from second_brain.agents.ask import ask_agent
        tool_names = list(ask_agent._function_toolset.tools)
        assert "load_brain_context" in tool_names
        assert "find_relevant_patterns" in tool_names
        assert "find_similar_experiences" in tool_names
        assert "search_knowledge" in tool_names

    def test_agent_has_knowledge_tool(self):
        from second_brain.agents.ask import ask_agent
        tool_names = list(ask_agent._function_toolset.tools.keys())
        assert "search_knowledge" in tool_names


class TestLearnResult:
    def test_learn_result_defaults(self):
        result = LearnResult(input_summary="test")
        assert result.patterns_extracted == []
        assert result.insights == []
        assert result.experience_recorded is False
        assert result.patterns_new == 0
        assert result.patterns_reinforced == 0

    def test_pattern_extract_fields(self):
        pattern = PatternExtract(
            name="Test Pattern",
            topic="Process",
            pattern_text="Always test first",
            evidence=["Worked in project X"],
        )
        assert pattern.confidence == "LOW"
        assert pattern.is_reinforcement is False
        assert pattern.existing_pattern_name == ""

    def test_learn_result_with_patterns(self):
        pattern = PatternExtract(
            name="Test",
            topic="Content",
            pattern_text="Write concisely",
        )
        result = LearnResult(
            input_summary="Session notes",
            patterns_extracted=[pattern],
            patterns_new=1,
            storage_summary="1 pattern stored",
        )
        assert len(result.patterns_extracted) == 1
        assert result.patterns_new == 1


class TestLearnAgent:
    def test_agent_exists(self):
        from second_brain.agents.learn import learn_agent
        assert learn_agent is not None

    def test_agent_output_type(self):
        from second_brain.agents.learn import learn_agent
        assert learn_agent.output_type is LearnResult

    def test_agent_has_tools(self):
        from second_brain.agents.learn import learn_agent
        tool_names = list(learn_agent._function_toolset.tools)
        assert "search_existing_patterns" in tool_names
        assert "store_pattern" in tool_names
        assert "add_to_memory" in tool_names
        assert "store_experience" in tool_names

    def test_agent_has_dynamic_instructions(self):
        from second_brain.agents.learn import learn_agent
        # @agent.instructions appends callables to _instructions list
        dynamic = [i for i in learn_agent._instructions if callable(i)]
        assert len(dynamic) > 0


class TestPatternReinforcement:
    def test_learn_agent_has_reinforce_tool(self):
        from second_brain.agents.learn import learn_agent
        tool_names = list(learn_agent._function_toolset.tools)
        assert "reinforce_existing_pattern" in tool_names

    def test_reinforce_pattern_tool_exists(self):
        from second_brain.agents.learn import learn_agent
        tools = learn_agent._function_toolset.tools
        assert "reinforce_existing_pattern" in tools
        assert "store_pattern" in tools

    async def test_reinforce_tool_calls_storage_methods(self, mock_deps):
        from second_brain.agents.learn import learn_agent
        mock_deps.storage_service.get_pattern_by_name = AsyncMock(return_value={
            "id": "uuid-1", "name": "Short > Structured", "use_count": 2,
        })
        mock_deps.storage_service.reinforce_pattern = AsyncMock(return_value={
            "id": "uuid-1", "name": "Short > Structured",
            "use_count": 3, "confidence": "MEDIUM",
        })
        tool_fn = learn_agent._function_toolset.tools["reinforce_existing_pattern"]
        mock_ctx = MagicMock()
        mock_ctx.deps = mock_deps
        result = await tool_fn.function(mock_ctx, pattern_name="Short > Structured", new_evidence=["e1"])
        mock_deps.storage_service.get_pattern_by_name.assert_called_once_with("Short > Structured")
        mock_deps.storage_service.reinforce_pattern.assert_called_once_with("uuid-1", ["e1"])
        assert "use_count: 3" in result
        assert "MEDIUM" in result

    async def test_reinforce_tool_pattern_not_found(self, mock_deps):
        from second_brain.agents.learn import learn_agent
        mock_deps.storage_service.get_pattern_by_name = AsyncMock(return_value=None)
        tool_fn = learn_agent._function_toolset.tools["reinforce_existing_pattern"]
        mock_ctx = MagicMock()
        mock_ctx.deps = mock_deps
        result = await tool_fn.function(mock_ctx, pattern_name="Nonexistent")
        assert "No existing pattern" in result
        assert "store_pattern" in result
        mock_deps.storage_service.reinforce_pattern.assert_not_called()

    async def test_reinforce_tool_handles_value_error(self, mock_deps):
        from second_brain.agents.learn import learn_agent
        mock_deps.storage_service.get_pattern_by_name = AsyncMock(return_value={
            "id": "uuid-1", "name": "Test",
        })
        mock_deps.storage_service.reinforce_pattern = AsyncMock(
            side_effect=ValueError("not found"),
        )
        tool_fn = learn_agent._function_toolset.tools["reinforce_existing_pattern"]
        mock_ctx = MagicMock()
        mock_ctx.deps = mock_deps
        result = await tool_fn.function(mock_ctx, pattern_name="Test")
        assert "Error" in result

    async def test_store_pattern_guards_duplicate(self, mock_deps):
        from second_brain.agents.learn import learn_agent
        mock_deps.storage_service.get_pattern_by_name = AsyncMock(return_value={
            "id": "uuid-1", "name": "Existing", "use_count": 2, "confidence": "MEDIUM",
        })
        tool_fn = learn_agent._function_toolset.tools["store_pattern"]
        mock_ctx = MagicMock()
        mock_ctx.deps = mock_deps
        result = await tool_fn.function(
            mock_ctx, name="Existing", topic="Test",
            pattern_text="text", confidence="LOW",
        )
        assert "already exists" in result
        assert "reinforce_existing_pattern" in result
        mock_deps.storage_service.insert_pattern.assert_not_called()

    async def test_store_pattern_creates_new(self, mock_deps):
        from second_brain.agents.learn import learn_agent
        mock_deps.storage_service.get_pattern_by_name = AsyncMock(return_value=None)
        mock_deps.storage_service.insert_pattern = AsyncMock(return_value={
            "id": "uuid-new", "name": "New Pattern",
        })
        tool_fn = learn_agent._function_toolset.tools["store_pattern"]
        mock_ctx = MagicMock()
        mock_ctx.deps = mock_deps
        result = await tool_fn.function(
            mock_ctx, name="New Pattern", topic="Test",
            pattern_text="text", confidence="LOW",
        )
        assert "Stored new pattern" in result
        mock_deps.storage_service.insert_pattern.assert_called_once()

    def test_confidence_type_validation(self):
        with pytest.raises(Exception):
            PatternExtract(
                name="test", topic="t", pattern_text="p",
                confidence="INVALID",
            )

    def test_confidence_type_accepts_valid(self):
        for level in ("LOW", "MEDIUM", "HIGH"):
            p = PatternExtract(
                name="test", topic="t", pattern_text="p", confidence=level,
            )
            assert p.confidence == level
