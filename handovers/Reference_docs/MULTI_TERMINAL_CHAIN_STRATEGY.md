# Multi-Terminal Chain Execution Strategy

**Created**: 2026-01-18
**Purpose**: Document the proven pattern for spawning chained Claude Code terminal sessions with pre-loaded prompts for sequential handover execution.

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| **3.0** | 2026-03-27 | **Orchestrator-Gated Mode** (preferred). Agents no longer auto-spawn the next terminal. Orchestrator reviews chain log between sessions, adjusts downstream handovers, then spawns the next. Dynamic sleep pattern for orchestrator liveness. |
| 2.0 | 2026-01-30 | Added Chain Log Pattern, Handover Document Structure, Slim Launch Prompts |
| 1.0 | 2026-01-18 | Initial document: core syntax, color scheme, prompt files |

---

## Executive Summary

Two execution modes exist for chaining Claude Code terminal sessions:

| | **Auto-Chain (v2)** | **Orchestrator-Gated (v3, preferred)** |
|---|---|---|
| Who spawns next? | The completing agent | The orchestrator |
| Orchestrator role | Passive monitor (sleep + check) | Active gatekeeper (review + adjust + spawn) |
| Cascade protection | None — next agent may run on stale instructions | Full — orchestrator updates handovers before spawn |
| Parallel potential | None — strictly sequential | Orchestrator can spawn 2+ if dependencies allow |
| Risk | Bad deviation propagates undetected | Orchestrator must stay alive (see Dynamic Sleep) |

**Use Orchestrator-Gated mode by default.** Only use Auto-Chain for simple, low-risk chains where deviations are unlikely.

---

## Pre-Chain Setup (Both Modes)

Before spawning the first terminal, the orchestrator must complete this setup ceremony. These steps protect master and establish the communication channel.

### Step 1: Write All Handovers

Write all handover documents in the series. Each must be self-contained — an agent with zero prior context must be able to execute it. Include:
- Full task details with file paths, line numbers, and code patterns
- Mandatory pre-work reading list (HANDOVER_INSTRUCTIONS.md, spec doc, etc.)
- Chain execution instructions (gated or auto-chain)
- Subagent type recommendations
- Success criteria and rollback plan

### Step 2: Create the Chain Log

Create `prompts/{chain_id}_chain/chain_log.json` with all sessions pre-defined. This is the inter-agent communication file — every agent reads it before starting and writes to it before stopping.

### Step 3: Update the Handover Catalogue

Add all new handovers to `handovers/handover_catalogue.md` in the Active section.

### Step 4: Clean Commit to Master

Commit all handover documents, the chain log, and catalogue update to master. This gives a clean rollback point if the chain goes wrong.

```bash
git add handovers/0XXXa_*.md handovers/0XXXb_*.md ... handovers/handover_catalogue.md prompts/0XXX_chain/chain_log.json
git commit -m "docs: 0XXXa-e [Series Name] handover series + chain log"
```

### Step 5: Create and Publish Feature Branch

All chain work happens on a feature branch — never directly on master.

```bash
git checkout -b feature/0XXX-short-description
git push -u origin feature/0XXX-short-description
```

### Step 6: Spawn First Terminal

Now the orchestrator spawns the first agent on the feature branch. Include the branch name in the launch prompt so the agent knows where it is.

---

## Chain Log Specification

### Location

`prompts/{chain_id}_chain/chain_log.json`

### Full Schema with Field Descriptions

```json
{
  "chain_id": "0842",
  "chain_name": "Vision Document Analysis Feature",
  "created_at": "2026-03-27",
  "spec_document": "handovers/VISION_DOC_ANALYSIS_SPEC_v2.md",
  "branch": "feature/0842-vision-doc-analysis",
  "total_sessions": 5,
  "orchestrator_notes": "Free-text instructions for all agents.",
  "orchestrator_directives": [],
  "sessions": [ ],
  "chain_summary": null,
  "final_status": "pending"
}
```

### Top-Level Fields

| Field | Type | Description |
|-------|------|-------------|
| `chain_id` | string | Handover series number (e.g., "0842") |
| `chain_name` | string | Human-readable name for the chain |
| `created_at` | string | ISO date when chain was created |
| `spec_document` | string | Path to the feature spec (relative to repo root) |
| `branch` | string | Git branch all agents work on |
| `total_sessions` | integer | Number of sessions in the chain |
| `orchestrator_notes` | string | Standing instructions for all agents (read on startup) |
| `orchestrator_directives` | string[] | Injected between sessions by the orchestrator. Agents check this FIRST. If contains "STOP", agent halts immediately. |
| `sessions` | array | Ordered list of session objects (see below) |
| `chain_summary` | string\|null | Written by the final agent or orchestrator on chain completion |
| `final_status` | string | `"pending"` \| `"in_progress"` \| `"complete"` \| `"blocked"` \| `"failed"` |

### Session Object Fields

| Field | Type | Written by | Description |
|-------|------|-----------|-------------|
| `session_id` | string | Orchestrator (setup) | Handover ID (e.g., "0842a") |
| `title` | string | Orchestrator (setup) | Short description |
| `handover` | string | Orchestrator (setup) | Path to handover document |
| `color` | string | Orchestrator (setup) | Terminal tab color hex |
| `status` | string | Agent | `"pending"` \| `"in_progress"` \| `"complete"` \| `"blocked"` \| `"failed"` |
| `started_at` | string\|null | Agent | ISO timestamp when agent began |
| `completed_at` | string\|null | Agent | ISO timestamp when agent finished |
| `agent_types` | string[] | Orchestrator (setup) | Recommended subagent types |
| `planned_tasks` | string[] | Orchestrator (setup) | What should be done |
| `tasks_completed` | string[] | Agent | What was actually done |
| `deviations` | string[] | Agent | Differences from plan (method name changes, skipped steps, alternative approaches) |
| `blockers_encountered` | string[] | Agent | Issues that blocked progress |
| `notes_for_next` | string\|null | Agent | **Critical context for the next agent.** Include exact class names, method signatures, column names, event types — anything the next handover references that the agent might have named differently. |
| `cascading_impacts` | string[] | Agent | Changes that affect downstream handovers (not just the next one). Orchestrator reads these to decide if handover files need updating. |
| `summary` | string\|null | Agent | 2-3 sentence summary of what was accomplished, including commit hash. |

### Rules for Agents

1. **Read before starting**: Check `orchestrator_directives` first, then review previous session's `notes_for_next`
2. **Write before stopping**: Fill in ALL fields in your session — `tasks_completed`, `deviations`, `notes_for_next`, `cascading_impacts`, `summary`
3. **Be specific in `notes_for_next`**: Don't write "model created." Write "Model class: VisionDocumentSummary at src/giljo_mcp/models/products.py:659. Ratio uses Decimal('0.33'). Source values: 'sumy' and 'ai'."
4. **Commit the chain log update**: `git commit -m "docs: 0XXXa chain log — session complete"`

### Rules for Orchestrator

1. **Read `deviations` and `cascading_impacts`** before spawning the next terminal
2. **Update downstream handover files** if any assumption changed (field names, method signatures, event types)
3. **Add to `orchestrator_directives`** if agents need warnings or adjusted instructions
4. **Set `final_status`** when chain completes or is abandoned

---

## Orchestrator-Gated Mode (v3) — Preferred

### How It Works

```
Orchestrator spawns Agent A
         │
         ▼
Orchestrator sleeps (dynamic timer)
         │
         ▼
Agent A completes → updates chain_log.json → STOPS (does NOT spawn next)
         │
         ▼
Orchestrator wakes → reads chain_log.json
         │
    ┌────┴────────────────┐
    ▼                     ▼
 Clean run            Deviations/issues
    │                     │
    │                 Updates downstream
    │                 handovers if needed
    │                     │
    └────────┬────────────┘
             ▼
Orchestrator spawns Agent B
         │
         ▼
    (repeat cycle)
```

### Dynamic Sleep Pattern (CRITICAL)

**The orchestrator MUST use active sleep timers to stay alive.** If the orchestrator goes passive (no pending sleep timer), nothing will wake it up when an agent finishes. The conversation will stall.

**Pattern:**
```
1. Spawn agent terminal
2. Estimate work duration from handover complexity
3. Start background sleep timer: `sleep <seconds> && echo "WAKE"` (run_in_background)
4. When timer fires, read chain_log.json
5. If agent still in_progress → start another shorter sleep
6. If agent complete → review, adjust, spawn next
7. If agent blocked/failed → alert user
```

**Duration heuristics:**
| Handover complexity | Initial sleep | Follow-up sleep |
|--------------------|--------------|-----------------|
| Light (0.5-1h est) | 10 min | 5 min |
| Medium (1-2h est) | 15 min | 10 min |
| Heavy (2h+ est) | 20 min | 10 min |

**Anti-stall rule:** Never sleep longer than 15 minutes without checking. If an agent finishes in 5 minutes and you're sleeping for 30, that's 25 minutes of wasted wall-clock time.

### Agent Handover Template (Orchestrator-Gated)

The key difference: Step 5 says **STOP**, not "spawn next terminal."

```markdown
## Chain Execution Instructions

### Step 1: Read Chain Log
Read `prompts/0XXX_chain/chain_log.json`
- Check `orchestrator_directives` — if STOP, halt immediately
- Review previous session's `notes_for_next`
- Verify previous session status is `complete`

### Step 2: Mark Session Started
Update your session: `"status": "in_progress", "started_at": "<timestamp>"`

### Step 3: Execute Handover Tasks
[Standard implementation work]

### Step 4: Update Chain Log
Update your session with:
- `tasks_completed`, `deviations`, `blockers_encountered`
- `notes_for_next`: Critical info for the next agent
- `cascading_impacts`: Changes that affect downstream handovers
- `summary`, `status`: "complete", `completed_at`

### Step 5: STOP
**Do NOT spawn the next terminal.** The orchestrator will review your
results, adjust downstream handovers if needed, and spawn the next session.
Commit your chain log update and exit.
```

### Orchestrator Review Checklist (Between Spawns)

When the orchestrator wakes and finds a completed session:

1. **Read `notes_for_next`** — does the next handover's assumptions still hold?
2. **Read `deviations`** — did the agent change method signatures, table names, event types?
3. **Read `cascading_impacts`** — do downstream handovers need updating?
4. **Check `blockers_encountered`** — anything that needs user input?
5. **Update downstream handover files** if any assumptions changed
6. **Add `orchestrator_directives`** to chain log if needed (e.g., warnings, adjusted instructions)
7. **Decide parallel vs sequential** — can the next 2 handovers run simultaneously?
8. **Spawn the next terminal**

### Chain Log Schema (v3 — Extended)

```json
{
  "chain_id": "0842",
  "chain_name": "Vision Document Analysis Feature",
  "created_at": "2026-03-27",
  "spec_document": "handovers/VISION_DOC_ANALYSIS_SPEC_v2.md",
  "branch": "feature/0842-vision-doc-analysis",
  "total_sessions": 5,
  "orchestrator_notes": "Agents: read this file BEFORE starting. If orchestrator_directives contains STOP, halt immediately.",
  "orchestrator_directives": [],
  "sessions": [
    {
      "session_id": "0842a",
      "title": "Database Schema",
      "handover": "handovers/0842a_db_migration.md",
      "color": "#4CAF50",
      "status": "pending",
      "started_at": null,
      "completed_at": null,
      "agent_types": ["database-expert", "tdd-implementor"],
      "planned_tasks": ["Task 1", "Task 2"],
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

**v3 additions over v2 schema:**
- `orchestrator_directives`: Array of strings the orchestrator can inject between sessions (STOP instructions, warnings, adjusted parameters)
- `cascading_impacts`: Per-session field for changes that affect downstream handovers
- `branch`: The git branch all agents work on

---

## Auto-Chain Mode (v2) — Legacy

In this mode, each agent spawns the next terminal on completion. The orchestrator monitors passively via sleep-and-check cycles but has no gate between sessions.

### When to Use Auto-Chain

- Simple chains (3 or fewer sessions)
- Low-risk work where deviations are unlikely
- Each handover is truly independent (no cascading field mappings, shared APIs, etc.)

### Chain Log Workflow (Auto-Chain)

**First Handover:**
1. CREATE the chain_log.json
2. Set own session to `in_progress`
3. Do the work
4. Update session with results, set `complete`
5. **Spawn next terminal**

**Subsequent Handovers:**
1. READ chain_log.json
2. Verify previous session `complete`
3. Set own session to `in_progress`
4. Do the work
5. Update session, set `complete`
6. **Spawn next terminal** (or mark chain complete if last)

### Handover Template (Auto-Chain)

```markdown
## Chain Execution Instructions

### Step 5: Spawn Next Terminal
**Use Bash tool to EXECUTE (don't just print!):**
\```powershell
powershell.exe -Command "Start-Process wt -ArgumentList '--title \"0XXXb - Title\" --tabColor \"#2196F3\" -d \"F:\GiljoAI_MCP\" cmd /k claude --dangerously-skip-permissions \"Execute handover 0XXXb. READ FIRST: F:\GiljoAI_MCP\handovers\0XXXb_title.md\"' -Verb RunAs"
\```

**CRITICAL: DO NOT SPAWN DUPLICATE TERMINALS.**
```

---

## Core Syntax (Both Modes)

### Terminal Spawn Command (PowerShell)

```powershell
powershell.exe -Command "Start-Process wt -ArgumentList '--title \"TITLE\" --tabColor \"#HEX\" -d \"WORKDIR\" cmd /k claude --dangerously-skip-permissions \"YOUR PROMPT\"' -Verb RunAs"
```

### Parameter Breakdown

| Parameter | Purpose | Example |
|-----------|---------|---------|
| `--title` | Tab/window title for identification | `"0842a - DB Migration"` |
| `--tabColor` | Hex color for visual tracking | `"#4CAF50"` (green) |
| `-d` | Working directory | `"F:\GiljoAI_MCP"` |
| `cmd /k` | Keep terminal open after command | Required for interactive session |
| `claude` | Claude Code CLI | The AI agent |
| `--dangerously-skip-permissions` | Bypass all permission prompts | **CRITICAL** - enables autonomous execution |
| `"YOUR PROMPT"` | Initial prompt passed to Claude | The mission instructions |
| `-Verb RunAs` | Run as Administrator | Required for elevated permissions |

### Color Scheme (Visual Progress Tracking)

| Phase | Color | Hex | Meaning |
|-------|-------|-----|---------|
| Phase 1 | Green | `#4CAF50` | Foundation/Database |
| Phase 2 | Blue | `#2196F3` | Backend changes |
| Phase 3 | Purple | `#9C27B0` | Backend (secondary) |
| Phase 4 | Orange | `#FF9800` | Frontend changes |
| Phase 5 | Red | `#F44336` | Final/Testing |

---

## Slim Launch Prompts

Launch prompts should be minimal — just enough to start Claude and point to the handover:

```powershell
powershell.exe -Command "Start-Process wt -ArgumentList '--title \"0842a - DB Migration\" --tabColor \"#4CAF50\" -d \"F:\GiljoAI_MCP\" cmd /k claude --dangerously-skip-permissions \"Execute handover 0842a. READ FIRST: F:\GiljoAI_MCP\handovers\0842a_VISION_DOC_ANALYSIS_DB_MIGRATION.md — Read the ENTIRE document including Chain Execution Instructions at the bottom. You are session 1 of 5 in the 0842 chain. Use database-expert and tdd-implementor subagents. You are on branch feature/0842-vision-doc-analysis.\"' -Verb RunAs"
```

The handover document contains:
- Full task details
- Chain log instructions
- Subagent recommendations
- Success criteria
- Pre-work reading requirements

---

## Subagent Mapping by Handover Type

| Handover Type | Recommended Subagents |
|---------------|----------------------|
| Database/Schema | `database-expert`, `tdd-implementor` |
| Backend Code | `tdd-implementor`, `backend-tester` |
| Frontend Code | `ux-designer`, `frontend-tester` |
| MCP Tools | `tdd-implementor` |
| Test Updates | `backend-tester`, `tdd-implementor` |
| Documentation | `documentation-manager` |

---

## Lessons Learned

### Problem: Trust/Permission Prompts Block Execution
**Solution**: Use `--dangerously-skip-permissions` flag

### Problem: Agent Displays Spawn Command Instead of Running It
**Solution**: Add explicit instruction: "Use Bash tool to RUN this command" and "Don't Just Print It!"

### Problem: Agent Doesn't Know Handover Document Location
**Solution**: Include explicit path in both initial prompt AND prompt file with "READ THIS FIRST"

### Problem: Agent Does Work Directly Instead of Using Subagents
**Solution**: Add "CRITICAL" section with examples showing Task tool syntax

### Problem: Terminal Doesn't Have Admin Rights
**Solution**: Add `-Verb RunAs` to PowerShell command

### Problem: Duplicate Terminals Spawned
**Cause**: Both the subagent AND the main agent execute the spawn command
**Solution**: Add explicit instruction: "CRITICAL: DO NOT SPAWN DUPLICATE TERMINALS! Only ONE agent should spawn the next terminal. If your subagent already spawned it, DO NOT spawn again."

### Problem: Deviation in session N breaks session N+2 (v2 auto-chain)
**Cause**: Agent N+1 spawns N+2 before orchestrator can review N's deviations and update N+2's handover
**Solution**: Use Orchestrator-Gated mode (v3). Agents STOP after completing. Orchestrator reviews chain log, updates downstream handovers, then spawns.

### Problem: Orchestrator goes passive and chain stalls (v3)
**Cause**: No active sleep timer running — nothing wakes the orchestrator when an agent finishes
**Solution**: Always maintain a background sleep timer. When it fires, check the chain log. If the agent is still working, start another timer. Never go passive without a pending timer.

---

## Implementation Checklist

### Setup Phase
- [ ] Create `prompts/{project}_chain/` directory
- [ ] Create chain_log.json with all sessions pre-defined
- [ ] Write self-contained handover document for each session
- [ ] Include mandatory pre-work reading list in each handover
- [ ] Include chain execution instructions (gated or auto) in each handover
- [ ] Use distinct colors for each phase
- [ ] Create feature branch (protect master)

### Orchestrator Responsibilities (v3)
- [ ] Spawn first terminal
- [ ] Start dynamic sleep timer
- [ ] On wake: read chain_log.json
- [ ] If agent still working: start another shorter timer
- [ ] If agent complete: review deviations + cascading impacts
- [ ] Update downstream handovers if needed
- [ ] Add orchestrator_directives if needed
- [ ] Spawn next terminal
- [ ] Repeat until chain complete

### Per-Handover Requirements
- [ ] Mission statement and task summary
- [ ] Handover document path (READ THIS FIRST)
- [ ] Mandatory pre-work reading list
- [ ] CRITICAL subagent instruction with agent types
- [ ] Prerequisite check (for non-first handovers)
- [ ] Success criteria
- [ ] Chain execution instructions (STOP for v3, spawn command for v2)

---

## Historical Results

### 0842 Vision Document Analysis (v3 Orchestrator-Gated, March 2026)

**Total Execution**: 5 chained terminals (orchestrator-gated)
**Chain**: 0842a (Green) → 0842b (Blue) → 0842c (Purple) → 0842d (Orange) → 0842e (Red)
**Pattern**: Orchestrator reviewed chain log between each session, no cascading issues detected

### 0387 Phase 4 JSONB Normalization (v2 Auto-Chain, January 2026)

**Total Execution**: 5 chained terminals (auto-chain)
**Files Changed**: 75 files, 8,321 insertions, 919 deletions
**New Files**: 27 created
**Tests**: 3,743 collected, core tests passing
**Outcome**: Complete JSONB normalization with counter-based architecture

Chain Completion Log:
1. 0387e - Counter columns added, 7 TDD tests pass
2. 0387f - JSONB writes removed, counters used
3. 0387g - Frontend updated to use counters
4. 0387h - Tests updated, fixtures cleaned
5. 0387i - Column deprecated, docs updated, merged to master

---

## Troubleshooting

### Terminal Opens But Claude Doesn't Start
- Check Windows Terminal is installed
- Verify `claude` is in PATH
- Check for syntax errors in ArgumentList

### Claude Starts But Prompt Not Loaded
- Ensure prompt is properly escaped in quotes
- Check for special characters that need escaping
- Verify prompt length isn't exceeding limits

### Agent Doesn't Spawn Next Terminal (v2 only)
- Check if agent printed command vs executed it
- Verify Bash tool is available
- Manually run the spawn command if needed

### Permission Denied Errors
- Ensure `-Verb RunAs` is included
- Accept UAC prompt when it appears
- Verify `--dangerously-skip-permissions` is present

### Orchestrator Stalls (v3)
- Check if a background sleep timer is pending
- If no timer: start one immediately (`sleep 300 && echo "WAKE"`)
- Read chain_log.json to see current state
- If agent completed but orchestrator missed it: review and spawn next
