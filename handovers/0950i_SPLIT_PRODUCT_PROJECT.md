# 0950i: God-Class Split — ProductService + ProjectService

**Series:** 0950 (Pre-Release Quality Sprint — God-Class Splitting Track)
**Phase:** 9 of 14
**Branch:** `feature/0950-pre-release-quality`
**Edition Scope:** CE
**Priority:** High
**Effort:** Heavy (5-7 hrs)
**Depends on:** 0950h (MessageService split must be complete before this session)
**Status:** Not Started

### Reference Documents
- **Chain log:** `prompts/0950_chain/chain_log.json`
- **Project rules:** `CLAUDE.md`, `handovers/HANDOVER_INSTRUCTIONS.md`

---

## Context

Two service files exceed class size limits in the same session:

- `src/giljo_mcp/services/product_service.py` — 1743 lines. Vision document upload, processing, and summarization logic is embedded in a service whose core responsibility is product CRUD and configuration management.
- `src/giljo_mcp/services/project_service.py` — 1298 lines. The `launch_project` method alone is 219 lines and coordinates agent spawning — orchestration logic that does not belong in a CRUD service.

Both files sit at the `Product` and `Project` layers of the entity hierarchy. Changes here have downstream impact on `Job` and `Agent` layers. Treat this session as high-risk and verify cascading effects explicitly.

---

## Pre-Work: Mandatory Caller Discovery

Before moving a single line of code, run all of the following:

```bash
# ProductService callers
grep -rn "ProductService\|product_service" \
  /media/patrik/Work/GiljoAI_MCP/src/ \
  /media/patrik/Work/GiljoAI_MCP/api/ \
  --include="*.py"

# ProjectService callers
grep -rn "ProjectService\|project_service" \
  /media/patrik/Work/GiljoAI_MCP/src/ \
  /media/patrik/Work/GiljoAI_MCP/api/ \
  --include="*.py"

# Vision-specific methods
grep -rn "vision_upload\|vision_analysis\|vision_summary\|summarize_vision\|process_vision\|upload_vision" \
  /media/patrik/Work/GiljoAI_MCP/src/ \
  /media/patrik/Work/GiljoAI_MCP/api/ \
  --include="*.py"

# launch_project and spawn-related methods
grep -rn "launch_project\|spawn_agent\|agent_spawn" \
  /media/patrik/Work/GiljoAI_MCP/src/ \
  /media/patrik/Work/GiljoAI_MCP/api/ \
  --include="*.py"
```

Record every file and line number. Every reference must be updated.

---

## Scope

**Primary files:**
- `src/giljo_mcp/services/product_service.py` (1743 lines)
- `src/giljo_mcp/services/project_service.py` (1298 lines)

**New files to create:**
- `src/giljo_mcp/services/product_vision_service.py` — vision upload, analysis trigger, summary storage
- `src/giljo_mcp/services/project_launch_service.py` — launch orchestration, agent spawning coordination

---

## ProductService Split (1743 lines)

### Phase 1: Map ProductService

Read `src/giljo_mcp/services/product_service.py` in full. Classify every method:

**CRUD / config / tuning / tech stack (stays in ProductService):**
- Product create, read, update, delete
- Product configuration management
- Tuning configuration
- Tech stack operations
- Core feature management
- Any method that operates on the product record or its directly owned config tables

**Vision document operations (moves to ProductVisionService):**
- Vision document upload and storage
- Vision analysis trigger (launching background summarization)
- Analysis status tracking
- Summary storage and retrieval
- Any method whose primary responsibility is the vision document lifecycle

If a method is ambiguous, keep it in `ProductService`.

### Phase 2: Create ProductVisionService

Create `src/giljo_mcp/services/product_vision_service.py`.

Rules:
- `ProductVisionService` may call `ProductService` methods to fetch the parent `Product` record
- `ProductService` must NOT import from `product_vision_service.py`
- All DB queries must filter by `tenant_key`
- No method may exceed 200 lines
- Constructor must accept `db_session` and any other required dependencies (match the pattern of existing services)

After the 0840 JSONB normalization series, vision data likely lives in dedicated columns or tables. Verify the schema before assuming method placement. Read the relevant migration file or model definition to confirm.

### Phase 3: Reduce ProductService

After extraction:
- Target: `product_service.py` under 1000 lines
- No method over 200 lines
- Verify no vision lifecycle logic remains in `ProductService` (grep for vision-related method names)

---

## ProjectService Split (1298 lines)

### Phase 4: Map ProjectService

Read `src/giljo_mcp/services/project_service.py` in full. Classify every method:

**CRUD / status / closeout (stays in ProjectService):**
- Project create, read, update, delete
- Project status transitions
- Project closeout and archival
- Any method that operates solely on the project record

**Launch orchestration (moves to ProjectLaunchService):**
- `launch_project` (219 lines — exceeds 200-line limit, must be extracted AND broken up)
- Agent spawning coordination called from launch
- Pre-launch validation that goes beyond simple record checks
- Any method whose primary purpose is kicking off a new execution run

### Phase 5: Break launch_project

`launch_project` at 219 lines exceeds the 200-line limit. The extraction to `ProjectLaunchService` is mandatory, but is not sufficient on its own. Break the method into named sub-methods:

Suggested decomposition (verify against actual code):
- `_validate_launch_preconditions(project, tenant_key)` — checks project state, product availability
- `_prepare_agent_assignments(project, tenant_key)` — resolves which agents to spawn
- `_spawn_project_agents(assignments, tenant_key)` — delegates to `AgentJobManager.spawn_agent()`
- `launch_project(project_id, tenant_key)` — orchestrates the above three, under 50 lines

Each sub-method must be under 100 lines. None may bypass the service layer: agent spawning goes through `AgentJobManager`, not raw DB writes.

### Phase 6: Create ProjectLaunchService

Create `src/giljo_mcp/services/project_launch_service.py`.

Rules:
- `ProjectLaunchService` may call `ProjectService` to fetch the `Project` record
- `ProjectLaunchService` MUST use `AgentJobManager` for agent lifecycle operations — no direct DB writes for agent records
- `ProjectService` must NOT import from `project_launch_service.py`
- All DB queries must filter by `tenant_key`
- No method may exceed 200 lines

### Phase 7: Reduce ProjectService

After extraction:
- Target: `project_service.py` under 900 lines
- No method over 200 lines
- Verify no launch/spawn logic remains in `ProjectService`

---

## Shared Phase: Import Updates and Tenant Isolation Verification

### Phase 8: Update all imports

For every file discovered in Pre-Work:
- Callers of vision methods update imports to `ProductVisionService`
- Callers of launch methods update imports to `ProjectLaunchService`
- `ProductService` and `ProjectService` CRUD callers need no import change
- Update dependency injection wiring in endpoints if needed

After updating:
```bash
grep -rn "from giljo_mcp.services.product_service import\|from giljo_mcp.services.project_service import" \
  /media/patrik/Work/GiljoAI_MCP/ --include="*.py"
```
Every remaining hit must import only symbols that still exist in those files.

### Phase 9: Tenant isolation verification

For every new file (`product_vision_service.py`, `project_launch_service.py`):

```bash
grep -n "select\|SELECT\|query\|session\." \
  /media/patrik/Work/GiljoAI_MCP/src/giljo_mcp/services/product_vision_service.py

grep -n "select\|SELECT\|query\|session\." \
  /media/patrik/Work/GiljoAI_MCP/src/giljo_mcp/services/project_launch_service.py
```

For every DB query found, verify the `tenant_key` filter is present. This is non-negotiable.

### Phase 10: Cascading impact check

The entity hierarchy is `Product → Project → Job → Agent`. This session touches the top two layers. Verify:

1. `OrchestrationService` — does it call `launch_project`? If so, update its import to `ProjectLaunchService`.
2. `MessageService` / `MessageRoutingService` (split in 0950h) — do they call `ProductService` or `ProjectService`? If so, verify those call sites still work after the split.
3. MCP tools under `src/giljo_mcp/tools/` — do any tools call vision or launch methods directly? Update if so.
4. Endpoints under `api/endpoints/` — update any that injected the old services and now need the extracted ones.

### Phase 11: Verification

Run after every individual split:

```bash
# Startup check
python -c "from api.app import create_app; print('OK')"

# Unit tests
python -m pytest tests/unit/ -q --timeout=60 --no-cov

# Lint
ruff check src/ api/
```

All three must pass before proceeding. Fix or delete failing tests — never skip them.

---

## Constraints

- No commented-out code. Delete removed code.
- No dict-return patterns. All error paths raise exceptions.
- No function may exceed 200 lines.
- No class may exceed 1000 lines.
- The public interfaces of `ProductService` and `ProjectService` must not change for their remaining methods. Callers of CRUD and status methods need zero modification.
- `AgentJobManager` is the only permitted path for agent lifecycle operations in `ProjectLaunchService` — no direct agent table writes.
- Every DB query in all four files must filter by `tenant_key`.
- No `ruff` violations in the final state.

---

## Acceptance Criteria

- [ ] `src/giljo_mcp/services/product_service.py` is under 1000 lines
- [ ] `src/giljo_mcp/services/project_service.py` is under 900 lines
- [ ] `product_vision_service.py` and `project_launch_service.py` exist and are under 1000 lines each
- [ ] No method in any of the four files exceeds 200 lines
- [ ] `launch_project` is decomposed into named sub-methods in `ProjectLaunchService`
- [ ] All DB queries in extracted files filter by `tenant_key`
- [ ] All callers updated and imports verified
- [ ] `python -c "from api.app import create_app; print('OK')"` passes
- [ ] `python -m pytest tests/unit/ -q --timeout=60 --no-cov` passes with zero new failures
- [ ] `ruff check src/ api/` reports zero issues
- [ ] No commented-out code in any modified file

---

## Rollback

```bash
git checkout -- src/giljo_mcp/services/product_service.py src/giljo_mcp/services/project_service.py
rm -f src/giljo_mcp/services/product_vision_service.py src/giljo_mcp/services/project_launch_service.py
```

---

## Commit Message Format

Two commits are acceptable (one per service) or a single combined commit:

```
cleanup(0950i): split ProductService — extract ProductVisionService

- Extract vision upload/analysis/summary methods into ProductVisionService
- ProductService retains CRUD, config, tuning, tech stack operations
- product_service.py reduced from 1743 lines to <1000
- tenant_key filtering verified in all extracted queries
```

```
cleanup(0950i): split ProjectService — extract ProjectLaunchService

- Extract launch_project + agent spawning into ProjectLaunchService
- Decompose 219-line launch_project into named sub-methods
- ProjectLaunchService delegates agent lifecycle to AgentJobManager
- ProjectService retains CRUD, status transitions, closeout
- project_service.py reduced from 1298 lines to <900
- tenant_key filtering verified in all extracted queries
```

---

## Chain Execution Instructions

### Step 1: Read Chain Log
Read `prompts/0950_chain/chain_log.json`.
- Check `orchestrator_directives` on session `0950i` — if STOP, halt immediately.
- Read `notes_for_next` from session `0950h` — it may describe routing service call paths that intersect with `ProductService` or `ProjectService`.

### Step 2: Mark Session Started
Update session `0950i` in chain_log.json: `"status": "in_progress"`.

### Step 3: Execute
Follow the ProductService split (Phases 1-3) first, run verification, then the ProjectService split (Phases 4-7), run verification, then the shared phases (8-11).

### Step 4: Update Chain Log
Before stopping, update session `0950i` with:
- `tasks_completed`: each extraction completed
- `deviations`: any deviation from this plan and why
- `blockers_encountered`: anything requiring escalation
- `notes_for_next`: critical context for 0950j — especially if `OrchestrationService` or `ProtocolBuilder` call `launch_project` and need their imports updated
- `cascading_impacts`: any call path changes from `OrchestrationService` perspective that the 0950j agent must be aware of
- `summary`: one-paragraph summary
- `status`: `"complete"`

### Step 5: STOP
Do NOT spawn the next terminal. The orchestrator handles that.

---

## Progress Updates

*(Agent updates this section during implementation)*
