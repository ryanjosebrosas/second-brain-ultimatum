```
PLAN → IMPLEMENT → VALIDATE → (iterate)
```

### Granularity Principle

Always do **smaller iterations**. Multiple small PIV loops, never try to implement everything at once. Each loop picks ONE feature slice and builds it completely before moving on.

For complex features (High complexity, 15+ tasks, 4+ phases), `/planning` automatically decomposes into multiple sub-plans — each executable in a fresh conversation with minimal context overhead. See `templates/PLAN-OVERVIEW-TEMPLATE.md` for the decomposed plan structure.

### Planning (Layer 1 + Layer 2)

**Layer 1 — Project Planning** (done once, updated rarely):
- **PRD** — defines **what** to build. Use template: `templates/PRD-TEMPLATE.md`
- **CLAUDE.md** — defines **how** to build (tech stack, conventions, patterns)
- **On-demand context** — reference guides, external docs (in `reference/`)

**Layer 2 — Task Planning** (done for every feature):
1. **Vibe Planning** — casual conversation to explore ideas, ask questions, research codebase. See: `templates/VIBE-PLANNING-GUIDE.md`
2. **Structured Plan** — turn conversation into a markdown document
   - Use template: `templates/STRUCTURED-PLAN-TEMPLATE.md`
   - Save to: `requests/{feature}-plan.md`
   - Apply the 4 pillars of Context Engineering

**Do NOT** take your PRD and use it as a structured plan. Break it into granular Layer 2 plans — one per PIV loop.

### Implementation
- Start a **new conversation** (fresh context)
- Feed ONLY the structured plan: `/execute requests/{feature}-plan.md`
- Or use prompt: `templates/IMPLEMENTATION-PROMPT.md` (for non-Claude Code tools)
- Trust but verify: watch loosely, don't micromanage

### Validation
- **AI validates**: unit tests, integration tests, linting
- **Human validates**: code review (git diffs), questions, manual testing
- Use checklist: `templates/VALIDATION-PROMPT.md`
- Small issues: one-off fix prompts
- Major issues: revert to git save point, tweak plan, retry
