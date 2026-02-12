# Feature: Reference Templates Completion

## Feature Description

Create 5 missing templates and documentation artifacts that are described in the reference guides but don't exist as standalone files. These templates were identified during a systematic audit of all 16 reference guides against the actual file system. Each template has clear content specifications from the reference guides — this plan extracts and formalizes them.

## User Story

As a developer using the PIV Loop system, I want ready-to-use templates for baseline assessment, validation reports, tool docstrings, meta-reasoning, and CodeRabbit config, so that I can follow reference guide recommendations without manually extracting template structures from prose.

## Problem Statement

The reference guides describe specific formats and frameworks (baseline assessment categories, validation report structure, tool docstring elements, meta-reasoning steps, CodeRabbit config) but these exist only as inline prose — not as copy-paste-ready template files. Users must read hundreds of lines of reference material to extract the format, which defeats the purpose of having templates.

## Solution Statement

- Decision 1: Create standalone template files — because templates should be immediately usable without reading the reference guide first
- Decision 2: Keep templates concise with placeholders — because templates that are too prescriptive become rigid; the reference guide provides the "why"
- Decision 3: Place in templates/ directory (except .coderabbit.yaml at root) — because that's the established convention per reference/file-structure.md

## Feature Metadata

- **Feature Type**: Enhancement (filling documented gaps)
- **Estimated Complexity**: Low
- **Primary Systems Affected**: templates/, project root (.coderabbit.yaml)
- **Dependencies**: None (all content sourced from existing reference guides)

---

## CONTEXT REFERENCES

### Relevant Codebase Files

- `reference/system-foundations.md` (lines 151-226) — Why: Contains the 5 assessment categories and measurement framework for baseline template
- `reference/piv-loop-practice.md` (lines 499-537) — Why: Contains the validation report format (success and failure examples)
- `reference/planning-methodology-guide.md` (lines 242-303) — Why: Contains the 7 required elements for tool docstrings
- `reference/implementation-discipline.md` (lines 185-248) — Why: Contains the 5-step meta-reasoning process and WHERE-to-fix framework
- `reference/github-orchestration.md` (lines 313-320) — Why: References .coderabbit.yaml setup requirements
- `reference/github-workflows/README.md` (lines 50-65) — Why: CodeRabbit customization options
- `templates/STRUCTURED-PLAN-TEMPLATE.md` — Why: Existing template pattern to follow (placeholder style, section organization)
- `templates/AGENT-TEMPLATE.md` — Why: Another strong template pattern (framework + guidance combined)
- `templates/COMMAND-TEMPLATE.md` — Why: Template design convention reference

### New Files to Create

- `templates/BASELINE-ASSESSMENT-TEMPLATE.md` — Self-assessment framework for measuring PIV Loop improvement
- `templates/VALIDATION-REPORT-TEMPLATE.md` — Standardized format for validation output (success/failure)
- `templates/TOOL-DOCSTRING-TEMPLATE.md` — 7-element template for writing agent tool documentation
- `templates/META-REASONING-CHECKLIST.md` — 5-step process + WHERE-to-fix decision framework
- `.coderabbit.yaml` — CodeRabbit configuration template for automated PR reviews

### Related Memories (from memory.md)

No relevant memories found in memory.md

### Relevant Documentation

- [CodeRabbit Configuration](https://docs.coderabbit.ai/getting-started/configuration)
  - Specific section: YAML Configuration
  - Why: Required for creating accurate .coderabbit.yaml template

### Patterns to Follow

**Template Header Pattern** (from `templates/STRUCTURED-PLAN-TEMPLATE.md:1-17`):
```markdown
# Template Name

> Brief description of when to use this template.
> Key constraints or rules.
>
> **Core Principle**: One sentence about the template's purpose.
```
- Why this pattern: All templates use blockquote headers with guidance
- Common gotchas: Don't make the header too long; keep it scannable

**Placeholder Pattern** (from `templates/STRUCTURED-PLAN-TEMPLATE.md:20-46`):
```markdown
## Section Name

{Brief instruction on what goes here}

- **Field Name**: {Type / Options}
- **Field Name**: {Description of expected content}
```
- Why this pattern: Consistent placeholder format with curly braces
- Common gotchas: Include both the field name AND guidance on how to fill it

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation Templates (Self-Assessment + Validation)

Create the two templates that support the PIV Loop's measurement and validation phases. These are the most frequently referenced missing templates.

**Tasks:**
- Create Baseline Assessment Template (from system-foundations.md)
- Create Validation Report Template (from piv-loop-practice.md)

### Phase 2: Development Templates (Tool Docstrings + Meta-Reasoning)

Create templates that support the development workflow — tool design and system evolution.

**Tasks:**
- Create Tool Docstring Template (from planning-methodology-guide.md)
- Create Meta-Reasoning Checklist (from implementation-discipline.md)

### Phase 3: CI Configuration (CodeRabbit)

Create the CodeRabbit config that enables automated PR review.

**Tasks:**
- Create .coderabbit.yaml at project root

### Phase 4: Validation

Verify all templates follow conventions and cross-references are correct.

**Tasks:**
- Verify each template is referenced correctly in the system
- Update reference/file-structure.md to include new templates

---

## STEP-BY-STEP TASKS

### CREATE templates/BASELINE-ASSESSMENT-TEMPLATE.md

- **IMPLEMENT**: Create a self-assessment template with these sections:
  1. Header with usage instructions (when to use: before starting the PIV Loop, and again after completing core guides)
  2. **Feature Being Assessed** — name, complexity, description
  3. **Category 1: Time Tracking** — Backend time, Frontend time, Total time (with fields for minutes)
  4. **Category 2: AI Interaction** — Number of prompts, types of prompts, iteration cycles, time waiting, time reviewing
  5. **Category 3: Confidence Levels** — 4 ratings (correct, best practices, understanding, maintainability) each 1-10
  6. **Category 4: Issues Encountered** — AI mistakes, type errors, debugging cycles, manual rework percentage
  7. **Category 5: Quality Signals** — 4 yes/no checks (tests pass, compiles, works e2e, passes code review)
  8. **Honest Self-Assessment Checklist** — 7 checkbox items from system-foundations.md lines 214-223
  9. **Improvement Comparison** section with Before/After columns and target improvements (30-50% time reduction, 40-60% fewer prompts, +2-3 confidence, fewer bugs)
  10. Footer note: "The system works if all five categories improve together"
- **PATTERN**: Follow `templates/STRUCTURED-PLAN-TEMPLATE.md:1-17` header pattern
- **IMPORTS**: None (markdown only)
- **GOTCHA**: Keep the template SHORT — just fields and brief instructions. The reference guide (system-foundations.md) provides the detailed explanations. Don't duplicate prose.
- **VALIDATE**: `powershell -Command "if (Test-Path 'templates/BASELINE-ASSESSMENT-TEMPLATE.md') { Write-Host 'OK'; (Get-Content 'templates/BASELINE-ASSESSMENT-TEMPLATE.md').Count } else { Write-Host 'MISSING' }"`

### CREATE templates/VALIDATION-REPORT-TEMPLATE.md

- **IMPLEMENT**: Create a validation report template with:
  1. Header explaining this is the standard output format for validation results
  2. **Report Header** section — Feature name, date, validator (AI/Human), plan reference
  3. **Results Table** — Level 1-5 validation results with PASSED/FAILED status:
     - Level 1: Syntax & Style (tool name, command, result)
     - Level 2: Type Safety (tool name, command, result)
     - Level 3: Unit Tests (count, time, result)
     - Level 4: Integration Tests (count, time, result)
     - Level 5: Human Review (reviewer, result)
  4. **Issues Found** section — grouped by category with file:line format
  5. **Status** — ALL CHECKS PASSED or VALIDATION FAILED
  6. Include both success and failure examples (from piv-loop-practice.md lines 502-537)
  7. **AI vs Human Validation** checklist — what AI handles (levels 1-4) vs what humans handle (level 5)
- **PATTERN**: Follow validation report format from `reference/piv-loop-practice.md:499-537`
- **IMPORTS**: None (markdown only)
- **GOTCHA**: The template should be project-agnostic — use placeholders for tool names (e.g., {linting_tool}, {type_checker}) since different projects use different tools
- **VALIDATE**: `powershell -Command "if (Test-Path 'templates/VALIDATION-REPORT-TEMPLATE.md') { Write-Host 'OK'; (Get-Content 'templates/VALIDATION-REPORT-TEMPLATE.md').Count } else { Write-Host 'MISSING' }"`

### CREATE templates/TOOL-DOCSTRING-TEMPLATE.md

- **IMPLEMENT**: Create a tool docstring template with:
  1. Header explaining this is for writing agent tool documentation (NOT standard code docstrings)
  2. **The 7 Required Elements** table (from planning-methodology-guide.md lines 249-258):
     - Element 1: One-line summary
     - Element 2: "Use this when" (3-5 specific scenarios)
     - Element 3: "Do NOT use this for" (redirect to other tools) — note this is the MOST IMPORTANT and most commonly missed
     - Element 4: Args with WHY (each param with type + guidance)
     - Element 5: Returns (format and structure details)
     - Element 6: Performance notes (token usage, execution time, limits)
     - Element 7: Examples (2-4 realistic scenarios, NOT "foo"/"bar")
  3. **Template** — actual docstring template with all 7 elements as placeholders
  4. **Anti-Patterns** section with 3 common mistakes and fixes (from planning-methodology-guide.md lines 262-283):
     - Vague guidance → Specific guidance
     - Missing negative guidance → Clear redirects
     - Toy examples → Realistic examples
  5. **Tool Consolidation Principle** — fewer, smarter tools reduce agent error rates (lines 285-302)
- **PATTERN**: Follow `templates/AGENT-TEMPLATE.md` style (framework + guidance combined)
- **IMPORTS**: None (markdown only)
- **GOTCHA**: Emphasize Element 3 ("Do NOT use this for") — this is the most impactful element and the one developers skip most often
- **VALIDATE**: `powershell -Command "if (Test-Path 'templates/TOOL-DOCSTRING-TEMPLATE.md') { Write-Host 'OK'; (Get-Content 'templates/TOOL-DOCSTRING-TEMPLATE.md').Count } else { Write-Host 'MISSING' }"`

### CREATE templates/META-REASONING-CHECKLIST.md

- **IMPLEMENT**: Create a meta-reasoning checklist with:
  1. Header explaining meta-reasoning: asking WHY something went wrong and WHERE to fix it, not just fixing the immediate problem
  2. **The 5-Step Process** (from implementation-discipline.md lines 192-198):
     - Step 1: Identify the problem (specific, measurable description)
     - Step 2: Ask for analysis (exact prompt: "Do some meta reasoning. Don't make any changes yet...")
     - Step 3: AI examines the system (global rules, on-demand context, commands, templates, vibe planning)
     - Step 4: You decide (human selects which suggestion to implement — may override AI)
     - Step 5: Apply system fix FIRST, then fix immediate output
  3. **WHERE-to-Fix Decision Framework** table (from implementation-discipline.md lines 203-209):
     - Global rules (CLAUDE.md/sections) → Convention applies to ALL tasks
     - On-demand context (reference/) → Task-type-specific guidance
     - Commands (planning, execute) → Process/workflow issue
     - Templates (structured plan, PRD) → Output format/structure issue
     - Vibe planning (your prompts) → Research was incomplete or scope wrong
  4. **One-Off Fix vs System Evolution** comparison table (lines 211-218)
  5. **Concrete Example** — Plan length constraint example (lines 220-237)
  6. **Human Override Example** — Streaming bug where human chose simpler fix (lines 239-248)
  7. **Quick Decision Checklist** — 5 questions to determine fix location
- **PATTERN**: Follow `templates/COMMAND-TEMPLATE.md` style (framework with actionable steps)
- **IMPORTS**: None (markdown only)
- **GOTCHA**: The meta-reasoning prompt (Step 2) must be exact — it tells the AI "don't make changes yet" which is critical. If you skip this, the AI will just start fixing things.
- **VALIDATE**: `powershell -Command "if (Test-Path 'templates/META-REASONING-CHECKLIST.md') { Write-Host 'OK'; (Get-Content 'templates/META-REASONING-CHECKLIST.md').Count } else { Write-Host 'MISSING' }"`

### CREATE .coderabbit.yaml

- **IMPLEMENT**: Create a CodeRabbit configuration file at project root with:
  1. Comment header explaining this is a template to copy to project roots
  2. `language: "en-US"`
  3. `reviews` section:
     - `profile: "assertive"` (thorough reviews)
     - `path_instructions` with common patterns (e.g., skip generated files, stricter for src/)
     - `auto_review` enabled for PRs
  4. `chat` section:
     - `auto_reply: true`
  5. Comment explaining free tier limitations (private repos: PR summaries only after 14-day trial; open source: full reviews on all tiers)
  6. Comment pointing to CodeRabbit docs for full configuration options
- **PATTERN**: Standard YAML configuration with inline comments
- **IMPORTS**: None (YAML only)
- **GOTCHA**: This is a TEMPLATE — users must customize path_instructions for their project. Don't make it too project-specific.
- **VALIDATE**: `powershell -Command "if (Test-Path '.coderabbit.yaml') { Write-Host 'OK'; (Get-Content '.coderabbit.yaml').Count } else { Write-Host 'MISSING' }"`

### UPDATE reference/file-structure.md

- **IMPLEMENT**: Add the 4 new template files to the file structure listing under the `templates/` section. Add entries:
  - `BASELINE-ASSESSMENT-TEMPLATE.md` — Self-assessment for measuring PIV Loop improvement
  - `VALIDATION-REPORT-TEMPLATE.md` — Standard format for validation output
  - `TOOL-DOCSTRING-TEMPLATE.md` — 7-element template for agent tool documentation
  - `META-REASONING-CHECKLIST.md` — 5-step meta-reasoning + WHERE-to-fix framework
  Also add `.coderabbit.yaml` entry at the root level of the file tree.
- **PATTERN**: Follow existing format in `reference/file-structure.md` — comment-style descriptions after each file
- **IMPORTS**: None
- **GOTCHA**: Maintain alphabetical ordering within the templates/ section where existing entries allow. Don't break the existing structure.
- **VALIDATE**: `powershell -Command "Select-String -Path 'reference/file-structure.md' -Pattern 'BASELINE-ASSESSMENT|VALIDATION-REPORT|TOOL-DOCSTRING|META-REASONING|coderabbit' | Measure-Object | Select-Object -ExpandProperty Count"`

---

## TESTING STRATEGY

### Unit Tests

N/A — these are markdown templates and YAML config. No code to unit test.

### Integration Tests

- Verify each template follows the established pattern (blockquote header, placeholder format)
- Verify .coderabbit.yaml is valid YAML syntax
- Verify reference/file-structure.md accurately reflects the new files

### Edge Cases

- Template is too long (should be concise — under 100 lines each)
- Template duplicates reference guide prose (should use placeholders, not copy paragraphs)
- .coderabbit.yaml uses CodeRabbit v1 syntax when v2 is current

---

## VALIDATION COMMANDS

### Level 1: Syntax & Style
```
powershell -Command "Get-ChildItem templates/*.md | ForEach-Object { Write-Host $_.Name ': ' $((Get-Content $_.FullName).Count) ' lines' }"
```

### Level 2: YAML Validation
```
powershell -Command "try { Get-Content '.coderabbit.yaml' -Raw | ConvertFrom-Yaml; Write-Host 'YAML Valid' } catch { Write-Host 'YAML Invalid' }"
```

### Level 3: File Structure Verification
```
powershell -Command "@('templates/BASELINE-ASSESSMENT-TEMPLATE.md','templates/VALIDATION-REPORT-TEMPLATE.md','templates/TOOL-DOCSTRING-TEMPLATE.md','templates/META-REASONING-CHECKLIST.md','.coderabbit.yaml') | ForEach-Object { if (Test-Path $_) { Write-Host 'OK: ' $_ } else { Write-Host 'MISSING: ' $_ } }"
```

### Level 4: Manual Validation

1. Read each template and verify it matches the source reference content
2. Verify templates use placeholder format (curly braces), not prescriptive content
3. Verify .coderabbit.yaml has helpful comments explaining customization
4. Verify reference/file-structure.md lists all new files

### Level 5: Cross-Reference Check

Verify each template is findable from its reference guide:
- system-foundations.md mentions baseline → templates/BASELINE-ASSESSMENT-TEMPLATE.md exists
- piv-loop-practice.md mentions validation report → templates/VALIDATION-REPORT-TEMPLATE.md exists
- planning-methodology-guide.md mentions tool docstrings → templates/TOOL-DOCSTRING-TEMPLATE.md exists
- implementation-discipline.md mentions meta-reasoning → templates/META-REASONING-CHECKLIST.md exists

---

## ACCEPTANCE CRITERIA

- [ ] All 5 new files created
- [ ] Each template follows the established header/placeholder pattern
- [ ] Templates are concise (under 100 lines each, preferably 50-80)
- [ ] .coderabbit.yaml is valid YAML with helpful comments
- [ ] reference/file-structure.md updated with all new entries
- [ ] No reference guide prose is duplicated — templates contain placeholders and brief instructions only
- [ ] Each template can be immediately used without reading the reference guide

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order
- [ ] Each task validation passed
- [ ] All validation commands executed successfully
- [ ] Manual verification confirms templates match source material
- [ ] File structure documentation updated

---

## NOTES

### Key Design Decisions
- Templates are CONCISE (50-80 lines) with placeholders — the reference guides provide the detailed "why"
- .coderabbit.yaml is intentionally generic — users customize per project
- Meta-reasoning checklist includes the exact prompt text — this is critical for reliable results

### Risks
- Risk 1: Templates become stale if reference guides are updated → Mitigation: templates reference the guide for detailed explanation
- Risk 2: .coderabbit.yaml syntax may differ across CodeRabbit versions → Mitigation: include link to official docs

### Confidence Score: 9/10
- **Strengths**: All content is clearly specified in existing reference guides; just formalizing into templates
- **Uncertainties**: CodeRabbit YAML schema may have changed since reference was written
- **Mitigations**: Include link to official CodeRabbit docs in the YAML comments
