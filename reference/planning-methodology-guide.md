# Planning Methodology: 6-Phase Systematic Planning

This guide explains **how to plan features systematically** — covering the 6-phase planning methodology, PRD creation and scoping, Vertical Slice Architecture, tool docstring design, and research prompt strategies — going deeper than the always-loaded overview in `sections/02_piv_loop.md`.

---

## 1. What This Guide Covers

### The Journey from Automation to Methodology

The System Foundations guide established the **why** — the system gap and learning architecture. The PIV Loop Practice guide taught the **how** — the PIV Loop in practice. The Global Rules Optimization guide taught **how to build** — modular CLAUDE.md and strategic context loading. The Command Design Framework guide taught **how to automate** — slash commands and the INPUT→PROCESS→OUTPUT framework. This guide teaches you **how to transform planning** from ad-hoc conversation into a systematic methodology that produces implementation-ready plans.

This is the planning revolution. You're not learning new tools or automation — you're learning the methodology that makes the `/planning` command produce plans with 85%+ first-pass implementation success.

### What You'll Learn

- **The 6-phase planning process** — systematic research, synthesis, and task generation
- **PRD creation** — Layer 1's "what to build" document with 14-section structure
- **Vertical Slice Architecture (VSA)** — the core/shared/features decision framework for AI codebases
- **Tool docstrings for agents** — writing documentation that LLMs use for tool selection
- **Research prompt design** — specific vs vague prompts and the 5 qualities that produce actionable results
- **Plan quality constraints** — why 700-1000 lines, per-task format, and template-driven completeness
- **Measuring planning success** — before/after metrics proving the transformation

### The Core Insight

> **Quality of plan = success of implementation.**

A plan with all relevant patterns documented, integration points mapped, external research completed, strategic decisions pre-made, and validation commands at every step enables one-pass implementation without surprises.

### The Before/After Transformation

**Before (ad-hoc planning)**: Variable planning time, vague plans, 30-50% of implementation time spent on mid-implementation research, ~40% first-pass success rate.

**After (6-phase systematic)**: Predictable 60-120 minute planning sessions, specific plans with file:line references, <10% mid-implementation research, 85%+ first-pass success rate.

### The Running Example

This guide uses **Paddy** — an AI agent for natural language interaction with Obsidian vaults — as its running example. This real-world project demonstrates VSA, tool design, and systematic planning throughout the guide.

---

## 2. The Running Example: Obsidian AI Agent

### Project Overview

Paddy is a self-hosted AI agent that enables natural language interaction with Obsidian knowledge vaults. It serves as the concrete project through which all concepts in this guide are demonstrated.

### Technology Stack

| Component | Choice |
|-----------|--------|
| Backend | FastAPI with OpenAI-compatible endpoints |
| Agent Framework | Pydantic AI for orchestration |
| Architecture | Vertical Slice Architecture (VSA) |
| LLM Support | Provider-agnostic (Anthropic, OpenAI, Google, local models) |
| Vault Access | Docker volume mounting |
| Package Manager | UV |

### Core Principles

1. **Self-hosted & Simple** — runs on your machine, no cloud dependency
2. **Provider-agnostic** — swap LLM providers without code changes
3. **Transparent** — clear reasoning, visible tool calls
4. **Workflow-oriented** — tools match how users think about their vault
5. **Type-safe** — leverages Pydantic AI's type system throughout

### MVP Scope

**In Scope**: Natural language querying (semantic search), reading notes with context, creating/updating/appending notes, folder management, bulk operations, OpenAI-compatible API endpoint.

**Out of Scope**: Cloud hosting, multi-user support, conversation persistence database, advanced features (embeddings, RAG), mobile support.

### The Three-Tool Architecture

Following Anthropic's principle: **"Fewer, smarter tools beat many simple ones"**

| Tool | Purpose | Key Feature |
|------|---------|-------------|
| `obsidian_query_vault` | Discovery & Search (read-only) | `response_format` parameter for token efficiency |
| `obsidian_vault_manager` | All Modifications (notes + folders + bulk) | `confirm_destructive` safety mechanism |
| `obsidian_get_context` | Reading with Context | Related notes, backlinks, daily notes |

### Tool Design Philosophy

- **Consolidate** operations into high-impact tools (3 tools, not 15)
- **Match user workflows** — tools mirror how users think, not CRUD operations
- **Clear namespacing** — all tools prefixed with `obsidian_`
- **Response format flexibility** — control token usage per call
- **Natural language over IDs** — human-readable paths, not database identifiers
- **Helpful error messages** — actionable guidance when things go wrong

This example matters because it demonstrates every concept in this guide in a real project: VSA organizes the code, tool docstrings guide the agent, and the 6-phase process plans each feature.

---

## 3. Layer 1: Creating Your PRD

### What the PRD Is

The PRD (Product Requirements Document) defines **what** to build. It complements CLAUDE.md (which defines **how** to build). Together they form the core of Layer 1 planning.

As covered in `sections/02_piv_loop.md`, Layer 1 is done once and updated rarely. The PRD is the anchor document — it feeds into global rules, on-demand context, and every Layer 2 feature plan.

### The 14-Section PRD Structure

| Section | What It Contains |
|---------|-----------------|
| Executive Summary | Product name, mission, MVP goal in one sentence |
| Mission & Core Principles | Why this product exists, guiding principles |
| Target Users | Who benefits, technical comfort level |
| MVP Scope | In-scope (checkmarks) and out-of-scope (X marks) |
| User Stories | "As a... I want... So that..." for primary and technical users |
| Core Architecture & Patterns | Architecture choice (VSA, layered), directory structure |
| Tools | Tool specifications, input/output formats, examples |
| Technology Stack | Backend, frontend, dependencies, deployment |
| Security & Configuration | Auth approach, env variables, deployment strategy |
| API Specification | Endpoints, request/response formats |
| Success Criteria | What "done" looks like, quality indicators |
| Implementation Phases | Phased delivery with validation per phase |
| Future Considerations | Post-MVP enhancements, integration opportunities |
| Risks & Mitigations | Identified risks and how to handle them |

Use `templates/PRD-TEMPLATE.md` for the actual template.

### Tool Design Document

For projects involving AI tools, create a **separate** document for detailed tool specifications. The PRD stays high-level; tool designs are implementation details.

Each tool specification includes: purpose and use cases, when to use vs when NOT to use, parameters with choice guidance, response format, performance notes, and 2-4 realistic examples.

**Why separate**: The PRD defines product scope. Tool designs define implementation specifics. Mixing them bloats the PRD and makes both harder to maintain.

### When to Create a PRD

**Greenfield projects**: PRD first → global rules → on-demand context → reconcile all three.

**Existing projects**: Analyze codebase → create global rules → create on-demand context. Skip PRD if scope is already clear from the existing product.

---

## 4. Vertical Slice Architecture for AI Codebases

### The Three Zones

VSA organizes code into three zones, each with a clear decision rule for what belongs there.

### Zone 1: `core/` — Universal Infrastructure

**Decision rule**: "Would this code be needed if ALL feature slices were removed?" If yes → core.

**Typical contents**:

| File | Purpose |
|------|---------|
| `config.py` | Application configuration (pydantic-settings) |
| `database.py` | Database connection & session management |
| `logging.py` | Structured logging setup |
| `middleware.py` | Request/response middleware |
| `exceptions.py` | Base exception classes |
| `dependencies.py` | Global FastAPI dependencies |
| `events.py` | Application lifecycle events |

**Why this matters for AI**: Configuration scattered across files wastes tokens. Centralizing in `core/config.py` gives AI a single source of truth.

### Zone 2: `shared/` — The Three-Feature Rule

**Decision rule**: Code moves to shared when **three or more** feature slices need it.

- **One instance**: Feature-specific — keep it in the feature
- **Two instances**: Might be coincidence — duplicate it (add comment noting duplication)
- **Three instances**: Proven pattern — extract to `shared/` and refactor both originals

```
1. First feature: Write validation inline
2. Second feature: Duplicate (add comment noting duplication)
3. Third feature: Extract to shared/ and refactor
```

**Why three?** Two instances might solve different underlying problems that happen to look similar. Three instances prove a genuine shared pattern worth abstracting. Premature extraction creates coupling between features that should remain independent.

### Zone 3: `features/` — Self-Contained Domains

Each feature is a complete vertical slice with its own directory:

```
app/products/
├── routes.py          # FastAPI endpoints
├── service.py         # Business logic
├── repository.py      # Database operations
├── models.py          # SQLAlchemy models
├── schemas.py         # Pydantic request/response
├── exceptions.py      # Feature-specific exceptions
├── test_routes.py     # Endpoint tests
├── test_service.py    # Business logic tests
└── README.md          # Feature documentation
```

**Flow**: Routes → Service → Repository → Database.

**Not every feature needs every file.** Start with `routes.py`, `service.py`, `schemas.py`. Add `repository.py`, `models.py`, etc. as needed. Optional files like `validators.py`, `cache.py`, and `tasks.py` are added only when the feature requires them.

### When to Duplicate vs Extract (DRY)

| Duplicate When | Extract to Shared When |
|---------------|----------------------|
| Used by 1-2 features (wait for third) | Used by 3+ features |
| Slight variations exist | Identical logic |
| Feature-specific context | Infrastructure-level (base schemas, mixins) |
| Uncertain stability | Stable, proven interface |

### Core Infrastructure Patterns

**Structured Logging with Correlation IDs**: Standard logging is hard for AI to parse. Use structured JSON logging with `structlog` and correlation IDs so AI can filter logs by `request_id` to see complete request lifecycles.

Event naming pattern: `{domain}.{action}.{status}` — e.g., `product.create.started`, `tool.execution.failed`.

**Request Middleware**: Every request gets a unique ID via middleware. Include `X-Request-ID` header propagation for end-to-end tracing.

### LLM Integration Placement

**Small apps** (AI is the core purpose): Put LLM infrastructure in `core/llm.py`.

**Larger apps** (multiple AI features): Create a dedicated `llm/` module:

```
app/llm/
├── clients.py     # LLM client wrappers (provider abstraction)
├── prompts.py     # Centralized prompt management
├── tools.py       # Tool registry for function calling
└── messages.py    # Message formatting utilities
```

Feature-specific AI logic goes in the feature slice (e.g., `app/products/ai.py`), not in the shared LLM module.

### Why VSA for AI Coding

Clear boundaries, predictable structure, self-contained features = AI navigates easily. The `core/shared/features` decision framework eliminates the "where does this go?" question that causes AI to make inconsistent organizational decisions.

---

## 5. Writing Tool Docstrings for Agents

### The Philosophy

Standard docstrings document **what code does** for human developers. Agent tool docstrings guide **when to use the tool and how** for LLM reasoning during tool selection. This is a fundamentally different audience with different needs.

### Seven Required Elements

| # | Element | Purpose |
|---|---------|---------|
| 1 | One-line summary | Clear primary purpose statement |
| 2 | "Use this when" | 3-5 specific scenarios (affirmative guidance) |
| 3 | "Do NOT use this for" | Redirect to OTHER tools (prevents confusion) |
| 4 | Args with WHY | Each param with type + guidance on different values |
| 5 | Returns | Format and structure details for parsing |
| 6 | Performance notes | Token usage, execution time, resource limits |
| 7 | Examples | 2-4 realistic scenarios (not "foo"/"bar") |

Element 3 ("Do NOT use this for") is the **most commonly missed and most important**. Without negative guidance, agents frequently choose the wrong tool because they can't distinguish between tools with overlapping descriptions.

### Common Anti-Patterns and Fixes

**Vague guidance → Specific guidance**:
```python
# BAD: "Use this when you need to work with notes."
# GOOD: "Use this when you need to read content of a single known note,
#        extract metadata from frontmatter, or verify a note exists."
```

**Missing negative guidance → Clear redirects**:
```python
# BAD: No "Do NOT use" section
# GOOD: "Do NOT use this for searching notes (use obsidian_vault_query),
#        batch reading (use batch mode), or graph analysis (use obsidian_graph_analyze)"
```

**Toy examples → Realistic examples**:
```python
# BAD: read_note("test.md"); read_note("foo.md")
# GOOD: read_note("daily/2025-01-15.md", response_format="minimal")  # Check daily note metadata
#        read_note("projects/website-redesign.md")  # Get project overview
```

### Tool Consolidation Principle

**Fragmented** (agent must orchestrate 3 separate calls):
```python
read_note(path)                      # Tool 1
patch_note(path, old, new)           # Tool 2
update_metadata(path, metadata)      # Tool 3
```

**Consolidated** (single tool call with parameters):
```python
obsidian_note_manage(
    path=path, operation="patch",
    find_replace=(old, new), metadata_updates=metadata
)
```

Fewer, smarter tools reduce agent orchestration complexity and error rates. Each tool call is an opportunity for the agent to make a mistake — minimize the number of calls needed per workflow.

---

## 6. The 6-Phase Planning Process

### Overview

As covered in `sections/02_piv_loop.md`, Layer 2 planning involves vibe planning followed by a structured plan. This guide transforms the structured planning step into a systematic 6-phase process:

```
Phase 1: Feature Understanding → Phase 2+3: Parallel Research → Phase 4: Design → Phase 5: Tasks → Phase 6: Validation
```

### Phase 1: Feature Understanding & Scoping

**Goal**: Fill template sections: Feature Description, User Story, Problem Statement, Solution Statement, Feature Metadata.

**Process**: Parse the feature request. Determine feature type (New/Enhancement/Refactor/Bug), complexity (Low/Medium/High), systems affected, and success criteria. Create user story: "As [user], I want [goal], so that [benefit]." State the problem and solution.

**Validation**: "Can someone understand the feature without additional questions?"

### Phase 2: Codebase Intelligence Gathering

**Goal**: Fill template sections: Relevant Codebase Files (with line numbers and WHY), New Files to Create, Patterns to Follow (with code examples from the project).

**Uses**: Explore agent (runs in parallel with Phase 3).

**Three activities**:
1. **Find similar implementations** — search for existing code doing similar things, document file paths with line numbers, extract pattern examples
2. **Map integration points** — files to modify, new files to create, where components connect
3. **Extract project patterns** — naming, error handling, logging, types, testing, database, API patterns from actual codebase code

**Output format**: File paths with line numbers + code examples from the project. Every reference must include line numbers. Every pattern must include a code snippet from the actual project.

### Phase 3: External Research & Documentation

**Goal**: Fill template section: Relevant Documentation (with section anchors and WHY).

**Uses**: General-purpose agent (runs in parallel with Phase 2 — saves 40-50% time).

**Four activities**:
1. **Library/framework documentation** — official docs with specific section links
2. **Best practices** — expert recommendations, common pitfalls
3. **Version compatibility** — breaking changes, migration guides
4. **Gotchas and known issues** — what doesn't work as expected

**Output format**: Links with section anchors + WHY explanations. Every link must include a section anchor. Every reference must explain why it's needed.

Research prompts must be SPECIFIC (see Section 7 for detailed guidance).

### Phase 4: Strategic Design & Decision-Making

**Goal**: Fill template sections: Implementation Plan (phases), Testing Strategy, Acceptance Criteria.

**Process**: Synthesize validated research from Phases 2-3. Design how new components fit existing architecture. Identify implementation phases (Foundation → Core → Integration → Testing). Plan testing strategy. Define measurable acceptance criteria.

**Validation**: Clear phase breakdown with no ambiguity.

### Phase 5: Comprehensive Plan Generation

**Goal**: Fill template section: Step-by-Step Tasks.

**THE KEY INNOVATION**: Each task MUST include all seven elements:

```markdown
### CREATE app/features/x/service.py

- **IMPLEMENT**: Class XService with method do_something()
- **PATTERN**: Follow pattern in app/core/logging.py:45-62
- **IMPORTS**:
  ```python
  from pydantic_ai import Agent
  from app.core.logging import get_logger
  ```
- **GOTCHA**: Don't pass system_prompt to agent.run(), already initialized
- **VALIDATE**: `uv run mypy app/features/x/service.py`
```

This per-task format with ACTION/IMPLEMENT/PATTERN/IMPORTS/GOTCHA/VALIDATE is this guide's single biggest contribution. It eliminates execution ambiguity entirely — the executing agent has everything needed for each task without guessing.

**Validation**: Every task is atomic. Every task has a validation command. No uncertainty.

### Phase 6: Plan Quality Validation

**Goal**: Fill template sections: Validation Commands, Completion Checklist, Notes (risks, confidence).

**Process**: Define validation commands at all 5 levels (syntax, types, unit, integration, manual). Create completion checklist. Assess confidence with a scored rating including strengths, uncertainties, and mitigations.

**Validation**: Every command is copy-paste ready. Every criterion is measurable.

### Template as Control Mechanism

All 6 phases exist to fill specific template sections. Nothing is missed because the template specifies exactly what's needed. Without the template, research is ad-hoc and gaps are discovered during implementation. With it, research is organized and plans are standardized.

See `templates/STRUCTURED-PLAN-TEMPLATE.md` for the complete template structure.

---

## 7. Research Prompt Design

### Why Specificity Matters

Vague prompts produce vague results. Specific prompts with concrete deliverables produce actionable insights. This principle applies to Phase 3 (External Research) but also to any research task.

### Bad Example (3 lines)

```
Research the Obsidian plugin
```

No direction, no deliverables, no structure. The agent will return a generic overview that doesn't help implementation.

### Good Example (structured)

```
Research Obsidian Copilot plugin's OpenAI-compatible API integration.

CRITICAL: Find and analyze actual SOURCE CODE.

Part 1: Message Content Format
1. Search for ChatOpenRouter.ts
2. Find message construction logic
3. Determine content format variations

Part 2: Endpoint Path Construction
1. Find OpenAI SDK initialization
2. Determine path construction
3. Verify with actual examples

Report Format:
1. Code snippet showing actual format from plugin
2. Exact URL construction logic
3. Implementation requirements (Pydantic models needed)

IMPORTANT: Include actual code snippets. Generic descriptions insufficient.
```

### Five Qualities That Make Research Prompts Work

| Quality | What It Means | Example |
|---------|--------------|---------|
| Explicit source code directive | Tell agent to find actual code, not just docs | "Find and analyze actual SOURCE CODE" |
| Concrete deliverables | Specify what the output must contain | "Code snippet showing actual format" |
| Structured investigation | Break research into numbered parts | "Part 1: Message Format, Part 2: Endpoint Path" |
| Context for WHY | Explain the problem being solved | "We need this to build OpenAI-compatible endpoint" |
| Cross-reference strategy | Require multiple sources | "Verify documentation claims against source code" |

### The Principle

> Documentation tells you WHAT. Source code shows you HOW. Always verify documentation claims against actual implementation.

This is especially important for integrations and third-party libraries where documentation may be outdated or incomplete.

---

## 8. Plan Quality & Conciseness

### The Complete Template Structure

Plans follow this exact section structure (see `templates/STRUCTURED-PLAN-TEMPLATE.md` for the full template):

- Feature Description → User Story → Problem Statement → Solution Statement → Feature Metadata
- Context References: Relevant Codebase Files, New Files to Create, Relevant Documentation, Patterns to Follow
- Implementation Plan (phased)
- Step-by-Step Tasks (per-task format)
- Testing Strategy (unit, integration, edge cases)
- Validation Commands (5 levels)
- Acceptance Criteria → Completion Checklist → Notes (decisions, confidence score)

### The 700-1000 Line Constraint

Plans should be **700-1000 lines**. Not 300 (too shallow) and not 1500+ (information overload). Sub-plans in decomposed mode should be **500-700 lines**.

**Why this range matters**:
- **700 is the floor** — below 700, template sections get generic placeholders instead of feature-specific content with file:line references and code examples
- **Prevents information overload** — agents have limited context windows too
- **Stays scannable** — humans can review the plan in one sitting
- **Fits context** — leaves room for implementation context alongside the plan
- **Sub-plans need 500+** — each sub-plan must be self-contained since the execution agent has no memory of previous sub-plans

### How to Achieve Conciseness

| Technique | Instead Of | Do This |
|-----------|-----------|---------|
| File references | Copying 30 lines of code | `Follow pattern in app/core/logging.py:45-62` |
| Tables | Paragraph descriptions | Compact table with columns |
| Bullets | Narrative paragraphs | Concise bullet points |
| Doc links | Pasting documentation | `See [Pydantic AI docs](url#section)` |
| Line numbers | Vague "see the auth module" | `src/auth/jwt.py:45-62` |

### Per-Task Format Recap

The IMPLEMENT/PATTERN/IMPORTS/GOTCHA/VALIDATE format (from Section 6, Phase 5) is the engine of plan quality. It transforms vague instructions into executable specifications:

**Before**: "Create the service layer"
**After**: CREATE with IMPLEMENT (what to build), PATTERN (which code to follow), IMPORTS (copy-paste ready), GOTCHA (what to avoid), VALIDATE (how to verify)

### Planning Approach Comparison

| Approach | Method | Success Rate |
|----------|--------|-------------|
| Template-First | Fill template with initial thoughts, skip research | ~30% |
| Sequential Research | Research codebase → research external → plan | ~50% |
| Parallel Research + Systematic | Parallel codebase + external research, synthesized design | ~85%+ |

The 6-phase process uses the third approach. Parallel research (Phases 2+3 running simultaneously via subagents) combined with systematic synthesis (Phase 4) and template-driven task generation (Phase 5) produces the highest success rates.

---

## 9. Measuring Planning Success

### Success Metrics: Before vs After

| Metric | Before (Ad-Hoc) | After (6-Phase) | Goal |
|--------|-----------------|-----------------|------|
| Planning time | Variable | 60-120 min | Predictable |
| Plan clarity | Vague | Specific | Crystal clear |
| Mid-implementation research | 30-50% of time | <10% of time | Almost zero |
| First-pass success | ~40% | 85%+ | High confidence |
| Pattern consistency | Inconsistent | Consistent | Project standard |
| Test coverage | Missed cases | Comprehensive | 80%+ |
| Integration issues | Common | Rare | Prevention |
| Rework/refactoring | Frequent | Minimal | One-pass |

### The Real-World Transformation

**Before (ad-hoc planning)**:
```
"Let's add email notifications" → 60 min: "Where should this go?"
→ 120 min: "What email library?" → 180 min: "But there's existing event handling..."
Result: 3 hours, plan keeps changing, missing context. Success rate: ~40%
```

**After (systematic planning)**:
```
/planning "Add email notifications"
→ Phase 1: Clarify (2 min) → Phase 2-3: Research parallel (15 min)
→ Phase 4: Design (10 min) → Phase 5: Generate plan (20 min) → Phase 6: Validate (5 min)
Total: 60 minutes. Then: 3 hours clean implementation without surprises. Success rate: 85%+
```

The plan includes: integration with existing event system (found in Phase 2), email library choice with justification (Phase 3), configuration following project patterns (Phase 2), validation commands per task, and an 8/10 confidence score with reasoning.

### Why This Works: 7 Principles

1. **Context is king** — more context = fewer surprises = better implementation
2. **Patterns not invention** — following existing patterns = consistency and fewer bugs
3. **Strategic before tactical** — design decisions BEFORE task specification = coherent plan
4. **Research parallelized** — simultaneous codebase + external research = 40-50% time savings
5. **Validation built-in** — every phase produces verifiable outputs = confidence
6. **Specificity over generality** — file paths > descriptions, line numbers > vague references
7. **Template driven** — every plan has identical structure = nothing missed

---

## 10. Practical Exercises

### Exercise: Building Your Planning Command

**The challenge**: Transform your manual planning workflow into a reusable slash command that produces consistent, implementation-ready plans.

### The Manual Workflow Pattern

Before commands, planning follows a manual conversation pattern:

```
/prime → "Read PRD, what's next?" → "I disagree, let's do X" →
"Research Pydantic AI docs..." → "Also read vsa-patterns.md..." →
/plan-new "Specific constraints..." → Manual review
```

This works but is repetitive. Every planning session repeats the same steps in roughly the same order. The question: can you template this workflow?

### Two Approaches

**Approach 1: Template-Driven (Claude Code style)**

- 6 explicit phases, each with a clear goal (which template sections to fill)
- Each phase has validation criteria
- Template structure shown upfront as the target output
- Phases explicitly separated: Feature Understanding → Codebase Intelligence (Explore agent) → External Research (general-purpose agent) → Strategic Design → Task Generation → Quality Validation

**Approach 2: Mission-Driven (alternative style)**

- "Mission" framing instead of rigid phases
- Uses specialized subagents "when beneficial" (not always)
- More flexible, adaptive depth based on feature complexity
- More narrative, less structured

### Key Similarities and Differences

**Same**: Both use the 6-phase core, same template structure, same validation criteria.

**Different**: Structure vs flexibility, explicit phases vs adaptive depth. Template-driven produces more consistent output. Mission-driven feels more natural for experienced users who want flexibility.

### Testing Your Command

The planning command should be:
- **Reusable** — works for multiple features, not just one
- **Time-saving** — faster than manual planning conversation
- **Quality-maintaining** — plans as good or better than manual
- **Natural** — matches your workflow preferences

### Steps to Build

1. Create `.claude/commands/plan-feature.md` (or update existing `/planning`)
2. Restart Claude Code to load the new command
3. Test: `/plan-feature "Add another LLM provider"`
4. Evaluate output against the template structure
5. Iterate and refine — each use reveals improvements

---

## FAQ: Common Questions

### "How long should a planning session take?"

**Short answer**: 60-120 minutes for a non-trivial feature.

**Long answer**: The time depends on feature complexity, but the 6-phase structure makes it predictable. Simple features (adding a new endpoint following existing patterns) may take 30-45 minutes. Complex features (new architecture pattern, external integration) may take the full 120 minutes. Parallel research (Phases 2+3) saves 40-50% compared to sequential research. The investment pays off during implementation — 60 minutes of planning prevents 2+ hours of mid-implementation research and rework.

### "Do I need a PRD for every project?"

**Short answer**: For greenfield projects, yes. For existing projects, usually not.

**Long answer**: The PRD defines **what** to build. Greenfield projects need this document first — it feeds into global rules (CLAUDE.md) and on-demand context. For existing projects where the product scope is already established through working code, skip the formal PRD and go straight to analyzing the codebase for global rules. However, if you're adding a major new capability to an existing project, a focused PRD for that capability is valuable.

### "Can I skip planning phases?"

**Short answer**: Each phase fills specific template sections. Skipping creates gaps that surface during implementation.

**Long answer**: Phases 2 and 3 are the most tempting to skip ("I already know the codebase" or "I'll research during implementation"). But these are precisely the phases that prevent mid-implementation research. Phase 2 discovers patterns you forgot about and integration points you missed. Phase 3 finds gotchas and version incompatibilities. The 40% → 85%+ success rate improvement comes primarily from not skipping research.

### "What if my plan exceeds 1000 lines?"

**Short answer**: Tighten with tables, file references, and documentation links instead of inline content.

**Long answer**: Reference files with line numbers instead of copying code blocks (saves 10-30 lines per reference). Use tables for structured data instead of paragraph descriptions. Link to external documentation instead of pasting it. Replace narrative explanations with concise bullet points. If the plan is still over 1000 lines after tightening, the feature may be too large for a single PIV loop — consider decomposing into sub-plans (500-700 lines each) or splitting into two smaller features.

### "Should I use the template-driven or mission-driven approach?"

**Short answer**: Whichever matches your workflow preferences. Both produce equivalent results.

**Long answer**: Template-driven (explicit phases) produces more consistent output and is easier to debug when something goes wrong — you can identify which phase failed. Mission-driven (adaptive depth) feels more natural and handles edge cases better because the agent adapts its depth to the feature's complexity. Most users start template-driven for consistency, then evolve toward mission-driven as they build trust in their planning command. The important thing is that the command feels natural and produces reliable plans.

---

## Next Steps

1. **Read this guide** (you're doing this now)
2. **Study the structured plan template** — read `templates/STRUCTURED-PLAN-TEMPLATE.md` to see the target output structure for the 6-phase process
3. **Review the PRD template** — read `templates/PRD-TEMPLATE.md` if you're starting a greenfield project
4. **Run `/planning` on your next feature** — experience the 6-phase process firsthand and evaluate the output
5. **Build Exercise 1** (planning command) — create or customize your own planning command following the template-driven or mission-driven approach
6. **Move to the Implementation Discipline guide** — learn execution discipline, meta-reasoning for system improvement, save states, and the `/execute` command

---

## Related Resources

- **PIV Loop overview**: `sections/02_piv_loop.md` — always-loaded overview of Plan → Implement → Validate and Layer 1 vs Layer 2
- **Structured Plan Template**: `templates/STRUCTURED-PLAN-TEMPLATE.md` — the template the 6-phase process fills
- **PRD Template**: `templates/PRD-TEMPLATE.md` — Layer 1 "what to build" document
- **Vibe Planning Guide**: `templates/VIBE-PLANNING-GUIDE.md` — example prompts for the exploratory planning phase
- **Command Design Framework guide** (prerequisite): `reference/command-design-framework.md` — INPUT→PROCESS→OUTPUT framework, Core 4 command patterns
- **Implementation Discipline guide** (next): `reference/implementation-discipline.md` — execution discipline, meta-reasoning, save states

---

**That's the Planning Methodology!** You now understand:
- The 6-phase planning process (Feature Understanding → Parallel Research → Design → Tasks → Validation)
- PRD creation with 14-section structure for Layer 1 "what to build"
- Vertical Slice Architecture — core/shared/features decision framework
- The Three-Feature Rule for when to extract shared code
- Writing tool docstrings for agent comprehension (7 required elements)
- Research prompt design — 5 qualities that produce actionable results
- Plan quality constraints — 700-1000 lines (500-700 sub-plans), per-task format, template-driven
- The per-task IMPLEMENT/PATTERN/IMPORTS/GOTCHA/VALIDATE format
- Measuring success — 40% → 85%+ first-pass implementation rate
- Building your own planning command (template-driven vs mission-driven)

**Ready for the Implementation Discipline guide?** Learn execution discipline — how to implement from plans with the `/execute` command, meta-reasoning for improving your system when things go wrong, save states for confident iteration, and the `/create-prd` command for generating PRDs from vibe planning conversations.
