"""Agent endpoints — 13 Pydantic AI agents exposed as POST endpoints."""

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException

from second_brain.deps import BrainDeps
from second_brain.api.deps import get_deps, get_model
from second_brain.api.schemas import (
    RecallRequest,
    AskRequest,
    LearnRequest,
    CreateContentRequest,
    ReviewContentRequest,
    CoachingRequest,
    PrioritizeRequest,
    EmailRequest,
    SpecialistRequest,
    PipelineRequest,
    ClarityRequest,
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


@router.post("/recall")
async def recall(body: RecallRequest, deps: BrainDeps = Depends(get_deps), model=Depends(get_model)):
    """Search memory for relevant context, patterns, and past experiences."""
    timeout = deps.config.api_timeout_seconds
    try:
        async with asyncio.timeout(timeout):
            result = await recall_agent.run(
                f"Search memory for: {body.query}", deps=deps, model=model,
            )
    except TimeoutError:
        raise HTTPException(504, detail=f"Recall timed out after {timeout}s")
    return result.output.model_dump()


@router.post("/ask")
async def ask(body: AskRequest, deps: BrainDeps = Depends(get_deps), model=Depends(get_model)):
    """Ask the Second Brain a question."""
    timeout = deps.config.api_timeout_seconds
    try:
        async with asyncio.timeout(timeout):
            result = await ask_agent.run(body.question, deps=deps, model=model)
    except TimeoutError:
        raise HTTPException(504, detail=f"Ask timed out after {timeout}s")
    return result.output.model_dump()


@router.post("/learn")
async def learn(body: LearnRequest, deps: BrainDeps = Depends(get_deps), model=Depends(get_model)):
    """Extract patterns and learnings from content."""
    timeout = deps.config.api_timeout_seconds
    prompt = f"Extract learnings from this work session (category: {body.category}):\n\n{body.content}"
    try:
        async with asyncio.timeout(timeout):
            result = await learn_agent.run(prompt, deps=deps, model=model)
    except TimeoutError:
        raise HTTPException(504, detail=f"Learn timed out after {timeout}s")
    return result.output.model_dump()


@router.post("/create")
async def create_content(body: CreateContentRequest, deps: BrainDeps = Depends(get_deps), model=Depends(get_model)):
    """Draft content in your voice using brain knowledge."""
    registry = deps.get_content_type_registry()
    type_config = await registry.get(body.content_type)
    if not type_config:
        available = await registry.slugs()
        raise HTTPException(400, detail=f"Unknown content type '{body.content_type}'. Available: {', '.join(available)}")

    # Pre-load voice guide
    voice_sections = []
    try:
        voice_content = await deps.storage_service.get_memory_content("style-voice")
        if voice_content:
            for item in voice_content:
                title = item.get("title", "Untitled")
                text = item.get("content", "")[:deps.config.content_preview_limit]
                voice_sections.append(f"### {title}\n{text}")
    except Exception:
        logger.debug("Failed to pre-load voice guide")

    # Pre-load examples
    example_sections = []
    try:
        examples = await deps.storage_service.get_examples(content_type=body.content_type)
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
        f"Structure: {type_config.structure_hint}",
    ]
    if type_config.length_guidance:
        enhanced_parts.append(f"Length: {type_config.length_guidance}")
    elif type_config.max_words:
        enhanced_parts.append(
            f"Typical length: around {type_config.max_words} words, "
            "but adjust to fit the content"
        )
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

    timeout = deps.config.api_timeout_seconds
    try:
        async with asyncio.timeout(timeout):
            result = await create_agent.run(enhanced, deps=deps, model=model)
    except TimeoutError:
        raise HTTPException(504, detail=f"Create timed out after {timeout}s")
    return result.output.model_dump()


@router.post("/review")
async def review_content(body: ReviewContentRequest, deps: BrainDeps = Depends(get_deps), model=Depends(get_model)):
    """Review content quality with adaptive dimension scoring."""
    timeout = deps.config.api_timeout_seconds * deps.config.mcp_review_timeout_multiplier
    try:
        async with asyncio.timeout(timeout):
            result = await run_full_review(body.content, deps, model, body.content_type)
    except TimeoutError:
        raise HTTPException(504, detail=f"Review timed out after {timeout}s")
    # run_full_review returns ReviewResult directly (not RunResult)
    return result.model_dump()


@router.post("/coaching")
async def coaching_session(body: CoachingRequest, deps: BrainDeps = Depends(get_deps), model=Depends(get_model)):
    """Get daily accountability coaching."""
    from second_brain.agents.coach import coach_agent
    prompt = f"Session type: {body.session_type}\n\n{body.request}"
    timeout = deps.config.api_timeout_seconds
    try:
        async with asyncio.timeout(timeout):
            result = await coach_agent.run(prompt, deps=deps, model=model)
    except TimeoutError:
        raise HTTPException(504, detail=f"Coaching timed out after {timeout}s")
    return result.output.model_dump()


@router.post("/prioritize")
async def prioritize_tasks(body: PrioritizeRequest, deps: BrainDeps = Depends(get_deps), model=Depends(get_model)):
    """Score and prioritize tasks using PMO methodology."""
    from second_brain.agents.pmo import pmo_agent
    timeout = deps.config.api_timeout_seconds
    try:
        async with asyncio.timeout(timeout):
            result = await pmo_agent.run(body.tasks, deps=deps, model=model)
    except TimeoutError:
        raise HTTPException(504, detail=f"Prioritization timed out after {timeout}s")
    return result.output.model_dump()


@router.post("/email")
async def compose_email(body: EmailRequest, deps: BrainDeps = Depends(get_deps), model=Depends(get_model)):
    """Compose emails with brand voice."""
    from second_brain.agents.email_agent import email_agent
    timeout = deps.config.api_timeout_seconds
    try:
        async with asyncio.timeout(timeout):
            result = await email_agent.run(body.request, deps=deps, model=model)
    except TimeoutError:
        raise HTTPException(504, detail=f"Email composition timed out after {timeout}s")
    return result.output.model_dump()


@router.post("/specialist")
async def ask_specialist(body: SpecialistRequest, deps: BrainDeps = Depends(get_deps), model=Depends(get_model)):
    """Ask a specialist question about Claude Code or Pydantic AI."""
    from second_brain.agents.specialist import specialist_agent
    timeout = deps.config.api_timeout_seconds
    try:
        async with asyncio.timeout(timeout):
            result = await specialist_agent.run(body.question, deps=deps, model=model)
    except TimeoutError:
        raise HTTPException(504, detail=f"Specialist query timed out after {timeout}s")
    return result.output.model_dump()


@router.post("/pipeline")
async def run_pipeline(body: PipelineRequest, deps: BrainDeps = Depends(get_deps), model=Depends(get_model)):
    """Run a multi-agent pipeline."""
    from second_brain.agents.utils import run_pipeline as _run_pipeline

    if not body.steps:
        from second_brain.agents.chief_of_staff import chief_of_staff
        timeout = deps.config.api_timeout_seconds
        try:
            async with asyncio.timeout(timeout):
                routing = await chief_of_staff.run(body.request, deps=deps, model=model)
        except TimeoutError:
            raise HTTPException(504, detail=f"Pipeline routing timed out after {timeout}s")
        routing_output = routing.output
        if routing_output.target_agent == "pipeline":
            step_list = list(routing_output.pipeline_steps)
        else:
            step_list = [routing_output.target_agent]
    else:
        step_list = [s.strip() for s in body.steps.split(",") if s.strip()]

    results = await _run_pipeline(
        steps=step_list, initial_prompt=body.request, deps=deps, model=model,
    )
    final = results.get("final")
    return {"result": str(final) if final else "Pipeline completed with no output."}


@router.post("/clarity")
async def analyze_clarity(body: ClarityRequest, deps: BrainDeps = Depends(get_deps), model=Depends(get_model)):
    """Analyze content for clarity and readability."""
    from second_brain.agents.clarity import clarity_agent
    timeout = deps.config.api_timeout_seconds
    try:
        async with asyncio.timeout(timeout):
            result = await clarity_agent.run(body.content, deps=deps, model=model)
    except TimeoutError:
        raise HTTPException(504, detail=f"Clarity analysis timed out after {timeout}s")
    return result.output.model_dump()


@router.post("/synthesize")
async def synthesize_feedback(body: SynthesizeRequest, deps: BrainDeps = Depends(get_deps), model=Depends(get_model)):
    """Consolidate review findings into actionable themes."""
    from second_brain.agents.synthesizer import synthesizer_agent
    timeout = deps.config.api_timeout_seconds
    try:
        async with asyncio.timeout(timeout):
            result = await synthesizer_agent.run(body.findings, deps=deps, model=model)
    except TimeoutError:
        raise HTTPException(504, detail=f"Synthesis timed out after {timeout}s")
    return result.output.model_dump()


@router.post("/templates")
async def find_templates(body: TemplateRequest, deps: BrainDeps = Depends(get_deps), model=Depends(get_model)):
    """Analyze a deliverable for reusable template opportunities."""
    from second_brain.agents.template_builder import template_builder_agent
    timeout = deps.config.api_timeout_seconds
    try:
        async with asyncio.timeout(timeout):
            result = await template_builder_agent.run(body.deliverable, deps=deps, model=model)
    except TimeoutError:
        raise HTTPException(504, detail=f"Template analysis timed out after {timeout}s")
    return result.output.model_dump()
