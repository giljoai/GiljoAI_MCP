# 0810a Research: #40 + #41 — Workflow Status Orchestrator Distinction + Per-Agent Status

**Handover ID:** 0810a
**Type:** Research / Triage
**Status:** COMPLETE
**Verdict:** #40: VALID (minor, P3/E1) | #41: SUPERSEDED
**Completed:** 2026-03-06
**Edition Scope:** CE

---

## Original Claims

- **#40:** "Workflow status doesn't distinguish orchestrator from sub-agents" (P2, E1)
- **#41:** "Per-agent status in workflow response" (P2, E2)

## Verdict

**#41: SUPERSEDED** — Commit `a00a863e` (2026-02-28) added `agents[]` array to `get_workflow_status()` with per-agent `job_id`, `agent_id`, `agent_name`, `display_name`, `status`, `unread_messages`, and `todos` breakdown.

**#40: VALID but minor (P3/E1)** — `AgentJob.job_type` stores "orchestrator" in DB and the JOIN fetches it, but `AgentWorkflowDetail` schema discards it. Fix is ~3 lines across 2 files. Practical need is LOW — orchestrator already knows its team composition.

## Key Flows Traced

- MCP tool -> `tool_accessor.get_workflow_status()` -> `orchestration_service` lines 189-355
- DB query JOINs AgentExecution+AgentJob, fetches `job_type` but doesn't surface it
- Per-agent detail includes batch todo query (lines 293-330)
- REST API `WorkflowStatusResponse` does NOT include agents array (separate concern)

## Implementation Needed

Optional: Add `job_type` field to `AgentWorkflowDetail` schema + assign in service loop (~3 lines, 2 files). Not blocking.

---

**Chain log:** `handovers/0808_tier2_chain_log.json`
