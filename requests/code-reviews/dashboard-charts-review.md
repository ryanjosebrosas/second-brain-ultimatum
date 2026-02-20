# Code Review: Dashboard & Charts Components

**Mode**: Parallel (4 agents)
**Files Modified**: 1 (`frontend/pages/dashboard.py`)
**Files Added**: 1 (`frontend/components/charts.py`)
**Files Deleted**: 1 (`requests/code-reviews/data-infra-docs-review.md`)
**Total Findings**: 15 (Critical: 1, Major: 7, Minor: 7)

---

## Critical Findings

### 1. [Type Safety] `Series.get()` Does Not Exist — Runtime AttributeError
- **File**: `frontend/components/charts.py:106`
- **Issue**: Calling `.get()` on a pandas `Series` — `Series` has no `.get()` method
- **Detail**: In `dimension_breakdown`, `for _, row in df.iterrows()` yields `pd.Series` objects. Line 106 calls `row.get("review_count", 0)`. `pandas.Series` does NOT have a `.get()` method. This is a guaranteed `AttributeError` at runtime whenever `dimension_breakdown()` is called with data containing rows.
- **Suggestion**: Replace with `count = row["review_count"] if "review_count" in row.index else 0`, or skip the DataFrame entirely and iterate the raw list of dicts (see Performance finding #4)

---

## Major Findings

### 2. [Performance] No Response Caching — 5 HTTP Calls Per Rerun
- **File**: `frontend/pages/dashboard.py:28,94,132,171,219`
- **Issue**: All 5 API calls execute on every Streamlit script rerun with zero caching
- **Detail**: Streamlit reruns the entire script on every widget interaction. Each rerun fires 5 synchronous HTTP requests to the FastAPI backend. Health/milestone/setup data doesn't change second-to-second, so every repeated fetch is wasted work causing noticeable UI lag.
- **Suggestion**: Wrap calls with `@st.cache_data(ttl=60)`:
  ```python
  @st.cache_data(ttl=60)
  def cached_get_health():
      return api_client.get_health()
  ```

### 3. [Performance] All Tabs Fetch Eagerly Regardless of Active Tab
- **File**: `frontend/pages/dashboard.py:26-232`
- **Issue**: All 4 tab data fetches execute unconditionally, not lazily per active tab
- **Detail**: Streamlit's `st.tabs` doesn't gate execution of `with tab_*:` blocks — all run every rerun. A user on the Overview tab still pays for `get_growth()`, `get_quality()`, and `get_setup()`. Combined with no caching, this means 5 blocking sequential HTTP calls before any UI renders.
- **Suggestion**: Combined with `@st.cache_data` fix (#2), the cost becomes a cache lookup for non-active tabs, which is acceptable. Alternatively, use `st.session_state` to track active tab and only fetch relevant data.

### 4. [Performance] Unnecessary DataFrame for Row-wise Iteration
- **File**: `frontend/components/charts.py:98-113`
- **Issue**: `dimension_breakdown` converts a list of dicts to a DataFrame only to iterate it back row-by-row with `.iterrows()` (slowest pandas iteration)
- **Detail**: The data is already a list of dicts. Converting to DataFrame then iterating with `.iterrows()` (which boxes each row into a `pd.Series`) adds unnecessary overhead and complexity.
- **Suggestion**: Skip the DataFrame entirely and iterate the raw list:
  ```python
  for row in dimensions:
      dim = row.get("dimension", "")
      score = row.get("avg_score", 0)
      count = row.get("review_count", 0)
  ```
  This also fixes the Critical `Series.get()` bug (#1).

### 5. [Security] XSS via Unsanitized API Data in `graph_status_card`
- **File**: `frontend/components/charts.py:133-138`
- **Issue**: API-sourced `status` string injected directly into HTML rendered with `unsafe_allow_html=True`
- **Detail**: If the backend returns unexpected data (e.g., `</span><script>...</script>`), the injected markup would execute in the browser. The `status` string is embedded unescaped at line 136.
- **Suggestion**: HTML-escape all API-sourced strings: `import html; status_safe = html.escape(status.upper())`

### 6. [Security] XSS via Unsanitized `level` in `brain_level_badge`
- **File**: `frontend/components/charts.py:37`
- **Issue**: API-sourced `level` string embedded unescaped into HTML with `unsafe_allow_html=True`
- **Detail**: Same pattern as #5 — `level` from the milestones API is placed as HTML content. A crafted level string would execute as HTML.
- **Suggestion**: `import html; level_safe = html.escape(level)`

### 7. [Type Safety] Untyped Parameters on `metric_card`
- **File**: `frontend/components/charts.py:10`
- **Issue**: `value` and `delta` parameters have no type annotations — implicit `Any`
- **Detail**: `metric_card` is called 20+ times in `dashboard.py`. Without types, mypy can't catch type mismatches at call sites (e.g., passing a dict where int is expected).
- **Suggestion**: `value: int | float | str, delta: int | float | str | None = None`

### 8. [Architecture] Inconsistent Import Style for `api_client`
- **File**: `frontend/pages/dashboard.py:15`
- **Issue**: Uses `import api_client` (module import) while all other pages use `from api_client import ...` (named imports)
- **Detail**: `memory.py` uses `from api_client import search_memory, semantic_search, ...`. Dashboard uses `api_client.get_health()`. Creates two conflicting idioms across pages.
- **Suggestion**: Replace with `from api_client import get_health, get_milestones, get_growth, get_quality, get_setup`

---

## Minor Findings

### 9. [Type Safety] Missing `-> None` Return Annotations on All `charts.py` Functions
- **File**: `frontend/components/charts.py:10,15,31,42,69,89,124`
- **Issue**: All 7 functions are side-effect render functions that implicitly return `None` but lack `-> None` annotations

### 10. [Type Safety] Bare `dict` Parameters Without Key/Value Types
- **File**: `frontend/components/charts.py:42,69,89,124`
- **Issue**: `setup_checklist(setup_data: dict)`, `quality_trend_chart(quality_data: dict)`, etc. use bare `dict` — equivalent to `dict[Any, Any]`
- **Suggestion**: Annotate as `dict[str, Any]` minimum; ideally define `TypedDict` for API response shapes

### 11. [Architecture] Duplicated Badge HTML Template
- **File**: `frontend/components/charts.py:34-39,133-138`
- **Issue**: Identical HTML badge template copy-pasted between `brain_level_badge()` and `graph_status_card()`
- **Suggestion**: Extract a private `_render_badge(text: str, color: str) -> None` helper

### 12. [Architecture] Lazy pandas Import Outside MCP Server
- **File**: `frontend/components/charts.py:71,92`
- **Issue**: `import pandas as pd` inside function bodies. The project's lazy-import pattern is reserved for agent imports in `mcp_server.py`
- **Suggestion**: Move to module top-level

### 13. [Performance] Redundant DataFrame Construction for Same Data
- **File**: `frontend/components/charts.py:78,98`
- **Issue**: Both `quality_trend_chart` and `dimension_breakdown` independently build `pd.DataFrame(dimensions)` from the same data in the same render
- **Suggestion**: Compute once and pass, or skip DataFrame entirely for `dimension_breakdown` (see #4)

### 14. [Security] Exception Message Leakage to UI
- **File**: `frontend/pages/dashboard.py:30,96,134,173,220`
- **Issue**: Raw exception objects from httpx rendered in `st.error(f"...: {e}")`, potentially exposing internal URLs
- **Suggestion**: Show generic error messages; log details server-side

### 15. [Security] Unescaped API Data in `st.markdown` f-strings
- **File**: `frontend/pages/dashboard.py:126,165,199`
- **Issue**: API-sourced strings embedded in `st.markdown()` without sanitization. While `unsafe_allow_html` is not set, malicious data could inject Markdown formatting (links, bold, etc.)
- **Suggestion**: Use `st.text()` for plain-text API data, or strip markdown special characters

---

## Summary Assessment

**Overall**: Needs revision

**Recommended action**: Fix the 1 critical bug (guaranteed runtime error) and the 2 security XSS findings before merge. Add response caching to prevent unnecessary backend load.

### Priority Actions

| Priority | # | Action | Effort |
|----------|---|--------|--------|
| P0 | 1,4 | Fix `Series.get()` bug — replace `iterrows()` with direct list iteration | Low |
| P1 | 2 | Add `@st.cache_data(ttl=60)` to all 5 API calls | Low |
| P1 | 5,6 | HTML-escape API strings in `unsafe_allow_html` templates | Low |
| P1 | 8 | Fix import style to match other pages | Low |
| P2 | 7 | Add type annotations to `metric_card` params | Low |
| P2 | 11 | Extract `_render_badge()` helper to DRY badge HTML | Low |
| P2 | 12 | Move pandas import to module top-level | Low |
| P3 | 9,10 | Add return types and dict type params | Low |
| P3 | 13 | Deduplicate DataFrame construction | Low |
| P3 | 14,15 | Sanitize error messages and markdown strings | Low |
