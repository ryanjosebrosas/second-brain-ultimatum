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
