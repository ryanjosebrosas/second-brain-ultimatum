"""Impact Analyzer agent — quantifies business value and ROI."""

import logging
from pydantic_ai import Agent, ModelRetry, RunContext
from second_brain.deps import BrainDeps
from second_brain.schemas import ImpactResult

logger = logging.getLogger(__name__)

impact_agent = Agent(
    deps_type=BrainDeps,
    output_type=ImpactResult,
    retries=3,
    instructions=(
        "You are an Impact Analyzer. Transform recommendations into "
        "quantified business cases with ROI.\n\n"
        "ANALYSIS FRAMEWORK:\n"
        "1. Quantify the business problem (cost of status quo)\n"
        "2. Calculate benefits (cost savings, revenue growth, efficiency)\n"
        "3. Compute ROI metrics (payback period, first-year ROI)\n"
        "4. Provide risk scenarios (conservative/base/optimistic at 75%/100%/125%)\n"
        "5. Calculate opportunity cost of NOT taking action\n\n"
        "COMMON PATTERNS TO FIX:\n"
        "- Activity metrics instead of business outcomes\n"
        "- Missing ROI calculation\n"
        "- Qualitative benefits without financial quantification\n"
        "- No opportunity cost analysis\n\n"
        "Every recommendation should answer: 'How much is this worth in dollars?'"
    ),
)


@impact_agent.output_validator
async def validate_impact(ctx: RunContext[BrainDeps], output: ImpactResult) -> ImpactResult:
    if not output.executive_summary:
        raise ModelRetry("Provide an executive_summary — a 1-2 paragraph business case.")
    if not output.metrics:
        raise ModelRetry("Quantify at least one metric. Every analysis needs numbers.")
    return output


@impact_agent.tool
async def load_business_context(ctx: RunContext[BrainDeps]) -> str:
    """Load business context for impact quantification."""
    try:
        parts = []
        for cat in ["company", "knowledge-repo"]:
            content = await ctx.deps.storage_service.get_memory_content(cat)
            if content:
                parts.append(f"{cat}:\n" + "\n".join(c.get("content", "")[:200] for c in content[:2]))
        return "\n\n".join(parts) if parts else "No business context available."
    except Exception as e:
        from second_brain.agents.utils import tool_error
        return tool_error("load_business_context", e)
