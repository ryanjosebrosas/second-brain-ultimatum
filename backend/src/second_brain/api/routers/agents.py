"""Agent endpoints — 13 Pydantic AI agents exposed as POST endpoints."""

import asyncio
import logging
from collections.abc import Callable, Coroutine
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException

if TYPE_CHECKING:
    from pydantic_ai.models import Model

from second_brain.deps import BrainDeps
from second_brain.api.deps import get_deps, get_model
from second_brain.api.schemas import (
    AskRequest,
    ChatRequest,
    ClarityRequest,
    CoachingRequest,
    CreateContentRequest,
    EmailRequest,
    LearnRequest,
    PipelineRequest,
    PrioritizeRequest,
    RecallRequest,
    ReviewContentRequest,
    SpecialistRequest,
    SynthesizeRequest,
    TemplateRequest,
)
from second_brain.agents.recall import recall_agent
from second_brain.agents.ask import ask_agent
from second_brain.agents.learn import learn_agent
from second_brain.agents.create import create_agent
from second_brain.agents.review import run_full_review

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Agents"])


async def _run_agent(
    name: str,
    coro: Callable[[], Coroutine[Any, Any, Any]],
    timeout: float,
) -> Any:
    """Run an agent coroutine with timeout and error handling.

    Returns the result on success. Raises HTTPException on timeout or failure.
    """
    try:
        async with asyncio.timeout(timeout):
            return await coro()
    except TimeoutError:
        raise HTTPException(504, detail=f"{name} timed out after {timeout}s")
    except HTTPException:
        raise
    except Exception as e:
        error_name = type(e).__name__
        if error_name == "UnexpectedModelBehavior":
            logger.warning("%s agent exhausted retries: %s", name, e)
            raise HTTPException(
                503,
                detail={
                    "error": f"{name} service degraded",
                    "message": "Backend memory services may be temporarily unavailable.",
                    "suggestion": "Try again in a few minutes, or use quick_recall for direct search.",
                    "retry_after": 30,
                },
            )
        logger.error("%s agent failed: %s", name, e, exc_info=True)
        raise HTTPException(502, detail=f"{name} failed: {error_name}: {e}")


@router.post("/recall")
async def recall(body: RecallRequest, deps: BrainDeps = Depends(get_deps), model: "Model" = Depends(get_model)) -> dict[str, Any]:
    """Search memory for relevant context, patterns, and past experiences."""
    result = await _run_agent(
        "Recall",
        lambda: recall_agent.run(f"Search memory for: {body.query}", deps=deps, model=model),
        deps.config.api_timeout_seconds,
    )
    return result.output.model_dump()


@router.post("/ask")
async def ask(body: AskRequest, deps: BrainDeps = Depends(get_deps), model: "Model | None" = Depends(get_model)) -> dict[str, Any]:
    """Ask the Second Brain a question."""
    # Short-circuit for greetings and small talk
    from second_brain.agents.utils import is_conversational
    if is_conversational(body.question):
        from second_brain.schemas import AskResult
        return AskResult(
            answer=(
                "Hey! I'm your Second Brain assistant. "
                "Ask me anything — I can search your memory, help with content, "
                "review your work, or answer questions using your accumulated knowledge."
            ),
            is_conversational=True,
            confidence="HIGH",
        ).model_dump()
    result = await _run_agent(
        "Ask",
        lambda: ask_agent.run(body.question, deps=deps, model=model),
        deps.config.api_timeout_seconds,
    )
    return result.output.model_dump()


@router.post("/learn")
async def learn(body: LearnRequest, deps: BrainDeps = Depends(get_deps), model: "Model" = Depends(get_model)) -> dict[str, Any]:
    """Extract patterns and learnings from content."""
    prompt = f"Extract learnings from this work session (category: {body.category}):\n\n{body.content}"
    result = await _run_agent(
        "Learn",
        lambda: learn_agent.run(prompt, deps=deps, model=model),
        deps.config.api_timeout_seconds,
    )
    return result.output.model_dump()


@router.post("/create")
async def create_content(body: CreateContentRequest, deps: BrainDeps = Depends(get_deps), model: "Model" = Depends(get_model)) -> dict[str, Any]:
    """Draft content in your voice using brain knowledge."""
    # Validate user_id against allowed list
    effective_uid = body.user_id.strip().lower() if body.user_id and body.user_id.strip() else None
    if effective_uid:
        allowed = deps.config.allowed_user_ids_list
        if allowed and effective_uid not in allowed:
            raise HTTPException(400, detail=f"Unknown user_id '{effective_uid}'. Allowed: {', '.join(allowed)}")

    registry = deps.get_content_type_registry()
    type_config = await registry.get(body.content_type)
    if not type_config:
        available = await registry.slugs()
        raise HTTPException(400, detail=f"Unknown content type '{body.content_type}'. Available: {', '.join(available)}")

    # Pre-load voice guide (scoped to user_id if provided)
    voice_sections = []
    try:
        voice_content = await deps.storage_service.get_memory_content(
            "style-voice", override_user_id=effective_uid,
        )
        if voice_content:
            for item in voice_content:
                title = item.get("title", "Untitled")
                text = item.get("content", "")[:deps.config.content_preview_limit]
                voice_sections.append(f"### {title}\n{text}")
    except Exception:
        logger.debug("Failed to pre-load voice guide")

    # Pre-load examples (scoped to user_id if provided)
    example_sections = []
    try:
        examples = await deps.storage_service.get_examples(
            content_type=body.content_type, override_user_id=effective_uid,
        )
        if examples:
            limit = deps.config.experience_limit
            for ex in examples[:limit]:
                title = ex.get("title", "Untitled")
                text = ex.get("content", "")[:deps.config.content_preview_limit]
                example_sections.append(f"### {title}\n{text}")
    except Exception:
        logger.debug("Failed to pre-load examples")

    # Build enhanced prompt (mirrors mcp_server.py create_content)
    enhanced_parts = [
        f"Content type: {type_config.name} ({body.content_type})",
    ]
    if body.structure_hint:
        enhanced_parts.append(
            "\n## Structure Template (MANDATORY)\n"
            "Follow this template structure exactly — match every section, "
            "heading, and flow. Fill in the placeholders with relevant content:\n\n"
            f"{body.structure_hint}"
        )
    elif type_config.structure_hint:
        enhanced_parts.append(f"Structure: {type_config.structure_hint}")
    if type_config.length_guidance:
        enhanced_parts.append(f"Length: {type_config.length_guidance}")
    elif type_config.max_words:
        enhanced_parts.append(
            f"Typical length: around {type_config.max_words} words, "
            "but adjust to fit the content"
        )
    if effective_uid:
        enhanced_parts.append(f"\nVoice profile: {effective_uid}")
    if voice_sections:
        enhanced_parts.append("\n## Your Voice & Tone Guide\n" + "\n\n".join(voice_sections))
    else:
        enhanced_parts.append(
            "\nNo voice guide stored yet. Write in a clear, direct, conversational tone. "
            "Avoid corporate speak and AI-sounding phrases."
        )
    if example_sections:
        enhanced_parts.append(
            f"\n## Reference Examples ({body.content_type})\nStudy these examples of your past "
            f"{type_config.name} content — match the style, structure, and voice:\n"
            + "\n\n".join(example_sections)
        )
    enhanced_parts.append(f"\n## Request\n{body.prompt}")
    enhanced = "\n".join(enhanced_parts)

    result = await _run_agent(
        "Create",
        lambda: create_agent.run(enhanced, deps=deps, model=model),
        deps.config.api_timeout_seconds,
    )
    return result.output.model_dump()


@router.post("/review")
async def review_content(body: ReviewContentRequest, deps: BrainDeps = Depends(get_deps), model: "Model" = Depends(get_model)) -> dict[str, Any]:
    """Review content quality with adaptive dimension scoring."""
    timeout = deps.config.api_timeout_seconds * deps.config.mcp_review_timeout_multiplier
    result = await _run_agent(
        "Review",
        lambda: run_full_review(body.content, deps, model, body.content_type),
        timeout,
    )
    # run_full_review returns ReviewResult directly (not RunResult)
    return result.model_dump()


@router.post("/coaching")
async def coaching_session(body: CoachingRequest, deps: BrainDeps = Depends(get_deps), model: "Model" = Depends(get_model)) -> dict[str, Any]:
    """Get daily accountability coaching."""
    from second_brain.agents.coach import coach_agent
    prompt = f"Session type: {body.session_type}\n\n{body.request}"
    result = await _run_agent(
        "Coaching",
        lambda: coach_agent.run(prompt, deps=deps, model=model),
        deps.config.api_timeout_seconds,
    )
    return result.output.model_dump()


@router.post("/prioritize")
async def prioritize_tasks(body: PrioritizeRequest, deps: BrainDeps = Depends(get_deps), model: "Model" = Depends(get_model)) -> dict[str, Any]:
    """Score and prioritize tasks using PMO methodology."""
    from second_brain.agents.pmo import pmo_agent
    result = await _run_agent(
        "Prioritize",
        lambda: pmo_agent.run(body.tasks, deps=deps, model=model),
        deps.config.api_timeout_seconds,
    )
    return result.output.model_dump()


@router.post("/email")
async def compose_email(body: EmailRequest, deps: BrainDeps = Depends(get_deps), model: "Model" = Depends(get_model)) -> dict[str, Any]:
    """Compose emails with brand voice."""
    from second_brain.agents.email_agent import email_agent
    result = await _run_agent(
        "Email",
        lambda: email_agent.run(body.request, deps=deps, model=model),
        deps.config.api_timeout_seconds,
    )
    return result.output.model_dump()


@router.post("/specialist")
async def ask_specialist(body: SpecialistRequest, deps: BrainDeps = Depends(get_deps), model: "Model" = Depends(get_model)) -> dict[str, Any]:
    """Ask a specialist question about Claude Code or Pydantic AI."""
    from second_brain.agents.specialist import specialist_agent
    result = await _run_agent(
        "Specialist",
        lambda: specialist_agent.run(body.question, deps=deps, model=model),
        deps.config.api_timeout_seconds,
    )
    return result.output.model_dump()


@router.post("/pipeline")
async def run_pipeline(body: PipelineRequest, deps: BrainDeps = Depends(get_deps), model: "Model" = Depends(get_model)) -> dict[str, Any]:
    """Run a multi-agent pipeline."""
    from second_brain.agents.utils import run_pipeline as _run_pipeline

    if not body.steps:
        from second_brain.agents.chief_of_staff import chief_of_staff
        routing = await _run_agent(
            "Pipeline routing",
            lambda: chief_of_staff.run(body.request, deps=deps, model=model),
            deps.config.api_timeout_seconds,
        )
        routing_output = routing.output
        if routing_output.target_agent == "pipeline":
            step_list = list(routing_output.pipeline_steps)
        else:
            step_list = [routing_output.target_agent]
    else:
        step_list = [s.strip() for s in body.steps.split(",") if s.strip()]

    results = await _run_agent(
        "Pipeline",
        lambda: _run_pipeline(steps=step_list, initial_prompt=body.request, deps=deps, model=model),
        deps.config.api_timeout_seconds * 2,
    )
    final = results.get("final")
    return {"result": str(final) if final else "Pipeline completed with no output."}


@router.post("/clarity")
async def analyze_clarity(body: ClarityRequest, deps: BrainDeps = Depends(get_deps), model: "Model" = Depends(get_model)) -> dict[str, Any]:
    """Analyze content for clarity and readability."""
    from second_brain.agents.clarity import clarity_agent
    result = await _run_agent(
        "Clarity",
        lambda: clarity_agent.run(body.content, deps=deps, model=model),
        deps.config.api_timeout_seconds,
    )
    return result.output.model_dump()


@router.post("/synthesize")
async def synthesize_feedback(body: SynthesizeRequest, deps: BrainDeps = Depends(get_deps), model: "Model" = Depends(get_model)) -> dict[str, Any]:
    """Consolidate review findings into actionable themes."""
    from second_brain.agents.synthesizer import synthesizer_agent
    result = await _run_agent(
        "Synthesize",
        lambda: synthesizer_agent.run(body.findings, deps=deps, model=model),
        deps.config.api_timeout_seconds,
    )
    return result.output.model_dump()


@router.post("/templates")
async def find_templates(body: TemplateRequest, deps: BrainDeps = Depends(get_deps), model: "Model" = Depends(get_model)) -> dict[str, Any]:
    """Analyze a deliverable for reusable template opportunities."""
    from second_brain.agents.template_builder import template_builder_agent
    result = await _run_agent(
        "Templates",
        lambda: template_builder_agent.run(body.deliverable, deps=deps, model=model),
        deps.config.api_timeout_seconds,
    )
    return result.output.model_dump()


@router.post("/chat")
async def unified_chat(body: ChatRequest, deps: BrainDeps = Depends(get_deps), model: "Model | None" = Depends(get_model)) -> dict[str, Any]:
    """Unified chat — Chief of Staff routes to the optimal agent automatically."""
    from second_brain.agents.chief_of_staff import chief_of_staff
    from second_brain.agents.utils import run_pipeline as _run_pipeline

    # Step 1: Run Chief of Staff routing
    routing = await _run_agent(
        "Chat routing",
        lambda: chief_of_staff.run(body.message, deps=deps, model=model),
        deps.config.api_timeout_seconds,
    )
    decision = routing.output
    target = decision.target_agent
    routing_info = {
        "agent": target,
        "reasoning": decision.reasoning,
        "confidence": decision.confidence,
        "complexity": decision.query_complexity,
    }

    # Step 2: Handle conversational short-circuit
    if target == "conversational":
        return {
            "agent": "conversational",
            "routing": routing_info,
            "output": {
                "answer": (
                    "Hey! I'm your Second Brain assistant. "
                    "Ask me anything — I can search your memory, help with content, "
                    "review your work, or answer questions using your accumulated knowledge."
                ),
                "is_conversational": True,
                "confidence": "HIGH",
            },
        }

    # Step 3: Handle pipeline routing
    if target == "pipeline":
        step_list = list(decision.pipeline_steps)
        results = await _run_agent(
            "Pipeline",
            lambda: _run_pipeline(steps=step_list, initial_prompt=body.message, deps=deps, model=model),
            deps.config.api_timeout_seconds * 2,
        )
        final = results.get("final")
        return {
            "agent": "pipeline",
            "routing": routing_info,
            "output": {"result": str(final) if final else "Pipeline completed with no output."},
        }

    # Step 4: Handle single-agent routing
    from second_brain.agents.registry import get_agent_registry
    registry = get_agent_registry()

    if target not in registry:
        raise HTTPException(400, detail=f"Unknown agent route: {target}")

    agent_instance, _desc = registry[target]

    # Special handling for review (uses run_full_review)
    if target == "review":
        timeout = deps.config.api_timeout_seconds * deps.config.mcp_review_timeout_multiplier
        result = await _run_agent(
            "Review",
            lambda: run_full_review(body.message, deps, model),
            timeout,
        )
        return {
            "agent": "review",
            "routing": routing_info,
            "output": result.model_dump(),
        }

    # Standard agent execution
    result = await _run_agent(
        target.title(),
        lambda: agent_instance.run(body.message, deps=deps, model=model),
        deps.config.api_timeout_seconds,
    )
    return {
        "agent": target,
        "routing": routing_info,
        "output": result.output.model_dump(),
    }
