"""LinkedIn Hook Writer agent — generates scroll-stopping opening lines."""

import logging

from pydantic_ai import Agent, ModelRetry, RunContext

from second_brain.agents.utils import load_voice_context, tool_error
from second_brain.deps import BrainDeps
from second_brain.schemas import HookWriterResult

logger = logging.getLogger(__name__)

HOOK_CATEGORIES = [
    "bold-statement",
    "self-deprecating",
    "curiosity-gap",
    "contrarian",
    "stat-lead",
    "question",
    "dialogue-scene",
    "meta-platform",
]

hook_writer_agent = Agent(
    deps_type=BrainDeps,
    output_type=HookWriterResult,
    retries=3,
    instructions=(
        "You are a LinkedIn Hook Writer — a specialist in creating scroll-stopping "
        "opening lines for LinkedIn posts.\n\n"
        "HOOK CATEGORIES (generate at least one from each requested category):\n"
        "1. Bold Statement — lead with a surprising claim or achievement\n"
        "   Example: 'I did it. $1M in earnings with less than 100K followers.'\n"
        "2. Self-Deprecating — disarm with humor and vulnerability\n"
        "   Example: 'As blunders go, this is a fairly substantial one.'\n"
        "3. Curiosity Gap — tease without revealing\n"
        "   Example: 'This is gonna make the business strategists cry...'\n"
        "4. Contrarian — challenge conventional wisdom\n"
        "   Example: 'Stop wasting decades chasing titles that won't matter when you're 60.'\n"
        "5. Stat/Number Lead — anchor with a specific data point\n"
        "   Example: '12 months and 70lbs between these photos.'\n"
        "6. Question Hook — ask something the reader needs answered\n"
        "   Example: 'How do I launch my coaching business if I don't have a niche yet?'\n"
        "7. Dialogue/Scene — drop into a moment\n"
        "   Example: 'An older lady approached me and my dog while we sat on a bench...'\n"
        "8. Meta/Platform — break the fourth wall\n"
        "   Example: 'Me: Takes a few days off posting. LinkedIn: DID YOU DIE?'\n\n"
        "RULES:\n"
        "- Generate 3-7 hook variations\n"
        "- Each hook must work BEFORE LinkedIn's 'see more' truncation (~210 chars)\n"
        "- Hooks must be specific to the topic, not generic\n"
        "- Match the user's voice/tone if voice guide is available\n"
        "- Never start with 'I'm excited to announce' or similar AI-sounding phrases\n"
        "- Vary the categories — don't generate 5 hooks of the same type\n"
        "- The hook_type field should reflect the PRIMARY category used across hooks"
    ),
)


@hook_writer_agent.output_validator
async def validate_hooks(
    ctx: RunContext[BrainDeps], output: HookWriterResult
) -> HookWriterResult:
    """Validate hook quality and quantity."""
    if output.error:
        return output
    if not output.hooks or len(output.hooks) < 3:
        raise ModelRetry(
            "Generate at least 3 hook variations. You provided "
            f"{len(output.hooks) if output.hooks else 0}."
        )
    long_hooks = [h for h in output.hooks if len(h) > 220]
    if long_hooks:
        raise ModelRetry(
            f"{len(long_hooks)} hook(s) exceed 220 characters. LinkedIn truncates "
            "at ~210 chars. Shorten them so they work before 'see more'."
        )
    if not output.hook_type:
        raise ModelRetry("Specify the primary hook_type category used.")
    return output


@hook_writer_agent.tool
async def load_voice_guide(ctx: RunContext[BrainDeps], voice_user_id: str = "") -> str:
    """Load the user's voice and tone guide to match hook style."""
    try:
        uid = voice_user_id if voice_user_id else None
        return await load_voice_context(ctx.deps, preview_limit=200, voice_user_id=uid)
    except Exception as e:
        return tool_error("load_voice_guide", e)


@hook_writer_agent.tool
async def search_hook_examples(ctx: RunContext[BrainDeps], topic: str = "") -> str:
    """Search template bank for LinkedIn templates with hook patterns."""
    try:
        templates = await ctx.deps.storage_service.get_templates(
            content_type="linkedin"
        )
        if not templates:
            return "No LinkedIn templates found in bank."
        lines = []
        for t in templates[:10]:
            name = t.get("name", "Untitled")
            body = t.get("body", "")
            # Extract first line as hook example
            first_line = body.split("\n")[0].strip() if body else ""
            tags = ", ".join(t.get("tags", []))
            lines.append(f"- **{name}** [{tags}]: {first_line}")
        return "LinkedIn hook examples from template bank:\n" + "\n".join(lines)
    except Exception as e:
        return tool_error("search_hook_examples", e)


@hook_writer_agent.tool
async def search_past_content(ctx: RunContext[BrainDeps], topic: str = "") -> str:
    """Search memory for past LinkedIn content and hooks."""
    try:
        query = f"linkedin hook {topic}" if topic else "linkedin hook opening line"
        result = await ctx.deps.memory_service.search(query)
        memories = result.memories if hasattr(result, "memories") else []
        if not memories:
            return "No past LinkedIn hooks found in memory."
        lines = []
        for m in memories[:5]:
            content = m.get("memory", "")[:200]
            lines.append(f"- {content}")
        return "Past LinkedIn content:\n" + "\n".join(lines)
    except Exception as e:
        return tool_error("search_past_content", e)
