## Code Style

**Naming**:
- `snake_case` — all functions, variables, module names, agent instances
- `PascalCase` — Pydantic model classes (`RecallResult`, `BrainDeps`, `ContentTypeConfig`)
- `UPPER_SNAKE_CASE` — module-level constants (`REVIEW_DIMENSIONS`, `MAX_INPUT_LENGTH`)
- `kebab-case` — content type slugs as strings (`"landing-page"`, `"case-study"`)

**Agent Definition Pattern** (one agent per file):
```python
agent_name = Agent(
    deps_type=BrainDeps,
    output_type=OutputSchema,
    retries=3,
    instructions="...",
)

@agent_name.output_validator
async def validate_output(ctx: RunContext[BrainDeps], output: OutputSchema) -> OutputSchema:
    if not output.field:
        raise ModelRetry("Retry message with alternatives")
    return output

@agent_name.tool
async def tool_name(ctx: RunContext[BrainDeps], param: str) -> str:
    try:
        result = await ctx.deps.some_service.some_method(param)
        return format_result(result)
    except Exception as e:
        return tool_error("tool_name", e)
```

**MCP Tool Pattern** (in `mcp_server.py`):
```python
@server.tool()
async def tool_name(input: str) -> str:
    try:
        input = _validate_mcp_input(input, label="input")
    except ValueError as e:
        return str(e)
    deps = _get_deps()
    model = _get_model()
    timeout = deps.config.api_timeout_seconds
    try:
        async with asyncio.timeout(timeout):
            result = await some_agent.run(input, deps=deps, model=model)
    except TimeoutError:
        return f"Tool timed out after {timeout}s."
    return format_output(result.output)
```

**Error Handling**:
- MCP layer: catch `ValueError` and `TimeoutError` → return plain string
- Agent tools: blanket `except Exception as e` → `return tool_error("name", e)`
- Output validation: `raise ModelRetry(message)` to force agent retry

**Schemas**: All Pydantic models live in `schemas.py`. No imports from other app modules in that file.

**Logging**: `logger = logging.getLogger(__name__)` in every module. Use `logger.debug()` for non-critical paths, `logger.error()` for initialization failures.
