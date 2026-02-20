"""Unit tests for frontend configuration.

Tests URL validation, constant definitions, and config structure.
"""

import os

import pytest
from unittest.mock import patch


class TestFastapiUrlValidation:
    """Tests for FASTAPI_URL validation at module load time."""

    def test_default_url_is_valid(self):
        """Default localhost URL should pass validation."""
        import importlib
        import config
        importlib.reload(config)
        assert config.FASTAPI_URL == "http://localhost:8001"
        assert config.API_BASE == "http://localhost:8001/api"

    def test_custom_valid_url(self):
        """Custom valid URL from environment should work."""
        import importlib
        with patch.dict(os.environ, {"SECOND_BRAIN_API_URL": "https://api.example.com:9000"}):
            import config
            importlib.reload(config)
            assert config.FASTAPI_URL == "https://api.example.com:9000"
            assert config.API_BASE == "https://api.example.com:9000/api"

    def test_invalid_url_raises_value_error(self):
        """Invalid URL should raise ValueError at import time."""
        import importlib
        with patch.dict(os.environ, {"SECOND_BRAIN_API_URL": "not-a-url"}):
            with pytest.raises(ValueError, match="Invalid SECOND_BRAIN_API_URL"):
                import config
                importlib.reload(config)

    def test_empty_url_raises_value_error(self):
        """Empty URL should raise ValueError."""
        import importlib
        with patch.dict(os.environ, {"SECOND_BRAIN_API_URL": ""}):
            with pytest.raises(ValueError, match="Invalid SECOND_BRAIN_API_URL"):
                import config
                importlib.reload(config)


class TestDeleteTableMap:
    """Tests for DELETE_TABLE_MAP constant."""

    def test_all_memory_table_keys_have_mapping(self):
        """Every key in MEMORY_TABLES should have a DELETE_TABLE_MAP entry."""
        from config import MEMORY_TABLES, DELETE_TABLE_MAP
        for key in MEMORY_TABLES:
            assert key in DELETE_TABLE_MAP, f"Missing DELETE_TABLE_MAP entry for '{key}'"

    def test_mapping_values_are_strings(self):
        """Mapped values should be non-empty strings."""
        from config import DELETE_TABLE_MAP
        for plural, singular in DELETE_TABLE_MAP.items():
            assert isinstance(singular, str)
            assert len(singular) > 0

    def test_knowledge_maps_to_knowledge(self):
        """'knowledge' is irregular — should map to 'knowledge' not 'knowledg'."""
        from config import DELETE_TABLE_MAP
        assert DELETE_TABLE_MAP["knowledge"] == "knowledge"


class TestDefaultContentTypes:
    """Tests for DEFAULT_CONTENT_TYPES constant."""

    def test_is_non_empty_list(self):
        from config import DEFAULT_CONTENT_TYPES
        assert isinstance(DEFAULT_CONTENT_TYPES, list)
        assert len(DEFAULT_CONTENT_TYPES) > 0

    def test_all_entries_are_strings(self):
        from config import DEFAULT_CONTENT_TYPES
        for ct in DEFAULT_CONTENT_TYPES:
            assert isinstance(ct, str)

    def test_contains_common_types(self):
        """Should contain at least the most common content types."""
        from config import DEFAULT_CONTENT_TYPES
        assert "linkedin" in DEFAULT_CONTENT_TYPES
        assert "email" in DEFAULT_CONTENT_TYPES


class TestAgentsConfig:
    """Tests for AGENTS configuration dict structure."""

    def test_all_agents_have_required_keys(self):
        """Each agent config must have name, icon, endpoint, input_field, input_label."""
        from config import AGENTS
        required_keys = {"name", "icon", "endpoint", "input_field", "input_label", "description"}
        for agent_key, agent_config in AGENTS.items():
            for key in required_keys:
                assert key in agent_config, f"Agent '{agent_key}' missing required key '{key}'"

    def test_agent_endpoints_start_with_slash(self):
        """All endpoints should be relative paths starting with /."""
        from config import AGENTS
        for agent_key, agent_config in AGENTS.items():
            endpoint = agent_config["endpoint"]
            assert endpoint.startswith("/"), f"Agent '{agent_key}' endpoint '{endpoint}' must start with /"

    def test_agent_count(self):
        """Verify expected agent count (catches accidental deletions)."""
        from config import AGENTS
        assert len(AGENTS) >= 10, f"Expected at least 10 agents, got {len(AGENTS)}"


class TestMemoryTablesConfig:
    """Tests for MEMORY_TABLES configuration dict structure."""

    def test_all_tables_have_required_keys(self):
        """Each table config must have name, icon, endpoint, display_fields."""
        from config import MEMORY_TABLES
        required_keys = {"name", "icon", "endpoint", "display_fields"}
        for table_key, table_config in MEMORY_TABLES.items():
            for key in required_keys:
                assert key in table_config, f"Table '{table_key}' missing required key '{key}'"

    def test_display_fields_are_lists(self):
        """display_fields should be a list of strings."""
        from config import MEMORY_TABLES
        for table_key, table_config in MEMORY_TABLES.items():
            assert isinstance(table_config["display_fields"], list), \
                f"Table '{table_key}' display_fields is not a list"


class TestCosAgentMapping:
    """Tests for Chief of Staff to frontend agent name mapping."""

    def test_cos_to_frontend_key_mapping(self):
        """CoS agent names map correctly to frontend keys."""
        from config import cos_to_frontend_key
        assert cos_to_frontend_key("coach") == "coaching"
        assert cos_to_frontend_key("pmo") == "prioritize"
        assert cos_to_frontend_key("synthesizer") == "synthesize"
        assert cos_to_frontend_key("template_builder") == "templates"
        assert cos_to_frontend_key("recall") == "recall"  # identity
        assert cos_to_frontend_key("ask") == "ask"  # identity
        assert cos_to_frontend_key("recall_deep") == "recall"

    def test_cos_agent_map_covers_all_mismatches(self):
        """All CoS routes that differ from frontend keys are mapped."""
        from config import AGENTS, COS_AGENT_MAP, cos_to_frontend_key
        # Every mapped value should exist in AGENTS
        for cos_name, frontend_key in COS_AGENT_MAP.items():
            assert frontend_key in AGENTS, f"COS_AGENT_MAP[{cos_name}] = {frontend_key} not in AGENTS"

    def test_cos_agent_map_identity_fallback(self):
        """Unknown CoS names fall through to identity mapping."""
        from config import cos_to_frontend_key
        # Names not in the map should return as-is
        assert cos_to_frontend_key("unknown_agent") == "unknown_agent"
        assert cos_to_frontend_key("new_agent") == "new_agent"
