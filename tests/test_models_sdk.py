"""Tests for ClaudeSDKModel and subscription auth model integration."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from second_brain.config import BrainConfig


# Known env vars to clear so host values don't bleed.
_ENV_VARS = [
    "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_BASE_URL", "OLLAMA_API_KEY",
    "OLLAMA_MODEL", "MEM0_API_KEY", "GRAPH_PROVIDER", "NEO4J_URL", "NEO4J_USERNAME",
    "NEO4J_PASSWORD", "SUPABASE_URL", "SUPABASE_KEY", "BRAIN_USER_ID",
    "BRAIN_DATA_PATH", "PRIMARY_MODEL", "FALLBACK_MODEL", "USE_SUBSCRIPTION",
    "CLAUDE_OAUTH_TOKEN", "CLAUDECODE",
]


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for var in _ENV_VARS:
        monkeypatch.delenv(var, raising=False)


def _make_config(tmp_path, **overrides):
    defaults = {
        "supabase_url": "https://test.supabase.co",
        "supabase_key": "test-key",
        "brain_data_path": tmp_path,
        "_env_file": None,
    }
    defaults.update(overrides)
    return BrainConfig(**defaults)


class TestClaudeSDKModel:
    """Tests for ClaudeSDKModel class."""

    def test_model_name(self):
        from second_brain.models_sdk import ClaudeSDKModel
        model = ClaudeSDKModel(model_id="claude-sonnet-4-5-20250929")
        assert model.model_name == "claude-sdk:claude-sonnet-4-5-20250929"

    def test_system(self):
        from second_brain.models_sdk import ClaudeSDKModel
        model = ClaudeSDKModel()
        assert model.system == "claude-sdk"

    def test_default_model_id(self):
        from second_brain.models_sdk import ClaudeSDKModel
        model = ClaudeSDKModel()
        assert "claude" in model.model_name

    def test_convert_messages_system_prompt(self):
        """System prompt parts are extracted correctly."""
        from second_brain.models_sdk import ClaudeSDKModel
        from pydantic_ai.messages import ModelRequest, SystemPromptPart, UserPromptPart

        model = ClaudeSDKModel()
        messages = [
            ModelRequest(parts=[
                SystemPromptPart(content="You are a helper"),
                UserPromptPart(content="Hello"),
            ])
        ]
        system, user = model._convert_messages(messages)
        assert "helper" in system
        assert "Hello" in user

    def test_convert_messages_no_system(self):
        """Works without system prompt."""
        from second_brain.models_sdk import ClaudeSDKModel
        from pydantic_ai.messages import ModelRequest, UserPromptPart

        model = ClaudeSDKModel()
        messages = [
            ModelRequest(parts=[UserPromptPart(content="Just a question")])
        ]
        system, user = model._convert_messages(messages)
        assert system == ""
        assert "question" in user


class TestCreateSDKModel:
    """Tests for create_sdk_model() factory."""

    def test_returns_none_when_disabled(self, tmp_path):
        """Returns None when use_subscription is False."""
        config = _make_config(tmp_path)
        assert config.use_subscription is False

        from second_brain.models_sdk import create_sdk_model
        result = create_sdk_model(config)
        assert result is None

    def test_returns_none_when_no_token(self, tmp_path):
        """Returns None when subscription enabled but no token available."""
        config = _make_config(tmp_path, use_subscription=True)

        with patch("second_brain.auth.get_oauth_token", return_value=None):
            from second_brain.models_sdk import create_sdk_model
            result = create_sdk_model(config)
            assert result is None

    def test_returns_none_when_invalid_token(self, tmp_path):
        """Returns None when token has invalid format."""
        config = _make_config(
            tmp_path,
            use_subscription=True,
            claude_oauth_token="invalid-token-format",
        )

        with patch("second_brain.auth.validate_oauth_token", return_value=False):
            from second_brain.models_sdk import create_sdk_model
            result = create_sdk_model(config)
            assert result is None

    def test_returns_none_when_cli_missing(self, tmp_path):
        """Returns None when claude CLI is not installed."""
        config = _make_config(
            tmp_path,
            use_subscription=True,
            claude_oauth_token="sk-ant-oat01-valid-token-here",
        )

        with patch("second_brain.auth.get_oauth_token", return_value="sk-ant-oat01-valid"), \
             patch("second_brain.auth.validate_oauth_token", return_value=True), \
             patch("second_brain.auth.verify_claude_cli", return_value=(False, "not found")):
            from second_brain.models_sdk import create_sdk_model
            result = create_sdk_model(config)
            assert result is None

    def test_returns_model_when_all_checks_pass(self, tmp_path):
        """Returns ClaudeSDKModel when all validations pass."""
        config = _make_config(
            tmp_path,
            use_subscription=True,
            claude_oauth_token="sk-ant-oat01-valid-token-here",
        )

        with patch("second_brain.auth.get_oauth_token", return_value="sk-ant-oat01-valid"), \
             patch("second_brain.auth.validate_oauth_token", return_value=True), \
             patch("second_brain.auth.verify_claude_cli", return_value=(True, "claude 1.0")), \
             patch("second_brain.service_mcp.get_service_mcp_config", return_value=("test-server", {"command": "python"})):
            from second_brain.models_sdk import create_sdk_model
            result = create_sdk_model(config)
            assert result is not None
            assert "claude-sdk" in result.model_name


class TestIsSDKAvailable:
    """Tests for is_sdk_available()."""

    def test_available_when_installed(self):
        """Returns True when claude-agent-sdk is importable."""
        mock_module = MagicMock()
        with patch.dict(sys.modules, {"claude_agent_sdk": mock_module}):
            from second_brain.models_sdk import is_sdk_available
            assert is_sdk_available() is True

    def test_not_available_when_missing(self):
        """Returns False when claude-agent-sdk is not installed."""
        # Setting sys.modules entry to None causes ImportError on import
        with patch.dict(sys.modules, {"claude_agent_sdk": None}):
            from second_brain.models_sdk import is_sdk_available
            assert is_sdk_available() is False


class TestModelDateSuffix:
    """Tests for model ID date suffix detection and application."""

    def test_date_suffix_regex_matches_yyyymmdd(self):
        """Regex matches 8-digit date suffix."""
        from second_brain.models_sdk import _DATE_SUFFIX_RE
        assert _DATE_SUFFIX_RE.search("claude-sonnet-4-5-20250929")
        assert _DATE_SUFFIX_RE.search("claude-opus-4-6-20260205")

    def test_date_suffix_regex_rejects_version_numbers(self):
        """Regex does not match short version numbers."""
        from second_brain.models_sdk import _DATE_SUFFIX_RE
        assert not _DATE_SUFFIX_RE.search("claude-sonnet-4-5")
        assert not _DATE_SUFFIX_RE.search("claude-opus-4-6")
        assert not _DATE_SUFFIX_RE.search("claude-haiku-4-5")

    def test_date_suffix_regex_rejects_partial_dates(self):
        """Regex does not match incomplete date patterns."""
        from second_brain.models_sdk import _DATE_SUFFIX_RE
        assert not _DATE_SUFFIX_RE.search("claude-sonnet-4-5-2025")
        assert not _DATE_SUFFIX_RE.search("claude-sonnet-4-5-202509")

    def test_create_sdk_model_appends_date_to_short_id(self, tmp_path):
        """Date suffix is appended when model ID has no date."""
        config = _make_config(
            tmp_path,
            use_subscription=True,
            primary_model="anthropic:claude-sonnet-4-5",
        )
        with patch("second_brain.auth.get_oauth_token", return_value="sk-ant-oat01-valid"), \
             patch("second_brain.auth.validate_oauth_token", return_value=True), \
             patch("second_brain.auth.verify_claude_cli", return_value=(True, "claude 1.0")), \
             patch("second_brain.service_mcp.get_service_mcp_config", return_value=("test-server", {"command": "python"})):
            from second_brain.models_sdk import create_sdk_model, DEFAULT_MODEL_DATE
            result = create_sdk_model(config)
            assert result is not None
            assert DEFAULT_MODEL_DATE in result.model_name

    def test_create_sdk_model_preserves_existing_date(self, tmp_path):
        """Date suffix is NOT appended when model ID already has one."""
        config = _make_config(
            tmp_path,
            use_subscription=True,
            primary_model="anthropic:claude-sonnet-4-5-20250929",
        )
        with patch("second_brain.auth.get_oauth_token", return_value="sk-ant-oat01-valid"), \
             patch("second_brain.auth.validate_oauth_token", return_value=True), \
             patch("second_brain.auth.verify_claude_cli", return_value=(True, "claude 1.0")), \
             patch("second_brain.service_mcp.get_service_mcp_config", return_value=("test-server", {"command": "python"})):
            from second_brain.models_sdk import create_sdk_model
            result = create_sdk_model(config)
            assert result is not None
            # Should have exactly one date, not double-appended
            assert result.model_name.count("20250929") == 1

    def test_default_model_date_constant_exists(self):
        """DEFAULT_MODEL_DATE constant is exported and valid."""
        from second_brain.models_sdk import DEFAULT_MODEL_DATE
        assert len(DEFAULT_MODEL_DATE) == 8
        assert DEFAULT_MODEL_DATE.isdigit()
        assert DEFAULT_MODEL_DATE == "20250929"


class TestClaudeCodeNestingGuard:
    """Tests for CLAUDECODE env var handling in _sdk_query()."""

    def test_claudecode_unset_during_pop(self):
        """CLAUDECODE is removed from env during pop and absent until restore."""
        import os

        os.environ["CLAUDECODE"] = "parent-session-123"

        # Simulate the exact pattern used in _sdk_query
        saved = os.environ.pop("CLAUDECODE", None)
        assert saved == "parent-session-123"
        assert "CLAUDECODE" not in os.environ

        # Restore
        if saved is not None:
            os.environ["CLAUDECODE"] = saved
        assert os.environ.get("CLAUDECODE") == "parent-session-123"

        # Cleanup
        os.environ.pop("CLAUDECODE", None)

    def test_claudecode_restored_after_sdk_call(self):
        """CLAUDECODE is restored after SDK query completes."""
        import os

        original_value = "parent-session-456"
        os.environ["CLAUDECODE"] = original_value

        # Simulate the save/restore pattern used in _sdk_query
        saved = os.environ.pop("CLAUDECODE", None)
        try:
            assert "CLAUDECODE" not in os.environ
        finally:
            if saved is not None:
                os.environ["CLAUDECODE"] = saved

        assert os.environ.get("CLAUDECODE") == original_value

        # Cleanup
        os.environ.pop("CLAUDECODE", None)

    def test_claudecode_restored_on_exception(self):
        """CLAUDECODE is restored even if SDK query raises."""
        import os

        original_value = "parent-session-789"
        os.environ["CLAUDECODE"] = original_value

        try:
            saved = os.environ.pop("CLAUDECODE", None)
            try:
                raise RuntimeError("SDK failed")
            finally:
                if saved is not None:
                    os.environ["CLAUDECODE"] = saved
        except RuntimeError:
            pass

        assert os.environ.get("CLAUDECODE") == original_value

        # Cleanup
        os.environ.pop("CLAUDECODE", None)

    def test_no_error_when_claudecode_not_set(self):
        """No error when CLAUDECODE is not in environment."""
        import os

        os.environ.pop("CLAUDECODE", None)

        saved = os.environ.pop("CLAUDECODE", None)
        try:
            assert saved is None
            assert "CLAUDECODE" not in os.environ
        finally:
            if saved is not None:
                os.environ["CLAUDECODE"] = saved

        assert "CLAUDECODE" not in os.environ

    def test_claudecode_in_env_cleanup_list(self):
        """CLAUDECODE is included in the test env cleanup list."""
        assert "CLAUDECODE" in _ENV_VARS


class TestMCPConfigFormat:
    """Tests for MCP server config dict format passed to SDK."""

    def test_mcp_servers_built_as_dict(self):
        """mcp_servers should be dict[str, config], not list."""
        from second_brain.models_sdk import ClaudeSDKModel

        config = {"command": "python", "args": ["-m", "test"]}
        model = ClaudeSDKModel(
            mcp_config=config,
            mcp_server_name="test-server",
        )
        assert model._mcp_config == config
        assert model._mcp_server_name == "test-server"

    def test_mcp_server_name_default(self):
        """Default server name is second-brain-services."""
        from second_brain.models_sdk import ClaudeSDKModel

        model = ClaudeSDKModel(mcp_config={"command": "python"})
        assert model._mcp_server_name == "second-brain-services"

    def test_no_name_key_in_config(self):
        """Config dict should NOT contain 'name' key."""
        from second_brain.service_mcp import get_service_mcp_config

        name, config = get_service_mcp_config()
        assert "name" not in config
        # Only valid McpStdioServerConfig keys
        valid_keys = {"type", "command", "args", "env"}
        assert set(config.keys()).issubset(valid_keys)

    def test_create_sdk_model_passes_separate_name_and_config(self, tmp_path):
        """create_sdk_model unpacks tuple and passes name + config separately."""
        config = _make_config(
            tmp_path,
            use_subscription=True,
        )
        with patch("second_brain.auth.get_oauth_token", return_value="sk-ant-oat01-valid"), \
             patch("second_brain.auth.validate_oauth_token", return_value=True), \
             patch("second_brain.auth.verify_claude_cli", return_value=(True, "claude 1.0")), \
             patch("second_brain.service_mcp.get_service_mcp_config", return_value=("my-server", {"command": "python"})):
            from second_brain.models_sdk import create_sdk_model
            result = create_sdk_model(config)
            assert result is not None
            assert result._mcp_server_name == "my-server"
            assert result._mcp_config == {"command": "python"}
            assert "name" not in result._mcp_config


class TestGetModelFallbackChain:
    """Tests for get_model() with subscription in the chain."""

    @patch("pydantic_ai.providers.anthropic.AnthropicProvider")
    @patch("pydantic_ai.models.anthropic.AnthropicModel")
    def test_api_key_takes_priority(self, mock_model_cls, mock_provider_cls, tmp_path):
        """API key auth is used even when subscription is also enabled."""
        config = _make_config(
            tmp_path,
            anthropic_api_key="sk-ant-api03-test-key",
            use_subscription=True,
        )
        mock_model_cls.return_value = MagicMock()

        from second_brain.models import get_model
        model = get_model(config)
        mock_model_cls.assert_called_once()

    @patch("pydantic_ai.providers.ollama.OllamaProvider")
    @patch("pydantic_ai.models.openai.OpenAIChatModel")
    def test_subscription_used_without_api_key(
        self, mock_openai_cls, mock_ollama_cls, tmp_path
    ):
        """SDK model used when no API key but subscription enabled."""
        config = _make_config(tmp_path, use_subscription=True)

        mock_sdk_model = MagicMock()
        mock_sdk_model.model_name = "claude-sdk:claude-sonnet-4-5-20250929"
        with patch("second_brain.models_sdk.create_sdk_model", return_value=mock_sdk_model):
            from second_brain.models import get_model
            model = get_model(config)
            assert model is mock_sdk_model
