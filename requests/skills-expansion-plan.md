# Feature: Skills Architecture Expansion

## Feature Description

Convert 4 heavy commands (>250 lines) into Cloud Skills with 3-tier progressive disclosure architecture. The existing `planning-methodology` skill serves as the proven reference pattern. This reduces session startup token cost by ~80-85% for these commands while maintaining full functionality when invoked.

## User Story

As a developer using the PIV Loop system, I want heavy commands converted to skills with progressive disclosure, so that my context window isn't bloated with 1,400+ lines of command definitions at session start when I only use 1-2 of them per session.

## Problem Statement

Five commands exceed the 250-line threshold recommended for skill conversion (per reference/mcp-skills-overview.md):
- `parallel-e2e.md` — 459 lines
- `merge-worktrees.md` — 383 lines
- `planning.md` — 363 lines (already has companion skill)
- `setup-github-automation.md` — 302 lines
- `new-worktree.md` — 255 lines

Combined: ~1,762 lines loaded upfront every session. As skills, only ~500 tokens of metadata would load upfront, with full content loaded on-demand. Since `planning.md` already has a companion skill, we focus on the remaining 4.

## Solution Statement

- Decision 1: Create skills as COMPANIONS to existing commands (not replacements) — because commands must continue working unchanged for backward compatibility
- Decision 2: Group worktree commands into one skill — because new-worktree and merge-worktrees are always used together as a workflow
- Decision 3: Use planning-methodology skill as the exact structural pattern — because it's proven and already demonstrates proper 3-tier architecture
- Decision 4: Extract methodology/reference content into skills, keep commands as execution instructions — because skills teach "how to think about it" while commands say "what to do"

## Feature Metadata

- **Feature Type**: Enhancement (architecture optimization)
- **Estimated Complexity**: Medium
- **Primary Systems Affected**: .claude/skills/, .claude/commands/ (companion references only)
- **Dependencies**: None (commands remain unchanged)

---

## CONTEXT REFERENCES

### Relevant Codebase Files

- `.claude/skills/planning-methodology/SKILL.md` (lines 1-80) — Why: The PROVEN reference pattern for skill structure
- `.claude/skills/planning-methodology/references/6-phase-process.md` — Why: Example of Tier 3 reference document
- `.claude/skills/planning-methodology/references/template-guide.md` — Why: Example of Tier 3 reference document
- `.claude/commands/parallel-e2e.md` (459 lines) — Why: Largest command, most benefit from skill conversion
- `.claude/commands/merge-worktrees.md` (383 lines) — Why: Complex merge workflow with 9-step validation
- `.claude/commands/new-worktree.md` (255 lines) — Why: Worktree setup with parallel mode
- `.claude/commands/setup-github-automation.md` (302 lines) — Why: GitHub Actions setup workflow
- `reference/mcp-skills-overview.md` (lines relevant to skills architecture) — Why: Defines the 3-tier model and conversion criteria
- `templates/SKILL-TEMPLATE.md` — Why: Template for creating skills
- `reference/mcp-skills-archon.md` — Why: Detailed skill architecture documentation

### New Files to Create

- `.claude/skills/worktree-management/SKILL.md` — Worktree workflow methodology
- `.claude/skills/worktree-management/references/worktree-workflow.md` — Detailed setup+merge workflow
- `.claude/skills/worktree-management/references/conflict-prevention.md` — Conflict prevention strategies
- `.claude/skills/parallel-implementation/SKILL.md` — Parallel E2E methodology
- `.claude/skills/parallel-implementation/references/parallel-workflow.md` — Full parallel pipeline
- `.claude/skills/parallel-implementation/references/troubleshooting.md` — Common issues and fixes
- `.claude/skills/github-automation/SKILL.md` — GitHub Actions setup methodology
- `.claude/skills/github-automation/references/setup-workflow.md` — Step-by-step setup process
- `.claude/skills/github-automation/references/workflow-templates.md` — Template customization guide

### Related Memories (from memory.md)

No relevant memories found in memory.md

### Relevant Documentation

- [Claude Code Skills Documentation](https://code.claude.com/docs/en/skills)
  - Specific section: Creating Skills
  - Why: Official documentation for skill structure and frontmatter

### Patterns to Follow

**Skill SKILL.md Pattern** (from `.claude/skills/planning-methodology/SKILL.md:1-20`):
```yaml
---
name: skill-name
description: >-
  One paragraph describing what this skill does and when it should be used.
  This description is loaded at Tier 1 (~100 tokens) for AI to determine relevance.
---
```
Followed by markdown body with high-level overview and `@references/` pointers.
- Why this pattern: Proven 3-tier structure (Tier 1: metadata, Tier 2: SKILL.md body, Tier 3: references/)
- Common gotchas: Description must be self-contained — AI uses it to decide whether to load the full skill

**Reference Document Pattern** (from `.claude/skills/planning-methodology/references/6-phase-process.md`):
```markdown
# Phase-by-Phase Process

> This reference is loaded on-demand during skill execution (Tier 3).

## Phase 1: ...
```
- Why this pattern: Tier 3 docs are loaded only when the skill is actively being used
- Common gotchas: Don't put critical routing info in Tier 3 — it won't be available for AI decision-making

---

## IMPLEMENTATION PLAN

### Phase 1: Worktree Management Skill

Extract methodology from new-worktree.md (255 lines) and merge-worktrees.md (383 lines) into a unified skill. Keep commands as-is for backward compatibility.

**Tasks:**
- Create SKILL.md with worktree workflow overview
- Create references/worktree-workflow.md with detailed setup+merge process
- Create references/conflict-prevention.md with conflict prevention strategies

### Phase 2: Parallel Implementation Skill

Extract methodology from parallel-e2e.md (459 lines). This is the most complex command and benefits most from progressive disclosure.

**Tasks:**
- Create SKILL.md with parallel pipeline overview
- Create references/parallel-workflow.md with full pipeline details
- Create references/troubleshooting.md with common issues

### Phase 3: GitHub Automation Skill

Extract methodology from setup-github-automation.md (302 lines).

**Tasks:**
- Create SKILL.md with GitHub automation overview
- Create references/setup-workflow.md with step-by-step process
- Create references/workflow-templates.md with template customization

### Phase 4: Update Documentation

Update file structure and cross-references.

**Tasks:**
- Update reference/file-structure.md with new skills
- Verify all skills have proper frontmatter

---

## STEP-BY-STEP TASKS

### CREATE .claude/skills/worktree-management/SKILL.md

- **IMPLEMENT**: Create the skill entry point (~60-80 lines):
  1. **Frontmatter**:
     ```yaml
     ---
     name: worktree-management
     description: >-
       Git worktree workflow for parallel feature implementation. Provides methodology
       for creating isolated working directories, executing features in parallel across
       multiple Claude Code instances, and safely merging with validation gates. Use when
       implementing multiple features simultaneously or when the user mentions worktrees,
       parallel implementation, or multi-branch development.
     ---
     ```
  2. **Body** — High-level overview covering:
     - What git worktrees provide (code isolation for parallel implementation)
     - When to use (2+ features, vertical slice architecture, features touch different code)
     - When NOT to use (single feature, features overlap, quick bug fixes)
     - The workflow: Setup → Execute → Merge
     - Architecture prerequisite: vertical slice (features in independent modules)
     - Key constraints: max 10 worktrees, port allocation (8124 + index), `--no-ff` merges
     - Reference pointers: `@references/worktree-workflow.md` for detailed steps, `@references/conflict-prevention.md` for handling conflicts
     - Related commands: `/new-worktree`, `/merge-worktrees`
- **PATTERN**: Follow `.claude/skills/planning-methodology/SKILL.md` structure exactly
- **IMPORTS**: None
- **GOTCHA**: The description in frontmatter must be self-contained enough for the AI to decide relevance at Tier 1. Include trigger phrases: "worktrees", "parallel implementation", "multi-branch".
- **VALIDATE**: `powershell -Command "if (Test-Path '.claude/skills/worktree-management/SKILL.md') { Write-Host 'OK'; (Get-Content '.claude/skills/worktree-management/SKILL.md').Count } else { Write-Host 'MISSING' }"`

### CREATE .claude/skills/worktree-management/references/worktree-workflow.md

- **IMPLEMENT**: Create detailed workflow reference (~120-150 lines) extracting from new-worktree.md and merge-worktrees.md:
  1. **Setup Phase** (from new-worktree.md):
     - Single vs parallel mode
     - Branch creation and worktree setup
     - Dependency sync per worktree
     - Health verification
     - Port allocation formula
  2. **Execution Phase**:
     - Opening separate terminals per worktree
     - Running `/execute` in each worktree
     - Monitoring progress
  3. **Merge Phase** (from merge-worktrees.md):
     - The 9-step gated merge process
     - Temporary integration branch
     - Sequential merge with tests between each
     - Final validation suite
     - Rollback instructions on failure
     - Worktree cleanup
  4. **Customization** — project-specific commands (dependency install, test runner, health check)
- **PATTERN**: Follow `.claude/skills/planning-methodology/references/6-phase-process.md` style
- **IMPORTS**: None
- **GOTCHA**: Don't duplicate the full command content — extract the METHODOLOGY and reference the commands for exact syntax
- **VALIDATE**: `powershell -Command "if (Test-Path '.claude/skills/worktree-management/references/worktree-workflow.md') { Write-Host 'OK' } else { Write-Host 'MISSING' }"`

### CREATE .claude/skills/worktree-management/references/conflict-prevention.md

- **IMPLEMENT**: Create conflict prevention reference (~80-100 lines) extracting from reference/git-worktrees-overview.md and reference/git-worktrees-parallel.md:
  1. **Scope Boundary Principle** — each agent owns specific directories
  2. **Shared File Strategy** — how to handle registration points (routes, configs)
  3. **Research Agent Deduplication** — partitioning work by scope
  4. **Detecting Overlap Before Parallelizing** — 4-step verification process
  5. **Vertical Slice Architecture** prerequisite — what makes parallelization safe
- **PATTERN**: Follow reference doc style
- **IMPORTS**: None
- **GOTCHA**: Keep focused on PREVENTION, not resolution — conflict resolution is handled by the merge command
- **VALIDATE**: `powershell -Command "if (Test-Path '.claude/skills/worktree-management/references/conflict-prevention.md') { Write-Host 'OK' } else { Write-Host 'MISSING' }"`

### CREATE .claude/skills/parallel-implementation/SKILL.md

- **IMPLEMENT**: Create the skill entry point (~60-80 lines):
  1. **Frontmatter**:
     ```yaml
     ---
     name: parallel-implementation
     description: >-
       Parallel end-to-end feature development pipeline using git worktrees and
       headless Claude Code instances. Chains: prime → plan all features → create
       worktrees → execute in parallel via claude -p → merge → commit → PR.
       Use when developing multiple independent features simultaneously, especially
       with vertical slice architecture. Requires proven /end-to-end-feature,
       /new-worktree, and /merge-worktrees commands.
     ---
     ```
  2. **Body** — High-level overview covering:
     - The parallel pipeline concept (plan sequentially, execute in parallel)
     - Prerequisites (proven individual commands, vertical slices, claude -p support)
     - Pipeline stages overview (8 stages from prime to PR)
     - Safety constraints: max 10 features, features must be independent
     - Reference pointers: `@references/parallel-workflow.md` for full pipeline, `@references/troubleshooting.md` for issues
     - Related: `/parallel-e2e` command, worktree-management skill
- **PATTERN**: Follow `.claude/skills/planning-methodology/SKILL.md` structure
- **IMPORTS**: None
- **GOTCHA**: Clearly state prerequisites — this is the most advanced workflow and requires ALL prior commands to be proven
- **VALIDATE**: `powershell -Command "if (Test-Path '.claude/skills/parallel-implementation/SKILL.md') { Write-Host 'OK'; (Get-Content '.claude/skills/parallel-implementation/SKILL.md').Count } else { Write-Host 'MISSING' }"`

### CREATE .claude/skills/parallel-implementation/references/parallel-workflow.md

- **IMPLEMENT**: Create detailed pipeline reference (~150-180 lines) extracting from parallel-e2e.md:
  1. **Stage 1: Prime** — load codebase context
  2. **Stage 2: Plan All Features** — sequential planning, one plan per feature
  3. **Stage 3: Create Worktrees** — `/new-worktree` for all features
  4. **Stage 4: Execute in Parallel** — `claude -p` in each worktree (headless mode)
  5. **Stage 5: Monitor** — check progress across worktrees
  6. **Stage 6: Merge** — `/merge-worktrees` with validation gates
  7. **Stage 7: Commit** — conventional commit for all merged features
  8. **Stage 8: PR** — create pull request with combined changes
  9. **Failure Recovery** — what to do when stages fail (per-stage instructions)
  10. **Feature Input Format** — pipe-separated feature descriptions
- **PATTERN**: Follow 6-phase-process.md style
- **IMPORTS**: None
- **GOTCHA**: Stage 4 (parallel execution) uses `claude -p` (headless mode) which has different behavior than interactive mode — document the differences
- **VALIDATE**: `powershell -Command "if (Test-Path '.claude/skills/parallel-implementation/references/parallel-workflow.md') { Write-Host 'OK' } else { Write-Host 'MISSING' }"`

### CREATE .claude/skills/parallel-implementation/references/troubleshooting.md

- **IMPLEMENT**: Create troubleshooting reference (~60-80 lines):
  1. Common issues: worktree creation fails, parallel execution hits rate limits, merge conflicts, validation failures
  2. Per-issue: symptom, cause, fix
  3. Rollback procedures for each stage
  4. When to fall back to sequential execution
- **PATTERN**: FAQ/troubleshooting style with clear symptoms and fixes
- **IMPORTS**: None
- **GOTCHA**: Keep practical — actual error messages and exact fix commands, not vague advice
- **VALIDATE**: `powershell -Command "if (Test-Path '.claude/skills/parallel-implementation/references/troubleshooting.md') { Write-Host 'OK' } else { Write-Host 'MISSING' }"`

### CREATE .claude/skills/github-automation/SKILL.md

- **IMPLEMENT**: Create the skill entry point (~60-80 lines):
  1. **Frontmatter**:
     ```yaml
     ---
     name: github-automation
     description: >-
       GitHub Actions setup and configuration for AI-assisted development workflows.
       Covers CodeRabbit automated reviews, Claude Code issue-triggered workflows,
       review-fix loops, and prompt template adaptation. Use when setting up GitHub
       automation for a new project, configuring CodeRabbit, or creating GitHub
       Action workflows for Claude Code.
     ---
     ```
  2. **Body** — High-level overview covering:
     - Two-part system: CodeRabbit (auto-reviews) + Claude Code (auto-fixes)
     - Three approaches: Hybrid, Autonomous, Deterministic
     - Prerequisites: GitHub repo, CodeRabbit installed, Claude Code OAuth token
     - Quick start pointer: `@references/setup-workflow.md`
     - Template customization pointer: `@references/workflow-templates.md`
     - Related: `/setup-github-automation`, `/quick-github-setup` commands
- **PATTERN**: Follow planning-methodology SKILL.md structure
- **IMPORTS**: None
- **GOTCHA**: Distinguish between CodeRabbit (GitHub App, no YAML needed for reviews) and Claude Code (GitHub Action, YAML needed)
- **VALIDATE**: `powershell -Command "if (Test-Path '.claude/skills/github-automation/SKILL.md') { Write-Host 'OK'; (Get-Content '.claude/skills/github-automation/SKILL.md').Count } else { Write-Host 'MISSING' }"`

### CREATE .claude/skills/github-automation/references/setup-workflow.md

- **IMPLEMENT**: Create setup reference (~100-120 lines) extracting from setup-github-automation.md:
  1. **Step 1**: Install CodeRabbit from GitHub Marketplace
  2. **Step 2**: Generate Claude Code OAuth token (`claude setup-token`)
  3. **Step 3**: Add secrets to GitHub (CLAUDE_CODE_OAUTH_TOKEN)
  4. **Step 4**: Enable PR creation permissions (repo + org level)
  5. **Step 5**: Add workflow YAML files (.github/workflows/)
  6. **Step 6**: Add prompt templates (.github/workflows/prompts/)
  7. **Step 7**: Add .coderabbit.yaml configuration
  8. **Step 8**: Test with a sample issue
  9. Label-based routing configuration
  10. Authorized users configuration
- **PATTERN**: Step-by-step guide style
- **IMPORTS**: None
- **GOTCHA**: This overlaps with templates/GITHUB-SETUP-CHECKLIST.md — reference it rather than duplicating
- **VALIDATE**: `powershell -Command "if (Test-Path '.claude/skills/github-automation/references/setup-workflow.md') { Write-Host 'OK' } else { Write-Host 'MISSING' }"`

### CREATE .claude/skills/github-automation/references/workflow-templates.md

- **IMPLEMENT**: Create template customization reference (~80-100 lines):
  1. Prompt template adaptation (local → GitHub): extra INPUT variables, configuration flags, adjusted OUTPUT
  2. Variable substitution: $REPOSITORY, $ISSUE_NUMBER, $BRANCH_NAME, etc.
  3. Label-based routing: how labels determine which template loads
  4. Customizing authorized users
  5. Iteration limit configuration (MAX_ITERATIONS)
  6. CodeRabbit configuration options
- **PATTERN**: Reference doc style with code examples
- **IMPORTS**: None
- **GOTCHA**: Include actual YAML snippets — abstract descriptions of YAML don't help users configure
- **VALIDATE**: `powershell -Command "if (Test-Path '.claude/skills/github-automation/references/workflow-templates.md') { Write-Host 'OK' } else { Write-Host 'MISSING' }"`

### UPDATE reference/file-structure.md

- **IMPLEMENT**: Add all 3 new skills to the `.claude/skills/` section of the file structure:
  ```
  worktree-management/                 #   Git worktree parallel workflow
    SKILL.md                           #   Entry point + frontmatter
    references/                        #   Detailed docs (Tier 3)
      worktree-workflow.md             #     Setup + merge workflow
      conflict-prevention.md           #     Conflict prevention strategies
  parallel-implementation/             #   Parallel end-to-end pipeline
    SKILL.md                           #   Entry point + frontmatter
    references/                        #   Detailed docs (Tier 3)
      parallel-workflow.md             #     Full 8-stage pipeline
      troubleshooting.md              #     Common issues and fixes
  github-automation/                   #   GitHub Actions setup methodology
    SKILL.md                           #   Entry point + frontmatter
    references/                        #   Detailed docs (Tier 3)
      setup-workflow.md                #     Step-by-step setup
      workflow-templates.md            #     Template customization
  ```
- **PATTERN**: Follow existing planning-methodology/ entry format
- **IMPORTS**: None
- **GOTCHA**: Keep the indentation and comment alignment consistent with existing entries
- **VALIDATE**: `powershell -Command "Select-String -Path 'reference/file-structure.md' -Pattern 'worktree-management|parallel-implementation|github-automation' | Measure-Object | Select-Object -ExpandProperty Count"` — should be >= 3

---

## TESTING STRATEGY

### Unit Tests

N/A — these are markdown skill files. No code to unit test.

### Integration Tests

- Verify each skill has proper 3-tier structure (frontmatter → SKILL.md body → references/)
- Verify SKILL.md descriptions are self-contained for Tier 1 relevance detection
- Verify reference files are pointed to by SKILL.md body

### Edge Cases

- Skills loaded when the corresponding command is invoked (should work seamlessly)
- Multiple skills loaded simultaneously (token budget should remain reasonable)
- Skills auto-loaded based on task description (description must contain trigger phrases)

---

## VALIDATION COMMANDS

### Level 1: File Existence
```
powershell -Command "@('.claude/skills/worktree-management/SKILL.md','.claude/skills/worktree-management/references/worktree-workflow.md','.claude/skills/worktree-management/references/conflict-prevention.md','.claude/skills/parallel-implementation/SKILL.md','.claude/skills/parallel-implementation/references/parallel-workflow.md','.claude/skills/parallel-implementation/references/troubleshooting.md','.claude/skills/github-automation/SKILL.md','.claude/skills/github-automation/references/setup-workflow.md','.claude/skills/github-automation/references/workflow-templates.md') | ForEach-Object { if (Test-Path $_) { Write-Host 'OK:' $_ } else { Write-Host 'MISSING:' $_ } }"
```

### Level 2: SKILL.md Frontmatter Verification
```
powershell -Command "Get-ChildItem '.claude/skills/*/SKILL.md' | ForEach-Object { $content = Get-Content $_.FullName -Raw; if ($content -match '^---') { Write-Host 'Frontmatter OK:' $_.FullName } else { Write-Host 'NO FRONTMATTER:' $_.FullName } }"
```

### Level 3: Line Count Verification
```
powershell -Command "Get-ChildItem '.claude/skills/*/SKILL.md' | ForEach-Object { Write-Host $_.FullName ': ' (Get-Content $_.FullName).Count ' lines' }"
powershell -Command "Get-ChildItem '.claude/skills/*/references/*.md' -Recurse | ForEach-Object { Write-Host $_.FullName ': ' (Get-Content $_.FullName).Count ' lines' }"
```

### Level 4: Manual Validation

1. Read each SKILL.md and verify it contains a clear overview + reference pointers
2. Read each reference file and verify it contains extracted methodology (not duplicated command text)
3. Verify all three skills follow the same structure as planning-methodology
4. Verify descriptions contain trigger phrases for auto-loading

### Level 5: Token Budget Check

Estimate total Tier 1 cost: 4 skills × ~100 tokens = ~400 tokens. Total with planning-methodology: ~500 tokens. This is well within budget.

---

## ACCEPTANCE CRITERIA

- [ ] All 3 skill directories created with proper structure (SKILL.md + references/)
- [ ] Each SKILL.md has valid frontmatter with name and description
- [ ] Each SKILL.md body provides high-level overview with reference pointers
- [ ] Reference documents contain extracted methodology, not duplicated command text
- [ ] Existing commands remain unchanged (backward compatibility)
- [ ] reference/file-structure.md updated with all new skills
- [ ] Total Tier 1 token cost for all skills is under 600 tokens

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order
- [ ] Each task validation passed
- [ ] All validation commands executed successfully
- [ ] Skills follow planning-methodology pattern
- [ ] Manual verification confirms proper 3-tier structure
- [ ] Acceptance criteria all met

---

## NOTES

### Key Design Decisions
- Skills are COMPANIONS to commands (not replacements) — backward compatibility is non-negotiable
- Worktree commands grouped into one skill — they're always used together
- Methodology extracted, not duplicated — skills teach the "how to think", commands define the "what to do"
- 3 skills (not 4) — planning.md already has a companion skill

### Risks
- Risk 1: Skills may not auto-load reliably based on task description → Mitigation: include specific trigger phrases in descriptions; users can always invoke manually
- Risk 2: Reference content may drift from command content over time → Mitigation: reference guides document methodology (stable), commands document execution (may evolve)
- Risk 3: Too many skills may slow session startup → Mitigation: 4 total skills × ~100 tokens = ~400 tokens (negligible)

### Confidence Score: 8/10
- **Strengths**: Proven pattern (planning-methodology skill exists), clear extraction strategy, well-defined 3-tier model
- **Uncertainties**: Auto-loading based on description matching is unpredictable; reference content scope may need adjustment
- **Mitigations**: Start with clear trigger phrases; iterate on descriptions based on actual usage
