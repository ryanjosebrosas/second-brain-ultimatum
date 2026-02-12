---
description: "Create comprehensive feature plan with deep codebase analysis and research"
argument-hint: [feature-description]
---

# Planning: Comprehensive Feature Plan

## Feature Request

$ARGUMENTS

## Mission

Transform this feature request into a **comprehensive implementation plan** through systematic codebase analysis, external research, and strategic planning.

**Core Principle**: The template is the control mechanism. All research is organized to fill specific template sections. Nothing is missed because the template specifies exactly what's needed.

**Key Rules**:
- We do NOT write code in this phase. Our goal is to create a context-rich plan that enables one-pass implementation success.
- The completed plan MUST be **500-700 lines**. Be concise but comprehensive. You have failed if the plan is outside this range.

## Determine Feature Name

Based on the feature description, create a concise kebab-case feature name (e.g., "user-authentication", "payment-processing", "data-export").

**Feature Name**: [create-feature-name]
**Plan File**: `requests/[feature-name]-plan.md`

---

## THE TEMPLATE (CONTROL MECHANISM)

The plan you create MUST fill every section from `templates/STRUCTURED-PLAN-TEMPLATE.md`. Read that template now — it defines the exact structure. All 6 phases below exist to fill those template sections systematically.

---

## PHASE 0: Interactive Discovery (Vibe Planning Buddy)

**Goal**: Collaboratively discover the right scope, approach, and priorities before formal planning begins.

**Escape hatch**: If the user provides a detailed feature description, references an existing plan, or explicitly says they want to skip discovery — proceed directly to Phase 1. This phase is for discovery, not bureaucracy.

**Process**:

1. **Understand the user's level**: Ask about their experience with this type of feature. Adapt your language — technical users get architecture questions, non-technical users get outcome-focused questions.

2. **Challenge the idea constructively**: Ask probing questions to sharpen the vision:
   - "What problem does this solve for your users?"
   - "What's the simplest version that would still be valuable?"
   - "What happens if we DON'T build this?"
   - "Have you seen this done well somewhere? Share a link or repo and I'll analyze their approach."

3. **Explore inspiration**: If the user has reference projects or repos:
   - Ask for the GitHub repo URL or example
   - Analyze their implementation approach (file structure, patterns, tech choices)
   - Identify what to adopt vs what to do differently
   - If no inspiration: suggest 2-3 approaches and explain trade-offs

4. **Scope negotiation**: Help find the right scope:
   - Push back on scope creep: "That sounds like 3 features — which one delivers the most value?"
   - Suggest vertical slices: "Could we build just the [core thing] first and add [extras] later?"
   - Identify hidden complexity: "This looks simple but [X] usually causes problems — let me check."

5. **Confirm readiness**: Before proceeding to Phase 1:
   - Summarize the agreed scope (1-3 sentences)
   - List key decisions made during discovery
   - Ask: "Does this capture what we're building? Anything I'm missing?"
   - Only proceed after user confirms

**Rules for Phase 0**:
- This is a CONVERSATION, not a checklist — adapt to the user's responses
- Be genuinely curious and challenging, not just asking questions to check boxes
- If the user has a clear vision and wants to move fast, respect that
- Spend 3-10 minutes here depending on clarity. Don't rush, but don't over-discuss.

---

## PHASE 1: Feature Understanding & Scoping

**Goal**: Fill these template sections → Feature Description, User Story, Problem Statement, Solution Statement, Feature Metadata

Using context from Phase 0 discovery (if conducted), proceed to scope the feature formally.

**Process**:

1. Before scoping, check memory.md (if it exists) for past decisions about this feature area
2. Parse the feature request thoroughly
3. If requirements are unclear, ask the user to clarify BEFORE continuing
4. Create User Story: `As a [user], I want [goal], so that [benefit]`
5. Clearly state the Problem being solved
6. Describe the Solution approach
7. Document Feature Metadata:
   - **Feature Type**: New Capability / Enhancement / Refactor / Bug Fix
   - **Estimated Complexity**: Low / Medium / High
   - **Primary Systems Affected**: list all components/services
   - **Dependencies**: external libraries or services required

**Validation**: Can someone understand the feature without additional questions?

---

## PHASE 2 & 3: Research (RUN IN PARALLEL)

### Research Mode Selection

**If custom research agents exist** in `.claude/agents/`:
- Use **Parallel Research Mode** (5-10 specialized agents, route to claude-zai)
- Agents: research-codebase, research-external

**If no custom research agents exist**:
- Use **Standard Research Mode** (2 built-in agents — Explore + general-purpose)

Check for agents:
```bash
ls .claude/agents/research-*.md 2>/dev/null | wc -l
```

---

### PARALLEL RESEARCH MODE (Preferred)

**Step 1: Generate Research Queries**

Before launching agents, analyze the feature and generate focused research queries:

1. Break the feature into research dimensions:
   - What codebase patterns exist? (naming, error handling, testing, API, DB, types)
   - What external docs are needed? (framework, library, best practices, migration)
2. Generate 5-10 focused queries (2-5 keywords each), split between codebase and external
3. Assign each query to either a research-codebase or research-external agent instance

**Example query generation** for a "user authentication" feature:
- Codebase queries: "auth patterns middleware", "session model schema", "login route handler", "auth test fixtures", "user service methods"
- External queries: "JWT token refresh flow", "bcrypt password hashing", "OAuth2 PKCE implementation", "session security best practices"

**Step 2: Launch Parallel Agents**

Launch up to 10 Task agents simultaneously (max 10 concurrent per subagent limits):

**Codebase Research Agents** (up to 5 × @research-codebase):
- Agent C1: [focused codebase query 1]
- Agent C2: [focused codebase query 2]
- Agent C3: [focused codebase query 3]
- Agent C4: [focused codebase query 4]
- Agent C5: [focused codebase query 5]

**External Research Agents** (up to 5 × @research-external):
- Agent E1: [focused external query 1]
- Agent E2: [focused external query 2]
- Agent E3: [focused external query 3]
- Agent E4: [focused external query 4]
- Agent E5: [focused external query 5]

**Execution**: All agents run in parallel via claude-zai instance. Each agent returns structured findings in its standard output format.

**Scale guideline**:
- Simple features (Low complexity): 2-4 agents total
- Medium features: 4-6 agents total
- Complex features (High complexity): 6-10 agents total

**Step 3: Combine Research Results**

After all agents complete:
1. Wait for all agents to return results
2. Combine codebase findings into unified "Relevant Codebase Files" and "Patterns to Follow" sections
3. Combine external findings into unified "Relevant Documentation" section
4. Remove duplicate findings (same file/doc found by multiple agents)
5. Verify all file references include line numbers (codebase) and section anchors (external)

---

### STANDARD RESEARCH MODE (Fallback)

Launch two Task agents simultaneously for 40-50% faster research:

#### Phase 2: Codebase Intelligence → Task agent (Explore)

**Goal**: Fill → Relevant Codebase Files, New Files to Create, Patterns to Follow

The Explore agent must:

1. **Find similar implementations**
   - Search for existing code doing similar things
   - Document file paths WITH line numbers
   - Extract pattern examples from actual project code

2. **Map integration points**
   - What existing files must be modified?
   - What new files must be created and where?
   - How do new components connect to existing ones?

3. **Extract project patterns** (with code examples from the project)
   - Naming conventions
   - Error handling approach
   - Logging patterns
   - Type/model patterns
   - Testing patterns
   - API/routing patterns (if applicable)
   - Database/model patterns (if applicable)

**Required output format**:
```
### Relevant Codebase Files
- `path/to/file` (lines X-Y) - Why: Contains pattern for Z that we'll mirror

### New Files to Create
- `path/to/new_file` - Purpose description

### Patterns to Follow
**Pattern Name**:
[code snippet from actual project]
- Why this pattern: explanation
- Common gotchas: warnings
```

**Phase 2 Validation**: Every file reference has line numbers. Every pattern has a code example from the project. No generic references.

#### Phase 3: External Research → Task agent (general-purpose)

**Goal**: Fill → Relevant Documentation

The research agent must:

1. **Library/framework documentation** — find official docs, identify specific sections needed
2. **Best practices** — what do experts recommend for this feature type?
3. **Version compatibility** — current library versions, breaking changes, migration guides
4. **Gotchas and known issues** — what doesn't work as expected?

**Required output format**:
```
### Relevant Documentation
- [Documentation Title](https://example.com/docs#section)
  - Specific section: [Section Name]
  - Why: Required for implementing X
```

**Phase 3 Validation**: Every documentation link includes a specific section anchor. Every reference explains WHY it's needed.

## PHASE 3b: Archon RAG Research (if available, run in parallel with Phase 3)

**If Archon RAG available (PRIORITIZED over generic web search):**

1. **Get indexed sources**: `rag_get_available_sources()` — returns list of curated documentation
2. **For each technology in the feature**: Search the knowledge base with SHORT queries (2-5 keywords)
   - Example: `rag_search_knowledge_base(query="React hooks", source_id="src_reactdocs", match_count=5)`
   - Example: `rag_search_code_examples(query="authentication JWT", match_count=3)`
3. **Critical Rule**: Keep queries SHORT — 2-5 keywords maximum for best vector search results
4. **Fallback**: If RAG returns no results, continue to Phase 3 generic research

**If Archon RAG unavailable:**
- Skip Phase 3b, continue with Phase 3 external research as normal

**Required output format**:
```
### Relevant Documentation (from Archon RAG)
- [Documentation Title](source_url)
  - Source ID: src_abc123
  - Why: Required for implementing X
```

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

---

## PHASE 3c: Research Validation

**Goal**: Ensure all research from Phases 2, 3, and vibe planning is accurate before building the plan on top of it.

**Process**:

1. Read any research reports, notes, or context gathered during vibe planning
2. Cross-check key findings — do code patterns still exist? Are library versions current? Are referenced files accurate?
3. Flag any contradictions between research sources
4. If critical research is missing or outdated, do targeted follow-up research now

**Validation**: No plan section should be built on unverified research. Better to spend 2 minutes validating than to build a plan on wrong assumptions.

---

## PHASE 4: Strategic Design & Synthesis

**Goal**: Fill → Implementation Plan (phases), Testing Strategy, Acceptance Criteria

**Process**:

1. **Synthesize validated research** from Phases 2, 3, & 3b
2. **Design implementation approach**:
   - How do new components fit with existing architecture?
   - What needs to be built first? (dependency ordering)
   - Break into phases: Foundation → Core → Integration → Testing
3. **Plan testing strategy**:
   - Unit tests needed (what to test, which patterns to follow)
   - Integration tests needed (what to verify end-to-end)
   - Edge cases to test (what could break?)
4. **Define acceptance criteria**:
   - Specific, measurable criteria for completion
   - Must include functional requirements, test coverage, and pattern compliance

**Validation**: Clear phase breakdown. Each phase has a clear purpose. No ambiguity about implementation order.

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

**Process**:

1. Break down Phase 4's implementation phases into atomic tasks
2. Order by dependency (what must happen first)
3. For EACH task, fill all fields above — no exceptions
4. Ensure tasks can be executed top-to-bottom without backtracking

**Example format**:
```markdown
### CREATE path/to/new_service.ext

- **IMPLEMENT**: Class/function with specific methods/behavior
- **PATTERN**: Follow pattern in path/to/existing.ext:45-62
- **IMPORTS**:
  [exact import statements]
- **GOTCHA**: [specific pitfall for this project]
- **VALIDATE**: `[exact command to verify]`
```

**Validation**: Every task is atomic. Every task has a validation command. No task leaves uncertainty about what to implement.

---

## PHASE 6: Quality Validation & Confidence Score

**Goal**: Fill → Validation Commands, Completion Checklist, Notes (including Confidence Score)

**Process**:

1. **Compile validation commands** (5 levels):
   - Level 1: Syntax & Style (linting, formatting)
   - Level 2: Unit Tests
   - Level 3: Integration Tests
   - Level 4: Manual Validation (feature-specific testing steps)
   - Level 5: Additional Validation (optional — MCP servers, CLI tools, etc.)

2. **Create completion checklist**:
   - All tasks completed in order
   - Each task validation passed
   - Full test suite passes
   - No linting/type checking errors
   - Manual testing confirms feature works
   - Acceptance criteria all met

3. **Assess confidence and risks**:
   - **Confidence Score**: X/10 that execution will succeed on first attempt
   - **Strengths**: What's clear and well-defined
   - **Uncertainties**: What might change or cause issues
   - **Mitigations**: How to handle the uncertainties
   - **Key Design Decisions**: Why this approach over alternatives

**Validation**: Every command is copy-paste ready and executable. Acceptance criteria are measurable. Confidence score is justified with reasoning.

---

## OUTPUT

Save the completed plan to: `requests/[feature-name]-plan.md`

Use the template structure from `templates/STRUCTURED-PLAN-TEMPLATE.md`. Every section must be filled — specific to this feature, not generic placeholders.

**CRITICAL**: This plan is for ANOTHER AGENT to execute in a fresh conversation. It must contain ALL information needed — patterns, file paths with line numbers, exact commands, documentation links. The execution agent should succeed without additional research or clarification.

## Confirmation

After creating the plan, report:
- Feature name and plan file path
- Complexity assessment
- Key implementation risks
- Confidence score for one-pass success
- **Next step**: Run `/execute requests/[feature-name]-plan.md` to implement
