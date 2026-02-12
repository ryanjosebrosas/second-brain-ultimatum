# Feature: Token Efficiency & README

## Feature Description

Optimize the My Coding System for token efficiency and context window sustainability, then create a public-facing README with visual diagrams. The system's auto-loaded base (~3.2K tokens) and on-demand architecture are already sound — this feature focuses on reducing per-conversation overhead from commands, trimming the auto-loaded Archon section, slimming the PIV loop section, and compressing the heaviest slash commands so more context window is available for actual implementation work.

## User Story

As a developer using My Coding System, I want commands and auto-loaded context to consume fewer tokens, so that I have more context window available for complex multi-agent builds and don't run out mid-conversation.

## Problem Statement

When building complex features (multi-agent systems, large codebases), conversations hit context window limits because:
1. `sections/15_archon_workflow.md` auto-loads 1,530 tokens every session, but Archon is only used during `/execute` and `/planning` — 48% of auto-loaded context is wasted in most sessions
2. `sections/02_piv_loop.md` includes deep references, optional workflows, and verbose prose that could be on-demand — 962 tokens, second-largest auto-loaded section
3. `/planning` command is 458 lines / ~3,374 tokens — the largest command, loaded in full when invoked
4. `/execute` command has verbose Archon conditional blocks repeated 5 times (if available / if unavailable patterns)
5. Other commands carry similar verbosity patterns

## Solution Statement

- Decision 1: Move Archon workflow to on-demand reference — because it's only needed during execution/planning, not every session. Replace with a 3-line pointer in auto-loaded sections.
- Decision 2: Slim PIV loop section by extracting optional/deep content to reference — because the core loop definition only needs ~400 tokens, not 962.
- Decision 3: Compress the 5 heaviest commands using structured shorthand over prose — because the AI can follow concise instructions just as well as verbose ones, and every token saved in the command is a token available for actual work.
- Decision 4: Create a public README.md with Mermaid diagrams — because the project has no README and this aids adoption and understanding.

## Feature Metadata

- **Feature Type**: Enhancement + New Capability (README)
- **Estimated Complexity**: Medium
- **Primary Systems Affected**: `sections/`, `reference/`, `.claude/commands/`, project root
- **Dependencies**: None (pure markdown changes + new file)

---

## CONTEXT REFERENCES

### Relevant Codebase Files

> IMPORTANT: The execution agent MUST read these files before implementing!

- `sections/15_archon_workflow.md` (all) — Why: Will be moved to reference/ and replaced with slim pointer
- `sections/02_piv_loop.md` (all) — Why: Will be slimmed, deep content extracted to reference/
- `CLAUDE.md` (lines 31-33) — Why: Archon section reference must be updated
- `.claude/commands/planning.md` (all, 458 lines) — Why: Largest command, primary compression target
- `.claude/commands/execute.md` (all, 216 lines) — Why: Has 5 repeated Archon conditional blocks
- `.claude/commands/commit.md` (all, 160 lines) — Why: Has verbose Archon/memory sections
- `.claude/commands/code-review.md` (all, 171 lines) — Why: Has verbose mode selection prose
- `.claude/commands/code-review-fix.md` (all, 148 lines) — Why: Can be compressed
- `reference/file-structure.md` (all) — Why: Must be updated when files move
- `memory.md` (all) — Why: Session notes update at the end

### New Files to Create

- `README.md` — Public-facing project README with Mermaid diagrams
- `reference/archon-workflow.md` — Relocated Archon workflow (renamed from sections/15)

### Related Memories (from memory.md)

- Memory: Slimmed CLAUDE.md by moving sections 06-14 to reference/ — saves ~12,000 tokens per session — Relevance: Same pattern we're applying to the Archon section now
- Memory: Adopted 3-tier skills architecture — Relevance: Progressive disclosure principle applies to command compression
- Memory: Archon queries must be 2-5 keywords — Relevance: Archon integration rules must be preserved in the reference guide
- Memory: Only ONE task in "doing" status at a time — Relevance: Must be preserved in relocated Archon guide

### Relevant Documentation

- No external docs needed — this is internal optimization of existing markdown files

### Patterns to Follow

**Slim section pointer pattern** (from `CLAUDE.md:7-8`):
```markdown
## Core Principles
@sections/01_core_principles.md
```
- Why this pattern: Auto-loaded sections use `@` includes, keeping CLAUDE.md slim
- Common gotchas: The section path must be relative to CLAUDE.md

**On-demand reference table pattern** (from `CLAUDE.md:41-49`):
```markdown
| Guide | Load when... |
|-------|-------------|
| `reference/layer1-guide.md` | Setting up CLAUDE.md for a new project |
```
- Why this pattern: On-demand guides are listed in a table so the AI knows when to load them
- Common gotchas: Must update this table when adding/moving reference guides

**Command frontmatter pattern** (from `.claude/commands/execute.md:1-4`):
```markdown
---
description: Execute an implementation plan
argument-hint: [path-to-plan]
allowed-tools: Read, Write, Edit, Bash(...)
---
```
- Why this pattern: Frontmatter defines command metadata, must be preserved during compression
- Common gotchas: `allowed-tools` must include Archon MCP tools for commands that use them

**Compact Archon conditional pattern** (new — to be used in all compressed commands):
```markdown
**Archon** (if available): `manage_task("update", task_id="...", status="doing")`
```
- Why this pattern: Replaces 5-8 line "If Archon available / If unavailable" blocks with 1 line
- The "(if available)" qualifier tells the AI to check and skip gracefully if Archon isn't configured
- Common gotchas: Must include the actual MCP function call in the line — don't just say "update Archon"

**Compression before/after example** (from `/execute` Archon block):

BEFORE (8 lines, ~80 words):
```markdown
### 1.5. Initialize Archon Task Management (if available)

**If Archon MCP is configured:**

1. **Create project**: `manage_project("create", title="{feature-name}", description="{plan description}")`
2. **Extract all tasks from plan**: Read "STEP-BY-STEP TASKS" section
3. **Create tasks in Archon**: For each task in plan...

**If Archon MCP unavailable:**
- Skip task initialization, proceed with implementation
```

AFTER (3 lines, ~30 words):
```markdown
### 1.5. Archon Setup (if available)

Create project and tasks: `manage_project("create", ...)`, then `manage_task("create", ...)` for each plan task. Skip if Archon unavailable.
```
- Why: Same information, 62% fewer words. The AI knows how to call MCP functions — it doesn't need step-by-step handholding for tool calls it makes regularly.

---

## IMPLEMENTATION PLAN

### Phase 1: Relocate & Slim Auto-Loaded Context

Move Archon workflow to reference/ and slim PIV loop section. This reduces the auto-loaded base from ~3,171 tokens to ~2,000 tokens — a 37% reduction in per-session overhead.

**Tasks:**
- Move `sections/15_archon_workflow.md` to `reference/archon-workflow.md`
- Create slim Archon pointer in `sections/15_archon_workflow.md` (3-5 lines)
- Slim `sections/02_piv_loop.md` — keep core loop, move optional/deep content to existing reference files
- Update `CLAUDE.md` on-demand table to include Archon workflow guide
- Update `reference/file-structure.md` to reflect moved files

### Phase 2: Compress Core Commands

Compress the 5 heaviest commands using structured shorthand. Target: 30-40% token reduction per command while preserving all functionality.

**Compression principles (apply to ALL commands):**

1. **Instruct, don't explain**: Replace "The execution agent should validate documentation and codebase patterns before implementing" with "Validate docs and patterns before implementing."
2. **One-line Archon conditionals**: Replace all 5-8 line "If Archon available / If unavailable" blocks with: `**Archon** (if available): [single MCP call]`
3. **Remove duplicate information**: If something is already in the template, don't repeat it in the command. The command says "Read the template" — that's enough.
4. **Remove examples that mirror templates**: The `/planning` command has "Example format" blocks that duplicate `STRUCTURED-PLAN-TEMPLATE.md`. Remove them.
5. **Combine tiny steps**: Steps that are 1-2 lines each can often be merged. "Stage files" + "Create commit" = one step.
6. **Remove validation questions**: Lines like "Validation: Can someone understand the feature?" are meta-commentary the AI doesn't need.
7. **Trust AI capabilities**: The AI knows conventional commit types, how to ask probing questions, what Critical/Major/Minor severity means. Don't explain these.

**Compression targets by command:**

| Command | Before (words) | Target (words) | Strategy Focus |
|---------|---------------:|---------------:|----------------|
| `/planning` | 2,595 | ~1,600 | Remove examples, condense phases, remove output format blocks |
| `/execute` | 1,132 | ~750 | Compact Archon blocks, condense series mode, merge small steps |
| `/commit` | 518 | ~350 | Remove commit type descriptions, merge stage+commit, slim memory |
| `/code-review` | 674 | ~450 | Remove philosophy, condense agent descriptions, slim output prose |
| `/code-review-fix` | 875 | ~550 | Remove severity definitions, condense selectivity, slim fix steps |

### Phase 3: Create README

Create a public-facing README.md with project overview, Mermaid diagrams, and quick start guide.

**Tasks:**
- Write README.md with project overview, PIV Loop diagram, command reference, and getting started guide

### Phase 4: Validation & Cleanup

Verify everything works together after changes.

**Tasks:**
- Update `reference/file-structure.md` with all changes
- Update `memory.md` with session notes

---

## STEP-BY-STEP TASKS

> Execute every task in order, top to bottom. Each task is atomic and independently testable.

### UPDATE `sections/15_archon_workflow.md`

- **IMPLEMENT**: Replace the entire 1,177-word Archon workflow with a slim 3-5 line pointer that tells the AI when and how to load the full guide. Content:
  ```markdown
  # Archon Integration

  > Task management and RAG search are handled via Archon MCP server.
  > Load `reference/archon-workflow.md` when using `/execute`, `/planning`, or task management.
  > Key rule: ALWAYS use Archon MCP tools for task management (never TodoWrite).
  ```
- **PATTERN**: Follow the slim section pattern from `sections/01_core_principles.md` — concise, essential rules only
- **IMPORTS**: N/A (markdown)
- **GOTCHA**: The "ARCHON-FIRST RULE" about never using TodoWrite must remain in the slim version — it's a critical behavioral override. Also keep the "ALWAYS use Archon MCP tools" instruction.
- **VALIDATE**: `powershell -Command "(Get-Content sections/15_archon_workflow.md | Measure-Object -Word).Words"` — should be under 50 words

### CREATE `reference/archon-workflow.md`

- **IMPLEMENT**: Move the full Archon workflow content here. Copy the entire original `sections/15_archon_workflow.md` content (before the slim replacement above) into this new file. Add a header note: `> On-demand guide. Loaded by /execute, /planning, and task management commands.`
- **PATTERN**: Follow structure of existing reference guides like `reference/validation-strategy.md`
- **IMPORTS**: N/A (markdown)
- **GOTCHA**: Preserve ALL content from the original — this is a move, not a deletion. The commands that need Archon context will load this file explicitly.
- **VALIDATE**: `powershell -Command "Test-Path reference/archon-workflow.md"` — should return True

### UPDATE `CLAUDE.md`

- **IMPLEMENT**: Two changes:
  1. In the On-Demand Guides table (around line 41-49), add a new row: `| reference/archon-workflow.md | Using Archon task management or RAG search |`
  2. Remove the `## Archon Workflow` section with its `@sections/15_archon_workflow.md` reference (lines 31-33) since Archon is now on-demand via the table, BUT keep the slim `sections/15_archon_workflow.md` as an auto-loaded section since it contains the critical TodoWrite override rule. Actually — keep the Archon section header and `@` reference as-is. The section file itself is now slim (3-5 lines), so it auto-loads at minimal cost (~40 tokens) while the full guide is on-demand.
  3. Just add the on-demand table row for the full reference guide.
- **PATTERN**: Follow existing on-demand table pattern at `CLAUDE.md:41-49`
- **IMPORTS**: N/A
- **GOTCHA**: Don't remove the `@sections/15_archon_workflow.md` include — the slim version still needs to auto-load for the TodoWrite override. Only ADD the reference table row.
- **VALIDATE**: `powershell -Command "Select-String 'archon-workflow.md' CLAUDE.md"` — should find the new table row

### UPDATE `sections/02_piv_loop.md`

- **IMPLEMENT**: Slim this section from ~740 words to ~350 words by:
  1. Keep the core PIV loop definition (PLAN → IMPLEMENT → VALIDATE)
  2. Keep the Granularity Principle (smaller iterations)
  3. Keep Layer 1 vs Layer 2 distinction (brief)
  4. Keep the Implementation and Validation bullet summaries
  5. REMOVE the "Enhanced Validation Workflow" subsection (move to reference/validation-discipline.md if not already there — it is, at reference/validation-discipline.md)
  6. REMOVE the "Leveraging Save States" subsection (this content exists in reference/piv-loop-practice.md)
  7. REMOVE the "For deeper context" and "For PIV Loop in practice" and "For global rules optimization" footer blocks — these are pointer text that wastes auto-loaded tokens. The on-demand table in CLAUDE.md already handles this.
  8. REMOVE the "Model recommendation" and "Billing" paragraphs — move to reference/multi-model-strategy.md (already covered there)
  9. Keep "Do NOT take your PRD and use it as a structured plan" warning
- **PATTERN**: Follow `sections/01_core_principles.md` — concise, actionable, no deep references
- **IMPORTS**: N/A
- **GOTCHA**: Don't lose the "Granularity Principle" and "Do NOT use PRD as structured plan" — these are critical behavioral rules. The content being removed is already in reference guides, so nothing is lost.
- **VALIDATE**: `powershell -Command "(Get-Content sections/02_piv_loop.md | Measure-Object -Word).Words"` — should be 300-400 words (down from 740)

### UPDATE `.claude/commands/planning.md`

- **IMPLEMENT**: Compress from ~2,595 words to ~1,600 words by:
  1. **Phase 0 (Vibe Planning)**: Reduce from 30 lines to 15 lines. Remove the 5 bullet-point example questions — the AI knows how to ask probing questions. Keep the escape hatch, process summary, and rules.
  2. **Phase 1 (Scoping)**: Already concise — minimal changes. Remove the validation question at the end.
  3. **Phases 2 & 3 (Research)**: Compress the Parallel Research Mode section. Remove the full "Example query generation" block (7 lines). Condense "Step 2: Launch Parallel Agents" by removing the Agent C1-C5 / E1-E5 listing — replace with "Launch up to 5 codebase + 5 external agents with focused queries." Remove the "Scale guideline" block (3 lines) — the AI can determine scale from complexity.
  4. **Standard Research Mode**: Condense the "Extract project patterns" list from 7 items to a single line: "Extract project patterns (naming, error handling, logging, types, testing, API, DB)."
  5. **Phase 3b (Archon RAG)**: Replace "If Archon RAG available" prose block with: "Search Archon RAG with 2-5 keyword queries. Use source_id filtering. Fallback to web search if no results."
  6. **Phase 3c (Research Validation)**: Condense from 8 lines to 3 lines.
  7. **Phase 4 (Design)**: Already fairly concise — trim validation line.
  8. **Phase 4.5 (Decomposition)**: Condense trigger criteria to a single line: "Decompose if: High complexity, 4+ phases, 15+ tasks, 3+ systems, or user requests it."
  9. **Phase 5 (Tasks)**: Keep the 7-field format specification. Remove the example format block (it's already in the template). Condense the decomposed mode instructions.
  10. **Phase 6 (Validation)**: Condense the 5-level validation list. Remove the completion checklist (it's in the template).
  11. **Output section**: Condense decomposed mode output instructions. Remove the full execution routing example.
  12. Throughout: Remove "Required output format" code blocks where they duplicate the template structure.
- **PATTERN**: Commands should instruct, not explain. Use imperative sentences. Remove "The execution agent should..." phrasing.
- **IMPORTS**: N/A
- **GOTCHA**: Preserve ALL phase numbers and names — `/execute` references them. Preserve the PLAN-SERIES marker. Preserve the template reference. Don't remove functionality, only compress prose.
- **VALIDATE**: `powershell -Command "(Get-Content .claude/commands/planning.md | Measure-Object -Word).Words"` — target ~1,600 words (down from 2,595)

### UPDATE `.claude/commands/execute.md`

- **IMPLEMENT**: Compress from ~1,132 words to ~750 words by:
  1. **Archon blocks**: There are 5 separate "If Archon available / If unavailable" conditional blocks (Steps 1.5, 2a.5, 2d, 5.5, and the series mode note). Replace each verbose block with a compact pattern:
     ```
     **Archon** (if available): `manage_task("update", task_id="...", status="doing")`
     ```
     One line instead of 5-8 lines per block.
  2. **Step 0.5 (Plan Type Detection)**: Condense the if/else description. Remove the "Instance Routing" sub-block (it's in the plan overview template).
  3. **Step 2 (Execute Tasks)**: Keep the a/b/c/d sub-steps but make each 1-2 lines instead of 3-5.
  4. **Step 2.5 (Series Mode)**: Condense from 18 lines to 8 lines. Remove the "Between sub-plans" explanation (it's in the template).
  5. **Step 6 (Update Checkboxes)**: Condense from 6 lines to 2 lines.
  6. **Output Report**: Keep structure but condense section descriptions.
  7. Remove the HTML comment block at top (lines 7-13) — customization note that's only needed once.
- **PATTERN**: Use the compact Archon pattern consistently across all conditional blocks
- **IMPORTS**: N/A
- **GOTCHA**: Preserve the `allowed-tools` frontmatter — it controls permissions. Preserve the plan type detection logic. Don't remove the series mode execution flow.
- **VALIDATE**: `powershell -Command "(Get-Content .claude/commands/execute.md | Measure-Object -Word).Words"` — target ~750 words (down from 1,132)

### UPDATE `.claude/commands/commit.md`

- **IMPLEMENT**: Compress from ~518 words to ~350 words by:
  1. **Step 2 (Analyze Changes)**: Remove the verbose type list with descriptions — the AI knows conventional commit types. Replace with: "Determine type (feat/fix/refactor/docs/test/chore/perf/style/plan), scope, and description (imperative mood, 50 chars)."
  2. **Steps 3-4 (Stage & Commit)**: Combine into one step with the git commands.
  3. **Step 6 (Memory update)**: Condense the 4 subsections (Session Notes, Lessons, Gotchas, Decisions) into: "Append to memory.md: session note, any lessons/gotchas/decisions discovered. Keep entries 1-2 lines each."
  4. **Step 7 (Archon)**: Condense to 1 line: `**Archon** (if available): manage_project("update", ..., description="Feature complete, committed: {hash}")`
  5. **Notes section**: Condense to 2 lines.
- **PATTERN**: Follow compact instruction style
- **IMPORTS**: N/A
- **GOTCHA**: Preserve the "Do NOT include Co-Authored-By" rule — it's a critical override. Preserve the `allowed-tools` frontmatter.
- **VALIDATE**: `powershell -Command "(Get-Content .claude/commands/commit.md | Measure-Object -Word).Words"` — target ~350 words (down from 518)

### UPDATE `.claude/commands/code-review.md`

- **IMPLEMENT**: Compress from ~674 words to ~450 words by:
  1. **Review Philosophy**: Remove entirely — 4 lines of philosophy that the AI doesn't need for execution.
  2. **Parallel Review Mode**: Condense the 4 agent descriptions. Each agent needs only: name, focus area, one line. Remove the verbose "Execution" and "After agents complete" subsections — replace with: "Launch 4 agents in parallel. Combine results, deduplicate, sort by severity (Critical → Major → Minor)."
  3. **Archon Integration**: Condense to 1 line.
  4. **Standard Review Mode**: Condense Step 3 (Analyze Each File) — the 5-category list with sub-bullets can be: "Check for: logic errors, security issues, performance problems, code quality, standards compliance."
  5. **Output Format**: Keep the YAML finding format (it's a template). Condense surrounding prose.
  6. **Important section**: Condense to 3 lines.
- **PATTERN**: Commands should be lean execution instructions
- **IMPORTS**: N/A
- **GOTCHA**: Preserve the agent check command (`ls .claude/agents/code-review-*.md`). Preserve the output file path pattern.
- **VALIDATE**: `powershell -Command "(Get-Content .claude/commands/code-review.md | Measure-Object -Word).Words"` — target ~450 words (down from 674)

### UPDATE `.claude/commands/code-review-fix.md`

- **IMPLEMENT**: Compress from ~875 words to ~550 words by:
  1. **Step 1 (Load)**: Keep the 3 conditional paths but condense each to 1 line.
  2. **Step 2 (Categorize)**: Remove the severity definitions — the AI knows what Critical/Major/Minor mean. Keep the scope filter logic but condense to a compact list.
  3. **Step 3 (Selectivity Principle)**: Condense from 10 lines to 4 lines. Keep the core rule: "Evaluate each issue. Skip issues that are: documented as acceptable, out of scope, require architectural changes, style preferences, or false positives. Explain every skip."
  4. **Step 4 (Fix)**: Keep the a/b/c/d sub-steps but condense each to 2 lines max.
  5. **Step 5 (Post-Fix Validation)**: Condense to 3 lines.
  6. **Step 6 (Output)**: Keep the table format. Condense prose around it.
  7. **Archon Integration**: Condense to 1 line.
  8. **Important Rules**: Keep as-is (already concise behavioral rules).
- **PATTERN**: Compact command style
- **IMPORTS**: N/A
- **GOTCHA**: Preserve the selectivity principle — it prevents over-fixing. Preserve the output table format.
- **VALIDATE**: `powershell -Command "(Get-Content .claude/commands/code-review-fix.md | Measure-Object -Word).Words"` — target ~550 words (down from 875)

### CREATE `README.md`

- **IMPLEMENT**: Create a public-facing README with the following sections in order:

  **Section 1 — Header & Badge Area** (lines 1-8):
  ```markdown
  # My Coding System

  A comprehensive AI-assisted development methodology combining systematic planning, implementation discipline, and validation strategies.

  Built for [Claude Code](https://claude.com/claude-code) | Powered by the PIV Loop
  ```

  **Section 2 — What is this?** (lines 10-20):
  Explain in 3-4 sentences: This is NOT an application — it's a development methodology for building applications with AI assistance. It provides structured workflows (slash commands), context management (auto-loaded rules + on-demand guides), and quality gates (code review, validation) that turn AI from a "guess and check" tool into a reliable development partner. The core idea: give the AI exactly the right context at the right time, and it produces better output.

  **Section 3 — The PIV Loop** (lines 22-55):
  Brief explanation paragraph, then the Mermaid diagram:
  ```mermaid
  graph LR
    subgraph "PIV Loop"
      P["PLAN<br/>/planning"] --> I["IMPLEMENT<br/>/execute"]
      I --> V["VALIDATE<br/>/code-review"]
      V -->|"Issues?"| P
      V -->|"Pass"| C["/commit"]
    end

    P -.->|"produces"| PLAN["requests/feature-plan.md"]
    PLAN -.->|"feeds"| I
    V -.->|"if issues"| FIX["/code-review-fix"]
    FIX -.-> V
  ```
  After the diagram, add 3-bullet explanation:
  - **Plan**: Vibe planning conversation → structured plan document (500-700 lines of context-rich implementation instructions)
  - **Implement**: Execute the plan task-by-task in a fresh conversation (clean context = better output)
  - **Validate**: Code review, testing, and human review. Issues loop back to Plan.

  **Section 4 — System Architecture** (lines 57-90):
  Brief explanation of how context is organized, then the Mermaid diagram:
  ```mermaid
  graph TD
    CLAUDE["CLAUDE.md<br/>~3K tokens auto-loaded"] --> S["sections/<br/>6 core rules"]
    CLAUDE -.->|"on-demand"| R["reference/<br/>20+ deep guides"]
    CLAUDE -.->|"on-demand"| T["templates/<br/>16 templates"]

    CMD[".claude/commands/<br/>17 slash commands"] -->|"reads"| T
    CMD -->|"produces"| REQ["requests/<br/>feature plans"]

    SK[".claude/skills/<br/>4 cloud skills"] -.->|"loads"| R

    MEM["memory.md<br/>cross-session context"] -.-> CMD
    ARCHON["Archon MCP<br/>task management + RAG"] -.-> CMD

    REQ -->|"/execute"| IMPL["Implementation"]
    IMPL -->|"/commit"| GIT["Git Save Points"]
  ```
  After the diagram, explain the key insight: auto-loaded context is kept minimal (~3K tokens) so the AI has maximum context window available for actual work. Deep guides are loaded on-demand only when relevant.

  **Section 5 — Quick Start** (lines 92-115):
  ```markdown
  ## Quick Start

  ### Prerequisites
  - [Claude Code CLI](https://claude.com/claude-code) installed
  - Git configured

  ### Setup
  1. Clone this repo (or copy to your project)
  2. Run `/prime` to load codebase context
  3. Run `/planning [feature description]` to create a plan
  4. Run `/execute requests/feature-plan.md` to implement
  5. Run `/commit` to save your work

  ### First Time?
  Start with `/prime` to understand the system, then try `/planning` on a small feature.
  ```

  **Section 6 — Core Commands** (lines 117-145):
  Table with the 10 most important commands:

  | Command | Description | When to Use |
  |---------|-------------|-------------|
  | `/prime` | Load codebase context | Start of every session |
  | `/planning [feature]` | Create implementation plan | Before building any feature |
  | `/execute [plan]` | Implement from plan file | After planning |
  | `/commit` | Git commit with conventional format | After implementation |
  | `/code-review` | Technical quality review | After implementation |
  | `/code-review-fix` | Fix review findings | After code review |
  | `/end-to-end-feature` | Full autonomous pipeline | Trusted, simple features |
  | `/new-worktree` | Create parallel branch | Multi-feature work |
  | `/parallel-e2e` | Parallel multi-feature | Advanced parallel builds |
  | `/init-c` | Generate CLAUDE.md for new project | New projects |

  **Section 7 — Project Structure** (lines 147-175):
  Brief tree-style overview:
  ```
  My-Coding-System/
  ├── CLAUDE.md              # Auto-loaded rules (slim, ~3K tokens)
  ├── memory.md              # Cross-session memory
  ├── sections/              # Core rule sections (auto-loaded)
  ├── reference/             # Deep guides (on-demand, ~89K tokens)
  ├── templates/             # Reusable templates (16 files)
  ├── requests/              # Feature plans (per PIV loop)
  ├── .claude/commands/      # Slash commands (17 commands)
  ├── .claude/skills/        # Cloud skills (4 skills)
  └── .claude/agents/        # Subagent examples (6 agents)
  ```

  **Section 8 — Core Principles** (lines 177-188):
  Brief bullet list: YAGNI, KISS, DRY, Limit AI Assumptions, Always Be Priming (ABP)

  **Section 9 — On-Demand Guides** (lines 190-210):
  Table of reference/ guides with "Load when..." column (mirror CLAUDE.md table)

  **Section 10 — Token Budget** (lines 212-225):
  Brief explanation of how the system manages tokens:
  - Auto-loaded: ~2K tokens (after this optimization)
  - Commands: loaded only when invoked
  - Reference guides: loaded only when needed
  - Total system: ~131K tokens available, but typical session uses <10K

- **PATTERN**: Follow standard GitHub README conventions. Use Mermaid for diagrams (rendered natively by GitHub).
- **IMPORTS**: N/A
- **GOTCHA**: Keep the README under 250 lines — it should be a quick overview, not a manual. The detailed docs live in reference/. Mermaid diagrams must use GitHub-compatible syntax (no advanced features like click events).
- **VALIDATE**: `powershell -Command "Test-Path README.md"` — should return True. Then visually verify Mermaid renders on GitHub after push.

### UPDATE `reference/file-structure.md`

- **IMPLEMENT**: Update the file structure listing to reflect:
  1. Add `README.md` to the root section with description: `# Public-facing project README with PIV Loop diagrams`
  2. Add `reference/archon-workflow.md` with description: `# Archon task management & RAG workflow (moved from sections/)`
  3. Update `sections/15_archon_workflow.md` description to: `# Archon integration pointer (slim — loads reference/archon-workflow.md)`
  4. Update `sections/02_piv_loop.md` description to reflect it's been slimmed
- **PATTERN**: Follow existing file-structure.md format with comments
- **IMPORTS**: N/A
- **GOTCHA**: Keep the structure listing alphabetically consistent within each directory section.
- **VALIDATE**: `powershell -Command "Select-String 'archon-workflow.md' reference/file-structure.md"` — should find the new entry

---

## TOKEN SAVINGS SUMMARY

Expected savings from all changes combined:

| Component | Before (tokens) | After (tokens) | Saved | % Reduction |
|-----------|----------------:|---------------:|------:|------------:|
| Auto-loaded (sections/) | 3,171 | ~2,000 | ~1,171 | 37% |
| `/planning` command | 3,374 | ~2,200 | ~1,174 | 35% |
| `/execute` command | 1,472 | ~1,000 | ~472 | 32% |
| `/commit` command | 673 | ~450 | ~223 | 33% |
| `/code-review` command | 876 | ~600 | ~276 | 31% |
| `/code-review-fix` command | 1,138 | ~720 | ~418 | 37% |
| **Total savings** | | | **~3,734** | **~34% avg** |

**Impact by workflow:**
- **Every session**: saves ~1,171 tokens (auto-loaded reduction)
- **Planning session** (`/prime` + `/planning`): saves ~1,171 + ~1,174 = ~2,345 tokens
- **Execution session** (`/execute` + validation chain): saves ~1,171 + ~472 + ~276 + ~418 = ~2,337 tokens
- **Full PIV loop** (plan + execute + review + commit): saves ~3,734 tokens total

These savings compound across conversation turns. In a 30-turn conversation, the auto-loaded savings alone free up ~1,171 tokens that can be used for actual implementation context.

---

## TESTING STRATEGY

### Unit Tests

N/A — this feature modifies markdown files only. No code to unit test.

### Integration Tests

- Verify all `@sections/` includes in CLAUDE.md resolve to existing files
- Verify all on-demand table entries in CLAUDE.md point to existing files in reference/
- Verify no broken cross-references between commands and templates
- Verify compressed commands still contain all required structural elements:
  - `/planning`: frontmatter, Phase 0-6 headers, PLAN-SERIES marker, template reference, output instructions
  - `/execute`: frontmatter with allowed-tools, Step 0.5 plan type detection, Step 2 task loop, Step 2.5 series mode, output report
  - `/commit`: frontmatter with allowed-tools, conventional commit types, memory.md update, Archon update, "Do NOT include Co-Authored-By" rule
  - `/code-review`: agent check command, parallel vs standard mode, YAML finding format, output file path pattern
  - `/code-review-fix`: severity triage, selectivity principle, scope filtering, fix output table, "Explain every skip" rule

### Edge Cases

- Compressed commands must still trigger correct AI behavior (e.g., Archon task updates, plan type detection)
- Slim PIV loop must still convey the core methodology to a fresh agent
- Slim Archon section must still override TodoWrite behavior
- README Mermaid diagrams must render correctly on GitHub
- Commands that load the Archon reference guide must still find it at the new path (`reference/archon-workflow.md`)
- The `/execute` command must still detect `<!-- PLAN-SERIES -->` markers correctly after compression

---

## VALIDATION COMMANDS

### Level 1: Syntax & Structure
```powershell
# Verify all referenced files exist
@("sections/15_archon_workflow.md", "reference/archon-workflow.md", "README.md") | ForEach-Object { if (Test-Path $_) { "$_ EXISTS" } else { "$_ MISSING" } }
```

### Level 2: Token Budget Verification
```powershell
# Measure auto-loaded context (should be ~2,000 tokens, down from ~3,171)
$words = 0; @("CLAUDE.md") + (Get-ChildItem sections/*.md | ForEach-Object { $_.Name }) | ForEach-Object { $words += (Get-Content "sections/$_" -ErrorAction SilentlyContinue | Measure-Object -Word).Words }; "Auto-loaded: ~$($words) words (~$([math]::Round($words * 1.3)) tokens)"

# Measure compressed commands
@("planning.md", "execute.md", "commit.md", "code-review.md", "code-review-fix.md") | ForEach-Object { $w = (Get-Content ".claude/commands/$_" | Measure-Object -Word).Words; "$_`: $w words (~$([math]::Round($w * 1.3)) tokens)" }
```

### Level 3: Cross-Reference Integrity
```powershell
# Verify CLAUDE.md on-demand table entries all point to existing files
Select-String "reference/" CLAUDE.md | ForEach-Object { $_.Line -match '`(reference/[^`]+)`' | Out-Null; if ($Matches[1]) { $f = $Matches[1]; if (Test-Path $f) { "$f OK" } else { "$f BROKEN" } } }
```

### Level 4: Manual Validation

Read each file and verify behavioral completeness:

**Auto-loaded sections:**
1. Read `sections/15_archon_workflow.md` — must contain TodoWrite override rule
2. Read `sections/02_piv_loop.md` — must explain PLAN → IMPLEMENT → VALIDATE, Granularity Principle, Layer 1 vs 2
3. Verify both files together convey the essential methodology without needing reference guides

**Compressed commands (read each end-to-end):**
4. `/planning` — verify all 7 phases present (0-6), PLAN-SERIES marker, template reference, output instructions
5. `/execute` — verify plan type detection (standard vs series), task loop with Archon updates, output report
6. `/commit` — verify conventional commit format, memory.md update, Archon update, Co-Authored-By prohibition
7. `/code-review` — verify parallel vs standard mode, agent check command, YAML output format
8. `/code-review-fix` — verify selectivity principle, severity order, scope filtering, output table

**New files:**
9. Read `README.md` — verify Mermaid diagrams are well-formed, quick start is clear, command table is complete
10. Read `reference/archon-workflow.md` — verify it contains the full original Archon content (all sections: Core Workflow, RAG Workflow, Project Workflows, Task Granularity, Tool Reference, Integration with PIV Loop Commands, Best Practices, Violation Examples)

**Cross-reference check:**
11. Verify `CLAUDE.md` on-demand table has the new `reference/archon-workflow.md` entry
12. Verify `reference/file-structure.md` reflects all moved/new files
13. Search all commands for references to `sections/15_archon_workflow.md` — none should exist (they should reference `reference/archon-workflow.md` or rely on the slim auto-loaded version)

### Level 5: Additional Validation

```powershell
# Verify git can track all new/moved files
git status

# Verify no command still references the old verbose Archon section path incorrectly
Select-String -Path ".claude/commands/*.md" -Pattern "sections/15_archon" -SimpleMatch

# Count total auto-loaded words (target: under 1,600 words / ~2,100 tokens)
$total = 0
$total += (Get-Content "CLAUDE.md" | Measure-Object -Word).Words
Get-ChildItem "sections/*.md" | ForEach-Object { $total += (Get-Content $_.FullName | Measure-Object -Word).Words }
"Total auto-loaded: $total words (~$([math]::Round($total * 1.3)) tokens)"
```

---

## ACCEPTANCE CRITERIA

- [x] Auto-loaded context reduced from ~3,171 tokens to under ~2,200 tokens
- [x] `/planning` command reduced from ~3,374 tokens to under ~2,200 tokens
- [x] `/execute` command reduced from ~1,472 tokens to under ~1,000 tokens
- [x] `/commit` command reduced from ~673 tokens to under ~460 tokens
- [x] `/code-review` reduced from ~876 tokens to under ~600 tokens
- [x] `/code-review-fix` reduced from ~1,138 tokens to under ~720 tokens
- [x] `reference/archon-workflow.md` exists with full original Archon content
- [x] `README.md` exists with Mermaid diagrams and quick start guide
- [x] All cross-references between CLAUDE.md, sections/, and reference/ are valid
- [x] No functionality lost — all commands still work as before, just more concisely
- [x] `reference/file-structure.md` updated to reflect all changes

---

## COMPLETION CHECKLIST

- [x] All tasks completed in order
- [x] Each task validation passed
- [x] All validation commands executed successfully
- [x] Manual validation confirms compressed commands are still clear
- [x] README Mermaid diagrams are well-structured
- [x] Acceptance criteria all met

---

## NOTES

### Key Design Decisions
- Kept the TodoWrite override in auto-loaded context (even though Archon is now on-demand) because it's a critical behavioral rule that must apply in every session
- Chose 30-40% compression target for commands (not 50%+) to maintain readability — compressed commands still need to be understandable to a human reading them
- Used Mermaid over ASCII art for README diagrams because GitHub renders Mermaid natively
- Did not compress `/parallel-e2e` (2,695 tokens) or `/new-worktree` (1,356 tokens) — these are less frequently used and complexity warrants verbosity

### What NOT to Compress (Preserve Exactly)
These elements must survive compression unchanged:
- **Frontmatter blocks** in all commands (description, argument-hint, allowed-tools)
- **`<!-- PLAN-SERIES -->`** marker in `/planning` output section
- **7-field task format** (ACTION, TARGET, IMPLEMENT, PATTERN, IMPORTS, GOTCHA, VALIDATE) in `/planning` Phase 5
- **"Do NOT include Co-Authored-By"** rule in `/commit`
- **"ALWAYS use Archon MCP tools (never TodoWrite)"** in `sections/15_archon_workflow.md`
- **"Do NOT take your PRD and use it as a structured plan"** in `sections/02_piv_loop.md`
- **YAML finding format** in `/code-review` output section
- **Selectivity principle** in `/code-review-fix` (the "May choose NOT to fix" rule)
- **Plan type detection logic** in `/execute` Step 0.5 (standard vs series mode)
- **Template file references** — any line that says "Read template X" or "Use template X"

### Risks
- Risk: Compressed commands may lose nuance that causes the AI to miss edge cases — Mitigation: Manual validation (Level 4) verifies each compressed command still conveys all critical behavior
- Risk: Mermaid diagrams may not render perfectly on first try — Mitigation: Use simple diagram structures, verify after push

### Confidence Score: 8/10
- **Strengths**: All changes are markdown-only (no code risk), clear compression targets, well-understood file structure, proven pattern (we did this exact move with sections 06-14 before)
- **Uncertainties**: Exact word counts after compression may not hit targets precisely — may need iteration. Mermaid diagram aesthetics depend on GitHub's renderer.
- **Mitigations**: Word count targets are approximate — focus on meaningful compression rather than exact numbers. Mermaid can be tweaked after visual review.
