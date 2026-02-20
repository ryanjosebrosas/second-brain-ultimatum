"""Memory, search, and ingestion endpoints."""

import asyncio
import logging

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile

from second_brain.deps import BrainDeps
from second_brain.api.deps import get_deps
from second_brain.api.schemas import (
    VectorSearchRequest,
    MultimodalSearchRequest,
    IngestExampleRequest,
    IngestKnowledgeRequest,
    ManageContentTypeRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Memory"])


@router.get("/search/examples")
async def search_examples(content_type: str | None = None, deps: BrainDeps = Depends(get_deps)):
    """Search content examples."""
    examples = await deps.storage_service.get_examples(content_type=content_type)
    return {"examples": examples, "count": len(examples)}


@router.get("/search/knowledge")
async def search_knowledge(category: str | None = None, deps: BrainDeps = Depends(get_deps)):
    """Search knowledge repository."""
    knowledge = await deps.storage_service.get_knowledge(category=category)
    return {"knowledge": knowledge, "count": len(knowledge)}


@router.get("/search/experiences")
async def search_experiences(
    category: str | None = None, limit: int = 20, deps: BrainDeps = Depends(get_deps),
):
    """List work experiences."""
    experiences = await deps.storage_service.get_experiences(category=category, limit=limit)
    return {"experiences": experiences, "count": len(experiences)}


@router.get("/search/patterns")
async def search_patterns(
    topic: str | None = None,
    confidence: str | None = None,
    keyword: str | None = None,
    limit: int = 30,
    deps: BrainDeps = Depends(get_deps),
):
    """Search patterns with optional filters."""
    patterns = await deps.storage_service.get_patterns(topic=topic, confidence=confidence)
    if keyword:
        kw = keyword.lower()
        patterns = [
            p for p in patterns
            if kw in p.get("name", "").lower() or kw in p.get("pattern_text", "").lower()
        ]
    return {"patterns": patterns[:limit], "count": len(patterns[:limit])}


@router.post("/search/vector")
async def vector_search(body: VectorSearchRequest, deps: BrainDeps = Depends(get_deps)):
    """Search using vector similarity (pgvector)."""
    if not deps.embedding_service:
        raise HTTPException(400, detail="Vector search unavailable: no embedding service configured")
    timeout = deps.config.api_timeout_seconds
    try:
        async with asyncio.timeout(timeout):
            embedding = await deps.embedding_service.embed_query(body.query)
            results = await deps.storage_service.vector_search(
                embedding=embedding, table=body.table, limit=body.limit,
            )
    except TimeoutError:
        raise HTTPException(504, detail=f"Vector search timed out after {timeout}s")
    return {"query": body.query, "results": results, "count": len(results)}


@router.post("/search/multimodal")
async def multimodal_search(body: MultimodalSearchRequest, deps: BrainDeps = Depends(get_deps)):
    """Search using multimodal vector similarity."""
    if not body.query.strip() and not body.image_url.strip():
        raise HTTPException(400, detail="Provide at least one of: query or image_url")
    if not deps.embedding_service:
        raise HTTPException(400, detail="Multimodal search unavailable: no embedding service configured")

    timeout = deps.config.api_timeout_seconds
    input_items: list = []
    if body.query.strip():
        input_items.append(body.query.strip())
    if body.image_url.strip():
        url = body.image_url.strip()
        if url.startswith("data:"):
            from PIL import Image as PILImage
            from io import BytesIO
            import base64 as b64
            b64_data = url.split(",", 1)[1] if "," in url else url
            input_items.append(PILImage.open(BytesIO(b64.b64decode(b64_data))))
        else:
            input_items.append(url)

    try:
        async with asyncio.timeout(timeout):
            embeddings = await deps.embedding_service.embed_multimodal([input_items], input_type="query")
            embedding = embeddings[0]
            results = await deps.storage_service.vector_search(
                embedding=embedding, table=body.table, limit=body.limit,
            )
    except TimeoutError:
        raise HTTPException(504, detail=f"Multimodal search timed out after {timeout}s")
    return {"results": results, "count": len(results)}


@router.post("/ingest/example")
async def ingest_example(body: IngestExampleRequest, deps: BrainDeps = Depends(get_deps)):
    """Add a content example to the example library."""
    example_data: dict = {
        "content_type": body.content_type,
        "title": body.title,
        "content": body.content,
    }
    if body.notes:
        example_data["notes"] = body.notes
    result = await deps.storage_service.upsert_example(example_data)
    if result:
        return {"message": f"Example added: {body.title}", "id": result.get("id", "unknown")}
    raise HTTPException(500, detail="Failed to ingest example")


@router.post("/ingest/knowledge")
async def ingest_knowledge(body: IngestKnowledgeRequest, deps: BrainDeps = Depends(get_deps)):
    """Add a knowledge entry to the knowledge repository."""
    knowledge_data: dict = {
        "category": body.category,
        "title": body.title,
        "content": body.content,
    }
    if body.tags:
        knowledge_data["tags"] = [t.strip() for t in body.tags.split(",") if t.strip()]
    result = await deps.storage_service.upsert_knowledge(knowledge_data)
    if result:
        return {"message": f"Knowledge added: {body.title}", "id": result.get("id", "unknown")}
    raise HTTPException(500, detail="Failed to ingest knowledge")


@router.post("/ingest/file")
async def ingest_file(
    file: UploadFile,
    context: str = Form(""),
    category: str = Form("general"),
    deps: BrainDeps = Depends(get_deps),
):
    """Upload and ingest a file (PDF, image, or text document)."""
    if not file.filename:
        raise HTTPException(400, detail="No file provided")

    content_bytes = await file.read()
    if len(content_bytes) > 20 * 1024 * 1024:  # 20 MB limit
        raise HTTPException(413, detail="File too large. Maximum 20 MB.")

    mime = file.content_type or ""
    filename = file.filename or "unknown"

    if mime.startswith("image/"):
        import base64

        b64 = base64.b64encode(content_bytes).decode("utf-8")
        data_uri = f"data:{mime};base64,{b64}"
        content_blocks = [{"type": "image_url", "image_url": {"url": data_uri}}]
        if context.strip():
            content_blocks.insert(0, {"type": "text", "text": context.strip()})
        mem_result = await deps.memory_service.add_multimodal(
            content_blocks,
            metadata={"category": category, "source": "file_upload", "filename": filename},
        )
        embed_status = "skipped"
        if deps.embedding_service:
            try:
                from PIL import Image as PILImage
                from io import BytesIO

                img = PILImage.open(BytesIO(content_bytes))
                input_items = [context.strip(), img] if context.strip() else [img]
                embeddings = await deps.embedding_service.embed_multimodal(
                    [input_items], input_type="document"
                )
                if embeddings and embeddings[0]:
                    await deps.storage_service.upsert_memory_content({
                        "category": category,
                        "title": filename,
                        "content": context.strip() or f"Image: {filename}",
                        "embedding": embeddings[0],
                    })
                    embed_status = f"stored ({len(embeddings[0])}d)"
            except Exception as e:
                logger.warning("Embedding generation failed: %s", type(e).__name__)
                embed_status = f"failed: {type(e).__name__}"
        return {
            "message": f"Image ingested: {filename}",
            "type": "image",
            "memory_stored": bool(mem_result),
            "embedding": embed_status,
        }

    elif mime == "application/pdf" or filename.lower().endswith(".pdf"):
        import base64

        b64 = base64.b64encode(content_bytes).decode("utf-8")
        data_uri = f"data:application/pdf;base64,{b64}"
        content_blocks = [{"type": "pdf_url", "pdf_url": {"url": data_uri}}]
        if context.strip():
            content_blocks.insert(0, {"type": "text", "text": context.strip()})
        mem_result = await deps.memory_service.add_multimodal(
            content_blocks,
            metadata={"category": category, "source": "file_upload", "filename": filename},
        )
        return {
            "message": f"PDF ingested: {filename}",
            "type": "pdf",
            "memory_stored": bool(mem_result),
        }

    elif mime.startswith("text/") or filename.lower().endswith((".txt", ".md", ".mdx")):
        text_content = content_bytes.decode("utf-8", errors="replace")
        if len(text_content) > 10000:
            text_content = text_content[:10000]
        mem_result = await deps.memory_service.add(
            text_content,
            metadata={"category": category, "source": "file_upload", "filename": filename},
        )
        return {
            "message": f"Text document ingested: {filename}",
            "type": "text",
            "memory_stored": bool(mem_result),
        }

    else:
        raise HTTPException(
            400,
            detail=f"Unsupported file type: {mime or filename}. "
            "Supported: images (jpg/png/webp/gif), PDF, text (txt/md).",
        )


@router.delete("/items/{table}/{item_id}")
async def delete_item(table: str, item_id: str, deps: BrainDeps = Depends(get_deps)):
    """Delete an item by table and ID."""
    methods = {
        "pattern": deps.storage_service.delete_pattern,
        "experience": deps.storage_service.delete_experience,
        "example": deps.storage_service.delete_example,
        "knowledge": deps.storage_service.delete_knowledge,
    }
    if table not in methods:
        raise HTTPException(400, detail=f"Invalid table '{table}'. Use: pattern, experience, example, knowledge")
    deleted = await methods[table](item_id)
    if deleted:
        return {"message": f"Deleted {table} with ID {item_id}"}
    raise HTTPException(404, detail=f"No {table} found with ID {item_id}")


@router.get("/content-types")
async def list_content_types(deps: BrainDeps = Depends(get_deps)):
    """List all available content types."""
    registry = deps.get_content_type_registry()
    all_types = await registry.get_all()
    types_list = [
        {
            "slug": slug,
            "name": config.name,
            "default_mode": config.default_mode,
            "max_words": config.max_words,
            "is_builtin": config.is_builtin,
            "structure_hint": config.structure_hint,
            "description": config.description,
            "writing_instructions": config.writing_instructions,
            "length_guidance": config.length_guidance,
            "ui_config": config.ui_config,
        }
        for slug, config in sorted(all_types.items())
    ] if all_types else []
    return {"content_types": types_list, "count": len(types_list)}


@router.post("/content-types")
async def manage_content_type(body: ManageContentTypeRequest, deps: BrainDeps = Depends(get_deps)):
    """Add or remove a content type."""
    registry = deps.get_content_type_registry()

    if body.action == "add":
        if not body.name or not body.structure_hint:
            raise HTTPException(400, detail="Both 'name' and 'structure_hint' are required for adding")
        row = {
            "slug": body.slug,
            "name": body.name,
            "default_mode": body.default_mode,
            "structure_hint": body.structure_hint,
            "example_type": body.slug,
            "max_words": body.max_words,
            "description": body.description,
            "is_builtin": False,
        }
        await deps.storage_service.upsert_content_type(row)
        registry.invalidate()
        return {"message": f"Added content type '{body.slug}' ({body.name})"}

    elif body.action == "remove":
        existing = await deps.storage_service.get_content_type_by_slug(body.slug)
        if not existing:
            raise HTTPException(404, detail=f"No content type found with slug '{body.slug}'")
        deleted = await deps.storage_service.delete_content_type(body.slug)
        if deleted:
            registry.invalidate()
            return {"message": f"Removed content type '{body.slug}'"}
        raise HTTPException(500, detail=f"Failed to remove '{body.slug}'")

    else:
        raise HTTPException(400, detail=f"Unknown action '{body.action}'. Use 'add' or 'remove'.")


@router.get("/pattern-registry")
async def pattern_registry(deps: BrainDeps = Depends(get_deps)):
    """View the full pattern registry."""
    registry = await deps.storage_service.get_pattern_registry()
    return {"patterns": registry, "count": len(registry)}
