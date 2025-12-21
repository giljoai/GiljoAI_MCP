# Handover 0356: MCP Tool Tenant & Identity Consistency (Post‑0366)

**Date**: 2025-12-20
**Status**: ✅ COMPLETED
**Completed**: 2025-12-20
**Priority**: High (Blocks clean 0366 rollout)
**Actual Effort**: ~3 hours
**Depends On**: 0366a (models), 0366b (services), 0366c/0366c‑2 (tool standardization)

---

## Completion Summary

### Test Results
- **19/19 tests passing** in `tests/integration/test_mcp_tool_consistency_0356.py`
- TDD process followed: RED → GREEN → REFACTOR

### Changes Made

| File | Change |
|------|--------|
| `api/endpoints/mcp_http.py` | `orchestrator_id` → `job_id`; Added `tenant_key` to 8 tools |
| `src/giljo_mcp/tools/tool_accessor.py` | Added `tenant_key` to 6 methods; renamed parameter |
| `api/endpoints/mcp_tools.py` | Updated MCP tool schema |
| `src/giljo_mcp/thin_prompt_generator.py` | Updated docs/examples |
| `src/giljo_mcp/prompt_generation/mcp_tool_catalog.py` | Updated tool definitions |
| `src/giljo_mcp/template_seeder.py` | Updated documentation |

### Tools Now Requiring `tenant_key`
`report_progress`, `complete_job`, `report_error`, `acknowledge_job`, `send_message`, `receive_messages`, `list_messages`, `gil_handover`, `get_orchestrator_instructions`

### Identity Naming Cleanup
- Removed all `orchestrator_id` references from MCP schemas
- Aligned with 0366 model: `job_id` for work orders, `agent_id` for executors

---

## Purpose

0366a/b/c completed the **agent identity refactor**:
- Introduced `AgentJob` (work order) and `AgentExecution` (executor instance).
- Standardized MCP tool parameters around **`job_id` = work** and **`agent_id` = executor**.
- Added new services (`MessageService0366b`, `AgentJobManager`) and updated many tools.

This handover closes the remaining gap from the original 0356:
- **Tenant isolation** for MCP tools must be explicit and consistent (`tenant_key` everywhere it’s needed).
- **Tool signatures, ToolAccessor, and service layer** must be fully aligned with the 0366 identity model.
- **Documentation and schemas** must reflect the final, stable parameter contract.

The goal is to make the MCP HTTP surface *boringly consistent* so agents and humans can rely on a single mental model.

---

## Context

### 0366 Identity Model (Authoritative)

- `job_id` (UUID):  
  - Identifies the **AgentJob** (work order).  
  - Persists across orchestrator succession and agent handovers.  
  - Used when the operation is about the *work itself*: mission, status, completing a job, listing executions, etc.

- `agent_id` (UUID):  
  - Identifies an **AgentExecution** (executor instance).  
  - Changes when succession/handover occurs.  
  - Used when the operation targets a **specific executor**: `get_agent_mission`, `receive_messages`, `send_message`, `check_orchestrator_messages`, etc.

0366c/0366c‑2 already updated the major tools to follow this contract, but 0356’s original tenant_key / identity work predates that refactor. We now need a **final alignment pass** focusing on:
- Tenant isolation (`tenant_key`) semantics.
- Consistency between:
  - MCP tool schemas (in `api/endpoints/mcp_http.py`),
  - `ToolAccessor` signatures (in `src/giljo_mcp/tools/tool_accessor.py`),
  - Service layer (`MessageService0366b`, `AgentJobManager`, `OrchestrationService`, context tools).

---

## Problem Statement

### 1. Tenant Key Exposure Is Still Inconsistent

Prior to 0366, we had problems like:
- Service layer methods supporting `tenant_key`, but ToolAccessor and MCP schemas not exposing it.
- Some tools relying on implicit tenant context from `TenantManager`, others requiring explicit `tenant_key`.

After 0366c, we still have a **mixed pattern**:
- Tools like `get_orchestrator_instructions`, `get_agent_mission`, `fetch_context`, `orchestrate_project` clearly require `tenant_key`.
- Other tools (especially messaging and coordination helpers) may:
  - Accept `tenant_key` in services but not advertise it in MCP schemas.
  - Allow falling back to `TenantManager` without clear documentation.

**Risk**:
- Cross‑tenant access bugs if new tools are added without explicit `tenant_key`.
- Confusion for external users about when to pass `tenant_key`.

### 2. Identity Terms Are Still Leaking Old Semantics

Even after 0366c:
- Some tools, docstrings, and comments still refer to:
  - `orchestrator_id` instead of `agent_id` for orchestrator executions.
  - `job_id` when they actually mean “this specific agent execution”.
  - `agent_type` strings as primary identifiers for messaging.

These remnants:
- Make the public MCP surface feel inconsistent.
- Increase the chance of future regressions (people copy old patterns).

---

## Objectives

1. **Tenant Key Standardization**
   - Every MCP tool that touches tenant‑scoped data must:
     - Accept a `tenant_key: str` parameter.
     - Pass it through to the service layer.
     - Declare it correctly in the MCP HTTP schema.
   - Tools that are truly tenant‑agnostic must explicitly document that fact.

2. **Identity Naming Consistency**
   - For each tool, be explicit:
     - Use `agent_id` when targeting a specific executor (AgentExecution).
     - Use `job_id` when targeting a work order (AgentJob).
   - Remove legacy names like `orchestrator_id` and ambiguous `job_id` usages.
   - Ensure ToolAccessor, MCP schemas, and docs match 0366c’s semantic contract.

3. **Single Source of Truth for Agent Identity**
   - Ensure `docs/developer_guides/agent_monitoring_developer_guide.md` and the new MCP protocol quick reference (0361) reference the same parameter naming and meanings.
   - Make sure 0366c remains the authoritative reference and this handover does not introduce divergent conventions.

---

## Scope

### In Scope

1. **MCP HTTP Tool Schemas**
   - File: `api/endpoints/mcp_http.py`
   - Tasks:
     - Audit all tools that touch projects, jobs, agents, or messages.
     - For each, verify:
       - `tenant_key` is present and marked required where appropriate.
       - Identity parameters match 0366c (agent_id vs job_id vs project_id).
       - Descriptions explain semantics briefly (e.g., “agent_id = executor UUID”).

2. **ToolAccessor Signatures**
   - File: `src/giljo_mcp/tools/tool_accessor.py`
   - Verify that:
     - Every MCP tool exposed via `mcp_http` has a corresponding ToolAccessor method with matching parameter names and order.
     - `tenant_key` is plumbed through to the underlying services.
     - Identity parameters (job_id, agent_id) align with services.

3. **Core Services Called by Tools**
   - `src/giljo_mcp/services/message_service_0366b.py`
   - `src/giljo_mcp/services/orchestration_service.py`
   - `src/giljo_mcp/services/project_service.py`
   - `src/giljo_mcp/services/agent_job_manager.py`

   Tasks:
   - Confirm that:
     - Service signatures accept `tenant_key` where appropriate.
     - Identity parameters (job_id vs agent_id) match tool semantics.
   - Where services accept both `tenant_key` and a fallback via `TenantManager`, document precedence and deprecate implicit context where feasible.

4. **Tool‑Level Docstrings**
   - `src/giljo_mcp/tools/*.py` (especially messaging/orchestration/coordination/context tools).
   - Update docstrings and inline comments so they:
     - Use the new identity terminology.
     - Explicitly call out tenant_key where applicable.

### Out of Scope

- Changing the **0366 identity model** itself.
- Adding new tools or capabilities beyond those already planned in other handovers (e.g., 0360).
- Frontend changes (covered in 0366d and 0358).

---

## Implementation Plan

### Step 1: Inventory & Matrix (COMPLETED - TDD RED Phase)

**Test Suite Created**: `tests/integration/test_mcp_tool_consistency_0356.py`
**Test Results**: `tests/integration/test_mcp_tool_consistency_0356_RESULTS.md`

**Summary of Issues Found** (19 tests, 17 failing):

#### HIGH Priority - Identity Naming Issues
| Tool | Current Parameter | Expected Parameter | Status |
|------|------------------|-------------------|--------|
| `get_orchestrator_instructions` | `orchestrator_id` | `job_id` | ❌ FAILING |
| MCP schema | Contains `orchestrator_id` | No `orchestrator_id` refs | ❌ FAILING |

#### MEDIUM Priority - Missing tenant_key in MCP Schemas
| Tool | Has tenant_key? | In Required Array? | Status |
|------|----------------|-------------------|--------|
| `report_progress` | ❌ No | ❌ No | ❌ FAILING |
| `complete_job` | ❌ No | ❌ No | ❌ FAILING |
| `report_error` | ❌ No | ❌ No | ❌ FAILING |
| `acknowledge_job` | ❌ No | ❌ No | ❌ FAILING |
| `send_message` | ❌ No | ❌ No | ❌ FAILING |
| `receive_messages` | ❌ No | ❌ No | ❌ FAILING |
| `list_messages` | ❌ No | ❌ No | ❌ FAILING |
| `gil_handover` | ❌ No | ❌ No | ❌ FAILING |

#### ToolAccessor Missing tenant_key Parameter
| Method | Has tenant_key? | Status |
|--------|----------------|--------|
| `report_progress` | ❌ No | ❌ FAILING |
| `complete_job` | ❌ No | ❌ FAILING |
| `report_error` | ❌ No | ❌ FAILING |

#### Security Tests (Cross-Tenant Isolation)
| Test | Status | Notes |
|------|--------|-------|
| `send_message` cross-tenant block | ✅ PASSING | MessageService correctly enforces tenant_key |
| `receive_messages` cross-tenant block | ✅ PASSING | MessageService correctly enforces tenant_key |
| `report_progress` cross-tenant block | ❌ FAILING | Missing tenant_key parameter |

### Step 2: Tenant Key Alignment (60–90 min)

For each tool in the matrix:

1. **Service Layer**
   - Verify that the service method takes `tenant_key: Optional[str]`.
   - Ensure it **does not silently fall back** to cross‑tenant queries when `tenant_key` is missing.
   - If `TenantManager` fallback is still needed, document it as legacy behavior with a deprecation comment.

2. **ToolAccessor**
   - Add or update `tenant_key` parameter where missing.
   - Pass `tenant_key` through to the service layer.

3. **MCP HTTP Schema**
   - Add `tenant_key` to the tool’s `inputSchema` if it’s not present.
   - Mark as `required` for any tool that:
     - Reads or writes tenant‑scoped data, and
     - Is accessible from external agents over HTTP.

4. **Docs**
   - Update docstrings for the affected tools to mention `tenant_key` explicitly.

### Step 3: Identity Naming Cleanup (45–60 min)

1. Replace ambiguous names in tools and schemas:
   - `orchestrator_id` → `agent_id` (for orchestrator executions).
   - Any `job_id` that is clearly used as an “agent” identifier → `agent_id`.
   - Any `agent_type` being used as a primary routing identifier in tools → migrate to `agent_id` (keeping `agent_type` as metadata only).

2. Confirm identity semantics:
   - Tools that **target a specific executor** (`get_agent_mission`, `receive_messages`, messaging) must use `agent_id`.
   - Tools that operate on **jobs** (`complete_job`, job history) use `job_id`.

3. Update error messages:
   - Example: “Expected `agent_id` (executor UUID), got `job_id`” where appropriate.

### Step 4: Tests (45–60 min)

Add or extend tests to lock in the contract:

1. **ToolAccessor Tests**
   - File: `tests/integration/test_mcp_orchestration_http_exposure.py`
   - Ensure:
     - Each tested tool passes `tenant_key` through.
     - Identity parameters map correctly (no leftover `orchestrator_id` / ambiguous `job_id`).

2. **Service Tests**
   - File: `tests/services/test_message_service_contract.py`
   - Add test that:
     - `send_message` and `receive_messages` behave correctly when `tenant_key` is provided.
     - Cross‑tenant messages are rejected.

3. **Validation / Developer Guide Tests**
   - File: `tests/integration/test_validation_integration.py`
   - Extend existing “protocol validation” cases to assert that:
     - Protocol snippets referencing `report_progress`, `send_message`, etc. match the new parameter names and semantics.

---

## Success Criteria

1. **Tenant Isolation**
   - All stateful MCP tools accept explicit `tenant_key`.
   - No tool silently ignores or guesses tenant context.
   - Cross‑tenant access attempts fail with clear errors.

2. **Identity Semantics**
   - No public MCP tool uses ambiguous identifier names.
   - `agent_id` is used consistently for executors; `job_id` for work orders.
   - Messaging and coordination tools route by `agent_id` and can always map back to `job_id`.

3. **Tool & Doc Alignment**
   - MCP HTTP schemas, ToolAccessor, services, and docs all describe the same parameter set.
   - Developer guides (esp. 0361’s quick reference) align with 0366 and this handover.

4. **Testing**
   - All updated tests pass.
   - New tests fail if:
     - `tenant_key` is omitted where required.
     - Tools attempt to use the wrong identifier (job_id where agent_id is required, etc.).

---

## Risks & Notes

- **Risk (Medium)**: There may still be legacy callers inside the backend that rely on old parameter names.  
  - **Mitigation**: Use search (`rg`) for the old names and update internal call sites alongside schema changes.

- **Risk (Low)**: Documentation drift between this handover, 0366c, and 0361.  
  - **Mitigation**: Treat 0366c as the *semantic* source of truth and have this handover reference, not replace, that contract.

---

## Developer Checklist

- [ ] Build tool/parameter matrix from `mcp_http` and ToolAccessor.
- [ ] Align all tenant_key usage across tools and services.
- [ ] Clean up identity naming (`agent_id` vs `job_id`) in MCP tools and schemas.
- [ ] Update docstrings and ensure 0361 quick reference matches.
- [ ] Add/extend tests for tenant_key and identity semantics.
- [ ] Run full test suite (`pytest tests/`) and fix regressions.

Once complete, the alpha‑trial remediation series and the 0366 identity refactor will share a consistent, explicit contract for how agents identify themselves and which tenant they operate in.

