"""Unit tests for BrainConfig field defaults, required fields, and env loading."""

import pytest
from pathlib import Path
from pydantic import ValidationError

from second_brain.config import BrainConfig


# Known env vars that BrainConfig reads via BaseSettings.
# Tests that check default values must clear these to avoid host bleed.
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


class TestBrainConfigDefaults:
    """Tests that BrainConfig fields have correct default values."""

    def test_default_values(self, tmp_path):
        """All optional fields use their documented defaults."""
        config = BrainConfig(
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
            brain_data_path=tmp_path,
            _env_file=None,
        )
        assert config.anthropic_api_key is None
        assert config.openai_api_key is None
        assert config.ollama_base_url == "http://localhost:11434"
        assert config.ollama_model == "llama3.1:8b"
        assert config.mem0_api_key is None
        assert config.graph_provider == "none"
        assert config.brain_user_id == "ryan"
        assert config.primary_model == "anthropic:claude-sonnet-4-5"
        assert config.fallback_model == "ollama:llama3.1:8b"
        assert config.memory_search_limit == 10
        assert config.graph_search_limit == 5
        assert config.pattern_context_limit == 30
        assert config.experience_limit == 5
        assert config.graduation_min_memories == 3
        assert config.graduation_lookback_days == 30
        assert config.content_preview_limit == 1000
        assert config.pattern_preview_limit == 200

    def test_custom_values(self, tmp_path):
        """All fields accept and store custom values."""
        config = BrainConfig(
            anthropic_api_key="sk-test",
            openai_api_key="sk-oai",
            ollama_base_url="http://gpu:11434",
            ollama_api_key="ollama-key",
            ollama_model="mistral:7b",
            mem0_api_key="mem0-key",
            graph_provider="graphiti",
            neo4j_url="neo4j+s://test",
            neo4j_username="neo4j",
            neo4j_password="pass",
            supabase_url="https://custom.supabase.co",
            supabase_key="custom-key",
            brain_user_id="alice",
            brain_data_path=tmp_path,
            primary_model="anthropic:claude-opus-4",
            fallback_model="ollama:mistral:7b",
            memory_search_limit=20,
            graph_search_limit=10,
            pattern_context_limit=50,
            experience_limit=10,
            graduation_min_memories=5,
            graduation_lookback_days=60,
            content_preview_limit=2000,
            pattern_preview_limit=500,
            _env_file=None,
        )
        assert config.anthropic_api_key == "sk-test"
        assert config.ollama_base_url == "http://gpu:11434"
        assert config.ollama_api_key == "ollama-key"
        assert config.mem0_api_key == "mem0-key"
        assert config.graph_provider == "graphiti"
        assert config.neo4j_url == "neo4j+s://test"
        assert config.brain_user_id == "alice"
        assert config.primary_model == "anthropic:claude-opus-4"
        assert config.memory_search_limit == 20
        assert config.graduation_min_memories == 5
        assert config.content_preview_limit == 2000

    def test_brain_data_path_is_pathlib_path(self, tmp_path):
        """Pydantic coerces string brain_data_path to Path."""
        config = BrainConfig(
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
            brain_data_path=str(tmp_path),
            _env_file=None,
        )
        assert isinstance(config.brain_data_path, Path)


class TestBrainConfigRequired:
    """Tests that required fields raise ValidationError when missing."""

    def test_missing_supabase_url(self, tmp_path):
        with pytest.raises(ValidationError):
            BrainConfig(
                supabase_key="test-key",
                brain_data_path=tmp_path,
                _env_file=None,
            )

    def test_missing_supabase_key(self, tmp_path):
        with pytest.raises(ValidationError):
            BrainConfig(
                supabase_url="https://test.supabase.co",
                brain_data_path=tmp_path,
                _env_file=None,
            )

    def test_missing_brain_data_path(self):
        with pytest.raises(ValidationError):
            BrainConfig(
                supabase_url="https://test.supabase.co",
                supabase_key="test-key",
                _env_file=None,
            )


class TestBrainConfigEnv:
    """Tests that environment variables are loaded via Pydantic Settings."""

    def test_env_override(self, tmp_path, monkeypatch):
        """BrainConfig reads values from environment variables."""
        monkeypatch.setenv("SUPABASE_URL", "https://env.supabase.co")
        monkeypatch.setenv("SUPABASE_KEY", "env-key")
        monkeypatch.setenv("BRAIN_DATA_PATH", str(tmp_path))
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-from-env")

        config = BrainConfig(_env_file=None)

        assert config.supabase_url == "https://env.supabase.co"
        assert config.supabase_key == "env-key"
        assert config.anthropic_api_key == "sk-from-env"

    def test_env_partial_override(self, tmp_path, monkeypatch):
        """Env vars override specific fields while others keep defaults."""
        monkeypatch.setenv("SUPABASE_URL", "https://env.supabase.co")
        monkeypatch.setenv("SUPABASE_KEY", "env-key")
        monkeypatch.setenv("BRAIN_DATA_PATH", str(tmp_path))
        monkeypatch.setenv("MEMORY_SEARCH_LIMIT", "25")

        config = BrainConfig(_env_file=None)

        assert config.memory_search_limit == 25
        assert config.graph_search_limit == 5  # default unchanged


class TestBrainConfigGraphProvider:
    """Tests graph provider configuration options."""

    def test_graph_none(self, tmp_path):
        config = BrainConfig(
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
            brain_data_path=tmp_path,
            graph_provider="none",
            _env_file=None,
        )
        assert config.graph_provider == "none"
        assert config.neo4j_url is None
        assert config.neo4j_username is None
        assert config.neo4j_password is None

    def test_graph_mem0(self, tmp_path):
        config = BrainConfig(
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
            brain_data_path=tmp_path,
            graph_provider="mem0",
            neo4j_url="neo4j+s://test",
            neo4j_username="neo4j",
            neo4j_password="pass",
            _env_file=None,
        )
        assert config.graph_provider == "mem0"
        assert config.neo4j_url == "neo4j+s://test"
        assert config.neo4j_username == "neo4j"
        assert config.neo4j_password == "pass"

    def test_graph_graphiti(self, tmp_path):
        config = BrainConfig(
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
            brain_data_path=tmp_path,
            graph_provider="graphiti",
            _env_file=None,
        )
        assert config.graph_provider == "graphiti"
