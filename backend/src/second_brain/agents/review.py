"""ReviewAgent — 6-dimension quality assessment."""

import asyncio
import logging
from typing import TYPE_CHECKING

from pydantic_ai import Agent, ModelRetry, RunContext

if TYPE_CHECKING:
    from pydantic_ai.models import Model

from second_brain.agents.utils import (
    all_tools_failed,
    format_relations,
    load_voice_context,
    search_with_graph_fallback,
    tool_error,
)
from second_brain.deps import BrainDeps
from second_brain.schemas import (
    DimensionScore, ReviewResult, REVIEW_DIMENSIONS,
    DEFAULT_REVIEW_DIMENSIONS, ReviewDimensionConfig,
)

logger = logging.getLogger(__name__)

# NOTE: When using ClaudeSDKModel (subscription auth), Pydantic AI tools
# are NOT called. Instead, the SDK process calls service MCP tools directly.
# The agent instructions and output schema validation still apply.
review_agent = Agent(
    deps_type=BrainDeps,
    output_type=DimensionScore,
    retries=3,
    instructions=(
        "You are a focused content reviewer evaluating ONE specific dimension of content quality. "
        "You will be told which dimension to evaluate and its specific criteria. "
        "Score 1-10: 9-10 excellent, 7-8 good, 5-6 acceptable, 3-4 needs work, 1-2 major issues. "
        "Classify findings as strengths (well done), suggestions (nice-to-have improvements), "
        "or issues (must-fix problems). "
        "Be specific — cite exact phrases or sections in your findings. "
        "Use brain context (voice guide, patterns, examples) when available to ground your evaluation. "
        "Set the dimension field to the dimension name you are reviewing. "
        "Set the status field: 'pass' if score >= 7, 'warning' if score 5-6, 'issue' if score <= 4."
    ),
)


@review_agent.output_validator
async def validate_review(ctx: RunContext[BrainDeps], output: DimensionScore) -> DimensionScore:
    """Validate review output with deterministic error detection.

    Uses deterministic error detection: checks if ALL tool outputs
    contain TOOL_ERROR_PREFIX, rather than relying on LLM setting the error field.
    This prevents death spirals when all backends are down.
    """
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

    # If all tools failed, set error and return (prevents retry)
    if tool_outputs and all_tools_failed(tool_outputs):
        if not output.error:
            output = output.model_copy(update={
                "error": "All review backends unavailable. Review skipped.",
            })
        return output

    # Normal validation (only if no error)
    if output.score < 1 or output.score > 10:
        raise ModelRetry(
            f"Score {output.score} is out of range. Use 1-10 scale. "
            "If tools failed, set the error field instead of retrying."
        )

    # Status must match score
    expected_status = "pass" if output.score >= 7 else ("warning" if output.score >= 5 else "issue")
    if output.status != expected_status:
        raise ModelRetry(
            f"Status '{output.status}' doesn't match score {output.score}. "
            f"Expected status '{expected_status}' (pass=7+, warning=5-6, issue=1-4). "
            "If tools failed, set the error field instead of retrying."
        )

    if not output.strengths and not output.issues:
        raise ModelRetry(
            "You must identify at least one strength or issue. "
            "If tools failed, set the error field instead of retrying."
        )
    return output


@review_agent.tool
async def load_voice_reference(ctx: RunContext[BrainDeps], voice_user_id: str = "") -> str:
    """Load the user's voice and tone guide for evaluating brand voice consistency.
    Pass voice_user_id to load a specific user's voice profile."""
    try:
        uid = voice_user_id if voice_user_id else None
        return await load_voice_context(ctx.deps, voice_user_id=uid)
    except Exception as e:
        return tool_error("load_voice_reference", e)


@review_agent.tool
async def load_positioning_context(ctx: RunContext[BrainDeps]) -> str:
    """Load company, personal, and customer positioning context for evaluating market alignment."""
    try:
        all_sections = []
        for category, label in [("company", "Company"), ("personal", "Personal"), ("customers", "Customers")]:
            items = await ctx.deps.storage_service.get_memory_content(category)
            if items:
                lines = [f"### {label}"]
                for item in items:
                    title = item.get("title", "Untitled")
                    text = item.get("content", "")[:ctx.deps.config.content_preview_limit]
                    lines.append(f"#### {title}\n{text}")
                all_sections.append("\n".join(lines))
        if not all_sections:
            return "No positioning context found."
        return "## Positioning Context\n" + "\n\n".join(all_sections)
    except Exception as e:
        return tool_error("load_positioning_context", e)


@review_agent.tool
async def load_example_benchmarks(ctx: RunContext[BrainDeps], content_type: str | None = None) -> str:
    """Load content examples as quality benchmarks for comparison."""
    try:
        examples = await ctx.deps.storage_service.get_examples(content_type=content_type)
        if not examples:
            return "No benchmark examples found."
        limit = ctx.deps.config.experience_limit
        sections = []
        for ex in examples[:limit]:
            title = ex.get("title", "Untitled")
            text = ex.get("content", "")[:ctx.deps.config.content_preview_limit]
            sections.append(f"### {title}\n{text}")
        return "## Example Benchmarks\n" + "\n\n".join(sections)
    except Exception as e:
        return tool_error("load_example_benchmarks", e)


@review_agent.tool
async def load_graph_context(
    ctx: RunContext[BrainDeps], content_summary: str
) -> str:
    """Load entity relationships from graph memory to ground review in brain context.
    Searches both Mem0 graph and Graphiti for related entities."""
    try:
        relations = []

        # Mem0 graph relations
        try:
            result = await ctx.deps.memory_service.search(
                content_summary, limit=5, enable_graph=True
            )
            relations.extend(result.relations)
        except Exception:
            logger.debug("Mem0 graph search failed in review_agent")

        # Graphiti relations via shared helper
        relations = await search_with_graph_fallback(ctx.deps, content_summary, relations)

        if not relations:
            return "No graph relationships found for this content."

        formatted = ["## Graph Context for Review"]
        rel_text = format_relations(relations)
        if rel_text:
            formatted.append(rel_text)
        return "\n".join(formatted)
    except Exception as e:
        return tool_error("load_graph_context", e)


async def run_full_review(
    content: str,
    deps: BrainDeps,
    model: "Model | None",
    content_type: str | None = None,
) -> ReviewResult:
    """Run dimension reviews in parallel and aggregate into a ReviewResult.

    If the content type has custom review_dimensions, only enabled dimensions
    are scored and weights are applied to the overall score.
    """
    # Determine which dimensions to use and their weights
    dim_configs: list[ReviewDimensionConfig] = list(DEFAULT_REVIEW_DIMENSIONS)

    if content_type:
        registry = deps.get_content_type_registry()
        type_config = await registry.get(content_type)
        if type_config and type_config.review_dimensions:
            dim_configs = [d for d in type_config.review_dimensions if d.enabled]

    # Build prompts only for enabled dimensions
    dim_details = {d["name"]: d for d in REVIEW_DIMENSIONS}
    prompts = []
    active_configs: list[ReviewDimensionConfig] = []
    for dc in dim_configs:
        detail = dim_details.get(dc.name)
        if not detail:
            continue
        prompt = (
            f"Review the following content for the **{detail['name']}** dimension.\n"
            f"Focus: {detail['focus']}\n"
            f"Checks: {detail['checks']}\n\n"
            f"Content to review:\n{content}"
        )
        if content_type:
            prompt += f"\nContent type: {content_type}"
        prompts.append(prompt)
        active_configs.append(dc)

    # Timeout-protected parallel reviews
    from pydantic_ai.usage import UsageLimits
    limits = UsageLimits(request_limit=deps.config.pipeline_request_limit)
    timeout_seconds = (
        deps.config.api_timeout_seconds * deps.config.mcp_review_timeout_multiplier
        if deps else 60
    )
    try:
        async with asyncio.timeout(timeout_seconds):
            results = await asyncio.gather(
                *[
                    review_agent.run(prompt, deps=deps, model=model, usage_limits=limits)
                    for prompt in prompts
                ],
                return_exceptions=True,
            )
    except TimeoutError:
        logger.warning("run_full_review timed out after %ds", timeout_seconds)
        results = []

    scores: list[DimensionScore] = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.warning("Dimension %s failed: %s", active_configs[i].name, result)
            scores.append(DimensionScore(
                dimension=active_configs[i].name,
                score=0,
                status="issue",
                issues=[f"Review failed: {result}"],
            ))
        else:
            scores.append(result.output)

    # Compute weighted overall score
    valid_scores = [
        (s.score, active_configs[i].weight)
        for i, s in enumerate(scores) if s.score > 0
    ]
    if valid_scores:
        weighted_sum = sum(score * weight for score, weight in valid_scores)
        weight_total = sum(weight for _, weight in valid_scores)
        overall_score = round(weighted_sum / weight_total, 1) if weight_total > 0 else 0.0
    else:
        overall_score = 0.0

    low_count = sum(1 for s in scores if s.score < 5)
    if overall_score >= 8 and all(s.score >= 6 for s in scores):
        verdict = "READY TO SEND"
    elif overall_score < 5 or low_count >= 3:
        verdict = "MAJOR REWORK"
    else:
        verdict = "NEEDS REVISION"

    all_strengths = [st for s in scores for st in s.strengths]
    top_strengths = all_strengths[:3]

    critical_issues = [iss for s in scores for iss in s.issues]

    next_steps = []
    dims_with_issues = [s.dimension for s in scores if s.issues]
    dims_with_suggestions = [s.dimension for s in scores if s.suggestions]
    if dims_with_issues:
        next_steps.append(f"Address issues in: {', '.join(dims_with_issues)}")
    if dims_with_suggestions:
        next_steps.append(f"Consider improvements in: {', '.join(dims_with_suggestions)}")

    if verdict == "READY TO SEND":
        summary = f"Content scores {overall_score}/10 overall and is ready to publish. All dimensions meet quality thresholds."
    elif verdict == "MAJOR REWORK":
        summary = f"Content scores {overall_score}/10 overall and needs significant revision. {len(critical_issues)} critical issues found across {len(dims_with_issues)} dimensions."
    else:
        summary = f"Content scores {overall_score}/10 overall and needs targeted revisions. Review the issues below before publishing."

    # Record review history (non-blocking)
    try:
        await deps.storage_service.add_review_history({
            "content_type": content_type or "",
            "overall_score": overall_score,
            "verdict": verdict,
            "dimension_scores": [
                {"dimension": s.dimension, "score": s.score, "status": s.status}
                for s in scores
            ],
            "dimension_details": {s.dimension: s.score for s in scores if s.score is not None},
            "top_strengths": top_strengths,
            "critical_issues": critical_issues,
            "content_preview": content[:200] if content else "",
        })
    except Exception:
        logger.debug("Failed to record review history")

    # Track pattern failures for confidence downgrade
    try:
        patterns = await deps.storage_service.get_patterns()
        tasks = []
        if overall_score < deps.config.confidence_downgrade_threshold:
            for p in patterns:
                applicable_types = p.get("applicable_content_types") or []
                if not applicable_types or content_type in applicable_types:
                    if p.get("confidence") != "LOW":
                        tasks.append(deps.storage_service.update_pattern_failures(p["id"]))
        else:
            for p in patterns:
                if p.get("consecutive_failures", 0) > 0:
                    applicable_types = p.get("applicable_content_types") or []
                    if not applicable_types or content_type in applicable_types:
                        tasks.append(deps.storage_service.update_pattern_failures(p["id"], reset=True))
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    except Exception:
        logger.debug("Pattern failure tracking failed (non-critical)")

    return ReviewResult(
        scores=scores,
        overall_score=overall_score,
        verdict=verdict,
        summary=summary,
        top_strengths=top_strengths,
        critical_issues=critical_issues,
        next_steps=next_steps,
    )
