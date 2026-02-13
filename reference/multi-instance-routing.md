# Multi-Instance Routing Guide

> **Load when**: You have multiple Claude accounts and want to route different tasks to different instances for cost optimization, load distribution, or team collaboration
> **Status (2026-02-13)**: ACTIVE — Multi-instance routing is configured via `~/llm-functions.sh` (sourced in `.bashrc`). All 5 instances are authenticated. Run `claude-list` in an interactive terminal to see available instances.

---

## What Is Multi-Instance Routing?

Instead of using different models (Haiku/Sonnet/Opus), you use **different Claude accounts/instances** to distribute work across:
- Multiple API keys (distribute load, avoid rate limits)
- Team member accounts (track who did what)
- Specialized instances (cheap tasks vs premium tasks)
- Cost centers (bill different work to different accounts)

**Key difference from multi-model**:
- Multi-model: Same account, different model intelligence (Haiku/Sonnet/Opus)
- Multi-instance: Different accounts, potentially different billing/limits/permissions

---

## Your Available Instances

Configured in `~/llm-functions.sh`, sourced via `.bashrc` at shell startup:

| Instance | Alias | Account | Config Dir | Best For |
|----------|-------|---------|-----------|----------|
| `claude1` | `c1` | Main Account (MAX 20x) | `~/.claude-main` | **Planning, PIV Loop, main orchestration** |
| `claude2` | `c2` | design@brainforge.ai (Pro) | `~/.claude-design` | **Burn first: parallel execution** |
| `claude3` | `c3` | Ryan.Brosas@brainforge.ai (Pro) | `~/.claude-ryan` | **Burn first: parallel execution** |
| `claude-kimi` | `ck` | Kimi | `~/.claude-kimi` | **Fallback 1: overflow when c2/c3 rate-limited** |
| `claude-zai` | `cz` | Z.AI GLM | `~/.claude-zai` | **Fallback 2: cheapest, non-critical tasks** |

**Burn order**: c2/c3 → kimi → zai | **Orchestrator**: c1
**Planning shortcut**: `cplan` = `claude1 --model opus`
**Utilities**: `claude-list` (show instances), `claude-which` (show active), `claude-health` (check auth)

---

## Strategic Routing

### Strategy 1: Criticality-Based Routing (RECOMMENDED)

Route based on how vital the task is:

```
Main Conversation (claude1 - Main Account)
  ├─> Type Safety Review (claude-zai, Haiku) ─── Non-critical, spammable
  ├─> Security Review (claude2, Sonnet) ───────── VITAL, can't fail
  ├─> Architecture Review (claude2, Sonnet) ───── VITAL, design expertise
  └─> Performance Review (claude3, Sonnet) ────── VITAL, critical issues
```

**Routing rules**:
- `claude-zai` → Tasks where false negatives are acceptable
- `claude2/3` → Tasks where quality matters, can't afford to miss issues
- `claude1` → Orchestration, main work

**Use case**: Parallel code review with smart cost/quality tradeoffs

### Strategy 2: Load-Balanced Vital Work

Distribute Sonnet-level vital tasks across `claude2` and `claude3`:

```
Main Planning (claude1 - PIV Loop orchestration)
  ├─> Security Review (claude2 - Vital Sonnet work)
  ├─> Architecture Review (claude2 - Vital Sonnet work)
  └─> Performance Review (claude3 - Vital Sonnet work)
```

**Use case**: Avoid hitting rate limits on single account, distribute vital work across two instances

### Strategy 3: Load Distribution

Distribute parallel agents across instances to avoid rate limits:

```
Main Agent (claude1)
  ├─> Agent 1 (claude1)
  ├─> Agent 2 (claude2)
  ├─> Agent 3 (claude3)
  └─> Agent 4 (claude-zai)
```

**Use case**: High-volume parallel execution, avoid hitting API rate limits on single account

### Strategy 4: Combined Multi-Model + Multi-Instance

Best of both worlds:

```
Main Conversation (claude1, Sonnet)
  ├─> Type Safety (claude-zai, Haiku) ─── cheapest
  ├─> Security (claude-zai, Haiku) ────── cheapest
  ├─> Architecture (claude2, Sonnet) ──── design expertise
  └─> Performance (claude1, Opus) ─────── premium analysis
```

### Strategy 5: Execution Fallback Chain (for Plan Decomposition)

When executing decomposed plans, distribute sub-plans across instances with fallback:

```
Planning (claude1, Opus)
  → Produces: overview + N sub-plans

Execution Fallback Chain:
  Sub-plan 01 → claude2 (Sonnet, primary)
  Sub-plan 02 → claude3 (Sonnet, secondary)
  Sub-plan 03 → claude2 (Sonnet, round-robin back)
  ...
  If claude2 rate-limited → switch to claude3
  If claude3 rate-limited → fall back to claude1 (Sonnet)
```

**Routing rules**:
- `claude2` → Primary execution instance (odd-numbered sub-plans)
- `claude3` → Secondary execution instance (even-numbered sub-plans)
- `claude1` (Sonnet) → Fallback if both primary and secondary hit rate limits
- Round-robin distribution keeps both instances active

**Rate limit detection**:
- If `claude -p` exits with error containing "rate_limited" or "429"
- Or if process exceeds expected duration by 3x (indicates throttling)
- Switch to next instance in chain

**Manual execution** (recommended for complex features):
```bash
# Sub-plan 1 on claude2
claude2 --model sonnet
> /execute requests/{feature}-plan-01-foundation.md

# Sub-plan 2 on claude3
claude3 --model sonnet
> /execute requests/{feature}-plan-02-core.md

# If rate-limited, fall back to claude1
claude1 --model sonnet  # Note: Sonnet, not Opus
> /execute requests/{feature}-plan-03-integration.md
```

### Strategy 6: Agent Teams Session Routing

Route entire `/team` sessions to burn accounts. Planning stays on c1 (Opus), team execution goes to c2/c3 (Sonnet).

```
Planning (claude1, Opus)
  → /planning my-feature
  → Produces: requests/my-feature-plan.md

Team Execution (claude2 or claude3, Sonnet)
  → /team requests/my-feature-plan.md
  → Lead + all teammates on same burn account
  → Full coordination: SendMessage, contracts, shared task list
  → Burn order: c2 → c3 → ck → cz
```

**Why session-level**: Agent Teams teammates are in-process subagents — they inherit the parent session's account and model. There's no mechanism to route individual teammates to different accounts. The Task tool has no `instance` parameter, and agent frontmatter has no `instance` field.

**What's preserved**: Everything. SendMessage, contract-first spawning, shared task list, lead coordination, auto-worktrees — all work identically on any account. The account only affects billing and rate limits.

**What changes**: Token costs go to the burn account instead of c1. When c2 hits rate limits, start a new session on c3. The plan file is portable — same plan works on any account.

**Rate limit recovery**:
- If c2 rate-limited mid-session: Session may slow down. Complete current team run, then switch to c3 for next `/team` session.
- If mid-team rate limit is severe: Ask user whether to continue (slower) or abort and restart on c3.

**Use case**: Any `/team` session. This should be the default routing for team execution.

---

## How to Configure Agents for Specific Instances

### Method 1: Environment Variable (Per Session)

Set the instance before running commands:

```bash
# Use cheap instance for code review
export CLAUDE_INSTANCE=claude-zai
claude code-review

# Use main instance for planning
export CLAUDE_INSTANCE=claude1
claude planning "new feature"
```

### Method 2: Command Prefix

Prefix commands with specific instance:

```bash
claude-zai code-review          # Route to Z.AI cheap instance
claude1 planning "feature"      # Route to main account
claude2 design-review           # Route to design account
```

### Method 3: Agent Frontmatter — NOT YET SUPPORTED

> **Status**: As of Claude Code's current version, agent frontmatter does NOT support an `instance` field. Supported fields are: `name`, `description`, `tools`, `disallowedTools`, `model`, `maxTurns`, `skills`, `mcpServers`, `hooks`, `memory`, `color`, `permissionMode`. There is no mechanism to route a subagent to a specific Claude account via frontmatter.

```yaml
---
name: code-review-type-safety
model: haiku
# instance: claude-zai  # NOT SUPPORTED — this field is ignored
tools: ["Read", "Glob", "Grep", "Bash"]
---
```

**Workaround**: Use Method 2 (Command Prefix) or Method 4 (Wrapper Scripts) instead. These are the working alternatives for instance routing today.

**Practical workaround**: The `instance` field in agent frontmatter is aspirational documentation — it indicates which instance the agent SHOULD be routed to when running manually. When using `/code-review` or `/planning`, the user starts the session with the desired instance (e.g., `cz` for cheap review work). The agents inherit the session's account.

### Method 4: Wrapper Scripts

Create routing scripts for common workflows:

```bash
# .claude/scripts/cheap-review.sh
#!/bin/bash
export CLAUDE_INSTANCE=claude-zai
claude code-review "$@"
```

Then use: `./claude/scripts/cheap-review.sh`

---

## Recommended Routing Rules

### Route to `claude-zai` (Spammable, Non-Critical):
- ✅ Type safety checks (helpful but not critical)
- ✅ Linting and formatting
- ✅ Simple refactoring (rename, extract)
- ✅ Test generation from patterns
- ✅ Documentation generation
- ✅ Search and analysis (grep, glob, read)
- ✅ Code style checks
- ❌ NOT security review (too vital!)
- ❌ NOT architecture review (consistency is vital)
- ❌ NOT performance review (critical issues can't be missed)

### Route to `claude1` (Main - Planning & PIV Loop):
- ✅ **Planning** (`/planning`) - Core PIV Loop
- ✅ **Implementation** (`/execute`) - Core PIV Loop
- ✅ **Main conversation orchestration** - Primary work
- ✅ **Commit messages and PR creation** - PIV Loop completion
- ✅ **Complex architecture decisions** (with Opus model)
- ✅ **End-to-end workflows** (`/end-to-end-feature`)

### Route to `claude2` (Vital Sonnet Work - Load Balanced):
- ✅ Security review (VITAL - can't miss vulnerabilities)
- ✅ Architecture review (VITAL - consistency + patterns)
- ✅ Any vital task requiring Sonnet
- ✅ Load distribution to avoid rate limits

### Route to `claude3` (Vital Sonnet Work - Load Balanced):
- ✅ Performance review (VITAL - critical issues)
- ✅ Complex code analysis
- ✅ Any vital task requiring Sonnet
- ✅ Load distribution to avoid rate limits

### Route to `claude2` + `claude3` (Execution - Load Balanced):
- ✅ Sub-plan execution from decomposed plans (round-robin)
- ✅ `/execute` for standard plans (overflow from claude1)
- ✅ Any Sonnet implementation work
- ✅ Integration testing and validation
- ✅ `/team` sessions — full Agent Teams with contract-first spawning

---

## Integration with Parallel Code Review

### Current Setup (Multi-Model Only)

```
Main Agent (Sonnet)
  ├─> Type Safety (Haiku)
  ├─> Security (Haiku)
  ├─> Architecture (Haiku)
  └─> Performance (Haiku)
```

### Enhanced Setup (Multi-Instance + Multi-Model)

```
Main Agent (claude1, Sonnet)
  ├─> Type Safety (claude-zai, Haiku) ──┐
  ├─> Security (claude-zai, Haiku) ─────┤  Routed to cheap instance
  ├─> Architecture (claude-zai, Haiku) ─┤  + using cheap model
  └─> Performance (claude-zai, Haiku) ──┘  = Maximum savings
```

**Combined savings**:
- Cheap model (Haiku): 70% cost reduction vs Sonnet
- Cheap instance (Z.AI GLM): Additional savings on top
- Parallel execution: 40-50% time savings

---

## Cost Optimization Examples

### Scenario 1: Code Review

**Without routing** (all on claude1):
- 4 agents × Sonnet cost × main account rate = $$$$

**With multi-model only** (all on claude1):
- 4 agents × Haiku cost × main account rate = $$ (70% savings)

**With multi-instance + multi-model**:
- 4 agents × Haiku cost × cheap instance rate = $ (80-90% savings)

### Scenario 2: Parallel Research

**Without routing**:
- 5 parallel agents on claude1 → hit rate limit, sequential fallback

**With multi-instance**:
- Distribute across claude1, claude2, claude3, claude-zai → no rate limits

---

## How to Implement

### Step 1: Test Instance Routing

Verify you can route commands:

```bash
claude-zai --version
claude1 --version
claude2 --version
claude3 --version
```

### Step 2: Use Wrapper Scripts for Agent Routing

Agent frontmatter does NOT support `instance` — use wrapper scripts or command prefixes instead. See Method 2 and Method 4 above.

### Step 3: Create Routing Wrapper Scripts

```bash
mkdir -p .claude/scripts

# cheap-review.sh
echo '#!/bin/bash
export CLAUDE_INSTANCE=claude-zai
claude /code-review "$@"' > .claude/scripts/cheap-review.sh

chmod +x .claude/scripts/cheap-review.sh
```

### Step 4: Update Commands to Use Routing

Modify `/code-review` command to explicitly route to cheap instance:

```markdown
When parallel mode is enabled, route all 4 review agents to claude-zai instance for cost savings.

Launch agents with instance routing:
- claude-zai: code-review-type-safety
- claude-zai: code-review-security
- claude-zai: code-review-architecture
- claude-zai: code-review-performance
```

---

## Team Collaboration Patterns

### Pattern 1: Work Assignment

Route work to specific team member accounts:

```markdown
/planning → claude1 (main orchestration)
/execute backend → claude3 (Ryan's account - backend work)
/execute frontend → claude2 (design account - UI work)
/code-review → claude-zai (cheap automated review)
```

### Pattern 2: Approval Workflow

```
Developer creates PR → claude-zai reviews (cheap, fast)
  ↓
If issues found → claude1 analyzes (main account, detailed)
  ↓
Senior review needed → claude3 (team lead account)
```

### Pattern 3: Load Balancing

Distribute heavy parallel workloads:

```python
agents = [
    ('agent1', 'claude1'),
    ('agent2', 'claude2'),
    ('agent3', 'claude3'),
    ('agent4', 'claude-zai'),
    ('agent5', 'claude1'),  # Round-robin back
]
```

---

## Limitations & Considerations

### Rate Limits
- Each instance has its own rate limits
- Distributing work helps avoid hitting limits
- But adds coordination complexity

### Cost Tracking
- Work spread across accounts = harder to track total cost
- Use instance routing strategically, not randomly
- Document routing rules in CLAUDE.md

### Context Isolation
- Each instance is separate → no shared conversation history
- Plan must be explicit (agents can't reference main conversation context)
- Good for isolation, bad for context-heavy tasks

### Authentication
- Must authenticate each instance separately
- Credentials stored in separate `.claude-*` directories
- Ensure team members have access to their assigned instances

---

## When to Use Multi-Instance

**Use multi-instance when**:
- ✅ You have multiple accounts with different pricing
- ✅ You need to distribute load across rate limits
- ✅ You want team-based work attribution
- ✅ You want to isolate cheap tasks from premium tasks

**Stick with multi-model (single instance) when**:
- ❌ You only have one account
- ❌ Cost tracking across accounts is complex
- ❌ Team coordination overhead isn't worth it
- ❌ Rate limits aren't an issue

---

## Combining with Existing System

### Multi-Model Strategy (reference/multi-model-strategy.md)
- Haiku for pattern matching
- Sonnet for balanced work
- Opus for complex reasoning

### Multi-Instance Strategy (this guide)
- claude-zai for cheap repetitive tasks
- claude1 for main orchestration
- claude2/3 for team-specific work

### Combined Strategy
- `claude-zai + Haiku` = cheapest (code review)
- `claude1 + Sonnet` = default (planning, implementation)
- `claude1 + Opus` = premium (complex architecture)
- `claude2 + Sonnet` = specialized (design work)

---

## Quick Reference

```bash
# Check available instances
claude-list

# Route specific command
claude-zai /code-review
claude1 /planning "feature"
claude2 /design-review

# Set instance for session
export CLAUDE_INSTANCE=claude-zai
claude /code-review

# Wrapper script
./.claude/scripts/cheap-review.sh
```

---

## Next Steps

1. **Test routing**: Try `claude-zai --version` and other instances
2. **Create wrapper scripts**: For common cheap tasks (see Method 4)
3. **Document routing rules**: Add to your project's CLAUDE.md
4. **Monitor costs**: Track savings from routing cheap tasks to claude-zai
5. **Watch for updates**: Agent frontmatter `instance` support may be added in future Claude Code versions

---

## Verified Answers (Previously Open Questions)

### 1. Does agent frontmatter support `instance` field?

**NO.** As of the current Claude Code version, the supported agent frontmatter fields are: `name`, `description`, `tools`, `disallowedTools`, `model`, `maxTurns`, `skills`, `mcpServers`, `hooks`, `memory`, `color`, `permissionMode`. There is no `instance` field. Source: [Claude Code Sub-agents Documentation](https://code.claude.com/docs/en/sub-agents.md).

### 2. Can the Task tool accept an instance parameter?

**NO.** The Task tool accepts: `prompt`, `subagent_type`, `model`, `max_turns`, `run_in_background`, `resume`, `description`. There is no `instance` parameter. Subagents inherit the current session's account.

### 3. What's the pricing difference between instances?

- **MAX subscription** ($100-200/month): All instances on the same subscription share the same usage pool. No per-instance pricing difference — the benefit is rate limit distribution, not cost savings.
- **API billing** (pay-per-token): Each instance uses its own API key and billing account. Costs are tracked separately per account. Pricing depends on each account's plan and negotiated rates.

### 4. Do all instances have the same rate limits?

**Each account has its own rate limits.** Multiple MAX subscriptions = separate rate limit pools. This is the primary benefit of multi-instance routing — distributing work across accounts avoids hitting rate limits on any single account. API billing accounts also have independent rate limits.

### 5. How to track which instance did what work?

- **Git commits**: Each instance creates commits under its authenticated user. Track via `git log --format='%an: %s'`.
- **Branch naming**: Use convention `{instance}/{feature}` (e.g., `claude-zai/code-review`, `claude1/auth-feature`).
- **Wrapper script logging**: Add logging to wrapper scripts that records which instance ran which command.
- **Archon tasks**: Assign tasks to specific instances via the `assignee` field for visibility on the Kanban board.

---

## Supported vs Aspirational Methods

| Method | Status | Notes |
|--------|--------|-------|
| **Method 1: Environment Variable** | Supported | Set `CLAUDE_INSTANCE` before running commands |
| **Method 2: Command Prefix** | Supported | `claude-zai /code-review` works if aliases/symlinks are configured |
| **Method 4: Wrapper Scripts** | Supported | Shell scripts that set env vars and run commands |
| **Method 3: Agent Frontmatter** | NOT YET SUPPORTED | No `instance` field in agent frontmatter. May be added in future versions. |
| **Task tool `instance` param** | NOT YET SUPPORTED | Cannot route subagents to specific instances programmatically. |

**Recommendation**: Use Method 2 (Command Prefix) for interactive work and Method 4 (Wrapper Scripts) for automated workflows. These are reliable and available today.
