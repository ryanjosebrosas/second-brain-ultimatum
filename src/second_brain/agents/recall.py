"""RecallAgent — semantic memory search across Mem0 and Supabase."""

import logging

from pydantic_ai import Agent, RunContext

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

        # Collect relations from Mem0 graph
        relations = result.relations

        # Also check Graphiti if available
        if ctx.deps.graphiti_service:
            try:
                graphiti_rels = await ctx.deps.graphiti_service.search(query)
                relations = relations + graphiti_rels
            except Exception as e:
                logger.debug("Graphiti search failed (non-critical): %s", e)

        if not result.memories and not relations:
            return "No semantic matches found."

        formatted = []
        for r in result.memories:
            memory = r.get("memory", r.get("result", ""))
            score = r.get("score", 0)
            formatted.append(f"- [{score:.2f}] {memory}")

        if relations:
            formatted.append("\nGraph Relationships:")
            for rel in relations:
                src = rel.get("source", "?")
                relationship = rel.get("relationship", "?")
                tgt = rel.get("target", "?")
                formatted.append(f"- {src} --[{relationship}]--> {tgt}")

        return "\n".join(formatted)
    except Exception as e:
        logger.warning("search_semantic_memory failed: %s", type(e).__name__)
        return f"Memory search unavailable: {type(e).__name__}"


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
                enable_graph=True,  # Request graph relationships
            )
            semantic_results = result.memories
            semantic_relations = result.relations  # Graph relationships from Mem0
        except Exception:
            logger.debug("Semantic pattern search failed, falling back to Supabase")

        # Always include Supabase patterns (source of truth)
        patterns = await ctx.deps.storage_service.get_patterns(topic=topic)

        if not patterns and not semantic_results:
            return "No patterns found in registry."

        formatted = []
        if semantic_results:
            formatted.append("## Semantic Matches")
            for m in semantic_results:
                memory = m.get("memory", m.get("result", ""))
                score = m.get("score", 0)
                formatted.append(f"- [{score:.2f}] {memory}")
            formatted.append("")

        if patterns:
            formatted.append("## Pattern Registry")
            for p in patterns:
                formatted.append(
                    f"- [{p['confidence']}] {p['name']}: "
                    f"{p.get('pattern_text', '')[:ctx.deps.config.pattern_preview_limit]}"
                )

        if semantic_relations:
            formatted.append("\n## Graph Relationships")
            for rel in semantic_relations:
                src = rel.get("source", rel.get("entity", "?"))
                relationship = rel.get("relationship", "?")
                tgt = rel.get("target", rel.get("connected_to", "?"))
                formatted.append(f"- {src} --[{relationship}]--> {tgt}")

        return "\n".join(formatted)
    except Exception as e:
        logger.warning("search_patterns failed: %s", type(e).__name__)
        return f"Pattern search unavailable: {type(e).__name__}"


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
        logger.warning("search_experiences failed: %s", type(e).__name__)
        return f"Experience search unavailable: {type(e).__name__}"


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
        logger.warning("search_examples failed: %s", type(e).__name__)
        return f"Example search unavailable: {type(e).__name__}"
