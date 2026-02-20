"""Unit tests for frontend API client functions.

All tests use the auto-patched mock_client fixture from conftest.py.
Each test configures the mock's return value, calls the api_client function,
and asserts on the result and the mock's call args.
"""

import httpx
from unittest.mock import MagicMock

from tests.helpers import make_response


class TestCheckApiHealth:
    """Tests for check_api_health()."""

    def test_returns_true_when_api_responds_200(self, mock_client):
        mock_client.get.return_value = make_response(200, {"status": "ok"})

        from api_client import check_api_health
        assert check_api_health() is True
        mock_client.get.assert_called_once()

    def test_returns_false_when_api_responds_500(self, mock_client):
        mock_client.get.return_value = make_response(500)

        from api_client import check_api_health
        assert check_api_health() is False

    def test_returns_false_when_connection_error(self, mock_client):
        mock_client.get.side_effect = httpx.ConnectError("Connection refused")

        from api_client import check_api_health
        assert check_api_health() is False

    def test_passes_custom_timeout(self, mock_client):
        mock_client.get.return_value = make_response(200)

        from api_client import check_api_health
        check_api_health(timeout=5.0)
        _, kwargs = mock_client.get.call_args
        assert kwargs["timeout"] == 5.0


class TestCallAgent:
    """Tests for call_agent()."""

    def test_posts_to_correct_endpoint(self, mock_client):
        expected = {"answer": "test response"}
        mock_client.post.return_value = make_response(200, expected)

        from api_client import call_agent
        result = call_agent("/recall", {"query": "test"})

        mock_client.post.assert_called_once_with("/recall", json={"query": "test"})
        assert result == expected

    def test_returns_error_dict_on_http_error(self, mock_client):
        response = make_response(500, {"detail": "Internal error"})
        mock_client.post.return_value = response
        response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "Server Error", request=httpx.Request("POST", "http://test"), response=response
            )
        )

        from api_client import call_agent
        result = call_agent("/recall", {"query": "test"})
        assert "error" in result
        assert "status_code" in result


class TestSearchMemory:
    """Tests for search_memory()."""

    def test_gets_with_params(self, mock_client):
        expected = {"patterns": [{"name": "test"}], "count": 1}
        mock_client.get.return_value = make_response(200, expected)

        from api_client import search_memory
        result = search_memory("/patterns", {"category": "coding"})

        mock_client.get.assert_called_once_with("/patterns", params={"category": "coding"})
        assert result == expected

    def test_gets_without_params_sends_empty_dict(self, mock_client):
        expected = {"patterns": [], "count": 0}
        mock_client.get.return_value = make_response(200, expected)

        from api_client import search_memory
        result = search_memory("/patterns")

        # search_memory uses `params or {}` so None becomes {}
        mock_client.get.assert_called_once_with("/patterns", params={})
        assert result == expected

    def test_returns_error_dict_on_http_error(self, mock_client):
        response = make_response(500)
        mock_client.get.return_value = response
        response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "Server Error", request=httpx.Request("GET", "http://test"), response=response
            )
        )

        from api_client import search_memory
        result = search_memory("/patterns")
        assert "error" in result


class TestSemanticSearch:
    """Tests for semantic_search()."""

    def test_delegates_to_call_agent_with_recall(self, mock_client):
        expected = {"matches": [{"content": "test", "score": 0.9}]}
        mock_client.post.return_value = make_response(200, expected)

        from api_client import semantic_search
        result = semantic_search("test query")

        mock_client.post.assert_called_once_with("/recall", json={"query": "test query"})
        assert result == expected


class TestVectorSearch:
    """Tests for vector_search()."""

    def test_posts_with_correct_payload(self, mock_client):
        expected = {"results": []}
        mock_client.post.return_value = make_response(200, expected)

        from api_client import vector_search
        result = vector_search("test", table="pattern_registry", limit=5)

        mock_client.post.assert_called_once_with(
            "/search/vector",
            json={"query": "test", "table": "pattern_registry", "limit": 5},
        )
        assert result == expected

    def test_uses_default_table_and_limit(self, mock_client):
        mock_client.post.return_value = make_response(200, {})

        from api_client import vector_search
        vector_search("test")

        call_args = mock_client.post.call_args
        payload = call_args[1]["json"]
        assert payload["table"] == "memory_content"
        assert payload["limit"] == 10


class TestDeleteItem:
    """Tests for delete_item()."""

    def test_deletes_correct_resource(self, mock_client):
        mock_client.delete.return_value = make_response(200, {"deleted": True})

        from api_client import delete_item
        result = delete_item("pattern", "abc-123")

        mock_client.delete.assert_called_once_with("/items/pattern/abc-123")
        assert result == {"deleted": True}


class TestHealthEndpoints:
    """Tests for health-related functions."""

    def test_get_health(self, mock_client):
        expected = {"total_memories": 42}
        mock_client.get.return_value = make_response(200, expected)

        from api_client import get_health
        assert get_health() == expected

    def test_get_growth(self, mock_client):
        expected = {"growth": []}
        mock_client.get.return_value = make_response(200, expected)

        from api_client import get_growth
        result = get_growth(days=7)
        mock_client.get.assert_called_once_with("/health/growth", params={"days": 7})
        assert result == expected

    def test_get_milestones(self, mock_client):
        expected = {"level": 3, "milestones": []}
        mock_client.get.return_value = make_response(200, expected)

        from api_client import get_milestones
        assert get_milestones() == expected

    def test_get_quality(self, mock_client):
        expected = {"avg_score": 8.5}
        mock_client.get.return_value = make_response(200, expected)

        from api_client import get_quality
        result = get_quality(days=7)
        mock_client.get.assert_called_once_with("/health/quality", params={"days": 7})
        assert result == expected

    def test_get_setup(self, mock_client):
        expected = {"configured": True}
        mock_client.get.return_value = make_response(200, expected)

        from api_client import get_setup
        assert get_setup() == expected


class TestProjectEndpoints:
    """Tests for project-related functions."""

    def test_list_projects_with_filter(self, mock_client):
        expected = {"projects": []}
        mock_client.get.return_value = make_response(200, expected)

        from api_client import list_projects
        result = list_projects(lifecycle_stage="active")
        mock_client.get.assert_called_once_with("/projects/", params={"lifecycle_stage": "active"})
        assert result == expected

    def test_list_projects_no_filter(self, mock_client):
        mock_client.get.return_value = make_response(200, {"projects": []})

        from api_client import list_projects
        list_projects()
        mock_client.get.assert_called_once_with("/projects/", params={})

    def test_get_project(self, mock_client):
        expected = {"id": "proj-1", "name": "Test"}
        mock_client.get.return_value = make_response(200, expected)

        from api_client import get_project
        result = get_project("proj-1")
        mock_client.get.assert_called_once_with("/projects/proj-1")
        assert result == expected

    def test_create_project(self, mock_client):
        expected = {"id": "proj-1", "name": "Test"}
        mock_client.post.return_value = make_response(200, expected)

        from api_client import create_project
        result = create_project("Test", category="content", description="A test project")
        mock_client.post.assert_called_once_with(
            "/projects/",
            json={"name": "Test", "category": "content", "description": "A test project"},
        )
        assert result == expected

    def test_create_project_without_description(self, mock_client):
        mock_client.post.return_value = make_response(200, {"id": "proj-1"})

        from api_client import create_project
        create_project("Test")
        payload = mock_client.post.call_args[1]["json"]
        assert "description" not in payload

    def test_delete_project(self, mock_client):
        mock_client.delete.return_value = make_response(200, {"deleted": True})

        from api_client import delete_project
        result = delete_project("proj-1")
        mock_client.delete.assert_called_once_with("/projects/proj-1")
        assert result == {"deleted": True}


class TestContentTypes:
    """Tests for get_content_types()."""

    def test_returns_content_types(self, mock_client):
        expected = {"content_types": [{"slug": "linkedin"}, {"slug": "email"}]}
        mock_client.get.return_value = make_response(200, expected)

        from api_client import get_content_types
        result = get_content_types()
        assert result == expected


class TestGraphEndpoints:
    """Tests for graph-related functions."""

    def test_graph_search(self, mock_client):
        expected = {"results": []}
        mock_client.post.return_value = make_response(200, expected)

        from api_client import graph_search
        result = graph_search("test query", limit=5)
        mock_client.post.assert_called_once_with(
            "/graph/search", json={"query": "test query", "limit": 5}
        )
        assert result == expected

    def test_graph_health(self, mock_client):
        expected = {"status": "healthy"}
        mock_client.get.return_value = make_response(200, expected)

        from api_client import graph_health
        assert graph_health() == expected

    def test_graph_episodes(self, mock_client):
        expected = {"episodes": []}
        mock_client.get.return_value = make_response(200, expected)

        from api_client import graph_episodes
        result = graph_episodes(group_id="grp-1")
        mock_client.get.assert_called_once_with("/graph/episodes", params={"group_id": "grp-1"})
        assert result == expected

    def test_graph_episodes_no_group(self, mock_client):
        mock_client.get.return_value = make_response(200, {"episodes": []})

        from api_client import graph_episodes
        graph_episodes()
        mock_client.get.assert_called_once_with("/graph/episodes", params={})


class TestSettingsEndpoints:
    """Tests for settings-related functions."""

    def test_get_settings_config(self, mock_client):
        expected = {"model_provider": "anthropic"}
        mock_client.get.return_value = make_response(200, expected)

        from api_client import get_settings_config
        assert get_settings_config() == expected

    def test_get_settings_providers(self, mock_client):
        expected = {"providers": ["anthropic", "openai"]}
        mock_client.get.return_value = make_response(200, expected)

        from api_client import get_settings_providers
        assert get_settings_providers() == expected
