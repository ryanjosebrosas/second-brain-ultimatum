# Project Memory

> AI reads at `/prime` and `/planning`. AI updates at `/commit`. Keep concise. Archive old entries to `memory-archive.md`.

---

## Key Decisions
<!-- Format: - [YYYY-MM-DD] Decision — Reason -->
- [2026-02-13] Agent Teams with contract-first spawning — Upstream publishes contracts before downstream starts
- [2026-02-13] Agent Teams for implementation, subagents for research — 2-4x token savings
- [2026-02-13] Session-level routing: c1 (Opus) for planning, c2/c3 (Sonnet) for /team execution. Burn order: c2 → c3 → ck → cz

## Architecture Patterns
<!-- Format: - **Pattern name**: Description. Used in: location -->
- **Modular CLAUDE.md**: `sections/` auto-loaded, `reference/` on-demand. Used in: CLAUDE.md
- **PIV Loop**: Plan → Implement → Validate, one slice per loop. Used in: all development
- **Contract-First Spawning**: Upstream first → lead verifies → relays to downstream. Used in: `/team`
- **Session-Level Routing**: Planning on c1, execution on c2/c3. Used in: `/team`, `/execute`

## Gotchas & Pitfalls
<!-- Format: - **Area**: What goes wrong — How to avoid -->
- **EnterPlanMode**: Never use — Use `/planning` command instead
- **Archon queries**: Keep RAG queries to 2-5 keywords — long queries return poor results
- **Agent `instance` field**: NOT valid frontmatter — silently ignored by Claude Code
- **Task tool `model` param**: Bug #18873 — may default to parent model. Put model guidance in spawn prompts.
- **Multi-instance routing**: ACTIVE via `~/llm-functions.sh` — 5 instances (c1/c2/c3/ck/cz)

## Session Notes
<!-- Format: - [YYYY-MM-DD] Brief summary of what was done -->
- [2026-02-13] Context Budget v3: audited 51k token overhead, created optimization plan targeting ~36k post-prime

---

> **Sizing guide**: Keep under 40 lines. Archive to `memory-archive.md` when needed.
