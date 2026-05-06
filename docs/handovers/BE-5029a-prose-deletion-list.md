# BE-5029a — Prose deletion list (Phase A audit deliverable)

**Project:** BE-5029 Approval primitive (Phase A)
**Phase:** 0 — Audit & placement decisions (analyzer)
**Edition Scope:** Both (prose contract is in CE-shared protocol/service files; new primitive lives in CE migration chain)
**Author:** analyzer (job `7a3cee64-508d-4b4a-968a-1acf7badddb9`)
**Date:** 2026-05-06

This is the verbatim checklist Phase C will execute. Each row is classified as
**DELETE** (pure prose contract, replace with the new primitive's mechanism),
**UPDATE** (test/assertion that must be rewritten against the new primitive),
or **LEAVE** (unrelated false positive — explained inline).

Phase C scope: replace the `user_approval_required` boolean + the
`set_agent_status(blocked, "Closeout: awaiting user review")` prose contract
with the new `user_approvals` row + `awaiting_user` execution status emitted
by the gate.

---

## 1. `user_approval_required` references

| # | File | Line | Surrounding context | Action | Notes |
|---|------|------|---------------------|--------|-------|
| 1 | `src/giljo_mcp/services/job_completion_service.py` | 211 | `user_approval_required=(closeout_mode == "hitl") and has_deferred,` — kwarg passed into `_build_closeout_checklist` | DELETE | Replace caller with the new gate that creates a `user_approvals` row when HITL+deferred; checklist no longer carries this boolean. |
| 2 | `src/giljo_mcp/services/job_completion_service.py` | 220 | `user_approval_required=True,` — second call site in the same flow | DELETE | Same as row 1 — the kwarg disappears once the gate replaces the prose contract. |
| 3 | `src/giljo_mcp/services/job_completion_service.py` | 447 | `def _build_closeout_checklist(*, user_approval_required: bool) -> dict[str, Any]:` | DELETE | Method signature loses the parameter. If `_build_closeout_checklist` becomes vestigial after the kwarg+key are removed, also delete the method and inline its remaining body at the two callers. |
| 4 | `src/giljo_mcp/services/job_completion_service.py` | 454 | Instruction string: `"If user_approval_required: set status blocked with reason "` | DELETE | This is the prose instruction the new primitive replaces. Remove the entire instruction block (rows 4 + 5 are the same string literal continuation). |
| 5 | `src/giljo_mcp/services/job_completion_service.py` | 455 | Continuation: `"'Closeout: awaiting user review' and present closure options to user. "` | DELETE | Continuation of row 4's f-string. Delete together. |
| 6 | `src/giljo_mcp/services/job_completion_service.py` | 460 | `"user_approval_required": user_approval_required,` — key written into the returned checklist dict | DELETE | The checklist contract loses this key. Phase B/C must confirm no consumer reads it; preliminary search shows only the unit test below. |
| 7 | `src/giljo_mcp/services/protocol_sections/agent_lifecycle.py` | 262 | `→ If user_approval_required=true: set status blocked with reason "Closeout: awaiting user review", present deferred findings and options to user, WAIT for user response` | DELETE | Authoritative prose contract injected into agent missions. This is the line the new primitive is designed to obsolete. Replace with the new gate's instruction (write a `user_approvals` row; agent's status flips to `awaiting_user` automatically). |
| 8 | `src/giljo_mcp/services/protocol_sections/agent_lifecycle.py` | 263 | `→ If user_approval_required=false: proceed with best judgment` | DELETE | Sibling branch of row 7; remove together. The new primitive replaces the boolean branching with "always create a user_approvals row when HITL+deferred; otherwise close cleanly". |
| 9 | `tests/unit/test_hitl_closeout_checkpoint.py` | 118 | `assert "user_approval_required" in checklist` | UPDATE | Rewrite at the new primitive's layer: assert a `user_approvals` row was created (or not) in the DB / via the service; drop the checklist-key assertion. |
| 10 | `tests/unit/test_hitl_closeout_checkpoint.py` | 120 | `assert isinstance(checklist["user_approval_required"], bool)` | UPDATE | Same as row 9 — drop key-shape assertion; assert primitive row instead. |
| 11 | `tests/unit/test_hitl_closeout_checkpoint.py` | 134 | `assert result.closeout_checklist["user_approval_required"] is False` | UPDATE | Rewrite: HITL + no deferred → no `user_approvals` row created (or status != `awaiting_user`). |
| 12 | `tests/unit/test_hitl_closeout_checkpoint.py` | 147 | `assert result.closeout_checklist["user_approval_required"] is True` | UPDATE | Rewrite: HITL + deferred → exactly one `user_approvals` row created and execution status transitioned to `awaiting_user`. |
| 13 | `tests/unit/test_hitl_closeout_checkpoint.py` | 167 | Docstring: `"""When closeout_mode='autonomous', user_approval_required is False."""` | UPDATE | Rewrite docstring against the primitive: "autonomous mode never creates a `user_approvals` row". |
| 14 | `tests/unit/test_hitl_closeout_checkpoint.py` | 193 | `assert result.closeout_checklist["user_approval_required"] is False` | UPDATE | Same as rows 11/12 — primitive-layer assertion. |
| 15 | `tests/unit/test_hitl_closeout_checkpoint.py` | 212 | `assert "user_approval_required" in body` (response body assertion) | UPDATE | If `complete_job`'s response still surfaces a HITL signal, swap the key for whatever the new primitive returns (e.g., `pending_user_approval_id`). If the response no longer surfaces it, delete this assertion. Phase B/C decides shape. |
| 16 | `handovers/completed/0700_series/comms_log.json` | 1030 | `"user_approval_required": true` inside an archived comms log | LEAVE | Historical archive under `handovers/completed/`. The export script strips `handovers/` from the public CE bundle, so this is private-only audit history. Do not edit archived comms logs. |

---

## 2. `Closeout: awaiting user review` references

| # | File | Line | Surrounding context | Action | Notes |
|---|------|------|---------------------|--------|-------|
| 17 | `src/giljo_mcp/services/protocol_sections/agent_lifecycle.py` | 262 | (same line as row 7) | DELETE | Already covered by row 7 — listed here for completeness. The string literal goes when the surrounding instruction is deleted. |
| 18 | `src/giljo_mcp/services/job_completion_service.py` | 455 | (same line as row 5) | DELETE | Already covered by row 5. |
| 19 | `frontend/src/utils/statusConfig.js` | 140 | `description: 'Orchestrator is awaiting user review before project closeout',` — UI status descriptor for the closeout-blocked pseudo-status | UPDATE | Frontend currently keys "Decision Required" off `status === "blocked" && reason === "Closeout: awaiting user review"`. After Phase B introduces `awaiting_user`, this descriptor's keying logic must move to `status === "awaiting_user"`. The descriptor TEXT can stay; the matching logic is what changes. |
| 20 | `frontend/tests/unit/utils/statusConfig.spec.js` | 29 | `const config = getStatusConfig('blocked', 'Closeout: awaiting user review');` | UPDATE | Rewrite around `getStatusConfig('awaiting_user')` once the new status exists. |
| 21 | `frontend/tests/unit/utils/statusConfig.spec.js` | 43 | `expect(isCloseoutBlocked('blocked', 'Closeout: awaiting user review')).toBe(true);` | UPDATE | Either rename `isCloseoutBlocked` → `isAwaitingUser` and re-key on the new status, or update the test to pass `'awaiting_user'`. Coordinate with the frontend slice of Phase B. |
| 22 | `frontend/tests/unit/utils/statusConfig.spec.js` | 66 | `expect(getStatusLabel('blocked', 'Closeout: awaiting user review')).toBe('Decision Required');` | UPDATE | Same as row 21 — re-key on `awaiting_user`. |
| 23 | `frontend/tests/unit/utils/statusConfig.spec.js` | 81 | `expect(getStatusColor('blocked', 'Closeout: awaiting user review')).toBe('#ffc107');` | UPDATE | Same as row 21. |
| 24 | `docs/protocol_injection_audit_2026_05_05.md` | 51 | Audit-table row referencing `agent_lifecycle.py:262` | LEAVE | This is a one-time audit doc dated 2026-05-05 documenting the very prose lines BE-5029 is removing. It is correct as a snapshot. Phase C may optionally append a note that the line was removed; not a blocker. |

---

## 3. `set_agent_status(status="blocked", reason="Closeout...` instruction prose

Grep for `set_agent_status\(status=\"blocked\", reason=\"Closeout` returned **no source-file matches** — the only instruction prose in the codebase that tells agents to flip themselves to `blocked` for HITL is the natural-language line in `agent_lifecycle.py:262` (rows 7/17 above). The pattern was searched both as a literal call-site fragment and as the surrounding "awaiting user review" prose; no other occurrences exist in `src/`, `tests/`, or `frontend/src/`.

`chapters_reference.py`, `agent_protocol.py`, `agent_lifecycle.py`, `thin_prompt_generator.py`, and `template_seeder.py` were searched individually. Only `agent_lifecycle.py:262-263` carries the HITL closeout-blocked instruction. `chapters_reference.py:664` and `agent_lifecycle.py:247-256` mention "Closeout" in unrelated contexts (Phase 3 transition, git-disabled guidance) — those are LEAVE.

| # | File | Line | Surrounding context | Action | Notes |
|---|------|------|---------------------|--------|-------|
| 25 | `src/giljo_mcp/services/protocol_sections/chapters_reference.py` | 664 | `* All agents complete → proceed to Closeout (Phase 3)` | LEAVE | Unrelated — describes orchestrator phase progression, not HITL approval. |
| 26 | `src/giljo_mcp/services/protocol_sections/agent_lifecycle.py` | 247-256 | `**Closeout works without git:**` + `**Closeout steps (order matters):**` | LEAVE | Unrelated — git-availability guidance and closeout step ordering. The HITL-specific lines are 262-263 only (rows 7/8). |
| 27 | `src/giljo_mcp/services/protocol_sections/agent_protocol.py` | 162 | `#### Phase 4 — ORCHESTRATOR ADDENDUM: Closeout sequence` | LEAVE | Unrelated — orchestrator closeout call-order addendum (complete_job → write_360_memory → close_project_and_update_memory). Not HITL. |

---

## 4. Other locations that instruct agents to flip themselves to `blocked` for HITL purposes

None found beyond `agent_lifecycle.py:262-263`. Phase 5 of the lifecycle protocol (rows surfaced inside `agent_protocol.py`) tells agents to use `blocked` for **unclear requirements / waiting for clarification / unrecoverable errors** — that is the legitimate, non-HITL use of `blocked` and must remain. Do not touch it.

---

# Appendix — Placement decisions report

## A1. Authoritative agent-status enum location

**There is no single domain enum.** The agent-status set is defined in three places, none of which is the `domain/` package (the domain enums there cover task and project status only — `domain/task_status.py`, `domain/project_status.py`).

The authoritative locations the implementer must extend with `awaiting_user`:

1. **`src/giljo_mcp/events/models.py:166`** — `valid_statuses = {"waiting", "working", "blocked", "complete", "silent", "decommissioned", "idle", "sleeping"}` inside `AgentStatusChangedData.validate_status_transition`. **MUST add `"awaiting_user"`** or the WebSocket event payload will fail Pydantic validation when the new gate emits the transition. This is the single hard gate on transition payloads.
2. **`src/giljo_mcp/models/agent_identity.py:184`** — `AgentExecution.status` column comment string `"Execution status: waiting, working, blocked, idle, sleeping, complete, closed, silent, decommissioned"`. Update the comment to include `awaiting_user`. **No CHECK constraint exists on this column** — the column accepts any string ≤50 chars at the DB layer. No migration is required to add the value itself; only update the comment.
3. **`src/giljo_mcp/services/orchestration_agent_state_service.py:55`** — `_AGENT_SETTABLE_STATUSES: ClassVar[set[str]] = {"blocked", "idle", "sleeping"}`. **DO NOT add `awaiting_user` here.** This set governs `set_agent_status()` (the agent-callable tool). `awaiting_user` is system-set by the gate, not agent-settable, so it must remain absent from this set or agents will be able to forge approval state.

There is no Alembic migration adding/checking agent-execution status values in the CE chain — searched `migrations/versions/*.py` and the only status-enum migration is `ce_0008_project_status_enum.py` (project status, not agent status). The implementer adds the new value purely at the application layer + comment.

## A2. FK targets for `user_approvals`

**BLOCKER-LEVEL CLARIFICATION** (not a hard blocker, but the project description's FK list is incorrect against the actual schema — implementer needs the corrected list before writing the migration):

The mission lists FKs `agents.id`, `jobs.id`, `projects.id`, `users.id`. The actual CE schema is:

| Mission says | Actual table | Actual PK | CE chain? |
|--------------|--------------|-----------|-----------|
| `agents.id` | **`agent_executions`** (PK `id`, String(36)) — there is no `agents` table; the executor row is `agent_executions` | `agent_executions.id` | **CE** (`models/agent_identity.py:159`) |
| `jobs.id` | **`agent_jobs`** (PK `job_id`, String(36) — note: the column is `job_id`, NOT `id`) | `agent_jobs.job_id` | **CE** (`models/agent_identity.py:63`) |
| `projects.id` | `projects` (PK `id`, String(36)) | `projects.id` | **CE** (`models/projects.py:91-93`) |
| `users.id` | `users` (PK `id`, String(36)) | `users.id` | **CE** (`models/auth.py:75-77`) |

**All four FK targets are CE tables.** None are SaaS-only — confirmed by checking `models/__init__.py` and that none of these tables appear under `migrations/saas_versions/`. **No SaaS-table dependency. No blocker on the design.**

The implementer should:
- Use `String(36)` UUIDs (not native UUID type — this codebase uses string UUIDs throughout, see `base.py:generate_uuid`).
- Reference `agent_executions.id`, `agent_jobs.job_id` (not `.id`), `projects.id`, `users.id`.
- Decide whether the FK to `agent_executions.id` should be `ON DELETE CASCADE` (executor rows are immutable post-completion in this codebase, so SET NULL or RESTRICT is safer; recommend RESTRICT to preserve audit history).
- Index `(tenant_key, status)` and `(tenant_key, agent_execution_id)` for the dashboard query path.
- Filter every query by `tenant_key` per the codebase rule.

If the project description prefers semantic field names (`agent_id`, `job_id`), they should map to:
- `agent_id` → FK to `agent_executions.id` (NOT `agent_executions.agent_id`, which is a non-unique grouping column for succession; the PK is `id`).
- `job_id` → FK to `agent_jobs.job_id`.

**Phase B implementer must confirm with the orchestrator which "agent" they meant** — the executor row (`agent_executions.id`) or the succession-group key (`agent_executions.agent_id`, non-unique). Recommend the executor row because each approval is tied to one specific execution, not a succession lineage.

## A3. `jsonb_validators.py` location

Exists at **`src/giljo_mcp/schemas/jsonb_validators.py`**. Existing pattern: `BaseModel` subclasses (e.g., `SettingsData`, `IntegrationsSettingsData`, `SecuritySettingsData`, `RuntimeSettingsData` at lines 103, 128, 142, 168) plus a dispatch dict at line 384 (`{"integrations": IntegrationsSettingsData, "security": SecuritySettingsData, ...}`).

**Implementer extends this file** by adding (e.g.) `UserApprovalContextData(BaseModel)` for any JSONB column the new primitive carries (deferred-findings payload, options offered to the user, decision metadata). Call the validator at the write boundary in `UserApprovalService` (per the JSONB column discipline rule in `CLAUDE.md`).

## A4. Repository / service / tool / schema / model layout

All five directories from the project description **exist as named** at exactly these absolute paths:

- `src/giljo_mcp/models/` ✓ (17 modules; add `user_approval.py` here)
- `src/giljo_mcp/repositories/` ✓ (26 modules; add `user_approval_repository.py` extending `repositories/base.py`)
- `src/giljo_mcp/services/` ✓ (existing `job_completion_service.py`, `orchestration_agent_state_service.py`, `progress_service.py` are the call sites the gate will hook into; add `user_approval_service.py`)
- `src/giljo_mcp/tools/` ✓ (12 modules; the new MCP tool — `dismiss_user_approval` or `decide_user_approval` — goes in a new file or extends `agent_coordination.py` if naming fits; recommend a new file because the tool surface is user-facing rather than agent-coordination)
- `src/giljo_mcp/schemas/` ✓ (3 modules; `jsonb_validators.py` for the JSONB validator, `service_responses.py` for the typed response object the new tool returns)

No directory rename or alternative path is needed.

## A5. Existing NOTIFY / event-emission helper to reuse

**Helper:** `WebSocketManager.broadcast_to_tenant(tenant_key, event_type, data)` defined at `api/websocket.py:304`, exposed via dependency `api/dependencies/websocket.py:83`, and assigned onto services as `self._websocket_manager` (see `OrchestrationAgentStateService.__init__` line 69).

**Canonical example call site:** `src/giljo_mcp/services/orchestration_agent_state_service.py:97-111` (`_broadcast_completion`) shows the full pattern:
- guard `if self._websocket_manager:`
- await `broadcast_to_tenant(tenant_key=..., event_type="agent:status_changed", data={...})`
- wrap in `try/except Exception` with `noqa: BLE001` and a warning log — websocket failures must never break the request path

Other proven call sites in the same file at lines 265, 363, 438, 577 — all use the same envelope (`event_type="agent:status_changed"`, `data` dict with `job_id`, `project_id`, `agent_display_name`, `agent_name`, `old_status`, `status`, plus event-specific fields).

**Implementer reuses this helper** for the `awaiting_user` transition emission. Use `event_type="agent:status_changed"` with the existing data envelope so the frontend's existing WebSocket subscription handles it without a new event channel — only the `status` value (`"awaiting_user"`) is new. A separate `event_type="user_approval:created"` (carrying the `user_approvals` row id and tenant key) can be added if the frontend needs to fetch primitive details, but ride the existing channel for the agent-status piece.

There is no `pg_notify` / Postgres LISTEN/NOTIFY broker in `src/giljo_mcp/` (the README mentions one historically; `Grep` for `PostgresNotifyBroker | notify_broker` returned only handover/archive doc hits, no source code). Real-time is delivered via the WebSocket manager only.

## A6. Unexpected prose locations beyond the four grep patterns

None that meaningfully expand Phase C's scope. The four pattern searches plus targeted checks of `chapters_reference.py`, `agent_protocol.py`, `thin_prompt_generator.py`, and `template_seeder.py` returned the 27 rows above and nothing else. The frontend has the test/util pair at `statusConfig.{js,spec.js}` (rows 19-23) — already in the table; the implementer should not be surprised by them.

One adjacent observation worth flagging (not in scope, do NOT auto-create a project):

- `frontend/src/utils/statusConfig.js:140` keys the "Decision Required" UI off the `(status, reason)` tuple. After BE-5029 the keying becomes `status === "awaiting_user"` alone — the `reason` parameter to `getStatusConfig`/`isCloseoutBlocked` may become vestigial. Phase B's frontend slice should decide whether to drop the parameter or keep it for backwards compatibility during the rollout window. This is a Phase B concern, not Phase C.

---

# Bloat audit

**1 new file** (this document). Zero code changes. Within the 1-file Phase 0 budget.
