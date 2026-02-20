# Code Review: Recall Hardening

- **Mode**: Parallel (4 specialized agents)
- **Commits**: `4682c13`, `a7b7762` (recall hardening — config wiring, latency logging, crash protection, tests)
- **Files Modified**: 8 | **Lines Changed**: +888 / -124
- **Total Findings**: 20 (Critical: 0, Major: 8, Minor: 12)

---

## Findings by Severity

### Major (8)

```yaml
severity: major
category: Performance
file: backend/src/second_brain/mcp_server.py:271 + backend/src/second_brain/agents/utils.py:404
issue: Embedding computed twice for same query on complex-query routing
detail: >
  quick_recall computes an embedding (~200-500ms Voyage AI call), then if
  complexity="complex", routes to recall_deep which computes the same
  embedding again. One full API call is wasted on every complex query.
suggestion: >
  Move classify_query_complexity() before the embedding block in quick_recall.
  If complexity is "complex", skip embedding and call recall_deep directly
  (it computes its own). Saves ~200-500ms + one API call per complex query.
```

```yaml
severity: major
category: Performance
file: backend/src/second_brain/agents/recall.py:149
issue: Embedding awaited serially before parallel search gather
detail: >
  In search_patterns, embed_query is awaited sequentially before building
  the parallel coroutine map. The mem0 search could run concurrently with
  embedding but waits for it to finish first. Adds full embedding latency
  (~200-500ms) to the serial portion.
suggestion: >
  Run embed_query and mem0.search_with_filters in a first asyncio.gather,
  then use the embedding result for hybrid_search. Same pattern exists in
  search_semantic_memory.
```

```yaml
severity: major
category: Security
file: backend/src/second_brain/agents/utils.py:895
issue: Raw exception messages stored in pipeline results and surfaced to callers
detail: >
  Pipeline step exceptions are stored as {"error": str(e)} — internal details
  (connection strings, table names, API key fragments) could leak through
  the pipeline output to tool consumers.
suggestion: >
  Replace {"error": str(e)} with {"error": f"Step failed: {type(e).__name__}"}
  to match the established tool_error() pattern.
```

```yaml
severity: major
category: Security
file: backend/src/second_brain/mcp_server.py:245
issue: User query content logged at INFO level
detail: >
  Full query (truncated to 80 chars) logged at INFO with %r. If queries contain
  sensitive data, this persists in log aggregators. Privacy/data retention risk.
suggestion: >
  Downgrade to DEBUG level. Log only query length, not content:
  logger.debug("quick_recall complexity=%s query_len=%d", complexity, len(query))
```

```yaml
severity: major
category: Security
file: backend/src/second_brain/mcp_server.py:79
issue: Health endpoint exposes raw initialization error to unauthenticated callers
detail: >
  /health returns _deps_error = str(e) in the JSON response. In Docker
  deployments (mcp_host: 0.0.0.0), this is network-accessible without auth.
  Failed init errors may contain connection strings or API key fragments.
suggestion: >
  Return generic message in response; keep full error in server logs only:
  {"status": "unhealthy", "error": "Initialization failed. Check server logs."}
```

```yaml
severity: major
category: Architecture
file: backend/src/second_brain/agents/utils.py:578-622
issue: Pipeline orchestration logic (run_review_learn_pipeline) in utils.py
detail: >
  utils.py imports and invokes review_agent and learn_agent directly. This is
  orchestration, not utility code. Creates latent circular import risk since
  learn.py and review.py both import from utils.py.
suggestion: >
  Move run_review_learn_pipeline() to mcp_server.py or a new agents/pipelines.py.
  Keep utils.py limited to pure functions and helpers.
```

```yaml
severity: major
category: Architecture
file: backend/src/second_brain/agents/utils.py:735-796
issue: Agent registry (get_agent_registry) placed in utils.py instead of orchestration layer
detail: >
  utils.py imports all agent modules and builds a routing registry. This is
  routing/orchestration that belongs in chief_of_staff.py or a dedicated registry.
  Every new agent requires editing utils.py — DRY violation in maintenance.
suggestion: >
  Move get_agent_registry() to agents/registry.py or agents/chief_of_staff.py.
```

```yaml
severity: major
category: Type Safety
file: backend/src/second_brain/agents/utils.py:243
issue: Coroutine parameter typed as `object` instead of Awaitable
detail: >
  parallel_search_gather's `searches` param uses list[tuple[str, object]]
  but the second element is always a coroutine passed to asyncio.wait_for.
  `object` provides no type safety. Same issue at line 395 in deep_recall_search.
suggestion: >
  Replace `object` with `Awaitable[Any]` from collections.abc.
```

---

### Minor (12)

```yaml
severity: minor
category: Type Safety
file: backend/src/second_brain/agents/utils.py:372
issue: Bare `-> dict` return type on deep_recall_search
detail: Known keys (memories, relations, search_sources, query) — use TypedDict or dict[str, Any].
suggestion: Define DeepRecallResult TypedDict or at minimum -> dict[str, Any].
```

```yaml
severity: minor
category: Type Safety
file: backend/src/second_brain/agents/utils.py:735
issue: Bare `-> dict` return type on get_agent_registry
suggestion: Annotate as -> dict[str, tuple[Agent[BrainDeps, Any], str]].
```

```yaml
severity: minor
category: Type Safety
file: backend/src/second_brain/agents/utils.py:268
issue: `if per_source_timeout:` excludes 0.0 — should be `is not None`
suggestion: Change to `if per_source_timeout is not None:`.
```

```yaml
severity: minor
category: Type Safety
file: backend/src/second_brain/mcp_server.py:152
issue: _get_model accesses module-level _deps without type narrowing
suggestion: Use `deps = _get_deps()` return value instead of module-level _deps.
```

```yaml
severity: minor
category: Type Safety
file: backend/src/second_brain/agents/utils.py:34-35
issue: format_memories score may be non-numeric — :.2f would raise TypeError
suggestion: Add defensive cast: score = float(score or 0).
```

```yaml
severity: minor
category: Security
file: backend/src/second_brain/agents/utils.py:151
issue: MD5 used for content deduplication — cryptographically broken
suggestion: Use hashlib.sha256(content.encode(), usedforsecurity=False).hexdigest().
```

```yaml
severity: minor
category: Security
file: backend/src/second_brain/mcp_server.py:217
issue: Unbounded limit parameter on search endpoints — no upper bound before oversample multiply
suggestion: Cap limit at reasonable max: limit = max(1, min(limit, 100)).
```

```yaml
severity: minor
category: Architecture
file: backend/src/second_brain/agents/utils.py:142,263,635
issue: Standard library imports (hashlib, time, datetime) inline in function bodies
detail: Lazy-import pattern is for agent circular imports in mcp_server.py, not stdlib.
suggestion: Move hashlib, time, datetime imports to module-level.
```

```yaml
severity: minor
category: Architecture
file: backend/tests/test_mcp_server.py:16-27
issue: _mock_deps() duplicates conftest.py mock_deps fixture — DRY violation in tests
detail: New config fields must be maintained in two places. Missing memory_search_limit.
suggestion: Consolidate into conftest fixture or document why separate.
```

```yaml
severity: minor
category: Performance
file: backend/src/second_brain/agents/utils.py:114
issue: query.lower() recomputed per synonym iteration in expand_query inner loop
suggestion: Hoist query_lower = query.lower() before the outer loop.
```

```yaml
severity: minor
category: Performance
file: backend/src/second_brain/agents/utils.py:652
issue: datetime.now(timezone.utc) called per row in format_pattern_registry loop
suggestion: Compute now once before loop; also merge double-iteration into single pass.
```

```yaml
severity: minor
category: Architecture
file: backend/src/second_brain/mcp_server.py:250-258
issue: utils utility functions lazily imported inside asyncio.timeout block
detail: Lazy import pattern is for agent modules, not pure utility functions.
suggestion: Move agents.utils imports to function entry or module level.
```

---

## Summary Assessment

- **Overall**: **Needs minor fixes** — no critical blockers, but 8 Major findings across all categories
- **Security**: 3 Major (info leakage in pipeline errors, query logging, health endpoint) — should fix before any network-accessible deployment
- **Performance**: 2 Major (double embedding, serial embedding bottleneck) — combined ~400-1000ms wasted per complex query
- **Architecture**: 2 Major (utils.py accumulating orchestration responsibilities) — refactor opportunity, not blocking
- **Type Safety**: 1 Major (object vs Awaitable) — correctness risk for future callers

### Priority Actions
1. **P0**: Move `classify_query_complexity()` before embedding in `quick_recall` to avoid double embedding (performance)
2. **P1**: Sanitize pipeline error messages, health endpoint error, and query logging level (security)
3. **P1**: Replace `object` with `Awaitable[Any]` in parallel_search_gather (type safety)
4. **P2**: Refactor `get_agent_registry()` and `run_review_learn_pipeline()` out of utils.py (architecture)
5. **P2**: Move inline stdlib imports to module level (architecture/performance)
