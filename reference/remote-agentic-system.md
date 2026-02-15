# Remote Agentic Coding System: Architecture & Deployment

This guide explains **how to build and deploy a remote AI coding system** — covering the orchestrator architecture, environment setup, Telegram and GitHub webhook configuration, remote PIV Loop walkthrough, cloud deployment, and cross-system integration — going deeper than the guide at `reference/remote-system-overview.md`.

---

## 1. Remote Execution: Core Concepts

### The Journey to Remote Execution

The System Foundations guide established the **why** — the system gap and learning architecture. The PIV Loop Practice guide taught the **how** — the PIV Loop in practice. The Global Rules Optimization guide taught **how to build** — modular CLAUDE.md and strategic context loading. The Command Design Framework guide taught **how to automate** — slash commands and the INPUT→PROCESS→OUTPUT framework. The Planning Methodology guide taught **how to plan** — the 6-phase planning methodology. The Implementation Discipline guide taught **execution discipline** — implementing from plans reliably and evolving the system through meta-reasoning. The Validation Discipline guide taught **validation discipline** — the 5-level pyramid, code review, system review, and divergence analysis. The GitHub Orchestration guide taught **GitHub integration** — using GitHub Actions as the orchestration layer for remote, trigger-based workflows. This guide teaches **remote system architecture** — how to build a custom application that runs your entire PIV Loop remotely with real-time conversation, multi-platform access, and persistent sessions.

This represents the culmination of the trust progression. Everything from the preceding guides now runs remotely, accessible from any platform, any device, 24/7.

### What You'll Learn

- **The orchestrator pattern** — M+N vs M×N integration architecture and why it matters
- **IPlatformAdapter interface** — how platforms (Telegram, GitHub, Slack) communicate with the system
- **IAssistantClient interface** — how coding assistants (Claude Code, Codex) are abstracted
- **Environment & authentication setup** — database, tokens, platform credentials, Docker configuration
- **Telegram setup** — BotFather workflow, real-time streaming, closest-to-CLI experience
- **GitHub webhook setup** — ngrok for local, DNS + Caddy for cloud, event configuration
- **The remote PIV Loop** — full walkthrough with real failure modes and iteration patterns
- **Session management** — automatic plan/execute separation, persistence, concurrent sessions
- **Cloud deployment** — DigitalOcean setup, security hardening, Caddy SSL, DNS configuration
- **Cross-system integration** — how every preceding concept applies in the remote system

### The Core Insight

> "I put so much time into creating this upfront. And so everything that you're looking at here in the final architecture maps pretty much exactly to what I have in the PRD. I barely had to change anything because I had a clear idea of what I wanted upfront and I iterated and iterated on the PRD before I built anything. That's the power of putting a lot of time into planning upfront. So it just made the entire application build 10, 20, 30 times faster because I had this guiding everything and it was rock solid from the get-go."

The entire Remote Agentic Coding System was built using the PIV Loop methodology — PRD first, then global rules, then on-demand context, then incremental PIV loops per feature. The system is proof that the methodology works at scale.

### The Architecture Insight

> "If we have a middleman that is able to generalize this connection, that means that if I add another application here, I don't actually have to build any more integrations besides just with the orchestrator itself. It becomes an M plus N set of integrations instead of M times N."

This orchestrator pattern is the key architectural decision. It determines everything else about the system — how platforms connect, how assistants are abstracted, and how the system scales.

---

## 2. The Orchestrator Architecture

### The M×N Problem

Direct integration between platforms and coding assistants creates an explosion of integrations:

| Scenario | Platforms | Assistants | Direct Integrations | Orchestrator Integrations |
|----------|-----------|------------|--------------------:|-------------------------:|
| Current | 3 | 3 | 9 (3×3) | 6 (3+3) |
| Add 1 platform | 4 | 3 | 12 (+3) | 7 (+1) |
| Add 1 assistant | 3 | 4 | 12 (+3) | 7 (+1) |
| Scale to 5+5 | 5 | 5 | 25 (5×5) | 10 (5+5) |

The orchestrator sits between platforms and assistants, standardizing communication through two generic interfaces. Adding a new platform = 1 integration. Adding a new assistant = 1 integration. Each new integration automatically works with everything on the other side.

### Architecture Diagram

```
Applications (Telegram, GitHub, Slack)
         |  IPlatformAdapter
    ORCHESTRATOR
         |  IAssistantClient
Coding Assistants (Claude Code, Codex)
         |
    POSTGRES DB
  (sessions, conversations, codebases)
```

### IPlatformAdapter Interface

Standardizes how applications send and receive messages:

| Method | Purpose | Example |
|--------|---------|---------|
| `receiveMessage()` | Get incoming message from platform | Telegram update, GitHub webhook payload |
| `sendMessage(conversationId, message)` | Send response back to platform | Telegram chat message, GitHub issue comment |
| `getConversationId()` | Identify the conversation thread | Telegram chat ID, GitHub issue number |

Each platform implements this interface differently, but the orchestrator treats them identically. Telegram streams all tool calls in real-time; GitHub posts only the final summary. The interface doesn't care — it just sends and receives.

### IAssistantClient Interface

Standardizes how the system interacts with any coding assistant:

| Method | Purpose | Example |
|--------|---------|---------|
| `startSession(prompt)` | Begin a new coding session | `claude` with system prompt, `codex` with initial instruction |
| `resumeSession(sessionId)` | Continue an existing session | Resume after container restart |
| `sendMessage(sessionId, message)` | Send instruction to assistant | `/command-invoke execute` |
| `endSession(sessionId)` | Clean up session resources | Close Claude Code process |

Different assistants have different auth methods (`claude setup-token` vs `.codex/auth.json`), different streaming formats, and different capabilities. The interface abstracts all of this — the orchestrator doesn't need to know which assistant it's talking to.

### Key Architectural Benefits

1. **Decoupling** — Platforms don't know about assistants, assistants don't know about platforms
2. **Extensibility** — Add a new platform in ~1 PIV loop (just implement `IPlatformAdapter`)
3. **Consistency** — Same behavior across all platform/assistant combinations
4. **Maintainability** — Bug fixes in one place benefit all integrations

---

## 3. Platform Integrations

### Platform Comparison

| Aspect | Telegram | GitHub | Slack (planned) |
|--------|----------|--------|-----------------|
| **Output style** | Real-time streamed (tool calls, thoughts) | Final summary comment only | TBD |
| **Context injection** | Manual (conversation-based) | Auto-injected (issue/PR body) | TBD |
| **Best for** | Interactive development, quick tasks | Full PIV loops, code review | Team collaboration |
| **Experience** | Closest to local CLI | Git-native workflows | TBD |

### Why Output Modes Differ

GitHub is not a chat app — posting every tool call would flood the issue with dozens of comments. Only the final summary matters. Telegram IS a chat app — real-time streaming shows all intermediate steps, giving the closest experience to using a local CLI.

The output mode is configured per platform adapter, not per assistant. The same Claude Code session streams to Telegram but summarizes to GitHub.

### Context Injection Timing

A critical design decision: **inject platform context at the first AI assistant call**, not when loading commands or resetting the session.

Why this matters:
- `/load-commands` and `/reset` are system commands — they don't go to the AI assistant
- Injecting context on these commands would waste it (context sent to nothing)
- Waiting until the first actual AI call (e.g., `/command-invoke prime`) ensures the assistant receives and processes the context

For GitHub, this means the issue/PR body is included in the first message to the coding assistant, automatically providing the task description without manual copy-paste.

---

## 4. Environment & Authentication Setup

### Environment Variables by Category

| Category | Variable | Purpose | Notes |
|----------|----------|---------|-------|
| **Database** | `DATABASE_URL` | Postgres connection string | Local Docker or remote (Supabase/Neon) |
| **GitHub (CLI)** | `GH_TOKEN` | GitHub CLI operations (create PR, comment) | Personal access token or fine-grained token |
| **GitHub (Clone)** | `GITHUB_TOKEN` | Repository cloning | Can be same token, different permissions |
| **GitHub (Webhook)** | `GITHUB_WEBHOOK_SECRET` | Verify webhook payloads | `openssl rand -base64 32` |
| **Claude Code** | `CLAUDE_CODE_OAUTH_TOKEN` | Claude Code authentication | **(Recommended)** Via `claude setup-token` (year-long, uses MAX/Pro subscription) |
| **Codex** | 4 values from `~/.codex/auth.json` | Codex authentication | Run `codex login` first, then copy values |
| **Telegram** | `TELEGRAM_BOT_TOKEN` | Bot API access | From @BotFather |
| **Config** | `DEFAULT_ASSISTANT` | Which assistant to use | Auto-detected from `.claude/` or `.codex/` folders |

### Two GitHub Tokens Explained

The system needs TWO GitHub tokens because they serve different purposes:
- **`GH_TOKEN`** — Used by the GitHub CLI (`gh`) for operations like creating PRs, commenting on issues, managing branches. Needs `repo` scope
- **`GITHUB_TOKEN`** — Used for `git clone` operations when pulling repositories into the container. Can be the same token but may have different permission requirements

### Claude Code Authentication

```bash
claude setup-token
```

This runs an OAuth flow that generates a long-lived token. Key details:
- Token lasts approximately one year
- Uses your Claude MAX/Pro subscription credits (not separate API credits)
- Store the resulting token as `CLAUDE_CODE_OAUTH_TOKEN` in `.env`

**Important**: If `ANTHROPIC_API_KEY` is also set in your environment, Claude Code will use API billing instead of your subscription — this can result in significantly higher costs. Remove or unset `ANTHROPIC_API_KEY` to ensure subscription billing.

### Docker Build Notes

- First build takes several minutes (installs GitHub CLI, coding assistants, dependencies)
- Subsequent builds use Docker cache — typically ~30 seconds
- Container restart after `.env` changes: `docker compose down && docker compose up -d`

---

## 5. Telegram Setup

### BotFather Workflow

1. Open Telegram, search for `@BotFather`
2. Send `/newbot`
3. Choose a display name (e.g., "My Coding Agent")
4. Choose a username (must end in `bot`, e.g., `my_coding_agent_bot`)
5. BotFather replies with your bot token — copy it
6. Set `TELEGRAM_BOT_TOKEN=<your-token>` in `.env`

### First-Use Flow

After starting the Docker container:

```
/help                                        # See available commands
/clone https://github.com/user/repo          # Clone a repository
                                             # System auto-detects .claude/ or .codex/
/load-commands .claude/commands               # Load your slash commands
/commands                                     # List loaded commands
/command-invoke prime                         # Start a PIV loop
```

### Key Behavior

- **Real-time streaming**: Every tool call, thought, and intermediate step appears in the chat
- **Manual context**: No auto-injection — you provide context through conversation
- **Session persistence**: Conversation survives container restarts
- **Works on any device**: Phone, tablet, desktop — same experience

Telegram is the recommended platform for learning and interactive development because the streaming output gives maximum visibility into what the agent is doing.

---

## 6. GitHub Webhook Setup (Local Development)

### Why Webhooks Are Needed

Unlike GitHub Actions (which run inside GitHub's infrastructure), the remote system runs outside GitHub. It needs to RECEIVE events (issue comments, PR reviews) via HTTP webhooks. This requires:
1. Your app to be accessible via HTTPS (GitHub requires it)
2. A webhook secret to verify payloads are genuine
3. Event subscriptions for the events you care about

### Step-by-Step Setup

**1. Generate webhook secret:**

```bash
# Linux/Mac
openssl rand -base64 32

# Windows PowerShell
[Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }) -as [byte[]])
```

Set `GITHUB_WEBHOOK_SECRET=<your-secret>` in `.env`.

**2. Set up ngrok (for local HTTPS):**

```bash
# Install ngrok (https://ngrok.com)
ngrok http 3000
```

ngrok provides a persistent HTTPS URL per device (same URL across restarts on the same machine). Copy the `https://` URL.

**3. Configure GitHub webhook:**

Navigate to your repo: Settings → Webhooks → Add webhook:

| Field | Value |
|-------|-------|
| Payload URL | `https://<ngrok-url>/webhook/github` |
| Content type | `application/json` |
| Secret | Your generated webhook secret |
| SSL verification | Enable |
| Events | Issues, Issue Comments, Pull Requests (uncheck Pushes) |

**4. Verify:** GitHub sends a ping event on creation. Check for 200 OK in the "Recent Deliveries" tab.

### Common Gotchas

- **Container restart required** after `.env` changes — ngrok URL stays the same but the app needs to re-read env vars
- **ngrok URL persists** across restarts on the same device — no need to update the webhook URL
- **HTTPS required** — GitHub rejects plain HTTP webhook URLs
- **Event selection matters** — only subscribe to events you handle (Issues, Issue Comments, Pull Requests); extra events create unnecessary load

---

## 7. The Remote PIV Loop (Walkthrough)

### Full Example: Adding Brave Web Search Tool

This walkthrough is based on an actual demonstration — adding a Brave web search tool to an Obsidian-based agent project via GitHub.

#### Step 1: Create GitHub Issue

```markdown
Title: Add Brave web search tool

Description:
- Implement Brave API web search
- Follow vertical slice architecture
- Update .env.example and documentation

Requirements:
- Use existing tool patterns
- Test with recent query (e.g., "GPT 5.1")
- Validate imports work
```

#### Step 2: Load Commands

```
@remote-agent /load-commands .claude/commands
```

Result: 16 commands loaded (prime, planning, execute, validate, etc.)

#### Step 3: Prime

```
@remote-agent /command-invoke prime
```

Issue context is auto-injected at this point (the first AI assistant call). The agent receives the issue body alongside the prime instructions. Result: codebase context loaded with task awareness.

#### Step 4: Plan

```
@remote-agent /command-invoke plan-feature "brave web search tool"
```

Result:
- Structured plan created (622 lines, within 700-1000 constraint)
- Saved to `.agents/plans/brave-web-search-plan.md`
- Feature branch `feature/brave-web-search` created and pushed
- Plan committed to branch

**Validate the plan**: Review on GitHub via the branch view or PR diff before proceeding.

#### Step 5: Execute

```
@remote-agent /command-invoke execute
Use branch: feature/brave-web-search
Plan: .agents/plans/brave-web-search-plan.md
Also make a PR at end of execution
```

Result:
- **Fresh conversation started** (automatic session separation — no planning context pollution)
- Plan read from feature branch
- Implementation completed (new tool in `tools/brave_search/`)
- Validation gates passed (tests, linting, type checking)
- PR created: "feat: add brave web search tool"

#### Step 6: Handle Real Failure

The initial implementation had an **import error** discovered during local testing (not caught by code review or linting). This is a key lesson: validation must include running the actual app.

**Fix iteration:**
```
@remote-agent I ran the app on this PR branch and got this error:
[paste error traceback]
```

Agent fixes the import, pushes the update. Pull locally and re-test.

**Session gotcha**: If the agent confuses the fix request with the previous conversation, use `/reset` to start a clean session on the same branch.

#### Step 7: Code Review

```
@remote-agent /command-invoke code-review
```

Runs in parallel with manual human validation. Posts technical review covering security, performance, and pattern compliance.

#### Step 8: Validate Locally

```bash
gh pr checkout 29       # Pull the PR branch
uv run python main.py   # Run the application
# Test: "search the web for GPT 5.1"
# Verify: Brave search returns results with recent data
```

#### Step 9: Merge PR & System Evolution

Merge via GitHub UI. Optionally, ask the agent to recommend system improvements:

```
@remote-agent What can we change in system (commands, rules, context)
to avoid this import error in future?
```

The agent suggests adding import validation to the structured plan template. Apply the suggestion as a separate PR — evolving the system so future PIV loops don't hit the same issue.

### Key Takeaways from the Walkthrough

1. **Automatic session separation** between plan and execute prevents context pollution
2. **Running the actual app** is critical validation — linting and type-checking aren't sufficient
3. **Iteration is easy** — send errors to the agent on the PR, it fixes and pushes
4. **System evolution applies remotely** — meta-reasoning works the same way over GitHub

---

## 8. Cloud Deployment

### Why Deploy to the Cloud?

Local development (Docker + ngrok) works for testing, but has limitations:
- Only available when your computer is running
- ngrok free tier has connection limits
- Not suitable for team access

Cloud deployment provides 24/7 availability, stable HTTPS via a real domain, and team access — for approximately $14/month.

### Platform Recommendations

| Provider | Cost | Notes |
|----------|------|-------|
| **DigitalOcean** | ~$14/month | Recommended; Docker marketplace image available |
| Hetzner | ~$5-10/month | Budget option; manual Docker install |
| Hostinger | Varies | VPS options available |
| AWS/GCP/Azure | Varies | Overkill for this use case |

Instance sizing: **2GB RAM, 1 CPU** is sufficient. The system orchestrates coding assistants — it doesn't run LLMs itself.

### Deployment Steps (Condensed)

**1. Create droplet**: DigitalOcean → Create Droplet → Docker on Ubuntu 22.04 (marketplace image) → 2GB/1CPU → Add SSH key

**2. SSH key setup:**
```bash
ssh-keygen -t ed25519 -C "remote-coding-agent"
# Add public key to droplet during creation
ssh root@<droplet-ip> -i ~/.ssh/remote-coding-agent
```

**3. Security hardening:**
```bash
# Create deploy user
adduser deploy
usermod -aG sudo deploy

# Copy SSH keys to deploy user
mkdir -p /home/deploy/.ssh
cp ~/.ssh/authorized_keys /home/deploy/.ssh/
chown -R deploy:deploy /home/deploy/.ssh

# Disable password auth (edit /etc/ssh/sshd_config)
# PasswordAuthentication no
# Optional: disable root login
systemctl restart sshd

# CRITICAL: Test deploy user in a SEPARATE terminal before disconnecting root

# Firewall
ufw allow 22    # SSH
ufw allow 80    # HTTP (Caddy redirect)
ufw allow 443   # HTTPS
ufw enable
```

**4. DNS setup (do EARLY — propagation takes time):**
- Create an A record: `remote-agent.yourdomain.com` → `<droplet-ip>`
- Wait for DNS propagation before Caddy SSL step

**5. Docker group + clone:**
```bash
usermod -aG docker deploy   # Add deploy user to docker group
# Reconnect as deploy user
git clone https://github.com/dynamous-community/remote-coding-agent
# Copy .env from local, update DATABASE_URL if using remote Postgres
```

**6. Caddy SSL setup:**
```bash
cp Caddyfile.example Caddyfile
# Edit: replace domain with your subdomain
# Caddyfile content:
# remote-agent.yourdomain.com {
#     reverse_proxy app:3000
# }
```

**7. Launch:**
```bash
docker compose -f docker-compose.yml -f docker-compose.cloud.yml up -d --build
```

**8. Smoke test:**
- Telegram: `/clone` a repo → test a command
- GitHub: Check webhook ping (200 OK) → comment on an issue

### Common Gotchas

- **Cannot run two Telegram bot instances** with the same token simultaneously (one local, one cloud). Stop local before starting cloud
- **GitHub webhook URL** must be updated from ngrok to your domain when moving to cloud
- **Container restart** needed after `.env` changes: `docker compose down && docker compose up -d`
- **Logs**: `docker compose logs -f app` to debug issues

---

## 9. Lessons Learned & Best Practices

### Patterns (DO)

| Pattern | Why |
|---------|-----|
| Use orchestrator for ALL communication | Platforms and assistants stay decoupled; adding either is 1 integration |
| Auto-inject platform context at first AI call | Context reaches the right place (not wasted on system commands) |
| Store sessions in Postgres | Enables persistence, concurrency, and conversation history |
| Separate planning from execution automatically | Prevents context pollution; fresh session for implementation |
| Use environment variables for all config | Same `.env` works locally and in cloud; easy to switch assistants/platforms |
| Make commands Git-native for remote workflows | Auto-push, auto-PR — agent handles Git operations end-to-end |
| Validate by running the actual app | Linting and type-checking miss runtime errors (import bugs, config issues) |

### Anti-Patterns (DON'T)

| Anti-Pattern | Why It Fails |
|--------------|--------------|
| Create M×N direct integrations | Adding 1 platform requires integrating with ALL assistants |
| Stream everything to GitHub | GitHub is not a chat app — floods issues with tool call comments |
| Inject context before first AI call | Context sent to `/load-commands` or `/reset` goes nowhere |
| Run two instances with same bot token | Telegram rejects duplicate connections; only one instance works |
| Forget session separation | Planning context pollutes execution; causes confusion and bugs |
| Use HTTP for GitHub webhooks | GitHub requires HTTPS; plain HTTP payloads are rejected |
| Implement entire PRD in one PIV loop | Break into incremental loops — same principle as local development |

### PRD Quality Compounds

The experience building this system reinforces the Planning Methodology guide's lesson: thorough upfront planning (PRD) made the entire build "10-20-30x faster." The final architecture mapped almost exactly to the PRD with minimal changes. This is the strongest evidence for the PIV Loop methodology — a complex, multi-platform application built incrementally from a well-crafted plan.

---

## 10. Cross-System Integration

### How Every Preceding Concept Applies Remotely

| Guide | Concept | Remote Application |
|-------|---------|-------------------|
| **System Foundations + PIV Loop Practice** | PIV Loop | Runs remotely via GitHub Issues — create issue, plan, execute, validate, merge |
| **Global Rules Optimization** | Layer 1 context | PRD + CLAUDE.md + on-demand context all created for the remote project itself |
| **Command Design Framework** | Slash commands | Work via `/load-commands` + `/command-invoke`; auto-detect assistant type |
| **Planning Methodology** | 6-phase planning | Runs remotely, plan saved to feature branch and pushed |
| **Implementation Discipline** | Execution discipline | Execute in fresh session (automatic separation), reads plan from branch |
| **Validation Discipline** | Validation | Code review, execution report, system review — all work remotely via commands |
| **GitHub Orchestration** | GitHub Actions | **Comparison**: Actions = single-shot triggers; Remote System = real-time conversation |

### GitHub Actions vs Remote System

| Aspect | GitHub Actions (GitHub Orchestration guide) | Remote System (this guide) |
|--------|--------------------------|--------------------------|
| **Execution model** | Single-shot (one prompt, one response) | Conversational (multi-turn, real-time) |
| **Visibility** | Check Action logs | Real-time streaming (Telegram) or summary (GitHub) |
| **Session persistence** | None (fresh each run) | Survives restarts, resumable |
| **Cost** | Free (GitHub-hosted runners) | ~$14/month (self-hosted) |
| **Iteration** | Re-trigger the entire workflow | Send follow-up message in same session |
| **Best for** | Simple, well-defined triggers | Complex workflows needing conversation |

Both are valid approaches. Use GitHub Actions for simple triggers (label-based routing, single-shot fixes). Use the Remote System for complex workflows where mid-task conversation, iteration, and session persistence matter.

### Trust Progression (Complete)

```
Manual → Commands → Chained → GitHub Actions → Remote System
  |  trust & verify  |  trust & verify  |  trust & verify  |  trust & verify  |
```

The Remote System is the final level: full PIV Loop with real-time conversation, multi-platform support, persistent sessions, and automatic session separation. Only move here when GitHub Actions workflows are proven reliable.

---

## 11. Practical Exercises

### Exercise 1: Local Setup

**Challenge**: Get the Remote Agentic Coding System running locally with Telegram.

**Steps**:
1. Clone the repo: `git clone https://github.com/dynamous-community/remote-coding-agent`
2. Install prerequisites: Docker, Telegram app
3. Create a Telegram bot via @BotFather
4. Configure `.env` with database, Claude Code token (`claude setup-token`), and Telegram bot token
5. Run: `docker compose up --build -d`
6. In Telegram: `/help` → `/clone <your-repo-url>` → `/load-commands .claude/commands` → `/commands`

**Success criteria**: You can invoke `/command-invoke prime` and see real-time streaming output in Telegram.

### Exercise 2: Remote PIV Loop

**Challenge**: Run a complete PIV Loop remotely via GitHub.

**Steps**:
1. Configure GitHub webhook (ngrok + webhook secret + event subscriptions)
2. Create a GitHub Issue describing a small feature
3. Comment: `@remote-agent /load-commands .claude/commands`
4. Comment: `@remote-agent /command-invoke prime`
5. Comment: `@remote-agent /command-invoke plan-feature "<description>"`
6. Review the plan on the feature branch
7. Comment: `@remote-agent /command-invoke execute` (with branch and plan path)
8. Pull locally, test manually
9. Merge the PR

**Success criteria**: Feature implemented via GitHub comments alone (except local validation). PR merged successfully.

### Exercise 3: Cloud Deployment (Optional)

**Challenge**: Deploy to a cloud provider and verify both Telegram and GitHub access.

**Steps**:
1. Create a DigitalOcean droplet (Docker on Ubuntu 22.04, 2GB RAM)
2. Apply security hardening (deploy user, SSH keys, firewall)
3. Set up DNS A record for your subdomain
4. Configure Caddy for automatic SSL
5. Run `docker compose -f docker-compose.yml -f docker-compose.cloud.yml up -d --build`
6. Update GitHub webhook URL from ngrok to your domain
7. Test: Telegram clone + command, GitHub webhook ping + issue comment

**Success criteria**: Both Telegram and GitHub work against the cloud instance. System is accessible from your phone.

---

## FAQ: Common Remote System Questions

### "Do I need to deploy to the cloud?"

**Short answer**: No — local works for learning and development. **Long answer**: Cloud deployment gives you 24/7 availability, stable HTTPS without ngrok, and team access. But you can learn the entire system locally with Docker + ngrok. Only deploy to cloud when you want persistent availability or need to share the agent with team members.

### "Can I use this with Cursor/Windsurf/other coding tools?"

**Short answer**: Not directly — each tool needs an `IAssistantClient` implementation. **Long answer**: The orchestrator architecture is designed for exactly this extensibility. Adding a new coding assistant means implementing 4 methods (`startSession`, `resumeSession`, `sendMessage`, `endSession`). The effort is roughly one PIV loop. However, the assistant must support programmatic access (CLI or API) — GUI-only tools can't be integrated.

### "How is this different from GitHub Actions?"

**Short answer**: Actions are single-shot; the Remote System is conversational. **Long answer**: GitHub Actions execute one prompt and return one result — no iteration, no follow-up, no mid-task conversation. The Remote System maintains persistent sessions where you can send follow-up messages, iterate on errors, and run multi-step workflows with real-time visibility. Actions are free and simpler; the Remote System is more powerful but costs ~$14/month to host.

### "What does it cost to run?"

**Short answer**: Free locally; ~$14/month in the cloud. **Long answer**: Local development uses Docker on your machine (free) + ngrok free tier. Cloud deployment costs ~$14/month for a minimal DigitalOcean droplet (2GB RAM, 1 CPU). The system itself doesn't run LLMs — it orchestrates Claude Code or Codex, which use their own subscription credits. Total cost is hosting + your existing coding assistant subscription.

### "Can multiple team members use the same instance?"

**Short answer**: Yes — concurrent sessions are fully supported. **Long answer**: The system stores sessions in Postgres with proper isolation. Different team members can work on different issues simultaneously (e.g., one on Telegram, another via GitHub comments). Each gets their own session and conversation history. The only constraint is Telegram bot tokens — one token = one bot = one Telegram integration point (but multiple users can message the same bot).

### "Do my local slash commands work remotely?"

**Short answer**: Yes, via `/load-commands` + `/command-invoke`. **Long answer**: After cloning your repo in the remote system, run `/load-commands .claude/commands` to load all your slash commands. Then invoke them with `/command-invoke <name> <args>`. The system detects `.claude/` vs `.codex/` folders to pick the right coding assistant. Commands follow the same INPUT→PROCESS→OUTPUT framework — the only adaptation is that plans save to `.agents/plans/` (GitHub convention) instead of `requests/` (local convention).

---

## Next Steps

1. Read `reference/remote-system-overview.md` for the architecture overview
2. Clone the [remote-coding-agent repo](https://github.com/dynamous-community/remote-coding-agent) and explore the codebase
3. Try Exercise 1 — local setup with Telegram for interactive development
4. Try Exercise 2 — full remote PIV Loop via GitHub Issues
5. Read `reference/implementation-discipline.md` for execution discipline that feeds remote workflows
6. Read `reference/validation-discipline.md` for validation discipline critical to remote quality
7. Move to the MCP Skills & Archon guide (`reference/mcp-skills-archon.md`) to learn about Archon integration

---

## Related Resources

- **Remote system overview**: `reference/remote-system-overview.md` — on-demand architecture summary
- **GitHub integration**: `reference/github-integration.md` — GitHub Actions (GitHub Orchestration guide, prerequisite concepts)
- **Execute command**: `.claude/commands/execute.md` — used remotely via `/command-invoke`
- **Implementation Discipline guide**: `reference/implementation-discipline.md` — execution discipline feeding remote workflows
- **Validation Discipline guide**: `reference/validation-discipline.md` — validation discipline for remote quality
- **GitHub Orchestration guide**: `reference/github-orchestration.md` — GitHub Actions comparison (prerequisite)
- **Remote agent repo**: `https://github.com/dynamous-community/remote-coding-agent`

---

**That's the Remote Agentic System guide!** You now understand:
- The orchestrator architecture (M+N vs M×N) and its two generic interfaces
- How Telegram (real-time streaming) and GitHub (summary comments) integrate as platforms
- Environment setup — database, tokens, Docker, and the two-GitHub-token distinction
- Telegram bot creation via @BotFather and the first-use workflow
- GitHub webhook configuration with ngrok (local) and Caddy (cloud)
- The full remote PIV Loop — from issue creation through PR merge with real failure handling
- Cloud deployment — DigitalOcean, security hardening, DNS, and Caddy SSL
- Patterns and anti-patterns for remote system design
- How every preceding concept converges in the remote system

**Ready for the next step?** Learn how MCP Servers and Cloud Skills extend the PIV Loop with external tool access and progressive context loading — see `reference/mcp-skills-archon.md` for Archon integration, curated knowledge bases, and real-time task management.
