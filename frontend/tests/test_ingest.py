"""Tests for ingestion feature — config helpers and API client methods.

Tests config.group_content_types_by_category, KNOWLEDGE_CATEGORIES,
and new api_client methods: ingest_example, ingest_knowledge, upload_file.
"""

import httpx
from unittest.mock import MagicMock

from tests.helpers import make_response


# --- Config helper tests ---


class TestGroupContentTypesByCategory:
    """Tests for group_content_types_by_category()."""

    def test_groups_by_ui_config_category(self):
        from config import group_content_types_by_category

        types = {
            "linkedin": {"name": "LinkedIn Post", "ui_config": {"category": "social"}},
            "email": {"name": "Professional Email", "ui_config": {"category": "communication"}},
            "instagram": {"name": "Instagram Post", "ui_config": {"category": "social"}},
            "case-study": {"name": "Case Study", "ui_config": {"category": "long-form"}},
        }
        result = group_content_types_by_category(types)
        assert "Social Media" in result
        assert len(result["Social Media"]) == 2
        assert ("linkedin", "LinkedIn Post") in result["Social Media"]
        assert ("instagram", "Instagram Post") in result["Social Media"]
        assert "Communication" in result
        assert "Long-Form Writing" in result

    def test_empty_dict_returns_empty(self):
        from config import group_content_types_by_category

        result = group_content_types_by_category({})
        assert result == {}

    def test_missing_ui_config_goes_to_other(self):
        from config import group_content_types_by_category

        types = {
            "custom": {"name": "Custom Type"},
        }
        result = group_content_types_by_category(types)
        assert "Other" in result
        assert ("custom", "Custom Type") in result["Other"]

    def test_unknown_category_gets_title_cased(self):
        from config import group_content_types_by_category

        types = {
            "tweet": {"name": "Tweet", "ui_config": {"category": "micro-content"}},
        }
        result = group_content_types_by_category(types)
        assert "Micro-Content" in result

    def test_ordering_follows_predefined_categories(self):
        from config import group_content_types_by_category

        types = {
            "essay": {"name": "Essay", "ui_config": {"category": "long-form"}},
            "linkedin": {"name": "LinkedIn", "ui_config": {"category": "social"}},
            "email": {"name": "Email", "ui_config": {"category": "communication"}},
        }
        result = group_content_types_by_category(types)
        keys = list(result.keys())
        assert keys.index("Social Media") < keys.index("Communication")
        assert keys.index("Communication") < keys.index("Long-Form Writing")

    def test_items_sorted_alphabetically_within_group(self):
        from config import group_content_types_by_category

        types = {
            "instagram": {"name": "Instagram Post", "ui_config": {"category": "social"}},
            "linkedin": {"name": "LinkedIn Post", "ui_config": {"category": "social"}},
            "comment": {"name": "Comment", "ui_config": {"category": "social"}},
        }
        result = group_content_types_by_category(types)
        names = [name for slug, name in result["Social Media"]]
        assert names == ["Comment", "Instagram Post", "LinkedIn Post"]


class TestKnowledgeCategories:
    """Tests for KNOWLEDGE_CATEGORIES constant."""

    def test_is_non_empty_list(self):
        from config import KNOWLEDGE_CATEGORIES

        assert isinstance(KNOWLEDGE_CATEGORIES, list)
        assert len(KNOWLEDGE_CATEGORIES) >= 5

    def test_contains_expected_categories(self):
        from config import KNOWLEDGE_CATEGORIES

        assert "audience" in KNOWLEDGE_CATEGORIES
        assert "general" in KNOWLEDGE_CATEGORIES
        assert "product" in KNOWLEDGE_CATEGORIES


class TestContentTypeCategories:
    """Tests for CONTENT_TYPE_CATEGORIES constant."""

    def test_has_expected_keys(self):
        from config import CONTENT_TYPE_CATEGORIES

        assert "social" in CONTENT_TYPE_CATEGORIES
        assert "communication" in CONTENT_TYPE_CATEGORIES
        assert "marketing" in CONTENT_TYPE_CATEGORIES
        assert "business" in CONTENT_TYPE_CATEGORIES
        assert "long-form" in CONTENT_TYPE_CATEGORIES


# --- API client ingest method tests ---


class TestIngestExample:
    """Tests for api_client.ingest_example()."""

    def test_sends_correct_payload(self, mock_client):
        mock_client.post.return_value = make_response(200, {"message": "Example added: Test", "id": "123"})

        from api_client import ingest_example

        result = ingest_example("linkedin", "Test Post", "Hook first...")
        assert result["id"] == "123"
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "/ingest/example"
        payload = call_args[1]["json"]
        assert payload["content_type"] == "linkedin"
        assert payload["title"] == "Test Post"
        assert payload["content"] == "Hook first..."
        assert "notes" not in payload

    def test_includes_notes_when_provided(self, mock_client):
        mock_client.post.return_value = make_response(200, {"message": "OK", "id": "124"})

        from api_client import ingest_example

        ingest_example("email", "Test", "Content", notes="Some notes")
        payload = mock_client.post.call_args[1]["json"]
        assert payload["notes"] == "Some notes"

    def test_returns_error_on_http_error(self, mock_client):
        response = make_response(500)
        mock_client.post.return_value = response
        response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "Server Error", request=httpx.Request("POST", "http://test"), response=response
            )
        )

        from api_client import ingest_example

        result = ingest_example("linkedin", "Test", "Content")
        assert "error" in result


class TestIngestKnowledge:
    """Tests for api_client.ingest_knowledge()."""

    def test_sends_correct_payload(self, mock_client):
        mock_client.post.return_value = make_response(200, {"message": "Knowledge added", "id": "456"})

        from api_client import ingest_knowledge

        result = ingest_knowledge("audience", "ICP", "Enterprise buyers value...")
        assert result["id"] == "456"
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "/ingest/knowledge"
        payload = call_args[1]["json"]
        assert payload["category"] == "audience"
        assert payload["title"] == "ICP"

    def test_includes_tags_when_provided(self, mock_client):
        mock_client.post.return_value = make_response(200, {"message": "OK", "id": "457"})

        from api_client import ingest_knowledge

        ingest_knowledge("audience", "Test", "Content", tags="b2b,enterprise")
        payload = mock_client.post.call_args[1]["json"]
        assert payload["tags"] == "b2b,enterprise"

    def test_returns_error_on_http_error(self, mock_client):
        response = make_response(500)
        mock_client.post.return_value = response
        response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "Server Error", request=httpx.Request("POST", "http://test"), response=response
            )
        )

        from api_client import ingest_knowledge

        result = ingest_knowledge("audience", "Test", "Content")
        assert "error" in result


class TestUploadFile:
    """Tests for api_client.upload_file()."""

    def test_sends_multipart_form_data(self, mock_client):
        mock_client.post.return_value = make_response(200, {
            "message": "Image ingested: test.png", "type": "image", "memory_stored": True,
        })

        from api_client import upload_file

        result = upload_file(b"fake-png-bytes", "test.png", "image/png", context="Test image")
        assert result["type"] == "image"
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "/ingest/file"
        assert "files" in call_args[1]
        assert "data" in call_args[1]
        assert call_args[1]["data"]["context"] == "Test image"

    def test_uses_extended_timeout(self, mock_client):
        mock_client.post.return_value = make_response(200, {"message": "OK", "type": "pdf"})

        from api_client import upload_file

        upload_file(b"pdf-bytes", "doc.pdf", "application/pdf")
        call_args = mock_client.post.call_args
        assert call_args[1]["timeout"] == 180.0

    def test_passes_category(self, mock_client):
        mock_client.post.return_value = make_response(200, {"message": "OK", "type": "text"})

        from api_client import upload_file

        upload_file(b"text", "notes.txt", "text/plain", category="document")
        call_args = mock_client.post.call_args
        assert call_args[1]["data"]["category"] == "document"

    def test_returns_error_on_http_error(self, mock_client):
        response = make_response(413)
        mock_client.post.return_value = response
        response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "File too large", request=httpx.Request("POST", "http://test"), response=response
            )
        )

        from api_client import upload_file

        result = upload_file(b"\x00" * 100, "big.png", "image/png")
        assert "error" in result
