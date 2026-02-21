# Execution Report: Multi-User Voice Isolation

---

### Meta Information

- **Plan file**: `requests/multi-user-voice-isolation-plan.md`
- **Files added**: None
- **Files modified**:
  - `backend/src/second_brain/config.py`
  - `backend/src/second_brain/services/abstract.py`
  - `backend/src/second_brain/services/memory.py`
  - `backend/src/second_brain/services/storage.py`
  - `backend/src/second_brain/services/graphiti_memory.py`
  - `backend/src/second_brain/agents/utils.py`
  - `backend/src/second_brain/agents/create.py`
  - `backend/src/second_brain/agents/review.py`
  - `backend/src/second_brain/agents/email_agent.py`
  - `backend/src/second_brain/agents/clarity.py`
  - `backend/src/second_brain/mcp_server.py`
  - `backend/tests/test_config.py`
  - `backend/tests/test_services.py`
  - `backend/tests/test_mcp_server.py`
  - `backend/tests/test_agents.py`
  - `backend/.env.example`

### Completed Tasks

- Task 1: BrainConfig `allowed_user_ids` field + validators — completed
- Task 2: MemoryServiceBase ABC `override_user_id` on search methods — completed
- Task 3: MemoryService `_effective_user_id()` + override wiring — completed
- Task 4: StorageService `override_user_id` on `get_memory_content` + `get_examples` — completed
- Task 5: GraphitiMemoryAdapter `override_user_id` signature sync — completed
- Task 6: `load_voice_context()` `voice_user_id` parameter — completed
- Task 7: Create agent tools `voice_user_id` + instructions update — completed
- Task 8: Review agent `voice_user_id` on `load_voice_reference` — completed
- Task 9: Email + Clarity agent `voice_user_id` on voice tools — completed
- Task 10: MCP tools `user_id` param on `create_content` + `review_content` — completed
- Task 11: Config tests (`TestAllowedUserIds`, 6 tests) — completed
- Task 12: Service tests (`TestMemoryServiceUserOverride`, 4 tests) — completed
- Task 13: MCP server tests (`TestMultiUserVoice`, 6 tests) — completed
- Task 14: Agent tests (`TestCreateAgentVoiceRouting`, 7 tests) — completed
- Task 15: `.env.example` update with `ALLOWED_USER_IDS` — completed

### Divergences from Plan

- **What**: `allowed_user_ids` config field type changed from `list[str]` to `str`
- **Planned**: `list[str]` field with `@field_validator(mode="before")` for comma parsing
- **Actual**: `str` field with `@property allowed_user_ids_list` returning parsed list
- **Reason**: pydantic-settings' `prepare_field_value()` JSON-decodes `list[str]` fields from env vars BEFORE field validators run. Comma-separated string like `"uttam,robert"` fails JSON parsing. Changed to `str` + property to match existing project pattern (`model_fallback_chain` / `fallback_chain_list`).

- **What**: MCP `_validate_user_id()` reads `config.allowed_user_ids_list` (property) not `config.allowed_user_ids` (list)
- **Planned**: Direct list access
- **Actual**: Property access (returns parsed list from comma-separated string)
- **Reason**: Consequence of the config type change above.

- **What**: `learn` MCP tool skipped (no `user_id` param added)
- **Planned**: Plan noted "evaluate whether learn truly needs this"
- **Actual**: Skipped — learn writes to shared pool, no voice dependency
- **Reason**: Learn extracts patterns from content and stores in shared knowledge. Voice isolation is irrelevant for pattern extraction.

- **What**: Existing test assertions updated for new override parameter
- **Planned**: Not explicitly mentioned in plan
- **Actual**: 3 existing tests (`test_create_load_voice_guide_calls_storage`, `test_create_load_content_examples_calls_storage`, `test_review_load_voice_reference_calls_storage`) updated to assert `override_user_id=None` kwarg
- **Reason**: Adding `override_user_id` to `get_memory_content()` and `get_examples()` changed the call signatures. Existing `assert_called_once_with()` assertions needed the new kwarg.

### Validation Results

```
Level 1 — Imports:
  from second_brain.config import BrainConfig  ✓
  from second_brain.schemas import *  ✓
  from second_brain.services.abstract import MemoryServiceBase, StubMemoryService  ✓

Level 2 — New feature tests (23 tests):
  TestAllowedUserIds: 6 passed
  TestMemoryServiceUserOverride: 4 passed
  TestMultiUserVoice: 6 passed
  TestCreateAgentVoiceRouting: 7 passed

Level 3 — Full test suite:
  1484 passed, 0 failed, 6561 warnings in 19.97s
```

### Tests Added

- `test_config.py::TestAllowedUserIds` — 6 tests (default values, comma parsing, auto-add brain_user_id, no duplicate, empty skip, custom list)
- `test_services.py::TestMemoryServiceUserOverride` — 4 tests (search override, default fallback, search_with_filters override, _effective_user_id helper)
- `test_mcp_server.py::TestMultiUserVoice` — 6 tests (create_content with user_id, invalid user_id, empty user_id backward compat, review_content invalid, _validate_user_id empty, _validate_user_id lowercase)
- `test_agents.py::TestCreateAgentVoiceRouting` — 7 tests (voice_user_id param on all 6 agent tools + instructions check)
- **Total**: 23 new tests, all passing

### Issues & Notes

- pydantic-settings `list[str]` env var parsing is a known footgun — `str` + property is the safer pattern for comma-separated config fields
- The `_validate_user_id()` function reads the module-level `_deps` global (not `_get_deps()`), so MCP tests that validate user_id must set `mod._deps` in addition to patching `_get_deps`
- Service tests converted from sync (`asyncio.get_event_loop().run_until_complete()`) to async — Python 3.14 deprecated `get_event_loop()` in non-async contexts

### Ready for Commit

- All changes complete: yes
- All validations pass: yes
- Ready for `/commit`: yes
