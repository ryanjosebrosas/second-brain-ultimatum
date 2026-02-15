# Cross-CLI Orchestration Guide

> **Load when**: Delegating tasks to OpenCode or Codex, setting up multi-CLI tmux workspace, or routing tasks across providers

---

## Quick Start

### Prerequisites
- tmux installed (see `.claude/skills/agent-teams/references/tmux-wsl-setup.md`)
- OpenCode CLI installed: `go install github.com/opencode-ai/opencode@latest` or `brew install opencode`
- Codex CLI installed: `npm i -g @openai/codex` or `brew install --cask codex`
- Claude Code running inside tmux

### 30-Second Setup
```bash
# Run the setup script (creates tmux session with named panes)
bash scripts/cross-cli-setup.sh my-project

# Or manually:
tmux new-session -s my-project -n main -d
tmux send-keys -t my-project:main "claude" Enter
tmux split-window -h -t my-project:main
tmux send-keys -t my-project:main.1 "opencode" Enter
tmux split-window -v -t my-project:main.1
tmux send-keys -t my-project:main.2 "# codex ready" Enter
tmux attach -t my-project
```

---

## Configuration

### Recommended tmux Config

For optimal cross-CLI orchestration, configure tmux with:
- Mouse support enabled (`set -g mouse on`)
- High scrollback buffer (`set -g history-limit 50000`)
- Ergonomic prefix key (`set -g prefix C-f`)
- Zero escape delay (`set -g escape-time 0`)

Full config with rationale: `reference/tmux-recommended-config.md`

### Health Checks

Verify your workspace is correctly configured:

```bash
# Full health check
bash scripts/tmux-health-check.sh [session-name]

# Quick pane count check
tmux list-panes -t [session]:main -F "#{pane_index}: #{pane_title}"
```

### Setup Options

```bash
# Full 3-pane layout (default)
bash scripts/cross-cli-setup.sh my-project

# Claude-only (single pane, when OpenCode/Codex not needed)
bash scripts/cross-cli-setup.sh my-project --claude-only
```

---

## Architecture

```
tmux session: {project}
+-- pane 0: Claude Code (Opus 4.6) -- orchestrator
|   +-- /planning -- create plans
|   +-- /delegate opencode "task" -- send to OpenCode
|   +-- /delegate codex "review this" -- send to Codex
|   +-- captures output from worker panes
+-- pane 1: OpenCode -- execution worker
|   +-- receives tasks via tmux send-keys
|   +-- bulk implementation, large file processing
|   +-- flexible model selection (75+ providers)
+-- pane 2: Codex -- review worker
    +-- receives tasks via tmux send-keys
    +-- code review, bug fixes
    +-- powered by codex-1/gpt-5.3
```

---

## Task Routing Strategy

| Task Type | Route To | Why | How |
|-----------|----------|-----|-----|
| Planning & architecture | Claude Code (Opus) | Deepest reasoning, best for planning | Stay in current pane |
| Feature implementation | OpenCode or Claude Code | Flexible model choice, token-heavy | `/delegate opencode "implement X"` |
| Code review | Codex | Included with ChatGPT, optimized for review | `/delegate codex "review these changes"` |
| Bulk refactoring | OpenCode | 75+ models, potentially cheaper tokens | `/delegate opencode "refactor Y"` |
| Documentation | OpenCode | Large context, bulk text generation | `/delegate opencode "document Z"` |
| Bug investigation | Claude Code (Opus) | Deep reasoning for root cause | Stay in current pane |
| Test generation | Codex or OpenCode | Pattern matching, bulk work | `/delegate codex "generate tests"` |
| Quick fixes | Codex | Fast, included tokens | `/delegate codex "fix this typo"` |

### Decision Flowchart

```
New task arrives
|
+-- Requires deep reasoning? --> Claude Code (Opus)
|   (planning, architecture, debugging, novel problems)
|
+-- Pattern matching / review? --> Codex
|   (code review, test generation, quick fixes)
|
+-- Bulk / token-heavy work? --> OpenCode
    (implementation, refactoring, documentation, large files)
```

---

## tmux Communication Patterns

### Sending Commands

```bash
# Send a prompt to OpenCode (pane 1)
tmux send-keys -t {session}:main.1 "opencode run 'implement the auth module'" Enter

# Send a prompt to Codex (pane 2)
tmux send-keys -t {session}:main.2 "codex exec 'review src/auth.ts for security issues'" Enter

# Send literal text (avoids key name interpretation)
tmux send-keys -l -t {session}:main.1 "opencode run 'task with special chars'"
tmux send-keys -t {session}:main.1 Enter
```

### Reading Output

```bash
# Capture last 100 lines from OpenCode pane (clean, no ANSI)
tmux capture-pane -t {session}:main.1 -p -S -100

# Capture entire scrollback
tmux capture-pane -t {session}:main.1 -p -S -

# Save to file for analysis
tmux capture-pane -t {session}:main.1 -p -S -500 > /tmp/opencode-output.txt
```

### Synchronization

```bash
# Have worker signal when done (append to the delegated command)
tmux send-keys -t {session}:main.1 "opencode run 'task' && tmux wait-for -S oc-done" Enter
# Wait in orchestrator
tmux wait-for oc-done
```

### Smart Delegation via /delegate

The `/delegate` command automates the send → wait → capture pattern:

```bash
# Fire and forget (legacy behavior)
/delegate opencode "implement the auth module" --fire

# Wait for completion (default)
/delegate opencode "implement the auth module"

# Wait + capture output
/delegate codex "review src/auth.ts" --capture

# With context file forwarded
/delegate opencode "implement from this plan" --capture --context requests/auth-plan.md
```

See `.claude/commands/delegate.md` for the full command specification including error
handling and timeout configuration.

---

## Non-Interactive Mode Reference

### OpenCode
```bash
# Basic non-interactive execution
opencode run "implement the login form"

# With JSON output (for parsing)
opencode run --format json "implement the login form"

# With specific working directory
opencode run --cwd /path/to/project "implement the login form"

# Quiet mode (disable spinner, useful for scripts)
opencode run --quiet "implement the login form"

# Session continuation
opencode run --session my-session "task 1"
opencode run --session my-session --continue "task 2"
```

### Codex
```bash
# Basic non-interactive execution
codex exec "review this file for bugs"

# Full auto mode (no confirmation prompts)
codex exec --full-auto "review this file for bugs"

# With JSON output (JSONL event stream)
codex exec --json "review this file for bugs"

# With working directory
codex exec --cd /path/to/project "review this file for bugs"

# Skip git repo check (for non-repo directories)
codex exec --skip-git-repo-check "analyze this code"

# Disable all approval prompts
codex exec --ask-for-approval never "fix the bug in login.ts"
```

### Claude Code (Headless)
```bash
# Basic non-interactive execution
claude -p "find and fix bug in auth.py"

# Auto-approve specific tools
claude -p "run tests and fix failures" \
  --allowedTools "Bash,Read,Edit"

# JSON output
claude -p "analyze this code" --output-format json

# Continue previous conversation
claude -p "follow up on last task" --continue

# Resume specific session
claude -p "continue work" --resume SESSION_ID
```

---

## Gotchas & Known Issues

| Issue | Impact | Workaround |
|-------|--------|------------|
| `send-keys` is asynchronous | No built-in completion detection | Use `tmux wait-for` signals or poll with `capture-pane` |
| Semicolons in commands | May be parsed as command termination | Escape semicolons or use `-l` flag for literal strings |
| ANSI codes in captured output | Parsing fails on escape sequences | Omit `-e` flag; strip ANSI with `sed 's/\x1b\[[0-9;]*m//g'` |
| OpenCode MCP cold boot | Slow startup with MCP servers | Use `opencode serve` as persistent server |
| Codex requires Git repo | `codex exec` fails outside repos | Use `--skip-git-repo-check` flag |
| Pane IDs drift on resize | Targeting wrong pane after splits | Use session:window.pane naming, not bare pane IDs |
| Scrollback buffer limits | Can't capture old history | Set `set-option -g history-limit 50000` in tmux.conf |
| Quotes in prompts | Nested quoting breaks send-keys | Use single quotes inside double quotes, or heredoc patterns |
| OAuth prompts block automation | MCP servers need interactive auth | Pre-authenticate before automation: `opencode mcp auth` / `codex mcp auth` |

---

## Cost & Token Strategy

| CLI Tool | Billing Model | Token Advantage | Best For |
|----------|--------------|-----------------|----------|
| Claude Code (MAX) | $100-200/month flat | Deep reasoning per token | Planning, orchestration, hard problems |
| OpenCode | Varies by provider | 75+ models, use cheapest | Bulk work, large files, flexible routing |
| Codex | Included with ChatGPT Plus/Pro | "Free" with subscription | Reviews, quick fixes, test generation |

**Strategy**: Use Claude Code MAX quota for high-leverage planning (Opus). Offload token-heavy execution to OpenCode (cheap models) and review to Codex (included tokens). This preserves Claude MAX quota for reasoning-heavy work.

---

## Integration with Existing System

### Cross-CLI vs Agent Teams vs Subagents

Three coordination mechanisms serve different purposes:

| Aspect | Subagents | Cross-CLI | Agent Teams |
|--------|-----------|-----------|-------------|
| **What** | Claude Code spawns focused workers | Claude Code delegates to OpenCode/Codex | Multiple Claude Code instances coordinate |
| **Communication** | One-way (worker → main) | One-way (send → capture) | Two-way (shared task list + mailbox) |
| **Coordination** | Main agent manages | `/delegate` command | Shared task list, contract relay |
| **File isolation** | None (shared workspace) | Separate tmux panes, same filesystem | Git worktrees (separate filesystems) |
| **Token cost** | Low (focused tasks) | Low (uses external CLI tokens) | 2-4x higher (multiple Claude instances) |
| **Stability** | Stable (built-in) | Stable (tmux is proven) | Experimental (API may change) |
| **Best for** | Research, analysis, review | Bulk implementation, code review, cost optimization | Coordinated multi-agent work with shared interfaces |

### Decision Flowchart

```
Need parallel work?
|
+-- No → Use single session (commands + subagents)
|
+-- Yes → Do agents need to coordinate on shared interfaces?
    |
    +-- No → Use Cross-CLI (/delegate) or worktrees (claude -p)
    |        Choose based on: need different CLI tools? → Cross-CLI
    |                         need file isolation? → Worktrees
    |
    +-- Yes → Is Agent Teams stable and cost acceptable?
        |
        +-- Yes → Use Agent Teams (/team)
        +-- No  → Use Cross-CLI with manual coordination
```

### Relationship to Multi-Model Strategy

Cross-CLI orchestration extends the multi-model strategy across providers:

1. **Within Claude Code**: Haiku (agents) → Sonnet (execution) → Opus (planning)
2. **Across CLIs**: Claude Code (reasoning) → OpenCode (bulk/cheap) → Codex (review/included)
3. **Both compose**: Claude Code (Opus) plans, delegates bulk work to OpenCode, reviews via Codex

---

## Reference

- OpenCode docs: https://opencode.ai/docs/cli/
- Codex docs: https://developers.openai.com/codex/cli/
- tmux manual: https://www.man7.org/linux/man-pages/man1/tmux.1.html
- CLI Agent Orchestrator (AWS): https://github.com/awslabs/cli-agent-orchestrator
- Named Tmux Manager: https://github.com/Dicklesworthstone/ntm
- Recommended tmux config: `reference/tmux-recommended-config.md`
- Health check script: `scripts/tmux-health-check.sh`
- Setup script: `scripts/cross-cli-setup.sh`
- Delegation command: `/delegate`
