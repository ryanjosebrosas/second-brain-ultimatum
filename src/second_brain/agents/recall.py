"""RecallAgent — semantic memory search across Mem0 and Supabase."""

import logging

from pydantic_ai import Agent, RunContext

from second_brain.agents.utils import (
    format_memories,
    format_relations,
    rerank_memories,
    search_with_graph_fallback,
    tool_error,
)
from second_brain.deps import BrainDeps
from second_brain.schemas import RecallResult

logger = logging.getLogger(__name__)

# NOTE: When using ClaudeSDKModel (subscription auth), Pydantic AI tools
# are NOT called. Instead, the SDK process calls service MCP tools directly.
# The agent instructions and output schema validation still apply.
recall_agent = Agent(
    deps_type=BrainDeps,
    output_type=RecallResult,
    instructions=(
        "You are a memory recall agent for an AI Second Brain. "
        "Search the user's semantic memory for relevant context, patterns, "
        "and past experiences. Return the most relevant matches ranked by "
        "relevance. Always include the source of each match."
    ),
)


@recall_agent.tool
async def search_semantic_memory(
    ctx: RunContext[BrainDeps], query: str
) -> str:
    """Search Mem0 semantic memory for relevant content."""
    try:
        result = await ctx.deps.memory_service.search(query)
        memories = await rerank_memories(ctx.deps, query, result.memories)
        relations = await search_with_graph_fallback(ctx.deps, query, result.relations)

        if not memories and not relations:
            return "No semantic matches found."

        parts = [format_memories(memories)]
        rel_text = format_relations(relations)
        if rel_text:
            parts.append(rel_text)
        return "\n".join(parts)
    except Exception as e:
        return tool_error("search_semantic_memory", e)


@recall_agent.tool
async def search_patterns(
    ctx: RunContext[BrainDeps], topic: str | None = None
) -> str:
    """Search the pattern registry using semantic search and Supabase."""
    try:
        # Try semantic search first (Mem0 with pattern filter)
        semantic_results = []
        semantic_relations = []
        try:
            filters = {"category": "pattern"}
            if topic:
                filters = {"AND": [{"category": "pattern"}, {"topic": topic}]}
            result = await ctx.deps.memory_service.search_with_filters(
                topic or "patterns",
                metadata_filters=filters,
                limit=10,
                enable_graph=True,
            )
            semantic_results = result.memories
            semantic_relations = result.relations
        except Exception:
            logger.debug("Semantic pattern search failed, falling back to Supabase")

        semantic_results = await rerank_memories(ctx.deps, topic or "patterns", semantic_results)

        # Always include Supabase patterns (source of truth)
        patterns = await ctx.deps.storage_service.get_patterns(topic=topic)

        if not patterns and not semantic_results:
            return "No patterns found in registry."

        formatted = []
        if semantic_results:
            formatted.append("## Semantic Matches")
            formatted.append(format_memories(semantic_results))
            formatted.append("")

        if patterns:
            formatted.append("## Pattern Registry")
            for p in patterns:
                formatted.append(
                    f"- [{p['confidence']}] {p['name']}: "
                    f"{p.get('pattern_text', '')[:ctx.deps.config.pattern_preview_limit]}"
                )

        rel_text = format_relations(semantic_relations)
        if rel_text:
            formatted.append(rel_text)

        return "\n".join(formatted)
    except Exception as e:
        return tool_error("search_patterns", e)


@recall_agent.tool
async def search_experiences(
    ctx: RunContext[BrainDeps], category: str | None = None
) -> str:
    """Search past experiences in Supabase."""
    try:
        experiences = await ctx.deps.storage_service.get_experiences(category=category)
        if not experiences:
            return "No past experiences found."
        formatted = []
        for e in experiences:
            score_str = f" (score: {e['review_score']})" if e.get("review_score") else ""
            formatted.append(f"- {e['name']} [{e['category']}]{score_str}")
        return "\n".join(formatted)
    except Exception as e:
        return tool_error("search_experiences", e)


@recall_agent.tool
async def search_examples(
    ctx: RunContext[BrainDeps], content_type: str | None = None
) -> str:
    """Search content examples in the brain (emails, LinkedIn posts, case studies, etc.)."""
    try:
        examples = await ctx.deps.storage_service.get_examples(content_type=content_type)
        if not examples:
            return "No content examples found."
        formatted = []
        for e in examples:
            formatted.append(f"- [{e['content_type']}] {e['title']}")
            preview = e.get("content", "")[:ctx.deps.config.pattern_preview_limit]
            if preview:
                formatted.append(f"  {preview}")
        return "\n".join(formatted)
    except Exception as e:
        return tool_error("search_examples", e)
