# Subagents Guide

> **Load when**: Creating a new subagent, debugging agent handoffs, designing parallel workflows, or integrating agents into slash commands.

---

## Step-by-Step: Creating Your First Agent

### Step 1: Create the File

Create a new markdown file at `.claude/agents/{name}.md` (project-scoped) or `~/.claude/agents/{name}.md` (personal).

The filename determines the agent's identity. Use lowercase with hyphens: `code-reviewer.md`, `system-analyzer.md`, `research-assistant.md`.

### Step 2: Add YAML Frontmatter

```yaml
---
name: code-reviewer
description: Use this agent when you want to review code before committing. Checks type safety, architecture compliance, and logging standards.
model: sonnet
tools: ["Read", "Glob", "Grep"]
---
```

The `description` field is critical — it tells the main agent WHEN to use this agent (for autonomous delegation) and appears in agent listings.

### Step 3: Define Role and Core Mission

```markdown
# Role: Code Reviewer

You are an expert code reviewer specializing in {domain}. Your singular purpose is to evaluate code quality against documented project standards.

You are NOT a fixer — you identify issues and report them. You do NOT make changes.
```

Be specific about what the agent IS and IS NOT. This prevents scope drift.

### Step 4: Define Context Gathering

```markdown
## Context Gathering

Read these files to understand project standards:
- `CLAUDE.md` — project rules and conventions
- `reference/validation-strategy.md` — validation criteria

Then read the files that were changed (provided by main agent or specified in arguments).
```

Specify exact files. "Read the project" is too vague — the agent will waste tokens reading irrelevant files.

### Step 5: Define Analysis Approach

```markdown
## Approach

1. Read project standards from context files
2. Read each changed file completely
3. For each file, check against: type safety, architecture, logging, testing
4. Classify each finding by severity (Critical/Major/Minor)
5. Include file path and line number for every finding
```

Numbered steps prevent the agent from improvising its own process.

### Step 6: Define Output Format

This is the most critical section. See "Output Format Design Patterns" below.

**Important**: Test with a single mission first before parallelizing. Restart your session or use `/agents` to load newly created agents.

---

## Frontmatter Field Reference

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | string | Yes | — | Unique identifier (lowercase-with-hyphens) |
| `description` | string | Yes | — | When to use; guides autonomous delegation decisions |
| `tools` | list | No | Inherits all | Tools the agent can use (e.g., `["Read", "Glob", "Grep"]`) |
| `disallowedTools` | list | No | None | Tools explicitly denied to this agent |
| `model` | string | No | Inherits | `haiku`, `sonnet`, `opus`, or `inherit` |
| `maxTurns` | number | No | — | Maximum agentic turns before stopping |
| `skills` | list | No | None | Skills to preload at agent startup |
| `mcpServers` | list | No | None | MCP servers available to this agent |
| `hooks` | object | No | None | Lifecycle hooks scoped to this agent |
| `memory` | string | No | None | Persistent memory scope: `user`, `project`, or `local` |
| `color` | string | No | — | Background color in terminal UI |
| `permissionMode` | string | No | — | `default`, `acceptEdits`, `delegate`, `dontAsk`, `bypassPermissions`, `plan` |

**Tool restriction best practice**: Reviewers/analyzers should only have read tools (`Read`, `Glob`, `Grep`). Implementers need write tools (`Edit`, `Write`, `Bash`). Always restrict to the minimum needed — omitting the `tools` field inherits ALL tools including MCP, which is rarely what you want.

---

## Output Format Design Patterns

### Metadata Header

```markdown
### Mission Understanding
[Agent echoes back what it understood — useful for debugging prompt issues]

### Context Analyzed
- Plan file: `requests/feature-plan.md` (247 lines)
- Execution report: `requests/execution-reports/feature-report.md` (189 lines)
- Additional: `reference/validation-strategy.md` (42 lines)

### Scope
- Included: all implementation tasks, validation results
- Excluded: testing strategy (separate review)
```

The Mission Understanding section is a debugging tool — when the agent misunderstands, you can see exactly where your prompt needs improvement.

### Findings List

```markdown
### Findings

**[Critical] Type Safety — `app/services/user.py:45`**
- Description: Function `create_user` missing return type annotation
- Evidence: `def create_user(data):` has no `-> User` return type
- Suggested Fix: Add `-> User` return type annotation

**[Major] Architecture — `app/routes/product.py:12`**
- Description: Direct database query in route handler instead of service layer
- Evidence: `db.execute(select(Product))` should be in `service.py`
- Suggested Fix: Move query to `ProductService.list_products()` method

**[Minor] Logging — `app/services/order.py:78`**
- Description: Missing structured context in error log
- Evidence: `logger.error("Failed")` should include order_id
- Suggested Fix: `logger.error("order.create_failed", order_id=order_id, exc_info=True)`
```

Each finding includes: severity, category, file:line, description, evidence (code snippet), suggested fix.

### Summary Block

```markdown
### Summary
- Total findings: 7 (Critical: 1, Major: 3, Minor: 3)
- Files reviewed: 5
- Compliance score: 78%
- Overall assessment: Needs revision — 1 critical type safety issue blocks commit
```

### Recommendations

```markdown
### Recommendations
1. **[P0]** Fix missing return type on `create_user` — blocks type checking (Low effort, High impact)
2. **[P1]** Move database queries to service layer — architecture violation (Medium effort, High impact)
3. **[P2]** Add structured logging context to 3 error handlers (Low effort, Medium impact)
4. **[P3]** Consider adding integration tests for the new endpoint (Medium effort, Medium impact)
```

Prioritized (P0-P3) with effort and impact estimates.

### Main Agent Instructions

```markdown
---
When done, instruct the main agent to present this report to the user and NOT start fixing any issues without explicit user approval. The user should review findings and decide which to address.
```

Without this, the main agent may automatically fix all issues when you just wanted a report.

---

## Parallel Execution Patterns

### Pattern A — Parallel Missions, Same Target

Launch multiple agents each checking a different aspect of the same codebase:

- Agent 1: Check type safety across all changed files
- Agent 2: Check logging standards across all changed files
- Agent 3: Check architecture compliance across all changed files
- Agent 4: Check test coverage across all changed files

Each returns focused findings. Main agent combines results into a unified report.

### Pattern B — Same Mission, Parallel Targets

Launch the same agent type across multiple modules:

- Code reviewer → Module A
- Code reviewer → Module B
- Code reviewer → Module C

Useful for large codebases where reviewing everything sequentially takes too long.

### Pattern C — Research Parallelization

Already used by `/planning` command:

- Explore agent → codebase structure and patterns
- General-purpose agent → external documentation and research
- memory.md reading → past decisions and lessons

Results feed into plan creation. This pattern gives 40-50% speed improvement.

**Limits and warnings**:
- Up to 10 concurrent subagents
- Results consume main context when they return — keep outputs concise
- Background agents cannot use MCP tools (run in foreground for MCP access)
- Each agent has ~20K token startup overhead — use for substantial tasks, not trivial ones

---

## Command + Agent Integration

### Pattern 1 — Command Invokes Agent Explicitly

In your slash command:
```markdown
Use the @code-reviewer agent to review the changed files in this diff.
After the agent completes, present findings to the user.
```

The `@` reference tells the main agent to delegate to that specific subagent.

### Pattern 2 — Command Uses Task Tool with Built-in Agents

Already used in `/planning`:
```markdown
Launch two Task agents simultaneously:
1. Explore agent: search the codebase for relevant patterns
2. General-purpose agent: research external documentation
```

No custom agent file needed — uses built-in agent types.

### Pattern 3 — Agent Saves Artifact, Next Command Consumes It

```markdown
# Step 1: Agent writes report
The code-reviewer agent saves findings to `.agents/code-reviews/review.md`

# Step 2: Another command reads it
/code-review-fix .agents/code-reviews/review.md critical
```

This chains subagent output into command input via a file-based handoff.

### Example: End-to-End Integration

Create a slash command `execute-review-fix.md` that:
1. Invokes the code-reviewer subagent on `$ARGUMENTS` target
2. Waits for agent to write report
3. Reads report and addresses only critical issues
4. Reports back to user with summary

This chains subagent output into main agent action via a single command invocation.

---

## Controlling Post-Agent Behavior

Two complementary strategies:

### Agent-Side Control (in the agent's system prompt)

Add at the end of your agent's system prompt:
```markdown
When you have written the report, instruct the main agent to NOT start fixing any issues without the user's approval.
```

The subagent includes this instruction in its return message to the main agent.

### Command-Side Control (in the calling slash command)

Add in the slash command that invokes the agent:
```markdown
Once the agent is done and has written its report, read that report and then address only the critical issues.
```

The main agent follows the command's instruction, overriding the agent's suggestion.

**Best practice**: Use both. Agent-side control as a safety net, command-side control for specific workflow behavior. Without either, the main agent may automatically act on all findings — fixing code, refactoring, adding tests — when you just wanted a report.

---

## Debugging Agent Handoffs

When subagent output isn't what you expected:

### Mission Echo Technique

Include "Explain your understanding of your mission" as the first section of the output format. Read this section to verify the agent understood correctly. If it misunderstood, your system prompt needs clarification — not more detail, but clearer framing.

### Context Checklist

Did the agent read the right files? Check the "Context Analyzed" section. If files are missing, add explicit file references to the system prompt rather than assuming the agent will find them.

### Output Verification

Is the format parsable? Can the main agent extract what it needs? Run a single mission and read the raw output before parallelizing. Verify the structure matches your template.

### Main Agent Behavior Check

After the subagent returns, does the main agent do what you expected? If it acts autonomously when you wanted it to wait, add control instructions (see "Controlling Post-Agent Behavior" above).

### Iteration Cycle

```
System prompt → Test → Read output → Adjust prompt → Test again
```

Usually 2-3 iterations to get reliable output. Don't try to get it perfect on the first attempt — iterate.

---

## Advanced: Meta-Agents

A meta-agent is an agent whose purpose is to create other agents. This encodes your preferences into the agent creation process itself.

Use the `/agents` command as a starting point, then customize the generated agent to follow YOUR standards:
- Your output format structure
- Your role definition template
- Your tool restriction policies
- Your naming conventions

Particularly valuable when your team creates many agents — ensures consistency without manual review of each agent file.

---

## Key Gotchas

| Gotcha | Impact | Mitigation |
|--------|--------|------------|
| Blank slate — no conversation history | Agent starts fresh, knows nothing about current discussion | Provide detailed brief in system prompt or main agent's delegation message |
| No nesting | Subagents can't spawn subagents | Chain from main conversation instead |
| MCP unavailable in background | Background agents can't use MCP tools | Run in foreground for MCP access |
| Startup overhead (~20K tokens) | Each agent consumes context before actual work | Use for substantial tasks, not trivial ones |
| Session reload required | Manually added agent files aren't loaded until restart | Use `/agents` or restart session |
| Results consume main context | Many agents returning detailed results bloat main conversation | Keep outputs concise, use file-based reports |
| Tool sprawl | Omitting `tools` field inherits ALL tools including MCP | Be explicit about tool restrictions |
