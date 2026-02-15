Archon MCP handles task management + RAG search. Load `reference/archon-workflow.md`
for `/execute`, `/planning`, or task work.

**When Archon MCP is available**, use its tools for task management and RAG search.
When unavailable, use local task tracking in plans and `memory.md` for context.
See `reference/archon-workflow.md` for availability checks and fallback patterns.

### MANDATORY: Full Archon Usage During /execute

**This is non-negotiable.** When Archon MCP is available during `/execute`:

1. **Create an Archon project** for the feature: `manage_project("create", ...)`
2. **Create an Archon task for EVERY plan task**: `manage_task("create", ...)` with `task_order` for priority and `feature` for grouping
3. **Cycle every task through statuses**:
   - `manage_task("update", ..., status="doing")` — before starting (only ONE task "doing" at a time)
   - `manage_task("update", ..., status="review")` — after completing implementation
   - `manage_task("update", ..., status="done")` — after validation passes
4. **At commit**: Mark all tasks "done", update project description with commit hash

**Do NOT substitute local TaskCreate/TaskUpdate for Archon tasks.** Local tasks are supplementary — Archon is the source of truth. Never partially use Archon (e.g., create project but skip tasks). Use it fully or not at all.
