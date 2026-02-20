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
    retries=3,
    instructions=(
        "You are a Template Deconstructor. Given a piece of content, you produce a "
        "complete reusable template blueprint — preserving the FULL structure.\n\n"
        "DECONSTRUCTION RULES:\n"
        "1. Preserve the COMPLETE section structure, headings, formatting, and flow\n"
        "2. Replace specific details with descriptive [PLACEHOLDER_NAME] markers\n"
        "   Example: 'John Smith, CEO of Acme Corp' -> '[PERSON_NAME], [TITLE] of [COMPANY_NAME]'\n"
        "3. Keep structural elements verbatim (transitions, section headers, formatting)\n"
        "4. Mark what is customizable vs what should stay standard\n"
        "5. Identify the content type slug (linkedin, email, case-study, etc.)\n\n"
        "PLACEHOLDER CONVENTIONS:\n"
        "- Use UPPER_SNAKE_CASE inside brackets: [HOOK_STATEMENT], [KEY_METRIC], [CTA_LINK]\n"
        "- Be descriptive: [PERSONAL_ANECDOTE] not just [TEXT]\n"
        "- Group related placeholders: [BENEFIT_1], [BENEFIT_2], [BENEFIT_3]\n\n"
        "QUALITY REQUIREMENTS:\n"
        "- The body MUST contain at least 3 [PLACEHOLDER] markers\n"
        "- The body MUST preserve the original's section structure completely\n"
        "- Include 'when to use' and 'when NOT to use' guidance\n"
        "- Suggest relevant tags for categorization\n"
        "- Provide a structure_hint summarizing the section flow"
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
            "Missing structure_hint. Summarize the section flow "
            "(e.g. 'Hook -> Body -> Evidence -> CTA')."
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
