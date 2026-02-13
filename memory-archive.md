# Memory Archive

> Entries moved from `memory.md` to reduce auto-loaded token cost.
> These are historical — not needed every session, but preserved for reference.

---

## Archived Key Decisions
- [2026-02-12] Migrated from mem0 MCP to file-based memory.md — Simpler, no external dependency, version-controlled
- [2026-02-12] Slimmed CLAUDE.md by moving sections 06-14 to reference/ — Saves ~12,000 tokens per session
- [2026-02-12] Adopted 3-tier skills architecture (SKILL.md → references/) — Progressive disclosure for complex workflows
- [2026-02-12] Plan decomposition for complex features — `<!-- PLAN-SERIES -->` marker triggers series mode in `/execute`
- [2026-02-12] Moved Archon workflow to on-demand reference — Auto-loaded pointer is 5 lines, full guide at `reference/archon-workflow.md`
- [2026-02-13] Activated 8 subagents from _examples/ to .claude/agents/ — Parallel Research Mode and Parallel Review Mode now operational
- [2026-02-13] System Enhancement v2: gap analysis identified 4 areas (subagents, priming, Archon lifecycle, Agent Teams polish) — all fixed

## Archived Architecture Patterns
- **Skills 3-tier**: SKILL.md (overview) → references/ (deep guides) → templates/ (artifacts). Used in: `.claude/skills/`
- **Command chaining**: `/execute → /execution-report → /code-review → /code-review-fix → /commit`. Used in: validation workflow
- **Plan decomposition**: Overview + N sub-plans for High-complexity features. Trigger: Phase 4.5 in `/planning`. Used in: `planning.md`, `execute.md`
- **Auto-Worktree per Teammate**: Implementation teammates get isolated worktrees. Branch: `team/{feature}/{agent}`. Used in: `/team` Step 2

## Archived Lessons Learned
- **Reference-to-System Alignment**: Audit found gaps between reference prose and actionable artifacts — Always create templates alongside reference guides
- **CLAUDE.md restructure**: Auto-loading 14 sections burned tokens on irrelevant context — Keep auto-loaded sections to essential rules only
- **Command compression**: Commands compressed 43-59% with no functionality loss — AI follows concise instructions as well as verbose ones

## Archived Session Notes
- [2026-02-12] Completed Reference-to-System Alignment project (Plans A-D): templates, commands, skills, memory migration
- [2026-02-12] Implemented plan decomposition & execution routing — 2 templates, 2 commands updated, 4 reference docs updated
- [2026-02-12] Token efficiency: compressed 5 commands (43-59%), slimmed auto-loaded context (66%), added README.md with Mermaid diagrams
- [2026-02-13] Implemented Agent Teams integration: /team command, reference guide, skill, spawn templates, contract-first spawning guide
- [2026-02-13] System Enhancement v2: activated subagents, enhanced /prime + /commit + /team Archon integration, documented Agent Teams model workaround
- [2026-02-13] Added multi-instance routing for Agent Teams: Strategy 6 in routing guide, cost optimization in /team command, README section
