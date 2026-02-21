"""LinkedIn Writer agent — dedicated LinkedIn post creation with hook integration."""

import logging

from pydantic_ai import Agent, ModelRetry, RunContext

from second_brain.agents.utils import (
    all_tools_failed,
    format_memories,
    format_relations,
    load_voice_context,
    tool_error,
)
from second_brain.deps import BrainDeps
from second_brain.schemas import LinkedInPostResult

logger = logging.getLogger(__name__)

POST_STRUCTURES = [
    "origin-story",
    "vulnerability-confession",
    "results-breakdown",
    "contrarian-advice",
    "listicle",
    "hot-take",
    "freeform",
]

linkedin_writer_agent = Agent(
    deps_type=BrainDeps,
    output_type=LinkedInPostResult,
    retries=3,
    instructions=(
        "You are a LinkedIn content specialist. Your process is ALWAYS:\n"
        "1. Load voice guide via load_voice_guide\n"
        "2. Load examples via load_linkedin_examples and templates via search_linkedin_templates\n"
        "3. Find topic patterns via find_linkedin_patterns\n"
        "4. Generate hooks via generate_hooks\n"
        "5. Pick the STRONGEST hook as your opening line\n"
        "6. Select a post structure that fits the topic\n"
        "7. Write the full post\n"
        "8. Validate via validate_draft\n\n"
        "HOOK INTEGRATION (CRITICAL):\n"
        "You MUST call generate_hooks before writing. Pick the strongest hook and "
        "use it as the FIRST LINE of your draft. The hook_used field must match "
        "the opening line exactly.\n\n"
        "POST STRUCTURES — select the best fit:\n"
        "- origin-story: Time anchor → Scene → Obstacle → Decision → Results → Moral\n"
        "- vulnerability-confession: Bold stat → Defense → Transformation list → Empowerment CTA\n"
        "- results-breakdown: Bold claim → Proof → Numbered lessons → CTA\n"
        "- contrarian-advice: Counter-intuitive hook → 'I used to...' → What changed → Framework\n"
        "- listicle: Question hook → Examples → Numbered proof → CTA\n"
        "- hot-take: Provocative opener → Punchline (mic drop, no CTA needed)\n"
        "- freeform: No fixed structure — let the content flow naturally\n\n"
        "VOICE:\n"
        "Mirror the user's voice from the voice guide. If voice profile is specified, "
        "pass voice_user_id to all tools.\n\n"
        "LINKEDIN FORMATTING:\n"
        "- Short paragraphs (1-3 sentences max per paragraph)\n"
        "- First 2-3 lines must hook before LinkedIn's 'see more' truncation (~210 chars)\n"
        "- End with a CTA or thought-provoking question (except hot-takes)\n"
        "- Use line breaks liberally for readability\n"
        "- Hashtags: 3-5 max, at the bottom, relevant to the topic\n"
        "- Emoji: sparingly, only if it fits the user's voice\n\n"
        "USER PROFILE ROUTING:\n"
        "Your prompt may include 'Voice profile: <user_id>'. When present, pass that "
        "user_id to load_voice_guide, load_linkedin_examples, and find_linkedin_patterns "
        "as the voice_user_id parameter.\n\n"
        "ERROR HANDLING:\n"
        "If brain context tools return 'BACKEND_ERROR:' messages, write the best draft "
        "you can without that context. Set the error field to describe which services "
        "were unavailable. A draft without full context is better than no draft at all."
    ),
)


@linkedin_writer_agent.output_validator
async def validate_linkedin_post(
    ctx: RunContext[BrainDeps], output: LinkedInPostResult
) -> LinkedInPostResult:
    """Validate LinkedIn post quality."""
    if output.error:
        return output

    # Deterministic check: if all tools returned errors, set error field and accept
    tool_outputs = []
    for msg in ctx.messages:
        if hasattr(msg, "parts"):
            for part in msg.parts:
                if hasattr(part, "content") and isinstance(part.content, str):
                    tool_outputs.append(part.content)

    if tool_outputs and all_tools_failed(tool_outputs):
        if not output.error:
            output = output.model_copy(update={
                "error": "All brain context backends unavailable. Post written without voice context.",
            })
        return output

    word_count = len(output.draft.split())
    if word_count < 30:
        raise ModelRetry(
            f"Draft is only {word_count} words. LinkedIn posts need at least 30 words. "
            "Write the COMPLETE post text, not a summary."
        )

    if not output.hook_used:
        raise ModelRetry(
            "hook_used is empty. You MUST call generate_hooks first, pick the "
            "strongest hook, and set hook_used to that hook text."
        )

    if output.post_structure not in POST_STRUCTURES:
        raise ModelRetry(
            f"Invalid post_structure '{output.post_structure}'. Must be one of: "
            f"{', '.join(POST_STRUCTURES)}"
        )

    summary_indicators = [
        "here is a draft", "here's a draft", "i would write",
        "the draft would", "this draft covers", "i've created a",
    ]
    draft_lower = output.draft.lower()[:200]
    for indicator in summary_indicators:
        if indicator in draft_lower:
            raise ModelRetry(
                f"The draft appears to be a DESCRIPTION, not the actual post. "
                f"Detected: '{indicator}'. Write the actual LinkedIn post text."
            )

    if output.word_count == 0:
        output.word_count = word_count

    return output


@linkedin_writer_agent.tool
async def generate_hooks(
    ctx: RunContext[BrainDeps], topic: str,
    hook_type: str = "", voice_user_id: str = "",
) -> str:
    """Generate scroll-stopping hook variations for the LinkedIn post topic.
    MUST be called before writing — pick the strongest hook as your opening line.
    Pass voice_user_id to match the user's voice style."""
    try:
        from second_brain.agents.hook_writer import hook_writer_agent

        prompt = f"Write LinkedIn hooks for: {topic}"
        if hook_type:
            prompt += f"\nPreferred hook category: {hook_type}"
        if voice_user_id:
            prompt += f"\nVoice profile: {voice_user_id}"

        result = await hook_writer_agent.run(
            prompt, deps=ctx.deps, usage=ctx.usage,
        )
        out = result.output

        lines = [f"## Hook Options (Category: {out.hook_type})"]
        for i, hook in enumerate(out.hooks, 1):
            lines.append(f"{i}. {hook}")
        if out.reasoning:
            lines.append(f"\nWhy these work: {out.reasoning}")
        lines.append("\nPick the STRONGEST hook and use it as the first line of your post.")
        return "\n".join(lines)
    except Exception as e:
        return tool_error("generate_hooks", e)


@linkedin_writer_agent.tool
async def load_voice_guide(ctx: RunContext[BrainDeps], voice_user_id: str = "") -> str:
    """Load the user's voice and tone guide for style matching.
    Pass voice_user_id for a specific user's voice profile."""
    try:
        uid = voice_user_id if voice_user_id else None
        return await load_voice_context(ctx.deps, include_graph=True, voice_user_id=uid)
    except Exception as e:
        return tool_error("load_voice_guide", e)


@linkedin_writer_agent.tool
async def load_linkedin_examples(
    ctx: RunContext[BrainDeps], voice_user_id: str = "",
) -> str:
    """Load past LinkedIn post examples for style reference.
    Pass voice_user_id for a specific user's examples."""
    try:
        uid = voice_user_id if voice_user_id else None
        examples = await ctx.deps.storage_service.get_examples(
            content_type="linkedin", override_user_id=uid,
        )
        if not examples:
            return "No LinkedIn examples found. Write in a clear, direct style."
        limit = ctx.deps.config.experience_limit
        sections = []
        for ex in examples[:limit]:
            title = ex.get("title", "Untitled")
            text = ex.get("content", "")[:ctx.deps.config.content_preview_limit]
            sections.append(f"### {title}\n{text}")
        return "## LinkedIn Examples\n" + "\n\n".join(sections)
    except Exception as e:
        return tool_error("load_linkedin_examples", e)


@linkedin_writer_agent.tool
async def find_linkedin_patterns(
    ctx: RunContext[BrainDeps], topic: str, voice_user_id: str = "",
) -> str:
    """Find brain patterns and semantic memories relevant to the topic.
    Searches for topic knowledge and LinkedIn-specific writing patterns."""
    try:
        uid = voice_user_id if voice_user_id else None

        # Topic knowledge from shared memory
        result = await ctx.deps.memory_service.search(topic)
        general_memories = result.memories
        general_relations = result.relations

        # LinkedIn-specific writing patterns
        pattern_memories = []
        pattern_relations = []
        try:
            filters = {
                "AND": [
                    {"category": "pattern"},
                    {"applicable_content_types": {"contains": "linkedin"}},
                ]
            }
            pattern_result = await ctx.deps.memory_service.search_with_filters(
                topic, metadata_filters=filters, limit=10,
                override_user_id=uid,
            )
            pattern_memories = pattern_result.memories
            pattern_relations = pattern_result.relations
        except Exception:
            logger.debug("Semantic pattern search failed in linkedin_writer")

        # Supabase patterns filtered to LinkedIn
        patterns = await ctx.deps.storage_service.get_patterns()
        if patterns:
            patterns = [
                p for p in patterns
                if (p.get("applicable_content_types")
                    and "linkedin" in p["applicable_content_types"])
                or p.get("applicable_content_types") is None
            ]

        sections = []

        if pattern_memories:
            sections.append(
                "## LinkedIn Patterns\n" + format_memories(pattern_memories)
            )

        if patterns:
            lines = ["## Pattern Registry"]
            for p in patterns:
                text = p.get("pattern_text", "")[:ctx.deps.config.pattern_preview_limit]
                lines.append(f"- [{p.get('confidence', 'LOW')}] **{p['name']}**: {text}")
            sections.append("\n".join(lines))

        if general_memories:
            mem_lines = ["## Topic Knowledge"]
            for m in general_memories[:5]:
                memory = m.get("memory", m.get("result", ""))
                mem_lines.append(f"- {memory}")
            sections.append("\n".join(mem_lines))

        all_relations = (general_relations or []) + pattern_relations
        rel_text = format_relations(all_relations)
        if rel_text:
            sections.append(rel_text)

        return "\n\n".join(sections) if sections else "No applicable patterns found."
    except Exception as e:
        return tool_error("find_linkedin_patterns", e)


@linkedin_writer_agent.tool
async def search_linkedin_templates(ctx: RunContext[BrainDeps]) -> str:
    """Search the template bank for LinkedIn post templates.
    Returns template names, structures, and when-to-use guidance."""
    try:
        templates = await ctx.deps.storage_service.get_templates(
            content_type="linkedin"
        )
        if not templates:
            return "No LinkedIn templates in the bank. Use freeform structure."
        lines = ["## LinkedIn Templates"]
        for t in templates[:10]:
            name = t.get("name", "Untitled")
            desc = t.get("description", "")
            structure = t.get("structure_hint", "")
            when = t.get("when_to_use", "")
            lines.append(f"### {name}")
            if desc:
                lines.append(f"  {desc}")
            if structure:
                lines.append(f"  Structure: {structure}")
            if when:
                lines.append(f"  When to use: {when}")
        return "\n".join(lines)
    except Exception as e:
        return tool_error("search_linkedin_templates", e)


@linkedin_writer_agent.tool
async def validate_draft(ctx: RunContext[BrainDeps], draft: str) -> str:
    """Validate a LinkedIn post draft for formatting and quality.
    Call this before finalizing your output."""
    try:
        issues = []
        word_count = len(draft.split())

        # LinkedIn posts typically 100-1300 words
        if word_count > 1300:
            issues.append(
                f"Draft is {word_count} words — quite long for LinkedIn. "
                "Consider tightening to keep readers engaged."
            )
        elif word_count < 30:
            issues.append(
                f"Draft is only {word_count} words — very short. "
                "Make sure the content is complete."
            )

        # Check hook length (first line should be under 210 chars)
        first_line = draft.strip().split("\n")[0].strip()
        if len(first_line) > 210:
            issues.append(
                f"Opening line is {len(first_line)} chars — LinkedIn truncates "
                "at ~210 chars. Shorten the hook so it works before 'see more'."
            )

        # Check for long paragraphs
        paragraphs = [p.strip() for p in draft.split("\n\n") if p.strip()]
        long_paras = [p for p in paragraphs if len(p.split()) > 60]
        if long_paras:
            issues.append(
                f"{len(long_paras)} paragraph(s) exceed 60 words. "
                "Break them up — LinkedIn readers skim."
            )

        if not issues:
            return f"Draft validates OK. Word count: {word_count}."
        return "Validation issues:\n" + "\n".join(f"- {i}" for i in issues)
    except Exception as e:
        return tool_error("validate_draft", e)
