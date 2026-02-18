# Plan Overview: Memory Provider Abstraction

<!-- PLAN-SERIES -->

> **This is a decomposed plan overview.** It coordinates multiple sub-plans that together
> implement a complex feature. Each sub-plan is self-contained and executable in a fresh
> conversation. Do NOT implement from this file — use `/execute` on each sub-plan in order.
>
> **Total Sub-Plans**: 4
> **Total Estimated Tasks**: 14

---

## Feature Description

Add a `MEMORY_PROVIDER` config switch (`mem0` | `graphiti` | `none`) so the Second Brain's
memory layer can run on either Mem0 (cloud SaaS, the current default) or Graphiti
(Neo4j/FalkorDB graph database, already in the codebase as an optional enrichment service)
with identical agent behavior regardless of which backend is chosen. This makes the system
usable without a Mem0 subscription — users can self-host Neo4j (free AuraDB tier) or run
FalkorDB locally instead.

The feature has four parts: (1) a new abstract base class `MemoryServiceBase` that defines the
interface both providers must satisfy, (2) a new `GraphitiMemoryAdapter` that wraps the existing
`GraphitiService` and maps Graphiti's graph API to the `MemoryServiceBase` interface with
multi-user `group_id` isolation, (3) a factory switch in `create_deps()` that instantiates the
right backend based on config, and (4) comprehensive tests for the new paths.

## User Story

As a developer self-hosting Second Brain, I want to set `MEMORY_PROVIDER=graphiti` in my `.env`
so that I can use Neo4j or FalkorDB as my memory backend without needing a Mem0 API key, while
all agents (recall, ask, learn, create, review, coach) behave identically regardless of which
provider is active.

## Problem Statement

Currently, `MemoryService` (Mem0) is unconditionally instantiated in `create_deps()` regardless
of any config. Users must have a Mem0 API key or local Mem0 setup. The codebase already includes
`GraphitiService` but only as a supplemental enrichment layer — never as the primary memory
backend. There is no abstract interface, no provider switch, and no user isolation in
`GraphitiService` (no `group_id` passed to any operation).

## Solution Statement

- **Decision 1: ABC over Protocol** — the project already uses `ABC + @abstractmethod` in
  `abstract.py` for all pluggable services (`EmailServiceBase`, etc.). Follow that pattern
  exactly for `MemoryServiceBase`. Protocol would require no inheritance but adds runtime
  complexity; ABC gives explicit contract enforcement + IDE navigation.
- **Decision 2: Adapter wraps GraphitiService** — don't change `GraphitiService` internals
  beyond adding `group_id` parameter. Create a separate `GraphitiMemoryAdapter` in a new file
  that implements `MemoryServiceBase` by delegating to `GraphitiService`. Clean separation.
- **Decision 3: Graceful degradation for missing methods** — Graphiti has no equivalent for
  `get_all()`, `update_memory()`, `delete_all()`, `get_by_id()`. Adapter returns empty/zero/None
  for these with a `logger.debug()` message. Agents that call these (learn agent's dedup check,
  health check's count) will see empty results rather than errors — acceptable degradation.
- **Decision 4: group_id = user_id** — Graphiti's `group_id` parameter is the exact equivalent
  of Mem0's `user_id`. Map `config.brain_user_id` → `group_id` in all Graphiti calls.
- **Decision 5: search_with_filters approximated** — Graphiti has no metadata filter concept.
  Adapter appends filter values as query terms (e.g., `"pattern react hooks"` for
  `metadata_filters={"category": "pattern"}`). Imperfect but functional; log at debug level.
- **Decision 6: StubMemoryService for `none`** — `memory_provider="none"` gets a no-op stub
  (same pattern as `StubEmailService`). Useful for testing and minimal deployments.

## Feature Metadata

- **Feature Type**: New Capability + Refactor
- **Estimated Complexity**: High
- **Plan Mode**: Decomposed (4 sub-plans)
- **Primary Systems Affected**: `services/abstract.py`, `services/memory.py`,
  `services/graphiti.py`, NEW `services/graphiti_memory.py`, `deps.py`, `config.py`,
  `pyproject.toml`, 4 test files
- **Dependencies**: `graphiti-core[anthropic,falkordb]>=0.1.0,<1.0.0` (already in extras);
  Neo4j included in base `graphiti-core` package (no new extras needed)

---

## CONTEXT REFERENCES

> Shared context that ALL sub-plans need. Each sub-plan also has its own per-phase context.

### Relevant Codebase Files

> IMPORTANT: The execution agent MUST read these files before implementing any sub-plan!

- `backend/src/second_brain/services/abstract.py` (lines 1–136) — Why: exact ABC pattern to
  follow for `MemoryServiceBase`; `StubEmailService` is the stub pattern to mirror
- `backend/src/second_brain/services/memory.py` (lines 1–100) — Why: full method signatures
  for `MemoryServiceBase` abstract methods; `MemoryService` must inherit from it
- `backend/src/second_brain/services/graphiti.py` (lines 1–240) — Why: `GraphitiService` is
  the backend for `GraphitiMemoryAdapter`; add `group_id` param to `add_episode` + `search`
- `backend/src/second_brain/deps.py` (lines 1–104) — Why: factory pattern + `BrainDeps`
  dataclass shape; type annotation + factory switch both live here
- `backend/src/second_brain/config.py` (lines 87–130, 249–281) — Why: `graph_provider` field
  (line ~94) and `_validate_graph_config` validator (line ~249) are exact patterns to mirror
- `backend/src/second_brain/services/search_result.py` — Why: `SearchResult(memories, relations,
  search_filters)` is the return type for all `search*` methods
- `backend/tests/conftest.py` (lines 1–100) — Why: `brain_config` fixture and `mock_memory`
  fixture patterns for new tests

### New Files to Create (All Sub-Plans)

- `backend/src/second_brain/services/graphiti_memory.py` — `GraphitiMemoryAdapter(MemoryServiceBase)` — Sub-plan 02
- `backend/tests/test_graphiti_memory.py` — `TestGraphitiMemoryAdapter` test class — Sub-plan 04

### Related Memories (from memory.md)

No relevant memories found in memory.md (file is empty).

### Relevant Documentation

- [Graphiti group_id isolation](https://help.getzep.com/graphiti/core-concepts/adding-episodes)
  - Section: Adding Episodes with group_id
  - Why: `group_id` is the Graphiti equivalent of Mem0's `user_id` — required for multi-user isolation
- [Graphiti search_ advanced method](https://help.getzep.com/graphiti/getting-started/quick-start)
  - Section: Searching the Graph
  - Why: `search_(query, group_ids=[...])` enables user-scoped retrieval; use this instead of `search()` when `group_id` filtering is needed
- [Mem0 async memory](https://docs.mem0.ai/open-source/features/async-memory)
  - Section: AsyncMemory API
  - Why: confirms `add`, `search`, `get_all`, `delete`, `delete_all` signatures used in `MemoryService`

### Patterns to Follow

**ABC + abstractmethod pattern** (from `backend/src/second_brain/services/abstract.py:9-29`):
```python
from abc import ABC, abstractmethod

class EmailServiceBase(ABC):
    """Interface for email operations (Gmail, Outlook, etc.)."""

    @abstractmethod
    async def send(self, to: list[str], subject: str, body: str, cc: list[str] | None = None) -> dict:
        """Send an email. Returns delivery status dict."""
```
- Why: every abstract method has a docstring describing its return shape; no `pass` or `...`
- Gotcha: Class name must be `{Name}ServiceBase`. Stub is `Stub{Name}Service`.

**Stub implementation pattern** (from `backend/src/second_brain/services/abstract.py:83-97`):
```python
class StubEmailService(EmailServiceBase):
    """Stub email service that logs operations without sending."""

    async def send(self, to, subject, body, cc=None):
        return {"status": "stub", "to": to, "subject": subject}

    async def search(self, query, limit=10):
        return []
```
- Why: stub methods have untyped parameters, return minimal data. Used for `memory_provider="none"`.

**Config field + validator pattern** (from `backend/src/second_brain/config.py:94-98, 249-265`):
```python
graph_provider: str = Field(
    default="none",
    description="Graph memory provider: none, mem0, or graphiti",
)

@model_validator(mode="after")
def _validate_graph_config(self) -> "BrainConfig":
    if self.graph_provider == "graphiti":
        missing = []
        if not self.neo4j_url:
            missing.append("NEO4J_URL")
        if missing:
            raise ValueError(f"graph_provider='graphiti' requires: {', '.join(missing)}")
    return self
```
- Why: exact same `@model_validator(mode="after")` + missing-list pattern for `memory_provider`.

**Conditional service in create_deps** (from `backend/src/second_brain/deps.py:59-77`):
```python
graphiti = None
if config.graphiti_enabled:
    try:
        from second_brain.services.graphiti import GraphitiService
        graphiti = GraphitiService(config)
    except ImportError:
        logger.warning(
            "graphiti-core not installed. Install with: pip install -e '.[graphiti]'"
        )
```
- Why: lazy imports inside try/except, logger.warning with install hint, local var = None default.

**BrainDeps abstract type annotation** (from `backend/src/second_brain/deps.py:34`):
```python
email_service: "EmailServiceBase | None" = None
```
- Why: use base class type in BrainDeps, not concrete implementation. Enables provider swap.

---

## PLAN INDEX

| # | Phase | Sub-Plan File | Tasks | Context Load |
|---|-------|---------------|-------|--------------|
| 01 | Foundation | `requests/memory-provider-abstraction-plan-01-foundation.md` | 4 | Medium |
| 02 | Graphiti Adapter | `requests/memory-provider-abstraction-plan-02-graphiti-adapter.md` | 4 | Medium |
| 03 | Wiring | `requests/memory-provider-abstraction-plan-03-wiring.md` | 3 | Low |
| 04 | Tests | `requests/memory-provider-abstraction-plan-04-tests.md` | 4 | Medium |

---

## EXECUTION ROUTING

Each sub-plan runs in a fresh `/execute` session.
Recommended: Sonnet for all sub-plans.

### Execution Instructions

```bash
# Execute each sub-plan in a fresh session, in order
claude
> /execute requests/memory-provider-abstraction-plan-01-foundation.md

claude
> /execute requests/memory-provider-abstraction-plan-02-graphiti-adapter.md

claude
> /execute requests/memory-provider-abstraction-plan-03-wiring.md

claude
> /execute requests/memory-provider-abstraction-plan-04-tests.md
```

**Between sub-plans**: Read HANDOFF NOTES at the bottom of each completed sub-plan.
Sub-plans 02, 03, 04 each depend on earlier sub-plans completing successfully.

---

## ACCEPTANCE CRITERIA

- [ ] `MemoryServiceBase(ABC)` defined in `abstract.py` with all 13 abstract methods
- [ ] `StubMemoryService` defined in `abstract.py` (used for `memory_provider="none"`)
- [ ] `MemoryService` inherits from `MemoryServiceBase`
- [ ] `GraphitiMemoryAdapter(MemoryServiceBase)` exists in `services/graphiti_memory.py`
- [ ] `GraphitiService.add_episode` and `search` accept optional `group_id` parameter
- [ ] `config.py` has `memory_provider` field with validator requiring Neo4j/FalkorDB creds for `"graphiti"`
- [ ] `create_deps()` branches on `config.memory_provider` — no longer unconditionally creates Mem0
- [ ] `BrainDeps.memory_service` typed as `"MemoryServiceBase"` (not `"MemoryService"`)
- [ ] `MEMORY_PROVIDER=graphiti` makes all agents use Graphiti as primary memory backend
- [ ] `MEMORY_PROVIDER=none` makes agents see empty memory results (no crash)
- [ ] `MEMORY_PROVIDER=mem0` (default) behaves exactly as before — zero regressions
- [ ] All sub-plans executed successfully
- [ ] Full test suite passes (856 + new tests)

---

## COMPLETION CHECKLIST

- [ ] Sub-plan 01 (Foundation) — complete
- [ ] Sub-plan 02 (Graphiti Adapter) — complete
- [ ] Sub-plan 03 (Wiring) — complete
- [ ] Sub-plan 04 (Tests) — complete
- [ ] All acceptance criteria met
- [ ] Feature-wide manual validation passed
- [ ] README updated with `MEMORY_PROVIDER` env var
- [ ] Ready for `/commit`

---

## NOTES

### Key Design Decisions

- **Decomposed** because the feature touches 10+ files across config, services, deps, and tests.
  Each sub-plan is independently committable and testable.
- **GraphitiMemoryAdapter as a separate file** (not inside `graphiti.py`) — keeps concerns
  separated: `graphiti.py` = raw Graphiti client wrapper; `graphiti_memory.py` = MemoryServiceBase
  adapter. Makes testing cleaner and avoids bloating graphiti.py.
- **group_id as optional param on GraphitiService** — backward compatible; existing `graphiti_service`
  usage in agents (recall, learn, ask) passes no `group_id` and continues to work unfiltered.
  Only the adapter passes `group_id`.
- **Graphiti `search_()` vs `search()`** — `search_()` (with underscore) supports `group_ids=[]`
  filtering; `search()` (no underscore) does not. The adapter must use `search_()` via
  `self._graphiti._client.search_()` when `group_id` is needed.

### Risks

- **Risk 1**: `graphiti-core.search_()` method name may differ in older installed version —
  Mitigation: sub-plan 02 includes `hasattr` check + fallback to `search()` without group filtering
- **Risk 2**: Graphiti returns `EntityEdge` objects not dicts — adapter must handle attribute
  access (`.fact`, `.uuid`, `.source_node_name`, `.target_node_name`) defensively with `getattr`
- **Risk 3**: `StubMemoryService` must return `SearchResult` (not raw dict) for all `search*`
  methods — if it returns `[]` the agents will crash on `.memories` attribute access

### Confidence Score: 9/10

- **Strengths**: All method signatures verified from actual files. ABC pattern is exact match to
  existing codebase convention. group_id concept confirmed in Graphiti docs. Factory pattern in
  deps.py is already well-established.
- **Uncertainties**: Graphiti `search_()` method availability in pinned version; exact attribute
  names on `EntityEdge` objects at runtime.
- **Mitigations**: Defensive `getattr(..., "?")` calls (already used in `graphiti.py:193-196`);
  `hasattr` check for `search_()` availability.
