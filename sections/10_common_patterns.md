## Common Patterns

### 1. Adding a New Agent

Create `backend/src/second_brain/agents/{name}.py`:
```python
from pydantic_ai import Agent, ModelRetry, RunContext
from second_brain.agents.utils import tool_error
from second_brain.deps import BrainDeps
from second_brain.schemas import YourOutputSchema

your_agent = Agent(
    deps_type=BrainDeps,
    output_type=YourOutputSchema,
    retries=3,
    instructions="Agent purpose and constraints.",
)

@your_agent.output_validator
async def validate_output(ctx: RunContext[BrainDeps], output: YourOutputSchema) -> YourOutputSchema:
    if not output.required_field:
        raise ModelRetry("Required field missing. Please provide it.")
    return output

@your_agent.tool
async def do_something(ctx: RunContext[BrainDeps], param: str) -> str:
    try:
        result = await ctx.deps.storage_service.some_method(param)
        return str(result)
    except Exception as e:
        return tool_error("do_something", e)
```

Then expose it in `mcp_server.py` with `@server.tool()` wrapping input validation, timeout, and output formatting.

### 2. Adding a New Pydantic Schema

Add to `backend/src/second_brain/schemas.py` only. Never import from other app modules:
```python
class YourResult(BaseModel):
    """Output from YourAgent."""
    field: str = Field(description="What this field contains")
    items: list[str] = Field(default_factory=list, description="Optional list")
    confidence: ConfidenceLevel = Field(default="MEDIUM")
```

### 3. Adding a New Service Method

Add to the appropriate service class in `backend/src/second_brain/services/storage.py` or `memory.py`:
```python
async def get_something(self, filter: str | None = None) -> list[dict]:
    query = self._client.table("table_name").select("*")
    if filter:
        query = query.eq("column", filter)
    result = await asyncio.to_thread(query.execute)
    return result.data or []
```

### 4. Lazy-Import Pattern (in mcp_server.py)
Import agents inside the tool function body (not at module top) when they are not in the startup group:
```python
@server.tool()
async def my_tool(input: str) -> str:
    from second_brain.agents.my_agent import my_agent  # lazy import
    ...
```
Core agents (recall, ask, learn, create, review) are imported at module top. Others use lazy imports.
