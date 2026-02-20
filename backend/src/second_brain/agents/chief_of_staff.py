"""Chief of Staff agent — request routing and orchestration.

READ-ONLY orchestrator that analyzes user requests, loads brain context,
and routes to the optimal specialist agent or pipeline. Never executes
tasks directly — only coordinates.
"""

import logging

from pydantic_ai import Agent, ModelRetry, RunContext

from second_brain.agents.utils import classify_query_complexity, format_memories, tool_error
from second_brain.deps import BrainDeps
from second_brain.schemas import RoutingDecision

logger = logging.getLogger(__name__)

chief_of_staff = Agent(
    deps_type=BrainDeps,
    output_type=RoutingDecision,
    retries=3,
    instructions=(
        "You are the Chief of Staff for an AI Second Brain system. "
        "Your role is to analyze user requests and route them to the optimal "
        "specialist agent. You NEVER execute tasks directly — you coordinate.\n\n"
        "ROUTING RULES:\n"
        "- Greetings, small talk, pleasantries (hello, thanks, bye, how are you) → 'conversational'\n"
        "- Memory search/recall → 'recall'\n"
        "- Questions requiring brain context → 'ask'\n"
        "- Pattern extraction from work sessions → 'learn'\n"
        "- Content creation (posts, emails, copy) → 'create'\n"
        "- Content quality review → 'review'\n"
        "- Long-form essays/articles → 'create' (use content_type='essay')\n"
        "- Content clarity/readability check → 'clarity'\n"
        "- Consolidating multiple review findings → 'synthesizer'\n"
        "- Identifying reusable templates → 'template_builder'\n"
        "- Daily planning/coaching → 'coach'\n"
        "- Task prioritization → 'pmo'\n"
        "- Email operations → 'email'\n"
        "- Claude Code questions → 'specialist'\n"
        "- Multi-step workflows → 'pipeline' with pipeline_steps filled\n\n"
        "COMPLEXITY RULES:\n"
        "- Use classify_complexity tool to assess query complexity before routing.\n"
        "- Greetings/small talk (no information need) → 'conversational' (instant reply, no tools)\n"
        "- Simple queries (fact lookups) → 'recall' (fast path)\n"
        "- Medium queries (topic recall) → 'recall' (standard path)\n"
        "- Complex queries (synthesis, comparison, multi-source) → 'recall_deep' (parallel sub-agents)\n"
        "- Set query_complexity in your routing decision to match.\n\n"
        "PIPELINE MODE: When a request requires multiple agents in sequence, "
        "set target_agent='pipeline' and fill pipeline_steps with the ordered "
        "list of agents. Common pipelines:\n"
        "- Content creation: ['recall', 'create', 'review']\n"
        "- Learn from content: ['review', 'learn']\n"
        "- Research + answer: ['recall', 'ask']\n"
        "- Full content pipeline: ['recall', 'create', 'review', 'learn']\n\n"
        "Always explain your routing reasoning. Load brain context first to "
        "make informed routing decisions."
    ),
)


@chief_of_staff.output_validator
async def validate_routing(
    ctx: RunContext[BrainDeps], output: RoutingDecision
) -> RoutingDecision:
    """Validate routing decision."""
    if output.target_agent == "pipeline" and not output.pipeline_steps:
        raise ModelRetry(
            "You selected 'pipeline' mode but didn't specify pipeline_steps. "
            "List the ordered sequence of agents to chain."
        )
    if not output.reasoning:
        raise ModelRetry(
            "You must provide reasoning for your routing decision. "
            "Explain WHY this agent is the best choice for the user's request."
        )
    return output


@chief_of_staff.tool
async def load_brain_overview(ctx: RunContext[BrainDeps]) -> str:
    """Load a high-level overview of what the brain contains."""
    try:
        parts = []

        # Pattern count and topics
        patterns = await ctx.deps.storage_service.get_patterns()
        if patterns:
            topics = set(p.get("topic", "unknown") for p in patterns)
            parts.append(f"Patterns: {len(patterns)} across topics: {', '.join(sorted(topics))}")

        # Experience count
        experiences = await ctx.deps.storage_service.get_experiences(limit=1)
        if experiences:
            parts.append("Experiences: available")

        # Content types
        try:
            registry = ctx.deps.get_content_type_registry()
            types = await registry.get_all()
            if types:
                parts.append(f"Content types: {', '.join(types.keys())}")
        except Exception:
            pass

        # Available services
        services = []
        if ctx.deps.email_service:
            services.append("email")
        if ctx.deps.calendar_service:
            services.append("calendar")
        if ctx.deps.analytics_service:
            services.append("analytics")
        if ctx.deps.graphiti_service:
            services.append("graph memory")
        if services:
            parts.append(f"Active integrations: {', '.join(services)}")

        return "\n".join(parts) if parts else "Brain is empty — suggest using 'learn' agent."
    except Exception as e:
        return tool_error("load_brain_overview", e)


@chief_of_staff.tool
async def search_brain_context(ctx: RunContext[BrainDeps], query: str) -> str:
    """Search brain memory for context relevant to routing the request."""
    try:
        results = await ctx.deps.memory_service.search(query, limit=5)
        if not results or not results.memories:
            return "No relevant context found in brain memory."
        return format_memories(results.memories, limit=5)
    except Exception as e:
        return tool_error("search_brain_context", e)


@chief_of_staff.tool
async def check_active_projects(ctx: RunContext[BrainDeps]) -> str:
    """Check for active projects that might inform routing."""
    try:
        projects = await ctx.deps.storage_service.list_projects(
            lifecycle_stage="executing", limit=5
        )
        if not projects:
            return "No active projects."
        lines = []
        for p in projects:
            lines.append(f"- {p.get('name', 'unnamed')} ({p.get('lifecycle_stage', '?')})")
        return "Active projects:\n" + "\n".join(lines)
    except Exception as e:
        return tool_error("check_active_projects", e)


@chief_of_staff.tool
async def classify_complexity(
    ctx: RunContext[BrainDeps], query: str
) -> str:
    """Classify query complexity to determine retrieval depth.

    Returns 'simple', 'medium', or 'complex' with explanation."""
    try:
        complexity = classify_query_complexity(
            query,
            word_threshold=ctx.deps.config.complex_query_word_threshold,
        )
        return f"Complexity: {complexity}"
    except Exception as e:
        return tool_error("classify_complexity", e)
