## Backend Tech Stack

**Language**: Python >= 3.11
**Agent Framework**: Pydantic AI (`pydantic-ai[anthropic]`) — structured output agents with tool use
**MCP Server**: FastMCP — exposes agents as tools to Claude Code
**Memory**: Mem0 (`mem0ai`) — semantic memory with embedding search
**Database**: Supabase (PostgreSQL + pgvector) — structured storage, vector search, RLS
**Embeddings**: Voyage AI (`voyageai`) — primary; OpenAI fallback
**Knowledge Graph**: Graphiti (`graphiti-core[anthropic,falkordb]`) — optional, feature-flagged
**REST API**: FastAPI (`fastapi[standard]`) — HTTP API with routers for agents, memory, projects, graph, health, settings
**HTTP Client**: httpx — async HTTP client
**CLI**: Click — `brain` entrypoint maps to `second_brain.cli:cli`
**Retries**: Tenacity — retry decorator for transient failures
**Config**: Pydantic Settings (`pydantic-settings`) — `.env` loaded via `BrainConfig`

**Optional Extras** (install with `pip install -e '.[extra]'`):
- `graphiti` — knowledge graph support
- `subscription` — `claude-agent-sdk` for Claude subscription auth
- `ollama` — local model support via Pydantic AI

**AI Model**: Provider-agnostic — Claude, Ollama, OpenAI, Groq via provider registry
**Testing**: pytest + pytest-asyncio (asyncio_mode = "auto")
**Package Manager**: pip + setuptools/wheel (no pyproject scripts for lint/format)
**Entry Point**: `brain` CLI command

### LLM Provider Selection

The system uses a **Provider Registry Pattern** for flexible model selection:

**Config** (`.env`):
```bash
MODEL_PROVIDER=anthropic         # Primary provider (auto|anthropic|ollama-local|ollama-cloud|openai|groq)
MODEL_NAME=claude-sonnet-4-5     # Optional model name override
MODEL_FALLBACK_CHAIN=ollama-local  # Optional comma-separated fallback providers
```

**Supported Providers**:
| Provider | Env Vars Required | Default Model |
|----------|------------------|---------------|
| `anthropic` | `ANTHROPIC_API_KEY` | `claude-sonnet-4-5` |
| `ollama-local` | `OLLAMA_BASE_URL` (optional) | `llama3.1:8b` |
| `ollama-cloud` | `OLLAMA_BASE_URL`, `OLLAMA_API_KEY` | `llama3.1:8b` |
| `openai` | `OPENAI_API_KEY` | `gpt-4o` |
| `groq` | `GROQ_API_KEY` | `llama-3.3-70b-versatile` |

**Backward Compatibility**: `MODEL_PROVIDER=auto` (default) infers from available API keys: Anthropic > Ollama Cloud > Ollama Local. Old `.env` files with just `ANTHROPIC_API_KEY` work unchanged.

**Architecture**: `providers/__init__.py` (BaseProvider ABC + registry) → `providers/{name}.py` (one class per provider) → `models.py` (`get_model()` iterates primary + fallback chain).

**Adding a New Provider**: Create `providers/{name}.py` with a class inheriting `BaseProvider`, implement `validate_config()`, `build_model()`, `from_config()`, call `register_provider()` at module bottom, add lazy import in `providers/__init__.py._register_all()`.
