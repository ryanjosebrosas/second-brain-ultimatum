# GitHub as the AI Orchestration Layer

This guide explains **how GitHub serves as the orchestration layer for AI coding agents** — covering the GitHub Actions anatomy, three integration approaches (Hybrid, Autonomous, Deterministic), prompt template adaptation for remote workflows, the automated review-fix loop with CodeRabbit, and practical exercises — going deeper than the guide at `reference/github-integration.md`.

---

## 1. GitHub Orchestration: Core Concepts

### The Journey from Validation to Remote Orchestration

The System Foundations guide established the **why** — the system gap and learning architecture. The PIV Loop Practice guide taught the **how** — the PIV Loop in practice. The Global Rules Optimization guide taught **how to build** — modular CLAUDE.md and strategic context loading. The Command Design Framework guide taught **how to automate** — slash commands and the INPUT→PROCESS→OUTPUT framework. The Planning Methodology guide taught **how to plan** — the 6-phase planning methodology. The Implementation Discipline guide taught **execution discipline** — implementing from plans and evolving the system through meta-reasoning. The Validation Discipline guide taught **validation discipline** — the 5-level pyramid, dual review system, and divergence analysis. This guide teaches **remote orchestration** — how to run your entire PIV Loop through GitHub, with AI agents triggered by issues and PRs.

This is the **only tool-specific section** in the template. GitHub isn't just another tool — it's the infrastructure layer that coordinates tasks, tracks changes, and assigns work to AI agents. No matter how powerful coding agents become, you'll always need this orchestration layer.

### What You'll Learn

- **The orchestration layer concept** — why AI coding will never be a single "magic box"
- **GitHub Actions fundamentals** — workflow anatomy, triggers, setup requirements
- **Three integration approaches** — Hybrid, Autonomous, Deterministic with configuration flags
- **Prompt template adaptation** — transforming local commands into GitHub-compatible templates
- **The automated review-fix loop** — CodeRabbit + Claude Code for hands-off PR improvement
- **Label-based routing** — directing issues to different prompt templates automatically
- **Parallel agent execution** — multiple agents reviewing the same PR simultaneously
- **Command integration with PIV Loop** — bug fix, enhancement, and code review workflows
- **Limitations and cost optimization** — 5 constraints with practical workarounds
- **Trust progression to remote automation** — when and how to move workflows to GitHub

### The Core Insight

> **"The future of AI coding isn't a single magic box. It's an orchestration layer coordinating multiple specialized agents, with humans in the validation loop."**

GitHub provides this orchestration layer today. Issues are task assignments. PRs are proposed changes. Actions are the automation engine. The PIV Loop runs remotely with the same methodology you use locally.

---

## 2. The Orchestration Layer Concept

### The "Single Magic Box" Myth

There's a prevalent myth that AI coding will become one chat input where you tell the AI what to build and it gets it right every time. **This will never exist.** No matter how powerful coding agents become, you always need an orchestration layer to:

1. **Manage tasks** for coding agents
2. **Track changes** and version control
3. **Propose and review changes** (Pull Requests)
4. **Assign work** to different agents
5. **Coordinate parallel work** across multiple agents

### Three GitHub Concepts as Orchestration Primitives

| Concept | Orchestration Role | AI Agent Integration |
|---------|-------------------|---------------------|
| **Commits** | Track how code evolved, enable rollback | Agents push commits to feature branches |
| **Issues** | Task management — bugs, enhancements, work items | Agents receive work via issue comments |
| **Pull Requests** | Proposed changes with review gates | Agents create PRs, respond to review feedback |

### Why This Is the Only Tool-Specific Section

Every other section teaches transferable methodology (PIV Loop, planning, validation). This guide focuses on GitHub specifically because it serves as **infrastructure**, not just a tool. GitHub doesn't compete with your coding assistant — it coordinates them. The orchestration layer concept transfers even if you switch from GitHub to GitLab or another platform; the specific integration patterns are GitHub-native.

---

## 3. GitHub Actions Fundamentals

### What GitHub Actions Are

GitHub Actions are **serverless jobs triggered by repository events**. Key benefits: completely free (with usage limits), infinite auto-scaling, zero infrastructure to manage, and version-controlled (workflows live in `.github/workflows/`).

### Workflow Anatomy

Every issue-triggered workflow follows this 7-component structure:

| # | Component | Purpose | Example |
|---|-----------|---------|---------|
| 1 | **Trigger** (`on:`) | When to run | `issue_comment`, `pull_request_review`, `push` |
| 2 | **Permissions** | User authorization check | Whitelist of allowed GitHub usernames |
| 3 | **Checkout** | Get codebase into runner | `actions/checkout@v3` |
| 4 | **Load instructions** | Read prompt template | `cat .github/workflows/prompts/bug-fix.md` |
| 5 | **Variable substitution** | Inject GitHub context | Replace `$REPOSITORY`, `$ISSUE_NUMBER`, etc. |
| 6 | **Invoke assistant** | Execute coding agent | `anthropics/claude-code-action@v1` |
| 7 | **Post-processing** | Create PR, comment on issue | `gh pr create`, `gh issue comment` |

### Essential Workflow Structure

```yaml
name: AI Fix
on:
  issue_comment:
    types: [created]
jobs:
  fix:
    if: startsWith(github.event.comment.body, '@claude-fix')
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Load instructions
        run: |
          INSTRUCTIONS=$(cat .github/workflows/prompts/bug-fix-github.md)
          INSTRUCTIONS="${INSTRUCTIONS//\$REPOSITORY/${{ github.repository }}}"
          echo "INSTRUCTIONS<<EOF" >> $GITHUB_ENV
          echo "$INSTRUCTIONS" >> $GITHUB_ENV
          echo "EOF" >> $GITHUB_ENV
      - uses: anthropics/claude-code-action@v1
        with:
          claude_token: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
          custom_instructions: ${{ env.INSTRUCTIONS }}
```

### Setup Requirements

**Secrets** (Settings → Secrets and variables → Actions):

| Secret | Source | Notes |
|--------|--------|-------|
| `CLAUDE_CODE_OAUTH_TOKEN` | `claude setup-token` | **(Recommended)** 1-year OAuth token, uses your MAX/Pro subscription |
| `CURSOR_API_KEY` | Cursor dashboard → Integrations | Optional, for Cursor approach |
| `OPENAI_API_KEY` | platform.openai.com/api-keys | Optional, for Codex approach |
| `GITHUB_TOKEN` | Auto-provided | No setup needed |

**Permissions**: Settings → Actions → General → "Allow GitHub Actions to create and approve pull requests" (repo level + org level if applicable).

**Workflow files**: Push `.github/workflows/*.yml` to your repository — GitHub automatically discovers and activates them.

---

## 4. Three Integration Approaches

### Comparison

| Aspect | Hybrid (Claude Code) | Autonomous (Cursor) | Deterministic (Codex) |
|--------|---------------------|--------------------|-----------------------|
| **Agent does** | Branch, implement, post comment | Everything: branch, fix, PR, comment | Only writes code |
| **Workflow does** | Trigger, permissions | Trigger, permissions | Branch, PR, comments, all Git ops |
| **Human in loop** | Click "Create PR" button | Review PR before merge | Review PR before merge |
| **Trust level** | Medium (recommended start) | High (proven system) | Maximum control |

### Configuration Flags

These flags in prompt templates control agent vs workflow responsibility:

| Flag | Hybrid | Autonomous | Deterministic |
|------|--------|------------|---------------|
| `$CREATE_BRANCH` | `true` | `true` | `false` |
| `$CREATE_PR` | `false` | `true` | `false` |
| `$COMMENT_ON_ISSUE` | `true` | `true` | `false` |

### Hybrid (Claude Code Pattern)

Agent is autonomous until PR creation. The workflow:
1. User comments `@claude-fix` or `@claude-create` on an issue
2. Agent creates branch, implements fix, runs validation
3. Agent posts a comment with a **"Create PR" button** for human approval
4. Human clicks button to create the PR, then reviews before merge

Best starting point — you verify the agent's work before it becomes a formal PR. Enables iteration in issue comments before any PR exists.

### Autonomous (Cursor Pattern)

Agent handles everything end-to-end. The workflow:
1. User comments `@cursor-fix` or `@cursor-create` on an issue
2. Agent creates branch, analyzes and implements fix
3. Agent creates pull request and comments on issue
4. **First human touchpoint** is the PR review page

Best when your system is highly trusted after extensive testing. No human interaction until PR review.

### Deterministic (Codex Pattern)

Agent ONLY writes code. Everything else is deterministic. The workflow:
1. User comments `@codex-fix` or `@codex-create` on an issue
2. **Workflow** creates branch (deterministic naming, e.g., `fix/issue-123`)
3. Agent implements the fix (only coding step)
4. **Workflow** creates PR with defined format, comments on issue

Maximum control — the workflow defines exact PR format, commit messages, and branch naming. Agent never touches Git/GitHub operations.

### Progressive Rollout

| Week | Approach | Scope |
|------|----------|-------|
| 1 | Hybrid | Non-critical issues (README updates, small bug fixes) |
| 2 | Autonomous | Trusted issue types (well-labeled, clear scope) |
| 3 | Review automation | Add CodeRabbit review-fix loop |
| 4 | Full PIV Loop | Enhancement issues with full planning + execution |

---

## 5. Prompt Template Adaptation

### Local → GitHub Transformation

Local commands (`.claude/commands/`) become GitHub prompt templates (`.github/workflows/prompts/`) with three adaptations: extra INPUT, configuration flags, and adjusted OUTPUT.

### Extra INPUT — GitHub Context Variables

| Variable | Content | Injected From |
|----------|---------|---------------|
| `$REPOSITORY` | `owner/repo` | `github.repository` |
| `$ISSUE_NUMBER` | Issue being addressed | `github.event.issue.number` |
| `$ISSUE_TITLE` | Title of the issue | `github.event.issue.title` |
| `$ISSUE_BODY` | Full issue description | `github.event.issue.body` |
| `$TRIGGERED_BY` | GitHub username who triggered | `github.actor` |
| `$BRANCH_NAME` | Branch to work on | Computed from issue title |
| `$PR_NUMBER` | Pull request number | `github.event.pull_request.number` |

Variables are injected via bash substitution in the workflow: `INSTRUCTIONS="${INSTRUCTIONS//\$REPOSITORY/${{ github.repository }}}"`.

### Adjusted OUTPUT

| Local Behavior | GitHub Adaptation |
|---------------|-------------------|
| Local commits | Push to remote branch |
| Terminal output | Comment on Issue/PR |
| `requests/` plans | `.agents/plans/` (GitHub convention) |
| Manual review | PR review page |
| Local testing | CI pipeline validation |

### Key Principle

The same INPUT→PROCESS→OUTPUT framework applies. The adaptation is mechanical — inject GitHub context, adjust output targets, add configuration flags. The core logic of each command stays identical.

---

## 6. Command Integration with PIV Loop

### Three GitHub Workflows

| Workflow | Local Commands | GitHub Template | Trigger |
|----------|---------------|-----------------|---------|
| **Bug fix** | `/rca` + `/implement-fix` | `bug-fix-github.md` | `@claude-fix` on issue with `bug` label |
| **Enhancement** | `/end-to-end-feature` | `end-to-end-feature-github.md` | `@claude-create` on issue with `enhancement` label |
| **Code review** | `/code-review` | `code-review-github.md` | `@claude-review` on PR |

**Bug fix workflow** (Prime → RCA → Implement → PR → Comment):
- Combines `/rca` + `/implement-fix` into one template (single-shot execution)
- Agent performs deep investigation first, then implements based on findings
- GitHub context (`$ISSUE_BODY`) replaces the manual issue ID input

**Enhancement workflow** (Prime → Plan → Execute → PR → Comment):
- Full PIV Loop in one run — mirrors `/end-to-end-feature` locally
- Plans saved to `.agents/plans/` instead of `requests/` (GitHub convention)
- Agent creates branch, implements feature, creates PR with plan summary

**Code review workflow** (Fetch PR → Review → Post comment):
- Uses `gh pr view` to get PR diffs and summary before review
- Invokes assistant with PR context for focused, diff-scoped review
- Posts review as PR comment (not a formal GitHub review approval)

### Label-Based Routing

```yaml
- name: Determine prompt template
  run: |
    LABELS=$(gh issue view ${{ env.ISSUE_NUMBER }} --json labels -q '.labels[].name')
    if echo "$LABELS" | grep -q "enhancement\|feature"; then
      TEMPLATE=".github/workflows/prompts/end-to-end-feature-github.md"
    else
      TEMPLATE=".github/workflows/prompts/bug-fix-github.md"
    fi
    echo "TEMPLATE=$TEMPLATE" >> $GITHUB_ENV
```

| Label | Template | Workflow |
|-------|----------|---------|
| `enhancement` or `feature` | `end-to-end-feature-github.md` | Full PIV Loop |
| `bug` | `bug-fix-github.md` | RCA + implement fix |
| No label | `bug-fix-github.md` | Default to bug fix |

### Prompt Template File Mapping

| Local Command | GitHub Template | Location |
|--------------|-----------------|----------|
| `/prime` | `prime-github.md` | `.github/workflows/prompts/` |
| `/end-to-end-feature` | `end-to-end-feature-github.md` | `.github/workflows/prompts/` |
| `/rca` + `/implement-fix` | `bug-fix-github.md` | `.github/workflows/prompts/` |
| `/code-review` | `code-review-github.md` | `.github/workflows/prompts/` |

All templates live in `.github/workflows/prompts/` — NOT in `.claude/commands/`. They're consumed by GitHub Actions workflows, not by local slash commands.

---

## 7. The Automated Review-Fix Loop

### Architecture

Two complementary tools working in a cycle:

| Component | Type | Role | Setup |
|-----------|------|------|-------|
| **CodeRabbit** | GitHub App | Automatically reviews every PR | Install once from GitHub Marketplace |
| **Claude Code** | GitHub Action | Applies CodeRabbit's fixes, pushes back | `claude-fix-coderabbit.yml` workflow |

### The Loop

```
PR created → CodeRabbit reviews → Claude fixes → push → CodeRabbit re-reviews → (repeat)
```

**Iteration control**: `MAX_ITERATIONS` (default 3) prevents infinite cycles. The workflow counts commits prefixed with `[claude-fix]` to track iterations.

**Stopping conditions**: iteration limit reached, CodeRabbit approves (no more issues), or all suggestions applied.

### CodeRabbit Interactive Commands

| Command | Description |
|---------|-------------|
| `@coderabbitai review` | Request a review |
| `@coderabbitai full review` | Force a complete re-review |
| `@coderabbitai summary` | Regenerate PR summary |
| `@coderabbitai resolve` | Mark all comments as resolved |
| `@coderabbitai configuration` | Show current configuration |
| `@coderabbitai help` | List all available commands |

### Setup

1. **Install CodeRabbit** — GitHub Marketplace → CodeRabbit AI → Install on repository
2. **Add `.coderabbit.yaml`** — Copy config from template to repo root
3. **Add workflow** — `claude-fix-coderabbit.yml` to `.github/workflows/`
4. **Configure secrets** — `CLAUDE_CODE_OAUTH_TOKEN` (same as other workflows)

**Free tier note**: Open source repos get full line-by-line reviews on all tiers. Private repos on the free tier (after 14-day Pro trial) only get PR summaries — the automated fix loop requires full reviews (Lite plan or higher).

---

## 8. Advanced Patterns & Best Practices

### Parallel Agent Execution

GitHub's most powerful feature for AI coding: **run multiple agents simultaneously on the same PR**.

```bash
@claude-review     # Claude reviews code
@codex-review      # Codex reviews code
@cursor-review     # Cursor reviews code
```

Each agent gets: separate GitHub Actions runner, separate environment, separate API quota. All execute in parallel and post independent review comments. Use cases: different review perspectives (security, performance, architecture), comparing AI model approaches, and speeding up validation.

### Case Study: Archon Release Automation

**Trigger**: `on: push: tags: ['v*.*.*']` (version tags)

**Pattern**: Deterministic context gathering + AI-generated narrative.

1. Workflow deterministically gathers: commits between tags, changed files, closed PRs, contributors
2. Claude Code generates changelog narrative from structured context
3. Workflow deterministically publishes release with generated changelog

**Key insight**: Separate data gathering (deterministic, reliable) from content generation (AI, creative). This hybrid pattern applies to many automation scenarios.

### Multi-Stage PIV Loops

Chain multiple GitHub Action workflows through events:

1. **Issue created** → Trigger planning workflow → Save plan to branch
2. **Plan approved** (human review) → Trigger execution workflow → Implement from plan
3. **Implementation complete** → Trigger validation workflow → Run tests + code review
4. **Validation passes** → Create PR → Human final review

Each stage is triggered by different events (issue labels, PR comments, manual approval). This mirrors the local PIV Loop but with explicit human gates between stages.

### AI-Enhanced CI

Extend traditional CI (tests, lint, type checks) with AI capabilities:

| Traditional CI | AI Addition |
|---------------|-------------|
| Run unit tests | Generate edge case tests for uncovered paths |
| Lint code | Review for security vulnerabilities |
| Type checking | Validate against architectural patterns |
| Build containers | Generate integration test scenarios |

**Trigger**: `on: push: branches: [main]` or `on: pull_request`

### Best Practices

**Workflow design**: Keep workflows simple (one per trigger pattern), fail fast (check permissions early), add explicit logging (`echo` for key milestones), set timeout limits, make operations idempotent.

**Prompt engineering for GitHub**: Use structured markdown prompts, specify exact output format, include error handling instructions, always provide repository/issue/PR context, show expected output examples.

**Testing strategy**: Test locally first with commands, use a private test repo for workflow testing, add `workflow_dispatch` trigger for manual testing, roll out incrementally (one workflow at a time).

**Maintenance**: Version-control prompt templates like code, document workflows in README, audit Action runs regularly, update GitHub Actions versions, evolve prompts based on failures (meta-reasoning applies here too).

### Common Workflow Patterns

| Pattern | Purpose | Example |
|---------|---------|---------|
| **Permission check** | Whitelist authorized users | `contains(fromJSON('["user1"]'), github.actor)` |
| **Variable substitution** | Inject GitHub context into prompts | `TEMPLATE="${TEMPLATE//\$VAR/${{ env.VAR }}}"` |
| **Conditional output** | Agent or workflow handles output | `if: env.CREATE_PR == 'true'` |
| **Label routing** | Direct to different templates | `gh issue view --json labels` |
| **Output file** | Agent writes file, workflow posts it | `codex "$INSTRUCTIONS" --output review.md` |

These patterns compose — a typical workflow uses permission check + variable substitution + label routing + conditional output together.

---

## 9. Limitations, Security & Cost

### Five Key Limitations

| Limitation | Impact | Workaround |
|-----------|--------|------------|
| **No conversation** | Single-shot execution, can't iterate mid-task | Comment to trigger new run; the Remote Agentic System guide covers the conversational alternative |
| **Limited visibility** | Must check Action logs, no real-time terminal | Add `echo` statements for key milestones |
| **Limited memory.md in CI** | Runners can read memory.md but writes are lost | Commit updates via PR or store in `.github/LEARNINGS.md` |
| **Cost** | GitHub Actions minutes + MAX subscription usage per run | Use deterministic approach, filter triggers, set timeouts |
| **Security** | Exposed secrets, unauthorized triggers | Permission checks, branch protection, secrets management |

### Security Best Practices

| Risk | Mitigation |
|------|-----------|
| Unauthorized workflow triggers | Permission check with user whitelist |
| Exposed API tokens | GitHub Secrets (encrypted, not visible in logs) |
| Agent writing to main branch | Branch protection rules (require PR review) |
| Expensive runaway workflows | Timeout limits on jobs (`timeout-minutes:`) |
| Malicious issue content | Sanitize inputs, don't eval issue body directly |

**Permission check pattern:**
```yaml
jobs:
  fix:
    if: |
      github.event_name == 'issue_comment' &&
      contains(fromJSON('["your-username", "teammate"]'), github.actor)
```

### Cost Breakdown

**GitHub Actions**: Free tier includes 2,000 minutes/month for private repos (unlimited for public). After free tier: $0.008/minute. Concurrent job limits: 20 for free accounts.

**Claude Code usage**: When using `CLAUDE_CODE_OAUTH_TOKEN` (recommended), workflow runs draw from your MAX/Pro subscription — no separate API charges. Subscription usage is shared between claude.ai web and Claude Code (including GitHub Actions runs).

**WARNING**: If you set `ANTHROPIC_API_KEY` as a secret instead of `CLAUDE_CODE_OAUTH_TOKEN`, workflows will bill per-token via API — potentially much more expensive.

**Other assistants**: Cursor and Codex workflows use their respective billing (Cursor subscription or OpenAI API credits). Cost optimization: use the deterministic approach (minimal AI usage), filter triggers carefully (don't run on every comment), and set timeout limits.

### Trust Progression

```
Manual → Commands → Chained → GitHub Actions → Remote System (see Remote Agentic System guide)
  ↑ trust & verify ↑  ↑ trust & verify ↑  ↑ trust & verify ↑  ↑ trust & verify ↑
```

**Before GitHub Actions**: Your chained commands (`/end-to-end-feature`) work reliably. You've run them 10+ times locally. Your plans produce good results. Your execute command implements correctly. Your validation catches issues.

**Start simple**: README updates, small bug fixes. Graduate to larger features as confidence grows. Begin with hybrid approach before autonomous.

---

## 10. Practical Exercises

### Exercise 1: Adapt a Local Command for GitHub

**Challenge**: Take your `/commit` command and create `commit-github.md` — a GitHub-compatible version that creates a commit and pushes to a feature branch.

**Focus**: Identify what changes between local and GitHub: extra INPUT (which branch? which repo?), adjusted PROCESS (push to remote instead of local commit), adjusted OUTPUT (comment on PR with commit details instead of terminal output). Apply the three adaptations from Section 5.

**Expected outcome**: A prompt template in `.github/workflows/prompts/commit-github.md` that accepts `$REPOSITORY`, `$BRANCH_NAME`, and `$PR_NUMBER` variables, creates a conventional commit, pushes to the branch, and posts a summary comment.

### Exercise 2: Design a Label-Based Routing Workflow

**Challenge**: Create a workflow YAML that triggers on `@ai-fix` issue comments, routes to different prompt templates based on labels (`bug` → bug-fix, `enhancement` → full PIV Loop, `docs` → documentation update), and includes permission checks.

**Focus**: Workflow anatomy (Section 3), label routing (Section 6), permission check pattern (Section 9). The workflow should handle all 7 components from the anatomy table.

**Expected outcome**: A `.github/workflows/ai-fix.yml` file with trigger, permission check, label detection, template loading, variable substitution, and agent invocation steps.

---

## FAQ: Common GitHub Orchestration Questions

### "Do I need all three approaches (Hybrid/Autonomous/Deterministic)?"

**Short answer**: No, start with Hybrid.

**Long answer**: Most teams only need one approach. Hybrid is the recommended starting point because it gives the agent autonomy for implementation while keeping PR creation as a human checkpoint. Move to Autonomous only after extensive testing proves reliability. Deterministic is for teams that need maximum control over Git operations — common in regulated industries or large organizations.

### "Can I use this with Cursor or Codex instead of Claude Code?"

**Short answer**: Yes, adapt the invocation step.

**Long answer**: The prompt template adaptation (Section 5) and workflow anatomy (Section 3) apply to any coding assistant. Replace the `anthropics/claude-code-action` step with Cursor CLI invocation or OpenAI Codex action. The INPUT→PROCESS→OUTPUT framework, configuration flags, and label routing all transfer. Only the "Invoke assistant" step changes.

### "How do I debug a failing workflow?"

**Short answer**: Check the Actions tab logs and add `echo` statements.

**Long answer**: Go to your repo's Actions tab → find the failed run → click into the job → expand each step to see output. Add `echo` statements at key points in your workflow (after variable substitution, before agent invocation, after completion). Use `workflow_dispatch` trigger for manual testing. Test with a private repo to avoid polluting your main project.

### "Is CodeRabbit required for the review-fix loop?"

**Short answer**: No, but it's recommended for automated reviews.

**Long answer**: CodeRabbit provides the automated review side of the loop. Without it, you can still trigger Claude Code manually with `@claude-fix` on PRs, but you lose the automatic review → fix → re-review cycle. Alternatives: use GitHub's built-in code review with human reviewers, or configure another review bot. The key value is the **automated cycle**, not CodeRabbit specifically.

### "What about memory.md in CI? How do I get cross-session memory?"

**Short answer**: Partially available — runners can read memory.md but writes are lost.

**Long answer**: GitHub Actions runners can read `memory.md` from the repo (it's a committed file), so past learnings are available during CI runs. However, any writes during the run are lost when the runner terminates. Workaround: the agent can commit memory.md updates as part of a PR, or you can maintain a separate `.github/LEARNINGS.md` for CI-specific context. The key advantage of file-based memory over MCP-based: it's automatically available in any environment that clones the repo.

---

## Next Steps

1. Read this guide (you're doing this now)
2. Study `reference/github-integration.md` for the integration overview
3. Set up GitHub Actions on a test repository — follow `templates/GITHUB-SETUP-CHECKLIST.md`
4. Test the hybrid approach with a simple bug fix issue
5. Add CodeRabbit for automated review-fix loops
6. Move to the Remote Agentic System guide (`reference/remote-agentic-system.md`) — persistent sessions, multi-platform support, and real-time conversation

---

## Related Resources

- `reference/github-integration.md` — on-demand guide to GitHub integration
- `templates/GITHUB-SETUP-CHECKLIST.md` — step-by-step GitHub Actions setup guide
- `reference/github-workflows/` — example workflow YAML files (claude-fix, claude-review)
- `.github/workflows/prompts/` — GitHub-adapted prompt templates (prime, e2e, bug-fix, code-review)
- `.coderabbit.yaml` — CodeRabbit configuration template
- `reference/validation-discipline.md` — prerequisite: validation discipline
- `reference/remote-agentic-system.md` — next: Remote Agentic Coding System

---

**That's the GitHub Orchestration guide!** You now understand:
- The orchestration layer concept — why GitHub is the AI control center
- GitHub Actions fundamentals — workflow anatomy, triggers, setup
- Three integration approaches — Hybrid, Autonomous, Deterministic
- Prompt template adaptation — local commands → GitHub templates
- The automated review-fix loop — CodeRabbit + Claude Code
- Label-based routing — directing issues to the right workflow
- Parallel agent execution — multiple agents on the same PR
- Command integration with PIV Loop — bug fix, enhancement, code review
- Limitations, security, and cost optimization

**Ready for the next step?** Learn about the Remote Agentic Coding System (`reference/remote-agentic-system.md`) — persistent sessions that survive container restarts, real-time conversation (not single-shot), multi-platform support (Telegram, GitHub, Slack), and concurrent sessions for parallel agent execution.
