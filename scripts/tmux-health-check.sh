#!/usr/bin/env bash
# tmux Workspace Health Check
#
# Verifies that the cross-CLI tmux workspace is correctly set up
# and all panes are responsive.
#
# Usage: bash scripts/tmux-health-check.sh [session-name]
#   session-name: optional, defaults to "orchestrate"
#
# Assumes the session was created by scripts/cross-cli-setup.sh
# with a window named "main".

set -euo pipefail

SESSION_NAME="${1:-orchestrate}"
ERRORS=0
WARNINGS=0

echo "=== tmux Workspace Health Check ==="
echo "Session: $SESSION_NAME"
echo ""

# --- Check 1: Session exists ---

if ! tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
  echo "FAIL: Session '$SESSION_NAME' does not exist"
  echo "  Fix: bash scripts/cross-cli-setup.sh $SESSION_NAME"
  exit 1
fi
echo "PASS: Session exists"

# --- Check 2: Pane count ---

PANE_COUNT=$(tmux list-panes -t "$SESSION_NAME":main 2>/dev/null | wc -l)
if [ "$PANE_COUNT" -eq 3 ]; then
  echo "PASS: 3 panes found (full cross-CLI layout)"
elif [ "$PANE_COUNT" -eq 1 ]; then
  echo "PASS: 1 pane found (claude-only layout)"
else
  echo "WARN: $PANE_COUNT panes found (expected 1 or 3)"
  WARNINGS=$((WARNINGS + 1))
fi

# --- Check 3: Pane titles ---

TITLES=$(tmux list-panes -t "$SESSION_NAME":main -F "#{pane_title}" 2>/dev/null)
for expected in "claude-code" "opencode" "codex"; do
  if echo "$TITLES" | grep -q "$expected"; then
    echo "PASS: Pane '$expected' found"
  elif [ "$PANE_COUNT" -eq 1 ] && [ "$expected" != "claude-code" ]; then
    echo "SKIP: Pane '$expected' (claude-only mode)"
  else
    echo "WARN: Pane '$expected' not found"
    WARNINGS=$((WARNINGS + 1))
  fi
done

# --- Check 4: Scrollback buffer ---

HISTORY_LIMIT=$(tmux show-option -t "$SESSION_NAME" -gv history-limit 2>/dev/null || echo "2000")
if [ "$HISTORY_LIMIT" -ge 50000 ]; then
  echo "PASS: Scrollback buffer: $HISTORY_LIMIT lines"
else
  echo "WARN: Scrollback buffer: $HISTORY_LIMIT lines (recommend 50000)"
  WARNINGS=$((WARNINGS + 1))
fi

# --- Check 5: CLI availability ---

for cli in claude opencode codex; do
  if command -v "$cli" &>/dev/null; then
    echo "PASS: $cli found in PATH"
  else
    echo "WARN: $cli not found in PATH"
    WARNINGS=$((WARNINGS + 1))
  fi
done

# --- Summary ---

echo ""
echo "=== Summary ==="
echo "Errors:   $ERRORS"
echo "Warnings: $WARNINGS"

if [ "$ERRORS" -gt 0 ]; then
  echo "Status: UNHEALTHY"
  exit 1
elif [ "$WARNINGS" -gt 0 ]; then
  echo "Status: DEGRADED (functional with warnings)"
  exit 0
else
  echo "Status: HEALTHY"
  exit 0
fi
