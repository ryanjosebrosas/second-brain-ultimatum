# Parallel Implementation with Git Worktrees

This guide explains **how to parallelize feature implementation using Git worktrees** — covering the parallelization journey from subagents to worktrees, vertical slice architecture requirements, the complete worktree workflow, out-of-the-box remote coding solutions, the "build one, mirror many" pattern, and industry direction — going deeper than the guide at `reference/git-worktrees-overview.md`.

---

## 1. The Journey to Parallel Implementation

### The Parallelization Journey

The System Foundations guide established the **why** — the system gap and foundational mental models. The PIV Loop Practice guide taught the **how** — the PIV Loop in practice. The Global Rules Optimization guide taught **how to build** — modular CLAUDE.md and strategic context loading. The Command Design Framework guide taught **how to automate** — slash commands and the INPUT->PROCESS->OUTPUT framework. The Planning Methodology guide taught **how to plan** — the 6-phase planning methodology. The Implementation Discipline guide taught **execution discipline** — implementing from plans reliably and evolving the system through meta-reasoning. The Validation Discipline guide taught **validation discipline** — the 5-level pyramid, code review, system review, and divergence analysis. The GitHub Orchestration guide taught **remote orchestration** — GitHub Actions as the orchestration layer. The Remote Agentic System guide taught **remote system architecture** — a custom application running the PIV Loop remotely with real-time conversation. The MCP Skills & Archon guide taught **external integration** — MCP servers for tool access and Cloud Skills for progressive knowledge loading. The Subagents Deep Dive guide taught **research parallelization** — subagents for parallel exploration with context isolation. This guide teaches **implementation parallelization** — git worktrees for parallel feature development with full code isolation.

This is the culmination of the parallelization journey. The Subagents Deep Dive guide taught you to think in parallel; this guide teaches you to build in parallel. Together, they represent the complete shift from sequential AI-assisted development to parallel AI-assisted development.

### What You'll Learn

- **Git worktrees** — what they are, how they provide code isolation, and why they differ from branches
- **Vertical slice architecture** — the architectural prerequisite that makes parallel implementation safe
- **Parallelization patterns compared** — subagents vs terminals vs worktrees vs containers, and when to use each
- **The worktree workflow** — setup, parallel execution, and safe merging with validation gates
- **The live demonstration** — real stats from parallel implementation of two features simultaneously
- **"Build one, mirror many"** — the scaling pattern that enables 10+ parallel agents
- **Out-of-the-box remote solutions** — Google Jules, OpenAI Codex, Claude Code Web, Cursor 2, and their limitations
- **Industry direction** — the shift toward agent-first development and workflow engineering
- **Best practices** — dependency management, port allocation, cleanup, and customization
- **Trust progression** — when you're ready to parallelize and how to avoid amplifying bad patterns

### The Core Insight

Once you've built one feature with well-documented patterns, you can point every subsequent implementation at that reference. Scale to 10+ parallel features — each mirrors the established patterns and reaches 90-100% completion on the first pass, provided you've planned and scoped each implementation thoroughly.

The power of parallel implementation isn't just about running multiple agents. It's about establishing patterns so strong that additional agents can mirror them independently. Build one feature well, document everything, and every subsequent feature follows the blueprint.

### The Parallelization Arc

This guide completes a two-guide arc that started with the Subagents Deep Dive guide:

| Subagents Deep Dive (Subagents) | This Guide (Git Worktrees) |
|----------------------|---------------------------|
| Parallelizes **research and analysis** | Parallelizes **implementation and code writing** |
| Context isolation (separate AI instances) | Code isolation (separate file systems) |
| 2-5x speed gain for research | 2-10x speed gain for implementation |
| Low complexity (prompt-based) | Medium complexity (git setup required) |
| Risk: context handoff information loss | Risk: merge conflicts, integration issues |

These are complementary: use subagents during planning to research 5 aspects simultaneously, then use worktrees during implementation to build 2-3 features simultaneously.

---

## 2. What Git Worktrees Are

### The Mental Model

Traditional git gives you one working directory per repository. You switch branches with `git checkout`, but only one branch is "active" at a time — changing branches replaces your files. Git worktrees solve this by creating **additional working directories**, each locked to a different branch, sharing the same `.git` history.

```
main-repo/                          # Your normal repository
├── .git/                           # Shared Git history
├── src/
├── README.md
└── worktrees/                      # Convention: worktrees live here
    ├── feature-search/             # Branch: feature/search
    │   ├── .git (file, not dir)    # Pointer back to main .git
    │   ├── src/                    # Independent copy of source
    │   └── README.md
    └── feature-export/             # Branch: feature/export
        ├── .git (file, not dir)
        ├── src/
        └── README.md
```

Each worktree is a complete working directory. Claude Code running in `worktrees/feature-search/` sees entirely different files than Claude Code running in `worktrees/feature-export/`. Commits from both show up in the same repository history.

### Why This Works for Parallel AI Development

1. **Full file system isolation** — changes in one worktree cannot affect another; agents can't step on each other's code
2. **Shared Git history** — all commits from all worktrees track in one place; branches merge normally
3. **No development-time conflicts** — conflicts only surface during the controlled merge phase, not while agents are working
4. **Clean merge process** — features integrate only after individual completion and validation, never mid-implementation

Git worktrees are built into Git — not a third-party tool. They provide the same isolation as cloning the repo multiple times, without duplicating the entire `.git` history.

### The `.gitignore` Requirement

Add `worktrees/` to your project's `.gitignore` so worktree directories are never accidentally committed from the root repository. This is a practical detail explicitly called out — worktree directories are local development artifacts, not project source code.

---

## 3. Vertical Slice Architecture

### The Architectural Prerequisite

Parallel implementation only works safely when features are **isolated into independent modules** that rarely touch the same files. This is vertical slice architecture — each feature is self-contained in its own directory with its own models, services, routes, and tests.

```
project/
├── app/
│   ├── core/           # Shared infrastructure (rarely modified)
│   ├── features/       # Vertical slices
│   │   ├── tool_a/     # Agent 1 works here
│   │   │   ├── tool.py
│   │   │   ├── service.py
│   │   │   ├── models.py
│   │   │   └── operations/
│   │   ├── tool_b/     # Agent 2 works here
│   │   │   └── ...
│   │   └── tool_c/     # Agent 3 works here
│   │       └── ...
│   └── shared/         # Shared utilities (rarely modified)
```

### Why It Enables Parallelization

- **Each feature is self-contained** — agent 1 modifies `features/tool_a/`, agent 2 modifies `features/tool_b/`; they never touch each other's files
- **Merge conflicts are minimal** — typically limited to a registration point (e.g., adding a new tool to `main.py` or a route to `routes/index.ts`)
- **Patterns established in one feature guide all others** — the first feature becomes the reference implementation

### Without Vertical Slices

Parallel implementation becomes risky. If agents modify the same utility files, shared services, or configuration files, merge conflicts are frequent and hard to resolve. The merge step — which should be mechanical — becomes a manual conflict-resolution exercise. If your architecture isn't vertically sliced, sequential development is safer.

### Designing for Parallelization

Plan for parallelization from the start of a project. When writing your PRD and architecture decisions, consider:
- Can features be implemented independently?
- What shared files would multiple features touch?
- Can registration points (routers, registries) be designed for minimal conflict?

This is exactly why vertical slice architecture matters for parallel work. Splitting the codebase into self-contained feature slices means multiple agents can work on different parts simultaneously without stepping on each other.

---

## 4. Parallelization Patterns Compared

### The Four Approaches

| Approach | Setup | Isolation | Speed Gain | Best For |
|----------|-------|-----------|------------|----------|
| **Subagents** (see Subagents Deep Dive guide) | Low | Context only | 2-5x | Research, analysis, code review |
| **Multiple terminals** | Low | None | 2x | Quick parallel tasks, same branch |
| **Git worktrees** (this guide) | Medium | Full (code) | 2-10x | Feature implementation |
| **Containers/Cloud** | High | Complete | Unlimited | Large-scale parallel, CI/CD |

### The Escalation Ladder

```
Single agent → Subagents (research) → Worktrees (implementation) → Cloud agents (unlimited scale)
```

Start with subagents for planning and research. Graduate to worktrees for implementation. Move to cloud containers or remote systems (see Remote Agentic System guide) for massive scale — 10+ features simultaneously.

### Choosing the Right Level

- **Subagents**: When you need to explore multiple aspects of a problem simultaneously — API docs, codebase patterns, library comparisons. Low overhead, no git setup required.
- **Multiple terminals**: When you need two agents on the same branch doing non-overlapping work. No isolation guarantees — use only for trivial parallel tasks.
- **Git worktrees**: When you have multiple feature plans ready to execute and features are isolated. The sweet spot for local parallel implementation.
- **Containers/Cloud**: When local resources are insufficient (5+ parallel agents), or you need persistent remote execution with team access. See the Remote Agentic System guide for the remote system.

---

## 5. The Worktree Workflow

The workflow has three phases: Setup, Execute, Merge. Each phase has specific commands and safety mechanisms.

### Phase 1: Setup (`/new-worktree`)

**Two modes based on arguments:**

| Mode | Arguments | Behavior |
|------|-----------|----------|
| Single | `/new-worktree feature/search` | Sequential setup for one worktree |
| Parallel (2) | `/new-worktree feature/search feature/export` | Spawns 2 agents via Task tool |
| Parallel (N) | `/new-worktree branch1 branch2 ... branchN` | Spawns N agents (max 10) via Task tool |

**What happens per worktree:**
1. `git worktree add worktrees/<branch-name> -b <branch>` — creates the isolated directory
2. Navigate into the worktree directory
3. Sync dependencies independently (e.g., `uv sync`, `npm install`)
4. Run health check on a dedicated port (Worktree 1: 8124, Worktree 2: 8125)
5. Report ready status

**Why parallel setup matters**: When both worktrees need dependency installation (which can take minutes), parallel mode cuts setup time by ~50%.

**Why health checks**: Verifies the worktree has a working environment before you invest time executing a plan in it. Catches missing dependencies or configuration issues early.

### Phase 2: Execute in Parallel

Open separate terminals for each worktree. Each gets its own Claude Code instance with its own context window:

```
Terminal 1:                              Terminal 2:
cd worktrees/feature-search              cd worktrees/feature-export
claude                                   claude
/execute plans/search-plan.md            /execute plans/export-plan.md
```

Both agents work simultaneously — reading from their own plan, implementing in their own directory, committing to their own branch. There is zero risk of interference because they're operating on completely separate file systems.

**Key detail**: Each worktree has its own CLAUDE.md, its own `.claude/commands/`, and its own context. The agent in `worktrees/feature-search/` doesn't know the agent in `worktrees/feature-export/` exists. This is by design — full isolation means full independence.

**Plan placement**: Plans should be placed inside the worktree directory before launching Claude Code. In the demo, plans went to `.agents/plans/` inside each worktree. Locally, you might use `requests/` per your project convention. The key is the plan must be accessible from inside the worktree.

### Phase 3: Merge (`/merge-worktrees`)

The merge command implements a **9-step gated process** with safety at every level:

1. **Verify preconditions** — confirm we're in the repo root, both branches exist
2. **Create integration branch** — temporary `integration-<branch1>-<branch2>` branch; main stays clean
3. **Merge first feature** — `git merge --no-ff` preserves branch history
4. **Test first merge** — run validation suite; if tests fail, stop with rollback instructions
5. **Merge second feature** — only if first merge passed validation
6. **Full validation suite** — tests + type checking + linting; everything must pass
7. **Merge to original branch** — only after ALL validation passes
8. **Cleanup integration branch** — delete the temporary branch
9. **Ask about worktree cleanup** — user decides whether to remove worktree directories

**Why the integration branch matters**: Your main branch is never in a dirty state. If step 4 or 6 fails, you delete the integration branch and your main branch is untouched. This is the key safety mechanism — it separates "testing the merge" from "committing the merge."

**Why `--no-ff`**: No fast-forward merges preserve the branch structure in history. Each feature's commits stay grouped under a merge commit, making it easy to identify which commits belong to which feature and to revert an entire feature if needed.

**Rollback on failure**: If any step fails, the merge command provides explicit rollback instructions:

```bash
git checkout <original-branch>
git branch -D integration-<branch1>-<branch2>
```

The temporary integration branch is deleted, leaving your main branch exactly as it was before the merge attempt. You can fix the issue (resolve conflicts, fix tests) and re-run the merge command.

---

## 6. The Live Demonstration

### Obsidian Agent: Parallel Tool Implementation

The demonstration used an Obsidian note-taking agent project to show parallel implementation in action.

**Starting point**: Codebase rolled back to a single-tool state (`obsidian_query_vault` — one tool implemented and working).

**Goal**: Implement `obsidian_manage_note` and `obsidian_manage_folder` tools in parallel.

### Step-by-Step

1. **Create worktrees**: `/new-worktree manage-notes manage-folders` — two worktrees created in parallel via subagents. Both passed dependency sync and health checks.

2. **Place plans**: Pre-created structured plans copied into each worktree:
   - `worktrees/manage-notes/.agents/plans/note-manager-plan.md` (942 lines)
   - `worktrees/manage-folders/.agents/plans/folder-manage-plan.md` (886 lines)

3. **Execute in parallel**: Using a terminal splitter (Ghostty), two Claude Code instances ran `/execute` simultaneously — each reading its own plan, implementing in its own worktree.

4. **Merge**: `/merge-worktrees manage-notes manage-folders` — integration branch created, each feature merged and tested individually, full validation passed, both tools integrated into main branch.

### Results and Stats

| Metric | Sequential | Parallel | Improvement |
|--------|-----------|----------|-------------|
| Total time | ~1 hour | ~30 minutes | 50% reduction |
| Files created | 30 + 60 | 30 + 60 (same) | Same output |
| Merge conflicts | N/A | Minimal (tool registration) | Clean merge |
| Validation | After each feature | After each merge step | Equivalent coverage |

### Key Observations

- **Isolation worked perfectly** — no conflicts during development; agents never touched each other's files
- **Merge was clean** — the only conflict point was registering new tools in `main.py` (a predictable, minimal change)
- **Validation caught issues** — tests ran after each merge step, confirming both features and their integration
- **The `.gitignore` lesson** — `worktrees/` was added to `.gitignore` to prevent worktree directories from being committed
- **Scalability potential** — could easily extend to 3-4 parallel implementations with the same approach; the demo deliberately used 2 to show the basic pattern

### What the Plans Looked Like

Both plans followed the structured plan template with per-task IMPLEMENT/PATTERN/IMPORTS/GOTCHA/VALIDATE format. Critically, both plans referenced the existing `obsidian_query_vault` tool as the pattern to mirror — this is the "build one, mirror many" pattern in action. The first tool was built carefully, and subsequent tools pointed back to it as the reference implementation.

---

## 7. The "Build One, Mirror Many" Pattern

### The Scaling Insight

The real power of parallel implementation isn't the git mechanics — it's the **pattern replication** strategy. The process:

1. **Build one feature excellently** — take the time to establish patterns: file structure, naming conventions, error handling, testing approach, logging
2. **Document everything** — typing standards, import patterns, validation commands, common gotchas
3. **Create plans that reference the first feature** — "mirror the pattern in `features/tool_a/`" is the most powerful instruction you can give
4. **Launch multiple agents** — each plan points back to the same reference implementation

### Five Prerequisites for True Parallel Power

1. **Good patterns first** — build one feature really well before parallelizing
2. **Documented standards** — typing, logging, testing, naming conventions written down
3. **Vertical slice architecture** — features isolated in their own directories
4. **Reusable plans** — agents follow established patterns via structured plans
5. **Validation automation** — tests, type checking, linting all automated and reliable

### Scalability Projections

| Parallel Agents | Time (approx.) | Time Savings |
|----------------|----------------|--------------|
| 1 (sequential) | 30 min/feature | Baseline |
| 2 (worktrees) | ~30 min total | 50% |
| 3 (worktrees) | ~35 min total | 65% |
| 10 (cloud) | ~45 min total | 90%+ |

**Real-world constraints**: Local machines support 2-3 parallel agents (RAM/CPU limited). Cloud resources scale to 10+. The bottleneck shifts from implementation time to human review bandwidth — the AI writes code faster than you can review it.

### Advanced Technique: Same-Branch Parallel Bug Fixes

Experienced users can even fix bugs in parallel on the same branch when the fixes touch different parts of the codebase. Each fix gets its own commit and can become a separate PR. This is mentioned as an advanced technique — start with feature-level parallelization before attempting this.

---

## 8. Out-of-the-Box Remote Coding Solutions

### The Current Landscape

This section surveys tools that provide remote parallel coding out of the box:

| Tool | Approach | Key Feature |
|------|----------|-------------|
| **Google Jules** | GitHub integration | Remote agent execution, auto-PR creation |
| **OpenAI Codex** | Cloud sandbox | Parallel coding environments with container isolation |
| **Claude Code Web** | Configurable environments | Remote Claude Code with custom Docker images |
| **Cursor 2** | Agent-first design | Agent mode comes BEFORE the editor |
| **Archon** | Open source | Agent work orders with task management |

**Common pattern**: Connect to GitHub repo -> send task -> tool spins up isolated environment -> agent clones repo -> implements changes -> creates PR.

### The Critical Limitation

These tools **do NOT use your custom commands, system prompts, or workflows**. They use their own default patterns — not your carefully crafted `/plan` and `/execute` commands, custom validation workflows, project-specific conventions, or MCP servers and skills.

This means:
- Your `/planning` command's 6-phase methodology? Ignored.
- Your `CLAUDE.md` global rules? Partially loaded at best.
- Your project-specific validation strategy? Not available.
- Your memory.md cross-session context? Available but writes are lost.

### The Future Direction

The goal is to set up remote environments that exactly mirror your local setup — same rules, same MCP servers, same patterns — so that remote agents produce the same quality output as local ones.

The industry is moving toward **full environment customization** in remote contexts. The goal is to mirror your exact local environment — commands, MCP servers, rules, patterns — so remote agents produce the same quality as local ones. Until then, local worktrees give you full control over the execution environment.

### The Industry Shift

The IDE is evolving — AI writes more of the code while developers engineer the systems, patterns, and workflows that guide it. The shift is from "writing code" to "engineering context."

Evidence: Cursor 2 puts agent mode BEFORE the editor — the agent-first paradigm is becoming the default. The future of software development is **engineering workflows for AI**, not writing every line of code yourself. The skills you build with this template — PIV Loop, structured planning, validation automation — are the skills that matter in this future.

---

## 9. Worktrees vs Remote System

### Two Paths to Parallel Implementation

| Aspect | Git Worktrees (this guide) | Remote System (see Remote Agentic System guide) |
|--------|--------------------------|--------------------------|
| **Where** | Local machine | Cloud environment |
| **Control** | Full (your environment exactly) | Configurable (Docker + orchestrator) |
| **Feedback** | Immediate terminal output | Real-time (Telegram) or async (GitHub) |
| **Scale** | 2-3 agents (local resources) | 10+ agents (cloud resources) |
| **Cost** | Free (your hardware) | ~$14/month (VPS hosting) |
| **Custom commands** | Full support (local `.claude/commands/`) | Full support (via `/load-commands`) |
| **Best for** | Development, iterative work | Production workflows, team collaboration |

### When to Choose Each

**Choose local worktrees when:**
- You need immediate feedback and full environmental control
- You're implementing 2-3 features in parallel
- You're in active development and may need to iterate
- You want to watch agents work in real-time via terminal splitter

**Choose the remote system when:**
- You need to scale beyond local resources (5+ features)
- You want 24/7 availability
- Team members need access to the same agents
- You're running production workflows where persistence matters

Both approaches use the same PIV Loop methodology. Both require vertical slice architecture. Both benefit from the "build one, mirror many" pattern. Worktrees are simpler to start; the remote system scales further.

---

## 10. Best Practices & Common Pitfalls

### Dependency Management

Each worktree has **independent dependencies** — they don't share `node_modules/`, `venv/`, or `.uv/` directories. Always run your dependency sync command in each worktree after creation. Keep dependency versions aligned across worktrees using the same lock file (`package-lock.json`, `uv.lock`, `poetry.lock`).

### Port Allocation

Assign dedicated ports per worktree to avoid conflicts. Convention: Worktree 1 on port 8124, Worktree 2 on port 8125, etc. Document port assignments in your project's CLAUDE.md or README.

### Cleanup Protocol

**Never manually delete worktree directories** — always use `git worktree remove`. Manual deletion leaves stale references in `.git/worktrees/` that cause errors when creating new worktrees. Proper sequence: `git worktree remove worktrees/<name>` -> `git branch -d <branch>`. Use `git worktree list` to check status.

### Commit Hygiene

Keep commits separate per feature. Each feature's commits stay in their own branch. Merge with `--no-ff` to preserve branch structure in history. This makes it easy to identify which commits belong to which feature and to revert an entire feature if needed.

### Project-Specific Customization

The `/new-worktree` and `/merge-worktrees` commands are **project-agnostic templates**. You must customize:
- Dependency commands: `uv sync` -> `npm install`, `pip install`, `poetry install`
- Validation commands: `pytest` -> `jest`, `vitest`, `mocha`
- Type checking: `mypy`/`pyright` -> `tsc --noEmit`
- Health check endpoints and server startup commands

### Common Pitfalls

| Pitfall | Prevention |
|---------|------------|
| Parallelizing non-isolated features | Verify vertical slice architecture first |
| Forgetting `worktrees/` in `.gitignore` | Add before first worktree creation |
| Manual deletion of worktree dirs | Always use `git worktree remove` |
| Port conflicts between worktrees | Allocate dedicated ports per worktree |
| Skipping validation during merge | Use `/merge-worktrees` which enforces gates |
| Parallelizing before patterns are established | Build one feature well first, then mirror |

---

## 11. Trust Progression & Readiness

### The Complete Trust Ladder

```
Manual Prompts → Commands → Chained Commands → Subagents → Worktrees → Remote Automation
  |  trust & verify  |  trust & verify  |  trust & verify  |  trust & verify  |  trust & verify  |
```

Worktrees sit near the top of the trust progression. Don't skip stages — parallel implementation amplifies both good patterns and bad ones.

### Readiness Checklist

Before using worktrees, verify:

- **`/execute` works reliably** — you've run 5+ features sequentially with consistent results
- **Validation catches issues** — your test suite, type checking, and linting are automated
- **Patterns are documented** — CLAUDE.md, on-demand reference guides, and structured plans are established
- **Architecture supports it** — features are isolated in vertical slices
- **Plans are comprehensive** — your structured plans have enough detail for an agent to succeed without additional research

If any of these are weak, strengthen them first. Parallelizing a broken workflow produces 2-3x the bugs, not 2-3x the features.

### The Amplification Effect

This is the key insight about trust progression: parallel execution is a **multiplier**, not an addition. If your single-agent workflow produces quality code 90% of the time, running 3 agents gives you ~3 quality implementations. If your workflow produces quality code 50% of the time, running 3 agents gives you ~3 mediocre implementations that each need rework. Fix the foundation before scaling.

---

## 12. Practical Exercises

### Exercise 1: Single Worktree Setup

**Challenge**: Create a worktree and verify the environment works.

**Steps**:
1. From your project root, run: `git worktree add worktrees/test-feature -b test-feature`
2. Navigate into the worktree: `cd worktrees/test-feature`
3. Install dependencies (e.g., `npm install`, `uv sync`)
4. Run your test suite from the worktree to verify the environment
5. Clean up: `cd ../..` -> `git worktree remove worktrees/test-feature` -> `git branch -d test-feature`

**Success criteria**: Tests pass inside the worktree. Cleanup leaves no stale references (`git worktree list` shows only the main working tree).

### Exercise 2: Parallel Implementation

**Challenge**: Implement two small features in parallel using the worktree workflow.

**Steps**:
1. Identify two isolated features in your project (or create two simple ones)
2. Create structured plans for each feature
3. Run `/new-worktree feature-a feature-b`
4. Place plans in each worktree
5. Open two terminals, launch Claude Code in each, run `/execute` in both
6. After both complete, run `/merge-worktrees feature-a feature-b`
7. Verify the merged result passes all tests

**Success criteria**: Both features implemented. Merge completed without conflicts. Full validation suite passes.

### Exercise 3: Remote Solutions Exploration

**Challenge**: Try one out-of-the-box remote coding solution to understand its capabilities and limitations.

**Steps**:
1. Pick one tool: Google Jules, OpenAI Codex, or Claude Code Web
2. Connect it to a test repository
3. Give it a simple task (e.g., "add a health check endpoint")
4. Compare the output to what your `/execute` command would produce
5. Note what's missing: custom commands? Validation? Pattern adherence?

**Success criteria**: You understand the gap between out-of-the-box remote tools and your customized local workflow.

---

## 13. FAQ: Common Questions

### "Can I use more than 2 worktrees?"

**Short answer**: Yes — the `/new-worktree` command supports 1-10 worktrees natively. **Long answer**: Pass multiple branch names as arguments: `/new-worktree feature/a feature/b feature/c`. The command spawns one Task agent per branch (max 10 concurrent — the subagent limit). Each gets a dedicated port (8124 + index). For `/merge-worktrees`, pass all branches to merge them sequentially with test-after-each validation. Local resource constraints (RAM, CPU) may limit practical concurrency to 3-5 simultaneous Claude Code instances.

### "What if my features share files?"

**Short answer**: Don't parallelize features that extensively share files. **Long answer**: If features touch the same files extensively, merge conflicts require manual resolution. Vertical slice architecture minimizes this. For the common case of shared registration points (adding a route, registering a tool):

1. **Verify isolation before parallelizing**: Review each feature's plan. If two plans modify the same files (beyond registration points), implement them sequentially.
2. **Registration point conflicts are expected**: Two features adding routes to the same file will create a trivial merge conflict. The `/merge-worktrees` command's test-after-each-merge catches any issues.
3. **Design for append-friendly registration**: Structure config/route files so new entries are appended (not inserted at specific positions). This reduces positional conflicts.

If your architecture isn't sliced, sequential development is safer. Consider refactoring toward vertical slices before attempting parallel implementation.

### "How do I prevent agents from conflicting?"

**Short answer**: Scope boundaries + vertical slices + merge-time conflict handling. **Long answer**: Three layers of protection:

1. **Code isolation (automatic)**: Git worktrees give each agent its own file system. Agent A literally cannot see Agent B's changes until merge time.
2. **Scope boundaries (planning phase)**: When creating feature plans, verify each plan only modifies files within its slice. If two plans overlap, don't parallelize.
3. **Merge-time validation (automatic)**: The `/merge-worktrees` command tests after each merge. If Agent A's code breaks when combined with Agent B's code, the merge stops with clear error reporting.

For research agents (subagents in `/planning`), overlap prevention comes from partitioning queries — each agent searches different directories or documentation sources, preventing duplicate findings.

### "Do I need vertical slice architecture?"

**Short answer**: For safe parallel implementation, yes. **Long answer**: Vertical slices are what make merge conflicts predictable and minimal. Without them, you're relying on luck — hoping agents don't modify the same files. You can parallelize without vertical slices for features that happen to be isolated, but it's fragile. The architecture is a one-time investment that pays off across all future parallel work.

### "How do worktrees compare to just cloning the repo multiple times?"

**Short answer**: Same isolation, better integration. **Long answer**: Cloning creates completely independent repositories — they don't share Git history, so merging requires remote pushes and pulls. Worktrees share the same `.git` directory, so branches and commits are instantly visible across all worktrees. Merging is a local `git merge`, not a remote operation. Worktrees also save disk space by not duplicating the Git history.

---

## 14. Next Steps

1. Read `reference/git-worktrees-overview.md` for the worktree overview
2. Review `.claude/commands/new-worktree.md` and `.claude/commands/merge-worktrees.md` for command specifications
3. Customize the worktree commands for your project's tech stack (dependency sync, validation, health checks)
4. Build one feature excellently — establish the patterns that parallel agents will mirror
5. Try parallel implementation on two isolated features using the worktree workflow
6. Read `reference/remote-agentic-system.md` for the remote system when you need to scale beyond local resources
7. Explore out-of-the-box remote tools (Jules, Codex, Claude Code Web) to understand the landscape

---

## 15. Related Resources

- **Worktree overview**: `reference/git-worktrees-overview.md` — on-demand guide on worktrees
- **Worktree setup command**: `.claude/commands/new-worktree.md` — `/new-worktree` specification
- **Merge command**: `.claude/commands/merge-worktrees.md` — `/merge-worktrees` specification
- **Subagents guide**: `reference/subagents-guide.md` — Subagents Deep Dive context isolation (complementary to worktrees)
- **Subagents overview**: `reference/subagents-overview.md` — on-demand subagent guide
- **Remote system guide**: `reference/remote-agentic-system.md` — remote parallel execution at scale
- **GitHub Orchestration guide**: `reference/github-orchestration.md` — GitHub Actions (prerequisite for remote workflows)
- **Execute command**: `.claude/commands/execute.md` — used inside each worktree
- **Structured plan template**: `templates/STRUCTURED-PLAN-TEMPLATE.md` — plans that agents execute in worktrees
- **Worktree command specifications**: See `.claude/commands/new-worktree.md` and `.claude/commands/merge-worktrees.md`

---

**Summary.** You now understand:
- Git worktrees as code-isolated working directories for parallel AI development
- Vertical slice architecture as the prerequisite for safe parallel implementation
- The four parallelization patterns and when to use each (subagents -> terminals -> worktrees -> cloud)
- The complete worktree workflow: setup, parallel execution, and gated merging
- The live demonstration results: 50% time savings with clean merges
- The "build one, mirror many" pattern for scaling to 10+ parallel agents
- Out-of-the-box remote solutions and their current limitation (no custom workflows)
- Industry direction: agent-first development and workflow engineering
- Best practices for dependencies, ports, cleanup, and customization
- The complete trust progression from manual prompts to parallel implementation
