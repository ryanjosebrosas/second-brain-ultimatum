"""Clarity Maximizer agent — content readability and accessibility analysis.

Identifies jargon, complexity barriers, and comprehension issues.
Produces severity-ranked findings with specific improvement suggestions.
"""

import logging
from pydantic_ai import Agent, ModelRetry, RunContext
from second_brain.agents.utils import load_voice_context, tool_error
from second_brain.deps import BrainDeps
from second_brain.schemas import ClarityResult

logger = logging.getLogger(__name__)

clarity_agent = Agent(
    deps_type=BrainDeps,
    output_type=ClarityResult,
    retries=3,
    instructions=(
        "You are a Clarity Maximizer. Your job is to identify and eliminate "
        "comprehension barriers in content. Analyze the provided text and find:\n\n"
        "FINDING CATEGORIES:\n"
        "- 'jargon': Industry terms needing explanation or elimination\n"
        "- 'complexity': Overly technical concepts for the audience\n"
        "- 'density': Dense paragraphs overwhelming readers\n"
        "- 'abstract': Abstract concepts without concrete examples\n\n"
        "SEVERITY LEVELS:\n"
        "- CRITICAL: Incomprehensible sections, undefined critical terms\n"
        "- HIGH: Excessive jargon, technical concepts for business audience\n"
        "- MEDIUM: Better example opportunities, inconsistent language\n"
        "- LOW: Alternative phrasing, minor simplifications\n\n"
        "QUALITY CRITERIA:\n"
        "- Can a 12-year-old understand the core concept?\n"
        "- Would an executive grasp the key message in 30 seconds?\n"
        "- Are technical terms defined or eliminated?\n"
        "- Do examples make abstract concepts concrete?\n\n"
        "For each finding, provide a SPECIFIC suggestion — not 'improve clarity' "
        "but 'Replace \"synergistic cross-functional alignment\" with "
        "\"teams working together effectively\"'."
    ),
)


@clarity_agent.output_validator
async def validate_clarity(ctx: RunContext[BrainDeps], output: ClarityResult) -> ClarityResult:
    """Validate clarity analysis quality."""
    if not output.findings and output.overall_readability != "HIGH":
        raise ModelRetry(
            "You rated readability as non-HIGH but found no specific issues. "
            "Either upgrade the readability rating or identify specific findings."
        )
    for finding in output.findings:
        if not finding.suggestion:
            raise ModelRetry(
                f"Finding at '{finding.location}' has no suggestion. "
                "Every finding MUST include a specific improvement suggestion."
            )
    # Auto-compute critical count
    output.critical_count = sum(1 for f in output.findings if f.severity == "CRITICAL")
    return output


@clarity_agent.tool
async def load_audience_context(ctx: RunContext[BrainDeps]) -> str:
    """Load audience information to calibrate clarity assessment."""
    try:
        audience = await ctx.deps.storage_service.get_memory_content("audience")
        if not audience:
            return "No audience information available. Assess for general business audience."
        return "Audience context:\n" + "\n".join(
            a.get("content", "")[:200] for a in audience[:3]
        )
    except Exception as e:
        return tool_error("load_audience_context", e)


@clarity_agent.tool
async def load_voice_reference(ctx: RunContext[BrainDeps]) -> str:
    """Load voice/style guide for language level calibration."""
    try:
        return await load_voice_context(ctx.deps, preview_limit=200)
    except Exception as e:
        return tool_error("load_voice_reference", e)
