"""Feedback Synthesizer agent — consolidates review findings into actionable themes.

Takes 30-50 individual review findings and produces 6-8 themed improvement
actions with priority, effort estimates, dependencies, and ownership.
"""

import logging
from pydantic_ai import Agent, ModelRetry, RunContext
from second_brain.agents.utils import all_tools_failed, tool_error
from second_brain.deps import BrainDeps
from second_brain.schemas import SynthesizerResult

logger = logging.getLogger(__name__)

synthesizer_agent = Agent(
    deps_type=BrainDeps,
    output_type=SynthesizerResult,
    retries=3,
    instructions=(
        "You are a Feedback Synthesizer. You transform overwhelming review "
        "feedback (30-50 findings) into 6-8 actionable improvement themes.\n\n"
        "CONSOLIDATION RULES:\n"
        "1. Group related findings into themes (don't list individually)\n"
        "2. Merge duplicates across different review dimensions\n"
        "3. Map dependencies — which fixes must precede others\n"
        "4. Estimate effort realistically (minutes per theme)\n"
        "5. Identify parallel work opportunities\n\n"
        "PRIORITY LEVELS:\n"
        "- CRITICAL: Blocks delivery, must fix before any presentation\n"
        "- HIGH: Significantly improves quality, fix before delivery\n"
        "- MEDIUM: Nice to have, fix if time allows\n"
        "- LOW: Defer to next revision or template update\n\n"
        "OUTPUT RULES:\n"
        "- Produce 4-8 themes, not 20+ individual items\n"
        "- Each theme consolidates 2-8 related findings\n"
        "- Every theme has specific action steps, not vague guidance\n"
        "- Estimate effort in minutes (15-180 range per theme)\n"
        "- List dependencies between themes\n"
        "- Total implementation hours should be realistic (2-8 hours typical)"
    ),
)


@synthesizer_agent.output_validator
async def validate_synthesis(
    ctx: RunContext[BrainDeps], output: SynthesizerResult
) -> SynthesizerResult:
    """Validate synthesis output with deterministic error detection."""
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
                "error": "All synthesis backends unavailable. Synthesis skipped.",
            })
        return output

    # Normal validation (only if no error)
    if len(output.themes) < 2:
        raise ModelRetry(
            "Too few themes. Review findings should consolidate into 4-8 themes. "
            "Group related findings together rather than having one mega-theme. "
            "If tools failed, set the error field instead of retrying."
        )
    if len(output.themes) > 12:
        raise ModelRetry(
            f"Too many themes ({len(output.themes)}). Consolidate further — "
            "the goal is 6-8 actionable themes, not a long list. "
            "If tools failed, set the error field instead of retrying."
        )
    for theme in output.themes:
        if not theme.action:
            raise ModelRetry(
                f"Theme '{theme.title}' has no action steps. "
                "Every theme MUST have specific, concrete implementation steps. "
                "If tools failed, set the error field instead of retrying."
            )
    # Auto-compute totals
    output = output.model_copy(update={
        "total_themes_output": len(output.themes),
        "implementation_hours": sum(t.effort_minutes for t in output.themes) / 60.0,
    })
    return output


@synthesizer_agent.tool
async def load_past_reviews(ctx: RunContext[BrainDeps], content_type: str = "") -> str:
    """Load past review history for context on recurring issues."""
    try:
        reviews = await ctx.deps.storage_service.get_review_history(
            content_type=content_type or None, limit=5
        )
        if not reviews:
            return "No past review history available."
        lines = []
        for r in reviews:
            lines.append(
                f"- Score {r.get('overall_score', '?')}: "
                f"{', '.join(r.get('critical_issues', [])[:2])}"
            )
        return "Past reviews (recurring issues context):\n" + "\n".join(lines)
    except Exception as e:
        return tool_error("load_past_reviews", e)
