### Agent Definition
```python
from pydantic_ai import Agent, RunContext
from second_brain.deps import BrainDeps
from second_brain.schemas import RecallResult

recall_agent = Agent(
    "anthropic:claude-sonnet-4-5",
    deps_type=BrainDeps,
    output_type=RecallResult,
    instructions="You are a memory recall agent...",
)

@recall_agent.tool
async def search_memory(ctx: RunContext[BrainDeps], query: str) -> str:
    results = await ctx.deps.memory_service.search(query)
    return "\n".join(f"- {r['memory']}" for r in results)
```

### Service Wrapper
```python
class StorageService:
    def __init__(self, config: BrainConfig):
        self._client = create_client(config.supabase_url, config.supabase_key)

    async def get_patterns(self, topic: str | None = None) -> list[dict]:
        query = self._client.table("patterns").select("*")
        if topic:
            query = query.eq("topic", topic)
        return query.order("date_updated", desc=True).execute().data
```

### LLM Fallback Chain
```python
model = get_model(config)  # Tries Anthropic → Ollama
result = await agent.run(prompt, deps=deps, model=model)  # Override at runtime
```

### Dependency Injection
All agents receive `BrainDeps` via `RunContext`. Create once, pass everywhere:
```python
deps = BrainDeps(config=config, memory_service=MemoryService(config),
                 storage_service=StorageService(config))
result = await agent.run(prompt, deps=deps)
```
