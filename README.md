# Second Brain

**Persistent AI memory — your agents remember everything.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Tests: 1324 passing](https://img.shields.io/badge/tests-1324_passing-brightgreen.svg)](#tests)
[![MCP Tools: 49](https://img.shields.io/badge/MCP_tools-49-purple.svg)](#mcp-tool-reference)

Your AI forgets everything between sessions. Second Brain fixes that.

13 Pydantic AI agents expose **49 MCP tools** that give Claude (or any MCP client) persistent recall of your decisions, patterns, voice, and priorities — backed by Mem0 semantic memory, Supabase/pgvector hybrid search, and Voyage AI multimodal embeddings. Text, images, PDFs, video — all searchable in one shared vector space.

Three interfaces: **MCP server** for Claude Code, **REST API** (FastAPI, 45+ endpoints) for custom frontends, **CLI** for scripts. Ships with a **Streamlit dashboard** out of the box.

---

## Table of Contents

- [Why This Exists](#why-this-exists)
- [Quickstart](#quickstart)
- [Features](#features)
- [MCP Tool Reference](#mcp-tool-reference)
- [Setup](#setup)
- [Docker](#docker)
- [MCP Integration](#mcp-integration)
- [REST API](#rest-api)
- [CLI](#cli)
- [Architecture](#architecture)
- [Data Flow](#data-flow)
- [Service Layer](#service-layer)
- [Advanced Topics](#advanced-topics)
- [Tests](#tests)
- [Tech Stack](#tech-stack)
- [License](#license)

---

## Why This Exists

Every AI session starts from scratch. You re-explain your architecture, re-describe your preferences, re-establish context — every single time.

**Second Brain gives your AI a brain that persists.** Store decisions, recall patterns, generate content in your voice, score your work, get coached on priorities. Everything survives across sessions via hybrid semantic + keyword search with intelligent reranking.

---

## Quickstart

Get running in 3 steps:

### 1. Configure environment

```bash
cd backend
cp .env.example .env
```

Edit `.env` with your keys:
```bash
ANTHROPIC_API_KEY=sk-...       # Or any LLM provider key (OpenAI, Groq, Ollama)
MEM0_API_KEY=m0-...            # Mem0 cloud memory (or omit for local Qdrant)
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJ...
BRAIN_USER_ID=your-name        # Data isolation identifier
```

### 2. Install and run migrations

```bash
pip install -e ".[dev]"
# Apply all 21 SQL migrations via Supabase dashboard or CLI
# Migrations in: backend/supabase/migrations/ (001–020)
```

### 3. Start

**MCP Server** (for Claude Code):
```bash
python -m second_brain.mcp_server
```

**REST API** (for custom frontends):
```bash
uvicorn second_brain.api.main:app --host 0.0.0.0 --port 8001
```

**Docker** (full stack — MCP + API + Streamlit dashboard):
```bash
docker compose up -d
# MCP: http://localhost:8000  |  API: http://localhost:8001  |  Dashboard: http://localhost:8501
```

All 13 agents and 49 tools are now available. See [MCP Integration](#mcp-integration) for Claude Code/Desktop configuration.

---

## Features

### Memory & Retrieval
- **Complexity-aware recall** — queries auto-route between fast parallel search (~1-2s) and deep agent-driven retrieval (~5-15s) based on query complexity
- **Hybrid search** — combines Mem0 semantic memory, pgvector similarity, and BM25 full-text search with Reciprocal Rank Fusion (RRF)
- **Voyage AI reranking** — results reranked with `rerank-2.5-lite` for precision
- **Multimodal embeddings** — text, images, PDFs, and video indexed in one shared vector space via `voyage-multimodal-3.5`

### Content & Voice
- **Voice-matched content generation** — creates landing pages, case studies, emails in your writing style
- **Multi-dimension quality scoring** — 6 parallel reviewers score content across dimensions
- **Content type system** — built-in and custom content types with templates, voice guides, and examples

### Operations
- **Daily coaching** — Pomodoro-aware accountability coaching
- **PMO task prioritization** — 5-factor weighted scoring (urgency, impact, effort, alignment, momentum)
- **Project lifecycle** — 5-stage project tracking (planning → executing → reviewing → learning → complete)

### Architecture
- **Pluggable LLM providers** — Anthropic, OpenAI, Groq, Ollama (local + cloud) with automatic fallback chains
- **Pluggable memory providers** — Mem0 (cloud), Graphiti/Neo4j (graph), or stub — switch via config
- **Three interfaces** — MCP server, REST API (FastAPI), CLI — all backed by the same agent layer
- **Streamlit dashboard** — 7-page frontend for chat, memory browsing, content creation, settings

---

## MCP Tool Reference

49 tools across 13 agent backends. Tools are grouped by function — use the "When to use" guidance in each tool's description to pick the right one.

### Memory & Recall (6 tools)

| Tool | What it does |
|------|-------------|
| `quick_recall` | Fast parallel search across Mem0 + pgvector (~1-2s). Auto-upgrades complex queries. **Start here for most searches.** |
| `recall` | LLM agent picks the optimal search strategy, can chain searches (~5-15s). For nuanced/ambiguous queries. |
| `recall_deep` | All sources searched concurrently with synthesis (~3-8s). For comprehensive answers. |
| `search_examples` | Browse content examples by type (e.g., "landing-page", "case-study"). |
| `search_knowledge` | Browse knowledge repository by category. |
| `search_experiences` | List past work experiences by category. |

### Search & Data (5 tools)

| Tool | What it does |
|------|-------------|
| `search_patterns` | Query the pattern registry by topic, confidence, keyword. |
| `vector_search` | Direct pgvector similarity search against any table (patterns, examples, knowledge, experiences). |
| `ingest_example` | Add a content example to the library with metadata. |
| `ingest_knowledge` | Add a knowledge entry to the repository. |
| `delete_item` | Delete an item by table and ID. |

### Core Agents (6 tools)

| Tool | What it does |
|------|-------------|
| `ask` | Q&A with full brain context — answers using your stored knowledge, patterns, and experiences. |
| `learn` | Extract patterns and insights from a work session or text. Stores to memory. |
| `create_content` | Generate content (landing pages, emails, case studies) matched to your voice. |
| `review_content` | Multi-dimension quality scoring — 6 parallel reviews covering different aspects. |
| `consolidate_brain` | Run the Chief of Staff to route a request to the right agent or pipeline. |
| `run_brain_pipeline` | Execute a multi-step agent pipeline (e.g., learn → create → review). |

### Graph Memory (7 tools)

| Tool | What it does |
|------|-------------|
| `graph_search` | Search knowledge graph for entity relationships. |
| `graph_health` | Check Graphiti/Neo4j service health and stats. |
| `graph_entity_search` | Find specific entities in the knowledge graph. |
| `graph_entity_context` | Get full context around a known entity. |
| `graph_traverse` | Walk relationships from a starting entity. |
| `graph_communities` | Discover entity clusters and communities. |
| `graph_advanced_search` | Complex graph queries with node/edge type filters and date ranges. |

### Multimodal (4 tools)

| Tool | What it does |
|------|-------------|
| `learn_image` | Analyze and learn from an image (JPEG, PNG, WebP, GIF). |
| `learn_document` | Extract knowledge from a PDF document. |
| `learn_video` | Extract insights from video content. |
| `multimodal_vector_search` | Search across text + image embeddings in one query. |

### Project Lifecycle (9 tools)

| Tool | What it does |
|------|-------------|
| `list_projects` | List all projects with optional lifecycle stage filter. |
| `create_project` | Create a new project with metadata. |
| `project_status` | Get project details including all artifacts. |
| `update_project` | Update project metadata or lifecycle stage. |
| `delete_project` | Delete a project and its artifacts. |
| `advance_project` | Move project to the next lifecycle stage. |
| `add_artifact` | Add an artifact (plan, draft, review, output, note) to a project. |
| `delete_artifact` | Remove an artifact from a project. |
| `pattern_registry` | View the full pattern registry with confidence scores. |

### Operations (5 tools)

| Tool | What it does |
|------|-------------|
| `coaching_session` | Daily accountability coaching with Pomodoro integration. |
| `prioritize_tasks` | PMO-style task prioritization (5-factor weighted scoring). |
| `compose_email` | Compose emails in your brand voice. |
| `ask_claude_specialist` | Claude Code / Pydantic AI domain expert Q&A. |
| `analyze_clarity` | Readability and clarity analysis of text. |

### Content Pipeline (4 tools)

| Tool | What it does |
|------|-------------|
| `synthesize_feedback` | Consolidate review findings into actionable themes. |
| `find_template_opportunities` | Find reusable template opportunities in a deliverable. |
| `brain_health` | Brain metrics — memory count, growth rate, quality trends. |
| `brain_setup` | Check onboarding progress and recommend next steps. |

### Content Types (2 tools)

| Tool | What it does |
|------|-------------|
| `list_content_types` | List all registered content types (built-in and custom). |
| `manage_content_type` | Add or remove a custom content type (built-ins are protected). |

### Growth (1 tool)

| Tool | What it does |
|------|-------------|
| `growth_report` | Generate a growth report showing brain development over time. |

> **Note:** Tool names listed here match exactly what appears in your MCP client. Run `quick_recall` for most searches — it auto-upgrades complex queries to deeper retrieval.

---

## Setup

### 1. Install

```bash
cd backend
pip install -e ".[dev]"              # Core + dev dependencies
pip install -e ".[dev,graphiti]"     # + Graphiti knowledge graph (optional)
pip install -e ".[dev,subscription]" # + Claude subscription auth (optional)
```

### 2. Environment

```bash
cp .env.example .env
```

**Required:**

| Variable | Description |
|----------|-------------|
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_KEY` | Supabase anon/service key |
| `BRAIN_USER_ID` | User identifier for data isolation |
| `BRAIN_DATA_PATH` | Path to your markdown data files |

**LLM Provider** (at least one required):

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL_PROVIDER` | `auto` | `auto`, `anthropic`, `ollama-local`, `ollama-cloud`, `openai`, `groq` |
| `ANTHROPIC_API_KEY` | — | Claude models (default if `auto`) |
| `OPENAI_API_KEY` | — | GPT models; also used by Mem0 for internal embeddings |
| `GROQ_API_KEY` | — | Groq fast inference |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama (local or cloud) |

`MODEL_PROVIDER=auto` detects available keys: Anthropic → Ollama Cloud → Ollama Local.

**Memory** (at least one required):

| Variable | Default | Description |
|----------|---------|-------------|
| `MEM0_API_KEY` | — | Mem0 cloud (primary). Omit for local Qdrant fallback |
| `MEMORY_PROVIDER` | `mem0` | `mem0`, `graphiti`, or `none` |

**Optional:**

| Variable | Default | Description |
|----------|---------|-------------|
| `VOYAGE_API_KEY` | — | Voyage AI embeddings + reranking |
| `BRAIN_API_KEY` | `""` | REST API auth key (empty = no auth) |
| `MCP_TRANSPORT` | `stdio` | `stdio`, `http`, `streamable-http` |
| `GRAPHITI_ENABLED` | `false` | Enable Graphiti knowledge graph |
| `NEO4J_URL` | — | Required if `GRAPH_PROVIDER=graphiti` |
| `MODEL_FALLBACK_CHAIN` | `""` | Comma-separated fallback providers |
| `AGENT_MODEL_OVERRIDES` | `{}` | JSON dict for per-agent model selection |

See `.env.example` for the complete list with descriptions.

### 3. Database Migrations

Apply all 21 migrations via Supabase dashboard or CLI:

```bash
# Migrations in: backend/supabase/migrations/
# Numbered 001 through 020 (019 has two files)
```

Key migrations:
- `001–010`: Core tables (patterns, experiences, examples, knowledge, projects)
- `011–015`: Quality gates, content types, vault support
- `016–018`: User isolation (RLS policies, user_id columns)
- `019`: HNSW vector indexes + GIN tag indexes
- `020`: Hybrid search RPC (BM25 + pgvector fusion)

### 4. Start

```bash
# MCP Server (Claude Code / Desktop)
python -m second_brain.mcp_server

# REST API (custom frontends)
uvicorn second_brain.api.main:app --host 0.0.0.0 --port 8001

# CLI
brain --help
```

---

## Docker

### Full Stack (Backend + Frontend)

```bash
docker compose up -d          # Start everything
docker compose up -d backend  # Backend only (MCP + API)
docker compose up -d frontend # Frontend only
docker compose logs -f        # View logs
docker compose down           # Stop everything
```

| Service | Port | Purpose |
|---------|------|---------|
| `backend` | 8000 | MCP server (HTTP transport) |
| `backend` | 8001 | REST API (FastAPI) |
| `frontend` | 8501 | Streamlit dashboard |

Both containers run as non-root users. Backend uses a multi-stage uv build for fast, reproducible installs. Frontend starts only after backend health check passes.

<details>
<summary>Transport configuration and health checks</summary>

### Transport Configuration

The server supports three transport modes via the `MCP_TRANSPORT` environment variable:

| Transport | `MCP_TRANSPORT=` | Use Case |
|-----------|-----------------|----------|
| **stdio** | `stdio` (default) | Local development — Claude Code spawns as subprocess |
| **HTTP** | `http` | Docker / network — single `/mcp` endpoint, stateless |
| **Streamable HTTP** | `streamable-http` | Alias for `http` (same behavior in FastMCP 2.x) |
| **SSE** | `sse` | Legacy — Server-Sent Events (deprecated by MCP spec 2025-03-26) |

Additional env vars for HTTP/SSE mode:

```bash
MCP_HOST=0.0.0.0   # Bind address (default: 0.0.0.0)
MCP_PORT=8000       # Port (default: 8000, range: 1024-65535)
```

### Health Check

When running in HTTP/SSE mode, a deep health endpoint is available:

```bash
curl http://localhost:8000/health
# Healthy: {"status": "healthy", "service": "second-brain", "initialized": true}
# Unhealthy (503): {"status": "unhealthy", "service": "second-brain", "error": "..."}
```

Docker's `restart: unless-stopped` policy handles automatic recovery when the health check fails.

</details>

---

## MCP Integration

### Local (stdio)

Add to your MCP config (`.mcp.json` or `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "second-brain": {
      "command": "python",
      "args": ["-m", "second_brain.mcp_server"],
      "cwd": "/path/to/repo/backend"
    }
  }
}
```

Works with Claude Code, Cursor, Windsurf, and any other MCP-compatible client.

### Docker (HTTP) — Claude Code

```bash
claude mcp add --transport http second-brain http://localhost:8000/mcp
```

Or add to `.mcp.json`:

```json
{
  "mcpServers": {
    "second-brain": {
      "type": "http",
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

### Docker (HTTP) — Claude Desktop

Claude Desktop requires the `mcp-remote` proxy to connect to HTTP MCP servers:

```json
{
  "mcpServers": {
    "second-brain": {
      "command": "npx",
      "args": ["mcp-remote", "http://localhost:8000/mcp"]
    }
  }
}
```

### Usage Examples

Once connected, all 49 tools are available naturally:

```
Use quick_recall to find everything I know about authentication patterns.

Learn this pattern from my code: [paste code]

Create a LinkedIn post in my voice about shipping this feature.

Review this draft and score it across all dimensions.

Coach me — what should I be focused on today?
```

Manage projects and knowledge:

```
List all my active projects.

Update project "auth-system" — mark it as shipped.

Search patterns — find everything I've learned about rate limiting.

Ingest this example into my brain: [paste code or content]
```

Multimodal content:

```
Learn this image — it's my app's architecture diagram: [image URL]

Learn this PDF — it's the Supabase RLS guide: [PDF URL]

Search across all my stored content (text + images) for "authentication flow".
```

---

## REST API

FastAPI server with 45+ endpoints. Start with:

```bash
uvicorn second_brain.api.main:app --host 0.0.0.0 --port 8001
```

Auth: Set `BRAIN_API_KEY` in `.env`. Pass as `X-API-Key` header. Empty = no auth required.

### Endpoints

| Group | Path | Methods | Description |
|-------|------|---------|-------------|
| Health | `/api/health/*` | GET | Metrics, growth, milestones, quality, setup status (no auth) |
| Agents | `/api/recall`, `/api/ask`, `/api/learn`, etc. | POST | All 13 agents as REST endpoints |
| Memory | `/api/search/*`, `/api/ingest/*` | GET/POST | Search examples, knowledge, patterns, experiences; ingest content |
| Projects | `/api/projects/*` | CRUD | Project lifecycle management with artifacts |
| Graph | `/api/graph/*` | GET/POST | Knowledge graph search and health |
| Settings | `/api/settings/*` | GET | Active config and provider info |
| Content Types | `/api/content-types` | GET/POST | Manage content type registry |
| Items | `/api/items/{table}/{id}` | DELETE | Delete items by table and ID |

Interactive docs at `http://localhost:8001/docs` (Swagger UI).

---

## CLI

```bash
brain --help            # Show available commands
brain migrate           # Run data migration
brain health            # Check brain health
```

---

## Architecture

```mermaid
graph TB
    subgraph CLIENTS["Three Interfaces"]
        MCP["MCP Server<br/>Claude Code / Desktop"]
        API["REST API<br/>FastAPI (45+ endpoints)"]
        CLI["CLI<br/>Click"]
    end

    subgraph AGENTS["Agent Layer<br/>13 Pydantic AI agents → 49 MCP tools"]
        MEMORY["Memory<br/>recall · quick_recall · recall_deep · learn"]
        CONTENT["Content<br/>create · review · clarity · synthesize"]
        OPS["Operations<br/>coach · pmo · email · specialist"]
        ROUTING["Routing<br/>chief_of_staff · pipeline"]
    end

    subgraph SERVICES["Service Layer"]
        MEM0["Mem0<br/>Semantic memory"]
        SUPA["Supabase<br/>pgvector + hybrid search"]
        VOYAGE["Voyage AI<br/>Embeddings + reranking"]
        GRAPHITI["Graphiti<br/>Knowledge graph (optional)"]
    end

    CLIENTS --> AGENTS
    AGENTS --> SERVICES
```

```
backend/src/second_brain/
├── mcp_server.py          # 49 MCP tools (FastMCP 2.x)
├── api/                   # REST API (FastAPI)
│   ├── main.py            # App factory, middleware, CORS
│   └── routers/           # 6 route modules (agents, memory, projects, graph, health, settings)
├── agents/                # 13 Pydantic AI agents (one per file)
│   ├── recall.py          # Complexity-aware recall with hybrid search
│   ├── ask.py, learn.py   # Core knowledge agents
│   ├── create.py          # Voice-matched content generation
│   ├── review.py          # Multi-dimension scoring
│   ├── chief_of_staff.py  # Routing orchestrator
│   └── ...                # coach, pmo, email, specialist, clarity, synthesizer, template_builder
├── services/              # External service wrappers
│   ├── memory.py          # Mem0 semantic memory (retry + timeout hardened)
│   ├── storage.py         # Supabase CRUD + hybrid search + ContentTypeRegistry
│   ├── embeddings.py      # Voyage AI embedding generation
│   ├── voyage.py          # Voyage AI reranking
│   ├── graphiti.py        # Neo4j knowledge graph (optional)
│   ├── graphiti_memory.py # Graphiti ↔ MemoryServiceBase adapter
│   └── abstract.py        # MemoryServiceBase ABC (14 methods)
├── providers/             # LLM provider registry
│   ├── __init__.py        # BaseProvider ABC + PROVIDER_REGISTRY
│   └── anthropic.py, ollama.py, openai.py, groq.py
├── config.py              # BrainConfig (Pydantic Settings)
├── schemas.py             # All Pydantic output models
├── deps.py                # BrainDeps + create_deps() factory
└── models.py              # Model factory (provider + fallback chains)
```

---

## Data Flow

### Learn → Store → Recall

```mermaid
sequenceDiagram
    participant U as User
    participant M as MCP Server
    participant A as Agent
    participant Mem as Mem0
    participant S as Supabase
    participant V as Voyage AI

    U->>M: learn("Today I built auth with JWT...")
    M->>A: learn_agent.run(input, deps)
    A->>Mem: memory.add(patterns, user_id)
    A->>S: storage.upsert_patterns(extracted)
    A->>V: embeddings.embed(patterns)
    V-->>S: store vectors
    A-->>M: LearnResult(patterns, insights)
    M-->>U: "Learned 3 patterns, 2 insights"

    U->>M: quick_recall("JWT auth patterns")
    M->>A: classify_query_complexity(query)
    par Parallel Search
        A->>Mem: memory.search(query)
        A->>S: hybrid_search(semantic + BM25)
    end
    A->>V: rerank(combined_results)
    V-->>A: reranked matches
    A-->>M: RecallResult(matches, sources)
    M-->>U: "Found 5 matches (Mem0: 3, pgvector: 2)"
```

### Error Handling

Three-tier error handling ensures agents never crash — they degrade gracefully:

```mermaid
graph TD
    MCP["MCP Layer<br/>mcp_server.py"] -->|"catches"| VE["ValueError<br/>→ return plain string"]
    MCP -->|"catches"| TE["TimeoutError<br/>→ return timeout message"]

    AGENT["Agent Tools<br/>@agent.tool"] -->|"catches"| EX["Exception<br/>→ tool_error('name', e)"]

    OUTPUT["Output Validation<br/>@agent.output_validator"] -->|"raises"| MR["ModelRetry(message)<br/>→ agent retries with guidance"]

    SVC["Service Layer"] -->|"logs + returns"| FB["empty fallback<br/>[] or {}"]

    style MCP fill:#8e44ad,color:#fff
    style AGENT fill:#4a90d9,color:#fff
    style OUTPUT fill:#e67e22,color:#fff
    style SVC fill:#27ae60,color:#fff
    style VE fill:#e74c3c,color:#fff
    style TE fill:#e74c3c,color:#fff
    style EX fill:#e74c3c,color:#fff
    style MR fill:#f39c12,color:#fff
    style FB fill:#95a5a6,color:#fff
```

---

## Service Layer

Agents never talk to databases directly. External systems do the heavy lifting through a clean service abstraction — swappable at runtime via `MEMORY_PROVIDER`.

```mermaid
graph TD
    subgraph "Service Layer"
        MS["memory.py<br/>Mem0 wrapper"]
        SS["storage.py<br/>Supabase CRUD + hybrid search"]
        ES["embeddings.py<br/>Voyage AI / OpenAI"]
        VS["voyage.py<br/>Voyage AI reranking"]
        GS["graphiti.py<br/>Knowledge graph (optional)"]
        HS["health.py<br/>Metrics + growth milestones"]
    end

    subgraph "External Systems"
        MEM0[("Mem0<br/>Semantic memory store")]
        SB[("Supabase<br/>PostgreSQL + pgvector")]
        VAI[("Voyage AI<br/>voyage-multimodal-3.5")]
        FK[("FalkorDB<br/>Graph database")]
    end

    MS <--> MEM0
    SS <--> SB
    ES <--> VAI
    VS <--> VAI
    GS <--> FK

    style MS fill:#4a90d9,color:#fff
    style SS fill:#4a90d9,color:#fff
    style ES fill:#4a90d9,color:#fff
    style VS fill:#4a90d9,color:#fff
    style GS fill:#95a5a6,color:#fff
    style HS fill:#4a90d9,color:#fff
    style MEM0 fill:#e74c3c,color:#fff
    style SB fill:#e74c3c,color:#fff
    style VAI fill:#e74c3c,color:#fff
    style FK fill:#95a5a6,color:#fff
```

| Service | Purpose |
|---------|---------|
| `memory.py` | Mem0 wrapper — add, search, and retrieve semantic memories. Retry/timeout hardened via Tenacity. Supports multimodal content |
| `storage.py` | Supabase wrapper — CRUD for all structured data, hybrid search (BM25 + pgvector), `ContentTypeRegistry` for content type configs |
| `embeddings.py` | Embedding generation via Voyage AI (primary) or OpenAI (fallback). Supports multimodal inputs via `embed_multimodal()` |
| `voyage.py` | Voyage AI reranking + multimodal embeddings — `voyage-multimodal-3.5` embeds text, images, and video into a shared 1024-dim vector space |
| `graphiti.py` | Knowledge graph via Graphiti + FalkorDB — entity and relationship extraction (optional) |
| `graphiti_memory.py` | Adapts Graphiti to the `MemoryServiceBase` interface — complete drop-in replacement for Mem0, all 14 methods implemented |
| `health.py` | Brain metrics, growth milestones, and system health checks |
| `retry.py` | Tenacity retry decorators for transient failures |
| `search_result.py` | Shared data structures for search results across all retrieval methods |
| `abstract.py` | Abstract base classes (`MemoryServiceBase`, etc.) for pluggable service implementations + stub services for testing |

---

## Advanced Topics

### Pluggable Memory Providers

| Provider | Backend | Config |
|----------|---------|--------|
| `mem0` (default) | Mem0 Cloud / local Qdrant | `MEMORY_PROVIDER=mem0` + `MEM0_API_KEY` |
| `graphiti` | Neo4j knowledge graph | `MEMORY_PROVIDER=graphiti` + Neo4j vars |
| `none` | Stub (no memory) | `MEMORY_PROVIDER=none` |

All providers implement `MemoryServiceBase` (14 abstract methods). Switching is a config change — no code changes needed.

### Multimodal Support

| Content Type | Formats | Tool |
|-------------|---------|------|
| Images | JPEG, PNG, WebP, GIF | `learn_image` |
| Documents | PDF | `learn_document` |
| Video | Various | `learn_video` |
| Mixed search | Text + image | `multimodal_vector_search` |

Embeddings via Voyage `voyage-multimodal-3.5` — all content types share one vector space.

### Multi-User Support

Set `BRAIN_USER_ID` in `.env` to isolate data per user. All Supabase tables use row-level security (RLS) policies scoped to `user_id`. Mem0 memories are scoped via the `user_id` parameter.

### LLM Provider Fallback

Configure fallback chains for resilience:

```bash
MODEL_PROVIDER=anthropic
MODEL_FALLBACK_CHAIN=openai,ollama-local
```

If Anthropic fails, tries OpenAI, then local Ollama. Per-agent overrides:
```bash
AGENT_MODEL_OVERRIDES={"recall": "openai:gpt-4o", "create": "anthropic:claude-sonnet-4-5"}
```

---

## Tests

```bash
cd backend
pytest                          # All tests (1324+)
pytest tests/test_agents.py     # Single file
pytest -k "test_recall"         # Filter by name
pytest -x                       # Stop on first failure
```

25 test files covering agents, services, MCP tools, API endpoints, providers, config, CLI, and graph operations. See `backend/tests/` for the full list.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11+ |
| Agent Framework | Pydantic AI |
| MCP Server | FastMCP 2.x |
| REST API | FastAPI |
| Memory | Mem0 (cloud/local) |
| Database | Supabase (PostgreSQL + pgvector) |
| Embeddings | Voyage AI (`voyage-multimodal-3.5`) |
| Reranking | Voyage AI (`rerank-2.5-lite`) |
| Knowledge Graph | Graphiti + Neo4j (optional) |
| Frontend | Streamlit |
| CLI | Click |
| LLM Providers | Anthropic, OpenAI, Groq, Ollama |

---

## License

MIT — see [LICENSE](LICENSE).
