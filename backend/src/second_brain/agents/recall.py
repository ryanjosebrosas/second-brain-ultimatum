"""RecallAgent — semantic memory search across Mem0 and Supabase."""

import logging

from pydantic_ai import Agent, ModelRetry, RunContext

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
    retries=3,
    instructions=(
        "You are a memory recall agent for an AI Second Brain. "
        "Search the user's semantic memory for relevant context, patterns, "
        "and past experiences. Return the most relevant matches ranked by "
        "relevance. Always include the source of each match.\n\n"
        "IMPORTANT: If your initial search returns no results, try alternative "
        "search strategies: broaden the query, search different categories, "
        "or use pattern/experience search instead of semantic search."
    ),
)


@recall_agent.output_validator
async def validate_recall(ctx: RunContext[BrainDeps], output: RecallResult) -> RecallResult:
    """Retry if recall returned nothing — try alternative search strategies."""
    if not output.matches and not output.patterns and not output.relations:
        raise ModelRetry(
            "No results found. Try alternative search strategies:\n"
            "1. Broaden the search query (use fewer, more general terms)\n"
            "2. Search patterns by topic instead of semantic memory\n"
            "3. Search experiences for related past work\n"
            "4. Check examples for similar content types\n"
            "You have multiple search tools — use a different one."
        )
    return output


@recall_agent.tool
async def search_semantic_memory(
    ctx: RunContext[BrainDeps], query: str
) -> str:
    """Search Mem0 semantic memory for relevant content."""
    try:
        from second_brain.agents.utils import expand_query

        expanded = expand_query(query)
        oversample = ctx.deps.config.retrieval_oversample_factor
        result = await ctx.deps.memory_service.search(
            expanded,
            limit=ctx.deps.config.memory_search_limit * oversample,
        )
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
    """Search the pattern registry using hybrid search (semantic + keyword)."""
    try:
        from second_brain.agents.utils import expand_query

        formatted = []

        # Path A: Hybrid search (semantic + keyword via pgvector + FTS)
        if ctx.deps.embedding_service:
            query_text = topic or "patterns"
            expanded = expand_query(query_text)
            embedding = await ctx.deps.embedding_service.embed_query(expanded)
            try:
                hybrid_results = await ctx.deps.storage_service.hybrid_search(
                    query_text=query_text,
                    query_embedding=embedding,
                    table="patterns",
                    limit=ctx.deps.config.memory_search_limit,
                )
                if hybrid_results:
                    formatted.append("## Pattern Matches (hybrid)")
                    for p in hybrid_results:
                        title = p.get("title", "Unknown")
                        content = p.get("content", "")[:ctx.deps.config.pattern_preview_limit]
                        sim = p.get("similarity", 0)
                        search_type = p.get("search_type", "semantic")
                        formatted.append(f"- [{sim:.3f}|{search_type}] {title}: {content}")
            except Exception:
                logger.debug("Hybrid pattern search failed, using fallback")

        # Path B: Semantic memory search (Mem0 with pattern filter)
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
            logger.debug("Semantic pattern search failed, skipping")

        semantic_results = await rerank_memories(ctx.deps, topic or "patterns", semantic_results)

        if semantic_results:
            formatted.append("\n## Semantic Matches (Mem0)")
            formatted.append(format_memories(semantic_results))

        # Path C: Exact-match fallback (only if no results from A or B)
        if not formatted:
            patterns = await ctx.deps.storage_service.get_patterns(topic=topic)
            if not patterns:
                return "No patterns found in registry."
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
    ctx: RunContext[BrainDeps], query: str | None = None, category: str | None = None
) -> str:
    """Search past experiences by semantic similarity or category filter.

    Use query for semantic search, category for exact filter, or both."""
    try:
        experiences = []

        # Semantic search path (preferred when query + embedding service available)
        if query and ctx.deps.embedding_service:
            embedding = await ctx.deps.embedding_service.embed_query(query)
            experiences = await ctx.deps.storage_service.search_experiences_semantic(
                embedding=embedding,
                limit=ctx.deps.config.experience_limit,
            )

        # Fallback / supplement: exact-match filter
        if not experiences:
            experiences = await ctx.deps.storage_service.get_experiences(category=category)

        if not experiences:
            return "No past experiences found."

        formatted = []
        for e in experiences:
            sim = e.get("similarity")
            name = e.get("name", e.get("title", "Untitled"))
            cat = e.get("category", "unknown")
            score_str = f" (score: {e['review_score']})" if e.get("review_score") else ""
            sim_str = f"[{sim:.3f}] " if sim else ""
            formatted.append(f"- {sim_str}{name} [{cat}]{score_str}")
        return "\n".join(formatted)
    except Exception as e:
        return tool_error("search_experiences", e)


@recall_agent.tool
async def search_examples(
    ctx: RunContext[BrainDeps], query: str | None = None, content_type: str | None = None
) -> str:
    """Search content examples by semantic similarity or content type filter.

    Use query for semantic search, content_type for exact filter, or both."""
    try:
        examples = []

        # Semantic search path (preferred when query + embedding service available)
        if query and ctx.deps.embedding_service:
            embedding = await ctx.deps.embedding_service.embed_query(query)
            examples = await ctx.deps.storage_service.search_examples_semantic(
                embedding=embedding,
                limit=ctx.deps.config.memory_search_limit,
            )

        # Fallback / supplement: exact-match filter
        if not examples:
            examples = await ctx.deps.storage_service.get_examples(content_type=content_type)

        if not examples:
            return "No content examples found."

        formatted = []
        for e in examples:
            sim = e.get("similarity")
            ct = e.get("content_type", "unknown")
            title = e.get("title", "Untitled")
            prefix = f"[{sim:.3f}] " if sim else f"[{ct}] "
            formatted.append(f"- {prefix}{title}")
            preview = e.get("content", "")[:ctx.deps.config.pattern_preview_limit]
            if preview:
                formatted.append(f"  {preview}")
        return "\n".join(formatted)
    except Exception as e:
        return tool_error("search_examples", e)


@recall_agent.tool
async def search_projects(
    ctx: RunContext[BrainDeps],
    lifecycle_stage: str | None = None,
    category: str | None = None,
) -> str:
    """Search projects by lifecycle stage or category. Stages: planning, executing,
    reviewing, learning, complete, archived."""
    try:
        projects = await ctx.deps.storage_service.list_projects(
            lifecycle_stage=lifecycle_stage,
            category=category,
            limit=ctx.deps.config.experience_limit,
        )
        if not projects:
            filters = []
            if lifecycle_stage:
                filters.append(f"stage={lifecycle_stage}")
            if category:
                filters.append(f"category={category}")
            filter_str = f" ({', '.join(filters)})" if filters else ""
            return f"No projects found{filter_str}."

        lines = []
        for p in projects:
            stage_icon = {
                "planning": "[plan]", "executing": "[exec]", "reviewing": "[rev]",
                "learning": "[learn]", "complete": "[done]", "archived": "[arch]",
            }.get(p.get("lifecycle_stage", ""), "[?]")
            score = f" (score: {p['review_score']})" if p.get("review_score") else ""
            lines.append(
                f"{stage_icon} {p['name']} [{p.get('lifecycle_stage', 'unknown')}]{score}"
            )
        return "\n".join(lines)
    except Exception as e:
        return tool_error("search_projects", e)
