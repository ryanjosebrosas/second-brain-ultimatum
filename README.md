# Second Brain

**Persistent AI memory — your agents remember everything.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Tests: 1158 passing](https://img.shields.io/badge/tests-1158_passing-brightgreen.svg)](#tests)

Your AI forgets everything between sessions. Second Brain fixes that. 13 Pydantic AI agents give Claude (or any MCP client) persistent recall of your decisions, patterns, voice, and priorities — backed by Mem0 semantic memory, Supabase/pgvector, and Voyage AI embeddings. Text, images, PDFs, video — all searchable in one shared vector space.

Three ways in: MCP server for Claude Code, REST API for custom frontends, CLI for scripts. Ships with a Streamlit dashboard out of the box.

---

## Table of Contents

- [Why This Exists](#why-this-exists)
- [Quickstart](#quickstart)
- [Architecture](#architecture)
- [The 13 Agents](#the-13-agents)
- [Frontend Dashboard](#frontend-dashboard)
- [REST API](#rest-api)
- [Service Layer](#service-layer)
- [Pluggable Memory Providers](#pluggable-memory-providers)
- [Multimodal Support](#multimodal-support)
- [Multi-User Support](#multi-user-support)
- [Data Flow](#data-flow)
- [Setup](#setup)
- [Docker](#docker)
- [MCP Integration](#mcp-integration)
- [CLI](#cli)
- [Tests](#tests)
- [Tech Stack](#tech-stack)
- [By the Numbers](#by-the-numbers)
- [License](#license)

---

## Why This Exists

Every AI session starts from scratch. You re-explain your architecture, re-describe your preferences, re-establish context — every single time. The Claude that helped you build auth last week has zero memory of it today.

**Second Brain gives Claude a brain that persists.** Store decisions, recall patterns, generate content in your voice, score your work, get coached on priorities. Everything survives across sessions via semantic search — not keyword matching.

---

## Quickstart

Get running in 3 steps:

### 1. Install

```bash
cd backend
cp .env.example .env   # Add: MEM0_API_KEY, SUPABASE_URL, SUPABASE_KEY, OPENAI_API_KEY
pip install -e ".[dev]"
```

### 2. Apply database migrations

Run all 19 migrations in `backend/supabase/migrations/` via the Supabase dashboard or CLI.

### 3. Connect to Claude Code

```bash
claude mcp add second-brain -- python -m second_brain.mcp_server --cwd /path/to/backend
```

Or add to `.mcp.json`:

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

That's it. All 13 agents are now available as MCP tools. Try:

```
Recall everything I know about authentication patterns.
Learn this: [paste your architecture decisions]
Coach me — what should I focus on today?
```

---

## Architecture

```mermaid
graph TD
    CC["Claude Code<br/><i>any MCP client</i>"] -->|"MCP tool call"| MCP["mcp_server.py<br/>FastMCP"]
    ST["Streamlit Frontend"] -->|"HTTP"| API["FastAPI<br/>45+ endpoints"]
    CLI["CLI<br/><code>brain</code> command"] --> AGENTS

    MCP --> AGENTS["Agent Layer<br/>13 Pydantic AI agents"]
    API --> AGENTS

    AGENTS --> SVC["Service Layer"]

    SVC --> MEM0["Mem0<br/>Semantic memory"]
    SVC --> SB["Supabase<br/>PostgreSQL + pgvector"]
    SVC --> VAI["Voyage AI<br/>Embeddings + reranking"]
    SVC --> GR["Graphiti<br/>Knowledge graph<br/><i>optional</i>"]

    style CC fill:#2c3e50,color:#fff
    style ST fill:#2c3e50,color:#fff
    style CLI fill:#2c3e50,color:#fff
    style MCP fill:#8e44ad,color:#fff
    style API fill:#8e44ad,color:#fff
    style AGENTS fill:#4a90d9,color:#fff
    style SVC fill:#34495e,color:#fff
    style MEM0 fill:#e74c3c,color:#fff
    style SB fill:#e74c3c,color:#fff
    style VAI fill:#e74c3c,color:#fff
    style GR fill:#95a5a6,color:#fff
```

Three interfaces, one brain:

| Interface | Transport | Use Case |
|-----------|-----------|----------|
| **MCP Server** | stdio or HTTP | Claude Code, Cursor, Windsurf — any MCP client |
| **REST API** | HTTP (FastAPI) | Custom frontends, integrations, automation |
| **CLI** | Terminal | Scripts, health checks, migrations |

---

## The 13 Agents

### Memory — Store and retrieve knowledge across sessions

```mermaid
graph LR
    YOU["You"] -->|"paste notes, code, decisions"| LEARN["learn agent<br/>extracts patterns + insights"]
    LEARN -->|"stores to"| MEM0[("Mem0<br/>Semantic memory")]
    MEM0 -->|"searched by"| RECALL["recall agent<br/>surfaces relevant knowledge"]
    RECALL -->|"answers"| ASK["ask agent<br/>Q&A with full brain context"]
    ASK --> YOU

    style YOU fill:#2c3e50,color:#fff
    style LEARN fill:#27ae60,color:#fff
    style MEM0 fill:#e74c3c,color:#fff
    style RECALL fill:#4a90d9,color:#fff
    style ASK fill:#4a90d9,color:#fff
```

| Agent | What It Does |
|-------|-------------|
| `recall` | Semantic search across stored memory — surfaces past decisions, patterns, and notes by meaning |
| `ask` | Answers questions using full brain context — connects stored knowledge to new questions |
| `learn` | Extracts patterns and insights from anything you feed it and stores them |
| `learn_image` | Stores images to Mem0 with multimodal Voyage AI embeddings for cross-modal search |
| `learn_document` | Ingests PDFs, MDX, and TXT documents into semantic memory |
| `learn_video` | Generates multimodal video embeddings via Voyage AI with text context stored to memory |

> **Note**: `learn_image`, `learn_document`, and `learn_video` are MCP tools on the learn agent — not separate agents. They share the learn agent's pattern extraction pipeline with modality-specific ingestion.

### Content — Generate and score content in your voice

```mermaid
graph LR
    STORED[("Stored examples<br/>+ voice patterns")] --> CREATE["create agent<br/>generates content"]
    CREATE -->|"draft"| REVIEW["review agent<br/>scores across dimensions"]
    REVIEW -->|"scores + feedback"| CLARITY["clarity agent<br/>readability analysis"]
    CLARITY -->|"issues"| SYNTH["synthesizer agent<br/>consolidates all feedback"]
    SYNTH -->|"unified report"| YOU["You"]

    style STORED fill:#e74c3c,color:#fff
    style CREATE fill:#27ae60,color:#fff
    style REVIEW fill:#e67e22,color:#fff
    style CLARITY fill:#7b68ee,color:#fff
    style SYNTH fill:#7b68ee,color:#fff
    style YOU fill:#2c3e50,color:#fff
```

| Agent | What It Does |
|-------|-------------|
| `create` | Generates content in your authentic voice — pre-loads your voice guide and past examples |
| `review` | Scores content across dimensions: clarity, structure, impact, tone — with actionable feedback |
| `clarity` | Readability analysis — flags passive voice, jargon, complex sentences |
| `synthesizer` | Consolidates feedback from multiple sources into a single prioritized action list |
| `template_builder` | Detects repeating patterns and proposes reusable templates |

### Operations — Manage priorities and communications

```mermaid
graph LR
    CTX[("Stored context<br/>projects + history")] --> COACH["coach agent<br/>daily accountability"]
    CTX --> PMO["pmo agent<br/>task prioritization"]
    CTX --> EMAIL["email_agent<br/>voice-aware composition"]

    COACH -->|"priority brief"| YOU["You"]
    PMO -->|"ranked task list"| YOU
    EMAIL -->|"drafted email"| YOU

    style CTX fill:#e74c3c,color:#fff
    style COACH fill:#e67e22,color:#fff
    style PMO fill:#e67e22,color:#fff
    style EMAIL fill:#e67e22,color:#fff
    style YOU fill:#2c3e50,color:#fff
```

| Agent | What It Does |
|-------|-------------|
| `coach` | Daily accountability — surfaces top priorities, checks progress, prompts reflection |
| `pmo` | PMO-style task prioritization — manages competing projects and deadlines |
| `email_agent` | Composes emails matched to your voice and recipient context |

### Specialist

| Agent | What It Does |
|-------|-------------|
| `specialist` | Deep Q&A on Claude Code, Pydantic AI, and the Second Brain system itself |

---

## Frontend Dashboard

A Streamlit web UI for interacting with your brain without Claude Code.

```bash
# Start the full stack
docker compose up -d

# Or run standalone
cd frontend && streamlit run app.py
```

### Pages

| Page | What It Does |
|------|-------------|
| **Chat** | Talk to any of the 13 agents with per-agent response formatting and chat history |
| **Memory** | Browse Supabase tables, semantic search via Mem0, pgvector similarity search |
| **Dashboard** | Health metrics, growth trends, quality scores, brain level milestones |
| **Content** | Create and review content with voice-aware generation |
| **Projects** | Project lifecycle management — create, advance stages, attach artifacts |
| **Graph** | Knowledge graph explorer with interactive force-directed visualization |
| **Settings** | Live config viewer, active provider status, service health |

The frontend connects to the REST API — no direct database access. All secrets stay in the backend.

---

## REST API

45+ endpoints powering the frontend and available for custom integrations. Built with FastAPI, auto-documented at `/docs`.

### Endpoint Groups

| Group | Prefix | Endpoints | Purpose |
|-------|--------|-----------|---------|
| **Agents** | `/api/*` | 13 POST | One endpoint per agent — same interface as MCP tools |
| **Memory** | `/api/search/*`, `/api/ingest/*` | 12 | Search, browse, and ingest across all memory stores |
| **Health** | `/api/health/*` | 6 GET | Metrics, growth, milestones, quality, setup status |
| **Projects** | `/api/projects/*` | 8 | Full project lifecycle CRUD + artifacts |
| **Graph** | `/api/graph/*` | 4 | Knowledge graph search, episodes, health |
| **Settings** | `/api/settings/*` | 2 GET | Config and provider status (secrets redacted) |

```bash
# Start the API server
cd backend && uvicorn second_brain.api.main:create_app --factory --port 8001

# Or via Docker (starts both MCP + API)
docker compose up -d backend
```

---

## Service Layer

Agents never talk to databases directly. Three external systems do the heavy lifting through a clean service abstraction — swappable at runtime via `MEMORY_PROVIDER`.

```mermaid
graph TD
    subgraph "Service Layer"
        MS["memory.py<br/>Mem0 wrapper"]
        SS["storage.py<br/>Supabase CRUD + ContentTypeRegistry"]
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
| `memory.py` | Mem0 wrapper — add, search, and retrieve semantic memories. Retry/timeout hardened via Tenacity (3 attempts, exponential backoff). Supports multimodal content |
| `storage.py` | Supabase wrapper — CRUD for all structured data plus `ContentTypeRegistry` for content type configs |
| `embeddings.py` | Embedding generation via Voyage AI (primary) or OpenAI (fallback). Supports multimodal inputs via `embed_multimodal()` |
| `voyage.py` | Voyage AI reranking + multimodal embeddings — `voyage-multimodal-3.5` embeds text, images, and video into a shared 1024-dim vector space |
| `graphiti.py` | Knowledge graph via Graphiti + FalkorDB — entity and relationship extraction (optional) |
| `graphiti_memory.py` | Adapts Graphiti to the `MemoryServiceBase` interface — complete drop-in replacement for Mem0, all 14 methods implemented |
| `health.py` | Brain metrics, growth milestones, and system health checks |
| `retry.py` | Tenacity retry decorators for transient failures |
| `search_result.py` | Shared data structures for search results across all retrieval methods |
| `abstract.py` | Abstract base classes (`MemoryServiceBase`, etc.) for pluggable service implementations + stub services for testing |

---

## Pluggable Memory Providers

The memory layer is defined by an abstract interface (`MemoryServiceBase`) with three interchangeable backends. Switch between them with a single environment variable:

| Provider | `MEMORY_PROVIDER=` | Backend | Best For |
|----------|-------------------|---------|----------|
| **Mem0** | `mem0` (default) | Mem0 cloud API | Production — managed semantic memory with built-in embedding search |
| **Graphiti** | `graphiti` | FalkorDB graph database | Knowledge graphs — entity/relationship extraction with graph-native search |
| **None** | `none` | In-memory stub | Testing and CI — zero external dependencies, instant startup |

All three providers implement the same 14-method interface. Agents never know which backend is active — they call `memory_service.search()` and get back a `SearchResult` regardless. If a provider fails to initialize, it falls back to Mem0 automatically. Search errors return empty results instead of crashing.

---

## Multimodal Support

Store and search across multiple content types — not just text.

| Content Type | MCP Tool | Memory Storage | Vector Embedding |
|-------------|----------|---------------|-----------------|
| **Images** (JPEG, PNG, WebP, GIF) | `learn_image` | Mem0 `image_url` block | Voyage multimodal embedding |
| **Documents** (PDF, MDX, TXT) | `learn_document` | Mem0 `pdf_url` / `mdx_url` block | Text extraction + embedding |
| **Video** | `learn_video` | Text context to Mem0 | Voyage multimodal embedding |
| **Cross-modal search** | `multimodal_vector_search` | — | Combined text + image query vectors |

All multimodal embeddings use `voyage-multimodal-3.5` (1024 dimensions) — the same vector space as text. Images, documents, and video are searchable alongside text memories using the same pgvector infrastructure. No separate migration needed.

The Graphiti memory provider falls back to text-only mode for multimodal content — non-text blocks are skipped with a debug log.

---

## Multi-User Support

Each instance is scoped to a single user via the `BRAIN_USER_ID` environment variable. All reads and writes in `storage.py` are filtered by this value, so multiple instances can share one Supabase deployment without data leaking between users. Existing single-user setups work unchanged — the default value is `ryan`.

---

## Data Flow

### Learn → Store → Recall

```mermaid
sequenceDiagram
    participant You
    participant MCP as mcp_server.py
    participant Learn as learn agent
    participant Mem0
    participant Voyage as Voyage AI
    participant Recall as recall agent

    You->>MCP: "Learn this pattern: [content]"
    MCP->>Learn: run(input, deps=BrainDeps)
    Learn->>Voyage: embed(content)
    Voyage-->>Learn: vector
    Learn->>Mem0: add(content, vector, metadata)
    Mem0-->>Learn: stored
    Learn-->>MCP: InsightResult
    MCP-->>You: "Stored: [summary of what was learned]"

    Note over You,Recall: Later session...

    You->>MCP: "Recall what I know about Supabase RLS"
    MCP->>Recall: run(query, deps=BrainDeps)
    Recall->>Voyage: embed(query)
    Voyage-->>Recall: query vector
    Recall->>Mem0: search(vector, top_k=10)
    Mem0-->>Recall: ranked memories
    Recall-->>MCP: RecallResult
    MCP-->>You: relevant memories + context
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

## Setup

### 1. Environment

```bash
cd backend
cp .env.example .env
```

Edit `.env`:

```bash
MEM0_API_KEY=...            # Required — semantic memory store
SUPABASE_URL=...            # Required — structured storage + vector search
SUPABASE_KEY=...            # Required — Supabase service role key
OPENAI_API_KEY=...          # Required — Mem0 internal embeddings (text-embedding-3-small)
VOYAGE_API_KEY=...          # Optional — primary embeddings + reranking (falls back to OpenAI)
MEMORY_PROVIDER=mem0        # mem0 (default), graphiti, or none
BRAIN_USER_ID=ryan          # Optional — isolates data per user (default: ryan)
```

### 2. LLM Backend

Agents use a **provider registry** for flexible LLM selection with automatic fallback chains:

```bash
MODEL_PROVIDER=anthropic         # auto|anthropic|ollama-local|ollama-cloud|openai|groq
MODEL_NAME=claude-sonnet-4-5     # Optional model override
MODEL_FALLBACK_CHAIN=ollama-local  # Optional comma-separated fallback providers
```

`MODEL_PROVIDER=auto` (default) infers from available API keys: Anthropic > Ollama Cloud > Ollama Local. Existing `.env` files with just `ANTHROPIC_API_KEY` work unchanged.

<details>
<summary>All LLM provider configurations</summary>

| Provider | `MODEL_PROVIDER=` | Env Vars Required | Default Model |
|----------|-------------------|-------------------|---------------|
| Anthropic | `anthropic` | `ANTHROPIC_API_KEY` | `claude-sonnet-4-5` |
| Ollama Local | `ollama-local` | `OLLAMA_BASE_URL` (optional) | `llama3.1:8b` |
| Ollama Cloud | `ollama-cloud` | `OLLAMA_BASE_URL`, `OLLAMA_API_KEY` | `llama3.1:8b` |
| OpenAI | `openai` | `OPENAI_API_KEY` | `gpt-4o` |
| Groq | `groq` | `GROQ_API_KEY` | `llama-3.3-70b-versatile` |

</details>

**Claude Subscription setup** (recommended if you have Claude Pro/Max):

1. Install Claude CLI: `npm install -g @anthropic-ai/claude-code`
2. Authenticate: run `claude` and complete the login flow
3. Set `USE_SUBSCRIPTION=true` in `.env`
4. No `ANTHROPIC_API_KEY` needed — reads your OAuth token from the credential store automatically

The subscription auth works with any MCP client (Claude Code, Cursor, Windsurf, etc.) — the OAuth token is stored on your machine, not tied to the editor.

**Ollama Cloud setup** (for non-Anthropic models):

```bash
MODEL_PROVIDER=ollama-cloud
OLLAMA_BASE_URL=https://your-ollama-endpoint.com
OLLAMA_API_KEY=your-api-key
MODEL_NAME=llama3.1:8b
```

Any OpenAI-compatible API endpoint works here (Ollama, Together AI, OpenRouter, etc.).

### 3. Install

```bash
cd backend
pip install -e ".[dev]"
```

Optional extras:

```bash
pip install -e ".[dev,graphiti]"      # + Graphiti knowledge graph
pip install -e ".[dev,subscription]"  # + Claude Agent SDK (subscription auth)
pip install -e ".[dev,ollama]"        # + Ollama local model support
```

### 4. Database Migrations

Apply all 19 migrations in `backend/supabase/migrations/` via the Supabase dashboard or CLI, in order.

<details>
<summary>Full migration list (001–019)</summary>

| # | Migration | Purpose |
|---|-----------|---------|
| 001 | `initial_schema.sql` | Core tables |
| 002 | `examples_knowledge.sql` | Examples and knowledge tables |
| 003 | `pattern_constraints.sql` | Pattern uniqueness constraints |
| 004 | `content_types.sql` | Content type registry |
| 005 | `growth_tracking_tables.sql` | Growth and milestone tracking |
| 006 | `rls_policies.sql` | Row Level Security policies |
| 007 | `foreign_keys_indexes.sql` | Foreign keys and indexes |
| 008 | `data_constraints.sql` | Data validation constraints |
| 009 | `reinforce_pattern_rpc.sql` | Pattern reinforcement RPC |
| 010 | `vector_search_rpc.sql` | pgvector similarity search RPC |
| 011 | `voyage_dimensions.sql` | Voyage AI embedding dimensions |
| 012 | `projects_lifecycle.sql` | Project lifecycle tables |
| 013 | `quality_trending.sql` | Quality score trending |
| 014 | `content_type_instructions.sql` | Content type prompt instructions |
| 015 | `user_id_isolation.sql` | Multi-user data isolation |
| 016 | `hnsw_indexes.sql` | HNSW vector indexes for fast similarity search |
| 017 | `rls_hardening.sql` | Strengthened Row Level Security policies |
| 018 | `vector_search_hnsw.sql` | Vector search RPC with HNSW ef_search tuning |
| 019 | `reinforce_pattern_user_id.sql` | User-scoped pattern reinforcement |

</details>

### 5. Start the MCP Server

```bash
cd backend
python -m second_brain.mcp_server
```

All 13 agents are now available as MCP tools inside Claude Code.

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

Once connected, call any agent naturally:

```
Use the second brain to recall everything I know about Supabase RLS.

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

Frontend and API:

```
Show me my brain dashboard — health, growth, and quality.

Search my memories for anything about React hooks.

What's the status of the auth-system project?
```

---

## CLI

Direct access without the MCP layer:

```bash
brain --help         # Show all commands
brain health         # Check brain health and growth milestones
brain migrate        # Run data migration
```

---

## Tests

```bash
cd backend
pytest                              # All tests (1158+)
pytest tests/test_agents.py         # Single file
pytest -k "test_recall"             # Filter by name
pytest -x                           # Stop on first failure
```

25 test files. One per source module. All async tests run without `@pytest.mark.asyncio` — `asyncio_mode = "auto"`.

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.11+ (Docker: 3.12) |
| Agent framework | Pydantic AI (`pydantic-ai[anthropic]`) |
| MCP server | FastMCP |
| REST API | FastAPI |
| Frontend | Streamlit |
| Semantic memory | Mem0 (`mem0ai`) |
| Database | Supabase (PostgreSQL + pgvector) |
| Embeddings | Voyage AI `voyage-multimodal-3.5` (primary), OpenAI (text fallback) |
| Knowledge graph | Graphiti + FalkorDB (optional, feature-flagged) |
| LLM providers | Provider registry — Anthropic, OpenAI, Groq, Ollama with fallback chains |
| CLI | Click (`brain` entrypoint) |
| Testing | pytest + pytest-asyncio (`asyncio_mode = "auto"`) |

---

## By the Numbers

| Component | Count |
|-----------|-------|
| Pydantic AI agents | 13 |
| MCP tools | 42 |
| REST API endpoints | 45+ |
| Frontend pages | 7 |
| Service modules | 10 |
| LLM providers | 5 (Anthropic, OpenAI, Groq, Ollama local, Ollama cloud) |
| Database migrations | 19 |
| Test files | 25 |
| Tests passing | 1158+ |

<details>
<summary>Full code structure</summary>

```
backend/
├── src/second_brain/
│   ├── mcp_server.py          # MCP tool surface (42 tools)
│   ├── service_mcp.py         # Supplemental service routing
│   ├── api/
│   │   ├── main.py            # FastAPI app factory
│   │   └── routers/           # 6 router modules (agents, memory, health, projects, graph, settings)
│   ├── agents/                # 13 Pydantic AI agents
│   │   ├── chief_of_staff.py  # Routing orchestrator
│   │   ├── recall.py          # Semantic memory search
│   │   ├── ask.py             # Q&A with brain context
│   │   ├── learn.py           # Pattern extraction + storage
│   │   ├── create.py          # Content generation (voice-aware)
│   │   ├── review.py          # Multi-dimension content scoring
│   │   ├── coach.py           # Daily accountability coaching
│   │   ├── pmo.py             # Task prioritization
│   │   ├── email_agent.py     # Email composition
│   │   ├── specialist.py      # Claude Code / Pydantic AI Q&A
│   │   ├── clarity.py         # Readability analysis
│   │   ├── synthesizer.py     # Feedback consolidation
│   │   ├── template_builder.py# Template opportunity detection
│   │   └── utils.py           # Shared: tool_error(), run_pipeline(), format_*()
│   ├── services/              # 10 service modules
│   │   ├── memory.py          # Mem0 semantic memory wrapper
│   │   ├── storage.py         # Supabase CRUD + ContentTypeRegistry
│   │   ├── embeddings.py      # Voyage AI / OpenAI embedding generation
│   │   ├── voyage.py          # Voyage AI reranking
│   │   ├── graphiti.py        # Knowledge graph (optional)
│   │   ├── graphiti_memory.py # Graphiti-backed MemoryServiceBase adapter
│   │   ├── health.py          # Brain metrics + growth milestones
│   │   ├── retry.py           # Tenacity retry helpers
│   │   ├── search_result.py   # Search result data structures
│   │   └── abstract.py        # ABCs + stub services (MemoryServiceBase, etc.)
│   ├── providers/             # 4 LLM provider adapters
│   │   ├── __init__.py        # BaseProvider ABC + provider registry
│   │   ├── anthropic.py       # Anthropic Claude (API key + subscription)
│   │   ├── ollama.py          # Ollama local + cloud providers
│   │   ├── openai.py          # OpenAI GPT provider
│   │   └── groq.py            # Groq fast inference provider
│   ├── schemas.py             # All Pydantic models (no internal imports)
│   ├── config.py              # BrainConfig (Pydantic Settings)
│   ├── deps.py                # BrainDeps + create_deps() factory
│   ├── models.py              # Provider registry + fallback chains
│   ├── models_sdk.py          # Claude SDK model support (subscription auth)
│   ├── auth.py                # Authentication helpers
│   ├── migrate.py             # Data migration utilities
│   └── cli.py                 # Click CLI ("brain" command)
├── supabase/migrations/       # 19 SQL migrations (001–019)
├── tests/                     # 25 test files, 1158+ tests
├── docs/                      # Operational runbooks and integration guides
├── scripts/                   # Utility scripts
├── Dockerfile                 # Multi-stage uv build (Python 3.12)
└── pyproject.toml             # Dependencies + pytest config

frontend/
├── app.py                     # Streamlit multi-page app
├── pages/                     # 7 pages (chat, memory, dashboard, content, projects, graph, settings)
├── components/                # Reusable UI components
├── api_client.py              # HTTP client for REST API
├── config.py                  # Frontend configuration
├── Dockerfile                 # Python 3.12-slim
└── requirements.txt           # Frontend dependencies

docker-compose.yml             # Root: full-stack orchestration (backend + frontend)
```

</details>

---

## License

[MIT](LICENSE)
