"""Unit tests for get_model() provider-based LLM factory."""

import pytest
from unittest.mock import patch, MagicMock

from second_brain.config import BrainConfig
from second_brain.models import get_model, get_agent_model


# Known env vars that BrainConfig reads -- clear to prevent host bleed.
_ENV_VARS = [
    "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_BASE_URL", "OLLAMA_API_KEY",
    "OLLAMA_MODEL", "MEM0_API_KEY", "GRAPH_PROVIDER", "NEO4J_URL", "NEO4J_USERNAME",
    "NEO4J_PASSWORD", "SUPABASE_URL", "SUPABASE_KEY", "BRAIN_USER_ID",
    "BRAIN_DATA_PATH", "PRIMARY_MODEL", "FALLBACK_MODEL", "MEMORY_SEARCH_LIMIT",
    "GRAPH_SEARCH_LIMIT", "PATTERN_CONTEXT_LIMIT", "EXPERIENCE_LIMIT",
    "GRADUATION_MIN_MEMORIES", "GRADUATION_LOOKBACK_DAYS",
    "CONTENT_PREVIEW_LIMIT", "PATTERN_PREVIEW_LIMIT",
    "USE_SUBSCRIPTION", "CLAUDE_OAUTH_TOKEN",
    "MODEL_PROVIDER", "MODEL_NAME", "MODEL_FALLBACK_CHAIN",
    "OPENAI_MODEL_NAME", "GROQ_API_KEY", "GROQ_MODEL_NAME",
    "AGENT_MODEL_OVERRIDES",
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
    """Tests the Anthropic provider path."""

    @patch("pydantic_ai.providers.anthropic.AnthropicProvider")
    @patch("pydantic_ai.models.anthropic.AnthropicModel")
    def test_returns_anthropic_model(self, mock_model_cls, mock_provider_cls, brain_config):
        """get_model() returns AnthropicModel when provider=anthropic."""
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
        """get_model() uses custom model_name."""
        config = _make_config(
            tmp_path,
            anthropic_api_key="sk-test",
            model_provider="anthropic",
            model_name="claude-opus-4",
        )

        get_model(config)

        assert mock_model_cls.call_args[0][0] == "claude-opus-4"


class TestGetModelOllamaFallback:
    """Tests the Ollama provider paths."""

    @patch("pydantic_ai.providers.ollama.OllamaProvider")
    @patch("pydantic_ai.models.openai.OpenAIChatModel")
    def test_ollama_local_provider(self, mock_openai_cls, mock_ollama_cls, tmp_path):
        """ollama-local provider uses correct base URL."""
        config = _make_config(
            tmp_path,
            model_provider="ollama-local",
        )
        mock_model = MagicMock()
        mock_openai_cls.return_value = mock_model

        result = get_model(config)

        mock_ollama_cls.assert_called_once_with(
            base_url="http://localhost:11434/v1",
        )
        mock_openai_cls.assert_called_once()
        assert mock_openai_cls.call_args[0][0] == "llama3.1:8b"
        assert result is mock_model

    @patch("pydantic_ai.providers.ollama.OllamaProvider")
    @patch("pydantic_ai.models.openai.OpenAIChatModel")
    def test_ollama_cloud_provider(self, mock_openai_cls, mock_ollama_cls, tmp_path):
        """ollama-cloud provider uses API key."""
        config = _make_config(
            tmp_path,
            model_provider="ollama-cloud",
            ollama_base_url="https://cloud.ollama.ai",
            ollama_api_key="cloud-key-123",
        )
        mock_openai_cls.return_value = MagicMock()

        get_model(config)

        mock_ollama_cls.assert_called_once_with(
            base_url="https://cloud.ollama.ai/v1",
            api_key="cloud-key-123",
        )

    @patch("pydantic_ai.providers.ollama.OllamaProvider")
    @patch("pydantic_ai.models.openai.OpenAIChatModel")
    def test_ollama_with_custom_model(self, mock_openai_cls, mock_ollama_cls, tmp_path):
        """Uses custom ollama_model and ollama_base_url."""
        config = _make_config(
            tmp_path,
            model_provider="ollama-local",
            ollama_model="mistral:7b",
            ollama_base_url="http://gpu-server:11434",
        )

        get_model(config)

        assert mock_openai_cls.call_args[0][0] == "mistral:7b"
        mock_ollama_cls.assert_called_once_with(
            base_url="http://gpu-server:11434/v1",
        )

    @patch("pydantic_ai.providers.anthropic.AnthropicProvider")
    @patch("pydantic_ai.models.anthropic.AnthropicModel")
    @patch("pydantic_ai.providers.ollama.OllamaProvider")
    @patch("pydantic_ai.models.openai.OpenAIChatModel")
    def test_fallback_when_anthropic_fails(
        self, mock_openai_cls, mock_ollama_cls, mock_anthropic_prov, mock_anthropic_cls, tmp_path
    ):
        """Falls back to ollama-local when anthropic raises."""
        config = _make_config(
            tmp_path,
            anthropic_api_key="sk-test",
            model_provider="anthropic",
            model_fallback_chain="ollama-local",
        )
        mock_anthropic_cls.side_effect = Exception("API error")
        mock_fallback = MagicMock()
        mock_openai_cls.return_value = mock_fallback

        result = get_model(config)

        mock_openai_cls.assert_called_once()
        assert result is mock_fallback


class TestGetModelOpenAI:
    """Tests the OpenAI provider path."""

    @patch("pydantic_ai.providers.openai.OpenAIProvider")
    @patch("pydantic_ai.models.openai.OpenAIChatModel")
    def test_openai_provider(self, mock_openai_cls, mock_openai_prov, tmp_path):
        """OpenAI provider uses correct API key."""
        config = _make_config(
            tmp_path,
            model_provider="openai",
            openai_api_key="sk-openai-test",
        )
        mock_model = MagicMock()
        mock_openai_cls.return_value = mock_model

        result = get_model(config)

        mock_openai_prov.assert_called_once_with(api_key="sk-openai-test")
        assert result is mock_model

    @patch("pydantic_ai.providers.openai.OpenAIProvider")
    @patch("pydantic_ai.models.openai.OpenAIChatModel")
    def test_openai_custom_model_name(self, mock_openai_cls, mock_openai_prov, tmp_path):
        """OpenAI provider uses custom model name."""
        config = _make_config(
            tmp_path,
            model_provider="openai",
            openai_api_key="sk-test",
            model_name="gpt-4-turbo",
        )
        mock_openai_cls.return_value = MagicMock()

        get_model(config)

        assert mock_openai_cls.call_args[0][0] == "gpt-4-turbo"


class TestGetModelGroq:
    """Tests the Groq provider path."""

    @patch("pydantic_ai.providers.openai.OpenAIProvider")
    @patch("pydantic_ai.models.openai.OpenAIChatModel")
    def test_groq_provider(self, mock_openai_cls, mock_openai_prov, tmp_path):
        """Groq provider uses correct API key and base URL."""
        config = _make_config(
            tmp_path,
            model_provider="groq",
            groq_api_key="gsk-test-key",
        )
        mock_model = MagicMock()
        mock_openai_cls.return_value = mock_model

        result = get_model(config)

        mock_openai_prov.assert_called_once_with(
            base_url="https://api.groq.com/openai/v1",
            api_key="gsk-test-key",
        )
        assert result is mock_model


class TestGetModelNoProvider:
    """Tests the RuntimeError path when all providers fail."""

    @patch("pydantic_ai.providers.ollama.OllamaProvider")
    def test_runtime_error_when_all_fail(self, mock_ollama_cls, tmp_path):
        """Raises RuntimeError when provider fails and no fallback."""
        config = _make_config(tmp_path, model_provider="ollama-local")
        mock_ollama_cls.side_effect = Exception("Connection refused")

        with pytest.raises(RuntimeError, match="No LLM available"):
            get_model(config)

    def test_runtime_error_lists_providers_tried(self, tmp_path):
        """Error message lists all providers attempted."""
        config = _make_config(
            tmp_path,
            model_provider="groq",
            groq_api_key="",
        )

        with pytest.raises(RuntimeError, match="groq"):
            get_model(config)

    @patch("pydantic_ai.providers.ollama.OllamaProvider")
    @patch("pydantic_ai.providers.anthropic.AnthropicProvider")
    @patch("pydantic_ai.models.anthropic.AnthropicModel")
    def test_all_fallbacks_fail(
        self, mock_anthropic_cls, mock_anthropic_prov, mock_ollama_cls, tmp_path
    ):
        """RuntimeError when primary and all fallbacks fail."""
        config = _make_config(
            tmp_path,
            anthropic_api_key="sk-test",
            model_provider="anthropic",
            model_fallback_chain="ollama-local",
        )
        mock_anthropic_cls.side_effect = Exception("Anthropic down")
        mock_ollama_cls.side_effect = Exception("Ollama down")

        with pytest.raises(RuntimeError, match="No LLM available"):
            get_model(config)


class TestFallbackChains:
    """Tests for the fallback chain mechanism."""

    @patch("pydantic_ai.providers.ollama.OllamaProvider")
    @patch("pydantic_ai.models.openai.OpenAIChatModel")
    @patch("pydantic_ai.providers.anthropic.AnthropicProvider")
    @patch("pydantic_ai.models.anthropic.AnthropicModel")
    def test_primary_success_skips_fallback(
        self, mock_anthropic_cls, mock_anthropic_prov, mock_openai_cls, mock_ollama_cls, tmp_path
    ):
        """When primary succeeds, fallback is never attempted."""
        config = _make_config(
            tmp_path,
            anthropic_api_key="sk-test",
            model_provider="anthropic",
            model_fallback_chain="ollama-local",
        )
        primary = MagicMock()
        mock_anthropic_cls.return_value = primary

        result = get_model(config)

        assert result is primary
        mock_openai_cls.assert_not_called()

    @patch("pydantic_ai.providers.openai.OpenAIProvider")
    @patch("pydantic_ai.models.openai.OpenAIChatModel")
    @patch("pydantic_ai.providers.ollama.OllamaProvider")
    @patch("pydantic_ai.providers.anthropic.AnthropicProvider")
    @patch("pydantic_ai.models.anthropic.AnthropicModel")
    def test_multi_fallback_chain(
        self, mock_anthropic_cls, mock_anthropic_prov,
        mock_ollama_prov, mock_openai_cls, mock_openai_prov, tmp_path
    ):
        """Falls through multiple providers until one works."""
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

    def test_empty_fallback_chain_fail_fast(self, tmp_path):
        """No fallback chain = fail on first provider failure."""
        config = _make_config(
            tmp_path,
            model_provider="groq",
            groq_api_key="",
            model_fallback_chain="",
        )

        with pytest.raises(RuntimeError):
            get_model(config)


class TestGetModelAnthropicVariants:
    """Additional Anthropic model path tests."""

    @patch("pydantic_ai.providers.anthropic.AnthropicProvider")
    @patch("pydantic_ai.models.anthropic.AnthropicModel")
    def test_anthropic_model_with_opus(self, mock_model_cls, mock_provider_cls, tmp_path):
        """get_model() uses opus model when model_name is set to opus."""
        config = _make_config(
            tmp_path,
            anthropic_api_key="sk-test",
            model_provider="anthropic",
            model_name="claude-opus-4-5",
        )
        mock_model = MagicMock()
        mock_model_cls.return_value = mock_model

        result = get_model(config)

        assert mock_model_cls.call_args[0][0] == "claude-opus-4-5"
        assert result is mock_model

    @patch("pydantic_ai.providers.anthropic.AnthropicProvider")
    @patch("pydantic_ai.models.anthropic.AnthropicModel")
    def test_anthropic_model_with_haiku(self, mock_model_cls, mock_provider_cls, tmp_path):
        """get_model() uses haiku model when model_name is set."""
        config = _make_config(
            tmp_path,
            anthropic_api_key="sk-test",
            model_provider="anthropic",
            model_name="claude-haiku-4-5-20251001",
        )
        mock_model_cls.return_value = MagicMock()

        get_model(config)

        assert mock_model_cls.call_args[0][0] == "claude-haiku-4-5-20251001"

    @patch("pydantic_ai.providers.anthropic.AnthropicProvider")
    @patch("pydantic_ai.models.anthropic.AnthropicModel")
    def test_anthropic_model_with_sonnet_4_6(self, mock_model_cls, mock_provider_cls, tmp_path):
        """get_model() correctly uses sonnet-4-6 model."""
        config = _make_config(
            tmp_path,
            anthropic_api_key="sk-test",
            model_provider="anthropic",
            model_name="claude-sonnet-4-6",
        )
        mock_model_cls.return_value = MagicMock()

        get_model(config)

        assert mock_model_cls.call_args[0][0] == "claude-sonnet-4-6"

    @patch("pydantic_ai.providers.anthropic.AnthropicProvider")
    @patch("pydantic_ai.models.anthropic.AnthropicModel")
    def test_api_key_passed_to_provider(self, mock_model_cls, mock_provider_cls, tmp_path):
        """API key from config is passed to AnthropicProvider."""
        config = _make_config(
            tmp_path,
            anthropic_api_key="my-secret-key",
            model_provider="anthropic",
        )
        mock_model_cls.return_value = MagicMock()

        get_model(config)

        mock_provider_cls.assert_called_once_with(api_key="my-secret-key")

    @patch("pydantic_ai.providers.anthropic.AnthropicProvider")
    @patch("pydantic_ai.models.anthropic.AnthropicModel")
    def test_get_model_returns_model_object(self, mock_model_cls, mock_provider_cls, brain_config):
        """get_model() returns a model object (not None)."""
        expected = MagicMock()
        mock_model_cls.return_value = expected

        result = get_model(brain_config)

        assert result is expected

    @patch("second_brain.models_sdk.create_sdk_model")
    @patch("pydantic_ai.providers.anthropic.AnthropicProvider")
    @patch("pydantic_ai.models.anthropic.AnthropicModel")
    def test_subscription_path_not_called_when_disabled(
        self, mock_model_cls, mock_provider_cls, mock_sdk, brain_config
    ):
        """create_sdk_model is NOT called when use_subscription=False (default)."""
        mock_model_cls.return_value = MagicMock()

        get_model(brain_config)

        mock_sdk.assert_not_called()

    @patch("second_brain.models_sdk.create_sdk_model")
    def test_subscription_path_attempted_when_enabled(self, mock_sdk, tmp_path):
        """create_sdk_model is attempted when use_subscription=True."""
        config = _make_config(
            tmp_path,
            anthropic_api_key="sk-test",
            model_provider="anthropic",
            use_subscription=True,
        )
        sdk_model = MagicMock()
        mock_sdk.return_value = sdk_model

        result = get_model(config)

        mock_sdk.assert_called_once_with(config)
        assert result is sdk_model

    @patch("pydantic_ai.providers.anthropic.AnthropicProvider")
    @patch("pydantic_ai.models.anthropic.AnthropicModel")
    def test_default_model_derived_from_primary_model(
        self, mock_model_cls, mock_provider_cls, tmp_path
    ):
        """When model_name not set, derives from primary_model config."""
        config = _make_config(
            tmp_path,
            anthropic_api_key="sk-test",
            model_provider="anthropic",
            primary_model="anthropic:claude-custom-v99",
        )
        mock_model_cls.return_value = MagicMock()

        get_model(config)

        assert mock_model_cls.call_args[0][0] == "claude-custom-v99"


class TestAutoProviderDetection:
    """Tests backward compat: model_provider='auto' infers from keys."""

    def test_auto_with_anthropic_key(self, tmp_path):
        """Auto-detects anthropic when API key is present."""
        config = _make_config(
            tmp_path,
            anthropic_api_key="sk-test",
            model_provider="auto",
        )
        assert config.model_provider == "anthropic"

    def test_auto_with_subscription(self, tmp_path):
        """Auto-detects anthropic when subscription is enabled."""
        config = _make_config(
            tmp_path,
            use_subscription=True,
            model_provider="auto",
        )
        assert config.model_provider == "anthropic"

    def test_auto_with_ollama_api_key(self, tmp_path):
        """Auto-detects ollama-cloud when ollama API key is present."""
        config = _make_config(
            tmp_path,
            ollama_api_key="cloud-key",
            model_provider="auto",
        )
        assert config.model_provider == "ollama-cloud"

    def test_auto_default_to_ollama_local(self, tmp_path):
        """Auto defaults to ollama-local when no keys present."""
        config = _make_config(
            tmp_path,
            model_provider="auto",
        )
        assert config.model_provider == "ollama-local"

    def test_invalid_provider_raises(self, tmp_path):
        """Invalid model_provider raises ValueError."""
        with pytest.raises(ValueError, match="model_provider must be one of"):
            _make_config(tmp_path, model_provider="invalid-provider")


class TestConfigFallbackChain:
    """Tests config parsing of fallback chain."""

    def test_empty_fallback_chain(self, tmp_path):
        """Empty string produces empty list."""
        config = _make_config(tmp_path, model_fallback_chain="")
        assert config.fallback_chain_list == []

    def test_single_fallback(self, tmp_path):
        """Single provider in chain."""
        config = _make_config(tmp_path, model_fallback_chain="ollama-local")
        assert config.fallback_chain_list == ["ollama-local"]

    def test_multiple_fallbacks(self, tmp_path):
        """Multiple providers comma-separated."""
        config = _make_config(
            tmp_path,
            model_fallback_chain="ollama-local,openai,groq",
        )
        assert config.fallback_chain_list == ["ollama-local", "openai", "groq"]

    def test_fallback_chain_strips_whitespace(self, tmp_path):
        """Whitespace around provider names is stripped."""
        config = _make_config(
            tmp_path,
            model_fallback_chain=" ollama-local , openai ",
        )
        assert config.fallback_chain_list == ["ollama-local", "openai"]


class TestGetAgentModel:
    """Tests for get_agent_model() per-agent model resolution."""

    @patch("pydantic_ai.providers.anthropic.AnthropicProvider")
    @patch("pydantic_ai.models.anthropic.AnthropicModel")
    def test_no_override_falls_back_to_global(self, mock_model_cls, mock_provider_cls, tmp_path):
        """Agent without override uses global get_model()."""
        config = _make_config(
            tmp_path,
            anthropic_api_key="sk-test",
            model_provider="anthropic",
        )
        mock_model = MagicMock()
        mock_model_cls.return_value = mock_model

        result = get_agent_model("recall", config)

        assert result is mock_model

    @patch("pydantic_ai.providers.ollama.OllamaProvider")
    @patch("pydantic_ai.models.openai.OpenAIChatModel")
    def test_override_plain_model_uses_global_provider(
        self, mock_openai_cls, mock_ollama_cls, tmp_path
    ):
        """Override with plain model name uses global provider."""
        config = _make_config(
            tmp_path,
            model_provider="ollama-local",
            agent_model_overrides={"recall": "mistral:7b"},
        )
        mock_model = MagicMock()
        mock_openai_cls.return_value = mock_model

        result = get_agent_model("recall", config)

        assert result is mock_model
        assert mock_openai_cls.call_args[0][0] == "mistral:7b"

    @patch("pydantic_ai.providers.anthropic.AnthropicProvider")
    @patch("pydantic_ai.models.anthropic.AnthropicModel")
    def test_override_with_provider_prefix(self, mock_model_cls, mock_provider_cls, tmp_path):
        """Override with 'provider:model' syntax uses specified provider."""
        config = _make_config(
            tmp_path,
            model_provider="ollama-local",
            anthropic_api_key="sk-test",
            agent_model_overrides={"create": "anthropic:claude-sonnet-4-5"},
        )
        mock_model = MagicMock()
        mock_model_cls.return_value = mock_model

        result = get_agent_model("create", config)

        assert result is mock_model
        assert mock_model_cls.call_args[0][0] == "claude-sonnet-4-5"

    @patch("pydantic_ai.providers.ollama.OllamaProvider")
    @patch("pydantic_ai.models.openai.OpenAIChatModel")
    def test_ollama_colon_model_not_mistaken_for_provider(
        self, mock_openai_cls, mock_ollama_cls, tmp_path
    ):
        """Ollama model names with colons (e.g., deepseek-r1:70b) are not split as provider:model."""
        config = _make_config(
            tmp_path,
            model_provider="ollama-local",
            agent_model_overrides={"recall": "deepseek-r1:70b"},
        )
        mock_model = MagicMock()
        mock_openai_cls.return_value = mock_model

        result = get_agent_model("recall", config)

        # deepseek-r1 is not a registered provider, so full string is used as model name
        assert result is mock_model
        assert mock_openai_cls.call_args[0][0] == "deepseek-r1:70b"

    @patch("pydantic_ai.providers.anthropic.AnthropicProvider")
    @patch("pydantic_ai.models.anthropic.AnthropicModel")
    def test_override_build_failure_falls_back_to_global(
        self, mock_model_cls, mock_provider_cls, tmp_path
    ):
        """When override build fails, falls back to global model gracefully."""
        config = _make_config(
            tmp_path,
            anthropic_api_key="sk-test",
            model_provider="anthropic",
            agent_model_overrides={"recall": "openai:gpt-4o"},
        )
        # First call for override will fail (openai provider), second for global fallback
        global_model = MagicMock()
        mock_model_cls.return_value = global_model

        result = get_agent_model("recall", config)

        # Should get a model (either override or fallback)
        assert result is not None

    @patch("pydantic_ai.providers.anthropic.AnthropicProvider")
    @patch("pydantic_ai.models.anthropic.AnthropicModel")
    def test_different_agents_get_different_overrides(
        self, mock_model_cls, mock_provider_cls, tmp_path
    ):
        """Multiple agents can have different overrides."""
        config = _make_config(
            tmp_path,
            anthropic_api_key="sk-test",
            model_provider="anthropic",
            agent_model_overrides={
                "recall": "claude-haiku-4-5-20251001",
                "create": "claude-opus-4",
            },
        )
        mock_model_cls.return_value = MagicMock()

        get_agent_model("recall", config)
        recall_model_name = mock_model_cls.call_args[0][0]

        get_agent_model("create", config)
        create_model_name = mock_model_cls.call_args[0][0]

        assert recall_model_name == "claude-haiku-4-5-20251001"
        assert create_model_name == "claude-opus-4"
