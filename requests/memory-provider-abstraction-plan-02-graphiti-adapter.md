# Sub-Plan 02: Graphiti Adapter

> **Parent Plan**: `requests/memory-provider-abstraction-plan-overview.md`
> **Sub-Plan**: 02 of 04
> **Phase**: Graphiti Adapter — Extend GraphitiService + Create GraphitiMemoryAdapter
> **Tasks**: 4
> **Estimated Context Load**: Medium

---

## Scope

This sub-plan extends `GraphitiService` with optional `group_id` support and creates the new
`GraphitiMemoryAdapter` class that wraps `GraphitiService` and maps Graphiti's graph API to the
`MemoryServiceBase` interface. After this sub-plan, `memory_provider="graphiti"` has a concrete
implementation.

**What this sub-plan delivers**:
- `GraphitiService.add_episode` accepts optional `group_id: str | None = None` parameter
- `GraphitiService.search` accepts optional `group_id: str | None = None` parameter and uses
  `search_()` (with underscore) when group_id is provided for user-scoped retrieval
- NEW file `backend/src/second_brain/services/graphiti_memory.py` containing
  `GraphitiMemoryAdapter(MemoryServiceBase)` with all 13 abstract methods implemented
- All 13 methods: `add`/`add_with_metadata` delegate to `add_episode`; `search*` delegate to
  `GraphitiService.search`; `get_all/update_memory/delete/get_by_id/delete_all` gracefully degrade
  (return empty/0/None with `logger.debug` messages)

**Prerequisites from previous sub-plans**:
- Sub-plan 01 must be complete: `MemoryServiceBase(ABC)` defined in `abstract.py` with all 13
  abstract method signatures; `StubMemoryService` defined in `abstract.py`

---

## CONTEXT FOR THIS SUB-PLAN

### Files to Read Before Implementing

- `backend/src/second_brain/services/graphiti.py` (full file, ~240 lines) — Why: need the exact
  method signatures for `add_episode` (line ~131) and `search` (line ~182) to add `group_id`
  parameter; understand the `_ensure_initialized()` pattern and error handling style
- `backend/src/second_brain/services/abstract.py` (lines 136–end, appended by sub-plan 01) — Why:
  need the exact `MemoryServiceBase` abstract method signatures to implement in the adapter
- `backend/src/second_brain/services/search_result.py` (full file, ~13 lines) — Why:
  `GraphitiMemoryAdapter.search*` must return `SearchResult(memories=[...], relations=[...])`
- `backend/src/second_brain/config.py` (lines 85–135) — Why: need `config.brain_user_id` field
  name (confirmed at line ~132) for `self.user_id = config.brain_user_id` in adapter `__init__`

### Files Created by Previous Sub-Plans

- `abstract.py` appended with `MemoryServiceBase(ABC)` + `StubMemoryService` — all 13 abstract
  method signatures are ground truth for what `GraphitiMemoryAdapter` must implement

---

## STEP-BY-STEP TASKS

### UPDATE `backend/src/second_brain/services/graphiti.py` — add_episode group_id

- **ACTION**: UPDATE
- **TARGET**: `backend/src/second_brain/services/graphiti.py`
- **IMPLEMENT**: Add `group_id: str | None = None` parameter to `add_episode`. When `group_id`
  is provided, pass it as a keyword argument to `self._client.add_episode()`.

  **Locate `add_episode`** (around line 131) — the current signature looks like:
  ```python
  async def add_episode(self, content: str, metadata: dict | None = None) -> None:
  ```

  **Change to**:
  ```python
  async def add_episode(
      self,
      content: str,
      metadata: dict | None = None,
      group_id: str | None = None,
  ) -> None:
  ```

  **Inside the method**, find the `self._client.add_episode(...)` call. Add `group_id` to the
  kwargs dict or call if `group_id` is provided. The call currently builds kwargs — add:
  ```python
  if group_id:
      kwargs["group_id"] = group_id
  await self._client.add_episode(**kwargs)
  ```
  Or if the call is inline (not using a kwargs dict), change it to:
  ```python
  extra = {"group_id": group_id} if group_id else {}
  await self._client.add_episode(
      name=...,
      episode_body=content,
      source=EpisodeType.text,
      source_description=...,
      reference_time=...,
      **extra,
  )
  ```
  Use whichever pattern matches the existing call structure in `graphiti.py`.

- **PATTERN**: `backend/src/second_brain/services/graphiti.py:131` — existing `add_episode`
  signature; `deps.py:59-77` — optional parameter + try/except pattern
- **IMPORTS**: None new — `group_id` is a plain `str | None`
- **GOTCHA**: Do NOT pass `group_id=None` to `self._client.add_episode()` — only pass it when
  it has a value. Some versions of `graphiti-core` reject unexpected `None` keyword arguments.
  Use the `if group_id: kwargs["group_id"] = group_id` guard pattern.
- **VALIDATE**: `python -c "from second_brain.services.graphiti import GraphitiService; import inspect; sig = inspect.signature(GraphitiService.add_episode); print('group_id' in sig.parameters)"`

---

### UPDATE `backend/src/second_brain/services/graphiti.py` — search group_id

- **ACTION**: UPDATE
- **TARGET**: `backend/src/second_brain/services/graphiti.py`
- **IMPLEMENT**: Add `group_id: str | None = None` parameter to `search`. When `group_id` is
  provided, use `self._client.search_()` (method with underscore) which supports `group_ids=[...]`
  filtering. Fall back to `self._client.search()` when `group_id` is None or when `search_()` is
  not available in the installed version.

  **Locate `search`** (around line 182) — current signature:
  ```python
  async def search(self, query: str, limit: int = 10) -> SearchResult:
  ```

  **Change to**:
  ```python
  async def search(
      self, query: str, limit: int = 10, group_id: str | None = None
  ) -> SearchResult:
  ```

  **Inside the method**, replace the `self._client.search(query)` call with:
  ```python
  if group_id and hasattr(self._client, "search_"):
      raw = await self._client.search_(query, group_ids=[group_id])
      edges = getattr(raw, "edges", [])
  else:
      edges = await self._client.search(query)
  ```

  The rest of the method (edge translation to dicts, return `SearchResult(...)`) remains unchanged.
  It already uses `getattr(edge, "source_node_name", "?")` etc. (lines ~192–196) — leave that as-is.

  **Note on `search_()` return type**: `graphiti-core >= 0.1` returns an object with `.edges`
  attribute; `search()` returns `edges` directly as a list. The `getattr(raw, "edges", [])` call
  handles the `search_()` return safely.

- **PATTERN**: `backend/src/second_brain/services/graphiti.py:182-210` — existing `search` method;
  edge translation at lines ~192-196 uses `getattr(..., "?")` — keep that defensive pattern
- **IMPORTS**: None new
- **GOTCHA**: `search_()` (underscore) is the Graphiti method that supports `group_ids=[]` — the
  non-underscore `search()` does NOT have this parameter. The `hasattr(self._client, "search_")`
  guard ensures backward compatibility with older installed versions that may not have `search_()`.
  Always check `hasattr` first.
- **VALIDATE**: `python -c "from second_brain.services.graphiti import GraphitiService; import inspect; sig = inspect.signature(GraphitiService.search); print('group_id' in sig.parameters)"`

---

### CREATE `backend/src/second_brain/services/graphiti_memory.py`

- **ACTION**: CREATE
- **TARGET**: `backend/src/second_brain/services/graphiti_memory.py`
- **IMPLEMENT**: Create the `GraphitiMemoryAdapter` class. This is the main deliverable of this
  sub-plan. It wraps `GraphitiService` and implements all 13 `MemoryServiceBase` abstract methods.

  ```python
  """Graphiti-backed memory adapter implementing MemoryServiceBase.

  Maps the MemoryServiceBase interface to GraphitiService (Neo4j/FalkorDB).
  Used when MEMORY_PROVIDER=graphiti in config.
  """
  from __future__ import annotations

  import logging
  from typing import TYPE_CHECKING

  from second_brain.services.abstract import MemoryServiceBase
  from second_brain.services.search_result import SearchResult

  if TYPE_CHECKING:
      from second_brain.config import BrainConfig
      from second_brain.services.graphiti import GraphitiService

  logger = logging.getLogger(__name__)


  class GraphitiMemoryAdapter(MemoryServiceBase):
      """Adapts GraphitiService to the MemoryServiceBase interface.

      Uses config.brain_user_id as the Graphiti group_id for multi-user isolation.
      Methods not supported by Graphiti (get_all, update_memory, delete, get_by_id,
      delete_all) return empty/zero/None values with a debug log.
      """

      def __init__(self, config: "BrainConfig") -> None:
          from second_brain.services.graphiti import GraphitiService
          self._graphiti: GraphitiService = GraphitiService(config)
          self.user_id: str = config.brain_user_id

      async def add(
          self,
          content: str,
          metadata: dict | None = None,
          enable_graph: bool | None = None,
      ) -> dict:
          """Add content as a Graphiti episode. Returns status dict."""
          try:
              await self._graphiti.add_episode(
                  content, metadata=metadata, group_id=self.user_id
              )
              return {"status": "ok"}
          except Exception as e:
              logger.debug("GraphitiMemoryAdapter.add error: %s", e)
              return {}

      async def add_with_metadata(
          self,
          content: str,
          metadata: dict,
          enable_graph: bool | None = None,
      ) -> dict:
          """Add content with metadata. Delegates to add()."""
          return await self.add(content, metadata=metadata)

      async def search(
          self,
          query: str,
          limit: int | None = None,
          enable_graph: bool | None = None,
      ) -> SearchResult:
          """Semantic search via GraphitiService with user-scoped group_id."""
          return await self._graphiti.search(
              query, limit=limit or 10, group_id=self.user_id
          )

      async def search_with_filters(
          self,
          query: str,
          metadata_filters: dict | None = None,
          limit: int = 10,
          enable_graph: bool | None = None,
      ) -> SearchResult:
          """Search with metadata filters approximated by appending filter values to query."""
          if metadata_filters:
              extra = " ".join(str(v) for v in metadata_filters.values())
              query = f"{query} {extra}"
              logger.debug(
                  "GraphitiMemoryAdapter.search_with_filters: no native filter support — "
                  "appending filter terms to query: %r",
                  extra,
              )
          return await self._graphiti.search(query, limit=limit, group_id=self.user_id)

      async def search_by_category(
          self, category: str, query: str, limit: int = 10
      ) -> SearchResult:
          """Search by category by prepending category to query string."""
          combined = f"{category} {query}"
          return await self._graphiti.search(combined, limit=limit, group_id=self.user_id)

      async def get_all(self) -> list[dict]:
          """Not supported by Graphiti. Returns empty list."""
          logger.debug("GraphitiMemoryAdapter.get_all: not supported by Graphiti, returning []")
          return []

      async def get_memory_count(self) -> int:
          """Not supported by Graphiti. Returns 0."""
          logger.debug(
              "GraphitiMemoryAdapter.get_memory_count: not supported by Graphiti, returning 0"
          )
          return 0

      async def update_memory(
          self, memory_id: str, content: str, metadata: dict | None = None
      ) -> None:
          """Not supported by Graphiti. No-op."""
          logger.debug(
              "GraphitiMemoryAdapter.update_memory(%r): not supported by Graphiti, no-op",
              memory_id,
          )
          return None

      async def delete(self, memory_id: str) -> None:
          """Not supported by Graphiti. No-op."""
          logger.debug(
              "GraphitiMemoryAdapter.delete(%r): not supported by Graphiti, no-op", memory_id
          )
          return None

      async def get_by_id(self, memory_id: str) -> dict | None:
          """Not supported by Graphiti. Returns None."""
          logger.debug(
              "GraphitiMemoryAdapter.get_by_id(%r): not supported by Graphiti, returning None",
              memory_id,
          )
          return None

      async def delete_all(self) -> int:
          """Not supported by Graphiti. Returns 0."""
          logger.debug(
              "GraphitiMemoryAdapter.delete_all: not supported by Graphiti, returning 0"
          )
          return 0

      async def enable_project_graph(self) -> None:
          """Mem0-specific. No-op for Graphiti backend."""
          return None

      async def close(self) -> None:
          """Close underlying Graphiti client if possible."""
          try:
              if hasattr(self._graphiti, "close"):
                  await self._graphiti.close()
          except Exception as e:
              logger.debug("GraphitiMemoryAdapter.close error: %s", e)
          return None
  ```

- **PATTERN**: `backend/src/second_brain/services/abstract.py` (MemoryServiceBase signatures
  from sub-plan 01); `graphiti.py:182-210` (defensive `getattr` edge translation pattern);
  `deps.py:59-77` (lazy import in `__init__` for `GraphitiService`)
- **IMPORTS**:
  ```python
  from __future__ import annotations
  import logging
  from typing import TYPE_CHECKING
  from second_brain.services.abstract import MemoryServiceBase
  from second_brain.services.search_result import SearchResult
  if TYPE_CHECKING:
      from second_brain.config import BrainConfig
      from second_brain.services.graphiti import GraphitiService
  ```
- **GOTCHA 1**: `GraphitiService` is instantiated inside `__init__` via lazy import to avoid
  importing `graphiti-core` at module load time — mirrors the `deps.py:59-77` lazy import pattern.
- **GOTCHA 2**: ALL `search*` methods must return `SearchResult`, not a dict or list.
  `GraphitiService.search` already returns `SearchResult` — just pass it through.
- **GOTCHA 3**: `search_with_filters` appends filter values as query terms. This is an
  approximation — log at DEBUG level so operators can see when filters are being approximated.
- **GOTCHA 4**: `enable_graph` parameter is Mem0-specific. The adapter accepts it in the signature
  (ABC contract) but ignores it silently — no log needed since this is expected behavior.
- **VALIDATE**: `python -c "from second_brain.services.graphiti_memory import GraphitiMemoryAdapter; from second_brain.services.abstract import MemoryServiceBase; assert issubclass(GraphitiMemoryAdapter, MemoryServiceBase); print('OK')"`

---

### VERIFY sub-plan 02 by checking all method signatures match ABC

- **ACTION**: VALIDATE (no code change — verification step)
- **TARGET**: (verification only)
- **IMPLEMENT**: Run the verification commands in the VALIDATION COMMANDS section below.
  Specifically confirm:
  1. `GraphitiMemoryAdapter` is a subclass of `MemoryServiceBase`
  2. An instance can be created with a mock config
  3. `add_episode` and `search` in `graphiti.py` have `group_id` in their signatures

- **PATTERN**: Existing `conftest.py` brain_config fixture — use the same minimal config args
- **IMPORTS**: None
- **GOTCHA**: `GraphitiMemoryAdapter.__init__` calls `GraphitiService(config)` which tries to
  connect to the graph DB. In tests and validation, mock `GraphitiService` or use
  `unittest.mock.patch` to avoid connection attempts.
- **VALIDATE**: See VALIDATION COMMANDS section below.

---

## VALIDATION COMMANDS

### Syntax & Import Checks
```bash
cd backend
python -c "from second_brain.services.graphiti_memory import GraphitiMemoryAdapter; print('import OK')"
python -c "from second_brain.services.graphiti import GraphitiService; print('graphiti import OK')"
python -c "from second_brain.services.abstract import MemoryServiceBase; print('abstract import OK')"
```

### Signature Checks
```bash
cd backend
# Verify group_id added to GraphitiService methods
python -c "
import inspect
from second_brain.services.graphiti import GraphitiService
add_ep_sig = inspect.signature(GraphitiService.add_episode)
search_sig = inspect.signature(GraphitiService.search)
assert 'group_id' in add_ep_sig.parameters, 'add_episode missing group_id'
assert 'group_id' in search_sig.parameters, 'search missing group_id'
print('GraphitiService signatures: OK')
"

# Verify GraphitiMemoryAdapter is a valid subclass
python -c "
from second_brain.services.graphiti_memory import GraphitiMemoryAdapter
from second_brain.services.abstract import MemoryServiceBase
assert issubclass(GraphitiMemoryAdapter, MemoryServiceBase)
print('GraphitiMemoryAdapter inherits MemoryServiceBase: OK')
"
```

### Instantiation Check (with mock)
```bash
cd backend
python -c "
from unittest.mock import MagicMock, patch
from second_brain.services.graphiti_memory import GraphitiMemoryAdapter
config = MagicMock()
config.brain_user_id = 'test-user'
with patch('second_brain.services.graphiti.GraphitiService.__init__', return_value=None):
    adapter = GraphitiMemoryAdapter.__new__(GraphitiMemoryAdapter)
    adapter.user_id = config.brain_user_id
    adapter._graphiti = MagicMock()
assert adapter.user_id == 'test-user'
print('GraphitiMemoryAdapter instantiation: OK')
"
```

### Graceful Degradation Check
```bash
cd backend
python -c "
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from second_brain.services.graphiti_memory import GraphitiMemoryAdapter

config = MagicMock()
config.brain_user_id = 'test-user'
with patch('second_brain.services.graphiti_memory.GraphitiService') as MockGS:
    MockGS.return_value = AsyncMock()
    adapter = GraphitiMemoryAdapter(config)
    adapter.user_id = 'test-user'

result = asyncio.run(adapter.get_all())
assert result == [], f'Expected [] got {result}'
result = asyncio.run(adapter.get_memory_count())
assert result == 0, f'Expected 0 got {result}'
result = asyncio.run(adapter.get_by_id('x'))
assert result is None
print('Graceful degradation: OK')
"
```

### Regression Check
```bash
cd backend
python -m pytest tests/test_graphiti_service.py -q --tb=short 2>&1 | tail -5
python -m pytest tests/test_graph.py -q --tb=short 2>&1 | tail -5
python -m pytest tests/test_services.py -q --tb=short 2>&1 | tail -5
```

---

## SUB-PLAN CHECKLIST

- [x] Task 1 completed: `GraphitiService.add_episode` has `group_id: str | None = None` param
- [x] Task 2 completed: `GraphitiService.search` has `group_id` param + `hasattr` check for `search_()`
- [x] Task 3 completed: `graphiti_memory.py` created with `GraphitiMemoryAdapter(MemoryServiceBase)`
- [x] Task 4 completed: verification commands pass
- [x] All 13 abstract methods implemented in adapter
- [x] All graceful-degradation methods return correct empty types
- [x] Existing `test_graphiti_service.py` + `test_graph.py` still pass (no regressions)

---

## ACCEPTANCE CRITERIA

- [x] `issubclass(GraphitiMemoryAdapter, MemoryServiceBase)` is `True`
- [x] `GraphitiMemoryAdapter.user_id` is set from `config.brain_user_id` in `__init__`
- [x] `GraphitiService.add_episode(content, group_id="x")` passes `group_id` to client
- [x] `GraphitiService.search(query, group_id="x")` uses `search_()` with `group_ids=["x"]` when available
- [x] `adapter.get_all()` returns `[]` (no crash, no exception)
- [x] `adapter.get_memory_count()` returns `0`
- [x] `adapter.get_by_id("x")` returns `None`
- [x] `adapter.delete_all()` returns `0`
- [x] `adapter.search("test")` returns a `SearchResult` instance
- [x] `adapter.search_with_filters("q", {"category": "pattern"})` passes without error
- [x] All existing graphiti tests still pass

---

## HANDOFF NOTES

### Files Created
- `backend/src/second_brain/services/graphiti_memory.py` — `GraphitiMemoryAdapter(MemoryServiceBase)`

### Files Modified
- `backend/src/second_brain/services/graphiti.py` — `add_episode` + `search` gained optional
  `group_id: str | None = None` parameter; `search` uses `search_()` via `hasattr` guard when
  group_id is provided

### Patterns Established
- `GraphitiMemoryAdapter` lazy-imports `GraphitiService` inside `__init__` (avoids graphiti-core
  import at module load time)
- Graceful degradation: unsupported methods log at DEBUG and return empty/zero/None — no exceptions
- `search_with_filters` approximates metadata filters by appending values to query string

### State for Next Sub-Plan
- Sub-plan 03 (Wiring) needs `GraphitiMemoryAdapter` importable from
  `second_brain.services.graphiti_memory` to wire it into `create_deps()`
- Sub-plan 03 changes `create_deps()` in `deps.py` to branch on `config.memory_provider`:
  - `"graphiti"` → lazy import + instantiate `GraphitiMemoryAdapter`
  - `"none"` → import + instantiate `StubMemoryService`
  - `"mem0"` (default) → existing `MemoryService(config)` behavior
- Sub-plan 04 (Tests) needs both `GraphitiMemoryAdapter` and the `create_deps` branch to exist
  for full test coverage
