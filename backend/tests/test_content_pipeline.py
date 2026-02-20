"""Tests for content pipeline agents: clarity, synthesizer, template builder."""

import pytest
from unittest.mock import MagicMock
from pydantic_ai import ModelRetry

from second_brain.agents.clarity import clarity_agent
from second_brain.agents.synthesizer import synthesizer_agent
from second_brain.agents.template_builder import template_builder_agent
from second_brain.schemas import (
    ClarityResult, ClarityFinding,
    SynthesizerResult, SynthesizerTheme,
    TemplateBuilderResult, TemplateOpportunity,
)


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
    async def test_template_without_when_to_use(self):
        from second_brain.schemas import DeconstructedTemplate
        output = DeconstructedTemplate(
            name="Email Template",
            content_type="email",
            body="[GREETING]\n[BODY]\n[SIGN_OFF]",
            structure_hint="Greeting -> Body -> Sign-off",
            when_to_use="",  # missing!
        )
        ctx = MagicMock()
        validators = template_builder_agent._output_validators
        with pytest.raises(ModelRetry):
            await validators[0].validate(output, ctx, wrap_validation_errors=False)

    @pytest.mark.asyncio
    async def test_template_without_body(self):
        from second_brain.schemas import DeconstructedTemplate
        output = DeconstructedTemplate(
            name="Email Template",
            content_type="email",
            body="",  # missing!
            structure_hint="Greeting -> Body -> Sign-off",
            when_to_use="Follow-up emails",
        )
        ctx = MagicMock()
        validators = template_builder_agent._output_validators
        with pytest.raises(ModelRetry):
            await validators[0].validate(output, ctx, wrap_validation_errors=False)

    @pytest.mark.asyncio
    async def test_template_insufficient_placeholders(self):
        from second_brain.schemas import DeconstructedTemplate
        output = DeconstructedTemplate(
            name="Email Template",
            content_type="email",
            body="Hello [NAME], this is a template.",
            structure_hint="Greeting -> Body",
            when_to_use="Follow-up emails",
        )
        ctx = MagicMock()
        validators = template_builder_agent._output_validators
        with pytest.raises(ModelRetry):
            await validators[0].validate(output, ctx, wrap_validation_errors=False)

    @pytest.mark.asyncio
    async def test_valid_template(self):
        from second_brain.schemas import DeconstructedTemplate
        output = DeconstructedTemplate(
            name="Email Template",
            content_type="email",
            body="[GREETING],\n\n[OPENING_LINE]\n\n[BODY_PARAGRAPH]\n\n[SIGN_OFF]",
            structure_hint="Greeting -> Opening -> Body -> Sign-off",
            when_to_use="Follow-up emails to prospects",
        )
        ctx = MagicMock()
        validators = template_builder_agent._output_validators
        result = await validators[0].validate(output, ctx, wrap_validation_errors=False)
        assert result.name == "Email Template"

    @pytest.mark.asyncio
    async def test_template_without_structure_hint(self):
        from second_brain.schemas import DeconstructedTemplate
        output = DeconstructedTemplate(
            name="Email Template",
            content_type="email",
            body="[GREETING]\n[BODY]\n[SIGN_OFF]",
            structure_hint="",  # missing!
            when_to_use="Follow-up emails",
        )
        ctx = MagicMock()
        validators = template_builder_agent._output_validators
        with pytest.raises(ModelRetry):
            await validators[0].validate(output, ctx, wrap_validation_errors=False)


# --- Content Type Enrichment ---

class TestContentTypeEnrichment:
    """Tests for enriched ContentTypeConfig fields added by the Agent Factory refactor."""

    def test_essay_in_default_types(self):
        """Essay content type exists in DEFAULT_CONTENT_TYPES."""
        from second_brain.schemas import DEFAULT_CONTENT_TYPES
        assert "essay" in DEFAULT_CONTENT_TYPES

    def test_essay_has_stirc_protocol(self):
        """Essay content type includes STIRC scoring in writing_instructions."""
        from second_brain.schemas import DEFAULT_CONTENT_TYPES
        essay = DEFAULT_CONTENT_TYPES["essay"]
        assert "STIRC" in essay.writing_instructions
        assert "threshold 18/25" in essay.writing_instructions
        assert "FIVE WRITING LAWS" in essay.writing_instructions

    def test_essay_has_validation_rules(self):
        """Essay content type has validation rules for quality enforcement."""
        from second_brain.schemas import DEFAULT_CONTENT_TYPES
        essay = DEFAULT_CONTENT_TYPES["essay"]
        assert essay.validation_rules.get("min_words") == 300
        assert "title_required" in essay.validation_rules.get("custom_checks", [])
        assert "substantial_content" in essay.validation_rules.get("custom_checks", [])

    def test_essay_has_ui_config(self):
        """Essay content type has frontend UI metadata."""
        from second_brain.schemas import DEFAULT_CONTENT_TYPES
        essay = DEFAULT_CONTENT_TYPES["essay"]
        assert essay.ui_config.get("icon") == "pen-tool"
        assert essay.ui_config.get("category") == "long-form"
        assert essay.ui_config.get("show_framework_selector") is True

    def test_essay_metadata(self):
        """Essay content type has correct basic metadata."""
        from second_brain.schemas import DEFAULT_CONTENT_TYPES
        essay = DEFAULT_CONTENT_TYPES["essay"]
        assert essay.name == "Long-Form Essay"
        assert essay.max_words == 3000
        assert essay.default_mode == "professional"
        assert essay.is_builtin is True

    def test_all_types_have_writing_instructions(self):
        """Every builtin content type has non-empty writing_instructions."""
        from second_brain.schemas import DEFAULT_CONTENT_TYPES
        for slug, ct in DEFAULT_CONTENT_TYPES.items():
            assert ct.writing_instructions, f"{slug} missing writing_instructions"

    def test_all_types_have_ui_config_icon(self):
        """Every builtin content type has an icon in ui_config."""
        from second_brain.schemas import DEFAULT_CONTENT_TYPES
        for slug, ct in DEFAULT_CONTENT_TYPES.items():
            assert "icon" in ct.ui_config, f"{slug} missing ui_config.icon"

    def test_all_types_have_ui_config_category(self):
        """Every builtin content type has a category in ui_config."""
        from second_brain.schemas import DEFAULT_CONTENT_TYPES
        for slug, ct in DEFAULT_CONTENT_TYPES.items():
            assert "category" in ct.ui_config, f"{slug} missing ui_config.category"

    def test_ten_builtin_types(self):
        """DEFAULT_CONTENT_TYPES has exactly 10 types (9 original + essay)."""
        from second_brain.schemas import DEFAULT_CONTENT_TYPES
        assert len(DEFAULT_CONTENT_TYPES) == 10

    def test_content_type_config_new_field_defaults(self):
        """New ContentTypeConfig fields have correct defaults."""
        from second_brain.schemas import ContentTypeConfig
        ct = ContentTypeConfig(
            name="Test",
            default_mode="casual",
            structure_hint="A -> B",
            example_type="test",
        )
        assert ct.writing_instructions == ""
        assert ct.validation_rules == {}
        assert ct.ui_config == {}

    def test_content_type_config_with_enrichment(self):
        """ContentTypeConfig accepts all three enrichment fields."""
        from second_brain.schemas import ContentTypeConfig
        ct = ContentTypeConfig(
            name="Custom",
            default_mode="professional",
            structure_hint="Intro -> Body -> Close",
            example_type="custom",
            max_words=500,
            writing_instructions="Write clearly.",
            validation_rules={"min_words": 100, "required_sections": ["intro"]},
            ui_config={"icon": "star", "color": "#ff0000", "category": "custom"},
        )
        assert ct.writing_instructions == "Write clearly."
        assert ct.validation_rules["min_words"] == 100
        assert ct.ui_config["icon"] == "star"

    def test_content_type_from_row_parses_new_fields(self):
        """content_type_from_row() correctly parses enrichment fields from DB rows."""
        from second_brain.services.storage import content_type_from_row
        row = {
            "name": "Test Type",
            "slug": "test",
            "default_mode": "casual",
            "structure_hint": "A -> B",
            "example_type": "test",
            "max_words": 500,
            "description": "A test type",
            "is_builtin": True,
            "writing_instructions": "RULES:\n1. Be clear\n2. Be concise",
            "validation_rules": {"min_words": 100, "required_sections": ["intro"]},
            "ui_config": {"icon": "star", "color": "#ff0000", "category": "custom"},
        }
        ct = content_type_from_row(row)
        assert ct.writing_instructions == "RULES:\n1. Be clear\n2. Be concise"
        assert ct.validation_rules == {"min_words": 100, "required_sections": ["intro"]}
        assert ct.ui_config == {"icon": "star", "color": "#ff0000", "category": "custom"}

    def test_content_type_from_row_handles_none_fields(self):
        """content_type_from_row() handles None for JSONB fields (Supabase returns None)."""
        from second_brain.services.storage import content_type_from_row
        row = {
            "name": "Minimal",
            "slug": "minimal",
            "default_mode": "casual",
            "structure_hint": "",
            "example_type": "minimal",
            "writing_instructions": None,
            "validation_rules": None,
            "ui_config": None,
        }
        ct = content_type_from_row(row)
        assert ct.writing_instructions == ""
        assert ct.validation_rules == {}
        assert ct.ui_config == {}

    def test_content_type_from_row_handles_missing_fields(self):
        """content_type_from_row() handles missing new fields (old DB rows without migration)."""
        from second_brain.services.storage import content_type_from_row
        row = {
            "name": "Legacy",
            "slug": "legacy",
            "default_mode": "professional",
            "structure_hint": "A -> B",
            "example_type": "legacy",
        }
        ct = content_type_from_row(row)
        assert ct.writing_instructions == ""
        assert ct.validation_rules == {}
        assert ct.ui_config == {}

    def test_ui_config_categories_are_valid(self):
        """All ui_config categories are from the expected set."""
        from second_brain.schemas import DEFAULT_CONTENT_TYPES
        valid_categories = {"social", "communication", "marketing", "long-form", "business"}
        for slug, ct in DEFAULT_CONTENT_TYPES.items():
            category = ct.ui_config.get("category")
            assert category in valid_categories, (
                f"{slug} has unexpected category '{category}', expected one of {valid_categories}"
            )


# --- Registry Integration ---

class TestAgentRegistry:
    def test_all_content_pipeline_agents_in_registry(self):
        from second_brain.agents.registry import get_agent_registry
        registry = get_agent_registry()
        assert "clarity" in registry
        assert "synthesizer" in registry
        assert "template_builder" in registry

    def test_registry_has_descriptions(self):
        from second_brain.agents.registry import get_agent_registry
        registry = get_agent_registry()
        for key in ("clarity", "synthesizer", "template_builder"):
            agent, desc = registry[key]
            assert agent is not None
            assert desc

    def test_essay_writer_removed_from_registry(self):
        from second_brain.agents.registry import get_agent_registry
        registry = get_agent_registry()
        assert "essay_writer" not in registry
