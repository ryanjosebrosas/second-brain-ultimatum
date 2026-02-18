"""ClaudeSDKModel — Pydantic AI Model wrapping claude-agent-sdk.

Routes LLM calls through Claude CLI subprocess using OAuth subscription auth.
The CLI handles tool execution via the service MCP server.
"""

import json
import logging
import os
import re
from typing import TYPE_CHECKING

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse as MsgResponse,
    SystemPromptPart,
    TextPart,
    ToolCallPart,
    UserPromptPart,
    ToolReturnPart,
)
from pydantic_ai.models import Model, ModelRequestParameters, ModelResponse
from pydantic_ai.settings import ModelSettings
from pydantic_ai.usage import RequestUsage

if TYPE_CHECKING:
    from second_brain.config import BrainConfig

logger = logging.getLogger(__name__)

# Current model snapshot date — update when new snapshots release
DEFAULT_MODEL_DATE = "20250929"
_DATE_SUFFIX_RE = re.compile(r"-\d{8}$")


class ClaudeSDKModel(Model):
    """Pydantic AI Model that uses claude-agent-sdk for LLM calls.

    Uses Claude Pro/Max subscription via OAuth token instead of API credits.
    The SDK spawns a Claude CLI subprocess that handles tool execution
    via the service MCP server.
    """

    def __init__(
        self,
        model_id: str = f"claude-sonnet-4-5-{DEFAULT_MODEL_DATE}",
        oauth_token: str | None = None,
        mcp_config: dict | None = None,
        mcp_server_name: str = "second-brain-services",
        timeout: int = 120,
    ):
        self._model_id = model_id
        self._oauth_token = oauth_token
        self._mcp_config = mcp_config
        self._mcp_server_name = mcp_server_name
        self._timeout = timeout

    @property
    def model_name(self) -> str:
        return f"claude-sdk:{self._model_id}"

    @property
    def system(self) -> str:
        return "claude-sdk"

    async def request(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> ModelResponse:
        """Send messages to Claude via the SDK."""
        system_prompt, user_prompt = self._convert_messages(messages)
        output_schema = self._extract_output_schema(model_request_parameters)

        response_data = await self._sdk_query(
            system_prompt, user_prompt, output_schema
        )

        # Build response parts based on output mode and response type
        parts: list = []

        if isinstance(response_data, dict):
            # Structured output returned — format based on output mode
            if (model_request_parameters.output_mode == 'tool'
                    and model_request_parameters.output_tools):
                # Tool mode: return as a tool call that pydantic-ai will intercept
                tool_def = model_request_parameters.output_tools[0]
                parts.append(ToolCallPart(
                    tool_name=tool_def.name,
                    args=response_data,
                    tool_call_id=f"sdk-{id(response_data):x}",
                ))
            else:
                # Native/prompted mode: return JSON string
                parts.append(TextPart(content=json.dumps(response_data)))
        else:
            # Plain text response (text mode or fallback)
            parts.append(TextPart(content=response_data))

        return ModelResponse(
            parts=parts,
            model_name=self.model_name,
            usage=RequestUsage(),
        )

    def _convert_messages(
        self, messages: list[ModelMessage]
    ) -> tuple[str, str]:
        """Convert Pydantic AI messages to system + user prompt strings."""
        system_parts: list[str] = []
        user_parts: list[str] = []

        for msg in messages:
            # ModelRequest has instructions field for system prompt
            if isinstance(msg, ModelRequest) and msg.instructions:
                system_parts.append(msg.instructions)

            for part in msg.parts:
                if isinstance(part, SystemPromptPart):
                    system_parts.append(part.content)
                elif isinstance(part, UserPromptPart):
                    user_parts.append(part.content)
                elif isinstance(part, TextPart):
                    user_parts.append(part.content)
                elif isinstance(part, ToolReturnPart):
                    user_parts.append(
                        f"Tool result ({part.tool_name}): {part.content}"
                    )

        system_prompt = "\n\n".join(system_parts) if system_parts else ""
        user_prompt = "\n\n".join(user_parts) if user_parts else ""

        return system_prompt, user_prompt

    def _extract_output_schema(
        self, model_request_parameters: ModelRequestParameters
    ) -> dict | None:
        """Extract JSON schema for structured output from model request parameters.

        Returns the schema dict if structured output is requested, None for text mode.
        Handles both tool mode (schema in output_tools) and native mode (schema in output_object).
        """
        if model_request_parameters.output_mode == 'text':
            return None

        # Prefer output_object (native/prompted mode)
        if model_request_parameters.output_object is not None:
            schema = model_request_parameters.output_object.json_schema
            if schema:
                return schema

        # Fall back to output_tools (tool mode)
        if model_request_parameters.output_tools:
            return model_request_parameters.output_tools[0].parameters_json_schema

        return None

    async def _sdk_query(
        self, system_prompt: str, user_prompt: str,
        output_schema: dict | None = None,
    ) -> str | dict:
        """Execute a query via claude-agent-sdk async API.

        Important: The SDK's async generator uses anyio task groups internally.
        We must exhaust the generator fully (no early return/break) to avoid
        GeneratorExit triggering anyio cancel scope cleanup errors that corrupt
        pydantic-ai's cancel scope stack. We use asyncio.timeout (not wait_for)
        to avoid creating task boundaries that conflict with anyio scopes.
        """
        import asyncio

        try:
            from claude_agent_sdk import (
                ClaudeAgentOptions,
                ResultMessage,
                query as sdk_query,
            )
        except ImportError:
            raise RuntimeError(
                "claude-agent-sdk not installed. "
                "Install with: pip install claude-agent-sdk"
            )

        if self._oauth_token:
            from second_brain.auth import configure_subscription_env
            configure_subscription_env(self._oauth_token)

        # Set MCP timeout env vars for the SDK subprocess
        if self._mcp_config:
            os.environ.setdefault("MCP_TOOL_TIMEOUT", "120000")
            os.environ.setdefault("CLAUDE_CODE_STREAM_CLOSE_TIMEOUT", "180000")

        mcp_servers: dict = {}
        allowed_tools: list[str] = []
        if self._mcp_config:
            mcp_servers = {self._mcp_server_name: self._mcp_config}
            allowed_tools = [f"mcp__{self._mcp_server_name}__*"]

        options_kwargs: dict = {
            "model": self._model_id,
            "system_prompt": system_prompt or "You are a helpful AI assistant.",
            "mcp_servers": mcp_servers,
            "allowed_tools": allowed_tools,
        }
        if output_schema:
            options_kwargs["output_format"] = {
                "type": "json_schema",
                "schema": output_schema,
            }
        options = ClaudeAgentOptions(**options_kwargs)

        # Temporarily unset CLAUDECODE to allow SDK subprocess when running
        # inside a Claude Code session (e.g., via MCP or CLI invoked by Claude).
        saved_claudecode = os.environ.pop("CLAUDECODE", None)
        try:
            result: str | dict = ""
            # Use asyncio.timeout (same task) instead of asyncio.wait_for
            # (new task) to avoid anyio cancel scope task boundary conflicts.
            async with asyncio.timeout(self._timeout):
                # Exhaust the generator fully — do NOT return/break early.
                # Early exit triggers GeneratorExit which corrupts anyio's
                # cancel scope stack when the SDK cleans up its task group.
                async for message in sdk_query(
                    prompt=user_prompt, options=options
                ):
                    if isinstance(message, ResultMessage):
                        # Prefer structured_output when we requested it
                        if output_schema and message.structured_output is not None:
                            result = message.structured_output
                        else:
                            result = message.result or ""
            return result
        except TimeoutError:
            logger.error(
                "SDK query timed out after %ds. This may indicate the MCP "
                "server subprocess is not responding. Check stderr for errors.",
                self._timeout,
            )
            raise RuntimeError(
                f"SDK query timed out after {self._timeout}s. "
                "The MCP server subprocess may have failed to respond. "
                "Try increasing api_timeout_seconds in config."
            )
        finally:
            if saved_claudecode is not None:
                os.environ["CLAUDECODE"] = saved_claudecode


def create_sdk_model(config: "BrainConfig") -> ClaudeSDKModel | None:
    """Create a ClaudeSDKModel from config, or None if not available.

    Checks:
    1. use_subscription is True
    2. OAuth token is available (config, env, or credential store)
    3. Token format is valid
    4. Claude CLI is installed
    """
    from second_brain.auth import (
        get_oauth_token,
        validate_oauth_token,
        verify_claude_cli,
    )
    from second_brain.service_mcp import get_service_mcp_config

    if not config.use_subscription:
        return None

    token = config.claude_oauth_token or get_oauth_token()
    if not token:
        logger.warning(
            "Subscription auth enabled but no OAuth token found. "
            "Run 'claude' to authenticate, or set CLAUDE_OAUTH_TOKEN."
        )
        return None

    if not validate_oauth_token(token):
        logger.warning("Invalid OAuth token format. Expected sk-ant-oat01-* prefix.")
        return None

    cli_ok, cli_info = verify_claude_cli()
    if not cli_ok:
        logger.warning("Claude CLI not found: %s", cli_info)
        return None

    logger.info("Claude CLI found: %s", cli_info)

    model_id = config.primary_model.replace("anthropic:", "")
    if not _DATE_SUFFIX_RE.search(model_id):
        model_id = f"{model_id}-{DEFAULT_MODEL_DATE}"

    mcp_server_name, mcp_config = get_service_mcp_config()

    return ClaudeSDKModel(
        model_id=model_id,
        oauth_token=token,
        mcp_config=mcp_config,
        mcp_server_name=mcp_server_name,
        timeout=config.api_timeout_seconds * 4,
    )


def is_sdk_available() -> bool:
    """Check if claude-agent-sdk is installed."""
    try:
        import claude_agent_sdk  # noqa: F401
        return True
    except ImportError:
        return False


__all__ = ["ClaudeSDKModel", "create_sdk_model", "is_sdk_available"]
