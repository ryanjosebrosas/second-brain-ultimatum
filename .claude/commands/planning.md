---
description: "Create comprehensive feature plan with deep codebase analysis and research"
argument-hint: [feature-description]
allowed-tools: Read, Glob, Grep, Write, Edit, Bash(npm:*), Bash(bun:*), Bash(npx:*), Bash(uv:*), Bash(pip:*), Bash(python:*), Bash(node:*), mcp__archon__manage_project, mcp__archon__manage_task, mcp__archon__find_tasks, mcp__archon__find_projects, mcp__archon__rag_get_available_sources, mcp__archon__rag_search_knowledge_base, mcp__archon__rag_search_code_examples, mcp__archon__rag_list_pages_for_source, mcp__archon__rag_read_full_page, mcp__archon__find_documents, mcp__archon__manage_document, mcp__archon__get_project_features, mcp__archon__health_check, mcp__archon__session_info
---

# Planning: Comprehensive Feature Plan

## Feature Request

$ARGUMENTS

## Mission

Transform this feature request into a **comprehensive implementation plan** through systematic codebase analysis, external research, and strategic planning.

**Core Principle**: The template is the control mechanism. All research fills specific template sections. Nothing is missed because the template specifies what's needed.

**Key Rules**:
- We do NOT write code in this phase. Create a context-rich plan that enables one-pass implementation.
- The completed plan MUST be **700-1000 lines minimum**. You have failed if under 700 lines. Complex features should target 1000. Every section must have feature-specific content, not placeholders.

## Determine Feature Name

Create a concise kebab-case feature name (e.g., "user-authentication", "payment-processing").

**Feature Name**: [create-feature-name]
**Plan File**: `requests/[feature-name]-plan.md`

---

## THE TEMPLATE (CONTROL MECHANISM)

Read `templates/STRUCTURED-PLAN-TEMPLATE.md` now — it defines the exact structure. All 6 phases below fill those template sections.

---

## PHASE 0: Interactive Discovery (Vibe Planning Buddy)

**Goal**: Collaboratively discover scope, approach, and priorities before formal planning.

**Escape hatch**: If the user provides detailed requirements, references an existing plan, or wants to skip discovery — proceed to Phase 1.

**Process**:

1. **Understand the user's level**: Adapt language — technical users get architecture questions, non-technical get outcome-focused questions.
2. **Challenge constructively**: Ask probing questions to sharpen the vision — what problem does this solve? What's the simplest valuable version? Have you seen this done well?
3. **Explore inspiration**: If user has reference projects/repos, analyze their approach. If not, suggest 2-3 approaches with trade-offs.
4. **Scope negotiation**: Push back on scope creep. Suggest vertical slices. Identify hidden complexity.
5. **Confirm readiness**: Summarize agreed scope, list key decisions, get user confirmation before proceeding.

**Rules**: This is a CONVERSATION, not a checklist. Be genuinely curious. If the user has a clear vision, respect that. Spend 3-10 minutes depending on clarity.

---

## PHASE 1: Feature Understanding & Scoping

**Goal**: Fill → Feature Description, User Story, Problem Statement, Solution Statement, Feature Metadata

1. Check memory.md for past decisions about this feature area
2. Parse the feature request. If unclear, ask user to clarify BEFORE continuing.
3. Create User Story: `As a [user], I want [goal], so that [benefit]`
4. State Problem and Solution approach
5. Document Feature Metadata: Type (New/Enhancement/Refactor/Fix), Complexity (Low/Medium/High), Systems Affected, Dependencies

---

## PHASE 2 & 3: Research (RUN IN PARALLEL)

### Research Mode Selection

**If custom agents exist** in `.claude/agents/`: Use **Parallel Research Mode** (5-10 agents)
**If not**: Use **Standard Research Mode** (2 built-in agents)

```bash
ls .claude/agents/research-*.md 2>/dev/null | wc -l
```

---

### PARALLEL RESEARCH MODE (Preferred)

**Step 1: Generate Research Queries**

Break feature into research dimensions. Generate 5-10 focused queries (2-5 keywords each), split between codebase and external.

**Step 2: Launch Parallel Agents**

Launch up to 5 codebase (@research-codebase) + 5 external (@research-external) agents with focused queries. Scale: Low=2-4, Medium=4-6, High=6-10 agents total.

**Step 3: Combine Results**

Combine codebase findings into "Relevant Codebase Files" and "Patterns to Follow". Combine external into "Relevant Documentation". Deduplicate. Verify file references include line numbers.

---

### STANDARD RESEARCH MODE (Fallback)

Launch two Task agents simultaneously:

#### Phase 2: Codebase Intelligence → Task agent (Explore)

**Goal**: Fill → Relevant Codebase Files, New Files to Create, Patterns to Follow

1. **Find similar implementations** — document file paths WITH line numbers
2. **Map integration points** — what existing files change, what new files to create
3. **Extract project patterns** (naming, error handling, logging, types, testing, API, DB)

#### Phase 3: External Research → Task agent (general-purpose)

**Goal**: Fill → Relevant Documentation

1. **Library/framework docs** — find official docs, specific sections needed
2. **Best practices** — expert recommendations for this feature type
3. **Version compatibility** — current versions, breaking changes, migration guides
4. **Gotchas** — what doesn't work as expected

## PHASE 3b: Archon RAG Research (if available)

**Archon** (if available): Search with SHORT queries (2-5 keywords). Use `rag_get_available_sources()`, then `rag_search_knowledge_base(query="...", source_id="...", match_count=5)` and `rag_search_code_examples(query="...", match_count=3)`. Fallback to web search if no results.

### Phase 2c: Memory Search (if memory.md exists)

Read memory.md for past decisions, gotchas, and patterns relevant to this feature.

---

## PHASE 3c: Research Validation

Cross-check key findings — do code patterns still exist? Are library versions current? Are referenced files accurate? Flag contradictions. Do targeted follow-up if critical research is missing.

---

## PHASE 4: Strategic Design & Synthesis

**Goal**: Fill → Implementation Plan (phases), Testing Strategy, Acceptance Criteria

1. **Synthesize validated research** from Phases 2, 3, & 3b
2. **Design implementation approach**: fit with existing architecture, dependency ordering, phases (Foundation → Core → Integration → Testing)
3. **Plan testing strategy**: unit tests, integration tests, edge cases
4. **Define acceptance criteria**: specific, measurable, includes functional requirements + test coverage + pattern compliance

---

## PHASE 4.5: Plan Decomposition Decision

**Decompose if ANY of these apply**:
- High complexity, 4+ phases, 15+ tasks, 3+ systems
- Research produced robust context (extensive RAG results, many codebase patterns, detailed external docs)
- Main plan would exceed 1200 lines as a single file
- User requests it

**If decomposing**:
1. Read `templates/PLAN-OVERVIEW-TEMPLATE.md` and `templates/SUB-PLAN-TEMPLATE.md`
2. Split into sub-plans (1 phase = 1 sub-plan, max 8 tasks each)
3. Assign shared context to overview, per-phase context to sub-plans
4. Each sub-plan MUST be **600-700 lines minimum**. You have failed if a sub-plan is under 600 lines. Include full context: patterns with line numbers, imports, code examples, validation commands, gotchas — everything an agent needs in a fresh conversation.
5. Proceed to Phase 5 in "decomposed mode"

**If NOT decomposing** (default): Proceed to Phase 5 normally (single plan, 700-1000 lines).

---

## PHASE 5: Step-by-Step Task Generation

**Goal**: Fill → STEP-BY-STEP TASKS section

**Critical Rule**: Each task MUST include ALL of these fields:

- **ACTION**: CREATE / UPDATE / ADD / REMOVE / REFACTOR / MIRROR
- **TARGET**: Specific file path
- **IMPLEMENT**: What to implement (code-level detail)
- **PATTERN**: Reference to codebase pattern (file:line)
- **IMPORTS**: Exact imports needed (copy-paste ready)
- **GOTCHA**: Known pitfalls and how to avoid them
- **VALIDATE**: Executable command to verify task completion

Break Phase 4's implementation phases into atomic tasks. Order by dependency. Ensure top-to-bottom execution without backtracking.

**If decomposed mode**: Each sub-plan gets 5-8 tasks max using same 7-field format. Include HANDOFF NOTES at end of each sub-plan. Each sub-plan must be **fully self-contained** (600-700 lines minimum) — duplicate shared context (patterns, imports, architecture notes) rather than referencing the overview. An agent executing a sub-plan in a fresh conversation must have everything it needs without reading the overview.

---

## PHASE 6: Quality Validation & Confidence Score

**Goal**: Fill → Validation Commands, Completion Checklist, Notes (including Confidence Score)

1. **Compile validation commands** (5 levels): Syntax/Style, Unit Tests, Integration Tests, Manual Validation, Additional
2. **Create completion checklist**: all tasks done, validations pass, tests pass, acceptance criteria met
3. **Assess confidence**: Score X/10, strengths, uncertainties, mitigations, key design decisions

---

## OUTPUT

### Standard Mode (default)

Save to: `requests/[feature-name]-plan.md`

Use `templates/STRUCTURED-PLAN-TEMPLATE.md`. Every section must be filled — specific, not generic.

### Decomposed Mode (from Phase 4.5)

<!-- PLAN-SERIES -->

Save to multiple files:
- `requests/{feature}-plan-overview.md` (use `templates/PLAN-OVERVIEW-TEMPLATE.md`)
- `requests/{feature}-plan-01-{phase}.md` through `-NN-` (use `templates/SUB-PLAN-TEMPLATE.md`)

**Sub-plan line requirements**: Each sub-plan MUST be **600-700 lines minimum**. Include full duplicated context (patterns, imports, architecture, gotchas) so each sub-plan is executable standalone.

Include EXECUTION ROUTING in overview: Recommended model per sub-plan (e.g., Sonnet for execution, Opus for planning).

### For Both Modes

**CRITICAL**: This plan is for ANOTHER AGENT in a fresh conversation. It must contain ALL information needed — patterns, file paths with line numbers, exact commands, documentation links.

## Confirmation

Report: feature name, plan file path, complexity, key risks, confidence score, next step (`/execute`).
