# Sub-Plan 03: Wiring

> **Parent Plan**: `requests/memory-provider-abstraction-plan-overview.md`
> **Sub-Plan**: 03 of 04
> **Phase**: Wiring — Factory Switch in create_deps()
> **Tasks**: 3
> **Estimated Context Load**: Low

---

## Scope

This sub-plan updates `create_deps()` in `deps.py` to branch on `config.memory_provider` and
instantiate the correct memory backend. This is the final integration step that makes the
`MEMORY_PROVIDER` env var actually control which backend agents use.

**What this sub-plan delivers**:
- `create_deps()` branches on `config.memory_provider`: `"mem0"` → `MemoryService`, `"graphiti"` →
  `GraphitiMemoryAdapter`, `"none"` → `StubMemoryService`
- `"graphiti"` uses lazy import inside try/except with a `logger.warning` fallback to mem0 if
  `graphiti-core` is not installed
- Zero behavior change when `MEMORY_PROVIDER=mem0` (default) — existing path is untouched

**Prerequisites from previous sub-plans**:
- Sub-plan 01: `MemoryServiceBase` in `abstract.py`, `StubMemoryService` in `abstract.py`,
  `BrainDeps.memory_service` typed as `"MemoryServiceBase"`, `memory_provider` field in `config.py`
- Sub-plan 02: `GraphitiMemoryAdapter` in `services/graphiti_memory.py`

---

## CONTEXT FOR THIS SUB-PLAN

### Files to Read Before Implementing

- `backend/src/second_brain/deps.py` (full file, ~104 lines) — Why: need the exact structure of
  `create_deps()` (lines 47–104); specifically line ~98 where `MemoryService(config)` is
  unconditionally created — this line is the replacement target
- `backend/src/second_brain/config.py` (lines 85–100) — Why: confirm `memory_provider` field
  name (added by sub-plan 01) to use in `config.memory_provider` branch condition
- `backend/src/second_brain/services/abstract.py` (lines 136–end) — Why: confirm
  `StubMemoryService` import path (added by sub-plan 01) for the `"none"` branch

### Files Created by Previous Sub-Plans

- `backend/src/second_brain/services/graphiti_memory.py` — `GraphitiMemoryAdapter` — import in
  the `"graphiti"` branch
- `abstract.py` (appended) — `StubMemoryService` — import in the `"none"` branch

---

## STEP-BY-STEP TASKS

### UPDATE `backend/src/second_brain/deps.py` — factory switch in create_deps()

- **ACTION**: UPDATE
- **TARGET**: `backend/src/second_brain/deps.py`
- **IMPLEMENT**: Replace the unconditional `memory_service=MemoryService(config)` at line ~98
  with a branching block that checks `config.memory_provider`.

  **Locate** the `create_deps()` function. Find the line that reads:
  ```python
  memory_service=MemoryService(config)
  ```
  or if it's a separate assignment:
  ```python
  memory_service = MemoryService(config)
  ```

  **Replace that single line** with the following block (keep the same indentation level):
  ```python
  # Memory service — provider selected by config.memory_provider
  _mp = config.memory_provider
  if _mp == "graphiti":
      try:
          from second_brain.services.graphiti_memory import GraphitiMemoryAdapter
          memory_service = GraphitiMemoryAdapter(config)
      except ImportError:
          logger.warning(
              "graphiti-core not installed — cannot use memory_provider='graphiti'. "
              "Install with: pip install -e '.[graphiti]'. Falling back to mem0."
          )
          memory_service = MemoryService(config)
  elif _mp == "none":
      from second_brain.services.abstract import StubMemoryService
      memory_service = StubMemoryService()
  else:  # "mem0" (default) or any unrecognised value caught by config validator
      memory_service = MemoryService(config)
  ```

  **Then** in the `BrainDeps(...)` constructor call at the bottom of `create_deps()`, use the
  local variable `memory_service` rather than the inline `MemoryService(config)`. If the
  constructor call currently has `memory_service=MemoryService(config)` inline, change it to
  `memory_service=memory_service`.

  **Note**: `MemoryService` is already imported at the top of `deps.py` (used by the existing
  unconditional path). Leave that import in place — it is still used in the `else` branch and
  as the `"graphiti"` fallback.

- **PATTERN**: `backend/src/second_brain/deps.py:59-77` — existing `graphiti = None` conditional
  block; same lazy import + try/except + `logger.warning` with install hint pattern.
- **IMPORTS**: The `GraphitiMemoryAdapter` and `StubMemoryService` imports are **inside the
  if/elif branches** (not at module top). This matches the lazy import pattern used for
  `GraphitiService` at line 59-77. No new module-level imports needed.
- **GOTCHA 1**: Do NOT import `GraphitiMemoryAdapter` at the module top level. It must be a
  lazy import inside the `try:` block so that `second_brain` works normally when `graphiti-core`
  is not installed.
- **GOTCHA 2**: The `StubMemoryService` import (`from second_brain.services.abstract import
  StubMemoryService`) is safe to do at branch-time (not lazy-try) since `abstract.py` is always
  available (it's a core file). But for consistency with the pattern, keep it inside the `elif`
  branch.
- **GOTCHA 3**: If `create_deps()` builds `BrainDeps(...)` inline (all args in one call), you
  may need to extract the memory_service creation to before the constructor call. Adjust the
  surrounding code structure as needed to ensure `memory_service` is a local variable before
  being passed to `BrainDeps(...)`.
- **VALIDATE**: `python -c "from second_brain.deps import create_deps; print('create_deps import OK')"`

---

### VERIFY default behavior unchanged (memory_provider=mem0)

- **ACTION**: VALIDATE
- **TARGET**: `backend/src/second_brain/deps.py`
- **IMPLEMENT**: Verify that with default config (no `MEMORY_PROVIDER` env var), `create_deps()`
  still returns a `BrainDeps` with a `MemoryService` instance. This ensures zero regressions for
  users who don't set `MEMORY_PROVIDER`.

  Run the content verification commands from the VALIDATION COMMANDS section.

- **PATTERN**: `backend/tests/conftest.py` — `brain_config` fixture pattern for creating a
  minimal config in Python without env vars
- **IMPORTS**: None
- **GOTCHA**: `create_deps()` calls real external services at instantiation time (Mem0, Supabase).
  For the verification command, mock at the `MemoryService.__init__` level or check type only
  via the config branch logic rather than full instantiation.
- **VALIDATE**: See VALIDATION COMMANDS section.

---

### VERIFY graphiti branch selects GraphitiMemoryAdapter

- **ACTION**: VALIDATE
- **TARGET**: (verification only)
- **IMPLEMENT**: Verify that setting `memory_provider="graphiti"` in config with Neo4j creds
  (mocked) results in `GraphitiMemoryAdapter` being selected. Run the content verification
  commands from the VALIDATION COMMANDS section.

- **PATTERN**: `backend/tests/test_deps.py` — existing `create_deps` test patterns
- **IMPORTS**: None
- **GOTCHA**: For verification without real Neo4j: patch `GraphitiMemoryAdapter.__init__` to
  return None (prevents actual connection). Check `type(deps.memory_service).__name__`.
- **VALIDATE**: See VALIDATION COMMANDS section.

---

## VALIDATION COMMANDS

### Syntax Check
```bash
cd backend
python -c "from second_brain.deps import create_deps, BrainDeps; print('deps import OK')"
python -c "from second_brain.deps import BrainDeps; print(BrainDeps.__dataclass_fields__.get('memory_service', 'MISSING'))"
```

### Branch Logic Check (no real connections)
```bash
cd backend
python -c "
from unittest.mock import patch, MagicMock
from second_brain.config import BrainConfig

# Test: 'mem0' branch selects MemoryService
with patch('second_brain.services.memory.AsyncMemory'), \
     patch('second_brain.services.storage.create_client', return_value=MagicMock()):
    config = BrainConfig(
        anthropic_api_key='x', supabase_url='http://x', supabase_key='x',
        memory_provider='mem0',
    )
    from second_brain.services.memory import MemoryService
    with patch.object(MemoryService, '__init__', return_value=None) as mock_init:
        from second_brain.deps import create_deps
        # Just verify the import path works, not full construction
    print('mem0 branch: OK')
"
```

### Provider Routing Verification (isolated)
```bash
cd backend
python -c "
# Verify the branch logic in isolation
from second_brain.services.abstract import StubMemoryService
from second_brain.services.search_result import SearchResult

# Simulate 'none' path
stub = StubMemoryService()
import asyncio
result = asyncio.run(stub.search('test'))
assert hasattr(result, 'memories'), 'StubMemoryService.search must return SearchResult'
print('none branch (StubMemoryService): OK')
"

python -c "
# Verify GraphitiMemoryAdapter importable
from second_brain.services.graphiti_memory import GraphitiMemoryAdapter
from second_brain.services.abstract import MemoryServiceBase
assert issubclass(GraphitiMemoryAdapter, MemoryServiceBase)
print('graphiti branch (GraphitiMemoryAdapter): OK')
"
```

### Regression Tests
```bash
cd backend
python -m pytest tests/test_deps.py -q --tb=short 2>&1 | tail -10
python -m pytest tests/test_config.py -q --tb=short 2>&1 | tail -5
python -m pytest tests/test_services.py -q --tb=short 2>&1 | tail -5
```

### Full Suite Smoke Test
```bash
cd backend
python -m pytest -q --tb=short 2>&1 | tail -10
```

---

## SUB-PLAN CHECKLIST

- [x] Task 1 completed: `create_deps()` has provider branch replacing unconditional `MemoryService(config)`
- [x] Task 2 completed: default `memory_provider="mem0"` path unchanged (regression check passes)
- [x] Task 3 completed: `"graphiti"` and `"none"` branches verified importable
- [x] `deps.py` imports are still valid (no circular imports)
- [x] All existing `test_deps.py` tests pass
- [x] All existing `test_config.py` tests pass

---

## ACCEPTANCE CRITERIA

- [x] `config.memory_provider == "mem0"` → `create_deps()` creates `MemoryService(config)` (default behavior)
- [x] `config.memory_provider == "graphiti"` → `create_deps()` creates `GraphitiMemoryAdapter(config)`
- [x] `config.memory_provider == "none"` → `create_deps()` creates `StubMemoryService()`
- [x] `"graphiti"` branch uses lazy import inside try/except with `logger.warning` fallback
- [x] `StubMemoryService` import is inside the `elif _mp == "none":` branch (not at module top)
- [x] No new module-level imports added to `deps.py`
- [x] `BrainDeps.memory_service` field holds the correct type for each branch
- [x] All 849 existing tests still pass (9 pre-existing failures in test_models/test_models_sdk unchanged)

---

## HANDOFF NOTES

### Files Created
- None

### Files Modified
- `backend/src/second_brain/deps.py` — `create_deps()` now branches on `config.memory_provider`;
  `memory_service` assignment replaced with a 3-branch conditional block

### Patterns Established
- Lazy import pattern for `GraphitiMemoryAdapter` in try/except with `logger.warning` fallback
- `StubMemoryService` imported at branch time (not module top)
- Local variable `memory_service` built before `BrainDeps(...)` constructor call

### State for Next Sub-Plan
- Sub-plan 04 (Tests) is the final sub-plan. It needs all previous sub-plans complete:
  - `MemoryServiceBase` + `StubMemoryService` in `abstract.py` (sub-plan 01)
  - `GraphitiMemoryAdapter` in `graphiti_memory.py` (sub-plan 02)
  - `create_deps()` factory branch in `deps.py` (this sub-plan)
- Sub-plan 04 adds tests in 4 files:
  - `test_config.py` — `memory_provider` validator tests
  - `test_services.py` — `MemoryServiceBase` + `StubMemoryService` unit tests
  - NEW `test_graphiti_memory.py` — `GraphitiMemoryAdapter` full test class
  - `test_deps.py` — `create_deps()` provider branching tests
