### The Orchestration Layer

GitHub is not just version control — it's the **control center** for AI coding agents.

There is a myth that AI coding will become a single "magic box" where you just tell it what to build. In reality, we always need an orchestration layer to:
- **Manage tasks** for coding agents (Issues)
- **Track changes** and version control (Commits)
- **Propose and review changes** (Pull Requests)
- **Assign work** to different agents (GitHub Actions)

GitHub provides all of this. Issues become task assignments, PRs become proposed changes, and Actions become the automation engine that triggers your PIV Loop remotely.

### Automated Review-Fix Loop

The recommended setup uses two complementary tools:

1. **CodeRabbit** (GitHub App) — Automatically reviews every PR. Posts suggestions using GitHub's native suggestion format. Free for open source repos.
2. **Claude Code** (GitHub Action) — Automatically applies CodeRabbit's suggested fixes and pushes them back to the PR branch. This triggers CodeRabbit to re-review.

```
Developer creates PR → CodeRabbit reviews → Claude fixes → CodeRabbit re-reviews → (repeat)
```

The loop runs hands-off while the developer is offline. An iteration cap (`MAX_ITERATIONS`, default 3) prevents infinite cycles. Commit prefix tracking (`[claude-fix]`) counts iterations.

**Key distinction**: CodeRabbit is a GitHub App (install once, no YAML needed for reviews). Claude Code runs via a GitHub Action workflow (`claude-fix-coderabbit.yml`).

### Three Approaches

When integrating AI coding agents into GitHub for issue-triggered work, there are three approaches with different levels of autonomy:

| Approach | Agent Responsibility | Workflow Responsibility | Human in Loop |
|----------|---------------------|------------------------|----------------|
| **Hybrid** | Creates branch, implements fix, posts comment with "Create PR" button | Triggers agent, permissions | Click to create PR |
| **Autonomous** | Everything end-to-end: branch, fix, PR, issue comment | Triggers agent, permissions | Review PR before merge |
| **Deterministic** | Only writes code (the actual fix) | Branch creation, PR creation, issue comments | Review PR before merge |

**Choose based on trust level:**
- **Hybrid** — You trust the agent's code but want to approve PR creation (recommended starting point)
- **Autonomous** — You fully trust the agent to handle everything (use after extensive testing)
- **Deterministic** — You want maximum control; agent only touches code, workflow handles all Git/GitHub operations

### GitHub Actions Anatomy

A GitHub Action workflow (`.github/workflows/*.yml`) defines automated steps triggered by repository events.

**Issue-triggered workflow structure** (`claude-fix.yml`):
1. **Trigger** — `on: issue_comment` (when someone comments `@claude-fix` or `@claude-create`)
2. **Permission check** — Verify the commenter is an authorized user
3. **Checkout repository** — Get the codebase into the runner environment
4. **Load prompt template** — Read the instruction file from `.github/workflows/prompts/`
5. **Variable substitution** — Replace `$REPOSITORY`, `$ISSUE_NUMBER`, `$BRANCH_NAME`, etc.
6. **Invoke Claude Code** — Send instructions via `anthropics/claude-code-action`
7. **Post-processing** — Create PR, comment on issue (if deterministic approach)

**Review-fix workflow structure** (`claude-fix-coderabbit.yml`):
1. **Trigger** — `on: pull_request_review` (when CodeRabbit posts a review) or `on: issue_comment` (`@claude-fix` on PR)
2. **Iteration check** — Count `[claude-fix]` commits, stop if MAX_ITERATIONS reached
3. **Checkout PR branch** — Get the code being reviewed
4. **Invoke Claude Code** — Read CodeRabbit's review comments and apply fixes
5. **Commit and push** — Triggers CodeRabbit to re-review automatically

**Comment-based routing:**
- `@claude-fix` or `@claude-create` on an Issue — triggers the fix/create workflow
- `@claude-fix` on a Pull Request — manually triggers the review-fix workflow
- Issue labels (`enhancement` vs `bug`) determine which prompt template loads

See `reference/github-workflows/` for complete example YAML files.

### Prompt Template Adaptation

Local commands (`.claude/commands/`) become GitHub prompt templates (`.github/workflows/prompts/`) with these adaptations:

**Extra INPUT — GitHub context:**
```
$REPOSITORY — The GitHub repository (owner/repo)
$ISSUE_NUMBER — The issue being addressed
$ISSUE_TITLE — Title of the issue
$ISSUE_BODY — Full description of the issue
$TRIGGERED_BY — GitHub username who triggered the workflow
$BRANCH_NAME — Branch to work on
```

**Configuration flags** (control agent vs workflow responsibility):
```
$CREATE_BRANCH — Should the agent create a branch? (true/false)
$CREATE_PR — Should the agent create the PR? (true/false)
$COMMENT_ON_ISSUE — Should the agent comment on the issue? (true/false)
```

Set these to `true` for hybrid/autonomous approaches, `false` for deterministic (where the workflow handles these steps).

**Adjusted OUTPUT:**
- Instead of local commits, the agent pushes to a branch and creates a PR
- Instead of terminal output, the agent comments on Issues/PRs
- Plans go to `.agents/plans/` (GitHub convention) vs `requests/` (local convention)

See `.github/workflows/prompts/` for the adapted prompt templates.

### Setup Requirements

**1. Install CodeRabbit** — Go to [GitHub Marketplace → CodeRabbit](https://github.com/marketplace/coderabbit-ai) and install the App on your repository. Add `.coderabbit.yaml` to your repo root (copy from template).

**2. Secrets** — Add API credentials to your repo:
- Generate token: `claude setup-token` (creates a long-lived OAuth token, uses your MAX/Pro subscription)
- Add to GitHub: Settings → Secrets and variables → Actions → `CLAUDE_CODE_OAUTH_TOKEN`

**3. Permissions** — Enable PR creation:
- Settings → Actions → General → "Allow GitHub actions to create and approve pull requests"
- For organization repos, enable at the org level too

**4. Label-based routing** — Use issue labels to route to different prompts:
- `enhancement` or `feature` label → loads the full PIV Loop prompt (end-to-end-feature)
- `bug` label (or no label) → loads the bug fix prompt (RCA + implement fix)

See `templates/GITHUB-SETUP-CHECKLIST.md` for the complete step-by-step setup guide.

### CodeRabbit Interactive Commands

You can interact with CodeRabbit directly in PR comments:

| Command | Description |
|---------|-------------|
| `@coderabbitai review` | Request a review |
| `@coderabbitai full review` | Force a complete re-review |
| `@coderabbitai summary` | Regenerate PR summary |
| `@coderabbitai resolve` | Mark all comments as resolved |
| `@coderabbitai configuration` | Show current configuration |
| `@coderabbitai help` | List all available commands |

### Trust Progression (Extended)

```
Manual Prompts → Reusable Commands → Chained Commands → Remote Automation
     ↑ trust & verify ↑    ↑ trust & verify ↑    ↑ trust & verify ↑
```

**Before remote automation**: Your chained commands (`/end-to-end-feature`) work reliably. You've run them 10+ times locally with consistent results. Your structured plan template produces good plans. Your execute command implements them correctly.

**Start with simple tasks**: Use GitHub Actions for straightforward issues first (README updates, small bug fixes). Graduate to larger features as confidence grows.

**Parallel agents**: Once confident, you can trigger multiple agents on the same issue to compare approaches, or assign different issues to different agents simultaneously.

### Limitations

- **No easy conversation**: Each GitHub Action run is a single-shot execution. You can't easily iterate with the agent mid-task. For a custom system that solves this with real-time conversation, multi-platform support, and persistent sessions, see `reference/remote-system-overview.md`.
- **Limited visibility**: You must check Action logs to see what the agent is doing. No real-time terminal output.
- **Limited memory.md in CI**: GitHub Actions runners can read `memory.md` from the repo but any writes are lost when the runner terminates. To persist learnings, the agent can commit memory.md updates via PR.
- **Cost**: Each Action run consumes GitHub Actions minutes and your MAX/Pro subscription usage (or API credits if using `ANTHROPIC_API_KEY`).
- **CodeRabbit free tier**: After the 14-day Pro trial, private repos on the free tier only get PR summaries — not full line-by-line reviews. The automated fix loop requires full reviews (Lite plan or higher for private repos). Open source repos get full reviews on all tiers.

### Reference Files

- **Prompt templates**: `.github/workflows/prompts/` — GitHub-adapted versions of prime, planning+execute, and bug-fix
- **Example workflows**: `reference/github-workflows/` — Ready-to-use YAML files for Claude Code
- **Setup checklist**: `templates/GITHUB-SETUP-CHECKLIST.md` — Step-by-step instructions for adding GitHub Actions and CodeRabbit to your project
