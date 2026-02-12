# Feature: Command Completion & Enhancement

## Feature Description

Complete the placeholder `code-review-fix.md` command (currently 24 lines), create the missing `/agents` command for generating subagents, enhance `/planning` with an interactive discovery phase, and resolve the open questions in the multi-instance routing reference guide. These are the four command-layer gaps identified during the reference-to-implementation audit.

## User Story

As a developer using the PIV Loop system, I want a fully functional `/code-review-fix` command, an `/agents` command for creating subagents, an interactive `/planning` that acts as a collaborative discovery buddy, and verified multi-instance routing documentation, so that the command layer is 100% complete and the planning experience is genuinely collaborative.

## Problem Statement

Four command-layer issues were identified:
1. `/code-review-fix` is a 24-line placeholder — it lacks the structured approach needed for reliable fix application (no severity prioritization, no pattern matching, no selectivity principle)
2. The subagents reference guides mention an `/agents` command for generating agents, but it doesn't exist
3. `/planning` is purely mechanical — it doesn't act as a collaborative buddy that challenges ideas, asks about inspiration, or helps discover better paths. The PIV Loop's vibe planning phase should be integrated into the command, not separate.
4. The multi-instance routing guide (reference/multi-instance-routing.md) has 5 "Questions to Investigate" (lines 427-435) that are unanswered, including whether agent frontmatter supports an `instance` field

## Solution Statement

- Decision 1: Enhance code-review-fix.md to mirror code-review.md's structured approach — because the fix command consumes code-review output, so it should understand that format
- Decision 2: Create agents.md as a document-creation command that generates agent .md files — because the reference guides describe this capability and it follows the INPUT→PROCESS→OUTPUT pattern
- Decision 3: Investigate multi-instance routing questions via Claude Code docs and update the reference guide with verified answers — because unverified documentation is misleading

## Feature Metadata

- **Feature Type**: Enhancement (completing existing system)
- **Estimated Complexity**: Medium
- **Primary Systems Affected**: .claude/commands/, reference/
- **Dependencies**: None

---

## CONTEXT REFERENCES

### Relevant Codebase Files

- `.claude/commands/code-review-fix.md` (lines 1-25) — Why: Current placeholder to enhance
- `.claude/commands/code-review.md` (lines 1-171) — Why: Output format that code-review-fix consumes (YAML severity format, save location)
- `reference/validation-discipline.md` (lines 1-30) — Why: Describes the selectivity principle (don't blindly fix all AI recommendations)
- `reference/subagents-guide.md` (lines 1-342) — Why: 6-step agent creation process and frontmatter reference that /agents should automate
- `reference/subagents-deep-dive.md` (lines 1-556) — Why: 5-component design framework that /agents should encode
- `templates/AGENT-TEMPLATE.md` — Why: Existing template that /agents should generate filled versions of
- `reference/multi-instance-routing.md` (lines 427-435) — Why: 5 unanswered questions to investigate
- `.claude/agents/_examples/research-codebase.md` — Why: Example of a well-structured agent file to use as reference
- `.claude/commands/init-c.md` — Why: Pattern for a command that generates configuration files (similar to /agents generating agent files)
- `templates/COMMAND-TEMPLATE.md` — Why: INPUT→PROCESS→OUTPUT framework for command design

### New Files to Create

- `.claude/commands/agents.md` — Command to generate subagent definition files

### Related Memories (from memory.md)

No relevant memories found in memory.md

### Relevant Documentation

- [Claude Code Agent Configuration](https://code.claude.com/docs/en/agents)
  - Specific section: Agent frontmatter fields
  - Why: Verify which frontmatter fields are officially supported (including `instance`)

### Patterns to Follow

**Command Frontmatter Pattern** (from `.claude/commands/code-review.md:1-3`):
```yaml
---
description: Technical code review for quality and bugs
---
```
- Why this pattern: Simple frontmatter with just description (and optional argument-hint)
- Common gotchas: Don't add unnecessary frontmatter fields

**Review Output Format** (from `.claude/commands/code-review.md:139-146`):
```yaml
severity: critical|major|minor
category: Type Safety|Security|Architecture|Performance|Logic|Quality
file: path/to/file:line
issue: [one-line description]
detail: [explanation of why this is a problem]
suggestion: [how to fix it]
```
- Why this pattern: This is the format that code-review-fix must parse
- Common gotchas: The fix command must understand severity levels to prioritize correctly

**Agent Design Framework** (from `reference/subagents-deep-dive.md`):
```
1. Role Definition — clear identity
2. Core Mission — singular focus
3. Context Gathering — what files/info needed
4. Analysis Approach — specific steps
5. Output Format — structured results
```
- Why this pattern: The /agents command should guide users through these 5 components
- Common gotchas: Output format is the most critical component — must be explicitly designed

---

## IMPLEMENTATION PLAN

### Phase 1: Enhance code-review-fix.md

Transform the 24-line placeholder into a full command that intelligently processes code review output, prioritizes by severity, applies the selectivity principle, and validates fixes.

**Tasks:**
- Redesign code-review-fix.md with structured fix workflow

### Phase 2: Create /agents Command

Build a command that guides the AI through creating subagent definition files, using the 5-component design framework from the reference guides.

**Tasks:**
- Create agents.md command with INPUT→PROCESS→OUTPUT framework

### Phase 3: Resolve Multi-Instance Routing Questions

Investigate the 5 open questions in multi-instance-routing.md and update the guide with verified answers.

**Tasks:**
- Research Claude Code agent frontmatter capabilities
- Update multi-instance-routing.md with findings

### Phase 4: Update File Structure

Ensure reference/file-structure.md reflects the new /agents command.

**Tasks:**
- Add agents.md to the file structure listing

---

## STEP-BY-STEP TASKS

### UPDATE .claude/commands/code-review-fix.md

- **IMPLEMENT**: Replace the 24-line placeholder with a full implementation (~120-150 lines) covering:
  1. **Frontmatter**: Keep existing description and argument-hint (`[review-path-or-description] [scope]`)
  2. **Input Handling**:
     - If $1 is a file path → read the review file entirely
     - If $1 is a description → treat as inline issue description
     - $2 (scope) → optional filter for specific severity or category
  3. **Severity Prioritization**:
     - Parse the review's severity levels (critical, major, minor)
     - Fix CRITICAL issues first (security, data loss, crashes)
     - Then MAJOR issues (logic errors, performance, missing validation)
     - Then MINOR issues (style, naming, documentation) — ONLY if time permits
  4. **The Selectivity Principle** (from validation-discipline.md):
     - Add explicit instruction: "You may choose NOT to fix issues that are: already documented as acceptable, out of scope for MVP, would require architectural changes beyond the scope of this fix, or are style preferences rather than bugs"
     - For each skipped issue, explain the reasoning
  5. **Per-Issue Fix Process**:
     - Read the affected file in full (not just the flagged line)
     - Understand the surrounding context
     - Explain what's wrong and why
     - Apply the fix
     - Run the task's validation command if available
  6. **Validation After All Fixes**:
     - Run project linting (if configured)
     - Run project type checking (if configured)
     - Run project test suite
     - Report results
  7. **Output Summary**:
     - Issues fixed: count by severity
     - Issues skipped: count with reasons
     - Validation results: pass/fail
  8. **Archon Integration** (optional, conditional):
     - If part of PIV Loop with Archon: update code-review-fix task status
- **PATTERN**: Follow `code-review.md:1-171` structure (mode selection, step-by-step, output format)
- **IMPORTS**: None (markdown command)
- **GOTCHA**: The command must NOT automatically fix everything — the selectivity principle is critical. Include explicit "you may skip" instructions. Without this, the AI will attempt to fix every minor style issue.
- **VALIDATE**: `powershell -Command "(Get-Content '.claude/commands/code-review-fix.md').Count"` — should be 120-150 lines

### CREATE .claude/commands/agents.md

- **IMPLEMENT**: Create a new command (~100-130 lines) for generating subagent definition files:
  1. **Frontmatter**:
     ```yaml
     ---
     description: Create a new subagent definition file
     argument-hint: [agent-purpose-description]
     ---
     ```
  2. **Input**: $ARGUMENTS — description of what the agent should do (e.g., "code review focused on accessibility", "research API documentation for a framework")
  3. **Process** (guided by the 5-component design framework):
     - Step 1: **Determine Agent Type** — research agent, review agent, analysis agent, or custom
     - Step 2: **Choose Model** — suggest Haiku for read-only/pattern-matching tasks, Sonnet for analysis/synthesis, Opus for complex reasoning. Reference multi-model-strategy.md guidance.
     - Step 3: **Define Tools** — suggest minimal tool set needed. Read-only agents: [Read, Glob, Grep]. Analysis agents add [Bash]. Full agents: [*].
     - Step 4: **Design the 5 Components**:
       a. Role Definition — clear identity statement
       b. Core Mission — singular focus (one sentence)
       c. Context Gathering — what files/patterns to search
       d. Analysis Approach — specific steps (numbered)
       e. Output Format — structured results with metadata header, findings, summary
     - Step 5: **Generate the agent file** with proper frontmatter + markdown body
     - Step 6: **Save** to `.claude/agents/{agent-name}.md`
  4. **Output Format Guidance** — include the critical instruction: "In the output format, always include: 'Present findings to the main agent. DO NOT start fixing issues without user approval.'"
  5. **Reference Pattern** — instruct AI to read `.claude/agents/_examples/research-codebase.md` as a reference for structure
  6. **Validation** — after creating the file, verify it has proper frontmatter (name, description, model, tools) and all 5 components in the markdown body
- **PATTERN**: Follow `init-c.md` pattern (command that generates configuration files based on user input)
- **IMPORTS**: None (markdown command)
- **GOTCHA**: The generated agent's output format MUST include the "don't auto-fix" instruction — this prevents the main agent from acting on findings without user approval. This is the #1 mistake in subagent design.
- **VALIDATE**: `powershell -Command "if (Test-Path '.claude/commands/agents.md') { Write-Host 'OK'; (Get-Content '.claude/commands/agents.md').Count } else { Write-Host 'MISSING' }"`

### UPDATE .claude/commands/planning.md — Add Interactive Discovery Phase

- **IMPLEMENT**: Add a new "Phase 0: Interactive Discovery" before the current Phase 1. This phase transforms `/planning` from a mechanical research-and-plan tool into a collaborative discovery buddy. Insert after the frontmatter/header and before Phase 1 (~40-60 new lines):

  **Phase 0: Interactive Discovery (Vibe Planning Buddy)**

  Before researching or planning, engage the user in collaborative discovery:

  1. **Understand the user's level**: Ask what their experience is with this type of feature. Adapt language — technical users get architecture questions, non-technical users get outcome-focused questions.

  2. **Challenge the idea constructively**: Ask probing questions:
     - "What problem does this solve for your users?"
     - "Have you seen this done well somewhere? Share a link or repo and I'll analyze their approach."
     - "What's the simplest version of this that would still be valuable?"
     - "What happens if we DON'T build this?"

  3. **Explore inspiration**: If the user has reference projects/repos:
     - Ask for the GitHub repo URL
     - Analyze their implementation approach (file structure, patterns, tech choices)
     - Identify what to adopt vs what to do differently
     - If no inspiration: suggest 2-3 approaches and explain trade-offs

  4. **Scope negotiation**: Help find the right scope:
     - Push back on scope creep: "That sounds like 3 features — which one delivers the most value?"
     - Suggest vertical slices: "Could we build just the [core thing] first and add [extras] later?"
     - Identify hidden complexity: "This looks simple but [X] usually causes problems — let me check."

  5. **Confirm readiness**: Before proceeding to Phase 1:
     - Summarize the agreed scope (1-3 sentences)
     - List key decisions made during discovery
     - Ask: "Does this capture what we're building? Anything I'm missing?"
     - Only proceed to Phase 1 after user confirms

  **Rules for Phase 0**:
  - This is a CONVERSATION, not a checklist — adapt to the user's responses
  - Be genuinely curious and challenging, not just asking questions to check boxes
  - If the user has a clear vision and wants to skip discovery, respect that: "Sounds like you've thought this through — let me jump into research."
  - Spend 3-10 minutes here depending on clarity. Don't rush, but don't over-discuss.

  Also update Phase 1 to acknowledge Phase 0:
  - Add: "Using context from Phase 0 discovery (if conducted), proceed to scope the feature formally."

- **PATTERN**: Conversational AI interaction pattern (AskUserQuestion for key decisions, open dialogue for exploration)
- **IMPORTS**: None
- **GOTCHA**: Phase 0 must NOT be forced on users who already have a clear feature spec. Include the escape hatch: "If the user provides a detailed feature description or plan reference, skip Phase 0 and proceed to Phase 1." The interactive phase is for discovery, not bureaucracy.
- **VALIDATE**: `powershell -Command "Select-String -Path '.claude/commands/planning.md' -Pattern 'Phase 0|Interactive Discovery|Vibe Planning Buddy' | Measure-Object | Select-Object -ExpandProperty Count"` — should be >= 2

### UPDATE reference/multi-instance-routing.md

- **IMPLEMENT**: Resolve the 5 open questions at lines 427-435:
  1. **"Does agent frontmatter support `instance` field?"** — Research Claude Code docs. The answer is likely NO (as of current Claude Code version). Agent frontmatter supports: name, description, model, tools, disallowedTools, maxTurns, skills, mcpServers, hooks, memory, color, permissionMode. `instance` is NOT a standard field. Update the guide to:
     - Mark Method 3 (Agent Frontmatter) as "NOT YET SUPPORTED"
     - Recommend Method 2 (Command Prefix) or Method 4 (Wrapper Scripts) as working alternatives
  2. **"Can Task tool accept instance parameter?"** — NO. The Task tool accepts: prompt, subagent_type, model, max_turns, run_in_background. No instance parameter. Document this.
  3. **"What's the pricing difference between instances?"** — With MAX subscription, all instances share the same pool. With API billing, each instance uses its own API key. Document both cases.
  4. **"Do all instances have same rate limits?"** — Each MAX subscription has its own rate limits. Multiple accounts = separate rate limit pools. Document this.
  5. **"How to track which instance did what work?"** — Each instance creates separate git commits/branches. Track via git log author or branch naming convention. Suggest naming convention: `{instance}/{feature}`.
  6. Update the "Questions to Investigate" section to "Verified Answers" section
  7. Add a "Supported vs Aspirational" section clarifying which routing methods work TODAY vs which are theoretical
- **PATTERN**: Follow existing reference guide style (informational with tables and code examples)
- **IMPORTS**: None (markdown)
- **GOTCHA**: Be honest about what's NOT supported. Don't leave aspirational features unmarked — users will try them and be confused when they fail.
- **VALIDATE**: `powershell -Command "Select-String -Path 'reference/multi-instance-routing.md' -Pattern 'NOT YET SUPPORTED|Verified Answers' | Measure-Object | Select-Object -ExpandProperty Count"` — should be >= 2

### UPDATE reference/file-structure.md

- **IMPLEMENT**: Add the new agents.md command to the `.claude/commands/` section:
  ```
  agents.md                            #   /agents — generate subagent definition files
  ```
  Place it alphabetically in the commands list.
- **PATTERN**: Follow existing format in `reference/file-structure.md`
- **IMPORTS**: None
- **GOTCHA**: Maintain the existing comment alignment (use spaces/tabs consistently)
- **VALIDATE**: `powershell -Command "Select-String -Path 'reference/file-structure.md' -Pattern 'agents.md' | Measure-Object | Select-Object -ExpandProperty Count"` — should be >= 1

---

## TESTING STRATEGY

### Unit Tests

N/A — markdown commands. No code to unit test.

### Integration Tests

- Verify code-review-fix.md can parse a sample code-review output format
- Verify agents.md generates a valid agent file when tested manually
- Verify multi-instance-routing.md no longer has "Questions to Investigate" as open items

### Edge Cases

- code-review-fix receives an empty review (no issues found) — should handle gracefully
- code-review-fix receives a review with only MINOR issues — should note "all issues are minor, consider skipping"
- /agents receives a vague description — should ask clarifying questions
- Multi-instance routing: user has only 1 account — guide should still be useful (recommend multi-model instead)

---

## VALIDATION COMMANDS

### Level 1: File Existence
```
powershell -Command "@('.claude/commands/code-review-fix.md','.claude/commands/agents.md','reference/multi-instance-routing.md','reference/file-structure.md') | ForEach-Object { if (Test-Path $_) { Write-Host 'OK:' $_ } else { Write-Host 'MISSING:' $_ } }"
```

### Level 2: Line Count Verification
```
powershell -Command "@('.claude/commands/code-review-fix.md','.claude/commands/agents.md') | ForEach-Object { Write-Host $_ ': ' (Get-Content $_).Count ' lines' }"
```

### Level 3: Content Verification
```
powershell -Command "Select-String -Path '.claude/commands/code-review-fix.md' -Pattern 'selectivity|severity|CRITICAL|MAJOR|MINOR' | Measure-Object | Select-Object -ExpandProperty Count"
powershell -Command "Select-String -Path '.claude/commands/agents.md' -Pattern 'Role Definition|Core Mission|Output Format|frontmatter' | Measure-Object | Select-Object -ExpandProperty Count"
powershell -Command "Select-String -Path 'reference/multi-instance-routing.md' -Pattern 'NOT YET SUPPORTED|Verified' | Measure-Object | Select-Object -ExpandProperty Count"
```

### Level 4: Manual Validation

1. Read code-review-fix.md and verify it references the correct review output format
2. Read agents.md and verify it follows the 5-component design framework
3. Read multi-instance-routing.md and verify all 5 questions are answered with evidence
4. Test /code-review-fix manually with a sample review file

---

## ACCEPTANCE CRITERIA

- [x] code-review-fix.md is 120-150 lines with severity prioritization and selectivity principle
- [x] agents.md generates agent files using the 5-component design framework
- [x] planning.md has Phase 0 Interactive Discovery that acts as a collaborative buddy
- [x] Phase 0 adapts to user's technical level and challenges ideas constructively
- [x] Phase 0 has escape hatch for users with clear specs
- [x] multi-instance-routing.md has all 5 questions answered with "Verified Answers" section
- [x] All commands have proper frontmatter (description, argument-hint where needed)
- [x] reference/file-structure.md includes agents.md entry
- [x] No aspirational features are presented as working (honest documentation)

---

## COMPLETION CHECKLIST

- [x] All tasks completed in order
- [x] Each task validation passed
- [x] All validation commands executed successfully
- [ ] Manual testing confirms commands work as expected
- [x] Acceptance criteria all met

---

## NOTES

### Key Design Decisions
- code-review-fix uses selectivity principle rather than "fix everything" — prevents over-correction
- /agents command generates files rather than just printing output — creates reusable artifacts
- Multi-instance routing honestly documents what works vs what's aspirational — prevents user confusion

### Risks
- Risk 1: code-review-fix may need project-specific validation commands → Mitigation: use generic "run project's validation suite" instruction
- Risk 2: Agent frontmatter may add `instance` support in future Claude Code versions → Mitigation: document current state and note "check for updates"
- Risk 3: /agents command may produce agents that need manual refinement → Mitigation: this is expected; reference the "trust but verify" principle

### Confidence Score: 8/10
- **Strengths**: Clear patterns to follow (code-review.md, AGENT-TEMPLATE.md), well-documented requirements from reference guides
- **Uncertainties**: Multi-instance routing investigation may reveal surprises; code-review-fix selectivity balance is subjective
- **Mitigations**: Be honest in documentation; test commands manually before committing
