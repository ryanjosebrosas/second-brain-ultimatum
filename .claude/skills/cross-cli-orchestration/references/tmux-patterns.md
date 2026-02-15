# tmux Orchestration Patterns

Detailed patterns for cross-CLI communication via tmux. Load this reference when actively orchestrating work across Claude Code, OpenCode, and Codex.

---

## Pane Targeting

### Naming Convention

The setup script creates a standard layout:
- `{session}:main.0` — Claude Code (orchestrator)
- `{session}:main.1` — OpenCode (worker)
- `{session}:main.2` — Codex (reviewer)

### Getting Current Session
```bash
SESSION=$(tmux display-message -p '#S')
```

---

## Sending Commands (send-keys)

### Basic Pattern
```bash
# Send command and press Enter
tmux send-keys -t $SESSION:main.1 "command here" Enter
```

### Literal Mode (avoids key name interpretation)
```bash
# Use -l flag when text contains reserved words (Enter, Tab, etc.)
tmux send-keys -l -t $SESSION:main.1 "text with Enter in it"
tmux send-keys -t $SESSION:main.1 Enter
```

### Quoting Strategies
```bash
# Single quotes inside double quotes (recommended)
tmux send-keys -t $SESSION:main.1 "opencode run 'implement auth'" Enter

# Escaped double quotes (when prompt needs doubles)
tmux send-keys -t $SESSION:main.1 "codex exec \"review this\"" Enter

# Heredoc for complex prompts (multi-line)
tmux send-keys -t $SESSION:main.1 "opencode run 'implement the following:
1. Create auth module
2. Add login endpoint
3. Add tests'" Enter
```

---

## Reading Output (capture-pane)

### Capture Recent Output
```bash
# Last 100 lines (clean, no ANSI codes)
tmux capture-pane -t $SESSION:main.1 -p -S -100

# Last 500 lines saved to file
tmux capture-pane -t $SESSION:main.1 -p -S -500 > /tmp/worker-output.txt
```

### Capture Entire Scrollback
```bash
tmux capture-pane -t $SESSION:main.1 -p -S -
```

### Strip ANSI Codes (for programmatic parsing)
```bash
tmux capture-pane -t $SESSION:main.1 -p -S -100 | sed 's/\x1b\[[0-9;]*m//g'
```

---

## Synchronization (wait-for)

### Signal-Based Completion Detection
```bash
# Orchestrator sends command with completion signal
tmux send-keys -t $SESSION:main.1 "opencode run 'task' && tmux wait-for -S task-done" Enter

# Orchestrator waits for signal
tmux wait-for task-done

# Then captures output
tmux capture-pane -t $SESSION:main.1 -p -S -100
```

### Poll-Based Monitoring (alternative)
```bash
# Check if pane is idle (no process running)
# Useful when wait-for signals aren't practical
while tmux capture-pane -t $SESSION:main.1 -p -S -1 | grep -q "running"; do
  sleep 5
done
```

---

## Common Gotchas

| Issue | Solution |
|-------|----------|
| Semicolons break commands | Use `-l` flag or escape: `\;` |
| Spaces stripped from strings | Wrap in double quotes |
| Pane IDs change on window resize | Use `{session}:{window}.{pane}` not bare pane IDs |
| Nested tmux sessions | Never nest — use windows/panes within one session |
| Scrollback buffer too small | Set `history-limit 50000` in tmux.conf or setup script |
