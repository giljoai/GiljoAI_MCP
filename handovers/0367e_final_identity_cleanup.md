# Handover 0367e: Final Agent Identity Cleanup & Legacy Isolation

**Date**: 2025-12-21  
**Status**: COMPLETE  
**Priority**: HIGH  
**Owner**: Backend / Orchestration  
**Related Handovers**: 0358 (dual-model), 0366a–c (identity model), 0367a–d (MCPAgentJob cleanup)

---

## Context

By the end of 0367d the production code path had been migrated from the legacy `MCPAgentJob` model to the dual-model identity architecture:

- `AgentJob` – work order (WHAT, persistent across succession)  
- `AgentExecution` – executor instance (WHO, per succession attempt)

However, a few pieces still referenced `MCPAgentJob` directly or implied old semantics:

- `/gil_handover` slash command loaded orchestrators via `MCPAgentJob` while the `OrchestratorSuccessionManager` had been fully migrated to `AgentExecution`.
- The legacy `GenericAgentTemplate` prompt still spoke in terms of “MCPAgentJob” and instructed agents to call `get_agent_mission(agent_job_id, …)` instead of `get_agent_mission(agent_id, …)`.
- Comments and high-level tool docs still described “Jobs” as backed by the `MCPAgentJob` table.

This created subtle confusion for humans (and thin-client prompts) even though the runtime identity model was already correct.

---

## Objective

Finalize the identity refactor by:

1. Removing all **runtime** dependencies on `MCPAgentJob` outside the legacy model module and tests.
2. Aligning all **agent-facing prompts/templates** with the 0366 identity contract:
   - `job_id` = work order UUID (AgentJob)
   - `agent_id` = executor UUID (AgentExecution)
3. Updating comments and architectural notes so that “jobs” clearly refer to `AgentJob` + `AgentExecution`, not `MCPAgentJob`.

After this handover:

- `MCPAgentJob` exists only as a **deprecated historical model** (for existing data, relationships, and tests).
- All orchestrator/agent behavior, slash commands, and thin-client prompts use `AgentJob` + `AgentExecution` exclusively.

---

## Scope

**In scope**

- Slash command: `src/giljo_mcp/slash_commands/handover.py`
- Templates: `src/giljo_mcp/templates/generic_agent_template.py`
- Tool docs/comments:
  - `src/giljo_mcp/tools/agent_coordination.py`
  - `src/giljo_mcp/tools/__init__.py`
- New tests for `/gil_handover` behavior (AgentExecution-only).

**Out of scope**

- Dropping the `mcp_agent_jobs` table.
- Removing the `MCPAgentJob` ORM model.
- Migrating all remaining tests off `MCPAgentJob` (covered by future identity/test cleanup).

---

## Semantic Contract (Identity Model – FINAL)

This handover reaffirms and enforces the 0366 identity semantics across all updated code:

- **job_id (AgentJob.job_id)**  
  - “WHAT” – persistent work order.  
  - Used for: job status, progress aggregation, project-level reporting, and completion.

- **agent_id (AgentExecution.agent_id)**  
  - “WHO” – executor instance.  
  - Changes on succession; each instance has its own status/health/progress.
  - Used for: `get_agent_status`, `get_agent_mission`, succession chains, and executor-level monitoring.

- **project_id (Project.id)**  
  - “WHERE” – project workspace; ties jobs and executions to a project.

Slash commands, prompts, and MCP tools must never treat `job_id` and `agent_id` as interchangeable.

---

## Implementation Details

### 1. `/gil_handover` Slash Command (Runtime Fix)

**File**: `src/giljo_mcp/slash_commands/handover.py`

**Before**

- Imported and queried `MCPAgentJob` to find the active orchestrator:
  - `_get_active_orchestrator()` returned `MCPAgentJob`.
  - When `orchestrator_job_id` was provided, the slash command executed a direct `select(MCPAgentJob)` query.
- Passed the resulting `MCPAgentJob` instance into `OrchestratorSuccessionManager`, which is now designed to work with `AgentExecution`.

**After**

- The slash command:
  - Imports `AgentExecution` (and, if needed, `AgentJob`) from `models.agent_identity`.
  - `_get_active_orchestrator()` now returns an `AgentExecution`:
    - Filters by `tenant_key`, `agent_type == "orchestrator"`, and `status == "working"`.
    - Optionally joins `AgentJob` to filter by `project_id` when provided.
  - When `orchestrator_job_id` is provided, it resolves the active orchestrator **execution** by:
    - Filtering `AgentExecution.job_id == orchestrator_job_id`.
    - Applying the same tenant and type/status filters.
- The `OrchestratorSuccessionManager` now receives the correct `AgentExecution` object for:
  - `generate_handover_summary()`
  - `create_successor()`
  - `complete_handover()`

**Behavioral Guarantees**

- Manual slash command succession operates on the **current orchestrator execution**, not the legacy MCPAgentJob row.
- Returned `successor_id` and `GILJO_AGENT_JOB_ID` in the launch prompt remain the **job_id (AgentJob)**, matching thin-client expectations.
- If no matching execution is found, the command returns a structured error (no fallback to MCPAgentJob).

---

### 2. Generic Agent Template (Prompt Semantics Fix)

**File**: `src/giljo_mcp/templates/generic_agent_template.py`

**Before**

- Comments and docs described `job_id` as “UUID of this job (MCPAgentJob)”.
- The template instructed agents to:
  - Call `mcp__giljo-mcp__get_agent_mission(agent_job_id, tenant_key)`.
  - Use `agent_job_id` in example code blocks.

**After**

- Updated template semantics:
  - `agent_id`: Executor UUID (AgentExecution.agent_id).
  - `job_id`: Work order UUID (AgentJob.job_id).
- All examples and tool wiring now use:
  - `mcp__giljo-mcp__get_agent_mission(agent_id, tenant_key)` – resolve mission via executor identity.
  - `job_id` remains the key for progress/completion/report_error tools.
- All references to “MCPAgentJob” have been replaced with the dual-model terminology.

Result: Generic/legacy agent prompts no longer encode the old “agent_job_id” contract and align fully with 0366.

---

### 3. Coordination & Tool Docs (Comment/Doc Cleanup)

**Files**

- `src/giljo_mcp/tools/agent_coordination.py`
- `src/giljo_mcp/tools/__init__.py`

**Changes**

- Updated comments that previously claimed “MCPAgentJob status is authoritative” to instead refer to `AgentJob` via `AgentJobManager`.
- Updated high-level tools package docstring:
  - “Jobs: … Database: MCPAgentJob table” → “Jobs: … Database: AgentJob + AgentExecution tables”.
  - “Orchestration: … Database: MCPAgentJob, Project, Product tables” → “AgentJob, AgentExecution, Project, Product”.

No runtime logic changes were made here; this is to prevent future readers (and agents) from inferring the wrong model.

---

### 4. Tests

**File**: `tests/slash_commands/test_handover_0367e.py`

**Purpose**

- Assert that `/gil_handover` operates purely on `AgentExecution` and does not require `MCPAgentJob`.

**Key Behaviors Tested**

1. Given an active `AgentJob` + `AgentExecution` of type `orchestrator` in a tenant:
   - `handle_gil_handover(db_session, tenant_key, project_id=None, orchestrator_job_id=job_id)`:
     - Returns `success: True`.
     - Returns a `successor_id` (job_id of the same AgentJob) and a non-empty `launch_prompt`.
2. When no matching `AgentExecution` exists for the given tenant/job:
   - The function returns `success: False` with an `error` code (no fallback to MCPAgentJob).

> Note: Coverage thresholds still apply at the global pytest level. This file is designed to be included in the regular suite; running isolated tests may still trigger coverage fail-under warnings, which are unrelated to 0367e behavior.

---

## Success Criteria (0367e)

- [x] No imports or queries of `MCPAgentJob` in `src/giljo_mcp/slash_commands/handover.py`.
- [x] Slash command `/gil_handover` uses `AgentExecution` for orchestrator identity and works end-to-end with the 0366b succession manager.
- [x] Generic agent template references `agent_id`/`job_id` correctly and calls `get_agent_mission(agent_id, tenant_key)`.
- [x] Tools package and coordination comments reflect the `AgentJob` + `AgentExecution` model.
- [x] New tests for `/gil_handover` pass alongside existing 0367a tests (modulo global coverage thresholds).

---

## Notes & Future Work

- `MCPAgentJob` remains in `models/agents.py` as a **deprecated historical model** and is still referenced by some legacy relationships (`templates`, `projects`, `tasks`) and test fixtures. This is intentional to preserve existing data until a dedicated schema/table archival handover.
- A future “test identity migration” handover can:
  - Move remaining tests off `MCPAgentJob`.
  - Remove or archive the `mcp_agent_jobs` table entirely.
  - Simplify remaining relationships to depend only on `AgentJob` and `AgentExecution`.

