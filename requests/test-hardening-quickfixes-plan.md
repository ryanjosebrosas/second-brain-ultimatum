# Feature: Test Hardening + Quick Fixes

## Feature Description

Address code quality quick fixes and fill test branch coverage gaps across CLI, MCP server, and deps modules. The codebase has 443 tests passing but several output-formatting branches, edge-case paths, and CLI/MCP parity gaps are untested. This plan also fixes 3 micro code issues (missing loggers, missing type hint) and adds 1 missing MCP tool (`graph_health`) for CLI/MCP parity.

## User Story

As a developer maintaining the Second Brain, I want comprehensive branch coverage on both user-facing interfaces (CLI + MCP) and consistent code quality patterns, so that refactors don't silently break output formatting or degrade the user experience.

## Problem Statement

1. **Inconsistent logging setup**: `cli.py` and `config.py` use inline `logging.basicConfig()` / `logging.getLogger(__name__)` inside functions instead of module-level `logger` constants — inconsistent with the other 16 modules.
2. **Missing type hint**: `mcp_server.py:51` `_get_model()` has no return type annotation.
3. **CLI/MCP parity gap**: CLI has `graph health` command but MCP server has no equivalent `graph_health` tool.
4. **Branch coverage gaps**: CLI tests (~30 tests) and MCP tests (~35 tests) cover happy paths but skip conditional branches for: graphiti status, stale patterns, review scores, CLI option flags, and output formatting with populated data.
5. **deps.py edge cases**: `create_deps()` with `graphiti_enabled=True` (independent flag path) is untested. Default config creation path (no arg) is untested.

## Solution Statement

- Decision 1: Fix code quality issues inline (loggers, type hint) — because they're 1-2 line changes that reduce inconsistency
- Decision 2: Add `graph_health` MCP tool mirroring CLI's `graph health` — because it's the only command missing from MCP
- Decision 3: Add targeted branch-coverage tests, not duplicate existing tests — because 443 tests already cover happy paths
- Decision 4: Keep tests in existing files (test_cli.py, test_mcp_server.py, test_config.py) — because the project has no separate test_deps.py and deps tests already live in test_config.py
- Decision 5: Follow existing test patterns exactly (same mock setup, same assertion style) — because consistency > novelty

## Feature Metadata

- **Feature Type**: Enhancement (code quality + test coverage)
- **Estimated Complexity**: Low-Medium
- **Primary Systems Affected**: cli.py, config.py, mcp_server.py, deps.py, test_cli.py, test_mcp_server.py, test_config.py
- **Dependencies**: None (all internal)

---

## CONTEXT REFERENCES

### Relevant Codebase Files

> IMPORTANT: The execution agent MUST read these files before implementing!

- `src/second_brain/cli.py` (lines 1-578) — Why: Quick fix targets (logger line 4, subscription flag line 36-38) + test targets (health branch line 343, growth branches lines 378-393)
- `src/second_brain/config.py` (lines 1-184) — Why: Quick fix target (inline logger on line 177-178, no module-level logging import)
- `src/second_brain/mcp_server.py` (lines 1-578) — Why: Quick fix targets (type hint line 51, graph_health tool after line 411) + test targets
- `src/second_brain/deps.py` (lines 1-71) — Why: Test target for graphiti_enabled path (line 47) and default config path (line 42-43)
- `src/second_brain/models.py` (lines 1-66) — Why: Reference for `get_model()` return type (returns `Model` from pydantic_ai)
- `src/second_brain/services/health.py` (lines 1-165) — Why: HealthService.compute() used by graph_health; HealthMetrics dataclass for test mocking
- `src/second_brain/schemas.py` (lines 1-50) — Why: RecallResult, MemoryMatch, Relation, AskResult used in CLI output formatting tests
- `tests/conftest.py` (lines 1-256) — Why: All shared fixtures (brain_config, mock_memory, mock_storage, mock_graphiti, mock_deps, mock_create_deps) needed for new tests
- `tests/test_cli.py` (lines 1-466) — Why: Existing CLI test patterns + mock_create_deps fixture + all test classes to extend
- `tests/test_mcp_server.py` (lines 1-700) — Why: Existing MCP test patterns + TestMCPGraphSearch, TestGrowthReport classes to extend
- `tests/test_config.py` (lines 296-395) — Why: Existing TestCreateDeps class + TestBrainDepsRegistry to extend

### New Files to Create

None — all changes go into existing files.

### Related Memories (from memory.md)

- Memory: "pydantic_ai tool introspection: Use `_function_toolset.tools` not `_function_tools`" — Relevance: Test patterns for agent tool verification use correct attribute path
- Memory: "BrainConfig .env bleed: `monkeypatch.delenv()` alone isn't enough — must pass `_env_file=None` to BrainConfig() in tests" — Relevance: Critical for config/deps tests; every BrainConfig in tests must use `_env_file=None`
- Memory: "Lazy imports in CLI/deps/MCP require patching at source module, not import site (e.g. `second_brain.agents.recall.recall_agent` not `second_brain.cli.recall_agent`)" — Relevance: Mock patching must target the module where the agent is defined
- Memory: "FastMCP `@server.tool()` wraps functions in FunctionTool objects — use `.fn` attribute for direct testing" — Relevance: All MCP tool tests use `tool_name.fn()` pattern
- Memory: "graphiti_core not installed — use `patch.dict(sys.modules)` to mock entire module tree" — Relevance: deps graphiti_enabled test path when graphiti_core not installed

### Relevant Documentation

- No external docs needed — all patterns are internal to this codebase.

### Patterns to Follow

**Pattern 1: CLI Agent Command Test** (from `tests/test_cli.py:56-77`):
```python
class TestRecallCommand:
    @patch("second_brain.cli.get_model")
    @patch("second_brain.agents.recall.recall_agent")
    def test_recall_success(self, mock_agent, mock_model, runner, mock_create_deps):
        mock_model.return_value = MagicMock()
        mock_output = MagicMock()
        mock_output.query = "test"
        mock_output.matches = []
        mock_output.patterns = []
        mock_output.relations = []
        mock_output.summary = "Test summary"
        mock_agent.run = AsyncMock(return_value=MagicMock(output=mock_output))
        result = runner.invoke(cli, ["recall", "test query"])
        assert result.exit_code == 0
        assert "Recall" in result.output
```
- Why this pattern: CLI commands are tested via Click's CliRunner, patching agents at source module
- Common gotchas: Agent must be patched at `second_brain.agents.X.agent_name`, not at `second_brain.cli.agent_name`. The `mock_create_deps` fixture patches `second_brain.cli.create_deps` and provides a pre-configured MagicMock.

**Pattern 2: CLI HealthService Command Test** (from `tests/test_cli.py:246-267`):
```python
class TestHealthCommand:
    @patch("second_brain.services.health.HealthService")
    def test_health_success(self, mock_hs, runner, mock_create_deps):
        mock_metrics = MagicMock()
        mock_metrics.memory_count = 42
        mock_metrics.total_patterns = 5
        mock_metrics.high_confidence = 2
        mock_metrics.medium_confidence = 2
        mock_metrics.low_confidence = 1
        mock_metrics.experience_count = 3
        mock_metrics.graph_provider = "none"
        mock_metrics.latest_update = "2026-02-15"
        mock_metrics.topics = {"content": 3}
        mock_metrics.status = "BUILDING"
        mock_hs.return_value.compute = AsyncMock(return_value=mock_metrics)
        result = runner.invoke(cli, ["health"])
        assert result.exit_code == 0
        assert "Memories: 42" in result.output
```
- Why this pattern: HealthService is patched at service module level; metrics mock must include ALL fields the command accesses
- Common gotchas: `graphiti_status` field controls the "Graphiti:" output line. Must set to non-"disabled" to test that branch. MagicMock auto-creates attrs but comparison `!= "disabled"` on MagicMock object is truthy — always set explicitly.

**Pattern 3: MCP Tool Test** (from `tests/test_mcp_server.py:19-42`):
```python
@patch("second_brain.mcp_server._get_model")
@patch("second_brain.mcp_server._get_deps")
@patch("second_brain.mcp_server.recall_agent")
async def test_recall_tool(self, mock_agent, mock_deps_fn, mock_model_fn):
    from second_brain.mcp_server import recall
    mock_result = MagicMock()
    mock_result.output = RecallResult(
        query="content patterns",
        matches=[MemoryMatch(content="Use exact user words", source="content-patterns.md", relevance="HIGH")],
        patterns=["Short > Structured"],
        summary="Found content creation patterns.",
    )
    mock_agent.run = AsyncMock(return_value=mock_result)
    mock_deps_fn.return_value = MagicMock()
    mock_model_fn.return_value = MagicMock()
    result = await recall.fn(query="content patterns")
    assert "content patterns" in result
    assert "Use exact user words" in result
```
- Why this pattern: MCP tools accessed via `.fn` attribute, deps/model mocked via module-level `_get_deps`/`_get_model` functions
- Common gotchas: Must import the tool function INSIDE the test method (after patches applied). Tool functions are FastMCP FunctionTool wrappers — call `.fn()` not the tool directly.

**Pattern 4: MCP Graph Search Test** (from `tests/test_mcp_server.py:457-493`):
```python
class TestMCPGraphSearch:
    @patch("second_brain.mcp_server._get_deps")
    async def test_graph_search_not_enabled(self, mock_get_deps):
        mock_deps = MagicMock()
        mock_deps.graphiti_service = None
        mock_get_deps.return_value = mock_deps
        from second_brain.mcp_server import graph_search
        result = await graph_search.fn(query="test")
        assert "not enabled" in result.lower()
```
- Why this pattern: Graph tools only mock `_get_deps` (no agent or model needed). Graphiti availability is controlled by setting `deps.graphiti_service` to None or a mock.
- Common gotchas: The `.fn` import must happen inside the test method.

**Pattern 5: MCP Growth Report with HealthMetrics Dataclass** (from `tests/test_mcp_server.py:543-574`):
```python
class TestGrowthReport:
    @patch("second_brain.mcp_server._get_deps")
    @patch("second_brain.services.health.HealthService")
    async def test_growth_report(self, mock_hs_cls, mock_deps_fn):
        from second_brain.mcp_server import growth_report
        mock_metrics = HealthMetrics(
            memory_count=50, total_patterns=10, high_confidence=3,
            medium_confidence=5, low_confidence=2, experience_count=8,
            graph_provider="none", latest_update="2026-02-15", status="GROWING",
            growth_events_total=15, patterns_created_period=5,
            patterns_reinforced_period=8, confidence_upgrades_period=2,
            reviews_completed_period=0, stale_patterns=[], topics={"Content": 5},
        )
        mock_hs_cls.return_value.compute_growth = AsyncMock(return_value=mock_metrics)
        mock_deps_fn.return_value = MagicMock()
        result = await growth_report.fn(days=30)
        assert "Growth Report" in result
```
- Why this pattern: Uses actual HealthMetrics dataclass (not MagicMock) for type safety. All required fields must be provided. Optional fields use dataclass defaults.
- Common gotchas: HealthMetrics has 8 required positional fields. If you miss one, you get a TypeError. Always copy the full constructor from an existing test.

**Pattern 6: Deps Creation Test** (from `tests/test_config.py:297-313`):
```python
class TestCreateDeps:
    @patch("second_brain.services.storage.StorageService")
    @patch("second_brain.services.memory.MemoryService")
    def test_create_deps_with_config(self, mock_mem, mock_storage, tmp_path):
        config = BrainConfig(
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
            brain_data_path=tmp_path,
            _env_file=None,
        )
        from second_brain.deps import create_deps
        deps = create_deps(config=config)
        assert deps.config is config
        assert deps.graphiti_service is None
        mock_mem.assert_called_once_with(config)
        mock_storage.assert_called_once_with(config)
```
- Why this pattern: Services are patched at their SOURCE modules (`second_brain.services.storage.StorageService`), not at the deps module. Config uses `_env_file=None` to prevent `.env` bleed.
- Common gotchas: `_env_file=None` is mandatory. Without it, BrainConfig reads the real `.env` file and tests become environment-dependent.

---

## IMPLEMENTATION PLAN

### Phase 1: Quick Fixes (Code Quality)

Fix 4 micro issues that bring consistency across the codebase:
1. Add module-level `logger` to `cli.py` (consistency with 16 other modules)
2. Add module-level `logger` to `config.py` (replace inline logging.getLogger in validator)
3. Add return type to `_get_model()` in `mcp_server.py` (matches `_get_deps() -> BrainDeps` pattern)
4. Add `graph_health` MCP tool for CLI/MCP parity (mirrors cli.py:523-538)

### Phase 2: CLI Branch Coverage

Add ~10 tests for untested conditional branches in CLI commands:
- Health command: graphiti-enabled branch (cli.py:343-344), no-topics branch
- Growth command: reviews branch (cli.py:378-382), stale patterns (cli.py:384-387), topics (cli.py:389-392), custom --days
- Create command: --mode override (cli.py:194)
- Review command: --type flag (cli.py:237)
- Recall/Learn: populated output formatting (matches, patterns, relations, anti_patterns)
- CLI --subscription flag: env var setting behavior

### Phase 3: MCP Branch Coverage

Add ~5 tests for untested conditional branches in MCP tools:
- New graph_health tool: not-enabled, healthy, error cases
- Growth report: stale patterns, topics output
- Create content: default mode (mode=None)

### Phase 4: Deps Edge Cases

Add ~3 tests for untested paths in deps.py:
- create_deps with graphiti_enabled=True (independent flag, not graph_provider)
- create_deps with graphiti_enabled=True + ImportError (graceful degradation)
- create_deps with no config argument (default BrainConfig from env)

---

## STEP-BY-STEP TASKS

### Task 1: UPDATE `src/second_brain/cli.py` — Add module-level logger

- **IMPLEMENT**: Add `logger = logging.getLogger(__name__)` after the imports block. The file already imports `logging` on line 4. Insert the logger constant after the last import line (after `from second_brain.models import get_model` on line 14), before the `_validate_input` function. Exact insertion:
  ```python
  from second_brain.models import get_model

  logger = logging.getLogger(__name__)
  ```
  Do NOT touch the `logging.basicConfig(level=level, ...)` on line 35 — that configures root logger for CLI output and must remain.
- **PATTERN**: `deps.py:12`, `models.py:7`, `auth.py:8`, `mcp_server.py:19` all follow `logger = logging.getLogger(__name__)` at module level
- **IMPORTS**: Already imported: `import logging` on line 4
- **GOTCHA**: Do NOT remove the `logging.basicConfig()` call in the `cli()` function. The module-level logger is for consistency and future use. The basicConfig call configures log output formatting for the CLI user.
- **VALIDATE**: `python -c "from second_brain.cli import logger; print(logger.name)"`

### Task 2: UPDATE `src/second_brain/config.py` — Add module-level logger

- **IMPLEMENT**: Three changes:
  1. Add `import logging` after line 1 (`from pathlib import Path`) — currently no module-level logging import
  2. Add `logger = logging.getLogger(__name__)` after the import block (after `from pydantic_settings import BaseSettings` on line 3)
  3. In `_validate_subscription_config` method (line 172-182): Remove the inline `import logging` on line 177, and change `logging.getLogger(__name__).info(...)` on line 178 to `logger.info(...)`.

  Before:
  ```python
  from pathlib import Path
  from pydantic import Field, model_validator
  from pydantic_settings import BaseSettings
  ```
  After:
  ```python
  import logging
  from pathlib import Path

  from pydantic import Field, model_validator
  from pydantic_settings import BaseSettings

  logger = logging.getLogger(__name__)
  ```
  And in the validator (line ~177):
  Before: `import logging` + `logging.getLogger(__name__).info(...)`
  After: `logger.info(...)` (remove local import)
- **PATTERN**: Same as all other modules
- **IMPORTS**: Adding `import logging` as new module-level import
- **GOTCHA**: The standard library import `import logging` goes BEFORE third-party imports (`from pathlib import Path`, `from pydantic import ...`). Follow PEP 8 import ordering.
- **VALIDATE**: `python -c "from second_brain.config import logger; print(logger.name)"`

### Task 3: UPDATE `src/second_brain/mcp_server.py` — Add return type to `_get_model()`

- **IMPLEMENT**: Add return type annotation to `_get_model()` on line 51. The function returns the `_model` module global which is set by `get_model(config)` from `models.py`. `get_model()` returns `Model` (from `pydantic_ai.models`). Since `_model` is initialized as `None` and only set after `_get_deps()` is called, the type is technically `Model | None`. But in practice, `_get_model()` always calls `_get_deps()` first which initializes it. Use `Model | None` to be accurate.

  Before (line 51):
  ```python
  def _get_model():
  ```
  After:
  ```python
  def _get_model() -> "Model | None":
  ```
  Add `Model` to the TYPE_CHECKING imports. Add a TYPE_CHECKING block since Model is only needed for the annotation:
  ```python
  from typing import TYPE_CHECKING

  if TYPE_CHECKING:
      from pydantic_ai.models import Model
  ```
  Or simply add the import directly (it's already a runtime dependency via `get_model`). Prefer the string annotation approach to avoid adding a new runtime import:
  ```python
  def _get_model() -> "Model | None":
  ```
  with the TYPE_CHECKING import.
- **PATTERN**: `_get_deps() -> BrainDeps` on line 43 uses a direct type. Follow the same style. Since `BrainDeps` is already imported at runtime (line 11), and `Model` is not, use TYPE_CHECKING guard.
- **IMPORTS**: Add `from typing import TYPE_CHECKING` and `if TYPE_CHECKING: from pydantic_ai.models import Model`
- **GOTCHA**: Don't add `from pydantic_ai.models import Model` as a runtime import — it would add an unnecessary import chain. Use TYPE_CHECKING guard + string annotation.
- **VALIDATE**: `python -c "from second_brain.mcp_server import _get_model; print('return' in str(_get_model.__annotations__) or 'annotations OK')"`

### Task 4: ADD `graph_health` tool to `src/second_brain/mcp_server.py`

- **IMPLEMENT**: Add a new `@server.tool()` async function `graph_health()` that mirrors CLI's `graph health` command (cli.py:523-538). Place it after the `graph_search` tool (after line 411). The implementation:

  ```python
  @server.tool()
  async def graph_health() -> str:
      """Check the health and connectivity of the Graphiti knowledge graph backend.
      Returns status, backend type, and any errors.
      """
      deps = _get_deps()
      if not deps.graphiti_service:
          return "Graphiti is not enabled. Set GRAPHITI_ENABLED=true in your .env file."

      health = await deps.graphiti_service.health_check()
      parts = [
          "# Graph Health\n",
          f"Status: {health.get('status', 'unknown')}",
          f"Backend: {health.get('backend', 'none')}",
      ]
      if health.get("error"):
          parts.append(f"Error: {health['error']}")
      return "\n".join(parts)
  ```

  This mirrors the CLI's output format (cli.py:533-536) but uses MCP markdown formatting (header + plain text).
- **PATTERN**: Mirror `graph_search` tool (mcp_server.py:386-411) for the deps/graphiti guard pattern. Mirror `brain_health` tool (mcp_server.py:360-383) for the output formatting style.
- **IMPORTS**: No new imports needed — `_get_deps` already available at module level.
- **GOTCHA**: Must check `deps.graphiti_service` is truthy (not just `is not None`) — same guard as `graph_search` on line 397. The `health_check()` return dict may not have an "error" key — use `.get("error")` with no default.
- **VALIDATE**: `python -c "from second_brain.mcp_server import server; names = [t.name for t in server._tool_manager._tools.values()]; assert 'graph_health' in names; print('graph_health tool registered')"`

### Task 5: UPDATE `tests/test_cli.py` — Health branch coverage

- **IMPLEMENT**: Add 2 tests to `TestHealthCommand` class (after `test_health_success` around line 266):

  ```python
  @patch("second_brain.services.health.HealthService")
  def test_health_with_graphiti_enabled(self, mock_hs, runner, mock_create_deps):
      """health command shows Graphiti status when not disabled."""
      mock_metrics = MagicMock()
      mock_metrics.memory_count = 42
      mock_metrics.total_patterns = 5
      mock_metrics.high_confidence = 2
      mock_metrics.medium_confidence = 2
      mock_metrics.low_confidence = 1
      mock_metrics.experience_count = 3
      mock_metrics.graph_provider = "none"
      mock_metrics.latest_update = "2026-02-15"
      mock_metrics.topics = {}
      mock_metrics.status = "BUILDING"
      mock_metrics.graphiti_status = "healthy"
      mock_metrics.graphiti_backend = "neo4j"
      mock_hs.return_value.compute = AsyncMock(return_value=mock_metrics)
      result = runner.invoke(cli, ["health"])
      assert result.exit_code == 0
      assert "Graphiti: healthy" in result.output
      assert "neo4j" in result.output

  @patch("second_brain.services.health.HealthService")
  def test_health_no_topics(self, mock_hs, runner, mock_create_deps):
      """health command skips topics section when topics is empty."""
      mock_metrics = MagicMock()
      mock_metrics.memory_count = 10
      mock_metrics.total_patterns = 2
      mock_metrics.high_confidence = 1
      mock_metrics.medium_confidence = 1
      mock_metrics.low_confidence = 0
      mock_metrics.experience_count = 1
      mock_metrics.graph_provider = "none"
      mock_metrics.latest_update = "2026-02-15"
      mock_metrics.topics = {}
      mock_metrics.status = "BUILDING"
      mock_metrics.graphiti_status = "disabled"
      mock_hs.return_value.compute = AsyncMock(return_value=mock_metrics)
      result = runner.invoke(cli, ["health"])
      assert result.exit_code == 0
      assert "Patterns by Topic" not in result.output
  ```
- **PATTERN**: Mirror existing `test_health_success` — same fixture dependencies, same mock setup structure
- **IMPORTS**: Already present — `from unittest.mock import patch, MagicMock, AsyncMock`
- **GOTCHA**: Must explicitly set `graphiti_status` on the mock. MagicMock auto-creates attributes, but `mock_metrics.graphiti_status` would return a MagicMock object which compares as `!= "disabled"` (truthy), causing the Graphiti line to print with garbled output. Always set string values explicitly.
- **VALIDATE**: `python -m pytest tests/test_cli.py::TestHealthCommand -v`

### Task 6: UPDATE `tests/test_cli.py` — Growth branch coverage

- **IMPLEMENT**: Add 4 tests to `TestGrowthCommand` class (after `test_growth_success` around line 291):

  ```python
  @patch("second_brain.services.health.HealthService")
  def test_growth_with_reviews(self, mock_hs, runner, mock_create_deps):
      """growth command shows quality metrics when reviews exist."""
      mock_metrics = MagicMock()
      mock_metrics.status = "GROWING"
      mock_metrics.graphiti_status = "disabled"
      mock_metrics.total_patterns = 10
      mock_metrics.high_confidence = 3
      mock_metrics.medium_confidence = 5
      mock_metrics.low_confidence = 2
      mock_metrics.growth_events_total = 15
      mock_metrics.patterns_created_period = 5
      mock_metrics.patterns_reinforced_period = 8
      mock_metrics.confidence_upgrades_period = 2
      mock_metrics.reviews_completed_period = 4
      mock_metrics.avg_review_score = 8.2
      mock_metrics.review_score_trend = "improving"
      mock_metrics.stale_patterns = []
      mock_metrics.topics = {}
      mock_hs.return_value.compute_growth = AsyncMock(return_value=mock_metrics)
      result = runner.invoke(cli, ["growth"])
      assert result.exit_code == 0
      assert "Quality Metrics" in result.output
      assert "8.2" in result.output
      assert "improving" in result.output

  @patch("second_brain.services.health.HealthService")
  def test_growth_with_stale_patterns(self, mock_hs, runner, mock_create_deps):
      """growth command shows stale patterns when present."""
      mock_metrics = MagicMock()
      mock_metrics.status = "GROWING"
      mock_metrics.graphiti_status = "disabled"
      mock_metrics.total_patterns = 10
      mock_metrics.high_confidence = 3
      mock_metrics.medium_confidence = 5
      mock_metrics.low_confidence = 2
      mock_metrics.growth_events_total = 15
      mock_metrics.patterns_created_period = 5
      mock_metrics.patterns_reinforced_period = 8
      mock_metrics.confidence_upgrades_period = 2
      mock_metrics.reviews_completed_period = 0
      mock_metrics.stale_patterns = ["Old Pattern", "Forgotten Rule"]
      mock_metrics.topics = {}
      mock_hs.return_value.compute_growth = AsyncMock(return_value=mock_metrics)
      result = runner.invoke(cli, ["growth"])
      assert result.exit_code == 0
      assert "Stale Patterns" in result.output
      assert "Old Pattern" in result.output

  @patch("second_brain.services.health.HealthService")
  def test_growth_custom_days(self, mock_hs, runner, mock_create_deps):
      """growth command accepts --days option."""
      mock_metrics = MagicMock()
      mock_metrics.status = "BUILDING"
      mock_metrics.graphiti_status = "disabled"
      mock_metrics.total_patterns = 5
      mock_metrics.high_confidence = 1
      mock_metrics.medium_confidence = 2
      mock_metrics.low_confidence = 2
      mock_metrics.growth_events_total = 3
      mock_metrics.patterns_created_period = 2
      mock_metrics.patterns_reinforced_period = 1
      mock_metrics.confidence_upgrades_period = 0
      mock_metrics.reviews_completed_period = 0
      mock_metrics.stale_patterns = []
      mock_metrics.topics = {}
      mock_hs.return_value.compute_growth = AsyncMock(return_value=mock_metrics)
      result = runner.invoke(cli, ["growth", "--days", "7"])
      assert result.exit_code == 0
      assert "Growth Report (7 days)" in result.output

  @patch("second_brain.services.health.HealthService")
  def test_growth_with_topics(self, mock_hs, runner, mock_create_deps):
      """growth command shows topics breakdown."""
      mock_metrics = MagicMock()
      mock_metrics.status = "GROWING"
      mock_metrics.graphiti_status = "disabled"
      mock_metrics.total_patterns = 10
      mock_metrics.high_confidence = 3
      mock_metrics.medium_confidence = 5
      mock_metrics.low_confidence = 2
      mock_metrics.growth_events_total = 15
      mock_metrics.patterns_created_period = 5
      mock_metrics.patterns_reinforced_period = 8
      mock_metrics.confidence_upgrades_period = 2
      mock_metrics.reviews_completed_period = 0
      mock_metrics.stale_patterns = []
      mock_metrics.topics = {"content": 5, "messaging": 3}
      mock_hs.return_value.compute_growth = AsyncMock(return_value=mock_metrics)
      result = runner.invoke(cli, ["growth"])
      assert result.exit_code == 0
      assert "content: 5" in result.output
      assert "messaging: 3" in result.output
  ```
- **PATTERN**: Mirror existing `test_growth_success` — same fixture dependencies, same mock pattern
- **IMPORTS**: Already present
- **GOTCHA**: The growth command calls `HealthService().compute_growth()` not `.compute()`. Mock must be on `.compute_growth`. All metric fields must be set even for branches you're not testing, because the command accesses them sequentially.
- **VALIDATE**: `python -m pytest tests/test_cli.py::TestGrowthCommand -v`

### Task 7: UPDATE `tests/test_cli.py` — Create and Review flag coverage

- **IMPLEMENT**: Add 2 tests:

  In `TestCreateCommand` (after `test_create_success` around line 165):
  ```python
  @patch("second_brain.cli.get_model")
  @patch("second_brain.agents.create.create_agent")
  def test_create_with_mode_override(self, mock_agent, mock_model, runner, mock_create_deps):
      """create command passes --mode override to agent prompt."""
      mock_model.return_value = MagicMock()
      type_config = MagicMock()
      type_config.name = "LinkedIn Post"
      type_config.default_mode = "casual"
      type_config.structure_hint = "Hook -> Body -> CTA"
      type_config.max_words = 300
      registry = mock_create_deps.get_content_type_registry()
      registry.get = AsyncMock(return_value=type_config)
      mock_output = MagicMock()
      mock_output.content_type = "linkedin"
      mock_output.mode = "formal"
      mock_output.draft = "Draft content here"
      mock_output.word_count = 80
      mock_output.voice_elements = []
      mock_output.patterns_applied = []
      mock_output.examples_referenced = []
      mock_output.notes = None
      mock_agent.run = AsyncMock(return_value=MagicMock(output=mock_output))
      result = runner.invoke(cli, ["create", "Write about AI", "--mode", "formal"])
      assert result.exit_code == 0
      # Verify the enhanced prompt included the overridden mode
      call_args = mock_agent.run.call_args
      prompt = call_args[0][0]  # First positional arg
      assert "Communication mode: formal" in prompt
  ```

  In `TestReviewCommand` (after `test_review_success` around line 186):
  ```python
  @patch("second_brain.cli.get_model")
  @patch("second_brain.agents.review.run_full_review")
  def test_review_with_type_flag(self, mock_review, mock_model, runner, mock_create_deps):
      """review command passes --type flag to run_full_review."""
      mock_model.return_value = MagicMock()
      mock_result = MagicMock()
      mock_result.overall_score = 7.5
      mock_result.verdict = "NEEDS REVISION"
      mock_result.summary = "Good but needs work"
      mock_result.scores = []
      mock_result.top_strengths = []
      mock_result.critical_issues = []
      mock_result.next_steps = []
      mock_review.return_value = mock_result
      result = runner.invoke(cli, ["review", "Test content", "--type", "email"])
      assert result.exit_code == 0
      # Verify content_type was passed to run_full_review
      mock_review.assert_called_once()
      call_args = mock_review.call_args[0]
      assert call_args[3] == "email"  # 4th positional arg is content_type
  ```
- **PATTERN**: Mirror existing create/review success tests
- **IMPORTS**: Already present
- **GOTCHA**: For the create mode test, the enhanced prompt is built as a string (cli.py:196-203) and passed as the first arg to `agent.run()`. Check `mock_agent.run.call_args[0][0]` to verify. For review, `run_full_review` is called with `(content, deps, model, content_type)` — the 4th arg (index 3) is content_type.
- **VALIDATE**: `python -m pytest tests/test_cli.py::TestCreateCommand tests/test_cli.py::TestReviewCommand -v`

### Task 8: UPDATE `tests/test_cli.py` — Recall and Learn output formatting

- **IMPLEMENT**: Add 2 tests for populated output branches:

  In `TestRecallCommand` (after `test_recall_missing_query`):
  ```python
  @patch("second_brain.cli.get_model")
  @patch("second_brain.agents.recall.recall_agent")
  def test_recall_with_populated_output(self, mock_agent, mock_model, runner, mock_create_deps):
      """recall command formats matches, patterns, and relations."""
      mock_model.return_value = MagicMock()
      mock_match = MagicMock()
      mock_match.relevance = "HIGH"
      mock_match.content = "Use compelling hooks"
      mock_match.source = "content-patterns.md"
      mock_relation = MagicMock()
      mock_relation.source = "LinkedIn"
      mock_relation.relationship = "uses"
      mock_relation.target = "hooks"
      mock_output = MagicMock()
      mock_output.query = "hooks"
      mock_output.matches = [mock_match]
      mock_output.patterns = ["Hook First", "Short > Structured"]
      mock_output.relations = [mock_relation]
      mock_output.summary = "Found hook patterns"
      mock_agent.run = AsyncMock(return_value=MagicMock(output=mock_output))
      result = runner.invoke(cli, ["recall", "hooks"])
      assert result.exit_code == 0
      assert "Matches" in result.output
      assert "Use compelling hooks" in result.output
      assert "content-patterns.md" in result.output
      assert "Hook First" in result.output
      assert "Graph Relationships" in result.output
      assert "LinkedIn" in result.output
      assert "uses" in result.output
  ```

  In `TestLearnCommand` (after `test_learn_missing_content`):
  ```python
  @patch("second_brain.cli.get_model")
  @patch("second_brain.agents.learn.learn_agent")
  def test_learn_with_patterns_output(self, mock_agent, mock_model, runner, mock_create_deps):
      """learn command formats extracted patterns with details."""
      mock_model.return_value = MagicMock()
      mock_pattern = MagicMock()
      mock_pattern.confidence = "MEDIUM"
      mock_pattern.name = "Hook First"
      mock_pattern.is_reinforcement = False
      mock_pattern.pattern_text = "Always start with a compelling hook that grabs attention"
      mock_pattern.anti_patterns = ["Starting with a question", "Generic openings"]
      mock_output = MagicMock()
      mock_output.input_summary = "Content writing session"
      mock_output.patterns_extracted = [mock_pattern]
      mock_output.insights = ["Hooks outperform questions"]
      mock_output.experience_recorded = True
      mock_output.experience_category = "content"
      mock_output.patterns_new = 1
      mock_output.patterns_reinforced = 0
      mock_output.storage_summary = "1 pattern stored"
      mock_agent.run = AsyncMock(return_value=MagicMock(output=mock_output))
      result = runner.invoke(cli, ["learn", "Today I learned about hooks"])
      assert result.exit_code == 0
      assert "Hook First" in result.output
      assert "(new)" in result.output
      assert "MEDIUM" in result.output
      assert "Anti:" in result.output
      assert "Starting with a question" in result.output
      assert "Insights" in result.output
  ```
- **PATTERN**: Mirror existing recall/learn success tests, but with populated output fields
- **IMPORTS**: Already present
- **GOTCHA**: For learn anti_patterns, the CLI only shows first 2 (cli.py:146 — `p.anti_patterns[:2]`). Mock should have 2+ to verify truncation works. For pattern_text, CLI truncates to 100 chars (cli.py:144 — `p.pattern_text[:100]`).
- **VALIDATE**: `python -m pytest tests/test_cli.py::TestRecallCommand tests/test_cli.py::TestLearnCommand -v`

### Task 9: UPDATE `tests/test_cli.py` — Subscription flag test

- **IMPLEMENT**: Add test to `TestCLIBasic`:
  ```python
  @patch("second_brain.services.health.HealthService")
  def test_subscription_flag_sets_env(self, mock_hs, runner, mock_create_deps, monkeypatch):
      """--subscription flag sets USE_SUBSCRIPTION env var."""
      monkeypatch.delenv("USE_SUBSCRIPTION", raising=False)
      mock_metrics = MagicMock()
      mock_metrics.memory_count = 0
      mock_metrics.total_patterns = 0
      mock_metrics.high_confidence = 0
      mock_metrics.medium_confidence = 0
      mock_metrics.low_confidence = 0
      mock_metrics.experience_count = 0
      mock_metrics.graph_provider = "none"
      mock_metrics.latest_update = "none"
      mock_metrics.topics = {}
      mock_metrics.status = "BUILDING"
      mock_metrics.graphiti_status = "disabled"
      mock_hs.return_value.compute = AsyncMock(return_value=mock_metrics)
      result = runner.invoke(cli, ["--subscription", "health"])
      assert result.exit_code == 0
      import os
      assert os.environ.get("USE_SUBSCRIPTION") == "true"
      # Clean up
      monkeypatch.delenv("USE_SUBSCRIPTION", raising=False)
  ```
- **PATTERN**: Mirror `test_cli_verbose_flag` style but with a command that actually runs
- **IMPORTS**: Add `import os` at top of test_cli.py if not already present
- **GOTCHA**: CliRunner runs in the same process — env vars set by the CLI persist. Use monkeypatch to clean up. The `monkeypatch` fixture is available via pytest but needs to be added to the test method signature.
- **VALIDATE**: `python -m pytest tests/test_cli.py::TestCLIBasic -v`

### Task 10: UPDATE `tests/test_mcp_server.py` — graph_health tool tests

- **IMPLEMENT**: Add new test class `TestGraphHealth` after `TestMCPGraphSearch`:
  ```python
  class TestGraphHealth:
      """Test graph_health MCP tool."""

      @patch("second_brain.mcp_server._get_deps")
      async def test_graph_health_not_enabled(self, mock_get_deps):
          mock_deps = MagicMock()
          mock_deps.graphiti_service = None
          mock_get_deps.return_value = mock_deps
          from second_brain.mcp_server import graph_health
          result = await graph_health.fn()
          assert "not enabled" in result.lower()

      @patch("second_brain.mcp_server._get_deps")
      async def test_graph_health_healthy(self, mock_get_deps):
          mock_graphiti = AsyncMock()
          mock_graphiti.health_check = AsyncMock(return_value={
              "status": "healthy",
              "backend": "neo4j",
          })
          mock_deps = MagicMock()
          mock_deps.graphiti_service = mock_graphiti
          mock_get_deps.return_value = mock_deps
          from second_brain.mcp_server import graph_health
          result = await graph_health.fn()
          assert "healthy" in result
          assert "neo4j" in result

      @patch("second_brain.mcp_server._get_deps")
      async def test_graph_health_with_error(self, mock_get_deps):
          mock_graphiti = AsyncMock()
          mock_graphiti.health_check = AsyncMock(return_value={
              "status": "degraded",
              "backend": "falkordb",
              "error": "Connection timeout",
          })
          mock_deps = MagicMock()
          mock_deps.graphiti_service = mock_graphiti
          mock_get_deps.return_value = mock_deps
          from second_brain.mcp_server import graph_health
          result = await graph_health.fn()
          assert "degraded" in result
          assert "falkordb" in result
          assert "Connection timeout" in result
  ```
- **PATTERN**: Mirror `TestMCPGraphSearch` (test_mcp_server.py:454-493) — same mock structure
- **IMPORTS**: Already present — `from unittest.mock import MagicMock, AsyncMock, patch`
- **GOTCHA**: Import `graph_health` inside each test method (after patches applied). The `.fn` attribute gives the raw function to call.
- **VALIDATE**: `python -m pytest tests/test_mcp_server.py::TestGraphHealth -v`

### Task 11: UPDATE `tests/test_mcp_server.py` — Growth report branch coverage

- **IMPLEMENT**: Add 2 tests to `TestGrowthReport`:
  ```python
  @patch("second_brain.mcp_server._get_deps")
  @patch("second_brain.services.health.HealthService")
  async def test_growth_report_with_stale_patterns(self, mock_hs_cls, mock_deps_fn):
      from second_brain.mcp_server import growth_report
      mock_metrics = HealthMetrics(
          memory_count=50, total_patterns=10, high_confidence=3,
          medium_confidence=5, low_confidence=2, experience_count=8,
          graph_provider="none", latest_update="2026-02-15", status="GROWING",
          stale_patterns=["Old Pattern", "Forgotten Rule"],
      )
      mock_hs_cls.return_value.compute_growth = AsyncMock(return_value=mock_metrics)
      mock_deps_fn.return_value = MagicMock()
      result = await growth_report.fn(days=30)
      assert "Stale Patterns" in result
      assert "Old Pattern" in result
      assert "Forgotten Rule" in result

  @patch("second_brain.mcp_server._get_deps")
  @patch("second_brain.services.health.HealthService")
  async def test_growth_report_with_topics(self, mock_hs_cls, mock_deps_fn):
      from second_brain.mcp_server import growth_report
      mock_metrics = HealthMetrics(
          memory_count=50, total_patterns=10, high_confidence=3,
          medium_confidence=5, low_confidence=2, experience_count=8,
          graph_provider="none", latest_update="2026-02-15", status="GROWING",
          topics={"Content": 5, "Messaging": 3},
      )
      mock_hs_cls.return_value.compute_growth = AsyncMock(return_value=mock_metrics)
      mock_deps_fn.return_value = MagicMock()
      result = await growth_report.fn(days=30)
      assert "Content" in result
      assert "Messaging" in result
  ```
- **PATTERN**: Mirror existing `test_growth_report` — uses HealthMetrics dataclass directly
- **IMPORTS**: Already present — `from second_brain.services.health import HealthMetrics`
- **GOTCHA**: HealthMetrics has 8 required fields. The optional fields (stale_patterns, topics) use `field(default_factory=...)` so they can be omitted. But the required fields MUST all be provided.
- **VALIDATE**: `python -m pytest tests/test_mcp_server.py::TestGrowthReport -v`

### Task 12: UPDATE `tests/test_mcp_server.py` — Create content default mode

- **IMPLEMENT**: Add test after `test_create_content_invalid_type` in `TestMCPTools`:
  ```python
  @patch("second_brain.mcp_server._get_model")
  @patch("second_brain.mcp_server._get_deps")
  @patch("second_brain.mcp_server.create_agent")
  async def test_create_content_default_mode(self, mock_agent, mock_deps_fn, mock_model_fn):
      """create_content uses type's default_mode when mode is None."""
      from second_brain.mcp_server import create_content
      mock_result = MagicMock()
      mock_result.output = CreateResult(
          draft="Test draft content",
          content_type="linkedin",
          mode="casual",
          word_count=50,
      )
      mock_agent.run = AsyncMock(return_value=mock_result)
      linkedin_config = ContentTypeConfig(
          name="LinkedIn Post", default_mode="casual",
          structure_hint="Hook -> Body -> CTA", example_type="linkedin",
          max_words=300, is_builtin=True,
      )
      mock_registry = MagicMock()
      mock_registry.get = AsyncMock(return_value=linkedin_config)
      mock_deps = MagicMock()
      mock_deps.get_content_type_registry.return_value = mock_registry
      mock_deps_fn.return_value = mock_deps
      mock_model_fn.return_value = MagicMock()
      # Call WITHOUT mode parameter (defaults to None)
      result = await create_content.fn(prompt="Write about AI", content_type="linkedin")
      assert "Test draft" in result
      # Verify agent was called with default mode in prompt
      call_args = mock_agent.run.call_args[0][0]
      assert "Communication mode: casual" in call_args
  ```
- **PATTERN**: Mirror `test_create_content_tool` (test_mcp_server.py:315-353)
- **IMPORTS**: Need `CreateResult`, `ContentTypeConfig` — already imported
- **GOTCHA**: The `mode` parameter defaults to `None` in `create_content()` function signature. When None, `effective_mode = mode or type_config.default_mode` uses the type's default. Verify by checking the prompt string passed to agent.run.
- **VALIDATE**: `python -m pytest tests/test_mcp_server.py::TestMCPTools -v`

### Task 13: UPDATE `tests/test_config.py` — Deps graphiti_enabled path

- **IMPLEMENT**: Add 3 tests to `TestCreateDeps`:
  ```python
  @patch("second_brain.services.storage.StorageService")
  @patch("second_brain.services.memory.MemoryService")
  def test_create_deps_graphiti_enabled_flag(self, mock_mem, mock_storage, tmp_path):
      """create_deps with graphiti_enabled=True (independent of graph_provider)."""
      config = BrainConfig(
          graphiti_enabled=True,
          falkordb_url="falkor://localhost:6379",
          supabase_url="https://test.supabase.co",
          supabase_key="test-key",
          brain_data_path=tmp_path,
          _env_file=None,
      )
      with patch("second_brain.services.graphiti.GraphitiService") as mock_graphiti:
          mock_graphiti.return_value = MagicMock()
          from second_brain.deps import create_deps
          deps = create_deps(config=config)
          assert deps.graphiti_service is not None
          mock_graphiti.assert_called_once_with(config)

  @patch("second_brain.services.storage.StorageService")
  @patch("second_brain.services.memory.MemoryService")
  def test_create_deps_graphiti_enabled_import_error(self, mock_mem, mock_storage, tmp_path):
      """create_deps gracefully handles missing graphiti when enabled."""
      config = BrainConfig(
          graphiti_enabled=True,
          falkordb_url="falkor://localhost:6379",
          supabase_url="https://test.supabase.co",
          supabase_key="test-key",
          brain_data_path=tmp_path,
          _env_file=None,
      )
      with patch("second_brain.services.graphiti.GraphitiService", side_effect=ImportError):
          from second_brain.deps import create_deps
          deps = create_deps(config=config)
          assert deps.graphiti_service is None

  @patch("second_brain.services.storage.StorageService")
  @patch("second_brain.services.memory.MemoryService")
  def test_create_deps_default_config(self, mock_mem, mock_storage, tmp_path, monkeypatch):
      """create_deps() with no config arg creates BrainConfig from env."""
      monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
      monkeypatch.setenv("SUPABASE_KEY", "test-key")
      monkeypatch.setenv("BRAIN_DATA_PATH", str(tmp_path))
      # Patch BrainConfig at the deps module to control .env loading
      with patch("second_brain.deps.BrainConfig") as mock_config_cls:
          mock_config_cls.return_value = BrainConfig(
              supabase_url="https://test.supabase.co",
              supabase_key="test-key",
              brain_data_path=tmp_path,
              _env_file=None,
          )
          from second_brain.deps import create_deps
          deps = create_deps()  # No config arg — triggers config=None path
          mock_config_cls.assert_called_once()
          assert deps.config is not None
  ```
- **PATTERN**: Mirror `test_create_deps_graphiti_enabled` (test_config.py:315-333)
- **IMPORTS**: Already present — `from unittest.mock import patch, MagicMock` and `from second_brain.config import BrainConfig`
- **GOTCHA**: For `test_create_deps_default_config`, patching `second_brain.deps.BrainConfig` is the safest approach. This avoids `.env` file loading entirely. The mock returns a real BrainConfig instance (created with `_env_file=None`) so downstream code works normally.
- **VALIDATE**: `python -m pytest tests/test_config.py::TestCreateDeps -v`

### Task 14: VALIDATE — Full test suite

- **IMPLEMENT**: Run the complete test suite to verify zero regressions. Current baseline is 443 tests. Expected new total: ~463 (443 + 20 new tests).
- **PATTERN**: Standard validation
- **IMPORTS**: N/A
- **GOTCHA**: If any existing test fails, investigate before assuming it's a regression — could be pre-existing flakiness or environment issue. Check the failure message for `.env` bleed or import issues.
- **VALIDATE**: `python -m pytest tests/ -v --tb=short`

---

## TESTING STRATEGY

### Unit Tests

All new tests are unit tests that mock external dependencies:

**CLI tests** (10 new tests in test_cli.py):
- `TestHealthCommand.test_health_with_graphiti_enabled` — Tests cli.py:343-344 branch
- `TestHealthCommand.test_health_no_topics` — Tests cli.py:346 branch absence
- `TestGrowthCommand.test_growth_with_reviews` — Tests cli.py:378-382 branch
- `TestGrowthCommand.test_growth_with_stale_patterns` — Tests cli.py:384-387 branch
- `TestGrowthCommand.test_growth_custom_days` — Tests cli.py:357 --days option
- `TestGrowthCommand.test_growth_with_topics` — Tests cli.py:389-392 branch
- `TestCreateCommand.test_create_with_mode_override` — Tests cli.py:194 mode param
- `TestReviewCommand.test_review_with_type_flag` — Tests cli.py:237 content_type param
- `TestRecallCommand.test_recall_with_populated_output` — Tests cli.py:60-73 output branches
- `TestLearnCommand.test_learn_with_patterns_output` — Tests cli.py:139-146 output branches
- `TestCLIBasic.test_subscription_flag_sets_env` — Tests cli.py:36-38 env setting

**MCP tests** (6 new tests in test_mcp_server.py):
- `TestGraphHealth.test_graph_health_not_enabled` — Tests new tool guard
- `TestGraphHealth.test_graph_health_healthy` — Tests new tool success path
- `TestGraphHealth.test_graph_health_with_error` — Tests new tool error path
- `TestGrowthReport.test_growth_report_with_stale_patterns` — Tests mcp_server.py:484-487
- `TestGrowthReport.test_growth_report_with_topics` — Tests mcp_server.py:489-492
- `TestMCPTools.test_create_content_default_mode` — Tests mcp_server.py:211

**Deps tests** (3 new tests in test_config.py):
- `TestCreateDeps.test_create_deps_graphiti_enabled_flag` — Tests deps.py:47
- `TestCreateDeps.test_create_deps_graphiti_enabled_import_error` — Tests deps.py:47-53
- `TestCreateDeps.test_create_deps_default_config` — Tests deps.py:42-43

### Integration Tests

No new integration tests — this plan focuses on branch coverage of existing functionality. The commands and tools are already integration-tested at the happy-path level.

### Edge Cases

- Health with `graphiti_status = "healthy"` — the `if metrics.graphiti_status != "disabled"` branch executes
- Health with empty topics dict — the `if metrics.topics:` branch is skipped
- Growth with `reviews_completed_period > 0` — the quality metrics section appears
- Growth with non-empty `stale_patterns` — the stale patterns section appears
- Growth with non-empty `topics` — the topics section appears
- Growth with custom `--days 7` — the report header reflects the custom days
- Create with `--mode formal` — the mode override is used instead of type default
- Create with mode=None — falls back to `type_config.default_mode`
- Review with `--type email` — content_type parameter is passed through to `run_full_review`
- Recall with populated matches, patterns, relations — all output sections render
- Learn with populated patterns + anti_patterns — pattern details + anti-pattern truncation render
- Graph health with no graphiti service — returns "not enabled" message
- Graph health with error in response dict — error message appears in output
- Deps with `graphiti_enabled=True` but `graph_provider="none"` — independent flag path activates
- Deps with `graphiti_enabled=True` but ImportError — graceful degradation to None
- Deps with no config argument — BrainConfig created from environment

---

## VALIDATION COMMANDS

### Level 1: Syntax & Style
```bash
python -c "from second_brain.cli import logger; print(f'cli logger: {logger.name}')"
python -c "from second_brain.config import logger; print(f'config logger: {logger.name}')"
python -c "from second_brain.mcp_server import _get_model; print('_get_model has annotations')"
python -c "from second_brain.mcp_server import server; names = [t.name for t in server._tool_manager._tools.values()]; assert 'graph_health' in names; print('graph_health registered')"
```

### Level 2: Unit Tests
```bash
python -m pytest tests/test_cli.py -v --tb=short
python -m pytest tests/test_mcp_server.py -v --tb=short
python -m pytest tests/test_config.py -v --tb=short
```

### Level 3: Integration Tests
```bash
python -m pytest tests/ -v --tb=short
```

### Level 4: Manual Validation

1. Run `python -m second_brain.cli --help` — verify "subscription" flag visible in output
2. Run `python -m second_brain.cli health --help` — verify command exists and shows help
3. Verify import: `python -c "from second_brain.mcp_server import graph_health; print(type(graph_health))"`
4. Verify all modules import cleanly: `python -c "from second_brain import cli, config, mcp_server, deps; print('All imports OK')"`

### Level 5: Additional Validation (Optional)

```bash
# Count total tests (should be ~463)
python -m pytest tests/ --co -q 2>/dev/null | tail -1
```

---

## ACCEPTANCE CRITERIA

- [ ] `cli.py` has module-level `logger = logging.getLogger(__name__)` after imports
- [ ] `config.py` has module-level `import logging` + `logger = logging.getLogger(__name__)` and validator uses the module-level logger
- [ ] `mcp_server.py` `_get_model()` has `-> "Model | None"` return type annotation with TYPE_CHECKING import
- [ ] `mcp_server.py` has `graph_health` tool registered on server that mirrors CLI behavior
- [ ] CLI health test covers `graphiti_status != "disabled"` branch — asserts "Graphiti: healthy"
- [ ] CLI health test covers empty topics branch — asserts "Patterns by Topic" absent
- [ ] CLI growth tests cover reviews, stale patterns, topics, and custom --days
- [ ] CLI create test covers --mode override — verifies mode in agent prompt
- [ ] CLI review test covers --type flag — verifies content_type passed to run_full_review
- [ ] CLI recall test covers populated matches/patterns/relations output formatting
- [ ] CLI learn test covers populated patterns with anti_patterns output formatting
- [ ] CLI subscription flag test verifies USE_SUBSCRIPTION env var is set
- [ ] MCP graph_health tests cover: not enabled, healthy, error cases
- [ ] MCP growth report tests cover stale patterns and topics branches
- [ ] MCP create content test covers default mode fallback (mode=None)
- [ ] Deps tests cover graphiti_enabled=True path (create + import error)
- [ ] Deps test covers create_deps() with no config arg
- [ ] All validation commands pass with zero errors
- [ ] Full test suite passes with zero failures
- [ ] Total test count increases by ~20 from 443 baseline

---

## COMPLETION CHECKLIST

- [ ] All 14 tasks completed in order
- [ ] Each task validation command passed
- [ ] All Level 1-3 validation commands executed successfully
- [ ] Full test suite passes with zero failures
- [ ] No import errors in any modified module
- [ ] Manual testing confirms CLI and MCP tools work
- [ ] All acceptance criteria met
- [ ] Total test count is ~463

---

## NOTES

### Key Design Decisions

- **Tests in existing files, not new ones**: deps tests stay in test_config.py where they logically belong alongside config tests. No test_deps.py created — avoids file proliferation.
- **Only testing untested branches**: Maximizes ROI per test. We don't re-test happy paths that already have coverage.
- **graph_health MCP tool is a thin passthrough**: No business logic — just formatting the health_check() dict response. Mirrors CLI behavior exactly.
- **TYPE_CHECKING guard for Model import**: Avoids adding a runtime import to mcp_server.py. The Model type is only needed for the annotation, not at runtime.
- **MagicMock with explicit attributes over spec**: The existing test suite consistently uses explicit attribute setting on MagicMock (not `spec=HealthMetrics`). We follow the same pattern for consistency.

### Risks

- Risk 1: MagicMock auto-attribute creation may mask missing fields — **Mitigation**: All mock attributes explicitly set to match production types
- Risk 2: `create_deps()` with no arg reads `.env` file — **Mitigation**: Patch `second_brain.deps.BrainConfig` constructor to return a controlled config
- Risk 3: CliRunner doesn't isolate env vars for subscription flag test — **Mitigation**: Use monkeypatch.delenv() for cleanup

### Confidence Score: 9/10

- **Strengths**: All target files read with line numbers, all test patterns documented with actual code, fixtures understood, scope well-bounded, ~20 focused tests with explicit implementations
- **Uncertainties**: The `create_deps()` default config test uses constructor patching which may be fragile if deps.py import patterns change
- **Mitigations**: If the BrainConfig constructor patch breaks, fall back to monkeypatch.setenv for all required vars + monkeypatch the `.env` file path to a nonexistent file
