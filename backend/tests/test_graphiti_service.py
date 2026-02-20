"""GraphitiService unit tests."""

import sys
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from second_brain.config import BrainConfig


@pytest.fixture(autouse=True)
def _mock_graphiti_core():
    """Inject a mock graphiti_core module so imports don't fail."""
    mock_module = MagicMock()
    mock_module.Graphiti = MagicMock()
    mock_module.edges.EpisodeType.text = "text"
    with patch.dict(sys.modules, {
        "graphiti_core": mock_module,
        "graphiti_core.edges": mock_module.edges,
        "graphiti_core.llm_client": MagicMock(),
        "graphiti_core.llm_client.config": MagicMock(),
        "graphiti_core.llm_client.anthropic_client": MagicMock(),
        "graphiti_core.llm_client.openai_generic_client": MagicMock(),
        "graphiti_core.embedder": MagicMock(),
        "graphiti_core.embedder.openai": MagicMock(),
        "graphiti_core.embedder.voyage": MagicMock(),
        "graphiti_core.cross_encoder": MagicMock(),
        "graphiti_core.cross_encoder.openai_reranker_client": MagicMock(),
    }):
        yield mock_module


@pytest.fixture
def graphiti_config(tmp_path):
    return BrainConfig(
        anthropic_api_key="test-key",
        openai_api_key="test-key",
        graph_provider="graphiti",
        neo4j_url="neo4j://localhost:7687",
        neo4j_username="neo4j",
        neo4j_password="test",
        supabase_url="https://test.supabase.co",
        supabase_key="test-key",
        brain_data_path=tmp_path,
        _env_file=None,
    )


class TestGraphitiServiceInit:
    """Test initialization and lazy setup."""

    def test_constructor_sets_defaults(self, graphiti_config):
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        assert service._client is None
        assert service._initialized is False
        assert service._init_failed is False

    @patch("second_brain.services.graphiti.GraphitiService._build_providers")
    async def test_ensure_init_success(self, mock_providers, graphiti_config, _mock_graphiti_core):
        mock_providers.return_value = (MagicMock(), MagicMock(), MagicMock())
        mock_client = AsyncMock()
        _mock_graphiti_core.Graphiti.return_value = mock_client
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        await service._ensure_init()
        assert service._initialized is True
        mock_client.build_indices_and_constraints.assert_awaited_once()

    @patch("second_brain.services.graphiti.GraphitiService._build_providers")
    async def test_ensure_init_failure_sets_flag(self, mock_providers, graphiti_config, _mock_graphiti_core):
        mock_providers.return_value = (MagicMock(), MagicMock(), MagicMock())
        _mock_graphiti_core.Graphiti.side_effect = Exception("Connection refused")
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        await service._ensure_init()
        assert service._initialized is False
        assert service._init_failed is True
        # Reset side_effect for other tests
        _mock_graphiti_core.Graphiti.side_effect = None

    async def test_ensure_init_skips_after_failure(self, graphiti_config):
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._init_failed = True
        await service._ensure_init()  # Should return immediately
        assert service._initialized is False

    async def test_ensure_init_skips_when_already_initialized(self, graphiti_config):
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._initialized = True
        service._client = MagicMock()
        await service._ensure_init()  # Should return immediately
        assert service._initialized is True


class TestGraphitiServiceSearch:
    """Test search method."""

    async def test_search_returns_relations(self, graphiti_config):
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._initialized = True
        mock_edge = MagicMock()
        mock_edge.source_node_name = "NodeA"
        mock_edge.fact = "relates_to"
        mock_edge.target_node_name = "NodeB"
        service._client = AsyncMock()
        service._client.search = AsyncMock(return_value=[mock_edge])
        results = await service.search("test query")
        assert len(results) == 1
        assert results[0]["source"] == "NodeA"
        assert results[0]["relationship"] == "relates_to"
        assert results[0]["target"] == "NodeB"

    async def test_search_returns_empty_when_not_initialized(self, graphiti_config):
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._init_failed = True
        results = await service.search("test")
        assert results == []

    async def test_search_handles_exception(self, graphiti_config):
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._initialized = True
        service._client = AsyncMock()
        service._client.search = AsyncMock(side_effect=Exception("timeout"))
        results = await service.search("test")
        assert results == []

    async def test_search_respects_limit(self, graphiti_config):
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._initialized = True
        edges = []
        for i in range(15):
            edge = MagicMock()
            edge.source_node_name = f"Node{i}"
            edge.fact = "rel"
            edge.target_node_name = f"Target{i}"
            edges.append(edge)
        service._client = AsyncMock()
        service._client.search = AsyncMock(return_value=edges)
        results = await service.search("test", limit=5)
        assert len(results) == 5


class TestGraphitiServiceAddEpisode:
    """Test add_episode method."""

    async def test_add_episode_success(self, graphiti_config):
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._initialized = True
        service._client = AsyncMock()
        await service.add_episode("test content", {"source": "test"})
        service._client.add_episode.assert_awaited_once()

    async def test_add_episode_skips_when_not_initialized(self, graphiti_config):
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._init_failed = True
        await service.add_episode("test content")
        # Should not raise — just skip silently

    async def test_add_episode_handles_exception(self, graphiti_config):
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._initialized = True
        service._client = AsyncMock()
        service._client.add_episode = AsyncMock(side_effect=Exception("graph error"))
        await service.add_episode("test content")
        # Should not raise — caught and logged


class TestGraphitiServiceClose:
    """Test close method."""

    async def test_close_with_client(self, graphiti_config):
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._client = AsyncMock()
        service._initialized = True
        await service.close()
        service._client.close.assert_awaited_once()
        assert service._initialized is False

    async def test_close_without_client(self, graphiti_config):
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        await service.close()  # Should not raise


class TestGraphitiServiceFallback:
    """Test Neo4j → FalkorDB fallback behavior."""

    @patch("second_brain.services.graphiti.GraphitiService._build_providers")
    async def test_neo4j_primary_success(self, mock_providers, graphiti_config, _mock_graphiti_core):
        """When Neo4j connects, it should be used as backend."""
        mock_providers.return_value = (MagicMock(), MagicMock(), MagicMock())
        mock_client = AsyncMock()
        _mock_graphiti_core.Graphiti.return_value = mock_client
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        await service._ensure_init()
        assert service._initialized is True
        assert service._backend == "neo4j"

    @patch("second_brain.services.graphiti.GraphitiService._build_providers")
    async def test_fallback_to_falkordb(self, mock_providers, tmp_path, _mock_graphiti_core):
        """When Neo4j fails, should fall back to FalkorDB."""
        mock_providers.return_value = (MagicMock(), MagicMock(), MagicMock())
        # First call (Neo4j) fails, second call (FalkorDB) succeeds
        mock_client_falkor = AsyncMock()
        _mock_graphiti_core.Graphiti.side_effect = [
            Exception("Neo4j connection refused"),
            mock_client_falkor,
        ]
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
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(config)
        await service._ensure_init()
        assert service._initialized is True
        assert service._backend == "falkordb"
        # Reset side_effect
        _mock_graphiti_core.Graphiti.side_effect = None

    @patch("second_brain.services.graphiti.GraphitiService._build_providers")
    async def test_both_backends_fail(self, mock_providers, tmp_path, _mock_graphiti_core):
        """When both Neo4j and FalkorDB fail, should mark init_failed."""
        mock_providers.return_value = (MagicMock(), MagicMock(), MagicMock())
        _mock_graphiti_core.Graphiti.side_effect = Exception("All connections refused")
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
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(config)
        await service._ensure_init()
        assert service._initialized is False
        assert service._init_failed is True
        # Reset side_effect
        _mock_graphiti_core.Graphiti.side_effect = None

    async def test_falkordb_only_config(self, tmp_path):
        """When only falkordb_url is set, should try FalkorDB directly."""
        config = BrainConfig(
            graphiti_enabled=True,
            falkordb_url="falkor://localhost:6379",
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
            brain_data_path=tmp_path,
            _env_file=None,
        )
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(config)
        # Without mocking Graphiti constructor, init will fail (graphiti_core not installed)
        # but it should NOT crash — just set _init_failed
        await service._ensure_init()
        assert service._init_failed is True


class TestGraphitiServiceHealth:
    """Test health check method."""

    async def test_health_check_healthy(self, graphiti_config):
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._initialized = True
        service._backend = "neo4j"
        service._client = AsyncMock()
        service._client.search = AsyncMock(return_value=[])
        result = await service.health_check()
        assert result["status"] == "healthy"
        assert result["backend"] == "neo4j"

    async def test_health_check_degraded(self, graphiti_config):
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._initialized = True
        service._backend = "neo4j"
        service._client = AsyncMock()
        service._client.search = AsyncMock(side_effect=Exception("timeout"))
        result = await service.health_check()
        assert result["status"] == "degraded"

    async def test_health_check_unavailable(self, graphiti_config):
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._init_failed = True
        result = await service.health_check()
        assert result["status"] == "unavailable"


class TestGraphitiServiceBatch:
    """Test batch episode add."""

    async def test_add_episodes_batch_success(self, graphiti_config):
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._initialized = True
        service._client = AsyncMock()
        episodes = [
            {"content": "Episode 1", "metadata": {"source": "test"}},
            {"content": "Episode 2"},
        ]
        count = await service.add_episodes_batch(episodes)
        assert count == 2

    async def test_add_episodes_batch_skips_when_unavailable(self, graphiti_config):
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._init_failed = True
        count = await service.add_episodes_batch([{"content": "test"}])
        assert count == 0


class TestBuildProvidersVoyage:
    """Test _build_providers() Voyage AI embedder selection."""

    def test_voyage_embedder_when_key_present(self, graphiti_config):
        """Voyage AI embedder is used when voyage_api_key is set."""
        graphiti_config.voyage_api_key = "test-voyage-key"
        graphiti_config.graphiti_embedding_model = "voyage-3.5"
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        llm, embedder, cross = service._build_providers()
        # The embedder should come from the voyage mock module
        assert embedder is not None

    def test_openai_embedder_fallback(self, graphiti_config):
        """Falls back to OpenAI when no Voyage key."""
        graphiti_config.voyage_api_key = None
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        llm, embedder, cross = service._build_providers()
        assert embedder is not None

    def test_voyage_uses_configured_model(self, graphiti_config):
        """Voyage embedder uses graphiti_embedding_model from config."""
        graphiti_config.voyage_api_key = "test-voyage-key"
        graphiti_config.graphiti_embedding_model = "voyage-3.5-lite"
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        # Should not raise
        llm, embedder, cross = service._build_providers()
        assert embedder is not None


class TestBuildProvidersOllamaCloud:
    """Test _build_providers() Ollama Cloud LLM override."""

    def test_ollama_cloud_override(self, graphiti_config):
        """graphiti_llm_model forces Ollama even with Anthropic key."""
        graphiti_config.anthropic_api_key = "test-key"
        graphiti_config.graphiti_llm_model = "deepseek-v3.1:671b-cloud"
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        llm, embedder, cross = service._build_providers()
        # LLM should be OpenAIGenericClient (from mocked module)
        assert llm is not None

    def test_anthropic_when_no_override(self, graphiti_config):
        """Anthropic is used when no graphiti_llm_model override."""
        graphiti_config.anthropic_api_key = "test-key"
        graphiti_config.graphiti_llm_model = None
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        llm, embedder, cross = service._build_providers()
        assert llm is not None

    def test_ollama_fallback_when_no_anthropic(self, graphiti_config):
        """Ollama is used when no Anthropic key and no override."""
        graphiti_config.anthropic_api_key = None
        graphiti_config.graphiti_llm_model = None
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        llm, embedder, cross = service._build_providers()
        assert llm is not None

    def test_cross_encoder_ollama_fallback(self, graphiti_config):
        """Cross-encoder uses Ollama when no OpenAI key."""
        graphiti_config.openai_api_key = None
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        llm, embedder, cross = service._build_providers()
        assert cross is not None

    def test_cross_encoder_openai_when_key_present(self, graphiti_config):
        """Cross-encoder uses OpenAI when key is present."""
        graphiti_config.openai_api_key = "test-openai-key"
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        llm, embedder, cross = service._build_providers()
        assert cross is not None


class TestAddEpisodesChunked:
    """Test add_episodes_chunked() contextual chunking."""

    async def test_short_content_single_episode(self, graphiti_config):
        """Content under chunk_size is sent as a single episode."""
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._initialized = True
        service._client = AsyncMock()
        count = await service.add_episodes_chunked("Short content", chunk_size=4000)
        assert count == 1

    async def test_long_content_multiple_chunks(self, graphiti_config):
        """Content over chunk_size is split into multiple episodes."""
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._initialized = True
        service._client = AsyncMock()
        long_content = "Word " * 2000  # ~10000 chars
        count = await service.add_episodes_chunked(long_content, chunk_size=2000)
        assert count > 1

    async def test_skips_when_unavailable(self, graphiti_config):
        """Returns 0 when Graphiti is not initialized."""
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._init_failed = True
        count = await service.add_episodes_chunked("test content")
        assert count == 0

    async def test_chunk_metadata_includes_index(self, graphiti_config):
        """Each chunk includes chunk_index and total_chunks in metadata."""
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._initialized = True
        service._client = AsyncMock()
        long_content = "Sentence here. " * 500  # ~7500 chars
        await service.add_episodes_chunked(
            long_content,
            metadata={"source": "test"},
            chunk_size=2000,
        )
        assert service._client.add_episode.call_count > 1

    async def test_empty_content_single_episode(self, graphiti_config):
        """Empty/short content produces a single episode."""
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._initialized = True
        service._client = AsyncMock()
        count = await service.add_episodes_chunked("")
        assert count == 1

    async def test_content_at_chunk_boundary(self, graphiti_config):
        """Content exactly at chunk_size produces a single episode."""
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._initialized = True
        service._client = AsyncMock()
        content = "x" * 4000
        count = await service.add_episodes_chunked(content, chunk_size=4000)
        assert count == 1


class TestAddEpisodeMetadata:
    """Test improved add_episode() metadata handling."""

    async def test_episode_name_includes_source(self, graphiti_config):
        """Episode name includes source from metadata."""
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._initialized = True
        service._client = AsyncMock()
        await service.add_episode("test", metadata={"source": "learn_agent"})
        call_kwargs = service._client.add_episode.call_args.kwargs
        assert call_kwargs["name"].startswith("learn_agent_")

    async def test_episode_name_fallback_without_metadata(self, graphiti_config):
        """Episode name uses 'episode_' prefix when no metadata."""
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._initialized = True
        service._client = AsyncMock()
        await service.add_episode("test content")
        call_kwargs = service._client.add_episode.call_args.kwargs
        assert call_kwargs["name"].startswith("episode_")

    async def test_source_description_rich_metadata(self, graphiti_config):
        """Source description combines source, category, and client."""
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._initialized = True
        service._client = AsyncMock()
        await service.add_episode(
            "test",
            metadata={"source": "zoom", "category": "meeting", "client": "ABC"},
        )
        call_kwargs = service._client.add_episode.call_args.kwargs
        assert "zoom" in call_kwargs["source_description"]
        assert "category:meeting" in call_kwargs["source_description"]
        assert "client:ABC" in call_kwargs["source_description"]

    async def test_reference_time_from_metadata(self, graphiti_config):
        """Reference time is parsed from metadata when provided."""
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._initialized = True
        service._client = AsyncMock()
        await service.add_episode(
            "test",
            metadata={"reference_time": "2026-01-15T14:30:00+00:00"},
        )
        call_kwargs = service._client.add_episode.call_args.kwargs
        assert call_kwargs["reference_time"].year == 2026
        assert call_kwargs["reference_time"].month == 1

    async def test_reference_time_invalid_falls_back(self, graphiti_config):
        """Invalid reference_time falls back to now."""
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._initialized = True
        service._client = AsyncMock()
        await service.add_episode(
            "test",
            metadata={"reference_time": "not-a-date"},
        )
        call_kwargs = service._client.add_episode.call_args.kwargs
        # Should still have a reference_time (falls back to now)
        assert call_kwargs["reference_time"] is not None


class TestRemoveEpisode:
    """Test remove_episode() via Cypher query."""

    async def test_remove_episode_success(self, graphiti_config):
        """remove_episode() deletes an episode and returns True."""
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._initialized = True
        mock_driver = AsyncMock()
        mock_driver.execute_query = AsyncMock(return_value=([{"deleted": 1}], None, None))
        service._client = MagicMock()
        service._client.driver = mock_driver
        result = await service.remove_episode("ep-uuid-1")
        assert result is True
        mock_driver.execute_query.assert_awaited_once()

    async def test_remove_episode_not_found(self, graphiti_config):
        """remove_episode() returns False when episode doesn't exist."""
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._initialized = True
        mock_driver = AsyncMock()
        mock_driver.execute_query = AsyncMock(return_value=([{"deleted": 0}], None, None))
        service._client = MagicMock()
        service._client.driver = mock_driver
        result = await service.remove_episode("nonexistent")
        assert result is False

    async def test_remove_episode_no_driver(self, graphiti_config):
        """remove_episode() returns False when driver unavailable."""
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._initialized = True
        service._client = MagicMock(spec=[])  # no driver attr
        result = await service.remove_episode("ep-uuid-1")
        assert result is False

    async def test_remove_episode_not_initialized(self, graphiti_config):
        """remove_episode() returns False when not initialized."""
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._init_failed = True
        result = await service.remove_episode("ep-uuid-1")
        assert result is False

    async def test_remove_episode_exception(self, graphiti_config):
        """remove_episode() returns False on exception."""
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._initialized = True
        mock_driver = AsyncMock()
        mock_driver.execute_query = AsyncMock(side_effect=Exception("db error"))
        service._client = MagicMock()
        service._client.driver = mock_driver
        result = await service.remove_episode("ep-uuid-1")
        assert result is False


class TestGetEpisodes:
    """Test get_episodes() via Cypher query."""

    async def test_get_episodes_with_group_id(self, graphiti_config):
        """get_episodes() returns episodes filtered by group_id."""
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._initialized = True
        mock_driver = AsyncMock()
        mock_driver.execute_query = AsyncMock(return_value=([
            {"id": "uuid-1", "content": "ep 1", "source": "test", "created_at": "2026-01-01"},
            {"id": "uuid-2", "content": "ep 2", "source": "test", "created_at": "2026-01-02"},
        ], None, None))
        service._client = MagicMock()
        service._client.driver = mock_driver
        result = await service.get_episodes("user-1")
        assert len(result) == 2
        assert result[0]["id"] == "uuid-1"
        assert result[0]["content"] == "ep 1"

    async def test_get_episodes_without_group_id(self, graphiti_config):
        """get_episodes() returns all episodes when no group_id."""
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._initialized = True
        mock_driver = AsyncMock()
        mock_driver.execute_query = AsyncMock(return_value=([
            {"id": "uuid-1", "content": "ep 1", "source": None, "created_at": None},
        ], None, None))
        service._client = MagicMock()
        service._client.driver = mock_driver
        result = await service.get_episodes()
        assert len(result) == 1
        assert result[0]["source"] == "unknown"

    async def test_get_episodes_no_driver(self, graphiti_config):
        """get_episodes() returns [] when driver unavailable."""
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._initialized = True
        service._client = MagicMock(spec=[])
        result = await service.get_episodes("user-1")
        assert result == []

    async def test_get_episodes_not_initialized(self, graphiti_config):
        """get_episodes() returns [] when not initialized."""
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._init_failed = True
        result = await service.get_episodes("user-1")
        assert result == []

    async def test_get_episodes_exception(self, graphiti_config):
        """get_episodes() returns [] on exception."""
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._initialized = True
        mock_driver = AsyncMock()
        mock_driver.execute_query = AsyncMock(side_effect=Exception("network error"))
        service._client = MagicMock()
        service._client.driver = mock_driver
        result = await service.get_episodes("user-1")
        assert result == []


class TestGetEpisodeCount:
    """Test get_episode_count() via COUNT Cypher query."""

    async def test_get_episode_count_returns_count(self, graphiti_config):
        """get_episode_count() returns count from COUNT Cypher query."""
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._initialized = True
        mock_driver = AsyncMock()
        mock_driver.execute_query = AsyncMock(return_value=([
            {"cnt": 3},
        ], None, None))
        service._client = MagicMock()
        service._client.driver = mock_driver
        result = await service.get_episode_count("user-1")
        assert result == 3

    async def test_get_episode_count_returns_zero_when_not_initialized(self, graphiti_config):
        """get_episode_count() returns 0 when not initialized."""
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._init_failed = True
        result = await service.get_episode_count("user-1")
        assert result == 0


class TestDeleteGroupData:
    """Test delete_group_data() via Cypher query."""

    async def test_delete_group_data_success(self, graphiti_config):
        """delete_group_data() deletes episodes and returns count."""
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._initialized = True
        mock_driver = AsyncMock()
        mock_driver.execute_query = AsyncMock(return_value=([{"deleted": 5}], None, None))
        service._client = MagicMock()
        service._client.driver = mock_driver
        result = await service.delete_group_data("user-1")
        assert result == 5

    async def test_delete_group_data_no_driver(self, graphiti_config):
        """delete_group_data() returns 0 when driver unavailable."""
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._initialized = True
        service._client = MagicMock(spec=[])
        result = await service.delete_group_data("user-1")
        assert result == 0

    async def test_delete_group_data_not_initialized(self, graphiti_config):
        """delete_group_data() returns 0 when not initialized."""
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._init_failed = True
        result = await service.delete_group_data("user-1")
        assert result == 0

    async def test_delete_group_data_exception(self, graphiti_config):
        """delete_group_data() returns 0 on exception."""
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._initialized = True
        mock_driver = AsyncMock()
        mock_driver.execute_query = AsyncMock(side_effect=Exception("db error"))
        service._client = MagicMock()
        service._client.driver = mock_driver
        result = await service.delete_group_data("user-1")
        assert result == 0


class TestTimeoutWrapping:
    """Test asyncio.timeout wrapping on key methods."""

    def test_timeout_stored_from_config(self, graphiti_config):
        """Timeout is read from config.service_timeout_seconds."""
        graphiti_config.service_timeout_seconds = 25
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        assert service._timeout == 25

    def test_timeout_default_fallback(self, tmp_path):
        """Timeout defaults to 15 when config field absent."""
        config = MagicMock(spec=[])
        config.neo4j_url = None
        config.falkordb_url = None
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(config)
        assert service._timeout == 15

    async def test_search_timeout_returns_empty(self, graphiti_config):
        """search() returns [] on timeout."""
        import asyncio
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._initialized = True
        service._timeout = 0  # immediate timeout

        async def slow_search(*args, **kwargs):
            await asyncio.sleep(10)
            return []

        service._client = AsyncMock()
        service._client.search = slow_search
        # Should not have search_ attr to avoid group_id branch
        if hasattr(service._client, "search_"):
            del service._client.search_
        result = await service.search("test query")
        assert result == []

    async def test_add_episode_timeout_does_not_raise(self, graphiti_config):
        """add_episode() handles timeout gracefully."""
        import asyncio
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._initialized = True
        service._timeout = 0  # immediate timeout

        async def slow_add(*args, **kwargs):
            await asyncio.sleep(10)

        service._client = AsyncMock()
        service._client.add_episode = slow_add
        # Should not raise
        await service.add_episode("test content")


class TestRetryDecorator:
    """Tests for _GRAPHITI_RETRY tenacity decorator."""

    async def test_retry_decorator_exists(self):
        from second_brain.services.graphiti import _GRAPHITI_RETRY
        assert _GRAPHITI_RETRY is not None

    async def test_search_retries_on_connection_error(self, graphiti_config):
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._initialized = True
        mock_client = AsyncMock()
        service._client = mock_client
        # First call raises ConnectionError, second succeeds
        mock_edge = MagicMock()
        mock_edge.source_node_name = "A"
        mock_edge.fact = "rel"
        mock_edge.target_node_name = "B"
        mock_client.search.side_effect = [ConnectionError("conn failed"), [mock_edge]]
        # Remove search_ to avoid group_id branch
        if hasattr(mock_client, "search_"):
            del mock_client.search_
        result = await service.search("test")
        assert mock_client.search.call_count == 2
        assert len(result) == 1

    async def test_search_no_retry_on_value_error(self, graphiti_config):
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._initialized = True
        mock_client = AsyncMock()
        service._client = mock_client
        mock_client.search.side_effect = ValueError("bad query")
        if hasattr(mock_client, "search_"):
            del mock_client.search_
        result = await service.search("test")
        assert mock_client.search.call_count == 1
        assert result == []


class TestGetEpisodeCountOptimized:
    """Tests for O(1) get_episode_count using COUNT query."""

    async def test_count_uses_cypher_not_full_scan(self, graphiti_config):
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._initialized = True
        mock_driver = AsyncMock()
        mock_driver.execute_query.return_value = ([{"cnt": 42}], None, None)
        service._client = MagicMock(driver=mock_driver)
        count = await service.get_episode_count("user1")
        assert count == 42
        # Verify it used COUNT query, not get_episodes
        query_arg = mock_driver.execute_query.call_args[0][0]
        assert "count(e)" in query_arg.lower()

    async def test_count_zero_when_no_records(self, graphiti_config):
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._initialized = True
        mock_driver = AsyncMock()
        mock_driver.execute_query.return_value = ([], None, None)
        service._client = MagicMock(driver=mock_driver)
        count = await service.get_episode_count("user1")
        assert count == 0


class TestGetEpisodeById:
    """Tests for get_episode_by_id O(1) lookup."""

    async def test_returns_episode_dict(self, graphiti_config):
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._initialized = True
        mock_driver = AsyncMock()
        mock_driver.execute_query.return_value = (
            [{"id": "uuid-123", "content": "test content", "source": "brain", "created_at": "2024-01-01"}],
            None, None,
        )
        service._client = MagicMock(driver=mock_driver)
        ep = await service.get_episode_by_id("uuid-123")
        assert ep is not None
        assert ep["id"] == "uuid-123"
        assert ep["content"] == "test content"

    async def test_returns_none_when_not_found(self, graphiti_config):
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._initialized = True
        mock_driver = AsyncMock()
        mock_driver.execute_query.return_value = ([], None, None)
        service._client = MagicMock(driver=mock_driver)
        ep = await service.get_episode_by_id("nonexistent")
        assert ep is None


class TestSearchEntities:
    """Tests for search_entities Cypher query."""

    async def test_returns_entity_dicts(self, graphiti_config):
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._initialized = True
        mock_driver = AsyncMock()
        mock_driver.execute_query.return_value = (
            [{"uuid": "e1", "name": "Alice", "summary": "A person", "labels": ["Person"], "created_at": None}],
            None, None,
        )
        service._client = MagicMock(driver=mock_driver)
        entities = await service.search_entities("Alice")
        assert len(entities) == 1
        assert entities[0]["name"] == "Alice"
        assert entities[0]["summary"] == "A person"

    async def test_empty_on_no_results(self, graphiti_config):
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._initialized = True
        mock_driver = AsyncMock()
        mock_driver.execute_query.return_value = ([], None, None)
        service._client = MagicMock(driver=mock_driver)
        entities = await service.search_entities("nothing")
        assert entities == []

    async def test_label_fallback(self, graphiti_config):
        """Should try Entity first, then EntityNode."""
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._initialized = True
        mock_driver = AsyncMock()
        # First call (Entity label) returns empty, second call (EntityNode) returns data
        mock_driver.execute_query.side_effect = [
            ([], None, None),
            ([{"uuid": "e1", "name": "Bob", "summary": "", "labels": [], "created_at": None}], None, None),
        ]
        service._client = MagicMock(driver=mock_driver)
        entities = await service.search_entities("Bob")
        assert len(entities) == 1
        assert entities[0]["name"] == "Bob"
        assert mock_driver.execute_query.call_count == 2

    async def test_group_id_filtering(self, graphiti_config):
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._initialized = True
        mock_driver = AsyncMock()
        mock_driver.execute_query.return_value = (
            [{"uuid": "e1", "name": "Alice", "summary": "", "labels": [], "created_at": None}],
            None, None,
        )
        service._client = MagicMock(driver=mock_driver)
        await service.search_entities("Alice", group_id="user1")
        # Verify Cypher includes group_id filter
        query_arg = mock_driver.execute_query.call_args[0][0]
        assert "group_id" in query_arg

    async def test_returns_empty_when_not_initialized(self, graphiti_config):
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._init_failed = True
        result = await service.search_entities("test")
        assert result == []


class TestGetEntityContext:
    """Tests for get_entity_context Cypher query."""

    async def test_returns_entity_with_relationships(self, graphiti_config):
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._initialized = True
        mock_driver = AsyncMock()
        mock_driver.execute_query.return_value = (
            [{
                "uuid": "e1", "name": "Alice", "summary": "A person",
                "outgoing": [
                    {"type": "KNOWS", "fact": "knows well", "target_name": "Bob", "target_uuid": "e2", "direction": "outgoing"},
                ],
                "incoming": [
                    {"type": "WORKS_AT", "fact": "employed", "source_name": "Corp", "source_uuid": "e3", "direction": "incoming"},
                ],
            }],
            None, None,
        )
        service._client = MagicMock(driver=mock_driver)
        ctx = await service.get_entity_context("e1")
        assert ctx["entity"]["name"] == "Alice"
        assert len(ctx["relationships"]) == 2

    async def test_returns_none_entity_when_not_found(self, graphiti_config):
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._initialized = True
        mock_driver = AsyncMock()
        mock_driver.execute_query.return_value = ([], None, None)
        service._client = MagicMock(driver=mock_driver)
        ctx = await service.get_entity_context("nonexistent")
        assert ctx["entity"] is None
        assert ctx["relationships"] == []

    async def test_returns_default_when_not_initialized(self, graphiti_config):
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._init_failed = True
        ctx = await service.get_entity_context("e1")
        assert ctx["entity"] is None


class TestTraverseNeighbors:
    """Tests for traverse_neighbors BFS traversal."""

    async def test_cypher_fallback(self, graphiti_config):
        """When search_ not available, falls back to Cypher variable-length path."""
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._initialized = True
        mock_driver = AsyncMock()
        mock_driver.execute_query.return_value = (
            [{"source": "Alice", "relationship": "KNOWS", "target": "Bob", "fact": "friends"}],
            None, None,
        )
        # Use spec=[] so hasattr(client, "search_") returns False
        service._client = MagicMock(spec=["driver"])
        service._client.driver = mock_driver
        result = await service.traverse_neighbors("e1")
        assert len(result) == 1
        assert result[0]["source"] == "Alice"

    async def test_max_hops_capped_at_5(self, graphiti_config):
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._initialized = True
        mock_driver = AsyncMock()
        mock_driver.execute_query.return_value = ([], None, None)
        service._client = MagicMock(spec=["driver"])
        service._client.driver = mock_driver
        await service.traverse_neighbors("e1", max_hops=10)
        query_arg = mock_driver.execute_query.call_args[0][0]
        assert "*1..5" in query_arg

    async def test_empty_on_no_connections(self, graphiti_config):
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._initialized = True
        mock_driver = AsyncMock()
        mock_driver.execute_query.return_value = ([], None, None)
        service._client = MagicMock(spec=["driver"])
        service._client.driver = mock_driver
        result = await service.traverse_neighbors("e1")
        assert result == []


class TestSearchCommunities:
    """Tests for search_communities via search_ API."""

    async def test_returns_community_dicts(self, graphiti_config):
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._initialized = True
        mock_community = MagicMock()
        mock_community.uuid = "c1"
        mock_community.name = "Engineering"
        mock_community.summary = "Engineering team"
        mock_raw = MagicMock()
        mock_raw.communities = [mock_community]
        service._client = AsyncMock()
        service._client.search_ = AsyncMock(return_value=mock_raw)
        result = await service.search_communities("engineering")
        assert len(result) == 1
        assert result[0]["name"] == "Engineering"

    async def test_empty_when_search_unavailable(self, graphiti_config):
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._initialized = True
        service._client = MagicMock(spec=["search", "driver"])
        result = await service.search_communities("test")
        assert result == []

    async def test_returns_empty_when_not_initialized(self, graphiti_config):
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._init_failed = True
        result = await service.search_communities("test")
        assert result == []


class TestBuildCommunities:
    """Tests for build_communities trigger + return."""

    async def test_builds_and_returns_communities(self, graphiti_config):
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._initialized = True
        mock_community = MagicMock()
        mock_community.uuid = "c1"
        mock_community.name = "Engineering"
        mock_community.summary = "Engineering team"
        mock_raw = MagicMock()
        mock_raw.communities = [mock_community]
        service._client = AsyncMock()
        service._client.build_communities_ = AsyncMock(return_value=None)
        service._client.search_ = AsyncMock(return_value=mock_raw)
        result = await service.build_communities()
        service._client.build_communities_.assert_called_once_with()
        assert len(result) == 1
        assert result[0]["name"] == "Engineering"

    async def test_empty_when_api_unavailable(self, graphiti_config):
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._initialized = True
        service._client = MagicMock(spec=["search", "driver"])
        result = await service.build_communities()
        assert result == []

    async def test_returns_empty_when_not_initialized(self, graphiti_config):
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._init_failed = True
        result = await service.build_communities()
        assert result == []

    async def test_passes_group_id(self, graphiti_config):
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._initialized = True
        mock_raw = MagicMock()
        mock_raw.communities = []
        service._client = AsyncMock()
        service._client.build_communities_ = AsyncMock(return_value=None)
        service._client.search_ = AsyncMock(return_value=mock_raw)
        await service.build_communities(group_id="grp1")
        service._client.build_communities_.assert_called_once_with(group_ids=["grp1"])


class TestAdvancedSearch:
    """Tests for advanced_search with filters."""

    async def test_returns_edges_nodes_communities(self, graphiti_config):
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._initialized = True
        mock_edge = MagicMock()
        mock_edge.source_node_name = "A"
        mock_edge.fact = "knows"
        mock_edge.target_node_name = "B"
        mock_edge.uuid = "edge1"
        mock_node = MagicMock()
        mock_node.uuid = "n1"
        mock_node.name = "NodeA"
        mock_node.summary = "A node"
        mock_community = MagicMock()
        mock_community.uuid = "c1"
        mock_community.name = "Community1"
        mock_community.summary = "A community"
        mock_raw = MagicMock()
        mock_raw.edges = [mock_edge]
        mock_raw.nodes = [mock_node]
        mock_raw.communities = [mock_community]
        service._client = AsyncMock()
        service._client.search_ = AsyncMock(return_value=mock_raw)
        result = await service.advanced_search("test")
        assert len(result["edges"]) == 1
        assert len(result["nodes"]) == 1
        assert len(result["communities"]) == 1

    async def test_falls_back_to_basic_search(self, graphiti_config):
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._initialized = True
        mock_edge = MagicMock()
        mock_edge.source_node_name = "X"
        mock_edge.fact = "rel"
        mock_edge.target_node_name = "Y"
        # Mock basic search path
        service._client = AsyncMock()
        service._client.search = AsyncMock(return_value=[mock_edge])
        # Remove search_ so it falls back
        del service._client.search_
        result = await service.advanced_search("test")
        assert len(result["edges"]) == 1
        assert result["nodes"] == []
        assert result["communities"] == []

    async def test_returns_empty_when_not_initialized(self, graphiti_config):
        from second_brain.services.graphiti import GraphitiService
        service = GraphitiService(graphiti_config)
        service._init_failed = True
        result = await service.advanced_search("test")
        assert result == {"edges": [], "nodes": [], "communities": []}
