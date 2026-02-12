```
CLAUDE.md                              # Layer 1: Global rules (slim, @references)
README.md                              # Public-facing project README with PIV Loop diagrams
memory.md                              # Cross-session memory (optional, from MEMORY-TEMPLATE.md)
.coderabbit.yaml                       # CodeRabbit config template (copy to project root)
sections/                              # Auto-loaded rule sections (every session)
  01_core_principles.md                #   YAGNI, KISS, DRY, Limit AI Assumptions, ABP
  02_piv_loop.md                       #   Plan, Implement, Validate methodology (slim)
  03_context_engineering.md            #   4 Pillars: Memory, RAG, Prompts, Tasks
  04_git_save_points.md                #   Commit plans before implementing
  05_decision_framework.md             #   When to proceed vs ask
  15_archon_workflow.md                #   Archon integration pointer (slim — loads reference/archon-workflow.md)
reference/                             # On-demand guides (loaded when needed)
  archon-workflow.md                   #   Archon task management & RAG workflow (moved from sections/)
  layer1-guide.md                      #   How to build CLAUDE.md for real projects
  validation-strategy.md               #   5-level validation pyramid, linting, tests
  file-structure.md                    #   This file — project directory layout
  command-design-overview.md           #   Slash commands & INPUT→PROCESS→OUTPUT
  github-integration.md                #   GitHub Actions, remote agents, orchestration
  remote-system-overview.md            #   Remote Agentic Coding System, orchestrator
  mcp-skills-overview.md               #   MCP protocol, cloud skills, progressive loading
  subagents-overview.md                #   Subagents, parallel execution, context isolation
  git-worktrees-overview.md            #   Git worktrees, parallel implementation
  system-foundations.md                #   System gap, mental models, self-assessment
  piv-loop-practice.md                #   PIV Loop in practice, 4 Pillars, validation
  global-rules-optimization.md        #   Modular CLAUDE.md, Two-Question Framework
  command-design-framework.md          #   Slash commands, INPUT→PROCESS→OUTPUT (deep dive)
  planning-methodology-guide.md        #   6-phase planning, PRD, Vertical Slice
  implementation-discipline.md         #   Execute command, meta-reasoning, save states
  validation-discipline.md             #   5-level pyramid, code review, system review
  github-orchestration.md              #   GitHub Actions, 3 approaches, review-fix loop
  remote-agentic-system.md             #   Remote system, orchestrator, cloud deployment
  mcp-skills-archon.md                 #   MCP servers, Cloud Skills, Archon integration
  subagents-deep-dive.md               #   Subagents, context handoff, agent design framework
  git-worktrees-parallel.md            #   Git worktrees, parallel implementation, vertical slices
  remote-system-guide.md               #   Setup & deployment guide for remote coding agent
  subagents-guide.md                   #   Subagent creation, frontmatter, output patterns
  multi-model-strategy.md              #   When to use Haiku/Sonnet/Opus for cost optimization
  multi-instance-routing.md            #   Route tasks to different Claude accounts (claude1/2/3/zai)
  github-workflows/                    #   Example GitHub Action YAML files
    claude-fix.yml                     #     Claude Code issue fix/create workflow
    claude-fix-coderabbit.yml          #     Claude Code auto-fix from CodeRabbit reviews
    README.md                          #     Workflow setup instructions
.github/workflows/                     # GitHub Action workflows & prompt templates
  claude-fix-coderabbit.yml            #   Review-fix loop workflow (copy to project)
  prompts/                             #   GitHub-adapted prompt templates
    prime-github.md                    #     Prime for GitHub Actions context
    end-to-end-feature-github.md       #     Full PIV Loop for enhancement issues
    bug-fix-github.md                  #     RCA + fix for bug issues
templates/
  PRD-TEMPLATE.md                      # Template for Layer 1 PRD (what to build)
  STRUCTURED-PLAN-TEMPLATE.md          # Template for Layer 2 plans (per feature)
  SUB-PLAN-TEMPLATE.md                 # Individual sub-plan template (150-250 lines, self-contained)
  VIBE-PLANNING-GUIDE.md              # Example prompts for vibe planning
  IMPLEMENTATION-PROMPT.md             # Reusable prompt for implementation phase
  VALIDATION-PROMPT.md                 # Reusable prompt for validation phase
  NEW-PROJECT-CHECKLIST.md             # Step-by-step guide for new projects
  PLAN-OVERVIEW-TEMPLATE.md            # Master file for decomposed plan series (overview + index)
  CREATE-REFERENCE-GUIDE-PROMPT.md     # Prompt to generate on-demand reference guides
  MEMORY-TEMPLATE.md                   # Template for project memory (cross-session context)
  COMMAND-TEMPLATE.md                  # How to design new slash commands
  AGENT-TEMPLATE.md                    # How to design new subagents
  BASELINE-ASSESSMENT-TEMPLATE.md      # Self-assessment for measuring PIV Loop improvement
  GITHUB-SETUP-CHECKLIST.md            # Step-by-step GitHub Actions setup
  META-REASONING-CHECKLIST.md          # 5-step meta-reasoning + WHERE-to-fix framework
  TOOL-DOCSTRING-TEMPLATE.md           # 7-element template for agent tool documentation
  VALIDATION-REPORT-TEMPLATE.md        # Standard format for validation output
requests/
  {feature}-plan.md                    # Layer 2: Feature plans go here
.claude/commands/                      # Slash commands (reusable prompts)
  agents.md                            #   /agents — generate subagent definition files
  init-c.md                            # /init-c — generate CLAUDE.md for a new project
  prime.md                             # /prime — load codebase context
  planning.md                          # /planning — create implementation plan
  execute.md                           # /execute — implement from plan
  commit.md                            # /commit — conventional git commit
  rca.md                               # /rca — root cause analysis (GitHub issues)
  implement-fix.md                     # /implement-fix — fix from RCA document
  end-to-end-feature.md                # /end-to-end-feature — autonomous workflow
  create-prd.md                        # /create-prd — generate PRD from conversation
  code-review.md                       # /code-review — technical code review
  code-review-fix.md                   # /code-review-fix — fix issues from code review
  execution-report.md                  # /execution-report — implementation report
  system-review.md                     # /system-review — divergence analysis
  new-worktree.md                      # /new-worktree — create git worktrees with optional parallel setup
  merge-worktrees.md                   # /merge-worktrees — safely merge feature branches from worktrees
  parallel-e2e.md                      # /parallel-e2e — parallel end-to-end with worktrees
.claude/skills/                        # Cloud Skills (progressive loading)
  planning-methodology/                #   6-phase planning methodology (example skill)
    SKILL.md                           #   Entry point + frontmatter (Tier 1+2)
    references/                        #   Detailed docs (Tier 3, on-demand)
      6-phase-process.md               #     Phase-by-phase methodology
      template-guide.md                #     Template section-filling guide
  worktree-management/                 #   Git worktree parallel workflow
    SKILL.md                           #   Entry point + frontmatter (Tier 1+2)
    references/                        #   Detailed docs (Tier 3, on-demand)
      worktree-workflow.md             #     Setup + merge workflow
      conflict-prevention.md           #     Conflict prevention strategies
  parallel-implementation/             #   Parallel end-to-end pipeline
    SKILL.md                           #   Entry point + frontmatter (Tier 1+2)
    references/                        #   Detailed docs (Tier 3, on-demand)
      parallel-workflow.md             #     Full 8-stage pipeline
      troubleshooting.md              #     Common issues and fixes
  github-automation/                   #   GitHub Actions setup methodology
    SKILL.md                           #   Entry point + frontmatter (Tier 1+2)
    references/                        #   Detailed docs (Tier 3, on-demand)
      setup-workflow.md                #     Step-by-step setup
      workflow-templates.md            #     Template customization
  {skill-name}/                        #   Additional skills follow same structure
    SKILL.md                           #   Entry point + frontmatter (required)
    references/                        #   Detailed docs (loaded on-demand)
    examples/                          #   Example outputs
    scripts/                           #   Executable scripts
.claude/agents/                        # Custom subagents (project-specific, user-created)
  _examples/                           # Example agents (copy and customize)
    research-codebase.md               #   Haiku codebase exploration agent
    research-external.md               #   Sonnet documentation research agent
    code-review-type-safety.md         #   Type safety reviewer (parallel review)
    code-review-security.md            #   Security vulnerability reviewer
    code-review-architecture.md        #   Architecture & patterns reviewer
    code-review-performance.md         #   Performance & optimization reviewer
    README.md                          #   How to use and customize examples
  {agent-name}.md                      # Your custom project-specific agents
```
