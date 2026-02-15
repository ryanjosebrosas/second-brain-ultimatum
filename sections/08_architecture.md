```
src/second_brain/
├── __init__.py          # Package init, __version__
├── config.py            # BrainConfig (Pydantic Settings, loads .env)
├── models.py            # get_model() — LLM provider factory (Claude → Ollama)
├── deps.py              # BrainDeps dataclass — injected into all agents
├── schemas.py           # Pydantic output models (RecallResult, AskResult)
├── cli.py               # Click CLI entry points
├── mcp_server.py        # FastMCP server for Claude Code integration
├── migrate.py           # Markdown → Mem0 + Supabase migration tool
├── agents/
│   ├── __init__.py      # Agent exports
│   ├── recall.py        # RecallAgent — semantic memory search
│   └── ask.py           # AskAgent — contextual help
└── services/
    ├── __init__.py      # Service exports
    ├── memory.py        # MemoryService — Mem0 wrapper
    └── storage.py       # StorageService — Supabase CRUD
```

### Layers
- **Config** → `config.py` loads env, `models.py` resolves LLM provider
- **Services** → `services/` wraps external backends (Mem0, Supabase)
- **Agents** → `agents/` Pydantic AI agents with typed deps and tools
- **Interfaces** → `cli.py` (Click) and `mcp_server.py` (FastMCP) both call agents

### Data Flow
```
CLI / MCP → Agent.run(deps=BrainDeps) → Agent tools → Services → Mem0 / Supabase
```

### External Data
- Markdown source: `C:\Users\Utopia\Documents\MEGA\Template` (BRAIN_DATA_PATH)
- Supabase schema: `supabase/migrations/001_initial_schema.sql`
