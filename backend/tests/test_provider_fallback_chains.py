"""Integration tests for provider fallback chain mechanism."""

import pytest
from unittest.mock import patch, MagicMock

from second_brain.config import BrainConfig
from second_brain.models import get_model


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


class TestFallbackChainIntegration:
    """Integration tests for multi-provider fallback chains."""

    @patch("pydantic_ai.providers.anthropic.AnthropicProvider")
    @patch("pydantic_ai.models.anthropic.AnthropicModel")
    def test_primary_succeeds_no_fallback(
        self, mock_model_cls, mock_prov_cls, tmp_path
    ):
        """Primary provider succeeds -- fallback never tried."""
        config = _make_config(
            tmp_path,
            anthropic_api_key="sk-test",
            model_provider="anthropic",
            model_fallback_chain="ollama-local,openai",
        )
        expected = MagicMock()
        mock_model_cls.return_value = expected

        result = get_model(config)

        assert result is expected

    @patch("pydantic_ai.providers.ollama.OllamaProvider")
    @patch("pydantic_ai.models.openai.OpenAIChatModel")
    @patch("pydantic_ai.providers.anthropic.AnthropicProvider")
    @patch("pydantic_ai.models.anthropic.AnthropicModel")
    def test_primary_fails_first_fallback_succeeds(
        self, mock_anthropic_cls, mock_anthropic_prov,
        mock_openai_cls, mock_ollama_prov, tmp_path
    ):
        """Primary fails, first fallback succeeds."""
        config = _make_config(
            tmp_path,
            anthropic_api_key="sk-test",
            model_provider="anthropic",
            model_fallback_chain="ollama-local",
        )
        mock_anthropic_cls.side_effect = Exception("API down")
        fallback = MagicMock()
        mock_openai_cls.return_value = fallback

        result = get_model(config)

        assert result is fallback

    @patch("pydantic_ai.providers.openai.OpenAIProvider")
    @patch("pydantic_ai.models.openai.OpenAIChatModel")
    @patch("pydantic_ai.providers.ollama.OllamaProvider")
    @patch("pydantic_ai.providers.anthropic.AnthropicProvider")
    @patch("pydantic_ai.models.anthropic.AnthropicModel")
    def test_primary_and_first_fallback_fail_second_succeeds(
        self, mock_anthropic_cls, mock_anthropic_prov,
        mock_ollama_prov, mock_openai_cls, mock_openai_prov, tmp_path
    ):
        """Primary + first fallback fail, second fallback succeeds."""
        config = _make_config(
            tmp_path,
            anthropic_api_key="sk-test",
            model_provider="anthropic",
            model_fallback_chain="ollama-local,openai",
            openai_api_key="sk-openai",
        )
        mock_anthropic_cls.side_effect = Exception("Anthropic down")
        mock_ollama_prov.side_effect = Exception("Ollama down")
        openai_model = MagicMock()
        mock_openai_cls.return_value = openai_model

        result = get_model(config)

        assert result is openai_model

    @patch("pydantic_ai.providers.openai.OpenAIProvider")
    @patch("pydantic_ai.providers.ollama.OllamaProvider")
    @patch("pydantic_ai.providers.anthropic.AnthropicProvider")
    @patch("pydantic_ai.models.anthropic.AnthropicModel")
    def test_all_providers_fail_runtime_error(
        self, mock_anthropic_cls, mock_anthropic_prov,
        mock_ollama_prov, mock_openai_prov, tmp_path
    ):
        """All providers (primary + all fallbacks) fail -- RuntimeError."""
        config = _make_config(
            tmp_path,
            anthropic_api_key="sk-test",
            model_provider="anthropic",
            model_fallback_chain="ollama-local,openai",
            openai_api_key="sk-openai",
        )
        mock_anthropic_cls.side_effect = Exception("Anthropic down")
        mock_ollama_prov.side_effect = Exception("Ollama down")
        mock_openai_prov.side_effect = Exception("OpenAI down")

        with pytest.raises(RuntimeError, match="No LLM available") as exc_info:
            get_model(config)

        # Error should list all providers tried
        msg = str(exc_info.value)
        assert "anthropic" in msg
        assert "ollama-local" in msg
        assert "openai" in msg

    def test_empty_fallback_chain_fail_fast(self, tmp_path):
        """No fallback = immediate failure on primary failure."""
        config = _make_config(
            tmp_path,
            model_provider="groq",
            groq_api_key="",
            model_fallback_chain="",
        )

        with pytest.raises(RuntimeError):
            get_model(config)

    def test_invalid_provider_in_fallback_chain(self, tmp_path):
        """Unknown provider in fallback chain raises ValueError within RuntimeError."""
        config = _make_config(
            tmp_path,
            model_provider="groq",
            groq_api_key="",
            model_fallback_chain="nonexistent-provider",
        )

        with pytest.raises(RuntimeError, match="No LLM available"):
            get_model(config)


class TestBackwardCompatibility:
    """Tests that old .env configs still work via auto-detection."""

    @patch("pydantic_ai.providers.anthropic.AnthropicProvider")
    @patch("pydantic_ai.models.anthropic.AnthropicModel")
    def test_old_env_with_anthropic_key(self, mock_model_cls, mock_prov_cls, tmp_path):
        """Old .env with ANTHROPIC_API_KEY works (no MODEL_PROVIDER set)."""
        config = _make_config(
            tmp_path,
            anthropic_api_key="sk-old-key",
            model_provider="auto",
        )
        mock_model_cls.return_value = MagicMock()

        result = get_model(config)

        assert result is not None
        assert config.model_provider == "anthropic"

    @patch("pydantic_ai.providers.ollama.OllamaProvider")
    @patch("pydantic_ai.models.openai.OpenAIChatModel")
    def test_old_env_with_ollama_only(self, mock_openai_cls, mock_ollama_cls, tmp_path):
        """Old .env with only Ollama config works."""
        config = _make_config(
            tmp_path,
            anthropic_api_key=None,
            model_provider="auto",
        )
        mock_openai_cls.return_value = MagicMock()

        result = get_model(config)

        assert result is not None
        assert config.model_provider == "ollama-local"

    @patch("pydantic_ai.providers.anthropic.AnthropicProvider")
    @patch("pydantic_ai.models.anthropic.AnthropicModel")
    def test_old_primary_model_field_used(self, mock_model_cls, mock_prov_cls, tmp_path):
        """Old primary_model field derives model_name when not explicitly set."""
        config = _make_config(
            tmp_path,
            anthropic_api_key="sk-test",
            model_provider="auto",
            primary_model="anthropic:claude-opus-4",
        )
        mock_model_cls.return_value = MagicMock()

        get_model(config)

        assert mock_model_cls.call_args[0][0] == "claude-opus-4"

    @patch("pydantic_ai.providers.ollama.OllamaProvider")
    @patch("pydantic_ai.models.openai.OpenAIChatModel")
    def test_old_ollama_model_field_used(self, mock_openai_cls, mock_ollama_cls, tmp_path):
        """Old ollama_model field used when provider is ollama."""
        config = _make_config(
            tmp_path,
            model_provider="ollama-local",
            ollama_model="codellama:13b",
        )
        mock_openai_cls.return_value = MagicMock()

        get_model(config)

        assert mock_openai_cls.call_args[0][0] == "codellama:13b"
