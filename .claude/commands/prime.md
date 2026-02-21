---
description: Prime agent with codebase understanding
---

# Prime: Load Project Context

Load project context using parallel Explore agents for speed and context isolation. All agents use `Explore` type with `haiku` model — optimized for fast, read-only analysis.

## Step 1: Detect Context Mode

Check for code directories using a **single** Glob call with brace expansion:

```
{src,app,frontend,backend,lib,api,server,client}/**
```

**If ANY files found** → **Codebase Mode** (go to Step 2B)
**If no files found** → **System Mode** (go to Step 2A)

---

## Step 2A: System Mode — Launch 4 Parallel Agents

Launch ALL of the following Task agents **simultaneously**:

### Agent 1: Resources Inventory
- **subagent_type**: `Explore`
- **model**: `haiku`
- **description**: "Inventory commands and agents"
- **prompt**: |
    You are inventorying a Claude Code project's available resources.

    1. Run via Bash: `grep -r "^description:" .claude/commands/ 2>/dev/null | head -20`
    2. Run via Bash: `ls .claude/skills/ 2>/dev/null`
    3. Read `.claude/agents/README.md` for the agent catalog

    Return ONLY this formatted section:

    ## Available Resources
    ### Commands
    | Command | Purpose |
    |---------|---------|
    {one row per command found}

    ### Agents
    - **Research**: {agent names}
    - **Code Review**: {agent names}
    - **Utility**: {agent names}
    - **Specialist**: {agent names}

    ### Skills
    {list any skills found, or "None"}

### Agent 2: Project Structure
- **subagent_type**: `Explore`
- **model**: `haiku`
- **description**: "Map project structure"
- **prompt**: |
    You are mapping a methodology/documentation project's structure.
    Use Glob to find .md files in: root, sections/, reference/, templates/, requests/.
    Identify key directories and their purposes.

    Return ONLY this formatted section:

    ## Detection
    - **Mode**: System
    - **Signals**: {what you found — no code directories, only docs/templates}

    ## Project Overview
    - **Type**: {project description}
    - **Tech Stack**: {e.g., "Markdown, Claude Code CLI, Git"}
    - **Structure**: {key directories, 1 line each}

### Agent 3: Memory Context
- **subagent_type**: `Explore`
- **model**: `haiku`
- **description**: "Read project memory"
- **prompt**: |
    Read the file `memory.md` if it exists.

    Return ONLY this formatted section:

    ## Memory Context
    - **Last Session**: {most recent date, or "No memory.md found"}
    - **Key Decisions**: {bullet list, or "None recorded"}
    - **Active Patterns**: {bullet list, or "None recorded"}
    - **Gotchas**: {bullet list, or "None recorded"}
    - **Memory Health**: {if >7 days old, warn "Stale". Otherwise "Fresh"}

### Agent 4: Git State
- **subagent_type**: `Explore`
- **model**: `haiku`
- **description**: "Get git state"
- **prompt**: |
    Run via Bash: `git log -10 --oneline` and `git status`

    Return ONLY this formatted section:

    ## Current State
    - **Branch**: {current branch name}
    - **Status**: {clean/dirty, summary of changes}
    - **Recent Work**: {list last 10 commits as "- `hash` message"}

---

## Step 2B: Codebase Mode — Launch 4 Parallel Agents

Launch ALL of the following Task agents **simultaneously**:

### Agent 1: Architecture & Tech Stack
- **subagent_type**: `Explore`
- **model**: `haiku`
- **description**: "Analyze architecture and stack"
- **prompt**: |
    You are analyzing a codebase's architecture and tech stack.

    1. Run via Bash: `tree -L 2 -d -I 'node_modules|__pycache__|.git|dist|build|.pytest_cache|*.egg-info' 2>/dev/null || ls -la`
    2. Read package manifest (package.json, pyproject.toml, Cargo.toml, go.mod)
    3. Identify architectural layers from directory structure:
       - API: routes/, api/, controllers/
       - Business: services/, agents/, domain/
       - Data: models/, schemas/, migrations/
       - UI: components/, pages/, views/
       - Tests: tests/, __tests__/

    Return ONLY these formatted sections:

    ## Detection
    - **Mode**: Codebase
    - **Signals**: {code directories found}

    ## Architecture
    - **Entry Points**: {main files — e.g., src/index.ts, main.py}
    - **Layers**: {which layers exist}
    - **Key Directories**: {important dirs, 1 line each}

    ## Tech Stack
    - **Language**: {language and version}
    - **Framework**: {primary framework}
    - **Database**: {DB technology or "None detected"}
    - **Testing**: {test framework}
    - **Key Dependencies**: {top 5-7 with versions}

### Agent 2: Code Conventions & README
- **subagent_type**: `Explore`
- **model**: `haiku`
- **description**: "Identify conventions and purpose"
- **prompt**: |
    You are identifying a codebase's conventions and purpose.

    1. Read README.md (if exists)
    2. Read 1-2 core source files (services/, agents/, or main entry point)
    3. Skip .claude/ directory — that's tooling

    Limit: Read at most 3 files total.

    Return ONLY these formatted sections:

    ## Project Overview
    - **Purpose**: {what this app does — 1-2 sentences}
    - **Key Capabilities**: {main features, comma-separated}
    - **Setup**: {setup summary, or "See README"}

    ## Core Principles
    - **Naming**: {snake_case, camelCase, PascalCase observed}
    - **Error Handling**: {pattern used}
    - **Code Organization**: {how modules are structured}
    - **Testing**: {unit, integration, e2e — what's present}

### Agent 3: Memory Context
- **subagent_type**: `Explore`
- **model**: `haiku`
- **description**: "Read project memory"
- **prompt**: |
    Read the file `memory.md` if it exists.

    Return ONLY this formatted section:

    ## Memory Context
    - **Last Session**: {most recent date, or "No memory.md found"}
    - **Key Decisions**: {bullet list, or "None recorded"}
    - **Active Patterns**: {bullet list, or "None recorded"}
    - **Gotchas**: {bullet list, or "None recorded"}
    - **Memory Health**: {if >7 days old, warn "Stale". Otherwise "Fresh"}

### Agent 4: Git State
- **subagent_type**: `Explore`
- **model**: `haiku`
- **description**: "Get git state"
- **prompt**: |
    Run via Bash: `git log -10 --oneline` and `git status`

    Return ONLY this formatted section:

    ## Current State
    - **Branch**: {current branch name}
    - **Status**: {clean/dirty, summary of changes}
    - **Recent Work**: {list last 10 commits as "- `hash` message"}

---

## Step 3: Assemble Report

After ALL agents return, assemble the Prime Context Report:

1. Start with `# Prime Context Report`
2. Add each agent's returned section in this order:
   - **System Mode**: Detection → Project Overview → Available Resources → Current State → Memory Context → Suggested Next Steps
   - **Codebase Mode**: Detection → Project Overview → Architecture → Tech Stack → Core Principles → Current State → Memory Context → Suggested Next Steps
3. Add a `## Suggested Next Steps` section — synthesize from Current State + Memory Context to suggest what to work on next
4. Present the assembled report to the user

**CRITICAL**: Do NOT re-read files or re-run git commands. The agents already did all the work. Just assemble and present.

---

## Design Notes

**Why Explore + Haiku?**
- `Explore` agents have Bash access — can run git commands
- All tasks are read-only (no Edit/Write needed)
- `haiku` is 10x faster and cheaper than `sonnet`
- Simple extraction tasks don't need complex reasoning

**Consolidation:**
- System Mode: 5 → 4 agents (merged Commands + Agents inventory)
- Codebase Mode: 6 → 4 agents (merged Architecture + Tech Stack, merged Conventions + README)
