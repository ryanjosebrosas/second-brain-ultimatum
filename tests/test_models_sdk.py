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
    "CLAUDE_OAUTH_TOKEN",
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
        model = ClaudeSDKModel(model_id="claude-sonnet-4-5-20250514")
        assert model.model_name == "claude-sdk:claude-sonnet-4-5-20250514"

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
             patch("second_brain.service_mcp.get_service_mcp_config", return_value={"name": "test"}):
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
        mock_sdk_model.model_name = "claude-sdk:claude-sonnet-4-5-20250514"
        with patch("second_brain.models_sdk.create_sdk_model", return_value=mock_sdk_model):
            from second_brain.models import get_model
            model = get_model(config)
            assert model is mock_sdk_model
