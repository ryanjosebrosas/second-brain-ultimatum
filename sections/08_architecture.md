```
src/second_brain/
├── __init__.py          # Package init, __version__
├── config.py            # BrainConfig (Pydantic Settings, loads .env)
├── models.py            # get_model() — LLM provider factory (Claude → Ollama)
├── deps.py              # BrainDeps dataclass — injected into all agents
├── schemas.py           # Pydantic output models (RecallResult, AskResult, LearnResult, etc.)
├── cli.py               # Click CLI (recall, ask, learn, create, review, health, migrate)
├── mcp_server.py        # FastMCP server for Claude Code integration
├── migrate.py           # Markdown → Mem0 + Supabase migration tool
├── agents/
│   ├── __init__.py      # Agent exports (5 agents)
│   ├── recall.py        # RecallAgent — semantic memory search
│   ├── ask.py           # AskAgent — contextual Q&A with pattern/experience context
│   ├── learn.py         # LearnAgent — pattern extraction, memory consolidation
│   ├── create.py        # CreateAgent — content creation with voice + patterns
│   └── review.py        # ReviewAgent — multi-dimension content review + scoring
└── services/
    ├── __init__.py      # Service exports (lazy GraphitiService import)
    ├── memory.py        # MemoryService — Mem0 wrapper (cloud + local, metadata, graph)
    ├── storage.py       # StorageService — Supabase CRUD + ContentTypeRegistry
    ├── health.py        # HealthService — brain health + growth metrics
    ├── graphiti.py      # GraphitiService — graph memory via Graphiti + Neo4j (optional)
    └── search_result.py # SearchResult dataclass — typed Mem0 search results
```

### Layers
- **Config** → `config.py` loads env, `models.py` resolves LLM provider
- **Services** → `services/` wraps external backends (Mem0, Supabase, Neo4j/Graphiti)
- **Agents** → `agents/` Pydantic AI agents with typed deps and tools
- **Interfaces** → `cli.py` (Click) and `mcp_server.py` (FastMCP) both call agents

### Data Flow
```
CLI / MCP → Agent.run(deps=BrainDeps) → Agent tools → Services → Mem0 / Supabase / Neo4j
```

### External Data
- Markdown source: `C:\Users\Utopia\Documents\MEGA\Template` (BRAIN_DATA_PATH)
- Supabase schema: `supabase/migrations/` (5 migration files)
- Scripts: `scripts/` (reingest_graph.py, cross-cli-setup.sh, start_mcp.sh)
