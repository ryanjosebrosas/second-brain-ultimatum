"""Essay Writer agent — long-form content creation with STIRC protocol.

Creates intellectually rigorous, stylistically compelling essays using an
8-step construction protocol with angle scoring and quality calibration.
"""

import logging
from pydantic_ai import Agent, ModelRetry, RunContext
from second_brain.deps import BrainDeps
from second_brain.schemas import EssayResult

logger = logging.getLogger(__name__)

essay_writer_agent = Agent(
    deps_type=BrainDeps,
    output_type=EssayResult,
    retries=3,
    instructions=(
        "You are a world-class essayist. Create intellectually rigorous, "
        "stylistically compelling essays.\n\n"
        "WRITING PROCESS (follow in order):\n"
        "1. Identify the topic and evaluate the angle using STIRC scoring\n"
        "2. Formulate a central question the essay answers\n"
        "3. Choose structural framework: argumentative/explanatory/narrative\n"
        "4. Load voice guide and relevant patterns from brain\n"
        "5. Write the essay following the Five Laws\n"
        "6. Self-review against the quality checklist\n\n"
        "STIRC ANGLE SCORING (each 1-5, threshold 18/25):\n"
        "- Surprising: Contradicts common assumptions\n"
        "- True: Supported by evidence\n"
        "- Important: Matters to people\n"
        "- Relevant: Connects to current concerns\n"
        "- Cool: Inherently interesting\n\n"
        "FIVE WRITING LAWS:\n"
        "1. Active voice always (object then action)\n"
        "2. Remove needless words — every word earns its place\n"
        "3. No adverbs — strong verbs don't need modification\n"
        "4. Write simply — 4th-7th grade reading level\n"
        "5. First sentence must demand attention\n\n"
        "AI PATTERNS TO AVOID: em dashes for drama, 'Here's the thing:', "
        "'Let me explain why', Three. Word. Sentences., fake enthusiasm "
        "(amazing, incredible), rhetorical questions as transitions, "
        "'In conclusion'.\n\n"
        "OUTPUT RULES:\n"
        "- The 'essay' field MUST contain the COMPLETE essay text\n"
        "- The 'stirc_score' MUST reflect your honest angle evaluation\n"
        "- Set word_count to the actual word count\n"
        "- Put editorial notes in 'notes', NOT in the essay"
    ),
)


@essay_writer_agent.output_validator
async def validate_essay(ctx: RunContext[BrainDeps], output: EssayResult) -> EssayResult:
    """Validate essay quality."""
    word_count = len(output.essay.split())
    if word_count < 100:
        raise ModelRetry(
            f"Essay is only {word_count} words. Essays must be substantial "
            "(at least 300 words for short essays, 800+ for full essays). "
            "Write the complete essay, not a summary."
        )
    threshold = ctx.deps.config.stirc_threshold
    if output.stirc_score > 0 and output.stirc_score < threshold:
        raise ModelRetry(
            f"STIRC score {output.stirc_score} is below threshold {threshold}. "
            "Reconsider the angle. Find a more surprising, relevant, or "
            "important perspective. Re-evaluate and either improve the angle "
            "or explain why this angle is still worth pursuing."
        )
    if not output.title:
        raise ModelRetry("Essay must have a title. Provide a compelling, specific title.")
    # Auto-set word count
    output.word_count = word_count
    return output


@essay_writer_agent.tool
async def load_voice_and_patterns(ctx: RunContext[BrainDeps], topic: str) -> str:
    """Load voice guide and relevant patterns for the essay topic."""
    try:
        parts = []
        # Voice guide
        voice = await ctx.deps.storage_service.get_memory_content("style-voice")
        if voice:
            parts.append("Voice guide:\n" + "\n".join(v.get("content", "") for v in voice[:2]))
        # Relevant patterns
        patterns = await ctx.deps.storage_service.get_patterns(topic=topic)
        if patterns:
            from second_brain.agents.utils import format_pattern_registry
            parts.append("Relevant patterns:\n" + format_pattern_registry(patterns))
        return "\n\n".join(parts) if parts else "No voice guide or patterns found."
    except Exception as e:
        from second_brain.agents.utils import tool_error
        return tool_error("load_voice_and_patterns", e)


@essay_writer_agent.tool
async def load_examples(ctx: RunContext[BrainDeps], content_type: str = "essay") -> str:
    """Load example content for reference."""
    try:
        examples = await ctx.deps.storage_service.get_examples(content_type=content_type)
        if not examples:
            return "No examples found for this content type."
        lines = []
        for ex in examples[:3]:
            lines.append(f"- {ex.get('title', 'Untitled')}: {ex.get('content', '')[:200]}...")
        return "Example references:\n" + "\n".join(lines)
    except Exception as e:
        from second_brain.agents.utils import tool_error
        return tool_error("load_examples", e)


@essay_writer_agent.tool
async def search_research_context(ctx: RunContext[BrainDeps], query: str) -> str:
    """Search brain memory for research context relevant to the essay topic."""
    try:
        import asyncio
        results = await asyncio.to_thread(ctx.deps.memory_service.search, query, limit=5)
        if not results:
            return "No research context found in memory."
        from second_brain.agents.utils import format_memories
        return format_memories(results, limit=5)
    except Exception as e:
        from second_brain.agents.utils import tool_error
        return tool_error("search_research_context", e)
