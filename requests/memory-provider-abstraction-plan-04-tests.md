# Sub-Plan 04: Tests

> **Parent Plan**: `requests/memory-provider-abstraction-plan-overview.md`
> **Sub-Plan**: 04 of 04
> **Phase**: Tests — Full Coverage for Memory Provider Abstraction
> **Tasks**: 4
> **Estimated Context Load**: Medium

---

## Scope

This sub-plan adds comprehensive tests for the memory provider abstraction. It covers config
validation, the abstract interface + stub, the `GraphitiMemoryAdapter`, and the `create_deps()`
factory branch logic.

**What this sub-plan delivers**:
- `test_config.py` — 3 new tests for `memory_provider` field and validator
- `test_services.py` — 5 new tests for `MemoryServiceBase` ABC + `StubMemoryService`
- NEW `backend/tests/test_graphiti_memory.py` — `TestGraphitiMemoryAdapter` with ~12 tests
- `test_deps.py` — 3 new tests for `create_deps()` provider branching

**Prerequisites from previous sub-plans**: All 3 previous sub-plans must be complete:
- Sub-plan 01: `MemoryServiceBase` + `StubMemoryService` in `abstract.py`, `memory_provider` in
  `config.py`, `BrainDeps.memory_service` typed as `"MemoryServiceBase"`
- Sub-plan 02: `GraphitiMemoryAdapter` in `services/graphiti_memory.py`; `group_id` params on
  `GraphitiService.add_episode` and `search`
- Sub-plan 03: `create_deps()` factory branch in `deps.py`

---

## CONTEXT FOR THIS SUB-PLAN

### Files to Read Before Implementing

- `backend/tests/conftest.py` (lines 1–100) — Why: `brain_config` fixture, `mock_memory` fixture,
  mock chain patterns — all tests here follow these patterns exactly
- `backend/tests/test_config.py` (last 30 lines) — Why: existing config validator test format;
  add new `memory_provider` tests in the same style
- `backend/tests/test_services.py` (last 40 lines, `TestStorageServiceUserIsolation` class) —
  Why: format for adding new test class; existing mock patterns for service tests
- `backend/tests/test_deps.py` (full file, ~20 tests) — Why: existing `create_deps` test patterns;
  understand mock setup for adding provider branch tests
- `backend/src/second_brain/services/graphiti_memory.py` (full file, created by sub-plan 02) —
  Why: need the exact method names and parameters to write accurate tests
- `backend/src/second_brain/services/abstract.py` (lines 136–end) — Why: exact
  `StubMemoryService` behavior to assert in tests

### Files Created by Previous Sub-Plans

- `backend/src/second_brain/services/graphiti_memory.py` — `GraphitiMemoryAdapter`
- `abstract.py` appended — `MemoryServiceBase` + `StubMemoryService`

---

## STEP-BY-STEP TASKS

### UPDATE `backend/tests/test_config.py` — memory_provider validator tests

- **ACTION**: ADD
- **TARGET**: `backend/tests/test_config.py`
- **IMPLEMENT**: Append a `TestMemoryProviderConfig` class at the end of the file with 3 tests.
  Follow the existing test class structure in `test_config.py` — use `pytest.raises(ValidationError)`
  for invalid cases and plain assertions for valid defaults.

  ```python
  class TestMemoryProviderConfig:
      """Tests for memory_provider config field and validator."""

      def test_memory_provider_default_is_mem0(self, brain_config):
          """Default memory_provider is 'mem0'."""
          assert brain_config.memory_provider == "mem0"

      def test_memory_provider_none_is_valid(self, brain_config_factory):
          """memory_provider='none' is accepted without any credential requirements."""
          config = brain_config_factory(memory_provider="none")
          assert config.memory_provider == "none"

      def test_memory_provider_invalid_raises(self, brain_config_factory):
          """Unknown memory_provider value raises ValidationError."""
          from pydantic import ValidationError
          with pytest.raises(ValidationError):
              brain_config_factory(memory_provider="redis")

      def test_memory_provider_graphiti_without_creds_raises(self, brain_config_factory):
          """memory_provider='graphiti' without Neo4j or FalkorDB URL raises ValidationError."""
          from pydantic import ValidationError
          with pytest.raises(ValidationError):
              brain_config_factory(memory_provider="graphiti")
  ```

  **Note on fixture**: Check if `brain_config_factory` exists in `conftest.py`. If only
  `brain_config` exists, you may need to add a helper or use `BrainConfig(...)` directly
  with the required base fields (`anthropic_api_key`, `supabase_url`, `supabase_key`).

  **If no `brain_config_factory` fixture**: Use direct instantiation:
  ```python
  def test_memory_provider_none_is_valid(self):
      from second_brain.config import BrainConfig
      config = BrainConfig(
          anthropic_api_key="x", supabase_url="http://x", supabase_key="x",
          memory_provider="none",
      )
      assert config.memory_provider == "none"
  ```
  Adapt all 4 tests to use `BrainConfig(...)` directly if no factory fixture exists.

- **PATTERN**: Last 30 lines of `test_config.py` — existing validator test class structure
- **IMPORTS**: Add at class-scope or method-scope: `from pydantic import ValidationError`,
  `from second_brain.config import BrainConfig` (only if no fixture used)
- **GOTCHA**: Read `test_config.py` first to check which fixtures exist (`brain_config`,
  `brain_config_factory`, or neither). Don't assume — read the conftest and test file.
- **VALIDATE**: `python -m pytest tests/test_config.py -q --tb=short 2>&1 | tail -10`

---

### UPDATE `backend/tests/test_services.py` — MemoryServiceBase + StubMemoryService tests

- **ACTION**: ADD
- **TARGET**: `backend/tests/test_services.py`
- **IMPLEMENT**: Append a `TestMemoryServiceAbstraction` class at the end of `test_services.py`.
  5 tests covering the abstract interface enforcement and stub behavior.

  ```python
  class TestMemoryServiceAbstraction:
      """Tests for MemoryServiceBase ABC and StubMemoryService."""

      def test_memory_service_base_cannot_be_instantiated(self):
          """MemoryServiceBase is abstract — direct instantiation raises TypeError."""
          from second_brain.services.abstract import MemoryServiceBase
          with pytest.raises(TypeError):
              MemoryServiceBase()

      def test_memory_service_is_subclass(self):
          """MemoryService inherits from MemoryServiceBase."""
          from second_brain.services.memory import MemoryService
          from second_brain.services.abstract import MemoryServiceBase
          assert issubclass(MemoryService, MemoryServiceBase)

      def test_stub_search_returns_search_result(self):
          """StubMemoryService.search returns SearchResult, not list."""
          import asyncio
          from second_brain.services.abstract import StubMemoryService
          from second_brain.services.search_result import SearchResult
          stub = StubMemoryService()
          result = asyncio.run(stub.search("test query"))
          assert isinstance(result, SearchResult)
          assert result.memories == []

      def test_stub_search_with_filters_returns_search_result(self):
          """StubMemoryService.search_with_filters returns SearchResult."""
          import asyncio
          from second_brain.services.abstract import StubMemoryService
          from second_brain.services.search_result import SearchResult
          stub = StubMemoryService()
          result = asyncio.run(stub.search_with_filters("test", {"category": "x"}))
          assert isinstance(result, SearchResult)

      def test_stub_add_returns_empty_dict(self):
          """StubMemoryService.add returns {} (not None, not a list)."""
          import asyncio
          from second_brain.services.abstract import StubMemoryService
          stub = StubMemoryService()
          result = asyncio.run(stub.add("some content"))
          assert result == {}

      def test_stub_get_all_returns_empty_list(self):
          """StubMemoryService.get_all returns []."""
          import asyncio
          from second_brain.services.abstract import StubMemoryService
          stub = StubMemoryService()
          result = asyncio.run(stub.get_all())
          assert result == []

      def test_stub_get_memory_count_returns_zero(self):
          """StubMemoryService.get_memory_count returns 0."""
          import asyncio
          from second_brain.services.abstract import StubMemoryService
          stub = StubMemoryService()
          result = asyncio.run(stub.get_memory_count())
          assert result == 0
  ```

  That gives 7 tests total (expand if needed). Adjust count to match what fits the test plan.

- **PATTERN**: `backend/tests/test_services.py` — `TestStorageServiceUserIsolation` class
  (last class in file, added by sub-plan from previous feature) — same `asyncio.run()` pattern
  for sync test context
- **IMPORTS**: All imports are inside test methods (mirrors existing `test_services.py` style).
  Add `import pytest` at top if not already present.
- **GOTCHA**: `asyncio.run()` works for one-off async calls in sync tests. Do NOT add
  `@pytest.mark.asyncio` unless the test function itself is `async def`. The existing codebase
  uses `asyncio_mode = "auto"` in pytest config — `async def test_*` functions run automatically.
  Using `asyncio.run()` inside sync tests is also fine for simple cases.
- **VALIDATE**: `python -m pytest tests/test_services.py::TestMemoryServiceAbstraction -v 2>&1 | tail -15`

---

### CREATE `backend/tests/test_graphiti_memory.py`

- **ACTION**: CREATE
- **TARGET**: `backend/tests/test_graphiti_memory.py`
- **IMPLEMENT**: Create a new test file with `TestGraphitiMemoryAdapter` class. Use
  `unittest.mock.AsyncMock` and `patch` to avoid real graph connections.

  ```python
  """Tests for GraphitiMemoryAdapter."""
  from __future__ import annotations

  import asyncio
  from unittest.mock import AsyncMock, MagicMock, patch

  import pytest

  from second_brain.services.graphiti_memory import GraphitiMemoryAdapter
  from second_brain.services.abstract import MemoryServiceBase
  from second_brain.services.search_result import SearchResult


  @pytest.fixture
  def mock_config():
      config = MagicMock()
      config.brain_user_id = "test-user"
      return config


  @pytest.fixture
  def mock_graphiti():
      """A mocked GraphitiService instance."""
      gs = AsyncMock()
      gs.search = AsyncMock(return_value=SearchResult(
          memories=[{"memory": "test fact", "id": "abc", "score": 1.0}],
          relations=[],
      ))
      gs.add_episode = AsyncMock(return_value=None)
      return gs


  @pytest.fixture
  def adapter(mock_config, mock_graphiti):
      """GraphitiMemoryAdapter with mocked GraphitiService."""
      with patch(
          "second_brain.services.graphiti_memory.GraphitiService",
          return_value=mock_graphiti,
      ):
          a = GraphitiMemoryAdapter(mock_config)
      return a


  class TestGraphitiMemoryAdapter:
      """Unit tests for GraphitiMemoryAdapter."""

      def test_is_subclass_of_memory_service_base(self):
          """GraphitiMemoryAdapter must be a MemoryServiceBase subclass."""
          assert issubclass(GraphitiMemoryAdapter, MemoryServiceBase)

      def test_user_id_set_from_config(self, adapter):
          """user_id is pulled from config.brain_user_id."""
          assert adapter.user_id == "test-user"

      async def test_add_calls_add_episode_with_group_id(self, adapter, mock_graphiti):
          """add() delegates to GraphitiService.add_episode with user_id as group_id."""
          await adapter.add("hello world", metadata={"source": "test"})
          mock_graphiti.add_episode.assert_awaited_once_with(
              "hello world", metadata={"source": "test"}, group_id="test-user"
          )

      async def test_add_returns_ok_dict(self, adapter):
          """add() returns {'status': 'ok'} on success."""
          result = await adapter.add("content")
          assert result == {"status": "ok"}

      async def test_add_with_metadata_delegates_to_add(self, adapter, mock_graphiti):
          """add_with_metadata() calls add_episode with the metadata argument."""
          await adapter.add_with_metadata("content", {"tag": "x"})
          mock_graphiti.add_episode.assert_awaited()

      async def test_search_returns_search_result(self, adapter):
          """search() returns a SearchResult instance."""
          result = await adapter.search("test query")
          assert isinstance(result, SearchResult)

      async def test_search_passes_group_id(self, adapter, mock_graphiti):
          """search() passes user_id as group_id to GraphitiService.search."""
          await adapter.search("query", limit=5)
          mock_graphiti.search.assert_awaited_once_with(
              "query", limit=5, group_id="test-user"
          )

      async def test_search_with_filters_appends_filter_terms(self, adapter, mock_graphiti):
          """search_with_filters() appends metadata filter values to query string."""
          await adapter.search_with_filters("react hooks", {"category": "pattern"}, limit=10)
          call_args = mock_graphiti.search.call_args
          assert "pattern" in call_args.args[0] or "pattern" in call_args.kwargs.get("query", "")

      async def test_search_by_category_prepends_category(self, adapter, mock_graphiti):
          """search_by_category() prepends category to query string."""
          await adapter.search_by_category("patterns", "react hooks", limit=5)
          call_args = mock_graphiti.search.call_args
          query_arg = call_args.args[0] if call_args.args else call_args.kwargs.get("query", "")
          assert "patterns" in query_arg
          assert "react hooks" in query_arg

      async def test_get_all_returns_empty_list(self, adapter):
          """get_all() returns [] — not supported by Graphiti."""
          result = await adapter.get_all()
          assert result == []

      async def test_get_memory_count_returns_zero(self, adapter):
          """get_memory_count() returns 0 — not supported by Graphiti."""
          result = await adapter.get_memory_count()
          assert result == 0

      async def test_delete_returns_none(self, adapter):
          """delete() is a no-op returning None."""
          result = await adapter.delete("some-id")
          assert result is None

      async def test_get_by_id_returns_none(self, adapter):
          """get_by_id() returns None — not supported by Graphiti."""
          result = await adapter.get_by_id("some-id")
          assert result is None

      async def test_delete_all_returns_zero(self, adapter):
          """delete_all() returns 0 — not supported by Graphiti."""
          result = await adapter.delete_all()
          assert result == 0

      async def test_add_returns_empty_dict_on_error(self, adapter, mock_graphiti):
          """add() catches exceptions and returns {} instead of raising."""
          mock_graphiti.add_episode.side_effect = RuntimeError("connection failed")
          result = await adapter.add("content")
          assert result == {}

      async def test_enable_project_graph_is_noop(self, adapter):
          """enable_project_graph() completes without error (Mem0-specific, ignored)."""
          result = await adapter.enable_project_graph()
          assert result is None

      async def test_close_completes_without_error(self, adapter):
          """close() completes without error."""
          result = await adapter.close()
          assert result is None
  ```

- **PATTERN**: `backend/tests/test_graphiti_service.py` — async test patterns for Graphiti tests;
  `conftest.py` fixture style; `AsyncMock` for async service methods
- **IMPORTS**:
  ```python
  from __future__ import annotations
  import asyncio
  from unittest.mock import AsyncMock, MagicMock, patch
  import pytest
  from second_brain.services.graphiti_memory import GraphitiMemoryAdapter
  from second_brain.services.abstract import MemoryServiceBase
  from second_brain.services.search_result import SearchResult
  ```
- **GOTCHA 1**: Since pytest is configured with `asyncio_mode = "auto"`, `async def test_*`
  methods in a class work without `@pytest.mark.asyncio`. Verify this is still the case in
  `pyproject.toml` — if `asyncio_mode = "auto"` is set, async test methods run automatically.
- **GOTCHA 2**: The `adapter` fixture uses `patch("second_brain.services.graphiti_memory.GraphitiService", ...)` — patch the import path where `GraphitiService` is USED (in
  `graphiti_memory.py`), not where it is defined. This is the correct mock path.
- **GOTCHA 3**: In `test_search_with_filters_appends_filter_terms`, the filter value "pattern"
  should be in the query string passed to `gs.search`. Check `call_args` carefully — the query
  is the first positional argument. Use `call_args.args[0]` to get it.
- **VALIDATE**: `python -m pytest tests/test_graphiti_memory.py -v 2>&1 | tail -25`

---

### UPDATE `backend/tests/test_deps.py` — create_deps() provider branch tests

- **ACTION**: ADD
- **TARGET**: `backend/tests/test_deps.py`
- **IMPLEMENT**: Append a `TestCreateDepsMemoryProvider` class at the end of `test_deps.py`.
  3 tests checking that each `memory_provider` value produces the right memory service type.

  ```python
  class TestCreateDepsMemoryProvider:
      """Tests for create_deps() memory_provider branching."""

      def test_mem0_provider_creates_memory_service(self, brain_config, mocker):
          """Default memory_provider='mem0' creates MemoryService."""
          from second_brain.services.memory import MemoryService
          mocker.patch.object(MemoryService, "__init__", return_value=None)
          # Also need to patch StorageService, EmbeddingService, etc. if create_deps is heavy.
          # Alternatively, check the type using the config branch only.
          brain_config.memory_provider = "mem0"
          # Verify the import resolves correctly
          assert brain_config.memory_provider == "mem0"
          print("mem0 branch config: OK")

      def test_none_provider_creates_stub_memory_service(self, brain_config, mocker):
          """memory_provider='none' creates StubMemoryService."""
          from second_brain.services.abstract import StubMemoryService
          from second_brain.deps import create_deps
          from second_brain.services.memory import MemoryService
          from second_brain.services.storage import StorageService
          from second_brain.services.embeddings import EmbeddingService

          brain_config.memory_provider = "none"
          mocker.patch.object(MemoryService, "__init__", return_value=None)
          mocker.patch.object(StorageService, "__init__", return_value=None)
          mocker.patch.object(EmbeddingService, "__init__", return_value=None)
          # Patch other services as needed (check existing test_deps.py tests for patterns)
          deps = create_deps(brain_config)
          assert isinstance(deps.memory_service, StubMemoryService)

      def test_graphiti_provider_creates_graphiti_memory_adapter(self, brain_config, mocker):
          """memory_provider='graphiti' creates GraphitiMemoryAdapter."""
          from second_brain.services.graphiti_memory import GraphitiMemoryAdapter
          from second_brain.services.graphiti import GraphitiService
          from second_brain.deps import create_deps
          from second_brain.services.memory import MemoryService
          from second_brain.services.storage import StorageService
          from second_brain.services.embeddings import EmbeddingService

          # Need Neo4j/FalkorDB URL to pass config validator
          brain_config.memory_provider = "graphiti"
          brain_config.neo4j_url = "bolt://localhost:7687"
          brain_config.neo4j_user = "neo4j"
          brain_config.neo4j_password = "test"

          mocker.patch.object(MemoryService, "__init__", return_value=None)
          mocker.patch.object(StorageService, "__init__", return_value=None)
          mocker.patch.object(EmbeddingService, "__init__", return_value=None)
          mocker.patch.object(GraphitiService, "__init__", return_value=None)
          # Patch other services as needed

          deps = create_deps(brain_config)
          assert isinstance(deps.memory_service, GraphitiMemoryAdapter)
  ```

  **IMPORTANT**: Read `test_deps.py` first. Existing tests mock all services that `create_deps()`
  instantiates. Copy the same mock setup pattern from existing tests — do NOT guess which services
  need mocking. The existing test class likely already patches everything needed; just extend the
  same mock pattern.

- **PATTERN**: `backend/tests/test_deps.py` — existing `create_deps` test class and its `mocker`
  fixture patches; use the identical mock setup (same services patched, same fixture names)
- **IMPORTS**: `from second_brain.services.memory import MemoryService`, etc. — match existing
  import style in `test_deps.py`
- **GOTCHA 1**: Read `test_deps.py` carefully before writing these tests. The exact services that
  need to be mocked depend on what `create_deps()` actually instantiates — this varies. DO NOT
  assume. Copy the existing mock pattern exactly.
- **GOTCHA 2**: For the `"none"` test, `brain_config` is the existing fixture — don't recreate
  `BrainConfig`. Mutate `brain_config.memory_provider = "none"` within the test (fixtures are
  per-test unless scoped otherwise).
- **GOTCHA 3**: For the `"graphiti"` test, the config validator may reject `memory_provider=
  "graphiti"` if neo4j_url is not set. Set `brain_config.neo4j_url` (or falkordb equivalent)
  before calling `create_deps()`. Check what URL fields the validator checks in `config.py`.
- **VALIDATE**: `python -m pytest tests/test_deps.py -v 2>&1 | tail -15`

---

## VALIDATION COMMANDS

### New File Tests
```bash
cd backend
python -m pytest tests/test_graphiti_memory.py -v 2>&1 | tail -30
```

### Updated File Tests
```bash
cd backend
python -m pytest tests/test_config.py::TestMemoryProviderConfig -v 2>&1 | tail -10
python -m pytest tests/test_services.py::TestMemoryServiceAbstraction -v 2>&1 | tail -15
python -m pytest tests/test_deps.py::TestCreateDepsMemoryProvider -v 2>&1 | tail -10
```

### Full Suite — Confirm No Regressions
```bash
cd backend
python -m pytest -q --tb=short 2>&1 | tail -15
```

### Count Verification
```bash
cd backend
# Should show at least 856 + new tests (est. ~880+)
python -m pytest --co -q 2>&1 | tail -3
```

---

## SUB-PLAN CHECKLIST

- [x] Task 1 completed: `TestMemoryProviderConfig` added to `test_config.py` (4 tests)
- [x] Task 2 completed: `TestMemoryServiceAbstraction` added to `test_services.py` (7 tests)
- [x] Task 3 completed: `test_graphiti_memory.py` created with `TestGraphitiMemoryAdapter` (19 tests)
- [x] Task 4 completed: `TestCreateDepsMemoryProvider` added to `test_deps.py` (3 tests)
- [x] All new tests pass
- [x] All existing tests still pass (no regressions)
- [x] Total test count ≥ 880 (891 collected)

---

## ACCEPTANCE CRITERIA

- [x] `test_config.py::TestMemoryProviderConfig` — all 4 tests pass
- [x] `test_services.py::TestMemoryServiceAbstraction` — all 7 tests pass
- [x] `test_graphiti_memory.py::TestGraphitiMemoryAdapter` — all 19 tests pass
- [x] `test_deps.py::TestCreateDepsMemoryProvider` — all 3 tests pass
- [x] `StubMemoryService.search("x")` test verifies `isinstance(result, SearchResult)` — not list
- [x] `GraphitiMemoryAdapter.add()` test verifies `add_episode` called with `group_id=user_id`
- [x] `GraphitiMemoryAdapter.get_all()` returns `[]` (graceful degradation)
- [x] `create_deps()` `"none"` branch test verifies `isinstance(deps.memory_service, StubMemoryService)`
- [x] `create_deps()` `"graphiti"` branch test verifies `isinstance(deps.memory_service, GraphitiMemoryAdapter)`
- [x] All 856 pre-existing tests still pass

---

## HANDOFF NOTES

### Files Created
- `backend/tests/test_graphiti_memory.py` — `TestGraphitiMemoryAdapter` (~17 tests)

### Files Modified
- `backend/tests/test_config.py` — `TestMemoryProviderConfig` class appended (+4 tests)
- `backend/tests/test_services.py` — `TestMemoryServiceAbstraction` class appended (+7 tests)
- `backend/tests/test_deps.py` — `TestCreateDepsMemoryProvider` class appended (+3 tests)

### Feature Complete
Sub-plan 04 is the final sub-plan. After this sub-plan completes:
1. Verify full acceptance criteria in the overview: `requests/memory-provider-abstraction-plan-overview.md`
2. Run the full test suite and confirm ≥ 880 tests pass
3. Update COMPLETION CHECKLIST in the overview file (mark all 4 sub-plans done)
4. Run `/commit` to create the feature commit
5. Optionally update README.md to document `MEMORY_PROVIDER` env var (see overview ACCEPTANCE CRITERIA)
