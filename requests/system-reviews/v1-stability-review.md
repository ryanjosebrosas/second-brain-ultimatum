# System Stability Review — v1.0 Lockdown

**Date**: 2026-02-21
**Scope**: Full-system audit across all layers
**Purpose**: Identify stability gaps before declaring v1.0 stable
**Current State**: 1408 tests, 52 MCP tools, 12 agents, system running smoothly

---

## Overall Stability Score: 7/10

The system is **functionally stable** — happy paths work, agents produce correct output, tests catch regressions. The gaps are in **resilience under failure conditions**: missing timeouts, inconsistent error handling, and incomplete health checks. These don't cause problems today but would in production with intermittent network issues.

---

## Layer-by-Layer Findings

### 1. MCP Server (mcp_server.py) — Needs Work

**What's good:**
- 52 tools, well-organized
- Core agent tools (recall, ask, learn, create, review) have timeouts
- `_validate_mcp_input` and `_get_deps`/`_get_model` helpers are clean

**Gaps found:**

| Issue | Count | Severity | Details |
|-------|-------|----------|---------|
| Missing `asyncio.timeout` on service I/O | ~19 tools | HIGH | `search_examples`, `search_knowledge`, `delete_item`, `brain_health`, `graph_search`, `growth_report`, `list_content_types`, `manage_content_type`, `list_projects`, `search_experiences`, `search_patterns`, `ingest_example`, `ingest_knowledge`, `brain_setup`, `pattern_registry`, `save_template`, `list_templates`, `get_template`, and more |
| Missing `except Exception` fallback | 13 tools | HIGH | All agent-invoking tools catch `TimeoutError` but NOT general exceptions — model API errors escape to FastMCP |
| Missing `_validate_mcp_input` | 6 tools | MEDIUM | Entire graph tool family (`graph_search`, `graph_entity_search`, `graph_entity_context`, `graph_traverse`, `graph_communities`, `graph_advanced_search`) |
| Inconsistent timeout messages | 3 tools | LOW | `graph_traverse`, `graph_communities`, `graph_advanced_search` don't include timeout duration |

---

### 2. Service Layer — Needs Work

**What's good:**
- Memory service degrades gracefully (returns empty on failure)
- Storage service returns safe empty values on failure
- Voyage retry via `async_retry()` is well-designed
- Idle reconnect for Mem0 cloud client

**Gaps found:**

| Service | Retry | Timeout | Graceful Degradation |
|---------|-------|---------|---------------------|
| **Memory (Mem0)** | Partial — only `add`, `search`, `search_with_filters` | Partial — same 3 methods only | Yes — all methods return safe empty |
| **Storage (Supabase)** | None — 0 of ~40 methods | Partial — only bulk/vector methods | Yes — all methods return safe empty |
| **Voyage** | Yes — all methods via `async_retry` | No — none | No — exceptions propagate |
| **Embeddings** | Yes — via delegation to Voyage/OpenAI | No — none | Partial — Voyage→OpenAI fallback at startup only |

**Key risk**: ~35 Supabase methods and all Voyage calls have no timeout. A hung connection blocks indefinitely.

---

### 3. Agent Layer — Stable (1 minor gap)

**What's good:**
- 13/14 agents fully pattern-compliant
- All agents have output validators and retries=3
- All tools use `tool_error()` except one
- Clean, consistent architecture

**Single gap:**
- `pmo.py` → `get_scoring_weights` has no `try/except` or `tool_error()` wrapper

---

### 4. REST API — Needs Work (Medium)

**What's good:**
- `agents` router uses shared `_run_agent()` with full error handling
- `projects` router is solid with proper 404/500 mapping
- CORS properly configured (allowlist, not wildcard)
- Auth opt-in via `BRAIN_API_KEY` with `X-API-Key` header

**Gaps found:**

| Router | Issue | Severity |
|--------|-------|----------|
| `memory` | 6 GET endpoints have no try/except — raw 500s on storage failure | MEDIUM |
| `health` | Service endpoints (metrics, growth, milestones, quality, setup) have no try/except | MEDIUM |
| `settings` | Zero error handling in both endpoints | LOW |
| `templates` | `deconstruct` catches TimeoutError but not Exception (doesn't use `_run_agent`) | MEDIUM |
| `health/ready` | Only checks Python init, not live service connectivity | MEDIUM |
| `memory` | No upper bound on `limit` query param in search endpoints | LOW |

---

### 5. Test Coverage — Stable (minor gaps)

**What's good:**
- 1408 tests across 26 test files
- Every major subsystem has meaningful coverage
- Test count tracked per commit — discipline maintained

**Missing test files (4 modules):**

| Module | Risk | Reason |
|--------|------|--------|
| `agents/registry.py` | Medium | Routing dispatch — regression could misdirect agents |
| `services/retry.py` | Medium | Silent degradation if retry logic breaks |
| `services/abstract.py` | Low | Base classes / interface contracts |
| `services/search_result.py` | Low | Data structures |

---

## Prioritized Fix List

### Phase 1: High-Impact Error Handling (Fastest wins)

1. **Add `except Exception` fallback to 13 agent-invoking MCP tools**
   - Pattern: after `except TimeoutError`, add `except Exception as e: return f"Error: {e}"`
   - Tools: `recall`, `ask`, `learn`, `create_content`, `review_content`, `consolidate_brain`, `coaching_session`, `prioritize_tasks`, `compose_email`, `ask_claude_specialist`, `analyze_clarity`, `synthesize_feedback`, `find_template_opportunities`
   - Est: ~30 min

2. **Add `asyncio.timeout` to 19 service-calling MCP tools**
   - Pattern: wrap service calls in `async with asyncio.timeout(timeout):`
   - Est: ~45 min

3. **Wrap `pmo.get_scoring_weights` in try/except + tool_error()**
   - Single tool, 2 lines
   - Est: 5 min

### Phase 2: REST API Consistency

4. **Add try/except to memory GET endpoints, health service endpoints, settings endpoints**
   - ~12 endpoints need wrapping
   - Est: ~30 min

5. **Use `_run_agent()` wrapper for templates/deconstruct**
   - Or replicate the pattern inline
   - Est: 10 min

6. **Add upper-bound validation to `limit` query params**
   - `Query(ge=1, le=100)` on search endpoints
   - Est: 10 min

### Phase 3: Service Layer Resilience

7. **Add timeout to remaining Memory service methods**
   - `add_with_metadata`, `add_multimodal`, `update_memory`, `get_all`, `delete`, `delete_all`, `get_by_id`
   - Est: ~20 min

8. **Add timeout to Voyage/Embeddings service calls**
   - Wrap in `asyncio.timeout()` around the retry calls
   - Est: ~15 min

9. **Add `_validate_mcp_input` to graph tool family**
   - 6 tools, mechanical
   - Est: 15 min

### Phase 4: Health & Observability

10. **Add Voyage + LLM provider checks to health service**
    - `compute()` should ping Voyage embed endpoint and LLM provider
    - Est: ~20 min

11. **Enhance `/ready` to do live dependency checks**
    - Ping Mem0, Supabase, Voyage with fast queries
    - Est: ~20 min

### Phase 5: Test Gaps

12. **Add `test_registry.py`** — agent registry routing
13. **Add `test_retry.py`** — retry count, backoff, re-raise
14. **Add tests for `abstract.py` and `search_result.py`**

---

## What's NOT Needed

- No new features
- No architectural changes
- No refactoring
- No new dependencies
- No breaking changes

This is purely about **applying existing patterns consistently** across the codebase.

---

## Recommendation

Phases 1-2 are the highest ROI — they're mechanical pattern application (copy the error handling from tools that have it to tools that don't). Phases 3-5 are good-to-have. All of this can be done in 1-2 sessions without touching any business logic.

After this, commit as `fix(stability): v1.0 hardening — consistent error handling, timeouts, health checks` and declare the system stable.
