# Project Status — Single Source of Truth (BE-5039)

**Edition Scope:** Both (CE + SaaS) — the column lives on the CE `projects` model
**Target branch:** `dev/v1.2.1`
**Phase:** 1 (design) of the 4-phase plan (analyze → backend → frontend → devops)
**Status:** Design accepted; implementation may begin
**Author:** analyzer (job 747ed9ea-9b7d-4fd4-86ac-a14640469803)

---

## 1. Purpose & non-goals

**Purpose.** Eliminate the project-status drift surface area. Today the same
six string literals are repeated in at least eight places (Python services,
Python repositories, a frontend SFC validator, a Pinia store, a contract
test, two informal docstrings on the SQLAlchemy model, and several ad-hoc
`status in ("completed", "cancelled")` checks). There is no DB-level CHECK
constraint and no ENUM type, so any caller can persist any string and the
database will accept it. Drift is detected today by a contract test that
parses the StatusBadge.vue file with a regex — useful, but a tripwire, not
a guard rail.

This design replaces those literals with a Postgres ENUM (`project_status`)
declared in a CE migration and a Python `enum.Enum` mirror declared in
`src/giljo_mcp/domain/project_status.py`. Both layers carry the same
metadata (label, color, lifecycle-finished flag) so frontend rendering and
backend gating consult one place.

**Non-goals.**
- No new statuses are introduced. The set is the union of values currently
  declared in `VALID_PROJECT_STATUSES` and observed in real data.
- The `staging_status` column (separate from `status`, tracks the staging
  workflow) is out of scope. It already has its own small enum-like set
  and is not user-facing in the badge.
- Soft-delete semantics (`deleted_at IS NOT NULL`) stay as-is. The
  `deleted` status value coexists with the timestamp column — they are
  set together by `ProjectDeletionService.delete_project`.
- Agent / job status enums are unrelated to project status; out of scope.

---

## 2. Phase 0 — Audit Reconciliation Table

Every status WRITE site, READ/VALIDATE site, real-data observation, and
existing constraint, with file:line and the value involved.

### 2.1 WRITE sites

| Site | File:line | Value(s) written | Trigger |
|------|-----------|------------------|---------|
| `ProjectLifecycleService.activate_project` | `src/giljo_mcp/services/project_lifecycle_service.py:150` | `"active"` | User clicks Activate; also auto-deactivates the previous active project (`existing_active.status = "inactive"` at `:137`) |
| `ProjectLifecycleService.deactivate_project` | `src/giljo_mcp/services/project_lifecycle_service.py:322` | `"inactive"` | User clicks Deactivate |
| `ProjectLifecycleService._complete_project_transaction` | `src/giljo_mcp/services/project_lifecycle_service.py:461` | `"completed"` | Orchestrator calls `complete_project(...)` |
| `ProjectLifecycleService.continue_working` | `src/giljo_mcp/services/project_lifecycle_service.py:615` | `"inactive"` | User clicks Continue Working on a completed project |
| `ProjectLifecycleRepository.cancel_project` | `src/giljo_mcp/repositories/project_lifecycle_repository.py:206` | `"cancelled"` | User clicks Cancel (REST `/cancel` endpoint) |
| `ProjectStagingService.cancel_staging` | `src/giljo_mcp/services/project_staging_service.py:233` | `"cancelled"` | User clicks Cancel Staging (`/cancel-staging` endpoint) |
| `ProjectCloseoutService.close_out_project` | `src/giljo_mcp/services/project_closeout_service.py:111` | `"completed"` | Orchestrator MCP closeout path |
| `ProjectDeletionService.delete_project` | `src/giljo_mcp/services/project_deletion_service.py:103` | `"deleted"` | User clicks Delete; also sets `deleted_at` |
| `ProjectRepository.restore_project` | `src/giljo_mcp/repositories/project_repository.py:564` | `"inactive"` | User clicks Restore; clears `completed_at` and `deleted_at` |
| `archive_project` REST endpoint | `api/endpoints/projects/lifecycle.py:451` | `"terminated"` if `proj.early_termination` else `"completed"` | User confirms archive via UI |
| `ProjectService._apply_project_updates` | `src/giljo_mcp/services/project_service.py:630` (allowlist includes `"status"`) | Whatever caller passes (validated upstream by `_VALID_UPDATE_STATUSES`) | Generic `update_project()` path |
| `ProjectService.update_project_metadata_for_mcp` | `src/giljo_mcp/services/project_service.py:1262` | `_VALID_UPDATE_STATUSES = {"inactive","active","completed","cancelled"}` | MCP tool `update_project_metadata` |
| `TaskConversionService` | `src/giljo_mcp/services/task_conversion_service.py:234` | `"inactive"` | When converting a task into a project, deactivates the previously active project |
| Frontend Pinia store (in-memory) | `frontend/src/stores/projects.js:349` | **`"closed"`** *(orphan value — not in canonical enum)* | WebSocket event `update_type === "closed"` overrides server-supplied `project_data.status` (which is `"completed"`) |
| Migrations | _none_ | _no backfill or seed UPDATEs of `projects.status` exist in `migrations/versions/`_ | n/a |

**Note: `staging` is never persisted via WRITE.** It is referenced in
`activate_project`'s state-transition check (`if project.status not in
["staging", "inactive"]`) but appears nowhere as a write target. The
`staging_status` column (separate from `status`) is the actual staging
tracker. Whether `staging` should be in the enum is decided in §3.1.

### 2.2 READ / VALIDATE sites

| Site | File:line | Comparison | Purpose |
|------|-----------|------------|---------|
| `IMMUTABLE_PROJECT_STATUSES` (constant) | `src/giljo_mcp/services/project_service.py:63` | `frozenset({"completed","cancelled"})` | Write gate; consulted by `update_project` (`:746`) and `update_project_mission` (`:561`) |
| `LIFECYCLE_FINISHED_STATUSES` (constant) | `src/giljo_mcp/services/project_service.py:79` | `frozenset({"completed","cancelled","terminated","deleted"})` | Default exclusion bucket for `list_projects_for_mcp` (`:1096`) |
| `VALID_PROJECT_STATUSES` (constant) | `src/giljo_mcp/services/project_service.py:90` | `frozenset({"inactive","active","completed","cancelled","terminated","deleted"})` | Source of truth for the cross-layer drift contract test |
| `_VALID_STATUS_FILTERS` | `src/giljo_mcp/services/project_service.py:847` | `{"inactive","active","completed","cancelled","all"}` | Legacy `status_filter` kwarg of `list_projects_for_mcp` |
| `_VALID_UPDATE_STATUSES` | `src/giljo_mcp/services/project_service.py:851` | `{"inactive","active","completed","cancelled"}` | MCP-tool write gate (excludes `terminated`/`deleted` — those are dedicated lifecycle endpoints only) |
| `_VALID_FILTER_STATUSES` | `src/giljo_mcp/services/project_service.py:855` | `= VALID_PROJECT_STATUSES` | MCP-tool read filter accepts the full enum |
| `archive_project` short-circuit guard | `api/endpoints/projects/lifecycle.py:446` | `proj.status not in ("inactive","completed","cancelled","archived","terminated")` | Avoids redundant deactivate; **`"archived"` is here as a hardcoded literal even though it does not exist in the canonical list** |
| `ProjectLifecycleService.activate_project` precheck | `src/giljo_mcp/services/project_lifecycle_service.py:123` | `project.status not in ["staging","inactive"]` | Allowed source states for activation |
| `ProjectLifecycleService.deactivate_project` precheck | `:315` | `project.status != "active"` | Must be active to deactivate |
| `ProjectLifecycleService.continue_working` precheck | `:607` | `project.status != "completed"` | Resume only allowed from completed |
| `ProjectStagingService.cancel_staging` precheck | `:227` | `project.status != "staging"` | Reads `staging` value (also relevant to §3.1 keep-or-drop decision) |
| `ProjectRepository.list_projects` filter | `src/giljo_mcp/repositories/project_repository.py:233-240` | Special-cases `"deleted"` to flip the soft-delete clause; otherwise excludes `"cancelled"` by default | Read-side soft-delete + cancellation hide |
| `ProjectRepository.get_active_project` | `:257` | `Project.status == "active"` | Find single active project |
| `ProjectRepository.get_deleted_projects` / `get_expired_deleted_projects` | `:532, :547` | `Project.status == "deleted"` AND `deleted_at IS NOT NULL` | Soft-delete maintenance |
| `ProductRepository` agent-job aggregation | `src/giljo_mcp/repositories/product_repository.py:507, 528, 548, 569` | `Project.status == "active"` and `AgentJob.status == "active"` (latter is unrelated agent status) | Product summary scoping |
| `MessageRoutingService.route_message` | `src/giljo_mcp/services/message_routing_service.py:493` | `project.status in ("completed","cancelled")` | Drops late messages to closed projects |
| `OrchestrationAgentStateService` | `src/giljo_mcp/services/orchestration_agent_state_service.py:258` | `project.status in ("completed","cancelled")` | Same pattern — both duplicate `IMMUTABLE_PROJECT_STATUSES` |
| `MessageRepository` | `src/giljo_mcp/repositories/message_repository.py:726` | `Project.status == "active"` | Active-project filter |
| `ProductMemoryRepository` | `src/giljo_mcp/repositories/product_memory_repository.py:534` | `Project.status != "deleted"` | Memory excludes soft-deleted |
| `ProductStatisticsRepository` | `:532` | `Project.status == "completed"` | Stats panel |
| `TaskRepository` | `src/giljo_mcp/repositories/task_repository.py:261` | `Project.status == "active"` | Active project task scoping |
| `agent_health_monitor` | `src/giljo_mcp/monitoring/agent_health_monitor.py:191, 269, 357, 520` | `Project.status == "active"` | Health monitor scoping |
| `ProjectLaunchService` | `src/giljo_mcp/services/project_launch_service.py:181` | `project.status != "active"` | Auto-activate if launching while not active |
| Frontend `StatusBadge.vue` validator (line 21) | `frontend/src/components/StatusBadge.vue:21` | `["inactive","active","completed","cancelled","terminated","deleted"].includes(value)` | Vue prop validator + label/color lookup |
| Frontend `useProjectFilters` (filterStatus matching) | `frontend/src/composables/useProjectFilters.js:73` | Equality match (no validation) | UI dropdown filter — matches whatever value is in the data |
| Cross-layer drift test | `tests/contract/test_status_enum_consistency.py:89` | `VALID_PROJECT_STATUSES == StatusBadge.vue literals` | Tripwire (decision §3.5) |

**`update_project_metadata` validation chain.** REST `PATCH` (via
`update_project`) bypasses the `_VALID_UPDATE_STATUSES` whitelist — it only
checks `IMMUTABLE_PROJECT_STATUSES` and the `_apply_project_updates` field
allowlist. The MCP tool path (`update_project_metadata_for_mcp`) is the
only place that whitelists the four user-mutable statuses. Implementer
must keep this asymmetry intact (REST is invoked by trusted lifecycle
endpoints that have already chosen the correct status; MCP is invoked by
agents and needs the whitelist).

### 2.3 Phase 0C — Real-data audit

Run on each environment.

| Environment | Distinct values observed | Counts |
|-------------|-------------------------|--------|
| Local dev (`giljo_mcp@localhost`) | `completed`, `deleted`, `inactive` | 1 / 1 / 1 |
| Dogfood (`giljo@10.1.0.191`) | **NOT QUERIED** — no creds available to this analyzer agent. Implementer-DevOps must run the query during smoke testing of the migration on the dogfood box. See §6.3. |
| Demo prod (`gildemo@10.1.0.16`) | **NOT QUERIED** — same reason. |

A REQUEST_CONTEXT was sent to the orchestrator asking for credentials or
the query result; design proceeds with the conservative pre-flight remap
step (§3.4) so any orphan value found in dogfood/demo at migration time
is coalesced safely without blocking the migration.

**Orphan value risk surface (what to remap if seen in dogfood/demo):**
- `archived` — referenced as a literal in `archive_project` short-circuit
  guard at `lifecycle.py:446` and in legacy handover docs (e.g. `0070`),
  but no current write site sets it. Remap → `completed`.
- `closed` — written client-side only by `frontend/src/stores/projects.js:349`
  on the WebSocket `closed` event. Never persisted to the DB by any
  backend code path. If observed, it indicates a forgotten manual
  override. Remap → `completed`.
- `paused` — referenced in handover `0071` ("removed paused/archived");
  no current write site. Remap → `inactive`.
- `staging` — see §3.1; if any legacy row carries this value the migration
  must remap to `inactive` (the new enum will not include it).
- Anything else → remap to `inactive` and log the row IDs.

### 2.4 Phase 0D — Existing CHECK constraints

Local dev DB:
```sql
SELECT conname, pg_get_constraintdef(c.oid)
FROM pg_constraint c
JOIN pg_class t ON c.conrelid = t.oid
WHERE t.relname = 'projects' AND c.contype = 'c';
-- (0 rows)
```

There is no CHECK constraint and no ENUM type today. The only structural
guards on the column are:
- `idx_project_status` — plain btree index on `status` (compatible with
  ENUM column type — no rebuild needed if we use `USING status::project_status`).
- `idx_project_single_active_per_product` — UNIQUE partial index `WHERE
  status::text = 'active'::text`. **Migration concern:** the partial
  predicate references the column as text. Postgres allows comparing an
  enum to a text literal via `::text` cast; the index expression has to
  be re-created against the enum type to keep the planner happy. The
  migration MUST drop and recreate this partial index after the column
  type change.

---

## 3. Phase 1 — Design Decisions

### 3.1 Decision 1 — Final ENUM entries

**Chosen.** The Postgres enum `project_status` and the Python mirror
`ProjectStatus` carry exactly these values, in this order:

```
INACTIVE      = 'inactive'
ACTIVE        = 'active'
COMPLETED     = 'completed'
CANCELLED     = 'cancelled'
TERMINATED    = 'terminated'
DELETED       = 'deleted'
```

**Rationale.**
- This is the union of `VALID_PROJECT_STATUSES`, the StatusBadge.vue
  validator literal, and observed real-data values from local dev (no
  dogfood/demo data available — see §2.3). Dogfood/demo orphans (if any)
  will be coalesced by the pre-flight remap (§3.4) into the same six.
- `staging` is **excluded.** It is a transitional state that exists only
  during the activation flow. The `staging_status` column on the same
  table is the proper tracker for the staging workflow (`null | staging
  | staging_complete`). The `status` column never persists `"staging"`
  in any write path I found; the only place that compares against it is
  the activate_project precondition (`status not in ["staging","inactive"]`)
  and the `cancel_staging` precondition (`status != "staging"`). Both of
  those guards are stale — keeping them does no harm because no row will
  ever match. The implementer MUST remove the `"staging"` literal from
  both prechecks during Phase 2 because the new enum cannot represent it
  and any attempt to compare via `==` would raise at runtime.
- `archived` is **excluded.** It survives only as a hardcoded literal in
  `archive_project`'s short-circuit guard at `lifecycle.py:446`. No
  write site sets it. The Phase 2 implementer must replace that literal
  with `terminated` (the actual canonical value `archive_project` writes).

**Edition isolation note.** This enum is CE-foundational. SaaS does not
extend it. If SaaS ever needs a SaaS-only project status, it adds the
value to `ProjectStatus` in CE with metadata declaring it SaaS-scoped
(`is_saas_only=True`). The CE deletion test still passes because CE code
will simply never write that value. Cross-edition status divergence at
the schema level is forbidden — it would either crash the export script's
SaaS-table-reference check or break the CE `alembic upgrade head` on
fresh installs.

### 3.2 Decision 2 — Categorical metadata model

**Chosen.** Class-level metadata declared on the `ProjectStatus` Python
enum, mirrored in a small JSON blob alongside the migration so the
frontend can pull it via API. Single declaration site for all backend
gating; the API endpoint just serializes the same blob.

**Concrete schema.** Create `src/giljo_mcp/domain/project_status.py`:

```python
# Pseudocode — implementer owns the exact API surface.
import enum
from dataclasses import dataclass

@dataclass(frozen=True)
class ProjectStatusMeta:
    label: str                  # human-readable badge label
    color_token: str            # SCSS token name (NOT a hex literal)
    is_lifecycle_finished: bool # member of LIFECYCLE_FINISHED_STATUSES
    is_immutable: bool          # member of IMMUTABLE_PROJECT_STATUSES
    is_user_mutable_via_mcp: bool  # member of _VALID_UPDATE_STATUSES

class ProjectStatus(str, enum.Enum):
    INACTIVE   = 'inactive'
    ACTIVE     = 'active'
    COMPLETED  = 'completed'
    CANCELLED  = 'cancelled'
    TERMINATED = 'terminated'
    DELETED    = 'deleted'

    @property
    def meta(self) -> ProjectStatusMeta: ...

PROJECT_STATUS_META: dict[ProjectStatus, ProjectStatusMeta] = {
    ProjectStatus.INACTIVE:   ProjectStatusMeta('Inactive',   'color-text-muted',         False, False, True),
    ProjectStatus.ACTIVE:     ProjectStatusMeta('Active',     'color-agent-implementer',  False, False, True),
    ProjectStatus.COMPLETED:  ProjectStatusMeta('Completed',  'color-status-complete',    True,  True,  True),
    ProjectStatus.CANCELLED:  ProjectStatusMeta('Cancelled',  'color-status-blocked',     True,  True,  True),
    ProjectStatus.TERMINATED: ProjectStatusMeta('Terminated', 'color-agent-analyzer',     True,  False, False),
    ProjectStatus.DELETED:    ProjectStatusMeta('Deleted',    'color-agent-analyzer',     True,  False, False),
}

# Derived sets (replace the three legacy module-level constants in project_service.py)
IMMUTABLE_PROJECT_STATUSES   = frozenset(s for s, m in PROJECT_STATUS_META.items() if m.is_immutable)
LIFECYCLE_FINISHED_STATUSES  = frozenset(s for s, m in PROJECT_STATUS_META.items() if m.is_lifecycle_finished)
VALID_UPDATE_STATUSES        = frozenset(s for s, m in PROJECT_STATUS_META.items() if m.is_user_mutable_via_mcp)
VALID_PROJECT_STATUSES       = frozenset(ProjectStatus)  # full set
```

**Rationale.**
- Class-level metadata wins over a separate config dict because the enum
  member and its metadata are conceptually inseparable; declaring them
  in two files invites the same drift this work is eliminating.
- `color_token` is a string naming a SCSS variable in `design-tokens.scss`
  — never a hex literal. The API serializer resolves the token name
  client-side by reading the compiled CSS custom property
  (`getComputedStyle(...).getPropertyValue(--color-...)`). This keeps
  the Luminous Pastel palette as the single source of color truth and
  keeps the enum semantically pure (color is presentation, not data).
- Existing module-level constants in `project_service.py`
  (`IMMUTABLE_PROJECT_STATUSES`, `LIFECYCLE_FINISHED_STATUSES`,
  `VALID_PROJECT_STATUSES`) become aliases to the derived sets above —
  the test suite that imports them keeps working.
- `is_user_mutable_via_mcp` derives `_VALID_UPDATE_STATUSES`. The legacy
  attribute on the service class becomes a deprecation alias.

**SQLAlchemy column type.** The `Project.status` column changes from
`Column(String(50), default="inactive")` to `Column(SQLEnum(ProjectStatus,
name="project_status", values_callable=lambda e: [m.value for m in e]),
default=ProjectStatus.INACTIVE, nullable=False)`. The `nullable=False` is
deliberate — there is no use case for a NULL status, and the migration
will fill any NULL row with `'inactive'` before applying the type cast.

### 3.3 Decision 3 — Frontend propagation mechanism

**Chosen.** A new HTTP endpoint `GET /api/v1/project-statuses/` that
mirrors the BE-5036 `/api/v1/project-types/` pattern (existing endpoint
at `api/endpoints/project_types/routes.py`). Returns:

```json
[
  {"value": "inactive", "label": "Inactive", "color_token": "color-text-muted",
   "is_lifecycle_finished": false, "is_immutable": false, "is_user_mutable_via_mcp": true},
  ...
]
```

Frontend stores the response in a Pinia store (or a simple composable
cache) keyed by `value`, and `StatusBadge.vue` consumes the cached map
instead of its hardcoded literal.

**Rationale.**
- Build-time codegen (a Python script that emits
  `frontend/src/generated/projectStatuses.js`) was the obvious
  alternative. It's rejected because:
  1. The repo has no precedent for codegen; introducing it pulls in a
     new maintenance burden (hooking into Vite build, adding a
     `npm run codegen` step, watching for stale checked-in artifacts,
     pre-commit checks for "regenerate after migration"). The export
     scripts (`scripts/export_ce_dev.sh`, `merge_to_public.sh`) would
     have to be taught about the generated file.
  2. The existing project-types endpoint already establishes the
     "metadata exposed via API" pattern. Keeping consistency wins over
     micro-optimizing for one fewer HTTP call.
  3. The endpoint cost is bounded: six rows of static metadata, cached
     by the frontend after first load, no DB query (the response is
     produced from `PROJECT_STATUS_META` in memory). Latency cost is
     a single round-trip per browser session.
- Cache invalidation is not a concern because the metadata only changes
  with a code deploy. On reload after deploy the frontend re-fetches.

**Endpoint placement.** `api/endpoints/project_statuses/routes.py` (new
directory mirroring `project_types/`). Mounted in `api/app.py` next to
`project_types.router`. CE — does not depend on tenant context (the
metadata is identical for all tenants).

**Edition isolation.** The endpoint is CE. If SaaS later adds SaaS-only
status values, the same endpoint serves them — gated by the
`is_saas_only` field on the metadata if/when that flag is added.

### 3.4 Decision 4 — Migration strategy

**Chosen.** A single CE migration `migrations/versions/ce_0008_project_status_enum.py`
(name to be confirmed by implementer-backend; revision id auto-generated)
that runs the following operations in `upgrade()`, all wrapped in the
implicit transaction Alembic provides:

1. **Pre-flight orphan remap** (idempotent):
   ```sql
   -- Fill NULLs first so the type cast cannot fail on null.
   UPDATE projects SET status = 'inactive' WHERE status IS NULL;
   -- Coalesce any legacy/orphan values not in the canonical six.
   UPDATE projects SET status = 'completed'
     WHERE status IN ('archived', 'closed');
   UPDATE projects SET status = 'inactive'
     WHERE status IN ('paused', 'staging');
   -- Catch-all: anything still outside the canonical set → 'inactive'.
   UPDATE projects SET status = 'inactive'
     WHERE status NOT IN ('inactive','active','completed','cancelled','terminated','deleted');
   ```
   Each step logs `RAISE NOTICE` with the affected row count so the
   migration output makes the remap auditable.

2. **Create the ENUM type** with an IF NOT EXISTS guard (safe on re-run):
   ```sql
   DO $$
   BEGIN
     IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'project_status') THEN
       CREATE TYPE project_status AS ENUM
         ('inactive','active','completed','cancelled','terminated','deleted');
     END IF;
   END$$;
   ```

3. **Drop the partial unique index** that references `status::text`
   (it has to be re-created against the new column type):
   ```sql
   DROP INDEX IF EXISTS idx_project_single_active_per_product;
   ```

4. **Convert the column type** with USING-cast and add NOT NULL:
   ```sql
   ALTER TABLE projects
     ALTER COLUMN status TYPE project_status
       USING status::project_status,
     ALTER COLUMN status SET DEFAULT 'inactive'::project_status,
     ALTER COLUMN status SET NOT NULL;
   ```

5. **Recreate the partial unique index** referencing the enum value:
   ```sql
   CREATE UNIQUE INDEX idx_project_single_active_per_product
     ON projects (product_id)
     WHERE status = 'active'::project_status;
   ```
   (The plain `idx_project_status` btree index does NOT need a rebuild —
   ENUM columns are indexable directly.)

`downgrade()` reverses cleanly:
1. Drop the partial unique index.
2. `ALTER TABLE projects ALTER COLUMN status DROP NOT NULL, ALTER COLUMN
   status DROP DEFAULT, ALTER COLUMN status TYPE varchar(50) USING
   status::text;`
3. Recreate the partial unique index against `status::text`.
4. `DROP TYPE project_status;`

**Migration chain rule (HARD).** This migration lives in
`migrations/versions/`, **never** `migrations/saas_versions/`. `status`
is a column on the CE `Project` model, and `startup.py` only runs
`alembic upgrade head` against the CE chain. A SaaS-chain migration here
would crash CE deployments with `column "status" does not exist` (per
the project CLAUDE.md migration chain rule).

**Down-revision pointer.** `down_revision` is the latest CE head as of
the implementer-backend's branch checkout — most likely
`ce_0007_users_skills_version_tracking`. Implementer must verify with
`alembic heads` before writing the migration.

### 3.5 Decision 5 — Fate of `tests/contract/test_status_enum_consistency.py`

**Chosen.** Repurpose, do not delete.

The test stops being a "two-source drift detector" the moment the enum
becomes single-source. But the failure mode it guards against ("someone
re-introduces a hardcoded `['inactive','active',...]` list anywhere")
is exactly what we want to keep blocking. After Phase 2/3 the test
asserts:

```
ProjectStatus enum members  ==  StatusBadge.vue rendered values  ==  GET /project-statuses/ payload values
```

Concrete shape after refactor (implementer-frontend owns the test edit
in Phase 4):
- Read the Python enum: `set(s.value for s in ProjectStatus)`.
- Read the StatusBadge.vue file: it should no longer have a hardcoded
  validator literal — instead it imports values from the cached API
  response. The test asserts that `StatusBadge.vue` does NOT contain
  the old `['inactive','active', ...].includes(value)` regex pattern
  — its presence is the regression we're guarding against.
- Optionally hit `GET /project-statuses/` from a test fixture and assert
  set-equality with the enum.

The renamed test file should be
`tests/contract/test_project_status_single_source.py` with a docstring
explaining what regression triggered it (BE-5039 follow-up: "no
hardcoded status list anywhere").

**Rationale.**
- Deletion was the obvious alternative. Rejected because the failure
  mode ("a future contributor copies the literal back into a frontend
  component") is real and cheap to guard against. The test runtime is
  trivial.
- The renamed test stays in `tests/contract/` (CE — same edition rules
  as the rest of the contract suite).

---

## 4. Implementer-Backend handoff (Phase 2)

**EDITION SCOPE: Both** — `Project` model and migration are CE; SaaS
inherits transparently.

### 4.1 New files

| File | Purpose |
|------|---------|
| `src/giljo_mcp/domain/__init__.py` | New package — holds shared domain enums. (Verify `domain/` doesn't already exist; if not, create it. CE.) |
| `src/giljo_mcp/domain/project_status.py` | `ProjectStatus` enum + `PROJECT_STATUS_META` dict + derived sets per §3.2 |
| `migrations/versions/ce_0008_project_status_enum.py` | Migration per §3.4 |
| `api/endpoints/project_statuses/__init__.py` | Router stub mirroring `project_types/__init__.py` (`prefix="/api/v1/project-statuses"`) |
| `api/endpoints/project_statuses/routes.py` | `GET /` returning the metadata array |
| `api/endpoints/project_statuses/schemas.py` | `ProjectStatusResponse` Pydantic model |

### 4.2 Files modified

| File | What changes | Why |
|------|-------------|-----|
| `src/giljo_mcp/models/projects.py` | `status` column type changes from `Column(String(50), default="inactive")` to `Column(SQLEnum(ProjectStatus, name="project_status", values_callable=...), default=ProjectStatus.INACTIVE, nullable=False)`. Update the comment that still says "Handover 0071: removed paused/archived". | New column type |
| `src/giljo_mcp/services/project_service.py` | Replace `IMMUTABLE_PROJECT_STATUSES`, `LIFECYCLE_FINISHED_STATUSES`, `VALID_PROJECT_STATUSES` with re-exports from `domain.project_status`. Replace `_VALID_UPDATE_STATUSES`, `_VALID_FILTER_STATUSES`, `_VALID_STATUS_FILTERS` with derived sets. Comparisons against `project.status` now compare against `ProjectStatus.X` instead of `"x"` (or `.value` if string equality is needed at the comparison site). | Drop hardcoded literals |
| `src/giljo_mcp/services/project_lifecycle_service.py` | Replace string writes (`project.status = "active"`) with enum writes (`project.status = ProjectStatus.ACTIVE`). Remove the `"staging"` reference in the activate precondition (it cannot be a row state — see §3.1). | Drop hardcoded literals; fix the staging precondition |
| `src/giljo_mcp/services/project_staging_service.py` | Same — `project.status = ProjectStatus.CANCELLED`. The `status != "staging"` precondition is dead code post-migration; replace with a clearer guard (e.g. check `staging_status` column instead, or remove the staging-cancel endpoint entirely if the design no longer needs it — coordinate with orchestrator before deciding). | Drop hardcoded literals; staging value gone |
| `src/giljo_mcp/services/project_closeout_service.py` | `project.status = ProjectStatus.COMPLETED`; comparisons updated. | Drop literals |
| `src/giljo_mcp/services/project_deletion_service.py` | `project.status = ProjectStatus.DELETED` | Drop literals |
| `src/giljo_mcp/services/project_launch_service.py:181` | `project.status != ProjectStatus.ACTIVE` | Drop literal |
| `src/giljo_mcp/services/task_conversion_service.py:234` | `existing_active_project.status = ProjectStatus.INACTIVE` | Drop literal |
| `src/giljo_mcp/services/message_routing_service.py:493` | Replace `project.status in ("completed","cancelled")` with `project.status in IMMUTABLE_PROJECT_STATUSES` (now derived from metadata) | Use derived set |
| `src/giljo_mcp/services/orchestration_agent_state_service.py:258` | Same pattern | Use derived set |
| `src/giljo_mcp/services/job_lifecycle_service.py:171` | Already uses `IMMUTABLE_PROJECT_STATUSES` — verify the import path still resolves | No-op verify |
| `src/giljo_mcp/repositories/project_repository.py` | All `Project.status == "X"` comparisons become `Project.status == ProjectStatus.X`. The `list_projects` filter that special-cases `"deleted"` keeps its behavior — it accepts a string from the caller and SQLAlchemy auto-coerces to the enum (or raises if invalid, which is the desired behavior). | Drop literals |
| `src/giljo_mcp/repositories/project_lifecycle_repository.py:103, :206` | `Project.status == ProjectStatus.ACTIVE`; `cancel_project` writes `ProjectStatus.CANCELLED` | Drop literals |
| `src/giljo_mcp/repositories/product_repository.py:507, 528, 548, 569` | `Project.status == ProjectStatus.ACTIVE` (the AgentJob.status references at :528 and :569 are unrelated — leave alone) | Drop literals |
| `src/giljo_mcp/repositories/product_memory_repository.py:534` | `Project.status != ProjectStatus.DELETED` | Drop literal |
| `src/giljo_mcp/repositories/product_statistics_repository.py:532` | `Project.status == ProjectStatus.COMPLETED` | Drop literal |
| `src/giljo_mcp/repositories/message_repository.py:726` | `Project.status == ProjectStatus.ACTIVE` | Drop literal |
| `src/giljo_mcp/repositories/task_repository.py:261` | `Project.status == ProjectStatus.ACTIVE` | Drop literal |
| `src/giljo_mcp/monitoring/agent_health_monitor.py:191, 269, 357, 520` | `Project.status == ProjectStatus.ACTIVE` | Drop literal |
| `api/endpoints/projects/lifecycle.py:446` | `archive_project` short-circuit guard — replace the hardcoded `("inactive","completed","cancelled","archived","terminated")` tuple with `ProjectStatus.INACTIVE` plus the `LIFECYCLE_FINISHED_STATUSES` derived set, and drop `"archived"` (orphan literal — there is no canonical `archived` value). | Drop literals + fix orphan |
| `api/endpoints/projects/lifecycle.py:451` | `target_status = ProjectStatus.TERMINATED if proj.early_termination else ProjectStatus.COMPLETED` | Drop literal |
| `api/app.py` | Mount the new `project_statuses.router` next to `project_types.router` | New endpoint |

### 4.3 Out-of-scope / leave alone

- Any reference to **`AgentJob.status`** or **`Task.status`** or
  **`AgentExecution.status`** — those are agent/task status enums,
  totally distinct from project status.
- Any reference to **`organizations.status`** in `ops_panel/` — that is
  the SaaS organization lifecycle, also unrelated.
- The `staging_status` column — separate field, not affected.

### 4.4 Tests the implementer must update or add

| Test | Action |
|------|--------|
| `tests/services/test_cancelled_status.py` | Imports `IMMUTABLE_PROJECT_STATUSES`. Will keep working if the constant stays exported as a frozenset of `ProjectStatus` members; adjust assertions if they compared to literal `"cancelled"`. |
| `tests/unit/services/test_list_projects_filtering.py` | Uses status string literals throughout; SQLAlchemy auto-coerces strings to enum on input. Verify tests pass without edits; fix any direct `assert p.status == "active"` to `assert p.status == ProjectStatus.ACTIVE`. |
| `tests/contract/test_status_enum_consistency.py` | Repurpose per §3.5 (implementer-frontend may own the rename in Phase 4). |
| New: `tests/unit/domain/test_project_status_enum.py` | Assert the six enum members, the metadata structure, and that the derived sets match the legacy frozensets. |
| New: `tests/api/test_project_statuses_endpoint.py` | Assert `GET /api/v1/project-statuses/` returns the six metadata objects with the expected keys. |

### 4.5 Backward compatibility

Existing callers that pass `status="completed"` (a Python string) to
service methods continue to work. SQLAlchemy's enum column accepts both
the enum member and its `.value` string. ORM reads return the enum
member; string equality (`p.status == "completed"`) works because
`ProjectStatus("completed") == "completed"` is True (the class inherits
from `str`). Test code that does `p.status == "active"` does not need to
change.

The HTTP API contract is unchanged: response bodies still serialize the
status field as a plain string (FastAPI/Pydantic flattens the enum to
its `.value`).

---

## 5. Implementer-Frontend handoff (Phase 4)

**EDITION SCOPE: Both** — frontend is single-bundle; SaaS reuses CE
components.

### 5.1 New files

| File | Purpose |
|------|---------|
| `frontend/src/composables/useProjectStatuses.js` | Fetches `/api/v1/project-statuses/` once, caches the result, exposes `getMeta(value)`, `validValues`, etc. |

### 5.2 Files modified

| File | What changes |
|------|--------------|
| `frontend/src/components/StatusBadge.vue` | Drop the hardcoded validator literal at line 21. Replace with a runtime check using `useProjectStatuses().validValues.includes(value)` (or rely on the parent to never pass an invalid value and remove the validator entirely — simpler). Replace the hardcoded `STATUS_CONFIG` object with a lookup against the cached metadata. Color resolution: read `var(--{color_token})` from the metadata's `color_token` field via `getComputedStyle`. |
| `frontend/src/stores/projects.js:349` | **Bug fix.** The `update_type === 'closed'` branch currently writes `project.status = 'closed'` — an orphan value that breaks the badge. Replace with: when `update_type === 'closed'`, accept `project_data.status` from the WebSocket payload (the backend sends `'completed'`). |
| `frontend/src/composables/useProjectFilters.js` | No code change required — equality matching works with whatever string the backend sends. Optionally add a defensive filter that drops projects with unknown status values from `filteredProjects` to make the bug above unreachable from the UI. |
| Anywhere else hardcoded status literals appear in `.vue`, `.js`, `.ts` | Sweep with `grep -rE "['\"](inactive\|active\|completed\|cancelled\|terminated\|deleted)['\"]"` over `frontend/src` and replace with imports from `useProjectStatuses`. The only confirmed hits today are the StatusBadge and the projects.js store. |

### 5.3 Tests

| Test | Action |
|------|--------|
| `frontend/tests/stores/projects.handleRealtimeUpdate.spec.js:83` | Currently asserts `store.projects[0].status` is `'closed'` after a closed event. **Update** to assert `'completed'` (the post-fix expected behavior). |
| `tests/contract/test_status_enum_consistency.py` | Rename per §3.5. The test now asserts that `StatusBadge.vue` does NOT contain a hardcoded validator literal AND that `GET /api/v1/project-statuses/` returns the same set as `ProjectStatus`. |

---

## 6. Implementer-DevOps handoff (Phase 3)

**EDITION SCOPE: CE-facing primarily** — installers are CE concern;
migration runs the same on both editions.

### 6.1 Migration smoke checklist

The migration must run cleanly on three boxes representing the upgrade
path. Implementer-DevOps owns running these.

| Box | Path | What to verify |
|-----|------|----------------|
| Local dev (Win) | `python startup.py --verbose` after pulling the branch | Migration applies; `\d projects` shows enum type; existing rows ({completed, deleted, inactive}) preserved; dashboard loads. |
| Dogfood (`giljo@10.1.0.191`, Win 11) | Pull dev branch, restart | Run `SELECT DISTINCT status, COUNT(*) FROM projects GROUP BY 1` BEFORE and AFTER the migration. Confirm the post-state has only canonical values; check the migration log output for `RAISE NOTICE` lines reporting the remap row counts. If any orphan was found, capture the value and add it to §2.3 retroactively (then push a docs follow-up). |
| Demo prod (`gildemo@10.1.0.16`, Ubuntu) | Same as dogfood | Same. |

### 6.2 Orphan-data scenarios to test in the upgrade smoke

Implementer-DevOps must explicitly exercise the pre-flight remap. On a
disposable copy of the dogfood DB (or a fresh local DB seeded by hand),
inject one row of each suspected orphan value before running the
migration:

```sql
INSERT INTO projects (id, tenant_key, product_id, name, alias, description, mission, status, ...)
VALUES
  ('orph1', '...', '...', 'p1', 'X1', '', '', 'archived', ...),
  ('orph2', '...', '...', 'p2', 'X2', '', '', 'closed', ...),
  ('orph3', '...', '...', 'p3', 'X3', '', '', 'paused', ...),
  ('orph4', '...', '...', 'p4', 'X4', '', '', 'staging', ...),
  ('orph5', '...', '...', 'p5', 'X5', '', '', 'gibberish', ...),
  ('orph6', '...', '...', 'p6', 'X6', '', '', NULL, ...);
```

After `alembic upgrade head` succeeds, every row above must be readable
via SQLAlchemy and pass `ProjectStatus(p.status)` validation. Expected
mappings: `archived → completed`, `closed → completed`, `paused →
inactive`, `staging → inactive`, `gibberish → inactive`, `NULL →
inactive`. Capture the migration log output and attach to the
implementer-DevOps closeout message.

### 6.3 Public-deploy DoD

This change touches `migrations/versions/`, `models/projects.py`, and
adds a new endpoint. Per the project CLAUDE.md "Public Deploy —
Definition of Done":
- Local pre-flight green: backend pytest unit, frontend lint+build+test,
  installer integrity check.
- Post-push CI green on private repo (9 required checks).
- After export to public master, verify the slimmer 6-check public CI
  badge stays green.
- Installer-touching changes require real installer runs on Win + Linux
  (AI-TOP at `patrik@10.1.0.163`). Migration runs as part of
  `python startup.py --verbose` so this is exercised by any install
  smoke.

### 6.4 Rollback plan

If the migration succeeds but a downstream defect surfaces in CI or
manual smoke before merge:

1. Run `alembic downgrade -1` to flip the column type back to
   `varchar(50)` (the `downgrade()` per §3.4 is symmetric).
2. Push a revert commit on the private branch.
3. The post-revert state matches pre-migration: enum-typed code in
   service layer would crash on string compare, so the implementer
   needs to either (a) revert the service-layer commits as well, or
   (b) leave them in but ship a follow-up. Coordinate with orchestrator
   before deciding which.

If the migration succeeds and reaches public master before a defect is
found, fix-forward — the public repo "always green" rule (memory note
`feedback_public_repo_must_be_green`) takes precedence over reverting.

---

## 7. Edition-isolation note (verbatim per mission)

> This enum is CE-foundational. SaaS does not extend it; if SaaS ever
> needs a new status, it adds to ProjectStatus in CE (with metadata
> declaring whether SaaS-only).

The Deletion Test still passes after this work: removing every directory
under `saas/`, `saas_endpoints/`, `saas_middleware/`, `frontend/src/saas/`,
and `demo/` leaves the enum, the metadata, the migration, and the
endpoint untouched. CE tests continue to pass; SaaS-conditional code in
those deleted dirs never had a status reference of its own to break.

---

## 8. Open questions / deferred items

- **Phase 0C dogfood + demo data audit** — analyzer could not query
  those boxes. Implementer-DevOps captures the data during smoke testing
  in §6.1 and updates §2.3 if anything unexpected surfaces.
- **`cancel_staging` endpoint after `staging` value removal** — the
  `staging` value never persisted in `status`, but `cancel_staging`'s
  precondition (`status != "staging"`) is a no-op gate post-migration.
  Implementer-backend should either rewrite the precondition to consult
  `staging_status` instead of `status`, or remove the endpoint if its
  contract no longer makes sense. Coordinate with orchestrator.
- **Frontend `closed` status orphan fix** — currently scoped to Phase 4
  (frontend). If the implementer-backend team wants to ship the migration
  ahead of the frontend fix, the bug stays present in production until
  the frontend lands; that is acceptable because the bug is in-memory
  only (never round-trips to the DB).
