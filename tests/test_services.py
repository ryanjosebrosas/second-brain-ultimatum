"""Unit tests for MemoryService and StorageService."""

from unittest.mock import MagicMock, patch

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

        assert len(results) == 1
        assert results[0]["memory"] == "test pattern"

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

        assert len(results) == 2

    @patch("mem0.Memory")
    async def test_search_non_list_result(self, mock_memory_cls, mock_config):
        mock_client = MagicMock()
        mock_client.search.return_value = {"results": []}  # non-list
        mock_memory_cls.from_config.return_value = mock_client

        service = MemoryService(mock_config)
        results = await service.search("test")

        assert results == []

    @patch("mem0.Memory")
    async def test_get_all(self, mock_memory_cls, mock_config):
        mock_client = MagicMock()
        mock_client.get_all.return_value = [{"id": "1"}, {"id": "2"}]
        mock_memory_cls.from_config.return_value = mock_client

        service = MemoryService(mock_config)
        results = await service.get_all()

        assert len(results) == 2

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
