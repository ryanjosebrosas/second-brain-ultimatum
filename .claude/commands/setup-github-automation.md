---
description: Automatically setup GitHub Actions workflows and secrets for Claude Code and/or Codex
argument-hint: [claude|codex|both]
---

# Setup GitHub Automation

**Agent Selection**: $ARGUMENTS (default: both)

This command automatically configures GitHub Actions workflows and secrets for AI-powered code review and fixes.

---

## INPUT

**Required Information:**
1. Current GitHub repository (from git remote)
2. Available authentication credentials:
   - Claude Code: `~/.claude/auth.json` or output from `claude setup-token`
   - Codex: `~/.codex/auth.json`
3. Which agent(s) to set up: claude, codex, or both

**Gather context:**
```bash
# Get repository
REPO=$(gh repo view --json nameWithOwner -q '.nameWithOwner')

# Check which auth files exist
CLAUDE_AUTH_EXISTS=$([ -f ~/.claude/auth.json ] && echo "true" || echo "false")
CODEX_AUTH_EXISTS=$([ -f ~/.codex/auth.json ] && echo "true" || echo "false")
```

---

## PROCESS

### Step 1: Determine What to Set Up

Based on `$ARGUMENTS`:
- `claude` → Set up only Claude Code
- `codex` → Set up only Codex
- `both` or empty → Set up both (if credentials available)

Check availability:
```bash
if [ "$AGENT_CHOICE" == "claude" ] || [ "$AGENT_CHOICE" == "both" ]; then
  if [ "$CLAUDE_AUTH_EXISTS" == "false" ]; then
    echo "⚠️  Claude Code not authenticated. Run: claude login"
    # Prompt user to authenticate first
  fi
fi

if [ "$AGENT_CHOICE" == "codex" ] || [ "$AGENT_CHOICE" == "both" ]; then
  if [ "$CODEX_AUTH_EXISTS" == "false" ]; then
    echo "⚠️  Codex not authenticated. Run: codex login"
    # Prompt user to authenticate first
  fi
fi
```

### Step 2: Setup Claude Code Secrets

If Claude Code selected:

```bash
echo "🔐 Setting up Claude Code secrets..."

# Method 1: Extract from auth.json
if [ -f ~/.claude/auth.json ]; then
  CLAUDE_TOKEN=$(jq -r '.oauth_token' ~/.claude/auth.json 2>/dev/null || grep -o '"oauth_token"[[:space:]]*:[[:space:]]*"[^"]*"' ~/.claude/auth.json | cut -d'"' -f4)
fi

# Method 2: Prompt user to run setup-token
if [ -z "$CLAUDE_TOKEN" ]; then
  echo "Running: claude setup-token"
  CLAUDE_TOKEN=$(claude setup-token 2>&1 | grep -o 'sk-ant-[A-Za-z0-9_-]*')
fi

# Add to GitHub
echo "$CLAUDE_TOKEN" | gh secret set CLAUDE_CODE_OAUTH_TOKEN -R "$REPO"
echo "✅ CLAUDE_CODE_OAUTH_TOKEN configured"
```

### Step 3: Setup Codex Secrets

If Codex selected:

```bash
echo "🔐 Setting up Codex secrets..."

# Extract from auth.json
ID_TOKEN=$(jq -r '.tokens.id_token' ~/.codex/auth.json)
ACCESS_TOKEN=$(jq -r '.tokens.access_token' ~/.codex/auth.json)
REFRESH_TOKEN=$(jq -r '.tokens.refresh_token' ~/.codex/auth.json)
ACCOUNT_ID=$(jq -r '.tokens.account_id' ~/.codex/auth.json)

# Add to GitHub
echo "$ID_TOKEN" | gh secret set CODEX_ID_TOKEN -R "$REPO"
echo "$ACCESS_TOKEN" | gh secret set CODEX_ACCESS_TOKEN -R "$REPO"
echo "$REFRESH_TOKEN" | gh secret set CODEX_REFRESH_TOKEN -R "$REPO"
echo "$ACCOUNT_ID" | gh secret set CODEX_ACCOUNT_ID -R "$REPO"

echo "✅ Codex secrets configured (4 tokens)"
```

### Step 4: Copy Workflow Files

Determine which workflow to deploy:

```bash
if [ "$AGENT_CHOICE" == "both" ]; then
  # Use multi-agent workflow
  cp .github/workflows/multi-agent-fix.yml /tmp/workflow.yml
  WORKFLOW_NAME="multi-agent-fix.yml"
  WORKFLOW_DESC="Multi-agent (Claude + Codex)"
elif [ "$AGENT_CHOICE" == "claude" ]; then
  # Use Claude-only workflow
  cp .github/workflows/claude-fix-coderabbit.yml /tmp/workflow.yml
  WORKFLOW_NAME="claude-fix-coderabbit.yml"
  WORKFLOW_DESC="Claude Code only"
elif [ "$AGENT_CHOICE" == "codex" ]; then
  # Use Codex-only workflow (extract from multi-agent)
  # Extract just the codex-fix job
  WORKFLOW_NAME="codex-fix-coderabbit.yml"
  WORKFLOW_DESC="Codex only"
fi

echo "📋 Deploying workflow: $WORKFLOW_DESC"
```

### Step 5: Enable GitHub Actions Permissions

```bash
echo "⚙️  Configuring GitHub Actions permissions..."

# Enable PR creation
gh api -X PATCH "/repos/$REPO" -f allow_auto_merge=true

# This requires manual check - inform user:
echo "⚠️  Manual step required:"
echo "   Go to: https://github.com/$REPO/settings/actions"
echo "   Enable: 'Allow GitHub Actions to create and approve pull requests'"
echo ""
read -p "Press Enter after enabling this setting..."
```

### Step 6: Install CodeRabbit (if not installed)

```bash
echo "🤖 Checking CodeRabbit installation..."

# Check if .coderabbit.yaml exists
if [ ! -f .coderabbit.yaml ]; then
  echo "📝 Creating .coderabbit.yaml configuration..."

  # Copy from template
  # .coderabbit.yaml should already exist in the project root from /init-c setup.
  # If missing, create one manually — see .coderabbit.yaml in My Coding System repo for reference.

  git add .coderabbit.yaml
  git commit -m "chore: add CodeRabbit configuration"

  echo "⚠️  CodeRabbit GitHub App not detected."
  echo "   Install from: https://github.com/marketplace/coderabbit-ai"
  echo "   Select this repository during installation"
  echo ""
  read -p "Press Enter after installing CodeRabbit..."
fi
```

### Step 7: Test the Setup

```bash
echo "🧪 Testing the automation..."

# Create a test branch
git checkout -b test/automated-pr-setup
echo "# Test" > TEST_AUTOMATION.md
git add TEST_AUTOMATION.md
git commit -m "test: verify automated PR creation"
git push -u origin test/automated-pr-setup

# Create a PR
gh pr create --title "test: verify automation setup" --body "This PR tests the automated review-fix loop." --base master

echo ""
echo "✅ Test PR created!"
echo "   CodeRabbit should review it automatically"
echo "   The selected agent(s) will auto-fix any issues"
echo ""
read -p "Press Enter to clean up test PR..."

# Clean up
gh pr close --delete-branch
git checkout master
```

---

## OUTPUT

### Setup Complete Summary

```
✅ GitHub Automation Configured!

**Repository**: {repo-name}

**Secrets Configured:**
{list of secrets based on selection}

**Workflows Deployed:**
- {workflow-name} - {description}

**How to Use:**

1. Create a PR or push to a feature branch
2. CodeRabbit will review automatically
3. Comment on PR:
   - `@claude-fix` → Claude Code applies fixes
   - `@codex-fix` → Codex applies fixes  (if both enabled)
   - Or wait for automatic fix (default agent)

**Next Steps:**
- Push code to any feat/* or fix/* branch
- PRs are auto-created (if post-push hook enabled)
- CodeRabbit reviews all PRs
- AI agents auto-fix issues

**Useful Commands:**
- Check secrets: `gh secret list`
- View workflows: `gh workflow list`
- Check runs: `gh run list --workflow={workflow-name}`
```

---

## VALIDATION

Before completing:
- ✅ Secrets are set in GitHub (verify with `gh secret list`)
- ✅ Workflow file exists in `.github/workflows/`
- ✅ GitHub Actions permissions are enabled
- ✅ CodeRabbit is installed (`.coderabbit.yaml` exists)
- ✅ Test PR was created and reviewed

---

## ERROR HANDLING

**If Claude auth not found:**
```bash
echo "❌ Claude Code authentication not found"
echo ""
echo "Setup Claude Code:"
echo "  1. Run: claude login"
echo "  2. Run: claude setup-token"
echo "  3. Re-run this command"
exit 1
```

**If Codex auth not found:**
```bash
echo "❌ Codex authentication not found"
echo ""
echo "Setup Codex:"
echo "  1. Install: npm install -g @openai/codex-cli"
echo "  2. Run: codex login"
echo "  3. Re-run this command"
exit 1
```

**If gh CLI not available:**
```bash
echo "❌ GitHub CLI not found"
echo ""
echo "Install GitHub CLI:"
echo "  - macOS: brew install gh"
echo "  - Linux: sudo apt install gh"
echo "  - Windows: winget install GitHub.cli"
echo "  - Or download: https://cli.github.com/"
exit 1
```

**If not in a git repository:**
```bash
echo "❌ Not in a git repository"
echo "Run this command from your project root"
exit 1
```

---

## NOTES

- This command must be run from the repository root
- Requires `gh`, `git`, and optionally `jq`
- Internet connection required
- GitHub repository must exist (run `gh repo create` first if needed)
- Secrets are encrypted and secure - only GitHub Actions can access them
- You can run this command multiple times to update secrets or workflows
- To remove automation: delete workflow files and secrets via GitHub Settings
