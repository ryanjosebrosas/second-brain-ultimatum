### Extending the PIV Loop with Coordinated Multi-Agent Implementation

Agent Teams are multiple Claude Code instances coordinated by a lead agent. Each teammate runs in its own context window with access to a shared task list and inter-agent mailbox. The lead orchestrates work using **contract-first spawning** — upstream agents publish interface contracts before downstream agents begin coding. This prevents the #1 failure mode of parallel implementation: agents building against wrong interfaces.

> **Experimental Feature**: Agent Teams requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`. The API may change. Design for easy updates.

### What Agent Teams Are

- Multiple Claude Code instances running simultaneously, coordinated by a lead
- Each teammate has its own context window (separate from the lead and other teammates)
- **Shared task list**: all agents can see, claim, and update tasks
- **Mailbox**: agents send messages to each other (relayed through the lead)
- The lead enters **delegate mode** (Shift+Tab) and coordinates without coding directly
- Teammates can run in split panes (tmux/iTerm2) or in-process mode

### When to Use Agent Teams vs Subagents

Rule of thumb from Cole Medin: **"Subagents for research, Agent Teams for implementation."**

| Approach | Communication | Coordination | File Isolation | Token Cost | Best For |
|----------|---------------|--------------|----------------|------------|----------|
| **Subagents** | One-way (to main) | Main agent manages | None | Low | Research, focused tasks |
| **Cross-CLI (`/delegate`)** | One-way (send→capture) | `/delegate` command | None (same FS) | Low (external tokens) | Bulk work, review, cost optimization |
| **Agent Teams** | Two-way (mailbox) | Shared task list | Via worktrees | 2-4x higher | Coordinated implementation |
| **Worktrees + `claude -p`** | None | Manual | Full (git) | Low | Independent parallel tasks |

**Cross-CLI orchestration** uses tmux to delegate tasks to OpenCode and Codex. Unlike
Agent Teams (multiple Claude Code instances), cross-CLI leverages different providers
for cost optimization and capability routing. See `reference/cross-cli-orchestration.md`.

**Use Agent Teams when**: Multiple agents need to coordinate on shared interfaces (DB schema → API → frontend). The coordination overhead is justified by preventing interface divergence.

**Use subagents when**: Tasks are independent (parallel research, code review, analysis). No inter-agent coordination needed. 2-4x cheaper.

### Contract-First Spawning

The core orchestration pattern. Without it, parallel agents build against wrong assumptions — the backend implements endpoints the frontend doesn't expect, or the API uses a schema the database doesn't provide.

**How it works:**

1. **Identify the contract chain** from the plan: what depends on what?
   - Common: `Database → Backend → Frontend`
   - Data-driven: `Schema → API → UI`
   - Library: `Core library → Consumers`
2. **Spawn the most upstream agent first** (e.g., Database agent)
3. **Wait for contract publication** — the upstream agent publishes its interface (schema, function signatures, type definitions) BEFORE implementing
4. **Lead verifies the contract** — checks for completeness, ambiguities, missing fields
5. **Lead relays verified contract** to the next downstream agent (e.g., Backend)
6. Repeat until all agents are spawned with verified contracts

**Anti-pattern**: Telling agents to "share your API with the frontend agent." The lead must be the relay — agents don't verify each other's contracts.

**Example: 3-Agent Full-Stack Team**

```
1. Lead spawns Database agent → "Publish your schema before implementing"
2. Database agent publishes: tables, types, function signatures
3. Lead verifies schema completeness
4. Lead spawns Backend agent with verified schema pasted in prompt
5. Backend agent publishes: API endpoints, request/response shapes
6. Lead verifies API contract
7. Lead spawns Frontend agent with verified API contract in prompt
8. All agents implement in parallel against verified contracts
```

### Delegate Mode

The lead enters delegate mode with **Shift+Tab**. In delegate mode, the lead:

- **Never codes directly** — only coordinates, relays, and validates
- Identifies the contract chain from the plan
- Spawns agents in dependency order (upstream first)
- Receives and verifies contracts before forwarding
- Monitors progress and intervenes on divergence
- Runs end-to-end validation after all agents complete

### Auto-Worktree Integration

Each implementation teammate gets its own git worktree for file isolation:

- **Branch naming**: `team/{feature}/{teammate-name}` (e.g., `team/auth/database`)
- **Directory**: `worktrees/team-{feature}/{teammate-name}`
- Lead creates worktrees before spawning teammates
- Merge happens sequentially (upstream first) after validation passes

This combines Agent Teams' coordination (shared task list, messaging) with worktrees' isolation (separate file systems). No file conflicts during implementation.

### Team Sizing

Dynamic based on plan complexity. Determined by analyzing the plan, not fixed.

| Agents | Use Case | Example |
|--------|----------|---------|
| 2 | Simple split | Frontend + backend |
| 3 | Full-stack | Frontend + backend + database |
| 4 | Complex system | + testing or DevOps agent |
| 5+ | Large systems | Many independent modules |

### Spawn Prompt Structure

Each teammate prompt must include these 5 sections (from Cole Medin's tested approach):

1. **Ownership** — files they own, files they must NOT touch
2. **Scope** — what they're building (specific deliverables)
3. **Mandatory communication** — publish contract BEFORE implementing
4. **Contract conformity** — the verified upstream contract they must respect
5. **Cross-cutting concerns** — shared conventions (URL patterns, error shapes, auth approach)

See `templates/TEAM-SPAWN-PROMPTS.md` for copy-paste-ready templates.

### 5-Phase Collaboration Flow

| Phase | Mode | Description |
|-------|------|-------------|
| 1. Contracts | Sequential | Lead spawns upstream agents first. Each publishes contract. Lead verifies and relays downstream. |
| 2. Implementation | Parallel | All agents code against verified contracts. Independent agents run in parallel. |
| 3. Contract Verification | Lead-driven | Lead compares actual implementations against published contracts. Catches drift. |
| 4. Polish | Cross-review | Agents review each other's integration points. Fix mismatches. |
| 5. Validation | Lead-driven | End-to-end validation. Lead merges worktrees and runs full test suite. |

### Display Modes

| Mode | Setup | Navigation | Best For |
|------|-------|------------|----------|
| **In-process** | None (default) | Shift+Up/Down between teammates, Ctrl+T for task list | Universal fallback, quick sessions |
| **tmux** | WSL + tmux installed | Each teammate in own pane, Ctrl+B shortcuts | Visual separation, WSL users |
| **iTerm2** | macOS + iTerm2 Python API | Native split panes | macOS users |

Setup guide: `.claude/skills/agent-teams/references/tmux-wsl-setup.md`

### Configuration

**Required settings:**

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  },
  "teammateMode": "auto"
}
```

Set in `~/.claude/settings.json` (global) or `.claude/settings.local.json` (per-project).

**teammateMode values**: `"auto"` (detect best mode), `"in-process"`, `"tmux"`, `"iterm2"`

**Permissions**: Teammates inherit the lead's permission settings. No separate configuration needed.

### Token Usage Warning

Agent Teams uses **2-4x more tokens** than single sessions. Each teammate is a separate Claude instance with its own context window. The shared task list and mailbox add coordination overhead.

**Cost optimization:**
- Use subagents for research (not Agent Teams)
- Keep teams small (2-3 agents for most features)
- Only use Agent Teams when coordination adds real value (shared interfaces)
- Use Sonnet for implementation teammates (balanced cost/capability)

**Cost optimization**: Run `/planning` with Opus (`claude --model opus`) for deep reasoning, and `/team` with Sonnet (default) for focused execution.

### Trust Progression

```
Manual → Commands → Chained → Subagents → Worktrees → Agent Teams → Remote
  ↑ trust & verify ↑  ↑ trust & verify ↑  ↑ trust & verify ↑  ↑ trust & verify ↑
```

**Before using Agent Teams**: Your worktree-based parallel implementation works reliably. You've run 5+ parallel features with `/parallel-e2e` or manual worktrees. Your contract identification skills are developing.

**Agent Teams' position**: Between worktrees (parallel but uncoordinated) and remote automation (fully autonomous). Agent Teams adds coordination to parallel work.

### Limitations

- **No session resumption** — if the lead's session ends, the team is lost
- **One team per session** — but you can destroy and create new teams within a session
- **No nested teams** — a teammate cannot spawn its own team
- **Split panes require tmux/iTerm2** — in-process mode is the universal fallback
- **Task status can lag** — shared task list updates aren't instant
- **Experimental** — API and behavior may change between Claude Code versions

### Reference Files

- `.claude/commands/team.md` — The `/team` slash command for orchestrating Agent Teams
- `.claude/skills/agent-teams/SKILL.md` — Skill entry point with quick start guide
- `.claude/skills/agent-teams/references/contract-first-spawning.md` — Deep dive on contract-first spawning
- `.claude/skills/agent-teams/references/tmux-wsl-setup.md` — WSL + tmux installation and setup
- `templates/TEAM-SPAWN-PROMPTS.md` — Spawn prompt templates for all agent types
