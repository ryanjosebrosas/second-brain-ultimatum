---
description: Prime agent with codebase understanding
---

# Prime: Load Project Context

## Process

### 1. Analyze Codebase Structure

Scan **source code only** using Glob patterns (NOT `git ls-files`):
- `src/**/*.py` — source code
- `tests/**/*.py` — test files
- `supabase/migrations/*.sql` — database schema
- `pyproject.toml` — project config

Exclude system/tooling directories: `.claude/`, `.opencode/`, `.codex/`, `.github/`, `templates/`, `reference/`, `sections/`, `requests/`, `scripts/`.

For each match, note the file but do NOT read it yet. Build a mental map of the codebase.

### 2. Read Core Files

> CLAUDE.md and sections/ are ALREADY auto-loaded. Do NOT re-read them.

Read ONLY:
- `memory.md` (if exists) — cross-session context
- Main entry points (e.g., `src/**/cli.py`, `src/**/mcp_server.py`)
- Core config files (`pyproject.toml`)
- Key model/schema definitions

Skip: README.md, AGENTS.md, anything in `.claude/`, `templates/`, `reference/`

Limit: Read at most 5 files total. Prioritize by importance.

### 3. Understand Current State

Check recent activity:
!`git log -10 --oneline`

Check current branch and status:
!`git status`

## Output Report

Provide a CONCISE summary (aim for 20-30 lines max):

### Project Overview
- Type, tech stack, current state (3-5 bullets)

### Architecture
- Key source directories and patterns (3-5 bullets)

### Current State
- Branch, recent commits, git status summary

### Memory Context
- Key decisions and gotchas from memory.md (3-5 bullets)
- Memory health: last session date + staleness warning if >7 days

**Keep it SHORT. The user will ask for details if needed.**
