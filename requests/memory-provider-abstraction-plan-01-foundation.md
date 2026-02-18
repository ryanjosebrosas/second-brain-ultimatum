# Sub-Plan 01: Foundation

> **Parent Plan**: `requests/memory-provider-abstraction-plan-overview.md`
> **Sub-Plan**: 01 of 04
> **Phase**: Foundation — Config + Abstract Interface + MemoryService Inheritance
> **Tasks**: 4
> **Estimated Context Load**: Medium

---

## Scope

This sub-plan implements the **structural foundation** for the memory provider abstraction.
It creates the config field that controls which backend is active, defines the abstract
interface both backends must satisfy, makes the existing `MemoryService` conform to that
interface, and updates the `BrainDeps` type annotation to use the base class.

**What this sub-plan delivers**:
- `memory_provider` config field with `_validate_memory_provider_config` validator
- `MemoryServiceBase(ABC)` in `abstract.py` with all 13 abstract methods
- `StubMemoryService(MemoryServiceBase)` in `abstract.py` for `memory_provider="none"`
- `MemoryService` inherits from `MemoryServiceBase` (backward compatible, no method changes)
- `BrainDeps.memory_service` type annotation updated to `"MemoryServiceBase"`

**Prerequisites from previous sub-plans**: None (first sub-plan)

---

## CONTEXT FOR THIS SUB-PLAN

### Files to Read Before Implementing

- `backend/src/second_brain/config.py` (lines 85–135, 249–285) — Why: `graph_provider` field
  and `_validate_graph_config` validator are the exact patterns to mirror for `memory_provider`
- `backend/src/second_brain/services/abstract.py` (full file, 136 lines) — Why: must append
  `MemoryServiceBase` + `StubMemoryService` after the existing stubs; understand the exact ABC
  pattern, docstring style, and stub implementation style
- `backend/src/second_brain/services/memory.py` (lines 1–170) — Why: need the exact method
  signatures to define abstract methods correctly; `MemoryService` will declare inheritance
- `backend/src/second_brain/services/search_result.py` (full file, 13 lines) — Why:
  `SearchResult` is the return type for all `search*` abstract methods
- `backend/src/second_brain/deps.py` (lines 1–45) — Why: need to update `TYPE_CHECKING` import
  block (lines 7–18) and `BrainDeps.memory_service` type annotation (line 28)

### Files Created by Previous Sub-Plans

None (first sub-plan).

---

## STEP-BY-STEP TASKS

### UPDATE `backend/src/second_brain/config.py`

- **IMPLEMENT**: Add `memory_provider` field and `_validate_memory_provider_config` validator.

  **Add this field** after the `graph_provider` field (around line 96):
  ```python
  memory_provider: str = Field(
      default="mem0",
      description="Primary memory backend: mem0 | graphiti | none",
  )
  ```

  **Add this validator** after `_validate_graph_config` (around line 281, before the end of
  the class). Follow the exact same `@model_validator(mode="after")` + missing-list pattern:
  ```python
  @model_validator(mode="after")
  def _validate_memory_provider_config(self) -> "BrainConfig":
      if self.memory_provider == "graphiti":
          if not self.neo4j_url and not self.falkordb_url:
              raise ValueError(
                  "memory_provider='graphiti' requires at least one of: "
                  "NEO4J_URL, FALKORDB_URL"
              )
      elif self.memory_provider not in ("mem0", "none"):
          raise ValueError(
              f"memory_provider must be 'mem0', 'graphiti', or 'none' — got: "
              f"{self.memory_provider!r}"
          )
      return self
  ```

- **PATTERN**: `backend/src/second_brain/config.py:94-98` (graph_provider field declaration),
  `config.py:249-265` (_validate_graph_config pattern)
- **IMPORTS**: None needed — `Field` and `model_validator` are already imported in `config.py`
- **GOTCHA**: The validator must return `self` at the end. Accumulate missing fields into a
  list before raising, so the error message is complete. Do NOT use `@field_validator` —
  use `@model_validator(mode="after")` to match the existing pattern.
- **VALIDATE**: `python -c "from second_brain.config import BrainConfig; c = BrainConfig(anthropic_api_key='x', supabase_url='x', supabase_key='x'); assert c.memory_provider == 'mem0'; print('OK')"`

---

### UPDATE `backend/src/second_brain/services/abstract.py`

- **IMPLEMENT**: Append `MemoryServiceBase(ABC)` and `StubMemoryService` at the end of the
  file (after the existing stubs ending at line 136). Do NOT modify existing classes.

  **Add this block** at the end of the file:
  ```python
  class MemoryServiceBase(ABC):
      """Abstract interface for semantic memory backends (Mem0, Graphiti, etc.)."""

      @abstractmethod
      async def add(self, content: str, metadata: dict | None = None,
                    enable_graph: bool | None = None) -> dict:
          """Add a memory. Returns result dict (may be empty on failure)."""

      @abstractmethod
      async def add_with_metadata(self, content: str, metadata: dict,
                                  enable_graph: bool | None = None) -> dict:
          """Add a memory with required structured metadata. Returns result dict."""

      @abstractmethod
      async def search(self, query: str, limit: int | None = None,
                       enable_graph: bool | None = None) -> "SearchResult":
          """Semantic search. Returns SearchResult(memories, relations, search_filters)."""

      @abstractmethod
      async def search_with_filters(
          self,
          query: str,
          metadata_filters: dict | None = None,
          limit: int = 10,
          enable_graph: bool | None = None,
      ) -> "SearchResult":
          """Search with metadata filters. Returns SearchResult."""

      @abstractmethod
      async def search_by_category(
          self, category: str, query: str, limit: int = 10
      ) -> "SearchResult":
          """Search within a category. Returns SearchResult."""

      @abstractmethod
      async def get_all(self) -> list[dict]:
          """Return all stored memories. Returns empty list if unsupported."""

      @abstractmethod
      async def get_memory_count(self) -> int:
          """Return count of stored memories. Returns 0 if unsupported."""

      @abstractmethod
      async def update_memory(
          self, memory_id: str, content: str, metadata: dict | None = None
      ) -> None:
          """Update an existing memory. No-op if unsupported."""

      @abstractmethod
      async def delete(self, memory_id: str) -> None:
          """Delete a memory by ID. No-op if unsupported."""

      @abstractmethod
      async def get_by_id(self, memory_id: str) -> dict | None:
          """Fetch a memory by ID. Returns None if unsupported."""

      @abstractmethod
      async def delete_all(self) -> int:
          """Delete all memories. Returns count deleted (0 if unsupported)."""

      @abstractmethod
      async def enable_project_graph(self) -> None:
          """Enable project graph (Mem0-specific). No-op for other backends."""

      @abstractmethod
      async def close(self) -> None:
          """Close any open connections."""


  class StubMemoryService(MemoryServiceBase):
      """No-op memory service for memory_provider='none' or testing."""

      async def add(self, content, metadata=None, enable_graph=None):
          return {}

      async def add_with_metadata(self, content, metadata, enable_graph=None):
          return {}

      async def search(self, query, limit=None, enable_graph=None):
          from second_brain.services.search_result import SearchResult
          return SearchResult()

      async def search_with_filters(self, query, metadata_filters=None, limit=10,
                                    enable_graph=None):
          from second_brain.services.search_result import SearchResult
          return SearchResult()

      async def search_by_category(self, category, query, limit=10):
          from second_brain.services.search_result import SearchResult
          return SearchResult()

      async def get_all(self):
          return []

      async def get_memory_count(self):
          return 0

      async def update_memory(self, memory_id, content, metadata=None):
          return None

      async def delete(self, memory_id):
          return None

      async def get_by_id(self, memory_id):
          return None

      async def delete_all(self):
          return 0

      async def enable_project_graph(self):
          return None

      async def close(self):
          return None
  ```

  **Note on `SearchResult` import in stub**: Use a lazy import inside each search method to
  avoid circular imports at module load time. `abstract.py` must remain import-free at the
  module level (it currently only imports `from abc import ABC, abstractmethod`).

  **Note on `SearchResult` in `MemoryServiceBase` type hint**: The return type `"SearchResult"`
  is a string annotation (forward reference) — this avoids an import at module level. It will
  resolve correctly at runtime for type checkers.

- **PATTERN**: `backend/src/second_brain/services/abstract.py:12-29` (ABC + abstractmethod),
  `abstract.py:83-97` (stub with untyped params, minimal returns)
- **IMPORTS**: No new module-level imports — `ABC` and `abstractmethod` are already imported
  at line 9. The `SearchResult` is imported lazily inside stub methods.
- **GOTCHA**: `StubMemoryService.search*` methods must return `SearchResult()` (empty
  instance), NOT `[]`. Agents access `result.memories` — if you return `[]`, they crash with
  `AttributeError: 'list' object has no attribute 'memories'`. Use the lazy import pattern.
- **VALIDATE**: `python -c "from second_brain.services.abstract import MemoryServiceBase, StubMemoryService; print('MemoryServiceBase:', MemoryServiceBase); print('StubMemoryService OK')"`

---

### UPDATE `backend/src/second_brain/services/memory.py`

- **IMPLEMENT**: Make `MemoryService` inherit from `MemoryServiceBase`. This is a one-line
  class declaration change — no method changes needed since `MemoryService` already implements
  all 13 abstract methods.

  **Change** (current `class MemoryService:` at line 12):
  ```python
  # BEFORE (line 12):
  class MemoryService:

  # AFTER:
  class MemoryService(MemoryServiceBase):
  ```

  **Add import** at the top of `memory.py` (after the existing imports, around line 6):
  ```python
  from second_brain.services.abstract import MemoryServiceBase
  ```

  That is the only change. All existing method implementations satisfy the abstract interface
  automatically — Python ABC enforces this at class definition time, so if we missed anything
  it will raise `TypeError: Can't instantiate abstract class MemoryService`.

- **PATTERN**: Same as how `StubEmailService(EmailServiceBase)` inherits — same file, same
  import pattern
- **IMPORTS**: `from second_brain.services.abstract import MemoryServiceBase`
- **GOTCHA**: After adding the import and inheritance declaration, run `python -c "from
  second_brain.services.memory import MemoryService"` immediately. If there is a `TypeError`
  about abstract methods, it means `MemoryService` is missing an implementation for one of the
  13 abstract methods defined in `MemoryServiceBase`. Check the method name mismatch.
  The most likely gap is `enable_project_graph` — verify it exists in `memory.py`.
- **VALIDATE**: `python -c "from second_brain.services.memory import MemoryService; from second_brain.services.abstract import MemoryServiceBase; assert issubclass(MemoryService, MemoryServiceBase); print('OK')"`

---

### UPDATE `backend/src/second_brain/deps.py`

- **IMPLEMENT**: Two changes in `deps.py`:

  **Change 1 — Add `MemoryServiceBase` to `TYPE_CHECKING` block** (lines 7–18):
  ```python
  if TYPE_CHECKING:
      from second_brain.services.abstract import (
          AnalyticsServiceBase,
          CalendarServiceBase,
          EmailServiceBase,
          MemoryServiceBase,          # ← add this line
          TaskManagementServiceBase,
      )
      from second_brain.services.embeddings import EmbeddingService
      from second_brain.services.graphiti import GraphitiService
      from second_brain.services.memory import MemoryService
      from second_brain.services.storage import ContentTypeRegistry, StorageService
      from second_brain.services.voyage import VoyageService
  ```

  **Change 2 — Update `BrainDeps.memory_service` type annotation** (line 28):
  ```python
  # BEFORE:
  memory_service: "MemoryService"

  # AFTER:
  memory_service: "MemoryServiceBase"
  ```

  That is all for this task. The factory wiring (`create_deps()` at line 98) is handled in
  sub-plan 03 — we intentionally leave `memory_service=MemoryService(config)` unchanged here
  to keep this sub-plan's scope clean. The type annotation change is backward compatible since
  `MemoryService` IS a `MemoryServiceBase`.

- **PATTERN**: `backend/src/second_brain/deps.py:34`
  (`email_service: "EmailServiceBase | None" = None`) — same base class annotation style.
  `deps.py:7-18` — existing `TYPE_CHECKING` block structure to follow.
- **IMPORTS**: No runtime imports added — only the `TYPE_CHECKING` block (lines 7–18) is
  modified. `MemoryServiceBase` is only needed for type annotations, not at runtime.
- **GOTCHA**: Do NOT change `create_deps()` in this sub-plan — that is sub-plan 03. Only
  change the `TYPE_CHECKING` block and the `BrainDeps` field annotation. The `memory_service`
  field at line 28 should become `"MemoryServiceBase"` (quoted string, forward ref).
- **VALIDATE**: `python -c "from second_brain.deps import BrainDeps, create_deps; d = create_deps.__annotations__; print('BrainDeps fields OK')"`

---

## VALIDATION COMMANDS

### Syntax & Structure
```bash
cd backend
python -c "from second_brain.config import BrainConfig; print('config OK')"
python -c "from second_brain.services.abstract import MemoryServiceBase, StubMemoryService; print('abstract OK')"
python -c "from second_brain.services.memory import MemoryService; print('memory OK')"
python -c "from second_brain.deps import BrainDeps; print('deps OK')"
```

### Content Verification
```bash
cd backend
# Verify memory_provider default is "mem0"
python -c "
from second_brain.config import BrainConfig
c = BrainConfig(anthropic_api_key='x', supabase_url='x', supabase_key='x')
assert c.memory_provider == 'mem0', f'expected mem0, got {c.memory_provider}'
print('memory_provider default: OK')
"

# Verify validator rejects unknown provider
python -c "
from second_brain.config import BrainConfig
from pydantic import ValidationError
try:
    BrainConfig(anthropic_api_key='x', supabase_url='x', supabase_key='x', memory_provider='redis')
    print('FAIL — should have raised')
except (ValidationError, ValueError):
    print('validator rejects unknown: OK')
"

# Verify graphiti requires creds
python -c "
from second_brain.config import BrainConfig
from pydantic import ValidationError
try:
    BrainConfig(anthropic_api_key='x', supabase_url='x', supabase_key='x', memory_provider='graphiti')
    print('FAIL — should have raised')
except (ValidationError, ValueError):
    print('validator requires creds for graphiti: OK')
"

# Verify MemoryService is subclass
python -c "
from second_brain.services.memory import MemoryService
from second_brain.services.abstract import MemoryServiceBase
assert issubclass(MemoryService, MemoryServiceBase)
print('MemoryService inherits MemoryServiceBase: OK')
"

# Verify StubMemoryService returns SearchResult
python -c "
import asyncio
from second_brain.services.abstract import StubMemoryService
from second_brain.services.search_result import SearchResult
stub = StubMemoryService()
result = asyncio.run(stub.search('test'))
assert isinstance(result, SearchResult)
print('StubMemoryService.search returns SearchResult: OK')
"
```

### Cross-Reference Check
```bash
cd backend
# Verify existing tests still pass
python -m pytest tests/test_services.py -q --tb=short 2>&1 | tail -5
python -m pytest tests/test_config.py -q --tb=short 2>&1 | tail -5
python -m pytest tests/test_deps.py -q --tb=short 2>&1 | tail -5
```

---

## SUB-PLAN CHECKLIST

- [ ] Task 1 completed: `memory_provider` field + validator in `config.py`
- [ ] Task 2 completed: `MemoryServiceBase` + `StubMemoryService` in `abstract.py`
- [ ] Task 3 completed: `MemoryService` inherits `MemoryServiceBase`
- [ ] Task 4 completed: `BrainDeps.memory_service` typed as `"MemoryServiceBase"`
- [ ] All validation commands pass
- [ ] No regressions in `test_services.py`, `test_config.py`, `test_deps.py`

---

## ACCEPTANCE CRITERIA

- [ ] `BrainConfig().memory_provider == "mem0"` (default)
- [ ] `BrainConfig(..., memory_provider="graphiti")` raises `ValueError` without Neo4j/FalkorDB creds
- [ ] `BrainConfig(..., memory_provider="redis")` raises `ValueError` for unknown value
- [ ] `issubclass(MemoryService, MemoryServiceBase)` is `True`
- [ ] `StubMemoryService().search("x")` returns a `SearchResult` instance
- [ ] `BrainDeps.memory_service` annotation is `"MemoryServiceBase"` (not `"MemoryService"`)
- [ ] All 856 existing tests still pass

---

## HANDOFF NOTES

### Files Created
- None

### Files Modified
- `backend/src/second_brain/config.py` — added `memory_provider` field (after `graph_provider`)
  and `_validate_memory_provider_config` validator (after `_validate_graph_config`)
- `backend/src/second_brain/services/abstract.py` — appended `MemoryServiceBase(ABC)` and
  `StubMemoryService` after the existing stubs (after line 136)
- `backend/src/second_brain/services/memory.py` — `class MemoryService(MemoryServiceBase):`
  + import added
- `backend/src/second_brain/deps.py` — `TYPE_CHECKING` block expanded with `MemoryServiceBase`;
  `BrainDeps.memory_service` annotation changed to `"MemoryServiceBase"`

### Patterns Established
- `MemoryServiceBase` ABC pattern: all 13 abstract methods with exact signatures from
  `MemoryService`. The method names and signatures are ground truth for sub-plan 02.
- `StubMemoryService` returns `SearchResult()` for all search methods — not `[]`.

### State for Next Sub-Plan
- Sub-plan 02 needs `MemoryServiceBase` from `abstract.py` to be complete before creating
  `GraphitiMemoryAdapter(MemoryServiceBase)`
- Sub-plan 02 also needs to add `group_id` param to `GraphitiService.add_episode` and `search`
  in `graphiti.py`
- The exact abstract method signatures (especially `search` returning `SearchResult`) are
  critical for sub-plan 02 — the adapter must return the same types
