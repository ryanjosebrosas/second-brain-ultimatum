"""Tests for the FastAPI REST API."""

import dataclasses
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from second_brain.api.main import create_app
from second_brain.config import BrainConfig
from second_brain.deps import BrainDeps


@pytest.fixture
def mock_brain_config(tmp_path):
    """Create a test BrainConfig for API tests."""
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
    """Create test app with mocked deps."""
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
    # get_content_type_registry returns the registry mock
    mock_deps.get_content_type_registry.return_value = mock_deps.content_type_registry
    application.state.deps = mock_deps
    application.state.model = MagicMock()
    return application


@pytest.fixture
def client(app):
    return TestClient(app)


# --- Agent endpoints ---


class TestRecallEndpoint:
    @patch("second_brain.api.routers.agents.recall_agent")
    def test_recall_success(self, mock_agent, client):
        mock_output = MagicMock()
        mock_output.model_dump.return_value = {"query": "test", "matches": [], "summary": "No results"}
        mock_result = MagicMock()
        mock_result.output = mock_output
        mock_agent.run = AsyncMock(return_value=mock_result)

        response = client.post("/api/recall", json={"query": "test query"})
        assert response.status_code == 200
        data = response.json()
        assert "query" in data

    def test_recall_empty_query(self, client):
        response = client.post("/api/recall", json={"query": ""})
        assert response.status_code == 422


class TestAskEndpoint:
    @patch("second_brain.api.routers.agents.ask_agent")
    def test_ask_success(self, mock_agent, client):
        mock_output = MagicMock()
        mock_output.model_dump.return_value = {"answer": "Test answer", "context_used": []}
        mock_result = MagicMock()
        mock_result.output = mock_output
        mock_agent.run = AsyncMock(return_value=mock_result)

        response = client.post("/api/ask", json={"question": "What is this?"})
        assert response.status_code == 200
        assert "answer" in response.json()


class TestLearnEndpoint:
    @patch("second_brain.api.routers.agents.learn_agent")
    def test_learn_success(self, mock_agent, client):
        mock_output = MagicMock()
        mock_output.model_dump.return_value = {"patterns_extracted": [], "insights": []}
        mock_result = MagicMock()
        mock_result.output = mock_output
        mock_agent.run = AsyncMock(return_value=mock_result)

        response = client.post("/api/learn", json={"content": "Some learning content", "category": "general"})
        assert response.status_code == 200


class TestReviewEndpoint:
    @patch("second_brain.api.routers.agents.run_full_review")
    def test_review_success(self, mock_review, client):
        mock_result = MagicMock()
        mock_result.model_dump.return_value = {
            "overall_score": 8.0, "verdict": "READY TO SEND", "scores": [],
        }
        mock_review.return_value = mock_result

        response = client.post("/api/review", json={"content": "Review this content"})
        assert response.status_code == 200
        assert response.json()["overall_score"] == 8.0


class TestCoachingEndpoint:
    def test_coaching_success(self, client):
        mock_output = MagicMock()
        mock_output.model_dump.return_value = {"session_type": "morning", "next_action": "Plan day"}
        mock_result = MagicMock()
        mock_result.output = mock_output

        with patch("second_brain.agents.coach.coach_agent") as mock_agent:
            mock_agent.run = AsyncMock(return_value=mock_result)
            response = client.post("/api/coaching", json={"request": "Help me plan today"})
        assert response.status_code == 200


class TestPrioritizeEndpoint:
    def test_prioritize_success(self, client):
        mock_output = MagicMock()
        mock_output.model_dump.return_value = {"scored_tasks": [], "coaching_message": "Focus!"}
        mock_result = MagicMock()
        mock_result.output = mock_output

        with patch("second_brain.agents.pmo.pmo_agent") as mock_agent:
            mock_agent.run = AsyncMock(return_value=mock_result)
            response = client.post("/api/prioritize", json={"tasks": "task1, task2, task3"})
        assert response.status_code == 200


class TestEmailEndpoint:
    def test_email_success(self, client):
        mock_output = MagicMock()
        mock_output.model_dump.return_value = {"subject": "Hello", "body": "Hi there", "status": "composed"}
        mock_result = MagicMock()
        mock_result.output = mock_output

        with patch("second_brain.agents.email_agent.email_agent") as mock_agent:
            mock_agent.run = AsyncMock(return_value=mock_result)
            response = client.post("/api/email", json={"request": "Draft follow-up"})
        assert response.status_code == 200


class TestSpecialistEndpoint:
    def test_specialist_success(self, client):
        mock_output = MagicMock()
        mock_output.model_dump.return_value = {"answer": "Use pydantic-ai", "confidence_level": "HIGH"}
        mock_result = MagicMock()
        mock_result.output = mock_output

        with patch("second_brain.agents.specialist.specialist_agent") as mock_agent:
            mock_agent.run = AsyncMock(return_value=mock_result)
            response = client.post("/api/specialist", json={"question": "How to use pydantic-ai?"})
        assert response.status_code == 200


# --- Memory endpoints ---


class TestMemoryEndpoints:
    def test_search_examples(self, client, app):
        app.state.deps.storage_service.get_examples = AsyncMock(return_value=[
            {"title": "Example 1", "content_type": "linkedin"},
        ])
        response = client.get("/api/search/examples")
        assert response.status_code == 200
        assert response.json()["count"] == 1

    def test_search_knowledge(self, client, app):
        app.state.deps.storage_service.get_knowledge = AsyncMock(return_value=[])
        response = client.get("/api/search/knowledge")
        assert response.status_code == 200
        assert response.json()["count"] == 0

    def test_search_experiences(self, client, app):
        app.state.deps.storage_service.get_experiences = AsyncMock(return_value=[])
        response = client.get("/api/search/experiences")
        assert response.status_code == 200

    def test_search_patterns(self, client, app):
        app.state.deps.storage_service.get_patterns = AsyncMock(return_value=[
            {"name": "Hook First", "confidence": "HIGH", "pattern_text": "Start with a hook"},
        ])
        response = client.get("/api/search/patterns?keyword=hook")
        assert response.status_code == 200
        assert response.json()["count"] == 1

    def test_vector_search(self, client, app):
        app.state.deps.embedding_service.embed_query = AsyncMock(return_value=[0.1] * 1024)
        app.state.deps.storage_service.vector_search = AsyncMock(return_value=[])
        response = client.post("/api/search/vector", json={"query": "test"})
        assert response.status_code == 200

    def test_vector_search_no_embedding_service(self, client, app):
        app.state.deps.embedding_service = None
        response = client.post("/api/search/vector", json={"query": "test"})
        assert response.status_code == 400

    def test_ingest_example(self, client, app):
        app.state.deps.storage_service.upsert_example = AsyncMock(return_value={"id": "ex-1"})
        response = client.post("/api/ingest/example", json={
            "content_type": "linkedin", "title": "Good Post", "content": "Hook first..."
        })
        assert response.status_code == 200
        assert "ex-1" in response.json()["id"]

    def test_ingest_knowledge(self, client, app):
        app.state.deps.storage_service.upsert_knowledge = AsyncMock(return_value={"id": "kn-1"})
        response = client.post("/api/ingest/knowledge", json={
            "category": "audience", "title": "Enterprise Buyers", "content": "They value..."
        })
        assert response.status_code == 200

    def test_delete_item(self, client, app):
        app.state.deps.storage_service.delete_pattern = AsyncMock(return_value=True)
        response = client.delete("/api/items/pattern/some-uuid")
        assert response.status_code == 200

    def test_delete_item_invalid_table(self, client, app):
        response = client.delete("/api/items/invalid_table/some-uuid")
        assert response.status_code == 400

    def test_delete_item_not_found(self, client, app):
        app.state.deps.storage_service.delete_pattern = AsyncMock(return_value=False)
        response = client.delete("/api/items/pattern/nonexistent-uuid")
        assert response.status_code == 404

    def test_list_content_types(self, client, app):
        mock_registry = MagicMock()
        mock_type = MagicMock()
        mock_type.name = "LinkedIn Post"
        mock_type.default_mode = "casual"
        mock_type.max_words = 300
        mock_type.is_builtin = True
        mock_type.structure_hint = "Hook -> Body -> CTA"
        mock_type.description = "A LinkedIn post"
        mock_type.writing_instructions = "Write with hooks"
        mock_type.length_guidance = "50-300 words"
        mock_type.ui_config = {"icon": "linkedin", "color": "#0077b5", "category": "social"}
        mock_registry.get_all = AsyncMock(return_value={"linkedin": mock_type})
        app.state.deps.get_content_type_registry.return_value = mock_registry
        response = client.get("/api/content-types")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        ct = data["content_types"][0]
        assert ct["description"] == "A LinkedIn post"
        assert ct["writing_instructions"] == "Write with hooks"
        assert ct["length_guidance"] == "50-300 words"
        assert ct["ui_config"]["category"] == "social"

    def test_list_content_types_empty(self, client, app):
        mock_registry = MagicMock()
        mock_registry.get_all = AsyncMock(return_value={})
        app.state.deps.get_content_type_registry.return_value = mock_registry
        response = client.get("/api/content-types")
        assert response.status_code == 200
        assert response.json()["count"] == 0
        assert response.json()["content_types"] == []


class TestFileIngest:
    """Tests for /ingest/file endpoint."""

    def test_ingest_image(self, client, app):
        app.state.deps.memory_service.add_multimodal = AsyncMock(return_value={"id": "mem-1"})
        app.state.deps.embedding_service = None
        response = client.post(
            "/api/ingest/file",
            files={"file": ("test.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 100, "image/png")},
            data={"context": "A test image", "category": "visual"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "image"
        assert data["memory_stored"] is True

    def test_ingest_pdf(self, client, app):
        app.state.deps.memory_service.add_multimodal = AsyncMock(return_value={"id": "mem-2"})
        response = client.post(
            "/api/ingest/file",
            files={"file": ("doc.pdf", b"%PDF-1.4 test content", "application/pdf")},
            data={"context": "", "category": "document"},
        )
        assert response.status_code == 200
        assert response.json()["type"] == "pdf"

    def test_ingest_text_file(self, client, app):
        app.state.deps.memory_service.add = AsyncMock(return_value={"id": "mem-3"})
        response = client.post(
            "/api/ingest/file",
            files={"file": ("notes.txt", b"Some text notes here", "text/plain")},
            data={"context": "", "category": "general"},
        )
        assert response.status_code == 200
        assert response.json()["type"] == "text"

    def test_ingest_unsupported_type(self, client, app):
        response = client.post(
            "/api/ingest/file",
            files={"file": ("program.exe", b"\x00\x01", "application/octet-stream")},
            data={"context": "", "category": "general"},
        )
        assert response.status_code == 400
        assert "Unsupported file type" in response.json()["detail"]

    def test_ingest_file_too_large(self, client, app):
        # 21 MB of zeros
        large_content = b"\x00" * (21 * 1024 * 1024)
        response = client.post(
            "/api/ingest/file",
            files={"file": ("big.png", large_content, "image/png")},
            data={"context": "", "category": "general"},
        )
        assert response.status_code == 413
        assert "too large" in response.json()["detail"]

    def test_ingest_pdf_by_extension(self, client, app):
        """Files with .pdf extension are treated as PDF even without PDF mime type."""
        app.state.deps.memory_service.add_multimodal = AsyncMock(return_value={"id": "mem-4"})
        response = client.post(
            "/api/ingest/file",
            files={"file": ("report.pdf", b"fake pdf", "application/octet-stream")},
            data={"context": "A report", "category": "document"},
        )
        assert response.status_code == 200
        assert response.json()["type"] == "pdf"

    def test_ingest_markdown_file(self, client, app):
        """Markdown files are treated as text."""
        app.state.deps.memory_service.add = AsyncMock(return_value={"id": "mem-5"})
        response = client.post(
            "/api/ingest/file",
            files={"file": ("readme.md", b"# Hello\n\nWorld", "application/octet-stream")},
            data={"context": "", "category": "general"},
        )
        assert response.status_code == 200
        assert response.json()["type"] == "text"

    def test_pattern_registry(self, client, app):
        app.state.deps.storage_service.get_pattern_registry = AsyncMock(return_value=[])
        response = client.get("/api/pattern-registry")
        assert response.status_code == 200


# --- Health endpoints ---


class TestHealthEndpoints:
    def test_health_metrics(self, client, app):
        from second_brain.services.health import HealthMetrics
        mock_metrics = HealthMetrics(
            memory_count=42, total_patterns=10, high_confidence=3,
            medium_confidence=5, low_confidence=2, experience_count=8,
            graph_provider="none", latest_update="2026-02-20",
            topics={"messaging": 4}, status="healthy",
        )
        with patch("second_brain.services.health.HealthService") as MockHS:
            MockHS.return_value.compute = AsyncMock(return_value=mock_metrics)
            response = client.get("/api/health/metrics")
        assert response.status_code == 200
        data = response.json()
        assert data["memory_count"] == 42
        assert data["total_patterns"] == 10

    def test_growth_report(self, client, app):
        from second_brain.services.health import HealthMetrics
        mock_metrics = HealthMetrics(
            memory_count=42, total_patterns=10, high_confidence=3,
            medium_confidence=5, low_confidence=2, experience_count=8,
            graph_provider="none", latest_update="2026-02-20",
            status="healthy", growth_events_total=5,
        )
        with patch("second_brain.services.health.HealthService") as MockHS:
            MockHS.return_value.compute_growth = AsyncMock(return_value=mock_metrics)
            response = client.get("/api/health/growth?days=7")
        assert response.status_code == 200

    def test_milestones(self, client, app):
        milestone_data = {"level": 3, "level_description": "Growing", "milestones_completed": 5, "milestones_total": 10}
        with patch("second_brain.services.health.HealthService") as MockHS:
            MockHS.return_value.compute_milestones = AsyncMock(return_value=milestone_data)
            response = client.get("/api/health/milestones")
        assert response.status_code == 200
        assert response.json()["level"] == 3

    def test_setup_status(self, client, app):
        setup_data = {"is_complete": False, "completed_count": 3, "total_steps": 5, "steps": []}
        with patch("second_brain.services.health.HealthService") as MockHS:
            MockHS.return_value.compute_setup_status = AsyncMock(return_value=setup_data)
            response = client.get("/api/health/setup")
        assert response.status_code == 200
        assert response.json()["is_complete"] is False


# --- Project endpoints ---


class TestProjectEndpoints:
    def test_list_projects(self, client, app):
        app.state.deps.storage_service.list_projects = AsyncMock(return_value=[
            {"id": "p1", "name": "Test", "lifecycle_stage": "planning"},
        ])
        response = client.get("/api/projects/")
        assert response.status_code == 200
        assert response.json()["count"] == 1

    def test_create_project(self, client, app):
        app.state.deps.storage_service.create_project = AsyncMock(return_value={
            "id": "p1", "name": "New Project", "lifecycle_stage": "planning",
        })
        response = client.post("/api/projects/", json={"name": "New Project"})
        assert response.status_code == 200
        assert response.json()["name"] == "New Project"

    def test_get_project(self, client, app):
        app.state.deps.storage_service.get_project = AsyncMock(return_value={
            "id": "p1", "name": "Test", "lifecycle_stage": "planning",
        })
        response = client.get("/api/projects/p1")
        assert response.status_code == 200

    def test_get_project_not_found(self, client, app):
        app.state.deps.storage_service.get_project = AsyncMock(return_value=None)
        response = client.get("/api/projects/nonexistent")
        assert response.status_code == 404

    def test_delete_project(self, client, app):
        app.state.deps.storage_service.get_project = AsyncMock(return_value={
            "id": "p1", "name": "Test",
        })
        app.state.deps.storage_service.delete_project = AsyncMock(return_value=True)
        response = client.delete("/api/projects/p1")
        assert response.status_code == 200

    def test_add_artifact(self, client, app):
        app.state.deps.storage_service.add_project_artifact = AsyncMock(return_value={
            "id": "art-1", "artifact_type": "plan",
        })
        response = client.post("/api/projects/p1/artifacts", json={
            "artifact_type": "plan", "title": "Phase 1 Plan",
        })
        assert response.status_code == 200

    def test_add_artifact_invalid_type(self, client, app):
        response = client.post("/api/projects/p1/artifacts", json={
            "artifact_type": "invalid",
        })
        assert response.status_code == 400


# --- Graph endpoints ---


class TestGraphEndpoints:
    def test_graph_health_disabled(self, client, app):
        response = client.get("/api/graph/health")
        assert response.status_code == 200
        assert response.json()["status"] == "disabled"

    def test_graph_search_disabled(self, client, app):
        response = client.post("/api/graph/search", json={"query": "test"})
        assert response.status_code == 404

    def test_graph_health_enabled(self, client, app):
        mock_graphiti = AsyncMock()
        mock_graphiti.health_check = AsyncMock(return_value={"status": "healthy", "backend": "neo4j"})
        app.state.deps.graphiti_service = mock_graphiti
        response = client.get("/api/graph/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_graph_search_enabled(self, client, app):
        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[
            {"source": "A", "relationship": "uses", "target": "B"},
        ])
        app.state.deps.graphiti_service = mock_graphiti
        response = client.post("/api/graph/search", json={"query": "test"})
        assert response.status_code == 200
        assert response.json()["count"] == 1

    def test_graph_episodes_disabled(self, client, app):
        response = client.get("/api/graph/episodes")
        assert response.status_code == 404

    def test_graph_episode_count_disabled(self, client, app):
        response = client.get("/api/graph/episode-count")
        assert response.status_code == 404


# --- Settings endpoints ---


class TestSettingsEndpoints:
    def test_config_redacted(self, client, app):
        response = client.get("/api/settings/config")
        assert response.status_code == 200
        data = response.json()
        # Secret fields should be redacted
        assert data["anthropic_api_key"] == "***"
        assert data["openai_api_key"] == "***"
        assert data["supabase_key"] == "***"
        # Non-secret fields should be present
        assert data["model_provider"] == "anthropic"

    def test_providers_info(self, client, app):
        response = client.get("/api/settings/providers")
        assert response.status_code == 200
        data = response.json()
        assert data["model_provider"] == "anthropic"
        assert "services" in data
        assert data["services"]["graphiti"] is None  # disabled


# --- 503 when deps not initialized ---


class TestDepsNotInitialized:
    def test_503_when_deps_none(self):
        application = create_app()
        application.state.deps = None
        test_client = TestClient(application)
        response = test_client.get("/api/health/metrics")
        assert response.status_code == 503
        assert "not initialized" in response.json()["detail"]


class TestModelNotInitialized:
    """Test that agent endpoints return 503 when model is None."""

    def test_recall_503_when_model_none(self):
        application = create_app()
        mock_deps = MagicMock(spec=BrainDeps)
        mock_deps.config = MagicMock()
        application.state.deps = mock_deps
        application.state.model = None
        test_client = TestClient(application)
        response = test_client.post("/api/recall", json={"query": "test"})
        assert response.status_code == 503
        assert "LLM model not initialized" in response.json()["detail"]

    def test_ask_503_when_model_none(self):
        application = create_app()
        mock_deps = MagicMock(spec=BrainDeps)
        mock_deps.config = MagicMock()
        application.state.deps = mock_deps
        application.state.model = None
        test_client = TestClient(application)
        response = test_client.post("/api/ask", json={"question": "test"})
        assert response.status_code == 503
        assert "LLM model not initialized" in response.json()["detail"]


class TestAgentError:
    """Test that agent exceptions return 502, not 500."""

    @patch("second_brain.api.routers.agents.recall_agent")
    def test_recall_502_on_agent_exception(self, mock_agent, client):
        mock_agent.run = AsyncMock(side_effect=RuntimeError("Model API unavailable"))
        response = client.post("/api/recall", json={"query": "test"})
        assert response.status_code == 502
        assert "Recall failed" in response.json()["detail"]
        assert "RuntimeError" in response.json()["detail"]

    @patch("second_brain.api.routers.agents.ask_agent")
    def test_ask_502_on_agent_exception(self, mock_agent, client):
        mock_agent.run = AsyncMock(side_effect=ConnectionError("Mem0 unreachable"))
        response = client.post("/api/ask", json={"question": "test"})
        assert response.status_code == 502
        assert "Ask failed" in response.json()["detail"]

    @patch("second_brain.api.routers.agents.recall_agent")
    def test_recall_504_on_timeout(self, mock_agent, client, app):
        app.state.deps.config.api_timeout_seconds = 0.001

        async def slow_run(*args, **kwargs):
            import asyncio
            await asyncio.sleep(1)
        mock_agent.run = slow_run
        response = client.post("/api/recall", json={"query": "test"})
        assert response.status_code == 504
        assert "timed out" in response.json()["detail"]


class TestHealthProbes:
    """Test lightweight health probes."""

    def test_liveness_always_200(self):
        application = create_app()
        application.state.deps = None
        application.state.model = None
        test_client = TestClient(application)
        response = test_client.get("/api/health/live")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert "uptime_seconds" in response.json()

    def test_readiness_503_when_deps_none(self):
        application = create_app()
        application.state.deps = None
        application.state.model = None
        application.state.init_error = "Mem0 connection refused"
        test_client = TestClient(application)
        response = test_client.get("/api/health/ready")
        assert response.status_code == 503
        assert "not_ready" in response.json()["status"]
        assert "Mem0 connection refused" in response.json()["error"]

    def test_readiness_200_when_initialized(self, client):
        response = client.get("/api/health/ready")
        assert response.status_code == 200
        assert response.json()["status"] == "ready"

    def test_readiness_model_unavailable(self):
        application = create_app()
        mock_deps = MagicMock(spec=BrainDeps)
        application.state.deps = mock_deps
        application.state.model = None
        application.state.init_error = "LLM model: No provider available"
        test_client = TestClient(application)
        response = test_client.get("/api/health/ready")
        assert response.status_code == 200  # deps are OK, so ready
        data = response.json()
        assert data["status"] == "ready"
        assert data["model"] == "unavailable"
