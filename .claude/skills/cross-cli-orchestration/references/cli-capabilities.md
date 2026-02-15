# CLI Capabilities Reference

Detailed reference for OpenCode and Codex CLI tools. Load when delegating tasks or troubleshooting CLI interactions.

---

## OpenCode CLI

### Non-Interactive Mode
```bash
# Basic execution
opencode run "implement the auth module"

# With JSON output (structured, parseable)
opencode run --format json "implement the auth module"

# With specific working directory
opencode run --cwd /path/to/project "implement the auth module"
```

### Key Flags
| Flag | Description | Use When |
|------|-------------|----------|
| `--format json` | JSON structured output | Parsing results programmatically |
| `--cwd <path>` | Set working directory | Targeting a specific project |
| `--attach` | Connect to running server | Reusing a warm instance |

### MCP Support
- Supports local and remote MCP servers
- OAuth auto-handling for remote servers
- Pre-authenticate: `opencode mcp auth <server-name>`

### Model Selection
- 75+ models supported (Claude, OpenAI, Gemini, local via Ollama)
- Configure in `opencode.json` or environment variables
- Can switch models mid-session in TUI mode

---

## Codex CLI

### Non-Interactive Mode
```bash
# Basic execution
codex exec "review src/auth.ts for security issues"

# Full auto (no confirmation prompts)
codex exec --full-auto "fix the bug in login.ts"

# JSON output (JSONL event stream)
codex exec --json "review this code"

# With working directory
codex exec --cd /path/to/project "review this code"
```

### Key Flags
| Flag | Description | Use When |
|------|-------------|----------|
| `--full-auto` | No confirmation prompts | Unattended execution |
| `--json` | JSONL event stream output | Parsing results |
| `--cd <path>` | Set working directory | Targeting a project |
| `--sandbox` | Control file access | Restricting agent scope |
| `--ask-for-approval never` | Disable all prompts | Fully automated mode |
| `--skip-git-repo-check` | Allow non-repo dirs | Outside git repos |

### Models
- Default: gpt-5.3-codex (optimized for coding)
- Available: codex-1 (o3-based), other OpenAI models
- Included with ChatGPT Plus/Pro/Business subscriptions

### MCP Support
- STDIO and HTTP MCP servers supported
- `codex mcp add` for configuration
- Auto-launches MCP servers on session start

---

## Comparison

| Capability | OpenCode | Codex |
|-----------|----------|-------|
| Non-interactive | `opencode run` | `codex exec` |
| JSON output | `--format json` | `--json` |
| Working dir | `--cwd` | `--cd` |
| Auto mode | Default in `run` | `--full-auto` |
| MCP support | Yes (OAuth auto) | Yes (STDIO + HTTP) |
| Model count | 75+ providers | OpenAI models only |
| Billing | Varies by provider | ChatGPT subscription |
| Git required | No | Yes (use `--skip-git-repo-check`) |

---

## Pre-Flight Checklist

Before delegating tasks, verify:

- [ ] CLI is installed and in PATH
- [ ] Authentication is configured (API keys or OAuth)
- [ ] MCP servers pre-authenticated (if needed)
- [ ] Working directory is correct
- [ ] Git repo exists (for Codex) or `--skip-git-repo-check` is used
