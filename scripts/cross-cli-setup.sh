#!/usr/bin/env bash
# Cross-CLI Orchestration — tmux Session Setup
#
# Creates a tmux session with named panes for AI CLI orchestration:
#   Default:       3 panes (Claude Code + OpenCode + Codex)
#   --claude-only: 1 pane  (Claude Code only)
#
# Usage: bash scripts/cross-cli-setup.sh [session-name] [--claude-only]
#   session-name: optional, defaults to "orchestrate"
#   --claude-only: optional, single-pane layout (no OpenCode/Codex)

set -euo pipefail

# --- Pre-flight validation ---

preflight_check() {
  local errors=0

  # Required: tmux
  if ! command -v tmux &>/dev/null; then
    echo "ERROR: tmux not installed. Run: sudo apt install tmux"
    errors=$((errors + 1))
  fi

  # Optional CLIs: warn but don't fail
  for cli in claude opencode codex; do
    if ! command -v "$cli" &>/dev/null; then
      echo "WARNING: $cli not found in PATH (pane will be empty)"
    fi
  done

  # Check tmux version (need 3.0+ for pane-border-format)
  if command -v tmux &>/dev/null; then
    local ver
    ver=$(tmux -V | grep -oP '\d+\.\d+' | head -1)
    local major
    major=$(echo "$ver" | cut -d. -f1)
    if [ "$major" -lt 3 ]; then
      echo "WARNING: tmux $ver detected. Version 3.0+ recommended for pane titles."
    fi
  fi

  # Check if already inside tmux (nested sessions cause issues)
  if [ -n "${TMUX:-}" ]; then
    echo "WARNING: Already inside tmux session. Nested sessions are not recommended."
    echo "  Current session: $(tmux display-message -p '#S')"
    read -r -p "Continue anyway? [y/N] " response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
      echo "Aborted. Detach from current session first: Ctrl+B then d"
      exit 0
    fi
  fi

  return $errors
}

# --- Parse arguments ---

CLAUDE_ONLY=false
SESSION_NAME=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --claude-only) CLAUDE_ONLY=true; shift ;;
    -*) echo "Unknown flag: $1"; exit 1 ;;
    *) SESSION_NAME="$1"; shift ;;
  esac
done

SESSION_NAME="${SESSION_NAME:-orchestrate}"

# --- Run pre-flight checks ---

preflight_check || exit 1

# --- Attach to existing session if present ---

tmux has-session -t "$SESSION_NAME" 2>/dev/null && {
  echo "Session '$SESSION_NAME' already exists. Attaching..."
  tmux attach -t "$SESSION_NAME"
  exit 0
}

# --- Create session ---

if [ "$CLAUDE_ONLY" = true ]; then
  # Single pane: Claude Code only
  tmux new-session -d -s "$SESSION_NAME" -n main
  tmux select-pane -t "$SESSION_NAME":main.0 -T "claude-code"
else
  # Full 3-pane layout
  tmux new-session -d -s "$SESSION_NAME" -n main
  tmux split-window -h -t "$SESSION_NAME":main
  tmux split-window -v -t "$SESSION_NAME":main.1
  tmux select-pane -t "$SESSION_NAME":main.0

  # Set pane titles
  tmux select-pane -t "$SESSION_NAME":main.0 -T "claude-code"
  tmux select-pane -t "$SESSION_NAME":main.1 -T "opencode"
  tmux select-pane -t "$SESSION_NAME":main.2 -T "codex"
fi

# Enable pane border status to show titles
tmux set-option -t "$SESSION_NAME" pane-border-status top
tmux set-option -t "$SESSION_NAME" pane-border-format " #{pane_title} "

# Set scrollback buffer
tmux set-option -t "$SESSION_NAME" history-limit 50000

# --- Post-setup health verification ---

verify_setup() {
  local session="$1"
  local expected_panes="$2"
  local actual_panes

  actual_panes=$(tmux list-panes -t "$session":main 2>/dev/null | wc -l)
  if [ "$actual_panes" -ne "$expected_panes" ]; then
    echo "ERROR: Expected $expected_panes panes, found $actual_panes"
    return 1
  fi

  echo "Health check: $actual_panes/$expected_panes panes created"

  # Show pane titles
  tmux list-panes -t "$session":main -F "  Pane #{pane_index}: #{pane_title}"

  return 0
}

if [ "$CLAUDE_ONLY" = true ]; then
  verify_setup "$SESSION_NAME" 1
else
  verify_setup "$SESSION_NAME" 3
fi

# --- Print instructions ---

echo ""
echo "Cross-CLI workspace created: $SESSION_NAME"
echo ""

if [ "$CLAUDE_ONLY" = true ]; then
  echo "Layout: Claude Code only (single pane)"
  echo "  +-------------------------------+"
  echo "  |         claude-code           |"
  echo "  +-------------------------------+"
else
  echo "Layout:"
  echo "  +---------------+---------------+"
  echo "  |               |  opencode     |"
  echo "  |  claude-code  +---------------+"
  echo "  |               |  codex        |"
  echo "  +---------------+---------------+"
fi

echo ""
echo "Attach with: tmux attach -t $SESSION_NAME"
echo ""
echo "Quick reference:"
echo "  Ctrl+B then o    -- switch panes"
echo "  Ctrl+B then z    -- zoom pane (fullscreen)"
echo "  Ctrl+B then d    -- detach (keeps running)"
echo ""

# Attach to session
tmux attach -t "$SESSION_NAME"
