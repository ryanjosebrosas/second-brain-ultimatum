## Backend Tech Stack

**Language**: Python >= 3.11
**Agent Framework**: Pydantic AI (`pydantic-ai[anthropic]`) — structured output agents with tool use
**MCP Server**: FastMCP — exposes agents as tools to Claude Code
**Memory**: Mem0 (`mem0ai`) — semantic memory with embedding search
**Database**: Supabase (PostgreSQL + pgvector) — structured storage, vector search, RLS
**Embeddings**: Voyage AI (`voyageai`) — primary; OpenAI fallback
**Knowledge Graph**: Graphiti (`graphiti-core[anthropic,falkordb]`) — optional, feature-flagged
**CLI**: Click — `brain` entrypoint maps to `second_brain.cli:cli`
**Retries**: Tenacity — retry decorator for transient failures
**Config**: Pydantic Settings (`pydantic-settings`) — `.env` loaded via `BrainConfig`

**Optional Extras** (install with `pip install -e '.[extra]'`):
- `graphiti` — knowledge graph support
- `subscription` — `claude-agent-sdk` for Claude subscription auth
- `ollama` — local model support via Pydantic AI

**AI Model**: Claude (Anthropic) via `pydantic-ai[anthropic]`; Ollama for local dev
**Testing**: pytest + pytest-asyncio (asyncio_mode = "auto")
**Package Manager**: pip + setuptools/wheel (no pyproject scripts for lint/format)
**Entry Point**: `brain` CLI command
