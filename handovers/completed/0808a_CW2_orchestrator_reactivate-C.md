# 0808a Research: CW-2 — Orchestrator Cannot Reactivate (reopen_job)

**Handover ID:** 0808a
**Type:** Research / Triage
**Status:** COMPLETE
**Verdict:** SUPERSEDED
**Completed:** 2026-03-06
**Edition Scope:** CE

---

## Original Claim

CW-2: "Orchestrator Cannot Reactivate — no `reopen_job()` tool."

## Verdict: SUPERSEDED

The concern is fully superseded by two mechanisms:

1. **0497e successor spawning** — `spawn_agent_job(predecessor_job_id=X)` creates a NEW AgentJob+AgentExecution with predecessor context injected. Fresh context prevents hallucination drift; completed work is an immutable audit trail.
2. **0498 handover protocol** — Same agent_id/job_id, new terminal, reads 360 Memory for context. Covers orchestrator continuation.

A `reopen_job()` tool would conflict with the Job/Execution separation architecture and violate the database CHECK constraint (one-way status transitions only).

## Key Flows Traced

- `spawn_agent_job()` -> AgentJob(active) + AgentExecution(waiting)
- `complete_job()` -> execution.status=complete, job.status=completed (immutable)
- `spawn_agent_job(predecessor_job_id=X)` -> `_build_predecessor_context()` -> NEW job with predecessor summary
- Simple handover -> same agent_id/job_id, new terminal session

## Implementation Needed

None. Minor cosmetic gap (no blocked->working dashboard transition) does not warrant a tool (~2 hrs if ever desired).

---

**Chain log:** `handovers/0808_tier2_chain_log.json`
