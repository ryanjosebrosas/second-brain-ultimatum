---
name: worktree-management
description: >-
  Git worktree workflow for parallel feature implementation. Provides methodology
  for creating isolated working directories, executing features in parallel across
  multiple Claude Code instances, and safely merging with validation gates. Use when
  implementing multiple features simultaneously or when the user mentions worktrees,
  parallel implementation, or multi-branch development.
allowed-tools: ["Read", "Glob", "Grep", "Bash", "Write", "Edit", "Task"]
---

# Worktree Management — Parallel Feature Implementation

This skill provides the methodology for parallel feature development using git worktrees. It complements the `/new-worktree` and `/merge-worktrees` commands — the commands provide execution steps, this skill provides the knowledge framework.

## What Git Worktrees Provide

Git worktrees create **isolated working directories** for different branches within the same repository. Each worktree has its own file system where a separate Claude Code instance can work independently. Changes in one worktree cannot affect another — conflicts only surface during the controlled merge phase.

This is **code isolation**, not just context isolation. Unlike subagents (which share the same file system), worktrees give each agent a completely separate copy of the source code.

## When to Use Worktrees

**Use when:**
- Implementing 2+ features simultaneously
- Features follow vertical slice architecture (isolated in independent modules)
- Each feature takes 30+ minutes to implement
- Features touch different parts of the codebase

**Don't use when:**
- Single feature (no parallelization benefit)
- Features share significant code paths (high merge conflict risk)
- Quick bug fixes (same branch is fine)
- Testing/debugging existing code

## The Workflow: Setup, Execute, Merge

### 1. Setup — Create Worktrees

Use `/new-worktree branch1 branch2 ... branchN` (1-10 branches).

Each worktree gets:
- Its own directory in `worktrees/`
- Synced dependencies (independent `node_modules/`, `venv/`, etc.)
- A dedicated port: `8124 + index` (0-based)
- Health check verification

### 2. Execute — Run in Parallel

Open separate terminals per worktree, launch Claude Code in each, and run `/execute` with the feature plan. Both agents work simultaneously with zero interference.

### 3. Merge — Validate and Integrate

Use `/merge-worktrees branch1 branch2 ... branchN` from the main repository root.

The 9-step gated process:
1. Verify preconditions (branches exist, correct directory)
2. Create temporary integration branch
3. Merge each branch with `--no-ff`
4. Test after each merge (fail fast)
5. Run full validation suite after all merges
6. Merge to original branch only if ALL validation passes
7. Cleanup integration branch
8. Ask about worktree cleanup

**Safety**: If any step fails, rollback instructions are provided and the main branch stays clean.

## Architecture Prerequisite: Vertical Slices

Parallel implementation requires **vertical slice architecture** — features isolated in independent modules. Agent 1 works on `features/search/`, Agent 2 works on `features/export/`. Minimal overlap means minimal merge conflicts.

Without vertical slices, merge conflicts become frequent and hard to resolve. If your architecture isn't sliced, implement features sequentially.

## Key Constraints

- **Max 10 worktrees** (subagent limit for parallel setup)
- **Port allocation**: `8124 + index` (ports 8124-8133)
- **Always use `--no-ff` merges** to preserve feature branch history
- **Never manually delete worktree directories** — use `git worktree remove`
- **Add `worktrees/` to `.gitignore`**

## Detailed References (Tier 3 — Load When Actively Using Worktrees)

For detailed setup and merge workflow:
@references/worktree-workflow.md

For conflict prevention strategies:
@references/conflict-prevention.md

## Related Commands

- `/new-worktree [branches]` — Create worktrees with dependency sync and health check
- `/merge-worktrees [branches]` — Safely merge feature branches with validation gates
- `/parallel-e2e [features]` — Full parallel PIV Loop (chains setup, execute, merge, commit, PR)
- `/execute [plan]` — Used inside each worktree to implement a feature
