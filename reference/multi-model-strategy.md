# Multi-Model Strategy Guide

> **Load when**: Creating subagents, optimizing costs, or deciding which model to use for different tasks

---

## Quick Start: Recommended Configuration

**Default model**: Sonnet 4.5 (balanced, cost-effective — use for everything except planning)
**Planning model**: Opus 4.6 (superior reasoning — use for `/planning` only)

The PIV Loop naturally separates planning and execution into different conversations. Use this to your advantage:

| Phase | Model | How to Start |
|-------|-------|-------------|
| `/planning` | Opus 4.6 | `claude --model opus` |
| `/execute` | Sonnet 4.5 | `claude` (default) |
| `/execute` (decomposed) | Sonnet 4.5 | `claude` (default) |
| `/code-review` | Sonnet 4.5 | `claude` (default) |
| `/commit` | Sonnet 4.5 | `claude` (default) |
| `/prime` | Sonnet 4.5 | `claude` (default) |

**Setup** (one-time):
```bash
# Set Sonnet as default (add to your shell profile)
export ANTHROPIC_MODEL=claude-sonnet-4-5-20250929

# Optional: create alias for planning sessions
alias cplan="claude --model opus"
```

**Daily workflow**:
```bash
# Planning session (Opus for deep reasoning)
cplan                           # or: claude --model opus
> /planning user-authentication

# Execution session (Sonnet for focused implementation)
claude                          # defaults to Sonnet
> /execute requests/user-authentication-plan.md
```

**Why Opus for planning?** Planning is the highest-leverage phase — a bad plan guarantees a bad implementation. Opus's deeper reasoning produces better feature scoping, more thorough codebase analysis, and higher-confidence implementation plans. The ~3x usage increase pays for itself by reducing implementation retries.

**Billing note**: This guide assumes MAX subscription (recommended). With MAX, all models share a usage pool — cost optimization is about usage efficiency, not per-token price. See the [Cost section](#cost-examples) below for details. If using API billing, per-token costs apply directly.

---

## The Three Models

| Model | Speed | Usage Efficiency | Best For |
|-------|-------|-----------------|----------|
| **Haiku 4.5** | Fastest | Lightest (~1/10th of Sonnet's quota usage) | Pattern matching, code review, simple analysis, repetitive tasks |
| **Sonnet 4.5** | Balanced | Medium | Most coding tasks, implementation, execution, general-purpose |
| **Opus 4.6** | Slowest | Heaviest (~3x Sonnet's quota usage) | Feature planning, complex architecture, hard bugs, creative solutions |

**Current model**: Check with `claude --version` or look at your environment info (you're probably on Sonnet 4.5)

---

## When to Use Each Model

### Haiku — Fast Pattern Matching

**Use for**:
- Code review agents (checking against known patterns)
- Linting and style checks
- Simple refactoring (rename, extract function)
- Test generation (following established patterns)
- Documentation updates
- Search and analysis tasks (grep, glob, read)

**Don't use for**:
- Complex implementation
- Architecture decisions
- Creative problem solving
- Novel algorithms

**Example frontmatter**:
```yaml
---
name: code-review-type-safety
model: haiku
tools: ["Read", "Glob", "Grep"]
---
```

**Why it works**: Code review is pattern matching against documented standards. Haiku excels at this and costs 1/10th of Sonnet.

### Sonnet — Balanced Workhorse

**Use for** (default for most tasks):
- Feature implementation (`/execute`)
- Code review (`/code-review`)
- Commits (`/commit`)
- Context loading (`/prime`)
- General conversation and debugging
- Complex refactoring
- Integration work

**Not recommended for**:
- Feature planning (use Opus for `/planning` — the reasoning quality directly impacts plan quality)

**This is your default**. Start every session with Sonnet unless you're planning. Only deviate to Haiku (for subagent cost savings) or Opus (for planning and hard problems).

**Example frontmatter**:
```yaml
---
name: feature-implementer
model: sonnet  # or omit to inherit
---
```

### Opus — Heavy Lifting

**Use for**:
- **Feature planning (`/planning` command)** — highest-leverage use of Opus
- Complex architectural decisions
- Hard-to-debug issues requiring deep reasoning
- Novel algorithm design
- Creative solutions to ambiguous problems
- System design from scratch
- When Sonnet struggles after 2-3 attempts

**Don't use for**:
- Routine tasks (waste of money)
- Simple code review (Haiku is fine)
- Implementation / execution (Sonnet is fine — plan quality matters more)
- Commits, priming, or other non-reasoning tasks

**Example frontmatter**:
```yaml
---
name: architecture-designer
model: opus
tools: ["*"]
---
```

**Usage awareness**: Opus uses ~3x more of your subscription quota than Sonnet. The recommended use is for `/planning` sessions where reasoning quality directly impacts plan quality. For other tasks, only use Opus when Sonnet has failed or the problem is genuinely complex.

---

## Multi-Model in Practice

### Strategy 1: Parallel Review with Haiku

All 4 code review agents use `model: haiku`:

```
Main Agent (Sonnet)
  ├─> Type Safety (Haiku) ─────┐
  ├─> Security (Haiku) ─────────┤
  ├─> Architecture (Haiku) ─────┤  40-50% faster
  └─> Performance (Haiku) ──────┘  + 70% cheaper
         ↓
Main Agent combines findings
```

**Savings**: 4 Haiku agents cost ~40% of 1 Sonnet doing sequential review.

### Strategy 2: Opus for Planning, Sonnet for Everything Else (Recommended)

```
Planning conversation (Opus):
  claude --model opus
  > /planning feature-name
  → Produces: requests/feature-name-plan.md

Execution conversation (Sonnet):
  claude
  > /execute requests/feature-name-plan.md
  → Implements from plan
```

**Why this works**: The PIV Loop already mandates fresh conversations between planning and execution. Planning is the highest-leverage phase — Opus's deeper reasoning produces better plans. Implementation needs focus, not creativity — Sonnet is ideal.

**Cost impact**: ~3x more for planning sessions, but planning is typically 1 session per feature while execution/review/commit are 3-4 sessions. Net increase: ~30-50% per feature, offset by fewer implementation retries.

### Strategy 3: Planning with Mixed Subagents

```
Main Agent (Sonnet or Opus) — orchestrates planning
  ├─> Codebase exploration (Haiku via Explore built-in)
  └─> External research (Sonnet via general-purpose)
```

**Why**: Codebase exploration is search/grep (Haiku's strength). External research requires synthesis (Sonnet's strength). Combines with Strategy 2 when main agent is Opus.

### Strategy 4: Escalation Pattern

```
1. Try with Haiku (cheap, fast)
   ↓
2. If insufficient → retry with Sonnet
   ↓
3. If still stuck → escalate to Opus
```

**Use for**: Debugging, root cause analysis, complex refactoring.

### Strategy 5: Plan Decomposition (Complex Features)

```
Planning (Opus):
  claude --model opus
  > /planning complex-feature
  → Detects High complexity
  → Produces: overview + N sub-plans

Sequential Execution (Sonnet):
  claude
  > /execute requests/complex-feature-plan-01-foundation.md

  claude
  > /execute requests/complex-feature-plan-02-core.md

  claude
  > /execute requests/complex-feature-plan-03-integration.md
```

**Why this works**: Each sub-plan is 500-700 lines (vs 700-1000 for a single plan). Sub-plans are self-contained with full context, patterns, and task details — the execution agent has no memory of previous sub-plans. Decomposition distributes the work, not the context depth.

**When to use**: Features with 15+ tasks, 4+ implementation phases, or 3+ systems affected. The `/planning` command detects this automatically at Phase 4.5.

**Cost impact**: Same total work, but distributed across instances. No cost increase — just better context utilization per session.

---

## How to Set Model for Agents

### In Agent Frontmatter

```yaml
---
name: my-agent
model: haiku  # or sonnet, or opus
---
```

If omitted, agent inherits from parent (usually Sonnet).

### In Slash Commands (via Task tool)

When invoking subagents from commands:

```markdown
Use the Explore agent (built-in, uses Haiku) to search the codebase.
Use a general-purpose Task agent (inherits Sonnet) for research.
```

Built-in agents:
- **Explore** → Haiku (search, glob, grep)
- **Plan** → Inherits (usually Sonnet)
- **General-purpose** → Inherits (usually Sonnet)

### Via Task Tool Parameters

```markdown
Launch a Task agent with model set to haiku:
- subagent_type: "general-purpose"
- model: "haiku"
- prompt: "Search for all authentication patterns"
```

See Task tool documentation for full parameter list.

---

## Cost Optimization Tips

### 1. Use Haiku for All Reviews

Code review agents should use Haiku by default. Pattern matching doesn't need Sonnet's reasoning.

**Savings**: ~70% cost reduction on review tasks.

### 2. Use Haiku for Research Exploration

When searching codebases or documentation, Haiku is sufficient:

```markdown
Launch an Explore agent (Haiku) to find all database query patterns.
```

**Savings**: ~90% cost reduction on search tasks.

### 3. Keep Main Conversation on Sonnet

Don't drop to Haiku for the main conversation — you lose reasoning quality. Use Sonnet for orchestration, Haiku for specialized subtasks.

### 4. Use Opus Strategically

Use Opus for:
- **Planning sessions** (`/planning` command) — the highest-leverage use
- Sonnet has failed 2-3 times on a hard problem
- Problem requires deep architectural reasoning
- Creative solution to novel problem

**Rule of thumb**: Always use Opus for planning. For other tasks, if you're not sure you need Opus, you don't.

---

## Current Implementation

### ✅ Recommended Configuration

- **Default model**: Sonnet 4.5 (set via `ANTHROPIC_MODEL` environment variable)
- **Planning sessions**: Opus 4.6 (start with `claude --model opus` or `cplan` alias)
- **Code review agents** (all 4): `model: haiku` in frontmatter
- **Utility agents** (2): `model: haiku` — plan-validator + test-generator
- **Built-in Explore agent**: Haiku (used in `/planning` for codebase search)
- **Research agents**: Haiku (codebase) + Sonnet (external)

### ⏳ Optional Enhancements

- Opus for complex debugging (escalation pattern: Sonnet → Opus when stuck)
- Explicit cost tracking per task
- `opusplan` mode for Claude Code's built-in plan mode (uses Opus for `/plan`, Sonnet for execution — note: this is different from our `/planning` slash command)
- Agent Teams model routing: Task tool `model` parameter has a known bug (Issue #18873). Specify model guidance in spawn prompts as workaround. See `templates/TEAM-SPAWN-PROMPTS.md` for details.

---

## Adding Model Strategy to Your Project

### Option 1: Document in CLAUDE.md

Add a section to your project's CLAUDE.md:

```markdown
## Model Selection

- Code review: Haiku (fast, cheap, pattern matching)
- Implementation: Sonnet (balanced)
- Architecture decisions: Opus (only when Sonnet struggles)
```

### Option 2: Create Cost-Optimized Agents

For tasks you do frequently, create Haiku agents:

```yaml
---
name: test-generator
model: haiku
tools: ["Read", "Glob", "Grep"]
---
```

### Option 3: Use Model Parameter in Commands

When calling Task tool, specify model:

```markdown
Launch a Task agent with model="haiku" to generate tests following existing patterns.
```

---

## Examples from Our System

### Planning Command (Opus Session, Mixed Subagents)

```
/planning → Main agent (Opus — started with `claude --model opus`)
  ├─> Phase 2: Explore agent (Haiku) → codebase search
  └─> Phase 3: general-purpose (Sonnet) → external research
```

**Why**: Main reasoning in Opus for superior plan quality. Codebase exploration delegated to Haiku (cheap pattern matching). External research delegated to Sonnet (good synthesis at lower cost than Opus).

### Code Review Command (All Haiku)

```
/code-review → Main agent (Sonnet)
  ├─> Type Safety agent (Haiku)
  ├─> Security agent (Haiku)
  ├─> Architecture agent (Haiku)
  └─> Performance agent (Haiku)
```

**Why all Haiku**: Review is checking against known patterns. Haiku benchmarks at 90%+ quality for pattern-based review (Qodo: 6.55/10 vs Sonnet 6.20/10). 4 Haiku agents cost ~40% of 1 Sonnet doing sequential review.

### Utility Agents (Haiku)

```
plan-validator → Validates plan structure before /execute (Haiku)
test-generator → Suggests test cases from changed code (Haiku)
```

**Why Haiku**: Both agents are advisory and read-only. Plan validation and test suggestion are pattern matching against templates and existing test patterns.

### Execute Command (Sonnet)

```
/execute → Implementation agent (Sonnet, inherited)
  └─> (optional) plan-validator (Haiku) — Step 1.25
```

**Why Sonnet**: Writing code requires reasoning, not just pattern matching. Sonnet is the right balance of capability and cost.

---

## Key Principles

1. **Default to Sonnet** — It's the balanced choice for execution, review, and most tasks
2. **Use Opus for planning** — The `/planning` phase benefits most from deep reasoning
3. **Drop to Haiku** — For subagent pattern matching, search, reviews, repetitive work
4. **Escalate to Opus** — For non-planning tasks, only when Sonnet fails or task is genuinely complex
5. **Parallel savings** — Multiple Haiku agents can be cheaper than one Sonnet doing sequential work
6. **Don't over-optimize** — Saving $0.01 by using Haiku for main conversation loses quality worth $1.00

---

## Cross-Provider Strategy

> Beyond Anthropic's Haiku/Sonnet/Opus, the system supports delegating to external CLI tools via tmux.

### Available CLI Tools

| CLI Tool | Provider | Best For | Billing |
|----------|----------|----------|---------|
| Claude Code | Anthropic | Planning, orchestration, deep reasoning | MAX subscription |
| OpenCode | Multi-provider (75+) | Bulk implementation, flexible model routing | Varies |
| Codex | OpenAI | Code review, quick fixes, test generation | ChatGPT subscription |

### Cross-Provider Task Routing

```
Task arrives
|
+-- Deep reasoning needed? --> Claude Code (Opus 4.6)
+-- Pattern matching / review? --> Codex (codex-1 / gpt-5.3)
+-- Bulk / token-heavy? --> OpenCode (choose cheapest model)
```

### Setup & Usage

See `reference/cross-cli-orchestration.md` for:
- tmux workspace setup (`scripts/cross-cli-setup.sh`)
- `/delegate` command for sending tasks
- tmux communication patterns
- CLI capabilities reference

### Integration with Internal Strategy

Cross-provider routing extends (not replaces) the internal model strategy:

1. **Within Claude Code**: Use Haiku/Sonnet/Opus per existing guidance
2. **Across CLIs**: Route between Claude Code / OpenCode / Codex based on task type
3. **Both strategies compose**: Claude Code (Opus) orchestrates, delegates bulk work externally, uses internal Haiku agents for review

---

## Cost Examples

With MAX subscription (recommended), all models draw from a shared usage pool. Cost optimization means maximizing output quality per usage unit — not minimizing per-token spend.

### MAX Subscription vs API Billing

| Aspect | MAX Subscription | API Billing |
|--------|-----------------|-------------|
| **Pricing** | $100/month (5x usage) or $200/month (20x usage) | Pay-per-token (variable) |
| **Heavy usage cost** | $200/month flat | Can exceed $3,000+/month |
| **Model selection** | All models share usage pool | Each model has different per-token rates |
| **Cost optimization** | Maximize quality per usage unit | Minimize token count |
| **Best for** | Interactive development (Claude Code, claude.ai) | CI/CD without OAuth, programmatic integrations |

**Recommendation**: Use MAX subscription for all interactive Claude Code work. API billing is only needed for CI/CD runners without OAuth support or programmatic API integrations.

**WARNING**: If `ANTHROPIC_API_KEY` is set in your environment, Claude Code silently switches to API billing instead of your subscription. Remove or unset `ANTHROPIC_API_KEY` to use subscription billing.

### Relative Model Usage (applies to both billing models)

Even with MAX subscription, model choice affects how fast you consume your usage quota:

| Model | Relative Usage | Use Case |
|-------|---------------|----------|
| Haiku | ~1/10th of Sonnet | Code review (4 agents = ~40% of 1 Sonnet call) |
| Sonnet | Baseline | Feature implementation |
| Opus | ~3x Sonnet | Complex architecture design |

**Parallel review savings**: 4 Haiku agents (~40% of 1 Sonnet) vs 1 Sonnet sequential = 60% less usage + 40% faster.

### API Pricing Reference

The per-token API pricing below is for reference only — most Claude Code users should use MAX subscription.

Assuming 10K tokens input + 5K tokens output:

| Model | Approx. API Cost | Use Case |
|-------|-----------------|----------|
| Haiku | $0.04 | Code review (4 agents = $0.16) |
| Sonnet | $0.40 | Feature implementation |
| Opus | $1.20 | Complex architecture design |

---

## Reference

- Built-in agent models: Check Task tool documentation
- Custom agent models: Set in frontmatter `model: haiku|sonnet|opus`
- MAX subscription info: https://support.claude.com/en/articles/11049741-what-is-the-max-plan
- API pricing: https://anthropic.com/pricing (for API billing users)
- Current model: Your session shows model ID in environment info
