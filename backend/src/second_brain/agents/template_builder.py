"""Template Builder agent — deconstructs content into reusable template blueprints.

Analyzes deliverables and captures the complete content structure as a
fill-in-the-blank template with [PLACEHOLDER] markers.
"""

import logging
from pydantic_ai import Agent, ModelRetry, RunContext
from second_brain.agents.utils import all_tools_failed, format_pattern_registry, tool_error
from second_brain.deps import BrainDeps
from second_brain.schemas import DeconstructedTemplate

logger = logging.getLogger(__name__)

template_builder_agent = Agent(
    deps_type=BrainDeps,
    output_type=DeconstructedTemplate,
    retries=5,
    instructions=(
        "You deconstruct the user's content into a reusable template.\n\n"
        "BODY RULES (`body` field) — MOST IMPORTANT:\n"
        "Take the user's content and make it REUSABLE for any topic/industry.\n"
        "Replace with [PLACEHOLDER_NAME] markers:\n"
        "- All topic-specific nouns (tools, platforms, products, industries)\n"
        "- All numbers, metrics, timeframes\n"
        "- All specific examples, filter names, features\n"
        "- All specific outcomes and results\n"
        "- All audience/role references specific to one niche\n\n"
        "KEEP as literal text:\n"
        "- Transition phrases ('But there's a better way', 'The best part?')\n"
        "- Structural connectors ('Try these', 'Save this', 'While...still work')\n"
        "- The formatting pattern (line breaks, arrows, emojis, spacing)\n"
        "- Generic action words ('set up', 'check', 'combining')\n"
        "- The rhetorical flow and rhythm\n\n"
        "The template should work for ANY topic — someone should be able to "
        "fill in the blanks for fitness, real estate, SaaS, cooking, anything.\n\n"
        "STRUCTURE (`structure_hint` field):\n"
        "- Multi-line abstract framework, each section on its own line\n"
        "- Use {curly brace descriptors} for each section\n\n"
        "WRITEPRINT (`writeprint`): voice/tone/style description of the content\n\n"
        "OTHER: name, content_type, when_to_use, when_not_to_use, "
        "customization_guide, tags"
    ),
)


@template_builder_agent.output_validator
async def validate_template(
    ctx: RunContext[BrainDeps], output: DeconstructedTemplate
) -> DeconstructedTemplate:
    """Validate template output with deterministic error detection."""
    # Early return if error already set
    if output.error:
        return output

    # Deterministic check: extract tool outputs from ctx.messages
    tool_outputs = []
    for msg in ctx.messages:
        if hasattr(msg, "parts"):
            for part in msg.parts:
                if hasattr(part, "content") and isinstance(part.content, str):
                    tool_outputs.append(part.content)

    # If all tools failed, set error and return
    if tool_outputs and all_tools_failed(tool_outputs):
        if not output.error:
            output = output.model_copy(update={
                "error": "All template analysis backends unavailable. Template extraction skipped.",
            })
        return output

    # Normal validation (only if no error)
    if not output.body:
        raise ModelRetry(
            "Missing body. Take the user's ACTUAL content and replace specific "
            "details with [PLACEHOLDER] markers. Keep everything else verbatim. "
            "If tools failed, set the error field instead of retrying."
        )
    placeholder_count = output.body.count("[")
    if placeholder_count < 2:
        raise ModelRetry(
            f"Body has only {placeholder_count} placeholders. "
            "Replace specific details with [PLACEHOLDER_NAME] markers. "
            "If tools failed, set the error field instead of retrying."
        )
    if output.structure_hint and "\n" not in output.structure_hint:
        raise ModelRetry(
            "structure_hint must be MULTI-LINE. Each section on its own line "
            "with {curly brace descriptors}. Never a flat one-liner. "
            "If tools failed, set the error field instead of retrying."
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
