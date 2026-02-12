## Slash Commands (Reusable Prompts)

Slash commands are markdown files that act as reusable, on-demand prompts. They implement the on-demand loading strategy (see `reference/global-rules-optimization.md`).

**Two scopes:**
- **Project commands** (`.claude/commands/`) — shared with your team via version control. Use for team standards and project-specific workflows.
- **Personal commands** (`~/.claude/commands/`) — just you, across all projects. Use for personal workflows and preferences.

### INPUT → PROCESS → OUTPUT Framework

Every command should answer:
1. **INPUT**: What context does the agent need?
2. **PROCESS**: What steps should the agent follow?
3. **OUTPUT**: What format/structure do you want back?

### Three Output Patterns

| Pattern | Produces | Consumer | Example |
|---------|----------|----------|---------|
| Context Loading | Agent understanding | You (human) | `/prime` |
| Document Creation | Saved artifact | Another agent | `/planning` |
| Action Automation | Side effect | System + you | `/commit` |

**Optimize for the consumer:**
- **Human** → scannable, concise, bullet points, quick verification
- **Agent** → explicit file paths, exact commands, no ambiguity, complete context
- **System** → format-compliant, exact syntax

### Core Commands Available

**Project Setup:**
- `/create-prd [product-name]` — Generate PRD from vibe planning conversation

**Development Cycle:**
- `/prime` — Load codebase context at session start
- `/planning [feature]` — Research and create implementation plan
- `/execute [plan-path]` — Implement from a plan document
- `/commit [files]` — Create conventional git commit

**Validation Workflow (optional, recommended):**
- `/code-review` — Technical code review on changed files (run before commit)
- `/code-review-fix [review-path] [scope]` — Fix issues from code review
- `/execution-report` — Generate implementation report (run in same context as execute)
- `/system-review [plan-path] [report-path]` — Divergence analysis for process improvement

**Bug Fix Workflow (requires GitHub CLI):**
- `/rca [issue-id]` — Root cause analysis for GitHub issues
- `/implement-fix [issue-id]` — Implement fix from RCA document

**Autonomous (use only when individual commands are trusted):**
- `/end-to-end-feature [description]` — Chains prime → planning → execute → commit

**Parallel (requires proven worktree commands):**
- `/parallel-e2e [feature A | feature B | ...]` — Parallel end-to-end: prime → plan all → worktrees → execute in parallel via `claude -p` → merge → commit → PR

All core commands integrate with `memory.md` (if it exists) for cross-session memory. `/prime` and `/planning` read, `/commit` updates.

### Skills vs Commands

Commands (`.claude/commands/`) and Skills (`.claude/skills/`) are now unified — both use the same INPUT→PROCESS→OUTPUT framework and identical frontmatter. They coexist for flexible context loading.

| Aspect | Commands | Skills |
|--------|----------|--------|
| **File type** | Single `.md` file | Directory with SKILL.md + supporting files |
| **Token cost** | Description loaded upfront | ~100 tokens metadata + on-demand full content |
| **Discovery** | Explicit `/command-name` | Auto-load via description OR explicit invocation |
| **Best for** | Lightweight workflows, simple tasks | Complex methodologies with reference docs |
| **Examples** | `/commit`, `/code-review-fix` | `/planning` (with templates), `/execute` (with patterns) |

**When to upgrade a command to a skill:**
- Command exceeds 250 lines with multiple reference sections
- Command loads 3+ external files (templates, guides, examples)
- You want AI to auto-load methodology based on task description
- Task-specific guides (e.g., API design, deployment patterns) better fit directory structure

**Backward compatibility**: All existing commands continue working unchanged. Skills are additive — no migration required.

**Example: Planning Methodology Skill**

The `/planning` command (292 lines) has a companion skill at `.claude/skills/planning-methodology/` that demonstrates progressive disclosure:
- **Tier 1** (~100 tokens at session start): Skill metadata — name and description. AI knows planning methodology exists but doesn't load it.
- **Tier 2** (~100 lines when invoked): Full SKILL.md with 6-phase overview, key rules, and reference pointers.
- **Tier 3** (on-demand during execution): `references/6-phase-process.md` and `references/template-guide.md` loaded only when actively planning.

The command and skill coexist — the skill provides methodology knowledge that enriches the command's execution. Users who don't configure skills lose nothing; the command works standalone. This is a concrete example of when a >250-line command benefits from progressive disclosure.

### Why Commands Chain Together

Commands are designed to work independently AND as workflows:

```
/prime → /planning [feature] → /execute [plan] → /commit
```

**Separation of concerns**: Planning requires exploration and thinking. Execution requires focus and precision. Keeping them separate improves both.

**Intelligence reuse**: Plans are artifacts that can be executed multiple times, reviewed before execution, refined, and referenced later.

**Agent-to-agent communication**: `/planning` optimizes its output for `/execute` — explicit file paths, exact validation commands, no ambiguity. The planning agent knows another agent will consume its output.

### Trust Progression

```
Manual Prompts → Reusable Commands → Chained Commands → Parallel Chained
     ↑ trust & verify ↑    ↑ trust & verify ↑    ↑ trust & verify ↑
```

**Before creating commands**: You've manually prompted the same task 3+ times successfully, you know what instructions work, the pattern is stable.

**Before chaining commands**: Each individual command works reliably, you've run the full workflow manually 10+ times, you trust each step's output without checking.

**Before parallel chaining**: Your `/end-to-end-feature`, `/new-worktree`, and `/merge-worktrees` commands are each proven reliable. Features are isolated (vertical slice architecture).

Don't skip stages. Prematurely chaining commands leads to unpredictable results and difficult debugging.

### System Evolution Principle

When a command produces suboptimal output, **update the command itself** — don't just one-off fix it. This compounds learning over time. Every mistake is an opportunity to make the system better.

Example: If `/planning` creates a 1500-line plan when you wanted 500-700, don't just ask it to shorten. Add the line constraint to the planning command so every future plan respects it.

**Two types of improvements:**
- **Plan updates** — fix the command/template for all future runs
- **One-off fixes** — fix the immediate output without changing the system

Always prefer plan updates. One-off fixes solve today; system updates solve forever.

#### Meta-Reasoning Technique

When something goes wrong, don't jump to fixing it. First ask the AI to analyze **why** it happened and **where** in the system the fix belongs:

1. Identify the problem (e.g., "This plan is 1700 lines, way too long")
2. Ask: "Do some meta reasoning. Don't make any changes yet. Help me understand WHY this happened and how I can adjust the system to avoid this in the future. Look at my commands, rules, and templates."
3. The AI examines the system and suggests where to fix
4. You decide which suggestion to implement (you may override the AI's idea)
5. Apply the system fix FIRST, then fix the immediate output

#### Where to Fix: Decision Framework

When encountering issues, think through where the fix belongs:

| Fix Location | When to Use |
|---|---|
| **Global rules** (CLAUDE.md/sections) | Convention that applies to ALL tasks |
| **On-demand context** (reference/) | Task-type-specific guidance |
| **Commands** (planning, execute, etc.) | Process/workflow issue |
| **Templates** (structured plan, PRD) | Output format/structure issue |
| **Vibe planning** (your prompts) | Research was incomplete or scope was wrong |

#### Generic vs. Project-Customized Commands

As you evolve commands through meta-reasoning, they often become project-specific. Recommendation: maintain this template as your **generic baseline** and create project-customized versions in each project's `.claude/commands/`. The more you evolve, the more customized — which is good for that project but may not transfer to others.

### Creating New Commands

Use `templates/COMMAND-TEMPLATE.md` for the full design guide. Key rules:
- Filename becomes command name (`fix-bug.md` → `/fix-bug`)
- Use `$ARGUMENTS` or `$1`, `$2` for dynamic input
- Use `!`backtick for bash execution, `@` for file references
- Add `allowed-tools` in frontmatter to restrict what tools the command can use
- Commands evolve: start simple, refine based on use, compound learning over time

### Subagents: Specialized Workers

Subagents complement commands — commands define WHAT to do, agents define WHO does the work. They're isolated AI instances with custom system prompts that run in their own context window.

**Two integration patterns:**

- **Command references agent**: A slash command instructs the main agent to delegate to a specific subagent, then acts on results (e.g., "use the code-reviewer agent to review the diff, then fix only critical issues")
- **Agent produces artifact for command**: A subagent saves a report file that a subsequent command consumes (e.g., agent writes review → `/code-review-fix` reads it)

Agents live in `.claude/agents/*.md` (project) or `~/.claude/agents/*.md` (personal). Use `templates/AGENT-TEMPLATE.md` for the design guide. See `reference/subagents-overview.md` for the full subagent documentation.

### GitHub Integration (Remote Workflows)

When using commands remotely via GitHub Actions, the same INPUT → PROCESS → OUTPUT framework applies, but with adaptations:

- **Extra INPUT**: GitHub context (repository, issue number, branch name, issue body)
- **Configuration flags**: `$CREATE_BRANCH`, `$CREATE_PR`, `$COMMENT_ON_ISSUE` — control what the agent handles vs what the workflow handles deterministically
- **Extra OUTPUT**: Branch creation, PR creation, issue comments
- **Automated reviews**: CodeRabbit (GitHub App) auto-reviews PRs; Claude Code auto-applies fixes via `claude-fix-coderabbit.yml`

Prompt templates for GitHub live in `.github/workflows/prompts/`. Example workflows live in `reference/github-workflows/`. See `reference/github-integration.md` for the full guide.

**Trust Progression (extended)**:

```
Manual Prompts → Commands → Chained → Parallel Chained → Remote Automation
     ↑ trust & verify ↑  ↑ trust & verify ↑  ↑ trust & verify ↑  ↑ trust & verify ↑
```

Only move to Parallel Chained when your single-feature chain is proven. Only move to Remote Automation when parallel chains are proven reliable.

### For Deeper Context

See `reference/command-design-framework.md` for:
- Command anatomy deep dive (frontmatter, arguments, bash execution, file references)
- Core 4 command patterns explained (how /prime, /planning, /execute, /commit are designed internally)
- Designing output for different consumers (human vs agent optimization)
- Bug fix workflow chain (/rca → /implement-fix)
- Trust progression with detailed transition criteria
- Practical exercises for building your own commands
