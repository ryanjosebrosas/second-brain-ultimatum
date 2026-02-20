"""RecallAgent — semantic memory search across Mem0 and Supabase."""

import asyncio
import logging

from pydantic_ai import Agent, ModelRetry, RunContext

from second_brain.agents.utils import (
    deduplicate_results,
    expand_query,
    format_memories,
    format_relations,
    normalize_results,
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
        "or use pattern/experience search instead of semantic search.\n\n"
        "SOURCES: Track which search tools you used in the search_sources field. "
        "Include entries like 'mem0', 'hybrid:patterns', 'pgvector:experiences', "
        "'pgvector:examples', 'projects' based on which tools returned results."
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
    """Search Mem0 semantic memory and pgvector in parallel for relevant content."""
    try:



        expanded = expand_query(query)
        oversample = ctx.deps.config.retrieval_oversample_factor
        search_limit = ctx.deps.config.memory_search_limit * oversample

        # Build parallel searches
        mem0_coro = ctx.deps.memory_service.search(expanded, limit=search_limit)
        hybrid_coro = None

        embedding = None
        if ctx.deps.embedding_service:
            try:
                embedding = await ctx.deps.embedding_service.embed_query(expanded)
            except Exception:
                logger.debug("Embedding failed in search_semantic_memory, skipping hybrid search")
        if embedding:
            hybrid_coro = ctx.deps.storage_service.hybrid_search(
                query_text=query,
                query_embedding=embedding,
                table="memory_content",
                limit=search_limit,
            )

        # Execute concurrently
        if hybrid_coro:
            mem0_result, hybrid_result = await asyncio.gather(
                mem0_coro, hybrid_coro, return_exceptions=True,
            )
        else:
            mem0_result = await mem0_coro
            hybrid_result = None

        # Collect results
        all_memories: list[dict] = []
        if not isinstance(mem0_result, BaseException):
            all_memories.extend(normalize_results(mem0_result.memories, source="mem0"))
        if hybrid_result and not isinstance(hybrid_result, BaseException):
            all_memories.extend(
                normalize_results(hybrid_result, source="hybrid:memory_content",
                                  content_key="content", score_key="similarity")
            )

        all_memories = deduplicate_results(all_memories)
        memories = await rerank_memories(ctx.deps, query, all_memories)
        relations = await search_with_graph_fallback(
            ctx.deps, query,
            mem0_result.relations if not isinstance(mem0_result, BaseException) else [],
        )

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
    """Search the pattern registry using hybrid + semantic search in parallel."""
    try:



        formatted = []
        query_text = topic or "patterns"
        expanded = expand_query(query_text)

        # Build parallel searches
        coros = {}

        # Path A: Hybrid search (semantic + keyword via pgvector + FTS)
        embedding = None
        if ctx.deps.embedding_service:
            try:
                embedding = await ctx.deps.embedding_service.embed_query(expanded)
            except Exception:
                logger.debug("Embedding failed in search_patterns, skipping hybrid search")
        if embedding:
            coros["hybrid"] = ctx.deps.storage_service.hybrid_search(
                query_text=query_text,
                query_embedding=embedding,
                table="patterns",
                limit=ctx.deps.config.memory_search_limit,
            )

        # Path B: Semantic memory search (Mem0 with pattern filter)
        filters = {"category": "pattern"}
        if topic:
            filters = {"AND": [{"category": "pattern"}, {"topic": topic}]}
        coros["mem0"] = ctx.deps.memory_service.search_with_filters(
            topic or "patterns",
            metadata_filters=filters,
            limit=10,
            enable_graph=True,
        )

        # Execute in parallel
        if len(coros) >= 2:
            results = await asyncio.gather(
                *coros.values(), return_exceptions=True,
            )
            result_map = dict(zip(coros.keys(), results))
        else:
            result_map = {}
            for key, coro in coros.items():
                try:
                    result_map[key] = await coro
                except Exception as exc:
                    result_map[key] = exc

        # Collect all results for unified reranking
        all_pattern_results = []

        # Hybrid results (Supabase)
        hybrid_result = result_map.get("hybrid")
        if hybrid_result and not isinstance(hybrid_result, BaseException):
            all_pattern_results.extend(
                normalize_results(hybrid_result, source="hybrid",
                                  content_key="content", score_key="similarity")
            )

        # Semantic results (Mem0)
        semantic_relations = []
        mem0_result = result_map.get("mem0")
        if mem0_result and not isinstance(mem0_result, BaseException):
            all_pattern_results.extend(
                normalize_results(mem0_result.memories, source="mem0")
            )
            semantic_relations = mem0_result.relations
        elif isinstance(mem0_result, BaseException):
            logger.debug("Semantic pattern search failed: %s", mem0_result)

        # Deduplicate and rerank as a unified set
        all_pattern_results = deduplicate_results(all_pattern_results)
        all_pattern_results = await rerank_memories(ctx.deps, topic or "patterns", all_pattern_results)

        if all_pattern_results:
            formatted.append("## Pattern Matches")
            formatted.append(format_memories(all_pattern_results))

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
        embedding = None
        if query and ctx.deps.embedding_service:
            try:
                embedding = await ctx.deps.embedding_service.embed_query(query)
            except Exception:
                logger.debug("Embedding failed in search_experiences, skipping semantic search")
        if embedding:
            experiences = await ctx.deps.storage_service.search_experiences_semantic(
                embedding=embedding,
                limit=ctx.deps.config.experience_limit,
            )

        # Fallback: exact-match filter when semantic search returns nothing
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
        embedding = None
        if query and ctx.deps.embedding_service:
            try:
                embedding = await ctx.deps.embedding_service.embed_query(query)
            except Exception:
                logger.debug("Embedding failed in search_examples, skipping semantic search")
        if embedding:
            examples = await ctx.deps.storage_service.search_examples_semantic(
                embedding=embedding,
                limit=ctx.deps.config.memory_search_limit,
            )

        # Fallback: exact-match filter when semantic search returns nothing
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
