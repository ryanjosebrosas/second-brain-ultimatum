"""Tests for the Template Bank feature."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from pydantic_ai import ModelRetry

from second_brain.schemas import (
    DeconstructedTemplate,
    TemplateBankEntry,
    TemplateOpportunity,
    TemplateBuilderResult,
)
from second_brain.agents.template_builder import template_builder_agent
from second_brain.api.main import create_app
from second_brain.config import BrainConfig
from second_brain.deps import BrainDeps


# --- Fixtures ---


@pytest.fixture
def mock_brain_config(tmp_path):
    return BrainConfig(
        anthropic_api_key="test-key",
        openai_api_key="test-key",
        mem0_api_key=None,
        graph_provider="none",
        neo4j_url=None,
        neo4j_username=None,
        neo4j_password=None,
        supabase_url="https://test.supabase.co",
        supabase_key="test-key",
        brain_user_id="ryan",
        brain_data_path=tmp_path,
        model_provider="anthropic",
        _env_file=None,
    )


@pytest.fixture
def app(mock_brain_config):
    application = create_app()
    mock_deps = MagicMock(spec=BrainDeps)
    mock_deps.config = mock_brain_config
    mock_deps.memory_service = AsyncMock()
    mock_deps.storage_service = AsyncMock()
    mock_deps.embedding_service = AsyncMock()
    mock_deps.voyage_service = AsyncMock()
    mock_deps.graphiti_service = None
    mock_deps.content_type_registry = MagicMock()
    mock_deps.email_service = None
    mock_deps.calendar_service = None
    mock_deps.analytics_service = None
    mock_deps.task_service = None
    mock_deps.get_content_type_registry.return_value = mock_deps.content_type_registry
    application.state.deps = mock_deps
    application.state.model = MagicMock()
    return application


@pytest.fixture
def client(app):
    return TestClient(app)


# --- Schema Tests ---


class TestTemplateBankSchemas:
    """Test new template bank Pydantic models."""

    def test_template_bank_entry_defaults(self):
        entry = TemplateBankEntry(
            name="Test", content_type="linkedin",
            body="[HOOK]\n[BODY]", when_to_use="For posts",
        )
        assert entry.id is None
        assert entry.tags == []
        assert entry.is_active is True
        assert entry.use_count == 0
        assert entry.ai_generated is False

    def test_template_bank_entry_full(self):
        entry = TemplateBankEntry(
            id="tmpl-1", name="LinkedIn Post",
            content_type="linkedin", body="[HOOK]\n[BODY]\n[CTA]",
            when_to_use="Thought leadership",
            when_not_to_use="Casual updates",
            tags=["professional", "thought-leadership"],
            structure_hint="Hook -> Body -> CTA",
            ai_generated=True, use_count=5,
        )
        assert entry.id == "tmpl-1"
        assert len(entry.tags) == 2
        assert entry.ai_generated is True

    def test_deconstructed_template_required_fields(self):
        tmpl = DeconstructedTemplate(
            name="Test", content_type="email",
            body="[GREETING]\n[BODY]\n[SIGN_OFF]",
            structure_hint="Greeting -> Body -> Sign-off",
            when_to_use="Client follow-ups",
        )
        assert tmpl.name == "Test"
        assert tmpl.content_type == "email"
        assert "[GREETING]" in tmpl.body

    def test_deconstructed_template_defaults(self):
        tmpl = DeconstructedTemplate(
            name="Test", content_type="email",
            body="[GREETING]\n[BODY]\n[SIGN_OFF]",
            structure_hint="Greeting -> Body -> Sign-off",
            when_to_use="Client emails",
        )
        assert tmpl.tags == []
        assert tmpl.when_not_to_use == ""
        assert tmpl.customization_guide == ""

    def test_old_schemas_still_work(self):
        """Backward compatibility — old schemas not removed."""
        opp = TemplateOpportunity(
            name="Test", source_deliverable="email",
            structure="A -> B", when_to_use="Testing",
        )
        result = TemplateBuilderResult(opportunities=[opp])
        assert len(result.opportunities) == 1


# --- Agent Tests ---


class TestTemplateBuilderAgent:
    """Test enhanced template builder agent structure."""

    def test_output_type_is_deconstructed(self):
        assert template_builder_agent._output_type is DeconstructedTemplate

    def test_has_tools(self):
        tools = template_builder_agent._function_toolset.tools
        assert "search_existing_patterns" in tools
        assert "search_examples" in tools
        assert "search_template_bank" in tools

    def test_has_retries(self):
        assert template_builder_agent._max_result_retries == 3

    def test_has_validator(self):
        assert len(template_builder_agent._output_validators) > 0


class TestTemplateValidator:
    """Test enhanced output validator."""

    @pytest.mark.asyncio
    async def test_missing_when_to_use(self):
        output = DeconstructedTemplate(
            name="Test", content_type="email",
            body="[A]\n[B]\n[C]",
            structure_hint="A -> B -> C",
            when_to_use="",
        )
        ctx = MagicMock()
        validators = template_builder_agent._output_validators
        with pytest.raises(ModelRetry):
            await validators[0].validate(output, ctx, wrap_validation_errors=False)

    @pytest.mark.asyncio
    async def test_missing_body(self):
        output = DeconstructedTemplate(
            name="Test", content_type="email",
            body="",
            structure_hint="A -> B -> C",
            when_to_use="For emails",
        )
        ctx = MagicMock()
        validators = template_builder_agent._output_validators
        with pytest.raises(ModelRetry):
            await validators[0].validate(output, ctx, wrap_validation_errors=False)

    @pytest.mark.asyncio
    async def test_insufficient_placeholders(self):
        output = DeconstructedTemplate(
            name="Test", content_type="email",
            body="Hello [NAME], this is a template.",
            structure_hint="Greeting -> Body",
            when_to_use="For emails",
        )
        ctx = MagicMock()
        validators = template_builder_agent._output_validators
        with pytest.raises(ModelRetry):
            await validators[0].validate(output, ctx, wrap_validation_errors=False)

    @pytest.mark.asyncio
    async def test_missing_structure_hint(self):
        output = DeconstructedTemplate(
            name="Test", content_type="email",
            body="[GREETING]\n[BODY]\n[SIGN_OFF]",
            structure_hint="",
            when_to_use="For emails",
        )
        ctx = MagicMock()
        validators = template_builder_agent._output_validators
        with pytest.raises(ModelRetry):
            await validators[0].validate(output, ctx, wrap_validation_errors=False)

    @pytest.mark.asyncio
    async def test_valid_template_passes(self):
        output = DeconstructedTemplate(
            name="Email Template", content_type="email",
            body="[GREETING],\n\n[OPENING_LINE]\n\n[BODY_PARAGRAPH]\n\n[SIGN_OFF]",
            structure_hint="Greeting -> Opening -> Body -> Sign-off",
            when_to_use="Professional follow-up emails",
        )
        ctx = MagicMock()
        validators = template_builder_agent._output_validators
        result = await validators[0].validate(output, ctx, wrap_validation_errors=False)
        assert result.name == "Email Template"


# --- Agent Tool Tests ---


class TestTemplateAgentTools:
    """Test template builder agent tools."""

    @pytest.mark.asyncio
    async def test_search_template_bank_empty(self, mock_deps):
        ctx = MagicMock()
        ctx.deps = mock_deps
        tool_fn = template_builder_agent._function_toolset.tools["search_template_bank"]
        result = await tool_fn.function(ctx, content_type="linkedin")
        assert "No templates found" in result

    @pytest.mark.asyncio
    async def test_search_template_bank_with_results(self, mock_deps):
        mock_deps.storage_service.get_templates = AsyncMock(return_value=[
            {"name": "LinkedIn Post", "content_type": "linkedin",
             "tags": ["professional"], "structure_hint": "Hook -> Body -> CTA"},
        ])
        ctx = MagicMock()
        ctx.deps = mock_deps
        tool_fn = template_builder_agent._function_toolset.tools["search_template_bank"]
        result = await tool_fn.function(ctx, content_type="linkedin")
        assert "LinkedIn Post" in result
        assert "Hook -> Body -> CTA" in result

    @pytest.mark.asyncio
    async def test_search_existing_patterns_empty(self, mock_deps):
        ctx = MagicMock()
        ctx.deps = mock_deps
        tool_fn = template_builder_agent._function_toolset.tools["search_existing_patterns"]
        result = await tool_fn.function(ctx, topic="")
        assert "No existing patterns found" in result

    @pytest.mark.asyncio
    async def test_search_examples_empty(self, mock_deps):
        ctx = MagicMock()
        ctx.deps = mock_deps
        tool_fn = template_builder_agent._function_toolset.tools["search_examples"]
        result = await tool_fn.function(ctx, content_type="")
        assert "No examples found" in result


# --- API Endpoint Tests ---


class TestTemplateEndpoints:
    """Test template bank REST API endpoints."""

    def test_list_templates_empty(self, client, app):
        app.state.deps.storage_service.get_templates = AsyncMock(return_value=[])
        response = client.get("/api/templates/")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["templates"] == []

    def test_list_templates_with_filter(self, client, app):
        app.state.deps.storage_service.get_templates = AsyncMock(return_value=[
            {"id": "t-1", "name": "LinkedIn Post", "content_type": "linkedin"},
        ])
        response = client.get("/api/templates/?content_type=linkedin")
        assert response.status_code == 200
        assert response.json()["count"] == 1

    def test_get_template_found(self, client, app):
        app.state.deps.storage_service.get_template = AsyncMock(return_value={
            "id": "t-1", "name": "Test", "content_type": "linkedin",
            "body": "[HOOK]\n[BODY]",
        })
        response = client.get("/api/templates/t-1")
        assert response.status_code == 200
        assert response.json()["name"] == "Test"

    def test_get_template_not_found(self, client, app):
        app.state.deps.storage_service.get_template = AsyncMock(return_value=None)
        response = client.get("/api/templates/nonexistent")
        assert response.status_code == 404

    def test_create_template(self, client, app):
        app.state.deps.storage_service.upsert_template = AsyncMock(return_value={
            "id": "t-new", "name": "New Template", "content_type": "email",
        })
        response = client.post("/api/templates/", json={
            "name": "New Template", "content_type": "email",
            "body": "[GREETING]\n[BODY]\n[SIGN_OFF]",
        })
        assert response.status_code == 200
        assert response.json()["id"] == "t-new"

    def test_create_template_missing_body(self, client, app):
        response = client.post("/api/templates/", json={
            "name": "Bad Template", "content_type": "email",
        })
        assert response.status_code == 422  # validation error

    def test_update_template(self, client, app):
        app.state.deps.storage_service.upsert_template = AsyncMock(return_value={
            "id": "t-1", "name": "Updated", "content_type": "linkedin",
        })
        response = client.patch("/api/templates/t-1", json={"name": "Updated"})
        assert response.status_code == 200

    def test_update_template_empty_body(self, client, app):
        response = client.patch("/api/templates/t-1", json={})
        assert response.status_code == 400

    def test_delete_template_success(self, client, app):
        app.state.deps.storage_service.delete_template = AsyncMock(return_value=True)
        response = client.delete("/api/templates/t-1")
        assert response.status_code == 200

    def test_delete_template_not_found(self, client, app):
        app.state.deps.storage_service.delete_template = AsyncMock(return_value=False)
        response = client.delete("/api/templates/nonexistent")
        assert response.status_code == 404

    def test_deconstruct_content(self, client, app):
        mock_output = MagicMock()
        mock_output.model_dump.return_value = {
            "name": "Email Template",
            "content_type": "email",
            "body": "[GREETING]\n[BODY]\n[SIGN_OFF]",
            "structure_hint": "Greeting -> Body -> Sign-off",
            "when_to_use": "Follow-up emails",
            "when_not_to_use": "",
            "customization_guide": "",
            "tags": ["email", "follow-up"],
            "estimated_time_savings": "10 min",
        }
        mock_result = MagicMock()
        mock_result.output = mock_output
        with patch(
            "second_brain.agents.template_builder.template_builder_agent"
        ) as mock_agent:
            mock_agent.run = AsyncMock(return_value=mock_result)
            response = client.post("/api/templates/deconstruct", json={
                "content": "Dear John, Thank you for our meeting yesterday. " * 5,
            })
        assert response.status_code == 200
        assert response.json()["name"] == "Email Template"
