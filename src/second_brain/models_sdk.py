"""ClaudeSDKModel — Pydantic AI Model wrapping claude-agent-sdk.

Routes LLM calls through Claude CLI subprocess using OAuth subscription auth.
The CLI handles tool execution via the service MCP server.
"""

import logging
from typing import TYPE_CHECKING

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse as MsgResponse,
    SystemPromptPart,
    TextPart,
    UserPromptPart,
    ToolReturnPart,
)
from pydantic_ai.models import Model, ModelRequestParameters, ModelResponse
from pydantic_ai.settings import ModelSettings
from pydantic_ai.usage import RequestUsage

if TYPE_CHECKING:
    from second_brain.config import BrainConfig

logger = logging.getLogger(__name__)


class ClaudeSDKModel(Model):
    """Pydantic AI Model that uses claude-agent-sdk for LLM calls.

    Uses Claude Pro/Max subscription via OAuth token instead of API credits.
    The SDK spawns a Claude CLI subprocess that handles tool execution
    via the service MCP server.
    """

    def __init__(
        self,
        model_id: str = "claude-sonnet-4-5-20250514",
        oauth_token: str | None = None,
        mcp_config: dict | None = None,
    ):
        self._model_id = model_id
        self._oauth_token = oauth_token
        self._mcp_config = mcp_config

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

        response_text = await self._sdk_query(system_prompt, user_prompt)

        return ModelResponse(
            parts=[TextPart(content=response_text)],
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

    async def _sdk_query(
        self, system_prompt: str, user_prompt: str
    ) -> str:
        """Execute a query via claude-agent-sdk."""
        import asyncio

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self._sdk_query_sync,
            system_prompt,
            user_prompt,
        )
        return result

    def _sdk_query_sync(
        self, system_prompt: str, user_prompt: str
    ) -> str:
        """Synchronous SDK query (runs in thread pool)."""
        try:
            from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
        except ImportError:
            raise RuntimeError(
                "claude-agent-sdk not installed. "
                "Install with: pip install claude-agent-sdk"
            )

        if self._oauth_token:
            from second_brain.auth import configure_subscription_env
            configure_subscription_env(self._oauth_token)

        mcp_servers = []
        allowed_tools = []
        if self._mcp_config:
            mcp_servers = [self._mcp_config]
            server_name = self._mcp_config.get("name", "second-brain-services")
            allowed_tools = [f"mcp__{server_name}__*"]

        options = ClaudeAgentOptions(
            model=self._model_id,
            prompt=system_prompt or "You are a helpful AI assistant.",
            mcp_servers=mcp_servers,
            allowed_tools=allowed_tools,
        )

        client = ClaudeSDKClient(options)
        response = client.process_message(user_prompt)

        if isinstance(response, str):
            return response
        return str(response)


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
    if not any(c.isdigit() for c in model_id.split("-")[-1]):
        model_id = f"{model_id}-20250514"

    return ClaudeSDKModel(
        model_id=model_id,
        oauth_token=token,
        mcp_config=get_service_mcp_config(),
    )


def is_sdk_available() -> bool:
    """Check if claude-agent-sdk is installed."""
    try:
        import claude_agent_sdk  # noqa: F401
        return True
    except ImportError:
        return False


__all__ = ["ClaudeSDKModel", "create_sdk_model", "is_sdk_available"]
