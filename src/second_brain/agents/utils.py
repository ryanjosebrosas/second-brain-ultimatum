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
