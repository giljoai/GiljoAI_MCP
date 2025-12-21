# Devlog – 2025-12-21 – MCPAgentJob Cleanup (0367a–e)

**Date**: 2025-12-21  
**Author**: Backend / Orchestration  
**Scope**: MCPAgentJob deprecation and AgentJob/AgentExecution identity model

---

## Summary

Completed the multi-phase cleanup of the legacy `MCPAgentJob` model in favor of the dual-model architecture:

- `AgentJob` – work order (WHAT)  
- `AgentExecution` – executor instance (WHO)

The 0367 series (a–d) migrated services, API endpoints, and tools. Handover **0367e** finalized runtime cleanup and prompt semantics, leaving `MCPAgentJob` only as a deprecated historical model and in tests.

---

## Changes

### Identity Model

- Confirmed `AgentJob` and `AgentExecution` are the **only** models used for:
  - Orchestrator and agent spawning
  - Agent mission resolution
  - Job/execution status and succession
- `MCPAgentJob` kept as:
  - Deprecated ORM model in `models/agents.py`
  - Historical linkage for templates/projects/tasks
  - Test-time fixture target (to be migrated later)

### Service & Tool Layer

- 0367a: Service layer (`orchestration_service`, `project_service`, `message_service`, `agent_job_manager`) migrated off `MCPAgentJob` with RED→GREEN tests in `tests/services/test_0367a_mcpagentjob_removal.py`.
- 0367b: API endpoints updated to query `AgentJob`/`AgentExecution` and return string UUID identifiers.
- 0367c: Tools and monitoring (orchestration tools, coordination, thin prompt generator) standardized on dual-model semantics.
- 0367e: Final runtime cleanup:
  - `/gil_handover` slash command now operates on `AgentExecution` only.
  - Generic agent template updated to use `agent_id` for `get_agent_mission`.
  - Tool documentation/comments updated to reference `AgentJob` + `AgentExecution` instead of `MCPAgentJob`.

---

## Slash Command: /gil_handover

- **Before**: `src/giljo_mcp/slash_commands/handover.py` loaded orchestrators from `MCPAgentJob` and passed them into `OrchestratorSuccessionManager`, which was already migrated to `AgentExecution`.
- **After**:
  - Slash command queries `AgentExecution` for active orchestrators:
    - `agent_type == "orchestrator"`
    - `status == "working"`
    - Filtered by `tenant_key`, and optionally by `job_id`/`project_id`.
  - Succession:
    - Uses `OrchestratorSuccessionManager` to create a successor `AgentExecution` on the same `job_id`.
    - Keeps `job_id` stable for launch prompts and environment variables.
  - Error path:
    - Returns structured error if no active orchestrator execution exists (no MCPAgentJob fallback).

New tests in `tests/slash_commands/test_handover_0367e.py` cover:

- Happy path: creating a successor for an existing `AgentJob` + `AgentExecution`.
- Error path: no active orchestrator → `success: False`, `error` code.

---

## Agent Template & Prompts

- `src/giljo_mcp/templates/generic_agent_template.py` updated:
  - `agent_id` = `AgentExecution.agent_id` (executor).
  - `job_id` = `AgentJob.job_id` (work order).
  - `get_agent_mission(agent_id, tenant_key)` used as the canonical mission fetch tool.
  - `job_id` kept as the key for `report_progress`, `complete_job`, and `report_error`.

This aligns generic/legacy prompts with the 0366 identity contract and avoids the old `agent_job_id` confusion.

---

## Migration Script Template

A template for archiving legacy MCPAgentJob records has been added:

- `migrations/archive_mcp_agent_jobs.sql`

Purpose:

- Provide a starting point for:
  - Copying `mcp_agent_jobs` into an archive table.
  - Dropping foreign keys / constraints referencing `mcp_agent_jobs`.
  - Eventually dropping or renaming the table after test migration.

The script is intentionally non-destructive and commented; DBAs can adapt it for each environment.

---

## Database Validation Plan

0367e did not directly modify schemas, but we validated behaviorally and prepared a validation plan:

- **Behavioral validation**:
  - `tests/services/test_0367a_mcpagentjob_removal.py` – ensures no service-layer fallback to `MCPAgentJob`.
  - `tests/slash_commands/test_handover_0367e.py` – ensures `/gil_handover` uses `AgentExecution`.
- **Manual DB validation (recommended before dropping MCPAgentJob)**:
  - Confirm no production code queries `mcp_agent_jobs`:
    - `rg "mcp_agent_jobs" src api`
  - Compare row counts between `mcp_agent_jobs` and `agent_jobs`/`agent_executions` for sanity:
    - Ensure new jobs are created only in `agent_jobs`/`agent_executions`.
  - Verify foreign-key references (templates/projects/tasks) still resolve correctly.

Future handover: a dedicated “test identity migration” can:

- Move remaining tests and fixtures off `MCPAgentJob`.
- Execute the archive script in controlled environments.
- Drop or archive the `mcp_agent_jobs` table.

---

## Status & Next Steps

- **Runtime identity model**: Single-source-of-truth on `AgentJob` + `AgentExecution` – COMPLETE.
- **Slash commands and prompts**: Aligned with 0366 contract – COMPLETE.
- **Legacy model**: `MCPAgentJob` deprecated, isolated to models/tests – COMPLETE (for runtime).
- **Future work**:
  - Migrate remaining test fixtures off `MCPAgentJob`.
  - Execute/archive `mcp_agent_jobs` via the new migration template.
  - Update any remaining documentation that still references MCPAgentJob as current.

