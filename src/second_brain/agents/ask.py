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
    sections = []
    for category in ["company", "personal", "customers"]:
        content = await ctx.deps.storage_service.get_memory_content(category)
        if content:
            section_parts = [f"## {category.title()}"]
            for item in content:
                section_parts.append(f"### {item['title']}\n{item['content'][:1000]}")
            sections.append("\n".join(section_parts))
    return "\n\n".join(sections) if sections else "Brain context is empty. Run /setup first."


@ask_agent.tool
async def find_relevant_patterns(
    ctx: RunContext[BrainDeps], query: str
) -> str:
    """Find patterns relevant to the current question."""
    result = await ctx.deps.memory_service.search(query, limit=5)
    patterns = await ctx.deps.storage_service.get_patterns()

    # Collect relations
    relations = result.relations
    if ctx.deps.graphiti_service:
        try:
            graphiti_rels = await ctx.deps.graphiti_service.search(query, limit=5)
            relations = relations + graphiti_rels
        except Exception as e:
            logger.debug("Graphiti search failed (non-critical): %s", e)

    formatted = ["## Semantic Memory Matches"]
    for r in result.memories[:5]:
        memory = r.get("memory", r.get("result", ""))
        formatted.append(f"- {memory}")

    if relations:
        formatted.append("\n## Graph Relationships")
        for rel in relations:
            formatted.append(
                f"- {rel.get('source', '?')} --[{rel.get('relationship', '?')}]--> {rel.get('target', '?')}"
            )

    formatted.append("\n## Pattern Registry")
    for p in patterns[:10]:
        formatted.append(
            f"- [{p['confidence']}] **{p['name']}**: {p.get('pattern_text', '')[:150]}"
        )
    return "\n".join(formatted)


@ask_agent.tool
async def find_similar_experiences(
    ctx: RunContext[BrainDeps], query: str
) -> str:
    """Find past work similar to the current question."""
    result = await ctx.deps.memory_service.search(
        f"past experience: {query}", limit=5
    )
    experiences = await ctx.deps.storage_service.get_experiences(limit=5)

    # Collect relations
    relations = result.relations
    if ctx.deps.graphiti_service:
        try:
            graphiti_rels = await ctx.deps.graphiti_service.search(query, limit=5)
            relations = relations + graphiti_rels
        except Exception as e:
            logger.debug("Graphiti search failed (non-critical): %s", e)

    formatted = ["## Similar Past Work"]
    for e in experiences:
        score = f" (score: {e['review_score']})" if e.get("review_score") else ""
        formatted.append(f"- **{e['name']}** [{e['category']}]{score}")
        if e.get("learnings"):
            formatted.append(f"  Learnings: {e['learnings'][:200]}")

    if relations:
        formatted.append("\n## Graph Relationships")
        for rel in relations:
            formatted.append(
                f"- {rel.get('source', '?')} --[{rel.get('relationship', '?')}]--> {rel.get('target', '?')}"
            )

    return "\n".join(formatted)
