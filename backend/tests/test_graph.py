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
