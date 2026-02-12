---
description: Execute an implementation plan
argument-hint: [path-to-plan]
allowed-tools: Read, Write, Edit, Bash(npm:*), Bash(bun:*), Bash(npx:*), Bash(uv:*), Bash(pip:*), Bash(python:*), Bash(node:*), mcp__archon-local__manage_project, mcp__archon-local__manage_task, mcp__archon-local__find_tasks, mcp__archon-local__find_projects
---

<!-- CUSTOMIZE: Replace the allowed-tools in the frontmatter above for your tech stack:
  Python:  Read, Write, Edit, Bash(uv:*), Bash(pip:*), Bash(python:*), Bash(pytest:*), Bash(mypy:*)
  Node.js: Read, Write, Edit, Bash(npm:*), Bash(npx:*), Bash(node:*), Bash(jest:*), Bash(tsc:*)
  Go:      Read, Write, Edit, Bash(go:*), Bash(make:*)
  Rust:    Read, Write, Edit, Bash(cargo:*)
  Add MCP tools (mcp__archon-local__*) as needed for your integrations.
-->

# Execute: Implement from Plan

## Plan to Execute

Read plan file: `$ARGUMENTS`

## Execution Instructions

### 1. Read and Understand

- Read the ENTIRE plan carefully
- Understand all tasks and their dependencies
- Note the validation commands to run
- Review the testing strategy

#### 1b. Check Memory for Warnings (if memory.md exists)

Before implementing, read `memory.md` at the project root for relevant warnings:
- Look for gotchas related to the feature area
- Check for lessons learned about affected files or systems

If relevant entries found, note them as additional context for implementation. If memory.md doesn't exist, continue without.

### 1.5. Initialize Archon Task Management (if available)

**If Archon MCP is configured:**

1. **Create project**: `manage_project("create", title="{feature-name from plan}", description="{plan Feature Description}")`
2. **Extract all tasks from plan**: Read "STEP-BY-STEP TASKS" section, identify every task (CREATE/UPDATE/ADD/etc.)
3. **Create tasks in Archon**: For each task in plan:
   - `manage_task("create", project_id="{from step 1}", title="{task ACTION + file}", task_order={priority}, description="{IMPLEMENT section}")`
   - Higher task_order = higher priority (assign based on dependency order: earlier tasks = higher numbers)
4. **Store project_id** for status updates during implementation

**If Archon MCP unavailable:**
- Skip task initialization, proceed with implementation

**Outcome**: Human sees all tasks on Kanban board before implementation starts. Real-time visibility into AI progress.

### 2. Execute Tasks in Order

For EACH task in "Step by Step Tasks":

#### a. Navigate to the task
- Identify the file and action required
- Read existing related files if modifying

#### a.5. Update Archon status (if available)

**If Archon project exists (from Step 1.5):**
- Find task ID: `find_tasks(filter_by="project", filter_value="{project_id}", query="{task file path}")`
- Start work: `manage_task("update", task_id="{found_id}", status="doing")`
- CRITICAL: Only ONE task in "doing" at a time — verify no other tasks have "doing" status

**If Archon unavailable:**
- Skip status update

#### b. Implement the task
- Follow the detailed specifications exactly
- Maintain consistency with existing code patterns
- Include proper type hints and documentation
- Add structured logging where appropriate

#### c. Verify as you go
- After each file change, check syntax
- Ensure imports are correct
- Verify types are properly defined

#### d. Mark for review (if Archon available)

**If Archon project exists:**
- `manage_task("update", task_id="{current_task_id}", status="review")`
- This signals to human: "Task implemented, ready for validation"

**If Archon unavailable:**
- Skip

### 3. Implement Testing Strategy

After completing implementation tasks:

- Create all test files specified in the plan
- Implement all test cases mentioned
- Follow the testing approach outlined
- Ensure tests cover edge cases

### 4. Run Validation Commands

Execute ALL validation commands from the plan in order.

If any command fails:
- Fix the issue
- Re-run the command
- Continue only when it passes

### 5. Final Verification

Before completing:

- All tasks from plan completed
- All tests created and passing
- All validation commands pass
- Code follows project conventions
- Documentation added/updated as needed

### 5.5. Mark Tasks Complete (if Archon available)

**If Archon project exists:**

1. **Mark all tasks as done**: For each task created in Step 1.5:
   - `manage_task("update", task_id="{task_id}", status="done")`
2. **Update project status**: `manage_project("update", project_id="{project_id}", description="Implementation complete, ready for commit")`

**If Archon unavailable:**
- Skip

**Outcome**: Kanban board shows feature 100% complete. Human sees green checkmarks across all tasks.

### 6. Update Plan Checkboxes

After all tasks and validations pass, update the plan file itself:

- Check off each item in **ACCEPTANCE CRITERIA** that was met (`- [ ]` → `- [x]`)
- Check off each item in **COMPLETION CHECKLIST** that was met
- If any criterion was NOT met, leave it unchecked and note why in the Output Report

This keeps the plan as a living record of what was actually delivered.

## Output Report

Provide summary:

### Completed Tasks
- List of all tasks completed
- Files created (with paths)
- Files modified (with paths)

### Tests Added
- Test files created
- Test cases implemented
- Test results

### Validation Results
```bash
# Output from each validation command
```

### Ready for Commit
- Confirm all changes are complete
- Confirm all validations pass
- Ready for `/commit` command

## Notes

- If you encounter issues not addressed in the plan, document them
- If you need to deviate from the plan, explain why
- If tests fail, fix implementation until they pass
- Don't skip validation steps
