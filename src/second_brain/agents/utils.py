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


async def run_review_learn_pipeline(
    content: str,
    content_type: str,
    deps: "BrainDeps",
    model,
) -> dict:
    """Run the review->learn pipeline: review content, then learn from the review results.

    Returns dict with 'review' (ReviewResult) and 'learn' (LearnResult) keys.
    """
    from second_brain.agents.review import run_full_review
    from second_brain.agents.learn import learn_agent

    # Step 1: Review
    review_result = await run_full_review(
        content=content,
        content_type=content_type,
        deps=deps,
        model=model,
    )

    # Step 2: Learn from review
    strengths = "\n".join(review_result.top_strengths or [])
    issues = "\n".join(review_result.critical_issues or [])
    overall_score = review_result.overall_score
    summary = review_result.summary or ""

    learn_prompt = (
        f"Learn from this review of {content_type} content.\n"
        f"Review score: {overall_score}/10\n"
        f"Summary: {summary}\n"
        f"Strengths:\n{strengths}\n"
        f"Issues:\n{issues}\n\n"
        f"Extract patterns from what worked well (strengths) and note what to avoid (issues)."
    )

    learn_result = await learn_agent.run(learn_prompt, deps=deps, model=model)

    return {
        "review": review_result,
        "learn": learn_result.output,
    }


def format_pattern_registry(patterns: list[dict], config=None) -> str:
    """Format patterns as a registry table for display."""
    if not patterns:
        return "No patterns in registry."

    stale_days = config.stale_pattern_days if config else 30

    lines = ["| Pattern | Topic | Confidence | Uses | Last Updated | Status |",
             "|---------|-------|------------|------|--------------|--------|"]

    for p in patterns:
        name = p.get("name", "Unknown")
        topic = p.get("topic", "-")
        conf = p.get("confidence", "LOW")
        uses = p.get("use_count", 0)
        updated = p.get("date_updated", "-")
        failures = p.get("consecutive_failures", 0)

        # Determine status
        status = "Active"
        if failures >= 2:
            status = "At Risk"
        elif updated and updated != "-":
            try:
                from datetime import datetime, timedelta, timezone
                last = datetime.fromisoformat(updated.replace("Z", "+00:00")) if "T" in updated else datetime.strptime(updated, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                if datetime.now(timezone.utc) - last > timedelta(days=stale_days):
                    status = "Stale"
            except (ValueError, TypeError):
                pass

        lines.append(f"| {name} | {topic} | {conf} | {uses} | {updated} | {status} |")

    lines.append(f"\nTotal: {len(patterns)} patterns")
    conf_counts: dict[str, int] = {}
    for p in patterns:
        c = p.get("confidence", "LOW")
        conf_counts[c] = conf_counts.get(c, 0) + 1
    dist = ", ".join(f"{k}: {v}" for k, v in sorted(conf_counts.items()))
    lines.append(f"Distribution: {dist}")

    return "\n".join(lines)


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
