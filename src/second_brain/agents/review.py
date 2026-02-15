"""ReviewAgent — 6-dimension quality assessment."""

import asyncio
import logging

from pydantic_ai import Agent, RunContext

from second_brain.deps import BrainDeps
from second_brain.schemas import (
    DimensionScore, ReviewResult, REVIEW_DIMENSIONS,
    DEFAULT_REVIEW_DIMENSIONS, ReviewDimensionConfig,
)

logger = logging.getLogger(__name__)

review_agent = Agent(
    deps_type=BrainDeps,
    output_type=DimensionScore,
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


@review_agent.tool
async def load_voice_reference(ctx: RunContext[BrainDeps]) -> str:
    """Load the user's voice and tone guide for evaluating brand voice consistency."""
    try:
        content = await ctx.deps.storage_service.get_memory_content("style-voice")
        if not content:
            return "No voice guide found."
        sections = []
        for item in content:
            title = item.get("title", "Untitled")
            text = item.get("content", "")[:ctx.deps.config.content_preview_limit]
            sections.append(f"### {title}\n{text}")
        return "## Voice & Tone Reference\n" + "\n\n".join(sections)
    except Exception as e:
        logger.warning("load_voice_reference failed: %s", type(e).__name__)
        return f"Voice reference unavailable: {type(e).__name__}"


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
        logger.warning("load_positioning_context failed: %s", type(e).__name__)
        return f"Positioning context unavailable: {type(e).__name__}"


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
        logger.warning("load_example_benchmarks failed: %s", type(e).__name__)
        return f"Example benchmarks unavailable: {type(e).__name__}"


async def run_full_review(
    content: str,
    deps: BrainDeps,
    model,
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

    results = await asyncio.gather(
        *[review_agent.run(prompt, deps=deps, model=model) for prompt in prompts],
        return_exceptions=True,
    )

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
            "top_strengths": top_strengths,
            "critical_issues": critical_issues,
            "content_preview": content[:200] if content else "",
        })
    except Exception:
        logger.debug("Failed to record review history")

    return ReviewResult(
        scores=scores,
        overall_score=overall_score,
        verdict=verdict,
        summary=summary,
        top_strengths=top_strengths,
        critical_issues=critical_issues,
        next_steps=next_steps,
    )
