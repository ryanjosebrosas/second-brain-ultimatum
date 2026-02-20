# Execution Report: Recall Hardening 02 — Config Wiring + Observability

---

### Meta Information

- **Plan file**: `requests/recall-hardening-plan-02-config-observability.md`
- **Files added**: None
- **Files modified**:
  - `backend/src/second_brain/mcp_server.py`
  - `backend/src/second_brain/agents/utils.py`
  - `backend/tests/test_mcp_server.py`

### Completed Tasks

- Task 1: Wire `max_input_length` and `service_timeout_seconds` in `mcp_server.py` — **completed**
  - Changed `_validate_mcp_input` default `max_length` to `None` with 10000 fallback
  - Moved validation after `_get_deps()` in `quick_recall` and `recall_deep`
  - Wired `deps.config.max_input_length` to both tools
- Task 2: Wire `voyage_rerank_top_k` to `rerank_memories` callers — **completed**
  - Added config fallback inside `rerank_memories` itself: `top_k = getattr(deps.config, "voyage_rerank_top_k", None)` when `top_k is None`
  - This covers all 6 callers that don't pass explicit `top_k`
- Task 3: Add per-source latency logging to `parallel_search_gather` — **completed**
  - Added `time.perf_counter()` around `asyncio.gather`
  - Added per-source outcome tracking (`{name}={count}hits` or `{name}=FAIL`)
  - Upgraded failure logging from `logger.debug` to `logger.info`
  - Added summary log: `parallel_search_gather: {ms}ms total, sources=[...]`
- Task 4: Log complexity routing decision in `quick_recall` — **completed**
  - Added `logger.info("quick_recall complexity=%s query=%r", ...)` before routing
  - Added `logger.info("quick_recall routing to recall_deep...")` on complex upgrade
  - Added `logger.info("quick_recall returning %d results from sources=%s", ...)` at end
- Task 5: Add source tag to `format_memories` output — **completed**
  - Appends `[source]` tag to formatted lines when `source` key is present
  - Non-normalized memories without `source` key are unaffected

### Divergences from Plan

- **What**: Added config defaults to `_mock_deps()` in test file
- **Planned**: Plan didn't mention test fixture updates
- **Actual**: Added `max_input_length`, `complex_query_word_threshold`, `retrieval_oversample_factor`, `voyage_rerank_top_k` to `_mock_deps()` in `tests/test_mcp_server.py`
- **Reason**: Moving `_validate_mcp_input` after `_get_deps()` in `quick_recall` caused the mock config to be accessed for `max_input_length`, which returned `MagicMock` instead of `int`. The mock needed explicit values for all config fields now accessed in the code path.

- **What**: `service_timeout_seconds` not additionally wired in `quick_recall`
- **Planned**: Plan suggested wiring `service_timeout_seconds` to `parallel_search_gather` callers in `quick_recall`
- **Actual**: `quick_recall` uses inline `asyncio.gather()`, not `parallel_search_gather()`. The outer `asyncio.timeout(api_timeout_seconds)` already protects the entire block. `parallel_multi_table_search` and `deep_recall_search` already wire `service_timeout_seconds` to their `parallel_search_gather` calls.
- **Reason**: Unnecessary to add per-source timeout to inline gather when it's already wrapped by the tool-level timeout.

### Validation Results

```
utils ok
mcp ok
max_input_length wired
latency tracking present
source tag present
1315 passed, 3 failed (pre-existing: claude-agent-sdk not installed)
```

### Tests Added

- No new test files created. Updated `_mock_deps()` fixture in `tests/test_mcp_server.py` to include config defaults needed by the new config wiring.

### Issues & Notes

- 3 pre-existing test failures in `test_models_sdk.py` due to `claude-agent-sdk` not being installed (optional dependency). Not related to this sub-plan.
- All 1315 previously-passing tests continue to pass.

### Ready for Commit

- All changes complete: yes
- All validations pass: yes
- Ready for `/commit`: yes
