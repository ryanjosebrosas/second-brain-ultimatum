# AI Second Brain

A Python-powered AI Second Brain that migrates a markdown-based knowledge system into a semantic, searchable, and structured architecture. Built with Pydantic AI agents, Mem0 semantic memory, and Supabase structured storage.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## What It Does

Your Second Brain stores business knowledge — patterns, experiences, examples, and knowledge entries — across two complementary backends:

- **Mem0** — Semantic memory with auto fact extraction. Ask natural language questions and get relevant context back, ranked by relevance.
- **Supabase** — Structured storage for patterns (with confidence levels), experiences, content examples, and a knowledge repository.

Three AI agents sit on top and do the thinking:

| Agent | Purpose |
|-------|---------|
| **RecallAgent** | Semantic memory search across Mem0 + Supabase. Returns ranked matches with sources and graph relationships. |
| **AskAgent** | Contextual help powered by accumulated knowledge. Applies patterns, references past work, suggests next actions. |
| **LearnAgent** | Extracts patterns and insights from raw work session text. Auto-detects reinforcements of existing patterns. |

Two interfaces expose everything:

- **CLI** (`brain` command) — For terminal use
- **MCP Server** — For Claude Code integration, making your brain available as tools during development

---

## Architecture

```
src/second_brain/
├── config.py            # BrainConfig — Pydantic Settings, loads .env
├── models.py            # get_model() — LLM provider factory (Claude → Ollama)
├── deps.py              # BrainDeps — injected into all agents
├── schemas.py           # Pydantic output models (RecallResult, AskResult, LearnResult)
├── cli.py               # Click CLI (8 commands)
├── mcp_server.py        # FastMCP server (9 tools)
├── migrate.py           # Markdown → Mem0 + Supabase migration
├── agents/
│   ├── recall.py        # RecallAgent — semantic memory search
│   ├── ask.py           # AskAgent — contextual help
│   └── learn.py         # LearnAgent — pattern extraction
└── services/
    ├── memory.py        # MemoryService — Mem0 wrapper (cloud + local)
    ├── storage.py       # StorageService — Supabase CRUD + delete
    ├── health.py        # HealthService — brain health metrics
    ├── search_result.py # SearchResult — typed search results
    └── graphiti.py      # GraphitiService — Neo4j graph memory (optional)
```

### Data Flow

```
CLI / MCP → Agent.run(deps=BrainDeps) → Agent tools → Services → Mem0 / Supabase
```

### LLM Fallback Chain

The system tries Anthropic Claude first. If unavailable, it falls back to Ollama for local inference. Model is resolved at runtime, not import time.

---

## Features

### Agents

**RecallAgent** — Search across all memory backends simultaneously:
- Mem0 semantic search (configurable result limit)
- Supabase pattern registry with confidence levels
- Past experiences with category filtering
- Content examples (emails, LinkedIn posts, case studies)
- Graph relationships via Mem0 graph or Graphiti/Neo4j

**AskAgent** — Contextual help grounded in your brain's knowledge:
- Loads core context (company info, customer profiles, positioning)
- Finds relevant patterns and applies them to your question
- Surfaces similar past experiences with learnings
- Searches the knowledge repository for frameworks and methodologies

**LearnAgent** — Extracts structured knowledge from raw text:
- Searches existing patterns before creating duplicates
- Marks reinforcements vs. new patterns with confidence escalation
- Extracts anti-patterns (what NOT to do)
- Records complete work experiences with outcomes
- Adds key insights to semantic memory for future recall

### Storage

**6 Supabase tables:**

| Table | Purpose |
|-------|---------|
| `patterns` | Pattern registry with name, topic, confidence (LOW/MEDIUM/HIGH), evidence, anti-patterns |
| `experiences` | Work session records with outcomes, learnings, and review scores |
| `examples` | Content examples (LinkedIn posts, emails, case studies, presentations) |
| `knowledge_repo` | Frameworks, methodologies, playbooks, research, tools |
| `memory_content` | Core brain context (company info, personal data, customer profiles) |
| `brain_health` | Health metric snapshots for tracking growth over time |

Full CRUD operations — get, upsert, and delete for patterns, experiences, examples, and knowledge entries.

### Memory Management

- **Delete operations** for all 4 content tables (patterns, experiences, examples, knowledge)
- Delete via CLI: `brain delete pattern <uuid>`
- Delete via MCP: `delete_item` tool with table and ID parameters
- Hard delete (no soft-delete) — KISS for a single-user brain

### Configurable Limits

All search limits and content truncation values are tunable via `.env`:

| Config Field | Default | Purpose |
|-------------|---------|---------|
| `MEMORY_SEARCH_LIMIT` | 10 | Semantic memory search results |
| `GRAPH_SEARCH_LIMIT` | 5 | Graph relationship search results |
| `PATTERN_CONTEXT_LIMIT` | 30 | Patterns injected into LearnAgent context |
| `EXPERIENCE_LIMIT` | 5 | Experience retrieval limit |
| `CONTENT_PREVIEW_LIMIT` | 1000 | Character limit for content previews |
| `PATTERN_PREVIEW_LIMIT` | 200 | Character limit for pattern text in results |

### Health Metrics

A dedicated `HealthService` computes brain health from a single source of truth:
- Total memories, patterns (by confidence), and experiences
- Topic breakdown across patterns
- Graph provider status
- Growth status (BUILDING vs. GROWING based on pattern count)

### Graph Memory (Optional)

Two graph memory providers for entity relationship tracking:

- **Mem0 Graph** — Cloud-based, enabled via `GRAPH_PROVIDER=mem0`. Extracts entity relationships during memory add/search.
- **Graphiti + Neo4j** — Local graph database via `GRAPH_PROVIDER=graphiti`. Requires `graphiti-core` and a Neo4j instance.

---

## Installation

```bash
# Clone the repo
git clone <repo-url>
cd ai-second-brain

# Install with dev dependencies
pip install -e ".[dev]"

# Optional: Ollama fallback support
pip install -e ".[ollama]"

# Optional: Graphiti graph memory
pip install -e ".[graphiti]"
```

### Configuration

Create a `.env` file:

```env
# Required
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
BRAIN_DATA_PATH=/path/to/markdown/data

# LLM (at least one required)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...          # For Mem0 embeddings

# Optional: Mem0 Cloud
MEM0_API_KEY=m0-...

# Optional: Graph memory
GRAPH_PROVIDER=none            # none, mem0, or graphiti
NEO4J_URL=neo4j+s://...
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=...

# Optional: Ollama fallback
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b

# Optional: Tuning
MEMORY_SEARCH_LIMIT=10
GRAPH_SEARCH_LIMIT=5
PATTERN_CONTEXT_LIMIT=30
EXPERIENCE_LIMIT=5
CONTENT_PREVIEW_LIMIT=1000
PATTERN_PREVIEW_LIMIT=200
```

### Database Setup

Apply the Supabase migration to create tables:

```bash
supabase db push
# or apply manually: supabase/migrations/001_initial_schema.sql
```

---

## Usage

### CLI

```bash
# Search memory
brain recall "content writing patterns"

# Get contextual help
brain ask "Help me write a follow-up email"

# Extract learnings from a work session
brain learn "We tested 3 LinkedIn hooks today..." --category content

# Browse content examples
brain examples --type linkedin

# Browse knowledge repository
brain knowledge --category framework

# Delete an item
brain delete pattern <uuid>
brain delete experience <uuid>
brain delete example <uuid>
brain delete knowledge <uuid>

# Check brain health
brain health

# Migrate markdown data
brain migrate
```

### MCP Server (Claude Code Integration)

The MCP server exposes all agents as tools callable from Claude Code:

```bash
# Run the server
python -m second_brain.mcp_server
```

Add to `.mcp.json` for auto-connection:

```json
{
  "mcpServers": {
    "second-brain": {
      "command": "python",
      "args": ["-m", "second_brain.mcp_server"]
    }
  }
}
```

**Available MCP tools:**

| Tool | Description |
|------|-------------|
| `recall` | Search semantic memory for context and patterns |
| `ask` | Get contextual help powered by brain knowledge |
| `learn` | Extract patterns from work session text |
| `search_examples` | Browse content examples by type |
| `search_knowledge` | Browse knowledge repository by category |
| `delete_item` | Delete an item by table and ID |
| `brain_health` | Check brain health and growth metrics |

---

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test files
python -m pytest tests/test_services.py -v    # Services + HealthService
python -m pytest tests/test_agents.py -v      # Agent schemas + tools
python -m pytest tests/test_mcp_server.py -v  # MCP tool functions
python -m pytest tests/test_migrate.py -v     # Migration tool
python -m pytest tests/test_graph.py -v       # Graph memory
```

**89 tests** covering services, agents, MCP tools, migration, and graph memory. All external services (Mem0, Supabase, LLMs) are mocked.

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.11+ |
| Agent Framework | Pydantic AI |
| Semantic Memory | Mem0 (cloud + local) |
| Structured Storage | Supabase (PostgreSQL + pgvector) |
| LLM Primary | Anthropic Claude |
| LLM Fallback | Ollama |
| MCP Server | FastMCP |
| CLI | Click |
| Config | Pydantic Settings |
| Testing | pytest + pytest-asyncio |
| Build | setuptools with `src/` layout |

---

## Development

```bash
# Verify imports
python -c "from second_brain import __version__; print(f'v{__version__}')"
python -c "from second_brain.config import BrainConfig; print('Config OK')"
python -c "from second_brain.agents import recall_agent, ask_agent; print('Agents OK')"

# Check available CLI commands
python -c "from second_brain.cli import cli; print([c.name for c in cli.commands.values()])"

# Check available MCP tools
python -c "from second_brain.mcp_server import server; print('MCP OK')"
```

---

## License

This project is licensed under the [MIT License](LICENSE).
