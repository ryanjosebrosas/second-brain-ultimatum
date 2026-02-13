# Example Agents

> **Note**: These agents have been activated and are live in `.claude/agents/`. This `_examples/` directory is kept as a reference for the original templates, including the `instance` field documentation. The active agents in `.claude/agents/` have `instance` removed since it's not a valid Claude Code frontmatter field.

This directory contains **8 example agents** demonstrating different subagent patterns. Copy agents to `.claude/agents/` in your project to activate them.

---

## Research Agents

These agents handle **parallel research** — exploring your codebase and external documentation simultaneously. They're designed to be invoked from commands like `/planning` or used directly for ad-hoc research.

| Agent | Model | Tools | Purpose |
|-------|-------|-------|---------|
| **research-codebase** | Haiku | Read, Glob, Grep | File discovery, pattern extraction, codebase exploration |
| **research-external** | Sonnet | Read, Glob, Grep, WebSearch, WebFetch | Documentation search, best practices, version compatibility |

### When to Use

- **research-codebase** (Haiku): Parallel codebase exploration during planning, finding files and patterns, extracting code examples with line numbers. Read-only tools keep it safe. Cost-optimized for high-volume exploration.
- **research-external** (Sonnet): Documentation search, best practices research, version compatibility checks, migration guides. Higher quality model for synthesis tasks that require judgment.

### Usage Examples

Invoke from a prompt or command:
```
Use the research-codebase agent to find all authentication-related files and patterns.
```
```
Use the research-external agent to find the React 19 migration guide and breaking changes.
```

### Multi-Instance Routing

Research agents use **cost-optimized routing** to `claude-zai`:

| Agent | Instance | Model | Why |
|-------|----------|-------|-----|
| **research-codebase** | `claude-zai` | Haiku | Non-critical: Phase 3b validation catches errors |
| **research-external** | `claude-zai` | Sonnet | Non-critical: validation catches errors; synthesis quality kept via Sonnet model |

**Routing Philosophy for Research**:
- Research is non-critical — wrong results get caught by Phase 3b research validation
- Unlike code review (where security findings are VITAL), research findings are always validated
- Both agents route to `claude-zai` for maximum cost savings

If you don't have multiple instances, remove the `instance:` lines and all agents will use your default.

### Parallel Research in /planning

When custom research agents are activated, the `/planning` command can launch **5-10 parallel agents** instead of 2:

```text
Main Agent (Sonnet)
  |-> research-codebase #1 (claude-zai, Haiku) --- "auth patterns middleware"
  |-> research-codebase #2 (claude-zai, Haiku) --- "session model schema"
  |-> research-codebase #3 (claude-zai, Haiku) --- "auth test fixtures"
  |-> research-external #1 (claude-zai, Sonnet) -- "JWT token refresh"
  |-> research-external #2 (claude-zai, Sonnet) -- "bcrypt password hashing"
  |-> research-external #3 (claude-zai, Sonnet) -- "OAuth2 PKCE flow"
       | (results return in parallel)
Main Agent combines findings into unified research report
```

**Speed improvement**: 3-5x faster than 2-agent standard mode for complex features.
**Cost optimization**: claude-zai instance + Haiku model = maximum savings for codebase exploration.

**Scale guideline**:
- Simple features (Low complexity): 2-4 agents total
- Medium features: 4-6 agents total
- Complex features (High complexity): 6-10 agents total (max 10 concurrent)

### Basic Parallel Research

Launch both agents simultaneously for comprehensive research (codebase patterns + external docs):
```
Launch two Task agents in parallel:
1. research-codebase agent: "Find all payment-related files, models, and API patterns"
2. research-external agent: "Find Stripe API v2024 documentation and migration guide"
```

### Activation

Copy agents from `_examples/` to `.claude/agents/` in your project:
```bash
cp .claude/agents/_examples/research-*.md .claude/agents/
```

Once activated, the `/planning` command automatically detects them and switches to Parallel Research Mode (5-10 agents) instead of Standard Research Mode (2 built-in agents).

---

## Code Review Agents

These agents demonstrate **parallel code review** using the Pattern A approach from `reference/subagents-guide.md`.

## What These Agents Do

Instead of one agent reviewing everything sequentially, these four agents work **in parallel** — each focusing on a specific aspect:

| Agent | Focus | What It Checks |
|-------|-------|----------------|
| **code-review-type-safety** | Type annotations & type checking | Missing types, incorrect types, type errors |
| **code-review-security** | Security vulnerabilities | SQL injection, XSS, exposed secrets, auth issues |
| **code-review-architecture** | Design patterns & conventions | Layer violations, DRY, YAGNI, naming, structure |
| **code-review-performance** | Performance & scalability | N+1 queries, inefficient algorithms, memory leaks |

## Multi-Instance Routing

These agents use **smart routing** based on criticality:

| Agent | Instance | Model | Why |
|-------|----------|-------|-----|
| **Type Safety** | `claude-zai` | Haiku | Pattern matching — type checks follow known rules |
| **Security** | `claude-zai` | Haiku | Pattern matching — OWASP checks, secret scanning patterns |
| **Architecture** | `claude-zai` | Haiku | Pattern matching — convention compliance, layer checks |
| **Performance** | `claude-zai` | Haiku | Pattern matching — N+1 detection, complexity analysis |

**Routing Philosophy**:
All review agents use Haiku + claude-zai. Code review is fundamentally pattern matching
against documented standards — Haiku benchmarks at 90%+ quality for this task type
(Qodo: 6.55/10 vs Sonnet 6.20/10). The cost savings are significant: 4 Haiku agents
cost ~40% of 1 Sonnet doing sequential review.

If you don't have multiple instances, remove the `instance:` lines and all agents will use your default.

## How to Use

### Option 1: Copy and Customize (Recommended)

1. Copy the agents you need from `_examples/` to `.claude/agents/`:
   ```bash
   cp .claude/agents/_examples/code-review-*.md .claude/agents/
   ```

2. Customize for your project:
   - Update `Context Gathering` section to reference your project files
   - Add project-specific patterns to check
   - Adjust severity thresholds based on your standards
   - Modify output format if needed

3. Restart your Claude Code session to load the agents

4. Use with `/code-review` command (which will invoke them automatically)

### Option 2: Use As-Is for Testing

The examples work out-of-the-box but are generic. They'll read `CLAUDE.md` and adapt to your project, but won't be as targeted as customized agents.

## Parallel Execution

When you run `/code-review`, all four agents launch simultaneously:

```text
Main Agent
  ├─> Type Safety Agent (reviews all files for type issues)
  ├─> Security Agent (reviews all files for vulnerabilities)
  ├─> Architecture Agent (reviews all files for pattern compliance)
  └─> Performance Agent (reviews all files for efficiency)
       ↓ (results return in parallel)
Main Agent combines findings into unified report
```

**Speed improvement**: 40-50% faster than sequential review (same as `/planning` parallel research).

## When NOT to Use All Four

You don't always need all four agents. Pick based on your feature:

| Feature Type | Agents to Use |
|--------------|---------------|
| **New API endpoint** | Security + Architecture + Performance |
| **Frontend component** | Type Safety + Architecture |
| **Database migration** | Security + Architecture + Performance |
| **Bug fix** | Type Safety + Security (usually sufficient) |
| **Documentation** | Skip parallel review, use basic `/code-review` |

To use only specific agents, modify the `/code-review` command to launch fewer agents.

## Output Format

Each agent returns structured findings:
- **Severity**: Critical / Major / Minor
- **Location**: file:line
- **Issue**: What's wrong
- **Evidence**: Code snippet
- **Fix**: How to resolve

The main agent combines all findings into a single report saved to `requests/code-reviews/{feature}-review.md`.

## Customization Ideas

### For Python Projects
- Add `mypy` or `pyright` integration to type-safety agent
- Add `bandit` security scanner integration to security agent
- Check for `pytest` coverage in architecture agent

### For TypeScript Projects
- Add `tsc --noEmit` to type-safety agent
- Check for `React` hook rules in architecture agent
- Add bundle size analysis to performance agent

### For API Projects
- Add OpenAPI/Swagger spec validation to architecture agent
- Add rate-limiting checks to security agent
- Add query plan analysis to performance agent

## Trust Progression

**Before using parallel agents**:
1. Use the basic `/code-review` command manually 3+ times
2. Verify it catches the issues you care about
3. Understand what good output looks like

**Before customizing agents**:
1. Run the example agents as-is on a few features
2. Note what they miss vs what's noise
3. Adjust based on your project's actual needs

**Before full automation**:
1. Use `/code-review` → `/code-review-fix` manually 5+ times
2. Verify fixes are correct and safe
3. Only then integrate into automated workflows (GitHub Actions, etc.)

Don't skip stages. Parallel agents are powerful but can generate a lot of noise if not tuned to your project.

## Integration with Commands

The updated `/code-review` command automatically uses these agents when they exist in `.claude/agents/`.

You can also invoke them from other commands:
```markdown
Use the @code-review-security agent to check for vulnerabilities in the authentication module.
```

See `reference/command-design-overview.md` for command + agent integration patterns.

## Reference

- **Pattern source**: `reference/subagents-guide.md` lines 175-185 (Pattern A)
- **Agent design guide**: `templates/AGENT-TEMPLATE.md`
- **Full subagent docs**: `reference/subagents-guide.md`

---

## Utility Agents

These agents provide **workflow optimization** — validating plans before execution
and suggesting test cases for changed code.

| Agent | Model | Tools | Purpose |
|-------|-------|-------|---------|
| **plan-validator** | Haiku | Read, Glob, Grep | Validates plan structure before /execute |
| **test-generator** | Haiku | Read, Glob, Grep | Suggests test cases from changed code |

### When to Use

- **plan-validator**: Before running `/execute` on a new plan. Catches missing sections,
  incomplete tasks, broken file references. Integrated as optional Step 1.25 in `/execute`.
- **test-generator**: After implementation, before or during `/code-review`. Identifies
  untested code paths and suggests structured test cases following project patterns.

### Usage Examples
```
Use the plan-validator agent to validate requests/my-feature-plan.md
```
```
Use the test-generator agent to suggest tests for the files changed in the last commit
```

### Multi-Instance Routing

| Agent | Instance | Model | Why |
|-------|----------|-------|-----|
| **plan-validator** | `claude-zai` | Haiku | Advisory — structural validation is pattern matching |
| **test-generator** | `claude-zai` | Haiku | Advisory — test suggestions follow existing patterns |

### Activation

Copy agents from `_examples/` to `.claude/agents/` in your project:
```bash
cp .claude/agents/_examples/plan-validator.md .claude/agents/
cp .claude/agents/_examples/test-generator.md .claude/agents/
```

---

## Model Cost Comparison

| Agent Type | Count | Model | Approx. Cost per Run |
|-----------|-------|-------|---------------------|
| Code review (4 agents parallel) | 4 | Haiku | ~$0.16 total |
| Research (2 agents parallel) | 2 | Haiku + Sonnet | ~$0.44 total |
| Utility (1-2 agents) | 2 | Haiku | ~$0.08 total |
| **Total (all 8)** | **8** | **7 Haiku + 1 Sonnet** | **~$0.68** |
