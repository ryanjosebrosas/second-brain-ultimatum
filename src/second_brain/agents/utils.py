"""Shared utilities for Second Brain agents."""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from second_brain.deps import BrainDeps

logger = logging.getLogger(__name__)


def format_memories(memories: list[dict], limit: int | None = None) -> str:
    """Format Mem0 search results as markdown list.

    Args:
        memories: Raw Mem0 search results (list of dicts with 'memory'/'result' and 'score').
        limit: Max memories to format. None = all.

    Returns:
        Formatted markdown string with score and content.
    """
    if not memories:
        return ""
    items = memories[:limit] if limit else memories
    lines = []
    for m in items:
        content = m.get("memory", m.get("result", ""))
        score = m.get("score", 0)
        lines.append(f"- [{score:.2f}] {content}")
    return "\n".join(lines)


def format_relations(relations: list[dict]) -> str:
    """Format graph relationships as markdown list.

    Args:
        relations: Graph relationship dicts with source/relationship/target keys.

    Returns:
        Formatted markdown string. Empty string if no relations.
    """
    if not relations:
        return ""
    lines = ["\n## Graph Relationships"]
    for rel in relations:
        src = rel.get("source", rel.get("entity", "?"))
        relationship = rel.get("relationship", "?")
        tgt = rel.get("target", rel.get("connected_to", "?"))
        lines.append(f"- {src} --[{relationship}]--> {tgt}")
    return "\n".join(lines)


async def search_with_graph_fallback(
    deps: "BrainDeps",
    query: str,
    base_relations: list[dict] | None = None,
) -> list[dict]:
    """Search Graphiti (if available) and merge with base relations.

    Graphiti is optional -- failures are debug-level, non-blocking.

    Args:
        deps: BrainDeps with optional graphiti_service.
        query: Search query string.
        base_relations: Relations already collected (e.g., from Mem0 graph).

    Returns:
        Merged list of relations (base + graphiti results).
    """
    relations = list(base_relations or [])
    if deps.graphiti_service:
        try:
            graphiti_rels = await deps.graphiti_service.search(query)
            relations = relations + graphiti_rels
        except Exception as e:
            logger.debug("Graphiti search failed (non-critical): %s", e)
    return relations


async def rerank_memories(
    deps: "BrainDeps",
    query: str,
    memories: list[dict],
    top_k: int | None = None,
) -> list[dict]:
    """Rerank Mem0 search results using Voyage reranker.

    Graceful degradation: returns original memories if Voyage unavailable.

    Args:
        deps: BrainDeps with optional voyage_service.
        query: Original search query.
        memories: Raw Mem0 results (dicts with 'memory'/'result' key).
        top_k: Max results after reranking. None = config default.

    Returns:
        Reranked list of memory dicts, or original list if reranking unavailable.
    """
    if not deps.voyage_service or not memories:
        return memories

    # Extract text from memory dicts
    documents = [
        m.get("memory", m.get("result", ""))
        for m in memories
    ]
    documents = [d for d in documents if d]  # filter empties

    if not documents:
        return memories

    try:
        reranked = await deps.voyage_service.rerank(query, documents, top_k=top_k)
        # Rebuild memory dicts in reranked order
        result = []
        for r in reranked:
            idx = r["index"]
            if idx < len(memories):
                mem = dict(memories[idx])
                mem["rerank_score"] = r["relevance_score"]
                result.append(mem)
        return result
    except Exception as e:
        logger.debug("Reranking failed (non-critical): %s", e)
        return memories


def tool_error(tool_name: str, error: Exception) -> str:
    """Standard error format for agent tool failures.

    Returns a user-friendly error string. Logs the technical details.

    Args:
        tool_name: Name of the tool that failed.
        error: The exception that occurred.

    Returns:
        Formatted error string for the LLM.
    """
    logger.warning("%s failed: %s", tool_name, type(error).__name__)
    logger.debug("%s error detail: %s", tool_name, error)
    return f"{tool_name} unavailable: {type(error).__name__}"
