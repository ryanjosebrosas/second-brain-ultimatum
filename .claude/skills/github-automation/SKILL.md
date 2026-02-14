---
name: github-automation
description: >-
  GitHub Actions setup and configuration for AI-assisted development workflows.
  Covers CodeRabbit automated reviews, Claude Code issue-triggered workflows,
  review-fix loops, and prompt template adaptation. Use when setting up GitHub
  automation for a new project, configuring CodeRabbit, or creating GitHub
  Action workflows for Claude Code.
allowed-tools: ["Read", "Glob", "Grep", "Bash", "Write", "Edit"]
---

# GitHub Automation — AI-Assisted Development Workflows

This skill provides the methodology for setting up GitHub-based automation that integrates AI code review and AI-powered fixes. It complements the `/setup-github-automation` and `/quick-github-setup` commands — the commands provide execution steps, this skill provides the knowledge framework.

## Two-Part System

GitHub automation consists of two complementary tools:

### CodeRabbit (Automated Reviews)
- **What**: GitHub App that automatically reviews every PR
- **How**: Install from GitHub Marketplace, configure with `.coderabbit.yaml`
- **No YAML workflow needed** — it's a GitHub App, not a GitHub Action
- **Output**: Review comments with specific code suggestions

### Claude Code (Automated Fixes)
- **What**: GitHub Action that implements fixes triggered by issues or comments
- **How**: Workflow YAML in `.github/workflows/`, prompt templates in `.github/workflows/prompts/`
- **Trigger**: Issue labels, PR comments (`@claude-fix`), or CodeRabbit review findings
- **Output**: Commits, PRs, or fixes applied directly to branches

## Three Approaches

| Approach | Review | Fix | Best For |
|----------|--------|-----|----------|
| **Hybrid** | CodeRabbit reviews | Claude Code fixes | Most projects (recommended) |
| **Autonomous** | CodeRabbit reviews | Auto-fix without human approval | Trusted, well-tested projects |
| **Deterministic** | CodeRabbit reviews | Human-triggered fixes only | High-stakes or regulated code |

## Prerequisites

- GitHub repository (public or private)
- CodeRabbit installed from GitHub Marketplace
- Claude Code OAuth token (`claude setup-token`)
- GitHub CLI (`gh`) for secret management
- PR creation permissions enabled in repo settings

## Quick Start

1. Install CodeRabbit from GitHub Marketplace
2. Generate Claude Code token: `claude setup-token`
3. Add secret: `gh secret set CLAUDE_CODE_OAUTH_TOKEN`
4. Copy workflow YAML to `.github/workflows/`
5. Copy prompt templates to `.github/workflows/prompts/`
6. Add `.coderabbit.yaml` to project root
7. Test with a sample issue

For step-by-step instructions: `/setup-github-automation` or `/quick-github-setup`

## Detailed References (Tier 3 — Load When Setting Up Automation)

For step-by-step setup process:
@references/setup-workflow.md

For template customization and configuration:
@references/workflow-templates.md

## Related Commands

- `/setup-github-automation [claude|codex|both]` — Full interactive setup with testing
- `/quick-github-setup` — Rapid setup using existing scripts
- `reference/github-integration.md` — On-demand guide for GitHub Actions overview
- `reference/github-orchestration.md` — Deep-dive on orchestration patterns
