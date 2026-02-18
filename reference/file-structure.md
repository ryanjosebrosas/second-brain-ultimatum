```
CLAUDE.md                              # Layer 1: Global rules (slim, @references sections 01-11)
README.md                              # Public-facing project README with PIV Loop diagrams
memory.md                              # Cross-session memory (optional, from MEMORY-TEMPLATE.md)
sections/                              # Auto-loaded rule sections (every session)
  01_core_principles.md                #   YAGNI, KISS, DRY, Limit AI Assumptions, ABP
  02_piv_loop.md                       #   Plan, Implement, Validate methodology (slim)
  03_context_engineering.md            #   4 Pillars: Memory, RAG, Prompts, Tasks
  04_git_save_points.md                #   Commit plans before implementing
  05_decision_framework.md             #   When to proceed vs ask
  06_tech_stack.md                     #   Backend: Python, Pydantic AI, FastMCP, Supabase, Mem0
  07_architecture.md                   #   Backend: MCP → Agent → Service → Storage layers
  08_code_style.md                     #   Naming, agent pattern, MCP tool pattern, error handling
  09_testing.md                        #   pytest, asyncio, test structure, run commands
  10_common_patterns.md                #   New agent, schema, service method, lazy-import patterns
  11_dev_commands.md                   #   Install, run MCP, CLI, tests, DB migrations
reference/                             # On-demand guides (loaded when needed)
  archon-workflow.md                   #   Archon task management & RAG workflow
  layer1-guide.md                      #   How to build CLAUDE.md for real projects
  file-structure.md                    #   This file — project directory layout
  system-foundations.md                #   System gap, mental models, self-assessment
  piv-loop-practice.md                 #   PIV Loop in practice, 4 Pillars, validation
  global-rules-optimization.md         #   Modular CLAUDE.md, Two-Question Framework
  command-design-framework.md          #   Slash commands, INPUT→PROCESS→OUTPUT
  implementation-discipline.md         #   Execute command, meta-reasoning, save states
  validation-discipline.md             #   5-level pyramid, code review, system review
  subagents-deep-dive.md               #   Subagents, context handoff, agent design framework
templates/
  PRD-TEMPLATE.md                      # Template for Layer 1 PRD (what to build)
  STRUCTURED-PLAN-TEMPLATE.md          # Template for Layer 2 plans (per feature)
  SUB-PLAN-TEMPLATE.md                 # Individual sub-plan template (500-700 lines, self-contained)
  PLAN-OVERVIEW-TEMPLATE.md            # Master file for decomposed plan series (overview + index)
  MEMORY-TEMPLATE.md                   # Template for project memory (cross-session context)
  AGENT-TEMPLATE.md                    # How to design new subagents
requests/
  .gitkeep                             # Preserves directory in git (plans are gitignored)
  {feature}-plan.md                    # Layer 2: Feature plans go here
  system-reviews/                      # System review output directory
.claude/settings.json                  # Hooks configuration (auto-compact memory recovery)
.claude/commands/                      # Slash commands (reusable prompts)
  agents.md                            #   /agents — generate subagent definition files
  init-c.md                            #   /init-c — generate CLAUDE.md for a new project
  prime.md                             #   /prime — load codebase context
  planning.md                          #   /planning — create implementation plan
  execute.md                           #   /execute — implement from plan
  commit.md                            #   /commit — conventional git commit
  rca.md                               #   /rca — root cause analysis (GitHub issues)
  implement-fix.md                     #   /implement-fix — fix from RCA document
  end-to-end-feature.md                #   /end-to-end-feature — autonomous workflow
  create-prd.md                        #   /create-prd — generate PRD from conversation
  code-review.md                       #   /code-review — technical code review
  code-review-fix.md                   #   /code-review-fix — fix issues from code review
  execution-report.md                  #   /execution-report — implementation report
  system-review.md                     #   /system-review — divergence analysis
  create-pr.md                         #   /create-pr — create GitHub PR
.claude/skills/                        # Cloud Skills (progressive loading)
  planning-methodology/                #   6-phase planning methodology
    SKILL.md                           #   Entry point + frontmatter (Tier 1+2)
    references/                        #   Detailed docs (Tier 3, on-demand)
.claude/agents/                        # Custom subagents (active, automatically loaded)
  research-codebase.md                 #   Sonnet codebase exploration agent
  research-external.md                 #   Sonnet documentation research agent
  code-review-type-safety.md           #   Type safety reviewer (parallel review)
  code-review-security.md              #   Security vulnerability reviewer
  code-review-architecture.md          #   Architecture & patterns reviewer
  code-review-performance.md           #   Performance & optimization reviewer
  plan-validator.md                    #   Plan structure validation agent
  test-generator.md                    #   Test case suggestion agent
  specialist-devops.md                 #   DevOps & infrastructure specialist
  specialist-data.md                   #   Database & data pipeline specialist
  specialist-copywriter.md             #   UI copy & UX writing specialist
  specialist-tech-writer.md            #   Technical documentation specialist
  README.md                            #   Agent overview and usage guide

# ── Backend Application ──────────────────────────────────────────────────────

backend/
  pyproject.toml                       # Dependencies + pytest config + build system
  .env                                 # Secrets — gitignored (ANTHROPIC_API_KEY, etc.)
  .env.example                         # Documented env var template
  src/second_brain/
    mcp_server.py                      # Public surface: @server.tool() FastMCP endpoints
    service_mcp.py                     # Service bridge / supplemental routing
    cli.py                             # Click CLI ("brain" command)
    deps.py                            # BrainDeps dataclass + create_deps() factory
    config.py                          # BrainConfig (Pydantic Settings, loads .env)
    schemas.py                         # All Pydantic output models (dependency-free)
    models.py                          # AI model selection logic
    models_sdk.py                      # Claude Agent SDK model support
    auth.py                            # Authentication helpers
    migrate.py                         # Data migration utilities
    __init__.py
    agents/
      recall.py                        # Semantic memory search agent
      ask.py                           # General Q&A with brain context
      learn.py                         # Pattern extraction + memory storage
      create.py                        # Content generation (voice-aware, factory pattern)
      review.py                        # Multi-dimension content scoring
      chief_of_staff.py                # Request routing orchestrator
      coach.py                         # Daily accountability coaching
      pmo.py                           # PMO-style task prioritization
      email_agent.py                   # Email composition
      specialist.py                    # Claude Code / Pydantic AI Q&A
      clarity.py                       # Readability & clarity analysis
      synthesizer.py                   # Feedback consolidation into themes
      template_builder.py              # Template opportunity detection
      utils.py                         # Shared: tool_error(), run_pipeline(), format_*()
      __init__.py
    services/
      memory.py                        # Mem0 semantic memory wrapper
      storage.py                       # Supabase CRUD + ContentTypeRegistry
      embeddings.py                    # Voyage AI / OpenAI embedding generation
      voyage.py                        # Voyage AI reranking service
      graphiti.py                      # Knowledge graph (optional, GRAPHITI_ENABLED)
      health.py                        # Brain metrics, growth milestones, setup status
      retry.py                         # Tenacity retry decorator helpers
      search_result.py                 # Search result data structures
      abstract.py                      # Abstract base classes for pluggable services
      __init__.py
  supabase/migrations/
    001_initial_schema.sql             # Base tables: memory_content, patterns, experiences
    002_examples_knowledge.sql         # examples + knowledge_repo tables
    003_pattern_constraints.sql        # Pattern uniqueness constraints
    004_content_types.sql              # content_types table (builtin + custom types)
    005_growth_tracking_tables.sql     # growth_log, confidence_transitions tables
    006_rls_policies.sql               # Row-level security policies
    007_foreign_keys_indexes.sql       # FK constraints + performance indexes
    008_data_constraints.sql           # Additional data integrity constraints
    009_reinforce_pattern_rpc.sql      # reinforce_pattern() RPC function
    010_vector_search_rpc.sql          # vector_search() RPC function (pgvector)
    011_voyage_dimensions.sql          # Voyage AI embedding dimension config
    012_projects_lifecycle.sql         # projects table + lifecycle stages
    013_quality_trending.sql           # review_history table for quality trending
    014_content_type_instructions.sql  # writing_instructions, validation_rules, ui_config cols
  tests/
    conftest.py                        # Shared fixtures (deps, mocked services, config)
    test_agents.py                     # Agent behavior tests
    test_mcp_server.py                 # MCP tool endpoint tests
    test_schemas.py                    # Pydantic model validation
    test_services.py                   # Service layer tests
    test_service_mcp.py                # Service-MCP bridge tests
    test_models.py / test_models_sdk.py
    test_config.py / test_auth.py / test_deps.py
    test_migrate.py / test_cli.py
    test_graph.py / test_graphiti_service.py / test_voyage.py
    test_projects.py / test_operations.py
    test_agentic.py / test_chief_of_staff.py
    test_content_pipeline.py / test_foundation.py
    __init__.py
  scripts/
    reingest_graph.py                  # Re-sync Graphiti graph from Mem0
    start_mcp.sh                       # Shell script to start MCP server
```
