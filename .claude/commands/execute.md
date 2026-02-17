---
description: Execute an implementation plan
argument-hint: [path-to-plan]
allowed-tools: Read, Write, Edit, Bash(npm:*), Bash(bun:*), Bash(npx:*), Bash(uv:*), Bash(pip:*), Bash(python:*), Bash(node:*), mcp__archon__manage_project, mcp__archon__manage_task, mcp__archon__find_tasks, mcp__archon__find_projects, mcp__archon__rag_get_available_sources, mcp__archon__rag_search_knowledge_base, mcp__archon__rag_search_code_examples, mcp__archon__rag_list_pages_for_source
---

# Execute: Implement from Plan

## Plan to Execute

Read plan file: `$ARGUMENTS`

## Execution Instructions

### 0.5. Detect Plan Type

Read the plan file.

**If file contains `<!-- PLAN-SERIES -->`**: Extract sub-plan paths from PLAN INDEX. Report: "Detected plan series with N sub-plans." Proceed to Series Mode (Step 2.5).

**If no marker**: Standard single plan — proceed normally, skip series-specific steps.

### 1. Read and Understand

- Read the ENTIRE plan carefully — all tasks, dependencies, validation commands, testing strategy
- Check `memory.md` for gotchas related to this feature area

### 1.25. Plan Validation (optional)

**If plan-validator agent exists** in `.claude/agents/`: Use the @plan-validator agent to validate the plan structure. Review findings. If Critical issues found, report to user before proceeding. If no critical issues, continue.

**If agent not available**: Skip — proceed to Archon setup.

### 1.5. Archon Setup (if available)

**a. Check availability**: `health_check()` — if fails, skip all Archon steps.

**b. Create project and tasks**: `manage_project("create", ...)`, then `manage_task("create", ...)` for each plan task with dependency-based task_order.

**c. RAG Research**: If the plan references external libraries or APIs, search for relevant docs:
1. `rag_get_available_sources()` — list indexed documentation
2. For each relevant source, `rag_search_knowledge_base(query="...", source_id="...")` with SHORT 2-5 keyword queries
3. `rag_search_code_examples(query="...")` for implementation patterns
4. Use findings to inform implementation — prefer RAG results over assumptions

### 2. Execute Tasks in Order

For EACH task in "Step by Step Tasks":

**a.** Read the task and any existing files being modified.

**b.** **Archon** (if available): `manage_task("update", task_id="...", status="doing")` — only ONE task in "doing" at a time.

**c.** Implement the task following specifications exactly. Maintain consistency with existing patterns.

**d.** Verify: check syntax, imports, types after each change.

**e.** **Archon** (if available): `manage_task("update", task_id="...", status="review")`

### 2.5. Series Mode Execution (if plan series detected)

For each sub-plan in PLAN INDEX order:

1. Read sub-plan file and shared context from overview
2. Execute tasks using Step 2 process (a → e)
3. Run sub-plan's validation commands
4. Read HANDOFF NOTES for state to carry forward
5. Report: "Sub-plan {N}/{total} complete."

**If a sub-plan fails**: Stop, report which sub-plan/task failed. Don't continue — failed state propagates.

### 3. Implement Testing Strategy

Create all test files specified in the plan. Implement test cases. Ensure edge case coverage.

### 4. Run Validation Commands

Execute ALL validation commands from the plan in order. Fix failures before continuing.

### 5. Final Verification

- All tasks completed
- All tests passing
- All validations pass
- Code follows project conventions

**Archon** (if available): `manage_task("update", task_id="...", status="done")` for all tasks. `manage_project("update", ..., description="Implementation complete, ready for commit")`

### 6. Update Plan Checkboxes

Check off met items in ACCEPTANCE CRITERIA (`- [ ]` → `- [x]`) and COMPLETION CHECKLIST. Note unmet criteria in Output Report.

## Output Report

### Completed Tasks
- List all tasks completed, files created, files modified

### Tests Added
- Test files, test cases, results

### Validation Results
```bash
# Output from each validation command
```

### Ready for Commit
- Confirm all changes complete and validations pass
- Ready for `/commit`

## Notes

- Document issues not addressed in the plan
- Explain any deviations from the plan
- Fix failing tests before completing
- Don't skip validation steps
