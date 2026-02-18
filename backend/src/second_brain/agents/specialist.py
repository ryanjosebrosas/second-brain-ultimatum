"""Claude Code Specialist agent — verified technical answers.

Provides accurate answers about Claude Code, Pydantic AI, and
second brain system architecture with mandatory source attribution.
"""

import logging
from pydantic_ai import Agent, ModelRetry, RunContext
from second_brain.deps import BrainDeps
from second_brain.schemas import SpecialistAnswer

logger = logging.getLogger(__name__)

specialist_agent = Agent(
    deps_type=BrainDeps,
    output_type=SpecialistAnswer,
    retries=3,
    instructions=(
        "You are a Claude Code Specialist. Provide accurate, sourced answers "
        "about Claude Code architecture, Pydantic AI, and AI development.\n\n"
        "TRUTH & ATTRIBUTION PROTOCOL (MANDATORY):\n"
        "1. Always cite data source with file path or URL\n"
        "2. State confidence: VERIFIED (from source), LIKELY (inferred), UNCERTAIN\n"
        "3. Search before answering — read first, then respond\n"
        "4. Admit ignorance immediately — NEVER guess\n"
        "5. Distinguish knowledge base from official documentation\n\n"
        "NEVER:\n"
        "- Guess or hallucinate information\n"
        "- Claim certainty without sources\n"
        "- Provide info without attribution\n\n"
        "ALWAYS:\n"
        "- Read relevant files/docs before answering\n"
        "- Cite specific sources\n"
        "- State confidence level explicitly"
    ),
)


@specialist_agent.output_validator
async def validate_specialist(ctx: RunContext[BrainDeps], output: SpecialistAnswer) -> SpecialistAnswer:
    if output.confidence_level == "VERIFIED" and not output.sources:
        raise ModelRetry(
            "You marked confidence as VERIFIED but cited no sources. "
            "Either add source citations or downgrade to LIKELY/UNCERTAIN."
        )
    if len(output.answer) < 30:
        raise ModelRetry("Answer is too brief. Provide a complete, detailed response.")
    return output


@specialist_agent.tool
async def search_codebase_knowledge(ctx: RunContext[BrainDeps], query: str) -> str:
    """Search the brain's knowledge base for technical information."""
    try:
        knowledge = await ctx.deps.storage_service.get_knowledge()
        if not knowledge:
            return "No knowledge base entries found."
        # Simple keyword match
        query_lower = query.lower()
        matches = [k for k in knowledge if query_lower in k.get("content", "").lower()]
        if not matches:
            return f"No knowledge base matches for '{query}'."
        return "Knowledge base matches:\n" + "\n".join(
            f"- {m.get('title', '?')}: {m.get('content', '')[:200]}" for m in matches[:5]
        )
    except Exception as e:
        from second_brain.agents.utils import tool_error
        return tool_error("search_codebase_knowledge", e)


@specialist_agent.tool
async def search_patterns_for_answer(ctx: RunContext[BrainDeps], topic: str) -> str:
    """Search patterns registry for technical patterns."""
    try:
        patterns = await ctx.deps.storage_service.get_patterns(topic=topic)
        if not patterns:
            return f"No patterns found for topic '{topic}'."
        from second_brain.agents.utils import format_pattern_registry
        return format_pattern_registry(patterns[:5])
    except Exception as e:
        from second_brain.agents.utils import tool_error
        return tool_error("search_patterns_for_answer", e)
