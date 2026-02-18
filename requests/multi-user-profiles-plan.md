# Feature: Multi-User Profiles (Supabase user_id Isolation)

## Feature Description

Add `user_id` column isolation to all Supabase storage tables so that multiple users can share
a single deployment (one Supabase project, one Mem0 account) with fully isolated data. Each user
is identified by a `brain_user_id` string set in their `.env` file. The `MemoryService` already
handles `user_id` isolation correctly via Mem0 — this plan closes the gap in `StorageService`,
which currently makes all Supabase tables globally visible across all users. One Supabase
migration adds the `user_id` column to 10 tables and updates the `vector_search` RPC function.
StorageService is updated to inject and filter `user_id` on every query. No new infrastructure,
no auth layer, no API changes — just data isolation at the storage layer.

## User Story

As an operator, I want to onboard a new user by setting `BRAIN_USER_ID=<name>` in their `.env`,
so that their patterns, experiences, examples, projects, and all other stored data are completely
isolated from every other user in the same Supabase deployment.

## Problem Statement

`StorageService` (storage.py) makes no reference to `brain_user_id`. Every query selects from
and inserts into the bare table with no user filter. If two users share the same Supabase project,
User B can see, modify, and delete User A's patterns, experiences, reviews, projects, etc. The
`vector_search` RPC function also performs no user filtering, leaking results across users. The
`MemoryService` already implements the correct pattern — it stores `self.user_id = config.brain_user_id`
and passes `user_id` to every Mem0 call. StorageService needs the same treatment.

## Solution Statement

- **Decision 1: Application-level filtering, not RLS** — The backend uses the Supabase service key,
  which bypasses RLS entirely. RLS would be dead weight. Explicit `.eq("user_id", self.user_id)`
  filters on every query are both sufficient and the recommended pattern for service-role backends.
- **Decision 2: `ALTER TABLE ... ADD COLUMN ... DEFAULT 'ryan'`** — PostgreSQL 11+ (Supabase runs
  15+) handles `NOT NULL DEFAULT 'constant'` as a near-instant metadata-only operation. No table
  rewrite, no backfill `UPDATE` needed. Existing rows automatically return `'ryan'` on read.
- **Decision 3: Inject user_id in service methods, not in callers** — `StorageService` creates a
  `{**data, "user_id": self.user_id}` copy before insert/upsert. Callers never need to know about
  user_id. This mirrors how `MemoryService` passes `user_id` to Mem0 internally.
- **Decision 4: Skip `content_types` for this iteration** — Content types are a shared catalog
  (built-in types apply to all users). Making them user-scoped requires an OR-filter pattern
  (`user_id = X OR is_builtin = true`) and is a v2 concern. Custom content types per user are an
  advanced feature.
- **Decision 5: Skip `project_artifacts`** — This table is a FK child of `projects`. Once
  `projects` is user-scoped, artifacts are transitively isolated via `project_id`. No direct
  user_id column needed.
- **Decision 6: Update `vector_search` SQL function** — The function searches across all rows
  with no user filter. Add `p_user_id TEXT DEFAULT 'ryan'` parameter and `AND user_id = $4`
  to the WHERE clause in the dynamic SQL.

## Feature Metadata

- **Feature Type**: Enhancement
- **Estimated Complexity**: Medium
- **Primary Systems Affected**: `supabase/migrations/`, `services/storage.py`, `tests/test_services.py`
- **Dependencies**: None — all changes are internal to this project

---

## CONTEXT REFERENCES

### Relevant Codebase Files

> IMPORTANT: The execution agent MUST read these files before implementing!

- `backend/src/second_brain/services/storage.py` (full file) — Why: contains every method that
  needs modification; read fully before implementing to understand exact signatures and query chains
- `backend/src/second_brain/services/storage.py` (lines 18-27) — Why: `__init__` method — add
  `self.user_id = config.brain_user_id` here, immediately after `self.config = config`
- `backend/src/second_brain/services/storage.py` (lines 30-45) — Why: `get_patterns` — canonical
  SELECT pattern with optional filters; shows where to insert the user_id eq filter
- `backend/src/second_brain/services/storage.py` (lines 545-583) — Why: `vector_search` method —
  shows how the RPC is called; must add `"p_user_id": self.user_id` to the params dict
- `backend/src/second_brain/services/memory.py` (lines 15-20) — Why: exact pattern to mirror for
  `self.user_id = config.brain_user_id` in `__init__`
- `backend/src/second_brain/services/memory.py` (lines 62-80) — Why: shows how `self.user_id`
  is passed as a kwarg; mirrors the pattern for insert methods
- `backend/supabase/migrations/013_quality_trending.sql` — Why: most recent ALTER TABLE style
  to follow (UPPERCASE, `ADD COLUMN IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`, schema_migrations insert)
- `backend/supabase/migrations/009_reinforce_pattern_rpc.sql` — Why: shows SQL function style
  and how RETURNS SETOF patterns works; reference for leaving reinforce_pattern unchanged
- `backend/supabase/migrations/010_vector_search_rpc.sql` — Why: the function we will update;
  read to understand current dynamic SQL construction and parameter numbering ($1, $2, $3)
- `backend/tests/test_services.py` — Why: test patterns for StorageService; understand existing
  mock chain setup before adding user_id assertions
- `backend/tests/conftest.py` (lines 103-203) — Why: `mock_storage` fixture — all AsyncMocks;
  understand what's already mocked before adding new test helpers

### New Files to Create

- `backend/supabase/migrations/015_user_id_isolation.sql` — SQL migration adding `user_id TEXT
  NOT NULL DEFAULT 'ryan'` to 10 tables plus indexes; also replaces `vector_search` function to
  accept `p_user_id` parameter

### Related Memories (from memory.md)

- Memory: `StorageService` uses `self._client` (private) not `self.client` — Relevance: all query
  chains use `self._client.table(...)`, not `self.client`; use the private attribute consistently
- Memory: `asyncio.to_thread` pattern uses `.execute` reference (not call) — Relevance: when
  passing inline chains to `asyncio.to_thread`, always pass `query.execute` not `query.execute()`;
  both forms exist in the file but the reference form is the memory-noted pattern
- Memory: Delete return pattern is `return len(result.data) > 0` — Relevance: all bool-returning
  delete methods must use this exact form, not `bool(result.data)`
- Memory: Plan code samples often have wrong `self.client` / `.execute()` / `logger.error` —
  Relevance: before implementing any task, re-read the actual file to verify the exact form in use

### Relevant Documentation

- [Supabase Python `.eq()` filter reference](https://supabase.com/docs/reference/python/eq)
  - Specific section: "Column is equal to a value"
  - Why: confirms `.eq(column, value)` chaining syntax for select, update, delete, upsert
- [PostgreSQL ALTER TABLE ADD COLUMN](https://www.postgresql.org/docs/current/ddl-alter.html)
  - Specific section: "Adding a Column"
  - Why: confirms that `ADD COLUMN ... NOT NULL DEFAULT 'constant'` is instant on PostgreSQL 11+
    (no table rewrite, no backfill needed); Supabase runs PostgreSQL 15+
- [Supabase Database Migrations](https://supabase.com/docs/guides/deployment/database-migrations)
  - Specific section: "Creating a migration"
  - Why: numbered migration file pattern and how to apply via dashboard SQL editor

### Patterns to Follow

**`StorageService.__init__` pattern** (from `storage.py:18-27`):
```python
class StorageService:
    def __init__(self, config: BrainConfig):
        self.config = config
        self._client: Client = create_client(
            config.supabase_url,
            config.supabase_key,
        )
```
- Why this pattern: add `self.user_id = config.brain_user_id` as the second line, immediately after
  `self.config = config`, before `self._client` — mirrors `MemoryService.__init__` exactly
- Common gotchas: do NOT rename `self._client` to `self.client` — it must stay private

**`MemoryService.__init__` user_id pattern** (from `memory.py:15-17`):
```python
def __init__(self, config: BrainConfig):
    self.config = config
    self.user_id = config.brain_user_id   # ← exact line to mirror in StorageService
```
- Why this pattern: single source of truth for user identity; set once, used everywhere
- Common gotchas: `brain_user_id` is the config field name (not `user_id` in config); `str` type

**SELECT with optional filter chain** (from `storage.py:30-45`):
```python
async def get_patterns(
    self, topic: str | None = None, confidence: str | None = None
) -> list[dict]:
    try:
        query = self._client.table("patterns").select("*")
        if topic:
            query = query.eq("topic", topic)
        if confidence:
            query = query.eq("confidence", confidence)
        query = query.order("date_updated", desc=True)
        result = await asyncio.to_thread(query.execute)
        return result.data
    except Exception as e:
        logger.warning("Supabase get_patterns failed: %s", type(e).__name__)
        logger.debug("Supabase error detail: %s", e)
        return []
```
- Why this pattern: add `.eq("user_id", self.user_id)` as the **first** filter, immediately after
  `.select("*")` and before any optional `if topic:` / `if category:` guards
- Common gotchas: the user_id filter is NOT conditional — it always applies; do not wrap in `if`

**INSERT/UPSERT — inject user_id into data copy** (pattern to introduce, mirroring Mem0 kwargs):
```python
async def add_experience(self, experience: dict) -> dict:
    try:
        data = {**experience, "user_id": self.user_id}   # non-mutating copy
        query = self._client.table("experiences").insert(data)
        result = await asyncio.to_thread(query.execute)
        return result.data[0] if result.data else {}
    except Exception as e:
        logger.warning("Supabase add_experience failed: %s", type(e).__name__)
        logger.debug("Supabase error detail: %s", e)
        return {}
```
- Why this pattern: use `{**original, "user_id": self.user_id}` — does not mutate the caller's
  dict; `user_id` key placed last so callers cannot accidentally override it
- Common gotchas: do NOT use `experience["user_id"] = self.user_id` (mutates caller's dict);
  do NOT expect caller to pass user_id — the service always injects it

**DELETE with user_id filter** (from `storage.py:146-155`, extended):
```python
async def delete_pattern(self, pattern_id: str) -> bool:
    try:
        query = (
            self._client.table("patterns")
            .delete()
            .eq("id", pattern_id)
            .eq("user_id", self.user_id)   # ← add this
        )
        result = await asyncio.to_thread(query.execute)
        return len(result.data) > 0
    except Exception as e:
        logger.warning("Supabase delete_pattern failed: %s", type(e).__name__)
        logger.debug("Supabase error detail: %s", e)
        return False
```
- Why this pattern: prevents cross-user deletes; `len(result.data) > 0` is the canonical bool form
- Common gotchas: `bool(result.data)` is wrong (per memory.md); always use `len(result.data) > 0`

**SQL migration style** (from `013_quality_trending.sql`):
```sql
ALTER TABLE examples ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES projects(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_review_history_type_date ON review_history(content_type, review_date DESC);
INSERT INTO schema_migrations (version, description)
VALUES ('013_quality_trending', '...')
ON CONFLICT (version) DO NOTHING;
```
- Why this pattern: UPPERCASE keywords, `IF NOT EXISTS` on both ALTER and CREATE INDEX, schema_migrations
  insert at the end with `ON CONFLICT DO NOTHING`
- Common gotchas: do NOT use lowercase SQL (style inconsistency); always use `IF NOT EXISTS` for idempotency

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation — SQL Migration

Write and apply the Supabase migration that adds the `user_id TEXT NOT NULL DEFAULT 'ryan'`
column to all 10 user-scoped tables plus performance indexes. Also update the `vector_search`
PostgreSQL function to accept `p_user_id` and filter results by it. This migration must be
applied to the Supabase project before the Python changes are deployed.

**Tasks:**
- Create `015_user_id_isolation.sql` with ALTER TABLE for all 10 tables
- Add `CREATE INDEX IF NOT EXISTS idx_<table>_user_id ON <table>(user_id)` for each table
- Replace `vector_search` function with updated version that accepts `p_user_id TEXT DEFAULT 'ryan'`
  and adds `AND user_id = $4` to the WHERE clause in the dynamic SQL
- Insert schema_migrations record

### Phase 2: Core Implementation — StorageService

Update `StorageService` to use `self.user_id` on every query. This is purely additive — no
existing method signatures change, no callers change.

**Tasks:**
- Add `self.user_id = config.brain_user_id` to `__init__`
- Add `.eq("user_id", self.user_id)` as the first filter on all SELECT methods for user-scoped tables
- Add `{**data, "user_id": self.user_id}` copy pattern to all INSERT/UPSERT methods
- Add `.eq("user_id", self.user_id)` to all DELETE and UPDATE methods for user-scoped tables
- Add `"p_user_id": self.user_id` to the `vector_search` RPC params dict

### Phase 3: Testing & Validation

Update existing test_services.py tests to account for the new user_id filter in query chains,
and add new isolation tests that verify user_id is correctly injected.

**Tasks:**
- Update `test_get_patterns` and similar SELECT tests: `mock_table.eq` now gets called N+1 times
  (once for user_id, plus once per optional filter applied); assert user_id call is present
- Update INSERT tests: assert `"user_id"` key is in the data passed to `.insert()` / `.upsert()`
- Add `test_storage_service_user_id_set`: verify `StorageService(config).user_id == config.brain_user_id`
- Add `test_get_patterns_filters_by_user_id`: verify `.eq` called with `("user_id", "ryan")`
- Add `test_add_experience_injects_user_id`: verify `"user_id"` present in insert call data
- Add `test_vector_search_passes_user_id`: verify RPC params include `p_user_id`

---

## STEP-BY-STEP TASKS

> Execute every task in order, top to bottom. Read each TARGET file fully before modifying.

### CREATE `backend/supabase/migrations/015_user_id_isolation.sql`

- **IMPLEMENT**: Create the migration file with the following exact content:

```sql
-- Migration 015: Add user_id isolation to all user-scoped tables
-- Allows multiple users to share one Supabase deployment with fully isolated data.
-- PostgreSQL 15+ (Supabase): ADD COLUMN NOT NULL DEFAULT 'constant' is a near-instant
-- metadata operation — no table rewrite, no backfill needed.

-- === ADD user_id COLUMN TO ALL USER-SCOPED TABLES ===

ALTER TABLE patterns            ADD COLUMN IF NOT EXISTS user_id TEXT NOT NULL DEFAULT 'ryan';
ALTER TABLE experiences         ADD COLUMN IF NOT EXISTS user_id TEXT NOT NULL DEFAULT 'ryan';
ALTER TABLE brain_health        ADD COLUMN IF NOT EXISTS user_id TEXT NOT NULL DEFAULT 'ryan';
ALTER TABLE growth_log          ADD COLUMN IF NOT EXISTS user_id TEXT NOT NULL DEFAULT 'ryan';
ALTER TABLE review_history      ADD COLUMN IF NOT EXISTS user_id TEXT NOT NULL DEFAULT 'ryan';
ALTER TABLE confidence_history  ADD COLUMN IF NOT EXISTS user_id TEXT NOT NULL DEFAULT 'ryan';
ALTER TABLE memory_content      ADD COLUMN IF NOT EXISTS user_id TEXT NOT NULL DEFAULT 'ryan';
ALTER TABLE examples            ADD COLUMN IF NOT EXISTS user_id TEXT NOT NULL DEFAULT 'ryan';
ALTER TABLE knowledge_repo      ADD COLUMN IF NOT EXISTS user_id TEXT NOT NULL DEFAULT 'ryan';
ALTER TABLE projects            ADD COLUMN IF NOT EXISTS user_id TEXT NOT NULL DEFAULT 'ryan';

-- === INDEXES FOR QUERY PERFORMANCE ===

CREATE INDEX IF NOT EXISTS idx_patterns_user_id           ON patterns(user_id);
CREATE INDEX IF NOT EXISTS idx_experiences_user_id        ON experiences(user_id);
CREATE INDEX IF NOT EXISTS idx_brain_health_user_id       ON brain_health(user_id);
CREATE INDEX IF NOT EXISTS idx_growth_log_user_id         ON growth_log(user_id);
CREATE INDEX IF NOT EXISTS idx_review_history_user_id     ON review_history(user_id);
CREATE INDEX IF NOT EXISTS idx_confidence_history_user_id ON confidence_history(user_id);
CREATE INDEX IF NOT EXISTS idx_memory_content_user_id     ON memory_content(user_id);
CREATE INDEX IF NOT EXISTS idx_examples_user_id           ON examples(user_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_repo_user_id     ON knowledge_repo(user_id);
CREATE INDEX IF NOT EXISTS idx_projects_user_id           ON projects(user_id);

-- === UPDATE vector_search FUNCTION TO FILTER BY USER ===
-- Adds p_user_id parameter so vector searches only return the requesting user's rows.
-- Default 'ryan' preserves backward compatibility for any callers not yet updated.

CREATE OR REPLACE FUNCTION vector_search(
  query_embedding vector(1024),
  match_table TEXT,
  match_count INT DEFAULT 10,
  match_threshold FLOAT DEFAULT 0.7,
  p_user_id TEXT DEFAULT 'ryan'
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
    'AND user_id = $4 '
    'AND 1 - (embedding <=> $1) >= $2 '
    'ORDER BY embedding <=> $1 '
    'LIMIT $3',
    match_table
  ) USING query_embedding, match_threshold, match_count, p_user_id;
END;
$$;

-- === RECORD MIGRATION ===

INSERT INTO schema_migrations (version, description)
VALUES ('015_user_id_isolation', 'Add user_id column to all user-scoped tables for multi-user isolation')
ON CONFLICT (version) DO NOTHING;
```

- **PATTERN**: `backend/supabase/migrations/013_quality_trending.sql` — ALTER TABLE style, index
  creation style, and schema_migrations insert format
- **IMPORTS**: None (SQL file)
- **GOTCHA**: The original `vector_search` used `vector(1536)` but migration 011 updated
  dimensions for Voyage AI to 1024. Use `vector(1024)` to match current embedding dimensions.
  The `DEFAULT 'ryan'` on `p_user_id` is backward-compatible — existing Python code calling the
  old function signature still works until Task 6 updates it.
- **VALIDATE**: Apply in Supabase dashboard SQL editor. Verify with:
  `SELECT column_name FROM information_schema.columns WHERE table_name='patterns' AND column_name='user_id';`

---

### UPDATE `backend/src/second_brain/services/storage.py` — `__init__` method

- **IMPLEMENT**: Add `self.user_id = config.brain_user_id` as the second line of `__init__`,
  immediately after `self.config = config` and before `self._client = create_client(...)`.

  Current (lines 21-26):
  ```python
  def __init__(self, config: BrainConfig):
      self.config = config
      self._client: Client = create_client(
          config.supabase_url,
          config.supabase_key,
      )
  ```

  Replace with:
  ```python
  def __init__(self, config: BrainConfig):
      self.config = config
      self.user_id = config.brain_user_id
      self._client: Client = create_client(
          config.supabase_url,
          config.supabase_key,
      )
  ```

- **PATTERN**: `backend/src/second_brain/services/memory.py:15-17` — identical one-liner that
  mirrors `self.user_id = config.brain_user_id`
- **IMPORTS**: None (no new imports needed)
- **GOTCHA**: `config.brain_user_id` is the field name (not `config.user_id`). Verify in
  `config.py:132`: `brain_user_id: str = Field(default="ryan", ...)`.
- **VALIDATE**: `python -c "from second_brain.services.storage import StorageService; print('ok')"`

---

### UPDATE `backend/src/second_brain/services/storage.py` — SELECT methods (user-scoped tables)

- **IMPLEMENT**: Add `.eq("user_id", self.user_id)` as the **first** filter on every SELECT
  method that queries a user-scoped table. The filter is unconditional — never inside an `if`.
  Apply to ALL of the following methods (read the full file to find each):

  1. **`get_patterns`** (line 30): after `.select("*")`, before `if topic:`
     ```python
     query = self._client.table("patterns").select("*")
     query = query.eq("user_id", self.user_id)   # ← add
     if topic:
     ```

  2. **`get_pattern_by_name`** (line 81): after `.select("*")`, before `.ilike`
     ```python
     query = (
         self._client.table("patterns")
         .select("*")
         .eq("user_id", self.user_id)   # ← add
         .ilike("name", name)
         .limit(1)
     )
     ```

  3. **`get_pattern_by_id`** (line 97): add to inline chain after `.select("*")`
     ```python
     result = await asyncio.to_thread(
         self._client.table("patterns")
         .select("*")
         .eq("user_id", self.user_id)   # ← add
         .eq("id", pattern_id)
         .execute
     )
     ```

  4. **`get_experiences`** (line 169): after `.select("*")`, before `if category:`
     ```python
     query = self._client.table("experiences").select("*")
     query = query.eq("user_id", self.user_id)   # ← add
     if category:
     ```

  5. **`get_experience_by_id`** (line 195): add to inline chain after `.select("*")`
     ```python
     result = await asyncio.to_thread(
         self._client.table("experiences")
         .select("*")
         .eq("user_id", self.user_id)   # ← add
         .eq("id", experience_id)
         .execute
     )
     ```

  6. **`get_health_history`** (line 229): add after `.select("*")`, before `.order`
     ```python
     query = (
         self._client.table("brain_health")
         .select("*")
         .eq("user_id", self.user_id)   # ← add
         .order("date", desc=True)
         .limit(limit)
     )
     ```

  7. **`get_growth_events`** (line 257): after `.select("*")`, before `if event_type:`
     ```python
     query = self._client.table("growth_log").select("*")
     query = query.eq("user_id", self.user_id)   # ← add
     if event_type:
     ```

  8. **`get_review_history`** (line 303): after `.select("*")`, before `if content_type:`
     ```python
     query = self._client.table("review_history").select("*")
     query = query.eq("user_id", self.user_id)   # ← add
     if content_type:
     ```

  9. **`get_confidence_history`** (line 334): after `.select("*")`, before `if pattern_name:`
     ```python
     query = self._client.table("confidence_history").select("*")
     query = query.eq("user_id", self.user_id)   # ← add
     if pattern_name:
     ```

  10. **`get_memory_content`** (line 354): after `.select("*")`, before `.eq("category", ...)`
      ```python
      query = self._client.table("memory_content").select("*")
      query = query.eq("user_id", self.user_id)   # ← add
      query = query.eq("category", category)
      ```

  11. **`get_examples`** (line 409): after `.select("*")`, before `if content_type:`
      ```python
      query = self._client.table("examples").select("*")
      query = query.eq("user_id", self.user_id)   # ← add
      if content_type:
      ```

  12. **`get_knowledge`** (line 447): after `.select("*")`, before `if category:`
      ```python
      query = self._client.table("knowledge_repo").select("*")
      query = query.eq("user_id", self.user_id)   # ← add
      if category:
      ```

  13. **`list_projects`** (line 614): after `.select("*")`, before `if lifecycle_stage:`
      ```python
      query = self._client.table("projects").select("*")
      query = query.eq("user_id", self.user_id)   # ← add
      if lifecycle_stage:
      ```

  14. **`get_project`** (line 599): add to inline chain after `.select("*, project_artifacts(*)")`
      ```python
      result = await asyncio.to_thread(
          self._client.table("projects")
          .select("*, project_artifacts(*)")
          .eq("user_id", self.user_id)   # ← add
          .eq("id", project_id)
          .execute
      )
      ```

  **SKIP**: `get_patterns_for_content_type` (delegates to `get_patterns`) — no direct query.
  **SKIP**: `get_growth_event_counts` (delegates to `get_growth_events`) — no direct query.
  **SKIP**: `get_content_types`, `get_content_type_by_slug` — content_types is shared catalog.

- **PATTERN**: `storage.py:30-45` — `get_patterns` as the canonical SELECT pattern; user_id
  filter goes first, before all optional filters
- **IMPORTS**: None
- **GOTCHA**: The inline chain form (used in `get_pattern_by_id`, `get_health_history`, etc.)
  passes `.execute` as a callable reference — NOT `.execute()`. Preserve this exactly. Also note
  `get_memory_content` already has a required (non-optional) `category` filter; user_id still goes
  first before that required filter.
- **VALIDATE**: `cd backend && pytest tests/test_services.py -x -q 2>&1 | head -30`

---

### UPDATE `backend/src/second_brain/services/storage.py` — INSERT/UPSERT methods

- **IMPLEMENT**: For every INSERT/UPSERT method on user-scoped tables, replace the raw `data`
  argument with `{**data, "user_id": self.user_id}` to inject user_id without mutating the caller's
  dict. Apply to ALL of the following methods:

  1. **`upsert_pattern`** (line 60):
     ```python
     async def upsert_pattern(self, pattern: dict) -> dict:
         try:
             data = {**pattern, "user_id": self.user_id}
             query = self._client.table("patterns").upsert(data)
     ```

  2. **`insert_pattern`** (line 70):
     ```python
     async def insert_pattern(self, pattern: dict) -> dict:
         try:
             data = {**pattern, "user_id": self.user_id}
             query = self._client.table("patterns").insert(data)
     ```

  3. **`add_experience`** (line 159):
     ```python
     async def add_experience(self, experience: dict) -> dict:
         try:
             data = {**experience, "user_id": self.user_id}
             query = self._client.table("experiences").insert(data)
     ```

  4. **`add_health_snapshot`** (line 219):
     ```python
     async def add_health_snapshot(self, snapshot: dict) -> dict:
         try:
             data = {**snapshot, "user_id": self.user_id}
             query = self._client.table("brain_health").insert(data)
     ```

  5. **`add_growth_event`** (line 246):
     ```python
     async def add_growth_event(self, event: dict) -> dict:
         try:
             data = {**event, "user_id": self.user_id}
             query = self._client.table("growth_log").insert(data)
     ```

  6. **`add_review_history`** (line 292):
     ```python
     async def add_review_history(self, entry: dict) -> dict:
         try:
             data = {**entry, "user_id": self.user_id}
             query = self._client.table("review_history").insert(data)
     ```

  7. **`add_confidence_transition`** (line 323):
     ```python
     async def add_confidence_transition(self, transition: dict) -> dict:
         try:
             data = {**transition, "user_id": self.user_id}
             query = self._client.table("confidence_history").insert(data)
     ```

  8. **`upsert_memory_content`** (line 369):
     ```python
     async def upsert_memory_content(self, content: dict) -> dict:
         try:
             data = {**content, "user_id": self.user_id}
             query = self._client.table("memory_content").upsert(data)
     ```

  9. **`upsert_example`** (line 424):
     ```python
     async def upsert_example(self, example: dict) -> dict:
         try:
             data = {**example, "user_id": self.user_id}
             query = self._client.table("examples").upsert(data)
     ```

  10. **`upsert_knowledge`** (line 462):
      ```python
      async def upsert_knowledge(self, knowledge: dict) -> dict:
          try:
              data = {**knowledge, "user_id": self.user_id}
              query = self._client.table("knowledge_repo").upsert(data)
      ```

  11. **`create_project`** (line 587): uses inline chain form — inject user_id into project dict
      ```python
      async def create_project(self, project: dict) -> dict:
          try:
              data = {**project, "user_id": self.user_id}
              result = await asyncio.to_thread(
                  self._client.table("projects").insert(data).execute
              )
      ```

  **SKIP**: `upsert_content_type` — content_types is the shared catalog; no user_id injection.

- **PATTERN**: `storage.py:159-167` — `add_experience` as the canonical insert example; the
  `{**original_dict, "user_id": self.user_id}` copy is the uniform pattern
- **IMPORTS**: None
- **GOTCHA**: Use `{**original, "user_id": self.user_id}` — NOT `original["user_id"] = ...`
  (that mutates the caller's dict). The `user_id` key goes last so callers cannot accidentally
  override it even if they include a `user_id` key themselves.
- **VALIDATE**: `cd backend && pytest tests/test_services.py -x -q -k "add or upsert or insert or create"`

---

### UPDATE `backend/src/second_brain/services/storage.py` — DELETE and UPDATE methods

- **IMPLEMENT**: Add `.eq("user_id", self.user_id)` to every DELETE method on user-scoped tables.
  Also add to UPDATE methods that operate on user-scoped tables.

  1. **`delete_pattern`** (line 146): add user_id eq to chain
     ```python
     query = (
         self._client.table("patterns")
         .delete()
         .eq("id", pattern_id)
         .eq("user_id", self.user_id)   # ← add
     )
     ```

  2. **`delete_experience`** (line 184): add user_id eq
     ```python
     query = (
         self._client.table("experiences")
         .delete()
         .eq("id", experience_id)
         .eq("user_id", self.user_id)   # ← add
     )
     ```

  3. **`delete_memory_content`** (line 379): inline chain form — add `.eq("user_id", self.user_id)`
     ```python
     result = await asyncio.to_thread(
         self._client.table("memory_content")
         .delete()
         .eq("category", category)
         .eq("subcategory", subcategory)
         .eq("user_id", self.user_id)   # ← add
         .execute
     )
     ```

  4. **`delete_example`** (line 434): add user_id eq
     ```python
     query = (
         self._client.table("examples")
         .delete()
         .eq("id", example_id)
         .eq("user_id", self.user_id)   # ← add
     )
     ```

  5. **`delete_knowledge`** (line 472): add user_id eq
     ```python
     query = (
         self._client.table("knowledge_repo")
         .delete()
         .eq("id", knowledge_id)
         .eq("user_id", self.user_id)   # ← add
     )
     ```

  6. **`delete_project`** (line 678): inline chain form — add `.eq("user_id", self.user_id)`
     ```python
     result = await asyncio.to_thread(
         self._client.table("projects")
         .delete()
         .eq("id", project_id)
         .eq("user_id", self.user_id)   # ← add
         .execute
     )
     ```

  7. **`update_project_stage`** (line 633): inline chain — add `.eq("user_id", self.user_id)`
     ```python
     result = await asyncio.to_thread(
         self._client.table("projects")
         .update(update_data)
         .eq("id", project_id)
         .eq("user_id", self.user_id)   # ← add
         .execute
     )
     ```

  8. **`update_project`** (line 655): inline chain — add `.eq("user_id", self.user_id)`
     ```python
     result = await asyncio.to_thread(
         self._client.table("projects")
         .update(fields)
         .eq("id", project_id)
         .eq("user_id", self.user_id)   # ← add
         .execute
     )
     ```

  **SKIP**: `delete_content_type` — content_types is shared catalog, no user_id filter.

- **PATTERN**: `storage.py:146-155` — `delete_pattern` canonical delete pattern with bool return
- **IMPORTS**: None
- **GOTCHA**: `delete_memory_content` uses the inline `asyncio.to_thread(chain.execute)` form (not
  the `query = ...; result = await asyncio.to_thread(query.execute)` form). Add `.eq("user_id",
  self.user_id)` before `.execute` in the chain. The return is `len(result.data) > 0`.
- **VALIDATE**: `cd backend && pytest tests/test_services.py -x -q -k "delete"`

---

### UPDATE `backend/src/second_brain/services/storage.py` — `vector_search` method

- **IMPLEMENT**: Add `"p_user_id": self.user_id` to the RPC params dict in `vector_search`
  (line 568).

  Current (lines 567-578):
  ```python
  result = await asyncio.to_thread(
      self._client.rpc(
          "vector_search",
          {
              "query_embedding": embedding,
              "match_table": table,
              "match_count": limit,
              "match_threshold": similarity_threshold,
          }
      ).execute
  )
  ```

  Replace with:
  ```python
  result = await asyncio.to_thread(
      self._client.rpc(
          "vector_search",
          {
              "query_embedding": embedding,
              "match_table": table,
              "match_count": limit,
              "match_threshold": similarity_threshold,
              "p_user_id": self.user_id,
          }
      ).execute
  )
  ```

- **PATTERN**: `storage.py:119-128` — `reinforce_pattern` shows existing RPC call style with
  dict params; `.execute` is a reference (no parentheses)
- **IMPORTS**: None
- **GOTCHA**: The SQL function parameter name is `p_user_id` (with prefix, matching the convention
  from `reinforce_pattern` which uses `p_pattern_id`). The Python dict key must match the SQL
  parameter name exactly. Do NOT use `"user_id"` as the key.
- **VALIDATE**: `cd backend && pytest tests/test_services.py -x -q -k "vector_search"`

---

### UPDATE `backend/tests/test_services.py` — existing SELECT test assertions

- **IMPLEMENT**: For each `TestStorageService` test that verifies query chain calls via
  `mock_table.eq.assert_called_with` or `mock_table.eq.call_count`, update to account for the
  new unconditional `.eq("user_id", self.user_id)` call that now precedes all other filters.

  Read `test_services.py` fully first. For every test where `mock_table.eq` is asserted:

  - If a test asserts `mock_table.eq.call_count == N`, update to `call_count == N + 1`
  - If a test asserts `mock_table.eq.assert_called_with(...)` for a specific filter, also assert
    the user_id call was made first:
    ```python
    # After: assert user_id filter present
    mock_table.eq.assert_any_call("user_id", "ryan")
    ```
  - If a test for `get_patterns` without optional filters currently expects `eq` not called,
    update: it will now be called once for user_id.

  For INSERT/UPSERT tests, find where mock_table.insert or mock_table.upsert is called and
  assert the data includes user_id:
  ```python
  call_args = mock_table.insert.call_args[0][0]   # first positional arg
  assert call_args["user_id"] == "ryan"
  ```

  For `test_vector_search` (if it exists), assert that the RPC params include `"p_user_id"`:
  ```python
  rpc_params = mock_client.rpc.call_args[0][1]   # second positional arg (params dict)
  assert rpc_params["p_user_id"] == "ryan"
  ```

- **PATTERN**: `backend/tests/test_services.py` (existing TestStorageService tests) — use the
  same `@patch("second_brain.services.storage.create_client")` setup; read the file fully first
- **IMPORTS**: No new imports (already uses `from unittest.mock import MagicMock, AsyncMock, patch`)
- **GOTCHA**: `mock_table.eq.return_value = mock_table` is already set in the MagicMock chain
  setup (any attribute of a MagicMock returns another MagicMock by default, and chaining works).
  Existing tests will NOT break just from adding user_id filters — only assertion-based tests
  need updating. Run `pytest test_services.py -x` first to see which ones fail.
- **VALIDATE**: `cd backend && pytest tests/test_services.py -x -v 2>&1 | head -50`

---

### ADD new tests to `backend/tests/test_services.py` — user isolation tests

- **IMPLEMENT**: Add a `TestStorageServiceUserIsolation` class (or additional methods to
  `TestStorageService`) with the following new test cases. Add after the existing
  `TestStorageService` class.

  ```python
  class TestStorageServiceUserIsolation:
      """Verify user_id is always applied to queries and inserts."""

      def test_user_id_set_from_config(self, mock_config):
          """StorageService.user_id is set from config.brain_user_id at init."""
          with patch("second_brain.services.storage.create_client"):
              service = StorageService(mock_config)
          assert service.user_id == mock_config.brain_user_id

      @patch("second_brain.services.storage.create_client")
      async def test_get_patterns_filters_by_user_id(self, mock_create, mock_config):
          """get_patterns always applies user_id eq filter."""
          mock_client = MagicMock()
          mock_table = MagicMock()
          mock_table.select.return_value = mock_table
          mock_table.eq.return_value = mock_table
          mock_table.order.return_value = mock_table
          mock_table.execute.return_value = MagicMock(data=[])
          mock_client.table.return_value = mock_table
          mock_create.return_value = mock_client

          service = StorageService(mock_config)
          await service.get_patterns()

          mock_table.eq.assert_any_call("user_id", mock_config.brain_user_id)

      @patch("second_brain.services.storage.create_client")
      async def test_add_experience_injects_user_id(self, mock_create, mock_config):
          """add_experience injects user_id into the insert payload."""
          mock_client = MagicMock()
          mock_table = MagicMock()
          mock_table.insert.return_value = mock_table
          mock_table.execute.return_value = MagicMock(data=[{"id": "exp-1"}])
          mock_client.table.return_value = mock_table
          mock_create.return_value = mock_client

          service = StorageService(mock_config)
          await service.add_experience({"task": "coding", "outcome": "success"})

          call_data = mock_table.insert.call_args[0][0]
          assert call_data["user_id"] == mock_config.brain_user_id
          assert call_data["task"] == "coding"

      @patch("second_brain.services.storage.create_client")
      async def test_delete_pattern_filters_by_user_id(self, mock_create, mock_config):
          """delete_pattern applies user_id eq filter to prevent cross-user deletes."""
          mock_client = MagicMock()
          mock_table = MagicMock()
          mock_table.delete.return_value = mock_table
          mock_table.eq.return_value = mock_table
          mock_table.execute.return_value = MagicMock(data=[{"id": "pat-1"}])
          mock_client.table.return_value = mock_table
          mock_create.return_value = mock_client

          service = StorageService(mock_config)
          result = await service.delete_pattern("pat-1")

          assert result is True
          mock_table.eq.assert_any_call("user_id", mock_config.brain_user_id)

      @patch("second_brain.services.storage.create_client")
      async def test_vector_search_passes_user_id_to_rpc(self, mock_create, mock_config):
          """vector_search passes p_user_id to the RPC function."""
          mock_client = MagicMock()
          mock_rpc = MagicMock()
          mock_rpc.execute.return_value = MagicMock(data=[])
          mock_client.rpc.return_value = mock_rpc
          mock_create.return_value = mock_client

          service = StorageService(mock_config)
          await service.vector_search(embedding=[0.1] * 1024, table="patterns")

          rpc_call_params = mock_client.rpc.call_args[0][1]
          assert rpc_call_params["p_user_id"] == mock_config.brain_user_id

      @patch("second_brain.services.storage.create_client")
      async def test_create_project_injects_user_id(self, mock_create, mock_config):
          """create_project injects user_id into the insert payload."""
          mock_client = MagicMock()
          mock_table = MagicMock()
          mock_table.insert.return_value = mock_table
          mock_table.execute.return_value = MagicMock(data=[{"id": "proj-1"}])
          mock_client.table.return_value = mock_table
          mock_create.return_value = mock_client

          service = StorageService(mock_config)
          await service.create_project({"name": "Test Project", "category": "content"})

          call_data = mock_table.insert.call_args[0][0]
          assert call_data["user_id"] == mock_config.brain_user_id
  ```

- **PATTERN**: `backend/tests/test_services.py` `TestStorageService` class — same
  `@patch("second_brain.services.storage.create_client")` decorator, same MagicMock chain setup
- **IMPORTS**: Already present in test_services.py: `from unittest.mock import MagicMock, AsyncMock, patch`
- **GOTCHA**: In the `test_vector_search_passes_user_id_to_rpc` test, note that `vector_search`
  uses `asyncio.to_thread(self._client.rpc(...).execute)` — the `.execute` is a reference, not
  a call. The mock will need `mock_rpc.execute` (attribute, not return value) to work correctly.
  If the test fails, verify whether `asyncio.to_thread` receives `.execute` or `.execute()` by
  reading the actual storage.py line.
- **VALIDATE**: `cd backend && pytest tests/test_services.py::TestStorageServiceUserIsolation -v`

---

## TESTING STRATEGY

### Unit Tests

Each modified method in `StorageService` should have a corresponding test verifying:
1. `user_id` eq filter is present in SELECT query chains (`mock_table.eq.assert_any_call("user_id", "ryan")`)
2. `user_id` key is in the data dict for INSERT/UPSERT operations
3. `user_id` eq filter is present in DELETE/UPDATE query chains
4. `p_user_id` is in the RPC params for `vector_search`

All tests use `@patch("second_brain.services.storage.create_client")` to avoid real Supabase
connections. The MagicMock chain (`mock_table.eq.return_value = mock_table`) already handles
chained calls correctly.

### Integration Tests

Apply migration 015 to Supabase (dashboard SQL editor or `supabase db push`), then run the
MCP server manually and verify:
- `recall("my patterns")` returns only data for `BRAIN_USER_ID=ryan`
- If `BRAIN_USER_ID` is changed to `alice`, the same `recall` call returns no data (isolated)

### Edge Cases

- **Caller passes `user_id` in dict**: `{**data, "user_id": self.user_id}` silently overwrites any
  caller-provided `user_id` — this is intentional; the service is authoritative over user identity
- **Migration re-run**: `IF NOT EXISTS` guards on ALTER TABLE and CREATE INDEX make migration
  idempotent; `ON CONFLICT DO NOTHING` on schema_migrations insert also idempotent
- **`get_patterns_for_content_type` delegation**: calls `get_patterns()` which will be filtered;
  no change needed but verify it still works by running its tests
- **`get_growth_event_counts` delegation**: calls `get_growth_events()` which will be filtered;
  no direct change but validate via test
- **`reinforce_pattern` RPC**: operates by pattern UUID; does not need user_id filter since:
  (a) UUID is hard to guess, (b) the pattern was fetched from a user-scoped SELECT; acceptable
  for v1 — note as v2 hardening item

---

## VALIDATION COMMANDS

### Level 1: Syntax Check
```bash
cd backend
python -c "from second_brain.services.storage import StorageService; print('import ok')"
```

### Level 2: Unit Tests
```bash
cd backend
pytest tests/test_services.py -v -q
pytest tests/test_services.py::TestStorageServiceUserIsolation -v
```

### Level 3: Full Test Suite (regression check)
```bash
cd backend
pytest --tb=short -q
```
Expected: test count >= 849 (843 existing + 6 new isolation tests). Zero regressions.

### Level 4: Manual Validation

After applying migration 015 to Supabase and running the MCP server:
```bash
# Start server
cd backend && python -m second_brain.mcp_server

# In Claude Code — call a tool that queries Supabase:
# Verify it returns only data for brain_user_id configured in .env
```

Also validate migration applied:
```sql
-- Run in Supabase SQL editor
SELECT table_name, column_name, column_default
FROM information_schema.columns
WHERE column_name = 'user_id'
  AND table_schema = 'public'
ORDER BY table_name;
-- Expected: 10 rows (patterns, experiences, brain_health, growth_log,
--           review_history, confidence_history, memory_content,
--           examples, knowledge_repo, projects)
```

### Level 5: Index Verification
```sql
-- Run in Supabase SQL editor
SELECT indexname, tablename
FROM pg_indexes
WHERE indexname LIKE 'idx_%_user_id'
ORDER BY tablename;
-- Expected: 10 indexes
```

---

## ACCEPTANCE CRITERIA

### Implementation (verify during execution)

- [x] Migration 015 created with all 10 ALTER TABLE statements and 10 indexes
- [x] `vector_search` SQL function updated with `p_user_id` parameter and WHERE filter
- [x] `StorageService.__init__` sets `self.user_id = config.brain_user_id`
- [x] All 14 SELECT methods on user-scoped tables have unconditional `.eq("user_id", self.user_id)` filter
- [x] All 11 INSERT/UPSERT methods inject `user_id` via `{**data, "user_id": self.user_id}`
- [x] All 8 DELETE/UPDATE methods have `.eq("user_id", self.user_id)` filter
- [x] `vector_search` method passes `"p_user_id": self.user_id` in RPC params
- [x] `content_types` table and its methods are unchanged (shared catalog)
- [x] `project_artifacts` table and its methods are unchanged (FK-isolated via projects)
- [x] All new tests pass: `pytest tests/test_services.py::TestStorageServiceUserIsolation -v`
- [x] Full test suite passes with zero regressions: `pytest -q`

### Runtime (verify after testing/deployment)

- [ ] Migration 015 applied to Supabase; `user_id` column present on all 10 tables
- [ ] Vector search index verification query returns 10 indexes
- [ ] MCP server starts with no errors
- [ ] Recall tool returns only data scoped to configured `BRAIN_USER_ID`
- [ ] No existing functionality broken (all agents behave identically for single-user case)

---

## COMPLETION CHECKLIST

- [x] All tasks completed in order
- [ ] Migration SQL applied to Supabase before running Python tests
- [x] Each task validation passed
- [x] All validation commands executed successfully
- [x] Full test suite passes (843+ tests, zero regressions)
- [x] No linting or import errors
- [ ] Manual testing confirms recall/search returns user-scoped data
- [x] Acceptance criteria all met

---

## NOTES

### Key Design Decisions

- **Application-level filtering is correct** — the service key bypasses RLS; adding `.eq("user_id")`
  in Python is both sufficient and better for query performance (PostgreSQL uses the index directly
  rather than evaluating a policy expression at runtime)
- **PostgreSQL 11+ fast ADD COLUMN** — Supabase runs PostgreSQL 15; `ALTER TABLE ... ADD COLUMN
  ... NOT NULL DEFAULT 'constant'` is instant; no multi-step migration needed
- **`{**data, "user_id": self.user_id}` pattern** — non-mutating dict copy; user_id goes last to
  be the authoritative value even if caller accidentally includes a user_id key
- **content_types skipped** — built-in content types are system-wide; adding user_id would require
  OR-filter logic (`user_id = X OR is_builtin = true`); defer to v2 if custom types per user needed
- **project_artifacts skipped** — transitively isolated via projects.user_id FK; no direct filter needed
- **reinforce_pattern RPC unchanged** — operates by UUID primary key; pattern was fetched from
  user-scoped query; UUID collision probability is negligible; update to v2 if paranoid security needed

### Risks

- **Risk 1**: Migration 015 fails if Supabase project is on a very old PostgreSQL version —
  Mitigation: Supabase runs PostgreSQL 15+; fast ADD COLUMN is supported since 11; negligible risk
- **Risk 2**: Some tests assert exact `mock_table.eq.call_count` which will now be off by 1 —
  Mitigation: Task 7 explicitly updates those assertions; run `pytest -x` first to identify failures
- **Risk 3**: `vector_search` test may need special handling for `asyncio.to_thread` with
  `.execute` reference vs `.execute()` call — Mitigation: read the actual storage.py line before
  writing the test mock setup; the GOTCHA in Task 8 documents this

### Confidence Score: 9/10

- **Strengths**: All table names, method signatures, and line numbers are verified against the
  actual file. SQL migration pattern is confirmed. The MemoryService user_id pattern is exact.
  PostgreSQL behavior for fast ADD COLUMN is well-documented. No external API changes.
- **Uncertainties**: The exact `mock_table.eq.call_count` values in existing tests are not
  enumerated here — Task 7 says "run pytest -x first to find failures" which is the right approach.
  The vector_search test mock setup for `asyncio.to_thread` needs care.
- **Mitigations**: Read each file before implementing. Run pytest -x after each task. The
  migration is idempotent (`IF NOT EXISTS`) so it can be re-applied safely if something goes wrong.
