"""Tests for the LinkedIn Writer agent."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from pydantic_ai import ModelRetry

from second_brain.agents.linkedin_writer import linkedin_writer_agent, POST_STRUCTURES
from second_brain.schemas import LinkedInPostResult


class TestLinkedInWriterAgent:
    """Agent structure tests."""

    def test_has_tools(self):
        tools = linkedin_writer_agent._function_toolset.tools
        assert "generate_hooks" in tools
        assert "load_voice_guide" in tools
        assert "load_linkedin_examples" in tools
        assert "find_linkedin_patterns" in tools
        assert "search_linkedin_templates" in tools
        assert "validate_draft" in tools

    def test_tool_count(self):
        assert len(linkedin_writer_agent._function_toolset.tools) == 6

    def test_has_retries(self):
        assert linkedin_writer_agent._max_result_retries == 3

    def test_has_validator(self):
        assert len(linkedin_writer_agent._output_validators) > 0

    def test_output_type(self):
        assert linkedin_writer_agent._output_type is LinkedInPostResult

    def test_post_structures_defined(self):
        assert len(POST_STRUCTURES) >= 7
        assert "origin-story" in POST_STRUCTURES
        assert "vulnerability-confession" in POST_STRUCTURES
        assert "results-breakdown" in POST_STRUCTURES
        assert "contrarian-advice" in POST_STRUCTURES
        assert "listicle" in POST_STRUCTURES
        assert "hot-take" in POST_STRUCTURES
        assert "freeform" in POST_STRUCTURES


class TestLinkedInWriterValidator:
    """Output validator tests."""

    @pytest.mark.asyncio
    async def test_error_bypass(self):
        output = LinkedInPostResult(
            draft="minimal", hook_used="", hook_type="", post_structure="freeform",
            error="BACKEND_ERROR: memory unavailable",
        )
        ctx = MagicMock()
        result = await linkedin_writer_agent._output_validators[0].validate(
            output, ctx, wrap_validation_errors=False
        )
        assert result.error

    @pytest.mark.asyncio
    async def test_empty_draft_retries(self):
        output = LinkedInPostResult(
            draft="Too short", hook_used="Hook", hook_type="bold-statement",
            post_structure="freeform",
        )
        ctx = MagicMock()
        with pytest.raises(ModelRetry, match="30 words"):
            await linkedin_writer_agent._output_validators[0].validate(
                output, ctx, wrap_validation_errors=False
            )

    @pytest.mark.asyncio
    async def test_missing_hook_retries(self):
        output = LinkedInPostResult(
            draft=" ".join(["word"] * 50),
            hook_used="", hook_type="bold-statement",
            post_structure="freeform",
        )
        ctx = MagicMock()
        with pytest.raises(ModelRetry, match="hook_used"):
            await linkedin_writer_agent._output_validators[0].validate(
                output, ctx, wrap_validation_errors=False
            )

    @pytest.mark.asyncio
    async def test_invalid_structure_retries(self):
        output = LinkedInPostResult(
            draft=" ".join(["word"] * 50),
            hook_used="A bold hook", hook_type="bold-statement",
            post_structure="invalid-structure",
        )
        ctx = MagicMock()
        with pytest.raises(ModelRetry, match="Invalid post_structure"):
            await linkedin_writer_agent._output_validators[0].validate(
                output, ctx, wrap_validation_errors=False
            )

    @pytest.mark.asyncio
    async def test_summary_instead_of_draft_retries(self):
        output = LinkedInPostResult(
            draft="Here is a draft about launching a coaching business " + " ".join(["word"] * 50),
            hook_used="A bold hook", hook_type="bold-statement",
            post_structure="freeform",
        )
        ctx = MagicMock()
        with pytest.raises(ModelRetry, match="DESCRIPTION"):
            await linkedin_writer_agent._output_validators[0].validate(
                output, ctx, wrap_validation_errors=False
            )

    @pytest.mark.asyncio
    async def test_valid_output_passes(self):
        draft = "I did it. $1M in earnings.\n\n" + " ".join(["word"] * 60)
        output = LinkedInPostResult(
            draft=draft,
            hook_used="I did it. $1M in earnings.",
            hook_type="bold-statement",
            post_structure="results-breakdown",
            voice_elements=["direct", "confident"],
            patterns_applied=["achievement-post"],
        )
        ctx = MagicMock()
        result = await linkedin_writer_agent._output_validators[0].validate(
            output, ctx, wrap_validation_errors=False
        )
        assert result.draft == draft
        assert result.hook_used == "I did it. $1M in earnings."

    @pytest.mark.asyncio
    async def test_word_count_auto_set(self):
        draft = " ".join(["word"] * 50)
        output = LinkedInPostResult(
            draft=draft, hook_used="Hook line",
            hook_type="bold-statement", post_structure="freeform",
            word_count=0,
        )
        ctx = MagicMock()
        result = await linkedin_writer_agent._output_validators[0].validate(
            output, ctx, wrap_validation_errors=False
        )
        assert result.word_count == 50

    @pytest.mark.asyncio
    async def test_word_count_preserved_if_set(self):
        draft = " ".join(["word"] * 50)
        output = LinkedInPostResult(
            draft=draft, hook_used="Hook line",
            hook_type="bold-statement", post_structure="freeform",
            word_count=42,
        )
        ctx = MagicMock()
        result = await linkedin_writer_agent._output_validators[0].validate(
            output, ctx, wrap_validation_errors=False
        )
        assert result.word_count == 42


class TestLinkedInWriterTools:
    """Tool function tests."""

    @pytest.mark.asyncio
    async def test_generate_hooks_calls_hook_writer(self, mock_deps):
        from second_brain.schemas import HookWriterResult

        mock_result = MagicMock()
        mock_result.output = HookWriterResult(
            hooks=["Hook 1", "Hook 2", "Hook 3"],
            hook_type="bold-statement",
            topic_angle="coaching",
            reasoning="Bold works for achievement",
        )
        ctx = MagicMock()
        ctx.deps = mock_deps
        ctx.usage = MagicMock()

        with patch(
            "second_brain.agents.hook_writer.hook_writer_agent"
        ) as mock_hw:
            mock_hw.run = AsyncMock(return_value=mock_result)
            tool_fn = linkedin_writer_agent._function_toolset.tools["generate_hooks"]
            result = await tool_fn.function(ctx, topic="coaching business")

        assert "Hook 1" in result
        assert "Hook 2" in result
        assert "Hook 3" in result
        mock_hw.run.assert_called_once()
        call_kwargs = mock_hw.run.call_args
        assert call_kwargs.kwargs.get("deps") is mock_deps
        assert call_kwargs.kwargs.get("usage") is ctx.usage

    @pytest.mark.asyncio
    async def test_generate_hooks_passes_voice(self, mock_deps):
        from second_brain.schemas import HookWriterResult

        mock_result = MagicMock()
        mock_result.output = HookWriterResult(
            hooks=["H1", "H2", "H3"], hook_type="question",
            topic_angle="test",
        )
        ctx = MagicMock()
        ctx.deps = mock_deps
        ctx.usage = MagicMock()

        with patch(
            "second_brain.agents.hook_writer.hook_writer_agent"
        ) as mock_hw:
            mock_hw.run = AsyncMock(return_value=mock_result)
            tool_fn = linkedin_writer_agent._function_toolset.tools["generate_hooks"]
            await tool_fn.function(ctx, topic="test", voice_user_id="uttam")

        call_args = mock_hw.run.call_args
        assert "uttam" in call_args.args[0]

    @pytest.mark.asyncio
    async def test_generate_hooks_error_handling(self, mock_deps):
        ctx = MagicMock()
        ctx.deps = mock_deps
        ctx.usage = MagicMock()

        with patch(
            "second_brain.agents.hook_writer.hook_writer_agent"
        ) as mock_hw:
            mock_hw.run = AsyncMock(side_effect=Exception("timeout"))
            tool_fn = linkedin_writer_agent._function_toolset.tools["generate_hooks"]
            result = await tool_fn.function(ctx, topic="test")

        assert "BACKEND_ERROR:" in result

    @pytest.mark.asyncio
    async def test_load_voice_guide(self, mock_deps):
        ctx = MagicMock()
        ctx.deps = mock_deps
        tool_fn = linkedin_writer_agent._function_toolset.tools["load_voice_guide"]
        result = await tool_fn.function(ctx)
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_load_linkedin_examples(self, mock_deps):
        ctx = MagicMock()
        ctx.deps = mock_deps
        mock_deps.storage_service.get_examples = AsyncMock(return_value=[
            {"title": "My Launch Post", "content": "I launched my coaching biz..."},
        ])
        tool_fn = linkedin_writer_agent._function_toolset.tools["load_linkedin_examples"]
        result = await tool_fn.function(ctx)
        assert "My Launch Post" in result
        assert "LinkedIn Examples" in result

    @pytest.mark.asyncio
    async def test_load_linkedin_examples_empty(self, mock_deps):
        ctx = MagicMock()
        ctx.deps = mock_deps
        mock_deps.storage_service.get_examples = AsyncMock(return_value=[])
        tool_fn = linkedin_writer_agent._function_toolset.tools["load_linkedin_examples"]
        result = await tool_fn.function(ctx)
        assert "No LinkedIn examples" in result

    @pytest.mark.asyncio
    async def test_load_linkedin_examples_error(self, mock_deps):
        ctx = MagicMock()
        ctx.deps = mock_deps
        mock_deps.storage_service.get_examples = AsyncMock(side_effect=Exception("DB"))
        tool_fn = linkedin_writer_agent._function_toolset.tools["load_linkedin_examples"]
        result = await tool_fn.function(ctx)
        assert "BACKEND_ERROR:" in result

    @pytest.mark.asyncio
    async def test_find_linkedin_patterns(self, mock_deps):
        from second_brain.services.search_result import SearchResult

        ctx = MagicMock()
        ctx.deps = mock_deps
        mock_deps.memory_service.search = AsyncMock(
            return_value=SearchResult(
                memories=[{"memory": "LinkedIn posts perform better with hooks"}],
                relations=[],
            )
        )
        mock_deps.memory_service.search_with_filters = AsyncMock(
            return_value=SearchResult(memories=[], relations=[])
        )
        mock_deps.storage_service.get_patterns = AsyncMock(return_value=[])
        tool_fn = linkedin_writer_agent._function_toolset.tools["find_linkedin_patterns"]
        result = await tool_fn.function(ctx, topic="coaching")
        assert "Topic Knowledge" in result

    @pytest.mark.asyncio
    async def test_find_linkedin_patterns_error(self, mock_deps):
        ctx = MagicMock()
        ctx.deps = mock_deps
        mock_deps.memory_service.search = AsyncMock(side_effect=Exception("Mem0"))
        tool_fn = linkedin_writer_agent._function_toolset.tools["find_linkedin_patterns"]
        result = await tool_fn.function(ctx, topic="test")
        assert "BACKEND_ERROR:" in result

    @pytest.mark.asyncio
    async def test_search_linkedin_templates(self, mock_deps):
        ctx = MagicMock()
        ctx.deps = mock_deps
        mock_deps.storage_service.get_templates = AsyncMock(return_value=[
            {"name": "Origin Story", "description": "Tell your backstory",
             "structure_hint": "Hook → Story → Lesson", "when_to_use": "New founders"},
        ])
        tool_fn = linkedin_writer_agent._function_toolset.tools["search_linkedin_templates"]
        result = await tool_fn.function(ctx)
        assert "Origin Story" in result
        assert "LinkedIn Templates" in result

    @pytest.mark.asyncio
    async def test_search_linkedin_templates_empty(self, mock_deps):
        ctx = MagicMock()
        ctx.deps = mock_deps
        mock_deps.storage_service.get_templates = AsyncMock(return_value=[])
        tool_fn = linkedin_writer_agent._function_toolset.tools["search_linkedin_templates"]
        result = await tool_fn.function(ctx)
        assert "No LinkedIn templates" in result

    @pytest.mark.asyncio
    async def test_validate_draft_ok(self, mock_deps):
        ctx = MagicMock()
        ctx.deps = mock_deps
        # Short paragraphs to pass all checks
        draft = "Great hook here.\n\n" + " ".join(["word"] * 40) + "\n\n" + " ".join(["word"] * 40)
        tool_fn = linkedin_writer_agent._function_toolset.tools["validate_draft"]
        result = await tool_fn.function(ctx, draft=draft)
        assert "validates OK" in result

    @pytest.mark.asyncio
    async def test_validate_draft_long_hook(self, mock_deps):
        ctx = MagicMock()
        ctx.deps = mock_deps
        draft = "x" * 220 + "\n\n" + " ".join(["word"] * 100)
        tool_fn = linkedin_writer_agent._function_toolset.tools["validate_draft"]
        result = await tool_fn.function(ctx, draft=draft)
        assert "truncates" in result

    @pytest.mark.asyncio
    async def test_validate_draft_too_short(self, mock_deps):
        ctx = MagicMock()
        ctx.deps = mock_deps
        tool_fn = linkedin_writer_agent._function_toolset.tools["validate_draft"]
        result = await tool_fn.function(ctx, draft="Too short")
        assert "very short" in result


class TestLinkedInPostResultSchema:
    """Schema validation tests."""

    def test_minimal_valid(self):
        result = LinkedInPostResult(
            draft="A full post text here", hook_used="Hook",
            hook_type="bold-statement", post_structure="freeform",
        )
        assert result.content_type == "linkedin"
        assert result.error == ""

    def test_defaults(self):
        result = LinkedInPostResult(
            draft="Post", hook_used="Hook",
            hook_type="question", post_structure="listicle",
        )
        assert result.voice_elements == []
        assert result.patterns_applied == []
        assert result.examples_referenced == []
        assert result.word_count == 0
        assert result.notes == ""
        assert result.error == ""

    def test_error_field_default_empty(self):
        result = LinkedInPostResult(
            draft="Post", hook_used="Hook",
            hook_type="bold-statement", post_structure="freeform",
        )
        assert result.error == ""

    def test_with_all_fields(self):
        result = LinkedInPostResult(
            draft="Full post text",
            hook_used="I did it.",
            hook_type="bold-statement",
            post_structure="origin-story",
            content_type="linkedin",
            voice_elements=["direct", "confident"],
            patterns_applied=["achievement-post"],
            examples_referenced=["My Launch Post"],
            word_count=150,
            notes="Consider adding a CTA",
            error="",
        )
        assert len(result.voice_elements) == 2
        assert result.word_count == 150
