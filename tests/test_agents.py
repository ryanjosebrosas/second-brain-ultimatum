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

    def test_content_types_registry(self):
        assert "linkedin" in DEFAULT_CONTENT_TYPES
        assert "email" in DEFAULT_CONTENT_TYPES
        assert "landing-page" in DEFAULT_CONTENT_TYPES
        assert "comment" in DEFAULT_CONTENT_TYPES
        assert len(DEFAULT_CONTENT_TYPES) == 9

    def test_content_type_defaults(self):
        linkedin = DEFAULT_CONTENT_TYPES["linkedin"]
        assert linkedin.default_mode == "casual"
        assert linkedin.max_words == 300
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
        assert len(DEFAULT_CONTENT_TYPES) == 9

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
        assert len(DEFAULT_CONTENT_TYPES) == 9

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
        from second_brain.schemas import content_type_from_row
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
        from second_brain.schemas import content_type_from_row
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
        from second_brain.schemas import content_type_from_row
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
