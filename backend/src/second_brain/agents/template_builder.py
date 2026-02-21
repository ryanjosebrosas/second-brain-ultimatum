"""Template Builder agent — deconstructs content into reusable template blueprints.

Analyzes deliverables and captures the complete content structure as a
fill-in-the-blank template with [PLACEHOLDER] markers.
"""

import logging
from pydantic_ai import Agent, ModelRetry, RunContext
from second_brain.agents.utils import format_pattern_registry, tool_error
from second_brain.deps import BrainDeps
from second_brain.schemas import DeconstructedTemplate

logger = logging.getLogger(__name__)

template_builder_agent = Agent(
    deps_type=BrainDeps,
    output_type=DeconstructedTemplate,
    retries=5,
    instructions=(
        "You are a master of content analysis, frameworks, structural understanding, "
        "and template creation. You identify and interpret implicit information with ease "
        "and with an instinct for what makes writing pop.\n\n"
        "Your output has three core pieces:\n"
        "1. A WRITEPRINT (`writeprint` field) — the voice/tone/style fingerprint\n"
        "2. A STRUCTURE (`structure_hint` field) — the visual-shape framework\n"
        "3. A TEMPLATE BODY (`body` field) — the fill-in-the-blank blueprint\n\n"
        "WRITEPRINT RULES (`writeprint` field):\n"
        "- Capture: lexical choices, syntactic patterns, register, idiosyncratic elements\n"
        "- Format: brief unambiguous description of the writer's voice, tone, and style\n"
        "- Example: 'Motivational and conversational tone with personal narrative style. "
        "Uses first-person perspective and simple, direct language. Incorporates personal "
        "experiences and progress over time to inspire and educate. Presents ideas in a "
        "simple problem-solution format. Employs repetition and parallel structure for "
        "emphasis and clarity.'\n\n"
        "STRUCTURE RULES (`structure_hint` field):\n"
        "This is the VISUAL SHAPE FRAMEWORK — a multi-line blueprint showing exactly how\n"
        "the content is laid out physically. It must look like a mini-template itself.\n\n"
        "CRITICAL: This must be MULTI-LINE with actual line breaks, NOT a flat one-liner.\n"
        "It shows the physical shape someone would follow to write new content.\n\n"
        "Format rules:\n"
        "- Start with: **{Post Type Name}**\n"
        "- Each structural element on its OWN LINE\n"
        "- Use {curly brace descriptors} for each section\n"
        "- Show line breaks, spacing, and visual rhythm explicitly\n"
        "- Note rhetorical devices inline\n\n"
        "GOOD example (multi-line visual framework):\n"
        "  **Blunders & Lessons Post**\n"
        "  {self-deprecating hook confession — 1 sentence}\n"
        "  \n"
        "  {dismissive one-liner: 'But it's fine. It's FINE.'}\n"
        "  \n"
        "  {humorous time reveal with emoji — 'I've only been doing X for *checks calendar* Y'}\n"
        "  \n"
        "  {transition to lessons — 'So I guess this is your reminder that:'}\n"
        "  \n"
        "  {emoji} {lesson 1}\n"
        "  {emoji} {lesson 2}\n"
        "  {emoji} {lesson 3 + CTA woven in}\n"
        "  \n"
        "  {gratitude shoutout — 'Thanks to [person] for [attribute]'}\n"
        "  \n"
        "  Love\n"
        "  {signature}\n\n"
        "BAD example (flat one-liner — NEVER do this):\n"
        "  Blunders & Lessons Pattern [Hook] [Follow-up] [Time reveal] [Lessons] [CTA]\n\n"
        "TEMPLATE BODY RULES (`body` field):\n"
        "The body is a FILL-IN-THE-BLANK version of the original content.\n"
        "- Replace specific details with [PLACEHOLDER_NAME] markers\n"
        "- Use UPPER_SNAKE_CASE inside brackets: [HOOK_STATEMENT], [KEY_METRIC]\n"
        "- Be descriptive: [PERSONAL_ANECDOTE] not just [TEXT]\n"
        "- Group related placeholders: [BENEFIT_1], [BENEFIT_2], [BENEFIT_3]\n"
        "- PRESERVE the original's line breaks, spacing, and physical layout exactly\n"
        "- Keep transitional phrases and structural connectors verbatim\n"
        "- The body MUST contain at least 3 [PLACEHOLDER] markers\n\n"
        "KEY DIFFERENCE between structure_hint and body:\n"
        "- structure_hint = abstract framework with {curly brace descriptors} — reusable shape\n"
        "- body = concrete fill-in-the-blank with [PLACEHOLDER] markers — closer to original\n\n"
        "ADDITIONAL OUTPUT:\n"
        "- `name`: memorable name reflecting the template's theme/style\n"
        "- `content_type`: slug (linkedin, email, case-study, etc.)\n"
        "- `when_to_use` and `when_not_to_use`: usage guidance\n"
        "- `customization_guide`: what to customize vs keep standard\n"
        "- `tags`: relevant categorization tags"
    ),
)


@template_builder_agent.output_validator
async def validate_template(
    ctx: RunContext[BrainDeps], output: DeconstructedTemplate
) -> DeconstructedTemplate:
    """Validate template quality — enforce full structure."""
    if not output.when_to_use:
        raise ModelRetry(
            f"Template '{output.name}' is missing 'when_to_use' guidance. "
            "Every template MUST specify when it should be applied."
        )
    if not output.body:
        raise ModelRetry(
            f"Template '{output.name}' has no body. "
            "Provide the full template structure with [PLACEHOLDER] markers."
        )
    placeholder_count = output.body.count("[")
    if placeholder_count < 3:
        raise ModelRetry(
            f"Template body has only {placeholder_count} placeholders. "
            "A good template needs at least 3 [PLACEHOLDER] markers. "
            "Replace specific details with descriptive [PLACEHOLDER_NAME] markers."
        )
    if not output.structure_hint:
        raise ModelRetry(
            "Missing structure_hint. Must be a MULTI-LINE visual framework showing "
            "the physical shape. Each structural element on its own line with "
            "{curly brace descriptors}. Start with **{Post Type Name}**. "
            "NEVER a flat one-liner."
        )
    if "\n" not in output.structure_hint:
        raise ModelRetry(
            "structure_hint must be MULTI-LINE — each structural element on its own "
            "line. You wrote a flat one-liner. Break it into lines showing the visual "
            "shape: one {descriptor} per line with blank lines for spacing."
        )
    if not output.writeprint:
        raise ModelRetry(
            "Missing writeprint. Capture the writer's voice, tone, and style: "
            "lexical choices, syntactic patterns, register, idiosyncratic elements. "
            "Example: 'Conversational tone with self-deprecating humor. Uses short "
            "punchy sentences and frequent line breaks for emphasis.'"
        )
    return output


@template_builder_agent.tool
async def search_existing_patterns(ctx: RunContext[BrainDeps], topic: str = "") -> str:
    """Search for existing patterns that might already cover this template."""
    try:
        patterns = await ctx.deps.storage_service.get_patterns(topic=topic or None)
        if not patterns:
            return "No existing patterns found."
        return format_pattern_registry(patterns[:10])
    except Exception as e:
        return tool_error("search_existing_patterns", e)


@template_builder_agent.tool
async def search_examples(ctx: RunContext[BrainDeps], content_type: str = "") -> str:
    """Search examples to identify recurring structures."""
    try:
        examples = await ctx.deps.storage_service.get_examples(
            content_type=content_type or None
        )
        if not examples:
            return "No examples found."
        lines = []
        for ex in examples[:5]:
            lines.append(f"- {ex.get('title', 'Untitled')}: {ex.get('content', '')[:150]}...")
        return "Examples:\n" + "\n".join(lines)
    except Exception as e:
        return tool_error("search_examples", e)


@template_builder_agent.tool
async def search_template_bank(ctx: RunContext[BrainDeps], content_type: str = "") -> str:
    """Search the template bank for existing templates of this content type."""
    try:
        templates = await ctx.deps.storage_service.get_templates(
            content_type=content_type or None
        )
        if not templates:
            return "No templates found in the bank."
        lines = ["Existing templates:"]
        for t in templates[:10]:
            tags = ", ".join(t.get("tags", [])) or "none"
            lines.append(
                f"- {t.get('name', 'Untitled')} ({t.get('content_type', '?')}) "
                f"[tags: {tags}]: {t.get('structure_hint', '')}"
            )
        return "\n".join(lines)
    except Exception as e:
        return tool_error("search_template_bank", e)
