# Execution Report: Security Hardening (Sub-Plan 01)

---

### Meta Information

- **Plan file**: `requests/codebase-review-fixes-plan-01-security.md`
- **Files added**: None
- **Files modified**:
  - `backend/src/second_brain/config.py`
  - `backend/src/second_brain/api/deps.py`
  - `backend/src/second_brain/api/main.py`
  - `backend/src/second_brain/api/schemas.py`
  - `backend/src/second_brain/api/routers/projects.py`
  - `backend/src/second_brain/api/routers/health.py`
  - `backend/src/second_brain/mcp_server.py`
  - `backend/src/second_brain/service_mcp.py`
  - `backend/.env.example`

### Completed Tasks

- Task 1: Add `brain_api_key` field to BrainConfig + warning validator -- completed
- Task 2: Add `verify_api_key` dependency to api/deps.py -- completed
- Task 3: Update api/main.py (fix double BrainConfig, add auth deps, fix __main__ host/reload) -- completed
- Task 4: Update mcp_server.py transport (MCP_HOST default, consolidate MAX_INPUT_LENGTH) -- completed
- Task 5: Update service_mcp.py (remove hardcoded MAX_INPUT_LENGTH) -- completed
- Task 6: Update schemas (Literal table), projects.py (stage validation), health.py (days bounds) -- completed
- Task 7: Update mcp_server.py (error sanitization + URL validation) -- completed
- Task 8: Update .env.example (replace PII, add BRAIN_API_KEY) -- completed

### Divergences from Plan

- **What**: `_validate_url_scheme` empty-check error message
- **Planned**: `"Missing or empty {label}."`
- **Actual**: `"{label} cannot be empty"` (matching existing test expectation)
- **Reason**: Existing test `test_learn_image_empty_url_returns_error` asserts `"cannot be empty"` in result. Changed error wording to be consistent with prior behavior and passing tests.

### Validation Results

```bash
# Syntax & Structure
$ python -c "from second_brain.config import BrainConfig; ..."
api_key field exists: True

$ python -c "from second_brain.api.deps import verify_api_key; ..."
auth dep OK

$ python -c "from second_brain.api.main import create_app; ..."
50 routes

$ python -c "from second_brain.api.schemas import VectorSearchRequest; ..."
Literal table OK

$ python -c "import second_brain.mcp_server; ..."
mcp_server import OK

$ python -c "import second_brain.service_mcp; ..."
service_mcp import OK

# Content Verification
$ grep -c "ryan" .env.example        # 0 (no PII)
$ grep -c "Utopia" .env.example      # 0 (no PII)
$ grep -c 'return f"Error.*{e}"' src/second_brain/mcp_server.py  # 0 (all sanitized)

# Test Suite
$ python -m pytest -x --tb=short
1272 passed, 5679 warnings in 18.79s
```

### Tests Added

- No new test files specified in plan. Existing tests all pass (1272 tests, up from 1264).

### Issues & Notes

- The `Query` import added to `health.py` complements the existing `Depends` import from FastAPI.
- The health router is intentionally exempt from API key auth to support monitoring/health checks without credentials.
- A linter appeared to run on save but did not modify the actual content of changed files.

### Ready for Commit

- All changes complete: yes
- All validations pass: yes
- Ready for `/commit`: yes
