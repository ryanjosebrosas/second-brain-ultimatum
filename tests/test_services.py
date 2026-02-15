"""Unit tests for MemoryService, StorageService, and HealthService."""

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
        mock_table.eq.return_value = mock_table
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
        mock_table.eq.assert_called_once_with("name", "Short > Structured")

    @patch("second_brain.services.storage.create_client")
    async def test_get_pattern_by_name_not_found(self, mock_create, mock_config):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
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
