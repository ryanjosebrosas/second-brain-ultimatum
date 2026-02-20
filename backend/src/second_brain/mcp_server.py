"""MCP Server for AI Second Brain.

Exposes recall and ask agents as tools callable from Claude Code.
Run: python -m second_brain.mcp_server
"""

import asyncio
import logging
from typing import TYPE_CHECKING

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

if TYPE_CHECKING:
    from pydantic_ai.models import Model

from second_brain.deps import BrainDeps, create_deps
from second_brain.models import get_model
from second_brain.agents.recall import recall_agent
from second_brain.agents.ask import ask_agent
from second_brain.agents.learn import learn_agent
from second_brain.agents.create import create_agent
from second_brain.agents.review import run_full_review

logger = logging.getLogger(__name__)

MAX_INPUT_LENGTH = 10000  # Characters


def _validate_mcp_input(text: str, label: str = "input") -> str:
    """Validate MCP tool text input."""
    if not text or not text.strip():
        raise ValueError(f"{label} cannot be empty")
    if len(text) > MAX_INPUT_LENGTH:
        raise ValueError(
            f"{label} too long ({len(text)} chars, max {MAX_INPUT_LENGTH})"
        )
    return text.strip()


# Initialize server
server = FastMCP("Second Brain")


@server.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """Health check endpoint for Docker HEALTHCHECK and monitoring.

    Returns:
        200: Server is healthy and deps initialized (or not yet attempted)
        503: Dep initialization failed permanently (circuit breaker tripped)
    """
    if _deps_failed:
        return JSONResponse(
            {"status": "unhealthy", "service": "second-brain", "error": _deps_error},
            status_code=503,
        )
    return JSONResponse({
        "status": "healthy",
        "service": "second-brain",
        "initialized": _deps is not None,
    })


# Lazy-init deps (created on first tool call) with circuit breaker
_deps: BrainDeps | None = None
_model = None
_agent_models: dict = {}  # Per-agent model cache
_deps_failed: bool = False
_deps_error: str = ""


def _get_deps() -> BrainDeps:
    global _deps, _model, _deps_failed, _deps_error, _agent_models
    if _deps_failed:
        raise RuntimeError(
            f"Second Brain initialization failed: {_deps_error}. "
            "Restart the MCP server to retry."
        )
    if _deps is None:
        try:
            _deps = create_deps()
            _model = get_model(_deps.config)
            _agent_models = {}
        except Exception as e:
            _deps_failed = True
            _deps_error = str(e)
            logger.error("Failed to initialize deps: %s", e)
            raise RuntimeError(f"Second Brain initialization failed: {e}") from e
    return _deps


def init_deps() -> None:
    """Initialize BrainDeps eagerly, BEFORE server.run() starts the event loop.

    Mem0's MemoryClient constructor makes synchronous HTTP calls that deadlock
    when called inside FastMCP's async event loop. Initializing deps before
    the event loop starts avoids this entirely.

    See also: service_mcp.py:init_deps() for the same pattern.
    """
    global _deps, _model, _deps_failed, _deps_error, _agent_models
    if _deps is not None:
        return  # Already initialized
    try:
        _deps = create_deps()
        _model = get_model(_deps.config)
        _agent_models = {}
        logger.warning("Dependencies initialized successfully")
    except Exception as e:
        _deps_failed = True
        _deps_error = str(e)
        logger.error("Failed to initialize deps: %s", e)


def _get_model(agent_name: str | None = None) -> "Model | None":
    """Get model for a specific agent, or the global default.

    Caches per-agent models to avoid rebuilding on every tool call.
    """
    _get_deps()  # ensure initialized

    if agent_name is None:
        return _model

    if agent_name not in _agent_models:
        from second_brain.models import get_agent_model
        _agent_models[agent_name] = get_agent_model(agent_name, _deps.config)

    return _agent_models[agent_name]


@server.tool()
async def recall(query: str) -> str:
    """Search your Second Brain's memory for relevant context, patterns,
    and past experiences. Returns ranked results with sources.

    Args:
        query: What to search for (e.g., "content writing patterns",
               "enterprise objection handling", "past LinkedIn work")
    """
    try:
        query = _validate_mcp_input(query, label="query")
    except ValueError as e:
        return str(e)
    deps = _get_deps()
    model = _get_model("recall")
    timeout = deps.config.api_timeout_seconds
    try:
        async with asyncio.timeout(timeout):
            result = await recall_agent.run(
                f"Search memory for: {query}",
                deps=deps,
                model=model,
            )
    except TimeoutError:
        return f"Recall timed out after {timeout}s. Try a simpler query."
    output = result.output

    # Format as readable text for Claude Code
    parts = [f"# Recall: {output.query}\n"]
    if output.matches:
        parts.append("## Matches\n")
        for m in output.matches:
            parts.append(f"- [{m.relevance}] {m.content}")
            if m.source:
                parts.append(f"  Source: {m.source}")
    if output.patterns:
        parts.append("\n## Related Patterns\n")
        for p in output.patterns:
            parts.append(f"- {p}")
    if output.relations:
        parts.append("\n## Graph Relationships\n")
        for rel in output.relations:
            parts.append(f"- {rel.source} --[{rel.relationship}]--> {rel.target}")
    if output.summary:
        parts.append(f"\n## Summary\n{output.summary}")
    return "\n".join(parts)


@server.tool()
async def ask(question: str) -> str:
    """Ask your Second Brain a question. Gets instant help powered by
    accumulated knowledge: company context, customer insights, content
    patterns, style preferences, and past experiences.

    Args:
        question: Your question (e.g., "Help me write a follow-up email",
                  "What's our positioning for enterprise clients?")
    """
    try:
        question = _validate_mcp_input(question, label="question")
    except ValueError as e:
        return str(e)
    deps = _get_deps()
    model = _get_model("ask")
    timeout = deps.config.api_timeout_seconds
    try:
        async with asyncio.timeout(timeout):
            result = await ask_agent.run(
                question,
                deps=deps,
                model=model,
            )
    except TimeoutError:
        return f"Ask timed out after {timeout}s. Try a simpler question."
    output = result.output

    # Format as readable text for Claude Code
    parts = [output.answer]
    if output.context_used:
        parts.append(f"\n---\nContext used: {', '.join(output.context_used)}")
    if output.patterns_applied:
        parts.append(f"Patterns applied: {', '.join(output.patterns_applied)}")
    if output.relations:
        parts.append("\n## Graph Relationships\n")
        for rel in output.relations:
            parts.append(f"- {rel.source} --[{rel.relationship}]--> {rel.target}")
    if output.next_action:
        parts.append(f"\nSuggested next: {output.next_action}")
    return "\n".join(parts)


@server.tool()
async def learn(content: str, category: str = "general") -> str:
    """Extract patterns and learnings from a work session or experience.
    Feed raw text and the agent will identify patterns, insights, and
    store them in your Second Brain.

    Args:
        content: Raw text from a work session, conversation, or experience
                 to extract learnings from.
        category: Experience category - content, prospects, clients, or general.
    """
    try:
        content = _validate_mcp_input(content, label="content")
    except ValueError as e:
        return str(e)
    deps = _get_deps()
    model = _get_model("learn")
    timeout = deps.config.api_timeout_seconds
    try:
        async with asyncio.timeout(timeout):
            result = await learn_agent.run(
                f"Extract learnings from this work session (category: {category}):\n\n{content}",
                deps=deps,
                model=model,
            )
    except TimeoutError:
        return f"Learn timed out after {timeout}s. Try submitting less content."
    output = result.output

    parts = [f"# Learn: {output.input_summary}\n"]

    if output.patterns_extracted:
        parts.append("## Patterns Extracted\n")
        for p in output.patterns_extracted:
            marker = "(reinforced)" if p.is_reinforcement else "(new)"
            parts.append(f"- [{p.confidence}] {p.name} {marker}")
            parts.append(f"  {p.pattern_text[:120]}")

    if output.insights:
        parts.append("\n## Insights\n")
        for insight in output.insights:
            parts.append(f"- {insight}")

    parts.append(f"\n## Summary")
    parts.append(f"New: {output.patterns_new} | Reinforced: {output.patterns_reinforced}")
    parts.append(output.storage_summary)

    return "\n".join(parts)


# --- Multimodal Learning Tools ---


@server.tool()
async def learn_image(image_url: str, context: str = "", category: str = "visual") -> str:
    """Store an image in your Second Brain's memory.

    The image is processed by Mem0 to extract visual information and stored
    as a searchable memory. Optionally generates a multimodal vector embedding
    for Supabase similarity search.

    Args:
        image_url: Image URL (https://...) or base64 data URI
                   (data:image/jpeg;base64,...). Supports JPEG, PNG, WebP, GIF.
        context: Optional text description or context about the image.
        category: Memory category for filtering (default: visual).
    """
    if not image_url or not image_url.strip():
        return "image_url cannot be empty"

    deps = _get_deps()
    timeout = deps.config.api_timeout_seconds
    results = []

    # Build multimodal content blocks
    content_blocks: list[dict] = [
        {"type": "image_url", "image_url": {"url": image_url.strip()}},
    ]
    if context.strip():
        content_blocks.insert(0, {"type": "text", "text": context.strip()})

    metadata = {"category": category, "source": "learn_image", "content_type": "image"}

    # Store to Mem0
    try:
        async with asyncio.timeout(timeout):
            mem_result = await deps.memory_service.add_multimodal(
                content_blocks, metadata=metadata
            )
        if mem_result:
            results.append("Memory stored in Mem0")
        else:
            results.append("Mem0 storage returned empty result")
    except TimeoutError:
        results.append(f"Mem0 storage timed out after {timeout}s")
    except Exception as e:
        results.append(f"Mem0 storage failed: {type(e).__name__}")

    # Generate multimodal embedding for Supabase (if Voyage configured)
    if deps.embedding_service:
        try:
            if image_url.startswith("data:"):
                from PIL import Image as PILImage
                from io import BytesIO
                import base64 as b64

                b64_data = image_url.split(",", 1)[1] if "," in image_url else image_url
                img = PILImage.open(BytesIO(b64.b64decode(b64_data)))
            else:
                img = image_url  # Voyage multimodal accepts URL strings

            inputs = [[context.strip(), img]] if context.strip() else [[img]]
            async with asyncio.timeout(timeout):
                embeddings = await deps.embedding_service.embed_multimodal(
                    inputs, input_type="document"
                )
            if embeddings:
                results.append(f"Multimodal embedding generated ({len(embeddings[0])} dims)")
        except ValueError as e:
            results.append(f"Embedding skipped: {e}")
        except Exception as e:
            results.append(f"Embedding failed: {type(e).__name__}")

    source = "base64" if image_url.startswith("data:") else image_url[:80]
    parts = [f"# Learn Image\n"]
    parts.append(f"- **Source**: {source}")
    if context:
        parts.append(f"- **Context**: {context[:100]}")
    parts.append(f"- **Category**: {category}")
    parts.append(f"\n## Results")
    for r in results:
        parts.append(f"- {r}")
    return "\n".join(parts)


@server.tool()
async def learn_document(
    document_url: str, document_type: str = "pdf", context: str = "", category: str = "document"
) -> str:
    """Store a document (PDF, text, or MDX) in your Second Brain's memory.

    The document is processed by Mem0 to extract textual information and stored
    as searchable memory.

    Args:
        document_url: Document URL (https://...) or base64 string.
                      For PDFs: URL only. For text/MDX: URL or raw base64.
        document_type: Type of document: pdf, mdx, or txt (default: pdf).
        context: Optional text description or context about the document.
        category: Memory category for filtering (default: document).
    """
    if not document_url or not document_url.strip():
        return "document_url cannot be empty"

    valid_types = {"pdf", "mdx", "txt"}
    if document_type not in valid_types:
        return f"Invalid document_type '{document_type}'. Must be one of: {valid_types}"

    deps = _get_deps()
    timeout = deps.config.api_timeout_seconds

    # Map document_type to Mem0 content block type
    type_map = {"pdf": "pdf_url", "mdx": "mdx_url", "txt": "mdx_url"}
    block_type = type_map[document_type]

    content_blocks: list[dict] = [
        {"type": block_type, block_type: {"url": document_url.strip()}},
    ]
    if context.strip():
        content_blocks.insert(0, {"type": "text", "text": context.strip()})

    metadata = {
        "category": category,
        "source": "learn_document",
        "content_type": document_type,
    }

    # Store to Mem0
    results = []
    try:
        async with asyncio.timeout(timeout):
            mem_result = await deps.memory_service.add_multimodal(
                content_blocks, metadata=metadata
            )
        if mem_result:
            results.append("Document stored in Mem0")
        else:
            results.append("Mem0 storage returned empty result")
    except TimeoutError:
        results.append(f"Mem0 storage timed out after {timeout}s")
    except Exception as e:
        results.append(f"Mem0 storage failed: {type(e).__name__}")

    source = document_url[:80] if len(document_url) > 80 else document_url
    parts = [f"# Learn Document ({document_type.upper()})\n"]
    parts.append(f"- **Source**: {source}")
    if context:
        parts.append(f"- **Context**: {context[:100]}")
    parts.append(f"- **Category**: {category}")
    parts.append(f"\n## Results")
    for r in results:
        parts.append(f"- {r}")
    return "\n".join(parts)


@server.tool()
async def learn_video(video_url: str, context: str = "", category: str = "video") -> str:
    """Generate a vector embedding for a video and store it in your Second Brain.

    Note: Video embedding is stored in Supabase via Voyage AI only.
    Mem0 does not support video — only the vector embedding is generated.

    Args:
        video_url: Video URL (https://...) or local file path. MP4 format only.
        context: Optional text description of the video content.
        category: Memory category for filtering (default: video).
    """
    if not video_url or not video_url.strip():
        return "video_url cannot be empty"

    deps = _get_deps()

    if not deps.embedding_service:
        return "Video embedding unavailable: VOYAGE_API_KEY not configured."

    timeout = deps.config.api_timeout_seconds
    results = []

    # Store text context to Mem0 (if provided)
    if context.strip():
        try:
            metadata = {
                "category": category,
                "source": "learn_video",
                "content_type": "video",
                "video_url": video_url.strip()[:200],
            }
            async with asyncio.timeout(timeout):
                await deps.memory_service.add(context.strip(), metadata=metadata)
            results.append("Video context stored in Mem0 (text only)")
        except Exception as e:
            results.append(f"Mem0 context storage failed: {type(e).__name__}")

    # Generate multimodal embedding with Voyage
    try:
        if video_url.startswith(("http://", "https://")):
            inputs = (
                [[context.strip(), {"type": "video_url", "video_url": video_url.strip()}]]
                if context.strip()
                else [[{"type": "video_url", "video_url": video_url.strip()}]]
            )
        else:
            from voyageai.video_utils import Video

            video = Video.from_path(
                video_url.strip(), model=deps.config.voyage_embedding_model, optimize=False
            )
            inputs = [[context.strip(), video]] if context.strip() else [[video]]

        async with asyncio.timeout(timeout * 2):  # Video takes longer
            embeddings = await deps.embedding_service.embed_multimodal(
                inputs, input_type="document"
            )
        if embeddings:
            results.append(f"Video embedding generated ({len(embeddings[0])} dims)")
    except ValueError as e:
        results.append(f"Embedding skipped: {e}")
    except ImportError:
        results.append("Video support requires voyageai >= 0.3.6")
    except Exception as e:
        results.append(f"Video embedding failed: {type(e).__name__}")

    parts = [f"# Learn Video\n"]
    parts.append(f"- **Source**: {video_url[:80]}")
    if context:
        parts.append(f"- **Context**: {context[:100]}")
    parts.append(f"- **Category**: {category}")
    parts.append(f"\n## Results")
    for r in results:
        parts.append(f"- {r}")
    return "\n".join(parts)


@server.tool()
async def multimodal_vector_search(
    query: str = "",
    image_url: str = "",
    table: str = "memory_content",
    limit: int = 10,
) -> str:
    """Search your Second Brain using multimodal vector similarity.

    Combines text and/or image queries into a single embedding for
    cross-modal search (e.g., find text content related to an image).

    Args:
        query: Optional text search query.
        image_url: Optional image URL or base64 data URI to search with.
        table: Table to search: memory_content, patterns, examples, knowledge_repo.
        limit: Maximum results (default 10).
    """
    if not query.strip() and not image_url.strip():
        return "Provide at least one of: query (text) or image_url."

    deps = _get_deps()
    if not deps.embedding_service:
        return "Multimodal search unavailable: VOYAGE_API_KEY not configured."

    timeout = deps.config.api_timeout_seconds

    # Build multimodal input
    input_items: list = []
    if query.strip():
        input_items.append(query.strip())
    if image_url.strip():
        url = image_url.strip()
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
            embeddings = await deps.embedding_service.embed_multimodal(
                [input_items], input_type="query"
            )
            embedding = embeddings[0]
            results = await deps.storage_service.vector_search(
                embedding=embedding,
                table=table,
                limit=limit,
            )
    except TimeoutError:
        return f"Multimodal search timed out after {timeout}s."
    except ValueError as e:
        return str(e)

    if not results:
        return f"No multimodal matches found in '{table}'."

    formatted = [f"# Multimodal Search\n"]
    if query:
        formatted.append(f"**Text query**: {query}")
    if image_url:
        src = "base64" if image_url.startswith("data:") else image_url[:60]
        formatted.append(f"**Image query**: {src}")
    formatted.append("")
    for r in results:
        sim = r.get("similarity", 0)
        title = r.get("title", "Untitled")
        content = r.get("content", "")[:200]
        formatted.append(f"- [{sim:.3f}] **{title}**: {content}")
    return "\n".join(formatted)


@server.tool()
async def create_content(
    prompt: str, content_type: str = "linkedin",
) -> str:
    """Draft content in your voice using brain knowledge.
    The agent pre-loads your voice guide, relevant examples, and applicable patterns,
    then produces a draft for human editing.

    Args:
        prompt: What to write about — e.g., "Announce our new AI automation product"
        content_type: Content type — linkedin, email, landing-page, comment,
                      case-study, proposal, one-pager, presentation, instagram,
                      or any custom type you've added.
    """
    try:
        prompt = _validate_mcp_input(prompt, label="prompt")
    except ValueError as e:
        return str(e)
    deps = _get_deps()
    model = _get_model("create")
    registry = deps.get_content_type_registry()

    type_config = await registry.get(content_type)
    if not type_config:
        available = await registry.slugs()
        return f"Unknown content type '{content_type}'. Available: {', '.join(available)}"

    # Pre-load voice guide
    voice_sections = []
    try:
        voice_content = await deps.storage_service.get_memory_content("style-voice")
        if voice_content:
            for item in voice_content:
                title = item.get("title", "Untitled")
                text = item.get("content", "")[:deps.config.content_preview_limit]
                voice_sections.append(f"### {title}\n{text}")
    except Exception:
        logger.debug("Failed to pre-load voice guide for create_content")

    # Pre-load content examples
    example_sections = []
    try:
        examples = await deps.storage_service.get_examples(content_type=content_type)
        if examples:
            limit = deps.config.experience_limit
            for ex in examples[:limit]:
                title = ex.get("title", "Untitled")
                text = ex.get("content", "")[:deps.config.content_preview_limit]
                example_sections.append(f"### {title}\n{text}")
    except Exception:
        logger.debug("Failed to pre-load examples for create_content")

    # Build enhanced prompt
    enhanced_parts = [
        f"Content type: {type_config.name} ({content_type})",
        f"Structure: {type_config.structure_hint}",
    ]

    # Length guidance (flexible, not rigid)
    if type_config.length_guidance:
        enhanced_parts.append(f"Length: {type_config.length_guidance}")
    elif type_config.max_words:
        enhanced_parts.append(
            f"Typical length: around {type_config.max_words} words, "
            "but adjust to fit the content"
        )

    # Voice guide
    if voice_sections:
        enhanced_parts.append(
            "\n## Your Voice & Tone Guide\n" + "\n\n".join(voice_sections)
        )
    else:
        enhanced_parts.append(
            "\nNo voice guide stored yet. Write in a clear, direct, conversational tone. "
            "Avoid corporate speak and AI-sounding phrases."
        )

    # Content examples
    if example_sections:
        enhanced_parts.append(
            f"\n## Reference Examples ({content_type})\nStudy these examples of your past "
            f"{type_config.name} content — match the style, structure, and voice:\n"
            + "\n\n".join(example_sections)
        )

    # The actual request
    enhanced_parts.append(f"\n## Request\n{prompt}")

    enhanced = "\n".join(enhanced_parts)

    timeout = deps.config.api_timeout_seconds
    try:
        async with asyncio.timeout(timeout):
            result = await create_agent.run(enhanced, deps=deps, model=model)
    except TimeoutError:
        return f"Create timed out after {timeout}s. Try a simpler prompt."
    output = result.output

    parts = [
        f"# Draft: {output.content_type}\n",
        output.draft,
        f"\n---",
        f"**Words**: {output.word_count}",
    ]
    if output.voice_elements:
        parts.append(f"**Voice**: {', '.join(output.voice_elements)}")
    if output.patterns_applied:
        parts.append(f"**Patterns**: {', '.join(output.patterns_applied)}")
    if output.examples_referenced:
        parts.append(f"**Examples**: {', '.join(output.examples_referenced)}")
    if output.notes:
        parts.append(f"\n**Editor notes**: {output.notes}")

    return "\n".join(parts)


@server.tool()
async def review_content(content: str, content_type: str | None = None) -> str:
    """Review content quality with adaptive dimension scoring. Returns a structured
    scorecard with per-dimension scores, overall score, and verdict.
    When content_type is provided, review dimensions are adapted to that type
    (e.g., a comment skips 'Data Accuracy', a case study weights it heavily).

    Args:
        content: The content to review (draft text, email, post, etc.)
        content_type: Optional content type for adaptive dimension scoring
                     (linkedin, email, etc.)
    """
    try:
        content = _validate_mcp_input(content, label="content")
    except ValueError as e:
        return str(e)
    deps = _get_deps()
    model = _get_model("review")
    timeout = deps.config.api_timeout_seconds * deps.config.mcp_review_timeout_multiplier
    try:
        async with asyncio.timeout(timeout):
            result = await run_full_review(content, deps, model, content_type)
    except TimeoutError:
        return f"Review timed out after {timeout}s. Try shorter content."

    parts = [f"# Review: {result.overall_score}/10 — {result.verdict}\n"]

    if result.summary:
        parts.append(result.summary)

    parts.append("\n| Dimension | Score | Status |")
    parts.append("|-----------|-------|--------|")
    for s in result.scores:
        parts.append(f"| {s.dimension} | {s.score}/10 | {s.status} |")

    if result.top_strengths:
        parts.append("\n## Strengths")
        for strength in result.top_strengths:
            parts.append(f"- {strength}")

    if result.critical_issues:
        parts.append("\n## Issues (Must Fix)")
        for issue in result.critical_issues:
            parts.append(f"- {issue}")

    if result.next_steps:
        parts.append("\n## Next Steps")
        for step in result.next_steps:
            parts.append(f"- {step}")

    return "\n".join(parts)


@server.tool()
async def search_examples(content_type: str | None = None) -> str:
    """Search your Second Brain's content examples — real samples of
    emails, LinkedIn posts, case studies, presentations, and more.

    Args:
        content_type: Filter by type (linkedin, email, case-study, etc.)
                      or None for all examples.
    """
    deps = _get_deps()
    examples = await deps.storage_service.get_examples(content_type=content_type)
    if not examples:
        return "No content examples found. Add examples to memory/examples/ and run migrate."
    parts = ["# Content Examples\n"]
    for e in examples:
        parts.append(f"## [{e['content_type']}] {e['title']}")
        parts.append(e.get("content", "")[:500])
        parts.append("")
    return "\n".join(parts)


@server.tool()
async def search_knowledge(category: str | None = None) -> str:
    """Search your Second Brain's knowledge repository — frameworks,
    methodologies, playbooks, research, and tools.

    Args:
        category: Filter by category (framework, methodology, playbook,
                  research, tool) or None for all.
    """
    deps = _get_deps()
    knowledge = await deps.storage_service.get_knowledge(category=category)
    if not knowledge:
        return "No knowledge entries found. Add content to memory/knowledge-repo/ and run migrate."
    parts = ["# Knowledge Repository\n"]
    for k in knowledge:
        parts.append(f"## [{k['category']}] {k['title']}")
        parts.append(k.get("content", "")[:500])
        parts.append("")
    return "\n".join(parts)


@server.tool()
async def delete_item(table: str, item_id: str) -> str:
    """Delete an item from your Second Brain by table and ID.

    Args:
        table: Which table to delete from (pattern, experience, example, knowledge)
        item_id: The UUID of the item to delete
    """
    try:
        item_id = _validate_mcp_input(item_id, label="item_id")
    except ValueError as e:
        return str(e)
    deps = _get_deps()
    methods = {
        "pattern": deps.storage_service.delete_pattern,
        "experience": deps.storage_service.delete_experience,
        "example": deps.storage_service.delete_example,
        "knowledge": deps.storage_service.delete_knowledge,
    }
    if table not in methods:
        return f"Invalid table '{table}'. Use: pattern, experience, example, knowledge"
    deleted = await methods[table](item_id)
    if deleted:
        return f"Deleted {table} with ID {item_id}"
    return f"No {table} found with ID {item_id}"


@server.tool()
async def brain_health() -> str:
    """Check the health and growth metrics of your Second Brain."""
    from second_brain.services.health import HealthService

    deps = _get_deps()
    metrics = await HealthService().compute(deps)

    parts = [
        "# Brain Health\n",
        f"Memories: {metrics.memory_count}",
        f"Patterns: {metrics.total_patterns} (HIGH: {metrics.high_confidence}, MEDIUM: {metrics.medium_confidence}, LOW: {metrics.low_confidence})",
        f"Experiences: {metrics.experience_count}",
        f"Graph: {metrics.graph_provider}",
        f"Last updated: {metrics.latest_update}",
    ]
    if metrics.graphiti_status != "disabled":
        parts.append(f"Graphiti: {metrics.graphiti_status} (backend: {metrics.graphiti_backend})")
    if metrics.topics:
        parts.append("\n## Patterns by Topic")
        for t, c in sorted(metrics.topics.items()):
            parts.append(f"  - {t}: {c}")
    parts.append(f"\nStatus: {metrics.status}")
    return "\n".join(parts)


@server.tool()
async def graph_search(query: str, limit: int = 10) -> str:
    """Search the Graphiti knowledge graph for entity relationships.
    Returns connections between people, concepts, patterns, and experiences
    discovered through graph traversal.

    Args:
        query: What to search for in the knowledge graph
        limit: Maximum number of relationships to return (default: 10)
    """
    deps = _get_deps()
    if not deps.graphiti_service:
        return "Graphiti is not enabled. Set GRAPHITI_ENABLED=true in your .env file."

    results = await deps.graphiti_service.search(query, limit=limit)
    if not results:
        return f"No graph relationships found for: {query}"

    parts = [f"# Graph Search: {query}\n"]
    for rel in results:
        src = rel.get("source", "?")
        relationship = rel.get("relationship", "?")
        tgt = rel.get("target", "?")
        parts.append(f"- {src} --[{relationship}]--> {tgt}")
    parts.append(f"\nFound {len(results)} relationship(s)")
    return "\n".join(parts)


@server.tool()
async def graph_health() -> str:
    """Check the health and connectivity of the Graphiti knowledge graph backend.
    Returns status, backend type, and any errors.
    """
    deps = _get_deps()
    if not deps.graphiti_service:
        return "Graphiti is not enabled. Set GRAPHITI_ENABLED=true in your .env file."

    health = await deps.graphiti_service.health_check()
    parts = [
        "# Graph Health\n",
        f"Status: {health.get('status', 'unknown')}",
        f"Backend: {health.get('backend', 'none')}",
    ]
    if health.get("error"):
        parts.append(f"Error: {health['error']}")
    return "\n".join(parts)


@server.tool()
async def consolidate_brain(min_cluster_size: int = 3) -> str:
    """Consolidate accumulated memories into patterns. Reviews recent Mem0
    memories, identifies recurring themes, and promotes them to structured
    patterns in the pattern registry.

    Args:
        min_cluster_size: Minimum memories needed to form a pattern cluster (default: 3)
    """
    deps = _get_deps()
    model = _get_model("learn")
    timeout = deps.config.api_timeout_seconds
    try:
        async with asyncio.timeout(timeout):
            result = await learn_agent.run(
                f"Run memory consolidation with min_cluster_size={min_cluster_size}. "
                f"Use the consolidate_memories tool to review accumulated memories, "
                f"then use store_pattern and reinforce_existing_pattern to act on findings. "
                f"Tag graduated memories with tag_graduated_memories when done.",
                deps=deps,
                model=model,
            )
    except TimeoutError:
        return f"Consolidation timed out after {timeout}s. Try again later."
    output = result.output

    parts = [f"# Brain Consolidation\n", f"**Summary**: {output.input_summary}\n"]

    if output.patterns_extracted:
        parts.append("## Patterns Identified\n")
        for p in output.patterns_extracted:
            marker = "(reinforced)" if p.is_reinforcement else "(new)"
            parts.append(f"- [{p.confidence}] {p.name} {marker}")

    parts.append(
        f"\n**Results**: {output.patterns_new} new, "
        f"{output.patterns_reinforced} reinforced"
    )

    return "\n".join(parts)


@server.tool()
async def growth_report(days: int = 30) -> str:
    """Get a growth report for your Second Brain showing pattern creation,
    reinforcement, confidence upgrades, and review score trends.

    Args:
        days: Number of days to include in the report (default: 30)
    """
    from second_brain.services.health import HealthService

    deps = _get_deps()
    health = HealthService()
    metrics = await health.compute_growth(deps, days=days)

    parts = [
        f"# Growth Report ({days} days)\n",
        f"## Brain Status: {metrics.status}\n",
        f"Memories: {metrics.memory_count}",
        f"Patterns: {metrics.total_patterns} (HIGH: {metrics.high_confidence}, "
        f"MEDIUM: {metrics.medium_confidence}, LOW: {metrics.low_confidence})",
        f"Experiences: {metrics.experience_count}",
        f"\n## Growth Activity\n",
        f"Events total: {metrics.growth_events_total}",
        f"Patterns created: {metrics.patterns_created_period}",
        f"Patterns reinforced: {metrics.patterns_reinforced_period}",
        f"Confidence upgrades: {metrics.confidence_upgrades_period}",
    ]

    if metrics.reviews_completed_period > 0:
        parts.append(f"\n## Quality Metrics\n")
        parts.append(f"Reviews completed: {metrics.reviews_completed_period}")
        parts.append(f"Average score: {metrics.avg_review_score}/10")
        parts.append(f"Trend: {metrics.review_score_trend}")

    if metrics.stale_patterns:
        parts.append(f"\n## Stale Patterns (no activity in 30+ days)\n")
        for name in metrics.stale_patterns:
            parts.append(f"- {name}")

    if metrics.topics:
        parts.append(f"\n## Patterns by Topic")
        for t, c in sorted(metrics.topics.items()):
            parts.append(f"  - {t}: {c}")

    # Milestones
    try:
        milestone_data = await health.compute_milestones(deps)
        parts.append(f"\nBrain Level: {milestone_data['level']}")
        parts.append(f"  {milestone_data['level_description']}")
        parts.append(f"  Milestones: {milestone_data['milestones_completed']}/{milestone_data['milestones_total']}")
        if milestone_data.get("next_milestone"):
            parts.append(f"  Next: {milestone_data['next_milestone']}")
    except Exception:
        logger.debug("Milestone computation failed (non-critical)")

    # Quality trending
    try:
        quality = await health.compute_quality_trend(deps, days=days)
        if quality.get("total_reviews", 0) > 0:
            parts.append(f"\nQuality ({days}d): {quality['total_reviews']} reviews, avg {quality['avg_score']}, trend: {quality['score_trend']}")
            if quality.get("recurring_issues"):
                parts.append(f"  Recurring issues: {', '.join(quality['recurring_issues'][:3])}")
    except Exception:
        logger.debug("Quality trending failed (non-critical)")

    return "\n".join(parts)


@server.tool()
async def list_content_types() -> str:
    """List all available content types in the Second Brain.
    Shows built-in and custom types with their configuration."""
    deps = _get_deps()
    registry = deps.get_content_type_registry()
    all_types = await registry.get_all()
    if not all_types:
        return "No content types available."

    parts = ["# Content Types\n"]
    parts.append("| Slug | Name | Mode | Words | Built-in |")
    parts.append("|------|------|------|-------|----------|")
    for slug, config in sorted(all_types.items()):
        builtin = "yes" if config.is_builtin else "no"
        parts.append(f"| {slug} | {config.name} | {config.default_mode} | {config.max_words} | {builtin} |")

    return "\n".join(parts)


@server.tool()
async def manage_content_type(
    action: str,
    slug: str,
    name: str = "",
    default_mode: str = "professional",
    structure_hint: str = "",
    max_words: int = 500,
    description: str = "",
) -> str:
    """Add or remove a content type from the Second Brain.

    Args:
        action: 'add' to create/update a content type, 'remove' to delete it
        slug: Content type slug in kebab-case (e.g., 'newsletter', 'blog-post')
        name: Human-readable name (required for 'add')
        default_mode: Communication mode — casual, professional, or formal
        structure_hint: Composition guide (required for 'add', e.g., 'Hook -> Body -> CTA')
        max_words: Target word count (default 500)
        description: Brief description of the content type
    """
    try:
        slug = _validate_mcp_input(slug, label="slug")
    except ValueError as e:
        return str(e)
    deps = _get_deps()
    registry = deps.get_content_type_registry()

    if action == "add":
        if not name or not structure_hint:
            return "Both 'name' and 'structure_hint' are required for adding a content type."
        row = {
            "slug": slug,
            "name": name,
            "default_mode": default_mode,
            "structure_hint": structure_hint,
            "example_type": slug,
            "max_words": max_words,
            "description": description,
            "is_builtin": False,
        }
        await deps.storage_service.upsert_content_type(row)
        registry.invalidate()
        return f"Added content type '{slug}' ({name})"

    elif action == "remove":
        existing = await deps.storage_service.get_content_type_by_slug(slug)
        if not existing:
            return f"No content type found with slug '{slug}'"
        deleted = await deps.storage_service.delete_content_type(slug)
        if deleted:
            registry.invalidate()
            return f"Removed content type '{slug}'"
        return f"Failed to remove '{slug}'"

    else:
        return f"Unknown action '{action}'. Use 'add' or 'remove'."


@server.tool()
async def vector_search(
    query: str,
    table: str = "memory_content",
    limit: int = 10,
) -> str:
    """Search your Second Brain using vector similarity (pgvector).

    Generates an embedding for the query and finds the most similar content
    in the specified table. Complements semantic search (recall) with
    pure vector similarity matching.

    Args:
        query: Text to search for (generates embedding automatically)
        table: Table to search: memory_content, patterns, examples, knowledge_repo
        limit: Maximum results (default 10)
    """
    try:
        query = _validate_mcp_input(query, label="query")
    except ValueError as e:
        return str(e)

    deps = _get_deps()

    if not deps.embedding_service:
        return "Vector search unavailable: VOYAGE_API_KEY or OPENAI_API_KEY not configured."

    try:
        timeout = deps.config.api_timeout_seconds
        async with asyncio.timeout(timeout):
            embedding = await deps.embedding_service.embed_query(query)
            results = await deps.storage_service.vector_search(
                embedding=embedding,
                table=table,
                limit=limit,
            )
    except TimeoutError:
        return f"Vector search timed out after {timeout}s."
    except ValueError as e:
        return str(e)

    if not results:
        return f"No vector matches found in '{table}'."

    formatted = [f"# Vector Search: {query}\n"]
    for r in results:
        sim = r.get("similarity", 0)
        title = r.get("title", "Untitled")
        content = r.get("content", "")[:200]
        formatted.append(f"- [{sim:.3f}] **{title}**: {content}")
    return "\n".join(formatted)


# --- Project Lifecycle ---

@server.tool()
async def create_project(
    name: str,
    category: str = "content",
    description: str | None = None,
) -> str:
    """Create a new project for lifecycle tracking (plan -> execute -> review -> learn).
    Categories: content, prospects, clients, products, general."""
    try:
        name = _validate_mcp_input(name, label="name")
    except ValueError as e:
        return str(e)
    deps = _get_deps()
    try:
        project_data = {"name": name, "category": category, "lifecycle_stage": "planning"}
        if description:
            project_data["description"] = description
        result = await deps.storage_service.create_project(project_data)
        if result:
            return (
                f"Project created: {result.get('name', name)} "
                f"(ID: {result.get('id', 'unknown')})\n"
                f"Stage: planning\n"
                f"Next: Add plan artifact or advance to executing"
            )
        return "Failed to create project."
    except Exception as e:
        return f"Error creating project: {e}"


@server.tool()
async def project_status(project_id: str) -> str:
    """Get project status, artifacts, and next action."""
    try:
        project_id = _validate_mcp_input(project_id, label="project_id")
    except ValueError as e:
        return str(e)
    deps = _get_deps()
    try:
        proj = await deps.storage_service.get_project(project_id)
        if not proj:
            return f"Project not found: {project_id}"
        parts = [
            f"Project: {proj['name']}",
            f"Stage: {proj.get('lifecycle_stage', 'unknown')}",
            f"Category: {proj.get('category', 'unknown')}",
        ]
        if proj.get("review_score"):
            parts.append(f"Review Score: {proj['review_score']}/10")
        artifacts = proj.get("project_artifacts", [])
        if artifacts:
            parts.append(f"\nArtifacts ({len(artifacts)}):")
            for a in artifacts:
                parts.append(f"  - {a['artifact_type']}: {a.get('title', 'untitled')}")
        return "\n".join(parts)
    except Exception as e:
        return f"Error getting project status: {e}"


@server.tool()
async def advance_project(project_id: str, target_stage: str | None = None) -> str:
    """Advance a project to the next lifecycle stage. Stages: planning -> executing ->
    reviewing -> learning -> complete. Specify target_stage to jump to a specific stage."""
    try:
        project_id = _validate_mcp_input(project_id, label="project_id")
    except ValueError as e:
        return str(e)
    deps = _get_deps()
    stage_order = ["planning", "executing", "reviewing", "learning", "complete"]
    try:
        proj = await deps.storage_service.get_project(project_id)
        if not proj:
            return f"Project not found: {project_id}"
        current = proj.get("lifecycle_stage", "planning")
        if target_stage:
            next_stage = target_stage
        else:
            try:
                idx = stage_order.index(current)
                next_stage = stage_order[idx + 1] if idx + 1 < len(stage_order) else current
            except ValueError:
                return f"Cannot auto-advance from stage: {current}"
        result = await deps.storage_service.update_project_stage(project_id, next_stage)
        if result:
            return f"Project '{proj['name']}' advanced: {current} -> {next_stage}"
        return "Failed to advance project."
    except Exception as e:
        return f"Error advancing project: {e}"


@server.tool()
async def list_projects(
    lifecycle_stage: str | None = None,
    category: str | None = None,
    limit: int = 20,
) -> str:
    """List Second Brain projects with optional filters.

    Args:
        lifecycle_stage: Filter by stage: planning, executing, reviewing, learning, done
        category: Filter by category: content, prospects, clients, products, general
        limit: Maximum number of projects to return (default 20)
    """
    deps = _get_deps()
    try:
        projects = await deps.storage_service.list_projects(
            lifecycle_stage=lifecycle_stage,
            category=category,
            limit=limit,
        )
        if not projects:
            return "No projects found. Create one with create_project."
        parts = [f"# Projects ({len(projects)})\n"]
        for p in projects:
            stage = p.get("lifecycle_stage", "unknown")
            parts.append(f"## {p['name']} [{stage}]")
            parts.append(f"ID: {p['id']}")
            if p.get("category"):
                parts.append(f"Category: {p['category']}")
            if p.get("description"):
                parts.append(p["description"][:120])
            parts.append("")
        return "\n".join(parts)
    except Exception as e:
        return f"Error listing projects: {e}"


@server.tool()
async def update_project(
    project_id: str,
    name: str | None = None,
    description: str | None = None,
    category: str | None = None,
) -> str:
    """Update a project's metadata (name, description, or category).

    Args:
        project_id: The project UUID (from list_projects or create_project)
        name: New project name (optional)
        description: New project description (optional)
        category: New category: content, prospects, clients, products, general (optional)
    """
    try:
        project_id = _validate_mcp_input(project_id, label="project_id")
    except ValueError as e:
        return str(e)
    fields = {
        k: v for k, v in
        {"name": name, "description": description, "category": category}.items()
        if v is not None
    }
    if not fields:
        return "No fields to update. Provide at least one of: name, description, category."
    deps = _get_deps()
    try:
        result = await deps.storage_service.update_project(project_id, fields)
        if not result:
            return f"Project not found: {project_id}"
        changed = ", ".join(fields.keys())
        return f"Project updated: {result.get('name', project_id)}\nChanged: {changed}"
    except Exception as e:
        return f"Error updating project: {e}"


@server.tool()
async def delete_project(project_id: str) -> str:
    """Permanently delete a project and all its artifacts.

    WARNING: This is irreversible. All artifacts (plan, draft, review, output)
    attached to the project will also be deleted.

    Args:
        project_id: The project UUID to delete (from list_projects)
    """
    try:
        project_id = _validate_mcp_input(project_id, label="project_id")
    except ValueError as e:
        return str(e)
    deps = _get_deps()
    try:
        # Fetch project first to get the name for confirmation message
        proj = await deps.storage_service.get_project(project_id)
        if not proj:
            return f"Project not found: {project_id}"
        project_name = proj.get("name", project_id)
        deleted = await deps.storage_service.delete_project(project_id)
        if deleted:
            return f"Deleted project: {project_name}"
        return f"Failed to delete project: {project_id}"
    except Exception as e:
        return f"Error deleting project: {e}"


@server.tool()
async def add_artifact(
    project_id: str,
    artifact_type: str,
    title: str | None = None,
    content: str | None = None,
) -> str:
    """Add an artifact to a project (plan, draft, review, output, note).

    Args:
        project_id: The project UUID
        artifact_type: Type of artifact: plan, draft, review, output, note
        title: Optional artifact title or label
        content: Optional artifact content text (e.g., the actual plan or draft)
    """
    valid_types = {"plan", "draft", "review", "output", "note"}
    try:
        project_id = _validate_mcp_input(project_id, label="project_id")
    except ValueError as e:
        return str(e)
    if artifact_type not in valid_types:
        return f"Invalid artifact_type '{artifact_type}'. Use: {', '.join(sorted(valid_types))}"
    deps = _get_deps()
    try:
        artifact_data: dict = {"project_id": project_id, "artifact_type": artifact_type}
        if title:
            artifact_data["title"] = title
        if content:
            artifact_data["content"] = content
        result = await deps.storage_service.add_project_artifact(artifact_data)
        if result:
            return (
                f"Artifact added: {artifact_type}"
                + (f" — {title}" if title else "")
                + f"\nArtifact ID: {result.get('id', 'unknown')}"
            )
        return "Failed to add artifact."
    except Exception as e:
        return f"Error adding artifact: {e}"


@server.tool()
async def delete_artifact(artifact_id: str) -> str:
    """Delete a project artifact by its ID.

    Args:
        artifact_id: The artifact UUID (from project_status output)
    """
    try:
        artifact_id = _validate_mcp_input(artifact_id, label="artifact_id")
    except ValueError as e:
        return str(e)
    deps = _get_deps()
    try:
        deleted = await deps.storage_service.delete_project_artifact(artifact_id)
        if deleted:
            return f"Deleted artifact: {artifact_id}"
        return f"Artifact not found: {artifact_id}"
    except Exception as e:
        return f"Error deleting artifact: {e}"


@server.tool()
async def search_experiences(
    category: str | None = None,
    limit: int = 20,
) -> str:
    """List work experiences from your Second Brain.

    Experiences are individual work events (client calls, launches, wins/losses)
    that inform future decisions. Use category to filter.

    Args:
        category: Filter by category (e.g., client-work, product-launch) or None for all
        limit: Maximum experiences to return (default 20)
    """
    deps = _get_deps()
    try:
        experiences = await deps.storage_service.get_experiences(
            category=category, limit=limit
        )
        if not experiences:
            cat_note = f" in category '{category}'" if category else ""
            return f"No experiences found{cat_note}. Record some with `learn`."
        parts = [f"# Experiences ({len(experiences)})\n"]
        for exp in experiences:
            parts.append(f"## {exp.get('title', 'Untitled')}")
            if exp.get("category"):
                parts.append(f"Category: {exp['category']}")
            if exp.get("date"):
                parts.append(f"Date: {exp['date']}")
            parts.append(exp.get("description", "")[:300])
            if exp.get("id"):
                parts.append(f"ID: {exp['id']}")
            parts.append("")
        return "\n".join(parts)
    except Exception as e:
        return f"Error searching experiences: {e}"


@server.tool()
async def search_patterns(
    topic: str | None = None,
    confidence: str | None = None,
    keyword: str | None = None,
    limit: int = 30,
) -> str:
    """Search your Second Brain patterns with optional filters.

    More granular than pattern_registry — supports keyword search
    and confidence filtering. Use pattern_registry for the full overview.

    Args:
        topic: Filter by topic (e.g., messaging, brand-voice, content, strategy)
        confidence: Filter by level: HIGH, MEDIUM, or LOW
        keyword: Text to match in pattern name or pattern_text (optional, case-insensitive)
        limit: Maximum results (default 30)
    """
    deps = _get_deps()
    try:
        patterns = await deps.storage_service.get_patterns(
            topic=topic, confidence=confidence
        )
        # Client-side keyword filter
        if keyword:
            kw = keyword.lower()
            patterns = [
                p for p in patterns
                if kw in p.get("name", "").lower() or kw in p.get("pattern_text", "").lower()
            ]
        patterns = patterns[:limit]
        if not patterns:
            return "No patterns found matching your filters."
        parts = [f"# Patterns ({len(patterns)})\n"]
        for p in patterns:
            parts.append(
                f"## [{p.get('confidence', '?')}] {p.get('name', 'Unnamed')}"
            )
            if p.get("topic"):
                parts.append(f"Topic: {p['topic']}")
            parts.append(p.get("pattern_text", "")[:300])
            if p.get("id"):
                parts.append(f"ID: {p['id']}")
            parts.append("")
        return "\n".join(parts)
    except Exception as e:
        return f"Error searching patterns: {e}"


@server.tool()
async def ingest_example(
    content_type: str,
    title: str,
    content: str,
    notes: str | None = None,
) -> str:
    """Add a content example directly to your Second Brain's example library.

    Previously this required running a migration script. Now you can add
    examples inline from Claude Code.

    Args:
        content_type: Content type slug (e.g., linkedin, email, case-study, newsletter)
        title: Short title describing what makes this a good example
        content: The example content text (the actual email, post, etc.)
        notes: Optional notes about why this is a good example or what to learn from it
    """
    try:
        content_type = _validate_mcp_input(content_type, label="content_type")
        title = _validate_mcp_input(title, label="title")
        content = _validate_mcp_input(content, label="content")
    except ValueError as e:
        return str(e)
    deps = _get_deps()
    try:
        example_data: dict = {
            "content_type": content_type,
            "title": title,
            "content": content,
        }
        if notes:
            example_data["notes"] = notes
        result = await deps.storage_service.upsert_example(example_data)
        if result:
            return (
                f"Example added: {title}\n"
                f"Type: {content_type}\n"
                f"ID: {result.get('id', 'unknown')}"
            )
        return "Failed to ingest example."
    except Exception as e:
        return f"Error ingesting example: {e}"


@server.tool()
async def ingest_knowledge(
    category: str,
    title: str,
    content: str,
    tags: str | None = None,
) -> str:
    """Add a knowledge entry directly to your Second Brain's knowledge repository.

    Knowledge entries capture audience insights, product info, competitive data,
    and other reference material. Previously required a migration script.

    Args:
        category: Knowledge category (e.g., audience, product, competitors, positioning)
        title: Short title for this knowledge entry
        content: The knowledge content text
        tags: Optional comma-separated tags (e.g., "enterprise,saas,2026")
    """
    try:
        category = _validate_mcp_input(category, label="category")
        title = _validate_mcp_input(title, label="title")
        content = _validate_mcp_input(content, label="content")
    except ValueError as e:
        return str(e)
    deps = _get_deps()
    try:
        knowledge_data: dict = {
            "category": category,
            "title": title,
            "content": content,
        }
        if tags:
            knowledge_data["tags"] = [t.strip() for t in tags.split(",") if t.strip()]
        result = await deps.storage_service.upsert_knowledge(knowledge_data)
        if result:
            return (
                f"Knowledge added: {title}\n"
                f"Category: {category}\n"
                f"ID: {result.get('id', 'unknown')}"
            )
        return "Failed to ingest knowledge."
    except Exception as e:
        return f"Error ingesting knowledge: {e}"


@server.tool()
async def brain_setup() -> str:
    """Check brain setup/onboarding status. Shows which memory categories are populated
    and what steps remain to fully configure the brain."""
    deps = _get_deps()
    try:
        from second_brain.services.health import HealthService
        health = HealthService()
        status = await health.compute_setup_status(deps)
        completed = status.get("completed_count", 0)
        total = status.get("total_steps", 0)
        pct = int(completed / total * 100) if total > 0 else 0
        parts = [f"Brain Setup: {pct}% complete ({completed}/{total} steps)"]
        for step in status.get("steps", []):
            icon = "[x]" if step["completed"] else "[ ]"
            parts.append(f"  {icon} {step['description']}")
        if not status.get("is_complete"):
            missing = status.get("missing_categories", [])
            if missing:
                parts.append(f"\nMissing categories: {', '.join(missing)}")
            parts.append("Use 'learn' tool or migration to populate missing categories.")
        else:
            parts.append("\nBrain is fully configured!")
        return "\n".join(parts)
    except Exception as e:
        return f"Error checking setup: {e}"


@server.tool()
async def pattern_registry() -> str:
    """View the full pattern registry -- all patterns with confidence, usage, and status."""
    deps = _get_deps()
    try:
        from second_brain.agents.utils import format_pattern_registry
        registry = await deps.storage_service.get_pattern_registry()
        return format_pattern_registry(registry, config=deps.config)
    except Exception as e:
        return f"Error loading pattern registry: {e}"


# --- Operations & Advisory Agents ---

@server.tool()
async def coaching_session(request: str, session_type: str = "morning") -> str:
    """Get daily accountability coaching for planning and productivity.

    Args:
        request: Your coaching request (e.g., "Help me plan today", "I'm overwhelmed")
        session_type: Session type — morning, evening, check_in, or intervention
    """
    try:
        request = _validate_mcp_input(request, label="request")
    except ValueError as e:
        return str(e)
    deps = _get_deps()
    model = _get_model("coach")
    from second_brain.agents.coach import coach_agent
    prompt = f"Session type: {session_type}\n\n{request}"
    timeout = deps.config.api_timeout_seconds
    try:
        async with asyncio.timeout(timeout):
            result = await coach_agent.run(prompt, deps=deps, model=model)
    except TimeoutError:
        return f"Coaching session timed out after {timeout}s."
    out = result.output
    parts = [f"Session: {out.session_type}", f"Next action: {out.next_action}"]
    if out.coaching_notes:
        parts.append(out.coaching_notes)
    return "\n".join(parts)


@server.tool()
async def prioritize_tasks(tasks: str) -> str:
    """Score and prioritize tasks using PMO methodology.

    Args:
        tasks: Comma-separated list of tasks to prioritize
    """
    try:
        tasks = _validate_mcp_input(tasks, label="tasks")
    except ValueError as e:
        return str(e)
    deps = _get_deps()
    model = _get_model("pmo")
    from second_brain.agents.pmo import pmo_agent
    timeout = deps.config.api_timeout_seconds
    try:
        async with asyncio.timeout(timeout):
            result = await pmo_agent.run(tasks, deps=deps, model=model)
    except TimeoutError:
        return f"Task prioritization timed out after {timeout}s."
    out = result.output
    lines = [out.coaching_message]
    for t in out.scored_tasks[:5]:
        lines.append(f"  {t.task_name}: {t.total_score:.0f} ({t.category})")
    return "\n".join(lines)


@server.tool()
async def compose_email(request: str) -> str:
    """Compose or manage emails with brand voice.

    Args:
        request: Email request (e.g., "Draft a follow-up to John about the proposal")
    """
    try:
        request = _validate_mcp_input(request, label="request")
    except ValueError as e:
        return str(e)
    deps = _get_deps()
    model = _get_model("email")
    from second_brain.agents.email_agent import email_agent
    timeout = deps.config.api_timeout_seconds
    try:
        async with asyncio.timeout(timeout):
            result = await email_agent.run(request, deps=deps, model=model)
    except TimeoutError:
        return f"Email composition timed out after {timeout}s."
    out = result.output
    return f"Subject: {out.subject}\n\n{out.body}\n\nStatus: {out.status}"


@server.tool()
async def ask_claude_specialist(question: str) -> str:
    """Ask a verified question about Claude Code, Pydantic AI, or AI development.

    Args:
        question: Technical question about Claude Code or AI development
    """
    try:
        question = _validate_mcp_input(question, label="question")
    except ValueError as e:
        return str(e)
    deps = _get_deps()
    model = _get_model("specialist")
    from second_brain.agents.specialist import specialist_agent
    timeout = deps.config.api_timeout_seconds
    try:
        async with asyncio.timeout(timeout):
            result = await specialist_agent.run(question, deps=deps, model=model)
    except TimeoutError:
        return f"Specialist query timed out after {timeout}s."
    out = result.output
    return f"[{out.confidence_level}] {out.answer}"


# --- Chief of Staff / Orchestration ---

@server.tool()
async def run_brain_pipeline(request: str, steps: str = "") -> str:
    """Run a multi-agent pipeline. Steps is a comma-separated list of agent names.

    If steps is empty, uses Chief of Staff to determine the optimal pipeline.
    Example steps: "recall,create,review"

    Args:
        request: The user's request to process through the pipeline
        steps: Comma-separated agent names (e.g., "recall,create,review"). Empty = auto-route.
    """
    try:
        request = _validate_mcp_input(request, label="request")
    except ValueError as e:
        return str(e)
    deps = _get_deps()
    model = _get_model("chief_of_staff")
    from second_brain.agents.utils import run_pipeline

    if not steps:
        # Auto-route via Chief of Staff
        from second_brain.agents.chief_of_staff import chief_of_staff
        timeout = deps.config.api_timeout_seconds
        try:
            async with asyncio.timeout(timeout):
                routing = await chief_of_staff.run(request, deps=deps, model=model)
        except TimeoutError:
            return f"Pipeline routing timed out after {timeout}s."
        routing_output = routing.output
        if routing_output.target_agent == "pipeline":
            step_list = list(routing_output.pipeline_steps)
        else:
            step_list = [routing_output.target_agent]
    else:
        step_list = [s.strip() for s in steps.split(",") if s.strip()]

    results = await run_pipeline(
        steps=step_list,
        initial_prompt=request,
        deps=deps,
        model=model,
    )
    final = results.get("final")
    return str(final) if final else "Pipeline completed with no output."


@server.tool()
async def analyze_clarity(content: str) -> str:
    """Analyze content for clarity and readability issues."""
    try:
        content = _validate_mcp_input(content, label="content")
    except ValueError as e:
        return str(e)
    deps = _get_deps()
    model = _get_model("clarity")
    from second_brain.agents.clarity import clarity_agent
    timeout = deps.config.api_timeout_seconds
    try:
        async with asyncio.timeout(timeout):
            result = await clarity_agent.run(content, deps=deps, model=model)
    except TimeoutError:
        return f"Clarity analysis timed out after {timeout}s."
    out = result.output
    lines = [f"Readability: {out.overall_readability} ({out.critical_count} critical)"]
    for f in out.findings[:10]:
        lines.append(f"[{f.severity}] {f.location}: {f.issue} -> {f.suggestion}")
    return "\n".join(lines)


@server.tool()
async def synthesize_feedback(findings: str) -> str:
    """Consolidate review findings into actionable improvement themes."""
    try:
        findings = _validate_mcp_input(findings, label="findings")
    except ValueError as e:
        return str(e)
    deps = _get_deps()
    model = _get_model("synthesizer")
    from second_brain.agents.synthesizer import synthesizer_agent
    timeout = deps.config.api_timeout_seconds
    try:
        async with asyncio.timeout(timeout):
            result = await synthesizer_agent.run(findings, deps=deps, model=model)
    except TimeoutError:
        return f"Feedback synthesis timed out after {timeout}s."
    out = result.output
    lines = [f"{out.total_themes_output} themes, {out.implementation_hours:.1f}h total"]
    for t in out.themes:
        lines.append(f"[{t.priority}] {t.title} ({t.effort_minutes}min): {t.action}")
    return "\n".join(lines)


@server.tool()
async def find_template_opportunities(deliverable: str) -> str:
    """Analyze a deliverable for reusable template opportunities."""
    try:
        deliverable = _validate_mcp_input(deliverable, label="deliverable")
    except ValueError as e:
        return str(e)
    deps = _get_deps()
    model = _get_model("template_builder")
    from second_brain.agents.template_builder import template_builder_agent
    timeout = deps.config.api_timeout_seconds
    try:
        async with asyncio.timeout(timeout):
            result = await template_builder_agent.run(deliverable, deps=deps, model=model)
    except TimeoutError:
        return f"Template analysis timed out after {timeout}s."
    out = result.output
    lines = [f"{out.templates_created} template opportunities"]
    for opp in out.opportunities:
        lines.append(f"- {opp.name}: {opp.when_to_use}")
    return "\n".join(lines)


if __name__ == "__main__":
    import os as _os
    import sys as _sys

    logging.basicConfig(
        stream=_sys.stderr,
        level=logging.WARNING,
        format="%(levelname)s: %(message)s",
    )

    # Read transport config from env (BrainConfig validates on first tool call)
    _transport = _os.environ.get("MCP_TRANSPORT", "stdio").lower()
    # Normalize streamable-http → http (FastMCP 2.x treats them identically)
    if _transport == "streamable-http":
        _transport = "http"

    # Eager dep initialization — avoids Mem0 deadlock inside async event loop.
    # See service_mcp.py:init_deps() for rationale.
    if _transport in ("http", "sse"):
        init_deps()

    try:
        if _transport in ("http", "sse"):
            _host = _os.environ.get("MCP_HOST", "0.0.0.0")
            _port = int(_os.environ.get("MCP_PORT", "8000"))
            logger.warning(
                "Starting MCP server: transport=%s host=%s port=%s",
                _transport, _host, _port,
            )
            server.run(
                transport=_transport,
                host=_host,
                port=_port,
            )
        else:
            server.run()
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
