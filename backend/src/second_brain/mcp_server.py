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

def _validate_mcp_input(
    text: str,
    label: str = "input",
    max_length: int | None = None,
) -> str:
    """Validate MCP tool text input.

    max_length priority: explicit param > deps config > 10000 fallback.
    """
    if max_length is None:
        if _deps is not None:
            max_length = _deps.config.max_input_length
        else:
            max_length = 10000  # fallback if called before deps available
    if not text or not text.strip():
        raise ValueError(f"{label} cannot be empty")
    if len(text) > max_length:
        raise ValueError(
            f"{label} too long ({len(text)} chars, max {max_length})"
        )
    return text.strip()


def _validate_user_id(user_id: str | None) -> str | None:
    """Validate user_id against allowed list. Returns cleaned user_id or None."""
    if not user_id or not user_id.strip():
        return None
    user_id = user_id.strip().lower()
    if _deps is not None:
        allowed = _deps.config.allowed_user_ids_list
        if allowed and user_id not in allowed:
            raise ValueError(
                f"Unknown user_id '{user_id}'. Allowed: {', '.join(allowed)}"
            )
    return user_id


def _validate_url_scheme(url: str, label: str = "URL") -> str:
    """Validate URL uses HTTP(S) scheme. Allows data URIs for base64 images."""
    if not url or not url.strip():
        raise ValueError(f"{label} cannot be empty")
    url = url.strip()
    if url.startswith("data:"):
        return url  # Allow data URIs for base64 images
    from urllib.parse import urlparse
    parsed = urlparse(url)
    if parsed.scheme not in ("https", "http"):
        raise ValueError(f"{label} must use HTTP(S) scheme.")
    return url


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
            {"status": "unhealthy", "service": "second-brain",
             "error": "Initialization failed. Check server logs."},
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
        logger.info("Dependencies initialized successfully")
    except Exception as e:
        _deps_failed = True
        _deps_error = str(e)
        logger.error("Failed to initialize deps: %s", e)


async def _setup_mem0_project() -> None:
    """Configure Mem0 project-level settings (criteria retrieval, custom instructions).

    Only runs when memory_provider='mem0'. Failures are logged but don't block startup.
    Called from __main__ after init_deps() but before server.run().
    """
    deps = _get_deps()
    if deps.config.memory_provider != "mem0":
        logger.debug("Skipping Mem0 project setup: memory_provider=%s", deps.config.memory_provider)
        return

    # Setup criteria retrieval (weighted scoring for searches)
    criteria_ok = await deps.memory.setup_criteria_retrieval()
    if not criteria_ok:
        logger.warning("Mem0 criteria retrieval setup failed — using defaults")

    # Setup custom instructions (memory extraction guidelines)
    instructions_ok = await deps.memory.setup_custom_instructions()
    if not instructions_ok:
        logger.warning("Mem0 custom instructions setup failed — using defaults")

    if criteria_ok and instructions_ok:
        logger.info("Mem0 project configuration complete")


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
    """Search your Second Brain using an LLM agent that selects the optimal
    search strategy across semantic memory, patterns, experiences, examples,
    and projects. The agent can chain multiple searches and synthesize results.

    When to use: For nuanced queries where the best search strategy is unclear,
    or when you need the agent to try multiple approaches. Slower than quick_recall
    (~5-15s) but more thorough for ambiguous queries.

    Returns: Ranked matches with relevance scores, related patterns, graph
    relationships, and a synthesis summary.

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
        logger.warning("MCP recall timed out after %ds", timeout)
        return f"Recall timed out after {timeout}s. Try a simpler query."
    except Exception as e:
        logger.error("Recall agent failed: %s", type(e).__name__)
        logger.debug("Recall error detail: %s", e)
        return (
            f"Recall encountered an error: {type(e).__name__}. "
            "Try quick_recall() for a direct search without agent overhead."
        )
    output = result.output

    # Format as readable text for Claude Code
    parts = [f"# Recall: {output.query}\n"]
    if output.matches:
        parts.append("## Matches\n")
        for m in output.matches:
            score_str = f" ({m.score:.2f})" if m.score > 0 else ""
            parts.append(f"- [{m.relevance}]{score_str} {m.content}")
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
    if output.search_sources:
        parts.append(f"\n_Sources: {', '.join(output.search_sources)}_")
    if output.error:
        parts.append(f"\n**WARNING**: {output.error}")
    return "\n".join(parts)


@server.tool()
async def quick_recall(query: str, limit: int = 10) -> str:
    """Fast parallel memory search — runs Mem0 semantic + pgvector hybrid
    concurrently, then deduplicates and reranks with Voyage AI. No LLM agent
    overhead. Auto-upgrades complex queries to recall_deep.

    When to use: Default choice for memory search. Handles simple lookups
    (~1-2s) and medium queries (~2-4s). Complex queries (comparisons,
    synthesis) are automatically redirected to recall_deep.

    Returns: Ranked matches with scores and source attribution.

    Args:
        query: What to search for (e.g., "content patterns", "client feedback")
        limit: Maximum results after dedup + reranking (default: 10)
    """
    try:
        query = _validate_mcp_input(query, label="query")
    except ValueError as e:
        return str(e)
    deps = _get_deps()
    limit = max(1, min(limit, 100))

    timeout = deps.config.api_timeout_seconds

    from second_brain.agents.utils import (
        classify_query_complexity,
        expand_query,
        deduplicate_results,
        format_memories,
        format_relations,
        normalize_results,
        rerank_memories,
        search_with_graph_fallback,
    )

    try:
        async with asyncio.timeout(timeout):
            # Auto-upgrade complex queries to deep recall
            complexity = classify_query_complexity(query, deps.config.complex_query_word_threshold)
            logger.debug("quick_recall complexity=%s query_len=%d", complexity, len(query))
            if complexity == "complex":
                logger.info("quick_recall routing to recall_deep for complex query")
                return await recall_deep(query, limit=limit)

            # Step 1: Expand query with domain synonyms
            expanded = expand_query(query)
            oversample = deps.config.retrieval_oversample_factor

            # Step 2: Run Mem0 + hybrid pgvector in parallel
            mem0_coro = deps.memory_service.search(expanded, limit=limit * oversample)

            hybrid_coro = None
            embedding = None
            if deps.embedding_service:
                try:
                    embedding = await deps.embedding_service.embed_query(query)
                except Exception as e:
                    logger.warning("Embedding failed in quick_recall (non-fatal): %s", type(e).__name__)
                    logger.debug("Embedding error detail: %s", e)
            if embedding:
                hybrid_coro = deps.storage_service.hybrid_search(
                    query_text=query,
                    query_embedding=embedding,
                    table="memory_content",
                    limit=limit * oversample,
                )

            # Execute concurrently
            if hybrid_coro:
                mem0_result, hybrid_result = await asyncio.gather(
                    mem0_coro, hybrid_coro, return_exceptions=True,
                )
            else:
                mem0_result = await mem0_coro
                hybrid_result = None

            # Step 3: Collect and normalize results
            search_sources = []
            all_memories: list[dict] = []

            if not isinstance(mem0_result, BaseException):
                all_memories.extend(
                    normalize_results(mem0_result.memories, source="mem0")
                )
                search_sources.append("mem0")
            else:
                logger.debug("Mem0 search failed in quick_recall: %s", mem0_result)

            if hybrid_result and not isinstance(hybrid_result, BaseException):
                all_memories.extend(
                    normalize_results(hybrid_result, source="hybrid:memory_content",
                                      content_key="content", score_key="similarity")
                )
                search_sources.append("hybrid:memory_content")
            elif isinstance(hybrid_result, BaseException):
                logger.debug("Hybrid search failed in quick_recall: %s", hybrid_result)

            # Step 4: Deduplicate and rerank
            all_memories = deduplicate_results(all_memories)
            memories = await rerank_memories(deps, query, all_memories, top_k=limit)

            # Step 5: Graph relations
            base_relations = mem0_result.relations if not isinstance(mem0_result, BaseException) else []
            relations = await search_with_graph_fallback(deps, query, base_relations)

    except TimeoutError:
        logger.warning("MCP quick_recall timed out after %ds", timeout)
        return f"Quick recall timed out after {timeout}s. Try a simpler query."
    except Exception as e:
        logger.error("Quick recall failed: %s", type(e).__name__)
        logger.debug("Quick recall error detail: %s", e)
        return f"Quick recall encountered an error: {type(e).__name__}. Try again or use recall() for agent-backed search."

    if not memories and not relations:
        return "No results found. Try recall() for a deeper multi-source search."

    logger.info("quick_recall returning %d results from sources=%s", len(memories), search_sources)

    # Format output
    parts = [f"# Quick Recall: {query}\n"]
    mem_text = format_memories(memories)
    if mem_text:
        parts.append("## Matches\n")
        parts.append(mem_text)
    rel_text = format_relations(relations)
    if rel_text:
        parts.append(rel_text)
    source_str = ", ".join(search_sources) if search_sources else "none"
    parts.append(f"\n---\n_Fast path ({len(memories)} results, sources: {source_str}). Use recall() for deeper search._")
    return "\n".join(parts)


@server.tool()
async def recall_deep(query: str, limit: int = 15) -> str:
    """Deep parallel search across ALL memory sources — Mem0 semantic, hybrid
    pgvector, patterns, examples, knowledge, experiences, and graph. Runs all
    sources concurrently for maximum recall breadth.

    When to use: For complex synthesis queries, cross-source comparisons, or
    comprehensive overviews. Slower (~3-8s) but searches every source. Usually
    auto-triggered by quick_recall for complex queries — rarely called directly.

    Returns: Ranked matches from multiple sources with source attribution,
    graph relationships, and source count summary.

    Args:
        query: Complex search query (e.g., "compare all content patterns with
               enterprise client engagement approaches")
        limit: Maximum results after dedup + reranking (default: 15)
    """
    try:
        query = _validate_mcp_input(query, label="query")
    except ValueError as e:
        return str(e)
    deps = _get_deps()
    limit = max(1, min(limit, 100))

    timeout = deps.config.api_timeout_seconds

    try:
        async with asyncio.timeout(timeout):
            from second_brain.agents.utils import (
                deep_recall_search,
                format_memories,
                format_relations,
            )

            result = await deep_recall_search(deps, query, limit=limit)
    except TimeoutError:
        logger.warning("MCP recall_deep timed out after %ds", timeout)
        return f"Deep recall timed out after {timeout}s. Try a simpler query or use quick_recall()."
    except Exception as e:
        logger.error("Deep recall failed: %s", type(e).__name__)
        logger.debug("Deep recall error detail: %s", e)
        return f"Deep recall encountered an error: {type(e).__name__}. Try again or use quick_recall() for a simpler search."

    memories = result["memories"]
    relations = result["relations"]
    search_sources = result["search_sources"]

    if not memories and not relations:
        return "No results found across all sources. Try broadening your query."

    # Format output
    parts = [f"# Deep Recall: {query}\n"]
    mem_text = format_memories(memories)
    if mem_text:
        parts.append("## Matches\n")
        parts.append(mem_text)
    rel_text = format_relations(relations)
    if rel_text:
        parts.append(rel_text)
    source_str = ", ".join(search_sources) if search_sources else "none"
    parts.append(f"\n---\n_Deep search ({len(memories)} results from {len(search_sources)} sources: {source_str})_")
    return "\n".join(parts)


@server.tool()
async def ask(question: str) -> str:
    """Answer questions using your Second Brain's accumulated knowledge —
    patterns, experiences, client context, and content history. The agent
    searches memory first, then synthesizes an answer.

    When to use: For questions that need a synthesized answer, not just raw
    search results. Unlike recall (which returns matches), ask interprets
    and answers. For pure search, use quick_recall instead.

    Returns: Answer text with context sources, patterns applied, graph
    relationships, and suggested next action.

    Args:
        question: Your question (e.g., "What's our positioning for enterprise?",
                  "Help me write a follow-up email to John")
    """
    try:
        question = _validate_mcp_input(question, label="question")
    except ValueError as e:
        return str(e)
    # Short-circuit for greetings and small talk — skip agent pipeline
    from second_brain.agents.utils import is_conversational
    if is_conversational(question):
        return (
            "Hey! I'm your Second Brain assistant. "
            "Ask me anything — I can search your memory, help with content, "
            "review your work, or answer questions using your accumulated knowledge."
        )
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
        logger.warning("MCP ask timed out after %ds", timeout)
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
    """Extract patterns and learnings from raw text — work sessions, meeting
    notes, client conversations, or content drafts. Identifies reusable
    patterns, reinforces existing ones, and stores experiences.

    When to use: After completing work you want to learn from. Feed raw text
    and the agent extracts patterns, insights, and experiences automatically.

    Returns: Extracted patterns (new + reinforced), stored experiences, and
    a learning summary.

    Args:
        content: Raw text from a work session, conversation, or experience.
        category: Experience category — content, prospects, clients, or general.
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
        logger.warning("MCP learn timed out after %ds", timeout)
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
    """Extract learnings from an image — diagrams, screenshots, photos, whiteboard
    captures. Uses multimodal embeddings for visual semantic search.

    When to use: When you have a visual artifact to learn from. Complements the
    text-based learn tool. Stored with multimodal embeddings for retrieval via
    multimodal_vector_search.

    Returns: Extracted insights and storage confirmation.

    Args:
        image_url: Image URL (https://...) or base64 data URI
                   (data:image/jpeg;base64,...). Supports JPEG, PNG, WebP, GIF.
        context: Optional text description or context about the image.
        category: Memory category for filtering (default: visual).
    """
    try:
        image_url = _validate_url_scheme(image_url, label="image_url")
    except ValueError as e:
        return str(e)

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
        logger.warning("MCP learn_image Mem0 storage timed out after %ds", timeout)
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
        except ImportError:
            results.append("Embedding skipped: Pillow (PIL) is required for base64 image processing. Install with: pip install Pillow")
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
    """Extract learnings from a document — PDFs, reports, slide decks.
    Analyzes content and stores with searchable memory.

    When to use: For document-based learning. Unlike learn (which takes raw text),
    this processes document formats directly. Stored for retrieval via
    multimodal_vector_search.

    Returns: Document analysis and storage confirmation.

    Args:
        document_url: Document URL (https://...) or base64 string.
                      For PDFs: URL only. For text/MDX: URL or raw base64.
        document_type: Document format — pdf, mdx, or txt (default: pdf).
        context: Optional description of the document's purpose.
        category: Memory category for filtering (default: document).
    """
    try:
        document_url = _validate_url_scheme(document_url, label="document_url")
    except ValueError as e:
        return str(e)

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
        logger.warning("MCP learn_document Mem0 storage timed out after %ds", timeout)
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
    """Extract learnings from a video — presentations, tutorials, interviews.
    Generates vector embedding via Voyage AI and stores context in Mem0.

    When to use: For video-based learning. Stored for retrieval via
    multimodal_vector_search. Requires video to be accessible via URL.

    Returns: Video analysis, embedding status, and storage confirmation.

    Args:
        video_url: Video URL (https://...) or local file path. MP4 format only.
        context: Optional description of the video content.
        category: Memory category for filtering (default: video).
    """
    try:
        video_url = _validate_url_scheme(video_url, label="video_url")
    except ValueError as e:
        return str(e)

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
    """Search across text AND visual content using multimodal embeddings.
    Finds images, documents, and videos alongside text matches.

    When to use: When searching for visual content stored via learn_image,
    learn_document, or learn_video. For text-only search, use quick_recall
    or vector_search instead.

    Returns: Multimodal matches ranked by similarity with content type and preview.

    Args:
        query: Optional text search query.
        image_url: Optional image URL or base64 data URI to search with.
        table: Table to search — memory_content, patterns, examples, knowledge_repo.
        limit: Maximum results (default: 10).
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
        logger.warning("MCP multimodal_vector_search timed out after %ds", timeout)
        return f"Multimodal search timed out after {timeout}s."
    except ValueError as e:
        return str(e)
    except Exception as e:
        logger.error("Multimodal vector search failed: %s", type(e).__name__)
        logger.debug("Multimodal vector search error detail: %s", e)
        return f"Multimodal search encountered an error: {type(e).__name__}. Check embedding service configuration."

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
    prompt: str, content_type: str = "linkedin", user_id: str = "",
    structure_hint: str = "",
) -> str:
    """Create content using your brand voice, patterns, and accumulated knowledge.
    Loads voice guide, relevant examples, and patterns before generating.
    Specify user_id to write in a specific user's voice.

    When to use: For content creation — LinkedIn posts, emails, case studies,
    newsletters, landing pages, essays. Specify content_type for format-specific
    structure and voice calibration.

    Returns: Generated content draft with structure following the content type's
    template, plus voice alignment notes.

    Args:
        prompt: What to create (e.g., "Announce our new AI automation product",
                "Draft a cold outreach email for SaaS founders")
        content_type: Content format — linkedin, email, case-study, newsletter,
                      landing-page, essay, or any custom type (default: linkedin)
        user_id: Voice profile to use (e.g., "uttam", "robert").
                 Empty = use default profile.
        structure_hint: Optional template body or structure guide. When provided,
                       overrides the content type's default structure.
    """
    try:
        prompt = _validate_mcp_input(prompt, label="prompt")
    except ValueError as e:
        return str(e)
    try:
        effective_uid = _validate_user_id(user_id)
    except ValueError as e:
        return str(e)

    deps = _get_deps()
    model = _get_model("create")
    registry = deps.get_content_type_registry()

    type_config = await registry.get(content_type)
    if not type_config:
        available = await registry.slugs()
        return f"Unknown content type '{content_type}'. Available: {', '.join(available)}"

    timeout = deps.config.api_timeout_seconds

    # Route LinkedIn content to dedicated LinkedIn Writer agent
    if content_type == "linkedin":
        from second_brain.agents.linkedin_writer import linkedin_writer_agent

        writer_prompt = f"Write a LinkedIn post about: {prompt}"
        if effective_uid:
            writer_prompt += f"\nVoice profile: {effective_uid}"
        if structure_hint:
            writer_prompt += (
                "\n\n## Structure Template (MANDATORY)\n"
                "Follow this template structure exactly:\n\n"
                f"{structure_hint}"
            )
        try:
            async with asyncio.timeout(timeout):
                result = await linkedin_writer_agent.run(
                    writer_prompt, deps=deps, model=model,
                )
        except TimeoutError:
            logger.warning("MCP create_content linkedin_writer timed out after %ds", timeout)
            return f"LinkedIn post creation timed out after {timeout}s."
        out = result.output
        parts = [
            f"# LinkedIn Post Draft\n",
            out.draft,
            f"\n---",
            f"**Hook**: {out.hook_used} ({out.hook_type})",
            f"**Structure**: {out.post_structure}",
            f"**Words**: {out.word_count}",
        ]
        if out.voice_elements:
            parts.append(f"**Voice**: {', '.join(out.voice_elements)}")
        if out.patterns_applied:
            parts.append(f"**Patterns**: {', '.join(out.patterns_applied)}")
        if out.notes:
            parts.append(f"\n**Notes**: {out.notes}")
        if out.error:
            parts.append(f"\n⚠️ **Degraded**: {out.error}")
        return "\n".join(parts)

    # Build prompt — agent's own tools fetch voice guide and examples
    agent_prompt = f"Create {type_config.name} ({content_type}) content"
    if type_config.length_guidance:
        agent_prompt += f" ({type_config.length_guidance})"
    elif type_config.max_words:
        agent_prompt += f" (around {type_config.max_words} words)"
    if effective_uid:
        agent_prompt += f"\n\nVoice profile: {effective_uid}"
    agent_prompt += f"\n\n{prompt}"
    if structure_hint:
        agent_prompt += (
            "\n\n## Structure Template (MANDATORY)\n"
            "Follow this template structure exactly — match every section, "
            "heading, and flow. Fill in the placeholders with relevant content:\n\n"
            f"{structure_hint}"
        )

    try:
        async with asyncio.timeout(timeout):
            result = await create_agent.run(agent_prompt, deps=deps, model=model)
    except TimeoutError:
        logger.warning("MCP create_content timed out after %ds", timeout)
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
async def review_content(content: str, content_type: str | None = None,
                         user_id: str = "") -> str:
    """Score content across multiple quality dimensions — structure, voice alignment,
    engagement, clarity, and persuasion. Uses your established patterns as the
    review standard. Specify user_id to evaluate against a specific user's voice.

    When to use: Before publishing content. Provides actionable scores and
    specific improvement suggestions. For voice-only analysis, use analyze_clarity
    instead.

    Returns: Overall score (1-10), per-dimension scores, top strengths,
    critical issues, and verdict (READY TO SEND / NEEDS REVISION / REWRITE).

    Args:
        content: The content text to review.
        content_type: Content format for type-specific review criteria (optional).
        user_id: Voice profile to use for voice alignment scoring (e.g., "uttam").
                 Empty = use default profile.
    """
    try:
        content = _validate_mcp_input(content, label="content")
    except ValueError as e:
        return str(e)
    try:
        _validate_user_id(user_id)
    except ValueError as e:
        return str(e)
    deps = _get_deps()
    model = _get_model("review")
    timeout = deps.config.api_timeout_seconds * deps.config.mcp_review_timeout_multiplier
    try:
        async with asyncio.timeout(timeout):
            result = await run_full_review(content, deps, model, content_type)
    except TimeoutError:
        logger.warning("MCP review_content timed out after %ds", timeout)
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
    """Browse stored content examples — real samples of emails, posts, case
    studies, and other content types from your experience.

    When to use: When you need reference examples for content creation or
    review. Filter by content_type for specific formats. For semantic search
    across examples, use quick_recall or recall instead.

    Returns: List of examples with content type, title, and preview text.

    Args:
        content_type: Filter by type (linkedin, email, case-study) or None for all.
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
    """Browse the knowledge repository — frameworks, methodologies, playbooks,
    research findings, and tools stored in the brain.

    When to use: When you need reference material or frameworks. Filter by
    category for specific types. For semantic search across knowledge, use
    quick_recall or recall instead.

    Returns: List of knowledge entries with category, title, and preview text.

    Args:
        category: Filter — framework, methodology, playbook, research, or tool.
                  None for all entries.
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
    """Delete a specific item from the brain by table and UUID.

    When to use: To remove outdated, incorrect, or duplicate entries. Deletion
    is permanent — there is no undo. Get the item_id from search results or
    list views.

    Returns: Confirmation of deletion or error if item not found.

    Args:
        table: Source table — pattern, experience, example, or knowledge
        item_id: UUID of the item to delete (from search results)
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
    """Check health metrics of your Second Brain — memory count, pattern
    distribution, experience count, graph status, and topic coverage.

    When to use: For a quick overview of brain state. For detailed setup
    progress, use brain_setup. For pattern details, use pattern_registry.

    Returns: Health summary with memory count, pattern distribution by
    confidence, experience count, graph provider status, and topic breakdown.
    """
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
    """Search the knowledge graph for relationships between entities —
    people, concepts, patterns, and experiences connected through Graphiti.

    When to use: When you need to understand HOW things are connected, not
    just find them. For content/memory search, use quick_recall. For entity
    lookup, use graph_entity_search.

    Returns: List of directed relationships (source --[type]--> target).

    Args:
        query: What to search for in the graph (e.g., "content strategy")
        limit: Maximum relationships to return (default: 10)
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
    """Check Graphiti knowledge graph connectivity and backend status.

    When to use: To verify the graph backend is running and accessible.
    For brain-wide health, use brain_health instead.

    Returns: Status (healthy/error), backend type, and error details if any.
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
async def graph_entity_search(query: str, limit: int = 10) -> str:
    """Find entities (people, concepts, topics) in the knowledge graph by name
    or description. Returns entity details, not relationships.

    When to use: To find specific entities before exploring their connections
    with graph_entity_context or graph_traverse. For relationship search,
    use graph_search instead.

    Returns: List of entities with name, labels, and summary.

    Args:
        query: Entity name or description to search for
        limit: Maximum results (default: 10)
    """
    deps = _get_deps()
    if not deps.graphiti_service:
        return "Entity search unavailable — Graphiti not configured."
    try:
        async with asyncio.timeout(deps.config.api_timeout_seconds):
            entities = await deps.graphiti_service.search_entities(
                query, limit=limit
            )
        if not entities:
            return "No entities found matching query."
        formatted = ["## Entities Found"]
        for e in entities:
            name = e.get("name", "?")
            summary = e.get("summary", "")
            labels = ", ".join(e.get("labels", [])) if e.get("labels") else ""
            line = f"- **{name}**"
            if labels:
                line += f" [{labels}]"
            if summary:
                line += f": {summary}"
            formatted.append(line)
        return "\n".join(formatted)
    except TimeoutError:
        logger.warning("MCP graph_entity_search timed out after %ds", deps.config.api_timeout_seconds)
        return f"Entity search timed out after {deps.config.api_timeout_seconds}s."
    except Exception as e:
        logger.warning("graph_entity_search failed: %s", type(e).__name__)
        return f"Entity search failed: {type(e).__name__}"


@server.tool()
async def graph_entity_context(entity_uuid: str) -> str:
    """Get all relationships for a specific entity — both incoming and outgoing
    connections. Shows how an entity relates to the rest of the knowledge graph.

    When to use: After finding an entity via graph_entity_search, use this to
    explore its connections. For broader traversal, use graph_traverse.

    Returns: Entity details with lists of incoming and outgoing relationships.

    Args:
        entity_uuid: UUID of the entity (from graph_entity_search results)
    """
    deps = _get_deps()
    if not deps.graphiti_service:
        return "Entity context unavailable — Graphiti not configured."
    try:
        async with asyncio.timeout(deps.config.api_timeout_seconds):
            ctx = await deps.graphiti_service.get_entity_context(entity_uuid)
        entity = ctx.get("entity")
        if not entity:
            return f"Entity {entity_uuid} not found."
        rels = ctx.get("relationships", [])
        formatted = [f"## {entity.get('name', '?')}"]
        if entity.get("summary"):
            formatted.append(f"_{entity['summary']}_\n")
        if not rels:
            formatted.append("No relationships found.")
        else:
            outgoing = [r for r in rels if r.get("direction") == "outgoing"]
            incoming = [r for r in rels if r.get("direction") == "incoming"]
            if outgoing:
                formatted.append("### Outgoing")
                for r in outgoing:
                    fact = r.get("fact", r.get("type", "?"))
                    formatted.append(f"- → {r.get('connected_entity', '?')}: {fact}")
            if incoming:
                formatted.append("### Incoming")
                for r in incoming:
                    fact = r.get("fact", r.get("type", "?"))
                    formatted.append(f"- ← {r.get('connected_entity', '?')}: {fact}")
        return "\n".join(formatted)
    except TimeoutError:
        logger.warning("MCP graph_entity_context timed out after %ds", deps.config.api_timeout_seconds)
        return f"Entity context timed out after {deps.config.api_timeout_seconds}s."
    except Exception as e:
        logger.warning("graph_entity_context failed: %s", type(e).__name__)
        return f"Entity context failed: {type(e).__name__}"


@server.tool()
async def graph_traverse(entity_uuid: str, max_hops: int = 2, limit: int = 20) -> str:
    """Traverse the knowledge graph from a starting entity, following
    relationships up to N hops deep. Discovers indirect connections.

    When to use: To explore how far-reaching an entity's influence is, or to
    find indirect connections between concepts. Start with graph_entity_search
    to find the starting entity UUID.

    Returns: Multi-hop relationship paths from the starting entity.

    Args:
        entity_uuid: Starting entity UUID (from graph_entity_search)
        max_hops: Maximum relationship hops to follow (default: 2, max: 5)
        limit: Maximum total relationships to return (default: 20)
    """
    deps = _get_deps()
    if not deps.graphiti_service:
        return "Graph traversal unavailable — Graphiti not configured."
    max_hops = min(max_hops, 5)
    try:
        async with asyncio.timeout(deps.config.api_timeout_seconds * 2):
            rels = await deps.graphiti_service.traverse_neighbors(
                entity_uuid, max_hops=max_hops, limit=limit
            )
        if not rels:
            return "No connections found from this entity."
        formatted = [f"## Graph Traversal (max {max_hops} hops)"]
        for r in rels:
            src = r.get("source", "?")
            rel = r.get("relationship", "?")
            tgt = r.get("target", "?")
            formatted.append(f"- {src} --[{rel}]--> {tgt}")
        return "\n".join(formatted)
    except TimeoutError:
        logger.warning("MCP graph_traverse timed out")
        return "Graph traversal timed out."
    except Exception as e:
        logger.warning("graph_traverse failed: %s", type(e).__name__)
        return f"Graph traversal failed: {type(e).__name__}"


@server.tool()
async def graph_communities(query: str = "", limit: int = 5) -> str:
    """Discover topic communities in the knowledge graph — clusters of
    densely connected entities that represent coherent knowledge domains.

    When to use: To understand the brain's knowledge structure at a high level.
    For specific entity lookup, use graph_entity_search. For relationship
    exploration, use graph_search.

    Returns: Community clusters with member entities and connection density.

    Args:
        query: Optional filter to find communities related to a topic
        limit: Maximum communities to return (default: 5)
    """
    deps = _get_deps()
    if not deps.graphiti_service:
        return "Community search unavailable — Graphiti not configured."
    try:
        async with asyncio.timeout(deps.config.api_timeout_seconds):
            communities = await deps.graphiti_service.search_communities(
                query or "community", limit=limit
            )
        if not communities:
            return "No communities found."
        formatted = ["## Knowledge Communities"]
        for c in communities:
            name = c.get("name", "?")
            summary = c.get("summary", "")
            formatted.append(f"- **{name}**")
            if summary:
                formatted.append(f"  {summary}")
        return "\n".join(formatted)
    except TimeoutError:
        logger.warning("MCP graph_communities timed out")
        return "Community search timed out."
    except Exception as e:
        logger.warning("graph_communities failed: %s", type(e).__name__)
        return f"Community search failed: {type(e).__name__}"


@server.tool()
async def graph_advanced_search(
    query: str,
    limit: int = 10,
    node_labels: str = "",
    edge_types: str = "",
    created_after: str = "",
    created_before: str = "",
) -> str:
    """Advanced graph search with filtering by entity type, edge type,
    and date range.

    When to use: When basic graph_search returns too many results and you need
    to narrow by entity type, edge type, or time range. For simple graph queries,
    use graph_search instead.

    Returns: Filtered relationships, entities, and communities with relevance.

    Args:
        query: Search query text
        limit: Maximum results (default: 10)
        node_labels: Comma-separated entity type filter (e.g., "Person,Organization")
        edge_types: Comma-separated edge type filter (e.g., "WORKS_AT,KNOWS")
        created_after: ISO date filter (e.g., "2024-01-01")
        created_before: ISO date filter (e.g., "2024-12-31")
    """
    deps = _get_deps()
    if not deps.graphiti_service:
        return "Advanced search unavailable — Graphiti not configured."
    try:
        labels = [lbl.strip() for lbl in node_labels.split(",") if lbl.strip()] or None
        types = [t.strip() for t in edge_types.split(",") if t.strip()] or None
        async with asyncio.timeout(deps.config.api_timeout_seconds):
            result = await deps.graphiti_service.advanced_search(
                query,
                limit=limit,
                node_labels=labels,
                edge_types=types,
                created_after=created_after or None,
                created_before=created_before or None,
            )
        edges = result.get("edges", [])
        nodes = result.get("nodes", [])
        communities = result.get("communities", [])
        if not edges and not nodes and not communities:
            return "No results found for advanced search."
        formatted = []
        if edges:
            formatted.append("## Relationships")
            for e in edges:
                formatted.append(
                    f"- {e.get('source', '?')} --[{e.get('relationship', '?')}]--> {e.get('target', '?')}"
                )
        if nodes:
            formatted.append("\n## Entities")
            for n in nodes:
                formatted.append(f"- **{n.get('name', '?')}**: {n.get('summary', '')}")
        if communities:
            formatted.append("\n## Communities")
            for c in communities:
                formatted.append(f"- **{c.get('name', '?')}**: {c.get('summary', '')}")
        return "\n".join(formatted)
    except TimeoutError:
        logger.warning("MCP graph_advanced_search timed out")
        return "Advanced search timed out."
    except Exception as e:
        logger.warning("graph_advanced_search failed: %s", type(e).__name__)
        return f"Advanced search failed: {type(e).__name__}"


@server.tool()
async def consolidate_brain(min_cluster_size: int = 3) -> str:
    """Analyze and consolidate the brain's memory into coherent clusters.
    Identifies related memories, suggests merges, and detects gaps.

    When to use: Periodically (weekly/monthly) to keep the brain organized.
    Finds redundant memories that can be merged and topics with insufficient
    coverage.

    Returns: Cluster summary with merge suggestions, gap analysis, and
    consolidation recommendations.

    Args:
        min_cluster_size: Minimum memories to form a cluster (default: 3)
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
        logger.warning("MCP consolidate_brain timed out after %ds", timeout)
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
    """Generate a growth report showing brain activity, pattern evolution, and
    learning velocity over a time period.

    When to use: For periodic progress review. Shows pattern creation, confidence
    transitions, review scores, and growth milestones. For current state only,
    use brain_health instead.

    Returns: Growth metrics, pattern activity, quality trends, milestones,
    and stale pattern warnings.

    Args:
        days: Lookback period in days (default: 30)
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
    """List all available content types — built-in and custom — with their
    configuration (mode, word count, built-in status).

    When to use: To see what content types are available for create_content
    and review_content. For managing types, use manage_content_type.

    Returns: Table of content types with slug, name, mode, word count, and
    built-in flag.
    """
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

    When to use: To create custom content types for create_content and
    review_content, or to remove ones no longer needed. For listing types,
    use list_content_types.

    Returns: Confirmation of add/remove action.

    Args:
        action: 'add' to create/update a content type, 'remove' to delete it
        slug: Content type slug in kebab-case (e.g., 'newsletter', 'blog-post')
        name: Human-readable name (required for 'add')
        default_mode: Communication mode — casual, professional, or formal
        structure_hint: Composition guide (required for 'add', e.g., 'Hook -> Body -> CTA')
        max_words: Target word count (default: 500)
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
    """Raw vector similarity search using pgvector embeddings. Bypasses the
    recall agent for direct embedding-to-embedding matching on a specific table.

    When to use: For precise vector matching on a specific table when you know
    exactly where to look. For general memory search, prefer quick_recall (which
    combines Mem0 + pgvector + reranking). For multi-table search, use recall_deep.

    Returns: Matches ranked by cosine similarity with score, title, and preview.

    Args:
        query: Text to embed and search (generates embedding automatically)
        table: Table to search — memory_content, patterns, examples, knowledge_repo
               (default: memory_content)
        limit: Maximum results (default: 10)
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
        logger.warning("MCP vector_search timed out after %ds", timeout)
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
    """Create a new project for lifecycle tracking through plan -> execute -> review -> learn stages.

    When to use: Starting a new initiative. Use advance_project to move through stages.

    Returns: Project name, ID, initial stage, and next action.

    Args:
        name: Project name (e.g., "Q4 Content Campaign")
        category: Project type — content, prospects, clients, products, or general
        description: Optional project description and goals
    """
    try:
        name = _validate_mcp_input(name, label="name")
    except ValueError as e:
        return str(e)
    deps = _get_deps()
    timeout = deps.config.api_timeout_seconds
    try:
        project_data = {"name": name, "category": category, "lifecycle_stage": "planning"}
        if description:
            project_data["description"] = description
        async with asyncio.timeout(timeout):
            result = await deps.storage_service.create_project(project_data)
        if result:
            return (
                f"Project created: {result.get('name', name)} "
                f"(ID: {result.get('id', 'unknown')})\n"
                f"Stage: planning\n"
                f"Next: Add plan artifact or advance to executing"
            )
        return "Failed to create project."
    except TimeoutError:
        return f"Project creation timed out after {timeout}s."
    except Exception as e:
        logger.error("Failed to create project: %s", e)
        return "Failed to create project. Check server logs for details."


@server.tool()
async def project_status(project_id: str) -> str:
    """Get current status, metadata, and artifacts for a specific project.

    When to use: To check a project's progress, stage, and associated artifacts.
    For listing all projects, use list_projects instead.

    Returns: Project name, stage, category, review score, and artifact list.

    Args:
        project_id: Project UUID (from list_projects or create_project)
    """
    try:
        project_id = _validate_mcp_input(project_id, label="project_id")
    except ValueError as e:
        return str(e)
    deps = _get_deps()
    timeout = deps.config.api_timeout_seconds
    try:
        async with asyncio.timeout(timeout):
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
    except TimeoutError:
        return f"Project status check timed out after {timeout}s."
    except Exception as e:
        logger.error("Failed to get project status: %s", e)
        return "Failed to get project status. Check server logs for details."


@server.tool()
async def advance_project(project_id: str, target_stage: str | None = None) -> str:
    """Move a project to the next lifecycle stage or jump to a specific stage.
    Stages: planning -> executing -> reviewing -> learning -> complete.

    When to use: When a project reaches a milestone and should move forward.
    Omit target_stage to auto-advance to the next stage.

    Returns: Confirmation with previous and new stage.

    Args:
        project_id: Project UUID
        target_stage: Specific stage to jump to (optional — omit for auto-advance)
    """
    try:
        project_id = _validate_mcp_input(project_id, label="project_id")
    except ValueError as e:
        return str(e)
    deps = _get_deps()
    timeout = deps.config.api_timeout_seconds
    stage_order = ["planning", "executing", "reviewing", "learning", "complete"]
    try:
        async with asyncio.timeout(timeout):
            proj = await deps.storage_service.get_project(project_id)
            if not proj:
                return f"Project not found: {project_id}"
            current = proj.get("lifecycle_stage", "planning")
            if target_stage:
                if target_stage not in stage_order:
                    return f"Invalid stage: {target_stage}. Must be one of: {stage_order}"
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
    except TimeoutError:
        return f"Project advance timed out after {timeout}s."
    except Exception as e:
        logger.error("Failed to advance project: %s", e)
        return "Failed to advance project. Check server logs for details."


@server.tool()
async def list_projects(
    lifecycle_stage: str | None = None,
    category: str | None = None,
    limit: int = 20,
) -> str:
    """List all Second Brain projects with optional stage and category filters.

    When to use: To see all projects or filter by lifecycle stage or category.
    For details on a specific project, use project_status instead.

    Returns: Project list with name, stage, category, and description preview.

    Args:
        lifecycle_stage: Filter by stage — planning, executing, reviewing, learning, complete
        category: Filter by category — content, prospects, clients, products, general
        limit: Maximum projects to return (default: 20)
    """
    deps = _get_deps()
    timeout = deps.config.api_timeout_seconds
    try:
        async with asyncio.timeout(timeout):
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
    except TimeoutError:
        return f"Project listing timed out after {timeout}s."
    except Exception as e:
        logger.error("Failed to list projects: %s", e)
        return "Failed to list projects. Check server logs for details."


@server.tool()
async def update_project(
    project_id: str,
    name: str | None = None,
    description: str | None = None,
    category: str | None = None,
) -> str:
    """Update a project's name, description, or category.

    When to use: To correct or update project metadata. To change lifecycle stage,
    use advance_project instead.

    Returns: Updated project name and list of changed fields.

    Args:
        project_id: Project UUID (from list_projects or create_project)
        name: New name (optional)
        description: New description (optional)
        category: New category — content, prospects, clients, products, general (optional)
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
        logger.error("Failed to update project: %s", e)
        return "Failed to update project. Check server logs for details."


@server.tool()
async def delete_project(project_id: str) -> str:
    """Permanently delete a project and all its artifacts.

    When to use: To remove abandoned or duplicate projects. Deletion is permanent
    with no undo. Consider archiving (advance to 'complete') instead.

    Returns: Confirmation of deletion or error if not found.

    Args:
        project_id: Project UUID to delete (from list_projects)
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
        logger.error("Failed to delete project: %s", e)
        return "Failed to delete project. Check server logs for details."


@server.tool()
async def add_artifact(
    project_id: str,
    artifact_type: str,
    title: str | None = None,
    content: str | None = None,
) -> str:
    """Attach an artifact to a project — plans, drafts, reviews, outputs, or notes.

    When to use: To associate deliverables with a project for lifecycle tracking.
    Each artifact is typed and can hold content text.

    Returns: Confirmation with artifact type and ID.

    Args:
        project_id: Project UUID
        artifact_type: Artifact kind — plan, draft, review, output, or note
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
        logger.error("Failed to add artifact: %s", e)
        return "Failed to add artifact. Check server logs for details."


@server.tool()
async def delete_artifact(artifact_id: str) -> str:
    """Remove a specific artifact from a project by its UUID.

    When to use: To clean up outdated or incorrect artifacts. Get the
    artifact_id from project_status output.

    Returns: Confirmation of deletion or error if not found.

    Args:
        artifact_id: Artifact UUID (from project_status output)
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
        logger.error("Failed to delete artifact: %s", e)
        return "Failed to delete artifact. Check server logs for details."


@server.tool()
async def search_experiences(
    category: str | None = None,
    limit: int = 20,
) -> str:
    """Browse past work experiences — meeting outcomes, project learnings,
    and client interactions stored in the brain.

    When to use: When recalling specific past work events. Use category to
    filter by type. For semantic search across experiences, use quick_recall
    or recall instead. For pattern search, use search_patterns.

    Returns: List of experiences with title, category, date, and description.

    Args:
        category: Filter by category (e.g., client-work, product-launch) or None for all
        limit: Maximum experiences to return (default: 20)
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
        logger.error("Failed to search experiences: %s", e)
        return "Failed to search experiences. Check server logs for details."


@server.tool()
async def search_patterns(
    topic: str | None = None,
    confidence: str | None = None,
    keyword: str | None = None,
    limit: int = 30,
) -> str:
    """Search the pattern registry by keyword, topic, or confidence level.
    Patterns are reusable strategies extracted from successful work.

    When to use: When you need specific writing patterns, content strategies,
    or engagement approaches. Use keyword for text search, topic/confidence
    for filtering. For the full registry view, use pattern_registry instead.

    Returns: List of patterns with confidence level, topic, and preview text.

    Args:
        topic: Filter by topic (e.g., messaging, brand-voice, content, strategy)
        confidence: Filter by confidence — HIGH, MEDIUM, or LOW
        keyword: Text to match in pattern name or text (case-insensitive)
        limit: Maximum results (default: 30)
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
        logger.error("Failed to search patterns: %s", e)
        return "Failed to search patterns. Check server logs for details."


@server.tool()
async def ingest_example(
    content_type: str,
    title: str,
    content: str,
    notes: str | None = None,
) -> str:
    """Store a content example in the brain for future reference during content
    creation and review. Examples serve as quality benchmarks for their content type.

    When to use: When you have a good content sample (email, post, case study)
    that should be used as reference. The content will be embedded for semantic
    search.

    Returns: Confirmation with the stored example ID.

    Args:
        content_type: Format type — linkedin, email, case-study, newsletter, etc.
        title: Example title (e.g., "Q4 Results LinkedIn Post")
        content: Full text of the content example
        notes: Optional notes about why this example is notable
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
        logger.error("Failed to ingest example: %s", e)
        return "Failed to ingest example. Check server logs for details."


@server.tool()
async def ingest_knowledge(
    category: str,
    title: str,
    content: str,
    tags: str | None = None,
) -> str:
    """Store a knowledge entry in the brain — frameworks, methodologies,
    research findings, playbooks, or tools. Embedded for semantic retrieval.

    When to use: When you have reference material to store for future use.
    Unlike learn (which extracts patterns from raw text), ingest_knowledge
    stores structured knowledge entries directly.

    Returns: Confirmation with the stored knowledge entry ID.

    Args:
        category: Entry type — audience, product, competitors, positioning, etc.
        title: Entry title (e.g., "SPIN Selling Framework")
        content: Full knowledge content text
        tags: Comma-separated tags for filtering (e.g., "enterprise,saas,2026")
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
        logger.error("Failed to ingest knowledge: %s", e)
        return "Failed to ingest knowledge. Check server logs for details."


@server.tool()
async def brain_setup() -> str:
    """Check brain onboarding/setup progress — which memory categories are
    populated and what steps remain to fully configure the brain.

    When to use: During initial setup to track onboarding progress. For
    ongoing health monitoring, use brain_health instead.

    Returns: Completion percentage, step-by-step checklist with status,
    and next actions for missing categories.
    """
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
        logger.error("Failed to check setup: %s", e)
        return "Failed to check setup. Check server logs for details."


@server.tool()
async def pattern_registry() -> str:
    """View the full pattern registry — all patterns with confidence, usage count,
    and status in a comprehensive overview.

    When to use: For a complete picture of all patterns. For filtered search,
    use search_patterns instead. For brain-wide health, use brain_health.

    Returns: Formatted pattern registry with confidence levels, usage counts,
    and topic groupings.
    """
    deps = _get_deps()
    try:
        from second_brain.agents.utils import format_pattern_registry
        registry = await deps.storage_service.get_pattern_registry()
        return format_pattern_registry(registry, config=deps.config)
    except Exception as e:
        logger.error("Failed to load pattern registry: %s", e)
        return "Failed to load pattern registry. Check server logs for details."


# --- Operations & Advisory Agents ---

@server.tool()
async def coaching_session(request: str, session_type: str = "morning") -> str:
    """Get daily accountability coaching — planning, productivity, and work-life
    management powered by your brain's context and patterns.

    When to use: For daily planning (morning), reflection (evening), mid-day
    check-ins, or when feeling overwhelmed (intervention).

    Returns: Session summary, coaching notes, and next action.

    Args:
        request: Your coaching need (e.g., "Help me plan today", "I'm overwhelmed")
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
        logger.warning("MCP coaching_session timed out after %ds", timeout)
        return f"Coaching session timed out after {timeout}s."
    out = result.output
    parts = [f"Session: {out.session_type}", f"Next action: {out.next_action}"]
    if out.coaching_notes:
        parts.append(out.coaching_notes)
    return "\n".join(parts)


@server.tool()
async def prioritize_tasks(tasks: str) -> str:
    """Score and prioritize tasks using PMO methodology — impact, urgency,
    effort, and alignment scoring.

    When to use: When you have multiple tasks and need to decide what to work
    on first. Provides scored rankings with category labels.

    Returns: Ranked task list with scores and category breakdown.

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
        logger.warning("MCP prioritize_tasks timed out after %ds", timeout)
        return f"Task prioritization timed out after {timeout}s."
    out = result.output
    lines = [out.coaching_message]
    for t in out.scored_tasks[:5]:
        lines.append(f"  {t.task_name}: {t.total_score:.0f} ({t.category})")
    return "\n".join(lines)


@server.tool()
async def compose_email(request: str) -> str:
    """Compose emails using your brand voice, patterns, and client context.

    When to use: For drafting or managing emails. Uses brain context for
    personalization. For general content creation, use create_content instead.

    Returns: Email with subject line, body, and status.

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
        logger.warning("MCP compose_email timed out after %ds", timeout)
        return f"Email composition timed out after {timeout}s."
    out = result.output
    return f"Subject: {out.subject}\n\n{out.body}\n\nStatus: {out.status}"


@server.tool()
async def ask_claude_specialist(question: str) -> str:
    """Ask a verified question about Claude Code, Pydantic AI, or AI development
    tools. Answers are confidence-rated.

    When to use: For technical questions about Claude Code, Pydantic AI, or
    AI development patterns. For general brain questions, use ask instead.

    Returns: Confidence-rated answer ([HIGH/MEDIUM/LOW] + answer text).

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
        logger.warning("MCP ask_claude_specialist timed out after %ds", timeout)
        return f"Specialist query timed out after {timeout}s."
    out = result.output
    return f"[{out.confidence_level}] {out.answer}"


# --- Chief of Staff / Orchestration ---

@server.tool()
async def run_brain_pipeline(request: str, steps: str = "") -> str:
    """Run a multi-agent pipeline — chains multiple agents in sequence where
    each agent's output feeds into the next. Auto-routes via Chief of Staff
    if no steps specified.

    When to use: For multi-step workflows like content creation pipelines
    (recall->create->review) or learn-from-content flows (review->learn).
    For single-agent tasks, call the specific tool directly.

    Returns: Final pipeline output (from the last agent in the chain).

    Args:
        request: The request to process through the pipeline.
        steps: Comma-separated agent names (e.g., "recall,create,review").
               Empty = auto-route via Chief of Staff.
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
            logger.warning("MCP run_brain_pipeline routing timed out after %ds", timeout)
            return f"Pipeline routing timed out after {timeout}s."
        routing_output = routing.output
        if routing_output.target_agent == "pipeline":
            step_list = list(routing_output.pipeline_steps)
        else:
            step_list = [routing_output.target_agent]
        # Short-circuit conversational routing — no pipeline needed
        if step_list == ["conversational"]:
            return (
                "Hey! I'm your Second Brain assistant. "
                "Ask me anything — I can search your memory, help with content, "
                "review your work, or answer questions using your accumulated knowledge."
            )
    else:
        step_list = [s.strip() for s in steps.split(",") if s.strip()]

    pipeline_timeout = deps.config.api_timeout_seconds * max(len(step_list), 1) * deps.config.mcp_review_timeout_multiplier
    try:
        async with asyncio.timeout(pipeline_timeout):
            results = await run_pipeline(
                steps=step_list,
                initial_prompt=request,
                deps=deps,
                model=model,
            )
    except TimeoutError:
        logger.warning("MCP run_brain_pipeline execution timed out after %ds (%d steps)", pipeline_timeout, len(step_list))
        return f"Pipeline timed out after {pipeline_timeout}s ({len(step_list)} steps). Try fewer steps or a simpler request."
    final = results.get("final")
    return str(final) if final else "Pipeline completed with no output."


@server.tool()
async def analyze_clarity(content: str) -> str:
    """Analyze content for readability and clarity issues — jargon, complexity,
    information density, and abstract language.

    When to use: For focused readability analysis. Unlike review_content (which
    scores across all quality dimensions), this specifically targets clarity.

    Returns: Overall readability rating, critical issue count, and specific
    findings with severity, location, and suggestions.

    Args:
        content: Text content to analyze for clarity issues
    """
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
        logger.warning("MCP analyze_clarity timed out after %ds", timeout)
        return f"Clarity analysis timed out after {timeout}s."
    out = result.output
    lines = [f"Readability: {out.overall_readability} ({out.critical_count} critical)"]
    for f in out.findings[:10]:
        lines.append(f"[{f.severity}] {f.location}: {f.issue} -> {f.suggestion}")
    return "\n".join(lines)


@server.tool()
async def synthesize_feedback(findings: str) -> str:
    """Consolidate review findings into actionable improvement themes.

    When to use: After running review_content or analyze_clarity, feed the
    findings here to get prioritized improvement themes with effort estimates.

    Returns: Theme count, total implementation hours, and prioritized themes
    with effort estimates and specific actions.

    Args:
        findings: Review findings text (from review_content or analyze_clarity output)
    """
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
        logger.warning("MCP synthesize_feedback timed out after %ds", timeout)
        return f"Feedback synthesis timed out after {timeout}s."
    out = result.output
    lines = [f"{out.total_themes_output} themes, {out.implementation_hours:.1f}h total"]
    for t in out.themes:
        lines.append(f"[{t.priority}] {t.title} ({t.effort_minutes}min): {t.action}")
    return "\n".join(lines)


@server.tool()
async def find_template_opportunities(deliverable: str) -> str:
    """Analyze a deliverable for reusable template opportunities — identifies
    repeatable structures that could be templatized for future use.

    When to use: After completing a deliverable that might contain reusable
    patterns or structures. Identifies template candidates with usage guidance.

    Returns: Template opportunity count and list with names and usage guidance.

    Args:
        deliverable: Completed deliverable text to analyze for template patterns
    """
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
        logger.warning("MCP find_template_opportunities timed out after %ds", timeout)
        return f"Template analysis timed out after {timeout}s."
    out = result.output
    lines = [
        f"Template: {out.name}",
        f"Type: {out.content_type}",
        "",
        "--- WRITEPRINT ---",
        out.writeprint,
        "--- END WRITEPRINT ---",
        "",
        "--- STRUCTURE ---",
        out.structure_hint,
        "--- END STRUCTURE ---",
        "",
        f"When to use: {out.when_to_use}",
    ]
    if out.when_not_to_use:
        lines.append(f"When NOT to use: {out.when_not_to_use}")
    if out.customization_guide:
        lines.extend(["", f"Customization: {out.customization_guide}"])
    lines.extend([
        f"Tags: {', '.join(out.tags)}",
        "",
        "--- TEMPLATE BODY ---",
        out.body,
        "--- END TEMPLATE ---",
        "",
        "Use save_template to persist this to your template bank.",
    ])
    return "\n".join(lines)


@server.tool()
async def save_template(
    name: str,
    content_type: str,
    body: str,
    when_to_use: str = "",
    structure_hint: str = "",
    writeprint: str = "",
    tags: str = "",
    description: str = "",
    customization_guide: str = "",
    when_not_to_use: str = "",
    source_deliverable: str = "",
    ai_generated: bool = False,
) -> str:
    """Save a reusable content template to the template bank for future use.

    When to use: After identifying or creating a reusable content structure.
    Save templates you want to reuse across content creation sessions.

    Returns: Confirmation with the stored template ID and name.

    Args:
        name: Template name (e.g., "LinkedIn Thought Leadership Post")
        content_type: Content type slug — linkedin, email, case-study, newsletter, etc.
        body: Full template text with [PLACEHOLDER] markers for customizable parts
        when_to_use: When this template should be applied
        structure_hint: Section flow summary (e.g., "Hook -> Body -> CTA")
        writeprint: Voice/tone/style fingerprint of the content
        tags: Comma-separated tags for filtering (e.g., "thought-leadership, professional")
        description: Brief description of the template
        customization_guide: What to customize vs keep standard
        when_not_to_use: When NOT to use this template
        source_deliverable: Original content this was deconstructed from
        ai_generated: Whether this template was AI-generated
    """
    try:
        name = _validate_mcp_input(name, label="name")
        content_type = _validate_mcp_input(content_type, label="content_type")
        body = _validate_mcp_input(body, label="body")
    except ValueError as e:
        return str(e)
    deps = _get_deps()
    try:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
        template_data: dict = {
            "name": name,
            "content_type": content_type,
            "body": body,
            "when_to_use": when_to_use,
            "structure_hint": structure_hint,
            "writeprint": writeprint,
            "tags": tag_list,
            "description": description,
            "customization_guide": customization_guide,
            "when_not_to_use": when_not_to_use,
            "source_deliverable": source_deliverable,
            "ai_generated": ai_generated,
        }
        result = await deps.storage_service.upsert_template(template_data)
        if result:
            return (
                f"Template saved: {name}\n"
                f"Type: {content_type}\n"
                f"ID: {result.get('id', 'unknown')}\n"
                f"Tags: {', '.join(tag_list) or 'none'}"
            )
        return "Failed to save template."
    except Exception as e:
        logger.error("Failed to save template: %s", e)
        return "Failed to save template. Check server logs for details."


@server.tool()
async def list_templates(content_type: str = "", tag: str = "") -> str:
    """Browse the template bank — list available reusable content templates.

    When to use: Before creating content, to check if a matching template
    exists. Also useful for reviewing what templates are available.

    Returns: List of templates with names, content types, and structure hints.

    Args:
        content_type: Optional filter by content type slug (linkedin, email, etc.)
        tag: Optional filter by tag
    """
    deps = _get_deps()
    try:
        tags = [tag] if tag else None
        templates = await deps.storage_service.get_templates(
            content_type=content_type or None, tags=tags,
        )
        if not templates:
            return "No templates found in the bank."
        lines = [f"{len(templates)} templates found:"]
        for t in templates:
            tags_str = ", ".join(t.get("tags", [])) or "none"
            lines.append(
                f"- [{t.get('content_type', '?')}] {t.get('name', 'Untitled')} "
                f"(tags: {tags_str}, uses: {t.get('use_count', 0)})\n"
                f"  Structure: {t.get('structure_hint', 'N/A')}\n"
                f"  ID: {t.get('id', 'unknown')}"
            )
        return "\n".join(lines)
    except Exception as e:
        logger.error("Failed to list templates: %s", e)
        return "Failed to list templates. Check server logs for details."


@server.tool()
async def get_template(template_id: str) -> str:
    """Retrieve a specific template's full content from the template bank.

    When to use: After finding a template via list_templates, use this to
    get the complete template body with placeholder markers.

    Returns: Full template details including body, usage guidance, and metadata.

    Args:
        template_id: UUID of the template to retrieve
    """
    try:
        template_id = _validate_mcp_input(template_id, label="template_id")
    except ValueError as e:
        return str(e)
    deps = _get_deps()
    try:
        tmpl = await deps.storage_service.get_template(template_id)
        if not tmpl:
            return f"Template not found: {template_id}"
        lines = [
            f"Template: {tmpl.get('name', 'Untitled')}",
            f"Type: {tmpl.get('content_type', '?')}",
            f"Tags: {', '.join(tmpl.get('tags', [])) or 'none'}",
            f"Structure: {tmpl.get('structure_hint', 'N/A')}",
            f"When to use: {tmpl.get('when_to_use', 'N/A')}",
            f"When NOT to use: {tmpl.get('when_not_to_use', 'N/A')}",
            f"Customization: {tmpl.get('customization_guide', 'N/A')}",
            "",
            "--- TEMPLATE BODY ---",
            tmpl.get("body", "(empty)"),
            "--- END TEMPLATE ---",
        ]
        return "\n".join(lines)
    except Exception as e:
        logger.error("Failed to get template: %s", e)
        return "Failed to get template. Check server logs for details."


@server.tool()
async def write_linkedin_hooks(
    topic: str, hook_type: str = "", user_id: str = "",
) -> str:
    """Generate scroll-stopping LinkedIn hook variations for a topic.
    Returns 3-7 hook options across different categories.

    When to use: Before writing a LinkedIn post, when you need a strong opening
    line. Use with create_content for the full post.

    Args:
        topic: What the post is about (e.g., "launching a coaching business",
               "lessons from failing at email marketing")
        hook_type: Optional preferred hook category — bold-statement,
                   self-deprecating, curiosity-gap, contrarian, stat-lead,
                   question, dialogue-scene, meta-platform
        user_id: Voice profile to match (e.g., "uttam"). Empty = default.
    """
    try:
        topic = _validate_mcp_input(topic, label="topic")
    except ValueError as e:
        return str(e)
    try:
        effective_uid = _validate_user_id(user_id)
    except ValueError as e:
        return str(e)

    deps = _get_deps()
    model = _get_model("hook_writer")
    from second_brain.agents.hook_writer import hook_writer_agent

    prompt = f"Write LinkedIn hooks for: {topic}"
    if hook_type:
        prompt += f"\nPreferred hook category: {hook_type}"
    if effective_uid:
        prompt += f"\nVoice profile: {effective_uid}"

    timeout = deps.config.api_timeout_seconds
    try:
        async with asyncio.timeout(timeout):
            result = await hook_writer_agent.run(prompt, deps=deps, model=model)
    except TimeoutError:
        logger.warning("MCP write_linkedin_hooks timed out after %ds", timeout)
        return f"Hook writing timed out after {timeout}s."
    out = result.output

    parts = [f"# LinkedIn Hooks: {topic}\n"]
    parts.append(f"**Category**: {out.hook_type}")
    parts.append(f"**Angle**: {out.topic_angle}\n")
    for i, hook in enumerate(out.hooks, 1):
        parts.append(f"{i}. {hook}")
    if out.reasoning:
        parts.append(f"\n**Why these work**: {out.reasoning}")

    return "\n".join(parts)


@server.tool()
async def linkedin_comment(
    post_content: str, context: str = "", user_id: str = "",
) -> str:
    """Write an authentic comment on someone's LinkedIn post using your brain context.
    Pulls expertise, meeting notes, and subject matter knowledge to craft a response
    that sounds like YOU — not AI-generated.

    When to use: When you want to engage with someone's LinkedIn post. The agent
    will analyze the post and write a comment that adds genuine value.

    Args:
        post_content: The LinkedIn post you want to comment on (paste the full text)
        context: Optional additional context (e.g., "I know this person from a conference",
                 "We discussed this topic in our team meeting last week")
        user_id: Voice profile to use (e.g., "uttam"). Empty = default.
    """
    try:
        post_content = _validate_mcp_input(post_content, label="post_content")
    except ValueError as e:
        return str(e)
    try:
        effective_uid = _validate_user_id(user_id)
    except ValueError as e:
        return str(e)

    deps = _get_deps()
    model = _get_model("linkedin_engagement")
    from second_brain.agents.linkedin_engagement import linkedin_engagement_agent

    prompt = f"Write a comment on this LinkedIn post:\n\n{post_content}"
    prompt += "\n\nEngagement type: comment"
    if context:
        prompt += f"\n\nAdditional context: {context}"
    if effective_uid:
        prompt += f"\nVoice profile: {effective_uid}"

    timeout = deps.config.api_timeout_seconds
    try:
        async with asyncio.timeout(timeout):
            result = await linkedin_engagement_agent.run(
                prompt, deps=deps, model=model,
            )
    except TimeoutError:
        logger.warning("MCP linkedin_comment timed out after %ds", timeout)
        return f"Comment generation timed out after {timeout}s."
    out = result.output

    parts = [f"# LinkedIn Comment\n", out.response]
    parts.append(f"\n---")
    parts.append(f"**Tone**: {out.tone}")
    parts.append(f"**Words**: {out.word_count}")
    if out.context_used:
        parts.append(f"**Context**: {', '.join(out.context_used)}")
    if out.notes:
        parts.append(f"\n**Notes**: {out.notes}")
    if out.error:
        parts.append(f"\n⚠️ **Degraded**: {out.error}")
    return "\n".join(parts)


@server.tool()
async def linkedin_reply(
    post_content: str, comment_to_reply: str, context: str = "",
    user_id: str = "",
) -> str:
    """Write an authentic reply to a comment on your LinkedIn post.
    Stays in context of the conversation and uses your brain knowledge.

    When to use: When someone comments on YOUR LinkedIn post and you want to
    reply thoughtfully without sounding generic or AI-generated.

    Args:
        post_content: Your original LinkedIn post text (for context)
        comment_to_reply: The comment you want to reply to
        context: Optional thread context (e.g., other comments in the thread)
        user_id: Voice profile to use (e.g., "uttam"). Empty = default.
    """
    try:
        post_content = _validate_mcp_input(post_content, label="post_content")
        comment_to_reply = _validate_mcp_input(comment_to_reply, label="comment")
    except ValueError as e:
        return str(e)
    try:
        effective_uid = _validate_user_id(user_id)
    except ValueError as e:
        return str(e)

    deps = _get_deps()
    model = _get_model("linkedin_engagement")
    from second_brain.agents.linkedin_engagement import linkedin_engagement_agent

    prompt = (
        f"Reply to this comment on your LinkedIn post.\n\n"
        f"## Your Original Post\n{post_content}\n\n"
        f"## Comment to Reply To\n{comment_to_reply}"
    )
    prompt += "\n\nEngagement type: reply"
    if context:
        prompt += f"\n\nThread context: {context}"
    if effective_uid:
        prompt += f"\nVoice profile: {effective_uid}"

    timeout = deps.config.api_timeout_seconds
    try:
        async with asyncio.timeout(timeout):
            result = await linkedin_engagement_agent.run(
                prompt, deps=deps, model=model,
            )
    except TimeoutError:
        logger.warning("MCP linkedin_reply timed out after %ds", timeout)
        return f"Reply generation timed out after {timeout}s."
    out = result.output

    parts = [f"# LinkedIn Reply\n", out.response]
    parts.append(f"\n---")
    parts.append(f"**Tone**: {out.tone}")
    parts.append(f"**Words**: {out.word_count}")
    if out.context_used:
        parts.append(f"**Context**: {', '.join(out.context_used)}")
    if out.notes:
        parts.append(f"\n**Notes**: {out.notes}")
    if out.error:
        parts.append(f"\n⚠️ **Degraded**: {out.error}")
    return "\n".join(parts)


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
        # Configure Mem0 project settings (criteria retrieval, custom instructions)
        asyncio.run(_setup_mem0_project())

    try:
        if _transport in ("http", "sse"):
            _host = _os.environ.get("MCP_HOST", "127.0.0.1")
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
