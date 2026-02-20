"""Project lifecycle endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException

from second_brain.deps import BrainDeps
from second_brain.api.deps import get_deps
from second_brain.api.schemas import (
    CreateProjectRequest,
    UpdateProjectRequest,
    AdvanceProjectRequest,
    AddArtifactRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("/")
async def list_projects(
    lifecycle_stage: str | None = None,
    category: str | None = None,
    limit: int = 20,
    deps: BrainDeps = Depends(get_deps),
):
    """List projects with optional filters."""
    projects = await deps.storage_service.list_projects(
        lifecycle_stage=lifecycle_stage, category=category, limit=limit,
    )
    return {"projects": projects, "count": len(projects)}


@router.post("/")
async def create_project(body: CreateProjectRequest, deps: BrainDeps = Depends(get_deps)):
    """Create a new project."""
    project_data = {"name": body.name, "category": body.category, "lifecycle_stage": "planning"}
    if body.description:
        project_data["description"] = body.description
    result = await deps.storage_service.create_project(project_data)
    if result:
        return result
    raise HTTPException(500, detail="Failed to create project")


@router.get("/{project_id}")
async def get_project(project_id: str, deps: BrainDeps = Depends(get_deps)):
    """Get project details including artifacts."""
    proj = await deps.storage_service.get_project(project_id)
    if not proj:
        raise HTTPException(404, detail=f"Project not found: {project_id}")
    return proj


@router.patch("/{project_id}")
async def update_project(project_id: str, body: UpdateProjectRequest, deps: BrainDeps = Depends(get_deps)):
    """Update project metadata."""
    fields = {k: v for k, v in body.model_dump(exclude_none=True).items()}
    if not fields:
        raise HTTPException(400, detail="No fields to update")
    result = await deps.storage_service.update_project(project_id, fields)
    if not result:
        raise HTTPException(404, detail=f"Project not found: {project_id}")
    return result


@router.delete("/{project_id}")
async def delete_project(project_id: str, deps: BrainDeps = Depends(get_deps)):
    """Delete a project and all its artifacts."""
    proj = await deps.storage_service.get_project(project_id)
    if not proj:
        raise HTTPException(404, detail=f"Project not found: {project_id}")
    deleted = await deps.storage_service.delete_project(project_id)
    if deleted:
        return {"message": f"Deleted project: {proj.get('name', project_id)}"}
    raise HTTPException(500, detail="Failed to delete project")


@router.post("/{project_id}/advance")
async def advance_project(project_id: str, body: AdvanceProjectRequest, deps: BrainDeps = Depends(get_deps)):
    """Advance a project to the next lifecycle stage."""
    stage_order = ["planning", "executing", "reviewing", "learning", "complete"]
    proj = await deps.storage_service.get_project(project_id)
    if not proj:
        raise HTTPException(404, detail=f"Project not found: {project_id}")
    current = proj.get("lifecycle_stage", "planning")
    if body.target_stage:
        next_stage = body.target_stage
    else:
        try:
            idx = stage_order.index(current)
            next_stage = stage_order[idx + 1] if idx + 1 < len(stage_order) else current
        except ValueError:
            raise HTTPException(400, detail=f"Cannot auto-advance from stage: {current}")
    result = await deps.storage_service.update_project_stage(project_id, next_stage)
    if result:
        return {"message": f"Advanced: {current} -> {next_stage}", "project": result}
    raise HTTPException(500, detail="Failed to advance project")


@router.post("/{project_id}/artifacts")
async def add_artifact(project_id: str, body: AddArtifactRequest, deps: BrainDeps = Depends(get_deps)):
    """Add an artifact to a project."""
    valid_types = {"plan", "draft", "review", "output", "note"}
    if body.artifact_type not in valid_types:
        raise HTTPException(400, detail=f"Invalid artifact_type. Use: {', '.join(sorted(valid_types))}")
    artifact_data: dict = {"project_id": project_id, "artifact_type": body.artifact_type}
    if body.title:
        artifact_data["title"] = body.title
    if body.content:
        artifact_data["content"] = body.content
    result = await deps.storage_service.add_project_artifact(artifact_data)
    if result:
        return result
    raise HTTPException(500, detail="Failed to add artifact")


@router.delete("/artifacts/{artifact_id}")
async def delete_artifact(artifact_id: str, deps: BrainDeps = Depends(get_deps)):
    """Delete a project artifact."""
    deleted = await deps.storage_service.delete_project_artifact(artifact_id)
    if deleted:
        return {"message": f"Deleted artifact: {artifact_id}"}
    raise HTTPException(404, detail=f"Artifact not found: {artifact_id}")
