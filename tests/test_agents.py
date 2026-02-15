"""Tests for agent schemas and registration."""

import pytest
from unittest.mock import MagicMock, AsyncMock

from second_brain.schemas import (
    RecallResult, AskResult, MemoryMatch, LearnResult, PatternExtract,
    CreateResult, ContentTypeConfig, CONTENT_TYPES,
    DimensionScore, ReviewResult, REVIEW_DIMENSIONS,
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


class TestCreateResultSchema:
    def test_create_result_defaults(self):
        result = CreateResult(
            draft="Test draft content",
            content_type="linkedin",
            mode="casual",
        )
        assert result.draft == "Test draft content"
        assert result.content_type == "linkedin"
        assert result.mode == "casual"
        assert result.voice_elements == []
        assert result.patterns_applied == []
        assert result.examples_referenced == []
        assert result.word_count == 0
        assert result.notes == ""

    def test_create_result_full(self):
        result = CreateResult(
            draft="Full draft here",
            content_type="email",
            mode="professional",
            voice_elements=["direct", "concise"],
            patterns_applied=["Hook First"],
            examples_referenced=["Q4 Update Email"],
            word_count=150,
            notes="Check the CTA wording",
        )
        assert len(result.voice_elements) == 2
        assert len(result.patterns_applied) == 1
        assert result.word_count == 150
        assert result.notes == "Check the CTA wording"

    def test_content_type_config(self):
        config = ContentTypeConfig(
            name="Test Type",
            default_mode="casual",
            structure_hint="Intro -> Body -> Close",
            example_type="test",
        )
        assert config.name == "Test Type"
        assert config.max_words == 0
        assert config.description == ""

    def test_content_types_registry(self):
        assert "linkedin" in CONTENT_TYPES
        assert "email" in CONTENT_TYPES
        assert "landing-page" in CONTENT_TYPES
        assert "comment" in CONTENT_TYPES
        assert len(CONTENT_TYPES) == 4

    def test_content_type_defaults(self):
        linkedin = CONTENT_TYPES["linkedin"]
        assert linkedin.default_mode == "casual"
        assert linkedin.max_words == 300
        email = CONTENT_TYPES["email"]
        assert email.default_mode == "professional"


class TestCreateAgent:
    def test_agent_exists(self):
        from second_brain.agents.create import create_agent
        assert create_agent is not None

    def test_agent_output_type(self):
        from second_brain.agents.create import create_agent
        assert create_agent.output_type is CreateResult

    def test_agent_has_tools(self):
        from second_brain.agents.create import create_agent
        tool_names = list(create_agent._function_toolset.tools)
        assert "load_voice_guide" in tool_names
        assert "load_content_examples" in tool_names
        assert "find_applicable_patterns" in tool_names
        assert "load_audience_context" in tool_names

    def test_agent_exported_from_package(self):
        from second_brain.agents import create_agent
        assert create_agent is not None


class TestDimensionScoreSchema:
    def test_dimension_score_defaults(self):
        score = DimensionScore(dimension="Messaging", score=8, status="pass")
        assert score.dimension == "Messaging"
        assert score.score == 8
        assert score.status == "pass"
        assert score.strengths == []
        assert score.suggestions == []
        assert score.issues == []

    def test_dimension_score_full(self):
        score = DimensionScore(
            dimension="Brand Voice",
            score=6,
            status="warning",
            strengths=["Consistent tone"],
            suggestions=["Add more personality"],
            issues=["Missing CTA"],
        )
        assert len(score.strengths) == 1
        assert len(score.suggestions) == 1
        assert len(score.issues) == 1


class TestReviewResultSchema:
    def test_review_result_defaults(self):
        scores = [
            DimensionScore(dimension="Messaging", score=7, status="pass"),
            DimensionScore(dimension="Quality", score=6, status="warning"),
        ]
        result = ReviewResult(scores=scores, overall_score=6.5, verdict="NEEDS REVISION")
        assert len(result.scores) == 2
        assert result.overall_score == 6.5
        assert result.verdict == "NEEDS REVISION"
        assert result.summary == ""
        assert result.top_strengths == []
        assert result.critical_issues == []
        assert result.next_steps == []

    def test_review_result_ready_to_send(self):
        result = ReviewResult(
            scores=[DimensionScore(dimension="Messaging", score=9, status="pass")],
            overall_score=8.5,
            verdict="READY TO SEND",
            top_strengths=["Clear value proposition", "Strong CTA"],
        )
        assert result.verdict == "READY TO SEND"
        assert len(result.top_strengths) == 2

    def test_review_result_major_rework(self):
        result = ReviewResult(
            scores=[DimensionScore(dimension="Quality", score=2, status="issue")],
            overall_score=3.0,
            verdict="MAJOR REWORK",
            critical_issues=["Missing sections", "Placeholder text found"],
        )
        assert result.verdict == "MAJOR REWORK"
        assert len(result.critical_issues) == 2


class TestReviewDimensions:
    def test_review_dimensions_count(self):
        assert len(REVIEW_DIMENSIONS) == 6

    def test_review_dimensions_names(self):
        names = [d["name"] for d in REVIEW_DIMENSIONS]
        assert names == ["Messaging", "Positioning", "Quality", "Data Accuracy", "Brand Voice", "Competitive"]

    def test_review_dimensions_have_required_fields(self):
        for dim in REVIEW_DIMENSIONS:
            assert "name" in dim
            assert "focus" in dim
            assert "checks" in dim


class TestReviewAgent:
    def test_agent_exists(self):
        from second_brain.agents.review import review_agent
        assert review_agent is not None

    def test_agent_output_type(self):
        from second_brain.agents.review import review_agent
        assert review_agent.output_type is DimensionScore

    def test_agent_has_tools(self):
        from second_brain.agents.review import review_agent
        tool_names = list(review_agent._function_toolset.tools)
        assert "load_voice_reference" in tool_names
        assert "load_positioning_context" in tool_names
        assert "load_example_benchmarks" in tool_names

    def test_agent_exported_from_package(self):
        from second_brain.agents import review_agent
        assert review_agent is not None

    def test_run_full_review_exists(self):
        from second_brain.agents.review import run_full_review
        assert callable(run_full_review)
