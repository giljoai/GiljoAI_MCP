# Handover 0365: Orchestrator Handover Behavior Injection (Post‑0366 Identity Model)

**Date**: 2025-12-20  
**Status**: READY FOR IMPLEMENTATION  
**Priority**: Medium  
**Type**: Architecture Enhancement  
**Estimated Effort**: 6–10 hours  
**Depends On**: 0364 (protocol message handling), 0366a/b/c (AgentJob/AgentExecution + tool standardization)

---

## Context

We now have:
- A clear **agent protocol** (0364) describing 5–6 phases of agent behavior.
- A new **identity model** (0366a/b/c):
  - `AgentJob` (persistent work order, identified by `job_id`).
  - `AgentExecution` (executor instance, identified by `agent_id`).
  - Succession chains modeled via `spawned_by` / `succeeded_by` on AgentExecution.
- Orchestrator succession plumbing via `OrchestratorSuccessionManager` and MCP tools (`mcp__giljo-mcp__create_successor_orchestrator`, etc.).

What we do **not** yet have is:
- A concrete, code‑level strategy for how **successor orchestrators** get appropriate **execution‑phase behavior instructions** after succession.
- A consistent way for successors to call `get_orchestrator_instructions(agent_id, tenant_key)` and receive instructions that reflect the fact that:
  - Staging is already done.
  - Agents are (possibly) already running.
  - The orchestrator’s job is now monitoring, coordinating, and completing the work.

This handover chooses a definitive option and makes it implementable.

---

## Problem

### Current Flow (Simplified)

1. Orchestrator 1 (execution `agent_id=AE1`, `job_id=J1`) performs staging:
   - Discovers agents.
   - Spawns jobs.
   - Activates project.
2. Orchestrator 1 approaches context limit or is manually handed over:
   - Calls `create_successor_orchestrator(current_agent_id=AE1, tenant_key, reason)`.
   - `OrchestratorSuccessionManager` creates new execution `AE2` with the same `job_id=J1`.
3. User launches Orchestrator 2 via thin prompt:
   - Thin prompt instructs: “Call `get_orchestrator_instructions(...)`.”
4. Orchestrator 2 calls `get_orchestrator_instructions(agent_id=AE2, tenant_key)`.
5. **Problem**: The tool returns a **staging‑focused** workflow (tasks 1–7) designed for a fresh orchestrator, not an execution‑phase successor.

As a result:
- Successors are not explicitly guided to:
  - Monitor existing agents.
  - Check messages and progress.
  - Coordinate handoffs.
  - Decide when to close out or escalate.

---

## Design Decision

From the original options (embedded mission text, separate tools, conditional logic, context‑aware staging), we adopt:

> **Option C – Conditional Logic in `get_orchestrator_instructions(agent_id, tenant_key)`**, using the 0366 identity model to decide whether to return:
> - **Staging instructions** (for first‑run orchestrators), or  
> - **Execution‑phase instructions** (for successors).

Rationale:
- Avoids proliferating new tools.
- Keeps the MCP catalog simple for users: “orchestrators always call `get_orchestrator_instructions`.”
- Leverages the AgentJob/AgentExecution model to distinguish first execution vs successor.
- Keeps behavior centralized and auditable.

---

## Desired Behavior

### 1. First‑Run Orchestrator (Instance #1)

When `get_orchestrator_instructions(agent_id, tenant_key)` is called and the corresponding `AgentExecution`:
- Has `instance_number == 1`.
- Has no `spawned_by` (or is not a successor).

Then:
- Return the current **staging‑focused prompt**, as defined by the existing thin‑prompt generator:
  - Tasks: identity, health check, environment understanding, agent discovery, context prioritization, spawning, activation.
  - Includes reference to how agents and project lifetime should be handled (stage → execution).

### 2. Successor Orchestrator (Instance #2+)

When `instance_number > 1` or `spawned_by` is set, indicating this execution is a successor for the same `job_id`:

- Return a **succession‑aware prompt** that:
  - Acknowledges that staging is complete.
  - Provides concise **execution‑phase monitoring instructions** drawn from:
    - 0364 (protocol message handling).
    - Existing execution‑phase guidance in `thin_prompt_generator.py`.
  - Emphasizes:
    - How to check status of existing agents.
    - How and when to poll messages and progress (using the new quick reference from 0361).
    - How to coordinate additional agents or follow‑up work if needed.

#### Example Structure (For Successor)

Conceptual outline of what `get_orchestrator_instructions` should return for successors:

```json
{
  "mode": "successor_execution",
  "job_id": "J1",
  "agent_id": "AE2",
  "staging_summary": "... short summary of what has already happened ...",
  "execution_tasks": [
    "Read previous orchestrator's summary in project memory / handover notes.",
    "List all active AgentExecutions for this job and project.",
    "Monitor agents via report_progress() and receive_messages().",
    "Coordinate follow‑up work or additional agent spawns if needed.",
    "Drive project to completion and ensure closeout / 360 memory is written."
  ],
  "mcp_calls": {
    "list_agents": "some tool using job_id + tenant_key",
    "check_messages": "receive_messages(agent_id, tenant_key)",
    "report_progress": "report_progress(job_id, progress, tenant_key)",
    "succession": "create_successor_orchestrator(agent_id, tenant_key, reason)"
  }
}
```

Exact fields and wording should follow existing patterns in the thin prompt generator and mission response JSON.

---

## Implementation Plan

### Step 1: Detect Successor vs First‑Run (30–45 min)

Files to touch:
- `src/giljo_mcp/tools/orchestration.py`
- `src/giljo_mcp/thin_prompt_generator.py`
- `src/giljo_mcp/services/agent_job_manager.py` (for helper queries, if needed)

Tasks:

1. In `get_orchestrator_instructions(agent_id, tenant_key)`:
   - Use `AgentExecution` and `AgentJob` to load:
     - `agent_id` (execution).
     - `job_id` (work).
     - `instance_number`.
     - `spawned_by` / `succeeded_by`.
   - Determine `is_successor = instance_number > 1 or spawned_by is not None`.

2. Pass `is_successor` (and possibly job context) down into the thin prompt generator:
   - e.g., `_build_orchestrator_prompt(job: AgentJob, execution: AgentExecution, is_successor: bool, ...)`.

### Step 2: Extend Thin Prompt Generator (60–90 min)

File:
- `src/giljo_mcp/thin_prompt_generator.py`

Tasks:

1. Refactor current staging prompt builder into something like:

   ```python
   async def build_orchestrator_prompt(
       job: AgentJob,
       execution: AgentExecution,
       is_successor: bool,
       tenant_key: str,
       db_manager: DatabaseManager,
   ) -> dict[str, Any]:
       if not is_successor:
           return await _build_staging_prompt(...)
       else:
           return await _build_successor_prompt(...)
   ```

2. Implement `_build_successor_prompt`:
   - Summarize what has already happened:
     - Use `job.job_metadata` and any existing 360 memory / handover fields.
   - List execution‑phase tasks:
     - Use guidance from 0364 and agent monitoring developer guide.
   - Provide explicit MCP call examples appropriate for successors:
     - `receive_messages(agent_id, tenant_key)`
     - `report_progress(job_id, progress, tenant_key)`
     - `get_team_agents(job_id, tenant_key)` (0360)
   - Include a clear note that staging is complete and should not be repeated.

3. Preserve protocol structure:
   - Ensure that the returned JSON matches the existing contract expected by the UI and orchestration tests (e.g., fields like `staging_prompt`, `context_framing`, etc. are still present or replaced in a compatible way).

### Step 3: Update MCP Tool & Thin Prompt Usage (30–45 min)

Files:
- `src/giljo_mcp/tools/orchestration.py`
- `src/giljo_mcp/template_seeder.py`
- Any relevant handover‑driven thin prompt examples.

Tasks:
1. Ensure the tool docstring for `get_orchestrator_instructions`:
   - Explains that:
     - For first‑run orchestrators (instance 1), the tool returns staging instructions.
     - For successors (instance > 1), it returns execution‑phase monitoring instructions.
2. Update any templates and developer docs (cross‑link with 0361):
   - Thin prompts for orchestrators should always use `agent_id` + `tenant_key`.
   - There is no separate “successor” tool – the behavior is conditional.

### Step 4: Tests (60–90 min)

Files:
- `tests/services/test_orchestration_service_agent_mission.py`
- `tests/thin_prompt/test_thin_prompt_unit.py`
- Possibly new tests under `tests/tools/test_orchestration_0365.py`

Test cases:

1. **First‑Run Orchestrator**
   - Create `AgentJob` + `AgentExecution` with `instance_number=1`, no `spawned_by`.
   - Call `get_orchestrator_instructions(agent_id, tenant_key)`.
   - Assert:
     - Response contains staging tasks.
     - No explicit “successor” mode flag (or `mode="staging"`).

2. **Successor Orchestrator**
   - Create `AgentJob` + first execution (`AE1`) + successor execution (`AE2`) with `instance_number=2`, `spawned_by=AE1.agent_id`.
   - Call `get_orchestrator_instructions(agent_id=AE2, tenant_key)`.
   - Assert:
     - Response indicates `mode="successor_execution"` (or equivalent).
     - Staging tasks are not repeated.
     - Execution‑phase tasks and monitoring guidance are present.

3. **Multi‑Level Succession**
   - Add third execution (`AE3`) with `instance_number=3`, `spawned_by=AE2.agent_id`.
   - Confirm successors continue to receive execution‑phase instructions.

4. **Backward Compatibility**
   - Ensure existing tests that assume staging behavior for instance #1 still pass.

---

## Success Criteria

1. **Behavior**
   - First‑run orchestrators receive staging‑focused instructions as before.
   - Successor orchestrators receive **execution‑phase monitoring and coordination instructions**, not staging again.

2. **Identity Model Integration**
   - `get_orchestrator_instructions` uses `agent_id` + `tenant_key` and derives `job_id` via `AgentExecution`.
   - Succession behavior is tied explicitly to `instance_number` and `spawned_by`/`succeeded_by`.

3. **Thin Prompt Simplicity**
   - From the user’s perspective, thin prompts remain simple:
     - “Call `get_orchestrator_instructions(agent_id, tenant_key)`.”
   - No new MCP tools are needed for successors.

4. **Testing**
   - New tests cover both staging and successor paths.
   - Existing tests still pass without modification to their expectations of the staging flow.

---

## Developer Checklist

- [ ] Implement successor detection in `get_orchestrator_instructions(agent_id, tenant_key)`.
- [ ] Extend thin prompt generator with `_build_successor_prompt`.
- [ ] Update tool docstrings and templates to explain successor behavior.
- [ ] Add tests for first‑run vs successor orchestrators and succession chains.
- [ ] Run `pytest tests/` and fix any regressions.

Once this handover is implemented, orchestrator succession will be a **first‑class, documented behavior**: successors start with the right mental model and instructions, rather than re‑reading staging tasks that no longer apply.

