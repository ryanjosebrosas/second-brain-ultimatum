"""Template bank CRUD endpoints."""

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from second_brain.deps import BrainDeps
from second_brain.api.deps import get_deps, get_model
from second_brain.api.schemas import (
    CreateTemplateRequest,
    UpdateTemplateRequest,
    DeconstructRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/templates", tags=["Templates"])


@router.get("/")
async def list_templates(
    content_type: str | None = None,
    tag: str | None = None,
    deps: BrainDeps = Depends(get_deps),
) -> dict[str, Any]:
    """List templates with optional filters."""
    tags = [tag] if tag else None
    templates = await deps.storage_service.get_templates(
        content_type=content_type, tags=tags,
    )
    return {"templates": templates, "count": len(templates)}


@router.post("/")
async def create_template(
    body: CreateTemplateRequest, deps: BrainDeps = Depends(get_deps),
) -> dict[str, Any]:
    """Create a new template in the bank."""
    template_data = body.model_dump()
    result = await deps.storage_service.upsert_template(template_data)
    if result:
        return result
    raise HTTPException(500, detail="Failed to create template")


@router.post("/deconstruct")
async def deconstruct_content(
    body: DeconstructRequest,
    deps: BrainDeps = Depends(get_deps),
    model=Depends(get_model),
) -> dict[str, Any]:
    """AI-deconstruct content into a template blueprint."""
    from second_brain.agents.template_builder import template_builder_agent

    prompt = body.content
    if body.content_type:
        prompt = f"[Content type: {body.content_type}]\n\n{body.content}"
    timeout = deps.config.api_timeout_seconds
    try:
        async with asyncio.timeout(timeout):
            result = await template_builder_agent.run(prompt, deps=deps, model=model)
    except TimeoutError:
        raise HTTPException(504, detail=f"Deconstruction timed out after {timeout}s")
    return result.output.model_dump()


@router.get("/{template_id}")
async def get_template(template_id: str, deps: BrainDeps = Depends(get_deps)):
    """Get a single template by ID."""
    tmpl = await deps.storage_service.get_template(template_id)
    if not tmpl:
        raise HTTPException(404, detail=f"Template not found: {template_id}")
    return tmpl


@router.patch("/{template_id}")
async def update_template(
    template_id: str,
    body: UpdateTemplateRequest,
    deps: BrainDeps = Depends(get_deps),
):
    """Update an existing template."""
    fields = body.model_dump(exclude_none=True)
    if not fields:
        raise HTTPException(400, detail="No fields to update")
    fields["id"] = template_id
    result = await deps.storage_service.upsert_template(fields)
    if result:
        return result
    raise HTTPException(404, detail=f"Template not found: {template_id}")


@router.delete("/{template_id}")
async def delete_template(template_id: str, deps: BrainDeps = Depends(get_deps)):
    """Soft-delete a template."""
    deleted = await deps.storage_service.delete_template(template_id)
    if deleted:
        return {"message": f"Deleted template: {template_id}"}
    raise HTTPException(404, detail=f"Template not found: {template_id}")
