---
description: Prime agent with codebase understanding
---

# Prime: Load Project Context

## Process

### 1. Analyze Project Structure

Scan the project using Glob patterns, NOT `git ls-files`:
- `**/*.{py,ts,js,tsx,jsx,go,rs}` — source code entry points
- `**/package.json`, `**/pyproject.toml`, `**/Cargo.toml` — config files
- `**/README.md` — documentation

For each match, note the file but do NOT read it yet. Build a mental map of the project.

### 2. Read Core Documentation

> CLAUDE.md and sections/ are ALREADY auto-loaded. Do NOT re-read them.

Read ONLY files that are NOT auto-loaded:
- `memory.md` (if exists) — cross-session context
- Main entry points identified in Step 1 (main.py, index.ts, etc.)
- Core config files (package.json, pyproject.toml, etc.)

Skip: README.md (use git log + file structure to understand the project instead)
Skip: AGENTS.md (loaded by Claude Code separately)

### 3. Identify Key Files

Based on the structure, identify (but only read if NOT auto-loaded):
- Main entry points
- Core configuration files
- Key model/schema definitions

Limit: Read at most 5 files total. Prioritize by importance.

### 4. Understand Current State

Check recent activity:
!`git log -10 --oneline`

Check current branch and status:
!`git status`

### 5. Surface Active Tasks (if Archon available)

Query for in-progress tasks ONLY:
1. `find_tasks(filter_by="status", filter_value="doing")`
2. Display as compact list: `[project] task title (status)`

Skip: todo tasks (user knows their backlog)
Skip: Archon RAG source listing (not needed for priming)
Skip: Archon RAG search queries (save for /planning)

## Output Report

Provide a CONCISE summary (aim for 20-30 lines max):

### Project Overview
- Type, tech stack, current state (3-5 bullets)

### Architecture
- Key directories and patterns (3-5 bullets)

### Current State
- Branch, recent commits, git status summary

### Memory Context
- Key decisions and gotchas from memory.md (3-5 bullets)
- Memory health: last session date + staleness warning if >7 days

### Active Tasks
- Archon doing tasks (or "No active tasks")

**Keep it SHORT. The user will ask for details if needed.**
