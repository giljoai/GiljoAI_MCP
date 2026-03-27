# Multi-Terminal Chain Strategy Template

Use this template to plan and coordinate a chain of AI coding agent sessions
that execute sequentially on a shared codebase. Customize the placeholders
for your project, commit it to your repo, and point each agent to it.

---

## Pre-Chain Setup Checklist

- [ ] All phase instructions written and self-contained (an agent with zero context can execute each one)
- [ ] Chain log created with all sessions pre-defined (see schema below)
- [ ] Clean commit on the base branch before any chain work begins
- [ ] Feature branch created and pushed (`feature/{project}-{short-description}`)
- [ ] Each phase assigned a distinct terminal tab color for visual tracking
- [ ] Phase dependencies mapped (which phases can run in parallel?)

---

## Chain Log Schema

Create a file at `{project}_chain/chain_log.json`. Every agent reads this before
starting and updates it before stopping. The orchestrator reviews it between phases.

```json
{
  "chain_id": "{project}",
  "chain_name": "{Human-readable chain name}",
  "created_at": "{YYYY-MM-DD}",
  "spec_document": "{path/to/feature_spec.md}",
  "branch": "feature/{project}-{short-description}",
  "total_sessions": 0,
  "orchestrator_notes": "{Standing instructions all agents should read on startup.}",
  "orchestrator_directives": [],
  "sessions": [
    {
      "session_id": "{phase_id}",
      "title": "{phase_1_title}",
      "handover": "{path/to/phase_1_instructions.md}",
      "color": "#4CAF50",
      "status": "pending",
      "started_at": null,
      "completed_at": null,
      "agent_types": ["{recommended_agent_type}"],
      "planned_tasks": ["{task_1}", "{task_2}"],
      "tasks_completed": [],
      "deviations": [],
      "blockers_encountered": [],
      "notes_for_next": null,
      "cascading_impacts": [],
      "summary": null
    }
  ],
  "chain_summary": null,
  "final_status": "pending"
}
```

### Field Reference

| Field | Description |
|-------|-------------|
| `orchestrator_directives` | Injected between phases. If contains "STOP", agent halts immediately. |
| `notes_for_next` | Critical context for the next agent: exact names, signatures, schema changes. |
| `deviations` | Differences from the plan (renamed methods, skipped steps, alternative approaches). |
| `cascading_impacts` | Changes that affect phases beyond the immediate next one. |

---

## Orchestrator-Gated Workflow

The orchestrator reviews the chain log between every phase. Agents do not spawn
the next session themselves.

```
Orchestrator spawns Phase 1 agent
         |
         v
Orchestrator sets a timer (see sleep heuristics)
         |
         v
Agent completes --> updates chain log --> STOPS
         |
         v
Orchestrator wakes --> reads chain log
         |
    +----+-------------------+
    v                        v
 Clean run             Deviations found
    |                        |
    |                  Update downstream
    |                  phase instructions
    |                        |
    +----------+-------------+
               v
Orchestrator spawns Phase 2 agent
         |
         v
    (repeat cycle)
```

### Agent Steps (Per Phase)

1. Read chain log -- check `orchestrator_directives` first, then previous phase `notes_for_next`
2. Mark your session `"status": "in_progress"` with `started_at` timestamp
3. Execute the phase tasks
4. Update your session: `tasks_completed`, `deviations`, `notes_for_next`, `cascading_impacts`, `summary`
5. Mark `"status": "complete"` with `completed_at` timestamp
6. Commit the chain log update and **stop** (do not spawn the next phase)

---

## Dynamic Sleep Heuristics

The orchestrator must maintain an active timer to avoid stalling when an agent
finishes. If no timer is pending, nothing will wake the orchestrator.

| Phase complexity | Initial timer | Follow-up timer |
|------------------|---------------|-----------------|
| Light (< 1 hour) | 10 min | 5 min |
| Medium (1-2 hours) | 15 min | 10 min |
| Heavy (2+ hours) | 20 min | 10 min |

**Rule:** Never wait longer than 15 minutes without checking the chain log.

When the timer fires:
- Agent still working --> start a shorter follow-up timer
- Agent complete --> review chain log, adjust downstream instructions, spawn next
- Agent blocked or failed --> alert the user

---

## Phase Planning Table

| Phase | Title | Color | Dependencies | Agent Type | Est. Time |
|-------|-------|-------|-------------|------------|-----------|
| 1 | {phase_1_title} | #4CAF50 | None | {type} | {time} |
| 2 | {phase_2_title} | #2196F3 | Phase 1 | {type} | {time} |
| 3 | {phase_3_title} | #9C27B0 | Phase 2 | {type} | {time} |
| 4 | {phase_4_title} | #FF9800 | Phase 3 | {type} | {time} |
| 5 | {phase_5_title} | #F44336 | Phase 4 | {type} | {time} |

Add or remove rows as needed. Mark phases that can run in parallel.

---

## Orchestrator Review Checklist (Between Phases)

Run through this list every time an agent completes before spawning the next:

- [ ] Read `notes_for_next` -- do the next phase instructions still match?
- [ ] Read `deviations` -- did the agent rename methods, tables, or event types?
- [ ] Read `cascading_impacts` -- do phases beyond the next one need updates?
- [ ] Check `blockers_encountered` -- anything requiring user input?
- [ ] Update downstream phase instructions if any assumptions changed
- [ ] Add `orchestrator_directives` to the chain log if agents need warnings
- [ ] Decide: can the next two phases run in parallel?
- [ ] Spawn the next phase

---

## Agent Handover Template

Include this structure in each phase's instruction file:

```markdown
## Phase Instructions

**Read first:** {path/to/this_phase_instructions.md}
**Branch:** feature/{project}-{short-description}
**Chain log:** {project}_chain/chain_log.json

### Tasks
1. {Task description with file paths and specifics}
2. {Task description}

### Success Criteria
- [ ] {Criterion 1}
- [ ] {Criterion 2}

### Chain Execution
1. Read chain log -- check directives and previous notes
2. Mark session in_progress
3. Execute tasks above
4. Update chain log with results, deviations, and notes for next
5. Mark session complete and STOP
```

---

## Lessons Learned

**Agent prints commands instead of running them**
Include explicit instructions: "Use your shell tool to EXECUTE this command, do not just display it."

**Deviations in phase N break phase N+2**
Use orchestrator-gated mode. The orchestrator reviews every phase before spawning the next and updates downstream instructions.

**Orchestrator goes idle and chain stalls**
Always maintain a background timer. When it fires, check the chain log. Start another timer if work is still in progress.

**Duplicate sessions spawned**
Ensure only the orchestrator spawns terminals. Agents must STOP after completing, never spawn the next phase.

**Agent lacks context from previous phase**
Write specific `notes_for_next` entries: exact class names, method signatures, column names, file paths. Avoid vague summaries.

**Permission prompts block autonomous execution**
Use your tool's auto-approve flag to bypass interactive confirmations during chain execution.

---

## Quick Start

1. Copy this template into your repository
2. Fill in the placeholders (`{project}`, `{phase_N_title}`, etc.)
3. Create the chain log JSON with all sessions pre-defined
4. Write self-contained instructions for each phase
5. Commit everything to a feature branch
6. Spawn Phase 1 and start your orchestrator timer
