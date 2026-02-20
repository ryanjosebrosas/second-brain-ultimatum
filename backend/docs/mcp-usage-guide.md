# Second Brain MCP — Usage Guide

## What is This?

The Second Brain is an **MCP server** (Model Context Protocol). It has no UI — no dashboard, no buttons, no sidebar. You interact with it through **natural language** in any MCP-compatible client.

Think of it as a brain that any AI assistant can plug into.

## Supported Clients

| Client | Config File |
|--------|------------|
| **Claude Code** (CLI) | `~/.claude/mcp.json` |
| **Cursor** | `.cursor/mcp.json` |
| **Windsurf** | Windsurf MCP settings |
| **Claude.ai** | MCP tool picker |
| **Any MCP client** | Varies |

### Connection Config

**Local (stdio — default):**
```json
{
  "mcpServers": {
    "second-brain": {
      "command": "python",
      "args": ["-m", "second_brain.mcp_server"],
      "cwd": "/path/to/backend"
    }
  }
}
```

**Docker (HTTP):**
```json
{
  "mcpServers": {
    "second-brain": {
      "url": "http://localhost:3030"
    }
  }
}
```

## How to Use It

There's no UI. You just talk. The AI client sees the available tools and calls them based on what you say.

### User Context

The system supports multiple users with separate memory spaces. Shared company content (`brainforge`) is always included in searches.

```
You: "Who am I right now?"
AI:  → calls get_current_user()
     → "Current user: uttam"

You: "Switch to Luke"
AI:  → calls set_user("luke")
     → "Switched from 'uttam' to 'luke'"

You: "Switch back to uttam"
AI:  → calls set_user("uttam")
```

**Available users:** `uttam`, `robert`, `luke`, `brainforge` (shared)

---

## Available Tools

### Memory & Search

| Tool | What You Say | What It Does |
|------|-------------|--------------|
| `recall` | "What do I know about branding?" | Semantic search across memories |
| `ask` | "How should I approach this proposal?" | Q&A with full brain context |
| `graph_search` | "Find connections between AI and marketing" | Graph-aware entity search |
| `vector_search` | "Find similar content to this text" | Raw pgvector similarity search |
| `search_experiences` | "Show my past client interactions" | Search experience entries |
| `search_patterns` | "What writing patterns do I have?" | Search extracted patterns |
| `search_examples` | "Show my LinkedIn examples" | Search stored examples |
| `search_knowledge` | "Find my company research" | Search knowledge repo |

### Learning & Ingestion

| Tool | What You Say | What It Does |
|------|-------------|--------------|
| `learn` | "Learn from this: [content]" | Extract patterns from text |
| `learn_image` | "Learn from this screenshot" | Extract patterns from images |
| `learn_document` | "Learn from this PDF" | Extract patterns from documents |
| `learn_video` | "Learn from this video" | Extract patterns from video |
| `ingest_example` | "Save this as a LinkedIn example" | Store a content example |
| `ingest_knowledge` | "Store this research" | Store knowledge entry |
| `vault_ingest` | "Ingest the vault" | Bulk ingest vault markdown files |

### Content Creation & Review

| Tool | What You Say | What It Does |
|------|-------------|--------------|
| `create_content` | "Write a LinkedIn post about AI tools" | Generate content in your voice |
| `review_content` | "Review this draft" | Score content against patterns |
| `analyze_clarity` | "Is this readable?" | Readability analysis |
| `compose_email` | "Write an email to the client" | Email composition |
| `find_template_opportunities` | "Can we templatize this?" | Detect template patterns |

### Coaching & Planning

| Tool | What You Say | What It Does |
|------|-------------|--------------|
| `coaching_session` | "Morning check-in" | Daily accountability coaching |
| `prioritize_tasks` | "Prioritize these tasks: ..." | PMO-style task ranking |
| `run_brain_pipeline` | "Full analysis on this content" | Multi-step agent pipeline |

### Projects

| Tool | What You Say | What It Does |
|------|-------------|--------------|
| `create_project` | "Start a new project: Website Redesign" | Create project with lifecycle |
| `list_projects` | "Show my projects" | List all projects |
| `project_status` | "How's the website project?" | Get project details |
| `advance_project` | "Move website project to review" | Change lifecycle stage |
| `update_project` | "Update project description" | Edit project fields |
| `add_artifact` | "Add a brief to the project" | Attach deliverables |

### System

| Tool | What You Say | What It Does |
|------|-------------|--------------|
| `set_user` | "Switch to Luke" | Change active user context |
| `get_current_user` | "Who am I?" | Check active user |
| `brain_health` | "How's my brain doing?" | Memory stats and health |
| `brain_setup` | "Is my brain set up?" | Check setup completion |
| `graph_health` | "Is the graph working?" | Graph memory status |
| `consolidate_brain` | "Clean up my memories" | Deduplicate and consolidate |
| `growth_report` | "Show growth this month" | Learning metrics report |
| `pattern_registry` | "List all patterns" | View pattern confidence levels |
| `list_content_types` | "What content types exist?" | Show content type registry |
| `manage_content_type` | "Add a new content type" | Create/update content types |

---

## Example Workflows

### 1. Write Content in Someone's Voice

```
You: "Switch to Luke"
You: "What writing patterns does Luke use for LinkedIn?"
You: "Write a LinkedIn post about AI automation for small businesses"
You: "Review this draft against Luke's patterns"
```

### 2. Prepare for a Client Meeting

```
You: "What do I know about ABC Home and Commercial?"
You: "Show transcripts for ABC"
You: "What action items came up in the last meeting?"
```

### 3. Learn from New Content

```
You: "Learn from this case study: [paste content]"
You: "Save this as a case-study example"
You: "What patterns did you extract?"
```

### 4. Daily Coaching

```
You: "Morning check-in"
You: "Prioritize these tasks: finish proposal, review content, update CRM"
You: "How's my brain growth this month?"
```

### 5. Research & Recall

```
You: "What do I know about competitor positioning?"
You: "Find connections between our brand strategy and client pain points"
You: "Show my past experiences with content strategy"
```

---

## Architecture

```
You (natural language)
  ↓
MCP Client (Claude Code / Cursor / Claude.ai)
  ↓
Second Brain MCP Server (FastMCP, port 3030)
  ↓
┌─────────────────────────────────────┐
│  Agent Layer (Pydantic AI)          │
│  recall, ask, learn, create, review │
│  coach, pmo, specialist, etc.       │
├─────────────────────────────────────┤
│  Service Layer                      │
│  MemoryService (Mem0 + Graph)       │
│  StorageService (Supabase)          │
│  EmbeddingService (Voyage AI)       │
├─────────────────────────────────────┤
│  Storage                            │
│  Mem0 Cloud (semantic + graph)      │
│  Supabase (structured + pgvector)   │
└─────────────────────────────────────┘
```

## Tips

- **Be conversational** — say "What do I know about X?" not "recall query=X"
- **The AI picks the tool** — you don't need to name tools, just describe what you want
- **Shared content is always included** — brainforge company knowledge is in every search
- **Switch users for different voices** — each user has their own patterns and style
- **Learn before creating** — teach the brain patterns first, then generate content
