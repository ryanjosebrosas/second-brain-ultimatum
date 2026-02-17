# Feature: Voyage Embeddings & Reranking

## Feature Description

Replace OpenAI `text-embedding-3-small` with Voyage AI embeddings for all vector search operations
and add Voyage `rerank-2-lite` reranking as a post-retrieval quality layer across all 5 agents.
This gives the Second Brain higher-quality semantic retrieval (better embeddings) and more
relevant result ordering (cross-encoder reranking) for every search path.

## User Story

As a Second Brain user, I want my brain's retrieval to use state-of-the-art Voyage embeddings
and reranking, so that search results (patterns, memories, experiences, knowledge) are more
relevant and accurately ranked by semantic similarity to my query.

## Problem Statement

The current EmbeddingService uses OpenAI `text-embedding-3-small` (1536 dims) for Supabase vector
search, and Mem0 handles its own embedding internally. Search results are ranked by raw cosine
similarity, which can miss nuanced relevance. There is no reranking layer — results come back
in embedding-distance order, which doesn't account for cross-encoder semantics.

## Solution Statement

- **Decision 1**: Use `voyage-4-lite` for standard embeddings — because `voyage-context-3` uses
  a different API (`contextualized_embed()` with `List[List[str]]` inputs) and CANNOT be used
  with the standard `embed()` method. `voyage-4-lite` is the cost-efficient option at 1024 dims
  default, 32K context, and $0.02/M tokens. See "Key Design Decisions" at bottom for detail.
- **Decision 2**: Use `rerank-2-lite` for post-retrieval reranking — because the user requested
  it specifically. Note: `rerank-2.5-lite` (32K context, better quality) is the newer model and
  could be a drop-in upgrade later. Both use the same API.
- **Decision 3**: Keep Mem0 with its default OpenAI embeddings for internal search — because Mem0
  Cloud (`MemoryClient`) doesn't expose embedder config, and Mem0 Local supports it only via
  LangChain bridge which adds complexity. Instead, we add reranking ON TOP of Mem0 search results.
- **Decision 4**: Change Supabase vector columns from `vector(1536)` to `vector(1024)` — because
  Voyage models output 1024 dims by default. OpenAI's 1536 is not a supported Voyage dimension
  (Voyage supports 256, 512, 1024, 2048). Existing data must be re-embedded.
- **Decision 5**: Replace `OPENAI_API_KEY` dependency in EmbeddingService with `VOYAGE_API_KEY` —
  OpenAI key is still needed for Mem0 but no longer for our EmbeddingService.

## Feature Metadata

- **Feature Type**: Enhancement
- **Estimated Complexity**: Medium-High
- **Primary Systems Affected**: EmbeddingService, all 5 agents, agent utils, config, deps,
  MCP server, migration tool, Supabase schema, conftest
- **Dependencies**: `voyageai` Python package, `VOYAGE_API_KEY` environment variable

---

## CONTEXT REFERENCES

### Relevant Codebase Files

> IMPORTANT: The execution agent MUST read these files before implementing!

- `src/second_brain/services/embeddings.py` (lines 1-82) — Why: REPLACE this entire service
  with Voyage-based implementation. Currently uses OpenAI `text-embedding-3-small`.
- `src/second_brain/config.py` (lines 23-39) — Why: Embedding config fields to update
  (`embedding_model`, `embedding_dimensions`, `embedding_batch_size`, `openai_api_key`)
- `src/second_brain/deps.py` (lines 67-73) — Why: EmbeddingService init wiring. Currently
  gates on `openai_api_key`. Must change to `voyage_api_key`.
- `src/second_brain/agents/utils.py` (lines 1-94) — Why: Add reranking helper here. All agents
  import from this module. Follow existing pattern (`format_memories`, `tool_error`, etc.)
- `src/second_brain/agents/recall.py` (lines 33-51) — Why: `search_semantic_memory` tool needs
  reranking after Mem0 search. Pattern to follow for all agents.
- `src/second_brain/agents/ask.py` (lines 65-120) — Why: `find_relevant_patterns` tool does
  both Mem0 search and Supabase patterns — both need reranking.
- `src/second_brain/agents/create.py` (lines 96-183) — Why: `find_applicable_patterns` tool
  with dual search (Mem0 + Supabase) — needs reranking.
- `src/second_brain/agents/review.py` (lines 41-50) — Why: `load_voice_reference` does storage
  lookup but no ranking — minimal change needed.
- `src/second_brain/agents/learn.py` (lines 38-48) — Why: `inject_existing_patterns` is a
  dynamic instruction, not a search tool — no reranking needed.
- `src/second_brain/services/memory.py` (lines 131-153) — Why: `search()` and
  `search_with_filters()` return `SearchResult`. Reranking happens AFTER these calls.
- `src/second_brain/services/storage.py` (lines 473-511) — Why: `vector_search()` method calls
  Supabase RPC with embedding. Embedding dimensions must match.
- `src/second_brain/mcp_server.py` (lines 644-686) — Why: `vector_search` MCP tool generates
  embedding and calls storage. Must use new EmbeddingService.
- `src/second_brain/migrate.py` (lines 17-30, 295-306) — Why: Migration uses EmbeddingService.
  Must work with new Voyage-based service.
- `src/second_brain/services/retry.py` (lines 1-47) — Why: `async_retry` pattern used by
  current EmbeddingService. Reuse for Voyage calls.
- `supabase/migrations/010_vector_search_rpc.sql` (lines 1-34) — Why: RPC function hardcodes
  `vector(1536)`. Must update to `vector(1024)`.
- `supabase/migrations/001_initial_schema.sql` — Why: `patterns` and `memory_content` tables
  define `embedding vector(1536)`. Must migrate.
- `supabase/migrations/002_examples_knowledge.sql` — Why: `examples` and `knowledge_repo`
  tables define `embedding vector(1536)`. Must migrate.
- `tests/conftest.py` (lines 170-177) — Why: `mock_embedding_service` returns `[0.1] * 1536`.
  Must update to `[0.1] * 1024` and add rerank mock.

### New Files to Create

- `src/second_brain/services/voyage.py` — VoyageService: wraps `voyageai.Client` for embed +
  rerank operations. Single service for both capabilities.
- `supabase/migrations/011_voyage_dimensions.sql` — ALTER embedding columns from
  `vector(1536)` to `vector(1024)`, recreate RPC, rebuild indexes.
- `tests/test_voyage.py` — Unit tests for VoyageService (embed, embed_batch, rerank,
  error handling, fallback behavior).

### Related Memories (from memory.md)

- Memory: `openai package is transitive via mem0ai — no need to add as direct dependency`
  — Relevance: OpenAI stays for Mem0, but we add voyageai as new direct dep.
- Memory: `Mem0 MemoryClient() constructor makes sync HTTP calls that deadlock inside FastMCP's
  async event loop` — Relevance: VoyageService must also be async-safe. Use `asyncio.to_thread`
  for sync Voyage client calls, same pattern as current EmbeddingService.
- Memory: `FastMCP 0.4.1 changed @server.tool() to return original function` — Relevance:
  Tests for MCP tools should call functions directly, not via `.fn()`.
- Memory: `Lazy imports in CLI/deps/MCP require patching at source module` — Relevance:
  VoyageService will be lazy-imported in deps.py; tests must patch at source.
- Memory: `asyncio.timeout(MagicMock()) crashes — mock deps must set config fields to real values`
  — Relevance: Mock config must have real `voyage_api_key` string for timeout tests.

### Relevant Documentation

- [Voyage AI Embeddings](https://docs.voyageai.com/docs/embeddings)
  - Specific section: Python API — `vo.embed()` parameters and return types
  - Why: Core API for embedding generation. `input_type` (query vs document) matters for retrieval.
- [Voyage AI Reranker](https://docs.voyageai.com/docs/reranker)
  - Specific section: Python API — `vo.rerank()` parameters, `RerankingResult` format
  - Why: Core API for reranking. Returns `results` list with `index`, `document`, `relevance_score`.
- [Voyage AI Contextualized Chunk Embeddings](https://docs.voyageai.com/docs/contextualized-chunk-embeddings)
  - Specific section: Model Choices, Python API
  - Why: Documents why `voyage-context-3` uses `contextualized_embed()` not `embed()`.
- [Voyage AI Rate Limits](https://docs.voyageai.com/docs/rate-limits)
  - Specific section: Rate limits table
  - Why: `voyage-4-lite` = 16M TPM / 2000 RPM. `rerank-2-lite` = 4M TPM / 2000 RPM.
- [Voyage AI Pricing](https://docs.voyageai.com/docs/pricing)
  - Specific section: Text Embeddings, Rerankers
  - Why: `voyage-4-lite` = $0.02/M tokens (200M free). `rerank-2-lite` pricing.
- [Mem0 Reranker-Enhanced Search](https://docs.mem0.ai/open-source/features/reranker-search)
  - Why: Mem0 has BUILT-IN reranker support but only for Cohere, Sentence Transformer,
    HuggingFace, LLM, Zero Entropy — NOT Voyage. We rerank externally instead.
- [Mem0 Embedder Overview](https://docs.mem0.ai/components/embedders/overview)
  - Why: Mem0 supports OpenAI, Ollama, HuggingFace, etc. but NOT Voyage natively.
    LangChain bridge exists but adds dependency complexity.

### Patterns to Follow

**EmbeddingService pattern** (from `src/second_brain/services/embeddings.py:12-82`):
```python
class EmbeddingService:
    def __init__(self, config: "BrainConfig"):
        self.config = config
        self._client = None
        self._model = config.embedding_model
        self._dimensions = config.embedding_dimensions

    def _get_client(self):
        """Lazy-init client."""
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.config.openai_api_key)
        return self._client

    async def embed(self, text: str) -> list[float]:
        from second_brain.services.retry import async_retry
        client = self._get_client()
        def _call():
            response = client.embeddings.create(input=text, model=self._model, dimensions=self._dimensions)
            return response.data[0].embedding
        return await async_retry(_call)
```
- Why: Mirror this pattern exactly for VoyageService. Lazy client init, async via `async_retry`.
- Gotcha: `voyageai.Client()` is sync. Must use `asyncio.to_thread` or `async_retry` wrapper.

**Agent tool search pattern** (from `src/second_brain/agents/recall.py:33-51`):
```python
@recall_agent.tool
async def search_semantic_memory(ctx: RunContext[BrainDeps], query: str) -> str:
    try:
        result = await ctx.deps.memory_service.search(query)
        relations = await search_with_graph_fallback(ctx.deps, query, result.relations)
        if not result.memories and not relations:
            return "No semantic matches found."
        parts = [format_memories(result.memories)]
        # ... format and return
    except Exception as e:
        return tool_error("search_semantic_memory", e)
```
- Why: Reranking inserts between search and formatting: `search → rerank → format`.
- Gotcha: Reranking is optional (graceful degradation if Voyage unavailable).

**Config field pattern** (from `src/second_brain/config.py:23-39`):
```python
embedding_model: str = Field(
    default="text-embedding-3-small",
    description="OpenAI embedding model for vector search",
)
embedding_dimensions: int = Field(
    default=1536, ge=256, le=3072,
    description="Embedding vector dimensions.",
)
```
- Why: Add `voyage_api_key`, `voyage_embedding_model`, `voyage_rerank_model` following this pattern.
- Gotcha: Keep `openai_api_key` — Mem0 still needs it.

**Test fixture pattern** (from `tests/conftest.py:170-177`):
```python
@pytest.fixture
def mock_embedding_service():
    service = MagicMock()
    service.embed = AsyncMock(return_value=[0.1] * 1536)
    service.embed_batch = AsyncMock(return_value=[[0.1] * 1536])
    service.close = AsyncMock()
    return service
```
- Why: Update dimensions to 1024 and add `rerank` mock method.

**Retry pattern** (from `src/second_brain/services/retry.py:33-47`):
```python
async def async_retry(func, *args, config: RetryConfig | None = None, **kwargs):
    cfg = config or DEFAULT_RETRY
    @retry(stop=stop_after_attempt(cfg.max_attempts), ...)
    def _call():
        return func(*args, **kwargs)
    return await asyncio.to_thread(_call)
```
- Why: Use for all Voyage API calls. Handles transient failures and runs sync code in thread.

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation (Config + Service)

Add the `voyageai` dependency, Voyage config fields, and the core VoyageService that provides
both embedding and reranking capabilities via a single `voyageai.Client`.

**Tasks:**
- Add `voyageai` to pyproject.toml dependencies
- Add Voyage config fields to BrainConfig (API key, model names, rerank settings)
- Create `VoyageService` with `embed()`, `embed_batch()`, `rerank()` methods
- Wire VoyageService into `deps.py` as replacement for EmbeddingService

### Phase 2: Core Implementation (Reranking Layer)

Add a shared reranking utility to `agents/utils.py` that all agents can use, and update the
EmbeddingService to delegate to VoyageService.

**Tasks:**
- Add `rerank_results()` helper to `agents/utils.py`
- Refactor EmbeddingService to use VoyageService internally (keeps interface, swaps backend)
- Create Supabase migration for `vector(1024)` dimensions

### Phase 3: Integration (Agents + Interfaces)

Wire reranking into every agent search tool and update MCP/migration interfaces.

**Tasks:**
- Add reranking to recall agent search tools
- Add reranking to ask agent search tools
- Add reranking to create agent pattern search
- Update MCP `vector_search` tool for new dimensions
- Update migration tool for new EmbeddingService

### Phase 4: Testing & Validation

Comprehensive tests for VoyageService, reranking, and updated fixtures.

**Tasks:**
- Create `test_voyage.py` with VoyageService unit tests
- Update `conftest.py` fixtures for 1024 dims and rerank mock
- Add reranking integration tests in existing agent test files
- Run full test suite and validate no regressions

---

## STEP-BY-STEP TASKS

### UPDATE `pyproject.toml`

- **IMPLEMENT**: Add `voyageai` to dependencies list. Add `voyage` optional dependency group.
  ```toml
  dependencies = [
      ...
      "voyageai>=0.3.0,<1.0.0",
  ]

  [project.optional-dependencies]
  voyage = ["voyageai>=0.3.0,<1.0.0"]
  ```
- **PATTERN**: Follow existing dep format in `pyproject.toml:6-15` (range pins with `>=,<`)
- **IMPORTS**: N/A (config file)
- **GOTCHA**: `voyageai` is the official PyPI package. Check latest version on PyPI. The package
  exposes `voyageai.Client()` which auto-reads `VOYAGE_API_KEY` env var.
- **VALIDATE**: `pip install -e ".[dev]" && python -c "import voyageai; print(voyageai.__version__)"`

### UPDATE `src/second_brain/config.py`

- **IMPLEMENT**: Add Voyage-specific config fields. Keep `openai_api_key` for Mem0.
  Add new fields after the existing embedding fields block (after line 39):
  ```python
  # Voyage AI
  voyage_api_key: str | None = Field(
      default=None, description="Voyage AI API key for embeddings and reranking",
      repr=False,
  )
  voyage_embedding_model: str = Field(
      default="voyage-4-lite",
      description="Voyage embedding model. Options: voyage-4-large, voyage-4, voyage-4-lite",
  )
  voyage_rerank_model: str = Field(
      default="rerank-2-lite",
      description="Voyage rerank model. Options: rerank-2.5, rerank-2.5-lite, rerank-2-lite",
  )
  voyage_rerank_top_k: int = Field(
      default=10,
      ge=1,
      le=100,
      description="Number of top results to return after reranking. Range: 1-100.",
  )
  ```
  Update `embedding_model` default from `"text-embedding-3-small"` to `"voyage-4-lite"`.
  Update `embedding_dimensions` default from `1536` to `1024`, and `le` from `3072` to `2048`.
  Update `embedding_model` description from `"OpenAI embedding model"` to `"Embedding model for
  vector search"`.
- **PATTERN**: Follow existing Field pattern at `config.py:14-39`. Group with comment.
- **IMPORTS**: No new imports needed (Pydantic Field already imported)
- **GOTCHA**: Changing `embedding_dimensions` default from 1536 to 1024 affects all new configs.
  Existing `.env` files with explicit `EMBEDDING_DIMENSIONS=1536` will override. Document this.
- **VALIDATE**: `python -c "from second_brain.config import BrainConfig; c = BrainConfig(supabase_url='x', supabase_key='y', brain_data_path='.', _env_file=None); print(c.voyage_embedding_model, c.embedding_dimensions)"`

### CREATE `src/second_brain/services/voyage.py`

- **IMPLEMENT**: VoyageService wrapping `voyageai.Client` with embed, embed_batch, and rerank
  methods. Follow EmbeddingService pattern exactly (lazy client init, async_retry, logging).
  ```python
  """Voyage AI embedding and reranking service."""

  import logging
  from typing import TYPE_CHECKING

  if TYPE_CHECKING:
      from second_brain.config import BrainConfig

  logger = logging.getLogger(__name__)


  class VoyageService:
      """Voyage AI embeddings + reranking via voyageai Python SDK.

      Provides embed(), embed_batch() for vector generation and
      rerank() for post-retrieval relevance scoring.
      """

      def __init__(self, config: "BrainConfig"):
          self.config = config
          self._client = None
          self._embed_model = config.voyage_embedding_model
          self._rerank_model = config.voyage_rerank_model
          self._dimensions = config.embedding_dimensions

      def _get_client(self):
          """Lazy-init Voyage client."""
          if self._client is None:
              if not self.config.voyage_api_key:
                  raise ValueError(
                      "VOYAGE_API_KEY required for Voyage AI. "
                      "Set it in .env or pass via config."
                  )
              import voyageai
              self._client = voyageai.Client(api_key=self.config.voyage_api_key)
          return self._client

      async def embed(self, text: str) -> list[float]:
          """Generate embedding for a single text string."""
          from second_brain.services.retry import async_retry
          client = self._get_client()

          def _call():
              result = client.embed(
                  [text],
                  model=self._embed_model,
                  input_type="document",
                  output_dimension=self._dimensions,
              )
              return result.embeddings[0]

          return await async_retry(_call)

      async def embed_query(self, text: str) -> list[float]:
          """Generate embedding for a search query (uses input_type='query')."""
          from second_brain.services.retry import async_retry
          client = self._get_client()

          def _call():
              result = client.embed(
                  [text],
                  model=self._embed_model,
                  input_type="query",
                  output_dimension=self._dimensions,
              )
              return result.embeddings[0]

          return await async_retry(_call)

      async def embed_batch(
          self, texts: list[str], input_type: str = "document"
      ) -> list[list[float]]:
          """Generate embeddings for a batch of texts.

          Respects Voyage batch limit of 128 items per request.
          """
          from second_brain.services.retry import async_retry
          client = self._get_client()
          batch_size = min(self.config.embedding_batch_size, 128)
          all_embeddings: list[list[float]] = []

          for i in range(0, len(texts), batch_size):
              batch = texts[i:i + batch_size]

              def _call(b=batch):
                  result = client.embed(
                      b,
                      model=self._embed_model,
                      input_type=input_type,
                      output_dimension=self._dimensions,
                  )
                  return result.embeddings

              embeddings = await async_retry(_call)
              all_embeddings.extend(embeddings)

          return all_embeddings

      async def rerank(
          self,
          query: str,
          documents: list[str],
          top_k: int | None = None,
      ) -> list[dict]:
          """Rerank documents by relevance to query.

          Args:
              query: The search query.
              documents: List of document strings to rerank.
              top_k: Number of top results. None = use config default.

          Returns:
              List of dicts with 'index', 'document', 'relevance_score',
              sorted by descending relevance.
          """
          if not documents:
              return []

          from second_brain.services.retry import async_retry
          client = self._get_client()
          k = top_k or self.config.voyage_rerank_top_k

          def _call():
              result = client.rerank(
                  query,
                  documents,
                  model=self._rerank_model,
                  top_k=k,
              )
              return [
                  {
                      "index": r.index,
                      "document": r.document,
                      "relevance_score": r.relevance_score,
                  }
                  for r in result.results
              ]

          return await async_retry(_call)

      async def close(self) -> None:
          """Release Voyage client resources."""
          self._client = None
  ```
- **PATTERN**: Mirror `services/embeddings.py:12-82` exactly (lazy init, async_retry, logging)
- **IMPORTS**: `voyageai` (lazy inside `_get_client`), `async_retry` (lazy inside methods)
- **GOTCHA**: Voyage `embed()` takes a LIST of strings, not a single string. Always wrap in
  `[text]` and extract `[0]`. Voyage batch limit is 128 items (not configurable). Use
  `input_type="query"` for search queries and `"document"` for stored content.
- **VALIDATE**: `python -c "from second_brain.services.voyage import VoyageService; print('OK')"`

### UPDATE `src/second_brain/services/embeddings.py`

- **IMPLEMENT**: Refactor to delegate to VoyageService when Voyage API key is available,
  falling back to OpenAI. This preserves the existing interface (`embed`, `embed_batch`, `close`)
  while adding Voyage as the primary backend.
  ```python
  """Embedding generation service — Voyage AI primary, OpenAI fallback."""

  import logging
  from typing import TYPE_CHECKING

  if TYPE_CHECKING:
      from second_brain.config import BrainConfig

  logger = logging.getLogger(__name__)


  class EmbeddingService:
      """Generate text embeddings.

      Uses Voyage AI (voyage-4-lite) when VOYAGE_API_KEY is set.
      Falls back to OpenAI text-embedding-3-small when only OPENAI_API_KEY is set.
      """

      def __init__(self, config: "BrainConfig"):
          self.config = config
          self._voyage = None
          self._openai_client = None
          self._model = config.embedding_model
          self._dimensions = config.embedding_dimensions

          # Determine backend
          if config.voyage_api_key:
              from second_brain.services.voyage import VoyageService
              self._voyage = VoyageService(config)
              logger.info("EmbeddingService using Voyage AI (%s)", config.voyage_embedding_model)
          elif config.openai_api_key:
              logger.info("EmbeddingService using OpenAI fallback (%s)", config.embedding_model)
          else:
              raise ValueError(
                  "Either VOYAGE_API_KEY or OPENAI_API_KEY required for embeddings."
              )

      def _get_openai_client(self):
          """Lazy-init OpenAI client (fallback only)."""
          if self._openai_client is None:
              from openai import OpenAI
              self._openai_client = OpenAI(api_key=self.config.openai_api_key)
          return self._openai_client

      async def embed(self, text: str) -> list[float]:
          """Generate embedding for a single text string."""
          if self._voyage:
              return await self._voyage.embed(text)

          from second_brain.services.retry import async_retry
          client = self._get_openai_client()
          def _call():
              response = client.embeddings.create(
                  input=text, model=self._model, dimensions=self._dimensions,
              )
              return response.data[0].embedding
          return await async_retry(_call)

      async def embed_query(self, text: str) -> list[float]:
          """Generate embedding optimized for search queries.

          Uses Voyage input_type='query' for better retrieval.
          Falls back to standard embed() for OpenAI.
          """
          if self._voyage:
              return await self._voyage.embed_query(text)
          return await self.embed(text)

      async def embed_batch(self, texts: list[str]) -> list[list[float]]:
          """Generate embeddings for a batch of texts."""
          if self._voyage:
              return await self._voyage.embed_batch(texts)

          from second_brain.services.retry import async_retry
          client = self._get_openai_client()
          batch_size = self.config.embedding_batch_size
          all_embeddings: list[list[float]] = []
          for i in range(0, len(texts), batch_size):
              batch = texts[i:i + batch_size]
              def _call(b=batch):
                  response = client.embeddings.create(
                      input=b, model=self._model, dimensions=self._dimensions,
                  )
                  return [item.embedding for item in response.data]
              embeddings = await async_retry(_call)
              all_embeddings.extend(embeddings)
          return all_embeddings

      async def close(self) -> None:
          """Release client resources."""
          if self._voyage:
              await self._voyage.close()
          self._openai_client = None
  ```
- **PATTERN**: Keep same public interface as current `embeddings.py:12-82`. Add delegation.
- **IMPORTS**: `VoyageService` (conditional, in `__init__`), `OpenAI` (lazy, fallback)
- **GOTCHA**: Import `VoyageService` at init time (not at module level) to avoid import errors
  when `voyageai` is not installed. The fallback path must still work without `voyageai`.
- **VALIDATE**: `python -c "from second_brain.services.embeddings import EmbeddingService; print('OK')"`

### UPDATE `src/second_brain/deps.py`

- **IMPLEMENT**: Update EmbeddingService initialization to prefer Voyage API key. Add
  VoyageService reference to BrainDeps for direct reranking access by agents.
  Add `voyage_service` field to BrainDeps dataclass:
  ```python
  from second_brain.services.voyage import VoyageService  # in TYPE_CHECKING block

  @dataclass
  class BrainDeps:
      # ... existing fields ...
      voyage_service: "VoyageService | None" = None
  ```
  Update `create_deps()` — change the embedding init block (lines 67-73):
  ```python
  embedding = None
  voyage = None
  if config.voyage_api_key:
      try:
          from second_brain.services.voyage import VoyageService
          voyage = VoyageService(config)
          from second_brain.services.embeddings import EmbeddingService
          embedding = EmbeddingService(config)
      except Exception as e:
          logger.warning("VoyageService init failed: %s", e)
  elif config.openai_api_key:
      try:
          from second_brain.services.embeddings import EmbeddingService
          embedding = EmbeddingService(config)
      except Exception as e:
          logger.warning("EmbeddingService init failed: %s", e)
  ```
  Pass `voyage_service=voyage` to BrainDeps constructor.
- **PATTERN**: Follow existing lazy import pattern at `deps.py:49-65` (try/except ImportError)
- **IMPORTS**: Add `VoyageService` to TYPE_CHECKING block at line 8
- **GOTCHA**: EmbeddingService now internally creates VoyageService too. To avoid double init,
  either pass the VoyageService instance or let EmbeddingService create its own. The simplest
  approach: let EmbeddingService create its own VoyageService internally (it already does this
  in the updated `__init__`), and also create a standalone VoyageService in deps for direct
  reranking access. The voyageai.Client is lightweight (no connection pool), so double init is fine.
- **VALIDATE**: `python -c "from second_brain.deps import BrainDeps; print(BrainDeps.__dataclass_fields__.keys())"`

### UPDATE `src/second_brain/agents/utils.py`

- **IMPLEMENT**: Add `rerank_memories()` async helper that reranks Mem0 search results using
  VoyageService. This is the shared reranking entry point for all agents.
  Add after `search_with_graph_fallback()` (after line 77):
  ```python
  async def rerank_memories(
      deps: "BrainDeps",
      query: str,
      memories: list[dict],
      top_k: int | None = None,
  ) -> list[dict]:
      """Rerank Mem0 search results using Voyage reranker.

      Graceful degradation: returns original memories if Voyage unavailable.

      Args:
          deps: BrainDeps with optional voyage_service.
          query: Original search query.
          memories: Raw Mem0 results (dicts with 'memory'/'result' key).
          top_k: Max results after reranking. None = config default.

      Returns:
          Reranked list of memory dicts, or original list if reranking unavailable.
      """
      if not deps.voyage_service or not memories:
          return memories

      # Extract text from memory dicts
      documents = [
          m.get("memory", m.get("result", ""))
          for m in memories
      ]
      documents = [d for d in documents if d]  # filter empties

      if not documents:
          return memories

      try:
          reranked = await deps.voyage_service.rerank(query, documents, top_k=top_k)
          # Rebuild memory dicts in reranked order
          result = []
          for r in reranked:
              idx = r["index"]
              if idx < len(memories):
                  mem = dict(memories[idx])
                  mem["rerank_score"] = r["relevance_score"]
                  result.append(mem)
          return result
      except Exception as e:
          logger.debug("Reranking failed (non-critical): %s", e)
          return memories
  ```
- **PATTERN**: Follow `search_with_graph_fallback` pattern at `utils.py:53-77` — optional
  service, graceful degradation, debug-level logging on failure.
- **IMPORTS**: No new imports (uses existing TYPE_CHECKING `BrainDeps`)
- **GOTCHA**: Memory dicts have inconsistent keys — some use `"memory"`, others `"result"`.
  Extract with `m.get("memory", m.get("result", ""))`. The reranked list must preserve the
  original dict structure (not just return strings), so we rebuild from the original list
  using the reranker's `index` field.
- **VALIDATE**: `python -c "from second_brain.agents.utils import rerank_memories; print('OK')"`

### UPDATE `src/second_brain/agents/recall.py`

- **IMPLEMENT**: Add reranking to `search_semantic_memory` and `search_patterns` tools.
  Import `rerank_memories` from utils. Insert reranking between search and formatting.

  In `search_semantic_memory` (line 39), after `result = await ctx.deps.memory_service.search(query)`:
  ```python
  # Rerank results for better relevance ordering
  memories = await rerank_memories(ctx.deps, query, result.memories)
  ```
  Then use `memories` instead of `result.memories` in the formatting below.

  In `search_patterns` (line 67-73), after getting `semantic_results`:
  ```python
  semantic_results = await rerank_memories(ctx.deps, topic or "patterns", semantic_results)
  ```

  Update import at line 7-11 to include `rerank_memories`.
- **PATTERN**: Follow existing tool pattern at `recall.py:33-51`
- **IMPORTS**: `from second_brain.agents.utils import rerank_memories` (add to existing import)
- **GOTCHA**: `search_patterns` searches both Mem0 (semantic) and Supabase (structured). Only
  rerank the Mem0 results — Supabase patterns are already sorted by confidence.
- **VALIDATE**: `python -m pytest tests/test_agents.py -v -k recall`

### UPDATE `src/second_brain/agents/ask.py`

- **IMPLEMENT**: Add reranking to `find_relevant_patterns` and `find_similar_experiences`.

  In `find_relevant_patterns` (line 72), after `result = await ctx.deps.memory_service.search(query)`:
  ```python
  reranked_memories = await rerank_memories(ctx.deps, query, result.memories)
  ```
  Use `reranked_memories` in the formatting loop at line 91.

  Also rerank `pattern_memories` after line 82:
  ```python
  pattern_memories = await rerank_memories(ctx.deps, query, pattern_memories)
  ```

  In `find_similar_experiences` (line 129), rerank the Mem0 results:
  ```python
  result = await ctx.deps.memory_service.search(f"past experience: {query}", enable_graph=True)
  reranked = await rerank_memories(ctx.deps, query, result.memories)
  ```

  Update import to include `rerank_memories`.
- **PATTERN**: Follow existing pattern at `ask.py:65-120`
- **IMPORTS**: `from second_brain.agents.utils import rerank_memories` (add to existing import)
- **GOTCHA**: `find_relevant_patterns` has TWO Mem0 searches (general + pattern-filtered).
  Rerank both independently — they serve different purposes.
- **VALIDATE**: `python -m pytest tests/test_agents.py -v -k ask`

### UPDATE `src/second_brain/agents/create.py`

- **IMPLEMENT**: Add reranking to `find_applicable_patterns` tool.

  After the general Mem0 search at line 104:
  ```python
  result = await ctx.deps.memory_service.search(topic)
  reranked_general = await rerank_memories(ctx.deps, topic, result.memories)
  ```

  After the pattern-filtered search at line 125:
  ```python
  pattern_memories = await rerank_memories(ctx.deps, topic, pattern_memories)
  ```

  Use `reranked_general` instead of `result.memories` in the formatting at line 168-173.

  Update import to include `rerank_memories`.
- **PATTERN**: Follow existing pattern at `create.py:96-183`
- **IMPORTS**: `from second_brain.agents.utils import rerank_memories` (add to existing import)
- **GOTCHA**: `find_applicable_patterns` merges Mem0 semantic, Supabase structured, and graph
  results. Only rerank the Mem0 results. Supabase patterns are confidence-sorted.
- **VALIDATE**: `python -m pytest tests/test_agents.py -v -k create`

### UPDATE `src/second_brain/mcp_server.py`

- **IMPLEMENT**: Update the `vector_search` MCP tool to use `embed_query()` instead of `embed()`
  for better retrieval quality (Voyage differentiates query vs document embeddings).

  At line 674, change:
  ```python
  embedding = await deps.embedding_service.embed(query)
  ```
  to:
  ```python
  embedding = await deps.embedding_service.embed_query(query)
  ```

  Also update the error message at line 669 from "OPENAI_API_KEY" to
  "VOYAGE_API_KEY or OPENAI_API_KEY".
- **PATTERN**: Follow existing MCP tool pattern at `mcp_server.py:644-686`
- **IMPORTS**: No new imports needed
- **GOTCHA**: `embed_query` is a new method that falls back to `embed` for OpenAI backend.
  Voyage uses `input_type="query"` for search queries which improves retrieval vs using
  `input_type="document"` for everything.
- **VALIDATE**: `python -c "from second_brain.mcp_server import server; print('OK')"`

### UPDATE `src/second_brain/migrate.py`

- **IMPLEMENT**: No changes needed to the migration tool itself — it already uses
  `EmbeddingService.embed()` which now delegates to Voyage when available. The only change:
  ensure the `_get_embedding` method at line 24 handles the new dimensions correctly.
  Verify that the migration entry point at line 295-306 still works (it creates EmbeddingService
  from config, which will now prefer Voyage).
- **PATTERN**: Existing pattern at `migrate.py:17-30`
- **IMPORTS**: No changes needed
- **GOTCHA**: Re-migration is needed after switching to Voyage because existing embeddings are
  1536-dim (OpenAI) and the new schema will be 1024-dim (Voyage). Run full migration after
  deploying the DB schema change.
- **VALIDATE**: `python -c "from second_brain.migrate import BrainMigrator; print('OK')"`

### CREATE `supabase/migrations/011_voyage_dimensions.sql`

- **IMPLEMENT**: Alter all embedding columns from `vector(1536)` to `vector(1024)`.
  Drop and recreate the `vector_search` RPC function. Rebuild ivfflat indexes.
  ```sql
  -- Migrate embedding columns from OpenAI (1536) to Voyage (1024) dimensions
  -- WARNING: This drops existing embeddings. Re-run migration after deployment.

  -- Step 1: Drop indexes that depend on embedding columns
  DROP INDEX IF EXISTS patterns_embedding_idx;
  DROP INDEX IF EXISTS memory_content_embedding_idx;
  DROP INDEX IF EXISTS examples_embedding_idx;
  DROP INDEX IF EXISTS knowledge_repo_embedding_idx;

  -- Step 2: Drop the old vector_search function (depends on vector(1536))
  DROP FUNCTION IF EXISTS vector_search(vector(1536), TEXT, INT, FLOAT);

  -- Step 3: Alter embedding columns to vector(1024)
  ALTER TABLE patterns ALTER COLUMN embedding TYPE vector(1024) USING NULL;
  ALTER TABLE memory_content ALTER COLUMN embedding TYPE vector(1024) USING NULL;
  ALTER TABLE examples ALTER COLUMN embedding TYPE vector(1024) USING NULL;
  ALTER TABLE knowledge_repo ALTER COLUMN embedding TYPE vector(1024) USING NULL;

  -- Step 4: Recreate indexes for vector(1024)
  CREATE INDEX IF NOT EXISTS patterns_embedding_idx
    ON patterns USING ivfflat (embedding vector_cosine_ops) WITH (lists = 10);
  CREATE INDEX IF NOT EXISTS memory_content_embedding_idx
    ON memory_content USING ivfflat (embedding vector_cosine_ops) WITH (lists = 10);
  CREATE INDEX IF NOT EXISTS examples_embedding_idx
    ON examples USING ivfflat (embedding vector_cosine_ops) WITH (lists = 10);
  CREATE INDEX IF NOT EXISTS knowledge_repo_embedding_idx
    ON knowledge_repo USING ivfflat (embedding vector_cosine_ops) WITH (lists = 10);

  -- Step 5: Recreate vector_search RPC with vector(1024)
  CREATE OR REPLACE FUNCTION vector_search(
    query_embedding vector(1024),
    match_table TEXT,
    match_count INT DEFAULT 10,
    match_threshold FLOAT DEFAULT 0.7
  )
  RETURNS TABLE (
    id UUID,
    content TEXT,
    title TEXT,
    category TEXT,
    similarity FLOAT
  )
  LANGUAGE plpgsql
  AS $$
  BEGIN
    RETURN QUERY EXECUTE format(
      'SELECT id, COALESCE(content, pattern_text, '''') as content, '
      'COALESCE(title, name, '''') as title, '
      'COALESCE(category, topic, '''') as category, '
      '1 - (embedding <=> $1) as similarity '
      'FROM %I '
      'WHERE embedding IS NOT NULL '
      'AND 1 - (embedding <=> $1) >= $2 '
      'ORDER BY embedding <=> $1 '
      'LIMIT $3',
      match_table
    ) USING query_embedding, match_threshold, match_count;
  END;
  $$;

  INSERT INTO schema_migrations (version, description)
  VALUES ('011_voyage_dimensions', 'Migrate embedding columns from vector(1536) to vector(1024) for Voyage AI')
  ON CONFLICT (version) DO NOTHING;
  ```
- **PATTERN**: Follow existing migration format at `010_vector_search_rpc.sql:1-38`
- **IMPORTS**: N/A (SQL)
- **GOTCHA**: `USING NULL` in ALTER drops existing embeddings. This is intentional — existing
  OpenAI 1536-dim vectors are incompatible with Voyage 1024-dim. Must re-embed after migration.
  The DROP FUNCTION needs the exact old signature `vector(1536)` to match.
- **VALIDATE**: Apply to Supabase via dashboard or `supabase db push`

### CREATE `tests/test_voyage.py`

- **IMPLEMENT**: Unit tests for VoyageService covering embed, embed_batch, rerank, error handling.
  ```python
  """Tests for VoyageService — Voyage AI embedding and reranking."""

  import pytest
  from unittest.mock import MagicMock, patch, AsyncMock

  from second_brain.services.voyage import VoyageService


  @pytest.fixture
  def voyage_config(tmp_path):
      from second_brain.config import BrainConfig
      return BrainConfig(
          voyage_api_key="test-voyage-key",
          voyage_embedding_model="voyage-4-lite",
          voyage_rerank_model="rerank-2-lite",
          voyage_rerank_top_k=5,
          embedding_dimensions=1024,
          supabase_url="https://test.supabase.co",
          supabase_key="test-key",
          brain_data_path=tmp_path,
          _env_file=None,
      )


  class TestVoyageServiceEmbed:
      @patch("second_brain.services.voyage.voyageai")
      async def test_embed_single(self, mock_voyageai, voyage_config):
          mock_client = MagicMock()
          mock_result = MagicMock()
          mock_result.embeddings = [[0.1] * 1024]
          mock_client.embed.return_value = mock_result
          mock_voyageai.Client.return_value = mock_client

          service = VoyageService(voyage_config)
          result = await service.embed("test text")

          assert len(result) == 1024
          mock_client.embed.assert_called_once_with(
              ["test text"],
              model="voyage-4-lite",
              input_type="document",
              output_dimension=1024,
          )

      @patch("second_brain.services.voyage.voyageai")
      async def test_embed_query(self, mock_voyageai, voyage_config):
          mock_client = MagicMock()
          mock_result = MagicMock()
          mock_result.embeddings = [[0.2] * 1024]
          mock_client.embed.return_value = mock_result
          mock_voyageai.Client.return_value = mock_client

          service = VoyageService(voyage_config)
          result = await service.embed_query("search query")

          mock_client.embed.assert_called_once_with(
              ["search query"],
              model="voyage-4-lite",
              input_type="query",
              output_dimension=1024,
          )

      @patch("second_brain.services.voyage.voyageai")
      async def test_embed_batch(self, mock_voyageai, voyage_config):
          mock_client = MagicMock()
          mock_result = MagicMock()
          mock_result.embeddings = [[0.1] * 1024, [0.2] * 1024]
          mock_client.embed.return_value = mock_result
          mock_voyageai.Client.return_value = mock_client

          service = VoyageService(voyage_config)
          result = await service.embed_batch(["text1", "text2"])

          assert len(result) == 2
          assert len(result[0]) == 1024

      async def test_embed_no_api_key(self, tmp_path):
          from second_brain.config import BrainConfig
          config = BrainConfig(
              voyage_api_key=None,
              supabase_url="https://test.supabase.co",
              supabase_key="test-key",
              brain_data_path=tmp_path,
              _env_file=None,
          )
          service = VoyageService(config)
          with pytest.raises(ValueError, match="VOYAGE_API_KEY"):
              await service.embed("test")


  class TestVoyageServiceRerank:
      @patch("second_brain.services.voyage.voyageai")
      async def test_rerank(self, mock_voyageai, voyage_config):
          mock_client = MagicMock()
          mock_rr1 = MagicMock(index=2, document="doc C", relevance_score=0.95)
          mock_rr2 = MagicMock(index=0, document="doc A", relevance_score=0.80)
          mock_result = MagicMock()
          mock_result.results = [mock_rr1, mock_rr2]
          mock_client.rerank.return_value = mock_result
          mock_voyageai.Client.return_value = mock_client

          service = VoyageService(voyage_config)
          result = await service.rerank("query", ["doc A", "doc B", "doc C"], top_k=2)

          assert len(result) == 2
          assert result[0]["index"] == 2
          assert result[0]["relevance_score"] == 0.95
          mock_client.rerank.assert_called_once_with(
              "query", ["doc A", "doc B", "doc C"],
              model="rerank-2-lite", top_k=2,
          )

      @patch("second_brain.services.voyage.voyageai")
      async def test_rerank_empty_documents(self, mock_voyageai, voyage_config):
          service = VoyageService(voyage_config)
          result = await service.rerank("query", [])
          assert result == []

      async def test_close(self, voyage_config):
          service = VoyageService(voyage_config)
          await service.close()
          assert service._client is None
  ```
- **PATTERN**: Follow `tests/test_services.py` patterns — `@patch` for external deps,
  `async def test_*`, assert on return values and call args.
- **IMPORTS**: `pytest`, `MagicMock`, `patch`, `AsyncMock`, `VoyageService`, `BrainConfig`
- **GOTCHA**: Must patch `voyageai` at `second_brain.services.voyage.voyageai` (source module).
  The `voyageai.Client()` is sync — mock it normally (not AsyncMock).
- **VALIDATE**: `python -m pytest tests/test_voyage.py -v`

### UPDATE `tests/conftest.py`

- **IMPLEMENT**: Update `mock_embedding_service` to return 1024-dim vectors. Add
  `mock_voyage_service` fixture with rerank capability. Update `brain_config` to include
  Voyage fields.

  Update `mock_embedding_service` (line 171-177):
  ```python
  @pytest.fixture
  def mock_embedding_service():
      service = MagicMock()
      service.embed = AsyncMock(return_value=[0.1] * 1024)
      service.embed_query = AsyncMock(return_value=[0.1] * 1024)
      service.embed_batch = AsyncMock(return_value=[[0.1] * 1024])
      service.close = AsyncMock()
      return service
  ```

  Add new fixture after `mock_embedding_service`:
  ```python
  @pytest.fixture
  def mock_voyage_service():
      service = MagicMock()
      service.embed = AsyncMock(return_value=[0.1] * 1024)
      service.embed_query = AsyncMock(return_value=[0.1] * 1024)
      service.embed_batch = AsyncMock(return_value=[[0.1] * 1024])
      service.rerank = AsyncMock(return_value=[
          {"index": 0, "document": "Test memory content", "relevance_score": 0.95},
      ])
      service.close = AsyncMock()
      return service
  ```

  Update `mock_deps` to include `voyage_service`:
  ```python
  @pytest.fixture
  def mock_deps(brain_config, mock_memory, mock_storage, mock_embedding_service, mock_voyage_service):
      return BrainDeps(
          config=brain_config,
          memory_service=mock_memory,
          storage_service=mock_storage,
          embedding_service=mock_embedding_service,
          voyage_service=mock_voyage_service,
      )
  ```
- **PATTERN**: Follow existing fixture patterns at `conftest.py:170-207`
- **IMPORTS**: No new imports needed
- **GOTCHA**: Changing 1536 → 1024 in mock_embedding_service will affect any test that
  asserts on embedding length. Search for `1536` in all test files and update.
- **VALIDATE**: `python -m pytest tests/conftest.py --collect-only`

### ADD reranking tests to existing test files

- **IMPLEMENT**: Add 2-3 tests per agent file verifying reranking behavior:
  1. Test that `rerank_memories` returns reranked results when voyage_service is available
  2. Test that `rerank_memories` returns original results when voyage_service is None
  3. Test that rerank failure degrades gracefully (returns original results)

  In `tests/test_agents.py` or a new section, add:
  ```python
  class TestRerankMemories:
      async def test_rerank_with_voyage(self, mock_deps):
          from second_brain.agents.utils import rerank_memories
          memories = [
              {"memory": "less relevant", "score": 0.7},
              {"memory": "most relevant", "score": 0.8},
          ]
          mock_deps.voyage_service.rerank = AsyncMock(return_value=[
              {"index": 1, "document": "most relevant", "relevance_score": 0.95},
              {"index": 0, "document": "less relevant", "relevance_score": 0.60},
          ])
          result = await rerank_memories(mock_deps, "test query", memories)
          assert result[0]["memory"] == "most relevant"
          assert result[0]["rerank_score"] == 0.95

      async def test_rerank_without_voyage(self, mock_deps):
          from second_brain.agents.utils import rerank_memories
          mock_deps.voyage_service = None
          memories = [{"memory": "a", "score": 0.9}]
          result = await rerank_memories(mock_deps, "query", memories)
          assert result == memories

      async def test_rerank_graceful_failure(self, mock_deps):
          from second_brain.agents.utils import rerank_memories
          mock_deps.voyage_service.rerank = AsyncMock(side_effect=Exception("API error"))
          memories = [{"memory": "a", "score": 0.9}]
          result = await rerank_memories(mock_deps, "query", memories)
          assert result == memories

      async def test_rerank_empty_memories(self, mock_deps):
          from second_brain.agents.utils import rerank_memories
          result = await rerank_memories(mock_deps, "query", [])
          assert result == []
  ```
- **PATTERN**: Follow existing test patterns in `tests/test_agents.py`
- **IMPORTS**: `AsyncMock` from `unittest.mock`
- **GOTCHA**: `mock_deps` fixture must include `voyage_service`. If using existing fixture,
  update it first (previous task).
- **VALIDATE**: `python -m pytest tests/test_agents.py -v -k rerank`

### FINAL VALIDATION: Run full test suite

- **IMPLEMENT**: Run the complete test suite and fix any regressions.
- **PATTERN**: N/A
- **IMPORTS**: N/A
- **GOTCHA**: Pre-existing failures in `test_models.py` (7) and `test_models_sdk.py` (2) are
  known — do not count as regressions. Search for `1536` in all test files to catch any
  dimension-related assertion failures.
- **VALIDATE**: `python -m pytest tests/ -v`

---

## TESTING STRATEGY

### Unit Tests

- **VoyageService**: embed, embed_query, embed_batch, rerank — mock `voyageai.Client`
- **EmbeddingService**: Voyage delegation (when `voyage_api_key` set), OpenAI fallback
  (when only `openai_api_key` set), embed_query method
- **rerank_memories**: with voyage, without voyage, API failure, empty input
- **Config**: New fields validate correctly, defaults are right

### Integration Tests

- **Agent search → rerank flow**: Verify that agent tools call rerank_memories and return
  reranked results (mock both MemoryService and VoyageService)
- **MCP vector_search**: Uses embed_query instead of embed
- **Migration**: EmbeddingService works with Voyage backend

### Edge Cases

- Voyage API key missing — fallback to OpenAI gracefully
- Voyage API rate limit / timeout — retry with exponential backoff (via async_retry)
- Empty search results — rerank returns empty list, no API call made
- Memories with missing 'memory' key — handled by `.get()` fallback to 'result'
- Rerank failure mid-list — graceful degradation to original order

---

## VALIDATION COMMANDS

### Level 1: Syntax & Style
```bash
python -c "from second_brain.services.voyage import VoyageService; print('VoyageService OK')"
python -c "from second_brain.services.embeddings import EmbeddingService; print('EmbeddingService OK')"
python -c "from second_brain.agents.utils import rerank_memories; print('rerank_memories OK')"
python -c "from second_brain.config import BrainConfig; c = BrainConfig(supabase_url='x', supabase_key='y', brain_data_path='.', _env_file=None); print(f'dims={c.embedding_dimensions}, model={c.voyage_embedding_model}')"
```

### Level 2: Unit Tests
```bash
python -m pytest tests/test_voyage.py -v
python -m pytest tests/test_agents.py -v -k rerank
python -m pytest tests/test_config.py -v
```

### Level 3: Integration Tests
```bash
python -m pytest tests/ -v
```

### Level 4: Manual Validation

1. Set `VOYAGE_API_KEY` in `.env`
2. Run: `python -c "from second_brain.services.voyage import VoyageService; from second_brain.config import BrainConfig; c = BrainConfig(); s = VoyageService(c); import asyncio; e = asyncio.run(s.embed('hello world')); print(f'Embedding dims: {len(e)}')"`
3. Verify output: `Embedding dims: 1024`
4. Apply SQL migration to Supabase
5. Re-run migration: `python -m second_brain.cli migrate`
6. Test vector search: `python -m second_brain.cli recall "content patterns"`

### Level 5: Additional Validation (Optional)

```bash
# Verify MCP server starts with Voyage
python -m second_brain.mcp_server
# Test from Claude Code: use vector_search tool
```

---

## ACCEPTANCE CRITERIA

- [x] VoyageService provides embed, embed_query, embed_batch, and rerank methods
- [ ] EmbeddingService delegates to Voyage when VOYAGE_API_KEY is set
- [ ] EmbeddingService falls back to OpenAI when only OPENAI_API_KEY is set
- [ ] All 5 agents use rerank_memories after Mem0 search calls
- [ ] Reranking degrades gracefully (returns original results on failure)
- [ ] Supabase schema migrated to vector(1024)
- [ ] MCP vector_search uses embed_query for better retrieval
- [ ] Config has voyage_api_key, voyage_embedding_model, voyage_rerank_model fields
- [ ] All existing tests pass (minus known pre-existing failures)
- [ ] New tests cover VoyageService and reranking (10+ new tests)
- [ ] No regressions in existing functionality

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order
- [ ] Each task validation passed
- [ ] All validation commands executed successfully
- [ ] Full test suite passes (unit + integration)
- [ ] No linting or type checking errors
- [ ] Manual testing confirms feature works
- [ ] Acceptance criteria all met

---

## NOTES

### Key Design Decisions

- **voyage-4-lite over voyage-context-3**: `voyage-context-3` uses `contextualized_embed()`
  which requires `List[List[str]]` input (chunks with document context). It CANNOT be used
  with the standard `embed()` API. Since our use case is embedding standalone text (memories,
  patterns, experiences), `voyage-4-lite` via `embed()` is the correct choice. If the user
  wants contextualized embeddings for markdown migration later, that would be a separate feature
  using `voyage-context-3`'s `contextualized_embed()` API.

- **rerank-2-lite vs rerank-2.5-lite**: User requested `rerank-2-lite` (8K context, 600K total
  tokens). The newer `rerank-2.5-lite` (32K context, instruction-following) is a drop-in upgrade
  — just change the model string. Both use the same `vo.rerank()` API.

- **External reranking over Mem0 built-in**: Mem0 supports rerankers natively (Cohere, Sentence
  Transformer, HuggingFace, LLM, Zero Entropy) but NOT Voyage. Rather than using the LangChain
  bridge or a non-Voyage reranker, we add reranking as a post-processing step on Mem0 results.
  This gives us Voyage quality without touching Mem0 internals.

- **Keep OpenAI for Mem0**: Mem0 Cloud doesn't expose embedder config. Mem0 Local supports
  custom embedders via LangChain bridge, but this adds `langchain-voyageai` as a dependency.
  The simplest approach: let Mem0 use its default OpenAI embeddings internally, and apply
  Voyage reranking on top. This preserves Mem0's search quality while adding cross-encoder
  reranking for better result ordering.

### Risks

- **Dimension migration**: Changing from 1536 to 1024 requires dropping and re-embedding all
  existing data. Mitigation: SQL migration uses `USING NULL` to clear old embeddings, then
  re-run the brain migration tool to re-embed everything.
- **Voyage API availability**: If Voyage API is down, embedding generation fails.
  Mitigation: EmbeddingService falls back to OpenAI. Reranking degrades gracefully.
- **Rate limits**: Voyage `voyage-4-lite` has 16M TPM. For batch migration of large datasets,
  this should be sufficient. Reranking at 4M TPM is adequate for interactive use.

### Confidence Score: 8/10
- **Strengths**: Clear API (Voyage SDK is simple), well-defined integration points (every agent
  search tool), graceful degradation pattern already established in codebase
- **Uncertainties**: `voyageai` package version compatibility (need to verify latest), exact
  ivfflat index behavior with dimension change, Mem0 Cloud + reranking interaction
- **Mitigations**: Version pin in pyproject.toml, test with real API key before deploying,
  reranking is optional/non-blocking
