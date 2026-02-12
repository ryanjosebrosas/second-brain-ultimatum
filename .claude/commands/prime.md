---
description: Prime agent with codebase understanding
---

# Prime: Load Project Context

## Objective

Build comprehensive understanding of the codebase by analyzing structure, documentation, and key files.

## Process

### 1. Analyze Project Structure

List all tracked files:
!`git ls-files`

### 2. Read Core Documentation

- Read project rules: @CLAUDE.md
- If `sections/` directory exists, read the section files referenced in CLAUDE.md
- Read README files at project root and major directories
- Read any architecture documentation

### 3. Identify Key Files

Based on the structure, identify and read:
- Main entry points (main.py, index.ts, app.py, etc.)
- Core configuration files (pyproject.toml, package.json, tsconfig.json)
- Key model/schema definitions
- Important service or controller files

### 4. Understand Current State

Check recent activity:
!`git log -10 --oneline`

Check current branch and status:
!`git status`

### 5. Read Project Memory (if memory.md exists)

If `memory.md` exists at project root, read it and include relevant entries in the output report:
- Key decisions that affect current work
- Known gotchas for the project's tech stack
- Architecture patterns established in past sessions
- Recent session notes for continuity

If memory.md doesn't exist, note "No memory.md found — consider creating one from `templates/MEMORY-TEMPLATE.md`"

### 5b. Search Archon Knowledge Base (if available)

If Archon RAG is available, search for project-relevant documentation:

1. Get available sources: `rag_get_available_sources()`
2. Search for project setup and architecture docs:
   - Query: "{project-name} setup"
   - Query: "{primary-framework} best practices"
3. Include top 3-5 relevant results in the output report

If Archon RAG is not available, skip this section gracefully.

## Output Report

Provide a concise summary covering:

### Project Overview
- Purpose and type of application
- Primary technologies and frameworks
- Current version/state

### Architecture
- Overall structure and organization
- Key architectural patterns identified
- Important directories and their purposes

### Tech Stack
- Languages and versions
- Frameworks and major libraries
- Build tools and package managers
- Testing frameworks

### Core Principles
- Code style and conventions observed
- Documentation standards
- Testing approach

### Current State
- Active branch
- Recent changes or development focus
- Any immediate observations or concerns

### Memory Context (from memory.md)
- Key decisions from past sessions
- Known gotchas and lessons
- Relevant patterns established
- (If no memory.md found, note "No memory.md found — this is a fresh project or memory.md hasn't been created yet")

### Knowledge Base Context (from Archon RAG)
- Relevant documentation sources found
- Key articles or guides applicable to this project
- (If Archon RAG unavailable, note "No Archon RAG available — skip knowledge base search")

**Make this summary easy to scan - use bullet points and clear headers.**
