# Graphiti Knowledge Graph — Best Practices & Tutorial

A comprehensive guide to setting up, configuring, and operating the Graphiti knowledge graph integration in the Second Brain system.

---

## 1. Overview & Architecture

[Graphiti](https://help.getzep.com/graphiti/getting-started/overview) is a temporal knowledge graph by Zep AI. It extracts entities and relationships from unstructured text, building a queryable graph that evolves over time (bi-temporal model).

### How It Fits in the Second Brain Stack

Graphiti runs as a **dual-write companion** alongside Mem0 semantic memory:

```
MCP Tool Call -> Agent (learn, ask, etc.)
                   |
                   +-> Mem0 (primary semantic memory)
                   +-> Graphiti (knowledge graph — entity/relationship extraction)
```

### Data Model

- **Episodes** — raw content snapshots (text, messages, JSON) ingested into the graph
- **Entity Nodes** — people, concepts, tools, patterns extracted from episodes
- **Entity Edges** — relationships between entities (e.g., "uses", "relates_to", "created_by")
- **Bi-temporal** — each fact has both a `valid_at` time (when it was true) and a `created_at` time (when it was ingested)

### Activation Modes

| Mode | Config | Behavior |
|------|--------|----------|
| Dual-write | `GRAPHITI_ENABLED=true` | Graphiti runs alongside Mem0; learn agent writes to both |
| Replace Mem0 | `MEMORY_PROVIDER=graphiti` | Graphiti replaces Mem0 as the primary memory backend |
| Disabled | `GRAPHITI_ENABLED=false` (default) | Graphiti is not used |

---

## 2. Prerequisites & Setup

### Neo4j Self-Hosted (Docker)

Neo4j is the recommended graph database backend:

```bash
docker run -d --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/your-password \
  -e NEO4J_PLUGINS='["apoc"]' \
  neo4j:5-community
```

Verify at http://localhost:7474 (browser UI).

### Ollama Cloud Setup (for Entity Extraction LLM)

Ollama Cloud provides access to large models (120B+) that reliably produce structured JSON for entity extraction, without requiring local GPU resources:

```bash
ollama signin                          # authenticate with ollama.com
ollama pull deepseek-v3.1:671b-cloud   # pull cloud model metadata
ollama serve                           # start local proxy (localhost:11434)
```

The local proxy forwards requests to Ollama Cloud infrastructure transparently.

### Install with Graphiti Extras

```bash
cd backend
pip install -e ".[dev,graphiti]"
```

This installs `graphiti-core` with Anthropic, FalkorDB, and Voyage AI embedder support.

Verify the Voyage AI embedder is available:

```bash
python -c "from graphiti_core.embedder.voyage import VoyageAIEmbedder; print('OK')"
```

---

## 3. Configuration

### Required `.env` Variables

```bash
# Neo4j
NEO4J_URL=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password

# Graphiti activation
GRAPHITI_ENABLED=true

# Embeddings (Voyage AI — no OpenAI needed!)
VOYAGE_API_KEY=your-voyage-key
GRAPHITI_EMBEDDING_MODEL=voyage-3.5

# LLM for entity extraction (Ollama Cloud)
GRAPHITI_LLM_MODEL=deepseek-v3.1:671b-cloud
OLLAMA_BASE_URL=http://localhost:11434
```

### Configuration Priority

**LLM selection:**
- If `GRAPHITI_LLM_MODEL` is set -> always uses Ollama (even if Anthropic key is present)
- If `GRAPHITI_LLM_MODEL` is not set and `ANTHROPIC_API_KEY` is present -> uses Anthropic
- If neither -> uses default `OLLAMA_MODEL` via Ollama

**Embedder selection:**
- If `VOYAGE_API_KEY` is set -> uses Voyage AI embedder (model from `GRAPHITI_EMBEDDING_MODEL`)
- If no Voyage key -> falls back to OpenAI embedder (`text-embedding-3-small`, requires `OPENAI_API_KEY`)

**Cross-encoder selection:**
- If `OPENAI_API_KEY` is set -> uses OpenAI reranker (`gpt-4.1-mini`)
- If no OpenAI key -> uses Ollama cross-encoder (same model as LLM)

This means a fully functional Graphiti setup requires **only Voyage AI + Ollama Cloud** — no OpenAI dependency.

---

## 4. Ingestion Best Practices

### 4a. Episode Types

| Type | Use For | Example |
|------|---------|---------|
| `EpisodeType.text` | Articles, docs, notes, patterns | Brain content, knowledge entries |
| `EpisodeType.message` | Conversations, transcripts | Zoom transcripts ("Speaker: text") |
| `EpisodeType.json` | Structured data | CRM records, metadata objects |

### 4b. Contextual Chunking (Critical for Quality)

Multi-episode chunked documents produce **more detailed knowledge graphs with richer node and edge extraction** than single-episode ingestion (per Graphiti docs).

**When to chunk:** content > 4000 characters.

**How it works:** Each chunk is prefixed with context from the beginning of the document, helping the LLM maintain entity references across chunk boundaries.

```python
# For long transcripts or documents:
count = await graphiti_service.add_episodes_chunked(
    content=long_transcript,
    metadata={
        "source": "zoom_transcript",
        "client": "ABC Home and Commercial",
        "category": "meeting",
        "reference_time": "2026-01-15T14:30:00Z",
    },
    group_id="uttam",
    chunk_size=4000,
    chunk_overlap=200,
)
```

For short content (< 4000 chars), use `add_episode()` directly.

### 4c. Episode Naming

Use meaningful names derived from source metadata:

- Good: `learn_agent_a1b2c3d4` (source + hash)
- Bad: `episode_a1b2c3d4` (generic, no provenance)

Episode names are set automatically when metadata includes `source` or `category`.

### 4d. Source Descriptions

Detailed `source_description` improves entity extraction quality:

- Good: `"zoom_transcript | category:meeting | client:ABC Home"`
- Bad: `"second-brain"` (too generic)

Source descriptions are built automatically from metadata fields (`source`, `category`, `client`).

### 4e. Reference Time

Always set `reference_time` to when the content was created/occurred, not ingestion time:

- For transcripts: use the meeting date
- For patterns/experiences: use the creation date
- For articles: use the publication date

This enables temporal queries ("what did we know about X in January?").

Pass as ISO 8601 string in metadata:

```python
metadata={"reference_time": "2026-01-15T14:30:00Z"}
```

---

## 5. Batch Ingestion

### Methods

| Method | Use Case | Behavior |
|--------|----------|----------|
| `add_episode()` | Single short content | Direct ingestion |
| `add_episodes_chunked()` | Single long content | Splits into contextual chunks |
| `add_episodes_batch()` | Multiple items | Loops `add_episode()` with error isolation |

### Reingest Script

For full re-ingestion of brain data into Graphiti:

```bash
cd backend
python scripts/reingest_graph.py
```

The script automatically uses `add_episodes_chunked()` for content over 4000 characters.

---

## 6. Community Detection

Communities are clusters of strongly-connected entities, discovered by the Leiden algorithm.

**When to rebuild:** After large ingestion batches (50+ episodes).

**Full rebuild:**
```python
await graphiti._client.build_communities()
```

**Incremental (slower but keeps communities fresh):**
```python
# Pass update_communities=True in add_episode kwargs
# Note: this adds latency per episode
```

---

## 7. Custom Entity Types (Advanced)

Define domain-specific entity types with Pydantic for better extraction:

```python
from pydantic import BaseModel, Field
from typing import Optional

class Client(BaseModel):
    industry: Optional[str] = Field(None, description="Client's industry sector")
    location: Optional[str] = Field(None, description="Client's primary location")

class ServiceRelationship(BaseModel):
    service_type: Optional[str] = Field(None, description="Type of service provided")
    start_date: Optional[str] = Field(None, description="When service started (ISO 8601)")

# Use in add_episode:
entity_types = {"Client": Client, "Person": Person}
edge_types = {"ServiceRelationship": ServiceRelationship}
```

**Protected attribute names** (cannot be used as custom fields):
`uuid`, `name`, `group_id`, `labels`, `created_at`, `summary`, `attributes`, `name_embedding`

All custom attributes must be `Optional` for graceful handling of incomplete data.

---

## 8. Search Patterns

### Basic Search

```python
results = await graphiti_service.search("query", limit=10)
```

### MCP Tool Interface

The `graph_search` MCP tool is the user-facing interface:

```
graph_search("client relationships")
```

Results are formatted as `source --[relationship]--> target`.

### Group-Scoped Search

When `group_id` is configured (via `brain_user_id`), searches are scoped to that user's data.

---

## 9. Operational Guide

### Health Check

- MCP tool: `graph_health`
- CLI: `brain health`
- Programmatic: `await graphiti_service.health_check()`

### Monitoring

Watch for these log messages:

| Log Level | Message | Meaning |
|-----------|---------|---------|
| INFO | "Graphiti initialized with Neo4j" | Successful startup |
| INFO | "Graphiti using Voyage AI embedder" | Voyage embedder active |
| INFO | "Graphiti using Ollama LLM" | Ollama LLM active |
| WARNING | "Graphiti add_episode failed" | Episode ingestion failed (non-critical) |
| WARNING | "Graphiti Neo4j init failed" | Neo4j connection issue |
| ERROR | "Graphiti initialization failed" | No backend available |

### Common Issues

**Neo4j connection refused:**
- Check Docker is running: `docker ps | grep neo4j`
- Check port 7687 is open: `curl -v telnet://localhost:7687`
- Verify credentials match `NEO4J_AUTH` in Docker config

**Ollama Cloud model not found:**
- Run `ollama signin` to authenticate
- Run `ollama pull model-name` to pull model metadata
- Ensure `ollama serve` is running

**Structured JSON errors during entity extraction:**
- Model too small for reliable structured output
- Use 120B+ cloud models (e.g., `deepseek-v3.1:671b-cloud`, `qwen3-coder:480b-cloud`)

**Slow ingestion:**
- Increase `SEMAPHORE_LIMIT` for cloud models (5-8 recommended)
- Use `add_episodes_chunked()` with larger `chunk_size` for fewer API calls

**Dimension mismatch (switching from OpenAI to Voyage embeddings):**
- OpenAI `text-embedding-3-small` uses 1536 dimensions
- Voyage `voyage-3.5` uses 1024 dimensions
- If Neo4j was initialized with OpenAI embeddings, you must reinitialize:

```bash
# WARNING: This deletes all graph data!
# Drop and recreate the Neo4j database, then restart.
# Graphiti will auto-create indexes at the new dimension on next init.
```

---

## 10. Model Recommendations

| Use Case | Recommended Model | Why |
|----------|------------------|-----|
| Entity extraction LLM | `deepseek-v3.1:671b-cloud` | Large enough for reliable structured JSON; cost-effective via Ollama Cloud |
| Embeddings | `voyage-3.5` (1024d) | Best text quality at low cost; outperforms `text-embedding-3-small` |
| Cross-encoder | `gpt-4.1-mini` (if OpenAI key) or same Ollama Cloud model | Reranking quality |
| Alternative LLM | `qwen3-coder:480b-cloud` | Good for technical/code-heavy content |
| Lite embeddings | `voyage-3.5-lite` | Faster, lower cost, slightly less quality |
