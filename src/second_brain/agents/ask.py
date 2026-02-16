"""AskAgent — contextual help using brain knowledge."""

import logging

from pydantic_ai import Agent, RunContext

from second_brain.deps import BrainDeps
from second_brain.schemas import AskResult

logger = logging.getLogger(__name__)

ask_agent = Agent(
    deps_type=BrainDeps,
    output_type=AskResult,
    instructions=(
        "You are the AI Second Brain assistant for a knowledge worker. "
        "You help with any task by leveraging the brain's accumulated "
        "knowledge: company context, customer insights, content patterns, "
        "style preferences, and past experiences. "
        "Always ground your response in the brain's actual knowledge. "
        "If the brain has relevant patterns, apply them. "
        "If the task is complex, suggest using /plan instead."
    ),
)


@ask_agent.tool
async def load_brain_context(ctx: RunContext[BrainDeps]) -> str:
    """Load core brain context: company info, customer profile, and positioning."""
    try:
        sections = []
        for category in ["company", "personal", "customers"]:
            content = await ctx.deps.storage_service.get_memory_content(category)
            if content:
                section_parts = [f"## {category.title()}"]
                for item in content:
                    section_parts.append(f"### {item['title']}\n{item['content'][:ctx.deps.config.content_preview_limit]}")
                sections.append("\n".join(section_parts))
        return "\n\n".join(sections) if sections else "Brain context is empty. Run /setup first."
    except Exception as e:
        logger.warning("load_brain_context failed: %s", type(e).__name__)
        return f"Brain context unavailable: {type(e).__name__}"


@ask_agent.tool
async def find_relevant_patterns(
    ctx: RunContext[BrainDeps], query: str
) -> str:
    """Find patterns relevant to the current question using semantic search."""
    try:
        # Semantic memory search (general)
        result = await ctx.deps.memory_service.search(query)

        # Semantic pattern search (filtered to patterns)
        pattern_memories = []
        try:
            pattern_result = await ctx.deps.memory_service.search_with_filters(
                query,
                metadata_filters={"category": "pattern"},
                limit=10,
            )
            pattern_memories = pattern_result.memories
        except Exception:
            logger.debug("Semantic pattern search failed in ask_agent")

        # Collect graph relations
        relations = result.relations
        if ctx.deps.graphiti_service:
            try:
                graphiti_rels = await ctx.deps.graphiti_service.search(query)
                relations = relations + graphiti_rels
            except Exception as e:
                logger.debug("Graphiti search failed (non-critical): %s", e)

        formatted = ["## Semantic Memory Matches"]
        for r in result.memories[:5]:
            memory = r.get("memory", r.get("result", ""))
            formatted.append(f"- {memory}")

        if pattern_memories:
            formatted.append("\n## Semantically Matched Patterns")
            for m in pattern_memories:
                memory = m.get("memory", m.get("result", ""))
                score = m.get("score", 0)
                formatted.append(f"- [{score:.2f}] {memory}")

        if relations:
            formatted.append("\n## Graph Relationships")
            for rel in relations:
                formatted.append(
                    f"- {rel.get('source', '?')} --[{rel.get('relationship', '?')}]--> {rel.get('target', '?')}"
                )

        # Still include top Supabase patterns as reference
        patterns = await ctx.deps.storage_service.get_patterns()
        if patterns:
            formatted.append("\n## Pattern Registry (Top 10)")
            for p in patterns[:10]:
                formatted.append(
                    f"- [{p['confidence']}] **{p['name']}**: "
                    f"{p.get('pattern_text', '')[:ctx.deps.config.pattern_preview_limit]}"
                )

        return "\n".join(formatted)
    except Exception as e:
        logger.warning("find_relevant_patterns failed: %s", type(e).__name__)
        return f"Pattern search unavailable: {type(e).__name__}"


@ask_agent.tool
async def find_similar_experiences(
    ctx: RunContext[BrainDeps], query: str
) -> str:
    """Find past work similar to the current question."""
    try:
        result = await ctx.deps.memory_service.search(
            f"past experience: {query}",
            enable_graph=True,  # Request graph relationships
        )
        experiences = await ctx.deps.storage_service.get_experiences(limit=ctx.deps.config.experience_limit)

        # Collect relations
        relations = result.relations
        if ctx.deps.graphiti_service:
            try:
                graphiti_rels = await ctx.deps.graphiti_service.search(query)
                relations = relations + graphiti_rels
            except Exception as e:
                logger.debug("Graphiti search failed (non-critical): %s", e)

        formatted = ["## Similar Past Work"]
        for e in experiences:
            score = f" (score: {e['review_score']})" if e.get("review_score") else ""
            formatted.append(f"- **{e['name']}** [{e['category']}]{score}")
            if e.get("learnings"):
                formatted.append(f"  Learnings: {e['learnings'][:ctx.deps.config.pattern_preview_limit]}")

        if relations:
            formatted.append("\n## Graph Relationships")
            for rel in relations:
                formatted.append(
                    f"- {rel.get('source', '?')} --[{rel.get('relationship', '?')}]--> {rel.get('target', '?')}"
                )

        return "\n".join(formatted)
    except Exception as e:
        logger.warning("find_similar_experiences failed: %s", type(e).__name__)
        return f"Experience search unavailable: {type(e).__name__}"


@ask_agent.tool
async def search_knowledge(
    ctx: RunContext[BrainDeps], category: str | None = None
) -> str:
    """Search the knowledge repository for frameworks, methodologies, and playbooks."""
    try:
        knowledge = await ctx.deps.storage_service.get_knowledge(category=category)
        if not knowledge:
            return "No knowledge entries found."
        formatted = ["## Knowledge Repository"]
        for k in knowledge:
            formatted.append(f"- [{k['category']}] **{k['title']}**")
            preview = k.get("content", "")[:ctx.deps.config.pattern_preview_limit]
            if preview:
                formatted.append(f"  {preview}")
        # Add graph relationships if available
        if ctx.deps.graphiti_service:
            try:
                query_str = category or "knowledge frameworks methodologies"
                graphiti_rels = await ctx.deps.graphiti_service.search(query_str)
                if graphiti_rels:
                    formatted.append("\n## Related Entities")
                    for rel in graphiti_rels[:5]:
                        formatted.append(
                            f"- {rel.get('source', '?')} --[{rel.get('relationship', '?')}]--> {rel.get('target', '?')}"
                        )
            except Exception as e:
                logger.debug("Graphiti search failed in search_knowledge (non-critical): %s", e)
        return "\n".join(formatted)
    except Exception as e:
        logger.warning("search_knowledge failed: %s", type(e).__name__)
        return f"Knowledge search unavailable: {type(e).__name__}"
