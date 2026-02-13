---
description: Orchestrate Agent Teams for coordinated multi-agent implementation using contract-first spawning
argument-hint: [feature-description or path/to/plan.md]
allowed-tools: Bash(git:*), Bash(claude:*), Bash(tmux:*), Bash(cd:*), Bash(cp:*), Bash(mkdir:*), Bash(cat:*), Bash(echo:*), Bash(wc:*), Read, Write, Edit, Task, AskUserQuestion
---

# Agent Teams — Contract-First Implementation

**Feature**: $ARGUMENTS

Orchestrates a coordinated team of Claude Code instances for parallel implementation using contract-first spawning. Upstream agents publish interface contracts before downstream agents begin. The lead relays and verifies all contracts.

**When to use**: Complex features where multiple agents need to coordinate on shared interfaces. For research, use subagents. For simple features, use `/end-to-end-feature`.

**Prerequisites**:
- Agent Teams enabled: `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`
- For split-pane: WSL + tmux (see `.claude/skills/agent-teams/references/tmux-wsl-setup.md`)
- A plan file at `requests/{feature}-plan.md` (create with `/planning` first)

**Cost Warning**: Agent Teams uses 2-4x more tokens than a single session. Each teammate = separate Claude instance.

---

## Cost Optimization — Multi-Instance Routing

Agent Teams preserves all coordination features (SendMessage, contracts, shared task list) regardless of which account you start on. Use burn accounts for execution to save your main account for planning.

**Recommended workflow**:
```
# Session 1: Planning (c1, Opus) — deep thinking
cplan
> /planning my-feature

# Session 2: Team execution (c2, Sonnet) — burn account
c2
> /team requests/my-feature-plan.md
```

**Burn order for /team sessions**: `c2 → c3 → ck → cz`
When one account hits rate limits, start the next `/team` session on the next account.

**Why this works**: All teammates are in-process subagents — they inherit the session's account. Starting on c2 means the lead AND all teammates run on c2. Coordination (SendMessage, contract relay, task list) works identically regardless of which account hosts the session.

**Model note**: The lead and teammates all use the session's default model. For c2/c3 (Pro accounts), this is typically Sonnet — which is sufficient for implementation coordination. Reserve Opus (via `cplan`) for the planning phase where deep reasoning matters most.

See `reference/multi-instance-routing.md` → Strategy 6 for the full routing pattern.

---

## Display Configuration

- **Split-pane mode** (recommended): Requires tmux. Each teammate gets its own pane. Run Claude Code inside a tmux session.
- **In-process mode** (fallback): No setup needed. Use Shift+Up/Down to navigate teammates. Ctrl+T toggles shared task list.
- Setup guide: `.claude/skills/agent-teams/references/tmux-wsl-setup.md`

---

## Step 0: Parse & Prepare

1. If `$ARGUMENTS` is a `.md` file path: read it as the plan. Extract feature name from the first heading.
2. If `$ARGUMENTS` is a description (not a file path): inform the user to create a plan first with `/planning [description]`, then re-run `/team` with the plan path. Stop here.
3. Generate kebab-case feature name for branches: `team/{feature}/`
4. Create logs directory: `mkdir -p logs/team-{feature}/`
5. **Archon Setup** (if available): Create project for team feature:
   `manage_project("create", title="Team: {feature-name}", description="Agent Teams implementation: {N} agents, contract-first")`
   Create one task per teammate: `manage_task("create", project_id=..., title="{agent-role} implementation", assignee="{agent-name}")`

---

## Step 1: Analyze Plan & Determine Team

1. Read the full plan file
2. Identify the **contract chain** — what depends on what?
   - Look for: database schemas, API endpoints, type definitions, shared interfaces
   - Common patterns:
     - `Database → Backend → Frontend` (web apps)
     - `Schema → API → UI` (data-driven)
     - `Core library → Consumers` (libraries)
     - No chain (independent modules — documentation, DevOps)
   - If the chain is unclear, ask the user to confirm
3. Determine **team size** from plan complexity:
   - 2 agents: Simple frontend/backend split
   - 3 agents: Full-stack (frontend + backend + database)
   - 4 agents: Complex system (+ testing/DevOps)
   - 5+ agents: Large systems with many independent modules
4. Identify **cross-cutting concerns**: shared conventions that need one owner (URL patterns, error shapes, auth approach, date formats)
5. Present the team structure to the user for confirmation:

```
Proposed Team Structure:

Feature: {feature-name}
Contract Chain: {upstream} → {middle} → {downstream}
Team Size: {N} agents

| Agent | Role | Owns | Template |
|-------|------|------|----------|
| 1 | {role} | {directories} | Upstream |
| 2 | {role} | {directories} | Downstream |
| 3 | {role} | {directories} | Terminal |

Cross-Cutting Concerns:
- {concern}: owned by {agent}

Proceed?
```

Use AskUserQuestion to confirm or adjust before proceeding.

---

## Step 2: Create Worktrees

For each teammate, create an isolated worktree:

```bash
git worktree add worktrees/team-{feature}/{agent-name} -b team/{feature}/{agent-name}
```

Copy the plan to each worktree:

```bash
cp requests/{feature}-plan.md worktrees/team-{feature}/{agent-name}/
```

Report worktree creation status for each teammate.

---

## Step 3: Contract-First Spawning

This is the core step. Follow contract-first spawning strictly.

1. **Enter delegate mode** (Shift+Tab) — you are the lead. Do NOT code directly. Only coordinate, relay, and validate.

2. **Spawn the most upstream agent first** using the Upstream Agent template from `templates/TEAM-SPAWN-PROMPTS.md`:
   - Set working directory to the agent's worktree
   - Include ownership boundaries (files they own, files they must NOT touch)
   - Include instruction: publish contract BEFORE implementing
   - Include cross-cutting concerns they define

3. **Wait for the upstream agent to publish their contract** (schema, function signatures, type definitions).

4. **Verify the contract**:
   - Is it complete? (all tables, endpoints, types defined?)
   - Any ambiguities? (vague types, unclear naming?)
   - Missing fields? (foreign keys, error responses, edge cases?)
   - If issues found: ask the agent to clarify or amend

5. **Spawn the next downstream agent** with the verified contract pasted into their prompt:
   - Use the Downstream or Terminal template from `templates/TEAM-SPAWN-PROMPTS.md`
   - Include the full verified upstream contract in the "Contract you MUST conform to" section
   - Include ownership boundaries and cross-cutting concerns

6. **Repeat** until all chain agents are spawned.

7. **Spawn independent agents** (testing, docs) in parallel — they don't need upstream contracts. Use the Independent template.

---

## Step 4: Monitor & Validate

1. **Monitor agent progress**. Intervene if:
   - An agent modifies files outside their ownership boundaries
   - An agent's implementation diverges from the verified contract
   - An agent is stuck (30+ turns without progress)

2. **When agents report done**, run pre-completion verification:
   - Each agent must have run their domain-specific validation (tests, type checks)
   - Compare actual implementations against published contracts — catch any drift

2b. **Archon** (if available): Mark completed agent's task as done:
    `manage_task("update", task_id="...", status="done")`

3. **Cross-review phase**: Have agents review each other's integration points.
   - Backend reviews frontend's API calls
   - Database reviews backend's query patterns

4. **Lead end-to-end validation**: Verify the integrated system works across all components.

---

## Step 5: Merge & Commit

1. **Merge worktrees sequentially** (upstream first):
   ```bash
   git checkout {original-branch}
   git merge team/{feature}/{upstream-agent} --no-ff -m "merge: integrate {upstream-agent}"
   # Run tests after each merge
   git merge team/{feature}/{downstream-agent} --no-ff -m "merge: integrate {downstream-agent}"
   # Run tests again
   ```

2. **If merge conflicts**: Stop, report conflicting files, provide resolution guidance.

3. **Run full test suite** after all merges.

4. **Cleanup worktrees**:
   ```bash
   git worktree remove worktrees/team-{feature}/{agent-name}
   ```
   Repeat for each teammate.

5. **Sync to Archon** (if available):
   - Mark all team tasks as "done": `manage_task("update", task_id="...", status="done")`
   - Update project: `manage_project("update", project_id="...", description="Team implementation complete. All {N} agents merged successfully.")`

---

## Step 6: Report

```
Agent Teams Implementation Complete

Feature: {feature-name}
Team Size: {N} agents
Contract Chain: {upstream} → {downstream} → ...

Agents:
- {agent-1}: {role} — {status} (worktree merged)
- {agent-2}: {role} — {status} (worktree merged)
- {agent-3}: {role} — {status} (worktree merged)

Contracts Published: {N}
Contract Verification: All passed
Cross-Review: Complete

Validation: {pass/fail}
Merge: {status}

Ready for /commit
```

---

## Error Handling

| Failure Point | Action |
|---------------|--------|
| Agent Teams not enabled | Show settings: `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` and `teammateMode` config. Link to `.claude/skills/agent-teams/references/tmux-wsl-setup.md` |
| Plan file not found | Prompt user to run `/planning [feature]` first |
| Worktree creation failure | Report error, offer retry for individual worktrees or continue with remaining |
| Contract not published | Prompt upstream agent, extend turn limit. If still stuck, report to user |
| Interface divergence detected | Show diff between contract and implementation, ask lead to mediate |
| Merge conflict | Stop, report conflicting files, provide resolution steps |
| Test failure after merge | Identify which agent's merge caused the failure, offer rollback |

---

## Notes

- This command expects a **plan file**. Create one with `/planning [feature]` first.
- The lead's conversation carries context across the session, providing continuity between agents.
- **Archon sync** is best-effort: if Archon tools are unavailable, the command continues without task tracking.
- For **Carlini-style logging**: teammates write progress to `logs/team-{feature}/` for post-session debugging.
- **Model recommendation**: Use Sonnet for implementation teammates (balanced cost/capability).
- See `reference/agent-teams-overview.md` for the full architecture guide.
- See `templates/TEAM-SPAWN-PROMPTS.md` for all spawn prompt templates.
