"""LinkedIn Engagement agent — authentic comments and replies using brain context."""

import logging

from pydantic_ai import Agent, ModelRetry, RunContext

from second_brain.agents.utils import (
    all_tools_failed,
    format_memories,
    format_relations,
    load_voice_context,
    tool_error,
)
from second_brain.deps import BrainDeps
from second_brain.schemas import LinkedInEngagementResult

logger = logging.getLogger(__name__)

# Patterns that signal AI-generated engagement — must be caught and rejected
AI_SOUNDING_PATTERNS = [
    "great post",
    "thanks for sharing",
    "i couldn't agree more",
    "absolutely!",
    "100%!",
    "love this!",
    "so true!",
    "this resonates",
]

linkedin_engagement_agent = Agent(
    deps_type=BrainDeps,
    output_type=LinkedInEngagementResult,
    retries=3,
    instructions=(
        "You are a LinkedIn Engagement specialist. You help the user comment on "
        "others' posts and reply to comments on their own posts in their authentic voice.\n\n"
        "FOR COMMENTS (on someone else's post):\n"
        "1. Load your voice guide via load_voice_guide\n"
        "2. Load expertise/knowledge context via load_expertise_context\n"
        "3. Analyze the original post — what's the key point?\n"
        "4. Write a comment that adds genuine value. NO 'Great post!' NO 'Thanks for "
        "sharing!' NO generic agreement. Instead: share a relevant experience, offer "
        "a counter-perspective, ask a probing question, or add a specific insight "
        "from your expertise.\n\n"
        "FOR REPLIES (to comments on your own post):\n"
        "1. Load your voice guide\n"
        "2. Search memory for context about the topic via search_relevant_knowledge\n"
        "3. Read the original post AND the comment thread to stay in context\n"
        "4. Reply conversationally. Reference specific points from their comment. "
        "Share additional insight or ask a follow-up question.\n\n"
        "ANTI-AI RULES (CRITICAL — your output will be REJECTED if you violate these):\n"
        "Never use: 'Great point!', 'Thanks for sharing!', 'I couldn't agree more', "
        "'This resonates with me', 'Absolutely!', '100%!', 'Love this!', 'So true!'. "
        "These are AI-generated engagement patterns that destroy authenticity. "
        "Instead: be specific, reference something from the post, share your own "
        "experience or data, disagree respectfully, ask a genuine question.\n\n"
        "VOICE:\n"
        "Use the user's CONVERSATIONAL voice — not their formal writing voice. "
        "Comments should feel like talking, not presenting.\n\n"
        "LENGTH:\n"
        "Comments should be 1-5 sentences. Replies should be 1-3 sentences. "
        "Don't write essays in comments. Brevity is authenticity.\n\n"
        "CONTEXT:\n"
        "Use load_expertise_context to understand what you're an expert in. "
        "Reference meetings, client work, and real experiences via "
        "search_relevant_knowledge — this is what makes comments sound like a "
        "REAL PERSON, not an AI.\n\n"
        "USER PROFILE ROUTING:\n"
        "Your prompt may include 'Voice profile: <user_id>'. When present, pass "
        "that user_id to load_voice_guide and load_expertise_context as voice_user_id.\n\n"
        "ERROR HANDLING:\n"
        "If brain context tools return 'BACKEND_ERROR:' messages, write the best "
        "comment you can based on the post content alone. Set the error field."
    ),
)


@linkedin_engagement_agent.output_validator
async def validate_engagement(
    ctx: RunContext[BrainDeps], output: LinkedInEngagementResult
) -> LinkedInEngagementResult:
    """Validate engagement output for authenticity."""
    if output.error:
        return output

    # Deterministic check: if all tools returned errors, set error field and accept
    tool_outputs = []
    for msg in ctx.messages:
        if hasattr(msg, "parts"):
            for part in msg.parts:
                if hasattr(part, "content") and isinstance(part.content, str):
                    tool_outputs.append(part.content)

    if tool_outputs and all_tools_failed(tool_outputs):
        if not output.error:
            output = output.model_copy(update={
                "error": "All brain context backends unavailable. Response written without brain context.",
            })
        return output

    word_count = len(output.response.split())
    if word_count < 5:
        raise ModelRetry(
            f"Response is only {word_count} words. Write a substantive comment "
            "that adds genuine value — at least 5 words."
        )

    if output.engagement_type not in ("comment", "reply"):
        raise ModelRetry(
            f"Invalid engagement_type '{output.engagement_type}'. "
            "Must be 'comment' or 'reply'."
        )

    # Detect AI-sounding patterns
    response_lower = output.response.lower().strip()
    for pattern in AI_SOUNDING_PATTERNS:
        if response_lower.startswith(pattern):
            raise ModelRetry(
                f"Response starts with '{pattern}' — this is an AI engagement pattern "
                "that sounds inauthentic. Rewrite with substance: share an experience, "
                "ask a genuine question, offer a specific insight, or respectfully disagree."
            )

    if output.word_count == 0:
        output.word_count = word_count

    return output


@linkedin_engagement_agent.tool
async def load_voice_guide(ctx: RunContext[BrainDeps], voice_user_id: str = "") -> str:
    """Load the user's conversational voice guide for comment style matching.
    Pass voice_user_id for a specific user's voice profile."""
    try:
        uid = voice_user_id if voice_user_id else None
        return await load_voice_context(ctx.deps, preview_limit=200, voice_user_id=uid)
    except Exception as e:
        return tool_error("load_voice_guide", e)


@linkedin_engagement_agent.tool
async def load_expertise_context(
    ctx: RunContext[BrainDeps], voice_user_id: str = "",
) -> str:
    """Load the user's subject matter expertise for authentic engagement.
    Returns product, audience, and positioning context."""
    try:
        uid = voice_user_id if voice_user_id else None
        sections = []

        for category, label in [
            ("product", "Products/Services"),
            ("audience", "Audience"),
            ("positioning", "Positioning"),
        ]:
            items = await ctx.deps.storage_service.get_memory_content(
                category, override_user_id=uid,
            )
            if items:
                lines = [f"### {label}"]
                for item in items:
                    title = item.get("title", "Untitled")
                    text = item.get("content", "")[:ctx.deps.config.content_preview_limit]
                    lines.append(f"**{title}**: {text}")
                sections.append("\n".join(lines))

        if not sections:
            return "No expertise context found. Engage based on the post content alone."
        return "## Your Expertise\n" + "\n\n".join(sections)
    except Exception as e:
        return tool_error("load_expertise_context", e)


@linkedin_engagement_agent.tool
async def search_relevant_knowledge(ctx: RunContext[BrainDeps], topic: str) -> str:
    """Search memory for relevant knowledge, experiences, and meeting notes.
    This gives you real anecdotes and data points to reference in comments."""
    try:
        # Topic-specific memories
        result = await ctx.deps.memory_service.search(topic)
        memories = result.memories
        relations = result.relations

        # Meeting/conversation context
        meeting_memories = []
        try:
            meeting_result = await ctx.deps.memory_service.search(
                f"meeting {topic}"
            )
            meeting_memories = meeting_result.memories
        except Exception:
            logger.debug("Meeting context search failed in engagement")

        sections = []

        if memories:
            sections.append(
                "## Relevant Knowledge\n" + format_memories(memories[:5])
            )

        if meeting_memories:
            meeting_lines = ["## Meeting/Experience Context"]
            for m in meeting_memories[:3]:
                memory = m.get("memory", m.get("result", ""))
                meeting_lines.append(f"- {memory}")
            sections.append("\n".join(meeting_lines))

        rel_text = format_relations(relations)
        if rel_text:
            sections.append(rel_text)

        return "\n\n".join(sections) if sections else "No relevant knowledge found."
    except Exception as e:
        return tool_error("search_relevant_knowledge", e)


@linkedin_engagement_agent.tool
async def search_past_engagement(
    ctx: RunContext[BrainDeps], topic: str = "",
) -> str:
    """Search memory for past LinkedIn engagement to maintain consistency."""
    try:
        query = f"linkedin comment {topic}" if topic else "linkedin comment"
        result = await ctx.deps.memory_service.search(query)
        memories = result.memories
        if not memories:
            return "No past engagement found in memory."
        lines = ["## Past Engagement"]
        for m in memories[:5]:
            memory = m.get("memory", m.get("result", ""))
            lines.append(f"- {memory}")
        return "\n".join(lines)
    except Exception as e:
        return tool_error("search_past_engagement", e)


@linkedin_engagement_agent.tool
async def load_content_examples(
    ctx: RunContext[BrainDeps], voice_user_id: str = "",
) -> str:
    """Load past LinkedIn posts to understand the user's writing style.
    Helps maintain consistent engagement voice."""
    try:
        uid = voice_user_id if voice_user_id else None
        examples = await ctx.deps.storage_service.get_examples(
            content_type="linkedin", override_user_id=uid,
        )
        if not examples:
            return "No LinkedIn examples found."
        limit = ctx.deps.config.experience_limit
        sections = []
        for ex in examples[:limit]:
            title = ex.get("title", "Untitled")
            text = ex.get("content", "")[:ctx.deps.config.content_preview_limit]
            sections.append(f"### {title}\n{text}")
        return "## Your LinkedIn Posts\n" + "\n\n".join(sections)
    except Exception as e:
        return tool_error("load_content_examples", e)
