"""Tests for the LinkedIn Hook Writer agent."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from pydantic_ai import ModelRetry

from second_brain.agents.hook_writer import hook_writer_agent, HOOK_CATEGORIES
from second_brain.schemas import HookWriterResult


class TestHookWriterAgent:
    """Agent structure tests."""

    def test_has_tools(self):
        tools = hook_writer_agent._function_toolset.tools
        assert "load_voice_guide" in tools
        assert "search_hook_examples" in tools
        assert "search_past_content" in tools

    def test_has_retries(self):
        assert hook_writer_agent._max_result_retries == 3

    def test_has_validator(self):
        assert len(hook_writer_agent._output_validators) > 0

    def test_hook_categories_defined(self):
        assert len(HOOK_CATEGORIES) >= 8
        assert "bold-statement" in HOOK_CATEGORIES
        assert "curiosity-gap" in HOOK_CATEGORIES
        assert "self-deprecating" in HOOK_CATEGORIES
        assert "contrarian" in HOOK_CATEGORIES
        assert "stat-lead" in HOOK_CATEGORIES
        assert "question" in HOOK_CATEGORIES
        assert "dialogue-scene" in HOOK_CATEGORIES
        assert "meta-platform" in HOOK_CATEGORIES


class TestHookWriterValidator:
    """Output validator tests."""

    @pytest.mark.asyncio
    async def test_error_bypass(self):
        output = HookWriterResult(
            hooks=[], hook_type="", topic_angle="",
            error="BACKEND_ERROR: memory unavailable"
        )
        ctx = MagicMock()
        result = await hook_writer_agent._output_validators[0].validate(
            output, ctx, wrap_validation_errors=False
        )
        assert result.error

    @pytest.mark.asyncio
    async def test_too_few_hooks_retries(self):
        output = HookWriterResult(
            hooks=["Only one hook"], hook_type="bold-statement",
            topic_angle="test"
        )
        ctx = MagicMock()
        with pytest.raises(ModelRetry, match="at least 3"):
            await hook_writer_agent._output_validators[0].validate(
                output, ctx, wrap_validation_errors=False
            )

    @pytest.mark.asyncio
    async def test_empty_hooks_retries(self):
        output = HookWriterResult(
            hooks=[], hook_type="bold-statement", topic_angle="test"
        )
        ctx = MagicMock()
        with pytest.raises(ModelRetry, match="at least 3"):
            await hook_writer_agent._output_validators[0].validate(
                output, ctx, wrap_validation_errors=False
            )

    @pytest.mark.asyncio
    async def test_long_hook_retries(self):
        output = HookWriterResult(
            hooks=["x" * 221, "Short hook", "Another hook"],
            hook_type="bold-statement", topic_angle="test"
        )
        ctx = MagicMock()
        with pytest.raises(ModelRetry, match="220 characters"):
            await hook_writer_agent._output_validators[0].validate(
                output, ctx, wrap_validation_errors=False
            )

    @pytest.mark.asyncio
    async def test_missing_hook_type_retries(self):
        output = HookWriterResult(
            hooks=["Hook 1", "Hook 2", "Hook 3"],
            hook_type="", topic_angle="test"
        )
        ctx = MagicMock()
        with pytest.raises(ModelRetry, match="hook_type"):
            await hook_writer_agent._output_validators[0].validate(
                output, ctx, wrap_validation_errors=False
            )

    @pytest.mark.asyncio
    async def test_valid_output_passes(self):
        output = HookWriterResult(
            hooks=["Hook one.", "Hook two.", "Hook three."],
            hook_type="bold-statement",
            topic_angle="coaching business launch",
            reasoning="Bold statements work for achievement posts"
        )
        ctx = MagicMock()
        result = await hook_writer_agent._output_validators[0].validate(
            output, ctx, wrap_validation_errors=False
        )
        assert len(result.hooks) == 3
        assert result.hook_type == "bold-statement"

    @pytest.mark.asyncio
    async def test_exactly_three_hooks_passes(self):
        output = HookWriterResult(
            hooks=["Hook A", "Hook B", "Hook C"],
            hook_type="question",
            topic_angle="freelancing",
        )
        ctx = MagicMock()
        result = await hook_writer_agent._output_validators[0].validate(
            output, ctx, wrap_validation_errors=False
        )
        assert len(result.hooks) == 3

    @pytest.mark.asyncio
    async def test_hook_at_exact_220_chars_passes(self):
        output = HookWriterResult(
            hooks=["x" * 220, "Short", "Medium length hook"],
            hook_type="bold-statement",
            topic_angle="test",
        )
        ctx = MagicMock()
        result = await hook_writer_agent._output_validators[0].validate(
            output, ctx, wrap_validation_errors=False
        )
        assert len(result.hooks) == 3


class TestHookWriterTools:
    """Tool function tests."""

    @pytest.mark.asyncio
    async def test_load_voice_guide(self, mock_deps):
        ctx = MagicMock()
        ctx.deps = mock_deps
        tool_fn = hook_writer_agent._function_toolset.tools["load_voice_guide"]
        result = await tool_fn.function(ctx)
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_search_hook_examples_empty(self, mock_deps):
        ctx = MagicMock()
        ctx.deps = mock_deps
        mock_deps.storage_service.get_templates = AsyncMock(return_value=[])
        tool_fn = hook_writer_agent._function_toolset.tools["search_hook_examples"]
        result = await tool_fn.function(ctx, topic="coaching")
        assert "No LinkedIn templates" in result

    @pytest.mark.asyncio
    async def test_search_hook_examples_with_data(self, mock_deps):
        ctx = MagicMock()
        ctx.deps = mock_deps
        mock_deps.storage_service.get_templates = AsyncMock(return_value=[
            {"name": "Origin Story", "body": "It was 2020...\nMore text", "tags": ["storytelling"]},
        ])
        tool_fn = hook_writer_agent._function_toolset.tools["search_hook_examples"]
        result = await tool_fn.function(ctx, topic="coaching")
        assert "Origin Story" in result
        assert "It was 2020..." in result

    @pytest.mark.asyncio
    async def test_search_hook_examples_error(self, mock_deps):
        ctx = MagicMock()
        ctx.deps = mock_deps
        mock_deps.storage_service.get_templates = AsyncMock(side_effect=Exception("DB error"))
        tool_fn = hook_writer_agent._function_toolset.tools["search_hook_examples"]
        result = await tool_fn.function(ctx, topic="coaching")
        assert "BACKEND_ERROR:" in result

    @pytest.mark.asyncio
    async def test_search_past_content_empty(self, mock_deps):
        from second_brain.services.search_result import SearchResult
        ctx = MagicMock()
        ctx.deps = mock_deps
        mock_deps.memory_service.search = AsyncMock(
            return_value=SearchResult(memories=[], relations=[])
        )
        tool_fn = hook_writer_agent._function_toolset.tools["search_past_content"]
        result = await tool_fn.function(ctx, topic="coaching")
        assert "No past LinkedIn hooks" in result

    @pytest.mark.asyncio
    async def test_search_past_content_with_data(self, mock_deps):
        from second_brain.services.search_result import SearchResult
        ctx = MagicMock()
        ctx.deps = mock_deps
        mock_deps.memory_service.search = AsyncMock(
            return_value=SearchResult(
                memories=[{"memory": "Great hook about AI automation"}],
                relations=[],
            )
        )
        tool_fn = hook_writer_agent._function_toolset.tools["search_past_content"]
        result = await tool_fn.function(ctx, topic="AI")
        assert "Past LinkedIn content:" in result
        assert "AI automation" in result

    @pytest.mark.asyncio
    async def test_search_past_content_error(self, mock_deps):
        ctx = MagicMock()
        ctx.deps = mock_deps
        mock_deps.memory_service.search = AsyncMock(side_effect=Exception("Mem0 error"))
        tool_fn = hook_writer_agent._function_toolset.tools["search_past_content"]
        result = await tool_fn.function(ctx, topic="coaching")
        assert "BACKEND_ERROR:" in result


class TestHookWriterSchema:
    """Schema validation tests."""

    def test_minimal_valid(self):
        result = HookWriterResult(
            hooks=["Hook"], hook_type="bold-statement", topic_angle="test"
        )
        assert result.error == ""
        assert result.reasoning == ""

    def test_with_error(self):
        result = HookWriterResult(
            hooks=[], hook_type="", topic_angle="",
            error="BACKEND_ERROR: service down"
        )
        assert result.error.startswith("BACKEND_ERROR:")

    def test_full_result(self):
        result = HookWriterResult(
            hooks=["Hook 1", "Hook 2", "Hook 3"],
            hook_type="curiosity-gap",
            topic_angle="AI automation",
            reasoning="Curiosity gaps work for tech topics"
        )
        assert len(result.hooks) == 3
        assert result.hook_type == "curiosity-gap"
        assert result.reasoning

    def test_default_fields(self):
        result = HookWriterResult(
            hooks=["H1"], hook_type="question", topic_angle="test"
        )
        assert result.error == ""
        assert result.reasoning == ""
        assert result.hooks == ["H1"]


class TestSeedTemplates:
    """Seed template definitions tests."""

    def test_seed_templates_count(self):
        from scripts.seed_linkedin_templates import SEED_TEMPLATES
        assert len(SEED_TEMPLATES) == 10

    def test_seed_templates_structure(self):
        from scripts.seed_linkedin_templates import SEED_TEMPLATES
        required_keys = {"name", "content_type", "body", "description",
                         "structure_hint", "writeprint", "when_to_use",
                         "when_not_to_use", "customization_guide", "tags"}
        for tmpl in SEED_TEMPLATES:
            missing = required_keys - set(tmpl.keys())
            assert not missing, f"Template '{tmpl.get('name')}' missing keys: {missing}"
            assert tmpl["content_type"] == "linkedin"
            assert len(tmpl["body"]) > 50, f"Template '{tmpl['name']}' body too short"
            assert len(tmpl["tags"]) >= 2, f"Template '{tmpl['name']}' needs >= 2 tags"

    def test_seed_templates_unique_names(self):
        from scripts.seed_linkedin_templates import SEED_TEMPLATES
        names = [t["name"] for t in SEED_TEMPLATES]
        assert len(names) == len(set(names)), f"Duplicate names: {names}"

    def test_seed_templates_all_linkedin(self):
        from scripts.seed_linkedin_templates import SEED_TEMPLATES
        for tmpl in SEED_TEMPLATES:
            assert tmpl["content_type"] == "linkedin"


class TestCreateContentRequestStructureHint:
    """Test CreateContentRequest accepts structure_hint."""

    def test_structure_hint_default_empty(self):
        from second_brain.api.schemas import CreateContentRequest
        req = CreateContentRequest(prompt="test")
        assert req.structure_hint == ""

    def test_structure_hint_with_value(self):
        from second_brain.api.schemas import CreateContentRequest
        req = CreateContentRequest(
            prompt="test", structure_hint="[HOOK]\n[BODY]\n[CTA]"
        )
        assert req.structure_hint == "[HOOK]\n[BODY]\n[CTA]"

    def test_structure_hint_long_template_body(self):
        from second_brain.api.schemas import CreateContentRequest
        long_body = "[PLACEHOLDER]\n" * 200
        req = CreateContentRequest(prompt="test", structure_hint=long_body)
        assert len(req.structure_hint) > 2000


class TestHookWriterValidatorErrorDetection:
    """Tests for deterministic error detection in hook_writer_agent validator."""

    @pytest.fixture
    def mock_ctx_all_errors(self):
        """Context with all tool outputs showing errors."""
        from second_brain.agents.utils import TOOL_ERROR_PREFIX

        ctx = MagicMock()
        ctx.deps = MagicMock()

        msg1 = MagicMock()
        part1 = MagicMock()
        part1.content = f"{TOOL_ERROR_PREFIX} load_voice_guide: ConnectionError"
        msg1.parts = [part1]

        msg2 = MagicMock()
        part2 = MagicMock()
        part2.content = f"{TOOL_ERROR_PREFIX} search_hook_examples: TimeoutError"
        msg2.parts = [part2]

        ctx.messages = [msg1, msg2]
        return ctx

    @pytest.fixture
    def mock_ctx_partial_errors(self):
        """Context with some successful tool outputs."""
        from second_brain.agents.utils import TOOL_ERROR_PREFIX

        ctx = MagicMock()
        ctx.deps = MagicMock()

        msg1 = MagicMock()
        part1 = MagicMock()
        part1.content = f"{TOOL_ERROR_PREFIX} load_voice_guide: ConnectionError"
        msg1.parts = [part1]

        msg2 = MagicMock()
        part2 = MagicMock()
        part2.content = "Found 5 hook examples: curiosity, controversy..."
        msg2.parts = [part2]

        ctx.messages = [msg1, msg2]
        return ctx

    @pytest.mark.asyncio
    async def test_accepts_with_all_errors_and_sets_error_field(self, mock_ctx_all_errors):
        """Validator accepts and sets error when all tools failed."""
        output = HookWriterResult(
            hooks=["Hook one here", "Hook two here", "Hook three here"],
            hook_type="curiosity",
            topic_angle="AI productivity",
        )

        validator = hook_writer_agent._output_validators[0]
        result = await validator.function(mock_ctx_all_errors, output)

        assert result.error
        assert "unavailable" in result.error.lower()

    @pytest.mark.asyncio
    async def test_continues_validation_with_partial_errors(self, mock_ctx_partial_errors):
        """Validator continues normal validation when not all tools failed."""
        output = HookWriterResult(
            hooks=["First hook line", "Second hook line", "Third hook line"],
            hook_type="curiosity",
            topic_angle="AI productivity",
        )

        validator = hook_writer_agent._output_validators[0]
        result = await validator.function(mock_ctx_partial_errors, output)

        assert not result.error
        assert len(result.hooks) >= 3

    @pytest.mark.asyncio
    async def test_insufficient_hooks_still_fails_without_all_errors(self, mock_ctx_partial_errors):
        """Validator still enforces minimum hook count when backends are partially up."""
        output = HookWriterResult(
            hooks=["Only one hook"],
            hook_type="curiosity",
            topic_angle="AI productivity",
        )

        validator = hook_writer_agent._output_validators[0]
        with pytest.raises(ModelRetry):
            await validator.function(mock_ctx_partial_errors, output)
