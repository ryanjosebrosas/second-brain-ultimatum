"""Tests for operations agents: coach, pmo, email, specialist."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from pydantic_ai import ModelRetry

from second_brain.agents.coach import coach_agent
from second_brain.agents.pmo import pmo_agent
from second_brain.agents.email_agent import email_agent
from second_brain.agents.specialist import specialist_agent
from second_brain.schemas import (
    CoachSession, PMOResult, PriorityScore,
    EmailAction, SpecialistAnswer,
)


# --- Tool Registration ---

class TestAgentToolRegistration:
    def test_coach_tools(self):
        tools = coach_agent._function_toolset.tools
        assert "load_goals_context" in tools
        assert "search_past_sessions" in tools

    def test_pmo_tools(self):
        tools = pmo_agent._function_toolset.tools
        assert "load_strategic_context" in tools
        assert "get_scoring_weights" in tools

    def test_email_tools(self):
        tools = email_agent._function_toolset.tools
        assert "load_email_voice" in tools

    def test_specialist_tools(self):
        tools = specialist_agent._function_toolset.tools
        assert "search_codebase_knowledge" in tools
        assert "search_patterns_for_answer" in tools


# --- Retry Configuration ---

class TestRetryConfig:
    def test_all_have_retries(self):
        for name, agent in [
            ("coach", coach_agent), ("pmo", pmo_agent),
            ("email", email_agent), ("specialist", specialist_agent),
        ]:
            assert agent._max_result_retries == 3, f"{name} missing retries"


# --- Output Validators ---

class TestCoachValidator:
    @pytest.mark.asyncio
    async def test_no_next_action_triggers_retry(self):
        output = CoachSession(session_type="morning", next_action="")
        ctx = MagicMock()
        validator = coach_agent._output_validators[0]
        with pytest.raises(ModelRetry):
            await validator.validate(output, ctx, wrap_validation_errors=False)

    @pytest.mark.asyncio
    async def test_morning_without_priorities_triggers_retry(self):
        output = CoachSession(session_type="morning", next_action="Start work", priorities=[])
        ctx = MagicMock()
        validator = coach_agent._output_validators[0]
        with pytest.raises(ModelRetry):
            await validator.validate(output, ctx, wrap_validation_errors=False)

    @pytest.mark.asyncio
    async def test_valid_session_passes(self):
        output = CoachSession(
            session_type="check_in",
            next_action="Continue working on API docs",
            coaching_notes="Good progress so far",
        )
        ctx = MagicMock()
        validator = coach_agent._output_validators[0]
        result = await validator.validate(output, ctx, wrap_validation_errors=False)
        assert result.next_action == "Continue working on API docs"

    @pytest.mark.asyncio
    async def test_evening_without_priorities_passes(self):
        """Evening sessions don't require priorities."""
        output = CoachSession(
            session_type="evening",
            next_action="Review tomorrow's plan",
            priorities=[],
        )
        ctx = MagicMock()
        validator = coach_agent._output_validators[0]
        result = await validator.validate(output, ctx, wrap_validation_errors=False)
        assert result.session_type == "evening"


class TestPMOValidator:
    @pytest.mark.asyncio
    async def test_no_tasks_triggers_retry(self):
        output = PMOResult(coaching_message="Here's my advice")
        ctx = MagicMock()
        validator = pmo_agent._output_validators[0]
        with pytest.raises(ModelRetry):
            await validator.validate(output, ctx, wrap_validation_errors=False)

    @pytest.mark.asyncio
    async def test_no_coaching_triggers_retry(self):
        output = PMOResult(
            scored_tasks=[PriorityScore(task_name="Test", total_score=80)],
            coaching_message="",
        )
        ctx = MagicMock()
        validator = pmo_agent._output_validators[0]
        with pytest.raises(ModelRetry):
            await validator.validate(output, ctx, wrap_validation_errors=False)

    @pytest.mark.asyncio
    async def test_auto_categorization(self):
        output = PMOResult(
            scored_tasks=[
                PriorityScore(task_name="Urgent", total_score=85, effort=2),
                PriorityScore(task_name="Important", total_score=70, effort=7),
                PriorityScore(task_name="Backlog", total_score=40, effort=5),
            ],
            coaching_message="Focus on urgent task first",
        )
        ctx = MagicMock()
        validator = pmo_agent._output_validators[0]
        result = await validator.validate(output, ctx, wrap_validation_errors=False)
        assert "Urgent" in result.today_focus
        assert "Important" in result.this_week
        assert "Urgent" in result.quick_wins  # effort <= 3

    @pytest.mark.asyncio
    async def test_backlog_not_in_today_focus(self):
        output = PMOResult(
            scored_tasks=[PriorityScore(task_name="LowPriority", total_score=40, effort=5)],
            coaching_message="This can wait",
        )
        ctx = MagicMock()
        validator = pmo_agent._output_validators[0]
        result = await validator.validate(output, ctx, wrap_validation_errors=False)
        assert "LowPriority" not in result.today_focus
        assert "LowPriority" not in result.this_week


class TestEmailValidator:
    @pytest.mark.asyncio
    async def test_send_without_subject_triggers_retry(self):
        output = EmailAction(action_type="send", subject="", body="Hello")
        ctx = MagicMock()
        validator = email_agent._output_validators[0]
        with pytest.raises(ModelRetry):
            await validator.validate(output, ctx, wrap_validation_errors=False)

    @pytest.mark.asyncio
    async def test_short_body_triggers_retry(self):
        output = EmailAction(action_type="draft", subject="Test", body="Hi")
        ctx = MagicMock()
        validator = email_agent._output_validators[0]
        with pytest.raises(ModelRetry):
            await validator.validate(output, ctx, wrap_validation_errors=False)

    @pytest.mark.asyncio
    async def test_send_forced_to_draft(self):
        output = EmailAction(
            action_type="send", subject="Test", body="A" * 50,
            status="sent",
        )
        ctx = MagicMock()
        validator = email_agent._output_validators[0]
        result = await validator.validate(output, ctx, wrap_validation_errors=False)
        assert result.status == "draft"  # forced to draft

    @pytest.mark.asyncio
    async def test_search_action_no_subject_required(self):
        """Search action doesn't require subject."""
        output = EmailAction(action_type="search", subject="", body="")
        ctx = MagicMock()
        validator = email_agent._output_validators[0]
        result = await validator.validate(output, ctx, wrap_validation_errors=False)
        assert result.action_type == "search"


class TestSpecialistValidator:
    @pytest.mark.asyncio
    async def test_verified_without_sources_triggers_retry(self):
        output = SpecialistAnswer(
            answer="Use @agent.tool decorator for tool registration",
            confidence_level="VERIFIED",
            sources=[],  # no sources!
        )
        ctx = MagicMock()
        validator = specialist_agent._output_validators[0]
        with pytest.raises(ModelRetry):
            await validator.validate(output, ctx, wrap_validation_errors=False)

    @pytest.mark.asyncio
    async def test_uncertain_without_sources_passes(self):
        output = SpecialistAnswer(
            answer="I believe this might work based on general knowledge " * 3,
            confidence_level="UNCERTAIN",
        )
        ctx = MagicMock()
        validator = specialist_agent._output_validators[0]
        result = await validator.validate(output, ctx, wrap_validation_errors=False)
        assert result.confidence_level == "UNCERTAIN"

    @pytest.mark.asyncio
    async def test_verified_with_sources_passes(self):
        output = SpecialistAnswer(
            answer="Use @agent.tool decorator for tool registration. This is documented in the official Pydantic AI docs.",
            confidence_level="VERIFIED",
            sources=["https://ai.pydantic.dev/tools/"],
        )
        ctx = MagicMock()
        validator = specialist_agent._output_validators[0]
        result = await validator.validate(output, ctx, wrap_validation_errors=False)
        assert result.confidence_level == "VERIFIED"

    @pytest.mark.asyncio
    async def test_short_answer_triggers_retry(self):
        output = SpecialistAnswer(
            answer="Yes",
            confidence_level="LIKELY",
        )
        ctx = MagicMock()
        validator = specialist_agent._output_validators[0]
        with pytest.raises(ModelRetry):
            await validator.validate(output, ctx, wrap_validation_errors=False)


# --- Agent Registry ---

class TestRegistryCompleteness:
    def test_all_operations_agents_in_registry(self):
        from second_brain.agents.registry import get_agent_registry
        registry = get_agent_registry()
        for name in ["coach", "pmo", "email", "specialist"]:
            assert name in registry, f"'{name}' missing from registry"
        # Total: 5 original + chief of staff + 3 content + 4 operations = 13 (essay_writer removed)
        assert len(registry) >= 12

    def test_registry_descriptions_present(self):
        from second_brain.agents.registry import get_agent_registry
        registry = get_agent_registry()
        for name, (agent, desc) in registry.items():
            assert desc, f"'{name}' has empty description"
            assert agent is not None, f"'{name}' has None agent"
