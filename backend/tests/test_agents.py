"""Tests for agent schemas and registration."""

import pytest
from unittest.mock import MagicMock, AsyncMock

from second_brain.schemas import (
    RecallResult, AskResult, MemoryMatch, LearnResult, PatternExtract,
    CreateResult, ContentTypeConfig, DEFAULT_CONTENT_TYPES,
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

    def test_agent_instructions_require_full_answer(self):
        """Guard against instructions that allow summary output in answer field."""
        from second_brain.agents.ask import ask_agent
        instructions = ask_agent._instructions
        assert "NEVER" in instructions or "MUST" in instructions, (
            "Ask agent instructions must explicitly require full response content"
        )
        assert "answer" in instructions.lower(), (
            "Ask agent instructions must reference the answer field"
        )


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
        # @agent.instructions registers SystemPromptRunners in _instructions_functions
        assert len(learn_agent._instructions_functions) > 0


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


class TestPatternContentTypeLink:
    """Test that store_pattern handles applicable_content_types."""

    async def test_store_pattern_with_content_types(self, mock_deps):
        from second_brain.agents.learn import learn_agent
        mock_deps.storage_service.get_pattern_by_name = AsyncMock(return_value=None)
        mock_deps.storage_service.insert_pattern = AsyncMock(return_value={
            "id": "uuid-new", "name": "Hook First",
        })
        tool_fn = learn_agent._function_toolset.tools["store_pattern"]
        mock_ctx = MagicMock()
        mock_ctx.deps = mock_deps
        result = await tool_fn.function(
            mock_ctx,
            name="Hook First",
            topic="Content",
            pattern_text="Start with a compelling hook",
            applicable_content_types=["linkedin", "instagram"],
        )
        assert "Stored new pattern" in result
        # Verify the content types were passed to storage
        call_args = mock_deps.storage_service.insert_pattern.call_args[0][0]
        assert call_args["applicable_content_types"] == ["linkedin", "instagram"]

    async def test_store_pattern_without_content_types(self, mock_deps):
        from second_brain.agents.learn import learn_agent
        mock_deps.storage_service.get_pattern_by_name = AsyncMock(return_value=None)
        mock_deps.storage_service.insert_pattern = AsyncMock(return_value={
            "id": "uuid-new", "name": "Universal",
        })
        tool_fn = learn_agent._function_toolset.tools["store_pattern"]
        mock_ctx = MagicMock()
        mock_ctx.deps = mock_deps
        result = await tool_fn.function(
            mock_ctx,
            name="Universal",
            topic="Process",
            pattern_text="Always test first",
        )
        assert "Stored new pattern" in result
        call_args = mock_deps.storage_service.insert_pattern.call_args[0][0]
        assert call_args["applicable_content_types"] is None


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
        assert config.length_guidance == ""

    def test_content_type_length_guidance(self):
        config = ContentTypeConfig(
            name="Test Type",
            default_mode="casual",
            structure_hint="Intro -> Body -> Close",
            example_type="test",
            length_guidance="50-300 words, flexible",
        )
        assert config.length_guidance == "50-300 words, flexible"

    def test_content_types_registry(self):
        assert "linkedin" in DEFAULT_CONTENT_TYPES
        assert "email" in DEFAULT_CONTENT_TYPES
        assert "landing-page" in DEFAULT_CONTENT_TYPES
        assert "comment" in DEFAULT_CONTENT_TYPES
        assert len(DEFAULT_CONTENT_TYPES) == 10

    def test_content_types_have_length_guidance(self):
        for slug, ct in DEFAULT_CONTENT_TYPES.items():
            assert ct.length_guidance, f"{slug} missing length_guidance"

    def test_content_type_defaults(self):
        linkedin = DEFAULT_CONTENT_TYPES["linkedin"]
        assert linkedin.default_mode == "casual"
        assert linkedin.max_words == 300
        assert "breathe" in linkedin.length_guidance.lower()
        email = DEFAULT_CONTENT_TYPES["email"]
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

    def test_agent_instructions_require_full_draft(self):
        """Guard against instructions that allow summary output in draft field."""
        from second_brain.agents.create import create_agent
        instructions = create_agent._instructions
        assert "NEVER" in instructions or "MUST" in instructions, (
            "Create agent instructions must explicitly require full draft content"
        )
        assert "draft" in instructions.lower(), (
            "Create agent instructions must reference the draft field"
        )

    def test_agent_instructions_prioritize_voice(self):
        """Instructions must direct agent to use pre-loaded voice guide."""
        from second_brain.agents.create import create_agent
        instructions = create_agent._instructions
        assert "VOICE GUIDE" in instructions, (
            "Create agent instructions must reference pre-loaded VOICE GUIDE"
        )
        assert "voice guide IS the voice" in instructions, (
            "Create agent instructions must emphasize voice guide as primary voice source"
        )


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


class TestGrowthEventRecording:
    """Test that learn agent tools record growth events."""

    def test_store_pattern_tool_exists(self):
        """Verify store_pattern is registered on learn_agent."""
        from second_brain.agents.learn import learn_agent
        tool_names = list(learn_agent._function_toolset.tools)
        assert "store_pattern" in tool_names

    def test_reinforce_pattern_tool_exists(self):
        """Verify reinforce_existing_pattern is registered on learn_agent."""
        from second_brain.agents.learn import learn_agent
        tool_names = list(learn_agent._function_toolset.tools)
        assert "reinforce_existing_pattern" in tool_names


class TestContentTypeExpansion:
    """Test that all content types are properly registered."""

    def test_total_content_types(self):
        """Verify we have 9 content types total."""
        from second_brain.schemas import DEFAULT_CONTENT_TYPES
        assert len(DEFAULT_CONTENT_TYPES) == 10

    def test_original_content_types_unchanged(self):
        """Verify original 4 content types are still present and unchanged."""
        from second_brain.schemas import DEFAULT_CONTENT_TYPES
        assert "linkedin" in DEFAULT_CONTENT_TYPES
        assert "email" in DEFAULT_CONTENT_TYPES
        assert "landing-page" in DEFAULT_CONTENT_TYPES
        assert "comment" in DEFAULT_CONTENT_TYPES
        # Verify original values unchanged
        assert DEFAULT_CONTENT_TYPES["linkedin"].max_words == 300
        assert DEFAULT_CONTENT_TYPES["email"].default_mode == "professional"
        assert DEFAULT_CONTENT_TYPES["landing-page"].max_words == 1000
        assert DEFAULT_CONTENT_TYPES["comment"].max_words == 150

    def test_new_content_types_registered(self):
        """Verify all 5 new content types are present."""
        from second_brain.schemas import DEFAULT_CONTENT_TYPES
        new_types = ["case-study", "proposal", "one-pager", "presentation", "instagram"]
        for t in new_types:
            assert t in DEFAULT_CONTENT_TYPES, f"Missing content type: {t}"

    def test_new_content_types_have_required_fields(self):
        """Verify each new content type has all required fields populated."""
        from second_brain.schemas import DEFAULT_CONTENT_TYPES
        new_types = ["case-study", "proposal", "one-pager", "presentation", "instagram"]
        for t in new_types:
            config = DEFAULT_CONTENT_TYPES[t]
            assert config.name, f"{t}: missing name"
            assert config.default_mode in ("casual", "professional", "formal"), \
                f"{t}: invalid mode '{config.default_mode}'"
            assert config.structure_hint, f"{t}: missing structure_hint"
            assert config.example_type, f"{t}: missing example_type"
            assert config.max_words > 0, f"{t}: max_words must be > 0"
            assert config.description, f"{t}: missing description"

    def test_case_study_config(self):
        """Verify case-study content type configuration."""
        from second_brain.schemas import DEFAULT_CONTENT_TYPES
        config = DEFAULT_CONTENT_TYPES["case-study"]
        assert config.name == "Case Study"
        assert config.default_mode == "professional"
        assert config.max_words == 1500
        assert "Results" in config.structure_hint

    def test_proposal_config(self):
        """Verify proposal content type configuration."""
        from second_brain.schemas import DEFAULT_CONTENT_TYPES
        config = DEFAULT_CONTENT_TYPES["proposal"]
        assert config.name == "Sales Proposal"
        assert config.default_mode == "professional"
        assert config.max_words == 2000
        assert "Investment" in config.structure_hint

    def test_one_pager_config(self):
        """Verify one-pager content type configuration."""
        from second_brain.schemas import DEFAULT_CONTENT_TYPES
        config = DEFAULT_CONTENT_TYPES["one-pager"]
        assert config.name == "One-Pager"
        assert config.default_mode == "professional"
        assert config.max_words == 500
        assert "Key Benefits" in config.structure_hint

    def test_presentation_config(self):
        """Verify presentation content type configuration."""
        from second_brain.schemas import DEFAULT_CONTENT_TYPES
        config = DEFAULT_CONTENT_TYPES["presentation"]
        assert config.name == "Presentation Script"
        assert config.default_mode == "professional"
        assert config.max_words == 800
        assert "Key Points" in config.structure_hint

    def test_instagram_config(self):
        """Verify instagram content type configuration."""
        from second_brain.schemas import DEFAULT_CONTENT_TYPES
        config = DEFAULT_CONTENT_TYPES["instagram"]
        assert config.name == "Instagram Post"
        assert config.default_mode == "casual"
        assert config.max_words == 200
        assert "Hashtags" in config.structure_hint


class TestDynamicContentTypes:
    """Tests for dynamic content type system."""

    def test_default_content_types_exists(self):
        from second_brain.schemas import DEFAULT_CONTENT_TYPES
        assert len(DEFAULT_CONTENT_TYPES) == 10

    def test_default_content_types_all_builtin(self):
        from second_brain.schemas import DEFAULT_CONTENT_TYPES
        for slug, config in DEFAULT_CONTENT_TYPES.items():
            assert config.is_builtin is True, f"{slug} should be builtin"

    def test_content_type_config_new_fields(self):
        from second_brain.schemas import ContentTypeConfig
        config = ContentTypeConfig(
            name="Newsletter",
            default_mode="professional",
            structure_hint="Subject -> Body -> Footer",
            example_type="newsletter",
            max_words=800,
            description="Email newsletter",
            is_builtin=False,
        )
        assert config.is_builtin is False
        assert config.review_dimensions is None

    def test_content_type_config_with_review_dimensions(self):
        from second_brain.schemas import ContentTypeConfig, ReviewDimensionConfig
        dims = [
            ReviewDimensionConfig(name="Messaging", weight=1.5, enabled=True),
            ReviewDimensionConfig(name="Quality", weight=1.0, enabled=True),
            ReviewDimensionConfig(name="Data Accuracy", weight=0.0, enabled=False),
        ]
        config = ContentTypeConfig(
            name="Comment",
            default_mode="casual",
            structure_hint="Ack -> Insight",
            example_type="comment",
            review_dimensions=dims,
        )
        assert len(config.review_dimensions) == 3
        assert config.review_dimensions[0].weight == 1.5
        assert config.review_dimensions[2].enabled is False

    def test_review_dimension_config_defaults(self):
        from second_brain.schemas import ReviewDimensionConfig
        dim = ReviewDimensionConfig(name="Messaging")
        assert dim.weight == 1.0
        assert dim.enabled is True

    def test_default_review_dimensions(self):
        from second_brain.schemas import DEFAULT_REVIEW_DIMENSIONS, REVIEW_DIMENSIONS
        assert len(DEFAULT_REVIEW_DIMENSIONS) == len(REVIEW_DIMENSIONS)
        for dc in DEFAULT_REVIEW_DIMENSIONS:
            assert dc.weight == 1.0
            assert dc.enabled is True

    def test_content_type_from_row_basic(self):
        from second_brain.services.storage import content_type_from_row
        row = {
            "slug": "newsletter",
            "name": "Newsletter",
            "default_mode": "professional",
            "structure_hint": "Subject -> Body -> Footer",
            "example_type": "newsletter",
            "max_words": 800,
            "description": "Email newsletter",
            "is_builtin": False,
            "review_dimensions": None,
        }
        config = content_type_from_row(row)
        assert config.name == "Newsletter"
        assert config.default_mode == "professional"
        assert config.max_words == 800
        assert config.is_builtin is False
        assert config.review_dimensions is None

    def test_content_type_from_row_with_dimensions(self):
        from second_brain.services.storage import content_type_from_row
        row = {
            "slug": "comment",
            "name": "Comment",
            "default_mode": "casual",
            "structure_hint": "Ack -> Insight",
            "example_type": "comment",
            "max_words": 150,
            "is_builtin": True,
            "review_dimensions": [
                {"name": "Messaging", "weight": 1.0, "enabled": True},
                {"name": "Quality", "weight": 1.0, "enabled": True},
            ],
        }
        config = content_type_from_row(row)
        assert config.review_dimensions is not None
        assert len(config.review_dimensions) == 2
        assert config.review_dimensions[0].name == "Messaging"

    def test_content_type_from_row_minimal(self):
        from second_brain.services.storage import content_type_from_row
        row = {
            "name": "Minimal",
            "slug": "minimal",
            "structure_hint": "X",
            "example_type": "minimal",
        }
        config = content_type_from_row(row)
        assert config.name == "Minimal"
        assert config.default_mode == "professional"  # default
        assert config.max_words == 0  # default
        assert config.is_builtin is False  # default

    def test_pattern_extract_applicable_content_types_default(self):
        from second_brain.schemas import PatternExtract
        p = PatternExtract(name="t", topic="t", pattern_text="t")
        assert p.applicable_content_types is None

    def test_pattern_extract_applicable_content_types_set(self):
        from second_brain.schemas import PatternExtract
        p = PatternExtract(
            name="Hook First",
            topic="Content",
            pattern_text="Start with a hook",
            applicable_content_types=["linkedin", "instagram"],
        )
        assert p.applicable_content_types == ["linkedin", "instagram"]

    def test_pattern_extract_universal_vs_specific(self):
        from second_brain.schemas import PatternExtract
        universal = PatternExtract(name="u", topic="t", pattern_text="t")
        specific = PatternExtract(
            name="s", topic="t", pattern_text="t",
            applicable_content_types=["email"],
        )
        assert universal.applicable_content_types is None  # universal
        assert specific.applicable_content_types == ["email"]  # specific


class TestGraphIntegration:
    """Test graph memory integration across agents."""

    async def test_store_pattern_passes_enable_graph(self, mock_deps):
        from second_brain.agents.learn import learn_agent
        mock_deps.storage_service.get_pattern_by_name = AsyncMock(return_value=None)
        mock_deps.storage_service.insert_pattern = AsyncMock(return_value={
            "id": "uuid-new", "name": "Hook First",
        })
        tool_fn = learn_agent._function_toolset.tools["store_pattern"]
        mock_ctx = MagicMock()
        mock_ctx.deps = mock_deps

        await tool_fn.function(
            mock_ctx, name="Hook First", topic="Content",
            pattern_text="Start with a hook",
            applicable_content_types=["linkedin"],
        )

        # Verify enable_graph=True is passed
        mock_deps.memory_service.add_with_metadata.assert_called_once()
        call_kwargs = mock_deps.memory_service.add_with_metadata.call_args[1]
        assert call_kwargs.get("enable_graph") is True

    async def test_store_pattern_includes_content_types_in_content(self, mock_deps):
        from second_brain.agents.learn import learn_agent
        mock_deps.storage_service.get_pattern_by_name = AsyncMock(return_value=None)
        mock_deps.storage_service.insert_pattern = AsyncMock(return_value={
            "id": "uuid-new", "name": "Hook First",
        })
        tool_fn = learn_agent._function_toolset.tools["store_pattern"]
        mock_ctx = MagicMock()
        mock_ctx.deps = mock_deps

        await tool_fn.function(
            mock_ctx, name="Hook First", topic="Content",
            pattern_text="Start with a hook",
            applicable_content_types=["linkedin", "instagram"],
        )

        call_kwargs = mock_deps.memory_service.add_with_metadata.call_args[1]
        assert "Applies to: linkedin, instagram" in call_kwargs["content"]

    async def test_store_experience_syncs_to_mem0(self, mock_deps):
        from second_brain.agents.learn import learn_agent
        tool_fn = learn_agent._function_toolset.tools["store_experience"]
        mock_ctx = MagicMock()
        mock_ctx.deps = mock_deps

        await tool_fn.function(
            mock_ctx,
            name="Q4 Campaign",
            category="content",
            output_summary="Launched Q4 email campaign",
            learnings="Hooks work better than questions",
            patterns_extracted=["Hook First"],
        )

        # Verify Mem0 dual-write was called with graph enabled
        mock_deps.memory_service.add_with_metadata.assert_called_once()
        call_kwargs = mock_deps.memory_service.add_with_metadata.call_args[1]
        assert call_kwargs.get("enable_graph") is True
        assert "Q4 Campaign" in call_kwargs.get("content", "")
        assert "Hook First" in call_kwargs.get("content", "")

    async def test_store_experience_succeeds_if_mem0_fails(self, mock_deps):
        from second_brain.agents.learn import learn_agent
        mock_deps.memory_service.add_with_metadata = AsyncMock(
            side_effect=Exception("Mem0 unavailable")
        )
        tool_fn = learn_agent._function_toolset.tools["store_experience"]
        mock_ctx = MagicMock()
        mock_ctx.deps = mock_deps

        result = await tool_fn.function(
            mock_ctx,
            name="Test",
            category="general",
            output_summary="Test output",
            learnings="Test learnings",
        )

        # Experience should still be stored despite Mem0 failure
        assert "Recorded experience" in result
        mock_deps.storage_service.add_experience.assert_called_once()

    async def test_recall_search_patterns_requests_graph(self, mock_deps):
        from second_brain.agents.recall import recall_agent
        tool_fn = recall_agent._function_toolset.tools["search_patterns"]
        mock_ctx = MagicMock()
        mock_ctx.deps = mock_deps

        await tool_fn.function(mock_ctx, topic="Content")

        # Verify search_with_filters was called with enable_graph=True
        mock_deps.memory_service.search_with_filters.assert_called_once()
        call_kwargs = mock_deps.memory_service.search_with_filters.call_args[1]
        assert call_kwargs.get("enable_graph") is True

    async def test_create_find_patterns_requests_graph(self, mock_deps):
        from second_brain.agents.create import create_agent
        tool_fn = create_agent._function_toolset.tools["find_applicable_patterns"]
        mock_ctx = MagicMock()
        mock_ctx.deps = mock_deps

        await tool_fn.function(mock_ctx, topic="hooks", content_type="linkedin")

        # Verify search_with_filters was called with enable_graph=True
        mock_deps.memory_service.search_with_filters.assert_called_once()
        call_kwargs = mock_deps.memory_service.search_with_filters.call_args[1]
        assert call_kwargs.get("enable_graph") is True

    async def test_ask_find_experiences_passes_graph(self, mock_deps):
        from second_brain.agents.ask import ask_agent
        tool_fn = ask_agent._function_toolset.tools["find_similar_experiences"]
        mock_ctx = MagicMock()
        mock_ctx.deps = mock_deps

        await tool_fn.function(mock_ctx, query="email campaigns")

        # Verify search was called with enable_graph=True
        mock_deps.memory_service.search.assert_called()
        call_kwargs = mock_deps.memory_service.search.call_args[1]
        assert call_kwargs.get("enable_graph") is True


class TestSemanticPatternSync:
    """Test dual-write from learn_agent to Mem0."""

    async def test_store_pattern_syncs_to_mem0(self, mock_deps):
        from second_brain.agents.learn import learn_agent
        mock_deps.storage_service.get_pattern_by_name = AsyncMock(return_value=None)
        mock_deps.storage_service.insert_pattern = AsyncMock(return_value={
            "id": "uuid-new", "name": "Hook First",
        })
        tool_fn = learn_agent._function_toolset.tools["store_pattern"]
        mock_ctx = MagicMock()
        mock_ctx.deps = mock_deps

        result = await tool_fn.function(
            mock_ctx, name="Hook First", topic="Content",
            pattern_text="Start with a compelling hook",
            applicable_content_types=["linkedin"],
        )

        assert "Stored new pattern" in result
        # Verify Mem0 dual-write was called
        mock_deps.memory_service.add_with_metadata.assert_called_once()
        call_kwargs = mock_deps.memory_service.add_with_metadata.call_args[1]
        assert "Hook First" in call_kwargs["content"]
        assert call_kwargs["metadata"]["category"] == "pattern"
        assert call_kwargs["metadata"]["pattern_name"] == "Hook First"
        assert call_kwargs["metadata"]["topic"] == "Content"

    async def test_store_pattern_succeeds_if_mem0_fails(self, mock_deps):
        from second_brain.agents.learn import learn_agent
        mock_deps.storage_service.get_pattern_by_name = AsyncMock(return_value=None)
        mock_deps.storage_service.insert_pattern = AsyncMock(return_value={
            "id": "uuid-new", "name": "Test",
        })
        mock_deps.memory_service.add_with_metadata = AsyncMock(
            side_effect=Exception("Mem0 unavailable")
        )
        tool_fn = learn_agent._function_toolset.tools["store_pattern"]
        mock_ctx = MagicMock()
        mock_ctx.deps = mock_deps

        result = await tool_fn.function(
            mock_ctx, name="Test", topic="T", pattern_text="text",
        )

        # Pattern should still be stored despite Mem0 failure
        assert "Stored new pattern" in result
        mock_deps.storage_service.insert_pattern.assert_called_once()

    async def test_reinforce_syncs_to_mem0(self, mock_deps):
        from second_brain.agents.learn import learn_agent
        mock_deps.storage_service.get_pattern_by_name = AsyncMock(return_value={
            "id": "uuid-1", "name": "Test", "topic": "Content",
            "use_count": 2, "confidence": "MEDIUM",
        })
        mock_deps.storage_service.reinforce_pattern = AsyncMock(return_value={
            "id": "uuid-1", "name": "Test",
            "use_count": 3, "confidence": "MEDIUM",
        })
        tool_fn = learn_agent._function_toolset.tools["reinforce_existing_pattern"]
        mock_ctx = MagicMock()
        mock_ctx.deps = mock_deps

        result = await tool_fn.function(mock_ctx, pattern_name="Test")

        assert "Reinforced" in result
        mock_deps.memory_service.add_with_metadata.assert_called_once()
        call_kwargs = mock_deps.memory_service.add_with_metadata.call_args[1]
        assert call_kwargs["metadata"]["category"] == "pattern_reinforcement"
        assert call_kwargs["metadata"]["pattern_name"] == "Test"

    async def test_recall_search_patterns_uses_semantic_search(self, mock_deps):
        from second_brain.agents.recall import recall_agent
        tool_fn = recall_agent._function_toolset.tools["search_patterns"]
        mock_ctx = MagicMock()
        mock_ctx.deps = mock_deps

        await tool_fn.function(mock_ctx, topic="Content")

        # Should call search_with_filters for semantic search
        mock_deps.memory_service.search_with_filters.assert_called_once()


class TestMemoryGraduation:
    """Test memory consolidation and graduation tools."""

    def test_consolidate_tool_exists(self):
        from second_brain.agents.learn import learn_agent
        tool_names = list(learn_agent._function_toolset.tools)
        assert "consolidate_memories" in tool_names

    def test_tag_graduated_tool_exists(self):
        from second_brain.agents.learn import learn_agent
        tool_names = list(learn_agent._function_toolset.tools)
        assert "tag_graduated_memories" in tool_names

    async def test_consolidate_no_memories(self, mock_deps):
        from second_brain.agents.learn import learn_agent
        mock_deps.memory_service.get_all = AsyncMock(return_value=[])
        tool_fn = learn_agent._function_toolset.tools["consolidate_memories"]
        mock_ctx = MagicMock()
        mock_ctx.deps = mock_deps

        result = await tool_fn.function(mock_ctx)
        assert "No memories found" in result

    async def test_consolidate_all_categorized(self, mock_deps):
        from second_brain.agents.learn import learn_agent
        mock_deps.memory_service.get_all = AsyncMock(return_value=[
            {"memory": "Pattern: Hook First", "metadata": {"category": "pattern"}},
            {"memory": "Graduated memory", "metadata": {"category": "graduated"}},
        ])
        tool_fn = learn_agent._function_toolset.tools["consolidate_memories"]
        mock_ctx = MagicMock()
        mock_ctx.deps = mock_deps

        result = await tool_fn.function(mock_ctx)
        assert "All memories are already categorized" in result

    async def test_consolidate_finds_uncategorized(self, mock_deps):
        from second_brain.agents.learn import learn_agent
        mock_deps.memory_service.get_all = AsyncMock(return_value=[
            {"memory": "Writing tip 1", "metadata": {"category": "learning"}},
            {"memory": "Writing tip 2", "metadata": {}},
            {"memory": "Pattern: Hook", "metadata": {"category": "pattern"}},
        ])
        tool_fn = learn_agent._function_toolset.tools["consolidate_memories"]
        mock_ctx = MagicMock()
        mock_ctx.deps = mock_deps

        result = await tool_fn.function(mock_ctx)
        assert "2 uncategorized memories" in result

    async def test_tag_graduated_success(self, mock_deps):
        from second_brain.agents.learn import learn_agent
        tool_fn = learn_agent._function_toolset.tools["tag_graduated_memories"]
        mock_ctx = MagicMock()
        mock_ctx.deps = mock_deps

        result = await tool_fn.function(
            mock_ctx,
            memory_ids=["mem-1", "mem-2"],
            pattern_name="Hook First",
        )

        assert "Tagged 2/2" in result
        assert mock_deps.memory_service.update_memory.call_count == 2

    async def test_tag_graduated_partial_failure(self, mock_deps):
        from second_brain.agents.learn import learn_agent
        mock_deps.memory_service.update_memory = AsyncMock(
            side_effect=[None, Exception("Mem0 error"), None]
        )
        tool_fn = learn_agent._function_toolset.tools["tag_graduated_memories"]
        mock_ctx = MagicMock()
        mock_ctx.deps = mock_deps

        result = await tool_fn.function(
            mock_ctx,
            memory_ids=["mem-1", "mem-2", "mem-3"],
            pattern_name="Test",
        )

        assert "Tagged 2/3" in result


class TestAgentGraphitiIntegration:
    """Test that agents interact with Graphiti when available."""

    def test_recall_agent_has_search_tool(self):
        from second_brain.agents.recall import recall_agent
        tools = list(recall_agent._function_toolset.tools.keys())
        assert "search_semantic_memory" in tools

    def test_review_agent_has_graph_context_tool(self):
        from second_brain.agents.review import review_agent
        tools = list(review_agent._function_toolset.tools.keys())
        assert "load_graph_context" in tools

    def test_learn_agent_has_store_pattern_tool(self):
        from second_brain.agents.learn import learn_agent
        tools = list(learn_agent._function_toolset.tools.keys())
        assert "store_pattern" in tools
        assert "store_experience" in tools

    def test_create_agent_has_pattern_tool(self):
        from second_brain.agents.create import create_agent
        tools = list(create_agent._function_toolset.tools.keys())
        assert "find_applicable_patterns" in tools


class TestAgentEnhancements:
    """Test agent enhancements from adopt-original-system sub-plans."""

    def test_learn_agent_has_learn_from_review_tool(self):
        from second_brain.agents.learn import learn_agent
        tools = list(learn_agent._function_toolset.tools.keys())
        assert "learn_from_review" in tools

    def test_recall_agent_has_search_projects_tool(self):
        from second_brain.agents.recall import recall_agent
        tools = list(recall_agent._function_toolset.tools.keys())
        assert "search_projects" in tools

    def test_format_pattern_registry_empty(self):
        from second_brain.agents.utils import format_pattern_registry
        result = format_pattern_registry([])
        assert "No patterns" in result

    def test_format_pattern_registry_with_data(self):
        from second_brain.agents.utils import format_pattern_registry
        result = format_pattern_registry([
            {"name": "Test Pattern", "topic": "Demo", "confidence": "HIGH",
             "use_count": 5, "date_updated": "2026-01-01",
             "consecutive_failures": 0},
        ])
        assert "Test Pattern" in result
        assert "HIGH" in result
        assert "Total: 1" in result

    def test_format_pattern_registry_at_risk(self):
        from second_brain.agents.utils import format_pattern_registry
        result = format_pattern_registry([
            {"name": "Risky", "topic": "Demo", "confidence": "LOW",
             "use_count": 2, "date_updated": "2026-01-01",
             "consecutive_failures": 3},
        ])
        assert "At Risk" in result

    def test_pipeline_function_importable(self):
        from second_brain.agents.utils import run_review_learn_pipeline
        assert callable(run_review_learn_pipeline)

    def test_tool_error_format(self):
        from second_brain.agents.utils import tool_error
        result = tool_error("search_memory", ValueError("bad input"))
        assert "search_memory" in result
        assert "ValueError" in result


class TestRetrievalUtils:
    """Tests for retrieval utility functions."""

    def test_expand_query_with_synonyms(self):
        from second_brain.agents.utils import expand_query
        result = expand_query("client patterns")
        assert "client" in result
        # Should include at least one synonym
        assert any(syn in result for syn in ["customer", "account", "prospect"])

    def test_expand_query_no_match(self):
        from second_brain.agents.utils import expand_query
        result = expand_query("random unrecognized words")
        assert result == "random unrecognized words"

    def test_expand_query_max_expansions(self):
        from second_brain.agents.utils import expand_query
        result = expand_query("client voice pattern", max_expansions=2)
        # Original words are still there
        assert "client" in result
        assert "voice" in result
        assert "pattern" in result
        # Count expansion terms (words not in original)
        original_words = {"client", "voice", "pattern"}
        extra_words = [w for w in result.split() if w.lower() not in original_words]
        assert len(extra_words) <= 2

    def test_expand_query_no_duplicates(self):
        """Synonyms already in query should not be re-added."""
        from second_brain.agents.utils import expand_query
        result = expand_query("customer patterns")  # "customer" is a synonym for "client"
        assert result.count("customer") == 1

    def test_deduplicate_results_removes_exact_dupes(self):
        from second_brain.agents.utils import deduplicate_results
        results = [
            {"memory": "fact A", "score": 0.9},
            {"memory": "fact B", "score": 0.8},
            {"memory": "fact A", "score": 0.7},  # duplicate
        ]
        deduped = deduplicate_results(results)
        assert len(deduped) == 2

    def test_deduplicate_results_preserves_order(self):
        from second_brain.agents.utils import deduplicate_results
        results = [
            {"memory": "first", "score": 0.5},
            {"memory": "second", "score": 0.9},
            {"memory": "first", "score": 0.3},
        ]
        deduped = deduplicate_results(results)
        assert deduped[0]["memory"] == "first"
        assert deduped[1]["memory"] == "second"

    def test_deduplicate_results_empty(self):
        from second_brain.agents.utils import deduplicate_results
        assert deduplicate_results([]) == []

    def test_deduplicate_results_custom_keys(self):
        from second_brain.agents.utils import deduplicate_results
        results = [
            {"content": "A", "similarity": 0.9},
            {"content": "B", "similarity": 0.8},
            {"content": "A", "similarity": 0.7},
        ]
        deduped = deduplicate_results(results, content_key="content")
        assert len(deduped) == 2

    def test_format_memories_shows_rerank_score(self):
        """format_memories should prefer rerank_score over score."""
        from second_brain.agents.utils import format_memories
        memories = [
            {"memory": "test content", "score": 0.7, "rerank_score": 0.95},
        ]
        result = format_memories(memories)
        assert "0.95" in result
        assert "0.70" not in result

    def test_format_memories_fallback_to_score(self):
        """When no rerank_score, should use original score."""
        from second_brain.agents.utils import format_memories
        memories = [
            {"memory": "test content", "score": 0.7},
        ]
        result = format_memories(memories)
        assert "0.70" in result

    def test_format_memories_no_score(self):
        """When no score at all, should show 0.00."""
        from second_brain.agents.utils import format_memories
        memories = [{"memory": "test content"}]
        result = format_memories(memories)
        assert "0.00" in result


class TestAgentFunctionalBehavior:
    """Functional tests that invoke agent tool functions with mocked deps.

    These tests go beyond structural checks — they call actual tool functions
    with a mocked RunContext and verify correct service method calls.
    """

    @pytest.fixture
    def mock_ctx(self, mock_deps):
        """Create a mock RunContext with deps."""
        ctx = MagicMock()
        ctx.deps = mock_deps
        return ctx

    # --- recall_agent ---

    async def test_recall_search_semantic_memory_calls_service(self, mock_ctx):
        """search_semantic_memory calls memory_service.search."""
        from second_brain.agents.recall import recall_agent

        tool = recall_agent._function_toolset.tools["search_semantic_memory"]
        mock_ctx.deps.memory_service.search = AsyncMock(return_value=[
            {"memory": "test memory", "score": 0.9}
        ])

        result = await tool.function(mock_ctx, query="test query")

        mock_ctx.deps.memory_service.search.assert_called_once()
        assert isinstance(result, str)

    async def test_recall_search_patterns_calls_storage(self, mock_ctx):
        """search_patterns calls storage_service.get_patterns."""
        from second_brain.agents.recall import recall_agent

        tool = recall_agent._function_toolset.tools["search_patterns"]
        mock_ctx.deps.memory_service.search_with_filters = AsyncMock(return_value=[])
        mock_ctx.deps.storage_service.get_patterns = AsyncMock(return_value=[
            {"name": "Hook First", "confidence": "HIGH", "use_count": 5,
             "pattern_text": "Start with a hook"}
        ])

        result = await tool.function(mock_ctx, topic=None)

        mock_ctx.deps.storage_service.get_patterns.assert_called_once()
        assert isinstance(result, str)

    async def test_recall_search_experiences_calls_storage(self, mock_ctx):
        """search_experiences calls storage_service.get_experiences."""
        from second_brain.agents.recall import recall_agent

        tool = recall_agent._function_toolset.tools["search_experiences"]
        mock_ctx.deps.storage_service.get_experiences = AsyncMock(return_value=[
            {"name": "Blog post", "category": "writing", "review_score": 8.5}
        ])

        result = await tool.function(mock_ctx, category=None)

        mock_ctx.deps.storage_service.get_experiences.assert_called_once()
        assert isinstance(result, str)

    # --- ask_agent ---

    async def test_ask_load_brain_context_calls_storage(self, mock_ctx):
        """load_brain_context calls storage_service.get_memory_content."""
        from second_brain.agents.ask import ask_agent

        tool = ask_agent._function_toolset.tools["load_brain_context"]
        mock_ctx.deps.storage_service.get_memory_content = AsyncMock(return_value=[])

        result = await tool.function(mock_ctx)

        assert mock_ctx.deps.storage_service.get_memory_content.call_count >= 1
        assert isinstance(result, str)

    async def test_ask_find_relevant_patterns_calls_services(self, mock_ctx):
        """find_relevant_patterns calls memory_service.search."""
        from second_brain.agents.ask import ask_agent

        tool = ask_agent._function_toolset.tools["find_relevant_patterns"]
        mock_ctx.deps.memory_service.search = AsyncMock(return_value=[
            {"memory": "hook pattern", "score": 0.8}
        ])
        mock_ctx.deps.memory_service.search_with_filters = AsyncMock(return_value=[])
        mock_ctx.deps.storage_service.get_patterns = AsyncMock(return_value=[])
        mock_ctx.deps.graphiti_service = None

        result = await tool.function(mock_ctx, query="hooks")

        mock_ctx.deps.memory_service.search.assert_called_once()
        assert isinstance(result, str)

    # --- learn_agent ---

    async def test_learn_search_existing_patterns_calls_storage(self, mock_ctx):
        """search_existing_patterns calls storage_service.get_patterns."""
        from second_brain.agents.learn import learn_agent

        tool = learn_agent._function_toolset.tools["search_existing_patterns"]
        mock_ctx.deps.storage_service.get_patterns = AsyncMock(return_value=[
            {"name": "Hook Pattern", "confidence": "HIGH", "use_count": 3}
        ])

        result = await tool.function(mock_ctx, query="hook")

        mock_ctx.deps.storage_service.get_patterns.assert_called_once()
        assert isinstance(result, str)

    async def test_learn_add_to_memory_calls_memory_service(self, mock_ctx):
        """add_to_memory calls memory_service.add."""
        from second_brain.agents.learn import learn_agent

        tool = learn_agent._function_toolset.tools["add_to_memory"]
        mock_ctx.deps.memory_service.add = AsyncMock(return_value={"id": "mem-1"})

        result = await tool.function(mock_ctx, content="New insight about hooks", category="learning")

        mock_ctx.deps.memory_service.add.assert_called_once()
        assert "Added to semantic memory" in result

    # --- create_agent ---

    async def test_create_load_voice_guide_calls_storage(self, mock_ctx):
        """load_voice_guide calls storage_service.get_memory_content."""
        from second_brain.agents.create import create_agent

        tool = create_agent._function_toolset.tools["load_voice_guide"]
        mock_ctx.deps.storage_service.get_memory_content = AsyncMock(return_value=[
            {"content": "Keep it conversational", "subcategory": "tone"}
        ])

        result = await tool.function(mock_ctx)

        mock_ctx.deps.storage_service.get_memory_content.assert_called_once_with("style-voice")
        assert isinstance(result, str)

    async def test_create_load_content_examples_calls_storage(self, mock_ctx):
        """load_content_examples calls storage_service.get_examples."""
        from second_brain.agents.create import create_agent

        tool = create_agent._function_toolset.tools["load_content_examples"]
        mock_ctx.deps.storage_service.get_examples = AsyncMock(return_value=[
            {"title": "Great blog post", "content": "Example content here",
             "content_type": "blog-post"}
        ])

        result = await tool.function(mock_ctx, content_type="blog-post")

        mock_ctx.deps.storage_service.get_examples.assert_called_once_with(content_type="blog-post")
        assert isinstance(result, str)

    # --- review_agent ---

    async def test_review_load_voice_reference_calls_storage(self, mock_ctx):
        """load_voice_reference calls storage_service.get_memory_content."""
        from second_brain.agents.review import review_agent

        tool = review_agent._function_toolset.tools["load_voice_reference"]
        mock_ctx.deps.storage_service.get_memory_content = AsyncMock(return_value=[
            {"content": "Be direct and punchy", "subcategory": "style"}
        ])

        result = await tool.function(mock_ctx)

        mock_ctx.deps.storage_service.get_memory_content.assert_called_once_with("style-voice")
        assert isinstance(result, str)

    async def test_review_load_example_benchmarks_calls_storage(self, mock_ctx):
        """load_example_benchmarks calls storage_service.get_examples."""
        from second_brain.agents.review import review_agent

        tool = review_agent._function_toolset.tools["load_example_benchmarks"]
        mock_ctx.deps.storage_service.get_examples = AsyncMock(return_value=[])

        result = await tool.function(mock_ctx, content_type=None)

        mock_ctx.deps.storage_service.get_examples.assert_called_once()
        assert isinstance(result, str)


class TestRecallAgentRetrieval:
    """Tests for updated recall agent tools with semantic search."""

    def test_search_examples_accepts_query_param(self):
        """search_examples should accept a query parameter for semantic search."""
        from second_brain.agents.recall import recall_agent
        import inspect
        tool = recall_agent._function_toolset.tools["search_examples"]
        sig = inspect.signature(tool.function)
        assert "query" in sig.parameters

    def test_search_experiences_accepts_query_param(self):
        """search_experiences should accept a query parameter for semantic search."""
        from second_brain.agents.recall import recall_agent
        import inspect
        tool = recall_agent._function_toolset.tools["search_experiences"]
        sig = inspect.signature(tool.function)
        assert "query" in sig.parameters

    @pytest.fixture
    def mock_ctx(self, mock_deps):
        ctx = MagicMock()
        ctx.deps = mock_deps
        return ctx

    async def test_search_examples_semantic_path(self, mock_ctx):
        """With query + embedding service, should use semantic search."""
        from second_brain.agents.recall import recall_agent
        tool = recall_agent._function_toolset.tools["search_examples"]
        mock_ctx.deps.storage_service.search_examples_semantic = AsyncMock(return_value=[
            {"id": "e1", "content": "Example", "title": "Good Email",
             "category": "email", "similarity": 0.85},
        ])
        result = await tool.function(mock_ctx, query="email writing", content_type=None)
        assert isinstance(result, str)
        assert "Good Email" in result
        mock_ctx.deps.storage_service.search_examples_semantic.assert_called_once()

    async def test_search_examples_fallback_no_embedding(self, mock_ctx):
        """Without embedding service, should fall back to get_examples."""
        from second_brain.agents.recall import recall_agent
        tool = recall_agent._function_toolset.tools["search_examples"]
        mock_ctx.deps.embedding_service = None
        mock_ctx.deps.storage_service.get_examples = AsyncMock(return_value=[
            {"content_type": "email", "title": "Fallback Email", "content": "text"},
        ])
        result = await tool.function(mock_ctx, query="email", content_type="email")
        assert "Fallback Email" in result

    async def test_search_experiences_semantic_path(self, mock_ctx):
        """With query + embedding service, should use semantic search."""
        from second_brain.agents.recall import recall_agent
        tool = recall_agent._function_toolset.tools["search_experiences"]
        mock_ctx.deps.storage_service.search_experiences_semantic = AsyncMock(return_value=[
            {"id": "ex1", "content": "Project", "title": "Consulting Gig",
             "category": "consulting", "similarity": 0.78},
        ])
        result = await tool.function(mock_ctx, query="consulting work", category=None)
        assert isinstance(result, str)
        assert "Consulting Gig" in result

    async def test_search_semantic_memory_uses_expand_query(self, mock_ctx):
        """search_semantic_memory should expand the query before searching."""
        from second_brain.agents.recall import recall_agent
        from second_brain.services.search_result import SearchResult
        tool = recall_agent._function_toolset.tools["search_semantic_memory"]
        mock_ctx.deps.memory_service.search = AsyncMock(return_value=SearchResult(
            memories=[{"memory": "test result", "score": 0.9}], relations=[],
        ))
        mock_ctx.deps.voyage_service = None  # skip reranking
        mock_ctx.deps.graphiti_service = None
        result = await tool.function(mock_ctx, query="client patterns")
        assert isinstance(result, str)
        mock_ctx.deps.memory_service.search.assert_called_once()

    async def test_search_patterns_hybrid_path(self, mock_ctx):
        """search_patterns should try hybrid search first."""
        from second_brain.agents.recall import recall_agent
        from second_brain.services.search_result import SearchResult
        tool = recall_agent._function_toolset.tools["search_patterns"]
        mock_ctx.deps.storage_service.hybrid_search = AsyncMock(return_value=[
            {"id": "p1", "content": "Hook First", "title": "Hook First",
             "category": "writing", "similarity": 0.9, "search_type": "hybrid"},
        ])
        mock_ctx.deps.memory_service.search_with_filters = AsyncMock(return_value=SearchResult(
            memories=[], relations=[],
        ))
        mock_ctx.deps.voyage_service = None
        mock_ctx.deps.graphiti_service = None
        result = await tool.function(mock_ctx, topic="writing")
        assert isinstance(result, str)
        assert "Hook First" in result


class TestAskAgentRetrieval:
    """Tests for consolidated ask agent search."""

    def test_find_relevant_patterns_exists(self):
        from second_brain.agents.ask import ask_agent
        tools = list(ask_agent._function_toolset.tools)
        assert "find_relevant_patterns" in tools

    @pytest.fixture
    def mock_ctx(self, mock_deps):
        ctx = MagicMock()
        ctx.deps = mock_deps
        return ctx

    async def test_find_relevant_patterns_returns_string(self, mock_ctx):
        from second_brain.agents.ask import ask_agent
        from second_brain.services.search_result import SearchResult
        tool = ask_agent._function_toolset.tools["find_relevant_patterns"]
        mock_ctx.deps.memory_service.search = AsyncMock(return_value=SearchResult(
            memories=[{"memory": "hook pattern", "score": 0.8}], relations=[],
        ))
        mock_ctx.deps.voyage_service = None
        mock_ctx.deps.graphiti_service = None
        result = await tool.function(mock_ctx, query="content writing")
        assert isinstance(result, str)

    async def test_find_relevant_patterns_hybrid_search_called(self, mock_ctx):
        """When embedding service available, should call hybrid_search."""
        from second_brain.agents.ask import ask_agent
        from second_brain.services.search_result import SearchResult
        tool = ask_agent._function_toolset.tools["find_relevant_patterns"]
        mock_ctx.deps.memory_service.search = AsyncMock(return_value=SearchResult(
            memories=[], relations=[],
        ))
        mock_ctx.deps.storage_service.hybrid_search = AsyncMock(return_value=[
            {"content": "Test pattern", "title": "Pattern A",
             "category": "writing", "similarity": 0.88, "search_type": "semantic"},
        ])
        mock_ctx.deps.voyage_service = None
        mock_ctx.deps.graphiti_service = None
        result = await tool.function(mock_ctx, query="writing patterns")
        # hybrid_search should have been called for patterns table
        mock_ctx.deps.storage_service.hybrid_search.assert_called_once()


class TestQueryComplexity:
    """Tests for classify_query_complexity heuristic."""

    def test_simple_query(self):
        from second_brain.agents.utils import classify_query_complexity
        assert classify_query_complexity("patterns") == "simple"
        assert classify_query_complexity("voice guide") == "simple"
        assert classify_query_complexity("client list") == "simple"

    def test_medium_query(self):
        from second_brain.agents.utils import classify_query_complexity
        assert classify_query_complexity("client voice patterns for emails") == "medium"
        assert classify_query_complexity("what are our best practices") == "medium"

    def test_complex_query_by_length(self):
        from second_brain.agents.utils import classify_query_complexity
        long_query = "compare all our enterprise patterns with the new healthcare engagement and synthesize recommendations"
        assert classify_query_complexity(long_query) == "complex"

    def test_complex_query_by_comparison(self):
        from second_brain.agents.utils import classify_query_complexity
        assert classify_query_complexity("compare email patterns versus linkedin") == "complex"

    def test_complex_query_by_synthesis(self):
        from second_brain.agents.utils import classify_query_complexity
        assert classify_query_complexity("comprehensive overview of all patterns") == "complex"

    def test_complex_query_multi_question(self):
        from second_brain.agents.utils import classify_query_complexity
        assert classify_query_complexity("what works? what doesn't?") == "complex"

    def test_custom_threshold(self):
        from second_brain.agents.utils import classify_query_complexity
        # With threshold=4, a 5-word query becomes complex
        assert classify_query_complexity("client voice patterns for emails", word_threshold=4) == "complex"


class TestNormalizeResults:
    """Tests for normalize_results cross-source adapter."""

    def test_normalize_mem0_results(self):
        from second_brain.agents.utils import normalize_results
        mem0 = [{"memory": "test content", "score": 0.9}]
        result = normalize_results(mem0, source="mem0")
        assert len(result) == 1
        assert result[0]["memory"] == "test content"
        assert result[0]["score"] == 0.9
        assert result[0]["source"] == "mem0"

    def test_normalize_pgvector_results(self):
        from second_brain.agents.utils import normalize_results
        pg = [{"content": "pattern text", "similarity": 0.85, "title": "Hook First"}]
        result = normalize_results(pg, source="pgvector:patterns", content_key="content", score_key="similarity")
        assert result[0]["memory"] == "pattern text"
        assert result[0]["score"] == 0.85
        assert result[0]["source"] == "pgvector:patterns"
        assert result[0]["_original"]["title"] == "Hook First"

    def test_normalize_skips_empty_content(self):
        from second_brain.agents.utils import normalize_results
        results = [{"memory": "", "score": 0.5}, {"memory": "real", "score": 0.9}]
        normalized = normalize_results(results, source="test")
        assert len(normalized) == 1

    def test_normalize_empty_input(self):
        from second_brain.agents.utils import normalize_results
        assert normalize_results([], source="test") == []

    def test_normalize_hybrid_results(self):
        from second_brain.agents.utils import normalize_results
        hybrid = [{"content": "hybrid match", "similarity": 0.78, "search_type": "hybrid"}]
        result = normalize_results(hybrid, source="hybrid:memory_content", content_key="content", score_key="similarity")
        assert result[0]["source"] == "hybrid:memory_content"
        assert result[0]["_original"]["search_type"] == "hybrid"


class TestParallelSearchGather:
    """Tests for parallel_search_gather fault-tolerant fan-out."""

    async def test_all_succeed(self):
        from second_brain.agents.utils import parallel_search_gather
        async def source_a():
            return [{"memory": "a", "score": 0.9, "source": "a"}]
        async def source_b():
            return [{"memory": "b", "score": 0.8, "source": "b"}]
        results, sources = await parallel_search_gather([("a", source_a()), ("b", source_b())])
        assert len(results) == 2
        assert "a" in sources
        assert "b" in sources

    async def test_one_fails_gracefully(self):
        from second_brain.agents.utils import parallel_search_gather
        async def good():
            return [{"memory": "ok", "score": 0.9, "source": "good"}]
        async def bad():
            raise ConnectionError("network error")
        results, sources = await parallel_search_gather([("good", good()), ("bad", bad())])
        assert len(results) == 1
        assert "good" in sources
        assert "bad" not in sources

    async def test_all_fail_returns_empty(self):
        from second_brain.agents.utils import parallel_search_gather
        async def fail1():
            raise TimeoutError("timeout")
        async def fail2():
            raise ValueError("bad")
        results, sources = await parallel_search_gather([("f1", fail1()), ("f2", fail2())])
        assert results == []
        assert sources == []

    async def test_handles_search_result_objects(self):
        from second_brain.agents.utils import parallel_search_gather
        from second_brain.services.search_result import SearchResult
        async def mem0_search():
            return SearchResult(memories=[{"memory": "from mem0", "score": 0.88}], relations=[])
        results, sources = await parallel_search_gather([("mem0", mem0_search())])
        assert len(results) == 1
        assert results[0]["memory"] == "from mem0"
        assert "mem0" in sources


class TestChiefOfStaffComplexity:
    """Tests for chief_of_staff complexity tool."""

    def test_classify_complexity_tool_exists(self):
        from second_brain.agents.chief_of_staff import chief_of_staff
        tools = list(chief_of_staff._function_toolset.tools)
        assert "classify_complexity" in tools

    async def test_classify_complexity_returns_string(self, mock_deps):
        from second_brain.agents.chief_of_staff import chief_of_staff
        from unittest.mock import MagicMock
        ctx = MagicMock()
        ctx.deps = mock_deps
        tool = chief_of_staff._function_toolset.tools["classify_complexity"]
        result = await tool.function(ctx, query="patterns")
        assert "simple" in result.lower()


class TestParallelMultiTableSearch:
    """Tests for parallel_multi_table_search utility."""

    async def test_searches_all_four_tables(self, mock_deps):
        """Should attempt all 4 tables and return without error."""
        from second_brain.agents.utils import parallel_multi_table_search
        results, sources = await parallel_multi_table_search(mock_deps, "test query")
        assert isinstance(results, list)
        assert isinstance(sources, list)

    async def test_searches_specific_tables(self, mock_deps):
        """Should only search specified tables."""
        from second_brain.agents.utils import parallel_multi_table_search
        mock_deps.storage_service.search_patterns_semantic = AsyncMock(
            return_value=[{"content": "pattern result", "similarity": 0.9}]
        )
        results, sources = await parallel_multi_table_search(
            mock_deps, "test", tables=["patterns"]
        )
        mock_deps.storage_service.search_patterns_semantic.assert_called_once()

    async def test_skips_without_embedding_service(self, mock_deps):
        """Should return empty when no embedding service."""
        from second_brain.agents.utils import parallel_multi_table_search
        mock_deps.embedding_service = None
        results, sources = await parallel_multi_table_search(mock_deps, "test")
        assert results == []
        assert sources == []

    async def test_handles_partial_failure(self, mock_deps):
        """Failed tables should not block successful ones."""
        from second_brain.agents.utils import parallel_multi_table_search
        mock_deps.storage_service.search_patterns_semantic = AsyncMock(
            side_effect=ConnectionError("timeout")
        )
        mock_deps.storage_service.search_examples_semantic = AsyncMock(
            return_value=[{"content": "example", "similarity": 0.85}]
        )
        results, sources = await parallel_multi_table_search(
            mock_deps, "test", tables=["patterns", "examples"]
        )
        assert any("examples" in s for s in sources)


class TestParallelSearchSemanticMemory:
    """Tests for parallelized search_semantic_memory recall tool."""

    @pytest.fixture
    def mock_ctx(self, mock_deps):
        ctx = MagicMock()
        ctx.deps = mock_deps
        return ctx

    async def test_search_semantic_memory_with_embedding(self, mock_ctx):
        """search_semantic_memory runs parallel Mem0 + hybrid when embedding available."""
        from second_brain.agents.recall import recall_agent

        tool = recall_agent._function_toolset.tools["search_semantic_memory"]
        result = await tool.function(mock_ctx, query="test patterns")
        assert isinstance(result, str)
        mock_ctx.deps.memory_service.search.assert_called_once()

    async def test_search_semantic_memory_without_embedding(self, mock_ctx):
        """search_semantic_memory falls back to Mem0-only when no embedding service."""
        from second_brain.agents.recall import recall_agent

        mock_ctx.deps.embedding_service = None
        tool = recall_agent._function_toolset.tools["search_semantic_memory"]
        result = await tool.function(mock_ctx, query="test patterns")
        assert isinstance(result, str)
        mock_ctx.deps.memory_service.search.assert_called_once()

    async def test_search_semantic_memory_hybrid_called(self, mock_ctx):
        """When embedding available, hybrid_search should be called in parallel."""
        from second_brain.agents.recall import recall_agent

        tool = recall_agent._function_toolset.tools["search_semantic_memory"]
        await tool.function(mock_ctx, query="test patterns")
        mock_ctx.deps.storage_service.hybrid_search.assert_called_once()
        mock_ctx.deps.embedding_service.embed_query.assert_called_once()


class TestParallelSearchPatterns:
    """Tests for parallelized search_patterns recall tool."""

    @pytest.fixture
    def mock_ctx(self, mock_deps):
        ctx = MagicMock()
        ctx.deps = mock_deps
        return ctx

    async def test_search_patterns_with_embedding(self, mock_ctx):
        """search_patterns runs parallel hybrid + Mem0 when embedding available."""
        from second_brain.agents.recall import recall_agent

        tool = recall_agent._function_toolset.tools["search_patterns"]
        result = await tool.function(mock_ctx, topic="content")
        assert isinstance(result, str)

    async def test_search_patterns_fallback(self, mock_ctx):
        """search_patterns falls back to get_patterns when no results from parallel."""
        from second_brain.agents.recall import recall_agent
        from second_brain.services.search_result import SearchResult

        mock_ctx.deps.embedding_service = None
        mock_ctx.deps.memory_service.search_with_filters = AsyncMock(
            return_value=SearchResult(memories=[], relations=[])
        )
        mock_ctx.deps.storage_service.get_patterns = AsyncMock(return_value=[
            {"name": "Test", "confidence": "HIGH", "pattern_text": "test pattern text"},
        ])

        tool = recall_agent._function_toolset.tools["search_patterns"]
        result = await tool.function(mock_ctx, topic="test")
        assert "Pattern Registry" in result or "Test" in result

    async def test_search_patterns_hybrid_and_mem0_parallel(self, mock_ctx):
        """Both hybrid and mem0 should be called when embedding available."""
        from second_brain.agents.recall import recall_agent

        tool = recall_agent._function_toolset.tools["search_patterns"]
        await tool.function(mock_ctx, topic="content")
        mock_ctx.deps.storage_service.hybrid_search.assert_called_once()
        mock_ctx.deps.memory_service.search_with_filters.assert_called_once()


class TestDeepRecallSearch:
    """Tests for deep_recall_search orchestrator."""

    async def test_deep_recall_returns_dict(self, mock_deps):
        from second_brain.agents.utils import deep_recall_search
        result = await deep_recall_search(mock_deps, "compare all patterns")
        assert isinstance(result, dict)
        assert "memories" in result
        assert "relations" in result
        assert "search_sources" in result
        assert "query" in result
        assert result["query"] == "compare all patterns"

    async def test_deep_recall_without_embedding(self, mock_deps):
        from second_brain.agents.utils import deep_recall_search
        mock_deps.embedding_service = None
        result = await deep_recall_search(mock_deps, "test query")
        # Should still work with just Mem0
        assert isinstance(result, dict)
        assert "memories" in result

    async def test_deep_recall_with_graphiti(self, mock_deps_with_graphiti_full):
        from second_brain.agents.utils import deep_recall_search
        result = await deep_recall_search(mock_deps_with_graphiti_full, "test")
        assert isinstance(result["relations"], list)

    async def test_deep_recall_handles_all_failures(self, mock_deps):
        from second_brain.agents.utils import deep_recall_search
        mock_deps.memory_service.search = AsyncMock(side_effect=ConnectionError("down"))
        mock_deps.embedding_service = None
        result = await deep_recall_search(mock_deps, "test")
        assert result["memories"] == []

    async def test_deep_recall_contributing_sources(self, mock_deps):
        """Sources that return results should be listed in search_sources."""
        from second_brain.agents.utils import deep_recall_search
        from second_brain.services.search_result import SearchResult

        mock_deps.memory_service.search = AsyncMock(return_value=SearchResult(
            memories=[{"memory": "test content", "score": 0.9}],
            relations=[],
        ))
        mock_deps.storage_service.hybrid_search = AsyncMock(return_value=[
            {"content": "hybrid result", "similarity": 0.8},
        ])
        result = await deep_recall_search(mock_deps, "test query")
        assert "mem0" in result["search_sources"]
        assert "hybrid:memory_content" in result["search_sources"]

    async def test_deep_recall_searches_all_tables(self, mock_deps):
        """When embedding available, should search patterns, examples, knowledge, experiences."""
        from second_brain.agents.utils import deep_recall_search
        await deep_recall_search(mock_deps, "comprehensive query")
        mock_deps.storage_service.search_patterns_semantic.assert_called_once()
        mock_deps.storage_service.search_examples_semantic.assert_called_once()
        mock_deps.storage_service.search_knowledge_semantic.assert_called_once()
        mock_deps.storage_service.search_experiences_semantic.assert_called_once()


class TestRecallDeepMCPTool:
    """Tests for recall_deep MCP tool."""

    async def test_recall_deep_exists(self):
        from second_brain.mcp_server import server
        tools = server._tool_manager._tools
        assert "recall_deep" in tools

    async def test_recall_deep_validates_input(self):
        from second_brain.mcp_server import server
        tool = server._tool_manager._tools["recall_deep"]
        result = await tool.fn(query="", limit=10)
        assert "empty" in result.lower() or "invalid" in result.lower()

    @pytest.fixture
    def mock_deps_for_mcp(self, mock_deps):
        """Patch _get_deps for MCP tool tests."""
        return mock_deps

    async def test_recall_deep_returns_string(self, mock_deps):
        from second_brain.mcp_server import server
        import second_brain.mcp_server as mcp_mod

        original_get_deps = mcp_mod._get_deps
        mcp_mod._get_deps = lambda: mock_deps

        try:
            tool = server._tool_manager._tools["recall_deep"]
            result = await tool.fn(query="compare all patterns", limit=10)
            assert isinstance(result, str)
        finally:
            mcp_mod._get_deps = original_get_deps

    async def test_recall_deep_no_results(self, mock_deps):
        """When all sources return empty, should indicate no results."""
        from second_brain.mcp_server import server
        import second_brain.mcp_server as mcp_mod
        from second_brain.services.search_result import SearchResult

        mock_deps.memory_service.search = AsyncMock(
            return_value=SearchResult(memories=[], relations=[])
        )
        mock_deps.storage_service.hybrid_search = AsyncMock(return_value=[])
        mock_deps.storage_service.search_patterns_semantic = AsyncMock(return_value=[])
        mock_deps.storage_service.search_examples_semantic = AsyncMock(return_value=[])
        mock_deps.storage_service.search_knowledge_semantic = AsyncMock(return_value=[])
        mock_deps.storage_service.search_experiences_semantic = AsyncMock(return_value=[])

        original_get_deps = mcp_mod._get_deps
        mcp_mod._get_deps = lambda: mock_deps

        try:
            tool = server._tool_manager._tools["recall_deep"]
            result = await tool.fn(query="nonexistent topic xyz", limit=10)
            assert isinstance(result, str)
            assert "no results" in result.lower() or "No results" in result
        finally:
            mcp_mod._get_deps = original_get_deps


class TestComplexityAwareRouting:
    """Tests for complexity-aware quick_recall → recall_deep upgrade."""

    def test_simple_query_classified_correctly(self):
        """Simple queries should be classified as simple."""
        from second_brain.agents.utils import classify_query_complexity
        assert classify_query_complexity("patterns") == "simple"

    def test_complex_query_classified_correctly(self):
        """Complex queries should be classified as complex."""
        from second_brain.agents.utils import classify_query_complexity
        result = classify_query_complexity(
            "compare all enterprise patterns with healthcare engagement and synthesize recommendations"
        )
        assert result == "complex"

    def test_medium_query_classified_correctly(self):
        """Medium queries should be classified as medium."""
        from second_brain.agents.utils import classify_query_complexity
        result = classify_query_complexity("content writing patterns for LinkedIn")
        assert result == "medium"

    async def test_recall_agent_has_search_sources_instruction(self):
        """Recall agent instructions mention search_sources."""
        from second_brain.agents.recall import recall_agent
        # Check the instructions string
        instructions = recall_agent._instructions
        if callable(instructions):
            text = instructions(None)
        else:
            text = str(instructions)
        assert "search_sources" in text

    async def test_complex_query_redirects_to_deep(self, mock_deps):
        """Complex queries in quick_recall should redirect to recall_deep."""
        import second_brain.mcp_server as mcp_mod
        from second_brain.mcp_server import server

        original_get_deps = mcp_mod._get_deps
        mcp_mod._get_deps = lambda: mock_deps

        try:
            tool = server._tool_manager._tools["quick_recall"]
            result = await tool.fn(
                query="compare all enterprise patterns with healthcare engagement and synthesize recommendations",
                limit=10,
            )
            assert isinstance(result, str)
            # Deep recall path was used (output format differs from quick_recall)
            assert "Deep Recall" in result or "No results" in result or "deep" in result.lower()
        finally:
            mcp_mod._get_deps = original_get_deps
