"""RecallAgent — semantic memory search across Mem0 and Supabase."""

from pydantic_ai import Agent, RunContext

from second_brain.deps import BrainDeps
from second_brain.schemas import RecallResult

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
    results = await ctx.deps.memory_service.search(query, limit=10)
    if not results:
        return "No semantic matches found."
    formatted = []
    for r in results:
        memory = r.get("memory", r.get("result", ""))
        score = r.get("score", 0)
        formatted.append(f"- [{score:.2f}] {memory}")
    return "\n".join(formatted)


@recall_agent.tool
async def search_patterns(
    ctx: RunContext[BrainDeps], topic: str | None = None
) -> str:
    """Search the pattern registry in Supabase."""
    patterns = await ctx.deps.storage_service.get_patterns(topic=topic)
    if not patterns:
        return "No patterns found in registry."
    formatted = []
    for p in patterns:
        formatted.append(
            f"- [{p['confidence']}] {p['name']}: {p.get('pattern_text', '')[:200]}"
        )
    return "\n".join(formatted)


@recall_agent.tool
async def search_experiences(
    ctx: RunContext[BrainDeps], category: str | None = None
) -> str:
    """Search past experiences in Supabase."""
    experiences = await ctx.deps.storage_service.get_experiences(category=category)
    if not experiences:
        return "No past experiences found."
    formatted = []
    for e in experiences:
        score_str = f" (score: {e['review_score']})" if e.get("review_score") else ""
        formatted.append(f"- {e['name']} [{e['category']}]{score_str}")
    return "\n".join(formatted)
