"""Unit tests for get_model() LLM provider factory."""

import pytest
from unittest.mock import patch, MagicMock

from second_brain.config import BrainConfig
from second_brain.models import get_model


# Known env vars that BrainConfig reads — clear to prevent host bleed.
_ENV_VARS = [
    "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_BASE_URL", "OLLAMA_API_KEY",
    "OLLAMA_MODEL", "MEM0_API_KEY", "GRAPH_PROVIDER", "NEO4J_URL", "NEO4J_USERNAME",
    "NEO4J_PASSWORD", "SUPABASE_URL", "SUPABASE_KEY", "BRAIN_USER_ID",
    "BRAIN_DATA_PATH", "PRIMARY_MODEL", "FALLBACK_MODEL", "MEMORY_SEARCH_LIMIT",
    "GRAPH_SEARCH_LIMIT", "PATTERN_CONTEXT_LIMIT", "EXPERIENCE_LIMIT",
    "GRADUATION_MIN_MEMORIES", "GRADUATION_LOOKBACK_DAYS",
    "CONTENT_PREVIEW_LIMIT", "PATTERN_PREVIEW_LIMIT",
]


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Remove all BrainConfig env vars so host values don't bleed into tests."""
    for var in _ENV_VARS:
        monkeypatch.delenv(var, raising=False)


def _make_config(tmp_path, **overrides):
    """Helper to create a BrainConfig with required fields + overrides."""
    defaults = {
        "supabase_url": "https://test.supabase.co",
        "supabase_key": "test-key",
        "brain_data_path": tmp_path,
        "_env_file": None,
    }
    defaults.update(overrides)
    return BrainConfig(**defaults)


class TestGetModelAnthropic:
    """Tests the primary (Anthropic) model path."""

    @patch("pydantic_ai.providers.anthropic.AnthropicProvider")
    @patch("pydantic_ai.models.anthropic.AnthropicModel")
    def test_returns_anthropic_model(self, mock_model_cls, mock_provider_cls, brain_config):
        """get_model() returns AnthropicModel when API key is set."""
        mock_model = MagicMock()
        mock_model_cls.return_value = mock_model

        result = get_model(brain_config)

        mock_provider_cls.assert_called_once_with(api_key="test-key")
        assert result is mock_model

    @patch("pydantic_ai.providers.anthropic.AnthropicProvider")
    @patch("pydantic_ai.models.anthropic.AnthropicModel")
    def test_strips_anthropic_prefix(self, mock_model_cls, mock_provider_cls, brain_config):
        """get_model() strips 'anthropic:' prefix from model name."""
        get_model(brain_config)

        model_name = mock_model_cls.call_args[0][0]
        assert "anthropic:" not in model_name
        assert model_name == "claude-sonnet-4-5"

    @patch("pydantic_ai.providers.anthropic.AnthropicProvider")
    @patch("pydantic_ai.models.anthropic.AnthropicModel")
    def test_anthropic_with_custom_model(self, mock_model_cls, mock_provider_cls, tmp_path):
        """get_model() uses custom primary_model name."""
        config = _make_config(tmp_path, anthropic_api_key="sk-test", primary_model="anthropic:claude-opus-4")

        get_model(config)

        assert mock_model_cls.call_args[0][0] == "claude-opus-4"


class TestGetModelOllamaFallback:
    """Tests the Ollama fallback path when Anthropic is unavailable."""

    @patch("pydantic_ai.providers.ollama.OllamaProvider")
    @patch("pydantic_ai.models.openai.OpenAIChatModel")
    def test_fallback_when_no_api_key(self, mock_openai_cls, mock_ollama_cls, tmp_path):
        """Falls back to Ollama when anthropic_api_key is None."""
        config = _make_config(tmp_path, anthropic_api_key=None)
        mock_model = MagicMock()
        mock_openai_cls.return_value = mock_model

        result = get_model(config)

        mock_ollama_cls.assert_called_once_with(
            base_url="http://localhost:11434/v1", api_key=None
        )
        mock_openai_cls.assert_called_once()
        assert mock_openai_cls.call_args[0][0] == "llama3.1:8b"
        assert result is mock_model

    @patch("pydantic_ai.providers.ollama.OllamaProvider")
    @patch("pydantic_ai.models.openai.OpenAIChatModel")
    @patch("pydantic_ai.providers.anthropic.AnthropicProvider")
    @patch("pydantic_ai.models.anthropic.AnthropicModel")
    def test_fallback_when_anthropic_fails(
        self, mock_anthropic_cls, mock_anthropic_prov, mock_openai_cls, mock_ollama_cls, brain_config
    ):
        """Falls back to Ollama when Anthropic raises an exception."""
        mock_anthropic_cls.side_effect = Exception("API error")
        mock_fallback = MagicMock()
        mock_openai_cls.return_value = mock_fallback

        result = get_model(brain_config)

        mock_openai_cls.assert_called_once()
        assert result is mock_fallback

    @patch("pydantic_ai.providers.ollama.OllamaProvider")
    @patch("pydantic_ai.models.openai.OpenAIChatModel")
    def test_fallback_with_custom_ollama_model(self, mock_openai_cls, mock_ollama_cls, tmp_path):
        """Uses custom ollama_model and ollama_base_url."""
        config = _make_config(
            tmp_path,
            anthropic_api_key=None,
            ollama_model="mistral:7b",
            ollama_base_url="http://gpu-server:11434",
        )

        get_model(config)

        assert mock_openai_cls.call_args[0][0] == "mistral:7b"
        mock_ollama_cls.assert_called_once_with(
            base_url="http://gpu-server:11434/v1", api_key=None
        )

    @patch("pydantic_ai.providers.ollama.OllamaProvider")
    @patch("pydantic_ai.models.openai.OpenAIChatModel")
    def test_fallback_with_ollama_api_key(self, mock_openai_cls, mock_ollama_cls, tmp_path):
        """Passes ollama_api_key to OllamaProvider."""
        config = _make_config(tmp_path, anthropic_api_key=None, ollama_api_key="ollama-key-123")

        get_model(config)

        mock_ollama_cls.assert_called_once_with(
            base_url="http://localhost:11434/v1", api_key="ollama-key-123"
        )


class TestGetModelNoProvider:
    """Tests the RuntimeError path when all providers fail."""

    @patch("pydantic_ai.providers.ollama.OllamaProvider")
    def test_runtime_error_when_all_fail(self, mock_ollama_cls, tmp_path):
        """Raises RuntimeError when no API key and Ollama fails."""
        config = _make_config(tmp_path, anthropic_api_key=None)
        mock_ollama_cls.side_effect = Exception("Connection refused")

        with pytest.raises(RuntimeError):
            get_model(config)

    @patch("pydantic_ai.providers.ollama.OllamaProvider")
    def test_runtime_error_message(self, mock_ollama_cls, tmp_path):
        """Error message tells user to set API key or start Ollama."""
        config = _make_config(tmp_path, anthropic_api_key=None)
        mock_ollama_cls.side_effect = Exception("Connection refused")

        with pytest.raises(RuntimeError, match="No LLM available"):
            get_model(config)

    @patch("pydantic_ai.providers.ollama.OllamaProvider")
    @patch("pydantic_ai.providers.anthropic.AnthropicProvider")
    @patch("pydantic_ai.models.anthropic.AnthropicModel")
    def test_anthropic_fails_ollama_fails(
        self, mock_anthropic_cls, mock_anthropic_prov, mock_ollama_cls, brain_config
    ):
        """RuntimeError when both Anthropic and Ollama fail."""
        mock_anthropic_cls.side_effect = Exception("Anthropic down")
        mock_ollama_cls.side_effect = Exception("Ollama down")

        with pytest.raises(RuntimeError):
            get_model(brain_config)
