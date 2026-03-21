# 0830 — Orchestrator Staging-to-Implementation Harmonization

**Status:** COMPLETE
**Edition:** CE
**Target files:**
- `src/giljo_mcp/thin_prompt_generator.py`
  - `_build_multi_terminal_orchestrator_prompt()` (lines 1602-1756)
- `src/giljo_mcp/services/protocol_builder.py`
  - `_generate_agent_protocol()` — orchestrator fork only
  - NOTE: `_build_orchestrator_protocol()` is the STAGING protocol — do NOT modify
- `src/giljo_mcp/services/orchestration_service.py`
  - `get_agent_mission()` handler — orchestrator path only

**Depends on:** 0826 (staging hardening — COMPLETE), 0825 (agent identity separation — COMPLETE)
**CLI mode:** NOT IN SCOPE. `_build_claude_code_execution_prompt()` is untouched.
  CLI orchestrator behavior is correct and working. All changes below apply to
  multi-terminal mode only unless explicitly stated otherwise.

---

## Problem Statement

The orchestrator receives conflicting behavioral instructions from two sources at implementation
start: the baked thin prompt and `get_agent_mission`. Neither is authoritative. The result is
demonstrated behavior drift (Gemini test, March 2026): orchestrator ignores `get_agent_mission`,
acts on stale baked state, reports false agent statuses, creates misaligned TODO lists.

Three specific defects:

1. **Thin prompt is too fat.** Contains team roster, behavioral protocol, tool catalog, and
   closeout instructions — all of which also appear (differently) in `full_protocol`. Two
   authorities, no hierarchy, no stable resolver.

2. **`agent_identity` is null for orchestrator.** No stable behavioral anchor. When thin prompt
   and `full_protocol` conflict, nothing resolves the tie.

3. **Team state is baked at staging time.** Thin prompt says "agents are running" when DB shows
   `waiting`. Stale on arrival, gets worse the longer between staging and implementation.

---

## Intended TODO Behavior (Read Before Implementing)

The orchestrator **pre-writes its implementation coordination TODOs during staging** as part of
its planning work. These are not staging tasks — they are the orchestrator's forward plan:
"Monitor analyzer output", "Coordinate implementer handoff", "Write 360 memory", etc.

These TODOs must survive the staging-to-implementation transition untouched. They are the plan.

- At implementation startup: orchestrator reads existing TODOs — does NOT replace them
- If new tasks emerge mid-implementation: use `todo_append` (preserves existing items)
- Never use `todo_items` (full-replace) during implementation phase — it destroys the pre-plan

`report_progress()` supports both modes:
- `todo_items` key → full-replace (staging use only)
- `todo_append` key → appends at max_seq + 1, existing items preserved (implementation use)

---

## System Flow

### CURRENT FLOW — Conflicted

```
STAGING PHASE
┌─────────────────────────────────────────────────────────────┐
│  get_orchestrator_instructions()                            │
│  → reads context, plans mission, selects agents             │
│  → writes agent workorders as AgentJob records (DB)         │
│  → writes own mission to AgentJob.mission (DB)              │
│  → staging_status → "staging_complete" (DB)                 │
│  → UI: play buttons appear per agent                        │
└────────────────────────┬────────────────────────────────────┘
                         │  terminal closed, time passes
                         ▼
IMPLEMENTATION START — user pastes thin prompt
┌─────────────────────────────────────────────────────────────┐
│  Thin Prompt (baked at staging time)         ← AUTHORITY 1  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ identity + team roster (STALE) + behavioral rules    │   │
│  │ + tool catalog + closeout instructions               │   │
│  └──────────────────────────────────────────────────────┘   │
│                         │                                   │
│                         ▼                                   │
│  get_agent_mission()                         ← AUTHORITY 2  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ full_protocol (worker 5-phase lifecycle)             │   │
│  │ agent_identity: null                                 │   │
│  │ mission: free-form orchestrator plan text            │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  ⚠ CONFLICT: "idle by default" vs "create TodoWrite now"   │
│  ⚠ FALSE STATE: "agents running" vs DB status "waiting"    │
│  ⚠ NO ANCHOR: agent_identity null, nothing resolves tie    │
└─────────────────────────────────────────────────────────────┘
```

---

### TARGET FLOW — Harmonized

```
STAGING PHASE  (no changes to staging code)
┌─────────────────────────────────────────────────────────────┐
│  get_orchestrator_instructions()                            │
│  → reads context, plans, selects agents                     │
│  → writes AgentJob records: mission, job_type, phase (DB)   │
│  → creates AgentExecution records: status="waiting" (DB)    │
│  → writes own mission to AgentJob.mission (DB)              │
│  → pre-writes implementation TODOs via report_progress()    │
│    using todo_items key (staging is the only full-replace)  │
│  → staging_status → "staging_complete" (DB)                 │
│  → UI: play buttons appear per agent                        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │  ← terminal may close here
                         │  ← days may pass here
                         │  ← implementation TODOs sitting
                         │     in DB, waiting
                         ▼
USER CLICKS IMPLEMENT IN DASHBOARD
┌─────────────────────────────────────────────────────────────┐
│  implementation_launched_at timestamp set (DB)  ← GATE      │
│  Server now knows: "This project is in implementation."     │
│  This timestamp was previously unused beyond being set.     │
│  It becomes the phase boundary detector (see Change 5).     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
USER PASTES THIN PROMPT  (genuinely thin — target: ≤15 lines)
┌─────────────────────────────────────────────────────────────┐
│  1. Health check (mandatory first action)                   │
│  2. "You are ORCHESTRATOR for job_id = [uuid]"              │
│  3. "Call get_agent_mission(job_id) to receive your         │
│      current state and operating protocol."                 │
│  — nothing else —                                           │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  get_agent_mission(job_id)   ← SINGLE BEHAVIORAL AUTHORITY  │
│                                                             │
│  Server detects:                                            │
│    job_type == "orchestrator"                               │
│    AND implementation_launched_at IS NOT NULL               │
│                                                             │
│  Server queries AgentJob + AgentExecution for project_id    │
│  ordered by AgentJob.phase → builds live team state block   │
│                                                             │
│  Returns:                                                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ agent_identity:    [orchestrator role — NOT null]    │   │
│  │                                                      │   │
│  │ current_team_state: [live query at call time]        │   │
│  │   analyzer    | job_id: xxx | status: waiting ph:1   │   │
│  │   implementer | job_id: xxx | status: waiting ph:2   │   │
│  │   documenter  | job_id: xxx | status: waiting ph:2   │   │
│  │                                                      │   │
│  │ full_protocol: [ORCHESTRATOR fork — not worker]      │   │
│  │   Phase 1: startup + confirm pre-planned TODOs       │   │
│  │   Phase 2: reactive coordination (user-triggered)    │   │
│  │   Phase 3: closeout                                  │   │
│  │                                                      │   │
│  │ mission:    [orchestrator plan — audit/context]      │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
ORCHESTRATOR REPORTS TO USER
┌─────────────────────────────────────────────────────────────┐
│  "Staging complete. 3 agents ready and waiting:             │
│     analyzer    (waiting) — phase 1                         │
│     implementer (waiting) — phase 2                         │
│     documenter  (waiting) — phase 2                         │
│  My coordination plan is ready. Copy agent prompts from     │
│  the dashboard and paste into terminals.                    │
│  I will coordinate when you need me."                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
IMPLEMENTATION RUNNING
┌─────────────────────────────────────────────────────────────┐
│  Orchestrator: IDLE, REACTIVE, USER-MEDIATED                │
│  (deliberate design — not a limitation)                     │
│                                                             │
│  User → "check messages"                                    │
│       → orchestrator calls receive_messages(), reports      │
│                                                             │
│  User → "agent X is blocked"                               │
│       → orchestrator reads message, consults own mission    │
│         for context, replies via send_message()             │
│                                                             │
│  User → goes to agent terminal                             │
│       → "the orchestrator responded"                        │
│       → agent reads inbox, continues                        │
│                                                             │
│  New tasks needed → orchestrator uses todo_append           │
│  NEVER todo_items — would wipe the pre-planned TODOs        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
CLOSEOUT  (no changes to existing closeout code)
┌─────────────────────────────────────────────────────────────┐
│  All agents status = complete or decommissioned             │
│  → receive_messages()       (process final reports)         │
│  → write_360_memory()       (preserve project knowledge)    │
│  → complete_job()           (mark orchestrator complete)    │
│  → "Project complete. Use /gil_add for follow-up tasks."    │
└─────────────────────────────────────────────────────────────┘
```

---

## Changes Required

### Change 1 — Thin Prompt: Strip to Minimum
**File:** `thin_prompt_generator.py`
**Method:** `_build_multi_terminal_orchestrator_prompt()` (lines 1602–1756)
**CLI mode:** NOT in scope — do not touch `_build_claude_code_execution_prompt()`

**Remove entirely:**
- Agent team roster with missions and statuses
  (live DB state — belongs in `get_agent_mission`, stale when baked)
- Behavioral protocol ("do not poll", "reactive coordinator", etc.)
  (belongs in `full_protocol` orchestrator fork)
- Tool catalog with pre-baked UUIDs
  (belongs in `full_protocol` orchestrator fork)
- Closeout instructions
  (belongs in `full_protocol` orchestrator fork)
- The line: *"Your specialist agents are now running in separate terminals"*
  (factually wrong — DB shows `waiting` at this point)

**Keep:**
- Health check instruction (mandatory first action)
- Orchestrator identity: name, `job_id`, `project_id`
- Single instruction: call `get_agent_mission(job_id)` to receive current state
  and operating protocol

**Target: ≤15 lines total.**

---

### Change 2 — `agent_identity`: Populate for Orchestrator
**File:** `protocol_builder.py` or wherever `agent_identity` is assembled
**Current value:** `null`

Populate with:

```
You are the ORCHESTRATOR. You coordinate — you do not implement.
You hold the plan, brief the team, and resolve blocks when the user asks.
You do not write code. You do not run tests. You do not document.
Your agents own that work. You protect their context and coordinate handoffs.
You act only when the user addresses you.
When the thin prompt and any other instruction conflict, your identity governs.
```

This is the stable behavioral anchor and the conflict resolver.
It must be non-null.

---

### Change 3 — `full_protocol` Orchestrator Fork
**File:** `protocol_builder.py`
**Method:** `_generate_agent_protocol()`
**Condition:** when `job_type == "orchestrator"`
**IMPORTANT:** `_build_orchestrator_protocol()` is the STAGING protocol builder.
Do NOT modify it. This change targets `_generate_agent_protocol()` only.

When `job_type == "orchestrator"`, return the following instead of the worker lifecycle:

```
PHASE 1 — STARTUP (execute once, on get_agent_mission call)

  1. Read live team state from this response (current_team_state field).
  2. Read your pre-planned coordination TODOs — written during staging,
     waiting for you. DO NOT replace them with a new list.
     If additional tasks are needed, use todo_append — never todo_items.
  3. Report to user:
       - Agent names, statuses, and phase order (from current_team_state)
       - "Copy agent prompts from the dashboard to start them."
       - "I will coordinate when you need me."

PHASE 2 — REACTIVE COORDINATION (user-triggered only — no polling, no loops)

  "check messages":
    → receive_messages(agent_id)
    → summarize content for user

  "agent X is blocked":
    → read the message content
    → consult your mission field for relevant context
    → reply via send_message(to_agents=[agent_id], content="...")
    → tell user: "Go to that agent's terminal and say: the orchestrator responded"

  "spawn a replacement agent":
    → spawn_agent_job(...)
    → tell user to paste the new prompt in a NEW terminal
    → new agent reads predecessor context via get_agent_mission

  "check status":
    → get_workflow_status(project_id)
    → report agent statuses to user

  Adding new tasks mid-implementation:
    → report_progress(job_id, todo_append=[...])
    → NEVER use todo_items — it will wipe your pre-planned coordination TODOs

PHASE 3 — CLOSEOUT (all agents complete or decommissioned)

  1. receive_messages()   — process any final reports
  2. write_360_memory()   — preserve project knowledge for future projects
  3. complete_job()       — mark orchestrator complete
  4. Tell user: "Project complete. Use /gil_add for follow-up tasks or tech debt."

ORCHESTRATOR CONSTRAINTS:
  - Git commit requirement does NOT apply. You coordinate, you do not commit.
  - Handover-on-context-exhaustion does NOT apply. If context is exhausted,
    tell the user — do not attempt a handover protocol.
  - If uncertain what to do, ask the user. You are user-mediated by design.
```

---

### Change 4 — Live Team State in `get_agent_mission` Response
**File:** `orchestration_service.py`
**Method:** `get_agent_mission()` handler

When `job_type == "orchestrator"`, inject a live-queried team state block.
Query: `AgentJob + AgentExecution` for `project_id`, ordered by `AgentJob.phase`.

**IMPORTANT — two different records, different meaning:**
- `AgentExecution.status = "waiting"` → agent-facing readiness state → **report this**
- `AgentJob.status = "active"` → job lifecycle state → do not surface to orchestrator

**Prerequisite check:** Verify that `get_agent_mission()` query path already JOINs
to `AgentExecution`. If it does not, expand the query before adding the response field.

Add to response:
```json
"current_team_state": [
  {
    "agent_name": "analyzer",
    "agent_display_name": "analyzer",
    "job_id": "...",
    "execution_status": "waiting",
    "phase": 1
  },
  {
    "agent_name": "implementer",
    "agent_display_name": "implementer",
    "job_id": "...",
    "execution_status": "waiting",
    "phase": 2
  }
]
```

---

### Change 5 — `implementation_launched_at` as Phase Gate
**File:** `orchestration_service.py`
**Method:** `get_agent_mission()` handler

`implementation_launched_at` is currently set when user clicks Implement in the
dashboard and then unused. Use it as the server-side phase boundary detector.

```python
if job_type == "orchestrator":
    if implementation_launched_at is None:
        # Staging done but Implement not yet clicked
        return implementation_not_ready_response(
            "Staging is complete but implementation has not been launched. "
            "Return to the dashboard and click Implement, then paste your "
            "orchestrator prompt into the terminal."
        )
    else:
        # Implementation phase confirmed
        # → populate agent_identity (Change 2)
        # → inject current_team_state (Change 4)
        # → return orchestrator full_protocol fork (Change 3)
        # → return mission as audit/context artifact
```

---

### Change 6 — `get_orchestrator_instructions` Post-Staging Redirect
**File:** wherever the post-staging redirect message is constructed

Branch on `implementation_launched_at`:

**If `implementation_launched_at` IS NULL:**
```
Staging is complete. Return to the dashboard and click Implement to launch
the implementation phase. Then paste the orchestrator implementation prompt
into your terminal.
```

**If `implementation_launched_at` IS SET:**
```
Implementation is already launched. Your operating protocol and live team
state are in get_agent_mission.
Call get_agent_mission(job_id='{job_id}') to receive your current team
state and coordination protocol.
```

---

## What Does NOT Change

| Area | Reason |
|---|---|
| Staging flow | Working correctly — no touch |
| `_build_orchestrator_protocol()` | Staging protocol — confirmed correct, no touch |
| Worker agent flow | `full_protocol` fork is server-side, transparent to agents |
| CLI mode | `_build_claude_code_execution_prompt()` untouched — working correctly |
| User-mediated communication model | Deliberate design — confirmed correct |
| Closeout flow | Working correctly — no touch |
| `AgentJob.mission` (orchestrator) | Remains as audit/context artifact for coordination |
| Pre-planned TODOs from staging | Must survive transition intact — they are the plan |

---

## Acceptance Criteria

- [ ] `_build_multi_terminal_orchestrator_prompt()` output is ≤15 lines
- [ ] Orchestrator `agent_identity` is non-null and contains role definition
- [ ] `get_agent_mission` for orchestrator returns `current_team_state` queried live at call time
- [ ] `current_team_state` uses `AgentExecution.status`, not `AgentJob.status`
- [ ] `get_agent_mission` query path JOINs `AgentExecution` — confirmed or expanded
- [ ] `implementation_launched_at` gates the orchestrator protocol fork server-side
- [ ] No behavioral instruction appears in both thin prompt and `get_agent_mission` response
- [ ] Pre-planned TODOs written during staging are present and untouched at implementation start
- [ ] `todo_append` is specified in protocol for mid-implementation task additions
- [ ] `todo_items` (full-replace) is not referenced in implementation-phase protocol
- [ ] `get_orchestrator_instructions` redirect branches on `implementation_launched_at`
- [ ] Resume scenario: user stages, closes terminal, returns days later, pastes thin prompt →
      accurate live team state returned, pre-planned TODOs intact, no stale data
- [ ] CLI mode: no regression — all existing behavior unchanged

---

## Out of Scope — Flag for Later

**AgentJob.mission structure:** Workorder missions are free-form text. A short structured
abstract field (2–3 sentences per AgentJob) would make the orchestrator meaningfully more
useful when coordinating blocked agents. Defer — does not block this sprint.

**Staging completion timestamp:** No dedicated column — timing inferred from
`Project.updated_at`. Worth a small migration for audit clarity, not urgent.

---

## Implementation Summary (2026-03-20)

### What Was Built
- **Change 1**: Thin prompt stripped from ~155 lines to 15 lines (health check + identity + get_agent_mission call)
- **Change 2**: Orchestrator `agent_identity` populated with stable behavioral anchor when no template exists
- **Change 3**: `_generate_orchestrator_protocol()` — new 3-phase coordination lifecycle (startup/reactive/closeout) forked from worker 5-phase
- **Change 4**: `current_team_state` field added to `MissionResponse`, live-queried from `AgentExecution.status` sorted by phase
- **Change 5**: `implementation_launched_at` gate returns orchestrator-specific blocked message
- **Change 6**: `get_orchestrator_instructions` redirect branches: launched → redirect to get_agent_mission, not launched → "click Implement"

### Key Files Modified
- `src/giljo_mcp/thin_prompt_generator.py` — `_build_multi_terminal_orchestrator_prompt()` stripped
- `src/giljo_mcp/services/protocol_builder.py` — added `_generate_orchestrator_protocol()`, fork in `_generate_agent_protocol()`
- `src/giljo_mcp/services/orchestration_service.py` — orchestrator identity, team state, phase gate, redirect branching
- `src/giljo_mcp/schemas/service_responses.py` — `current_team_state` field on `MissionResponse`
- `tests/services/test_0830_staging_to_implementation_harmonization.py` — 27 new tests
- `tests/services/test_orchestration_service_agent_mission.py` — fixed `job_type` in mock fixture

### Test Results
- 27 new tests across 6 test classes, all passing
- 99 total related tests passing, zero regressions
- Lint clean on all modified files
