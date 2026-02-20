"""Tests for graph memory functionality."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock, PropertyMock

from second_brain.services.memory import MemoryService
from second_brain.services.search_result import SearchResult
from second_brain.schemas import Relation, RecallResult, AskResult


class TestSearchResult:
    def test_empty_search_result(self):
        r = SearchResult()
        assert r.memories == []
        assert r.relations == []

    def test_search_result_with_data(self):
        r = SearchResult(
            memories=[{"memory": "test", "score": 0.9}],
            relations=[{"source": "A", "relationship": "links", "target": "B"}],
        )
        assert len(r.memories) == 1
        assert len(r.relations) == 1


class TestRelationSchema:
    def test_relation_creation(self):
        rel = Relation(source="A", relationship="uses", target="B")
        assert rel.source == "A"
        assert rel.relationship == "uses"
        assert rel.target == "B"

    def test_recall_result_with_relations(self):
        result = RecallResult(
            query="test",
            relations=[Relation(source="X", relationship="links", target="Y")],
        )
        assert len(result.relations) == 1

    def test_recall_result_empty_relations(self):
        result = RecallResult(query="test")
        assert result.relations == []

    def test_ask_result_with_relations(self):
        result = AskResult(
            answer="test answer",
            relations=[Relation(source="A", relationship="r", target="B")],
        )
        assert len(result.relations) == 1


class TestMemoryServiceGraph:
    @patch("mem0.MemoryClient")
    async def test_search_with_graph_returns_search_result(
        self, mock_client_cls, brain_config_graph
    ):
        mock_client = MagicMock()
        mock_client.search.return_value = {
            "results": [{"memory": "test", "score": 0.9}],
            "relations": [
                {"source": "A", "relationship": "links", "target": "B"}
            ],
        }
        mock_client_cls.return_value = mock_client
        service = MemoryService(brain_config_graph)
        result = await service.search("test query")
        assert isinstance(result, SearchResult)
        assert len(result.memories) == 1
        assert len(result.relations) == 1

    @patch.object(MemoryService, '_is_cloud', new_callable=PropertyMock, return_value=True)
    @patch("mem0.MemoryClient")
    async def test_add_with_graph_passes_enable_graph(
        self, mock_client_cls, mock_is_cloud, brain_config_graph
    ):
        mock_client = MagicMock()
        mock_client.add.return_value = [{"id": "m1", "event": "ADD"}]
        mock_client_cls.return_value = mock_client
        service = MemoryService(brain_config_graph)
        await service.add("Test content")
        call_kwargs = mock_client.add.call_args[1]
        assert call_kwargs.get("enable_graph") is True

    @patch("mem0.Memory")
    async def test_search_without_graph_returns_empty_relations(
        self, mock_memory_cls, mock_config
    ):
        mock_client = MagicMock()
        mock_client.search.return_value = [
            {"memory": "test", "score": 0.9}
        ]
        mock_memory_cls.from_config.return_value = mock_client
        service = MemoryService(mock_config)
        result = await service.search("test query")
        assert isinstance(result, SearchResult)
        assert len(result.memories) == 1
        assert result.relations == []

    @patch.object(MemoryService, '_is_cloud', new_callable=PropertyMock, return_value=True)
    @patch("mem0.MemoryClient")
    async def test_enable_project_graph_on_cloud(
        self, mock_client_cls, mock_is_cloud, brain_config_graph
    ):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        service = MemoryService(brain_config_graph)
        await service.enable_project_graph()
        mock_client.project.update.assert_called_once_with(enable_graph=True)

    @patch("mem0.Memory")
    async def test_enable_project_graph_skips_local(
        self, mock_memory_cls, mock_config
    ):
        mock_client = MagicMock()
        mock_memory_cls.from_config.return_value = mock_client
        service = MemoryService(mock_config)
        await service.enable_project_graph()
        mock_client.project.update.assert_not_called()


class TestReingestVerification:
    @patch("scripts.reingest_graph.BrainMigrator")
    @patch("scripts.reingest_graph.MemoryService")
    @patch("scripts.reingest_graph.BrainConfig")
    async def test_reingest_enables_graph_before_migration(
        self, mock_config_cls, mock_memory_cls, mock_migrator_cls
    ):
        # Configure BrainConfig mock
        mock_config = MagicMock()
        mock_config.graph_provider = "mem0"
        mock_config_cls.return_value = mock_config

        # Configure MemoryService mock
        mock_memory = MagicMock()
        mock_memory.enable_project_graph = AsyncMock()
        mock_memory.get_all = AsyncMock(return_value=[])
        mock_memory.search = AsyncMock(return_value=SearchResult(
            memories=[{"memory": "test", "score": 0.9}],
            relations=[{"source": "A", "relationship": "links", "target": "B"}],
        ))
        mock_memory_cls.return_value = mock_memory

        # Configure BrainMigrator mock
        mock_migrator = MagicMock()
        mock_migrator.migrate_memory_content = AsyncMock()
        mock_migrator.migrate_patterns = AsyncMock()
        mock_migrator.migrate_experiences = AsyncMock()
        mock_migrator_cls.return_value = mock_migrator

        from scripts.reingest_graph import reingest
        await reingest()

        # Verify enable_project_graph was called
        mock_memory.enable_project_graph.assert_called_once()
        # Verify migration methods were called
        mock_migrator.migrate_memory_content.assert_called_once()
        mock_migrator.migrate_patterns.assert_called_once()
        mock_migrator.migrate_experiences.assert_called_once()
        # Verify verification search was called
        mock_memory.search.assert_called_once_with("test", limit=1)


class TestGraphitiMemoryAdapterSearch:
    """Tests for GraphitiMemoryAdapter search methods populating both memories and relations."""

    async def test_search_populates_both_fields(self):
        with patch("second_brain.services.graphiti.GraphitiService") as MockGS:
            mock_gs = AsyncMock()
            MockGS.return_value = mock_gs
            mock_gs.search.return_value = [
                {"source": "Alice", "relationship": "knows", "target": "Bob"}
            ]
            from second_brain.services.graphiti_memory import GraphitiMemoryAdapter
            config = MagicMock()
            config.brain_user_id = "user1"
            adapter = GraphitiMemoryAdapter(config)
            adapter._graphiti = mock_gs
            result = await adapter.search("test query")
            assert len(result.memories) == 1
            assert len(result.relations) == 1
            assert result.memories[0]["memory"] == "Alice knows Bob"
            assert result.memories[0]["score"] == 1.0
            assert result.relations[0]["source"] == "Alice"

    async def test_search_with_filters_populates_search_filters(self):
        with patch("second_brain.services.graphiti.GraphitiService") as MockGS:
            mock_gs = AsyncMock()
            MockGS.return_value = mock_gs
            mock_gs.search.return_value = [
                {"source": "X", "relationship": "rel", "target": "Y"}
            ]
            from second_brain.services.graphiti_memory import GraphitiMemoryAdapter
            config = MagicMock()
            config.brain_user_id = "user1"
            adapter = GraphitiMemoryAdapter(config)
            adapter._graphiti = mock_gs
            filters = {"category": "pattern"}
            result = await adapter.search_with_filters("test", metadata_filters=filters)
            assert len(result.memories) == 1
            assert result.search_filters == {"category": "pattern"}

    async def test_search_returns_empty_on_error(self):
        with patch("second_brain.services.graphiti.GraphitiService") as MockGS:
            mock_gs = AsyncMock()
            MockGS.return_value = mock_gs
            mock_gs.search.side_effect = Exception("boom")
            from second_brain.services.graphiti_memory import GraphitiMemoryAdapter
            config = MagicMock()
            config.brain_user_id = "user1"
            adapter = GraphitiMemoryAdapter(config)
            adapter._graphiti = mock_gs
            result = await adapter.search("test")
            assert result.memories == []
            assert result.relations == []

    async def test_search_by_category_populates_memories(self):
        with patch("second_brain.services.graphiti.GraphitiService") as MockGS:
            mock_gs = AsyncMock()
            MockGS.return_value = mock_gs
            mock_gs.search.return_value = [
                {"source": "Pattern", "relationship": "applies_to", "target": "Code"}
            ]
            from second_brain.services.graphiti_memory import GraphitiMemoryAdapter
            config = MagicMock()
            config.brain_user_id = "user1"
            adapter = GraphitiMemoryAdapter(config)
            adapter._graphiti = mock_gs
            result = await adapter.search_by_category("pattern", "coding")
            assert len(result.memories) == 1
            assert "Pattern" in result.memories[0]["memory"]

    async def test_get_by_id_uses_direct_lookup(self):
        with patch("second_brain.services.graphiti.GraphitiService") as MockGS:
            mock_gs = AsyncMock()
            MockGS.return_value = mock_gs
            mock_gs.get_episode_by_id.return_value = {
                "id": "ep-123", "content": "test", "source": "brain", "created_at": None
            }
            from second_brain.services.graphiti_memory import GraphitiMemoryAdapter
            config = MagicMock()
            config.brain_user_id = "user1"
            adapter = GraphitiMemoryAdapter(config)
            adapter._graphiti = mock_gs
            mem = await adapter.get_by_id("ep-123")
            assert mem is not None
            assert mem["memory"] == "test"
            mock_gs.get_episode_by_id.assert_called_once_with("ep-123")
            # Verify it did NOT call get_episodes (old O(N) path)
            mock_gs.get_episodes.assert_not_called()


class TestRelationsToMemories:
    """Tests for _relations_to_memories conversion helper."""

    def test_converts_relations_to_memory_format(self):
        from second_brain.services.graphiti_memory import _relations_to_memories
        relations = [
            {"source": "Alice", "relationship": "knows", "target": "Bob"},
            {"source": "X", "relationship": "connects", "target": "Y"},
        ]
        memories = _relations_to_memories(relations)
        assert len(memories) == 2
        assert memories[0]["memory"] == "Alice knows Bob"
        assert memories[0]["score"] == 1.0
        assert memories[0]["metadata"]["source"] == "graphiti"

    def test_empty_relations(self):
        from second_brain.services.graphiti_memory import _relations_to_memories
        assert _relations_to_memories([]) == []

    def test_missing_keys_use_defaults(self):
        from second_brain.services.graphiti_memory import _relations_to_memories
        memories = _relations_to_memories([{"source": "A"}])
        assert "?" in memories[0]["memory"]


class TestFormatSearchResult:
    """Tests for format_search_result dual-path helper."""

    def test_formats_both_memories_and_relations(self):
        from second_brain.agents.utils import format_search_result
        result = format_search_result(
            memories=[{"memory": "test pattern", "score": 0.9}],
            relations=[{"source": "A", "relationship": "knows", "target": "B"}],
        )
        assert "test pattern" in result
        assert "A --[knows]--> B" in result

    def test_memories_only(self):
        from second_brain.agents.utils import format_search_result
        result = format_search_result(
            memories=[{"memory": "test", "score": 0.8}],
            relations=[],
        )
        assert "test" in result
        assert "Graph" not in result

    def test_relations_only(self):
        from second_brain.agents.utils import format_search_result
        result = format_search_result(
            memories=[],
            relations=[{"source": "X", "relationship": "r", "target": "Y"}],
        )
        assert "X --[r]--> Y" in result

    def test_both_empty(self):
        from second_brain.agents.utils import format_search_result
        assert format_search_result([], []) == ""

    def test_memory_limit(self):
        from second_brain.agents.utils import format_search_result
        memories = [{"memory": f"m{i}", "score": 0.5} for i in range(10)]
        result = format_search_result(memories, [], memory_limit=3)
        assert result.count("[0.50]") == 3
