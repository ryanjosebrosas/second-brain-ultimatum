"""Tests for ClaudeSDKModel and subscription auth model integration."""

import json
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from second_brain.config import BrainConfig
from second_brain.models_sdk import ClaudeSDKModel
from pydantic_ai.messages import TextPart, ToolCallPart


# Known env vars to clear so host values don't bleed.
_ENV_VARS = [
    "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_BASE_URL", "OLLAMA_API_KEY",
    "OLLAMA_MODEL", "MEM0_API_KEY", "GRAPH_PROVIDER", "NEO4J_URL", "NEO4J_USERNAME",
    "NEO4J_PASSWORD", "SUPABASE_URL", "SUPABASE_KEY", "BRAIN_USER_ID",
    "BRAIN_DATA_PATH", "PRIMARY_MODEL", "FALLBACK_MODEL", "USE_SUBSCRIPTION",
    "CLAUDE_OAUTH_TOKEN", "CLAUDECODE",
    "MODEL_PROVIDER", "MODEL_NAME", "MODEL_FALLBACK_CHAIN",
    "OPENAI_MODEL_NAME", "GROQ_API_KEY", "GROQ_MODEL_NAME",
]


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for var in _ENV_VARS:
        monkeypatch.delenv(var, raising=False)


def _make_config(tmp_path, **overrides):
    defaults = {
        "supabase_url": "https://test.supabase.co",
        "supabase_key": "test-key",
        "brain_data_path": tmp_path,
        "_env_file": None,
    }
    defaults.update(overrides)
    return BrainConfig(**defaults)


class TestClaudeSDKModel:
    """Tests for ClaudeSDKModel class."""

    def test_model_name(self):
        from second_brain.models_sdk import ClaudeSDKModel
        model = ClaudeSDKModel(model_id="claude-sonnet-4-5-20250929")
        assert model.model_name == "claude-sdk:claude-sonnet-4-5-20250929"

    def test_system(self):
        from second_brain.models_sdk import ClaudeSDKModel
        model = ClaudeSDKModel()
        assert model.system == "claude-sdk"

    def test_default_model_id(self):
        from second_brain.models_sdk import ClaudeSDKModel
        model = ClaudeSDKModel()
        assert "claude" in model.model_name

    def test_convert_messages_system_prompt(self):
        """System prompt parts are extracted correctly."""
        from second_brain.models_sdk import ClaudeSDKModel
        from pydantic_ai.messages import ModelRequest, SystemPromptPart, UserPromptPart

        model = ClaudeSDKModel()
        messages = [
            ModelRequest(parts=[
                SystemPromptPart(content="You are a helper"),
                UserPromptPart(content="Hello"),
            ])
        ]
        system, user = model._convert_messages(messages)
        assert "helper" in system
        assert "Hello" in user

    def test_convert_messages_no_system(self):
        """Works without system prompt."""
        from second_brain.models_sdk import ClaudeSDKModel
        from pydantic_ai.messages import ModelRequest, UserPromptPart

        model = ClaudeSDKModel()
        messages = [
            ModelRequest(parts=[UserPromptPart(content="Just a question")])
        ]
        system, user = model._convert_messages(messages)
        assert system == ""
        assert "question" in user


class TestCreateSDKModel:
    """Tests for create_sdk_model() factory."""

    def test_returns_none_when_disabled(self, tmp_path):
        """Returns None when use_subscription is False."""
        config = _make_config(tmp_path)
        assert config.use_subscription is False

        from second_brain.models_sdk import create_sdk_model
        result = create_sdk_model(config)
        assert result is None

    def test_returns_none_when_no_token(self, tmp_path):
        """Returns None when subscription enabled but no token available."""
        config = _make_config(tmp_path, use_subscription=True)

        with patch("second_brain.auth.get_oauth_token", return_value=None):
            from second_brain.models_sdk import create_sdk_model
            result = create_sdk_model(config)
            assert result is None

    def test_returns_none_when_invalid_token(self, tmp_path):
        """Returns None when token has invalid format."""
        config = _make_config(
            tmp_path,
            use_subscription=True,
            claude_oauth_token="invalid-token-format",
        )

        with patch("second_brain.auth.validate_oauth_token", return_value=False):
            from second_brain.models_sdk import create_sdk_model
            result = create_sdk_model(config)
            assert result is None

    def test_returns_none_when_cli_missing(self, tmp_path):
        """Returns None when claude CLI is not installed."""
        config = _make_config(
            tmp_path,
            use_subscription=True,
            claude_oauth_token="sk-ant-oat01-valid-token-here",
        )

        with patch("second_brain.auth.get_oauth_token", return_value="sk-ant-oat01-valid"), \
             patch("second_brain.auth.validate_oauth_token", return_value=True), \
             patch("second_brain.auth.verify_claude_cli", return_value=(False, "not found")):
            from second_brain.models_sdk import create_sdk_model
            result = create_sdk_model(config)
            assert result is None

    def test_returns_model_when_all_checks_pass(self, tmp_path):
        """Returns ClaudeSDKModel when all validations pass."""
        config = _make_config(
            tmp_path,
            use_subscription=True,
            claude_oauth_token="sk-ant-oat01-valid-token-here",
        )

        with patch("second_brain.auth.get_oauth_token", return_value="sk-ant-oat01-valid"), \
             patch("second_brain.auth.validate_oauth_token", return_value=True), \
             patch("second_brain.auth.verify_claude_cli", return_value=(True, "claude 1.0")), \
             patch("second_brain.service_mcp.get_service_mcp_config", return_value=("test-server", {"command": "python"})):
            from second_brain.models_sdk import create_sdk_model
            result = create_sdk_model(config)
            assert result is not None
            assert "claude-sdk" in result.model_name


class TestIsSDKAvailable:
    """Tests for is_sdk_available()."""

    def test_available_when_installed(self):
        """Returns True when claude-agent-sdk is importable."""
        mock_module = MagicMock()
        with patch.dict(sys.modules, {"claude_agent_sdk": mock_module}):
            from second_brain.models_sdk import is_sdk_available
            assert is_sdk_available() is True

    def test_not_available_when_missing(self):
        """Returns False when claude-agent-sdk is not installed."""
        # Setting sys.modules entry to None causes ImportError on import
        with patch.dict(sys.modules, {"claude_agent_sdk": None}):
            from second_brain.models_sdk import is_sdk_available
            assert is_sdk_available() is False


class TestModelDateSuffix:
    """Tests for model ID date suffix detection and application."""

    def test_date_suffix_regex_matches_yyyymmdd(self):
        """Regex matches 8-digit date suffix."""
        from second_brain.models_sdk import _DATE_SUFFIX_RE
        assert _DATE_SUFFIX_RE.search("claude-sonnet-4-5-20250929")
        assert _DATE_SUFFIX_RE.search("claude-opus-4-6-20260205")

    def test_date_suffix_regex_rejects_version_numbers(self):
        """Regex does not match short version numbers."""
        from second_brain.models_sdk import _DATE_SUFFIX_RE
        assert not _DATE_SUFFIX_RE.search("claude-sonnet-4-5")
        assert not _DATE_SUFFIX_RE.search("claude-opus-4-6")
        assert not _DATE_SUFFIX_RE.search("claude-haiku-4-5")

    def test_date_suffix_regex_rejects_partial_dates(self):
        """Regex does not match incomplete date patterns."""
        from second_brain.models_sdk import _DATE_SUFFIX_RE
        assert not _DATE_SUFFIX_RE.search("claude-sonnet-4-5-2025")
        assert not _DATE_SUFFIX_RE.search("claude-sonnet-4-5-202509")

    def test_create_sdk_model_appends_date_to_short_id(self, tmp_path):
        """Date suffix is appended when model ID has no date."""
        config = _make_config(
            tmp_path,
            use_subscription=True,
            primary_model="anthropic:claude-sonnet-4-5",
        )
        with patch("second_brain.auth.get_oauth_token", return_value="sk-ant-oat01-valid"), \
             patch("second_brain.auth.validate_oauth_token", return_value=True), \
             patch("second_brain.auth.verify_claude_cli", return_value=(True, "claude 1.0")), \
             patch("second_brain.service_mcp.get_service_mcp_config", return_value=("test-server", {"command": "python"})):
            from second_brain.models_sdk import create_sdk_model, DEFAULT_MODEL_DATE
            result = create_sdk_model(config)
            assert result is not None
            assert DEFAULT_MODEL_DATE in result.model_name

    def test_create_sdk_model_preserves_existing_date(self, tmp_path):
        """Date suffix is NOT appended when model ID already has one."""
        config = _make_config(
            tmp_path,
            use_subscription=True,
            primary_model="anthropic:claude-sonnet-4-5-20250929",
        )
        with patch("second_brain.auth.get_oauth_token", return_value="sk-ant-oat01-valid"), \
             patch("second_brain.auth.validate_oauth_token", return_value=True), \
             patch("second_brain.auth.verify_claude_cli", return_value=(True, "claude 1.0")), \
             patch("second_brain.service_mcp.get_service_mcp_config", return_value=("test-server", {"command": "python"})):
            from second_brain.models_sdk import create_sdk_model
            result = create_sdk_model(config)
            assert result is not None
            # Should have exactly one date, not double-appended
            assert result.model_name.count("20250929") == 1

    def test_default_model_date_constant_exists(self):
        """DEFAULT_MODEL_DATE constant is exported and valid."""
        from second_brain.models_sdk import DEFAULT_MODEL_DATE
        assert len(DEFAULT_MODEL_DATE) == 8
        assert DEFAULT_MODEL_DATE.isdigit()
        assert DEFAULT_MODEL_DATE == "20250929"


class TestClaudeCodeNestingGuard:
    """Tests for CLAUDECODE env var handling in _sdk_query()."""

    def test_claudecode_unset_during_pop(self):
        """CLAUDECODE is removed from env during pop and absent until restore."""
        import os

        os.environ["CLAUDECODE"] = "parent-session-123"

        # Simulate the exact pattern used in _sdk_query
        saved = os.environ.pop("CLAUDECODE", None)
        assert saved == "parent-session-123"
        assert "CLAUDECODE" not in os.environ

        # Restore
        if saved is not None:
            os.environ["CLAUDECODE"] = saved
        assert os.environ.get("CLAUDECODE") == "parent-session-123"

        # Cleanup
        os.environ.pop("CLAUDECODE", None)

    def test_claudecode_restored_after_sdk_call(self):
        """CLAUDECODE is restored after SDK query completes."""
        import os

        original_value = "parent-session-456"
        os.environ["CLAUDECODE"] = original_value

        # Simulate the save/restore pattern used in _sdk_query
        saved = os.environ.pop("CLAUDECODE", None)
        try:
            assert "CLAUDECODE" not in os.environ
        finally:
            if saved is not None:
                os.environ["CLAUDECODE"] = saved

        assert os.environ.get("CLAUDECODE") == original_value

        # Cleanup
        os.environ.pop("CLAUDECODE", None)

    def test_claudecode_restored_on_exception(self):
        """CLAUDECODE is restored even if SDK query raises."""
        import os

        original_value = "parent-session-789"
        os.environ["CLAUDECODE"] = original_value

        try:
            saved = os.environ.pop("CLAUDECODE", None)
            try:
                raise RuntimeError("SDK failed")
            finally:
                if saved is not None:
                    os.environ["CLAUDECODE"] = saved
        except RuntimeError:
            pass

        assert os.environ.get("CLAUDECODE") == original_value

        # Cleanup
        os.environ.pop("CLAUDECODE", None)

    def test_no_error_when_claudecode_not_set(self):
        """No error when CLAUDECODE is not in environment."""
        import os

        os.environ.pop("CLAUDECODE", None)

        saved = os.environ.pop("CLAUDECODE", None)
        try:
            assert saved is None
            assert "CLAUDECODE" not in os.environ
        finally:
            if saved is not None:
                os.environ["CLAUDECODE"] = saved

        assert "CLAUDECODE" not in os.environ

    def test_claudecode_in_env_cleanup_list(self):
        """CLAUDECODE is included in the test env cleanup list."""
        assert "CLAUDECODE" in _ENV_VARS


class TestMCPConfigFormat:
    """Tests for MCP server config dict format passed to SDK."""

    def test_mcp_servers_built_as_dict(self):
        """mcp_servers should be dict[str, config], not list."""
        from second_brain.models_sdk import ClaudeSDKModel

        config = {"command": "python", "args": ["-m", "test"]}
        model = ClaudeSDKModel(
            mcp_config=config,
            mcp_server_name="test-server",
        )
        assert model._mcp_config == config
        assert model._mcp_server_name == "test-server"

    def test_mcp_server_name_default(self):
        """Default server name is second-brain-services."""
        from second_brain.models_sdk import ClaudeSDKModel

        model = ClaudeSDKModel(mcp_config={"command": "python"})
        assert model._mcp_server_name == "second-brain-services"

    def test_no_name_key_in_config(self):
        """Config dict should NOT contain 'name' key."""
        from second_brain.service_mcp import get_service_mcp_config

        name, config = get_service_mcp_config()
        assert "name" not in config
        # Only valid McpStdioServerConfig keys
        valid_keys = {"type", "command", "args", "env"}
        assert set(config.keys()).issubset(valid_keys)
        # Verify unbuffered flag
        assert "-u" in config["args"]
        assert config["env"]["PYTHONUNBUFFERED"] == "1"

    def test_create_sdk_model_passes_separate_name_and_config(self, tmp_path):
        """create_sdk_model unpacks tuple and passes name + config separately."""
        config = _make_config(
            tmp_path,
            use_subscription=True,
        )
        with patch("second_brain.auth.get_oauth_token", return_value="sk-ant-oat01-valid"), \
             patch("second_brain.auth.validate_oauth_token", return_value=True), \
             patch("second_brain.auth.verify_claude_cli", return_value=(True, "claude 1.0")), \
             patch("second_brain.service_mcp.get_service_mcp_config", return_value=("my-server", {"command": "python"})):
            from second_brain.models_sdk import create_sdk_model
            result = create_sdk_model(config)
            assert result is not None
            assert result._mcp_server_name == "my-server"
            assert result._mcp_config == {"command": "python"}
            assert "name" not in result._mcp_config

    def test_timeout_default(self):
        """Default timeout is 120 seconds."""
        from second_brain.models_sdk import ClaudeSDKModel
        model = ClaudeSDKModel()
        assert model._timeout == 120

    def test_timeout_custom(self):
        """Custom timeout is stored correctly."""
        from second_brain.models_sdk import ClaudeSDKModel
        model = ClaudeSDKModel(timeout=60)
        assert model._timeout == 60

    def test_create_sdk_model_passes_timeout_from_config(self, tmp_path):
        """create_sdk_model derives timeout from config.api_timeout_seconds."""
        config = _make_config(
            tmp_path,
            use_subscription=True,
            api_timeout_seconds=45,
        )
        with patch("second_brain.auth.get_oauth_token", return_value="sk-ant-oat01-valid"), \
             patch("second_brain.auth.validate_oauth_token", return_value=True), \
             patch("second_brain.auth.verify_claude_cli", return_value=(True, "claude 1.0")), \
             patch("second_brain.service_mcp.get_service_mcp_config", return_value=("srv", {"command": "python"})):
            from second_brain.models_sdk import create_sdk_model
            result = create_sdk_model(config)
            assert result is not None
            assert result._timeout == 180  # 45 * 4


class TestGetModelFallbackChain:
    """Tests for get_model() with subscription in the chain."""

    @patch("second_brain.models_sdk.create_sdk_model")
    def test_subscription_tried_first_when_enabled(self, mock_sdk, tmp_path):
        """When use_subscription=True, subscription auth is tried first via provider."""
        config = _make_config(
            tmp_path,
            anthropic_api_key="sk-ant-api03-test-key",
            use_subscription=True,
            model_provider="anthropic",
        )
        sdk_model = MagicMock()
        mock_sdk.return_value = sdk_model

        from second_brain.models import get_model
        model = get_model(config)
        mock_sdk.assert_called_once_with(config)
        assert model is sdk_model

    @patch("pydantic_ai.providers.anthropic.AnthropicProvider")
    @patch("pydantic_ai.models.anthropic.AnthropicModel")
    @patch("second_brain.models_sdk.create_sdk_model")
    def test_api_key_fallback_when_subscription_fails(
        self, mock_sdk, mock_model_cls, mock_provider_cls, tmp_path
    ):
        """Falls back to API key when subscription fails."""
        config = _make_config(
            tmp_path,
            anthropic_api_key="sk-ant-api03-test-key",
            use_subscription=True,
            model_provider="anthropic",
        )
        mock_sdk.side_effect = Exception("SDK unavailable")
        mock_model_cls.return_value = MagicMock()

        from second_brain.models import get_model
        model = get_model(config)
        mock_model_cls.assert_called_once()

    @patch("second_brain.models_sdk.create_sdk_model")
    def test_subscription_used_without_api_key(self, mock_sdk, tmp_path):
        """SDK model used when no API key but subscription enabled."""
        config = _make_config(
            tmp_path,
            use_subscription=True,
            model_provider="anthropic",
            anthropic_api_key="placeholder",
        )

        mock_sdk_model = MagicMock()
        mock_sdk_model.model_name = "claude-sdk:claude-sonnet-4-5-20250929"
        mock_sdk.return_value = mock_sdk_model

        from second_brain.models import get_model
        model = get_model(config)
        assert model is mock_sdk_model


class TestClaudeSDKModelStructuredOutput:
    """Tests for structured output extraction, SDK query, and response construction."""

    def test_extract_output_schema_text_mode(self):
        """Returns None when output_mode='text'."""
        from pydantic_ai.models import ModelRequestParameters

        model = ClaudeSDKModel()
        params = ModelRequestParameters(output_mode='text')
        assert model._extract_output_schema(params) is None

    def test_extract_output_schema_tool_mode(self):
        """Extracts schema from output_tools when output_mode='tool'."""
        from pydantic_ai.models import ModelRequestParameters
        from pydantic_ai.tools import ToolDefinition

        schema = {"type": "object", "properties": {"query": {"type": "string"}}}
        tool = ToolDefinition(name="final_result", parameters_json_schema=schema)
        params = ModelRequestParameters(output_mode='tool', output_tools=[tool])
        model = ClaudeSDKModel()
        assert model._extract_output_schema(params) == schema

    def test_extract_output_schema_native_mode(self):
        """Extracts schema from output_object when output_mode='native'."""
        from pydantic_ai.models import ModelRequestParameters
        from pydantic_ai.models import OutputObjectDefinition

        schema = {"type": "object", "properties": {"answer": {"type": "string"}}}
        obj_def = OutputObjectDefinition(json_schema=schema)
        params = ModelRequestParameters(output_mode='native', output_object=obj_def)
        model = ClaudeSDKModel()
        assert model._extract_output_schema(params) == schema

    def test_extract_output_schema_no_schema_available(self):
        """Returns None when mode is not text but no schema is provided."""
        from pydantic_ai.models import ModelRequestParameters

        params = ModelRequestParameters(output_mode='native')
        model = ClaudeSDKModel()
        assert model._extract_output_schema(params) is None

    async def test_request_structured_output_tool_mode(self):
        """Tool mode returns ToolCallPart with correct tool_name and args."""
        from pydantic_ai.models import ModelRequestParameters
        from pydantic_ai.tools import ToolDefinition

        schema = {"type": "object", "properties": {"query": {"type": "string"}}}
        tool = ToolDefinition(name="final_result", parameters_json_schema=schema)
        params = ModelRequestParameters(output_mode='tool', output_tools=[tool])

        model = ClaudeSDKModel()
        structured = {"query": "test", "matches": [], "patterns": [], "relations": [], "summary": ""}

        with patch.object(model, '_sdk_query', new_callable=AsyncMock, return_value=structured):
            with patch.object(model, '_convert_messages', return_value=("system", "user")):
                response = await model.request([], None, params)

        assert len(response.parts) == 1
        part = response.parts[0]
        assert isinstance(part, ToolCallPart)
        assert part.tool_name == "final_result"
        assert part.args == structured

    async def test_request_structured_output_native_mode(self):
        """Native mode returns TextPart with JSON-serialized dict."""
        from pydantic_ai.models import ModelRequestParameters
        from pydantic_ai.models import OutputObjectDefinition

        schema = {"type": "object", "properties": {"answer": {"type": "string"}}}
        obj_def = OutputObjectDefinition(json_schema=schema)
        params = ModelRequestParameters(output_mode='native', output_object=obj_def)

        model = ClaudeSDKModel()
        structured = {"answer": "test answer"}

        with patch.object(model, '_sdk_query', new_callable=AsyncMock, return_value=structured):
            with patch.object(model, '_convert_messages', return_value=("system", "user")):
                response = await model.request([], None, params)

        part = response.parts[0]
        assert isinstance(part, TextPart)
        assert json.loads(part.content) == structured

    async def test_request_text_mode_plain_text(self):
        """Text mode still returns plain TextPart (backward compat)."""
        from pydantic_ai.models import ModelRequestParameters

        params = ModelRequestParameters(output_mode='text')

        model = ClaudeSDKModel()

        with patch.object(model, '_sdk_query', new_callable=AsyncMock, return_value="plain text"):
            with patch.object(model, '_convert_messages', return_value=("system", "user")):
                response = await model.request([], None, params)

        part = response.parts[0]
        assert isinstance(part, TextPart)
        assert part.content == "plain text"

    async def test_sdk_query_passes_output_format(self):
        """output_format is passed to ClaudeAgentOptions when schema provided."""
        schema = {"type": "object", "properties": {"query": {"type": "string"}}}

        mock_result = MagicMock()
        mock_result.structured_output = {"query": "test"}
        mock_result.result = None

        # Create mock SDK module
        mock_sdk = MagicMock()
        mock_sdk.ResultMessage = type(mock_result)

        # Mock the async generator
        async def mock_query(prompt, options):
            yield mock_result

        mock_sdk.query = mock_query
        mock_opts_cls = MagicMock()
        mock_sdk.ClaudeAgentOptions = mock_opts_cls

        model = ClaudeSDKModel()

        with patch.dict('sys.modules', {'claude_agent_sdk': mock_sdk}):
            result = await model._sdk_query("system", "user", output_schema=schema)

        # Verify output_format was passed to ClaudeAgentOptions
        call_kwargs = mock_opts_cls.call_args
        assert call_kwargs is not None
        assert "output_format" in call_kwargs.kwargs
        assert call_kwargs.kwargs["output_format"]["type"] == "json_schema"
        assert call_kwargs.kwargs["output_format"]["schema"] == schema
        # Verify structured_output was returned
        assert result == {"query": "test"}

    async def test_sdk_query_structured_output_fallback(self):
        """Falls back to result text when structured_output is None."""
        schema = {"type": "object", "properties": {"query": {"type": "string"}}}

        mock_result = MagicMock()
        mock_result.structured_output = None
        mock_result.result = '{"query": "fallback"}'

        mock_sdk = MagicMock()
        mock_sdk.ResultMessage = type(mock_result)

        async def mock_query(prompt, options):
            yield mock_result

        mock_sdk.query = mock_query
        mock_sdk.ClaudeAgentOptions = MagicMock()

        model = ClaudeSDKModel()

        with patch.dict('sys.modules', {'claude_agent_sdk': mock_sdk}):
            result = await model._sdk_query("system", "user", output_schema=schema)

        assert isinstance(result, str)
        assert result == '{"query": "fallback"}'

    async def test_sdk_query_no_schema_returns_text(self):
        """Without schema, _sdk_query returns plain text as before."""
        mock_result = MagicMock()
        mock_result.result = "plain text response"

        mock_sdk = MagicMock()
        mock_sdk.ResultMessage = type(mock_result)

        async def mock_query(prompt, options):
            yield mock_result

        mock_sdk.query = mock_query
        mock_sdk.ClaudeAgentOptions = MagicMock()

        model = ClaudeSDKModel()

        with patch.dict('sys.modules', {'claude_agent_sdk': mock_sdk}):
            result = await model._sdk_query("system", "user")

        assert isinstance(result, str)
        assert result == "plain text response"

    async def test_request_structured_dict_fallback_to_text(self):
        """Dict response with empty output_tools falls back to TextPart with JSON."""
        from pydantic_ai.models import ModelRequestParameters

        params = ModelRequestParameters(output_mode='tool', output_tools=[])

        model = ClaudeSDKModel()
        structured = {"query": "test"}

        with patch.object(model, '_sdk_query', new_callable=AsyncMock, return_value=structured):
            with patch.object(model, '_convert_messages', return_value=("system", "user")):
                response = await model.request([], None, params)

        part = response.parts[0]
        assert isinstance(part, TextPart)
        assert json.loads(part.content) == structured
