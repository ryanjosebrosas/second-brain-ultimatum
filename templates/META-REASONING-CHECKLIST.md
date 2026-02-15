# Meta-Reasoning Checklist

> Use this when something goes wrong and you want to fix the **system**, not just the symptom.
> Meta-reasoning asks WHY something happened and WHERE in the system the fix belongs.
>
> **Core Principle**: Always prefer system evolution over one-off fixes.
> One-off fixes solve today; system updates solve forever.

---

## The 5-Step Process

### Step 1: Identify the Problem

State the problem specifically and measurably:
- **What went wrong?** {specific description}
- **How bad is it?** {measurable impact — e.g., "plan is 1700 lines, target was 700-1000"}
- **Is this the first time?** {one-off or recurring pattern}

### Step 2: Ask for Analysis

Use this exact prompt (the "don't make changes yet" instruction is critical):

> "Do some meta reasoning. Don't make any changes yet. Help me understand WHY this happened and how I can adjust the system to avoid this in the future. Look at my commands, rules, and templates."

### Step 3: AI Examines the System

The AI will analyze these locations for root cause:
- Global rules (CLAUDE.md / sections/)
- On-demand context (reference/)
- Commands (.claude/commands/)
- Templates (templates/)
- Vibe planning prompts (your inputs)

### Step 4: You Decide

Review the AI's suggestions and choose which to implement. You may:
- Accept a suggestion as-is
- Modify it (simpler, more general, different scope)
- Reject it (your judgment overrides the AI)
- Combine multiple suggestions

**Do NOT accept all AI suggestions blindly.** Sometimes simpler is better.

### Step 5: Apply System Fix FIRST, Then Fix Immediate Output

1. Fix the system (command, template, rule, or reference guide)
2. Then fix the immediate output using the updated system
3. Verify the system fix would prevent the issue for future runs

---

## WHERE-to-Fix Decision Framework

| Fix Location | When to Use | Example |
|---|---|---|
| **Global rules** (CLAUDE.md/sections) | Convention applies to ALL tasks | "Always use structured logging" |
| **On-demand context** (reference/) | Task-type-specific guidance | Streaming patterns guide |
| **Commands** (planning, execute) | Process/workflow issue | Add plan length constraint |
| **Templates** (structured plan, PRD) | Output format/structure issue | Add new section to plan template |
| **Vibe planning** (your prompts) | Research was incomplete or scope wrong | Ask better research questions |

---

## One-Off Fix vs System Evolution

| Approach | Scope | Outcome |
|----------|-------|---------|
| One-off fix | Fixes immediate output | Same issue recurs next time |
| System evolution | Updates command/template | Issue prevented for all future runs |

---

## Quick Decision Checklist

When deciding where to fix, ask these 5 questions:

1. **Will this happen again?** → If yes, system fix. If truly one-off, patch is fine.
2. **Does it affect all tasks or just this type?** → All tasks: global rules. This type: on-demand context or command.
3. **Is it a process issue or output issue?** → Process: command. Output: template.
4. **Was the research incomplete?** → Yes: improve vibe planning prompts or research phase.
5. **Could a hard constraint prevent it?** → Yes: add the constraint (e.g., line count limits).

---

## Concrete Example: Plan Length

**Problem**: Plan was 1,752 lines (target: 700-1000).

**Meta-reasoning revealed**: No hard constraint on plan length existed in the planning command.

**AI suggestions**: (1) Add hard constraint, (2) reduce task detail, (3) compress research, (4) limit validation detail.

**Human decision**: Accept #1 (add constraint), reject #2 (detailed tasks are valuable).

**System fix**: Added to planning command:
```markdown
CRITICAL CONSTRAINT: The final structured plan must be between 700-1000 lines long.
```

**Then fixed immediate output**: "Make this plan between 500 and 700 lines long."

---

## Human Override Example: Streaming Bug

**AI suggested**: Create extensive on-demand context for streaming patterns.

**Human chose instead**: Research validation — validate research docs during planning before building plans on them.

**Why the override was better**:
- More general (applies to all research, not just streaming)
- Won't clutter reference/ with niche topics
- Addresses the systemic issue (incomplete research)
- Simpler to maintain

---

> **Reference**: See `reference/implementation-discipline.md` Section 5 for the full meta-reasoning methodology with additional anti-patterns.
