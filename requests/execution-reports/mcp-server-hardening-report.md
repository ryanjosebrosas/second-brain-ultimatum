# Execution Report: MCP Server Hardening

---

### Meta Information

- **Plan file**: `requests/mcp-server-hardening-plan.md`
- **Files added**: None
- **Files modified**:
  - `backend/pyproject.toml`
  - `backend/src/second_brain/mcp_server.py`
  - `backend/src/second_brain/service_mcp.py`
  - `backend/tests/conftest.py`

### Completed Tasks

- Task 1: Update fastmcp version pin in pyproject.toml — completed
- Task 2: Harden mcp_server.py __main__ block — completed
- Task 3: Add CancelledError catch to service_mcp.py __main__ — completed
- Task 4: Fix test_review_content_tool_exists internal API usage — skipped (test passes as-is with fastmcp 2.x; `server._tool_manager._tools` API preserved in 2.14.5)
- Task 5: Validate full test suite (895 tests, 0 failures) — completed
- Task 6: Validate MCP server startup — completed

### Divergences from Plan

- **What**: Added FunctionTool.__call__ compatibility patch in conftest.py
- **Planned**: Plan only anticipated `test_review_content_tool_exists` might need fixing, with a hasattr fallback chain
- **Actual**: fastmcp 2.x wraps ALL `@server.tool()` functions in FunctionTool objects that are not directly callable. This broke 96 tests (not just 1). Added a module-level patch in `conftest.py` that sets `FunctionTool.__call__` to delegate to `self.fn`, restoring direct callability for all tests.
- **Reason**: The plan underestimated the scope of the fastmcp 2.x API change. In 0.4.1, `@server.tool()` kept functions callable. In 2.x, they become FunctionTool Pydantic model instances. The conftest patch is the minimal, centralized fix that preserves all 895 existing tests unchanged.

- **What**: `pip install -e ".[dev]"` hit voyageai Python 3.14 conflict
- **Planned**: Plan expected clean pip install
- **Actual**: Installed fastmcp directly (`pip install "fastmcp>=2.14.0,<3.0.0"`), then reinstalled editable with `--no-deps`. The voyageai conflict is pre-existing (not caused by this change) — voyageai 0.3.x doesn't support Python 3.14.
- **Reason**: Pre-existing dependency issue unrelated to this feature. voyageai was already installed from a previous pip install before the Python version constraint was added.

### Validation Results

```
Syntax validation:
  mcp_server.py: OK
  service_mcp.py: OK

Version check:
  fastmcp 2.14.5
  mcp 1.26.0
  beartype 0.22.9 (>= 0.22.4, Python 3.14 compatible)

Stdout pollution check:
  OK: No stdout pollution from imports

__main__ block structure:
  OK: __main__ block has all required elements (basicConfig, CancelledError, stderr redirect)

MCP server startup:
  OK: MCP server responded to initialize

Full test suite:
  895 passed, 3870 warnings in 5.19s
```

### Tests Added

No new test files created. The conftest.py FunctionTool compatibility patch is a test infrastructure change, not a new test. Existing 895 tests serve as the regression suite.

### Issues & Notes

- **voyageai Python 3.14 incompatibility**: voyageai 0.3.x requires Python <3.14. This is a pre-existing issue unrelated to the fastmcp upgrade. Currently works because voyageai was installed before the version constraint was added. May need attention in a future PIV loop.
- **OpenTelemetry deprecation warnings**: fastmcp 2.x pulls in opentelemetry, which produces deprecation warnings about `Logger`, `LoggerProvider`, and `ProxyLoggerProvider`. These are cosmetic (3870 warnings in test output) and don't affect functionality.
- **FunctionTool.__call__ patch scope**: The conftest patch makes FunctionTool instances callable by delegating to `self.fn`. This is safe for testing but not for production code. The patch only exists in `tests/conftest.py` and doesn't affect the runtime MCP server.

### Ready for Commit

- All changes complete: yes
- All validations pass: yes
- Ready for `/commit`: yes
