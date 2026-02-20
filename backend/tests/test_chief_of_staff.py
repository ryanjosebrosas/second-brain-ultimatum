"""Tests for Chief of Staff orchestration agent."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from pydantic_ai import ModelRetry

from second_brain.agents.chief_of_staff import chief_of_staff
from second_brain.agents.registry import get_agent_registry
from second_brain.agents.utils import run_pipeline
from second_brain.schemas import RoutingDecision
from second_brain.config import BrainConfig
from second_brain.deps import BrainDeps


def _make_config():
    """Create a minimal BrainConfig for tests (no .env loading)."""
    return BrainConfig(
        supabase_url="https://test.supabase.co",
        supabase_key="test-key",
        brain_data_path="/fake/path",
        _env_file=None,
    )


class TestChiefOfStaffAgent:
    def test_agent_has_tools(self):
        tools = chief_of_staff._function_toolset.tools
        assert "load_brain_overview" in tools
        assert "search_brain_context" in tools
        assert "check_active_projects" in tools

    def test_agent_has_retries(self):
        assert chief_of_staff._max_result_retries == 3

    def test_output_type(self):
        assert chief_of_staff._output_type is RoutingDecision

    def test_has_output_validator(self):
        assert len(chief_of_staff._output_validators) > 0


class TestRoutingValidator:
    @pytest.mark.asyncio
    async def test_pipeline_without_steps_triggers_retry(self):
        output = RoutingDecision(
            target_agent="pipeline",
            reasoning="Multi-step needed",
            pipeline_steps=[],  # empty!
        )
        ctx = MagicMock()
        validator = chief_of_staff._output_validators[0]
        # Call the underlying function directly to bypass wrap_validation_errors
        with pytest.raises(ModelRetry):
            await validator.function(ctx, output)

    @pytest.mark.asyncio
    async def test_empty_reasoning_triggers_retry(self):
        output = RoutingDecision(
            target_agent="recall",
            reasoning="",
        )
        ctx = MagicMock()
        validator = chief_of_staff._output_validators[0]
        with pytest.raises(ModelRetry):
            await validator.function(ctx, output)

    @pytest.mark.asyncio
    async def test_valid_routing_passes(self):
        output = RoutingDecision(
            target_agent="create",
            reasoning="User wants content creation",
        )
        ctx = MagicMock()
        validator = chief_of_staff._output_validators[0]
        result = await validator.function(ctx, output)
        assert result.target_agent == "create"

    @pytest.mark.asyncio
    async def test_valid_pipeline_passes(self):
        output = RoutingDecision(
            target_agent="pipeline",
            reasoning="Content creation needs multiple steps",
            pipeline_steps=["recall", "create", "review"],
        )
        ctx = MagicMock()
        validator = chief_of_staff._output_validators[0]
        result = await validator.function(ctx, output)
        assert len(result.pipeline_steps) == 3

    @pytest.mark.asyncio
    async def test_pipeline_with_steps_does_not_trigger_retry(self):
        output = RoutingDecision(
            target_agent="pipeline",
            reasoning="Needs recall then ask",
            pipeline_steps=["recall", "ask"],
        )
        ctx = MagicMock()
        validator = chief_of_staff._output_validators[0]
        result = await validator.function(ctx, output)
        assert result.target_agent == "pipeline"


class TestConversationalRoute:
    def test_conversational_is_valid_route(self):
        """Verify 'conversational' is a valid AgentRoute for routing decisions."""
        decision = RoutingDecision(
            target_agent="conversational",
            reasoning="User sent a greeting",
        )
        assert decision.target_agent == "conversational"

    def test_conversational_in_chief_instructions(self):
        instructions = chief_of_staff._instructions
        assert "conversational" in instructions.lower(), (
            "Chief of staff instructions must include conversational routing rule"
        )


class TestAgentRegistry:
    def test_registry_has_core_agents(self):
        registry = get_agent_registry()
        assert "recall" in registry
        assert "ask" in registry
        assert "learn" in registry
        assert "create" in registry
        assert "review" in registry

    def test_registry_returns_tuples(self):
        registry = get_agent_registry()
        agent, description = registry["recall"]
        assert description == "Semantic memory search"
        assert hasattr(agent, "run")  # is an Agent instance

    def test_registry_ask_tuple(self):
        registry = get_agent_registry()
        agent, description = registry["ask"]
        assert description == "Contextual Q&A with brain knowledge"
        assert hasattr(agent, "run")

    def test_registry_create_tuple(self):
        registry = get_agent_registry()
        agent, description = registry["create"]
        assert description == "Content creation with voice and patterns"

    def test_registry_review_tuple(self):
        registry = get_agent_registry()
        agent, description = registry["review"]
        assert description == "Single-dimension content review"

    def test_registry_learn_tuple(self):
        registry = get_agent_registry()
        agent, description = registry["learn"]
        assert description == "Pattern extraction and learning"

    def test_registry_is_dict(self):
        registry = get_agent_registry()
        assert isinstance(registry, dict)

    def test_registry_at_least_five_agents(self):
        registry = get_agent_registry()
        assert len(registry) >= 5


class TestPipeline:
    @pytest.mark.asyncio
    async def test_pipeline_function_exists(self):
        """Pipeline function is importable and callable."""
        assert callable(run_pipeline)

    @pytest.mark.asyncio
    async def test_pipeline_handles_missing_agent(self):
        """Pipeline should skip unknown agent names gracefully."""
        config = _make_config()
        deps = BrainDeps(
            config=config,
            memory_service=MagicMock(),
            storage_service=MagicMock(),
        )
        # Run with non-existent agent
        results = await run_pipeline(
            steps=["nonexistent_agent"],
            initial_prompt="test",
            deps=deps,
        )
        assert "nonexistent_agent" not in results or results.get("nonexistent_agent") is None

    @pytest.mark.asyncio
    async def test_pipeline_empty_steps_returns_final_none(self):
        """Pipeline with empty steps returns final=None."""
        config = _make_config()
        deps = BrainDeps(
            config=config,
            memory_service=MagicMock(),
            storage_service=MagicMock(),
        )
        results = await run_pipeline(
            steps=[],
            initial_prompt="test",
            deps=deps,
        )
        assert results["final"] is None

    @pytest.mark.asyncio
    async def test_pipeline_step_error_is_recorded(self):
        """Pipeline records step errors without crashing."""
        config = _make_config()
        mock_storage = MagicMock()
        deps = BrainDeps(
            config=config,
            memory_service=MagicMock(),
            storage_service=mock_storage,
        )
        # Mock the recall agent to raise an exception
        with patch("second_brain.agents.recall.recall_agent") as mock_agent:
            mock_agent.run = AsyncMock(side_effect=RuntimeError("test error"))
            results = await run_pipeline(
                steps=["recall"],
                initial_prompt="test",
                deps=deps,
            )
        # Should not crash; recall key should be in results with error info or missing
        assert "final" in results


class TestChiefOfStaffTools:
    @pytest.mark.asyncio
    async def test_load_brain_overview_with_patterns(self):
        """Brain overview tool returns pattern and experience info."""
        config = _make_config()
        mock_storage = MagicMock()
        mock_storage.get_patterns = AsyncMock(return_value=[
            {"topic": "Content", "name": "Hook Pattern"},
            {"topic": "Messaging", "name": "Value Prop"},
        ])
        mock_storage.get_experiences = AsyncMock(return_value=[{"name": "test"}])

        deps = BrainDeps(
            config=config,
            memory_service=MagicMock(),
            storage_service=mock_storage,
        )

        ctx = MagicMock()
        ctx.deps = deps

        tool_fn = chief_of_staff._function_toolset.tools["load_brain_overview"]
        result = await tool_fn.function(ctx)
        assert "Patterns: 2" in result

    @pytest.mark.asyncio
    async def test_load_brain_overview_empty_brain(self):
        """Brain overview returns helpful message for empty brain."""
        config = _make_config()
        mock_storage = MagicMock()
        mock_storage.get_patterns = AsyncMock(return_value=[])
        mock_storage.get_experiences = AsyncMock(return_value=[])

        deps = BrainDeps(
            config=config,
            memory_service=MagicMock(),
            storage_service=mock_storage,
        )

        ctx = MagicMock()
        ctx.deps = deps

        # Patch get_content_type_registry to raise so it's skipped
        deps.get_content_type_registry = MagicMock(side_effect=Exception("no registry"))

        tool_fn = chief_of_staff._function_toolset.tools["load_brain_overview"]
        result = await tool_fn.function(ctx)
        assert "empty" in result.lower() or "learn" in result.lower()

    @pytest.mark.asyncio
    async def test_check_active_projects_no_projects(self):
        """check_active_projects returns 'No active projects.' when none found."""
        config = _make_config()
        mock_storage = MagicMock()
        mock_storage.list_projects = AsyncMock(return_value=[])

        deps = BrainDeps(
            config=config,
            memory_service=MagicMock(),
            storage_service=mock_storage,
        )

        ctx = MagicMock()
        ctx.deps = deps

        tool_fn = chief_of_staff._function_toolset.tools["check_active_projects"]
        result = await tool_fn.function(ctx)
        assert "No active projects" in result

    @pytest.mark.asyncio
    async def test_check_active_projects_with_projects(self):
        """check_active_projects lists active project names."""
        config = _make_config()
        mock_storage = MagicMock()
        mock_storage.list_projects = AsyncMock(return_value=[
            {"name": "Blog Campaign", "lifecycle_stage": "executing"},
            {"name": "Q1 Report", "lifecycle_stage": "executing"},
        ])

        deps = BrainDeps(
            config=config,
            memory_service=MagicMock(),
            storage_service=mock_storage,
        )

        ctx = MagicMock()
        ctx.deps = deps

        tool_fn = chief_of_staff._function_toolset.tools["check_active_projects"]
        result = await tool_fn.function(ctx)
        assert "Blog Campaign" in result
        assert "Q1 Report" in result

    @pytest.mark.asyncio
    async def test_search_brain_context_no_results(self):
        """search_brain_context returns friendly message when no results."""
        config = _make_config()
        mock_memory = MagicMock()
        mock_memory.search = AsyncMock(return_value=[])

        deps = BrainDeps(
            config=config,
            memory_service=mock_memory,
            storage_service=MagicMock(),
        )

        ctx = MagicMock()
        ctx.deps = deps

        tool_fn = chief_of_staff._function_toolset.tools["search_brain_context"]
        result = await tool_fn.function(ctx, "test query")
        assert "No relevant context" in result
