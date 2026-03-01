# 0750c2: Fix get_project_summary Status Strings

**Series:** 0750 (Code Quality Cleanup Sprint) — Point Fix
**Branch:** `0750-cleanup-sprint`
**Priority:** HIGH — dashboard shows 0% completion for all projects

### Reference Documents
- **Orchestrator handover:** `handovers/0700_series/0750_ORCHESTRATOR_HANDOVER.md` (Point Fixes section, item 1)
- **Chain log:** `prompts/0750_chain/chain_log.json`
- **Progress tracker:** `handovers/0700_series/0750_cleanup_progress.json`

---

## Context

The function `get_project_summary` in `src/giljo_mcp/services/project_service.py` (line 1446) returns 0% completion for all projects. The bug: it counts AgentExecution jobs using old status strings (`"completed"`, `"active"`, `"pending"`) that may not match the actual values in the database after the 0491 status migration.

The canonical post-0491 agent statuses are: `waiting`, `working`, `blocked`, `complete`, `silent`, `decommissioned`.

---

## Scope

### Step 1: Verify actual AgentExecution status values

Before changing anything, determine what status values AgentExecution actually uses:

```bash
# Check the AgentExecution model for status enum/column definition
grep -rn "status" src/giljo_mcp/models/agent_execution.py | head -20
```

Also check:
- `src/giljo_mcp/models/agent_identity.py` — the canonical status list
- Any Alembic migration that changed status values (grep for `0491` in `alembic/versions/`)
- The AgentExecution model definition to see if it has its own status enum or shares with AgentIdentity

### Step 2: Fix get_project_summary (line 1446-1565)

In `src/giljo_mcp/services/project_service.py`, fix lines 1501-1504:

```python
# CURRENT (broken):
completed_jobs = job_counts.get("completed", 0)
blocked_jobs = job_counts.get("blocked", 0)
active_jobs = job_counts.get("active", 0)
pending_jobs = job_counts.get("pending", 0)

# FIX (use actual status values from Step 1):
# If post-0491 statuses apply to AgentExecution:
completed_jobs = job_counts.get("complete", 0)
blocked_jobs = job_counts.get("blocked", 0)
active_jobs = job_counts.get("working", 0)
pending_jobs = job_counts.get("waiting", 0)
```

**IMPORTANT:** Only change the status strings if Step 1 confirms AgentExecution uses the post-0491 values. If AgentExecution has its own separate status enum, the fix may be different.

### Step 3: Check for similar bugs in the same file

Lines 1652-1805 have similar status string references in other functions. Check:
- Line 1652: `status_counts["completed"]` — should this be `"complete"`?
- Line 1655: `status_counts["active"]` — should this be `"working"`?
- Line 1687: `status_counts["active"] == 0`
- Line 1701: `"complete": status_counts["completed"]`
- Line 1802: `"completed": completed_agents`
- Line 1805: `"active": active_agents`
- Line 2558: already has both `"completed"` and `"complete"` (suspicious)

For each one: trace where `status_counts` is built and verify the keys match actual DB values.

### Step 4: Run tests

```bash
python -m pytest tests/ -x -q --timeout=60
```

Must still be GREEN: 1238 passed, 522 skipped, 0 failed.

---

## What NOT To Do

- Do NOT change project-level status strings (`"active"`, `"completed"` on Project model). Those may be correct for the Project model — this fix is about AgentExecution status values only.
- Do NOT refactor or restructure the function — only fix the status string values.
- Do NOT modify any other files besides `project_service.py` unless a caller explicitly breaks.

---

## Acceptance Criteria

- [ ] `get_project_summary` uses correct AgentExecution status strings (verified against model/DB)
- [ ] Any other functions in project_service.py with the same bug are also fixed
- [ ] Test suite still GREEN
- [ ] No changes outside `src/giljo_mcp/services/project_service.py`

---

## Completion Steps

### Step 1: Verify branch
```bash
git branch --show-current
# Must show: 0750-cleanup-sprint
```

### Step 2: Commit
```bash
git add src/giljo_mcp/services/project_service.py
git commit -m "fix(0750c2): Fix get_project_summary status strings — use post-0491 values"
```

### Step 3: Record commit hash
```bash
git rev-parse --short HEAD
```

### Step 4: Done
Do NOT update chain_log.json for this point fix — it's a bridge commit between phases.
Do NOT spawn the next terminal.
Print "0750c2 COMPLETE" as your final message.
