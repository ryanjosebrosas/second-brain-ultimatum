### Extending the PIV Loop

MCP (Model Context Protocol) and Cloud Skills are two complementary integration technologies. MCP provides **access** to external systems — databases, browsers, APIs, task managers. Skills provide **knowledge** about how to do things — procedures, conventions, domain expertise. Together they expand what the PIV Loop can automate without bloating the context window.

Think of MCP as USB-C for AI — a universal connector standard that lets any AI tool talk to any external service through a standardized protocol.

### MCP Protocol Fundamentals

MCP is an open standard developed by Anthropic and donated to the Linux Foundation's AAIF. It uses a client-server architecture: your AI tool (Claude Code, Cursor, Codex) is the client, external services are servers.

Each server exposes up to three capabilities:
- **Tools** — Functions the AI can call (e.g., query database, take screenshot, create issue)
- **Resources** — Data the AI can read (e.g., file contents, API responses)
- **Prompts** — Pre-built workflows the AI can execute

Supported by all major coding assistants: Claude Code, Cursor, Codex, Gemini CLI. Three transport types: HTTP (cloud services, recommended), SSE (deprecated), stdio (local processes). Add servers with `claude mcp add`, manage with `claude mcp list/get/remove`.

### The Token Cost Problem

Critical limitation: each MCP server loads ALL tool definitions into context upfront. A single server with 20 tools can consume 14,000+ tokens just for descriptions. Five major MCPs can eat ~50% of your context window before you type anything. Each server is all-or-nothing — no selective loading.

**Tool Search** mitigates this (auto-enabled when tools exceed 10% of context):
- Instead of loading all tools upfront, defers them behind a search tool
- AI discovers relevant tools on-demand via search
- Reduces token usage by ~85% in practice
- Configure with `ENABLE_TOOL_SEARCH` environment variable

Rule of thumb: if you exceed 3 MCP servers, ensure Tool Search is active. Monitor with `/context` command.

### Cloud Skills Architecture

Skills solve the context bloat problem through **progressive disclosure** — a three-tier loading model:

- **Tier 1 — Metadata** (~100 tokens per skill): Only name + description loaded at session start. AI uses this to decide relevance. 30 skills cost only ~3,000-6,000 tokens total
- **Tier 2 — Full SKILL.md** (variable): Loaded on-demand when AI determines the skill applies or user invokes it. Typically 2,000-20,000 tokens
- **Tier 3 — Supporting files** (on-demand): Referenced docs, examples, scripts loaded only during execution. Effectively unbounded without upfront cost

Skill structure: a directory with `SKILL.md` entry point + optional `references/`, `examples/`, `scripts/` subdirectories. SKILL.md uses YAML frontmatter (name, description, allowed-tools) followed by markdown instructions.

Skills teach Claude HOW to do things — they're organized, autonomous on-demand context. Unlike commands (which you explicitly invoke), skills can auto-load when the AI determines they're relevant to the current task.

### MCP vs Skills

| Aspect | MCP Servers | Cloud Skills |
|--------|-------------|--------------|
| **Purpose** | Access external systems & data | Encode procedures & knowledge |
| **Token cost** | Thousands upfront per server | ~100 tokens initially, rest on-demand |
| **Loading** | All tools at once (mitigated by Tool Search) | Progressive 3-tier disclosure |
| **Best for** | Databases, APIs, browsers, issue trackers | Workflows, conventions, domain knowledge |
| **Creation** | Install package or implement server | Write markdown documentation |
| **Portability** | Vendor-neutral (works with any AI tool) | Currently Claude-focused (standard emerging) |

Use BOTH together — MCP provides data access, Skills provide procedural knowledge. Example: MCP connects to your database, a Skill teaches Claude your data analysis methodology.

### Integration in the PIV Loop

MCP and Skills integrate at every phase — not just implementation.

**Planning phase:**
- MCP: Search curated knowledge bases via Archon RAG (Phase 3b in `/planning` command)
- Pattern: `rag_get_available_sources()` → `rag_search_knowledge_base(query, source_id)` → `rag_search_code_examples(query)`
- Rule: Keep queries SHORT (2-5 keywords) for best vector search results
- Skills: Load planning methodology, research patterns, domain conventions

**Execute phase:**
- MCP: Archon task management cycle integrated in `/execute` command
- Pattern: Create project (Step 1.5) → Create all tasks → Update status per task (Step 2) → Mark complete (Step 5.5)
- Critical: Only ONE task in "doing" at a time
- Skills: Load implementation patterns, coding standards, deployment procedures

**Validate phase:**
- MCP: Update task status in `/code-review` (optional when part of PIV Loop)
- Skills: Review conventions, validation procedures, quality checklists

**Commit phase:**
- MCP: Mark feature complete in Archon (Step 7 in `/commit` command)
- memory.md: Store cross-session lessons (Step 6 in `/commit` command)
- Both systems coexist — different purposes (task tracking vs pattern learning)

When integrating MCP into commands, use conditional checks ("If Archon available, use it") for backward compatibility — not everyone has MCP servers configured.

### Context Window Budget

| Configuration | MCP Servers | Tool Search | Context Available |
|--------------|-------------|-------------|-------------------|
| Bare | 0 | N/A | ~100% |
| Light | 1-2 | Off | ~85% |
| Medium | 3-4 | Auto | ~90% (with Tool Search) |
| Heavy | 5+ | Required | ~85-90% (with Tool Search) |
| Heavy | 5+ | Off | ~50% (not recommended) |

Monitor usage with `/context` command. Skills have negligible upfront cost (~100 tokens each) — the budget concern is primarily about MCP servers.

**Note**: Token costs in this section refer to context window consumption, not billing. With MAX subscription (recommended), you pay a flat monthly fee — these token counts affect how much context is available per session, not your bill. With API billing, tokens directly affect cost.

### Token Cost Analysis: Archon Integration

| Configuration | Upfront Cost | Per-Feature Cost | Total Overhead |
|--------------|--------------|------------------|----------------|
| memory.md only | 0 | 0 (file read) | ~0% MCP overhead |
| Archon only (with Tool Search) | ~5,000-7,000 | ~200-500 tokens | ~5-7% upfront + 0.2-0.5% per feature |
| memory.md + Archon | ~5,000-7,000 | ~200-500 tokens | ~5-7% upfront + 0.2-0.5% per feature |
| Archon + 3 MCPs (Tool Search ON) | ~10,000-15,000 | ~500-1,000 tokens | ~10-15% upfront + 0.5-1% per feature |

**Recommendation**: Use Archon for task management and RAG. Use `memory.md` for cross-session learning:
- **memory.md**: Cross-session learning (past gotchas, decisions, patterns) — zero MCP overhead
- **Archon RAG**: Curated documentation search (better than generic web)
- **Archon Tasks**: Real-time progress visibility (shared Kanban board)

**Token Optimization Rules**:
1. Ensure Tool Search is active when using 3+ MCP servers (`claude mcp list` shows Tool Search status)
2. Keep RAG queries SHORT (2-5 keywords maximum)
3. Keep memory.md entries concise (1-2 lines each)
4. Create tasks upfront in Archon (no mid-implementation task creation overhead)

### Skills + Commands Integration Example

Convert `/planning` from command to skill to demonstrate progressive disclosure:

**Before** (command):
- planning.md: 292 lines loaded upfront
- Token cost: ~600 tokens per planning session
- References: STRUCTURED-PLAN-TEMPLATE.md loaded inline

**After** (skill):
- SKILL.md: 80-100 lines (high-level 6-phase methodology)
- Metadata loaded: ~100 tokens (description alone)
- references/ directory: Template, phase guides, examples (loaded when planning starts)
- Token cost: ~100 tokens upfront + ~400 tokens when planning phase loads Tier 2

**Result**: 80-85% token reduction at session start, zero reduction per actual planning session. Best for teams with 10+ commands.

**Implementation**: Skills and Commands coexist — keep planning.md for backward compatibility, add `.claude/skills/planning-methodology/` for users who want progressive loading.

### Archon: Knowledge + Task Management

Archon is an MCP server that acts as a command center for AI coding — combining curated knowledge with task tracking.

Two key capabilities:
1. **Curated Knowledge Base** — Crawl and index documentation (Supabase docs, framework guides, API references). AI searches this instead of generic web search. More reliable, more relevant. Keep queries SHORT (2-5 keywords) for best results
2. **Task Management** — Kanban board visible to both human and AI via MCP. Tasks move through: To Do → Doing → Review → Done. Human can update tasks in real-time, AI sees changes immediately

Particularly powerful for the execute phase: read tasks from plan, create in Archon, track progress per task. Both human and AI see the same board — enabling real-time collaboration.

See `reference/mcp-skills-archon.md` for setup instructions.

### Reference Files

- `reference/mcp-skills-archon.md` — Detailed setup guide for MCP servers, skills creation, and Archon
- `sections/15_archon_workflow.md` — Archon task management & RAG workflow rules (auto-loaded via CLAUDE.md @reference)
- Load when: setting up MCP servers for a project, creating custom skills, troubleshooting token usage
- MCP official docs: https://modelcontextprotocol.io
- Skills docs: https://code.claude.com/docs/en/skills
