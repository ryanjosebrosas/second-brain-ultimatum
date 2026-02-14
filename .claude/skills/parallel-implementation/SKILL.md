---
name: parallel-implementation
description: >-
  Parallel end-to-end feature development pipeline using git worktrees and
  headless Claude Code instances. Chains: prime, plan all features, create
  worktrees, execute in parallel via claude -p, merge, commit, PR.
  Use when developing multiple independent features simultaneously, especially
  with vertical slice architecture. Requires proven /end-to-end-feature,
  /new-worktree, and /merge-worktrees commands.
allowed-tools: ["Read", "Glob", "Grep", "Bash", "Write", "Edit", "Task"]
---

# Parallel Implementation — End-to-End Pipeline

This skill provides the methodology for running the full PIV Loop across multiple features simultaneously. It complements the `/parallel-e2e` command — the command provides execution steps, this skill provides the knowledge framework.

## The Parallel Pipeline Concept

**Plan sequentially, execute in parallel.** Features are planned one at a time (for overlap detection), then implemented simultaneously using git worktrees and headless `claude -p` processes. This combines the safety of sequential planning with the speed of parallel execution.

## Prerequisites

This is the most advanced workflow in the system. Only use it when:

1. **`/end-to-end-feature` is proven** — you've run 5+ features with consistent results
2. **`/new-worktree` and `/merge-worktrees` work reliably** — tested on real features
3. **Vertical slice architecture** — features are isolated in independent modules
4. **`claude -p` support** — headless CLI mode available
5. **Comprehensive validation** — tests, type checking, linting all automated

Bugs in any prerequisite command will compound during parallel execution.

## Pipeline Stages (Overview)

The pipeline has 8 stages, progressing from context loading to PR creation:

| Stage | Action | Mode |
|-------|--------|------|
| 1. Prime | Load codebase context | Sequential |
| 2. Plan | Create plans for all features (with overlap detection) | Sequential |
| 3. Commit Plans | Git save point | Sequential |
| 4. Create Worktrees | Set up isolated directories | Parallel |
| 5. Execute | Run `claude -p` in each worktree | Parallel |
| 6. Merge | Validate and integrate all branches | Sequential |
| 7. Commit | Conventional commit for merged features | Sequential |
| 8. PR | Create pull request | Sequential |

**Key insight**: Stages 4 and 5 run in parallel (the speed gain). All other stages are sequential for safety.

## Safety Constraints

- **Max 10 features** per parallel run
- **Features must be independent** — overlapping files (beyond registration points) require sequential implementation
- **Overlap detection** is mandatory — after each plan, compare file targets across all plans
- **Cost awareness** — N parallel `claude -p` processes = N times API costs
- **Platform**: Background process management requires Unix-like systems (macOS/Linux/WSL)

## Feature Input Format

Features are pipe-separated descriptions:

```
/parallel-e2e search functionality | CSV export | email notifications
```

Each description is converted to a kebab-case name, branch, and plan path.

## Failure Recovery

Each stage has specific recovery procedures:
- **Planning overlap**: Remove overlapping feature or implement sequentially
- **Worktree failure**: Retry individual worktree or continue with successful ones
- **Execution failure**: Continue merge with successful features or stop to investigate
- **Merge conflict**: Rollback to clean state, resolve, and retry

## Detailed References (Tier 3 — Load When Running Parallel Pipeline)

For the full 8-stage pipeline with detailed instructions:
@references/parallel-workflow.md

For common issues and fixes:
@references/troubleshooting.md

## Related

- `/parallel-e2e [features]` — The execution command that uses this methodology
- `worktree-management` skill — Worktree setup and merge methodology
- `/end-to-end-feature` — Single-feature version (must be proven first)
- `/new-worktree`, `/merge-worktrees` — Individual worktree commands
