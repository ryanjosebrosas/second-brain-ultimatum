"""Service-level MCP server for Claude SDK integration.

Exposes raw service functions (memory, storage) as MCP tools.
This server is used by the Claude SDK subprocess to interact with
Second Brain data WITHOUT going through agents (which would create
circular dependencies).

Run: python -m second_brain.service_mcp
"""

import json
import logging

from fastmcp import FastMCP

from second_brain.deps import BrainDeps, create_deps

logger = logging.getLogger(__name__)

# Initialize server with a distinct name (not "Second Brain" to avoid conflicts)
service_server = FastMCP("Second Brain Services")

MAX_INPUT_LENGTH = 10000  # Characters

# Deps initialized eagerly before server.run() via init_deps()
_deps: BrainDeps | None = None


def init_deps() -> None:
    """Initialize BrainDeps eagerly, BEFORE server.run() starts the event loop.

    Mem0's MemoryClient constructor makes synchronous HTTP calls that deadlock
    when called inside FastMCP's async event loop (both directly and via
    asyncio.to_thread). Initializing deps before the event loop starts avoids
    this entirely.
    """
    global _deps
    if _deps is None:
        _deps = create_deps()


async def _get_deps() -> BrainDeps:
    """Return pre-initialized BrainDeps.

    Deps MUST be initialized via init_deps() before server.run().
    Falls back to synchronous creation if not pre-initialized (e.g. in tests),
    but this may block the event loop.
    """
    global _deps
    if _deps is None:
        logger.warning("deps not pre-initialized, creating synchronously (may block)")
        _deps = create_deps()
    return _deps


def _validate_input(text: str, label: str = "input") -> str:
    """Validate service MCP tool text input."""
    if not text or not text.strip():
        raise ValueError(f"{label} cannot be empty")
    if len(text) > MAX_INPUT_LENGTH:
        raise ValueError(
            f"{label} too long ({len(text)} chars, max {MAX_INPUT_LENGTH})"
        )
    return text.strip()


# --- Memory Service Tools ---


@service_server.tool()
async def search_memory(query: str, limit: int = 10) -> str:
    """Search semantic memory for relevant content.

    Args:
        query: What to search for
        limit: Maximum number of results (default: 10)
    """
    try:
        query = _validate_input(query, "query")
    except ValueError as e:
        return str(e)
    deps = await _get_deps()
    try:
        result = await deps.memory_service.search(query, limit=limit)
        if not result.memories and not result.relations:
            return "No semantic matches found."
        formatted = []
        for r in result.memories:
            memory = r.get("memory", r.get("result", ""))
            score = r.get("score", 0)
            formatted.append(f"- [{score:.2f}] {memory}")
        if result.relations:
            formatted.append("\nGraph Relationships:")
            for rel in result.relations:
                src = rel.get("source", "?")
                relationship = rel.get("relationship", "?")
                tgt = rel.get("target", "?")
                formatted.append(f"- {src} --[{relationship}]--> {tgt}")
        return "\n".join(formatted)
    except Exception as e:
        logger.warning("search_memory failed: %s", type(e).__name__)
        return f"Memory search unavailable: {type(e).__name__}"


@service_server.tool()
async def search_memory_with_filters(
    query: str,
    category: str | None = None,
    topic: str | None = None,
    limit: int = 10,
) -> str:
    """Search semantic memory with metadata filters.

    Args:
        query: What to search for
        category: Filter by category (e.g., "pattern")
        topic: Filter by topic
        limit: Maximum results
    """
    try:
        query = _validate_input(query, "query")
    except ValueError as e:
        return str(e)
    deps = await _get_deps()
    try:
        filters = {}
        if category and topic:
            filters = {"AND": [{"category": category}, {"topic": topic}]}
        elif category:
            filters = {"category": category}
        elif topic:
            filters = {"topic": topic}

        result = await deps.memory_service.search_with_filters(
            query, metadata_filters=filters, limit=limit, enable_graph=True
        )
        if not result.memories and not result.relations:
            return "No filtered matches found."
        formatted = []
        if result.memories:
            for m in result.memories:
                memory = m.get("memory", m.get("result", ""))
                score = m.get("score", 0)
                formatted.append(f"- [{score:.2f}] {memory}")
        if result.relations:
            formatted.append("\nGraph Relationships:")
            for rel in result.relations:
                src = rel.get("source", "?")
                relationship = rel.get("relationship", "?")
                tgt = rel.get("target", "?")
                formatted.append(f"- {src} --[{relationship}]--> {tgt}")
        return "\n".join(formatted)
    except Exception as e:
        logger.warning("search_memory_with_filters failed: %s", type(e).__name__)
        return f"Filtered search unavailable: {type(e).__name__}"


@service_server.tool()
async def add_memory(text: str, category: str = "general", metadata: str = "") -> str:
    """Add a memory with metadata to Mem0.

    Args:
        text: The memory content to store
        category: Memory category
        metadata: JSON string of additional metadata
    """
    try:
        text = _validate_input(text, "text")
    except ValueError as e:
        return str(e)
    deps = await _get_deps()
    try:
        meta = {"category": category}
        if metadata:
            try:
                extra = json.loads(metadata)
                meta.update(extra)
            except json.JSONDecodeError:
                pass
        await deps.memory_service.add_with_metadata(text, metadata=meta)
        return f"Memory stored with category={category}"
    except Exception as e:
        logger.warning("add_memory failed: %s", type(e).__name__)
        return f"Failed to store memory: {type(e).__name__}"


# --- Storage Service Tools ---


@service_server.tool()
async def get_patterns(topic: str | None = None) -> str:
    """Get patterns from the pattern registry.

    Args:
        topic: Filter by topic (optional)
    """
    deps = await _get_deps()
    try:
        patterns = await deps.storage_service.get_patterns(topic=topic)
        if not patterns:
            return "No patterns found in registry."
        formatted = []
        for p in patterns:
            formatted.append(
                f"- [{p['confidence']}] {p['name']}: "
                f"{p.get('pattern_text', '')[:200]}"
            )
        return "\n".join(formatted)
    except Exception as e:
        return f"Pattern search unavailable: {type(e).__name__}"


@service_server.tool()
async def get_experiences(category: str | None = None) -> str:
    """Get past experiences from Supabase.

    Args:
        category: Filter by category (content, prospects, clients, general)
    """
    deps = await _get_deps()
    try:
        experiences = await deps.storage_service.get_experiences(category=category)
        if not experiences:
            return "No past experiences found."
        formatted = []
        for exp in experiences:
            score_str = f" (score: {exp['review_score']})" if exp.get("review_score") else ""
            formatted.append(f"- {exp['name']} [{exp['category']}]{score_str}")
        return "\n".join(formatted)
    except Exception as e:
        return f"Experience search unavailable: {type(e).__name__}"


@service_server.tool()
async def get_examples(content_type: str | None = None) -> str:
    """Get content examples from Supabase.

    Args:
        content_type: Filter by type (linkedin, email, etc.)
    """
    deps = await _get_deps()
    try:
        examples = await deps.storage_service.get_examples(content_type=content_type)
        if not examples:
            return "No content examples found."
        formatted = []
        for ex in examples:
            formatted.append(f"[{ex['content_type']}] {ex['title']}")
            formatted.append(ex.get("content", "")[:500])
            formatted.append("")
        return "\n".join(formatted)
    except Exception as e:
        return f"Example search unavailable: {type(e).__name__}"


@service_server.tool()
async def get_knowledge(category: str | None = None) -> str:
    """Get knowledge entries from Supabase.

    Args:
        category: Filter by category (framework, methodology, playbook, etc.)
    """
    deps = await _get_deps()
    try:
        knowledge = await deps.storage_service.get_knowledge(category=category)
        if not knowledge:
            return "No knowledge entries found."
        formatted = []
        for k in knowledge:
            formatted.append(f"[{k['category']}] {k['title']}")
            formatted.append(k.get("content", "")[:500])
            formatted.append("")
        return "\n".join(formatted)
    except Exception as e:
        return f"Knowledge search unavailable: {type(e).__name__}"


@service_server.tool()
async def store_pattern(
    name: str,
    topic: str,
    pattern_text: str,
    confidence: str = "LOW",
    context: str = "",
    evidence: str = "",
) -> str:
    """Store a new pattern in the pattern registry.

    Args:
        name: Short descriptive name
        topic: Category (Messaging, Content, Process, etc.)
        pattern_text: The actionable insight
        confidence: LOW, MEDIUM, or HIGH
        context: When to apply this pattern
        evidence: Comma-separated evidence items
    """
    try:
        name = _validate_input(name, "name")
        pattern_text = _validate_input(pattern_text, "pattern_text")
    except ValueError as e:
        return str(e)
    deps = await _get_deps()
    try:
        evidence_list = [item.strip() for item in evidence.split(",") if item.strip()] if evidence else []
        data = {
            "name": name,
            "topic": topic,
            "pattern_text": pattern_text,
            "confidence": confidence,
            "context": context,
            "evidence": evidence_list,
        }
        result = await deps.storage_service.insert_pattern(data)
        if result:
            return f"Stored pattern: {name} [{confidence}]"
        return f"Failed to store pattern: {name}"
    except Exception as e:
        return f"Pattern storage failed: {type(e).__name__}"


@service_server.tool()
async def store_experience(
    name: str,
    category: str,
    content: str,
    outcome: str = "",
) -> str:
    """Record a new experience in Supabase.

    Args:
        name: Experience name/title
        category: content, prospects, clients, or general
        content: The experience content/description
        outcome: What happened as a result
    """
    try:
        name = _validate_input(name, "name")
        content = _validate_input(content, "content")
    except ValueError as e:
        return str(e)
    deps = await _get_deps()
    try:
        data = {
            "name": name,
            "category": category,
            "output_summary": content,
            "outcome": outcome,
        }
        result = await deps.storage_service.add_experience(data)
        if result:
            return f"Recorded experience: {name} [{category}]"
        return f"Failed to record experience: {name}"
    except Exception as e:
        return f"Experience storage failed: {type(e).__name__}"


# --- Graphiti Tools ---


@service_server.tool()
async def graph_search(query: str, limit: int = 10) -> str:
    """Search the Graphiti knowledge graph for entity relationships.

    Args:
        query: What to search for in the knowledge graph
        limit: Maximum relationships to return
    """
    try:
        query = _validate_input(query, "query")
    except ValueError as e:
        return str(e)
    deps = await _get_deps()
    if not deps.graphiti_service:
        return "Graphiti is not enabled."
    try:
        results = await deps.graphiti_service.search(query, limit=limit)
        if not results:
            return f"No graph relationships found for: {query}"
        formatted = [f"Graph Search: {query}"]
        for rel in results:
            src = rel.get("source", "?")
            relationship = rel.get("relationship", "?")
            tgt = rel.get("target", "?")
            formatted.append(f"- {src} --[{relationship}]--> {tgt}")
        formatted.append(f"Found {len(results)} relationship(s)")
        return "\n".join(formatted)
    except Exception as e:
        return f"Graph search failed: {type(e).__name__}"


# --- Vector Search Tools ---


@service_server.tool()
async def service_vector_search(
    query: str,
    table: str = "memory_content",
    limit: int = 10,
) -> str:
    """Search using vector similarity (pgvector) in the SDK path.

    Args:
        query: Search query to embed and match against vectors.
        table: Table to search (patterns, memory_content, examples, knowledge_repo, experiences).
        limit: Maximum results.
    """
    deps = await _get_deps()
    if not deps.embedding_service:
        return "Vector search unavailable: embedding service not configured."
    try:
        embedding = await deps.embedding_service.embed_query(query)
        results = await deps.storage_service.vector_search(
            embedding=embedding, table=table, limit=limit,
        )
    except ValueError as e:
        return str(e)
    except Exception as e:
        logger.warning("service_vector_search failed: %s", type(e).__name__)
        return f"Vector search error: {type(e).__name__}"

    if not results:
        return f"No vector matches found in '{table}'."

    formatted = [f"## Vector Search: {query}\n"]
    for r in results:
        sim = r.get("similarity", 0)
        title = r.get("title", "Untitled")
        content = r.get("content", "")[:200]
        formatted.append(f"- [{sim:.3f}] **{title}**: {content}")
    return "\n".join(formatted)


# --- Config Helper ---


def get_service_mcp_config() -> tuple[str, dict]:
    """Get MCP server configuration for claude-agent-sdk.

    Returns (server_name, config) for ClaudeAgentOptions.mcp_servers.
    The SDK expects mcp_servers={server_name: config} (dict, not list).
    Config follows McpStdioServerConfig: command (required), type/args/env (optional).

    Uses -u flag and PYTHONUNBUFFERED=1 to force unbuffered stdout.
    Without this, JSON-RPC responses get stuck in Python's output buffer
    when running as a subprocess with piped stdout (not a TTY).
    """
    import sys
    return (
        "second-brain-services",
        {
            "type": "stdio",
            "command": sys.executable,
            "args": ["-u", "-m", "second_brain.service_mcp"],
            "env": {"PYTHONUNBUFFERED": "1"},
        },
    )


if __name__ == "__main__":
    import sys as _sys
    import asyncio as _asyncio

    logging.basicConfig(
        stream=_sys.stderr,
        level=logging.WARNING,
        format="%(levelname)s: %(message)s",
    )
    init_deps()
    try:
        service_server.run()
    except (KeyboardInterrupt, _asyncio.CancelledError):
        pass
