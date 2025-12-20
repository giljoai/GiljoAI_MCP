# Handover 0360: Medium-Priority Tool Enhancements (Post‑0366 Identity Model)

**Date**: 2025-12-20  
**Status**: READY FOR IMPLEMENTATION  
**Priority**: Medium  
**Type**: MCP Tool Enhancement  
**Estimated Effort**: 4–5 hours  
**Related Issues**: #10 (message filtering), #11 (team discovery), #14 (file_exists utility)  
**Depends On**: 0366a/b/c (AgentJob/AgentExecution + tool standardization), 0356 (tenant/identity consistency audit)

---

## Context

The original 0360 handover identified three ergonomics gaps for agents:

1. **Message noise** – `receive_messages()` returning an agent’s own progress messages.
2. **Team blindness** – no easy way for an agent to discover its teammates on the current project.
3. **File safety** – no lightweight way to check file existence without a full read.

Since that document was written, the **0366 identity refactor** landed:
- `AgentJob` (work order) vs `AgentExecution` (executor instance).
- `agent_id` (executor UUID) vs `job_id` (work UUID).
- `MessageService0366b` routes messages by `agent_id`, not by ambiguous `job_id` or `agent_type`.

This updated handover keeps the original goals but **re-specs the tools in terms of the 0366 model**.

---

## Goals

1. Enhance `receive_messages()` with **filtering options** that make sense in an `agent_id` world.
2. Add a `get_team_agents()` tool to expose **team awareness** based on AgentJob/AgentExecution.
3. Add a `file_exists()` utility tool for safe filesystem checks (within the MCP sandbox).

All changes must:
- Respect tenant isolation (`tenant_key`).
- Use `agent_id` for executor‑level operations and `job_id` for job‑level ones.
- Align with the standard MCP tool contracts defined in 0366c.

---

## 1. Message Filtering for `receive_messages()`

### Problem

Agents currently see unnecessary noise in `receive_messages()`:
- Their own progress/status messages appear in the queue.
- System/broadcast messages can overshadow direct, actionable messages.

Post‑0366, messages are associated with **AgentExecution** via `agent_id`, and `MessageService0366b` already:
- Excludes the sender from broadcast recipients.
- Stores metadata such as `_from_agent_id`, `_from_agent_type`, `_message_type`, etc.

We now want a **thin filtering layer** on top of this model.

### Desired Behavior

New MCP tool signature (conceptual):

```python
@tool
async def receive_messages(
    agent_id: str,
    tenant_key: str,
    exclude_self: bool = True,
    exclude_progress: bool = True,
    message_types: Optional[list[str]] = None,
) -> dict[str, Any]:
    """
    Retrieve and auto‑acknowledge pending messages for this agent execution.

    - agent_id: AgentExecution.agent_id (executor UUID).
    - tenant_key: Tenant isolation key.
    - exclude_self: If True, filter out messages where from_agent_id == agent_id.
    - exclude_progress: If True, filter out messages of type "progress".
    - message_types: Optional allow‑list of message types (e.g., ["direct", "system"]).
    """
```

Notes:
- This is a **backward‑compatible extension**:
  - Existing callers that don’t pass the new flags get sane defaults.
  - The underlying `MessageService0366b` API already distinguishes sender vs recipients.

### Implementation Sketch

1. **Service Layer** – `MessageService0366b.receive_messages`
   - Extend query to:
     - Join or filter on `_from_agent_id` (in metadata) when `exclude_self` is True.
     - Filter by `message_type` when `message_types` is provided.
   - Keep auto‑acknowledgement behavior as defined in earlier handovers (0326/0362).

2. **ToolAccessor & MCP Schema**
   - Expose `exclude_self`, `exclude_progress`, `message_types` as optional parameters.
   - Update `api/endpoints/mcp_http.py` to reflect the new parameters and defaults.

3. **Tests**
   - Add tests to `tests/services/test_message_service_contract.py` and a new `tests/tools/test_agent_communication_0360.py`:
     - When `exclude_self=True`, an agent does not see its own messages.
     - When `exclude_progress=True`, `message_type="progress"` messages are filtered out.
     - When `message_types` is specified, only those types are returned.

---

## 2. `get_team_agents()` – Team Discovery Tool

### Problem

Agents have no easy, structured way to discover teammates:
- Who else is working on this project?
- Which agents are orchestrators vs specialists?
- What is each teammate’s `agent_id` and `agent_type`?

After 0366:
- The **team** can be derived from `AgentJob` + `AgentExecution` for a given project/job.

### Desired Behavior

New MCP tool signature (conceptual):

```python
@tool
async def get_team_agents(
    job_id: str,
    tenant_key: str,
    include_inactive: bool = False,
) -> dict[str, Any]:
    """
    List agent executions (teammates) associated with this job/project.

    - job_id: AgentJob.job_id (the work order UUID).
    - tenant_key: Tenant isolation key.
    - include_inactive: If True, include completed/decommissioned executions.
    """
```

Returned data (example):

```json
{
  "success": true,
  "team": [
    {
      "agent_id": "ae-orch-001",
      "job_id": "job-abc",
      "agent_type": "orchestrator",
      "status": "working",
      "instance_number": 2
    },
    {
      "agent_id": "ae-impl-002",
      "job_id": "job-abc",
      "agent_type": "implementer",
      "status": "waiting",
      "instance_number": 1
    }
  ]
}
```

### Implementation Sketch

1. **Service Layer**
   - Add a method to `AgentJobManager` or a dedicated `TeamService`:

   ```python
   async def list_team_agents(job_id: str, tenant_key: str, include_inactive: bool) -> list[AgentExecution]:
       # Query AgentJob by job_id + tenant_key, then its executions.
   ```

2. **ToolAccessor & MCP Tool**
   - Add a `get_team_agents()` MCP tool under agent coordination/communication tools.
   - Wire it through ToolAccessor to the service method.

3. **Tests**
   - Integration tests that:
     - Create an `AgentJob` with multiple `AgentExecution` rows.
     - Assert that `get_team_agents(job_id, tenant_key)` returns the expected team members.
     - Check that `include_inactive=False` only returns active/running executions.

4. **Usage in Templates**
   - Update relevant agent templates (via 0353/0361) to show example usage:
     - “Call `get_team_agents(job_id, tenant_key)` to discover your teammates and broadcast results.”

---

## 3. `file_exists()` – File Existence Utility

### Problem

Agents currently have to:
- Use a “read file” tool and catch exceptions just to see if a file exists.
- Potentially waste tokens and runtime by reading entire file contents.

We want a simple utility aligned with existing MCP file tools and the per‑tenant sandbox.

### Desired Behavior

New MCP tool signature (conceptual):

```python
@tool
async def file_exists(
    path: str,
    tenant_key: str,
) -> dict[str, Any]:
    """
    Check whether a file or directory exists within the allowed workspace.

    Returns:
      - exists: bool
      - is_file: bool
      - is_dir: bool
    """
```

Example response:

```json
{
  "success": true,
  "path": "src/app.py",
  "exists": true,
  "is_file": true,
  "is_dir": false
}
```

### Implementation Sketch

1. **Service Implementation**
   - Add a small helper (likely in an existing file tools module) that:
     - Resolves the path within the tenant’s workspace (respecting any existing sandbox rules).
     - Uses `pathlib.Path` to check existence.

2. **MCP Tool & Schema**
   - Register `file_exists` in `mcp_http` and ToolAccessor.
   - Ensure `tenant_key` is required so the server can locate the correct workspace root.

3. **Tests**
   - Unit tests that:
     - Return `exists=False` for missing paths.
     - Correctly distinguish between file and directory.
   - Optional: integration test verifying that the tool is exposed via MCP HTTP.

---

## Testing & Validation

### Unit & Service Tests

- `tests/services/test_message_service_contract.py`
  - Add cases for `exclude_self`, `exclude_progress`, `message_types`.
- `tests/services/test_agent_job_manager_0366b.py`
  - Add cases for `list_team_agents`.
- File tools tests:
  - Add `test_file_exists_basic` under a new or existing file tools test module.

### Tool-Level Tests

- `tests/tools/test_agent_communication_0360.py`
  - Exercise `receive_messages` filter options via the MCP layer.
- `tests/tools/test_agent_coordination_0360.py`
  - Exercise `get_team_agents`.
- `tests/tools/test_file_utils_0360.py`
  - Exercise `file_exists`.

---

## Success Criteria

1. `receive_messages()` has optional, well‑documented filters that:
   - Reduce self‑noise and progress noise by default.
   - Allow callers to opt into custom filtering patterns.
2. `get_team_agents()` provides a simple, consistent way for agents to discover teammates using the 0366 identity model.
3. `file_exists()` gives agents a safe, cheap way to check for files/directories without reading contents.
4. All new tools and parameters:
   - Respect `tenant_key`.
   - Use `agent_id`/`job_id` consistently with 0366c.
   - Are documented in the MCP protocol quick reference (0361).

---

## Developer Checklist

- [ ] Implement `receive_messages` filters in `MessageService0366b` + MCP tool.
- [ ] Implement `get_team_agents` service + MCP tool.
- [ ] Implement `file_exists` service + MCP tool.
- [ ] Update MCP schemas (`mcp_http`) and ToolAccessor.
- [ ] Add tests for all three enhancements.
- [ ] Run `pytest tests/` and fix regressions.
- [ ] Update agent templates/docs with new capabilities (coordinated with 0361).

