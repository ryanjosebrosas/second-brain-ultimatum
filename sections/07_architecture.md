## Backend Architecture

**Pattern**: MCP Server / REST API → Agent Layer → Service Layer → Storage

```
backend/
  src/second_brain/
    mcp_server.py          # Public surface: @server.tool() functions (FastMCP)
    service_mcp.py         # Service bridge (supplemental routing)
    cli.py                 # Click CLI entrypoint ("brain" command)
    deps.py                # BrainDeps dataclass + create_deps() factory
    config.py              # BrainConfig (Pydantic Settings, loads .env)
    schemas.py             # All Pydantic output models — NO imports from other app modules
    models.py              # Model factory (provider registry + fallback chains)
    models_sdk.py          # Claude SDK model support (subscription auth)
    auth.py                # Authentication helpers
    migrate.py             # Data migration utilities
    providers/
      __init__.py          # BaseProvider ABC + PROVIDER_REGISTRY
      anthropic.py         # Anthropic Claude provider (API key + subscription)
      ollama.py            # Ollama local + cloud providers
      openai.py            # OpenAI GPT provider
      groq.py              # Groq fast inference provider
    api/
      main.py              # FastAPI app entry point
      deps.py              # API dependency injection
      routers/
        agents.py          # Agent invocation endpoints
        graph.py           # Knowledge graph endpoints
        health.py          # Health check endpoints
        memory.py          # Memory CRUD endpoints
        projects.py        # Project lifecycle endpoints
        settings.py        # Settings management endpoints
    agents/
      recall.py            # Semantic memory search
      ask.py               # General Q&A with brain context
      learn.py             # Pattern extraction + memory storage
      create.py            # Content generation (voice-aware)
      review.py            # Multi-dimension content scoring
      chief_of_staff.py    # Routing orchestrator (picks agent/pipeline)
      coach.py             # Daily accountability coaching
      pmo.py               # PMO-style task prioritization
      email_agent.py       # Email composition
      specialist.py        # Claude Code / Pydantic AI Q&A
      clarity.py           # Readability analysis
      synthesizer.py       # Feedback consolidation
      template_builder.py  # Template opportunity detection
      utils.py             # Shared: tool_error(), run_pipeline(), format_*()
    services/
      memory.py            # Mem0 semantic memory wrapper
      storage.py           # Supabase CRUD + ContentTypeRegistry
      embeddings.py        # Voyage AI / OpenAI embedding generation
      voyage.py            # Voyage AI reranking
      graphiti.py          # Knowledge graph (optional)
      graphiti_memory.py   # Graphiti-backed memory provider (fallback)
      health.py            # Brain metrics + growth milestones
      retry.py             # Tenacity retry helpers
      search_result.py     # Search result data structures
      abstract.py          # Abstract base classes for pluggable services
      __init__.py
  docs/                    # Operational runbooks and integration guides
  supabase/migrations/     # Numbered SQL migrations (001–020)
  tests/                   # One test file per source module
  scripts/                 # Utility scripts (e.g., reingest_graph.py)
  .env                     # Secrets (gitignored)
  .env.example             # Documented env var template
  pyproject.toml           # Dependencies + pytest config
```

**Data Flow**:
MCP tool call → `mcp_server.py` validates input → calls agent with `BrainDeps` → agent uses service layer → Mem0 / Supabase / Voyage → structured output returned → formatted as plain text string
REST request → `api/routers/*.py` → same agent/service layer → JSON response

**Key Constraint**: `schemas.py` must remain dependency-free (no imports from other app modules).
