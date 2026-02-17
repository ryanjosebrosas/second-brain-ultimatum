"""Tests for project lifecycle storage operations."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from second_brain.services.storage import StorageService


class TestProjectCRUD:
    """Test project create/read/update/list operations."""

    @patch("second_brain.services.storage.create_client")
    async def test_create_project(self, mock_create, brain_config):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.insert.return_value = mock_table
        mock_table.execute.return_value = MagicMock(
            data=[{"id": "proj-1", "name": "Test", "lifecycle_stage": "planning"}]
        )
        mock_client.table.return_value = mock_table
        mock_create.return_value = mock_client

        service = StorageService(brain_config)
        result = await service.create_project({"name": "Test", "category": "content"})
        assert result.get("id") == "proj-1"
        mock_client.table.assert_called_with("projects")

    @patch("second_brain.services.storage.create_client")
    async def test_get_project(self, mock_create, brain_config):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(
            data=[{"id": "proj-1", "name": "Test", "project_artifacts": []}]
        )
        mock_client.table.return_value = mock_table
        mock_create.return_value = mock_client

        service = StorageService(brain_config)
        result = await service.get_project("proj-1")
        assert result is not None
        assert result["name"] == "Test"

    @patch("second_brain.services.storage.create_client")
    async def test_get_project_not_found(self, mock_create, brain_config):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[])
        mock_client.table.return_value = mock_table
        mock_create.return_value = mock_client

        service = StorageService(brain_config)
        result = await service.get_project("nonexistent")
        assert result is None

    @patch("second_brain.services.storage.create_client")
    async def test_list_projects_no_filter(self, mock_create, brain_config):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.order.return_value = mock_table
        mock_table.limit.return_value = mock_table
        mock_table.execute.return_value = MagicMock(
            data=[
                {"id": "p1", "name": "A", "lifecycle_stage": "planning"},
                {"id": "p2", "name": "B", "lifecycle_stage": "complete"},
            ]
        )
        mock_client.table.return_value = mock_table
        mock_create.return_value = mock_client

        service = StorageService(brain_config)
        result = await service.list_projects()
        assert len(result) == 2

    @patch("second_brain.services.storage.create_client")
    async def test_list_projects_with_stage_filter(self, mock_create, brain_config):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.order.return_value = mock_table
        mock_table.limit.return_value = mock_table
        mock_table.execute.return_value = MagicMock(
            data=[{"id": "p1", "name": "A", "lifecycle_stage": "planning"}]
        )
        mock_client.table.return_value = mock_table
        mock_create.return_value = mock_client

        service = StorageService(brain_config)
        result = await service.list_projects(lifecycle_stage="planning")
        assert len(result) == 1
        mock_table.eq.assert_called_once_with("lifecycle_stage", "planning")

    @patch("second_brain.services.storage.create_client")
    async def test_list_projects_with_category_filter(self, mock_create, brain_config):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.order.return_value = mock_table
        mock_table.limit.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[])
        mock_client.table.return_value = mock_table
        mock_create.return_value = mock_client

        service = StorageService(brain_config)
        await service.list_projects(category="content")
        mock_table.eq.assert_called_once_with("category", "content")

    @patch("second_brain.services.storage.create_client")
    async def test_update_project_stage(self, mock_create, brain_config):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.update.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(
            data=[{"id": "proj-1", "lifecycle_stage": "executing"}]
        )
        mock_client.table.return_value = mock_table
        mock_create.return_value = mock_client

        service = StorageService(brain_config)
        result = await service.update_project_stage("proj-1", "executing")
        assert result.get("lifecycle_stage") == "executing"

    @patch("second_brain.services.storage.create_client")
    async def test_update_project_stage_complete(self, mock_create, brain_config):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.update.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(
            data=[{"id": "proj-1", "lifecycle_stage": "complete"}]
        )
        mock_client.table.return_value = mock_table
        mock_create.return_value = mock_client

        service = StorageService(brain_config)
        result = await service.update_project_stage("proj-1", "complete")
        assert result.get("lifecycle_stage") == "complete"
        # Verify completed_at was included in update
        call_args = mock_table.update.call_args[0][0]
        assert "completed_at" in call_args

    @patch("second_brain.services.storage.create_client")
    async def test_create_project_failure_returns_empty(self, mock_create, brain_config):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.insert.return_value = mock_table
        mock_table.execute.side_effect = Exception("DB error")
        mock_client.table.return_value = mock_table
        mock_create.return_value = mock_client

        service = StorageService(brain_config)
        result = await service.create_project({"name": "Fail"})
        assert result == {}


class TestProjectArtifacts:
    """Test project artifact operations."""

    @patch("second_brain.services.storage.create_client")
    async def test_add_artifact(self, mock_create, brain_config):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.upsert.return_value = mock_table
        mock_table.execute.return_value = MagicMock(
            data=[{"id": "art-1", "artifact_type": "plan", "project_id": "proj-1"}]
        )
        mock_client.table.return_value = mock_table
        mock_create.return_value = mock_client

        service = StorageService(brain_config)
        result = await service.add_project_artifact({
            "project_id": "proj-1", "artifact_type": "plan", "content": "My plan"
        })
        assert result.get("artifact_type") == "plan"
        mock_client.table.assert_called_with("project_artifacts")

    @patch("second_brain.services.storage.create_client")
    async def test_get_project_artifacts(self, mock_create, brain_config):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.order.return_value = mock_table
        mock_table.execute.return_value = MagicMock(
            data=[
                {"artifact_type": "plan", "title": "Plan"},
                {"artifact_type": "output", "title": "Output"},
            ]
        )
        mock_client.table.return_value = mock_table
        mock_create.return_value = mock_client

        service = StorageService(brain_config)
        result = await service.get_project_artifacts("proj-1")
        assert len(result) == 2

    @patch("second_brain.services.storage.create_client")
    async def test_get_artifacts_empty(self, mock_create, brain_config):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.order.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[])
        mock_client.table.return_value = mock_table
        mock_create.return_value = mock_client

        service = StorageService(brain_config)
        result = await service.get_project_artifacts("proj-1")
        assert result == []

    @patch("second_brain.services.storage.create_client")
    async def test_add_artifact_failure_returns_empty(self, mock_create, brain_config):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.upsert.return_value = mock_table
        mock_table.execute.side_effect = Exception("DB error")
        mock_client.table.return_value = mock_table
        mock_create.return_value = mock_client

        service = StorageService(brain_config)
        result = await service.add_project_artifact({"project_id": "p1"})
        assert result == {}


class TestPatternRegistry:
    """Test pattern registry and failure tracking."""

    @patch("second_brain.services.storage.create_client")
    async def test_get_pattern_registry(self, mock_create, brain_config):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.order.return_value = mock_table
        mock_table.execute.return_value = MagicMock(
            data=[
                {"name": "Hook Pattern", "topic": "LinkedIn", "confidence": "HIGH",
                 "use_count": 5, "date_added": "2026-01-01", "date_updated": "2026-02-01"},
            ]
        )
        mock_client.table.return_value = mock_table
        mock_create.return_value = mock_client

        service = StorageService(brain_config)
        result = await service.get_pattern_registry()
        assert len(result) == 1
        assert result[0]["name"] == "Hook Pattern"

    @patch("second_brain.services.storage.create_client")
    async def test_update_pattern_failures_increment(self, mock_create, brain_config):
        mock_client = MagicMock()
        mock_table = MagicMock()
        # First call: select to get current failures
        select_result = MagicMock(data=[{"consecutive_failures": 1}])
        # Second call: update with incremented value
        update_result = MagicMock(data=[{"consecutive_failures": 2}])
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.update.return_value = mock_table
        # execute returns different results for select vs update
        mock_table.execute.side_effect = [select_result, update_result]
        mock_client.table.return_value = mock_table
        mock_create.return_value = mock_client

        service = StorageService(brain_config)
        result = await service.update_pattern_failures("pat-1")
        assert result.get("consecutive_failures") == 2

    @patch("second_brain.services.storage.create_client")
    async def test_update_pattern_failures_reset(self, mock_create, brain_config):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.update.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(
            data=[{"consecutive_failures": 0}]
        )
        mock_client.table.return_value = mock_table
        mock_create.return_value = mock_client

        service = StorageService(brain_config)
        result = await service.update_pattern_failures("pat-1", reset=True)
        assert result.get("consecutive_failures") == 0

    @patch("second_brain.services.storage.create_client")
    async def test_downgrade_pattern_confidence(self, mock_create, brain_config):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.update.return_value = mock_table
        # First call (select): returns HIGH pattern
        select_result = MagicMock(
            data=[{"name": "Test", "confidence": "HIGH", "consecutive_failures": 3}]
        )
        # Second call (update): returns downgraded pattern
        update_result = MagicMock(
            data=[{"name": "Test", "confidence": "MEDIUM", "consecutive_failures": 0}]
        )
        mock_table.execute.side_effect = [select_result, update_result]
        mock_client.table.return_value = mock_table
        mock_create.return_value = mock_client

        service = StorageService(brain_config)
        result = await service.downgrade_pattern_confidence("pat-1")
        assert result.get("confidence") == "MEDIUM"

    @patch("second_brain.services.storage.create_client")
    async def test_get_pattern_registry_empty(self, mock_create, brain_config):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.order.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[])
        mock_client.table.return_value = mock_table
        mock_create.return_value = mock_client

        service = StorageService(brain_config)
        result = await service.get_pattern_registry()
        assert result == []
