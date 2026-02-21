"""PMO Advisor agent — priority coaching and task sequencing.

Applies multi-factor scoring (Urgency 35%, Impact 25%, Effort 15%,
Alignment 15%, Momentum 10%) to help users decide what to work on.
"""

import logging
from pydantic_ai import Agent, ModelRetry, RunContext
from second_brain.agents.utils import all_tools_failed, tool_error
from second_brain.deps import BrainDeps
from second_brain.schemas import PMOResult

logger = logging.getLogger(__name__)

pmo_agent = Agent(
    deps_type=BrainDeps,
    output_type=PMOResult,
    retries=3,
    instructions=(
        "You are a PMO (Project Management Office) Advisor. Help users "
        "prioritize tasks and make decisions about what to work on.\n\n"
        "SCORING ALGORITHM (weights from config):\n"
        "- Urgency (35%): Days until deadline x dependency factor\n"
        "- Impact (25%): Revenue potential + strategic advancement\n"
        "- Effort (15%): Inverted — low effort = higher score\n"
        "- Alignment (15%): Strategic goal alignment\n"
        "- Momentum (10%): Current progress and context\n\n"
        "TASK CATEGORIES:\n"
        "- Today's Focus: Score >= 75\n"
        "- This Week: Score >= 60\n"
        "- Backlog: Score < 60\n\n"
        "COACHING PRINCIPLES:\n"
        "1. Always explain trade-offs, not just rankings\n"
        "2. Validate user intuition — algorithm is guidance, not gospel\n"
        "3. Break down overwhelm — reduce scope when stuck\n"
        "4. Consider human factors: energy, context switching, meeting fatigue\n\n"
        "Provide a conversational coaching_message, not just data."
    ),
)


@pmo_agent.output_validator
async def validate_pmo(ctx: RunContext[BrainDeps], output: PMOResult) -> PMOResult:
    """Validate PMO output with deterministic error detection."""
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
                "error": "All PMO backends unavailable. Task prioritization skipped.",
            })
        return output

    # Normal validation (only if no error)
    if not output.scored_tasks:
        raise ModelRetry(
            "You must score at least one task. Load the user's tasks and "
            "apply the scoring algorithm to each. "
            "If tools failed, set the error field instead of retrying."
        )
    if not output.coaching_message:
        raise ModelRetry(
            "Provide a conversational coaching_message. Don't just list scores — "
            "explain trade-offs, suggest sequence, and address human factors. "
            "If tools failed, set the error field instead of retrying."
        )
    # Auto-categorize
    output = output.model_copy(update={
        "today_focus": [t.task_name for t in output.scored_tasks if t.total_score >= 75],
        "this_week": [t.task_name for t in output.scored_tasks if 60 <= t.total_score < 75],
        "quick_wins": [t.task_name for t in output.scored_tasks if t.effort <= 3],
    })
    return output


@pmo_agent.tool
async def load_strategic_context(ctx: RunContext[BrainDeps]) -> str:
    """Load strategic goals and priorities from brain."""
    try:
        parts = []
        projects = await ctx.deps.storage_service.list_projects(limit=5)
        if projects:
            parts.append("Active projects:\n" + "\n".join(
                f"- {p.get('name', '?')} ({p.get('lifecycle_stage', '?')})" for p in projects
            ))
        patterns = await ctx.deps.storage_service.get_patterns(confidence="HIGH")
        if patterns:
            parts.append(f"HIGH confidence patterns: {len(patterns)}")
        return "\n\n".join(parts) if parts else "No strategic context available."
    except Exception as e:
        return tool_error("load_strategic_context", e)


@pmo_agent.tool
async def get_scoring_weights(ctx: RunContext[BrainDeps]) -> str:
    """Get the configured priority scoring weights."""
    weights = ctx.deps.config.pmo_score_weights
    return "Scoring weights:\n" + "\n".join(f"- {k}: {v*100:.0f}%" for k, v in weights.items())
