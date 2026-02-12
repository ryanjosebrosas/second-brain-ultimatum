# Feature: mem0 to memory.md Migration

## Feature Description

Replace all mem0 MCP server integration with a simple file-based memory system using `memory.md` at the project root. mem0 requires external infrastructure (API keys, cloud service), adds MCP token overhead, and isn't well-suited for coding context. A `memory.md` file is portable, version-controlled, human-readable, and works everywhere with zero setup.

## User Story

As a developer using the PIV Loop system, I want persistent cross-session memory stored in a simple markdown file, so that I don't need to set up external services for the AI to remember past decisions, patterns, and lessons.

## Problem Statement

mem0 is currently referenced across 9+ system files as the memory layer. Problems:
1. Requires external service setup (API key, cloud account) — friction for new users
2. Adds MCP token overhead (~100-200 tokens per query)
3. Vector search for coding context often returns irrelevant results
4. Not version-controlled — memory lives outside the repo
5. Not human-readable without the mem0 dashboard
6. Breaks in CI/CD environments (GitHub Actions, remote system)

## Solution Statement

- Decision 1: Replace mem0 with `memory.md` at project root — because it's zero-setup, version-controlled, and human-readable
- Decision 2: Use structured sections in memory.md (Decisions, Patterns, Gotchas, Lessons) — because structured content is easier for AI to parse than free-form notes
- Decision 3: Commands read/append to memory.md instead of calling mem0 MCP — because file I/O is simpler, faster, and doesn't require MCP server
- Decision 4: Keep the "Memory" pillar in Context Engineering but redefine it as file-based — because the concept is still valid, just the implementation changes

## Feature Metadata

- **Feature Type**: Refactor (replacing external dependency with simpler approach)
- **Estimated Complexity**: Medium
- **Primary Systems Affected**: sections/, .claude/commands/, reference/, templates/
- **Dependencies**: None (removing a dependency, not adding one)

---

## CONTEXT REFERENCES

### Relevant Codebase Files

- `sections/02_piv_loop.md` (lines 1-90) — Why: References mem0 in planning/commit workflow
- `sections/03_context_engineering.md` (lines 1-11) — Why: Lists mem0 as "Memory" pillar
- `reference/mcp-skills-overview.md` (lines 1-150+) — Why: Token cost analysis includes mem0
- `.claude/commands/planning.md` (lines 1-362) — Why: Phase 2c searches mem0 for past decisions
- `.claude/commands/commit.md` (lines 1-166) — Why: Step 6 stores learnings to mem0
- `.claude/commands/prime.md` (lines 1-108) — Why: Step 5 searches mem0 for project memories
- `.claude/commands/end-to-end-feature.md` (lines 1-148) — Why: May reference mem0 through chained commands
- `reference/piv-loop-practice.md` (lines 274-359) — Why: 4 Pillars section details mem0 as Memory pillar
- `reference/mcp-skills-archon.md` — Why: mem0 + Archon comparison and token cost table
- `templates/STRUCTURED-PLAN-TEMPLATE.md` (lines 64-71) — Why: "Related Memories (from mem0)" section

### New Files to Create

- `templates/MEMORY-TEMPLATE.md` — Template for the memory.md file structure

### Related Memories (from mem0)

N/A — we're removing mem0

### Relevant Documentation

No external docs needed — this is simplification, not new technology.

### Patterns to Follow

**File-based memory pattern** (common in Claude Code projects):
```markdown
# Project Memory

## Decisions
- [date] Decision description — reason

## Patterns
- Pattern name: description, where it's used

## Gotchas
- Gotcha description — how to avoid

## Lessons
- Lesson learned — context
```
- Why this pattern: Simple, structured, grep-able, version-controlled
- Common gotchas: File can grow too large — keep entries concise (1-2 lines each)

---

## IMPLEMENTATION PLAN

### Phase 1: Create memory.md Template

Define the standard structure for project memory files.

**Tasks:**
- Create MEMORY-TEMPLATE.md

### Phase 2: Update Commands (Read/Write memory.md)

Replace mem0 MCP calls with file read/append operations in the 3 core commands.

**Tasks:**
- Update prime.md to read memory.md
- Update planning.md to read memory.md
- Update commit.md to append to memory.md

### Phase 3: Update Sections (Documentation)

Replace mem0 references in always-loaded sections with memory.md approach.

**Tasks:**
- Update sections/02_piv_loop.md
- Update sections/03_context_engineering.md
- Update reference/mcp-skills-overview.md

### Phase 4: Update References & Templates

Replace mem0 references in on-demand guides and templates.

**Tasks:**
- Update reference/piv-loop-practice.md
- Update reference/mcp-skills-archon.md
- Update templates/STRUCTURED-PLAN-TEMPLATE.md
- Update reference/file-structure.md

---

## STEP-BY-STEP TASKS

### CREATE templates/MEMORY-TEMPLATE.md

- **IMPLEMENT**: Create the memory.md template (~40-50 lines):
  1. Header with usage instructions:
     - Copy to project root as `memory.md`
     - AI reads at session start (`/prime`) and during planning (`/planning`)
     - AI appends after implementation (`/commit`)
     - Human can edit anytime — it's just a markdown file
  2. **Sections**:
     ```markdown
     # Project Memory

     ## Key Decisions
     <!-- Format: - [YYYY-MM-DD] Decision — Reason -->

     ## Architecture Patterns
     <!-- Format: - **Pattern name**: Description. Used in: location -->

     ## Gotchas & Pitfalls
     <!-- Format: - **Area**: What goes wrong — How to avoid -->

     ## Lessons Learned
     <!-- Format: - **Context**: Lesson — Impact on future work -->

     ## Session Notes
     <!-- Format: - [YYYY-MM-DD] Brief summary of what was done -->
     ```
  3. Footer: "Keep entries concise (1-2 lines). This file is read by AI at session start — large files waste context tokens."
- **PATTERN**: Follow template header convention from other templates
- **IMPORTS**: None
- **GOTCHA**: Keep the template SHORT. The power is in the structure, not verbose instructions.
- **VALIDATE**: `powershell -Command "if (Test-Path 'templates/MEMORY-TEMPLATE.md') { Write-Host 'OK'; (Get-Content 'templates/MEMORY-TEMPLATE.md').Count } else { Write-Host 'MISSING' }"`

### UPDATE .claude/commands/prime.md

- **IMPLEMENT**: Replace Step 5 (mem0 search) with memory.md reading:
  - **Remove**: All mem0 search queries (search for "mem0" and remove those lines)
  - **Replace with**:
    ```markdown
    ### 5. Read Project Memory (if memory.md exists)

    If `memory.md` exists at project root, read it and include relevant entries in the output report:
    - Key decisions that affect current work
    - Known gotchas for the project's tech stack
    - Architecture patterns established in past sessions
    - Recent session notes for continuity

    If memory.md doesn't exist, note "No memory.md found — consider creating one from templates/MEMORY-TEMPLATE.md"
    ```
  - Keep the section numbering consistent
  - Update the Output Report section: rename "Memory Context (from mem0)" to "Memory Context (from memory.md)"
- **PATTERN**: Conditional file reading (if exists, read; if not, skip gracefully)
- **IMPORTS**: None
- **GOTCHA**: Must handle the case where memory.md doesn't exist — don't fail, just note its absence
- **VALIDATE**: `powershell -Command "if (Select-String -Path '.claude/commands/prime.md' -Pattern 'mem0' -Quiet) { Write-Host 'FAIL: mem0 still referenced' } else { Write-Host 'OK: no mem0 references' }"`

### UPDATE .claude/commands/planning.md

- **IMPLEMENT**: Replace Phase 2c (mem0 search) with memory.md reading:
  - **Remove**: All mem0 search queries in Phase 2c and Phase 1
  - **Replace Phase 1 mem0 search** with:
    ```markdown
    1. Before scoping, check memory.md (if it exists) for past decisions about this feature area
    ```
  - **Replace Phase 2c** with:
    ```markdown
    ### Phase 2c: Memory Search (if memory.md exists)

    Read memory.md for past experiences relevant to this feature:
    - Decisions that affect this feature area
    - Gotchas in the affected systems
    - Patterns established for similar work

    **Required output format**:
    ```
    ### Related Memories (from memory.md)
    - Memory: {summary} — Relevance: {why this matters for current feature}
    ```

    If memory.md doesn't exist or has no relevant entries, note "No relevant memories found" and continue.
    ```
  - Remove any `mem0` import/tool references
- **PATTERN**: File reading instead of MCP tool calls
- **IMPORTS**: None
- **GOTCHA**: The planning command is 362 lines — be surgical, only change mem0-specific lines
- **VALIDATE**: `powershell -Command "if (Select-String -Path '.claude/commands/planning.md' -Pattern 'mem0' -Quiet) { Write-Host 'FAIL: mem0 still referenced' } else { Write-Host 'OK: no mem0 references' }"`

### UPDATE .claude/commands/commit.md

- **IMPLEMENT**: Replace Step 6 (mem0 storage) with memory.md append:
  - **Remove**: All mem0 add_memory calls
  - **Replace with**:
    ```markdown
    ### Step 6: Update Project Memory (if memory.md exists)

    If `memory.md` exists at project root, append a brief entry:

    Under **Session Notes**:
    - [today's date] Implemented {feature}: {1-line summary}

    Under **Lessons Learned** (if any lessons emerged):
    - **{context}**: {lesson} — {impact}

    Under **Gotchas & Pitfalls** (if any new gotchas discovered):
    - **{area}**: {what went wrong} — {how to avoid}

    Keep entries concise (1-2 lines each). Don't repeat information already in memory.md.
    If memory.md doesn't exist, skip this step.
    ```
- **PATTERN**: File append instead of MCP tool calls
- **IMPORTS**: None
- **GOTCHA**: Append, don't overwrite. And keep entries brief — memory.md should stay under 100 lines for token efficiency.
- **VALIDATE**: `powershell -Command "if (Select-String -Path '.claude/commands/commit.md' -Pattern 'mem0' -Quiet) { Write-Host 'FAIL: mem0 still referenced' } else { Write-Host 'OK: no mem0 references' }"`

### UPDATE sections/02_piv_loop.md

- **IMPLEMENT**: Replace mem0 references with memory.md:
  - Find all instances of "mem0" and replace with "memory.md" or "project memory file"
  - Update any descriptions of how memory works (from "MCP server" to "markdown file at project root")
  - Keep the concept of cross-session memory — just change the mechanism
  - Update the command descriptions that reference mem0 integration
- **PATTERN**: Surgical find/replace, preserve surrounding context
- **IMPORTS**: None
- **GOTCHA**: Don't change the conceptual framework — "Memory" as a pillar of Context Engineering is still valid. Only the implementation changes.
- **VALIDATE**: `powershell -Command "if (Select-String -Path 'sections/02_piv_loop.md' -Pattern 'mem0' -Quiet) { Write-Host 'FAIL: mem0 still referenced' } else { Write-Host 'OK: no mem0 references' }"`

### UPDATE sections/03_context_engineering.md

- **IMPLEMENT**: Replace mem0 reference in the Memory pillar:
  - Change: "leverage the vibe planning conversation (short-term) AND mem0 for persistent cross-session recall (long-term). mem0 is searched during `/prime` and `/planning`, and populated during `/commit`."
  - To: "leverage the vibe planning conversation (short-term) AND `memory.md` for persistent cross-session recall (long-term). `memory.md` is read during `/prime` and `/planning`, and updated during `/commit`."
- **PATTERN**: Direct text replacement
- **IMPORTS**: None
- **GOTCHA**: This is only 11 lines — one precise edit needed
- **VALIDATE**: `powershell -Command "if (Select-String -Path 'sections/03_context_engineering.md' -Pattern 'mem0' -Quiet) { Write-Host 'FAIL: mem0 still referenced' } else { Write-Host 'OK: no mem0 references' }"`

### UPDATE reference/mcp-skills-overview.md

- **IMPLEMENT**: Replace mem0 references in the token cost analysis and integration sections:
  - Update the token cost table: remove "mem0 only" and "mem0 + Archon" rows, or replace with "memory.md" (which has zero MCP token cost)
  - Update "Token Optimization Rules": remove mem0-specific rules
  - Update the "Use BOTH together" recommendation: replace with "Use Archon for task management and RAG. Use memory.md for cross-session learning."
  - Remove or update the mem0 comparison in "MCP vs Skills" context
  - Keep Archon RAG and task management references unchanged
- **PATTERN**: Surgical replacement, preserve table formatting
- **IMPORTS**: None
- **GOTCHA**: This is a longer section (~150 lines). Be careful to only change mem0-specific content, not Archon content.
- **VALIDATE**: `powershell -Command "if (Select-String -Path 'reference/mcp-skills-overview.md' -Pattern 'mem0' -Quiet) { Write-Host 'FAIL: mem0 still referenced' } else { Write-Host 'OK: no mem0 references' }"`

### UPDATE reference/piv-loop-practice.md

- **IMPLEMENT**: Replace mem0 references in the 4 Pillars section:
  - Update "Memory" pillar description: from mem0 MCP to memory.md file
  - Update any mem0 code examples or tool calls with file read/append equivalents
  - Keep the conceptual framework intact — Memory pillar is still about persistent cross-session context
- **PATTERN**: Find all "mem0" occurrences, replace with memory.md approach
- **IMPORTS**: None
- **GOTCHA**: This is a ~776-line file. Search for "mem0" specifically — don't read the entire file looking for references.
- **VALIDATE**: `powershell -Command "if (Select-String -Path 'reference/piv-loop-practice.md' -Pattern 'mem0' -Quiet) { Write-Host 'FAIL: mem0 still referenced' } else { Write-Host 'OK: no mem0 references' }"`

### UPDATE reference/mcp-skills-archon.md

- **IMPLEMENT**: Replace mem0 references in the Archon integration guide:
  - Update token cost comparison table (remove mem0 rows or replace with memory.md)
  - Update "Use both together" recommendation
  - Remove mem0-specific optimization rules
  - Keep all Archon RAG and task management content unchanged
- **PATTERN**: Find all "mem0" occurrences, replace
- **IMPORTS**: None
- **GOTCHA**: Archon content must remain untouched — only mem0 content changes
- **VALIDATE**: `powershell -Command "if (Select-String -Path 'reference/mcp-skills-archon.md' -Pattern 'mem0' -Quiet) { Write-Host 'FAIL: mem0 still referenced' } else { Write-Host 'OK: no mem0 references' }"`

### UPDATE templates/STRUCTURED-PLAN-TEMPLATE.md

- **IMPLEMENT**: Replace the "Related Memories (from mem0)" section:
  - Change section title to: "### Related Memories (from memory.md)"
  - Change description to: "> Past experiences and lessons relevant to this feature. Populated by `/planning` from memory.md."
  - Update the example entries to remove mem0 references
- **PATTERN**: Direct text replacement
- **IMPORTS**: None
- **GOTCHA**: Only change the mem0-specific text, not the surrounding template structure
- **VALIDATE**: `powershell -Command "if (Select-String -Path 'templates/STRUCTURED-PLAN-TEMPLATE.md' -Pattern 'mem0' -Quiet) { Write-Host 'FAIL: mem0 still referenced' } else { Write-Host 'OK: no mem0 references' }"`

### UPDATE reference/file-structure.md

- **IMPLEMENT**: Add memory.md template to the templates/ section and add memory.md as a project-level file:
  - Add under templates/: `MEMORY-TEMPLATE.md                    # Template for project memory (cross-session context)`
  - Add note near CLAUDE.md: `memory.md                              # Cross-session memory (decisions, patterns, gotchas)`
- **PATTERN**: Follow existing format
- **IMPORTS**: None
- **GOTCHA**: memory.md at project root is optional — note it as such
- **VALIDATE**: `powershell -Command "Select-String -Path 'reference/file-structure.md' -Pattern 'MEMORY-TEMPLATE|memory.md' | Measure-Object | Select-Object -ExpandProperty Count"` — should be >= 2

---

## TESTING STRATEGY

### Unit Tests

N/A — markdown files, no code.

### Integration Tests

- Run `Select-String -Recurse -Pattern 'mem0'` across entire project — should return ZERO matches after migration
- Verify memory.md template is usable (copy to a test location, verify structure)
- Verify commands reference memory.md correctly with conditional logic

### Edge Cases

- memory.md doesn't exist (commands must handle gracefully — skip, don't fail)
- memory.md is empty (commands should read and note "no entries yet")
- memory.md is very large (>100 lines) — note in template to keep it concise

---

## VALIDATION COMMANDS

### Level 1: Zero mem0 References
```
powershell -Command "Get-ChildItem -Recurse -Include '*.md','*.yaml' | Select-String -Pattern 'mem0' | ForEach-Object { Write-Host $_.Path ':' $_.LineNumber ':' $_.Line }"
```
This should return ZERO results after migration.

### Level 2: New Files Exist
```
powershell -Command "if (Test-Path 'templates/MEMORY-TEMPLATE.md') { Write-Host 'OK: MEMORY-TEMPLATE.md' } else { Write-Host 'MISSING: MEMORY-TEMPLATE.md' }"
```

### Level 3: Commands Reference memory.md
```
powershell -Command "@('.claude/commands/prime.md','.claude/commands/planning.md','.claude/commands/commit.md') | ForEach-Object { $count = (Select-String -Path $_ -Pattern 'memory.md').Count; Write-Host $_ ': ' $count ' memory.md references' }"
```

### Level 4: Manual Validation

1. Read each updated command and verify conditional logic: "if memory.md exists, read/append; if not, skip"
2. Verify no mem0 MCP tool calls remain (`mem0`, `search_memories`, `add_memory`)
3. Verify sections still make conceptual sense with memory.md replacing mem0
4. Verify the Memory pillar in Context Engineering is still coherent

---

## ACCEPTANCE CRITERIA

- [x] Zero instances of "mem0" across the entire project (`Select-String -Recurse` returns nothing)
- [x] MEMORY-TEMPLATE.md created with clear structure (Decisions, Patterns, Gotchas, Lessons, Session Notes)
- [x] /prime reads memory.md (conditional)
- [x] /planning reads memory.md (conditional)
- [x] /commit appends to memory.md (conditional)
- [x] All sections updated (02, 03, 12)
- [x] All references updated (piv-loop-practice, mcp-skills-archon)
- [x] STRUCTURED-PLAN-TEMPLATE.md updated
- [x] reference/file-structure.md updated

---

## COMPLETION CHECKLIST

- [x] All tasks completed in order
- [x] Each task validation passed
- [x] Zero mem0 references in entire project
- [x] Commands handle missing memory.md gracefully
- [x] Conceptual framework (Memory pillar) still coherent
- [x] Acceptance criteria all met

---

## NOTES

### Key Design Decisions
- memory.md is a SIMPLE markdown file — no special tooling, no MCP, no vector search
- Structured sections (Decisions, Patterns, etc.) make it grep-friendly for AI
- Conditional logic in commands — memory.md is optional, not required
- Version-controlled — memory travels with the repo, visible in PRs

### Risks
- Risk 1: memory.md grows too large over time → Mitigation: template includes "keep under 100 lines" guidance; /commit appends concisely
- Risk 2: AI writes verbose entries → Mitigation: explicit "1-2 lines each" constraint in commit command
- Risk 3: Users forget to create memory.md → Mitigation: /prime suggests creating it if missing

### Confidence Score: 9/10
- **Strengths**: Straightforward find/replace across known files; simpler system than what it replaces
- **Uncertainties**: Some mem0 references may be deeply embedded in prose (harder to find)
- **Mitigations**: Final validation command (`Select-String -Recurse 'mem0'`) catches any missed references
