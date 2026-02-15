---
name: cross-cli-orchestration
description: "Cross-CLI task orchestration via tmux. Delegate tasks from Claude Code to OpenCode and Codex running in adjacent tmux panes. Use when leveraging multiple AI CLI tools for task routing, cost optimization, or capability-based delegation."
allowed-tools: ["Read", "Glob", "Grep", "Bash", "AskUserQuestion"]
---

# Cross-CLI Orchestration — Multi-Tool Task Delegation

Orchestrate work across Claude Code, OpenCode, and Codex using tmux as the communication layer. Claude Code acts as the planning/reasoning orchestrator while OpenCode and Codex handle execution and review tasks.

## When This Skill Applies

- User wants to delegate a task to OpenCode or Codex
- User wants to delegate a task and capture the output
- User asks about setting up a multi-CLI workspace
- User wants to route tasks across different AI providers
- User invokes `/delegate` command
- User asks about cross-CLI orchestration patterns

## Quick Reference

| Action | Command |
|--------|---------|
| Setup workspace | `bash scripts/cross-cli-setup.sh [name]` |
| Delegate (fire) | `/delegate opencode "task" --fire` |
| Delegate (wait) | `/delegate opencode "task" --wait` |
| Delegate (capture) | `/delegate codex "review" --capture` |
| Delegate with context | `/delegate opencode "task" --capture --context requests/plan.md` |
| Check worker output | `tmux capture-pane -t {session}:main.{N} -p -S -100` |
| Switch panes | `Ctrl+B` then `o` |
| Health check workspace | `bash scripts/tmux-health-check.sh [name]` |
| Recommended tmux config | See `reference/tmux-recommended-config.md` |

## Task Routing

| Task | Route To | Why |
|------|----------|-----|
| Planning, architecture | Claude Code | Deep reasoning (Opus 4.6) |
| Implementation, bulk work | OpenCode | Flexible models, token-heavy |
| Code review, quick fixes | Codex | Included with ChatGPT |
| Debugging, RCA | Claude Code | Reasoning quality matters |

## Setup & Configuration

1. **First time**: Install tmux, copy recommended config from `reference/tmux-recommended-config.md`
2. **Create workspace**: `bash scripts/cross-cli-setup.sh [session-name]`
3. **Verify setup**: `bash scripts/tmux-health-check.sh [session-name]`
4. **Claude-only mode**: `bash scripts/cross-cli-setup.sh [name] --claude-only` (when OpenCode/Codex not needed)

## Detailed References (Tier 3 — Load When Actively Orchestrating)

For tmux command patterns (send-keys, capture-pane, wait-for, synchronization):
@references/tmux-patterns.md

For CLI capabilities (OpenCode flags, Codex flags, non-interactive modes, JSON output):
@references/cli-capabilities.md
