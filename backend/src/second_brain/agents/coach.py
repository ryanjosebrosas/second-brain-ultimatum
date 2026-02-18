"""Daily Accountability Coach — planning, coaching, and energy management.

Helps users plan their day, prioritize tasks, manage energy levels,
and provides coaching interventions when patterns are detected.
Uses CalendarService and TaskManagementService when available.
"""

import logging
from pydantic_ai import Agent, ModelRetry, RunContext
from pydantic_ai.tools import ToolDefinition
from second_brain.deps import BrainDeps
from second_brain.schemas import CoachSession

logger = logging.getLogger(__name__)

coach_agent = Agent(
    deps_type=BrainDeps,
    output_type=CoachSession,
    retries=3,
    instructions=(
        "You are a Daily Accountability Coach. Help users plan productive days "
        "through strategic planning and therapeutic coaching.\n\n"
        "SESSION TYPES:\n"
        "- morning: Create prioritized daily plan with time blocks\n"
        "- check_in: Assess progress, adjust plan, provide coaching\n"
        "- evening: Review accomplishments, extract learnings, prep tomorrow\n"
        "- intervention: When user is stuck, overwhelmed, or procrastinating\n\n"
        "COACHING APPROACH:\n"
        "1. Ask what user wants to work on (don't assume)\n"
        "2. Load brain context to assess alignment with goals\n"
        "3. Create focused, output-driven plan\n"
        "4. Suggest time blocks if calendar is available\n\n"
        "THERAPEUTIC DEPTH LEVELS:\n"
        "- Level 1 (Surface): Energy assessment, simple planning\n"
        "- Level 2 (Patterns): 'I notice you avoid X — what's going on?'\n"
        "- Level 3 (Core): Permission to be imperfect, reframing\n"
        "- Level 4 (Identity): Values alignment, future self perspective\n\n"
        "PRIORITY SCORING:\n"
        "- Revenue Impact (30%): Direct $/hour value\n"
        "- Strategic Alignment (25%): Quarterly goal advancement\n"
        "- Urgency (20%): Deadline proximity\n"
        "- Cognitive Load (15%): Energy required vs available\n"
        "- Learning (10%): Skill development compound effect\n\n"
        "Always provide a clear next_action — one specific thing to do RIGHT NOW."
    ),
)


@coach_agent.output_validator
async def validate_session(ctx: RunContext[BrainDeps], output: CoachSession) -> CoachSession:
    if not output.next_action:
        raise ModelRetry(
            "Every coaching session MUST end with a specific next_action. "
            "What should the user do RIGHT NOW? Be specific."
        )
    if output.session_type == "morning" and not output.priorities:
        raise ModelRetry(
            "Morning sessions MUST produce prioritized tasks. "
            "Create at least 1-3 priorities with rationale."
        )
    return output


@coach_agent.tool
async def load_goals_context(ctx: RunContext[BrainDeps]) -> str:
    """Load business goals and priorities from brain memory."""
    try:
        parts = []
        for cat in ["personal", "company", "values-beliefs"]:
            content = await ctx.deps.storage_service.get_memory_content(cat)
            if content:
                parts.append(f"{cat}:\n" + "\n".join(c.get("content", "")[:150] for c in content[:2]))
        return "\n\n".join(parts) if parts else "No goals context in brain."
    except Exception as e:
        from second_brain.agents.utils import tool_error
        return tool_error("load_goals_context", e)


@coach_agent.tool
async def search_past_sessions(ctx: RunContext[BrainDeps], query: str = "daily session") -> str:
    """Search for past coaching sessions and learnings."""
    try:
        import asyncio
        results = await asyncio.to_thread(ctx.deps.memory_service.search, query, limit=3)
        if not results:
            return "No past sessions found."
        from second_brain.agents.utils import format_memories
        return format_memories(results, limit=3)
    except Exception as e:
        from second_brain.agents.utils import tool_error
        return tool_error("search_past_sessions", e)


# Calendar tools — only available when CalendarService is configured

async def _calendar_available(ctx: RunContext[BrainDeps], tool_def: ToolDefinition) -> ToolDefinition | None:
    return tool_def if ctx.deps.calendar_service else None


@coach_agent.tool(prepare=_calendar_available)
async def check_calendar(ctx: RunContext[BrainDeps], date: str = "") -> str:
    """Check today's calendar for scheduling context."""
    try:
        events = await ctx.deps.calendar_service.get_events(date or "today")
        if not events:
            return "No calendar events found."
        lines = [f"- {e.get('summary', '?')} ({e.get('start', '?')} - {e.get('end', '?')})" for e in events]
        return "Today's calendar:\n" + "\n".join(lines)
    except Exception as e:
        from second_brain.agents.utils import tool_error
        return tool_error("check_calendar", e)


@coach_agent.tool(prepare=_calendar_available)
async def create_time_block(
    ctx: RunContext[BrainDeps], summary: str, start: str, end: str, description: str = ""
) -> str:
    """Create a calendar time block for focused work."""
    try:
        result = await ctx.deps.calendar_service.create_event(summary, start, end, description)
        return f"Time block created: {summary} ({start} - {end})"
    except Exception as e:
        from second_brain.agents.utils import tool_error
        return tool_error("create_time_block", e)


# Task tools — only available when TaskManagementService is configured

async def _tasks_available(ctx: RunContext[BrainDeps], tool_def: ToolDefinition) -> ToolDefinition | None:
    return tool_def if ctx.deps.task_service else None


@coach_agent.tool(prepare=_tasks_available)
async def get_task_backlog(ctx: RunContext[BrainDeps]) -> str:
    """Get current task backlog for planning."""
    try:
        tasks = await ctx.deps.task_service.get_tasks(limit=10)
        if not tasks:
            return "No tasks in backlog."
        lines = [f"- {t.get('title', '?')} (priority: {t.get('priority', '?')})" for t in tasks]
        return "Task backlog:\n" + "\n".join(lines)
    except Exception as e:
        from second_brain.agents.utils import tool_error
        return tool_error("get_task_backlog", e)
