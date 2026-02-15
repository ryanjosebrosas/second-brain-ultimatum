# Recommended tmux Configuration

> **Load when**: Setting up tmux for AI CLI orchestration, configuring cross-CLI workspace, or troubleshooting tmux issues

---

## Quick Start

Copy the full config at the bottom of this guide to `~/.tmux.conf`, then reload:

```bash
tmux source ~/.tmux.conf
```

Or create it in one command:

```bash
# Copy the "Full Config" section below into ~/.tmux.conf
# Then reload: tmux source ~/.tmux.conf
```

---

## Core Settings

Each setting includes a rationale for AI CLI workflows.

```bash
# Prefix key: Ctrl+F (ergonomic, doesn't conflict with shell shortcuts)
# Note: Ctrl+A conflicts with readline beginning-of-line; Ctrl+B is hard to reach
set -g prefix C-f
unbind C-b
bind C-f send-prefix          # Send prefix to nested tmux (rare but useful)

# No ESC delay (critical if using vim/neovim inside tmux)
set -g escape-time 0

# Windows and panes start at 1 (matches keyboard layout)
set -g base-index 1
setw -g pane-base-index 1

# Mouse support for pane selection, scrolling, and resizing
set -g mouse on

# Large scrollback for AI agent output (default 2000 is far too low)
set -g history-limit 50000

# Fill gaps after closing windows
set -g renumber-windows on

# Vi bindings in copy mode (optional, for vim users)
setw -g mode-keys vi

# Proper color support
set -g default-terminal "tmux-256color"

# Pass focus events to programs (needed by some editors)
set -g focus-events on
```

---

## Pane Navigation

```bash
# Vim-style pane navigation
bind h select-pane -L
bind j select-pane -D
bind k select-pane -U
bind l select-pane -R

# Alt+Arrow fallback for non-vim users
bind -n M-Left select-pane -L
bind -n M-Down select-pane -D
bind -n M-Up select-pane -U
bind -n M-Right select-pane -R

# Quick config reload
bind r source-file ~/.tmux.conf \; display "Config reloaded"
```

---

## Status Bar

```bash
# Status bar at top (bottom is default)
set -g status-position top

# Refresh every 5 seconds
set -g status-interval 5

# Show session name on left
set -g status-left "[#S] "

# Show time on right
set -g status-right "%H:%M"
```

Keep it minimal — complex status bars waste screen space in split-pane layouts.

---

## Plugins (Optional)

### TPM Installation

```bash
git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm
```

### Plugin Declarations

```bash
set -g @plugin 'tmux-plugins/tpm'
set -g @plugin 'tmux-plugins/tmux-sensible'    # Sane defaults
set -g @plugin 'tmux-plugins/tmux-resurrect'   # Save/restore sessions
set -g @plugin 'tmux-plugins/tmux-continuum'   # Auto-save sessions
set -g @plugin 'tmux-plugins/tmux-yank'        # System clipboard
```

### Plugin Usage

- **Resurrect**: `prefix + Ctrl-s` to save, `prefix + Ctrl-r` to restore
- **Continuum**: Auto-saves every 15 minutes, auto-restore on tmux start
- **Install plugins**: `prefix + I` (capital I) after first launch

### Initialize TPM (must be last line in .tmux.conf)

```bash
run '~/.tmux/plugins/tpm/tpm'
```

---

## Alternative Tools

- **[NTM (Named Tmux Manager)](https://github.com/Dicklesworthstone/ntm)** — Purpose-built
  for AI CLI orchestration. Animated TUI with token velocity badges, broadcast prompts
  to agent subsets, F6 palette keybinding. Consider if you need a visual dashboard.

- **[CLI Agent Orchestrator (AWS)](https://github.com/awslabs/cli-agent-orchestrator)** —
  Hierarchical supervisor-worker model with MCP-based Handoff/Assign/Send Message tools.
  Consider if you need formal supervisor patterns.

- This system uses custom tmux scripts (simpler, no dependencies). These tools
  are alternatives if you outgrow the custom approach.

---

## Full Config

Complete `.tmux.conf` ready to copy-paste:

```bash
# === Prefix ===
set -g prefix C-f
unbind C-b
bind C-f send-prefix

# === Core ===
set -g escape-time 0
set -g base-index 1
setw -g pane-base-index 1
set -g mouse on
set -g history-limit 50000
set -g renumber-windows on
setw -g mode-keys vi
set -g default-terminal "tmux-256color"
set -g focus-events on

# === Pane Navigation ===
bind h select-pane -L
bind j select-pane -D
bind k select-pane -U
bind l select-pane -R
bind -n M-Left select-pane -L
bind -n M-Down select-pane -D
bind -n M-Up select-pane -U
bind -n M-Right select-pane -R
bind r source-file ~/.tmux.conf \; display "Config reloaded"

# === Status Bar ===
set -g status-position top
set -g status-interval 5
set -g status-left "[#S] "
set -g status-right "%H:%M"

# === Plugins (optional — requires TPM) ===
# git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm
# set -g @plugin 'tmux-plugins/tpm'
# set -g @plugin 'tmux-plugins/tmux-sensible'
# set -g @plugin 'tmux-plugins/tmux-resurrect'
# set -g @plugin 'tmux-plugins/tmux-continuum'
# set -g @plugin 'tmux-plugins/tmux-yank'
# run '~/.tmux/plugins/tpm/tpm'
```
