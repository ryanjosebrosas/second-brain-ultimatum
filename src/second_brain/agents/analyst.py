"""Data Analyst agent — business intelligence and analytics."""

import logging
from pydantic_ai import Agent, ModelRetry, RunContext
from pydantic_ai.tools import ToolDefinition
from second_brain.deps import BrainDeps
from second_brain.schemas import AnalysisResult

logger = logging.getLogger(__name__)

analyst_agent = Agent(
    deps_type=BrainDeps,
    output_type=AnalysisResult,
    retries=3,
    instructions=(
        "You are a Data Analyst. Provide actionable business insights "
        "from data analysis.\n\n"
        "ANALYSIS METHODOLOGY:\n"
        "1. Understand the business question\n"
        "2. Identify relevant data sources\n"
        "3. Execute analysis (queries, calculations)\n"
        "4. Interpret results with business context\n"
        "5. Deliver actionable recommendations\n\n"
        "COMMUNICATION:\n"
        "- Lead with findings, not methodology\n"
        "- Plain language with supporting metrics\n"
        "- Be transparent about data limitations\n"
        "- Always provide executive_summary for business audience\n\n"
        "When analytics service is unavailable, provide analysis methodology "
        "and suggest the queries that should be run."
    ),
)


@analyst_agent.output_validator
async def validate_analysis(ctx: RunContext[BrainDeps], output: AnalysisResult) -> AnalysisResult:
    if not output.executive_summary:
        raise ModelRetry("Provide an executive_summary for business stakeholders.")
    if not output.findings and not output.recommendations:
        raise ModelRetry("Analysis must produce findings or recommendations.")
    return output


@analyst_agent.tool
async def load_business_metrics_context(ctx: RunContext[BrainDeps]) -> str:
    """Load business metrics context from brain."""
    try:
        knowledge = await ctx.deps.storage_service.get_knowledge(category="metrics")
        if not knowledge:
            knowledge = await ctx.deps.storage_service.get_knowledge()
        if not knowledge:
            return "No metrics context in brain."
        return "Business metrics context:\n" + "\n".join(
            k.get("content", "")[:200] for k in knowledge[:3]
        )
    except Exception as e:
        from second_brain.agents.utils import tool_error
        return tool_error("load_business_metrics_context", e)


async def _analytics_available(ctx: RunContext[BrainDeps], tool_def: ToolDefinition) -> ToolDefinition | None:
    return tool_def if ctx.deps.analytics_service else None


@analyst_agent.tool(prepare=_analytics_available)
async def run_query(ctx: RunContext[BrainDeps], sql: str) -> str:
    """Execute an analytics SQL query."""
    try:
        results = await ctx.deps.analytics_service.query(sql)
        if not results:
            return "Query returned no results."
        # Format as table-like string
        if results:
            headers = list(results[0].keys())
            lines = [" | ".join(headers)]
            for row in results[:20]:
                lines.append(" | ".join(str(row.get(h, "")) for h in headers))
            return "\n".join(lines)
        return "Empty result set."
    except Exception as e:
        from second_brain.agents.utils import tool_error
        return tool_error("run_query", e)


@analyst_agent.tool(prepare=_analytics_available)
async def get_revenue_metrics(ctx: RunContext[BrainDeps], period_days: int = 30) -> str:
    """Get revenue metrics for a period."""
    try:
        metrics = await ctx.deps.analytics_service.get_revenue(period_days)
        return "Revenue metrics:\n" + "\n".join(f"- {k}: {v}" for k, v in metrics.items())
    except Exception as e:
        from second_brain.agents.utils import tool_error
        return tool_error("get_revenue_metrics", e)
