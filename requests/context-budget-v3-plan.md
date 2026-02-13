# Feature: Context Budget Optimization v3

## Feature Description

Comprehensive token audit and optimization targeting the 51k token overhead observed after `/prime`. The system uses 25% of the 200k context window before any real work begins. This plan reduces that to ~36-38k (18-19%) through three optimization layers: MCP Tool Search, /prime command rewrite, and auto-loaded file compression.

## User Story

As a developer using My Coding System, I want priming to use fewer tokens, so that I have more context window available for implementation work.

## Problem Statement

After running `/prime`, the session consumes 51k/200k tokens (25%). Breakdown:
- System prompt + tools: 24.3k (12.2%) — **FIXED, cannot change**
- MCP tools: 6.7k (3.3%) — 16 Archon tools loaded upfront
- Skills: 841 (0.4%) — 26 skill descriptions
- Custom agents: 349 (0.2%) — 8 agent descriptions
- Memory files: 1.9k (1.0%) — CLAUDE.md + 6 sections + MEMORY.md
- Messages (priming): 16.8k (8.4%) — /prime conversation cost

The 26.7k of controllable overhead (MCP + skills + agents + memory + priming) can be reduced by ~13-15k tokens.

## Solution Statement

Three-phase optimization:
- **Phase 1**: Enable MCP Tool Search to lazy-load Archon tools (save ~5-6k)
- **Phase 2**: Rewrite /prime to eliminate waste (save ~6-8k)
- **Phase 3**: Compress auto-loaded sections (save ~449)
- Decision: Preserve all functionality — no features removed, only overhead reduced
- Decision: Skills and agents left as-is (1.2k combined is already minimal)

## Feature Metadata

- **Feature Type**: Enhancement / Refactor
- **Estimated Complexity**: Medium
- **Primary Systems Affected**: `.claude/commands/prime.md`, `sections/*.md`, `CLAUDE.md`, `.claude/settings.local.json`
- **Dependencies**: None (pure documentation/config changes)

---

## CONTEXT REFERENCES

### Relevant Codebase Files

> IMPORTANT: The execution agent MUST read these files before implementing!

- `.claude/commands/prime.md` (lines 1-133) — Why: primary optimization target, the /prime command
- `CLAUDE.md` (lines 1-56) — Why: auto-loaded index, compression target
- `sections/01_core_principles.md` (lines 1-21) — Why: compression candidate (-68 tokens)
- `sections/02_piv_loop.md` (lines 1-39) — Why: most verbose section, biggest compression (-120 tokens)
- `sections/03_context_engineering.md` (lines 1-11) — Why: compression candidate (-41 tokens)
- `sections/04_git_save_points.md` (lines 1-14) — Why: compression candidate (-24 tokens)
- `sections/05_decision_framework.md` (lines 1-16) — Why: compression candidate (-27 tokens)
- `sections/15_archon_workflow.md` (lines 1-6) — Why: compression candidate (-17 tokens)
- `.claude/settings.local.json` (lines 1-147) — Why: env config for Tool Search

### New Files to Create

- None — all changes are modifications to existing files

### Related Memories (from memory.md)

- Memory: "Slimmed CLAUDE.md by moving sections 06-14 to reference/ — Saves ~12,000 tokens per session" — Relevance: previous optimization round; this is v3
- Memory: "Token efficiency: compressed 5 commands (43-59%)" — Relevance: established compression approach
- Memory: "Agent `instance` field silently ignored" — Relevance: confirms agents are already minimal

### Relevant Documentation

- [Claude Code MCP Documentation](https://code.claude.com/docs/en/mcp)
  - Specific section: Tool Search configuration
  - Why: `ENABLE_TOOL_SEARCH` env var controls lazy loading of MCP tools
- [Optimising MCP Server Context Usage](https://scottspence.com/posts/optimising-mcp-server-context-usage-in-claude-code)
  - Specific section: Consolidation strategies
  - Why: real-world example of 60% MCP token reduction

### Patterns to Follow

**Section Compression Pattern** (from previous v1/v2 optimization):
```
BEFORE (verbose):
1. **YAGNI** (You Aren't Gonna Need It)
   - Only implement what's needed right now
   - No premature optimization or future-proofing

AFTER (compressed):
**YAGNI** — Only implement what's needed. No premature optimization.
```
- Why this pattern: preserves semantic meaning while cutting tokens 22-28%
- Common gotchas: don't lose critical policy statements during compression

**Prime Command Pattern** (from current prime.md):
```
### 2. Read Core Documentation
- Read project rules: @CLAUDE.md            ← DUPLICATE (already auto-loaded)
- read the section files referenced           ← DUPLICATE (already auto-loaded)
```
- Why this pattern: identifies waste from reading auto-loaded content again
- Common gotchas: some projects DON'T have CLAUDE.md auto-loaded, so the prime command was designed generically

---

## IMPLEMENTATION PLAN

### Phase 1: MCP Tool Search Configuration

Enable Tool Search to lazy-load Archon's 16 MCP tools. Currently all 6.7k tokens load upfront. With Tool Search, only a search index loads (~0.5-1k), and individual tools load on-demand.

**Tasks:**
- Add `ENABLE_TOOL_SEARCH` to settings env
- Verify Tool Search activates for Archon tools

### Phase 2: /prime Command Rewrite

The /prime command currently costs ~16.8k tokens in Messages. Major waste sources:
1. Duplicate reads of auto-loaded files (CLAUDE.md + sections) = ~1k wasted
2. Unbounded `git ls-files` output (~100 files) = ~1.5k wasted
3. Full README.md read (176 lines, mostly non-operational) = ~0.8k wasted
4. Full AGENTS.md read (279 lines, mostly style guides) = ~0.4k wasted
5. Archon RAG source listing (10 sources with summaries) = ~1.5k wasted
6. Verbose output report (12 sections) = ~0.8k wasted

**Tasks:**
- Remove duplicate reads of auto-loaded content
- Replace `git ls-files` with `git ls-files | head -50` or tree-style summary
- Make file reads selective (skip non-operational sections)
- Make Archon calls conditional and lighter
- Compact the output report format

### Phase 3: Auto-Loaded File Compression

Compress 8 auto-loaded files from ~1,914 tokens to ~1,465 tokens (-449, -23%). All essential rules preserved — only narrative bloat removed.

**Tasks:**
- Compress each section file
- Compress CLAUDE.md index

### Phase 4: Validation

Run /prime + /context and compare before/after token usage.

---

## STEP-BY-STEP TASKS

> Execute every task in order, top to bottom. Each task is atomic and independently testable.

### UPDATE `.claude/settings.local.json`

- **IMPLEMENT**: Add `"ENABLE_TOOL_SEARCH": "true"` to the `env` object. This enables MCP Tool Search for all MCP servers (Archon). With Tool Search, tool descriptions are replaced by a compact search index, and full tool definitions load only when needed.
- **PATTERN**: Current env section at line 2-4 has `"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"`. Add the new key alongside it.
- **IMPORTS**: N/A (JSON config)
- **GOTCHA**: Tool Search requires Sonnet 4+ or Opus 4+ (user is on Opus 4.6, so this works). If Tool Search doesn't activate, try `"auto:3"` instead of `"true"`. After changing settings, restart Claude Code for env changes to take effect.
- **VALIDATE**: Restart Claude Code, run `/context`, verify MCP tools section shows reduced token count (target: <2k instead of 6.7k)

### UPDATE `.claude/commands/prime.md`

- **IMPLEMENT**: Rewrite the /prime command to eliminate token waste. The new version should:

  **Section 1 — Analyze Project Structure** (replace git ls-files):
  ```markdown
  ### 1. Analyze Project Structure

  Scan the project using Glob patterns, NOT `git ls-files`:
  - `**/*.{py,ts,js,tsx,jsx,go,rs}` — source code entry points
  - `**/package.json`, `**/pyproject.toml`, `**/Cargo.toml` — config files
  - `**/README.md` — documentation

  For each match, note the file but do NOT read it yet. Build a mental map of the project.
  ```

  **Section 2 — Read Core Documentation** (remove duplicates):
  ```markdown
  ### 2. Read Core Documentation

  > CLAUDE.md and sections/ are ALREADY auto-loaded. Do NOT re-read them.

  Read ONLY files that are NOT auto-loaded:
  - `memory.md` (if exists) — cross-session context
  - Main entry points identified in Step 1 (main.py, index.ts, etc.)
  - Core config files (package.json, pyproject.toml, etc.)

  Skip: README.md (use git log + file structure to understand the project instead)
  Skip: AGENTS.md (loaded by Claude Code separately)
  ```

  **Section 3 — Identify Key Files** (keep as-is but limit reads):
  ```markdown
  ### 3. Identify Key Files

  Based on the structure, identify (but only read if NOT auto-loaded):
  - Main entry points
  - Core configuration files
  - Key model/schema definitions

  Limit: Read at most 5 files total. Prioritize by importance.
  ```

  **Section 4 — Current State** (keep, already efficient):
  ```markdown
  ### 4. Understand Current State

  Check recent activity:
  !`git log -10 --oneline`

  Check current branch and status:
  !`git status`
  ```

  **Section 5 — Archon Integration** (make conditional, lighter):
  ```markdown
  ### 5. Surface Active Tasks (if Archon available)

  Query for in-progress tasks ONLY:
  1. `find_tasks(filter_by="status", filter_value="doing")`
  2. Display as compact list: `[project] task title (status)`

  Skip: todo tasks (user knows their backlog)
  Skip: Archon RAG source listing (not needed for priming)
  Skip: Archon RAG search queries (save for /planning)
  ```

  **Section 6 — Output Report** (compact format):
  ```markdown
  ## Output Report

  Provide a CONCISE summary (aim for 20-30 lines max):

  ### Project Overview
  - Type, tech stack, current state (3-5 bullets)

  ### Architecture
  - Key directories and patterns (3-5 bullets)

  ### Current State
  - Branch, recent commits, git status summary

  ### Memory Context
  - Key decisions and gotchas from memory.md (3-5 bullets)
  - Memory health: last session date + staleness warning if >7 days

  ### Active Tasks
  - Archon doing tasks (or "No active tasks")

  **Keep it SHORT. The user will ask for details if needed.**
  ```

- **PATTERN**: Current prime.md at `.claude/commands/prime.md:1-133` — rewrite entirely
- **IMPORTS**: N/A (markdown command)
- **GOTCHA**: The `!` prefix in command files executes shell commands and embeds output. `!git ls-files` is the biggest offender (~1.5k tokens for 100 files). The new version replaces it with Glob patterns that the AI uses interactively (cheaper, more targeted). Also: the new /prime must work for ANY project, not just this one — keep it generic enough that entry point detection works across tech stacks.
- **VALIDATE**: `wc -l .claude/commands/prime.md` — target: 60-80 lines (down from 133). Then run `/prime` in a new conversation and check token cost with `/context`.

### UPDATE `sections/02_piv_loop.md`

- **IMPLEMENT**: Compress from ~540 tokens to ~420 tokens. Replace:
  ```markdown
  ### Granularity Principle

  Always do **smaller iterations**. Multiple small PIV loops, never try to implement everything at once. Each loop picks ONE feature slice and builds it completely before moving on.

  For complex features (High complexity, 15+ tasks, 4+ phases), `/planning` automatically decomposes into multiple sub-plans — each executable in a fresh conversation with minimal context overhead. See `templates/PLAN-OVERVIEW-TEMPLATE.md` for the decomposed plan structure.
  ```
  With:
  ```markdown
  ### Granularity Principle

  Multiple small PIV loops — one feature slice per loop, built completely before moving on.
  Complex features (15+ tasks, 4+ phases): `/planning` auto-decomposes into sub-plans.
  ```

  Replace the Layer 1 section:
  ```markdown
  **Layer 1 — Project Planning** (done once, updated rarely):
  - **PRD** — defines **what** to build. Use template: `templates/PRD-TEMPLATE.md`
  - **CLAUDE.md** — defines **how** to build (tech stack, conventions, patterns)
  - **On-demand context** — reference guides, external docs (in `reference/`)
  ```
  With:
  ```markdown
  **Layer 1 — Project Planning** (done once):
  - PRD (what to build), CLAUDE.md (how to build), reference guides (on-demand)
  ```

  Replace the Implementation section:
  ```markdown
  ### Implementation
  - Start a **new conversation** (fresh context)
  - Feed ONLY the structured plan: `/execute requests/{feature}-plan.md`
  - Or use prompt: `templates/IMPLEMENTATION-PROMPT.md` (for non-Claude Code tools)
  - Trust but verify: watch loosely, don't micromanage
  ```
  With:
  ```markdown
  ### Implementation
  - Fresh conversation → `/execute requests/{feature}-plan.md`
  - Trust but verify
  ```

  Replace the Validation section:
  ```markdown
  ### Validation
  - **AI validates**: unit tests, integration tests, linting
  - **Human validates**: code review (git diffs), questions, manual testing
  - Use checklist: `templates/VALIDATION-PROMPT.md`
  - Small issues: one-off fix prompts
  - Major issues: revert to git save point, tweak plan, retry
  ```
  With:
  ```markdown
  ### Validation
  - AI: tests + linting. Human: code review + manual testing.
  - Small issues → fix prompts. Major issues → revert to save point, tweak plan, retry.
  ```

  Keep the `Do NOT take your PRD and use it as a structured plan` warning — it's a critical policy.

- **PATTERN**: Compression pattern from v1/v2 optimization — preserve policy statements, cut narrative
- **IMPORTS**: N/A
- **GOTCHA**: Don't remove the plan decomposition mention or the template references — they're needed for `/planning` to know when to trigger series mode. Keep the `<!-- PLAN-SERIES -->` concept referenced.
- **VALIDATE**: `wc -w sections/02_piv_loop.md` — target: ~250 words (down from ~385)

### UPDATE `sections/01_core_principles.md`

- **IMPLEMENT**: Compress from ~248 tokens to ~180 tokens. Replace numbered multi-line format with single-line format:
  ```markdown
  **YAGNI** — Only implement what's needed. No premature optimization.
  **KISS** — Prefer simple, readable solutions over clever abstractions.
  **DRY** — Extract common patterns; balance with YAGNI.
  **Limit AI Assumptions** — Be explicit in plans and prompts. Less guessing = better output.
  **Always Be Priming (ABP)** — Start every session with `/prime`. Context is everything.
  ```
- **PATTERN**: Dense single-line format from other compressed sections
- **IMPORTS**: N/A
- **GOTCHA**: The ABP principle's sub-bullets ("Before any task: Does the AI know the codebase?") are helpful but cost tokens. The compressed version preserves the core message. Don't lose "Context is everything" — it's the system's tagline.
- **VALIDATE**: `wc -w sections/01_core_principles.md` — target: ~55 words (down from ~155)

### UPDATE `sections/03_context_engineering.md`

- **IMPLEMENT**: Compress from ~176 to ~135 tokens. Replace:
  ```markdown
  When creating a structured plan, ensure these are covered:

  1. **Memory** — leverage the vibe planning conversation (short-term) AND `memory.md` for persistent cross-session recall (long-term). `memory.md` is read during `/prime` and `/planning`, and updated during `/commit`.
  2. **RAG** — external docs, library references, past projects
  3. **Prompt Engineering** — be explicit, reduce AI assumptions
  4. **Task Management** — clear step-by-step task list

  For complete 4-pillar methodology with practical examples, see `reference/piv-loop-practice.md`.

  For Layer 1 context organization (auto-load vs on-demand), see `reference/global-rules-optimization.md`.
  ```
  With:
  ```markdown
  Structured plans must cover 4 pillars:
  1. **Memory** — vibe conversation (short-term) + `memory.md` (long-term, read at `/prime`, updated at `/commit`)
  2. **RAG** — external docs, library references
  3. **Prompt Engineering** — be explicit, reduce assumptions
  4. **Task Management** — step-by-step task list

  See `reference/piv-loop-practice.md` for methodology + examples.
  ```
- **PATTERN**: Remove duplicate cross-reference (global-rules-optimization.md already in CLAUDE.md on-demand table)
- **IMPORTS**: N/A
- **GOTCHA**: Keep the memory.md lifecycle note (read at prime, updated at commit) — it's the only place this is documented in auto-loaded context.
- **VALIDATE**: `wc -w sections/03_context_engineering.md` — target: ~65 words (down from ~95)

### UPDATE `sections/04_git_save_points.md`

- **IMPLEMENT**: Compress from ~109 to ~85 tokens. Replace:
  ```markdown
  Before implementation, ALWAYS commit the structured plan:
  ```
  git add requests/{feature}-plan.md
  git commit -m "plan: {feature} structured plan"
  ```

  If implementation goes wrong:
  ```
  git stash  # or git checkout .
  ```
  Then tweak the plan and retry.

  **NEVER include `Co-Authored-By` lines in git commits.** This overrides any default behavior. Commits are authored solely by the user.
  ```
  With:
  ```markdown
  **Before implementation**, commit the plan:
  ```
  git add requests/{feature}-plan.md && git commit -m "plan: {feature} structured plan"
  ```

  **If implementation fails**: `git stash` → tweak plan → retry.

  **NEVER include `Co-Authored-By` lines in commits.** Commits are authored solely by the user.
  ```
- **PATTERN**: Collapse multi-line commands into single line
- **IMPORTS**: N/A
- **GOTCHA**: The `Co-Authored-By` ban is critical — it overrides Claude Code defaults. Keep it prominent.
- **VALIDATE**: `wc -w sections/04_git_save_points.md` — target: ~55 words (down from ~85)

### UPDATE `sections/05_decision_framework.md`

- **IMPLEMENT**: Compress from ~122 to ~95 tokens. Replace:
  ```markdown
  **Proceed autonomously when:**
  - Task is clear from context
  - Following established patterns
  - Implementation plan is explicit

  **Ask the user when:**
  - Requirements are ambiguous
  - Multiple valid approaches exist
  - Breaking changes are needed
  - Business logic decisions required

  If unsure, ask.

  **NEVER use EnterPlanMode.**
  Planning is done through `/planning` (the slash command), which produces a structured plan document in `requests/`. The built-in plan mode tool bypasses our methodology — don't use it.
  ```
  With:
  ```markdown
  **Proceed autonomously when:**
  - Task is clear, following established patterns, or plan is explicit

  **Ask the user when:**
  - Requirements ambiguous, multiple approaches, breaking changes, or business logic decisions

  **NEVER use EnterPlanMode.** Use `/planning` command instead — it produces structured plans in `requests/`.
  ```
- **PATTERN**: Merge related bullets into single lines
- **IMPORTS**: N/A
- **GOTCHA**: "If unsure, ask" is redundant with the "Ask the user when" section — safe to remove. Keep the EnterPlanMode ban as a one-liner.
- **VALIDATE**: `wc -w sections/05_decision_framework.md` — target: ~55 words (down from ~105)

### UPDATE `sections/15_archon_workflow.md`

- **IMPLEMENT**: Compress from ~77 to ~60 tokens. Replace:
  ```markdown
  # Archon Integration

  > Task management and RAG search are handled via Archon MCP server.
  > Load `reference/archon-workflow.md` when using `/execute`, `/planning`, or task management.
  > Key rule: ALWAYS use Archon MCP tools for task management (never TodoWrite).
  ```
  With:
  ```markdown
  Archon MCP handles task management + RAG search. Load `reference/archon-workflow.md` for `/execute`, `/planning`, or task work.

  **Always use Archon MCP tools** for task management (never TodoWrite).
  ```
- **PATTERN**: Remove heading (CLAUDE.md already has the "## Archon Workflow" heading); collapse blockquotes to prose
- **IMPORTS**: N/A
- **GOTCHA**: Keep "never TodoWrite" — it overrides Claude Code's default behavior.
- **VALIDATE**: `wc -w sections/15_archon_workflow.md` — target: ~30 words (down from ~52)

### UPDATE `CLAUDE.md`

- **IMPLEMENT**: Compress the on-demand guides table by shortening descriptions and removing `reference/` prefix repetition. Replace:
  ```markdown
  | Guide | Load when... |
  |-------|-------------|
  | `reference/layer1-guide.md` | Setting up CLAUDE.md for a new project |
  | `reference/validation-strategy.md` | Planning or running validation |
  | `reference/file-structure.md` | Looking up where files belong |
  | `reference/command-design-overview.md` | Designing or modifying slash commands |
  | `reference/github-integration.md` | Setting up GitHub Actions or CodeRabbit |
  | `reference/remote-system-overview.md` | Deploying or using the remote coding agent |
  | `reference/mcp-skills-overview.md` | Configuring MCP servers or creating skills |
  | `reference/subagents-overview.md` | Creating or debugging subagents |
  | `reference/archon-workflow.md` | Using Archon task management or RAG search |
  | `reference/git-worktrees-overview.md` | Parallel feature implementation with worktrees |
  | `reference/agent-teams-overview.md` | Using Agent Teams, `/team` command, contract-first spawning |
  ```
  With:
  ```markdown
  > All guides in `reference/`. Load when the task requires it.

  | Guide | When |
  |-------|------|
  | `layer1-guide` | New project CLAUDE.md setup |
  | `validation-strategy` | Validation planning |
  | `file-structure` | File location lookup |
  | `command-design-overview` | Slash command design |
  | `github-integration` | GitHub Actions / CodeRabbit |
  | `remote-system-overview` | Remote coding agent |
  | `mcp-skills-overview` | MCP servers / skills |
  | `subagents-overview` | Subagent creation |
  | `archon-workflow` | Archon tasks / RAG |
  | `git-worktrees-overview` | Parallel worktree implementation |
  | `agent-teams-overview` | Agent Teams / `/team` |
  ```
  Also shorten the intro line and remove the footer note about `reference/` since the new note at top covers it.
- **PATTERN**: Prefix note replaces per-row repetition of `reference/`
- **IMPORTS**: N/A
- **GOTCHA**: The `@sections/` references MUST stay exactly as they are — Claude Code uses `@` syntax for auto-loading. Don't change section references.
- **VALIDATE**: `wc -w CLAUDE.md` — target: ~230 words (down from ~340)

---

## TESTING STRATEGY

### Unit Tests

N/A — documentation project, no automated tests.

### Integration Tests

1. **Token cost verification**: Run `/prime` in a fresh conversation, then `/context` to measure
2. **MCP Tool Search verification**: Check that `/context` shows MCP tools at <2k tokens
3. **Functionality preservation**: Verify `/prime` still produces a useful project summary

### Edge Cases

- MCP Tool Search might not activate if Archon connection fails — /prime should still work
- New projects with no `memory.md` — /prime skips gracefully (already handled)
- Projects with 500+ files — new Glob approach is more targeted than `git ls-files`

---

## VALIDATION COMMANDS

### Level 1: Syntax & Style
```
# Verify all modified files exist and are valid markdown
for f in .claude/commands/prime.md sections/01_core_principles.md sections/02_piv_loop.md sections/03_context_engineering.md sections/04_git_save_points.md sections/05_decision_framework.md sections/15_archon_workflow.md CLAUDE.md .claude/settings.local.json; do test -f "$f" && echo "OK: $f" || echo "MISSING: $f"; done
```

### Level 2: Word Count Verification
```
echo "=== Word counts (targets) ==="
echo "prime.md (target: 400-500 words):" && wc -w .claude/commands/prime.md
echo "02_piv_loop (target: ~250 words):" && wc -w sections/02_piv_loop.md
echo "01_core_principles (target: ~55 words):" && wc -w sections/01_core_principles.md
echo "CLAUDE.md (target: ~230 words):" && wc -w CLAUDE.md
```

### Level 3: Integration Tests
```
# Start fresh conversation, run /prime, then /context
# Compare before/after:
# BEFORE: 51k total, MCP 6.7k, Messages 16.8k
# TARGET: ~36-38k total, MCP <2k, Messages ~8-10k
```

### Level 4: Manual Validation

1. Run `/prime` in a fresh conversation — verify it still produces a useful summary
2. Run `/context` — verify total tokens decreased by 13-15k
3. Test that Archon MCP tools still work (e.g., `find_tasks`)
4. Verify Tool Search lazy-loads tools correctly (first Archon call may have slight delay)

---

## ACCEPTANCE CRITERIA

- [ ] Total session cost after /prime reduced from 51k to ≤40k tokens
- [ ] MCP tools section reduced from 6.7k to <2k tokens (via Tool Search)
- [ ] /prime Messages cost reduced from 16.8k to ≤10k tokens
- [ ] All auto-loaded sections compressed (total memory files ≤1.5k tokens)
- [ ] /prime still produces useful project summary in any project
- [ ] Archon MCP tools still functional (task queries, RAG search work)
- [ ] No features or policy rules lost during compression

---

## COMPLETION CHECKLIST

- [ ] MCP Tool Search enabled in settings
- [ ] /prime command rewritten (60-80 lines)
- [ ] All 7 section files compressed
- [ ] CLAUDE.md on-demand table compressed
- [ ] Fresh /prime + /context validates savings
- [ ] memory.md updated with session note

---

## NOTES

### Key Design Decisions
- **Tool Search over tool removal**: Rather than removing Archon tools, lazy-load all of them. This preserves full functionality while saving ~5k tokens.
- **/prime as Glob-based not git-based**: Replacing `git ls-files` with Glob patterns makes /prime more targeted and cheaper. The AI uses Glob interactively (reading file matches) instead of processing a dump of 100+ file paths.
- **Sections compressed, not removed**: All 6 sections remain auto-loaded. The content is the same, just denser. No policy rules lost.

### Risks
- **Tool Search not activating**: If `ENABLE_TOOL_SEARCH` doesn't work in settings.local.json env, may need to configure at MCP server level or use a different config path. Mitigation: test immediately, fall back to `"auto:3"` threshold setting.
- **Over-compressed sections losing clarity**: The compressed sections are tighter. New users reading them might find them less explanatory. Mitigation: reference guides exist for deep explanation.

### Security Note
- `.claude/settings.local.json` line 85 contains what appears to be an OAuth token in a permission entry. Consider removing this line during the settings update.

### Confidence Score: 8/10
- **Strengths**: Token waste is clearly identified with precise estimates. All changes are reversible. No functional changes — pure overhead reduction.
- **Uncertainties**: MCP Tool Search exact config syntax may need testing. Actual token savings depend on Claude Code's tokenizer (estimates are ±10%).
- **Mitigations**: Phase-by-phase validation. If Tool Search doesn't work, /prime optimization alone still saves 6-8k tokens.
