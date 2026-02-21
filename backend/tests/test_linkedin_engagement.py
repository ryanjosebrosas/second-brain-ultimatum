"""Tests for the LinkedIn Engagement agent."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from pydantic_ai import ModelRetry

from second_brain.agents.linkedin_engagement import (
    linkedin_engagement_agent,
    AI_SOUNDING_PATTERNS,
)
from second_brain.schemas import LinkedInEngagementResult


class TestLinkedInEngagementAgent:
    """Agent structure tests."""

    def test_has_tools(self):
        tools = linkedin_engagement_agent._function_toolset.tools
        assert "load_voice_guide" in tools
        assert "load_expertise_context" in tools
        assert "search_relevant_knowledge" in tools
        assert "search_past_engagement" in tools
        assert "load_content_examples" in tools

    def test_tool_count(self):
        assert len(linkedin_engagement_agent._function_toolset.tools) == 5

    def test_has_retries(self):
        assert linkedin_engagement_agent._max_result_retries == 3

    def test_has_validator(self):
        assert len(linkedin_engagement_agent._output_validators) > 0

    def test_output_type(self):
        assert linkedin_engagement_agent._output_type is LinkedInEngagementResult

    def test_ai_sounding_patterns_defined(self):
        assert len(AI_SOUNDING_PATTERNS) >= 8
        assert "great post" in AI_SOUNDING_PATTERNS
        assert "thanks for sharing" in AI_SOUNDING_PATTERNS
        assert "absolutely!" in AI_SOUNDING_PATTERNS


class TestLinkedInEngagementValidator:
    """Output validator tests."""

    @pytest.mark.asyncio
    async def test_error_bypass(self):
        output = LinkedInEngagementResult(
            response="minimal", engagement_type="comment", tone="conversational",
            error="BACKEND_ERROR: memory unavailable",
        )
        ctx = MagicMock()
        result = await linkedin_engagement_agent._output_validators[0].validate(
            output, ctx, wrap_validation_errors=False
        )
        assert result.error

    @pytest.mark.asyncio
    async def test_empty_response_retries(self):
        output = LinkedInEngagementResult(
            response="Yes", engagement_type="comment", tone="conversational",
        )
        ctx = MagicMock()
        with pytest.raises(ModelRetry, match="5 words"):
            await linkedin_engagement_agent._output_validators[0].validate(
                output, ctx, wrap_validation_errors=False
            )

    @pytest.mark.asyncio
    async def test_invalid_engagement_type_retries(self):
        output = LinkedInEngagementResult(
            response="This is a substantive and meaningful comment here",
            engagement_type="like", tone="conversational",
        )
        ctx = MagicMock()
        with pytest.raises(ModelRetry, match="comment.*reply"):
            await linkedin_engagement_agent._output_validators[0].validate(
                output, ctx, wrap_validation_errors=False
            )

    @pytest.mark.asyncio
    async def test_ai_sounding_great_post_retries(self):
        output = LinkedInEngagementResult(
            response="Great post! I really enjoyed reading this perspective on AI.",
            engagement_type="comment", tone="supportive",
        )
        ctx = MagicMock()
        with pytest.raises(ModelRetry, match="AI engagement pattern"):
            await linkedin_engagement_agent._output_validators[0].validate(
                output, ctx, wrap_validation_errors=False
            )

    @pytest.mark.asyncio
    async def test_ai_sounding_thanks_retries(self):
        output = LinkedInEngagementResult(
            response="Thanks for sharing this insightful piece on automation.",
            engagement_type="comment", tone="supportive",
        )
        ctx = MagicMock()
        with pytest.raises(ModelRetry, match="AI engagement pattern"):
            await linkedin_engagement_agent._output_validators[0].validate(
                output, ctx, wrap_validation_errors=False
            )

    @pytest.mark.asyncio
    async def test_ai_sounding_absolutely_retries(self):
        output = LinkedInEngagementResult(
            response="Absolutely! This is exactly what the industry needs right now.",
            engagement_type="comment", tone="conversational",
        )
        ctx = MagicMock()
        with pytest.raises(ModelRetry, match="AI engagement pattern"):
            await linkedin_engagement_agent._output_validators[0].validate(
                output, ctx, wrap_validation_errors=False
            )

    @pytest.mark.asyncio
    async def test_ai_sounding_love_this_retries(self):
        output = LinkedInEngagementResult(
            response="Love this! Great insights on building in public.",
            engagement_type="comment", tone="supportive",
        )
        ctx = MagicMock()
        with pytest.raises(ModelRetry, match="AI engagement pattern"):
            await linkedin_engagement_agent._output_validators[0].validate(
                output, ctx, wrap_validation_errors=False
            )

    @pytest.mark.asyncio
    async def test_ai_sounding_so_true_retries(self):
        output = LinkedInEngagementResult(
            response="So true! We see this exact pattern with our clients too.",
            engagement_type="comment", tone="conversational",
        )
        ctx = MagicMock()
        with pytest.raises(ModelRetry, match="AI engagement pattern"):
            await linkedin_engagement_agent._output_validators[0].validate(
                output, ctx, wrap_validation_errors=False
            )

    @pytest.mark.asyncio
    async def test_valid_comment_passes(self):
        output = LinkedInEngagementResult(
            response="We ran into this exact problem at our agency last quarter. "
            "Ended up building a custom attribution model that cut CAC by 30%.",
            engagement_type="comment", tone="insightful",
            context_used=["expertise: marketing automation"],
        )
        ctx = MagicMock()
        result = await linkedin_engagement_agent._output_validators[0].validate(
            output, ctx, wrap_validation_errors=False
        )
        assert result.engagement_type == "comment"

    @pytest.mark.asyncio
    async def test_valid_reply_passes(self):
        output = LinkedInEngagementResult(
            response="Good question — we actually tested both approaches and "
            "found the async version performed 2x better under load.",
            engagement_type="reply", tone="conversational",
        )
        ctx = MagicMock()
        result = await linkedin_engagement_agent._output_validators[0].validate(
            output, ctx, wrap_validation_errors=False
        )
        assert result.engagement_type == "reply"

    @pytest.mark.asyncio
    async def test_word_count_auto_set(self):
        output = LinkedInEngagementResult(
            response="This is a valid comment with enough words to pass",
            engagement_type="comment", tone="conversational",
            word_count=0,
        )
        ctx = MagicMock()
        result = await linkedin_engagement_agent._output_validators[0].validate(
            output, ctx, wrap_validation_errors=False
        )
        assert result.word_count > 0

    @pytest.mark.asyncio
    async def test_word_count_preserved_if_set(self):
        output = LinkedInEngagementResult(
            response="This is a valid comment with enough words to pass",
            engagement_type="comment", tone="conversational",
            word_count=42,
        )
        ctx = MagicMock()
        result = await linkedin_engagement_agent._output_validators[0].validate(
            output, ctx, wrap_validation_errors=False
        )
        assert result.word_count == 42


class TestLinkedInEngagementTools:
    """Tool function tests."""

    @pytest.mark.asyncio
    async def test_load_voice_guide(self, mock_deps):
        ctx = MagicMock()
        ctx.deps = mock_deps
        tool_fn = linkedin_engagement_agent._function_toolset.tools["load_voice_guide"]
        result = await tool_fn.function(ctx)
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_load_expertise_context(self, mock_deps):
        ctx = MagicMock()
        ctx.deps = mock_deps
        mock_deps.storage_service.get_memory_content = AsyncMock(return_value=[
            {"title": "AI Automation Platform", "content": "We build AI tools for agencies"},
        ])
        tool_fn = linkedin_engagement_agent._function_toolset.tools["load_expertise_context"]
        result = await tool_fn.function(ctx)
        assert "Your Expertise" in result
        assert "AI Automation Platform" in result

    @pytest.mark.asyncio
    async def test_load_expertise_context_empty(self, mock_deps):
        ctx = MagicMock()
        ctx.deps = mock_deps
        mock_deps.storage_service.get_memory_content = AsyncMock(return_value=[])
        tool_fn = linkedin_engagement_agent._function_toolset.tools["load_expertise_context"]
        result = await tool_fn.function(ctx)
        assert "No expertise context" in result

    @pytest.mark.asyncio
    async def test_load_expertise_context_error(self, mock_deps):
        ctx = MagicMock()
        ctx.deps = mock_deps
        mock_deps.storage_service.get_memory_content = AsyncMock(
            side_effect=Exception("Supabase error")
        )
        tool_fn = linkedin_engagement_agent._function_toolset.tools["load_expertise_context"]
        result = await tool_fn.function(ctx)
        assert "BACKEND_ERROR:" in result

    @pytest.mark.asyncio
    async def test_search_relevant_knowledge(self, mock_deps):
        from second_brain.services.search_result import SearchResult

        ctx = MagicMock()
        ctx.deps = mock_deps
        # First call: topic search. Second call: meeting search.
        mock_deps.memory_service.search = AsyncMock(
            return_value=SearchResult(
                memories=[{"memory": "AI automation reduces manual work by 80%"}],
                relations=[{"source": "AI", "target": "automation", "relation": "enables"}],
            )
        )
        tool_fn = linkedin_engagement_agent._function_toolset.tools["search_relevant_knowledge"]
        result = await tool_fn.function(ctx, topic="AI automation")
        assert "Relevant Knowledge" in result
        # Should be called twice: topic search + meeting search
        assert mock_deps.memory_service.search.call_count == 2

    @pytest.mark.asyncio
    async def test_search_relevant_knowledge_with_relations(self, mock_deps):
        from second_brain.services.search_result import SearchResult

        ctx = MagicMock()
        ctx.deps = mock_deps
        mock_deps.memory_service.search = AsyncMock(
            return_value=SearchResult(
                memories=[{"memory": "Content about coaching"}],
                relations=[{"source": "coaching", "target": "business", "relation": "grows"}],
            )
        )
        tool_fn = linkedin_engagement_agent._function_toolset.tools["search_relevant_knowledge"]
        result = await tool_fn.function(ctx, topic="coaching")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_search_relevant_knowledge_error(self, mock_deps):
        ctx = MagicMock()
        ctx.deps = mock_deps
        mock_deps.memory_service.search = AsyncMock(
            side_effect=Exception("Mem0 error")
        )
        tool_fn = linkedin_engagement_agent._function_toolset.tools["search_relevant_knowledge"]
        result = await tool_fn.function(ctx, topic="test")
        assert "BACKEND_ERROR:" in result

    @pytest.mark.asyncio
    async def test_search_past_engagement(self, mock_deps):
        from second_brain.services.search_result import SearchResult

        ctx = MagicMock()
        ctx.deps = mock_deps
        mock_deps.memory_service.search = AsyncMock(
            return_value=SearchResult(
                memories=[{"memory": "Commented on a post about AI tools"}],
                relations=[],
            )
        )
        tool_fn = linkedin_engagement_agent._function_toolset.tools["search_past_engagement"]
        result = await tool_fn.function(ctx, topic="AI")
        assert "Past Engagement" in result

    @pytest.mark.asyncio
    async def test_search_past_engagement_empty(self, mock_deps):
        from second_brain.services.search_result import SearchResult

        ctx = MagicMock()
        ctx.deps = mock_deps
        mock_deps.memory_service.search = AsyncMock(
            return_value=SearchResult(memories=[], relations=[])
        )
        tool_fn = linkedin_engagement_agent._function_toolset.tools["search_past_engagement"]
        result = await tool_fn.function(ctx, topic="test")
        assert "No past engagement" in result

    @pytest.mark.asyncio
    async def test_search_past_engagement_error(self, mock_deps):
        ctx = MagicMock()
        ctx.deps = mock_deps
        mock_deps.memory_service.search = AsyncMock(
            side_effect=Exception("Mem0 error")
        )
        tool_fn = linkedin_engagement_agent._function_toolset.tools["search_past_engagement"]
        result = await tool_fn.function(ctx, topic="test")
        assert "BACKEND_ERROR:" in result

    @pytest.mark.asyncio
    async def test_load_content_examples(self, mock_deps):
        ctx = MagicMock()
        ctx.deps = mock_deps
        mock_deps.storage_service.get_examples = AsyncMock(return_value=[
            {"title": "AI Automation Post", "content": "I built an AI tool that..."},
        ])
        tool_fn = linkedin_engagement_agent._function_toolset.tools["load_content_examples"]
        result = await tool_fn.function(ctx)
        assert "AI Automation Post" in result
        assert "Your LinkedIn Posts" in result

    @pytest.mark.asyncio
    async def test_load_content_examples_empty(self, mock_deps):
        ctx = MagicMock()
        ctx.deps = mock_deps
        mock_deps.storage_service.get_examples = AsyncMock(return_value=[])
        tool_fn = linkedin_engagement_agent._function_toolset.tools["load_content_examples"]
        result = await tool_fn.function(ctx)
        assert "No LinkedIn examples" in result

    @pytest.mark.asyncio
    async def test_load_content_examples_error(self, mock_deps):
        ctx = MagicMock()
        ctx.deps = mock_deps
        mock_deps.storage_service.get_examples = AsyncMock(
            side_effect=Exception("DB error")
        )
        tool_fn = linkedin_engagement_agent._function_toolset.tools["load_content_examples"]
        result = await tool_fn.function(ctx)
        assert "BACKEND_ERROR:" in result


class TestLinkedInEngagementResultSchema:
    """Schema validation tests."""

    def test_minimal_valid(self):
        result = LinkedInEngagementResult(
            response="A substantive comment",
            engagement_type="comment",
            tone="conversational",
        )
        assert result.error == ""
        assert result.word_count == 0

    def test_defaults(self):
        result = LinkedInEngagementResult(
            response="Comment", engagement_type="reply", tone="insightful",
        )
        assert result.context_used == []
        assert result.voice_elements == []
        assert result.word_count == 0
        assert result.notes == ""
        assert result.error == ""

    def test_engagement_type_values(self):
        comment = LinkedInEngagementResult(
            response="A comment", engagement_type="comment", tone="conversational",
        )
        reply = LinkedInEngagementResult(
            response="A reply", engagement_type="reply", tone="conversational",
        )
        assert comment.engagement_type == "comment"
        assert reply.engagement_type == "reply"

    def test_with_all_fields(self):
        result = LinkedInEngagementResult(
            response="We tested this approach and saw 30% improvement.",
            engagement_type="comment",
            tone="insightful",
            context_used=["expertise: AI automation", "meeting: client call"],
            voice_elements=["direct", "data-driven"],
            word_count=10,
            notes="Consider adding a specific example",
            error="",
        )
        assert len(result.context_used) == 2
        assert result.word_count == 10
