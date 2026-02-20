# System Review: Content Writer Voice Fix

## Overall Alignment Score: 9/10

Near-perfect plan adherence. Zero divergences reported. All 12 tasks completed in order, all validation levels passed, test count increased from 998 to 1004. The only deductions are for two residual inconsistencies the plan explicitly acknowledged but scoped out — one of which (CLI `--mode` param) is a real gap that could cause a runtime error.

---

## Divergence Analysis

The execution report states: "None — implementation matched plan exactly."

Verified by cross-referencing the plan's 12 step-by-step tasks against the code changes. Every task was implemented as specified. No shortcuts, no architectural deviations, no skipped validation steps.

**However**, two residual issues were flagged in the report's "Issues & Notes" section. These aren't divergences from plan (the plan acknowledged them as out-of-scope), but they represent incomplete scope in the *plan itself*:

### Residual Issue 1: CLI `--mode` parameter not updated

```
issue: CLI `brain create --mode` still accepts and forwards a `mode` parameter
impact: HIGH — the CLI create command at cli.py:180 builds an enhanced prompt with
        "Communication mode: {effective_mode}" and the old rigid "Target length: ~N words"
        format. This is the exact pattern the fix was meant to eliminate.
root_cause: Plan scoped CLI out ("not in scope of this plan")
classification: Plan scoping gap
recommendation: Should have been Task 5b — the CLI `create` command duplicates
                the exact MCP logic that was fixed. Same pre-loading pattern needed.
```

### Residual Issue 2: `inject_content_types` stale references

```
issue: Dynamic instructions at create.py:68 still show "max {ct.max_words} words,
       mode: {ct.default_mode}" for each content type
impact: LOW — the MCP layer's enhanced prompt overrides this with specific voice/length
        context, but it sends a mixed signal to the agent (old rigid framing alongside
        new flexible framing)
root_cause: Plan acknowledged but deprioritized ("low priority... could be cleaned up
            in a follow-up")
classification: Acceptable deferral
recommendation: Quick follow-up task — change the type list line to use length_guidance
                instead of max_words/mode
```

---

## Pattern Compliance

- **Followed codebase architecture**: yes — MCP layer -> agent -> service pattern maintained
- **Used documented patterns (from CLAUDE.md)**: yes — MCP tool pattern, agent definition pattern, error handling pattern, lazy import awareness
- **Applied testing patterns correctly**: yes — `_mock_deps()`, `@patch` decorators, `AsyncMock` for storage service calls
- **Met validation requirements**: yes — all 5 validation levels executed (syntax, unit, integration, full suite, manual noted as pending)

---

## Plan Quality Assessment

### What the plan did well

1. **Exact file:line references**: Every task cited specific line ranges in the codebase. The execution agent never needed to search — it could read directly.
2. **Code samples with gotchas**: Each task included a code block AND a GOTCHA section warning about specific pitfalls (e.g., "don't double-wrap async methods in asyncio.to_thread").
3. **Memory integration**: Plan referenced 4 specific gotchas from `memory.md` (StorageService async pattern, plan code sample errors, fastmcp test patterns, conftest mock requirements).
4. **Test strategy was comprehensive**: 6 new tests + 5 updated tests, covering pre-loading, fallback, and schema changes.
5. **Validation commands at every task level**: Each task had a VALIDATE step — not just the final validation section.

### What the plan missed

1. **CLI was not scoped in**: The CLI `brain create` command at `cli.py:172-214` duplicates the exact MCP `create_content` logic — same `mode` parameter, same rigid `"Target length: ~N words"`, same `"Communication mode: {effective_mode}"`. The plan's "Primary Systems Affected" listed `mcp_server.py` and `agents/create.py` but not `cli.py`. This means the CLI is now inconsistent with the MCP tool.

2. **No `service_mcp.py` check**: The plan's "Primary Systems Affected" didn't mention `service_mcp.py` (supplemental routing). If `create_content` is routed through `service_mcp.py`, the `mode` parameter removal could break that path too. (Verified: `service_mcp.py` does not route `create_content`, so this is a non-issue — but the plan should have verified.)

---

## System Improvement Actions

### Update CLAUDE.md

No changes needed. The existing patterns (MCP tool pattern, agent definition pattern, error handling) were followed correctly. The `length_guidance` field is a schema-level addition that doesn't warrant a CLAUDE.md update — it's domain-specific, not a universal pattern.

### Update Plan Command (`planning.md`)

**Add to Phase 2 (Codebase Intelligence) agent prompts:**

> When identifying files that need changes, also check for duplicate implementations of the same logic in other entry points (CLI commands, service bridges, API routes). If the MCP tool has a corresponding CLI command, both must be updated together.

This would have caught the CLI `--mode` gap. The current instruction says "Identify which existing files need changes" but doesn't explicitly prompt for parallel entry points.

### Update Execute Command (`execute.md`)

**Add to Step 5 (Final Verification):**

> - Verify no parallel entry points (CLI, service bridge) were left inconsistent with the MCP tool changes

This is a lightweight check that catches the CLI gap without requiring a full re-audit.

### Create New Command

No new commands needed. This was a clean single-plan execution. The only repeated manual step was the `_mock_deps()` + `AsyncMock` setup in each test, but that's test fixture boilerplate, not a command opportunity.

---

## Key Learnings

### What worked well

- **Plan precision eliminated guesswork**: Zero divergences because the plan specified exact code blocks, exact line numbers, and exact validation commands. The execution agent was a precise implementer, not a decision-maker.
- **Pre-loading pattern is clean**: Moving voice/examples from optional agent tools to MCP-layer injection is a solid architectural decision. It guarantees context without relying on LLM tool-calling behavior.
- **Test-first thinking in the plan**: The plan specified which existing tests would break and how to fix them. No surprise test failures during execution.
- **Memory gotchas prevented errors**: The plan's "Related Memories" section flagged `asyncio.to_thread` misuse, `.execute()` calling convention, and mock patterns — all common sources of bugs in this codebase.

### What needs improvement

- **Scope completeness for entry point changes**: When modifying an MCP tool's signature or behavior, the plan must audit ALL callers — not just the MCP layer. The CLI duplicated the exact logic being fixed and was left stale. This is a planning phase gap, not an execution gap.
- **Residual inconsistency tracking**: The plan acknowledged the CLI gap but dismissed it as "not in scope." A better approach: create a follow-up task in Archon during execution, so the gap is tracked rather than noted and forgotten.

### Concrete next step

Create a quick follow-up plan to:
1. Update `cli.py:172-214` to match the new `create_content` MCP behavior (remove `--mode`, add pre-loading, use `length_guidance`)
2. Update `inject_content_types` dynamic instructions to use `length_guidance` instead of `max_words`/`mode`

This is a ~30-minute task that completes the voice fix across all entry points.
