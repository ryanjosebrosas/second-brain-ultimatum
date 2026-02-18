"""Tests for BrainDeps dependency injection."""

import sys
from unittest.mock import patch, MagicMock

import pytest

from second_brain.config import BrainConfig
from second_brain.deps import BrainDeps, create_deps

# Lazy imports in create_deps must be patched at their source modules
_MEMORY_SVC = "second_brain.services.memory.MemoryService"
_STORAGE_SVC = "second_brain.services.storage.StorageService"
_GRAPHITI_SVC = "second_brain.services.graphiti.GraphitiService"
_EMBEDDING_SVC = "second_brain.services.embeddings.EmbeddingService"


def _config(tmp_path, **overrides):
    """Create a BrainConfig with test defaults + overrides."""
    defaults = {
        "supabase_url": "https://test.supabase.co",
        "supabase_key": "test-key",
        "brain_data_path": tmp_path,
        "_env_file": None,
    }
    defaults.update(overrides)
    return BrainConfig(**defaults)


class TestBrainDeps:
    """Tests for BrainDeps dataclass."""

    def test_get_content_type_registry_creates_on_first_call(self, mock_deps):
        """Registry is lazily created on first access."""
        mock_deps.content_type_registry = None
        registry = mock_deps.get_content_type_registry()
        assert registry is not None

    def test_get_content_type_registry_caches(self, mock_deps):
        """Same registry returned on subsequent calls."""
        mock_deps.content_type_registry = None
        r1 = mock_deps.get_content_type_registry()
        r2 = mock_deps.get_content_type_registry()
        assert r1 is r2

    def test_optional_services_default_none(self, brain_config, mock_memory, mock_storage):
        """Graphiti and embedding services default to None."""
        deps = BrainDeps(
            config=brain_config,
            memory_service=mock_memory,
            storage_service=mock_storage,
        )
        assert deps.graphiti_service is None
        assert deps.embedding_service is None
        assert deps.content_type_registry is None


class TestCreateDeps:
    """Tests for create_deps() factory function."""

    def test_creates_deps_basic(self, tmp_path):
        """create_deps returns BrainDeps with memory and storage services."""
        config = _config(tmp_path)
        with patch(_MEMORY_SVC) as mock_mem, \
             patch(_STORAGE_SVC) as mock_stor:
            deps = create_deps(config)
            assert deps.config is config
            mock_mem.assert_called_once_with(config)
            mock_stor.assert_called_once_with(config)

    def test_graphiti_none_when_disabled(self, tmp_path):
        """Graphiti is None when graphiti_enabled=False."""
        config = _config(tmp_path, graphiti_enabled=False)
        with patch(_MEMORY_SVC), patch(_STORAGE_SVC):
            deps = create_deps(config)
            assert deps.graphiti_service is None

    def test_embedding_service_none_without_key(self, tmp_path):
        """EmbeddingService is None when openai_api_key not set."""
        config = _config(tmp_path, openai_api_key=None)
        with patch(_MEMORY_SVC), patch(_STORAGE_SVC):
            deps = create_deps(config)
            assert deps.embedding_service is None

    def test_embedding_service_created_with_key(self, tmp_path):
        """EmbeddingService created when openai_api_key is set."""
        config = _config(tmp_path, openai_api_key="test-key")
        with patch(_MEMORY_SVC), patch(_STORAGE_SVC), \
             patch(_EMBEDDING_SVC) as mock_emb:
            mock_emb.return_value = MagicMock()
            deps = create_deps(config)
            assert deps.embedding_service is not None

    def test_graphiti_enabled_creates_service(self, tmp_path):
        """Graphiti service created when graphiti_enabled=True."""
        config = _config(
            tmp_path,
            graphiti_enabled=True,
            neo4j_url="neo4j://localhost",
            neo4j_username="neo4j",
            neo4j_password="test",
        )
        with patch(_MEMORY_SVC), patch(_STORAGE_SVC), \
             patch(_GRAPHITI_SVC) as mock_gs:
            mock_gs.return_value = MagicMock()
            deps = create_deps(config)
            assert deps.graphiti_service is not None

    def test_graphiti_import_error_degrades(self, tmp_path):
        """Graceful degradation when graphiti-core not installed."""
        config = _config(
            tmp_path,
            graphiti_enabled=True,
            neo4j_url="neo4j://localhost",
            neo4j_username="neo4j",
            neo4j_password="test",
        )
        with patch(_MEMORY_SVC), patch(_STORAGE_SVC):
            # Simulate ImportError by setting module to None
            original = sys.modules.get("second_brain.services.graphiti")
            sys.modules["second_brain.services.graphiti"] = None
            try:
                deps = create_deps(config)
                assert deps.graphiti_service is None
            finally:
                if original is not None:
                    sys.modules["second_brain.services.graphiti"] = original
                else:
                    sys.modules.pop("second_brain.services.graphiti", None)

    def test_legacy_graph_provider_graphiti(self, tmp_path):
        """Legacy graph_provider='graphiti' path creates service."""
        config = _config(
            tmp_path,
            graphiti_enabled=False,
            graph_provider="graphiti",
            neo4j_url="neo4j://localhost",
            neo4j_username="neo4j",
            neo4j_password="test",
        )
        with patch(_MEMORY_SVC), patch(_STORAGE_SVC), \
             patch(_GRAPHITI_SVC) as mock_gs:
            mock_gs.return_value = MagicMock()
            deps = create_deps(config)
            assert deps.graphiti_service is not None

    def test_default_config_when_none(self, tmp_path, monkeypatch):
        """create_deps creates BrainConfig when config=None."""
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_KEY", "test-key")
        monkeypatch.setenv("BRAIN_DATA_PATH", str(tmp_path))
        with patch(_MEMORY_SVC), patch(_STORAGE_SVC):
            deps = create_deps(None)
            assert deps.config is not None

    def test_embedding_service_init_error_degrades(self, tmp_path):
        """EmbeddingService failure returns None (graceful degradation)."""
        config = _config(tmp_path, openai_api_key="test-key")
        with patch(_MEMORY_SVC), patch(_STORAGE_SVC), \
             patch(_EMBEDDING_SVC, side_effect=RuntimeError("init failed")):
            deps = create_deps(config)
            assert deps.embedding_service is None


class TestBrainDepsExpanded:
    """Additional BrainDeps structural and accessor tests."""

    def test_brain_deps_with_all_five_services(
        self, brain_config, mock_memory, mock_storage,
        mock_embedding_service, mock_voyage_service, mock_graphiti,
    ):
        """BrainDeps can hold all 5 optional services simultaneously."""
        deps = BrainDeps(
            config=brain_config,
            memory_service=mock_memory,
            storage_service=mock_storage,
            embedding_service=mock_embedding_service,
            voyage_service=mock_voyage_service,
            graphiti_service=mock_graphiti,
        )
        assert deps.memory_service is mock_memory
        assert deps.storage_service is mock_storage
        assert deps.embedding_service is mock_embedding_service
        assert deps.voyage_service is mock_voyage_service
        assert deps.graphiti_service is mock_graphiti

    def test_brain_deps_memory_service_accessible(self, mock_deps):
        """mock_deps.memory_service is set and accessible."""
        assert mock_deps.memory_service is not None

    def test_brain_deps_storage_service_accessible(self, mock_deps):
        """mock_deps.storage_service is set and accessible."""
        assert mock_deps.storage_service is not None

    def test_brain_deps_config_accessible(self, mock_deps):
        """mock_deps.config is set with test values."""
        assert mock_deps.config is not None
        assert mock_deps.config.supabase_url == "https://test.supabase.co"

    def test_brain_deps_is_dataclass(self):
        """BrainDeps is a dataclass (not a plain class)."""
        import dataclasses
        assert dataclasses.is_dataclass(BrainDeps)

    def test_brain_deps_voyage_service_defaults_none(self, brain_config, mock_memory, mock_storage):
        """voyage_service defaults to None when not provided."""
        deps = BrainDeps(
            config=brain_config,
            memory_service=mock_memory,
            storage_service=mock_storage,
        )
        assert deps.voyage_service is None

    def test_create_deps_returns_brain_deps_instance(self, tmp_path):
        """create_deps() always returns a BrainDeps instance."""
        config = _config(tmp_path)
        with patch(_MEMORY_SVC), patch(_STORAGE_SVC):
            deps = create_deps(config)
            assert isinstance(deps, BrainDeps)

    def test_brain_deps_email_service_defaults_none(self, brain_config, mock_memory, mock_storage):
        """Optional services (email, calendar, etc.) default to None."""
        deps = BrainDeps(
            config=brain_config,
            memory_service=mock_memory,
            storage_service=mock_storage,
        )
        assert deps.email_service is None
        assert deps.calendar_service is None
        assert deps.task_service is None
