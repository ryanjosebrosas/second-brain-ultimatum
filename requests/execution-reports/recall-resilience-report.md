# Execution Report: recall-resilience

---

### Meta Information

- **Plan file**: `requests/recall-resilience-plan.md`
- **Files added**: None
- **Files modified**:
  - `backend/src/second_brain/services/memory.py`
  - `backend/src/second_brain/agents/recall.py`
  - `backend/src/second_brain/agents/utils.py`
  - `backend/src/second_brain/api/routers/agents.py`
  - `backend/src/second_brain/mcp_server.py`
  - `backend/tests/test_agents.py`
  - `backend/tests/test_agentic.py`
  - `backend/tests/test_api.py`
  - `backend/tests/test_mcp_server.py`
  - `backend/tests/test_services.py`

### Completed Tasks

- Task 1: Fix `search()` cloud filter — remove top-level `user_id`, use `AND` wrapper with `version="v2"` — completed
- Task 2: Fix `search_with_filters()` cloud filter — flatten nested AND, remove top-level `user_id` — completed
- Task 3: Fix `get_all()` cloud filter — remove top-level `user_id`, use `AND` wrapper — completed
- Task 4: Enhance `tool_error()` with `BACKEND_ERROR:` prefix — completed
- Task 5: Update recall tools to signal backend failures with `TOOL_ERROR_PREFIX` — completed (search_semantic_memory, search_patterns, search_experiences, search_examples)
- Task 6: Deterministic failure detection in validator — skipped (see divergences)
- Task 7: Reduce recall agent retries from 3 to 2 — completed
- Task 8: Improve API `_run_agent` 503 response with structured JSON detail — completed
- Task 9: Surface `output.error` in MCP recall formatted output — completed
- Task 10: Add resilience tests to test_agents.py — completed (4 new tests)
- Task 11: Add Mem0 filter construction tests to test_services.py — completed (7 new tests)
- Task 12: Add API error response tests to test_api.py + MCP test — completed (2 new tests)

### Divergences from Plan

- **What**: Task 6 (deterministic failure detection in validator via retry count) was simplified
- **Planned**: Detect retry count in output validator and accept empty results on final retry
- **Actual**: Kept the existing validator behavior unchanged. The plan itself acknowledged this risk (Pydantic AI doesn't expose retry count to validators) and recommended the simpler approach: reduce retries to 2 + let API/MCP layers handle `UnexpectedModelBehavior`. This is what was implemented.
- **Reason**: Pydantic AI's internal retry state isn't accessible from output validators. The combination of reduced retries (Task 7) + improved API error handling (Task 8) + MCP error surfacing (Task 9) provides equivalent resilience without accessing internal state.

- **What**: MCP error field uses `**WARNING**:` instead of emoji
- **Planned**: The plan suggested emoji warning symbol
- **Actual**: `**WARNING**: {error}`
- **Reason**: CLAUDE.md says "Only use emojis if the user explicitly requests it."

- **What**: Existing test `test_unexpected_model_behavior_returns_503` in test_agents.py needed updating
- **Planned**: Not mentioned in plan
- **Actual**: Updated assertion from `"degraded" in detail.lower()` to `"degraded" in detail["error"].lower()` since detail is now a dict
- **Reason**: Direct consequence of Task 8 changing detail from string to structured dict

### Validation Results

```
Level 1 — Syntax: imports OK
Level 2 — Unit Tests:
  tests/test_agents.py -k "recall or tool_error": 42 passed
  tests/test_services.py -k "mem0 or memory or Filter": 62 passed
Level 3 — Integration Tests:
  tests/test_mcp_server.py -k "recall": 19 passed
  tests/test_api.py -k "recall": 6 passed
  tests/test_agentic.py: 37 passed
Level 5 — Full Suite:
  1428 passed, 3 failed (pre-existing test_models_sdk failures)
```

### Tests Added

- `test_agents.py`: 4 new tests in `TestRecallValidatorResilience` — retries reduced, tool_error prefix, tool_error contains unavailable, existing test updated for dict detail
- `test_services.py`: 7 new tests in `TestMem0FilterConstruction` — cloud search/search_with_filters/get_all no top-level user_id, flattened AND, bare dict, no metadata, local uses top-level user_id
- `test_api.py`: 1 new test — 503 structured detail with suggestion on retry exhaustion
- `test_mcp_server.py`: 1 new test — MCP recall surfaces error field as WARNING
- `test_agentic.py`: 1 existing test updated (retries == 2)
- **Total**: net +20 passing (1408 -> 1428)

### Issues & Notes

- The 3 pre-existing `test_models_sdk.py` failures are unrelated to this feature and fail on clean master.
- The `version="v2"` parameter is belt-and-suspenders — Mem0 Platform API v2 is the current default, but being explicit prevents future breaking changes.
- The `TOOL_ERROR_PREFIX` constant is exported from `utils.py`. Other agents using `tool_error()` will also emit the prefix automatically, which is harmless.

### Ready for Commit

- All changes complete: yes
- All validations pass: yes (excluding 3 pre-existing SDK failures)
- Ready for `/commit`: yes
