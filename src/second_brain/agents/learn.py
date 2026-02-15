"""LearnAgent — extract patterns, insights, and experiences from raw text."""

from datetime import date

from pydantic_ai import Agent, RunContext

from second_brain.deps import BrainDeps
from second_brain.schemas import LearnResult

learn_agent = Agent(
    deps_type=BrainDeps,
    output_type=LearnResult,
    instructions=(
        "You are a learning extraction agent for an AI Second Brain. "
        "Your job: analyze raw text from work sessions and extract structured learnings. "
        "ALWAYS search for existing patterns first to avoid duplicates. "
        "If an input reinforces an existing pattern, mark is_reinforcement=True and upgrade its confidence. "
        "Confidence rules: LOW (new, 1st use), MEDIUM (2-4 uses), HIGH (5+ uses). "
        "Extract anti-patterns when the input describes what NOT to do. "
        "Store every extracted pattern and add key learnings to semantic memory. "
        "Create an experience entry if the input describes a complete work session with outcomes."
    ),
)


@learn_agent.instructions
async def inject_existing_patterns(ctx: RunContext[BrainDeps]) -> str:
    """Inject existing pattern names to prevent duplicate extraction."""
    patterns = await ctx.deps.storage_service.get_patterns()
    if not patterns:
        return "No existing patterns in the brain yet. All extractions will be new."
    names = [p["name"] for p in patterns[:ctx.deps.config.pattern_context_limit]]
    return (
        f"Existing patterns (check for reinforcement before creating new): "
        f"{', '.join(names)}"
    )


@learn_agent.tool
async def search_existing_patterns(
    ctx: RunContext[BrainDeps], query: str
) -> str:
    """Search for existing patterns that might match what you're about to extract.
    Call this BEFORE creating new patterns to check for reinforcement opportunities."""
    patterns = await ctx.deps.storage_service.get_patterns()
    if not patterns:
        return "No existing patterns found. Safe to create new ones."
    matching = [
        p for p in patterns
        if query.lower() in p.get("name", "").lower()
        or query.lower() in p.get("pattern_text", "").lower()
    ]
    if not matching:
        return f"No patterns matching '{query}'. This appears to be a new pattern."
    formatted = []
    for p in matching:
        formatted.append(
            f"- {p['name']} (confidence: {p.get('confidence', 'LOW')}, "
            f"uses: {p.get('use_count', 1)})"
        )
    return f"Existing matches:\n" + "\n".join(formatted)


@learn_agent.tool
async def store_pattern(
    ctx: RunContext[BrainDeps],
    name: str,
    topic: str,
    pattern_text: str,
    confidence: str = "LOW",
    evidence: list[str] | None = None,
    anti_patterns: list[str] | None = None,
    context: str = "",
    source_experience: str = "",
) -> str:
    """Store an extracted pattern in the Supabase pattern registry.
    Use confidence='LOW' for new patterns, 'MEDIUM' for reinforced (2+ uses), 'HIGH' for proven (5+ uses)."""
    pattern_data = {
        "name": name,
        "topic": topic,
        "pattern_text": pattern_text,
        "confidence": confidence,
        "evidence": evidence or [],
        "anti_patterns": anti_patterns or [],
        "context": context,
        "source_experience": source_experience,
        "date_updated": str(date.today()),
    }
    await ctx.deps.storage_service.upsert_pattern(pattern_data)
    return f"Stored pattern '{name}' (confidence: {confidence}) in registry."


@learn_agent.tool
async def add_to_memory(
    ctx: RunContext[BrainDeps],
    content: str,
    category: str = "learning",
) -> str:
    """Store a key learning or insight in Mem0 semantic memory for future recall.
    Use for insights that don't fit a structured pattern format."""
    metadata = {"category": category, "source": "learn_agent"}
    await ctx.deps.memory_service.add(content, metadata=metadata)
    return f"Added to semantic memory (category: {category})."


@learn_agent.tool
async def store_experience(
    ctx: RunContext[BrainDeps],
    name: str,
    category: str,
    output_summary: str,
    learnings: str,
    patterns_extracted: list[str] | None = None,
) -> str:
    """Store a work experience entry in Supabase. Only call this if the input
    describes a complete work session with clear outcomes."""
    experience_data = {
        "name": name,
        "category": category,
        "output_summary": output_summary,
        "learnings": learnings,
        "patterns_extracted": patterns_extracted or [],
    }
    await ctx.deps.storage_service.add_experience(experience_data)
    return f"Recorded experience '{name}' (category: {category})."
