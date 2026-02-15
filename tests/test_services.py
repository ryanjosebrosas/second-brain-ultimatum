"""Unit tests for MemoryService, StorageService, and HealthService."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from second_brain.services.memory import MemoryService
from second_brain.services.storage import StorageService


class TestMemoryService:
    @patch("mem0.Memory")
    def test_init_local(self, mock_memory_cls, mock_config):
        """MemoryService initializes Mem0 local when no cloud key."""
        service = MemoryService(mock_config)
        mock_memory_cls.from_config.assert_called_once()
        assert service.user_id == "ryan"

    @patch("mem0.Memory")
    async def test_add(self, mock_memory_cls, mock_config):
        mock_client = MagicMock()
        mock_client.add.return_value = {"id": "mem-123"}
        mock_memory_cls.from_config.return_value = mock_client

        service = MemoryService(mock_config)
        result = await service.add("test content", metadata={"source": "test"})

        mock_client.add.assert_called_once()
        assert result == {"id": "mem-123"}

    @patch("mem0.Memory")
    async def test_search(self, mock_memory_cls, mock_config):
        mock_client = MagicMock()
        mock_client.search.return_value = [
            {"memory": "test pattern", "score": 0.95}
        ]
        mock_memory_cls.from_config.return_value = mock_client

        service = MemoryService(mock_config)
        results = await service.search("test query")

        assert len(results.memories) == 1
        assert results.memories[0]["memory"] == "test pattern"
        assert results.relations == []

    @patch("mem0.Memory")
    async def test_search_with_limit(self, mock_memory_cls, mock_config):
        mock_client = MagicMock()
        mock_client.search.return_value = [
            {"memory": f"result {i}", "score": 0.9 - i * 0.1}
            for i in range(5)
        ]
        mock_memory_cls.from_config.return_value = mock_client

        service = MemoryService(mock_config)
        results = await service.search("test", limit=2)

        assert len(results.memories) == 2

    @patch("mem0.Memory")
    async def test_search_non_list_result(self, mock_memory_cls, mock_config):
        mock_client = MagicMock()
        mock_client.search.return_value = {"results": []}  # non-list
        mock_memory_cls.from_config.return_value = mock_client

        service = MemoryService(mock_config)
        results = await service.search("test")

        assert results.memories == []
        assert results.relations == []

    @patch("mem0.Memory")
    async def test_get_all(self, mock_memory_cls, mock_config):
        mock_client = MagicMock()
        mock_client.get_all.return_value = [{"id": "1"}, {"id": "2"}]
        mock_memory_cls.from_config.return_value = mock_client

        service = MemoryService(mock_config)
        results = await service.get_all()

        assert len(results) == 2

    @patch("mem0.Memory")
    async def test_get_memory_count(self, mock_memory_cls, mock_config):
        mock_client = MagicMock()
        mock_client.get_all.return_value = [
            {"id": "1", "memory": "a"},
            {"id": "2", "memory": "b"},
            {"id": "3", "memory": "c"},
        ]
        mock_memory_cls.from_config.return_value = mock_client

        service = MemoryService(mock_config)
        count = await service.get_memory_count()
        assert count == 3

    @patch("mem0.Memory")
    async def test_delete(self, mock_memory_cls, mock_config):
        mock_client = MagicMock()
        mock_memory_cls.from_config.return_value = mock_client

        service = MemoryService(mock_config)
        await service.delete("mem-123")

        mock_client.delete.assert_called_once_with("mem-123")


class TestStorageService:
    @patch("second_brain.services.storage.create_client")
    def test_init(self, mock_create, mock_config):
        service = StorageService(mock_config)
        mock_create.assert_called_once_with(
            mock_config.supabase_url,
            mock_config.supabase_key,
        )

    @patch("second_brain.services.storage.create_client")
    async def test_get_patterns(self, mock_create, mock_config):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.order.return_value = mock_table
        mock_table.execute.return_value = MagicMock(
            data=[{"name": "Test Pattern", "confidence": "HIGH"}]
        )
        mock_client.table.return_value = mock_table
        mock_create.return_value = mock_client

        service = StorageService(mock_config)
        patterns = await service.get_patterns()

        assert len(patterns) == 1
        assert patterns[0]["name"] == "Test Pattern"

    @patch("second_brain.services.storage.create_client")
    async def test_get_patterns_with_filters(self, mock_create, mock_config):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.order.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[])
        mock_client.table.return_value = mock_table
        mock_create.return_value = mock_client

        service = StorageService(mock_config)
        await service.get_patterns(topic="Messaging", confidence="HIGH")

        # eq() called twice: once for topic, once for confidence
        assert mock_table.eq.call_count == 2

    @patch("second_brain.services.storage.create_client")
    async def test_upsert_pattern(self, mock_create, mock_config):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.upsert.return_value = mock_table
        mock_table.execute.return_value = MagicMock(
            data=[{"id": "uuid-1", "name": "New Pattern"}]
        )
        mock_client.table.return_value = mock_table
        mock_create.return_value = mock_client

        service = StorageService(mock_config)
        result = await service.upsert_pattern({"name": "New Pattern", "pattern_text": "Do X"})

        assert result["name"] == "New Pattern"

    @patch("second_brain.services.storage.create_client")
    async def test_add_experience(self, mock_create, mock_config):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.insert.return_value = mock_table
        mock_table.execute.return_value = MagicMock(
            data=[{"id": "uuid-1", "name": "Test Experience"}]
        )
        mock_client.table.return_value = mock_table
        mock_create.return_value = mock_client

        service = StorageService(mock_config)
        result = await service.add_experience({"name": "Test Experience", "category": "content"})

        assert result["name"] == "Test Experience"

    @patch("second_brain.services.storage.create_client")
    async def test_get_health_history(self, mock_create, mock_config):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.order.return_value = mock_table
        mock_table.limit.return_value = mock_table
        mock_table.execute.return_value = MagicMock(
            data=[{"date": "2026-02-15", "total_patterns": 32}]
        )
        mock_client.table.return_value = mock_table
        mock_create.return_value = mock_client

        service = StorageService(mock_config)
        history = await service.get_health_history(limit=10)

        assert len(history) == 1
        assert history[0]["total_patterns"] == 32


class TestExamplesStorage:
    @patch("second_brain.services.storage.create_client")
    async def test_get_examples(self, mock_create, mock_config):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.order.return_value = mock_table
        mock_table.execute.return_value = MagicMock(
            data=[{"content_type": "linkedin", "title": "Hooks That Work", "content": "..."}]
        )
        mock_client.table.return_value = mock_table
        mock_create.return_value = mock_client

        service = StorageService(mock_config)
        examples = await service.get_examples()

        assert len(examples) == 1
        assert examples[0]["content_type"] == "linkedin"

    @patch("second_brain.services.storage.create_client")
    async def test_get_examples_with_filter(self, mock_create, mock_config):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.order.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[])
        mock_client.table.return_value = mock_table
        mock_create.return_value = mock_client

        service = StorageService(mock_config)
        await service.get_examples(content_type="email")

        mock_table.eq.assert_called_once_with("content_type", "email")

    @patch("second_brain.services.storage.create_client")
    async def test_upsert_example(self, mock_create, mock_config):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.upsert.return_value = mock_table
        mock_table.execute.return_value = MagicMock(
            data=[{"id": "uuid-1", "title": "LinkedIn Post"}]
        )
        mock_client.table.return_value = mock_table
        mock_create.return_value = mock_client

        service = StorageService(mock_config)
        result = await service.upsert_example({"title": "LinkedIn Post", "content": "..."})

        assert result["title"] == "LinkedIn Post"


class TestKnowledgeStorage:
    @patch("second_brain.services.storage.create_client")
    async def test_get_knowledge(self, mock_create, mock_config):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.order.return_value = mock_table
        mock_table.execute.return_value = MagicMock(
            data=[{"category": "frameworks", "title": "Value Ladder", "content": "..."}]
        )
        mock_client.table.return_value = mock_table
        mock_create.return_value = mock_client

        service = StorageService(mock_config)
        knowledge = await service.get_knowledge()

        assert len(knowledge) == 1
        assert knowledge[0]["category"] == "frameworks"

    @patch("second_brain.services.storage.create_client")
    async def test_get_knowledge_with_filter(self, mock_create, mock_config):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.order.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[])
        mock_client.table.return_value = mock_table
        mock_create.return_value = mock_client

        service = StorageService(mock_config)
        await service.get_knowledge(category="frameworks")

        mock_table.eq.assert_called_once_with("category", "frameworks")


class TestDeleteOperations:
    @patch("second_brain.services.storage.create_client")
    async def test_delete_pattern_success(self, mock_create, mock_config):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.delete.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[{"id": "uuid-1"}])
        mock_client.table.return_value = mock_table
        mock_create.return_value = mock_client

        service = StorageService(mock_config)
        result = await service.delete_pattern("uuid-1")

        assert result is True
        mock_client.table.assert_called_with("patterns")

    @patch("second_brain.services.storage.create_client")
    async def test_delete_pattern_not_found(self, mock_create, mock_config):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.delete.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[])
        mock_client.table.return_value = mock_table
        mock_create.return_value = mock_client

        service = StorageService(mock_config)
        result = await service.delete_pattern("nonexistent")

        assert result is False

    @patch("second_brain.services.storage.create_client")
    async def test_delete_experience_success(self, mock_create, mock_config):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.delete.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[{"id": "uuid-2"}])
        mock_client.table.return_value = mock_table
        mock_create.return_value = mock_client

        service = StorageService(mock_config)
        result = await service.delete_experience("uuid-2")

        assert result is True
        mock_client.table.assert_called_with("experiences")

    @patch("second_brain.services.storage.create_client")
    async def test_delete_experience_not_found(self, mock_create, mock_config):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.delete.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[])
        mock_client.table.return_value = mock_table
        mock_create.return_value = mock_client

        service = StorageService(mock_config)
        result = await service.delete_experience("nonexistent")

        assert result is False

    @patch("second_brain.services.storage.create_client")
    async def test_delete_example_success(self, mock_create, mock_config):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.delete.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[{"id": "uuid-3"}])
        mock_client.table.return_value = mock_table
        mock_create.return_value = mock_client

        service = StorageService(mock_config)
        result = await service.delete_example("uuid-3")

        assert result is True
        mock_client.table.assert_called_with("examples")

    @patch("second_brain.services.storage.create_client")
    async def test_delete_knowledge_success(self, mock_create, mock_config):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.delete.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[{"id": "uuid-4"}])
        mock_client.table.return_value = mock_table
        mock_create.return_value = mock_client

        service = StorageService(mock_config)
        result = await service.delete_knowledge("uuid-4")

        assert result is True
        mock_client.table.assert_called_with("knowledge_repo")


class TestHealthService:
    async def test_compute_health(self, mock_deps):
        from second_brain.services.health import HealthService

        mock_deps.storage_service.get_patterns = AsyncMock(return_value=[
            {"confidence": "HIGH", "topic": "content", "date_updated": "2026-02-15"},
            {"confidence": "MEDIUM", "topic": "messaging", "date_updated": "2026-02-14"},
            {"confidence": "LOW", "topic": "content", "date_updated": "2026-02-13"},
        ])
        mock_deps.storage_service.get_experiences = AsyncMock(return_value=[
            {"name": "test experience"}
        ])
        mock_deps.memory_service.get_memory_count = AsyncMock(return_value=42)
        mock_deps.config.graph_provider = "none"

        metrics = await HealthService().compute(mock_deps)

        assert metrics.total_patterns == 3
        assert metrics.high_confidence == 1
        assert metrics.medium_confidence == 1
        assert metrics.low_confidence == 1
        assert metrics.experience_count == 1
        assert metrics.memory_count == 42
        assert metrics.graph_provider == "none"
        assert metrics.latest_update == "2026-02-15"
        assert metrics.status == "BUILDING"
        assert metrics.topics == {"content": 2, "messaging": 1}

    async def test_compute_health_memory_unavailable(self, mock_deps):
        from second_brain.services.health import HealthService

        mock_deps.storage_service.get_patterns = AsyncMock(return_value=[])
        mock_deps.storage_service.get_experiences = AsyncMock(return_value=[])
        mock_deps.memory_service.get_memory_count = AsyncMock(
            side_effect=Exception("Mem0 unavailable")
        )
        mock_deps.config.graph_provider = "none"

        metrics = await HealthService().compute(mock_deps)

        assert metrics.memory_count == "unavailable"
        assert metrics.total_patterns == 0
        assert metrics.latest_update == "none"
        assert metrics.status == "BUILDING"

    async def test_compute_health_growing_status(self, mock_deps):
        from second_brain.services.health import HealthService

        mock_deps.storage_service.get_patterns = AsyncMock(return_value=[
            {"confidence": "HIGH", "topic": "content", "date_updated": "2026-02-15"}
            for _ in range(6)
        ])
        mock_deps.storage_service.get_experiences = AsyncMock(return_value=[])
        mock_deps.memory_service.get_memory_count = AsyncMock(return_value=10)
        mock_deps.config.graph_provider = "mem0"

        metrics = await HealthService().compute(mock_deps)

        assert metrics.status == "GROWING"
        assert metrics.total_patterns == 6
        assert metrics.graph_provider == "mem0"


class TestStorageReinforcement:
    @patch("second_brain.services.storage.create_client")
    async def test_get_pattern_by_name_exists(self, mock_create, mock_config):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.ilike.return_value = mock_table
        mock_table.limit.return_value = mock_table
        mock_table.execute.return_value = MagicMock(
            data=[{"id": "uuid-1", "name": "Short > Structured", "use_count": 3}]
        )
        mock_client.table.return_value = mock_table
        mock_create.return_value = mock_client

        service = StorageService(mock_config)
        result = await service.get_pattern_by_name("Short > Structured")

        assert result is not None
        assert result["name"] == "Short > Structured"
        mock_table.ilike.assert_called_once_with("name", "Short > Structured")

    @patch("second_brain.services.storage.create_client")
    async def test_get_pattern_by_name_not_found(self, mock_create, mock_config):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.ilike.return_value = mock_table
        mock_table.limit.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[])
        mock_client.table.return_value = mock_table
        mock_create.return_value = mock_client

        service = StorageService(mock_config)
        result = await service.get_pattern_by_name("Nonexistent Pattern")

        assert result is None

    @patch("second_brain.services.storage.create_client")
    async def test_reinforce_pattern_increments_use_count(self, mock_create, mock_config):
        mock_client = MagicMock()
        mock_table = MagicMock()
        # First call: select to fetch current pattern
        mock_select_result = MagicMock(
            data=[{"id": "uuid-1", "name": "Test", "use_count": 1,
                   "confidence": "LOW", "evidence": []}]
        )
        # Second call: update result
        mock_update_result = MagicMock(
            data=[{"id": "uuid-1", "name": "Test", "use_count": 2,
                   "confidence": "MEDIUM", "evidence": []}]
        )
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.limit.return_value = mock_table
        mock_table.update.return_value = mock_table
        mock_table.execute.side_effect = [mock_select_result, mock_update_result]
        mock_client.table.return_value = mock_table
        mock_create.return_value = mock_client

        service = StorageService(mock_config)
        result = await service.reinforce_pattern("uuid-1")

        assert result["use_count"] == 2
        assert result["confidence"] == "MEDIUM"
        mock_table.update.assert_called_once()
        update_args = mock_table.update.call_args[0][0]
        assert update_args["use_count"] == 2
        assert update_args["confidence"] == "MEDIUM"

    @patch("second_brain.services.storage.create_client")
    async def test_reinforce_pattern_upgrades_to_high(self, mock_create, mock_config):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_select_result = MagicMock(
            data=[{"id": "uuid-1", "name": "Test", "use_count": 4,
                   "confidence": "MEDIUM", "evidence": ["e1", "e2"]}]
        )
        mock_update_result = MagicMock(
            data=[{"id": "uuid-1", "name": "Test", "use_count": 5,
                   "confidence": "HIGH", "evidence": ["e1", "e2"]}]
        )
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.limit.return_value = mock_table
        mock_table.update.return_value = mock_table
        mock_table.execute.side_effect = [mock_select_result, mock_update_result]
        mock_client.table.return_value = mock_table
        mock_create.return_value = mock_client

        service = StorageService(mock_config)
        result = await service.reinforce_pattern("uuid-1")

        assert result["use_count"] == 5
        assert result["confidence"] == "HIGH"
        update_args = mock_table.update.call_args[0][0]
        assert update_args["confidence"] == "HIGH"

    @patch("second_brain.services.storage.create_client")
    async def test_reinforce_pattern_appends_evidence(self, mock_create, mock_config):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_select_result = MagicMock(
            data=[{"id": "uuid-1", "name": "Test", "use_count": 1,
                   "confidence": "LOW", "evidence": ["e1"]}]
        )
        mock_update_result = MagicMock(
            data=[{"id": "uuid-1", "name": "Test", "use_count": 2,
                   "confidence": "MEDIUM", "evidence": ["e1", "e2"]}]
        )
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.limit.return_value = mock_table
        mock_table.update.return_value = mock_table
        mock_table.execute.side_effect = [mock_select_result, mock_update_result]
        mock_client.table.return_value = mock_table
        mock_create.return_value = mock_client

        service = StorageService(mock_config)
        result = await service.reinforce_pattern("uuid-1", new_evidence=["e2"])

        assert result["evidence"] == ["e1", "e2"]
        update_args = mock_table.update.call_args[0][0]
        assert update_args["evidence"] == ["e1", "e2"]

    @patch("second_brain.services.storage.create_client")
    async def test_reinforce_pattern_not_found(self, mock_create, mock_config):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.limit.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[])
        mock_client.table.return_value = mock_table
        mock_create.return_value = mock_client

        service = StorageService(mock_config)
        with pytest.raises(ValueError, match="not found"):
            await service.reinforce_pattern("nonexistent-id")

    @patch("second_brain.services.storage.create_client")
    async def test_reinforce_pattern_update_fails(self, mock_create, mock_config):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_select = MagicMock(data=[{
            "id": "uuid-1", "name": "Test", "use_count": 1,
            "confidence": "LOW", "evidence": [],
        }])
        mock_update = MagicMock(data=[])
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.limit.return_value = mock_table
        mock_table.update.return_value = mock_table
        mock_table.execute.side_effect = [mock_select, mock_update]
        mock_client.table.return_value = mock_table
        mock_create.return_value = mock_client

        service = StorageService(mock_config)
        with pytest.raises(ValueError, match="Failed to update"):
            await service.reinforce_pattern("uuid-1")

    @patch("second_brain.services.storage.create_client")
    async def test_reinforce_pattern_null_evidence(self, mock_create, mock_config):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_select = MagicMock(data=[{
            "id": "uuid-1", "name": "Test", "use_count": 1,
            "confidence": "LOW", "evidence": None,
        }])
        mock_update = MagicMock(data=[{
            "id": "uuid-1", "use_count": 2, "confidence": "MEDIUM",
            "evidence": ["new"],
        }])
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.limit.return_value = mock_table
        mock_table.update.return_value = mock_table
        mock_table.execute.side_effect = [mock_select, mock_update]
        mock_client.table.return_value = mock_table
        mock_create.return_value = mock_client

        service = StorageService(mock_config)
        result = await service.reinforce_pattern("uuid-1", new_evidence=["new"])
        update_args = mock_table.update.call_args[0][0]
        assert update_args["evidence"] == ["new"]

    @patch("second_brain.services.storage.create_client")
    async def test_get_pattern_by_name_case_insensitive(self, mock_create, mock_config):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.ilike.return_value = mock_table
        mock_table.limit.return_value = mock_table
        mock_table.execute.return_value = MagicMock(
            data=[{"id": "uuid-1", "name": "Short > Structured"}]
        )
        mock_client.table.return_value = mock_table
        mock_create.return_value = mock_client

        service = StorageService(mock_config)
        result = await service.get_pattern_by_name("short > structured")

        assert result is not None
        mock_table.ilike.assert_called_once_with("name", "short > structured")

    @patch("second_brain.services.storage.create_client")
    async def test_insert_pattern(self, mock_create, mock_config):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.insert.return_value = mock_table
        mock_table.execute.return_value = MagicMock(
            data=[{"id": "uuid-new", "name": "New Pattern", "confidence": "LOW"}]
        )
        mock_client.table.return_value = mock_table
        mock_create.return_value = mock_client

        service = StorageService(mock_config)
        result = await service.insert_pattern({"name": "New Pattern", "confidence": "LOW"})

        assert result["id"] == "uuid-new"
        mock_table.insert.assert_called_once()


class TestGrowthLogStorage:
    @patch("second_brain.services.storage.create_client")
    async def test_add_growth_event(self, mock_create, mock_config):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.insert.return_value = mock_table
        mock_table.execute.return_value = MagicMock(
            data=[{"id": "uuid-1", "event_type": "pattern_created",
                   "pattern_name": "Test Pattern"}]
        )
        mock_client.table.return_value = mock_table
        mock_create.return_value = mock_client

        service = StorageService(mock_config)
        result = await service.add_growth_event({
            "event_type": "pattern_created",
            "pattern_name": "Test Pattern",
            "details": {"confidence": "LOW"},
        })

        assert result["event_type"] == "pattern_created"
        mock_client.table.assert_called_with("growth_log")

    @patch("second_brain.services.storage.create_client")
    async def test_get_growth_events(self, mock_create, mock_config):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.gte.return_value = mock_table
        mock_table.order.return_value = mock_table
        mock_table.execute.return_value = MagicMock(
            data=[
                {"event_type": "pattern_created", "event_date": "2026-02-15"},
                {"event_type": "pattern_reinforced", "event_date": "2026-02-14"},
            ]
        )
        mock_client.table.return_value = mock_table
        mock_create.return_value = mock_client

        service = StorageService(mock_config)
        events = await service.get_growth_events(days=7)

        assert len(events) == 2
        mock_table.gte.assert_called_once()

    @patch("second_brain.services.storage.create_client")
    async def test_get_growth_events_with_type_filter(self, mock_create, mock_config):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.gte.return_value = mock_table
        mock_table.order.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[])
        mock_client.table.return_value = mock_table
        mock_create.return_value = mock_client

        service = StorageService(mock_config)
        await service.get_growth_events(event_type="pattern_created", days=30)

        mock_table.eq.assert_called_once_with("event_type", "pattern_created")

    @patch("second_brain.services.storage.create_client")
    async def test_get_growth_event_counts(self, mock_create, mock_config):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.gte.return_value = mock_table
        mock_table.order.return_value = mock_table
        mock_table.execute.return_value = MagicMock(
            data=[
                {"event_type": "pattern_created"},
                {"event_type": "pattern_created"},
                {"event_type": "pattern_reinforced"},
            ]
        )
        mock_client.table.return_value = mock_table
        mock_create.return_value = mock_client

        service = StorageService(mock_config)
        counts = await service.get_growth_event_counts(days=30)

        assert counts == {"pattern_created": 2, "pattern_reinforced": 1}


class TestReviewHistoryStorage:
    @patch("second_brain.services.storage.create_client")
    async def test_add_review_history(self, mock_create, mock_config):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.insert.return_value = mock_table
        mock_table.execute.return_value = MagicMock(
            data=[{"id": "uuid-1", "overall_score": 8.5, "verdict": "READY TO SEND"}]
        )
        mock_client.table.return_value = mock_table
        mock_create.return_value = mock_client

        service = StorageService(mock_config)
        result = await service.add_review_history({
            "overall_score": 8.5,
            "verdict": "READY TO SEND",
            "content_type": "linkedin",
        })

        assert result["overall_score"] == 8.5
        mock_client.table.assert_called_with("review_history")

    @patch("second_brain.services.storage.create_client")
    async def test_get_review_history(self, mock_create, mock_config):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.order.return_value = mock_table
        mock_table.limit.return_value = mock_table
        mock_table.execute.return_value = MagicMock(
            data=[
                {"overall_score": 8.5, "review_date": "2026-02-15"},
                {"overall_score": 7.0, "review_date": "2026-02-14"},
            ]
        )
        mock_client.table.return_value = mock_table
        mock_create.return_value = mock_client

        service = StorageService(mock_config)
        history = await service.get_review_history(limit=10)

        assert len(history) == 2

    @patch("second_brain.services.storage.create_client")
    async def test_get_review_history_filtered(self, mock_create, mock_config):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.order.return_value = mock_table
        mock_table.limit.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[])
        mock_client.table.return_value = mock_table
        mock_create.return_value = mock_client

        service = StorageService(mock_config)
        await service.get_review_history(content_type="email")

        mock_table.eq.assert_called_once_with("content_type", "email")


class TestConfidenceHistoryStorage:
    @patch("second_brain.services.storage.create_client")
    async def test_add_confidence_transition(self, mock_create, mock_config):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.insert.return_value = mock_table
        mock_table.execute.return_value = MagicMock(
            data=[{"id": "uuid-1", "pattern_name": "Test",
                   "from_confidence": "LOW", "to_confidence": "MEDIUM"}]
        )
        mock_client.table.return_value = mock_table
        mock_create.return_value = mock_client

        service = StorageService(mock_config)
        result = await service.add_confidence_transition({
            "pattern_name": "Test",
            "from_confidence": "LOW",
            "to_confidence": "MEDIUM",
            "use_count": 2,
        })

        assert result["from_confidence"] == "LOW"
        assert result["to_confidence"] == "MEDIUM"
        mock_client.table.assert_called_with("confidence_history")

    @patch("second_brain.services.storage.create_client")
    async def test_get_confidence_history(self, mock_create, mock_config):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.order.return_value = mock_table
        mock_table.limit.return_value = mock_table
        mock_table.execute.return_value = MagicMock(
            data=[
                {"pattern_name": "A", "from_confidence": "LOW", "to_confidence": "MEDIUM"},
                {"pattern_name": "B", "from_confidence": "MEDIUM", "to_confidence": "HIGH"},
            ]
        )
        mock_client.table.return_value = mock_table
        mock_create.return_value = mock_client

        service = StorageService(mock_config)
        history = await service.get_confidence_history(limit=20)

        assert len(history) == 2

    @patch("second_brain.services.storage.create_client")
    async def test_get_confidence_history_by_pattern(self, mock_create, mock_config):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.order.return_value = mock_table
        mock_table.limit.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[])
        mock_client.table.return_value = mock_table
        mock_create.return_value = mock_client

        service = StorageService(mock_config)
        await service.get_confidence_history(pattern_name="Test Pattern")

        mock_table.eq.assert_called_once_with("pattern_name", "Test Pattern")


class TestEnhancedHealthService:
    async def test_compute_growth_includes_base_metrics(self, mock_deps):
        from second_brain.services.health import HealthService

        mock_deps.storage_service.get_patterns = AsyncMock(return_value=[
            {"confidence": "HIGH", "topic": "content", "date_updated": "2026-02-15"},
        ])
        mock_deps.storage_service.get_experiences = AsyncMock(return_value=[])
        mock_deps.memory_service.get_memory_count = AsyncMock(return_value=10)
        mock_deps.config.graph_provider = "none"
        mock_deps.storage_service.get_growth_event_counts = AsyncMock(
            return_value={"pattern_created": 3, "pattern_reinforced": 2}
        )
        mock_deps.storage_service.get_review_history = AsyncMock(return_value=[])

        metrics = await HealthService().compute_growth(mock_deps, days=30)

        assert metrics.total_patterns == 1
        assert metrics.patterns_created_period == 3
        assert metrics.patterns_reinforced_period == 2
        assert metrics.growth_events_total == 5

    async def test_compute_growth_review_trending(self, mock_deps):
        from second_brain.services.health import HealthService

        mock_deps.storage_service.get_patterns = AsyncMock(return_value=[])
        mock_deps.storage_service.get_experiences = AsyncMock(return_value=[])
        mock_deps.memory_service.get_memory_count = AsyncMock(return_value=0)
        mock_deps.config.graph_provider = "none"
        mock_deps.storage_service.get_growth_event_counts = AsyncMock(return_value={})
        mock_deps.storage_service.get_review_history = AsyncMock(return_value=[
            {"overall_score": 9.0, "review_date": "2026-02-15"},
            {"overall_score": 8.5, "review_date": "2026-02-14"},
            {"overall_score": 6.0, "review_date": "2026-02-10"},
            {"overall_score": 5.5, "review_date": "2026-02-09"},
        ])

        metrics = await HealthService().compute_growth(mock_deps, days=30)

        assert metrics.reviews_completed_period == 4
        assert metrics.avg_review_score > 0
        assert metrics.review_score_trend == "improving"

    async def test_compute_growth_stale_patterns(self, mock_deps):
        from second_brain.services.health import HealthService

        mock_deps.storage_service.get_patterns = AsyncMock(return_value=[
            {"name": "Old Pattern", "confidence": "LOW", "topic": "x",
             "date_updated": "2025-01-01"},
            {"name": "Recent Pattern", "confidence": "LOW", "topic": "x",
             "date_updated": "2026-02-15"},
            {"name": "Old HIGH", "confidence": "HIGH", "topic": "x",
             "date_updated": "2025-01-01"},
        ])
        mock_deps.storage_service.get_experiences = AsyncMock(return_value=[])
        mock_deps.memory_service.get_memory_count = AsyncMock(return_value=0)
        mock_deps.config.graph_provider = "none"
        mock_deps.storage_service.get_growth_event_counts = AsyncMock(return_value={})
        mock_deps.storage_service.get_review_history = AsyncMock(return_value=[])

        metrics = await HealthService().compute_growth(mock_deps, days=30)

        # Old Pattern is stale (old date, not HIGH), Old HIGH is excluded (HIGH confidence)
        assert "Old Pattern" in metrics.stale_patterns
        assert "Recent Pattern" not in metrics.stale_patterns
        assert "Old HIGH" not in metrics.stale_patterns

    async def test_compute_growth_handles_failures(self, mock_deps):
        from second_brain.services.health import HealthService

        mock_deps.storage_service.get_patterns = AsyncMock(return_value=[])
        mock_deps.storage_service.get_experiences = AsyncMock(return_value=[])
        mock_deps.memory_service.get_memory_count = AsyncMock(return_value=0)
        mock_deps.config.graph_provider = "none"
        mock_deps.storage_service.get_growth_event_counts = AsyncMock(
            side_effect=Exception("Table not found")
        )
        mock_deps.storage_service.get_review_history = AsyncMock(
            side_effect=Exception("Table not found")
        )

        # Should not raise — graceful degradation
        metrics = await HealthService().compute_growth(mock_deps, days=30)

        assert metrics.growth_events_total == 0
        assert metrics.reviews_completed_period == 0
