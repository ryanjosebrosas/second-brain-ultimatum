# Code Review: Data Infrastructure, Docs & Tests

**Mode**: Parallel (4 agents)
**Files Modified**: 3 (README.md, test_config.py, test_services.py)
**Files Added**: 3 (mcp-usage-guide.md, supabase-postgrest-fix.md, content-writer-voice-fix-review.md)
**Files Deleted**: 1 (auth-wsl-fallback-review.md)
**Total Findings**: 18 (Critical: 0, Major: 6, Minor: 12)

---

## Critical Findings

None.

---

## Major Findings

### 1. [Security] Insecure Default Bind Address
- **File**: `backend/src/second_brain/config.py:287` (tested at `test_config.py:64`)
- **Issue**: Default `mcp_host` is `0.0.0.0`, binding to all network interfaces
- **Detail**: When `MCP_TRANSPORT=http`, the MCP server is network-exposed by default. Combined with unauthenticated `set_user()` tool, any host on the same network can pivot to any user's data
- **Suggestion**: Change default to `127.0.0.1`. Only use `0.0.0.0` when explicitly configured

### 2. [Security] Unauthenticated User Switching Documented with User Enumeration
- **File**: `backend/docs/mcp-usage-guide.md:59-66`
- **Issue**: Docs list all valid user IDs (`uttam`, `robert`, `luke`, `brainforge`) and show how to switch between them without auth
- **Detail**: Combined with network binding, this is a complete user-enumeration and privilege-escalation guide
- **Suggestion**: Remove enumerated user list from public docs. Add auth warning for HTTP deployments

### 3. [Security] Supabase Project ID Disclosed in Documentation
- **File**: `backend/docs/supabase-postgrest-fix.md:144`
- **Issue**: Live Supabase project identifier `umagqyjrvflkdvppkxnp` hardcoded in committed file
- **Detail**: Reduces attack surface — attacker only needs the key, not project ID. Enables targeted probing of auth endpoints
- **Suggestion**: Replace with `<your-project-ref>` placeholder

### 4. [Architecture] Port Mismatch in Documentation
- **File**: `backend/docs/mcp-usage-guide.md:195`
- **Issue**: Architecture diagram shows `port 3030` while actual default is `port 8000`
- **Detail**: Contradicts `config.py`, `test_config.py`, and `README.md` which all use 8000
- **Suggestion**: Change to `port 8000 (default)`

### 5. [Performance] Missing GIN Index on Tags Array Workaround
- **File**: `backend/docs/supabase-postgrest-fix.md:110-123` (documents live `storage.py` pattern)
- **Issue**: Structured fields packed into `tags` array as `"author:luke"` strings. Queries use `ANY(tags)` without GIN index
- **Detail**: Full table scan on every tag-based lookup. At vault scale (10K entries, 5 tags each), 50K values scanned per query
- **Suggestion**: Add `CREATE INDEX ... USING GIN(tags)` in a new migration

### 6. [Performance] Python-Side Aggregation in `get_growth_event_counts`
- **File**: `backend/tests/test_services.py:1080-1100` (exercises live service method)
- **Issue**: Fetches all growth events then counts in Python instead of `GROUP BY` in PostgreSQL
- **Detail**: O(n) network transfer + memory for a simple count that the database handles natively
- **Suggestion**: Replace with `SELECT event_type, COUNT(*) FROM growth_log ... GROUP BY event_type`

---

## Minor Findings

### Type Safety

7. **Missing return types on fixtures** — `test_services.py:2064, 2075, 2149` — `mock_supabase_config` and `storage` fixtures lack `-> BrainConfig` / `-> StorageService` annotations
8. **Missing parameter types on `_setup_base_mocks`** — `test_services.py:1509` — all params implicitly `Any`
9. **Unparameterized `dict` return** — `test_services.py:2093+` — `bulk_upsert_*` returns bare `dict` instead of typed `TypedDict`
10. **Test fixture alias loses type** — `conftest.py:45` — `mock_config = brain_config` strips return type annotation

### Architecture

11. **Fixture duplication** — `test_services.py:2063-2085, 2148-2160` — `TestStorageBulkOperations` and `TestStorageTimeout` duplicate `mock_config`/`storage` fixtures instead of using `conftest.py`
12. **Inline imports in tests** — `test_services.py` (multiple) — `HealthService`, `ContentTypeRegistry` etc. imported inside methods; no circular-import reason to use lazy imports in tests
13. **Temporal class name** — `test_services.py:1650` — `TestStorageServiceNewMethods` uses "New" which becomes meaningless over time. Rename to `TestStorageServiceProjectOperations`
14. **`TestDataInfraConfig` abbreviation** — `test_config.py:546` — "Infra" inconsistent with peer classes using full words
15. **`backend/docs/` undocumented** — New directory not listed in `sections/07_architecture.md` or README code structure
16. **Tests call mock directly** — `test_services.py:1809-1839` — `TestMemoryServiceNewMethods` tests call `mock_memory.get_by_id()` directly, testing mock infrastructure not production code
17. **Supabase workaround lacks follow-up tracking** — `supabase-postgrest-fix.md` has "Future Fix" section but no linked `requests/` plan to track the revert

### Security (Minor)

18. **Real-format OAuth token in test** — `test_config.py:664` — `sk-ant-oat01-test` matches Anthropic token prefix format, may trigger secret scanners

---

## Summary Assessment

**Overall**: Needs minor fixes

**Recommended action**: Fix the 3 security findings (P0-P1) before any public/shared deployment. The port mismatch is a quick documentation fix. Performance findings are worth tracking but not blocking.

### Priority Actions

| Priority | Action | Effort |
|----------|--------|--------|
| P0 | Change `mcp_host` default to `127.0.0.1` | Low |
| P1 | Redact Supabase project ID from docs | Low |
| P1 | Remove user enumeration from mcp-usage-guide | Low |
| P1 | Fix port 3030 → 8000 in mcp-usage-guide | Low |
| P1 | Add GIN index on `knowledge_repo.tags` | Low |
| P2 | Push `get_growth_event_counts` to database | Medium |
| P2 | Fix mock-only tests in `TestMemoryServiceNewMethods` | Low |
| P3 | Type annotations, naming, fixture cleanup | Low |
