"""Email Agent — email composition, search, and organization."""

import logging
from pydantic_ai import Agent, ModelRetry, RunContext
from pydantic_ai.tools import ToolDefinition
from second_brain.agents.utils import all_tools_failed, load_voice_context, tool_error
from second_brain.deps import BrainDeps
from second_brain.schemas import EmailAction

logger = logging.getLogger(__name__)

email_agent = Agent(
    deps_type=BrainDeps,
    output_type=EmailAction,
    retries=3,
    instructions=(
        "You are an Email Agent. Compose, search, and organize emails "
        "with brand voice consistency.\n\n"
        "BEFORE WRITING ANY EMAIL:\n"
        "1. Load voice guide for brand tone\n"
        "2. Search for relevant templates/examples\n"
        "3. Check for past thread context if following up\n"
        "4. Apply appropriate formality for recipient\n\n"
        "EMAIL STRUCTURE:\n"
        "Subject: Clear, specific, value-focused\n"
        "Opening: Context/reference to previous conversation\n"
        "Body: Clear value proposition, specific next steps, easy to scan\n"
        "Closing: Appropriate sign-off\n\n"
        "For 'send' actions, always draft first and set status='draft'. "
        "The user must approve before sending."
    ),
)


@email_agent.output_validator
async def validate_email(ctx: RunContext[BrainDeps], output: EmailAction) -> EmailAction:
    """Validate email action with deterministic error detection."""
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

    # If all tools failed, set error and return
    if tool_outputs and all_tools_failed(tool_outputs):
        if not output.error:
            output = output.model_copy(update={
                "error": "All email backends unavailable. Email action skipped.",
            })
        return output

    # Normal validation (only if no error)
    if output.action_type in ("send", "draft") and not output.subject:
        raise ModelRetry(
            "Emails must have a subject line. "
            "If tools failed, set the error field instead of retrying."
        )
    if output.action_type in ("send", "draft") and len(output.body) < 20:
        raise ModelRetry(
            "Email body is too short. Write a complete email. "
            "If tools failed, set the error field instead of retrying."
        )
    # Force draft status for send actions (safety)
    if output.action_type == "send":
        output = output.model_copy(update={"status": "draft"})
    return output


@email_agent.tool
async def load_email_voice(ctx: RunContext[BrainDeps], voice_user_id: str = "") -> str:
    """Load email-specific voice and style guidelines.
    Pass voice_user_id to load a specific user's voice profile."""
    try:
        uid = voice_user_id if voice_user_id else None
        parts = []
        voice_text = await load_voice_context(ctx.deps, preview_limit=200, voice_user_id=uid)
        if voice_text:
            parts.append(voice_text)
        examples = await ctx.deps.storage_service.get_examples(
            content_type="email", override_user_id=uid,
        )
        if examples:
            parts.append("Email examples:\n" + "\n".join(
                f"- {e.get('title', '?')}: {e.get('content', '')[:100]}..." for e in examples[:3]
            ))
        return "\n\n".join(parts) if parts else "No email voice guide available."
    except Exception as e:
        return tool_error("load_email_voice", e)


async def _email_available(ctx: RunContext[BrainDeps], tool_def: ToolDefinition) -> ToolDefinition | None:
    return tool_def if ctx.deps.email_service else None


@email_agent.tool(prepare=_email_available)
async def search_email_history(ctx: RunContext[BrainDeps], query: str) -> str:
    """Search past emails for context."""
    try:
        results = await ctx.deps.email_service.search(query, limit=5)
        if not results:
            return "No matching emails found."
        lines = [f"- {r.get('subject', '?')} from {r.get('from', '?')}" for r in results]
        return "Email history:\n" + "\n".join(lines)
    except Exception as e:
        return tool_error("search_email_history", e)


@email_agent.tool(prepare=_email_available)
async def send_email(ctx: RunContext[BrainDeps], to: str, subject: str, body: str) -> str:
    """Send an email (requires user approval)."""
    try:
        result = await ctx.deps.email_service.send([to], subject, body)
        return f"Email sent to {to}: {result.get('status', 'unknown')}"
    except Exception as e:
        return tool_error("send_email", e)
