"""Unit tests for BrainConfig field defaults, required fields, and env loading."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
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
    "GRAPHITI_ENABLED", "FALKORDB_URL", "FALKORDB_PASSWORD",
    "USE_SUBSCRIPTION", "CLAUDE_OAUTH_TOKEN",
    "MEMORY_PROVIDER",
    "MCP_TRANSPORT", "MCP_HOST", "MCP_PORT",
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
        assert config.mcp_transport == "stdio"
        assert config.mcp_host == "0.0.0.0"
        assert config.mcp_port == 8000

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
            mcp_transport="http",
            mcp_host="127.0.0.1",
            mcp_port=9000,
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
        assert config.mcp_transport == "http"
        assert config.mcp_host == "127.0.0.1"
        assert config.mcp_port == 9000

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
            neo4j_url="neo4j+s://test.databases.neo4j.io",
            neo4j_username="neo4j",
            neo4j_password="test-password",
            _env_file=None,
        )
        assert config.graph_provider == "graphiti"


class TestGraphProviderValidation:
    """Test graph_provider cross-field validation."""

    def test_graphiti_requires_neo4j_url(self, tmp_path):
        with pytest.raises(ValidationError, match="NEO4J_URL"):
            BrainConfig(
                graph_provider="graphiti",
                neo4j_url=None,
                neo4j_username="neo4j",
                neo4j_password="pass",
                supabase_url="https://test.supabase.co",
                supabase_key="test-key",
                brain_data_path=tmp_path,
                _env_file=None,
            )

    def test_graphiti_requires_neo4j_username(self, tmp_path):
        with pytest.raises(ValidationError, match="NEO4J_USERNAME"):
            BrainConfig(
                graph_provider="graphiti",
                neo4j_url="neo4j://localhost:7687",
                neo4j_username=None,
                neo4j_password="pass",
                supabase_url="https://test.supabase.co",
                supabase_key="test-key",
                brain_data_path=tmp_path,
                _env_file=None,
            )

    def test_graphiti_requires_neo4j_password(self, tmp_path):
        with pytest.raises(ValidationError, match="NEO4J_PASSWORD"):
            BrainConfig(
                graph_provider="graphiti",
                neo4j_url="neo4j://localhost:7687",
                neo4j_username="neo4j",
                neo4j_password=None,
                supabase_url="https://test.supabase.co",
                supabase_key="test-key",
                brain_data_path=tmp_path,
                _env_file=None,
            )

    def test_graphiti_valid_config_accepted(self, tmp_path):
        config = BrainConfig(
            graph_provider="graphiti",
            neo4j_url="neo4j://localhost:7687",
            neo4j_username="neo4j",
            neo4j_password="test",
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
            brain_data_path=tmp_path,
            _env_file=None,
        )
        assert config.graph_provider == "graphiti"

    def test_non_graphiti_skips_validation(self, tmp_path):
        config = BrainConfig(
            graph_provider="none",
            neo4j_url=None,
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
            brain_data_path=tmp_path,
            _env_file=None,
        )
        assert config.graph_provider == "none"

    def test_sensitive_fields_hidden_in_repr(self, tmp_path):
        config = BrainConfig(
            anthropic_api_key="SECRET_KEY",
            supabase_url="https://test.supabase.co",
            supabase_key="SECRET_SUPABASE",
            brain_data_path=tmp_path,
            _env_file=None,
        )
        r = repr(config)
        assert "SECRET_KEY" not in r
        assert "SECRET_SUPABASE" not in r


class TestCreateDeps:
    """Test shared create_deps factory."""

    @patch("second_brain.services.storage.StorageService")
    @patch("second_brain.services.memory.MemoryService")
    def test_create_deps_with_config(self, mock_mem, mock_storage, tmp_path):
        config = BrainConfig(
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
            brain_data_path=tmp_path,
            _env_file=None,
        )
        from second_brain.deps import create_deps
        deps = create_deps(config=config)
        assert deps.config is config
        assert deps.graphiti_service is None  # graph_provider="none"
        mock_mem.assert_called_once_with(config)
        mock_storage.assert_called_once_with(config)

    @patch("second_brain.services.storage.StorageService")
    @patch("second_brain.services.memory.MemoryService")
    def test_create_deps_graphiti_enabled(self, mock_mem, mock_storage, tmp_path):
        config = BrainConfig(
            graph_provider="graphiti",
            neo4j_url="neo4j://localhost",
            neo4j_username="neo4j",
            neo4j_password="test",
            supabase_url="https://test.supabase.co",
            supabase_key="test",
            brain_data_path=tmp_path,
            _env_file=None,
        )
        with patch("second_brain.services.graphiti.GraphitiService") as mock_graphiti:
            mock_graphiti.return_value = MagicMock()
            from second_brain.deps import create_deps
            deps = create_deps(config=config)
            assert deps.graphiti_service is not None
            mock_graphiti.assert_called_once_with(config)

    @patch("second_brain.services.storage.StorageService")
    @patch("second_brain.services.memory.MemoryService")
    def test_create_deps_graphiti_import_error(self, mock_mem, mock_storage, tmp_path):
        config = BrainConfig(
            graph_provider="graphiti",
            neo4j_url="neo4j://localhost",
            neo4j_username="neo4j",
            neo4j_password="test",
            supabase_url="https://test.supabase.co",
            supabase_key="test",
            brain_data_path=tmp_path,
            _env_file=None,
        )
        with patch("second_brain.services.graphiti.GraphitiService", side_effect=ImportError):
            from second_brain.deps import create_deps
            deps = create_deps(config=config)
            assert deps.graphiti_service is None  # Graceful degradation


    @patch("second_brain.services.storage.StorageService")
    @patch("second_brain.services.memory.MemoryService")
    def test_create_deps_graphiti_enabled_flag(self, mock_mem, mock_storage, tmp_path):
        """create_deps with graphiti_enabled=True (independent of graph_provider)."""
        config = BrainConfig(
            graphiti_enabled=True,
            falkordb_url="falkor://localhost:6379",
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
            brain_data_path=tmp_path,
            _env_file=None,
        )
        with patch("second_brain.services.graphiti.GraphitiService") as mock_graphiti:
            mock_graphiti.return_value = MagicMock()
            from second_brain.deps import create_deps
            deps = create_deps(config=config)
            assert deps.graphiti_service is not None
            mock_graphiti.assert_called_once_with(config)

    @patch("second_brain.services.storage.StorageService")
    @patch("second_brain.services.memory.MemoryService")
    def test_create_deps_graphiti_enabled_import_error(self, mock_mem, mock_storage, tmp_path):
        """create_deps gracefully handles missing graphiti when enabled."""
        config = BrainConfig(
            graphiti_enabled=True,
            falkordb_url="falkor://localhost:6379",
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
            brain_data_path=tmp_path,
            _env_file=None,
        )
        with patch("second_brain.services.graphiti.GraphitiService", side_effect=ImportError):
            from second_brain.deps import create_deps
            deps = create_deps(config=config)
            assert deps.graphiti_service is None

    @patch("second_brain.services.storage.StorageService")
    @patch("second_brain.services.memory.MemoryService")
    def test_create_deps_default_config(self, mock_mem, mock_storage, tmp_path, monkeypatch):
        """create_deps() with no config arg creates BrainConfig from env."""
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_KEY", "test-key")
        monkeypatch.setenv("BRAIN_DATA_PATH", str(tmp_path))
        with patch("second_brain.deps.BrainConfig") as mock_config_cls:
            mock_config_cls.return_value = BrainConfig(
                supabase_url="https://test.supabase.co",
                supabase_key="test-key",
                brain_data_path=tmp_path,
                _env_file=None,
            )
            from second_brain.deps import create_deps
            deps = create_deps()
            mock_config_cls.assert_called_once()
            assert deps.config is not None


class TestBrainDepsRegistry:
    """Test get_content_type_registry lazy initialization."""

    def test_get_content_type_registry_creates_on_first_call(self, tmp_path):
        from second_brain.deps import BrainDeps
        config = BrainConfig(
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
            brain_data_path=tmp_path,
            _env_file=None,
        )
        deps = BrainDeps(
            config=config,
            memory_service=MagicMock(),
            storage_service=MagicMock(),
        )
        with patch("second_brain.services.storage.ContentTypeRegistry") as mock_reg:
            mock_reg.return_value = MagicMock()
            registry = deps.get_content_type_registry()
            assert registry is not None
            mock_reg.assert_called_once()

    def test_get_content_type_registry_caches(self, tmp_path):
        from second_brain.deps import BrainDeps
        config = BrainConfig(
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
            brain_data_path=tmp_path,
            _env_file=None,
        )
        deps = BrainDeps(
            config=config,
            memory_service=MagicMock(),
            storage_service=MagicMock(),
        )
        with patch("second_brain.services.storage.ContentTypeRegistry") as mock_reg:
            mock_reg.return_value = MagicMock()
            r1 = deps.get_content_type_registry()
            r2 = deps.get_content_type_registry()
            assert r1 is r2  # Same instance (cached)
            mock_reg.assert_called_once()  # Only created once


class TestGraphitiConfig:
    """Test graphiti_enabled config validation."""

    def test_graphiti_enabled_with_neo4j(self, tmp_path):
        """graphiti_enabled=True with neo4j_url should pass."""
        config = BrainConfig(
            graphiti_enabled=True,
            neo4j_url="neo4j://localhost:7687",
            neo4j_username="neo4j",
            neo4j_password="test",
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
            brain_data_path=tmp_path,
            _env_file=None,
        )
        assert config.graphiti_enabled is True

    def test_graphiti_enabled_with_falkordb(self, tmp_path):
        """graphiti_enabled=True with falkordb_url should pass."""
        config = BrainConfig(
            graphiti_enabled=True,
            falkordb_url="falkor://localhost:6379",
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
            brain_data_path=tmp_path,
            _env_file=None,
        )
        assert config.graphiti_enabled is True
        assert config.falkordb_url == "falkor://localhost:6379"

    def test_graphiti_enabled_with_both_backends(self, tmp_path):
        """graphiti_enabled=True with both URLs for fallback."""
        config = BrainConfig(
            graphiti_enabled=True,
            neo4j_url="neo4j://localhost:7687",
            neo4j_username="neo4j",
            neo4j_password="test",
            falkordb_url="falkor://localhost:6379",
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
            brain_data_path=tmp_path,
            _env_file=None,
        )
        assert config.neo4j_url is not None
        assert config.falkordb_url is not None

    def test_graphiti_enabled_without_any_backend_fails(self, tmp_path):
        """graphiti_enabled=True without neo4j or falkordb should fail."""
        with pytest.raises(ValueError, match="graphiti_enabled=True requires"):
            BrainConfig(
                graphiti_enabled=True,
                supabase_url="https://test.supabase.co",
                supabase_key="test-key",
                brain_data_path=tmp_path,
                _env_file=None,
            )

    def test_graphiti_disabled_by_default(self, tmp_path):
        """graphiti_enabled defaults to False."""
        config = BrainConfig(
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
            brain_data_path=tmp_path,
            _env_file=None,
        )
        assert config.graphiti_enabled is False
        assert config.falkordb_url is None

    def test_falkordb_password_not_in_repr(self, tmp_path):
        """falkordb_password should be hidden in repr."""
        config = BrainConfig(
            graphiti_enabled=True,
            falkordb_url="falkor://localhost:6379",
            falkordb_password="secret",
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
            brain_data_path=tmp_path,
            _env_file=None,
        )
        assert "secret" not in repr(config)


class TestSubscriptionConfig:
    """Tests for subscription auth config fields."""

    def test_use_subscription_default_false(self, tmp_path):
        config = BrainConfig(
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
            brain_data_path=tmp_path,
            _env_file=None,
        )
        assert config.use_subscription is False

    def test_use_subscription_from_env(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_KEY", "test-key")
        monkeypatch.setenv("BRAIN_DATA_PATH", str(tmp_path))
        monkeypatch.setenv("USE_SUBSCRIPTION", "true")
        config = BrainConfig(_env_file=None)
        assert config.use_subscription is True

    def test_oauth_token_default_none(self, tmp_path):
        config = BrainConfig(
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
            brain_data_path=tmp_path,
            _env_file=None,
        )
        assert config.claude_oauth_token is None

    def test_oauth_token_from_env(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_KEY", "test-key")
        monkeypatch.setenv("BRAIN_DATA_PATH", str(tmp_path))
        monkeypatch.setenv("CLAUDE_OAUTH_TOKEN", "sk-ant-oat01-test")
        config = BrainConfig(_env_file=None)
        assert config.claude_oauth_token == "sk-ant-oat01-test"

    def test_oauth_token_not_in_repr(self, tmp_path):
        """OAuth token should be hidden in repr (security)."""
        config = BrainConfig(
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
            brain_data_path=tmp_path,
            claude_oauth_token="sk-ant-oat01-secret",
            _env_file=None,
        )
        assert "sk-ant-oat01-secret" not in repr(config)


class TestMemoryProviderConfig:
    """Tests for memory_provider config field and validator."""

    def test_memory_provider_default_is_mem0(self, tmp_path):
        """Default memory_provider is 'mem0'."""
        config = BrainConfig(
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
            brain_data_path=tmp_path,
            _env_file=None,
        )
        assert config.memory_provider == "mem0"

    def test_memory_provider_none_is_valid(self, tmp_path):
        """memory_provider='none' is accepted without any credential requirements."""
        config = BrainConfig(
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
            brain_data_path=tmp_path,
            memory_provider="none",
            _env_file=None,
        )
        assert config.memory_provider == "none"

    def test_memory_provider_invalid_raises(self, tmp_path):
        """Unknown memory_provider value raises ValidationError."""
        with pytest.raises(ValidationError):
            BrainConfig(
                supabase_url="https://test.supabase.co",
                supabase_key="test-key",
                brain_data_path=tmp_path,
                memory_provider="redis",
                _env_file=None,
            )

    def test_memory_provider_graphiti_without_creds_raises(self, tmp_path):
        """memory_provider='graphiti' without Neo4j or FalkorDB URL raises ValidationError."""
        with pytest.raises(ValidationError):
            BrainConfig(
                supabase_url="https://test.supabase.co",
                supabase_key="test-key",
                brain_data_path=tmp_path,
                memory_provider="graphiti",
                _env_file=None,
            )


class TestMcpTransportConfig:
    """Tests for MCP transport config fields and validator."""

    def test_mcp_transport_default_stdio(self, tmp_path):
        config = BrainConfig(
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
            brain_data_path=tmp_path,
            _env_file=None,
        )
        assert config.mcp_transport == "stdio"

    def test_mcp_transport_http(self, tmp_path):
        config = BrainConfig(
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
            brain_data_path=tmp_path,
            mcp_transport="http",
            _env_file=None,
        )
        assert config.mcp_transport == "http"

    def test_mcp_transport_sse(self, tmp_path):
        config = BrainConfig(
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
            brain_data_path=tmp_path,
            mcp_transport="sse",
            _env_file=None,
        )
        assert config.mcp_transport == "sse"

    def test_mcp_transport_invalid_raises(self, tmp_path):
        with pytest.raises(ValidationError, match="mcp_transport must be"):
            BrainConfig(
                supabase_url="https://test.supabase.co",
                supabase_key="test-key",
                brain_data_path=tmp_path,
                mcp_transport="websocket",
                _env_file=None,
            )

    def test_mcp_transport_from_env(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_KEY", "test-key")
        monkeypatch.setenv("BRAIN_DATA_PATH", str(tmp_path))
        monkeypatch.setenv("MCP_TRANSPORT", "http")
        config = BrainConfig(_env_file=None)
        assert config.mcp_transport == "http"

    def test_mcp_host_default(self, tmp_path):
        config = BrainConfig(
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
            brain_data_path=tmp_path,
            _env_file=None,
        )
        assert config.mcp_host == "0.0.0.0"

    def test_mcp_port_default(self, tmp_path):
        config = BrainConfig(
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
            brain_data_path=tmp_path,
            _env_file=None,
        )
        assert config.mcp_port == 8000

    def test_mcp_port_from_env(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_KEY", "test-key")
        monkeypatch.setenv("BRAIN_DATA_PATH", str(tmp_path))
        monkeypatch.setenv("MCP_PORT", "9090")
        config = BrainConfig(_env_file=None)
        assert config.mcp_port == 9090

    def test_mcp_port_below_range_raises(self, tmp_path):
        with pytest.raises(ValidationError):
            BrainConfig(
                supabase_url="https://test.supabase.co",
                supabase_key="test-key",
                brain_data_path=tmp_path,
                mcp_port=80,
                _env_file=None,
            )

    def test_mcp_port_above_range_raises(self, tmp_path):
        with pytest.raises(ValidationError):
            BrainConfig(
                supabase_url="https://test.supabase.co",
                supabase_key="test-key",
                brain_data_path=tmp_path,
                mcp_port=70000,
                _env_file=None,
            )
