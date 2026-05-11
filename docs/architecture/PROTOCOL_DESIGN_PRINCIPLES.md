# Protocol Design Principles

**Edition Scope:** CE

This document records the design principles that govern how agent-protocol contracts
are introduced, hardened, and enforced in GiljoAI MCP. It grows by example: each
major primitive promotion is documented here as a worked case that future work can
pattern-match against.

---

## Principle 1 — Prose contracts must become enforced primitives

A "prose contract" is a behavioural instruction embedded as plain text inside an
agent's protocol (the strings returned by `protocol_sections/`). Prose contracts
work as long as every agent reads and follows the text. They fail silently when an
agent misreads the instruction, a future edit changes the surrounding text, or a
new agent template is added without inheriting the prose.

The pattern for eliminating a prose contract:

1. **Smell** — a behaviour that is supposed to always happen (or never happen) is
   expressed only as English prose in a protocol string.
2. **Schema layer** — introduce a database model, migration, and Pydantic schema that
   makes the intended state explicit and queryable.
3. **Service layer** — add a service method that enforces the state transition
   atomically (row insert + status flip + WebSocket broadcast in one transaction).
4. **Tool layer** — expose an `@mcp.tool` wrapper so agents can trigger the
   enforced transition via the MCP protocol, not via prose instruction.
5. **Gate layer** — add a hard gate (e.g. `complete_job` refuses until the row is
   resolved) so the state machine cannot be bypassed.
6. **REST surface** — add HTTP endpoints for the human-facing side of the same
   primitive (list + decide).
7. **UI surface** — surface the primitive in the dashboard so a human can act on it.
8. **Deletion layer** — remove every prose reference to the old contract from active
   source; add a Tier-1 pytest gate that will fail CI if the prose token is
   reintroduced.

The order matters: schema before service, service before tool, gate before UI.
Skipping steps leaves a window where the old prose and the new primitive coexist
and can diverge.

---

## Worked example: `user_approval_required` → `request_approval`

### The smell (BE-5028 trigger)

The HITL closeout behaviour was encoded entirely in prose inside
`src/giljo_mcp/services/protocol_sections/agent_lifecycle.py` (lines 262-263,
pre-deletion):

```
→ If user_approval_required=true: set status blocked with reason
  "Closeout: awaiting user review" …
→ If user_approval_required=false: proceed with best judgment
```

and in `src/giljo_mcp/services/job_completion_service.py` (lines 213, 222, 477,
484-490, pre-deletion), which threaded a `user_approval_required: bool` key through
a closeout checklist dict returned to the agent in the `complete_job` response.

The boolean was never persisted to the database, never validated against actual
deferred findings, and never checked by the server before allowing the agent to
proceed. An agent that ignored the prose instruction could close out a HITL job
without ever pausing for user review. Bug tracker: BE-5028.

---

### Phase A — Schema, service, and MCP tool (commit `e7e63a4f5`)

**Migration:** `migrations/versions/ce_0018_user_approvals.py`
- New table `user_approvals` in the CE migration chain (`migrations/versions/`),
  down-revision `ce_0017_tasks_add_series_number_subseries`.
- Key columns: `tenant_key`, `agent_execution_id` (FK → `agent_executions`),
  `job_id` (FK → `agent_jobs.job_id`), `reason`, `options` (JSONB),
  `context` (JSONB, nullable), `status` (default `pending`),
  `decided_option_id`, `decided_by_user_id` (FK → `users`).
- Composite index `ix_user_approvals_tenant_status` on `(tenant_key, status)` —
  the primary dashboard query path.
- Same migration extends `agent_executions.status` CHECK constraint to include
  `awaiting_user`.

**Model:** `src/giljo_mcp/models/user_approval.py`
- `UserApproval` ORM model; `VALID_USER_APPROVAL_STATUSES` constant at line 31.

**Service:** `src/giljo_mcp/services/user_approval_service.py`
- `UserApprovalService.create_pending` (lines 136-201): insert row + flip
  `agent_executions.status` to `awaiting_user` + broadcast `agent:status_changed`
  WebSocket event — all in one transaction; rolls back on any failure.
- Single-pending invariant at lines 167-173: `ValidationError` if the execution
  already has a pending approval.

**Tool:** `api/endpoints/mcp_sdk_server.py` lines 705-737
- `@mcp.tool request_approval` — the agent-facing primitive that replaces the prose.
- Parameters: `job_id`, `project_id`, `reason`, `options` (list of `{id, label}`),
  optional `context` dict.
- Returns: `{approval_id: str, status: str}`.
- Inner implementation: `src/giljo_mcp/tools/tool_accessor.py` lines 302-340
  (`ToolAccessor.request_approval`).

**Status isolation:** `awaiting_user` is intentionally absent from
`src/giljo_mcp/services/orchestration_agent_state_service.py` line 55
(`_AGENT_SETTABLE_STATUSES`) — agents cannot forge the status directly; it can
only be set by `UserApprovalService.create_pending`.

**Regression test:** `tests/unit/test_awaiting_user_status.py`
- Asserts `awaiting_user` is a valid WebSocket status (line 22) AND is not
  agent-settable (line 45).

---

### Phase B — Close-gate and REST decide endpoint (commits `1fdab9e31`, `1c4e94765`)

**Close gate:** `complete_job` now refuses to complete an agent job while a
`pending` `user_approvals` row exists for that execution. The gate lives in the
service layer; `awaiting_user` execution status is the observable signal.

**Decide endpoint:** `api/endpoints/approvals.py` lines 116-154
- `POST /api/approvals/{approval_id}/decide`
- Request body: `ApprovalDecideRequest {option_id: str (1-100 chars)}` — closed
  schema (`extra='forbid'`).
- Response: `ApprovalDecideResponse {approval_id, status, decided_option_id,
  job_id, project_id}`.
- Error codes: 404 (not found or cross-tenant — no existence leak), 409 (already
  decided), 422 (invalid option or unsupported status).
- Tenant isolation enforced at `service.mark_decided` by filtering on
  `current_user.tenant_key`.
- Router mounted at `api/app.py` lines 535-536, prefix `/api/approvals`,
  tag `approvals`.

**WebSocket channel:** no new event type was added. The existing
`agent:status_changed` channel carries user-approval transitions. The
`awaiting_user` broadcast payload includes a `user_approval_id` field so the
frontend can hydrate the approval surface without a separate fetch.
Broadcast implementation: `src/giljo_mcp/services/user_approval_service.py`
`_broadcast_status_change` (lines 307-338) and `_broadcast_resume` (lines 272-305).

**Integration tests:** `tests/integration/test_decide_endpoint.py` — 12 tests
covering tenant isolation (cross-tenant returns 404), auth dependency, already-decided
409, invalid option 422, and resume broadcast.

---

### Phase C — UI surface and prose deletion (commit `79cf97a37`)

**List endpoint:** `api/endpoints/approvals.py` lines 74-113
- `GET /api/approvals/?status=pending&limit=N&offset=M`
- Paginated, tenant-isolated, auth-gated (`Depends(get_current_active_user)`).
- Response: `ApprovalListResponse {items: list[UserApprovalRead], count, total,
  limit, offset}` — schema in `src/giljo_mcp/schemas/user_approval.py`.
- Repository method: `UserApprovalRepository.list_pending_for_tenant` uses the
  `ix_user_approvals_tenant_status` index.

**Frontend store:** `frontend/src/stores/useApprovalsStore.js` (NEW)
- Pinia store managing the cross-project pending approvals inbox.
- HTTP via `api.approvals.listPending` / `api.approvals.decide` added to the
  existing `frontend/src/services/api.js` singleton (ADR-001: always use
  `getApiBaseUrl()`, never compose `${host}:${port}` manually).
- Realtime updates via the existing `agent:status_changed` WebSocket channel;
  handler enriched in `frontend/src/stores/eventRoutes/agentEventRoutes.js`.

**ApprovalCard component:** `frontend/src/components/orchestration/ApprovalCard.vue`
(NEW)
- Renders a pending approval (reason, agent identity, option buttons).
- Composed into `frontend/src/components/orchestration/CloseoutModal.vue` at the
  `awaiting_user` branch (replaces the static "Decision Required" alert).
- Design system compliance: `smooth-border` inset box-shadow (never CSS `border`
  on rounded surfaces), agent-color via `getAgentColor()` + `hexToRgba()`, WCAG AA
  text via `--text-muted` (`#8895a8`).

**statusConfig re-key:** `frontend/src/utils/statusConfig.js`
- `isCloseoutBlocked` renamed `isAwaitingUser`; matching logic re-keyed to
  `status === 'awaiting_user'` (dropping the `blockReason` second argument).
- All callers updated: `StatusChip.vue`, `ProjectTabs.vue`, `CloseoutModal.vue`.

**Prose deletion:** executed against the deletion list in
`docs/handovers/BE-5029a-prose-deletion-list.md` (Phase 0 audit document, preserved
as historical record):
- `src/giljo_mcp/services/job_completion_service.py` — `user_approval_required`
  kwarg, checklist key, and the instruction f-string block removed; dead
  `_build_closeout_checklist` branches collapsed.
- `src/giljo_mcp/services/protocol_sections/agent_lifecycle.py` lines 262-263 —
  the `if/else user_approval_required` prose replaced with a reference to
  `request_approval` as the enforced gate.

---

### The deletion-test-in-CI pattern

Deleting prose is not enough on its own. A future refactor, template copy-paste, or
LLM agent can silently reintroduce the deleted token. The defence is a Tier-1 pytest
gate that fails CI if the token reappears.

**Test file:** `tests/unit/test_be5029_prose_deletion.py` (NEW, commit `1c4e94765`)

The test scans every `.py`, `.js`, `.vue`, `.ts`, `.tsx`, `.jsx` file under `src/`,
`api/`, `tests/`, `frontend/src/`, and `frontend/tests/` for the string
`user_approval_required`. Files in the allowed-survivor set (model docstring,
`request_approval` tool description, and the test itself) are skipped. Any other
hit fails with an actionable message citing the offending file and the correct
primitive to use instead.

**CI tier:** Tier 1 — the test has no custom markers and is collected by the standard
`pytest tests/unit/` run in `.github/workflows/ci.yml` (the `test` job, triggered on
every push to `master` and every pull request). It is NOT gated behind a tag-only
trigger. Runtime is sub-second (pure filesystem scan, no DB).

A companion test (`test_allowed_survivors_still_exist`) guards the inverse: if a
survivor file is moved or deleted, the test fails until the allowlist is updated,
preventing the deletion gate from silently developing a hole.

---

### Summary: what each phase enforces

| Phase | Layer | Enforced by |
|-------|-------|-------------|
| A | Schema + tool | DB row insert is atomic; `awaiting_user` status only set by service |
| B | Close gate + decide | `complete_job` refuses; REST `POST /decide` resolves |
| C | UI + prose deletion | Dashboard renders the primitive; Tier-1 CI prevents re-prose |

The three phases together complete the prose-to-primitive promotion cycle: the
behaviour is no longer possible to ignore via prose, impossible to bypass at the
server gate, visible to the human in the dashboard, and protected against regression
by a fast CI check on every push.
