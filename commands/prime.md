---
description: Prime agent with codebase understanding
---

# Prime: Load Project Context

## Process

### 1. Detect Context Mode

Check for code directories using Glob patterns:
- `src/`, `app/`, `frontend/`, `backend/`, `lib/`, `api/`, `server/`, `client/`

**If ANY exist**: This is **Codebase Mode** — focus on source code entry points.
**If NONE exist**: This is **System Mode** — focus on methodology/documentation files.

Report the detected mode and what signals triggered it.

### 2. Analyze Project Structure

**System Mode**:
- List all `.md` files in root, `sections/`, `reference/`, `.claude/`
- Identify commands, agents, skills, templates

**Codebase Mode**:
- List tracked files: !`git ls-files`
- Show directory structure: !`tree -L 3 -I 'node_modules|__pycache__|.git|dist|build' 2>/dev/null || ls -la`
- Detect architectural layers — look for these directory patterns:
  - **Routing/API**: `routes/`, `pages/`, `app/` (Next.js), `controllers/`, `api/`
  - **Business Logic**: `services/`, `use-cases/`, `domain/`, `agents/`
  - **Data Layer**: `models/`, `schemas/`, `prisma/`, `migrations/`, `entities/`
  - **Middleware**: `middleware/`, `guards/`, `interceptors/`
  - **UI**: `components/`, `views/`, `layouts/`, `hooks/`
  - **Utilities**: `utils/`, `helpers/`, `lib/`, `common/`
  - **Config**: `config/`, `env/`
  - **Tests**: `tests/`, `test/`, `__tests__/`, `spec/`
- Note which layers exist and which are absent — this reveals the architecture

### 3. Read Core Documentation

> CLAUDE.md and sections/ are ALREADY auto-loaded. Do NOT re-read them.

**Always read**:
- `memory.md` (if exists) — FULL content, this is cross-session context

**System Mode additional**:
- List `.claude/commands/` and `.claude/agents/` with descriptions

**Codebase Mode additional**:
- Main entry points (main.py, index.ts, app.py, etc.)
- Package manifest (package.json or pyproject.toml) — extract:
  - Key dependencies with versions
  - Available scripts/commands
  - Package manager (npm/yarn/pnpm/pip/poetry)
  - Testing framework (pytest, jest, vitest, etc.)
- Important service or controller files (pick 1-2 representative ones)
- Schema/model definitions if present (prisma/schema.prisma, models.py, schema.graphql)
- README.md (for project overview)

**Skip**: `.claude/` directory contents (commands, agents, skills) — these are tooling, not the app.

Limit: Read at most 7 files total. Prioritize: entry point > manifest > schema > service > README.

### 4. Identify Key Files

**System Mode**:
- List commands with their descriptions
- List agents with their purposes
- List available skills

**Codebase Mode**:
- Entry points with their roles (e.g., "src/index.ts — Express server setup")
- Architecture layers found (from Step 2) and how they connect
- Data models and their relationships
- Key conventions observed (naming, error handling, logging, state management)
- Testing infrastructure (framework, test organization, coverage setup)

### 5. Understand Current State

Check recent activity:
!`git log -10 --oneline`

Check current branch and status:
!`git status`

## Output Report

Provide a **COMPREHENSIVE** report (50-80 lines) that is LLM-ready for handoff.
Use the template matching the detected mode.

**Make this summary easy to scan — use bullet points and clear headers.**

---

**System Mode** — use this template:

    # Prime Context Report

    ## Detection
    - **Mode**: System
    - **Signals**: {what triggered System Mode}

    ## Project Overview
    - **Type**: {project description}
    - **Tech Stack**: {languages, frameworks, build tools}
    - **Structure**: {key directories and their purposes}

    ## Current State
    - **Branch**: {name}
    - **Status**: {git status summary}
    - **Recent Work**: {last 10 commits}

    ## Memory Context
    - **Last Session**: {date from memory.md}
    - **Key Decisions**: {from memory.md}
    - **Active Patterns**: {from memory.md}
    - **Gotchas**: {from memory.md}
    - **Memory Health**: {staleness warning if >7 days}

    ## Available Resources
    ### Commands
    {List each command with brief description}

    ### Agents
    {List each agent with brief description}

    ## Suggested Next Steps
    - {Based on current state and memory}

---

**Codebase Mode** — use this template:

    # Prime Context Report

    ## Detection
    - **Mode**: Codebase
    - **Signals**: {what directories/files triggered Codebase Mode}

    ## Project Overview
    - **Purpose**: {what this application does}
    - **Version**: {from manifest if available}

    ## Architecture
    - **Entry Points**: {main files and their roles}
    - **Layers**: {which architectural layers exist and how they connect}
    - **Data Flow**: {how data moves through the system}
    - **Key Directories**: {important dirs and their purposes}

    ## Tech Stack
    - **Language**: {language and version}
    - **Framework**: {primary framework and version}
    - **Database**: {DB technology if applicable}
    - **Testing**: {test framework and approach}
    - **Build Tools**: {package manager, bundler, etc.}

    ## Core Principles
    - **Naming**: {conventions observed — camelCase, snake_case, etc.}
    - **Error Handling**: {pattern used}
    - **Code Organization**: {how files/modules are structured}
    - **Testing Approach**: {unit, integration, e2e — what's present}

    ## Dependencies & Tooling
    - **Key Dependencies**: {top 5-10 with versions}
    - **Dev Dependencies**: {linter, formatter, type checker}
    - **Scripts**: {available npm/make/task commands}

    ## Current State
    - **Branch**: {name}
    - **Status**: {git status summary}
    - **Recent Work**: {last 10 commits}

    ## Memory Context
    - **Last Session**: {date from memory.md}
    - **Key Decisions**: {from memory.md}
    - **Active Patterns**: {from memory.md}
    - **Gotchas**: {from memory.md}
    - **Memory Health**: {staleness warning if >7 days}

    ## Suggested Next Steps
    - {Based on current state, recent work, and memory}

---

**Key principle**: The output should be comprehensive enough that a fresh LLM session can pick up full context without additional exploration. "Handoff-ready" means another agent can continue work immediately.
