"""Unit tests for LLM provider classes."""

import pytest
from unittest.mock import patch, MagicMock

from second_brain.config import BrainConfig
from second_brain.providers import (
    BaseProvider,
    PROVIDER_REGISTRY,
    get_provider_class,
)
from second_brain.providers.anthropic import AnthropicProvider
from second_brain.providers.ollama import OllamaLocalProvider, OllamaCloudProvider
from second_brain.providers.openai import OpenAIProvider
from second_brain.providers.groq import GroqProvider


# Known env vars -- clear to prevent host bleed.
_ENV_VARS = [
    "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_BASE_URL", "OLLAMA_API_KEY",
    "OLLAMA_MODEL", "SUPABASE_URL", "SUPABASE_KEY", "BRAIN_DATA_PATH",
    "MODEL_PROVIDER", "MODEL_NAME", "MODEL_FALLBACK_CHAIN",
    "OPENAI_MODEL_NAME", "GROQ_API_KEY", "GROQ_MODEL_NAME",
    "USE_SUBSCRIPTION", "CLAUDE_OAUTH_TOKEN",
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


class TestProviderRegistry:
    """Tests for provider registry lookup."""

    def test_all_providers_registered(self):
        """All expected providers are in the registry."""
        expected = {"anthropic", "ollama-local", "ollama-cloud", "openai", "groq"}
        assert expected.issubset(set(PROVIDER_REGISTRY.keys()))

    def test_get_provider_class_returns_correct_class(self):
        assert get_provider_class("anthropic") is AnthropicProvider
        assert get_provider_class("ollama-local") is OllamaLocalProvider
        assert get_provider_class("ollama-cloud") is OllamaCloudProvider
        assert get_provider_class("openai") is OpenAIProvider
        assert get_provider_class("groq") is GroqProvider

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown model provider"):
            get_provider_class("nonexistent")

    def test_error_lists_available_providers(self):
        with pytest.raises(ValueError, match="anthropic"):
            get_provider_class("bad-provider")

    def test_all_providers_inherit_base(self):
        for cls in PROVIDER_REGISTRY.values():
            assert issubclass(cls, BaseProvider)


class TestAnthropicProvider:
    """Tests for Anthropic provider."""

    def test_validate_config_valid(self):
        provider = AnthropicProvider(api_key="sk-test")
        assert provider.validate_config() is True

    def test_validate_config_missing_key(self):
        provider = AnthropicProvider(api_key="")
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
            provider.validate_config()

    @patch("pydantic_ai.providers.anthropic.AnthropicProvider")
    @patch("pydantic_ai.models.anthropic.AnthropicModel")
    def test_build_model(self, mock_model_cls, mock_provider_cls):
        provider = AnthropicProvider(api_key="sk-test")
        mock_model_cls.return_value = MagicMock()

        model = provider.build_model("claude-sonnet-4-5")

        mock_model_cls.assert_called_once()
        assert mock_model_cls.call_args[0][0] == "claude-sonnet-4-5"

    @patch("pydantic_ai.providers.anthropic.AnthropicProvider")
    @patch("pydantic_ai.models.anthropic.AnthropicModel")
    def test_build_model_strips_prefix(self, mock_model_cls, mock_provider_cls):
        provider = AnthropicProvider(api_key="sk-test")
        mock_model_cls.return_value = MagicMock()

        provider.build_model("anthropic:claude-sonnet-4-5")

        assert mock_model_cls.call_args[0][0] == "claude-sonnet-4-5"

    def test_from_config(self, tmp_path):
        config = _make_config(
            tmp_path, anthropic_api_key="sk-test", model_provider="anthropic"
        )
        provider = AnthropicProvider.from_config(config)
        assert provider._api_key == "sk-test"

    @patch("second_brain.models_sdk.create_sdk_model")
    def test_subscription_mode(self, mock_sdk, tmp_path):
        config = _make_config(
            tmp_path,
            anthropic_api_key="sk-test",
            model_provider="anthropic",
            use_subscription=True,
        )
        sdk_model = MagicMock()
        mock_sdk.return_value = sdk_model

        provider = AnthropicProvider.from_config(config)
        result = provider.build_model("claude-sonnet-4-5")

        assert result is sdk_model


class TestOllamaLocalProvider:
    """Tests for Ollama local provider."""

    def test_validate_config_valid(self):
        provider = OllamaLocalProvider(base_url="http://localhost:11434")
        assert provider.validate_config() is True

    def test_validate_config_missing_url(self):
        provider = OllamaLocalProvider(base_url="")
        with pytest.raises(ValueError, match="OLLAMA_BASE_URL"):
            provider.validate_config()

    @patch("pydantic_ai.providers.ollama.OllamaProvider")
    @patch("pydantic_ai.models.openai.OpenAIChatModel")
    def test_build_model(self, mock_openai_cls, mock_ollama_cls):
        provider = OllamaLocalProvider(base_url="http://localhost:11434")
        mock_openai_cls.return_value = MagicMock()

        model = provider.build_model("llama3.1:8b")

        mock_ollama_cls.assert_called_once_with(base_url="http://localhost:11434/v1")
        assert mock_openai_cls.call_args[0][0] == "llama3.1:8b"

    @patch("pydantic_ai.providers.ollama.OllamaProvider")
    @patch("pydantic_ai.models.openai.OpenAIChatModel")
    def test_build_model_uses_default(self, mock_openai_cls, mock_ollama_cls):
        """Empty model_name falls back to configured default."""
        provider = OllamaLocalProvider(model="mistral:7b")
        mock_openai_cls.return_value = MagicMock()

        provider.build_model("")

        assert mock_openai_cls.call_args[0][0] == "mistral:7b"

    def test_from_config(self, tmp_path):
        config = _make_config(
            tmp_path,
            model_provider="ollama-local",
            ollama_base_url="http://gpu:11434",
            ollama_model="codellama:7b",
        )
        provider = OllamaLocalProvider.from_config(config)
        assert provider._base_url == "http://gpu:11434"
        assert provider._model == "codellama:7b"


class TestOllamaCloudProvider:
    """Tests for Ollama cloud provider."""

    def test_validate_config_valid(self):
        provider = OllamaCloudProvider(
            base_url="https://cloud.ollama.ai", api_key="cloud-key"
        )
        assert provider.validate_config() is True

    def test_validate_config_missing_key(self):
        provider = OllamaCloudProvider(base_url="https://cloud.ollama.ai", api_key="")
        with pytest.raises(ValueError, match="OLLAMA_API_KEY"):
            provider.validate_config()

    def test_validate_config_missing_url(self):
        provider = OllamaCloudProvider(base_url="", api_key="cloud-key")
        with pytest.raises(ValueError, match="OLLAMA_BASE_URL"):
            provider.validate_config()

    @patch("pydantic_ai.providers.ollama.OllamaProvider")
    @patch("pydantic_ai.models.openai.OpenAIChatModel")
    def test_build_model(self, mock_openai_cls, mock_ollama_cls):
        provider = OllamaCloudProvider(
            base_url="https://cloud.ollama.ai", api_key="cloud-key"
        )
        mock_openai_cls.return_value = MagicMock()

        provider.build_model("llama3.1:70b")

        mock_ollama_cls.assert_called_once_with(
            base_url="https://cloud.ollama.ai/v1", api_key="cloud-key"
        )


class TestOpenAIProvider:
    """Tests for OpenAI provider."""

    def test_validate_config_valid(self):
        provider = OpenAIProvider(api_key="sk-openai-test")
        assert provider.validate_config() is True

    def test_validate_config_missing_key(self):
        provider = OpenAIProvider(api_key="")
        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            provider.validate_config()

    @patch("pydantic_ai.providers.openai.OpenAIProvider")
    @patch("pydantic_ai.models.openai.OpenAIChatModel")
    def test_build_model(self, mock_openai_cls, mock_openai_prov):
        provider = OpenAIProvider(api_key="sk-test")
        mock_openai_cls.return_value = MagicMock()

        provider.build_model("gpt-4o")

        mock_openai_cls.assert_called_once()
        assert mock_openai_cls.call_args[0][0] == "gpt-4o"
        mock_openai_prov.assert_called_once_with(api_key="sk-test")

    @patch("pydantic_ai.providers.openai.OpenAIProvider")
    @patch("pydantic_ai.models.openai.OpenAIChatModel")
    def test_build_model_uses_default(self, mock_openai_cls, mock_openai_prov):
        """Empty model_name falls back to configured default."""
        provider = OpenAIProvider(api_key="sk-test", model="gpt-4-turbo")
        mock_openai_cls.return_value = MagicMock()

        provider.build_model("")

        assert mock_openai_cls.call_args[0][0] == "gpt-4-turbo"

    def test_from_config(self, tmp_path):
        config = _make_config(
            tmp_path,
            model_provider="openai",
            openai_api_key="sk-test",
            openai_model_name="gpt-4-turbo",
        )
        provider = OpenAIProvider.from_config(config)
        assert provider._api_key == "sk-test"
        assert provider._model == "gpt-4-turbo"


class TestGroqProvider:
    """Tests for Groq provider."""

    def test_validate_config_valid(self):
        provider = GroqProvider(api_key="gsk-test")
        assert provider.validate_config() is True

    def test_validate_config_missing_key(self):
        provider = GroqProvider(api_key="")
        with pytest.raises(ValueError, match="GROQ_API_KEY"):
            provider.validate_config()

    @patch("pydantic_ai.providers.openai.OpenAIProvider")
    @patch("pydantic_ai.models.openai.OpenAIChatModel")
    def test_build_model(self, mock_openai_cls, mock_openai_prov):
        provider = GroqProvider(api_key="gsk-test")
        mock_openai_cls.return_value = MagicMock()

        provider.build_model("llama-3.3-70b-versatile")

        mock_openai_prov.assert_called_once_with(
            base_url="https://api.groq.com/openai/v1",
            api_key="gsk-test",
        )
        assert mock_openai_cls.call_args[0][0] == "llama-3.3-70b-versatile"

    def test_from_config(self, tmp_path):
        config = _make_config(
            tmp_path,
            model_provider="groq",
            groq_api_key="gsk-test",
            groq_model_name="mixtral-8x7b",
        )
        provider = GroqProvider.from_config(config)
        assert provider._api_key == "gsk-test"
        assert provider._model == "mixtral-8x7b"
