"""Template Builder agent — identifies and captures reusable frameworks.

Analyzes deliverables for patterns worth templating. Follows the
'third time is the template' principle.
"""

import logging
from pydantic_ai import Agent, ModelRetry, RunContext
from second_brain.deps import BrainDeps
from second_brain.schemas import TemplateBuilderResult

logger = logging.getLogger(__name__)

template_builder_agent = Agent(
    deps_type=BrainDeps,
    output_type=TemplateBuilderResult,
    retries=3,
    instructions=(
        "You are a Template Builder. Analyze deliverables and identify "
        "structures worth capturing as reusable templates.\n\n"
        "TEMPLATE DETECTION RULES:\n"
        "1. 'Third time is the template' — recurring structures deserve templates\n"
        "2. Successful deliverables with clear structure are template candidates\n"
        "3. Templates balance structure (repeatability) with flexibility (customization)\n"
        "4. Every template needs 'when to use' and 'when NOT to use' guidance\n\n"
        "TEMPLATE QUALITY:\n"
        "- Captures the structure, not the specific content\n"
        "- Marks what to customize vs what to keep standard\n"
        "- Includes time-savings estimate\n"
        "- References the source deliverable\n\n"
        "Look for: standard structures, recurring sections, proven frameworks, "
        "successful patterns that could reduce startup time for similar future work."
    ),
)


@template_builder_agent.output_validator
async def validate_templates(
    ctx: RunContext[BrainDeps], output: TemplateBuilderResult
) -> TemplateBuilderResult:
    """Validate template quality."""
    for opp in output.opportunities:
        if not opp.when_to_use:
            raise ModelRetry(
                f"Template '{opp.name}' is missing 'when_to_use' guidance. "
                "Every template MUST specify when it should be applied."
            )
        if not opp.structure:
            raise ModelRetry(
                f"Template '{opp.name}' has no structure defined. "
                "Provide the reusable framework/structure."
            )
    output.templates_created = len(output.opportunities)
    return output


@template_builder_agent.tool
async def search_existing_patterns(ctx: RunContext[BrainDeps], topic: str = "") -> str:
    """Search for existing patterns that might already cover this template."""
    try:
        patterns = await ctx.deps.storage_service.get_patterns(topic=topic or None)
        if not patterns:
            return "No existing patterns found."
        from second_brain.agents.utils import format_pattern_registry
        return format_pattern_registry(patterns[:10])
    except Exception as e:
        from second_brain.agents.utils import tool_error
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
        from second_brain.agents.utils import tool_error
        return tool_error("search_examples", e)
