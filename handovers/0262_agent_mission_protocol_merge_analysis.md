# Handover 0262: Agent Mission Protocol Merge Analysis

## Status: PARTIAL DECISION / READY FOR IMPLEMENTATION (CLI SUBAGENTS)

## Context

During Handover 0260/0261 implementation, we discovered a disconnect between two components that should work together:

1. **`GenericAgentTemplate`** - Full 6-phase protocol for agent execution
2. **`get_agent_mission()`** - MCP tool that returns agent mission from database

This handover documents the analysis and proposes a merge strategy.

---

## Code Locations

### GenericAgentTemplate
**File**: `src/giljo_mcp/templates/generic_agent_template.py`
**Lines**: 12-272
**Purpose**: Provides unified protocol for ALL agent types in multi-terminal mode

### get_agent_mission() MCP Tool
**File**: `src/giljo_mcp/tools/orchestration.py`
**Lines**: 1963-2006
**Purpose**: Fetches agent mission from database for thin-client agents

### get_generic_agent_template()
**File**: `src/giljo_mcp/tools/orchestration.py`
**Lines**: 2009-2082
**Purpose**: Renders GenericAgentTemplate with injected variables (used in multi-terminal mode)

---

## Current State Comparison

### What GenericAgentTemplate Contains

```
# GENERIC AGENT - MULTI-TERMINAL MODE

## Your Identity
- Agent ID, Job ID, Product, Project, Tenant (injected)

## Standard Protocol (ALL Agents Follow This)

### Phase 1: Initialization
- Verify identity
- Check MCP health: health_check()
- Claim job: acknowledge_job(job_id, agent_id)
- Read CLAUDE.md
- Confirm understanding

### Phase 2: Mission Fetch
- Call: get_agent_mission(job_id, tenant_key)
- Parse mission and requirements
- Understand scope
- Identify deliverables

### Phase 3: Work Execution
- Execute mission
- Follow GiljoAI standards
- Track progress at 25%, 50%, 75%, 100%
- Collect outputs

### Phase 4: Progress Reporting
- Call: report_progress(job_id, progress)
- Include specific details
- Report blockers/decisions
- At 100%: comprehensive summary

### Phase 5: Communication
- Send: send_message(to_agent_id, message)
- Check: get_next_instruction(job_id, agent_type, tenant_key)

### Phase 6: Completion
- Call: complete_job(job_id, result)
- Provide actionable info for successors
- Document decisions/blockers

## Your Mission
Instructions to call get_agent_mission() and expected response format

## GiljoAI Standards & Expectations
- Code Quality (ruff, black, type hints, docstrings, pathlib)
- Testing (TDD, >80% coverage)
- Documentation
- Multi-Tenant Safety
- Database & Services patterns
- Version Control

## Communication Protocol
- Receiving Instructions example
- Reporting Errors example
- Coordination Example

## Success Criteria
- Tests pass
- Code follows standards
- Changes committed
- Documentation updated
- Multi-tenant isolation enforced
```

### What get_agent_mission() Returns

```python
return {
    "agent_job_id": agent_job_id,
    "agent_name": agent_job.agent_name,
    "agent_type": agent_job.agent_type,
    "mission": agent_job.mission or "",  # Raw mission text only
    "thin_client": True,
    "estimated_tokens": estimated_tokens,
}
```

### What GenericAgentTemplate PROMISES get_agent_mission() Returns

```json
{
    "success": true,
    "mission": "<full mission text for this job>",
    "context": {
        "project_id": "...",
        "product_id": "...",
        "agent_type": "<your agent type>",
        "priority": "high/medium/low",
        "deadline": "ISO timestamp or null",
        "related_agents": ["<list of other agents>"]
    },
    "previous_work": [
        {"agent": "implementer", "summary": "..."},
        {"agent": "tester", "summary": "..."}
    ]
}
```

---

## The Disconnect

| Aspect | GenericAgentTemplate | get_agent_mission() |
|--------|---------------------|---------------------|
| Protocol phases | Full 6-phase protocol | None |
| MCP tool examples | acknowledge_job, report_progress, complete_job, send_message, get_next_instruction | None |
| Mission content | References get_agent_mission() | Returns raw mission text |
| Context metadata | Promises project_id, product_id, priority, deadline, related_agents | Not implemented |
| Previous work | Promises previous agent summaries | Not implemented |
| GiljoAI standards | Embedded in template | Not included |
| Success criteria | Defined | Not included |

---

## Usage Pattern Analysis

### Multi-Terminal Mode (Toggle OFF)
1. User copies prompt from Jobs tab for each agent
2. Prompt comes from `get_generic_agent_template()` which renders `GenericAgentTemplate`
3. Template includes full protocol + tells agent to call `get_agent_mission()`
4. Agent calls `get_agent_mission()` and gets raw mission
5. **Works because**: Protocol is in the initial prompt, mission fetched separately

### Claude Code CLI Mode (Toggle ON)
1. User copies ONE prompt for orchestrator
2. Orchestrator spawns agents via Task tool with `subagent_type`
3. Task tool agent needs to call `get_agent_mission()` to know what to do
4. Agent gets raw mission only - **NO protocol, NO lifecycle, NO communication patterns**
5. **Broken because**: Agent doesn't know HOW to execute, just WHAT to do

---

## Merge Options

### Option A: Enhance get_agent_mission() Response

Add protocol to the response:

```python
return {
    "agent_job_id": agent_job_id,
    "agent_name": agent_job.agent_name,
    "agent_type": agent_job.agent_type,
    "mission": agent_job.mission or "",
    "thin_client": True,
    "estimated_tokens": estimated_tokens,
    # NEW: Add protocol
    "protocol": {
        "phases": [...],  # 6-phase lifecycle
        "mcp_tools": [...],  # Available tools with examples
        "communication": {...},  # How to coordinate
        "completion": {...},  # How to finish
    },
    # NEW: Add context (as promised)
    "context": {
        "project_id": project_id,
        "product_id": product_id,
        "priority": "normal",
        "related_agents": [...],
    },
}
```

**Pros**: Single tool call gets everything
**Cons**: Large response, duplicates template content

### Option B: CLI Mode Instructs Agents to Fetch Template

CLI implementation prompt tells orchestrator to instruct each Task tool agent:
1. First call `get_generic_agent_template(agent_id, job_id, ...)`
2. Then call `get_agent_mission(job_id, tenant_key)`

**Pros**: Reuses existing components
**Cons**: Two calls, more complex orchestrator instructions

### Option C: Merge Template INTO get_agent_mission()

When `get_agent_mission()` is called, render and return the full template with mission embedded:

```python
async def get_agent_mission(agent_job_id: str, tenant_key: str) -> dict:
    # Fetch job from DB
    agent_job = ...

    # Render full template with mission embedded
    template = GenericAgentTemplate()
    full_prompt = template.render_with_mission(
        agent_id=agent_job.agent_id,
        job_id=agent_job_id,
        product_id=agent_job.product_id,
        project_id=agent_job.project_id,
        tenant_key=tenant_key,
        mission=agent_job.mission,  # Inject mission into template
    )

    return {
        "agent_job_id": agent_job_id,
        "agent_name": agent_job.agent_name,
        "agent_type": agent_job.agent_type,
        "full_prompt": full_prompt,  # Complete ready-to-execute prompt
        "estimated_tokens": len(full_prompt) // 4,
    }
```

**Pros**: Single call, complete prompt, mission pre-embedded
**Cons**: Requires template modification, larger response

### Option D: Create New Unified Tool

New MCP tool `get_agent_execution_context()` that combines:
- Template protocol
- Mission from database
- Context metadata
- Related agent info

Keep `get_agent_mission()` as lightweight mission-only fetch.

**Pros**: Clean separation, backward compatible
**Cons**: Another tool to maintain

---

## Recommendation (Updated)

**Option C (merged behavior)** remains the best fit for the thin-client architecture, with a **refinement for Claude Code CLI subagents**:

1. Agents still call a single tool: `get_agent_mission(agent_job_id, tenant_key)`.
2. That call returns everything needed to execute (mission + key metadata) **and** is treated as the job’s atomic “start” in CLI mode.
3. GenericAgentTemplate / agent templates describe this behavior so agents do not need to call a separate `acknowledge_job()` in CLI subagent flows.
4. Multi-terminal mode may continue to use the same tool, but can optionally keep `acknowledge_job()` for queue-style flows.

The template will still benefit from a helper like:
```python
def render_with_mission(self, ..., mission: str) -> str:
    # Render template but replace "Your Mission" section
    # with actual mission content instead of fetch instructions
```
but for **Claude Code CLI MODE** the key behavioral decision is about how the tools change state, not how much text is embedded.

---

## Decision v1 – CLI Subagents (Claude Code CLI Mode)

This section records the agreed behavior for **Claude Code CLI mode**, where agents run as subagents in the same terminal and are not individually visible to the user.

### 1. `get_agent_mission` = atomic job start (CLI subagents)

For agents spawned as Claude Code subagents (toggle ON):

- Agents MUST call:
  - `get_agent_mission(agent_job_id, tenant_key)` as their **first MCP action** (after optional `health_check()`).
- On the **first** successful call for a job in `waiting` state, the server MUST:
  - Set `mission_acknowledged_at = now()` for that `MCPAgentJob`.
  - If current `status == "waiting"` (or alias `"pending"`), set:
    - `status = "working"` (active execution), and
    - `started_at = now()`.
  - Emit WebSocket events to drive the dashboard:
    - `job:mission_acknowledged` with `{job_id, mission_acknowledged_at, tenant_key}`
      - Drives the “Job Acknowledged” checkmark column in Jobs/Agent table views.
    - `agent:status_changed` with `{job_id, old_status, status="working", ...}`
      - Drives the status chip from “Waiting” → “Working”.
- On subsequent calls for the same job:
  - Return the same mission payload and metadata.
  - **Do not** change status or timestamps (idempotent re-read).

**Implication:** For CLI subagents, `get_agent_mission` is the single, obvious “I have read my mission and started work” signal, and the UI reflects this without needing `acknowledge_job`.

### 2. Role of `acknowledge_job` after this change

We **keep** `acknowledge_job(job_id, agent_id, tenant_key)` but narrow its use:

- Primary use cases:
  - Queue/worker pattern: `get_pending_jobs` → `acknowledge_job` → `get_agent_mission` for generic worker agents (non-CLI, or future external workers).
  - Admin / HTTP flows where a human explicitly “claims” a job via `/api/agent-jobs/{job_id}/acknowledge`.
- Not required in Claude Code CLI subagent templates:
  - Templates for CLI subagents should **not** instruct agents to call `acknowledge_job` during Phase 1.
  - Existing documentation should describe `acknowledge_job` as a queue/worker tool, not part of the standard CLI subagent startup sequence.

`acknowledge_job` still:

- Transitions `waiting` → `working`,
- Sets `started_at` and `mission_acknowledged_at` (for non-CLI flows),
- Emits `agent:status_changed` for the UI.

But for hidden CLI subagents, those responsibilities are fulfilled by `get_agent_mission` instead.

### 3. Minimal MCP tool set for CLI subagents

To keep CLI subagent prompts thin and behavior predictable, we standardize on this tool set:

- **Initialization**
  - `health_check()` – optional but recommended first call to verify MCP connectivity.
  - `get_agent_mission(agent_job_id, tenant_key)` – required; atomic “claim + mission fetch” for CLI subagents.

- **Work & coordination**
  - `send_message(to_agents, content, project_id, message_type="direct", priority="normal", from_agent)`  
    - Primary channel for all agent-to-agent and agent-to-user communication.
  - `get_next_instruction(job_id, agent_type, tenant_key)`  
    - Friendly “read messages / instructions addressed to me” wrapper over the message queue; agents should poll this between major steps.

- **Completion / failure**
  - `complete_job(job_id, result)`  
    - Marks job as complete, emits status change, records completion time and summary.
  - `report_error(job_id, error)`  
    - Marks job failed/blocked, stores error, emits status change for the dashboard.

- **Optional / coarse-grained**
  - `report_progress(job_id, progress)`  
    - Allowed but should be used sparingly (major milestones) since progress can also be conveyed via `send_message(..., message_type="progress")`.

### 4. UI semantics in CLI mode

With these semantics in place, for Claude Code CLI subagents:

- **“Job Acknowledged” column** shows:
  - Whether the agent has ever successfully called `get_agent_mission` (i.e., `mission_acknowledged_at` is set).
- **Status chip** shows:
  - `waiting` until the first mission fetch,
  - `working` after `get_agent_mission` or `acknowledge_job` (depending on flow),
  - `complete`, `failed`, `blocked`, or `cancelled` after `complete_job` / `report_error` / cancel.
- **Message counters and audit views** (see Handover 0331) remain the primary way for users to see what each hidden subagent has actually done or requested.

This matches the visual expectations in the workflow slides: mission read/acknowledged, active/working, completed/failed, plus rich message history.

---

## Open Questions / Future Work

1. **Template coupling vs data-only response**
   - For CLI mode we are leaning toward **data-first**: `get_agent_mission` returns structured mission and context data, while templates (GenericAgentTemplate + agent `.md` files) provide protocol text. We may still add `full_prompt` in the response later, but it is not required for this decision.
2. **Multi-terminal mode alignment**
   - Multi-terminal agents can either adopt the same “`get_agent_mission` = atomic start” semantics or continue using `acknowledge_job` explicitly. This decision can be deferred; the CLI mode behavior is safe and backward-compatible.
3. **Context/previous_work payload**
   - The template still promises `context` and `previous_work`; we should implement at least a minimal version of these fields in the service response and gradually fill them out.

---

## Related Handovers

- **0260**: Claude Code CLI Toggle & Execution Mode (UI + behavior switch)
- **0261**: CLI Implementation Prompt (orchestrator thin prompt and Task tool usage)
- **0246b**: Generic Agent Template Implementation (6-phase protocol)
- **0297**: UI Message Status and Job Signaling (mission_acknowledged_at + events)

---

## Next Steps

1. Implement the `get_agent_mission` atomic start semantics in `OrchestrationService.get_agent_mission` (and ensure ToolAccessor + HTTP MCP code paths use it).
2. Confirm `job:mission_acknowledged` and `agent:status_changed` are emitted as described for the first mission fetch.
3. Update GenericAgentTemplate and CLI agent templates so **CLI subagents**:
   - Call `get_agent_mission(agent_job_id, tenant_key)` as the first MCP tool, and
   - Do **not** call `acknowledge_job()` unless they are using queue/worker flows.
4. Update 0260/0261 documentation to reference this decision for CLI mode.
5. Add/extend tests covering:
   - First vs subsequent `get_agent_mission` calls,
   - Status and timestamp transitions,
   - WebSocket event emission,
   - Dashboard “Job Acknowledged” and status behavior in CLI mode.
