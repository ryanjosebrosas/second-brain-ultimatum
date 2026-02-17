"""Tests for content pipeline agents: essay writer, clarity, synthesizer, template builder."""

import pytest
from unittest.mock import MagicMock
from pydantic_ai import ModelRetry

from second_brain.agents.essay_writer import essay_writer_agent
from second_brain.agents.clarity import clarity_agent
from second_brain.agents.synthesizer import synthesizer_agent
from second_brain.agents.template_builder import template_builder_agent
from second_brain.schemas import (
    EssayResult, ClarityResult, ClarityFinding,
    SynthesizerResult, SynthesizerTheme,
    TemplateBuilderResult, TemplateOpportunity,
)


# --- Essay Writer ---

class TestEssayWriterAgent:
    def test_has_tools(self):
        tools = essay_writer_agent._function_toolset.tools
        assert "load_voice_and_patterns" in tools
        assert "load_examples" in tools
        assert "search_research_context" in tools

    def test_has_retries(self):
        assert essay_writer_agent._max_result_retries == 3

    def test_has_validator(self):
        assert len(essay_writer_agent._output_validators) > 0


class TestEssayValidator:
    @pytest.mark.asyncio
    async def test_short_essay_triggers_retry(self):
        output = EssayResult(title="Test", essay="Too short.")
        ctx = MagicMock()
        ctx.deps.config.stirc_threshold = 18
        validators = essay_writer_agent._output_validators
        with pytest.raises(ModelRetry):
            await validators[0].validate(output, ctx, wrap_validation_errors=False)

    @pytest.mark.asyncio
    async def test_low_stirc_triggers_retry(self):
        output = EssayResult(
            title="Test",
            essay=" ".join(["word"] * 500),
            stirc_score=12,
        )
        ctx = MagicMock()
        ctx.deps.config.stirc_threshold = 18
        validators = essay_writer_agent._output_validators
        with pytest.raises(ModelRetry):
            await validators[0].validate(output, ctx, wrap_validation_errors=False)

    @pytest.mark.asyncio
    async def test_missing_title_triggers_retry(self):
        output = EssayResult(
            title="",
            essay=" ".join(["word"] * 500),
            stirc_score=20,
        )
        ctx = MagicMock()
        ctx.deps.config.stirc_threshold = 18
        validators = essay_writer_agent._output_validators
        with pytest.raises(ModelRetry):
            await validators[0].validate(output, ctx, wrap_validation_errors=False)

    @pytest.mark.asyncio
    async def test_zero_stirc_score_skips_threshold(self):
        """STIRC score of 0 means the LLM skipped scoring — should not penalize."""
        output = EssayResult(
            title="Why AI Matters",
            essay=" ".join(["word"] * 500),
            stirc_score=0,
        )
        ctx = MagicMock()
        ctx.deps.config.stirc_threshold = 18
        validators = essay_writer_agent._output_validators
        result = await validators[0].validate(output, ctx, wrap_validation_errors=False)
        assert result.word_count == 500

    @pytest.mark.asyncio
    async def test_good_essay_passes(self):
        output = EssayResult(
            title="Why AI Agents Matter",
            essay=" ".join(["word"] * 500),
            stirc_score=22,
        )
        ctx = MagicMock()
        ctx.deps.config.stirc_threshold = 18
        validators = essay_writer_agent._output_validators
        result = await validators[0].validate(output, ctx, wrap_validation_errors=False)
        assert result.word_count == 500

    @pytest.mark.asyncio
    async def test_word_count_auto_set(self):
        """Validator should auto-set word_count from actual essay content."""
        essay_text = " ".join(["word"] * 350)
        output = EssayResult(title="Test Essay", essay=essay_text, stirc_score=20)
        ctx = MagicMock()
        ctx.deps.config.stirc_threshold = 18
        validators = essay_writer_agent._output_validators
        result = await validators[0].validate(output, ctx, wrap_validation_errors=False)
        assert result.word_count == 350


# --- Clarity Maximizer ---

class TestClarityAgent:
    def test_has_tools(self):
        tools = clarity_agent._function_toolset.tools
        assert "load_audience_context" in tools
        assert "load_voice_reference" in tools

    def test_has_retries(self):
        assert clarity_agent._max_result_retries == 3

    def test_has_validator(self):
        assert len(clarity_agent._output_validators) > 0


class TestClarityValidator:
    @pytest.mark.asyncio
    async def test_no_findings_but_low_readability(self):
        output = ClarityResult(findings=[], overall_readability="LOW")
        ctx = MagicMock()
        validators = clarity_agent._output_validators
        with pytest.raises(ModelRetry):
            await validators[0].validate(output, ctx, wrap_validation_errors=False)

    @pytest.mark.asyncio
    async def test_no_findings_medium_readability(self):
        output = ClarityResult(findings=[], overall_readability="MEDIUM")
        ctx = MagicMock()
        validators = clarity_agent._output_validators
        with pytest.raises(ModelRetry):
            await validators[0].validate(output, ctx, wrap_validation_errors=False)

    @pytest.mark.asyncio
    async def test_finding_without_suggestion(self):
        output = ClarityResult(
            findings=[ClarityFinding(
                severity="HIGH", location="para 1",
                issue="Jargon", suggestion="",
            )],
            overall_readability="MEDIUM",
        )
        ctx = MagicMock()
        validators = clarity_agent._output_validators
        with pytest.raises(ModelRetry):
            await validators[0].validate(output, ctx, wrap_validation_errors=False)

    @pytest.mark.asyncio
    async def test_no_findings_high_readability_passes(self):
        """No findings with HIGH readability is valid — content is clear."""
        output = ClarityResult(findings=[], overall_readability="HIGH")
        ctx = MagicMock()
        validators = clarity_agent._output_validators
        result = await validators[0].validate(output, ctx, wrap_validation_errors=False)
        assert result.critical_count == 0

    @pytest.mark.asyncio
    async def test_valid_analysis_passes(self):
        output = ClarityResult(
            findings=[ClarityFinding(
                severity="CRITICAL", location="title",
                issue="Undefined acronym", suggestion="Define ROI on first use",
            )],
            overall_readability="MEDIUM",
        )
        ctx = MagicMock()
        validators = clarity_agent._output_validators
        result = await validators[0].validate(output, ctx, wrap_validation_errors=False)
        assert result.critical_count == 1

    @pytest.mark.asyncio
    async def test_critical_count_auto_computed(self):
        """critical_count is computed from findings, not trusted from LLM."""
        output = ClarityResult(
            findings=[
                ClarityFinding(severity="CRITICAL", location="s1", issue="X", suggestion="Fix X"),
                ClarityFinding(severity="HIGH", location="s2", issue="Y", suggestion="Fix Y"),
                ClarityFinding(severity="CRITICAL", location="s3", issue="Z", suggestion="Fix Z"),
            ],
            overall_readability="LOW",
            critical_count=0,  # intentionally wrong — validator should override
        )
        ctx = MagicMock()
        validators = clarity_agent._output_validators
        result = await validators[0].validate(output, ctx, wrap_validation_errors=False)
        assert result.critical_count == 2


# --- Feedback Synthesizer ---

class TestSynthesizerAgent:
    def test_has_tools(self):
        tools = synthesizer_agent._function_toolset.tools
        assert "load_past_reviews" in tools

    def test_has_retries(self):
        assert synthesizer_agent._max_result_retries == 3

    def test_has_validator(self):
        assert len(synthesizer_agent._output_validators) > 0


class TestSynthesizerValidator:
    @pytest.mark.asyncio
    async def test_too_few_themes(self):
        output = SynthesizerResult(themes=[
            SynthesizerTheme(title="Fix all", priority="HIGH", action="Do stuff"),
        ])
        ctx = MagicMock()
        validators = synthesizer_agent._output_validators
        with pytest.raises(ModelRetry):
            await validators[0].validate(output, ctx, wrap_validation_errors=False)

    @pytest.mark.asyncio
    async def test_too_many_themes(self):
        themes = [
            SynthesizerTheme(title=f"Theme {i}", priority="LOW", action=f"Do {i}", effort_minutes=15)
            for i in range(13)
        ]
        output = SynthesizerResult(themes=themes)
        ctx = MagicMock()
        validators = synthesizer_agent._output_validators
        with pytest.raises(ModelRetry):
            await validators[0].validate(output, ctx, wrap_validation_errors=False)

    @pytest.mark.asyncio
    async def test_theme_without_action(self):
        themes = [
            SynthesizerTheme(title=f"Theme {i}", priority="MEDIUM", action="Do X", effort_minutes=30)
            for i in range(4)
        ]
        themes[2].action = ""  # empty action
        output = SynthesizerResult(themes=themes)
        ctx = MagicMock()
        validators = synthesizer_agent._output_validators
        with pytest.raises(ModelRetry):
            await validators[0].validate(output, ctx, wrap_validation_errors=False)

    @pytest.mark.asyncio
    async def test_valid_synthesis(self):
        themes = [
            SynthesizerTheme(title=f"Theme {i}", priority="HIGH", action=f"Do {i}", effort_minutes=30)
            for i in range(5)
        ]
        output = SynthesizerResult(themes=themes, total_findings_input=25)
        ctx = MagicMock()
        validators = synthesizer_agent._output_validators
        result = await validators[0].validate(output, ctx, wrap_validation_errors=False)
        assert result.total_themes_output == 5
        assert result.implementation_hours == 2.5

    @pytest.mark.asyncio
    async def test_totals_auto_computed(self):
        """total_themes_output and implementation_hours are auto-computed."""
        themes = [
            SynthesizerTheme(title=f"Theme {i}", priority="MEDIUM", action=f"Step {i}", effort_minutes=60)
            for i in range(4)
        ]
        output = SynthesizerResult(themes=themes, total_themes_output=0, implementation_hours=0.0)
        ctx = MagicMock()
        validators = synthesizer_agent._output_validators
        result = await validators[0].validate(output, ctx, wrap_validation_errors=False)
        assert result.total_themes_output == 4
        assert result.implementation_hours == 4.0


# --- Template Builder ---

class TestTemplateBuilderAgent:
    def test_has_tools(self):
        tools = template_builder_agent._function_toolset.tools
        assert "search_existing_patterns" in tools
        assert "search_examples" in tools

    def test_has_retries(self):
        assert template_builder_agent._max_result_retries == 3

    def test_has_validator(self):
        assert len(template_builder_agent._output_validators) > 0


class TestTemplateValidator:
    @pytest.mark.asyncio
    async def test_opportunity_without_when(self):
        output = TemplateBuilderResult(
            opportunities=[TemplateOpportunity(
                name="Email Template",
                source_deliverable="client email",
                structure="Subject -> Body -> CTA",
                when_to_use="",  # missing!
            )]
        )
        ctx = MagicMock()
        validators = template_builder_agent._output_validators
        with pytest.raises(ModelRetry):
            await validators[0].validate(output, ctx, wrap_validation_errors=False)

    @pytest.mark.asyncio
    async def test_opportunity_without_structure(self):
        output = TemplateBuilderResult(
            opportunities=[TemplateOpportunity(
                name="Email Template",
                source_deliverable="client email",
                structure="",  # missing!
                when_to_use="Follow-up emails",
            )]
        )
        ctx = MagicMock()
        validators = template_builder_agent._output_validators
        with pytest.raises(ModelRetry):
            await validators[0].validate(output, ctx, wrap_validation_errors=False)

    @pytest.mark.asyncio
    async def test_valid_template(self):
        output = TemplateBuilderResult(
            opportunities=[TemplateOpportunity(
                name="Email Template",
                source_deliverable="client email",
                structure="Subject -> Body -> CTA",
                when_to_use="Follow-up emails to prospects",
            )]
        )
        ctx = MagicMock()
        validators = template_builder_agent._output_validators
        result = await validators[0].validate(output, ctx, wrap_validation_errors=False)
        assert result.templates_created == 1

    @pytest.mark.asyncio
    async def test_empty_opportunities_passes(self):
        """No template opportunities found is a valid result."""
        output = TemplateBuilderResult(opportunities=[])
        ctx = MagicMock()
        validators = template_builder_agent._output_validators
        result = await validators[0].validate(output, ctx, wrap_validation_errors=False)
        assert result.templates_created == 0

    @pytest.mark.asyncio
    async def test_templates_created_auto_set(self):
        """templates_created is auto-computed from opportunities length."""
        output = TemplateBuilderResult(
            opportunities=[
                TemplateOpportunity(
                    name=f"Template {i}",
                    source_deliverable=f"deliverable {i}",
                    structure=f"Step A -> Step B -> Step C",
                    when_to_use=f"Use case {i}",
                )
                for i in range(3)
            ],
            templates_created=0,  # intentionally wrong
        )
        ctx = MagicMock()
        validators = template_builder_agent._output_validators
        result = await validators[0].validate(output, ctx, wrap_validation_errors=False)
        assert result.templates_created == 3


# --- Registry Integration ---

class TestAgentRegistry:
    def test_all_content_pipeline_agents_in_registry(self):
        from second_brain.agents.utils import get_agent_registry
        registry = get_agent_registry()
        assert "essay_writer" in registry
        assert "clarity" in registry
        assert "synthesizer" in registry
        assert "template_builder" in registry

    def test_registry_has_descriptions(self):
        from second_brain.agents.utils import get_agent_registry
        registry = get_agent_registry()
        for key in ("essay_writer", "clarity", "synthesizer", "template_builder"):
            agent, desc = registry[key]
            assert agent is not None
            assert desc
