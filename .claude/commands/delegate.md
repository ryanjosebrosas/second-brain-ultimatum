---
description: Delegate a task to OpenCode or Codex via tmux with output capture
argument-hint: <opencode|codex> "task description" [--fire|--wait|--capture] [--context path/to/file]
allowed-tools: Bash(tmux:*), Bash(sleep:*), Bash(sed:*), Bash(kill:*), Bash(cat:*), Bash(wc:*), Read, AskUserQuestion
---

# Delegate: Smart Task Delegation to External CLI

## Arguments

- **Target CLI**: $1 — `opencode` or `codex`
- **Task description**: $2 — the task prompt to send
- **Mode** (optional): $3
  - `--fire` — Send and forget (legacy behavior, no output capture)
  - `--wait` — Send, wait for completion, show confirmation (default)
  - `--capture` — Send, wait for completion, capture and display output
- **Context file** (optional): `--context path/to/file` — file to include in the task prompt

## Process

### 1. Validate Environment

1. **Verify tmux session**: Run `tmux display-message -p '#S'` to get the current session name.
   - If not inside tmux: stop and inform the user:
     ```
     Not inside a tmux session. To set up:
       bash scripts/cross-cli-setup.sh [session-name]
     ```

2. **Parse arguments**:
   - If `$1` is "opencode": target pane = 1, CLI command prefix = `opencode run`
   - If `$1` is "codex": target pane = 2, CLI command prefix = `codex exec --full-auto`
   - If neither: show usage and stop:
     ```
     Usage: /delegate <opencode|codex> "task description" [--fire|--wait|--capture] [--context file]
     ```

3. **Determine mode** from $3 (or remaining args):
   - `--fire` → FIRE mode (send only, no waiting)
   - `--wait` → WAIT mode (send + wait for completion signal)
   - `--capture` → CAPTURE mode (send + wait + capture output)
   - If no mode specified → default to WAIT mode

4. **Check for context file**: Scan remaining args for `--context`. If found, read the
   file path that follows. Verify the file exists. If it doesn't exist, warn and continue
   without context.

5. **Verify target pane exists**: Run `tmux list-panes -t {session}:main -F "#{pane_index}"`.
   - If the target pane index is NOT in the list: stop and inform:
     ```
     Pane {N} does not exist in session {session}.
     Your session may be in claude-only mode (single pane).
     To create a full 3-pane layout: bash scripts/cross-cli-setup.sh [name]
     ```

6. **Get session name**: Store result of `tmux display-message -p '#S'` for use in all
   subsequent tmux commands.

### 2. Construct Task Prompt

Build the full prompt to send to the worker CLI.

**Base prompt**: Use the task description from $2.

**If --context was provided**: Prepend context to the task prompt:
1. Read the context file using the Read tool
2. Construct an enriched prompt:
   ```
   Context from {filename}:
   ---
   {file contents, truncated to first 200 lines if longer}
   ---

   Task: {original task description}
   ```

**Working directory**: Both OpenCode and Codex support working directory flags:
- OpenCode: `opencode run --cwd "$(pwd)" '{prompt}'`
- Codex: `codex exec --cd "$(pwd)" --full-auto '{prompt}'`

Always include the working directory flag to ensure the worker operates in the same
project directory as the orchestrator.

**Construct the full command**:
- OpenCode: `opencode run --cwd "$(pwd)" '{enriched prompt}'`
- Codex: `codex exec --cd "$(pwd)" --full-auto '{enriched prompt}'`

### 3. Execute Delegation

Get the session name:
```bash
SESSION=$(tmux display-message -p '#S')
```

#### Mode: FIRE (--fire)

Send the command and return immediately. No completion detection.

```bash
tmux send-keys -t $SESSION:main.{N} "{full_command}" Enter
```

Report the delegation and provide manual monitoring instructions.

#### Mode: WAIT (--wait, default)

Send the command with a completion signal and wait for it.

```bash
# Generate unique signal name to avoid collisions
SIGNAL="delegate-done-$(date +%s)"

# Send command with completion signal appended
tmux send-keys -t $SESSION:main.{N} "{full_command} && tmux wait-for -S $SIGNAL" Enter

# Wait for completion with timeout (5 minutes default)
# Use a background sleep + kill as timeout mechanism
TIMEOUT=300
(sleep $TIMEOUT && tmux wait-for -S $SIGNAL 2>/dev/null) &
TIMEOUT_PID=$!

# Wait for the signal
tmux wait-for $SIGNAL

# Kill the timeout process if it's still running
kill $TIMEOUT_PID 2>/dev/null || true
```

Report completion status and duration.

#### Mode: CAPTURE (--capture)

Send command, wait for completion (same as WAIT mode), then capture and display output.

```bash
# Capture output (last 200 lines, ANSI stripped)
OUTPUT=$(tmux capture-pane -t $SESSION:main.{N} -p -S -200 | sed 's/\x1b\[[0-9;]*m//g')

# Also save to file for reference
OUTFILE="/tmp/delegate-{target}-$(date +%Y%m%d-%H%M%S).txt"
echo "$OUTPUT" > "$OUTFILE"
```

Display the captured output inline and report the saved file path.

## Output

### FIRE Mode Output
```
Delegated to {target} (fire-and-forget):
  Task: {task description}
  Pane: {session}:main.{N}
  Working dir: {pwd}

Monitor:
  Switch pane: Ctrl+B (or Ctrl+F) then o
  Capture output: tmux capture-pane -t {session}:main.{N} -p -S -100
```

### WAIT Mode Output
```
Delegated to {target} (waiting for completion...):
  Task: {task description}
  Pane: {session}:main.{N}
  Timeout: 300s

[... waiting ...]

Delegation complete:
  Status: Completed | Timed out
  Duration: {elapsed}s
  View output: tmux capture-pane -t {session}:main.{N} -p -S -100
```

### CAPTURE Mode Output
```
Delegated to {target} (waiting for completion...):
  Task: {task description}
  Pane: {session}:main.{N}

[... waiting ...]

Delegation complete:
  Status: Completed
  Duration: {elapsed}s
  Output saved: /tmp/delegate-{target}-{timestamp}.txt

--- Captured Output (last 200 lines) ---
{cleaned output from worker pane}
--- End Output ---
```

### Context Mode Output (when --context used)
```
Delegated to {target} with context:
  Task: {task description}
  Context: {context file path} ({line count} lines)
  Pane: {session}:main.{N}
```

## Error Handling

| Error | Detection | Response |
|-------|-----------|----------|
| Not in tmux | `tmux display-message` fails | "Not inside a tmux session. Run: `bash scripts/cross-cli-setup.sh`" |
| Invalid target | `$1` not "opencode" or "codex" | Show usage with valid targets |
| Target pane missing | `tmux list-panes` doesn't include pane N | "Pane N not found. Session may be claude-only. Run setup script for full layout." |
| Context file not found | `test -f` fails | "Context file not found: {path}. Continuing without context." |
| Timeout (WAIT/CAPTURE) | timeout process fires signal | "Delegation timed out after {N}s. Worker may still be running. Check pane manually." |
| Worker command fails | Exit code captured via `$?` in wait-for chain | "Worker command failed. Capture output for debugging." |
| Empty output (CAPTURE) | Captured output is blank or only whitespace | "No output captured. Worker may not have produced visible output." |

### Recovery Guidance

If delegation fails:
1. Check the worker pane manually: `Ctrl+B then o` to switch
2. Run health check: `bash scripts/tmux-health-check.sh`
3. If pane is stuck, kill it: `tmux send-keys -t {session}:main.{N} C-c`
4. Re-setup if needed: `bash scripts/cross-cli-setup.sh`
