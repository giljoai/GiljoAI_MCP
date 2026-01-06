# Alpha Test Findings - Claude Code CLI Mode
**Date:** 2026-01-02
**Tester:** Claude Opus 4.5 (Orchestrator)
**Test Project:** TinyContacts (F:\TinyContacts)
**MCP Server Version:** 3.1.0

---

## Executive Summary

Two full staging → implementation cycles were completed testing the GiljoAI MCP orchestration server in Claude Code CLI mode. The core workflow functions correctly, but several issues were identified related to message routing, status synchronization, and protocol gaps.

**Overall Assessment:** System is functional for basic orchestration. Issues are primarily in messaging subsystem and dashboard synchronization.

---

## Test Runs Completed

### Test 1: Project "Project 1 TinyContacts Start Claude code CLI"
- Project ID: `ca054e78-aa3f-4af6-ac59-05f30496ac67`
- Agents: analyzer, documenter, reviewer (sequential)
- Result: Completed with messaging issues identified

### Test 2: Project "Test project 2 Repeat of 001 TinyContacts claude code CLI"
- Project ID: `e97a542c-1783-4cb7-b50c-c235ce00dff5`
- Agents: analyzer, documenter, reviewer (sequential)
- Result: Completed, broadcast fix verified working

---

## Issues Found

### CRITICAL: Message Status Discrepancy (Dashboard vs API)

**Severity:** High
**Component:** Message subsystem / Dashboard

**Symptom:**
- Dashboard shows messages with status "waiting" for agents
- `list_messages` API returns same messages with status "acknowledged"
- `receive_messages` returns 0 messages (empty queue)

**Example:**
```
Dashboard: documenter has 2 messages "waiting"
list_messages: Same 2 messages show status "acknowledged"
receive_messages: Returns count: 0
```

**Impact:** Dashboard shows inaccurate message state, confusing for users monitoring agent progress.

**Possible Causes:**
1. Status enum mismatch: Dashboard uses "waiting", API uses "pending"/"acknowledged"
2. Acknowledgment not persisting to DB correctly
3. Dashboard querying different table/view than API

---

### FIXED: Broadcast Message Routing

**Severity:** High (was critical, now fixed)
**Component:** send_message / message routing

**Issue in Test 1:**
- `send_message(to_agents=["all"])` stored `to_agent="all"` literally
- `receive_messages(agent_id="specific-uuid")` couldn't match "all"
- Result: Broadcasts never reached agents

**Fix Verified in Test 2:**
- Broadcast now expands "all" to individual agent_ids:
```json
"to_agents": [
  "fa39d78e-7b91-4bb2-92a2-75cf5f49152f",
  "4f9f6b29-94e5-4bdd-951d-bdb61185d7db",
  "33ea7368-f926-4d93-b029-0d3f922a8078"
]
```
- Orchestrator successfully received messages from documenter and reviewer

---

### MEDIUM: job_id vs agent_id Confusion in Implementation Prompt

**Severity:** Medium
**Component:** Prompt generation (gil_launch / implementation prompt)

**Issue:**
- Staging prompt provided: `job_id: c6cc75c7-c41c-4c14-b7db-b3310b3ef6c8`
- Implementation prompt provided: `job_id: bfe5d0f9-07ce-431f-80ab-2feb8ab7c2e9` (this was actually the agent_id)

**Impact:**
- `get_agent_mission(job_id="wrong-id")` returns NOT_FOUND
- Orchestrator must know to use the correct job_id from staging

**Root Cause:**
Implementation prompt generator using `agent_id` field where it should use `job_id`.

**Location to Fix:**
Check the code that generates the `/gil_launch` implementation prompt - it's mapping the wrong identifier.

---

### MEDIUM: Progress Reporting Not Reaching 100%

**Severity:** Medium
**Component:** Protocol adherence / report_progress

**Issue in Test 1:**
- Orchestrator had 6 todos
- Final `report_progress()` sent 5/6 (83%)
- `complete_job()` called without sending 6/6 (100%)
- Dashboard showed "Steps 5/6" even after job completed

**Root Cause:**
Protocol says "sync TodoWrite with report_progress" but doesn't explicitly require 100% progress before `complete_job()`.

**Suggestion:**
Either:
1. Add explicit step to protocol: "Report 100% progress before calling complete_job()"
2. Have `complete_job()` auto-set progress to 100%

---

### MEDIUM: list_messages agent_id Filter Broken

**Severity:** Medium
**Component:** list_messages tool

**Issue:**
```python
list_messages(agent_id="4f9f6b29-94e5-4bdd-951d-bdb61185d7db")
# Returns: "error": "Job 4f9f6b29-94e5-4bdd-951d-bdb61185d7db not found"
```

**Impact:** Cannot filter messages by agent_id - tool treats it as job_id.

---

### LOW: Dashboard Display Issues

**Severity:** Low
**Component:** Dashboard UI

**Issues:**
- "From Agent ID" shows "User" instead of actual agent_id
- "To Agent ID" shows "Broadcast" instead of expanded agent_ids
- May be cosmetic only, but confusing for debugging

---

### LOW: report_progress Routes to Self

**Severity:** Low (by design?)
**Component:** report_progress / message routing

**Observation:**
Progress messages created by `report_progress()` have:
```json
"from_agent": "79e45c00-...",
"to_agent": "79e45c00-..."  // Same as from_agent
```

Progress messages route to the sender, not to orchestrator. This means orchestrators can only see progress via `get_workflow_status()`, not via message queue.

**Question:** Is this intentional? Should progress be routable to orchestrator?

---

## Protocol Gaps Identified

### Missing: Project Closeout Procedure

**Issue:** No instructions or tools for:
- Marking project as complete (vs job complete)
- Setting project completion timestamp
- Writing 360 memory at project end
- Final project summary

**Current State:**
- `complete_job()` exists for jobs
- No `complete_project()` tool
- No 360 memory write instructions

**Recommendation:** Add Phase 5: PROJECT CLOSEOUT to protocol with:
1. Verify `get_workflow_status()` shows 100%
2. Write 360 memory capturing outcomes
3. Call `complete_project(project_id, summary)`

---

### Missing: Agent Experience Report Instructions

**Issue:** In Test 1, experience reports were only generated because explicit alpha testing instructions were added to agent prompts. Standard protocol doesn't include self-assessment.

**Consideration:** May want optional "reflection" phase for agents to document:
- What worked well
- Issues encountered
- Suggestions for improvement

---

## Agent Feedback (from Test 1 Experience Reports)

### Documenter Agent Feedback (9/10 rating)
- Protocol mostly clear
- Confusion: Progress reporting frequency ("after every todo felt excessive")
- Confusion: Broadcast message echo (received own broadcast back)
- Suggestion: Add message handling examples to protocol

### Reviewer Agent Feedback (9/10 rating)
- 19 MCP tool calls, 0 errors (100% success rate)
- Confusion: When to notify downstream agents
- Suggestion: Add downstream notification examples
- Suggestion: Auto-calculate progress percent in backend

---

## What Worked Well

1. **Thin-client architecture** - Mission stored server-side, agents fetch via `get_agent_mission()`
2. **Sequential agent execution** - Dependency chain worked correctly
3. **MCP tools reliability** - Zero tool call errors across both tests
4. **TodoWrite integration** - Helped agents plan and track work
5. **Broadcast fix (Test 2)** - Messages now route to individual agents
6. **Agent coordination** - Analyzer → Documenter → Reviewer handoffs successful

---

## Recommended Fixes (Priority Order)

### P0 - Critical
1. **Message status discrepancy** - Dashboard/API showing different status values

### P1 - High
2. **job_id in implementation prompt** - Use correct job_id, not agent_id
3. **list_messages agent_id filter** - Fix "Job not found" error when filtering by agent_id

### P2 - Medium
4. **Progress 100% before complete** - Either enforce in protocol or auto-set
5. **Project closeout tools** - Add `complete_project()` and 360 memory write

### P3 - Low
6. **Dashboard display** - Show actual agent_ids instead of "User"/"Broadcast"
7. **Protocol examples** - Add message handling and downstream notification examples

---

## Files Created During Testing

### Test 1 (Project 1)
- F:\TinyContacts\docs\folder-structure.md
- F:\TinyContacts\docs\index.md
- F:\TinyContacts\README.md
- F:\TinyContacts\backend\requirements.txt
- F:\TinyContacts\REVIEW_REPORT.md
- F:\TinyContacts\AGENT_EXPERIENCE_REPORT_documenter.md
- F:\TinyContacts\AGENT_EXPERIENCE_REPORT_reviewer.md
- 17 folder README.md files

### Test 2 (Project 2)
- Same deliverables regenerated/verified
- No experience reports (not requested)

---

## Reproduction Steps

### To Reproduce Message Status Discrepancy:
1. Create project, spawn agents
2. Send broadcast message via `send_message(to_agents=["all"])`
3. Check dashboard - shows "waiting" status
4. Call `list_messages()` - shows "acknowledged" status
5. Call `receive_messages(agent_id=X)` - returns empty

### To Reproduce job_id Issue:
1. Complete staging phase, note orchestrator job_id
2. Run `/gil_launch`
3. Note the job_id in implementation prompt
4. Compare - they may be different (agent_id used instead of job_id)

---

## Appendix: Key Identifiers from Test 2

```
Orchestrator:
- job_id: ae6eed1b-3a94-4c32-970b-8b3fdd185d37
- agent_id: f8772c71-8334-4db5-b638-364d1892bc95

Analyzer:
- job_id: b2649320-0e3e-481e-9543-f04ae88d531c
- agent_id: fa39d78e-7b91-4bb2-92a2-75cf5f49152f

Documenter:
- job_id: 683b939f-5702-4004-a099-1b270731c5f4
- agent_id: 4f9f6b29-94e5-4bdd-951d-bdb61185d7db

Reviewer:
- job_id: b9b7a2fb-0259-4879-9186-994cbc23e575
- agent_id: 33ea7368-f926-4d93-b029-0d3f922a8078

Project ID: e97a542c-1783-4cb7-b50c-c235ce00dff5
Tenant Key: ***REMOVED***
```

---

**End of Report**
