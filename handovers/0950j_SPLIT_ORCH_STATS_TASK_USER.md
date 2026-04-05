# 0950j: God-Class Split — OrchestrationService + ProtocolBuilder + StatisticsRepository + TaskService + UserService

**Series:** 0950 (Pre-Release Quality Sprint — God-Class Splitting Track)
**Phase:** 10 of 14
**Branch:** `feature/0950-pre-release-quality`
**Edition Scope:** CE
**Priority:** High
**Effort:** Heavy (5-7 hrs)
**Depends on:** 0950i (ProductService + ProjectService splits must be complete)
**Status:** Not Started

### Reference Documents
- **Chain log:** `prompts/0950_chain/chain_log.json`
- **Project rules:** `CLAUDE.md`, `handovers/HANDOVER_INSTRUCTIONS.md`

---

## Context

This is the final god-class splitting session. Five files remain over the class size limit:

| File | Lines | Primary violation |
|------|-------|-------------------|
| `src/giljo_mcp/services/orchestration_service.py` | 1497 | WebSocket helpers mixed into orchestration logic |
| `src/giljo_mcp/services/protocol_builder.py` | 1544 | Large protocol-generation blocks not split into focused sections |
| `src/giljo_mcp/repositories/statistics_repository.py` | 1085 | Job stats and product stats mixed into one repository |
| `src/giljo_mcp/services/task_service.py` | 1042 | Bulk operations entangled with individual CRUD |
| `src/giljo_mcp/services/user_service.py` | 1044 | Password/PIN/auth logic mixed into profile management |

`OrchestrationService` and `ProtocolBuilder` are tightly coupled — tackle them together in a single sub-session before moving to the other three. The three remaining services are independent and can be tackled sequentially.

This is the highest-risk session in the 0950 chain. `OrchestrationService` is called by nearly every other service. Read the `notes_for_next` from 0950i carefully before starting — import path changes from the previous three sessions may affect files touched here.

---

## Pre-Work: Mandatory Caller Discovery

Before moving a single line of code, run all of the following:

```bash
# OrchestrationService callers
grep -rn "OrchestrationService\|orchestration_service" \
  /media/patrik/Work/GiljoAI_MCP/src/ \
  /media/patrik/Work/GiljoAI_MCP/api/ \
  --include="*.py"

# ProtocolBuilder callers
grep -rn "ProtocolBuilder\|protocol_builder" \
  /media/patrik/Work/GiljoAI_MCP/src/ \
  /media/patrik/Work/GiljoAI_MCP/api/ \
  --include="*.py"

# StatisticsRepository callers
grep -rn "StatisticsRepository\|statistics_repository" \
  /media/patrik/Work/GiljoAI_MCP/src/ \
  /media/patrik/Work/GiljoAI_MCP/api/ \
  --include="*.py"

# TaskService callers
grep -rn "TaskService\|task_service" \
  /media/patrik/Work/GiljoAI_MCP/src/ \
  /media/patrik/Work/GiljoAI_MCP/api/ \
  --include="*.py"

# UserService callers
grep -rn "UserService\|user_service" \
  /media/patrik/Work/GiljoAI_MCP/src/ \
  /media/patrik/Work/GiljoAI_MCP/api/ \
  --include="*.py"
```

Record every file and line number across all five searches. There will be many hits. Every reference must be updated by the end of this session.

---

## Sub-Session A: OrchestrationService + ProtocolBuilder

Tackle these together because they share internal dependencies. Splitting them independently risks circular imports.

### Phase A1: Map both files

Read `orchestration_service.py` and `protocol_builder.py` in full. Identify:

**In OrchestrationService — WebSocket broadcast helpers (extract):**
- Methods whose primary job is calling `WebSocketManager.broadcast()` or constructing WebSocket payloads
- Event emission helpers that wrap a single broadcast call
- These move to a focused `orchestration_broadcast_helper.py` (or similar name — choose the name that best describes what it does)

**In OrchestrationService — core orchestration (stays):**
- Job lifecycle management (start, pause, resume, complete, fail)
- Agent coordination calls
- State machine transitions
- Methods that read/write `AgentJob` and related records

**In ProtocolBuilder — protocol section blocks (extract to subpackage):**
- Large `_build_*_section` or `_generate_*_block` methods (over 80 lines each)
- These move to `src/giljo_mcp/services/protocol_sections/` subpackage
- Each file in `protocol_sections/` handles one logical section of the protocol document
- `ProtocolBuilder` becomes a compositor: it imports the section builders and assembles the final protocol

**In ProtocolBuilder — shared assembly logic (stays):**
- The public `build_protocol()` method and its direct orchestration of section order
- Section ordering, header/footer, and final document assembly
- Any helper under 80 lines that does not cleanly belong to a single section

### Phase A2: Create protocol_sections subpackage

```
src/giljo_mcp/services/protocol_sections/
    __init__.py
    <section_name_a>.py
    <section_name_b>.py
    ...
```

Determine section names from the actual code — do not invent names. Use the names already implied by the method names in `ProtocolBuilder`.

`__init__.py` must re-export all section builder classes for clean imports.

Each section file must be under 400 lines. No method within may exceed 200 lines.

### Phase A3: Extract broadcast helper

Create `src/giljo_mcp/services/orchestration_broadcast_helper.py` (or the name that best fits).

Rules:
- May call `WebSocketManager` directly
- Must NOT know about orchestration state machines or job records
- `OrchestrationService` imports this helper; the helper does not import `OrchestrationService`
- All broadcast calls that require a `tenant_key` for filtering must pass it explicitly — no tenant inference from global state

### Phase A4: Reduce both files

After extraction:
- `orchestration_service.py` target: under 1000 lines
- `protocol_builder.py` target: under 1000 lines
- No method over 200 lines in either file

---

## Sub-Session B: StatisticsRepository

### Phase B1: Map the file

Read `src/giljo_mcp/repositories/statistics_repository.py` in full. Classify every method:

**Job/agent/execution statistics (moves to JobStatisticsRepository):**
- Query methods that aggregate over `AgentJob`, `AgentExecution`, or agent-level metrics
- Time-series queries on execution duration, wait times, failure rates

**Product/project statistics (moves to ProductStatisticsRepository):**
- Query methods that aggregate over `Product`, `Project`, or product-level metrics
- Vision document counts, project completion rates, product-scoped dashboards

If a method aggregates across both layers (e.g., "jobs per product"), it belongs in `ProductStatisticsRepository` since the product is the higher-level grouping entity.

### Phase B2: Create both repositories

- `src/giljo_mcp/repositories/job_statistics_repository.py`
- `src/giljo_mcp/repositories/product_statistics_repository.py`

Rules:
- Both are repositories — they own SQL queries and return model or dataclass results
- Neither may call service layer code
- All queries must filter by `tenant_key` — statistics queries that join across multiple tables must apply `tenant_key` at every join anchor where ambiguity exists
- Each file target: under 600 lines
- No method over 200 lines

Provide a backward compatibility shim in the original `statistics_repository.py` if any callers are too numerous to update in this session:

```python
# Temporary re-export until callers are updated
from giljo_mcp.repositories.job_statistics_repository import JobStatisticsRepository
from giljo_mcp.repositories.product_statistics_repository import ProductStatisticsRepository

# Deprecated: use JobStatisticsRepository or ProductStatisticsRepository directly
StatisticsRepository = JobStatisticsRepository  # noqa: F401 — backward compat
```

If callers are few enough to update in this session, remove the original file entirely and update all callers. Do not leave dead shim files.

---

## Sub-Session C: TaskService

### Phase C1: Map the file

Read `src/giljo_mcp/services/task_service.py` in full. Classify every method:

**Individual CRUD / status / assignment (stays in TaskService):**
- Create, read, update, delete single task records
- Individual status transitions (open → in_progress → complete)
- Task assignment to a user or agent
- Individual task validation

**Bulk operations (moves to TaskBulkService):**
- Batch create (create multiple tasks from a list)
- Batch update (update status or assignment for multiple tasks in one call)
- Batch status changes triggered by project-level events
- Any method that operates on a `List[Task]` or takes a list of IDs

### Phase C2: Create TaskBulkService

Create `src/giljo_mcp/services/task_bulk_service.py`.

Rules:
- `TaskBulkService` may call `TaskService` methods for individual operations within a batch
- `TaskService` must NOT import from `task_bulk_service.py`
- All DB queries must filter by `tenant_key`
- Bulk insert/update operations must use SQLAlchemy's `insert().values(...)` or `update()` with a WHERE clause — not a loop of individual `session.add()` calls (performance requirement for batch operations)
- Target: under 400 lines
- No method over 200 lines

### Phase C3: Reduce TaskService

After extraction:
- Target: `task_service.py` under 800 lines
- No method over 200 lines

---

## Sub-Session D: UserService

### Phase D1: Map the file

Read `src/giljo_mcp/services/user_service.py` in full. Classify every method:

**Profile / settings / org membership (stays in UserService):**
- User create, read, update, deactivate
- Profile field management (display name, avatar, preferences)
- User settings management
- Organization membership queries

**Password / PIN / auth-adjacent (moves to UserAuthService):**
- Password hashing, verification, and change flows
- PIN creation, validation, and reset
- Session token management (if any lives here rather than in auth middleware)
- Account recovery flows

### Phase D2: Create UserAuthService

Create `src/giljo_mcp/services/user_auth_service.py`.

Rules:
- `UserAuthService` may call `UserService` to fetch/update the `User` record
- `UserService` must NOT import from `user_auth_service.py`
- Password and PIN operations must use the existing hashing utilities already in the codebase — do not introduce a new hashing path
- All DB queries must filter by `tenant_key`
- Target: under 400 lines
- No method over 200 lines

### Phase D3: Reduce UserService

After extraction:
- Target: `user_service.py` under 800 lines
- No method over 200 lines

---

## Shared Phase: Import Updates and Tenant Isolation Verification

### Phase E: Update all imports

Work through the list compiled in Pre-Work. This will be the longest phase given how many callers `OrchestrationService` has. Update systematically: one file at a time, run the startup check after each batch.

After completing all updates:
```bash
python -c "from api.app import create_app; print('OK')"
```
If this fails, stop and diagnose before touching more files.

### Phase F: Tenant isolation verification

For every new file created in this session, run:

```bash
grep -n "select\|SELECT\|query\|session\." <new_file>
```

For every DB query found, verify `tenant_key` filter presence. Document any query that legitimately does not need a `tenant_key` filter (e.g., a cross-tenant admin aggregate — but these should not exist in CE) and note the justification inline.

### Phase G: Final verification

```bash
# Startup check
python -c "from api.app import create_app; print('OK')"

# Unit tests
python -m pytest tests/unit/ -q --timeout=60 --no-cov

# Lint
ruff check src/ api/
```

All three must pass. Fix or delete failing tests — never skip them.

---

## Constraints

- No commented-out code. Delete removed code.
- No dict-return patterns. All error paths raise exceptions.
- No function may exceed 200 lines in any file touched.
- No class may exceed 1000 lines in any file touched.
- Public interfaces of all five original classes must not change for their retained methods.
- `AgentJobManager` is the only permitted path for agent lifecycle operations — `OrchestrationService` must delegate, not write agent records directly.
- Every DB query in every new and modified file must filter by `tenant_key`.
- No `ruff` violations in the final state.

---

## Acceptance Criteria

- [ ] `orchestration_service.py` under 1000 lines
- [ ] `protocol_builder.py` under 1000 lines
- [ ] `statistics_repository.py` replaced by `job_statistics_repository.py` and `product_statistics_repository.py` (each under 600 lines), or retains a documented shim
- [ ] `task_service.py` under 800 lines; `task_bulk_service.py` exists and is under 400 lines
- [ ] `user_service.py` under 800 lines; `user_auth_service.py` exists and is under 400 lines
- [ ] `protocol_sections/` subpackage exists; no section file exceeds 400 lines
- [ ] No method in any of the above files exceeds 200 lines
- [ ] All DB queries in extracted files filter by `tenant_key`
- [ ] All callers updated and imports verified
- [ ] `python -c "from api.app import create_app; print('OK')"` passes
- [ ] `python -m pytest tests/unit/ -q --timeout=60 --no-cov` passes with zero new failures
- [ ] `ruff check src/ api/` reports zero issues
- [ ] No commented-out code in any modified file

---

## Rollback

If the session goes badly, revert all at once:

```bash
git stash
```

Or revert individual files:
```bash
git checkout -- src/giljo_mcp/services/orchestration_service.py
git checkout -- src/giljo_mcp/services/protocol_builder.py
git checkout -- src/giljo_mcp/repositories/statistics_repository.py
git checkout -- src/giljo_mcp/services/task_service.py
git checkout -- src/giljo_mcp/services/user_service.py
rm -rf src/giljo_mcp/services/protocol_sections/
rm -f src/giljo_mcp/services/orchestration_broadcast_helper.py
rm -f src/giljo_mcp/repositories/job_statistics_repository.py
rm -f src/giljo_mcp/repositories/product_statistics_repository.py
rm -f src/giljo_mcp/services/task_bulk_service.py
rm -f src/giljo_mcp/services/user_auth_service.py
```

---

## Commit Message Format

One commit per sub-session (A through D) is preferred for reviewability:

```
cleanup(0950j): split OrchestrationService + ProtocolBuilder

- Extract WebSocket broadcast helpers into orchestration_broadcast_helper.py
- Extract ProtocolBuilder sections into protocol_sections/ subpackage
- orchestration_service.py reduced from 1497 to <1000 lines
- protocol_builder.py reduced from 1544 to <1000 lines
```

```
cleanup(0950j): split StatisticsRepository into job/product repositories

- Extract job/agent stats into JobStatisticsRepository
- Extract product/project stats into ProductStatisticsRepository
- statistics_repository.py reduced from 1085 lines; both new repos <600 lines
- tenant_key filtering verified in all extracted queries
```

```
cleanup(0950j): split TaskService — extract TaskBulkService

- Extract batch create/update/status-change methods into TaskBulkService
- TaskService retains individual CRUD, transitions, assignment
- task_service.py reduced from 1042 to <800 lines
- tenant_key filtering verified in all extracted queries
```

```
cleanup(0950j): split UserService — extract UserAuthService

- Extract password/PIN/auth methods into UserAuthService
- UserService retains CRUD, profile, settings, org membership
- user_service.py reduced from 1044 to <800 lines
- tenant_key filtering verified in all extracted queries
```

---

## Chain Execution Instructions

### Step 1: Read Chain Log
Read `prompts/0950_chain/chain_log.json`.
- Check `orchestrator_directives` on session `0950j` — if STOP, halt immediately.
- Read `notes_for_next` from session `0950i` — it will describe import path changes from the `ProjectLaunchService` split that directly affect `OrchestrationService` imports.

### Step 2: Mark Session Started
Update session `0950j` in chain_log.json: `"status": "in_progress"`.

### Step 3: Execute
Work through sub-sessions A, B, C, D in order. Run verification after each sub-session. Do not start sub-session B until sub-session A passes all verification checks.

### Step 4: Update Chain Log
Before stopping, update session `0950j` with:
- `tasks_completed`: each sub-session (A/B/C/D) and each extraction within it
- `deviations`: any deviation from this plan and why
- `blockers_encountered`: anything requiring escalation
- `notes_for_next`: critical context for 0950k (Frontend Component Splits) and 0950l (Test Maintenance). Note any test files that now need updating because of changed import paths, and any new service classes that tests must cover.
- `cascading_impacts`: the complete list of new files created and old files reduced; 0950l will need this to prioritize test coverage
- `summary`: one-paragraph summary
- `status`: `"complete"`

### Step 5: STOP
Do NOT spawn the next terminal. The orchestrator handles that.

---

## Progress Updates

*(Agent updates this section during implementation)*
