# 0510/0511 Current State & Next-Agent Prompt

**Scope:** Handover 0510 (Fix Broken Test Suite) and 0511a/0511 (Smoke + Integration Tests)  
**Author:** Agentic CLI session (Codex/Serena)  
**Date:** 2025-11-13+ (post-template stabilization)

---

## 1. High-Level Status

- Application is **operational**; core workflows run (see `report_CLI.md`, `CCW_REPORT_2025-11-13.md`, `combined_findings.md`).
- Project 500 series is in **Phase 3**: making tests a reliable specification and cleaning up remaining 23 gaps.
- This session focused on **templates/auth/DB** and compatibility shims:
  - Template create/update/get/history/reset endpoints are now behaviorally aligned with the refactored backend and tests.
  - Auth dependencies now support Authorization Bearer tokens in addition to cookies and API keys.
  - DB schema for `template_archives` is aligned with the current ORM (dual fields).
  - Legacy endpoints removed by refactor (`orchestration.py`, `setup.py`) have been reintroduced as **thin compatibility modules**.
- Remaining work for 0510/0511 is mainly in **project completion endpoints**, **agent job/health**, and **smoke test wiring**.

---

## 2. What Has Already Been Done (This Session)

### 2.1 Template Models & Schema

**Files:**
- `src/giljo_mcp/models/templates.py`
- `template_archives` table in Postgres (`giljo_mcp` and `giljo_mcp_test`)

**Changes:**
- `AgentTemplate.category`:
  - Now has `default="role"`, `server_default="role"`, `nullable=False`.
  - Fixes NOT NULL violations and matches the “role-based default” semantics.
- `TemplateArchive`:
  - Extended ORM to include:
    - `system_instructions: Text (nullable)`
    - `user_instructions: Text (nullable)`
  - DB migrations not applied in this file, but **columns were added directly** in the dev/test DBs via:
    ```sql
    ALTER TABLE template_archives
        ADD COLUMN IF NOT EXISTS system_instructions TEXT;
    ALTER TABLE template_archives
        ADD COLUMN IF NOT EXISTS user_instructions TEXT;
    ```
  - See `handovers/Modify_install.md` for how to make this permanent via Alembic and install.py.

### 2.2 Template Endpoints (CRUD / History / Preview)

**Files:**
- `api/endpoints/templates/__init__.py`
- `api/endpoints/templates/crud.py`
- `api/endpoints/templates/history.py`
- `api/endpoints/templates/preview.py`
- `api/endpoints/templates/models.py`
- `api/endpoints/templates/dependencies.py`

**Key behaviors now implemented and tested:**

- **Create (`POST /api/v1/templates/`)**:
  - Validates template name (lowercase, length, uniqueness).
  - Validates system prompt via `validate_system_prompt`.
  - Auto-fills `background_color` from role (`get_role_color`).
  - Supports CLI tools (`claude`, `codex`, `gemini`, `generic`) and model defaults.

- **Get/List (`GET /api/v1/templates/{id}`, `/api/v1/templates/`)**:
  - Tenant-scoped queries using `tenant_key` from authenticated user.
  - Response model includes:
    - `system_instructions` (read-only)
    - `user_instructions`
    - `template_content` (merged view)
    - `is_system_role` flag based on system-managed roles (currently `{"orchestrator"}`).

- **Update (`PUT /api/v1/templates/{id}`)**:
  - **system_instructions**:
    - Explicitly **blocked**:
      - If present in the request body, returns `403` with detail:  
        `"system_instructions is read-only; use reset-system to restore defaults"`.
  - **template_content**:
    - Revalidated via `validate_system_prompt` on update (short or invalid prompts return `400`).
    - If updated, also updates `system_instructions` for backward-compat legacy support.
  - **user_instructions**:
    - Updatable.
    - Before mutating, creates a `TemplateArchive` snapshot that includes both `system_instructions` and `user_instructions`.
  - **role/background_color**:
    - If role changes, `background_color` is recomputed using `get_role_color`.
  - **8-role active limit (user roles only)**:
    - When `is_active` changes for a **non-system** role:
      - Delegates to `TemplateService.validate_active_agent_limit(...)`.
      - If the change would exceed the configured limit (7 user roles + reserved orchestrator), returns `409` with the service’s error message.

- **History & Reset (`api/endpoints/templates/history.py`)**:
  - `GET /api/v1/templates/{id}/history`:
    - Returns tenant-scoped list of `TemplateHistoryResponse`.
  - `POST /api/v1/templates/{id}/restore/{archive_id}`:
    - Archives current version (full dual fields), then restores from the selected archive.
  - `POST /api/v1/templates/{id}/reset`:
    - Archives current version and clears user-customizable fields (user instructions, behavioral rules, success criteria, tags).
  - `POST /api/v1/templates/{id}/reset-system`:
    - Archives the previous system instructions + user instructions.
    - Resets `system_instructions` to a canonical block that includes:
      - `acknowledge_job()`
      - `report_progress()`
      - `complete_job()`
      - `get_next_instruction()`
    - Preserves `user_instructions`.
  - Multi-tenant behavior:
    - If template exists under a different tenant:
      - Returns `403` `"Access denied for this template"`.
    - If template does not exist at all:
      - Returns `404`.

### 2.3 Auth Dependencies

**File:** `src/giljo_mcp/auth/dependencies.py`

**Changes:**
- `get_current_user` now supports:
  - JWT cookie (`access_token`).
  - `X-API-Key`.
  - `Authorization: Bearer <token>` (for CLI/API clients and tests).
- `get_current_user_optional` mirrors this behavior.
- This unblocks tests that create cross-tenant tokens via `JWTManager.create_access_token` and use them via `Authorization: Bearer ...`.

### 2.4 Compatibility Shims (for refactor cleanup)

**Files:**
- `api/endpoints/orchestration.py`
- `api/endpoints/setup.py`

**Orchestration shim:**
- Restores legacy module `api.endpoints.orchestration` expected by old tests.
- Re-exports:
  - `ProjectOrchestrator` from `src/giljo_mcp/orchestrator.py`.
  - A `router` that includes `api.endpoints.agent_jobs.orchestration.router`.

**Setup shim:**
- Restores `api.endpoints.setup` expected by `tests/unit/test_first_run_detection.py`.
- Implements:
  - `async check_first_run(request: Request) -> {"first_run": bool}`:
    - Prefers DB-based admin detection via `request.app.state.api_state.db_manager`.
    - Falls back to `SetupStateManager` with `tenant_key="default"`.
  - `GET /api/setup/first-run` wrapper.

---

## 3. Key Design Decisions (Lock These In)

1. **Orchestrator is a system-managed master agent**
   - Defined in `src/giljo_mcp/system_roles.py`:
     - `SYSTEM_MANAGED_ROLES = {"orchestrator"}`.
   - Orchestrator templates are protected:
     - Cannot be modified or deleted via standard template API endpoints.
     - Used as the “master” orchestrating agent for projects.
   - Tests in `tests/test_orchestrator_protection.py` codify this behavior.

2. **8-role limit applies to user-managed roles only**
   - Orchestrator is **reserved** outside the user quota.
   - `TemplateService.validate_active_agent_limit` enforces:
     - Max 7 distinct active **non-system** roles per tenant (with orchestrator as system-managed).
   - API-level enforcement in `update_template` respects this:
     - Uses the service method for non-system roles only.
     - System-managed roles are not toggleable.

3. **Template archives capture both system and user instructions**
   - `TemplateArchive` stores:
     - `system_instructions`, `user_instructions`, and `template_content`.
   - Updates and resets create archive entries that reflect the pre-change dual fields.

4. **Auth behavior**
   - JWT cookies and Bearer tokens are both first-class:
     - Web: cookie-based `access_token`.
     - CLI/API/tests: `Authorization: Bearer <jwt>`.
   - API keys remain supported via `X-API-Key`.

---

## 4. Source Documents the Next Agent Should Read

To get deeper context and align with the broader plan, the next agent should read (in this order):

1. **Master Plan & Project 500:**
   - `handovers/Projectplan_500.md`
   - `handovers/COMPLETE_EXECUTION_PLAN_0083_TO_0200.md`

2. **Refactor context:**
   - `handovers/REFACTORING_ROADMAP_0120-0130.md`
   - `handovers/REFACTORING_ROADMAP_0131-0200.md` (for what comes after 0500 series, not for immediate work)

3. **System health & gap analysis (from three independent agents):**
   - `handovers/report_CLI.md`  (CLI agent, bottom-up testing)
   - `handovers/CCW_REPORT_2025-11-13.md`  (CCW agent, top-down health)
   - `handovers/Codex_review.md`  (Codex agent, static/import graph analysis)
   - `handovers/combined_findings.md`  (consolidated conclusions)

4. **Specific to this phase (0510/0511/0511a):**
   - `handovers/0510_phase2b_api_test_migration_results.md`
   - `handovers/0511a_smoke_tests_critical_workflows.md`
   - `handovers/Modify_install.md` (DB migration & install flow notes)
   - This file: `handovers/0510_0511_current_state_and_prompt.md`

5. **Architecture & flows:**
   - `CLAUDE.md` (architecture)
   - `handovers/start_to_finish_agent_FLOW.md` (orchestrator and agent orchestration behavior)

---

## 5. Remaining Work (Checklist for Next Agent)

The templates/auth/DB slice of 0510 is largely complete. Remaining work for full 0510/0511 completion is primarily in these areas:

### 5.1 Project Completion & Close-Out Endpoints

**Files:**
- `api/endpoints/projects/completion.py`
- `src/giljo_mcp/services/project_service.py`
- Tests:
  - `tests/api/test_launch_project_endpoint.py`
  - Any other tests referencing project completion/continue-working.

**Tasks:**
- Replace 501 stubs with real implementations:
  - `close_out_project`:
    - Use `ProjectService` to mark projects as completed/closed.
    - Ensure tenant isolation and status transitions align with design docs.
  - `continue_working` (or equivalent):
    - Reopen/extend a project from a completed state where permitted.
- Align status codes and response payloads with tests and handover expectations.

### 5.2 Agent Jobs, Health, and Websocket Endpoints

**Files:**
- `api/endpoints/agent_jobs/*`
- `api/endpoints/agent_health.py` (or equivalent)
- Websocket handlers in `api/endpoints/agent_jobs_websocket.py` / `api/endpoints/agent_jobs/*`.
- Tests:
  - `tests/api/test_agent_health_endpoints.py`
  - `tests/api/test_agent_jobs_websocket.py`
  - `tests/api/test_regenerate_mission.py`

**Tasks:**
- Ensure:
  - Health endpoints correctly reflect job status and tenant isolation.
  - Cancel/force-fail endpoints set appropriate statuses and return expected payloads.
  - Websocket tests see the expected broadcasts.

### 5.3 Smoke Tests (0511a) & Integration Glue

**Files:**
- `tests/smoke/`:
  - `test_product_vision_smoke.py`
  - `test_project_lifecycle_smoke.py`
  - `test_succession_smoke.py`
  - `test_tenant_isolation_smoke.py`
  - `test_settings_smoke.py`

**Tasks:**
- Re-run:
  - `pytest tests/smoke -m smoke --no-cov`
- Fix any remaining harness issues:
  - Auth (cookies/tokens) for smoke tests.
  - Route prefixes (`/api/v1/...` vs legacy paths).
  - Any residual dependency mismatches.

### 5.4 Full API Sweeps & Coverage

**Files:** `tests/api/*`, `.coveragerc`, `pyproject.toml`

**Tasks:**
- Run:
  - `pytest tests/api -q --no-cov`
  - Then (once stable) `pytest tests -v` with coverage.
- Treat any failures as either:
  - Outdated tests (update them to match refactored behavior and handover design).
  - Real behavior gaps (fix endpoints/services accordingly).

---

## 6. Suggested Prompt for the Next Agent

You can paste this prompt to a fresh agent (e.g., Claude Code CLI, Codex CLI, or Serena-enabled environment) to continue:

```text
Execute remaining work for Handover 0510 (Fix Broken Test Suite) and 0511a/0511 (Smoke + Integration Tests) following production-grade standards.

Project Context:
- Master Plan: handovers/Projectplan_500.md
- Architecture: CLAUDE.md
- Orchestrator / Agent Flow: handovers/start_to_finish_agent_FLOW.md
- Current 0510/0511 state: handovers/0510_0511_current_state_and_prompt.md
- Install/migration notes: handovers/Modify_install.md
- Health & gap analysis: handovers/report_CLI.md, handovers/CCW_REPORT_2025-11-13.md, handovers/Codex_review.md, handovers/combined_findings.md

Constraints & Design Rules:
- Orchestrator is a system-managed master agent and NOT user-toggleable via template APIs.
- 8-role limit applies to user-managed roles only (7 user roles + reserved orchestrator).
- Use TemplateService.validate_active_agent_limit for business logic; endpoints remain thin.
- Tests should be treated as specifications, but update them when they conflict with architecture decisions documented in handovers and code.

Execution Focus (for this agent session):
1. Read the documents listed above, especially:
   - handovers/0510_0511_current_state_and_prompt.md
   - handovers/0510_phase2b_api_test_migration_results.md
   - handovers/0511a_smoke_tests_critical_workflows.md
2. Implement and stabilize:
   - Project completion/close-out endpoints in api/endpoints/projects/completion.py
   - Agent health/job endpoints and websocket behavior
3. Make all tests green in:
   - tests/api/test_launch_project_endpoint.py
   - tests/api/test_agent_health_endpoints.py
   - tests/api/test_agent_jobs_websocket.py
   - tests/api/test_regenerate_mission.py
   - tests/smoke/*
4. Run pytest (with --no-cov initially), then with coverage once stable, respecting .coveragerc thresholds.
5. Update handovers and/or add a new completion summary documenting what was fixed and any remaining known gaps.
```

---

This file is meant to be the **single starting point** for the next agent: it summarizes what has been done, codifies key decisions (especially around orchestrator and the 8-role limit), and points to the deeper docs they should read before continuing the work on 0510 and 0511.  

