"""CreateAgent — content creation using brain knowledge."""

import logging

from pydantic_ai import Agent, RunContext

from second_brain.deps import BrainDeps
from second_brain.schemas import CreateResult

logger = logging.getLogger(__name__)

create_agent = Agent(
    deps_type=BrainDeps,
    output_type=CreateResult,
    instructions=(
        "You are a content creation agent for an AI Second Brain. "
        "You draft content in the user's authentic voice using their accumulated knowledge. "
        "ALWAYS load the voice guide and relevant examples before drafting. "
        "Match the communication mode (casual/professional/formal) to the content type. "
        "Follow the Five Writing Laws: active voice, remove needless words, no adverbs, "
        "write simply, hit the reader with the first sentence. "
        "AVOID AI patterns: no em dashes for drama, no 'Here's the thing:', "
        "no fake enthusiasm ('amazing', 'incredible'), "
        "no generic intros ('In today's fast-paced world...'). "
        "Produce a DRAFT for human editing, not final copy. "
        "Include notes about what the human should review or polish. "
        "Set word_count in the output to the actual word count of the draft."
    ),
)


@create_agent.tool
async def load_voice_guide(ctx: RunContext[BrainDeps]) -> str:
    """Load the user's voice and tone guide from the brain for style matching."""
    content = await ctx.deps.storage_service.get_memory_content("style-voice")
    if not content:
        return "No voice guide found. Write in a clear, direct, conversational tone."
    sections = []
    for item in content:
        title = item.get("title", "Untitled")
        text = item.get("content", "")[:ctx.deps.config.content_preview_limit]
        sections.append(f"### {title}\n{text}")
    return "## Voice & Tone Guide\n" + "\n\n".join(sections)


@create_agent.tool
async def load_content_examples(
    ctx: RunContext[BrainDeps], content_type: str
) -> str:
    """Load reference examples of a specific content type from the brain.
    Use this to study the user's past work before drafting."""
    examples = await ctx.deps.storage_service.get_examples(
        content_type=content_type
    )
    if not examples:
        return f"No examples found for type '{content_type}'."
    limit = ctx.deps.config.experience_limit
    sections = []
    for ex in examples[:limit]:
        title = ex.get("title", "Untitled")
        text = ex.get("content", "")[:ctx.deps.config.content_preview_limit]
        sections.append(f"### {title}\n{text}")
    return f"## Examples ({content_type})\n" + "\n\n".join(sections)


@create_agent.tool
async def find_applicable_patterns(
    ctx: RunContext[BrainDeps], topic: str, content_type: str = ""
) -> str:
    """Find brain patterns and semantic memories relevant to the content topic.
    When content_type is provided, uses filtered semantic search for that type."""
    # Semantic search for general memories about the topic
    result = await ctx.deps.memory_service.search(topic)

    # Semantic search for patterns (optionally filtered by content type)
    pattern_memories = []
    try:
        if content_type:
            filters = {
                "AND": [
                    {"category": "pattern"},
                    {"applicable_content_types": {"contains": content_type}},
                ]
            }
        else:
            filters = {"category": "pattern"}
        pattern_result = await ctx.deps.memory_service.search_with_filters(
            topic,
            metadata_filters=filters,
            limit=10,
        )
        pattern_memories = pattern_result.memories
    except Exception:
        logger.debug("Semantic pattern search failed in create_agent")

    # Fall back to Supabase patterns (structured data)
    patterns = await ctx.deps.storage_service.get_patterns()

    # Filter patterns by content type if provided (Supabase fallback)
    if content_type and patterns:
        type_specific = [
            p for p in patterns
            if p.get("applicable_content_types")
            and content_type in p["applicable_content_types"]
        ]
        universal = [
            p for p in patterns
            if p.get("applicable_content_types") is None
        ]
        patterns = type_specific + universal

    sections = []

    if pattern_memories:
        mem_lines = ["## Semantically Matched Patterns"]
        for m in pattern_memories:
            memory = m.get("memory", m.get("result", ""))
            score = m.get("score", 0)
            mem_lines.append(f"- [{score:.2f}] {memory}")
        sections.append("\n".join(mem_lines))

    if patterns:
        pattern_lines = ["## Pattern Registry"]
        for p in patterns:
            text = p.get("pattern_text", "")[:ctx.deps.config.pattern_preview_limit]
            types_label = ""
            if p.get("applicable_content_types"):
                types_label = f" [{', '.join(p['applicable_content_types'])}]"
            pattern_lines.append(
                f"- [{p.get('confidence', 'LOW')}] **{p['name']}**{types_label}: {text}"
            )
        sections.append("\n".join(pattern_lines))

    if result.memories:
        mem_lines = ["## Semantic Memory"]
        for m in result.memories[:5]:
            memory = m.get("memory", m.get("result", ""))
            mem_lines.append(f"- {memory}")
        sections.append("\n".join(mem_lines))

    return "\n\n".join(sections) if sections else "No applicable patterns found."


@create_agent.tool
async def load_audience_context(ctx: RunContext[BrainDeps]) -> str:
    """Load audience and customer context from the brain for targeting."""
    audience = await ctx.deps.storage_service.get_memory_content("audience")
    customers = await ctx.deps.storage_service.get_memory_content("customers")

    sections = []
    for label, items in [("Audience", audience), ("Customers", customers)]:
        if items:
            lines = [f"## {label}"]
            for item in items:
                title = item.get("title", "Untitled")
                text = item.get("content", "")[:ctx.deps.config.content_preview_limit]
                lines.append(f"### {title}\n{text}")
            sections.append("\n".join(lines))

    if not sections:
        return "No audience context found. Write for a general professional audience."
    return "\n\n".join(sections)
