# System Review: Agent Search Resilience

**Plan**: `requests/agent-search-resilience-plan.md`
**Execution Report**: `requests/execution-reports/agent-search-resilience-report.md`
**Implementation Commit**: `1a49eca`

---

### Overall Alignment Score: 9/10

Near-perfect plan adherence. One justified divergence (updating existing tests that asserted old broken behavior) and one undocumented divergence (bundled unrelated `test_models_sdk.py` fix into the commit). No problematic divergences. The plan's quality directly enabled one-pass implementation with 14 new tests and 0 failures.

---

### Divergence Analysis

```
divergence: Updated 4 existing tests that asserted old broken behavior
planned: Plan mentioned "update all tests that call validators[0].validate() with the old schema" in Related Memories, and GOTCHA sections warned about existing tests, but no explicit task was created for updating existing tests
actual: Executor renamed/updated test_recall_search_patterns_requests_graph → test_recall_search_patterns_no_enable_graph, test_create_find_patterns_requests_graph → test_create_find_patterns_no_enable_graph, updated test_search_cloud_no_top_level_user_id (removed version assertion), flipped test_get_all_cloud_no_top_level_user_id → test_get_all_cloud_uses_top_level_user_id
reason: Existing tests asserted the OLD broken behavior — without updating, the suite would fail
classification: good
justified: yes
root_cause: Plan mentioned the gotcha but didn't create explicit tasks for updating existing tests
```

```
divergence: Bundled unrelated test_models_sdk.py fix into the implementation commit
planned: Not mentioned anywhere in the plan — test_models_sdk.py is not in the plan's affected files list
actual: 3 test cases in TestClaudeSDKModelStructuredOutput received additional mock for claude_agent_sdk._errors module (21 lines changed)
reason: File was already modified in working tree before execution (visible in session git status). Executor bundled it into the commit rather than separating it.
classification: bad (minor)
justified: partially — the fix itself is fine, but it should have been either (a) committed separately before execution, or (b) documented in the execution report as an out-of-scope change
root_cause: No execute command guidance for handling pre-existing dirty state
```

---

### Pattern Compliance

- Followed codebase architecture: **yes** — all changes fit existing layered architecture, error bypass pattern mirrors recall/ask precedent
- Used documented patterns (from CLAUDE.md): **yes** — `tool_error()` pattern, validator bypass, protected `@agent.instructions`, schema conventions
- Applied testing patterns correctly: **yes** — one test file per source module, used existing fixtures and `validator.function()` call pattern
- Met validation requirements: **yes** — all 5 validation levels passed, 1452 tests (14 new), 0 failures

---

### Plan Quality Assessment

**Strengths (worth preserving)**:
1. **Root cause + safety net dual approach** — fixing the bug AND adding resilience. This prevented a "fix the symptom" anti-pattern.
2. **Exact line numbers and code snippets** — executor had copy-paste ready diffs for every task. This is why one-pass implementation worked.
3. **Patterns to Follow section** — including actual code from RecallResult/AskResult gave the executor a concrete reference, not just a description.
4. **GOTCHA fields on every task** — the "don't remove keyword_search kwarg" and "existing tests may break" warnings prevented mistakes.
5. **1015 lines** — exceeded the 700-line minimum. The depth justified itself in execution quality.

**Weaknesses (worth addressing)**:
1. **Existing test updates not tasked** — the plan warned about existing tests in GOTCHAs but didn't create Tasks 17-20 for updating them. This forced the executor to improvise.
2. **No pre-execution cleanup step** — the dirty `test_models_sdk.py` state was visible in git status but the executor had no guidance on whether to commit it separately.

---

### System Improvement Actions

**Update CLAUDE.md:**
- No changes needed. The error bypass pattern, validator conventions, and `tool_error()` pattern are already well-documented. The execution proved the existing documentation is sufficient.

**Update Plan Command (`planning.md`)**:
- **Add guidance for "assertion inversion" tasks**: When a plan removes or changes behavior that existing tests assert, Phase 5 should generate explicit tasks for updating those tests — not just mention it in GOTCHAs. Suggested addition to Phase 5 instructions:

  > When a task removes a kwarg, changes a function signature, or alters behavior, check if existing tests assert the OLD behavior. If so, create an explicit UPDATE task for each affected test (don't just mention it in GOTCHA — make it a task).

**Update Execute Command (`execute.md`)**:
- **Add pre-execution dirty state check**: Between Step 1 (Read plan) and Step 2 (Execute tasks), add:

  > **Step 1.75: Clean Working Tree Check**
  > Run `git status`. If there are uncommitted changes unrelated to the plan, warn the user and suggest committing or stashing them before proceeding. Do NOT bundle unrelated changes into the implementation commit.

**Create New Command:**
- None needed. No manual process was repeated 3+ times.

---

### Key Learnings

**What worked well:**
- The plan's dual "root cause + safety net" strategy is the gold standard for resilience work. Both prongs were necessary — the root cause fix alone wouldn't protect against future service outages, and the safety nets alone wouldn't fix the 400 errors.
- The 7-field task format (ACTION/TARGET/IMPLEMENT/PATTERN/IMPORTS/GOTCHA/VALIDATE) delivered on its promise: the executor followed tasks top-to-bottom without backtracking.
- Confidence score 9/10 was accurate — execution matched almost exactly.
- Test count discipline (1428 → 1452) provides a clear audit trail.

**What needs improvement:**
- **Test update tasks must be explicit, not implicit.** The pattern of "mention it in GOTCHA, hope the executor handles it" works when the executor is experienced, but would fail for a weaker model or a fresh conversation with less context. The plan should have had Tasks 17-19 for updating the 4 existing tests.
- **Pre-execution state hygiene.** The execute command should enforce a clean working tree or at minimum document any pre-existing changes. Bundling `test_models_sdk.py` into the commit is a minor hygiene issue but could be worse with larger unrelated changes.

**Concrete improvements for next implementation:**
1. Planning: When removing/changing kwargs or behavior, create explicit "update existing test" tasks (not just GOTCHAs)
2. Execution: Add a `git status` check at the start; warn about unrelated dirty files
