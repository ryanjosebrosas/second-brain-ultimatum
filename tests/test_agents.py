"""Tests for agent schemas and registration."""

from second_brain.schemas import RecallResult, AskResult, MemoryMatch


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
