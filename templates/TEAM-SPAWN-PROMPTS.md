# Agent Teams — Spawn Prompt Templates

Copy-paste-ready templates for spawning Agent Teams teammates using the contract-first pattern. Each template includes the 5 required sections: ownership, scope, mandatory communication, contract conformity, and cross-cutting concerns.

Replace all `[BRACKETED]` values with specifics from your plan.

---

## Upstream Agent Template

> Spawns **FIRST** in the contract chain. Publishes the foundational contract (database schema, core types, library API). No upstream contract to conform to.

```
You are the [ROLE] agent for [FEATURE]. You are the most upstream agent in the contract chain.

**Ownership**:
- Files you OWN: [list specific directories/files]
- Files you must NOT touch: [everything else — be explicit]

**Scope**: [What this agent builds — specific deliverables, files to create/modify]

**Mandatory Communication — CONTRACT FIRST**:
Before implementing ANYTHING, you MUST publish your contract to the lead:
- [For DB: complete schema with table definitions, column types, constraints, function signatures]
- [For Core: public API surface, type exports, interface definitions]
- [For Schema: all type definitions, validation rules, shared constants]
Send the contract as a message to the lead. The lead will verify and forward it to downstream agents.
Only begin implementation AFTER the lead confirms your contract.

**Cross-Cutting Concerns you define** (downstream agents will follow these):
- [List shared conventions this agent establishes: naming patterns, date formats, ID types, etc.]

**Validation**: Before reporting done, run:
- [Domain-specific validation commands: tests, type checks, migrations, etc.]

**Turn limit**: If you've been working for 30+ turns without progress, report blockers to the lead.
**Logging**: Write detailed progress to logs/team-[feature]/, send concise summaries via messages.
```

---

## Downstream Agent Template

> Spawns **AFTER** the upstream agent's contract is verified. Publishes its own contract for further downstream agents.

```
You are the [ROLE] agent for [FEATURE].

**Ownership**:
- Files you OWN: [list specific directories/files]
- Files you must NOT touch: [everything else — be explicit]

**Scope**: [What this agent builds — specific deliverables, files to create/modify]

**Contract you MUST conform to** (verified by lead):
[Paste the exact upstream contract here — complete schema, function signatures, type definitions.
This is your source of truth. Do NOT deviate from these interfaces.]

**Mandatory Communication — CONTRACT FIRST**:
Before implementing ANYTHING, publish your API contract to the lead:
- [For API: endpoint URLs, HTTP methods, request/response shapes, error formats]
- [For Service: public method signatures, return types, event definitions]
Send the contract as a message to the lead. The lead will verify and forward to the next agent.
Only begin full implementation AFTER the lead confirms your contract.

**Cross-Cutting Concerns**:
- [List shared conventions from upstream + any this agent defines]

**Validation**: Before reporting done, run:
- [Domain-specific validation commands: tests, type checks, linting, etc.]

**Turn limit**: If you've been working for 30+ turns without progress, report blockers to the lead.
**Logging**: Write detailed progress to logs/team-[feature]/, send concise summaries via messages.
```

---

## Terminal Agent Template

> Spawns **LAST** in the contract chain. Consumes upstream contracts but doesn't publish one (no downstream agents).

```
You are the [ROLE] agent for [FEATURE].

**Ownership**:
- Files you OWN: [list specific directories/files]
- Files you must NOT touch: [everything else — be explicit]

**Scope**: [What this agent builds — specific deliverables, files to create/modify]

**Contract you MUST conform to** (verified by lead):
[Paste the full API contract here — endpoints, request/response shapes, error formats, SSE events, auth headers, etc.
This is your source of truth. Build all integrations against these exact interfaces.]

**Cross-Cutting Concerns**:
- [List all shared conventions from upstream agents]

**Validation**: Before reporting done, run:
- [Domain-specific validation commands: tests, build check, type checks, etc.]

**Turn limit**: If you've been working for 30+ turns without progress, report blockers to the lead.
**Logging**: Write detailed progress to logs/team-[feature]/, send concise summaries via messages.
```

---

## Independent Agent Template

> Can run **in parallel** with the contract chain. Not dependent on upstream contracts for most work (testing, DevOps, documentation).

```
You are the [ROLE] agent for [FEATURE].

**Ownership**:
- Files you OWN: [list specific directories/files]
- Files you must NOT touch: [everything else — be explicit]

**Scope**: [What this agent builds — specific deliverables, files to create/modify]

**Dependencies**: Wait for [agent name] to publish their contract before starting [specific dependent work].
Other work can proceed immediately without waiting.

**Cross-Cutting Concerns**:
- [List any shared conventions relevant to this agent's domain]

**Validation**: Before reporting done, run:
- [Domain-specific validation commands]

**Turn limit**: If you've been working for 30+ turns without progress, report blockers to the lead.
**Logging**: Write detailed progress to logs/team-[feature]/, send concise summaries via messages.
```

---

## Usage Notes

- Replace ALL `[BRACKETED]` values with specifics from your plan
- The **contract section** must contain EXACT interfaces — not vague descriptions. Paste real schema, real endpoint definitions, real type definitions.
- **Cross-cutting concerns** should be assigned to ONE agent (usually the most upstream). All others follow that agent's conventions.
- Include **turn limits** to prevent runaway agents. 30 turns is a reasonable default.
- Include **logging instructions** — teammates write to `logs/team-{feature}/` for debugging. Send concise summaries via messages to the lead.
- The lead **never codes** — it coordinates, relays contracts, and validates. Keep this in mind when writing spawn prompts.

---

## Customization Examples

### 2-Agent Split (Frontend + Backend)

No separate database agent. Backend is upstream, publishes API contract, frontend is downstream.

- **Contract chain**: `Backend → Frontend`
- **Backend**: Use Upstream template. Publishes API endpoints, request/response shapes, error format.
- **Frontend**: Use Terminal template. Receives API contract, builds UI against it.

### 3-Agent Full-Stack (Database + Backend + Frontend)

Classic three-tier architecture. Most common pattern.

- **Contract chain**: `Database → Backend → Frontend`
- **Database**: Use Upstream template. Publishes schema, function signatures.
- **Backend**: Use Downstream template. Receives DB schema, publishes API contract.
- **Frontend**: Use Terminal template. Receives API contract.

### 4-Agent Complex (Database + Backend + Frontend + Testing)

Testing agent runs independently — it can start writing test scaffolding immediately and add integration tests as contracts are published.

- **Contract chain**: `Database → Backend → Frontend`
- **Testing**: Use Independent template. Receives all contracts for integration test planning.

### Documentation-Only Project (No Code Contracts)

When there's no code interface to coordinate (e.g., documentation systems like My Coding System), all agents are independent. Each owns specific files.

- **Contract chain**: None
- **All agents**: Use Independent template. Each owns specific directories/files.

### Model Selection for Teammates

- **Sonnet**: Default for implementation teammates (balanced capability and cost)
- **Haiku**: For review tasks, documentation agents, simple changes
- **Opus**: For complex architectural decisions (rarely needed for teammates)

Specify model in the spawn prompt or let Claude choose based on task complexity.

---

## Anti-Patterns

Avoid these mistakes based on real-world testing:

1. **"Just share with each other"** — Never tell agents to communicate directly. The lead MUST relay and verify all contracts. Agents messaging each other leads to unverified, ambiguous interfaces.

2. **"Spawn all agents at once"** — Upstream agents MUST publish contracts before downstream agents start. Spawning all simultaneously means the backend builds against a wrong or nonexistent DB schema.

3. **"Skip contract verification"** — The lead MUST check every contract for completeness before forwarding. Missing fields, ambiguous types, and inconsistent naming cause integration failures late in implementation.

4. **"Let agents figure out file boundaries"** — Every spawn prompt MUST explicitly state files owned and files NOT to touch. Without clear ownership, agents overwrite each other's work.

---

## Model Routing

### Known Issue: Task Tool Model Parameter (February 2026)

The Task tool's `model` parameter has a known bug (GitHub Issue #18873) that may cause 404 errors or default to the parent session's model regardless of the specified value.

**Workaround**: When spawning teammates via Agent Teams (TeamCreate + Task tool with `team_name`), specify the desired model in the spawn prompt itself rather than relying on the `model` parameter:

```
You are the Backend agent. Use efficient, focused implementation.
Model guidance: This task is suitable for Sonnet-level implementation.
```

**Current recommendation**:
- Lead: Opus (for reasoning during contract verification and coordination)
- Implementation teammates: Sonnet (balanced capability/cost)
- Review/testing teammates: Haiku (pattern matching, cheaper)

Monitor Issue #18873 for resolution. When fixed, switch to using the `model` parameter directly.
