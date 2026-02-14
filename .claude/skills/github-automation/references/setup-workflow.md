# Setup Workflow — Step-by-Step GitHub Automation

> This reference is loaded on-demand during skill execution (Tier 3).

For the quick-start checklist, also see `templates/GITHUB-SETUP-CHECKLIST.md`.

---

## Step 1: Install CodeRabbit

1. Go to [GitHub Marketplace — CodeRabbit](https://github.com/marketplace/coderabbit-ai)
2. Install on your repository (free tier available)
3. CodeRabbit automatically reviews every PR — no YAML workflow needed

**Verification**: Create a test PR and check for CodeRabbit review comments.

---

## Step 2: Generate Claude Code OAuth Token

```bash
claude setup-token
```

This outputs an OAuth token (starts with `sk-ant-`). Store it securely — it's used as a GitHub secret.

**Alternative**: Extract from auth file:
```bash
jq -r '.oauth_token' ~/.claude/auth.json
```

**If not authenticated**: Run `claude login` first.

---

## Step 3: Add Secrets to GitHub

```bash
# Claude Code token (required)
echo "$CLAUDE_TOKEN" | gh secret set CLAUDE_CODE_OAUTH_TOKEN -R owner/repo

# Verify
gh secret list -R owner/repo
```

**For Codex** (if using both):
```bash
echo "$ID_TOKEN" | gh secret set CODEX_ID_TOKEN -R owner/repo
echo "$ACCESS_TOKEN" | gh secret set CODEX_ACCESS_TOKEN -R owner/repo
echo "$REFRESH_TOKEN" | gh secret set CODEX_REFRESH_TOKEN -R owner/repo
echo "$ACCOUNT_ID" | gh secret set CODEX_ACCOUNT_ID -R owner/repo
```

---

## Step 4: Enable PR Creation Permissions

GitHub Actions needs permission to create PRs and push commits.

### Repository Level
1. Go to: `https://github.com/{owner}/{repo}/settings/actions`
2. Under "Workflow permissions", select "Read and write permissions"
3. Check "Allow GitHub Actions to create and approve pull requests"
4. Save

### Organization Level (if applicable)
1. Go to: `https://github.com/organizations/{org}/settings/actions`
2. Same settings as repository level

---

## Step 5: Add Workflow YAML Files

Copy the appropriate workflow to `.github/workflows/`:

### Claude Code Only (Recommended Start)
Copy from `reference/github-workflows/claude-fix.yml` or `.github/workflows/claude-fix.yml`

### Claude Code + CodeRabbit Auto-Fix
Copy from `reference/github-workflows/claude-fix-coderabbit.yml`

**Key workflow triggers**:
- `issues.labeled` — When an issue gets a trigger label (e.g., `claude-fix`, `claude-create`)
- `issue_comment.created` — When someone comments `@claude-fix` on a PR

---

## Step 6: Add Prompt Templates

Copy prompt templates to `.github/workflows/prompts/`:

| Template | Purpose |
|----------|---------|
| `prime-github.md` | Load context in GitHub Actions environment |
| `end-to-end-feature-github.md` | Full PIV Loop for enhancement issues |
| `bug-fix-github.md` | RCA + fix for bug issues |
| `rca-github.md` | Root cause analysis |
| `implement-fix-github.md` | Implement fix from RCA |

These are GitHub-adapted versions of local commands with extra INPUT variables (`$REPOSITORY`, `$ISSUE_NUMBER`, `$BRANCH_NAME`).

---

## Step 7: Add CodeRabbit Configuration

Create `.coderabbit.yaml` in project root:

```yaml
reviews:
  auto_review:
    enabled: true
  path_filters:
    - "!**/*.md"  # Skip markdown files
```

For the full template, copy the `.coderabbit.yaml` from the project root.

---

## Step 8: Configure Label-Based Routing

Create issue labels that determine which workflow runs:

| Label | Workflow | Agent Action |
|-------|----------|-------------|
| `claude-fix` | claude-fix.yml | Analyze issue, create fix PR |
| `claude-create` | claude-fix.yml | Plan and implement feature |
| `bug` | claude-fix.yml | RCA + bug fix |
| `enhancement` | claude-fix.yml | End-to-end feature |

Label routing is configured in the workflow YAML's `if` conditions.

---

## Step 9: Configure Authorized Users

In the workflow YAML, set which users can trigger the AI agent:

```yaml
env:
  AUTHORIZED_USERS: "username1,username2"
```

Only comments from authorized users will trigger the agent. This prevents unauthorized usage and cost spikes.

---

## Step 10: Test the Setup

```bash
# Create a test issue
gh issue create --title "test: verify automation" --body "This tests the AI workflow" --label "claude-fix"

# Watch the workflow run
gh run list --workflow=claude-fix.yml

# Check the run status
gh run view {run-id}
```

**Expected result**: Claude Code picks up the issue, creates a branch, implements a fix, and opens a PR.

---

## Iteration Limits

Configure `MAX_ITERATIONS` in the workflow to control how many fix cycles the agent runs:

```yaml
env:
  MAX_ITERATIONS: "3"  # Agent tries up to 3 times to pass validation
```

Higher values increase thoroughness but also cost. Start with 3 and adjust based on results.
