"""Tests for agentic behavior upgrades on existing agents."""

import pytest
from unittest.mock import MagicMock
from pydantic_ai import ModelRetry

from second_brain.agents.recall import recall_agent
from second_brain.agents.ask import ask_agent
from second_brain.agents.learn import learn_agent
from second_brain.agents.create import create_agent
from second_brain.agents.review import review_agent
from second_brain.schemas import (
    RecallResult, AskResult, LearnResult, CreateResult,
    DimensionScore, PatternExtract, MemoryMatch,
)


# --- Retry Configuration ---

class TestRetryConfig:
    def test_recall_has_retries(self):
        assert recall_agent._max_result_retries == 3

    def test_ask_has_retries(self):
        assert ask_agent._max_result_retries == 3

    def test_learn_has_retries(self):
        assert learn_agent._max_result_retries == 3

    def test_create_has_retries(self):
        assert create_agent._max_result_retries == 3

    def test_review_has_retries(self):
        assert review_agent._max_result_retries == 3


# --- Output Validator Tests ---

class TestRecallValidator:
    @pytest.mark.asyncio
    async def test_empty_results_triggers_retry(self):
        """Recall validator should retry when all result lists are empty."""
        output = RecallResult(query="test query")
        ctx = MagicMock()
        validators = recall_agent._output_validators
        assert len(validators) > 0
        with pytest.raises(ModelRetry):
            await validators[0].validate(output, ctx, wrap_validation_errors=False)

    @pytest.mark.asyncio
    async def test_results_pass_validation(self):
        """Recall validator should pass when matches are found."""
        output = RecallResult(
            query="test",
            matches=[MemoryMatch(content="found something", relevance="HIGH")],
        )
        ctx = MagicMock()
        validators = recall_agent._output_validators
        result = await validators[0].validate(output, ctx, wrap_validation_errors=False)
        assert result == output

    @pytest.mark.asyncio
    async def test_patterns_only_pass_validation(self):
        """Recall validator should pass when only patterns are found."""
        output = RecallResult(
            query="test",
            patterns=["Hook-Then-Value Structure"],
        )
        ctx = MagicMock()
        validators = recall_agent._output_validators
        result = await validators[0].validate(output, ctx, wrap_validation_errors=False)
        assert result == output


class TestAskValidator:
    @pytest.mark.asyncio
    async def test_brief_answer_triggers_retry(self):
        """Ask validator should retry on very short answers."""
        output = AskResult(answer="I don't know.")
        ctx = MagicMock()
        validators = ask_agent._output_validators
        assert len(validators) > 0
        with pytest.raises(ModelRetry):
            await validators[0].validate(output, ctx, wrap_validation_errors=False)

    @pytest.mark.asyncio
    async def test_no_context_triggers_retry(self):
        """Ask validator should retry when no context was referenced."""
        output = AskResult(answer="A" * 100)  # long enough but no context
        ctx = MagicMock()
        validators = ask_agent._output_validators
        with pytest.raises(ModelRetry):
            await validators[0].validate(output, ctx, wrap_validation_errors=False)

    @pytest.mark.asyncio
    async def test_good_answer_passes(self):
        """Ask validator should pass a complete, grounded answer."""
        output = AskResult(
            answer="A" * 100,
            context_used=["style-voice/brand-voice.md"],
            confidence="HIGH",
        )
        ctx = MagicMock()
        validators = ask_agent._output_validators
        result = await validators[0].validate(output, ctx, wrap_validation_errors=False)
        assert result == output

    @pytest.mark.asyncio
    async def test_patterns_applied_satisfies_context_check(self):
        """Ask validator should pass when patterns_applied is set (no context_used needed)."""
        output = AskResult(
            answer="A" * 100,
            patterns_applied=["Hook-Then-Value Structure"],
        )
        ctx = MagicMock()
        validators = ask_agent._output_validators
        result = await validators[0].validate(output, ctx, wrap_validation_errors=False)
        assert result == output


class TestLearnValidator:
    @pytest.mark.asyncio
    async def test_empty_extraction_triggers_retry(self):
        """Learn validator should retry when nothing was extracted."""
        output = LearnResult(input_summary="Test input")
        ctx = MagicMock()
        validators = learn_agent._output_validators
        assert len(validators) > 0
        with pytest.raises(ModelRetry):
            await validators[0].validate(output, ctx, wrap_validation_errors=False)

    @pytest.mark.asyncio
    async def test_short_pattern_name_triggers_retry(self):
        """Learn validator should reject generic pattern names."""
        output = LearnResult(
            input_summary="Test",
            patterns_extracted=[
                PatternExtract(name="hook", topic="Content", pattern_text="Use hooks")
            ],
        )
        ctx = MagicMock()
        validators = learn_agent._output_validators
        with pytest.raises(ModelRetry):
            await validators[0].validate(output, ctx, wrap_validation_errors=False)

    @pytest.mark.asyncio
    async def test_pattern_without_evidence_triggers_retry(self):
        """Learn validator should require evidence for patterns."""
        output = LearnResult(
            input_summary="Test",
            patterns_extracted=[
                PatternExtract(
                    name="Hook-Then-Value Structure",
                    topic="Content",
                    pattern_text="Start with hook, follow with value",
                    evidence=[],  # no evidence!
                )
            ],
        )
        ctx = MagicMock()
        validators = learn_agent._output_validators
        with pytest.raises(ModelRetry):
            await validators[0].validate(output, ctx, wrap_validation_errors=False)

    @pytest.mark.asyncio
    async def test_good_pattern_passes(self):
        """Learn validator should pass valid pattern extraction."""
        output = LearnResult(
            input_summary="Test session",
            patterns_extracted=[
                PatternExtract(
                    name="Hook-Then-Value Structure",
                    topic="Content",
                    pattern_text="Start with a hook, deliver value immediately",
                    evidence=["Example from post: 'The algorithm doesn't care...'"],
                )
            ],
        )
        ctx = MagicMock()
        validators = learn_agent._output_validators
        result = await validators[0].validate(output, ctx, wrap_validation_errors=False)
        assert result == output

    @pytest.mark.asyncio
    async def test_insights_only_passes(self):
        """Learn validator should pass when only insights are extracted."""
        output = LearnResult(
            input_summary="Test",
            insights=["Consistency beats perfection in content creation"],
        )
        ctx = MagicMock()
        validators = learn_agent._output_validators
        result = await validators[0].validate(output, ctx, wrap_validation_errors=False)
        assert result == output

    @pytest.mark.asyncio
    async def test_experience_recorded_passes(self):
        """Learn validator should pass when only experience_recorded is set."""
        output = LearnResult(
            input_summary="Test",
            experience_recorded=True,
        )
        ctx = MagicMock()
        validators = learn_agent._output_validators
        result = await validators[0].validate(output, ctx, wrap_validation_errors=False)
        assert result == output


class TestCreateValidator:
    @pytest.mark.asyncio
    async def test_short_draft_triggers_retry(self):
        """Create validator should retry on very short drafts."""
        output = CreateResult(
            draft="Hello world",
            content_type="linkedin",
            mode="casual",
        )
        ctx = MagicMock()
        validators = create_agent._output_validators
        assert len(validators) > 0
        with pytest.raises(ModelRetry):
            await validators[0].validate(output, ctx, wrap_validation_errors=False)

    @pytest.mark.asyncio
    async def test_summary_draft_triggers_retry(self):
        """Create validator should catch summary-instead-of-draft."""
        output = CreateResult(
            draft="Here is a draft of a LinkedIn post about AI agents and their impact on productivity...",
            content_type="linkedin",
            mode="casual",
            voice_elements=["conversational"],
        )
        ctx = MagicMock()
        validators = create_agent._output_validators
        with pytest.raises(ModelRetry):
            await validators[0].validate(output, ctx, wrap_validation_errors=False)

    @pytest.mark.asyncio
    async def test_no_voice_triggers_retry(self):
        """Create validator should require voice elements."""
        output = CreateResult(
            draft="A" * 200,  # long enough
            content_type="linkedin",
            mode="casual",
            voice_elements=[],  # no voice!
        )
        ctx = MagicMock()
        validators = create_agent._output_validators
        with pytest.raises(ModelRetry):
            await validators[0].validate(output, ctx, wrap_validation_errors=False)

    @pytest.mark.asyncio
    async def test_good_draft_passes(self):
        """Create validator should pass a complete draft with voice."""
        output = CreateResult(
            draft="The future of AI agents isn't about replacement " * 20,
            content_type="linkedin",
            mode="casual",
            voice_elements=["conversational", "direct"],
        )
        ctx = MagicMock()
        validators = create_agent._output_validators
        result = await validators[0].validate(output, ctx, wrap_validation_errors=False)
        assert result.word_count > 0  # auto-set by validator

    @pytest.mark.asyncio
    async def test_word_count_auto_set(self):
        """Create validator should set word_count when it's 0."""
        output = CreateResult(
            draft="Real content about AI agents and their capabilities " * 5,
            content_type="linkedin",
            mode="casual",
            voice_elements=["direct"],
            word_count=0,
        )
        ctx = MagicMock()
        validators = create_agent._output_validators
        result = await validators[0].validate(output, ctx, wrap_validation_errors=False)
        assert result.word_count > 0


class TestReviewValidator:
    @pytest.mark.asyncio
    async def test_invalid_score_triggers_retry(self):
        """Review validator should reject out-of-range scores."""
        output = DimensionScore(
            dimension="Messaging", score=11, status="pass",
        )
        ctx = MagicMock()
        validators = review_agent._output_validators
        assert len(validators) > 0
        with pytest.raises(ModelRetry):
            await validators[0].validate(output, ctx, wrap_validation_errors=False)

    @pytest.mark.asyncio
    async def test_zero_score_triggers_retry(self):
        """Review validator should reject score of 0."""
        output = DimensionScore(
            dimension="Messaging", score=0, status="issue",
            issues=["Major problem"],
        )
        ctx = MagicMock()
        validators = review_agent._output_validators
        with pytest.raises(ModelRetry):
            await validators[0].validate(output, ctx, wrap_validation_errors=False)

    @pytest.mark.asyncio
    async def test_mismatched_status_triggers_retry(self):
        """Review validator should catch score-status mismatch."""
        output = DimensionScore(
            dimension="Messaging", score=3, status="pass",
            issues=["Major problems"],
        )
        ctx = MagicMock()
        validators = review_agent._output_validators
        with pytest.raises(ModelRetry):
            await validators[0].validate(output, ctx, wrap_validation_errors=False)

    @pytest.mark.asyncio
    async def test_no_feedback_triggers_retry(self):
        """Review validator should require at least one strength or issue."""
        output = DimensionScore(
            dimension="Messaging", score=7, status="pass",
        )
        ctx = MagicMock()
        validators = review_agent._output_validators
        with pytest.raises(ModelRetry):
            await validators[0].validate(output, ctx, wrap_validation_errors=False)

    @pytest.mark.asyncio
    async def test_good_review_passes(self):
        """Review validator should pass a valid, consistent review."""
        output = DimensionScore(
            dimension="Messaging",
            score=8,
            status="pass",
            strengths=["Clear value proposition", "Strong hook"],
        )
        ctx = MagicMock()
        validators = review_agent._output_validators
        result = await validators[0].validate(output, ctx, wrap_validation_errors=False)
        assert result == output

    @pytest.mark.asyncio
    async def test_warning_status_matches_score(self):
        """Review validator should accept warning status for score 5-6."""
        output = DimensionScore(
            dimension="Messaging",
            score=5,
            status="warning",
            issues=["CTA could be stronger"],
            suggestions=["Consider strengthening the CTA"],
        )
        ctx = MagicMock()
        validators = review_agent._output_validators
        result = await validators[0].validate(output, ctx, wrap_validation_errors=False)
        assert result == output

    @pytest.mark.asyncio
    async def test_issue_status_matches_low_score(self):
        """Review validator should accept issue status for score 1-4."""
        output = DimensionScore(
            dimension="Messaging",
            score=3,
            status="issue",
            issues=["Missing value proposition entirely"],
        )
        ctx = MagicMock()
        validators = review_agent._output_validators
        result = await validators[0].validate(output, ctx, wrap_validation_errors=False)
        assert result == output


# --- Dynamic Instructions ---

class TestCreateDynamicInstructions:
    def test_has_dynamic_instructions(self):
        """Create agent should have dynamic instructions for content types."""
        assert len(create_agent._instructions_functions) > 0

    def test_learn_still_has_dynamic_instructions(self):
        """Learn agent should still have its existing dynamic instructions."""
        assert len(learn_agent._instructions_functions) > 0


# --- Existing Tools Still Registered ---

class TestExistingToolRegistration:
    """Verify existing tools are still registered after upgrades."""

    def test_recall_tools_intact(self):
        tools = recall_agent._function_toolset.tools
        assert "search_semantic_memory" in tools
        assert "search_patterns" in tools
        assert "search_experiences" in tools
        assert "search_examples" in tools

    def test_ask_tools_intact(self):
        tools = ask_agent._function_toolset.tools
        assert "load_brain_context" in tools
        assert "find_relevant_patterns" in tools

    def test_learn_tools_intact(self):
        tools = learn_agent._function_toolset.tools
        assert "store_pattern" in tools
        assert "search_existing_patterns" in tools

    def test_create_tools_intact(self):
        tools = create_agent._function_toolset.tools
        assert "load_voice_guide" in tools
        assert "validate_draft" in tools

    def test_review_tools_intact(self):
        tools = review_agent._function_toolset.tools
        assert "load_voice_reference" in tools
