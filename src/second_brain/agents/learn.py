"""LearnAgent — extract patterns, insights, and experiences from raw text."""

import logging
from datetime import date

from pydantic_ai import Agent, RunContext

logger = logging.getLogger(__name__)

from second_brain.deps import BrainDeps
from second_brain.schemas import LearnResult

learn_agent = Agent(
    deps_type=BrainDeps,
    output_type=LearnResult,
    instructions=(
        "You are a learning extraction agent for an AI Second Brain. "
        "Your job: analyze raw text from work sessions and extract structured learnings. "
        "ALWAYS search for existing patterns first to avoid duplicates. "
        "If an input reinforces an existing pattern, mark is_reinforcement=True and "
        "use the reinforce_existing_pattern tool, NOT store_pattern. "
        "Only use store_pattern for genuinely new patterns. "
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
    """Store a NEW pattern in the Supabase pattern registry.
    Only use for genuinely new patterns. For reinforcement, use reinforce_existing_pattern."""
    existing = await ctx.deps.storage_service.get_pattern_by_name(name)
    if existing:
        return (
            f"Pattern '{name}' already exists (use_count: {existing.get('use_count', 1)}, "
            f"confidence: {existing.get('confidence', 'LOW')}). "
            f"Use reinforce_existing_pattern instead."
        )
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
    try:
        await ctx.deps.storage_service.insert_pattern(pattern_data)
        # Record growth event (non-blocking)
        try:
            await ctx.deps.storage_service.add_growth_event({
                "event_type": "pattern_created",
                "pattern_name": name,
                "pattern_topic": topic,
                "details": {
                    "confidence": confidence,
                    "evidence_count": len(evidence or []),
                },
            })
        except Exception:
            logger.debug("Failed to record growth event for pattern '%s'", name)
    except Exception as e:
        logger.exception("Failed to insert pattern '%s'", name)
        return f"Error storing pattern '{name}': {e}"
    return f"Stored new pattern '{name}' (confidence: {confidence}) in registry."


@learn_agent.tool
async def reinforce_existing_pattern(
    ctx: RunContext[BrainDeps],
    pattern_name: str,
    new_evidence: list[str] | None = None,
) -> str:
    """Reinforce an existing pattern: increment use_count, upgrade confidence, append evidence.
    Use this when is_reinforcement=True instead of store_pattern."""
    pattern = await ctx.deps.storage_service.get_pattern_by_name(pattern_name)
    if not pattern:
        return (
            f"No existing pattern named '{pattern_name}'. "
            f"Use store_pattern to create it instead."
        )
    try:
        updated = await ctx.deps.storage_service.reinforce_pattern(
            pattern["id"], new_evidence
        )
    except ValueError as e:
        logger.exception("Failed to reinforce pattern '%s'", pattern_name)
        return f"Error reinforcing pattern '{pattern_name}': {e}"
    # Record growth event (non-blocking)
    try:
        old_confidence = pattern.get("confidence", "LOW")
        new_confidence = updated.get("confidence", old_confidence)
        await ctx.deps.storage_service.add_growth_event({
            "event_type": "pattern_reinforced",
            "pattern_name": pattern_name,
            "pattern_topic": pattern.get("topic", ""),
            "details": {
                "new_use_count": updated.get("use_count", 0),
                "old_confidence": old_confidence,
                "new_confidence": new_confidence,
            },
        })
        # Record confidence transition if confidence changed
        if new_confidence != old_confidence:
            await ctx.deps.storage_service.add_growth_event({
                "event_type": "confidence_upgraded",
                "pattern_name": pattern_name,
                "pattern_topic": pattern.get("topic", ""),
                "details": {
                    "from": old_confidence,
                    "to": new_confidence,
                    "use_count": updated.get("use_count", 0),
                },
            })
            await ctx.deps.storage_service.add_confidence_transition({
                "pattern_name": pattern_name,
                "pattern_topic": pattern.get("topic", ""),
                "from_confidence": old_confidence,
                "to_confidence": new_confidence,
                "use_count": updated.get("use_count", 0),
                "reason": f"Reinforced to use_count {updated.get('use_count', 0)}",
            })
    except Exception:
        logger.debug("Failed to record growth/confidence events for '%s'", pattern_name)
    return (
        f"Reinforced pattern '{pattern_name}' → "
        f"use_count: {updated['use_count']}, confidence: {updated['confidence']}"
    )


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
