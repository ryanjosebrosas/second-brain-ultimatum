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


class TestProjectLifecycleMCP:
    """Tests for project/artifact MCP tools added in system-gap-remediation sub-plan 03."""

    @patch("second_brain.mcp_server._get_deps")
    async def test_update_project_name(self, mock_deps_fn):
        from second_brain.mcp_server import update_project
        from unittest.mock import AsyncMock, MagicMock
        mock_deps = MagicMock()
        mock_deps.storage_service.update_project = AsyncMock(
            return_value={"id": "proj-1", "name": "Renamed Project"}
        )
        mock_deps_fn.return_value = mock_deps
        result = await update_project(project_id="proj-1", name="Renamed Project")
        assert "Renamed Project" in result
        assert "name" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_update_project_not_found(self, mock_deps_fn):
        from second_brain.mcp_server import update_project
        from unittest.mock import AsyncMock, MagicMock
        mock_deps = MagicMock()
        mock_deps.storage_service.update_project = AsyncMock(return_value=None)
        mock_deps_fn.return_value = mock_deps
        result = await update_project(project_id="proj-999", description="X")
        assert "not found" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_update_project_empty_fields(self, mock_deps_fn):
        from second_brain.mcp_server import update_project
        from unittest.mock import MagicMock
        mock_deps_fn.return_value = MagicMock()
        result = await update_project(project_id="proj-1")
        assert "No fields" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_delete_project_success(self, mock_deps_fn):
        from second_brain.mcp_server import delete_project
        from unittest.mock import AsyncMock, MagicMock
        mock_deps = MagicMock()
        mock_deps.storage_service.get_project = AsyncMock(
            return_value={"id": "proj-1", "name": "Completed Campaign"}
        )
        mock_deps.storage_service.delete_project = AsyncMock(return_value=True)
        mock_deps_fn.return_value = mock_deps
        result = await delete_project(project_id="proj-1")
        assert "Deleted" in result
        assert "Completed Campaign" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_delete_project_not_found(self, mock_deps_fn):
        from second_brain.mcp_server import delete_project
        from unittest.mock import AsyncMock, MagicMock
        mock_deps = MagicMock()
        mock_deps.storage_service.get_project = AsyncMock(return_value=None)
        mock_deps_fn.return_value = mock_deps
        result = await delete_project(project_id="proj-none")
        assert "not found" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_add_artifact_plan_type(self, mock_deps_fn):
        from second_brain.mcp_server import add_artifact
        from unittest.mock import AsyncMock, MagicMock
        mock_deps = MagicMock()
        mock_deps.storage_service.add_project_artifact = AsyncMock(
            return_value={"id": "art-plan-1", "artifact_type": "plan"}
        )
        mock_deps_fn.return_value = mock_deps
        result = await add_artifact(
            project_id="proj-1", artifact_type="plan", title="Q1 Strategy"
        )
        assert "art-plan-1" in result
        assert "plan" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_add_artifact_invalid_type(self, mock_deps_fn):
        from second_brain.mcp_server import add_artifact
        from unittest.mock import MagicMock
        mock_deps_fn.return_value = MagicMock()
        result = await add_artifact(project_id="proj-1", artifact_type="invalid_type")
        assert "Invalid artifact_type" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_delete_artifact_success(self, mock_deps_fn):
        from second_brain.mcp_server import delete_artifact
        from unittest.mock import AsyncMock, MagicMock
        mock_deps = MagicMock()
        mock_deps.storage_service.delete_project_artifact = AsyncMock(return_value=True)
        mock_deps_fn.return_value = mock_deps
        result = await delete_artifact(artifact_id="art-1")
        assert "Deleted" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_delete_artifact_not_found(self, mock_deps_fn):
        from second_brain.mcp_server import delete_artifact
        from unittest.mock import AsyncMock, MagicMock
        mock_deps = MagicMock()
        mock_deps.storage_service.delete_project_artifact = AsyncMock(return_value=False)
        mock_deps_fn.return_value = mock_deps
        result = await delete_artifact(artifact_id="art-missing")
        assert "not found" in result.lower()

    @patch("second_brain.mcp_server._get_deps")
    async def test_list_projects_with_stage_filter_mcp(self, mock_deps_fn):
        from second_brain.mcp_server import list_projects
        from unittest.mock import AsyncMock, MagicMock
        mock_deps = MagicMock()
        mock_deps.storage_service.list_projects = AsyncMock(return_value=[
            {"id": "p1", "name": "Active", "lifecycle_stage": "executing"},
        ])
        mock_deps_fn.return_value = mock_deps
        result = await list_projects(lifecycle_stage="executing")
        assert "Active" in result
        assert "executing" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_list_projects_with_category_filter_mcp(self, mock_deps_fn):
        from second_brain.mcp_server import list_projects
        from unittest.mock import AsyncMock, MagicMock
        mock_deps = MagicMock()
        mock_deps.storage_service.list_projects = AsyncMock(return_value=[
            {"id": "p2", "name": "Newsletter", "lifecycle_stage": "planning",
             "category": "content"},
        ])
        mock_deps_fn.return_value = mock_deps
        result = await list_projects(category="content")
        assert "Newsletter" in result
        assert "content" in result

    @patch("second_brain.mcp_server._get_deps")
    async def test_list_projects_empty_with_filter(self, mock_deps_fn):
        from second_brain.mcp_server import list_projects
        from unittest.mock import AsyncMock, MagicMock
        mock_deps = MagicMock()
        mock_deps.storage_service.list_projects = AsyncMock(return_value=[])
        mock_deps_fn.return_value = mock_deps
        result = await list_projects(lifecycle_stage="done")
        assert "No projects found" in result
