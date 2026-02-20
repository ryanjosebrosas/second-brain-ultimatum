"""AskAgent — contextual help using brain knowledge."""

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
from second_brain.schemas import AskResult

logger = logging.getLogger(__name__)

# NOTE: When using ClaudeSDKModel (subscription auth), Pydantic AI tools
# are NOT called. Instead, the SDK process calls service MCP tools directly.
# The agent instructions and output schema validation still apply.
ask_agent = Agent(
    deps_type=BrainDeps,
    output_type=AskResult,
    retries=3,
    instructions=(
        "You are the AI Second Brain assistant for a knowledge worker. "
        "You help with any task by leveraging the brain's accumulated "
        "knowledge: company context, customer insights, content patterns, "
        "style preferences, and past experiences.\n\n"
        "OUTPUT RULES (CRITICAL):\n"
        "- The 'answer' field MUST contain your COMPLETE response. If the user asks you to "
        "write or draft something, put the FULL written text in the answer — NEVER a summary "
        "or description of what you would write.\n"
        "- Populate context_used with the sources listed in tool outputs.\n"
        "- If the brain has relevant patterns, apply them and list them in patterns_applied.\n\n"
        "CONVERSATIONAL QUERIES:\n"
        "- For greetings, small talk, or pleasantries (hello, thanks, bye, etc.), "
        "respond naturally and briefly. Set is_conversational=True. "
        "You do NOT need to call any tools or reference brain context for these.\n\n"
        "For all other queries, always ground your response in the brain's actual knowledge. "
        "If the task is complex, suggest using /plan instead.\n\n"
        "ERROR HANDLING: If brain context tools return 'unavailable' errors, "
        "set the error field to describe the issue and answer the question "
        "using your general knowledge. Do not keep retrying failing tools."
    ),
)


@ask_agent.output_validator
async def validate_ask(ctx: RunContext[BrainDeps], output: AskResult) -> AskResult:
    """Validate answer completeness — accept graceful degradation.

    When brain context tools fail, the agent should still provide a useful
    answer from general knowledge. We don't force retries on missing context
    to prevent death spirals when backends are down.
    """
    # Conversational responses skip all checks
    if output.is_conversational:
        return output
    # Backend errors — accept whatever the agent produced
    if output.error:
        return output
    # Check answer isn't a cop-out (still enforce minimum substance)
    if len(output.answer) < 50:
        raise ModelRetry(
            "Your answer is too brief. Provide a COMPLETE, detailed response. "
            "If brain tools are unavailable, answer from general knowledge "
            "and set the error field."
        )
    return output


@ask_agent.tool
async def load_brain_context(ctx: RunContext[BrainDeps]) -> str:
    """Load core brain context: company info, customer profile, and positioning."""
    try:
        sections = []
        sources = []
        for category in ["company", "personal", "customers"]:
            content = await ctx.deps.storage_service.get_memory_content(category)
            if content:
                section_parts = [f"## {category.title()}"]
                for item in content:
                    section_parts.append(f"### {item['title']}\n{item['content'][:ctx.deps.config.content_preview_limit]}")
                    sources.append(f"{category}/{item['title']}")
                sections.append("\n".join(section_parts))

        if not sections:
            return "Brain context is empty. Run /setup first."

        source_section = "\n\n---\nSources used: " + ", ".join(sources)
        return "\n\n".join(sections) + source_section
    except Exception as e:
        return tool_error("load_brain_context", e)


@ask_agent.tool
async def find_relevant_patterns(
    ctx: RunContext[BrainDeps], query: str
) -> str:
    """Find patterns relevant to the current question using hybrid search."""
    try:
        from second_brain.agents.utils import expand_query, deduplicate_results

        expanded = expand_query(query)

        # Call 1: Mem0 semantic + keyword search (keyword_search enabled at service layer)
        result = await ctx.deps.memory_service.search(expanded)

        # Call 2: Rerank Mem0 results (single rerank, not two separate ones)
        reranked_memories = await rerank_memories(ctx.deps, query, result.memories)

        # Call 3: Hybrid pgvector + FTS search for patterns (replaces full get_patterns scan)
        pattern_results = []
        if ctx.deps.embedding_service:
            try:
                embedding = await ctx.deps.embedding_service.embed_query(query)
                pattern_results = await ctx.deps.storage_service.hybrid_search(
                    query_text=query,
                    query_embedding=embedding,
                    table="patterns",
                    limit=10,
                )
            except Exception:
                logger.debug("Hybrid pattern search failed, falling back to Supabase")
                pattern_results = []

        # Fallback: exact-match patterns if hybrid unavailable
        if not pattern_results:
            patterns = await ctx.deps.storage_service.get_patterns()
            pattern_results = [
                {"content": p.get("pattern_text", ""), "title": p.get("name", ""),
                 "category": p.get("topic", ""), "confidence": p.get("confidence", "LOW")}
                for p in (patterns or [])[:10]
            ]

        # Graph relations (single call, same as before)
        relations = await search_with_graph_fallback(ctx.deps, query, result.relations)

        sources = []
        formatted = ["## Semantic Memory Matches"]
        for r in reranked_memories[:5]:
            memory = r.get("memory", r.get("result", ""))
            score = r.get("rerank_score", r.get("score", 0))
            formatted.append(f"- [{score:.2f}] {memory}")

        if pattern_results:
            formatted.append("\n## Relevant Patterns")
            for p in pattern_results:
                title = p.get("title", p.get("name", "Unknown"))
                content = p.get("content", p.get("pattern_text", ""))
                sim = p.get("similarity")
                conf = p.get("confidence", p.get("category", ""))
                prefix = f"[{sim:.3f}]" if sim else f"[{conf}]"
                formatted.append(f"- {prefix} **{title}**: {content[:ctx.deps.config.pattern_preview_limit]}")
                sources.append(f"pattern/{title}")

        rel_text = format_relations(relations)
        if rel_text:
            formatted.append(rel_text)

        if sources:
            formatted.append(f"\n---\nSources: {', '.join(sources)}")

        return "\n".join(formatted)
    except Exception as e:
        return tool_error("find_relevant_patterns", e)


@ask_agent.tool
async def find_similar_experiences(
    ctx: RunContext[BrainDeps], query: str
) -> str:
    """Find past work similar to the current question."""
    try:
        result = await ctx.deps.memory_service.search(
            f"past experience: {query}",
            enable_graph=True,
        )
        result.memories = await rerank_memories(ctx.deps, query, result.memories)
        experiences = await ctx.deps.storage_service.get_experiences(limit=ctx.deps.config.experience_limit)

        relations = await search_with_graph_fallback(ctx.deps, query, result.relations)

        sources = []
        formatted = ["## Similar Past Work"]
        for e in experiences:
            score = f" (score: {e['review_score']})" if e.get("review_score") else ""
            formatted.append(f"- **{e['name']}** [{e['category']}]{score}")
            if e.get("learnings"):
                formatted.append(f"  Learnings: {e['learnings'][:ctx.deps.config.pattern_preview_limit]}")
            sources.append(f"supabase/experience/{e['name']}")

        rel_text = format_relations(relations)
        if rel_text:
            formatted.append(rel_text)

        if sources:
            formatted.append(f"\n---\nSources: {', '.join(sources)}")

        return "\n".join(formatted)
    except Exception as e:
        return tool_error("find_similar_experiences", e)


@ask_agent.tool
async def search_knowledge(
    ctx: RunContext[BrainDeps], category: str | None = None
) -> str:
    """Search the knowledge repository for frameworks, methodologies, and playbooks."""
    try:
        knowledge = await ctx.deps.storage_service.get_knowledge(category=category)
        if not knowledge:
            return "No knowledge entries found."

        sources = []
        formatted = ["## Knowledge Repository"]
        for k in knowledge:
            formatted.append(f"- [{k['category']}] **{k['title']}**")
            preview = k.get("content", "")[:ctx.deps.config.pattern_preview_limit]
            if preview:
                formatted.append(f"  {preview}")
            sources.append(f"knowledge/{k['category']}/{k['title']}")

        # Add graph relationships if available
        if ctx.deps.graphiti_service:
            try:
                query_str = category or "knowledge frameworks methodologies"
                graphiti_rels = await ctx.deps.graphiti_service.search(query_str)
                if graphiti_rels:
                    formatted.append(format_relations(graphiti_rels))
            except Exception as e:
                logger.debug("Graphiti search failed in search_knowledge (non-critical): %s", e)

        if sources:
            formatted.append(f"\n---\nSources: {', '.join(sources)}")

        return "\n".join(formatted)
    except Exception as e:
        return tool_error("search_knowledge", e)
