# MCP Servers, Cloud Skills & Archon Integration

This guide explains **how MCP servers and Cloud Skills extend the PIV Loop with external tool access and progressive context loading** — covering the MCP protocol, token cost management, Cloud Skills architecture, Archon integration for knowledge bases and task management, PIV Loop integration, and practical examples — going deeper than the guide at `reference/mcp-skills-overview.md`.

---

## 1. What This Guide Teaches

### The Journey to External Integration

The System Foundations guide established the **why** — the system gap and mental models. The PIV Loop Practice guide taught the **how** — the PIV Loop in practice. The Global Rules Optimization guide taught **how to build** — modular CLAUDE.md and strategic context loading. The Command Design Framework guide taught **how to automate** — slash commands and the INPUT→PROCESS→OUTPUT framework. The Planning Methodology guide taught **how to plan** — the 6-phase planning methodology. The Implementation Discipline guide taught **execution discipline** — implementing from plans reliably and evolving the system through meta-reasoning. The Validation Discipline guide taught **validation discipline** — the 5-level pyramid, code review, system review, and divergence analysis. The GitHub Orchestration guide taught **GitHub integration** — using GitHub Actions as the orchestration layer. The Remote Agentic System guide taught **remote system architecture** — persistent sessions, multi-platform access, and the orchestrator pattern. This guide teaches **external system integration** — how MCP servers connect your AI coding assistant to databases, browsers, and task managers, while Cloud Skills provide progressive knowledge transfer without bloating your context window.

With MCP and Skills, the PIV Loop gains access to external tools (databases, browsers, knowledge bases) and structured knowledge (conventions, patterns, methodologies) — all through standardized protocols that keep context usage efficient.

### What You'll Learn

- **MCP protocol fundamentals** — client-server architecture, three capabilities, transport types, management commands
- **The token cost problem** — why MCP servers consume context, how Tool Search mitigates it
- **Cloud Skills architecture** — progressive disclosure, three-tier loading, skill directory structure
- **MCP vs Skills** — when to use each, how they complement each other
- **Archon MCP** — curated knowledge base (RAG) and shared task management (Kanban)
- **PIV Loop integration** — how MCP and Skills plug into planning, execution, validation, and commit phases
- **Token cost optimization** — budgeting context across memory.md, Archon, and multiple MCP servers
- **Practical examples** — Supabase, Playwright, AST-Grep, and the Skills + Commands conversion pattern

### The Core Insight

> "Just like USB-C gives us a standard for connecting electronic devices, MCP gives us a standard for connecting our AI applications to our external systems."

MCP is a **universal connector standard for AI**. Build one server, connect it to any AI assistant that supports the protocol. The M+N advantage: 3 platforms + 3 assistants = 6 integrations (not 9). Adding a new platform or assistant costs one integration, not N.

---

## 2. MCP Protocol Deep Dive

### Architecture

MCP uses a client-server architecture with three layers:

```text
AI Coding Assistant (Client)  →  MCP Server  →  External Service
    (Claude Code, Cursor,         (Supabase,      (Database,
     Codex, Gemini CLI)            Playwright,      Browser,
                                   Archon, Git)     Task Manager)
```

The **client** is your AI coding assistant. The **server** is middleware that translates between the AI and external services. Each server exposes a standardized interface so any client can use any server.

### Three Capabilities

Each MCP server exposes up to three types of functionality:

| Capability | What It Does | Examples |
|------------|-------------|---------|
| **Tools** | Functions the AI can call | `query_database()`, `take_screenshot()`, `create_task()` |
| **Resources** | Data the AI can read | File contents, API responses, configuration |
| **Prompts** | Pre-built workflows | Query templates, common operations |

### Transport & Adoption

Three transport types: **HTTP** (recommended for cloud services), **stdio** (local processes via stdin/stdout), **SSE** (deprecated, being phased out).

Supported by all major coding assistants: Claude Code, Cursor, Codex, Gemini CLI, Windsurf, Zed, Continue — any tool supporting the MCP standard.

MCP is an open standard developed by Anthropic and donated to the Linux Foundation's AAIF, ensuring vendor-neutral portability.

### Management Commands

```bash
claude mcp add <name> <transport> <args>   # Add a server
claude mcp list                             # List servers + Tool Search status
claude mcp get <name>                       # Show server details
claude mcp remove <name>                    # Remove a server
```

Server configuration lives in `.claude/settings.json` (project-level) or `~/.claude/settings.json` (user-level).

---

## 3. The Token Cost Problem & Tool Search

### The Cost Reality

Each MCP server loads **ALL** tool definitions into context upfront. This is the biggest challenge with MCP integration.

| Metric | Impact |
|--------|--------|
| Single server (20 tools) | ~14,000+ tokens consumed |
| 5 MCP servers | ~50% of context window gone |
| Each server | All-or-nothing — no selective loading |

### Context Window Budget

| Configuration | Servers | Tool Search | Context Available |
|--------------|---------|-------------|-------------------|
| Bare | 0 | N/A | ~100% |
| Light | 1-2 | Off | ~85% |
| Medium | 3-4 | Auto | ~90% (with Tool Search) |
| Heavy | 5+ | Required | ~85-90% (with Tool Search) |
| Heavy | 5+ | Off | ~50% (NOT recommended) |

### Tool Search: The Mitigation

**Auto-enabled** when total tool count exceeds 10% of context window capacity:

- Instead of loading all tool definitions upfront, defers them behind a search tool
- AI discovers relevant tools on-demand via semantic search
- **Reduces token usage by ~85%** in practice
- Trade-off: small latency cost for tool discovery vs massive context savings

**How to check**: `claude mcp list` shows Tool Search status per server. Also monitor overall context with `/context` command.

**Configure**: Set `ENABLE_TOOL_SEARCH` environment variable to force-enable or disable.

**Rule of thumb**: If you exceed 3 MCP servers, verify Tool Search is active.

---

## 4. Cloud Skills Architecture

### Progressive Disclosure

Skills solve the token cost problem differently from Tool Search — through a **three-tier loading model** that keeps context lean until needed:

| Tier | Content | Token Cost | When Loaded |
|------|---------|------------|-------------|
| **Tier 1** | Metadata (name + description) | ~100 tokens per skill | Session start (always) |
| **Tier 2** | Full SKILL.md content | 2,000-20,000 tokens | On-demand when relevant |
| **Tier 3** | Supporting files (references/, examples/, scripts/) | Variable, unbounded | During execution only |

**Comparison**: 30 skills = ~3,000-6,000 tokens upfront (Tier 1 only). 5 MCP servers without Tool Search = ~70,000 tokens upfront. Skills win by 10x+ on initial context cost.

### Skill Directory Structure

A skill is a **directory** (not a single file):

```text
.claude/skills/ast-grep/
├── SKILL.md          # Entry point + frontmatter (required)
├── references/       # Detailed docs (on-demand, Tier 3)
│   └── rule_reference.md
├── examples/         # Example outputs (on-demand, Tier 3)
│   └── good-example.md
└── scripts/          # Executable scripts (on-demand, Tier 3)
    └── setup.sh
```

**SKILL.md frontmatter** determines auto-load behavior:

```yaml
---
name: ast-grep
description: Guide for writing ast-grep rules for structural code search. Use when...
allowed-tools: [Read, Glob, Grep, Bash]
---
```

The `description` field is the **only** content loaded at Tier 1. Write it to be specific and action-oriented — it determines when the AI auto-loads the full skill.

### Two Loading Modes

1. **Auto-load**: AI reads Tier 1 description, determines skill is relevant to current task, loads Tier 2 automatically
2. **Explicit invocation**: User or command directly references the skill

### Skills vs Commands

| Aspect | Commands | Skills |
|--------|----------|--------|
| **File type** | Single `.md` file | Directory with SKILL.md + supporting files |
| **Token cost** | Description loaded upfront | ~100 tokens metadata + on-demand content |
| **Discovery** | Explicit `/command-name` | Auto-load via description OR explicit |
| **Best for** | Lightweight workflows | Complex methodologies with reference docs |

Skills and Commands are unified — same INPUT→PROCESS→OUTPUT framework, identical frontmatter. They coexist. All existing commands continue working unchanged.

**When to upgrade a command to a skill**: command exceeds 250 lines, loads 3+ external files, benefits from auto-load via description, or has reference docs that fit a directory structure.

---

## 5. Archon: Knowledge Base + Task Management

### What Archon Is

> "For us, it is a sleek interface to manage knowledge, context, and tasks for our projects. For the AI coding assistant, it is an MCP server to collaborate on the same context and tasks."

Archon is the **command center for AI coding** — an MCP server combining curated knowledge search with shared task management.

### Two Problems Solved

**Problem 1 — Uncontrolled Web Search**: AI coding assistants have web search, but results are generic, uncontrolled, and unreliable. You cannot control what documentation the AI finds, and quality varies wildly.

> "AI coding assistants have web search to pull external knowledge. But what if we want to control the documentation that it searches through and curate it for the coding assistant? That is what we have here."

**Archon solution**: Crawl and index specific documentation. AI searches only through curated, known-good sources you control.

**Problem 2 — Invisible Task Lists**: Coding assistants have internal task management, but humans have no visibility into what tasks the AI is working on. No control over prioritization, no collaboration.

**Archon solution**: Shared Kanban board. Humans manage via UI, AI manages via MCP. Full real-time collaboration. Both sides see the same tasks, update in real-time.

### RAG Workflow (Research Before Implementation)

**Critical rule**: Keep queries SHORT — 2-5 keywords only. Vector search works best with concise queries.

| Step | Function | Purpose |
|------|----------|---------|
| 1 | `rag_get_available_sources()` | List all indexed documentation sources |
| 2 | `rag_search_knowledge_base(query, source_id, match_count)` | Search specific docs with short query |
| 3 | `rag_search_code_examples(query, match_count)` | Find relevant code examples |
| 4 | `rag_list_pages_for_source(source_id)` | Browse all pages in a source |
| 5 | `rag_read_full_page(page_id or url)` | Read complete page content |

**Query examples** — good vs bad:

| Good (2-5 keywords) | Bad (too long) |
|---------------------|---------------|
| `"vector search pgvector"` | `"how to implement vector search with pgvector in PostgreSQL"` |
| `"React useState"` | `"React hooks useState useEffect useContext useReducer"` |
| `"authentication JWT"` | `"how to implement user authentication with JWT tokens"` |

### Task Management Workflow

Mandatory 6-step cycle before coding:

| Step | Action | Function |
|------|--------|----------|
| 1 | Get task | `find_tasks(task_id="...")` or `find_tasks(filter_by="status", filter_value="todo")` |
| 2 | Start work | `manage_task("update", task_id="...", status="doing")` |
| 3 | Research | Use RAG workflow above |
| 4 | Implement | Write code based on research findings |
| 5 | Mark review | `manage_task("update", task_id="...", status="review")` |
| 6 | Next task | `find_tasks(filter_by="status", filter_value="todo")` |

**Status flow**: `todo` → `doing` → `review` → `done`

**Critical**: Only ONE task in "doing" status at a time. This prevents context confusion and gives humans clear progress visibility.

### ARCHON-FIRST Rule

When Archon MCP is available, it overrides all other task management systems. See `sections/15_archon_workflow.md` for the complete rule set, tool reference, and integration patterns. The core principle: always check Archon availability first, use it as the primary system for tasks and research.

### Task Granularity

| Project Scope | Task Level | Examples |
|--------------|-----------|---------|
| Feature-specific | Granular implementation tasks | "Create database schema", "Implement API endpoints", "Write unit tests" |
| Codebase-wide | Feature-level tasks | "Implement user authentication", "Add payment processing" |

Default: lean toward more granular. Each task = 30 minutes to 4 hours of work.

---

## 6. Integration in the PIV Loop

MCP and Skills integrate at **every phase** of the PIV Loop — not just implementation.

### Planning Phase

| Integration Point | What Happens |
|------------------|-------------|
| **Phase 1.5** | Create Archon project: `manage_project("create", title="...", description="...")` |
| **Phase 3b** | Archon RAG research (prioritized over generic web search): `rag_get_available_sources()` → `rag_search_knowledge_base(query, source_id)` |
| **Phase 5** | Create all tasks in Archon from plan: `manage_task("create", project_id=..., title=..., task_order=...)` |

Skills loaded during planning: planning methodology, research patterns, domain conventions.

### Execute Phase

| Integration Point | What Happens |
|------------------|-------------|
| **Step 1.5** | Initialize Archon tasks (create project if needed, extract tasks from plan) |
| **Step 2a.5** | Per-task status update: `manage_task("update", task_id=..., status="doing")` — ONE "doing" at a time |
| **Step 5.5** | Mark all tasks done, update project status to "complete" |

Skills loaded during execution: implementation patterns, coding standards, deployment procedures.

### Validate & Commit Phases

| Phase | MCP Integration | memory.md Integration |
|-------|----------------|----------------------|
| **Validate** | Optional: update task status during `/code-review` | N/A |
| **Commit** | Step 7: report feature completion in Archon | Step 6: append cross-session lessons |

Both systems coexist — Archon tracks tasks and provides documentation, memory.md stores learning and pattern recognition.

### Backward Compatibility

When integrating MCP into commands, use **conditional checks**: "If Archon available, use it." Not everyone has MCP servers configured. Commands must work with or without MCP — the integration is additive, not required.

---

## 7. Example MCP Servers & Skills

### Server Examples

| Server | Type | Purpose | Key Capabilities |
|--------|------|---------|-----------------|
| **Supabase** | MCP | Database management | DDL/DML operations, schema listing, RLS advisors, migrations |
| **Playwright** | MCP | Browser automation | Navigate URLs, take screenshots, accessibility snapshots, console messages |
| **Archon** | MCP | Knowledge + tasks | RAG search, task CRUD, project management, document storage |
| **AST-Grep** | Skill | Structural code search | AST pattern matching, code queries, rule writing |

### Why AST-Grep Is a Skill, Not MCP

AST-Grep teaches the AI **how to write rules** for structural code search. There is no external system to connect to — it is pure knowledge transfer. This makes it a perfect example of the MCP vs Skill distinction: external I/O = MCP, internal knowledge = Skill.

### Skills + Commands Conversion Example

Converting `/planning` from a command to a skill demonstrates progressive disclosure savings:

| Metric | Command (before) | Skill (after) |
|--------|-----------------|---------------|
| Upfront token cost | ~600 tokens (292 lines loaded) | ~100 tokens (metadata only) |
| On-demand cost | N/A (always loaded) | ~400 tokens (when planning starts) |
| Session start reduction | Baseline | **80-85% reduction** |
| Per-planning-session cost | ~600 tokens | ~500 tokens (Tier 1 + Tier 2) |

**Implementation pattern**: Keep the command (`.claude/commands/planning.md`) for backward compatibility. Add a skill directory (`.claude/skills/planning-methodology/`) with SKILL.md + references/ for users who want progressive loading. Both coexist — no migration required.

Best for teams with 10+ commands where upfront token cost matters.

---

## 8. Token Cost Analysis & Optimization

### Combined Token Budget (memory.md + Archon)

| Configuration | Upfront Cost | Per-Feature Cost | Total Overhead |
|--------------|--------------|------------------|----------------|
| memory.md only | 0 | 0 (file read) | ~0% MCP overhead |
| Archon only (Tool Search) | ~5,000-7,000 | ~200-500 tokens | ~5-7% upfront |
| memory.md + Archon | ~5,000-7,000 | ~200-500 tokens | ~5-7% upfront + 0.2-0.5% per feature |
| Archon + 3 MCPs (Tool Search ON) | ~10,000-15,000 | ~500-1,000 tokens | ~10-15% upfront |

### Recommendation: Use Both Together

memory.md and Archon solve **different problems** and complement each other:

- **memory.md**: Cross-session learning — past gotchas, decisions, patterns. Zero MCP overhead.
- **Archon RAG**: Curated documentation search — better than generic web. Shared across team.
- **Archon Tasks**: Real-time progress visibility — shared Kanban board. Human-AI collaboration.

### Four Optimization Rules

1. **Tool Search for 3+ servers**: Verify active with `claude mcp list`. If context usage from tools exceeds 20%, Tool Search may not be working
2. **Short RAG queries**: 2-5 keywords maximum. Extract core technical terms, omit filler words
3. **Concise memory.md entries**: Keep entries to 1-2 lines each. Under 100 lines total.
4. **Create tasks upfront**: Extract ALL tasks from the plan in Step 1.5. Avoid mid-implementation task creation overhead

---

## 9. Lessons Learned & Best Practices

### Patterns (DO)

| Pattern | Why |
|---------|-----|
| Keep RAG queries to 2-5 keywords | Vector search performs best with concise, focused queries |
| One task in "doing" at a time | Prevents context confusion, gives humans clear progress visibility |
| Curate documentation sources | Controlled knowledge beats generic web search |
| Use progressive loading (Skills) | Keeps session start lean, loads knowledge on-demand |
| Enable Tool Search for 3+ servers | Prevents context window exhaustion |
| Use conditional MCP checks in commands | Backward compatibility — commands work with or without MCP |
| Start with 1-2 MCP servers | Verify value before adding complexity |

### Anti-Patterns (DON'T)

| Anti-Pattern | Why |
|-------------|-----|
| Long verbose RAG queries | Dilutes semantic meaning, returns poor results |
| Multiple tasks in "doing" | Context confusion, unclear progress for humans |
| Uncontrolled web search when RAG available | Generic results, unreliable quality |
| 5+ MCP servers without Tool Search | ~50% context consumed before you start working |
| Skipping task status updates | Humans lose visibility, AI loses focus |
| Adding MCP when a Skill would suffice | Unnecessary token cost — use MCP for I/O, Skills for knowledge |

### Five Key Principles

1. **"Load what you need, when you need it"** — Progressive disclosure for skills, Tool Search for MCP
2. **"Control the knowledge base, control the quality"** — Curated RAG over generic web search
3. **"Visibility enables collaboration"** — Shared Kanban board for human-AI task management
4. **"Conciseness improves relevance"** — Short queries for vector search
5. **"Focus enables completion"** — One task in "doing" at a time

---

## 10. Practical Exercises

### Exercise 1: Add an MCP Server to Your Project

**Challenge**: Add the Playwright MCP server and use it to validate a web page.

**Steps**:

1. Install: `claude mcp add playwright npx @anthropic/mcp-playwright`
2. Verify: `claude mcp list` — confirm Playwright appears with Tool Search status
3. Test: Ask Claude to navigate to a URL, take a screenshot, and report the page structure
4. Check context: Run `/context` to see token impact of the new server
5. Compare: Note context usage before and after adding the server

**Success criteria**: AI can navigate to a URL, capture a screenshot, and describe the accessibility tree. Tool Search status is visible in `claude mcp list`. You understand the token cost of adding one server.

### Exercise 2: Create Your First Cloud Skill

**Challenge**: Create a skill directory for a project-specific convention (e.g., database naming, API design, testing patterns).

**Steps**:

1. Create directory: `.claude/skills/your-pattern/`
2. Write `SKILL.md` with YAML frontmatter:
   - `name`: kebab-case identifier
   - `description`: specific action-oriented sentence (this determines auto-load)
   - Body: high-level methodology and instructions
3. Add `references/` subdirectory with a detailed guide document (detailed rules, examples, edge cases)
4. Test auto-load: start a new session, describe a task matching the skill description, verify the AI loads it
5. Test explicit: invoke the skill directly and verify the full content loads correctly

**Success criteria**: AI auto-loads the skill based on task description without explicit invocation. Skill content appears in context only when relevant. The `description` field accurately triggers auto-load for matching tasks.

### Exercise 3: Archon-Driven PIV Loop (Optional)

**Challenge**: Use Archon for a complete feature implementation with RAG research and task tracking.

**Steps**:

1. Create project: `manage_project("create", title="...", description="...")`
2. Create 3-5 tasks from a plan with proper ordering
3. For each task: update status to "doing", use RAG to research, implement, mark "review"
4. Verify Kanban board shows progress in real-time
5. Mark all tasks "done" and update project status

**Success criteria**: Kanban board reflects the complete task lifecycle. RAG research informed at least one implementation decision. All tasks progressed through `todo` → `doing` → `review` → `done`.

---

## FAQ: Common Questions

### "Do I need MCP servers to use this template?"

**Short answer**: No — MCP is entirely optional and additive.

**Long answer**: The template works without any MCP servers. All commands, plans, and validation work standalone. MCP adds external system access (databases, browsers, task managers) when you need it. Start without MCP, add servers as specific needs arise. The conditional checks in commands ("if Archon available") ensure backward compatibility.

### "How many MCP servers should I use?"

**Short answer**: Start with 1-2, add more only when needed.

**Long answer**: Each server consumes tokens (mitigated by Tool Search above 3 servers). Add one server, verify it provides value for 5+ features, then consider adding another. Monitor context usage with `/context`. Most developers benefit from 1-3 servers (typically Archon + one domain-specific server like Supabase or Playwright).

### "When should I create a Skill vs add content to CLAUDE.md?"

**Short answer**: Skill when content exceeds 250 lines or benefits from progressive loading.

**Long answer**: Apply the Two-Question Framework (see `reference/global-rules-optimization.md`). Is the knowledge constant or task-specific? If constant and needed every session, put it in CLAUDE.md sections. If task-specific and large (250+ lines, 3+ reference files), create a skill directory. Skills cost ~100 tokens upfront vs potentially thousands for always-loaded sections. The progressive disclosure model is specifically designed for knowledge that's needed sometimes, not always.

### "Is Archon required for task management?"

**Short answer**: No — it's optional but significantly improves visibility.

**Long answer**: Without Archon, your coding assistant uses its built-in task management (invisible to you). Archon adds three things: human-visible Kanban board, curated RAG for documentation, and real-time task collaboration. It is most valuable when you want to see AI progress in real-time, curate specific documentation for the AI to search, or work collaboratively on task prioritization. See `sections/15_archon_workflow.md` for complete integration rules.

### "How do I know if Tool Search is working?"

**Short answer**: Run `claude mcp list` and check the Tool Search status column.

**Long answer**: Tool Search auto-enables when total tool definitions exceed 10% of context window capacity. Verify with `claude mcp list` — it shows Tool Search status per server. Also run `/context` to see overall context usage breakdown. If you have 3+ servers and tools consume more than 20% of context, Tool Search may not be active — set `ENABLE_TOOL_SEARCH=true` environment variable to force-enable it.

---

## Next Steps

1. Read this guide (you're doing this now)
2. Study `reference/mcp-skills-overview.md` for the MCP & Skills overview
3. Try Exercise 1 — add an MCP server and test it
4. Try Exercise 2 — create a Cloud Skill for a project convention
5. Study `sections/15_archon_workflow.md` for the complete Archon integration rules
6. Move to the Subagents Deep Dive guide (see `reference/subagents-deep-dive.md`) to learn about parallel execution and context isolation

---

## Related Resources

- **MCP & Skills overview**: `reference/mcp-skills-overview.md` — on-demand guide with tables and integration patterns
- **Archon workflow rules**: `sections/15_archon_workflow.md` — complete ARCHON-FIRST rule, tool reference, task/RAG workflow
- **Remote Agentic System**: `reference/remote-agentic-system.md` — prerequisite: remote system architecture
- **Subagents guide**: `reference/subagents-guide.md` — next: parallel execution with context isolation
- **MCP official docs**: <https://modelcontextprotocol.io>
- **Skills docs**: <https://code.claude.com/docs/en/skills>

---

**That's the MCP, Skills & Archon guide!** You now understand:

- ✅ The MCP protocol — client-server architecture, three capabilities, universal adoption
- ✅ The token cost problem — why MCP servers consume context and how Tool Search mitigates it
- ✅ Cloud Skills architecture — progressive disclosure with three-tier loading
- ✅ MCP vs Skills — when to use each, how they complement each other
- ✅ Archon — curated knowledge base (RAG) + shared task management (Kanban)
- ✅ PIV Loop integration — how MCP and Skills plug into every phase
- ✅ Token cost optimization — budgeting context across memory.md, Archon, and multiple servers
- ✅ Practical patterns — Supabase, Playwright, AST-Grep, Skills+Commands conversion
- ✅ The five key principles — progressive loading, curated knowledge, visibility, conciseness, focus

**Next**: Learn about subagents — isolated AI instances with custom system prompts that run in their own context window. Parallelize research with up to 10 concurrent agents, build specialized workers for code review, and design agent output formats that minimize context handoff loss. See `reference/subagents-deep-dive.md`.
