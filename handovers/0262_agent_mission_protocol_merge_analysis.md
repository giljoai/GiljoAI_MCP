# Handover 0262: Agent Mission Protocol Merge Analysis

## Status: RESEARCH / DISCUSSION

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

## Recommendation

**Option C** appears most aligned with the thin-client architecture:

1. Agent calls ONE tool: `get_agent_mission()`
2. Gets EVERYTHING needed to execute
3. No need to know about GenericAgentTemplate separately
4. Works for both multi-terminal and CLI mode

The template would need a new method:
```python
def render_with_mission(self, ..., mission: str) -> str:
    # Render template but replace "Your Mission" section
    # with actual mission content instead of fetch instructions
```

---

## Questions for Discussion

1. Should `get_agent_mission()` return a complete executable prompt or just data?
2. Is the 6-phase protocol too verbose for CLI mode where agents are short-lived?
3. Should CLI mode agents have a simplified protocol?
4. How do we handle the "What You'll Receive" section that promises fields not implemented?

---

## Related Handovers

- **0260**: Claude Code CLI Toggle Enhancement (predecessor)
- **0261**: CLI Implementation Prompt (defines two-phase flow)
- **0246b**: Generic Agent Template Implementation (created the template)

---

## Next Steps

1. Decide on merge strategy (A, B, C, or D)
2. Implement chosen approach
3. Update CLI implementation prompt to leverage merged response
4. Test both multi-terminal and CLI mode flows
