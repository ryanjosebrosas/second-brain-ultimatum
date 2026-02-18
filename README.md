# My Coding System — Second Brain

**Stop guessing. Start engineering.**

A complete development methodology that turns AI from an unpredictable autocomplete into a disciplined engineering partner — plus a full Python backend that gives your AI a persistent memory and knowledge system. Built for [Claude Code](https://claude.com/claude-code), powered by the PIV Loop, and battle-tested across real projects.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## The Problem

AI coding tools are powerful, but without structure they produce inconsistent results. Give the AI too little context and it guesses. Give it too much and it drowns. Ask it to build a feature without a plan and you get code that works in isolation but breaks everything around it.

Most developers use AI like a magic 8-ball: ask a question, hope for a good answer, and manually clean up when it isn't.

**This system fixes that.** It manages context automatically, enforces a plan-first workflow, gives you quality gates at every stage, and backs it all with a persistent memory system so the AI actually remembers what you've built.

---

## What This Is

This repo is two things in one, deeply connected:

**1. A development methodology** — slash commands, templates, reference guides, and subagents that wrap around Claude Code and enforce a plan-first workflow. No source code required to use this layer. Clone it, work inside it, and build your applications on top of it.

**2. A Second Brain MCP backend** — a full Python application in `backend/` with 13 Pydantic AI agents, a FastMCP server, Mem0 semantic memory, Supabase/pgvector database, and Voyage AI embeddings. This is the application the methodology was built to create. The backend powers the memory and knowledge features used during development sessions.

The connection: the methodology enforces good practices for building the backend. The backend powers the memory that makes the methodology smarter over time.

### Who Is This For?

- **Solo developers using Claude Code** who want consistent, production-grade output instead of trial-and-error prompting
- **Teams adopting AI workflows** who need a repeatable methodology, not ad-hoc prompting
- **Developers who want a personal AI memory system** — store patterns, recall past decisions, score and refine content, coach yourself through daily priorities
- **Anyone tired of AI inconsistency** — the difference between 30% and 88% code acceptance is context clarity, not AI intelligence

### What You Get

**Methodology layer:**
- **15 slash commands** that automate every phase of development — from planning to commit
- **8 templates** for plans, PRDs, and agents — only the ones you will actually use
- **10 reference guides** loaded on-demand — consolidated, focused, no redundancy
- **12 pre-built AI subagents** for parallel research, code review, and specialist tasks
- **1 skill** for systematic planning methodology
- A token-conscious architecture that keeps <10K tokens of system context, leaving the rest for your actual work

**Second Brain backend:**
- **13 Pydantic AI agents** — recall, ask, learn, create, review, orchestrate, coach, prioritize, email, and more
- **Semantic memory** via Mem0 — stores patterns, decisions, and knowledge across all sessions
- **Vector search** via Supabase + pgvector — structured retrieval with RLS
- **FastMCP server** — exposes all agents as tools directly in Claude Code
- **781 tests** — pytest + pytest-asyncio, one file per module

---

## The Philosophy: Less Is More

This system went through two rounds of cleanup, removing **55+ files** across commands, skills, references, templates, and config. Here is why:

**What was removed:**
- 6 reference guides consolidated into others — one authoritative source per topic
- 9 speculative templates nobody used — YAGNI applied to documentation
- Features with no active use: cross-CLI orchestration, worktrees, agent teams, GitHub automation, remote system guides, MCP skills guides
- Config files for unused tools (CodeRabbit, githooks, opencode)

**What you get instead:**
- **Less cognitive load** — Fewer files means less to explore and understand
- **No redundancy** — One guide per topic, not three overlapping ones
- **Faster context loading** — Smaller codebase = faster AI comprehension
- **Easier maintenance** — Fewer files to keep in sync
- **Focused documentation** — Only what is actually used, nothing speculative

The best documentation is documentation you can trust. When every guide is essential, you know where to look.

---

## The PIV Loop

Every feature follows the same cycle: **Plan**, **Implement**, **Validate**, then iterate.

```mermaid
graph LR
    subgraph "PIV Loop"
        direction LR
        P["PLAN<br/>/planning<br/><i>Opus recommended</i>"]
        I["IMPLEMENT<br/>/execute<br/><i>Sonnet recommended</i>"]
        V["VALIDATE<br/>/code-review<br/><i>4 Sonnet agents</i>"]
        C["COMMIT<br/>/commit"]

        P --> I --> V
        V -->|"Issues found"| FIX["/code-review-fix"]
        FIX --> V
        V -->|"All clear"| C
    end

    VIBE["Vibe Planning<br/>conversation"] -->|"distill"| P
    P -->|"produces"| PLAN["requests/<br/>feature-plan.md"]
    PLAN -->|"fresh session"| I
    C -->|"iterate"| NEXT["Next PIV Loop"]

    style P fill:#4a90d9,color:#fff
    style I fill:#7b68ee,color:#fff
    style V fill:#e67e22,color:#fff
    style C fill:#27ae60,color:#fff
```

**Why fresh sessions matter.** Planning creates exploration context — options considered, tradeoffs weighed, research gathered. Execution needs clean context, not exploration baggage. The plan distills exploration into execution instructions. A fresh session with only the plan means the AI focuses on building, not rediscovering. *Vibe planning is good, vibe coding is not.*

**Multiple small loops.** Do not build entire features in one pass. Each PIV loop covers one feature slice, built completely before moving on. Complex features (15+ tasks, 4+ phases) auto-decompose into sub-plans via `/planning`, each getting their own loop.

**The handoff.** The plan is the bridge between thinking and building — 700-1000 lines capturing architecture decisions, file paths, code patterns, gotchas, and atomic tasks. Each task has 7 fields (ACTION, TARGET, IMPLEMENT, PATTERN, IMPORTS, GOTCHA, VALIDATE) so the execution agent has zero ambiguity.

---

## Context Engineering: How the AI Gets It Right

The difference between 30% and 88% code acceptance is not AI intelligence — it is context clarity. Every structured plan is built on four pillars that ensure the AI has exactly what it needs.

```mermaid
graph TD
    subgraph "4 Pillars of Context"
        MEM["Memory<br/>memory.md + vibe planning"]
        RAG["RAG<br/>docs + codebase patterns"]
        PE["Prompt Engineering<br/>explicit decisions"]
        TM["Task Management<br/>7-field atomic tasks"]
    end
    MEM --> PLAN["Structured Plan<br/>700-1000 lines"]
    RAG --> PLAN
    PE --> PLAN
    TM --> PLAN
    PLAN --> EXEC["Fresh Session<br/>/execute"]
    EXEC --> CODE["Production Code"]

    style MEM fill:#4a90d9,color:#fff
    style RAG fill:#7b68ee,color:#fff
    style PE fill:#e67e22,color:#fff
    style TM fill:#27ae60,color:#fff
    style PLAN fill:#8e44ad,color:#fff
    style EXEC fill:#2c3e50,color:#fff
    style CODE fill:#27ae60,color:#fff
```

**Memory** — Past decisions prevent repeated mistakes. `memory.md` persists across sessions: read at `/prime`, appended at `/commit`. Vibe planning conversations add short-term memory within a session.

**RAG** — External docs and codebase patterns ensure the AI does not reinvent existing code. Archon MCP adds curated knowledge base search (optional). Always cite specific sections, not just "see the docs."

**Prompt Engineering** — Explicit solution statements and decisions from vibe planning eliminate guesswork. Bad context: "Add authentication." Good context: "Add JWT auth following the pattern in `src/auth/jwt.py:45-62`, storing tokens in HttpOnly cookies with 24-hour expiration."

**Task Management** — 7-field atomic tasks (ACTION, TARGET, IMPLEMENT, PATTERN, IMPORTS, GOTCHA, VALIDATE) ensure zero ambiguity. Top-to-bottom execution, no backtracking.

**The template is the control mechanism.** The structured plan template (`templates/STRUCTURED-PLAN-TEMPLATE.md`) maps each pillar to specific sections, so nothing gets missed. Memory maps to Related Memories. RAG maps to Relevant Documentation. Prompt Engineering maps to Solution Statement. Task Management maps to Step-by-Step Tasks.

---

## System Architecture

Context is organized in layers. Auto-loaded context stays minimal so the AI has maximum context window for actual work. Deep guides load on-demand only when relevant.

```mermaid
graph TD
    subgraph "Auto-Loaded Context (~2K tokens)"
        CLAUDE["CLAUDE.md"] --> S["sections/<br/>6 core rules"]
    end

    subgraph "On-Demand Context (loaded when needed)"
        R["reference/<br/>10 deep guides"]
        T["templates/<br/>8 templates"]
    end

    subgraph "Automation Layer"
        CMD[".claude/commands/<br/>15 slash commands"]
        AG[".claude/agents/<br/>12 subagents"]
        SK[".claude/skills/<br/>1 skill"]
    end

    subgraph "External Integrations"
        MEM["memory.md<br/>cross-session context"]
        ARCHON["Archon MCP<br/>(optional)<br/>tasks + RAG"]
        BRAIN["Second Brain MCP<br/>(backend/)<br/>memory + agents"]
    end

    CLAUDE -.->|"on-demand"| R
    CLAUDE -.->|"on-demand"| T
    CMD -->|"reads"| T
    CMD -->|"spawns"| AG
    SK -.->|"loads"| R
    MEM -.-> CMD
    ARCHON -.-> CMD
    BRAIN -.-> CMD
    CMD -->|"produces"| REQ["requests/<br/>feature plans"]
    REQ -->|"/execute"| IMPL["Implementation"]
    IMPL -->|"/code-review"| AG
    IMPL -->|"/commit"| GIT["Git Save Points"]

    style CLAUDE fill:#4a90d9,color:#fff
    style CMD fill:#7b68ee,color:#fff
    style AG fill:#e67e22,color:#fff
    style IMPL fill:#27ae60,color:#fff
    style BRAIN fill:#8e44ad,color:#fff
```

### Token Budget

Auto-loading everything would waste 20-30K tokens before any real work begins. The system keeps core rules always available (~2K tokens) and loads deep guides only when a command needs them.

| Layer | Token Cost | Loading |
|-------|-----------|---------|
| `CLAUDE.md` + 6 sections | ~2K tokens | Auto-loaded every session |
| Slash commands | varies | Loaded only when invoked |
| Reference guides (10) | varies | On-demand only |
| Templates (8) | varies | On-demand only |
| **Typical session total** | **<10K tokens** | Leaves ~100K+ for implementation |

### How Context Flows

```mermaid
graph LR
    PRIME["/prime<br/>memory + structure<br/>~2K baseline"] --> PLANNING["/planning<br/>templates + research<br/>heavy context"]
    PLANNING --> EXECUTE["/execute<br/>plan file only<br/>clean context"]
    EXECUTE --> COMMIT["/commit<br/>lessons to memory<br/>persistence"]
    COMMIT -->|"next feature"| PRIME

    style PRIME fill:#4a90d9,color:#fff
    style PLANNING fill:#8e44ad,color:#fff
    style EXECUTE fill:#7b68ee,color:#fff
    style COMMIT fill:#27ae60,color:#fff
```

Each command loads only what it needs. `/prime` establishes baseline context. `/planning` pulls in templates, spawns research agents, and references external docs — heavy context, but isolated to the planning session. `/execute` starts fresh with only the plan file — clean context for focused implementation. `/commit` appends lessons learned to `memory.md` for cross-session persistence.

---

## Context Recovery After Auto-Compact

When the context window fills up, Claude Code compacts the conversation automatically to free space. Compaction summarizes the conversation, but summaries drop details: decisions from `memory.md`, architecture patterns, and session notes are not guaranteed to survive. The next prompt arrives in a session that has forgotten its own history.

The system includes a `SessionStart` hook that detects compaction and re-injects `memory.md` automatically on resume, before your next prompt.

```mermaid
graph LR
    FULL["Context Window Full"] --> COMPACT["Auto-Compact<br/>summarizes conversation"]
    COMPACT --> RESUME["Session Resumes"]
    RESUME --> HOOK["SessionStart Hook<br/>matcher: compact"]
    HOOK --> MEM["memory.md injected<br/>into context"]
    MEM --> PRIME["Run /prime<br/>for full inventory"]

    style FULL fill:#e74c3c,color:#fff
    style COMPACT fill:#e67e22,color:#fff
    style RESUME fill:#f39c12,color:#fff
    style HOOK fill:#8e44ad,color:#fff
    style MEM fill:#4a90d9,color:#fff
    style PRIME fill:#27ae60,color:#fff
```

**What gets recovered automatically:** `memory.md` content (key decisions, architecture patterns, gotchas, session notes).

**What still requires `/prime`:** file structure map, command inventory, and agent list. Hooks inject text into context but cannot invoke slash commands, so `/prime` must be run manually after the compaction banner appears.

The hook is defined in `.claude/settings.json` (project-level, committed). Anyone who clones the system gets it automatically.

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "compact",
        "hooks": [
          {
            "type": "command",
            "command": "echo '=== Auto-compact occurred - memory context re-injected ===' && echo '' && cat \"$CLAUDE_PROJECT_DIR/memory.md\" && echo '' && echo 'Run /prime for full project structure, commands, and agent inventory.'"
          }
        ]
      }
    ]
  }
}
```

**After a compaction:** you will see the banner, your memory will already be loaded, and running `/prime` restores the rest.

---

## Second Brain Backend

The `backend/` directory contains a full Python application that gives your AI sessions persistent memory and structured knowledge. It runs as an MCP server, exposing all capabilities as tools directly inside Claude Code.

### 13 Pydantic AI Agents

```mermaid
graph TD
    COS["chief_of_staff<br/>Orchestrator — routes to the right agent"]
    COS --> RECALL["recall<br/>Semantic memory search"]
    COS --> ASK["ask<br/>General Q&A with brain context"]
    COS --> LEARN["learn<br/>Pattern extraction + memory storage"]
    COS --> CREATE["create<br/>Content generation (voice-aware)"]
    COS --> REVIEW["review<br/>Multi-dimension content scoring"]
    COS --> COACH["coach<br/>Daily accountability coaching"]
    COS --> PMO["pmo<br/>Task prioritization (PMO-style)"]
    COS --> EMAIL["email_agent<br/>Email composition"]
    COS --> SPEC["specialist<br/>Claude Code / Pydantic AI Q&A"]
    COS --> CLARITY["clarity<br/>Readability analysis"]
    COS --> SYNTH["synthesizer<br/>Feedback consolidation"]
    COS --> TB["template_builder<br/>Template opportunity detection"]

    style COS fill:#8e44ad,color:#fff
    style RECALL fill:#4a90d9,color:#fff
    style ASK fill:#4a90d9,color:#fff
    style LEARN fill:#27ae60,color:#fff
    style CREATE fill:#27ae60,color:#fff
    style REVIEW fill:#e67e22,color:#fff
```

| Agent | What It Does |
|-------|-------------|
| `chief_of_staff` | Routing orchestrator — analyses your request and delegates to the right agent or pipeline |
| `recall` | Searches semantic memory to surface relevant past decisions, patterns, and knowledge |
| `ask` | General Q&A with full brain context — answers questions using stored knowledge |
| `learn` | Extracts patterns and insights from content, stores them to semantic memory |
| `create` | Generates content with awareness of your voice, style, and stored examples |
| `review` | Scores content across multiple dimensions (clarity, structure, impact, etc.) |
| `coach` | Daily accountability coaching — surfaces priorities and tracks progress |
| `pmo` | PMO-style task prioritization — helps manage competing projects and deadlines |
| `email_agent` | Composes emails matched to your voice and the recipient relationship |
| `specialist` | Deep Q&A on Claude Code, Pydantic AI, and the Second Brain system itself |
| `clarity` | Readability analysis — identifies complexity, jargon, and structural issues |
| `synthesizer` | Consolidates feedback from multiple sources into a unified, actionable summary |
| `template_builder` | Detects template opportunities in repeated content patterns |

### Backend Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.11+ |
| Agent framework | Pydantic AI (`pydantic-ai[anthropic]`) |
| MCP server | FastMCP |
| Semantic memory | Mem0 (`mem0ai`) |
| Database | Supabase (PostgreSQL + pgvector) |
| Embeddings | Voyage AI (primary), OpenAI (fallback) |
| Knowledge graph | Graphiti (optional, feature-flagged) |
| CLI | Click (`brain` entrypoint) |
| Retries | Tenacity |
| Config | Pydantic Settings |
| Testing | pytest + pytest-asyncio |

### Data Flow

```
MCP tool call
  → mcp_server.py validates input
  → calls agent with BrainDeps
  → agent uses service layer
  → Mem0 / Supabase / Voyage AI
  → structured output returned
  → formatted as plain text string
```

### Backend Setup

```bash
cd backend
pip install -e ".[dev]"
cp .env.example .env
# Edit .env with your keys:
# ANTHROPIC_API_KEY, MEM0_API_KEY, SUPABASE_URL, SUPABASE_KEY, VOYAGE_API_KEY
python -m second_brain.mcp_server   # Start MCP server
```

Optional extras:

```bash
pip install -e ".[dev,graphiti]"      # + Graphiti knowledge graph
pip install -e ".[dev,subscription]"  # + Claude Agent SDK (subscription auth)
```

Run tests:

```bash
cd backend
pytest          # All 781 tests
pytest -x       # Stop on first failure
pytest -v       # Verbose output
```

---

## Model Strategy

The system separates thinking from doing. Use the right model for each phase:

```mermaid
graph LR
    PLAN["Planning<br/>Opus"] --> EXEC["Execution<br/>Sonnet"]
    EXEC --> REV["Code Review<br/>4x Sonnet agents"]
    REV --> COM["Commit<br/>Sonnet"]

    style PLAN fill:#4a90d9,color:#fff
    style EXEC fill:#7b68ee,color:#fff
    style REV fill:#e67e22,color:#fff
    style COM fill:#27ae60,color:#fff
```

**Why this separation matters.** Planning is the highest-leverage phase — a bad plan guarantees bad implementation. Opus's deeper reasoning produces better feature scoping, more thorough codebase analysis, and higher-confidence implementation plans. The ~3x usage increase pays for itself by reducing implementation retries. Code review uses 4 parallel Sonnet agents, each focused on a single review dimension for maximum depth.

| Phase | Recommended Model | Why |
|-------|-------------------|-----|
| `/planning` | **Opus** (`claude --model opus`) | Deep reasoning produces better plans |
| `/execute` | **Sonnet** (`claude` default) | Balanced — follows plans well at lower cost |
| `/code-review` | **Sonnet** (via subagents) | 4 parallel agents, each covering one review dimension |
| `/commit`, `/prime` | **Sonnet** (`claude` default) | General-purpose tasks |

```bash
# Planning session (Opus for deep reasoning)
claude --model opus
> /planning my-feature

# Execution session (Sonnet for focused implementation)
claude
> /execute requests/my-feature-plan.md
```

See `reference/subagents-deep-dive.md` for model selection guidance.

---

## Learning Path: Trust Progression

Do not try everything at once. The system unlocks capabilities progressively — each tier amplifies both good patterns and bad ones.

```mermaid
graph TD
    M["Manual Prompts<br/><i>Start here</i>"] --> CMD["Slash Commands<br/>/prime, /planning, /execute"]
    CMD --> CHAIN["Chained Workflows<br/>/end-to-end-feature"]
    CHAIN --> SUB["Subagents<br/>Parallel research + review"]

    style M fill:#85c1e9,color:#000
    style CMD fill:#5dade2,color:#fff
    style CHAIN fill:#3498db,color:#fff
    style SUB fill:#2e86c1,color:#fff
```

- **Manual Prompts** — Use Claude Code with good prompts. Understand the base tool before adding structure.
- **Slash Commands** — Structured reusable prompts. Master the core cycle: `/prime` -> `/planning` -> `/execute` -> `/commit`.
- **Chained Workflows** — `/end-to-end-feature` chains the full PIV Loop autonomously. Only use after individual commands are trusted.
- **Subagents** — Parallel research (5-10 agents) and code review (4 agents). Results flow one-way back to the main agent.

**When to move up:** Prove the current tier works reliably across 5+ features before advancing. See `reference/system-foundations.md` for the full trust model.

---

## Validation: The 5-Level Pyramid

Validation is not an afterthought — it is the third pillar of the PIV Loop. A 5-level gated pyramid catches problems from syntax errors to architectural violations.

```mermaid
graph TD
    L1["Level 1: Syntax & Style<br/><i>Linting, formatting</i>"] --> L2["Level 2: Type Safety<br/><i>Type checking</i>"]
    L2 --> L3["Level 3: Unit Tests<br/><i>Isolated logic</i>"]
    L3 --> L4["Level 4: Integration Tests<br/><i>System behavior</i>"]
    L4 --> L5["Level 5: Human Review<br/><i>Alignment with intent</i>"]

    style L1 fill:#27ae60,color:#fff
    style L2 fill:#2ecc71,color:#fff
    style L3 fill:#f39c12,color:#fff
    style L4 fill:#e67e22,color:#fff
    style L5 fill:#e74c3c,color:#fff
```

**Each level gates the next.** Do not run expensive integration tests when a linting error would catch the issue in seconds. Do not request human review until automated checks pass clean.

**Parallel Code Review.** `/code-review` launches 4 specialized Sonnet agents simultaneously — type safety, security, architecture, and performance — each focused on one concern with its entire context window:

```mermaid
graph LR
    MAIN["Main Agent"] --> TS["Type Safety"]
    MAIN --> SEC["Security"]
    MAIN --> ARCH["Architecture"]
    MAIN --> PERF["Performance"]
    TS --> REPORT["Unified Report"]
    SEC --> REPORT
    ARCH --> REPORT
    PERF --> REPORT

    style MAIN fill:#7b68ee,color:#fff
    style TS fill:#3498db,color:#fff
    style SEC fill:#e74c3c,color:#fff
    style ARCH fill:#f39c12,color:#fff
    style PERF fill:#e67e22,color:#fff
    style REPORT fill:#27ae60,color:#fff
```

40-50% faster than sequential review. Each agent catches issues a general reviewer might miss.

**System evolution insight.** When validation catches an issue, do not just fix the code — fix the system that allowed the bug. Update the command, template, or rule that let it through. One-off fixes solve today; system updates solve forever. See `reference/validation-discipline.md` for the full methodology.

---

## Quick Start

### Prerequisites
- [Claude Code CLI](https://claude.com/claude-code) installed
- Git configured

### Methodology Setup

1. **Clone** this repo:
   ```bash
   git clone https://github.com/ryanjosebrosas/my-coding-system-claude.git
   cd my-coding-system-claude
   ```

2. **Create your memory file** from the template:
   ```bash
   cp templates/MEMORY-TEMPLATE.md memory.md
   ```

3. **Start Claude Code** and prime the system:
   ```bash
   claude
   > /prime
   ```

4. **Plan your first feature**:
   ```
   > /planning user-authentication
   ```

5. **Execute the plan** (in a fresh session for clean context):
   ```
   > /execute requests/user-authentication-plan.md
   ```

6. **Review and commit**:
   ```
   > /code-review
   > /commit
   ```

### Backend Setup (Optional)

If you want the Second Brain MCP server — persistent semantic memory, 13 agents as MCP tools, content scoring and retrieval:

1. **Set up environment:**
   ```bash
   cd backend
   cp .env.example .env
   # Edit .env with:
   # ANTHROPIC_API_KEY=...
   # MEM0_API_KEY=...
   # SUPABASE_URL=...
   # SUPABASE_KEY=...
   # VOYAGE_API_KEY=...  (optional, falls back to OpenAI)
   ```

2. **Install dependencies:**
   ```bash
   pip install -e ".[dev]"
   ```

3. **Apply database migrations** via the Supabase dashboard or CLI. Migrations are in `backend/supabase/migrations/` (001–014, numbered).

4. **Start the MCP server:**
   ```bash
   python -m second_brain.mcp_server
   ```

   The server exposes all 13 agents as MCP tools that Claude Code can call directly. Once running, use the `brain` CLI:

   ```bash
   brain --help
   brain health    # Check system health
   brain migrate   # Run data migration
   ```

### What Happens Next?

Each feature gets its own PIV loop. Small loops, built completely before moving on. Plan, implement, validate, iterate — then start the next feature. The system compounds: lessons from each loop feed into `memory.md`, informing future plans. When the backend is running, recalled memories come from persistent semantic storage rather than a flat file.

### First Time?
Start with `/prime` to load context, then try `/planning` on a small feature. Read `reference/file-structure.md` for a full map of everything included.

---

## Adopting for Your Project

### Option A: Use as Your Project Base (Recommended for new projects)
Fork or clone this repo, then build your application inside it. All slash commands, templates, and reference guides are ready to go.

### Option B: Copy Into an Existing Project
```bash
cp -r sections/ reference/ templates/ requests/ your-project/
cp CLAUDE.md your-project/
cp -r .claude/ your-project/
cp -r agents/ commands/ skills/ your-project/
cp templates/MEMORY-TEMPLATE.md your-project/memory.md
```

Then run `/init-c` to customize `CLAUDE.md` for your project's tech stack.

### After Setup
- `memory.md` — Created from template, gitignored. Each developer maintains their own.
- `requests/*.md` — Feature plans, gitignored. Ephemeral by design.
- `.claude/settings.local.json` — Personal Claude Code settings, gitignored.

---

## All 15 Slash Commands

15 slash commands automate every phase. The core 6 cover 90% of daily development — expand below for advanced workflows and utilities.

### Core Workflow

| Command | What It Does | When to Use |
|---------|-------------|-------------|
| `/prime` | Loads codebase context, reads memory, checks active tasks | Start of every session |
| `/planning [feature]` | 6-phase deep analysis producing a structured plan document | Before building any feature |
| `/execute [plan]` | Implements a plan file task-by-task with validation | After planning, in a fresh session |
| `/commit` | Creates a conventional-format git commit | After implementation passes review |
| `/code-review` | Runs 4 parallel review agents (type safety, security, architecture, performance) | After implementation |
| `/code-review-fix` | Applies fixes from code review findings | After code review surfaces issues |

<details>
<summary>Advanced Workflows (1 command)</summary>

| Command | What It Does | When to Use |
|---------|-------------|-------------|
| `/end-to-end-feature` | Full autonomous pipeline: plan, implement, review, commit | Trusted, well-defined features |

</details>

<details>
<summary>Utilities (8 commands)</summary>

| Command | What It Does | When to Use |
|---------|-------------|-------------|
| `/rca [issue]` | Root cause analysis for a GitHub issue | Investigating bugs |
| `/implement-fix` | Implements a fix based on an RCA document | After root cause analysis |
| `/create-prd` | Generates a Product Requirements Document from conversation | Defining a new product or major feature |
| `/create-pr` | Creates a GitHub Pull Request with AI-generated description | After pushing a branch |
| `/execution-report` | Generates a post-implementation report for system review | Reviewing what was built vs. what was planned |
| `/init-c` | Generates a customized `CLAUDE.md` for a new project | New project setup |
| `/agents` | Creates a new custom subagent definition file | Extending the system with new agents |
| `/system-review` | Audits system state for divergence between plan and reality | Periodic system health checks |

</details>

---

## 12 Subagents

12 subagents run in isolation with their own context windows. Research agents explore in parallel. Code review agents check 4 dimensions simultaneously. Specialist agents bring domain expertise.

Each agent is a markdown file with a system prompt in `.claude/agents/`. The main agent delegates via the Task tool, and agents return structured results without polluting your implementation context.

<details>
<summary>All 12 agents — Research, Code Review, Utility, Specialist</summary>

### Research Agents

| Agent | Model | Purpose |
|-------|-------|---------|
| `research-codebase` | Sonnet | Parallel codebase exploration — finds files, extracts patterns, reports findings |
| `research-external` | Sonnet | Documentation search, best practices, version compatibility checks |

### Code Review Agents

These four run in parallel during `/code-review`, each checking a different dimension:

| Agent | Model | What It Catches |
|-------|-------|----------------|
| `code-review-type-safety` | Sonnet | Missing type hints, type checking errors, unsafe casts |
| `code-review-security` | Sonnet | SQL injection, XSS, exposed secrets, insecure data handling |
| `code-review-architecture` | Sonnet | Pattern violations, layer breaches, convention drift |
| `code-review-performance` | Sonnet | N+1 queries, inefficient algorithms, memory leaks, unnecessary computation |

### Utility Agents

| Agent | Model | Purpose |
|-------|-------|---------|
| `plan-validator` | Sonnet | Validates plan structure and completeness before `/execute` |
| `test-generator` | Sonnet | Analyzes changed code and suggests test cases following project patterns |

### Specialist Agents

| Agent | Model | Purpose |
|-------|-------|---------|
| `specialist-devops` | Sonnet | CI/CD pipelines, Docker, IaC, monitoring, deployments |
| `specialist-data` | Sonnet | Database design, migrations, queries, data pipelines |
| `specialist-copywriter` | Sonnet | UI copy, microcopy, error messages, UX writing |
| `specialist-tech-writer` | Sonnet | API docs, READMEs, changelogs, architecture documentation |

</details>

See `reference/subagents-deep-dive.md` for creating your own agents.

---

## System Components

<details>
<summary>1 Cloud Skill</summary>

| Skill | Purpose |
|-------|---------|
| `planning-methodology` | 6-phase systematic planning with parallel research |

</details>

<details>
<summary>8 Templates</summary>

### Planning & Requirements
| Template | Purpose |
|----------|---------|
| `STRUCTURED-PLAN-TEMPLATE.md` | Main planning template — covers all 4 Context Engineering pillars |
| `SUB-PLAN-TEMPLATE.md` | Sub-feature plans for complex decomposition |
| `PLAN-OVERVIEW-TEMPLATE.md` | High-level plan overview |
| `PRD-TEMPLATE.md` | Product Requirements Document |
| `VIBE-PLANNING-GUIDE.md` | Guide for casual-to-structured planning conversations |

### System Extension
| Template | Purpose |
|----------|---------|
| `AGENT-TEMPLATE.md` | Create custom subagent definitions |
| `COMMAND-TEMPLATE.md` | Create new slash commands |
| `MEMORY-TEMPLATE.md` | Cross-session memory file |

</details>

<details>
<summary>10 Reference Guides</summary>

### Core Methodology
| Guide | What It Covers |
|-------|---------------|
| `system-foundations.md` | Why this system exists, baseline assessment, trust progression |
| `piv-loop-practice.md` | PIV Loop in practice with real examples |
| `implementation-discipline.md` | `/execute` design, Navigate-Implement-Verify, save states |
| `validation-discipline.md` | 5-level validation pyramid |
| `global-rules-optimization.md` | Layer 1 optimization, `@sections` modular organization |

### Context & Architecture
| Guide | What It Covers |
|-------|---------------|
| `layer1-guide.md` | Setting up CLAUDE.md for a new project |
| `file-structure.md` | Complete file location reference |

### Agents & Extensions
| Guide | What It Covers |
|-------|---------------|
| `subagents-deep-dive.md` | Subagent creation, parallel execution, context isolation |
| `command-design-framework.md` | INPUT-PROCESS-OUTPUT command framework |
| `archon-workflow.md` | Archon task management and RAG search |

</details>

---

## Optional: Archon MCP

[Archon MCP](https://github.com/coleam00/archon) provides task management and RAG search across sessions. **Completely optional** — all commands work without it. When available, it adds:

- Persistent task tracking across planning and execution sessions
- RAG search over curated documentation sources
- Project and version management

See `reference/archon-workflow.md` for setup instructions.

---

## Project Structure

```
root/
├── CLAUDE.md                          # Auto-loaded rules (~2K tokens)
├── README.md
├── memory.md                          # Cross-session memory (gitignored)
├── settings.json                      # Session hooks (compact recovery)
├── .gitignore
│
├── backend/                           # Second Brain Python application
│   ├── src/second_brain/
│   │   ├── mcp_server.py              # FastMCP server (@server.tool() functions)
│   │   ├── service_mcp.py             # Service bridge (supplemental routing)
│   │   ├── deps.py                    # BrainDeps dataclass + create_deps()
│   │   ├── config.py                  # BrainConfig (Pydantic Settings)
│   │   ├── schemas.py                 # All Pydantic output models
│   │   ├── models.py                  # AI model selection logic
│   │   ├── auth.py                    # Authentication helpers
│   │   ├── migrate.py                 # Data migration utilities
│   │   ├── cli.py                     # Click CLI ("brain" command)
│   │   ├── agents/                    # 13 Pydantic AI agents
│   │   │   ├── recall.py
│   │   │   ├── ask.py
│   │   │   ├── learn.py
│   │   │   ├── create.py
│   │   │   ├── review.py
│   │   │   ├── chief_of_staff.py      # Routing orchestrator
│   │   │   ├── coach.py
│   │   │   ├── pmo.py
│   │   │   ├── email_agent.py
│   │   │   ├── specialist.py
│   │   │   ├── clarity.py
│   │   │   ├── synthesizer.py
│   │   │   ├── template_builder.py
│   │   │   └── utils.py               # Shared: tool_error(), run_pipeline()
│   │   └── services/                  # External service wrappers
│   │       ├── memory.py              # Mem0 semantic memory
│   │       ├── storage.py             # Supabase CRUD + ContentTypeRegistry
│   │       ├── embeddings.py          # Voyage AI / OpenAI embeddings
│   │       ├── voyage.py              # Voyage AI reranking
│   │       ├── graphiti.py            # Knowledge graph (optional)
│   │       ├── health.py              # Brain metrics + growth milestones
│   │       ├── retry.py               # Tenacity retry helpers
│   │       ├── search_result.py       # Search result data structures
│   │       └── abstract.py            # Abstract base classes
│   ├── supabase/migrations/           # 14 SQL migrations (001–014)
│   ├── tests/                         # 781 tests (one file per module)
│   ├── scripts/                       # Utility scripts
│   ├── .env.example                   # Documented env var template
│   └── pyproject.toml                 # Dependencies + pytest config
│
├── sections/                          # Core methodology (6 files, auto-loaded via CLAUDE.md)
│   ├── 01_core_principles.md
│   ├── 02_piv_loop.md
│   ├── 03_context_engineering.md
│   ├── 04_git_save_points.md
│   ├── 05_decision_framework.md
│   └── 06_tech_stack.md
│
├── reference/                         # Deep guides (10 files, on-demand)
│   ├── system-foundations.md
│   ├── piv-loop-practice.md
│   ├── implementation-discipline.md
│   ├── validation-discipline.md
│   ├── global-rules-optimization.md
│   ├── layer1-guide.md
│   ├── file-structure.md
│   ├── subagents-deep-dive.md
│   ├── command-design-framework.md
│   └── archon-workflow.md
│
├── templates/                         # Reusable templates (8 files)
│   ├── STRUCTURED-PLAN-TEMPLATE.md
│   ├── SUB-PLAN-TEMPLATE.md
│   ├── PLAN-OVERVIEW-TEMPLATE.md
│   ├── PRD-TEMPLATE.md
│   ├── VIBE-PLANNING-GUIDE.md
│   ├── AGENT-TEMPLATE.md
│   ├── COMMAND-TEMPLATE.md
│   └── MEMORY-TEMPLATE.md
│
├── requests/                          # Feature plans (gitignored)
│
├── agents/                            # Subagent definitions (12 agents)
├── commands/                          # Slash command definitions (15 commands)
├── skills/                            # Skills (1 skill)
│
└── .claude/
    ├── agents/                        # Same agents (also accessible here)
    ├── commands/                      # Same commands (also accessible here)
    ├── skills/                        # Same skills (also accessible here)
    └── settings.json                  # Session hooks (compact recovery)
```

---

## By the Numbers

### Methodology Layer

| Component | Count |
|-----------|-------|
| Core methodology sections | 6 |
| Reference guides | 10 |
| Reusable templates | 8 |
| Slash commands | 15 |
| Subagents | 12 |
| Cloud skills | 1 |
| Auto-loaded context cost | ~2K tokens |
| Typical session context | <10K tokens |

### Second Brain Backend

| Component | Count |
|-----------|-------|
| Pydantic AI agents | 13 |
| Service layer modules | 9 |
| Database migrations | 14 |
| Test count | 781 |
| Python version | 3.11+ |

---

## License

This project is licensed under the [MIT License](LICENSE).
