# Second Brain

**A personal AI memory and knowledge system — exposed as an MCP server for Claude Code.**

13 Pydantic AI agents backed by Mem0 semantic memory, Supabase/pgvector, and Voyage AI embeddings. Your AI remembers what you've built, what you've learned, and how you think — across every session.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## What It Does

Most AI sessions start from zero. You re-explain your architecture, re-describe your voice, re-establish your preferences — every time. Second Brain fixes that.

It gives Claude Code a persistent memory layer: store decisions, recall patterns, generate content in your voice, score your work, and get coaching on your priorities. Everything persists across sessions via semantic search, not keyword matching.

---

## The 13 Agents

All agents are exposed as MCP tools via FastMCP. The `chief_of_staff` orchestrator routes requests to the right agent automatically.

| Agent | What It Does |
|-------|-------------|
| `chief_of_staff` | Routing orchestrator — analyses your request and delegates to the right agent or pipeline |
| `recall` | Searches semantic memory to surface relevant past decisions, patterns, and knowledge |
| `ask` | General Q&A with full brain context — answers questions using stored knowledge |
| `learn` | Extracts patterns and insights from content, stores them to semantic memory |
| `create` | Generates content with awareness of your voice, style, and stored examples |
| `review` | Scores content across multiple dimensions (clarity, structure, impact) |
| `coach` | Daily accountability coaching — surfaces priorities and tracks progress |
| `pmo` | PMO-style task prioritization — manages competing projects and deadlines |
| `email_agent` | Composes emails matched to your voice and the recipient relationship |
| `specialist` | Deep Q&A on Claude Code, Pydantic AI, and the Second Brain system itself |
| `clarity` | Readability analysis — identifies complexity, jargon, and structural issues |
| `synthesizer` | Consolidates feedback from multiple sources into a unified, actionable summary |
| `template_builder` | Detects template opportunities in repeated content patterns |

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.11+ |
| Agent framework | Pydantic AI (`pydantic-ai[anthropic]`) |
| MCP server | FastMCP |
| Semantic memory | Mem0 (`mem0ai`) |
| Database | Supabase (PostgreSQL + pgvector) |
| Embeddings | Voyage AI (primary), OpenAI (fallback) |
| Knowledge graph | Graphiti (optional, feature-flagged) |
| CLI | Click (`brain` entrypoint) |
| Retries | Tenacity |
| Config | Pydantic Settings (`.env` via `BrainConfig`) |
| Testing | pytest + pytest-asyncio (`asyncio_mode = "auto"`) |

---

## Architecture

```
MCP tool call
  → mcp_server.py validates input + enforces timeout
  → agent receives request with BrainDeps
  → chief_of_staff routes to specialist agent
  → agent tools call service layer
  → Mem0 / Supabase / Voyage AI
  → structured Pydantic output validated
  → formatted as plain text string → returned to Claude Code
```

```
backend/src/second_brain/
├── mcp_server.py          # Public surface: @server.tool() functions
├── service_mcp.py         # Supplemental service routing
├── deps.py                # BrainDeps dataclass + create_deps()
├── config.py              # BrainConfig (Pydantic Settings, loads .env)
├── schemas.py             # All Pydantic output models (dependency-free)
├── models.py              # AI model selection logic
├── cli.py                 # Click CLI ("brain" command)
├── agents/
│   ├── chief_of_staff.py  # Routing orchestrator
│   ├── recall.py
│   ├── ask.py
│   ├── learn.py
│   ├── create.py
│   ├── review.py
│   ├── coach.py
│   ├── pmo.py
│   ├── email_agent.py
│   ├── specialist.py
│   ├── clarity.py
│   ├── synthesizer.py
│   ├── template_builder.py
│   └── utils.py           # Shared: tool_error(), run_pipeline(), format_*()
└── services/
    ├── memory.py          # Mem0 semantic memory wrapper
    ├── storage.py         # Supabase CRUD + ContentTypeRegistry
    ├── embeddings.py      # Voyage AI / OpenAI embedding generation
    ├── voyage.py          # Voyage AI reranking
    ├── graphiti.py        # Knowledge graph (optional)
    ├── health.py          # Brain metrics + growth milestones
    ├── retry.py           # Tenacity retry helpers
    ├── search_result.py   # Search result data structures
    └── abstract.py        # Abstract base classes
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
ANTHROPIC_API_KEY=...
MEM0_API_KEY=...
SUPABASE_URL=...
SUPABASE_KEY=...
VOYAGE_API_KEY=...        # optional — falls back to OpenAI embeddings
GRAPHITI_ENABLED=false    # set true to enable knowledge graph
```

### 2. Install

```bash
cd backend
pip install -e ".[dev]"
```

Optional extras:

```bash
pip install -e ".[dev,graphiti]"      # + Graphiti knowledge graph (FalkorDB)
pip install -e ".[dev,subscription]"  # + Claude Agent SDK (subscription auth)
pip install -e ".[dev,ollama]"        # + Ollama local model support
```

### 3. Database

Apply migrations via the Supabase dashboard or CLI. Migrations are in `backend/supabase/migrations/` — numbered `001` through `014`.

### 4. Start the MCP Server

```bash
cd backend
python -m second_brain.mcp_server
```

All 13 agents are now available as MCP tools inside Claude Code.

---

## MCP Integration

Add the server to your Claude Code MCP config:

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

Once connected, you can call any agent directly from Claude Code:

```
Use the second brain to recall everything I know about Supabase RLS.
Learn this pattern: [paste code or notes]
Create a LinkedIn post in my voice about [topic]
Review this draft and score it across all dimensions
```

---

## CLI

The `brain` CLI provides direct access without the MCP layer:

```bash
brain --help         # Show all commands
brain health         # Check brain health + growth milestones
brain migrate        # Run data migration
```

---

## Tests

```bash
cd backend
pytest               # All tests (~781)
pytest tests/test_agents.py    # Single file
pytest -k "test_recall"        # Filter by name
pytest -x            # Stop on first failure
pytest -v            # Verbose
```

One test file per source module. All async tests run without `@pytest.mark.asyncio` — `asyncio_mode = "auto"` is set in `pyproject.toml`.

---

## By the Numbers

| Component | Count |
|-----------|-------|
| Pydantic AI agents | 13 |
| Service layer modules | 9 |
| Database migrations | 14 |
| Test files | 20 |
| Tests | ~781 |
| Python version | 3.11+ |

---

## License

[MIT](LICENSE)
