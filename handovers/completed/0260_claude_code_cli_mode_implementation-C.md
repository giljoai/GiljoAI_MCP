# Handover 0260: Claude Code CLI Mode Toggle Implementation

**Status**: In Progress
**Started**: 2025-11-29
**Tools**: CLI (backend, MCP tools, database, integration tests)
**Estimated Effort**: 4-6 hours

---

## Problem Statement

The UI toggle for "Enable Claude Code CLI" exists in JobsTab.vue but is not wired to the backend. The orchestrator and specialist agents receive the same instructions regardless of execution mode, preventing:

1. **Claude Code CLI mode** - Orchestrator cannot spawn subagents via Task tool with @ mentions
2. **Multi-terminal mode** - Agents don't know team roster for MCP communication via `send_message()`

---

## Solution Overview

Wire the UI toggle to backend, store execution mode in orchestrator job metadata, and update MCP tools to return mode-specific instructions with team roster.

### Two-Phase Workflow

#### **Phase 1: Staging** (Jobs Already Created)
When user clicks **[Stage Project]**:
- Orchestrator creates mission plan
- Spawns agent jobs in database with missions
- Enables **[Launch Jobs]** button

#### **Phase 2: Implementation** (Execute Existing Jobs)
When user clicks **[Launch Jobs]**:

**Claude Code CLI Mode (Toggle ON)**:
- Orchestrator prompt: "Fetch instructions from MCP"
- MCP returns: "Use Task tool to spawn subagents with @ mentions"
- Single terminal, orchestrator spawns all agents

**Multi-Terminal Mode (Toggle OFF - Default)**:
- Orchestrator prompt: "Fetch instructions from MCP"
- MCP returns: "Coordinate via send_message(), user launches agents manually"
- Each agent gets copy-paste prompt with team roster
- Multiple terminals, user launches each agent

---

## Architecture

### Data Flow

```
┌─────────────────────────────────────────────────┐
│ JobsTab.vue                                     │
│ ┌──────────────────────────────────────────┐   │
│ │ Toggle: usingClaudeCodeSubagents = true  │   │
│ │ User clicks [Launch Jobs]                │   │
│ └──────────────────────────────────────────┘   │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│ PUT /api/jobs/{orchestrator_job_id}/            │
│     execution-mode                              │
│ Body: { mode: 'claude_code' }                   │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│ Database: MCPAgentJob.metadata                  │
│ {                                               │
│   "execution_mode": "claude_code"               │
│ }                                               │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│ User copies orchestrator prompt                 │
│ Orchestrator calls:                             │
│ get_orchestrator_instructions(job_id, ...)      │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│ MCP Tool: get_orchestrator_instructions()       │
│ 1. Read job.metadata['execution_mode']          │
│ 2. Build team roster from project's agent jobs  │
│ 3. Return mode-specific instructions + roster   │
└─────────────────────────────────────────────────┘
```

### MCP Response Structure

#### Claude Code CLI Mode Response
```python
{
    "mission": "Your condensed mission with field priorities...",
    "execution_mode": "claude_code",
    "spawning_instructions": """
You are in Claude Code CLI mode.

Spawn subagents using the Task tool with @ mentions:

@implementer - You are agent {agent_id}, job {job_id}.
Fetch your mission: get_agent_mission('{job_id}', '{tenant_key}')

@tester - You are agent {agent_id}, job {job_id}.
Fetch your mission: get_agent_mission('{job_id}', '{tenant_key}')

All agents run in THIS terminal. You can see their output directly.
""",
    "team_roster": [
        {"agent_type": "implementer", "agent_id": "uuid-1", "job_id": "uuid-a", "name": "Implementer"},
        {"agent_type": "tester", "agent_id": "uuid-2", "job_id": "uuid-b", "name": "Tester"}
    ]
}
```

#### Multi-Terminal Mode Response
```python
{
    "mission": "Your condensed mission with field priorities...",
    "execution_mode": "multi_terminal",
    "coordination_instructions": """
You are coordinating agents in separate terminal windows.

The user will manually launch each agent. You should:
- Monitor agent progress via WebSocket updates
- Send instructions via: send_message(to_agent_id='{agent_id}', message='...')
- Broadcast to all: send_message(to_agent_id='broadcast', message='...')
- Check for responses via dashboard notifications

Each agent will run in their own terminal window with their own prompt.
""",
    "team_roster": [
        {"agent_type": "implementer", "agent_id": "uuid-1", "job_id": "uuid-a", "name": "Implementer"},
        {"agent_type": "tester", "agent_id": "uuid-2", "job_id": "uuid-b", "name": "Tester"}
    ],
    "mcp_commands": {
        "send_message": "send_message(to_agent_id='<uuid>' or 'broadcast', message='<content>', priority='medium')",
        "check_messages": "get_next_instruction(job_id='{your_job_id}', agent_type='{your_type}', tenant_key='{tenant_key}')"
    }
}
```

#### Agent Mission Response (Both Modes)
```python
{
    "mission": "Your specific mission for this agent...",
    "execution_mode": "claude_code" | "multi_terminal",
    "team_roster": [
        {"agent_type": "orchestrator", "agent_id": "uuid-0", "job_id": "uuid-orch", "name": "Orchestrator"},
        {"agent_type": "implementer", "agent_id": "uuid-1", "job_id": "uuid-a", "name": "Implementer"},
        {"agent_type": "tester", "agent_id": "uuid-2", "job_id": "uuid-b", "name": "Tester"}
    ],
    "communication_instructions": """
Your Team:
- Orchestrator: {agent_id}, {job_id}
- Implementer: {agent_id}, {job_id}
- Tester: {agent_id}, {job_id}

Communicate via:
- send_message(to_agent_id='{uuid}', message='...') - Direct message
- send_message(to_agent_id='broadcast', message='...') - All agents
- Check for messages: get_next_instruction(job_id='{your_job_id}', ...)
"""
}
```

---

## Implementation Plan

### 1. Frontend - Wire Toggle to Backend

**File**: `frontend/src/components/projects/JobsTab.vue`

**Changes**:
```javascript
// When [Launch Jobs] or orchestrator play button clicked
async function handleLaunchJobs() {
    const orchestratorJob = agents.value.find(a => a.agent_type === 'orchestrator')

    if (!orchestratorJob) {
        showToast({ message: 'Orchestrator not found', type: 'error' })
        return
    }

    // Set execution mode based on toggle
    const mode = usingClaudeCodeSubagents.value ? 'claude_code' : 'multi_terminal'

    try {
        await api.jobs.setExecutionMode(orchestratorJob.id, mode)
        showToast({
            message: `Execution mode set to ${mode}`,
            type: 'success'
        })
    } catch (error) {
        console.error('Failed to set execution mode:', error)
        showToast({ message: 'Failed to set execution mode', type: 'error' })
    }
}

// Update play button handler for orchestrator
async function handleOrchestratorPlay(job) {
    // Set execution mode first
    const mode = usingClaudeCodeSubagents.value ? 'claude_code' : 'multi_terminal'
    await api.jobs.setExecutionMode(job.id, mode)

    // Then copy prompt (existing logic)
    await copyPrompt(job)
}
```

**File**: `frontend/src/api/index.js`

**Add endpoint**:
```javascript
jobs: {
    setExecutionMode: async (jobId, mode) => {
        const response = await fetch(`${API_BASE_URL}/jobs/${jobId}/execution-mode`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getToken()}`
            },
            body: JSON.stringify({ mode })
        })
        if (!response.ok) throw new Error('Failed to set execution mode')
        return response.json()
    }
}
```

---

### 2. Backend - Execution Mode Endpoint

**File**: `api/endpoints/orchestration.py` (or new `api/endpoints/jobs.py`)

**New endpoint**:
```python
@router.put("/jobs/{job_id}/execution-mode")
async def set_execution_mode(
    job_id: str,
    request: ExecutionModeRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Set execution mode for orchestrator job (Claude Code CLI vs Multi-Terminal)."""

    # Validate mode
    if request.mode not in ['claude_code', 'multi_terminal']:
        raise HTTPException(status_code=400, detail="Invalid execution mode")

    # Get job
    job = await db.get(MCPAgentJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Verify tenant
    if job.tenant_key != current_user.tenant_key:
        raise HTTPException(status_code=403, detail="Access denied")

    # Verify orchestrator job
    if job.agent_type != 'orchestrator':
        raise HTTPException(status_code=400, detail="Can only set mode for orchestrator jobs")

    # Update metadata
    if not job.metadata:
        job.metadata = {}
    job.metadata['execution_mode'] = request.mode
    flag_modified(job, 'metadata')

    await db.commit()
    await db.refresh(job)

    logger.info(f"Set execution mode to {request.mode} for job {job_id}")

    return {
        "job_id": job_id,
        "execution_mode": request.mode,
        "message": f"Execution mode set to {request.mode}"
    }


class ExecutionModeRequest(BaseModel):
    mode: str  # 'claude_code' or 'multi_terminal'
```

---

### 3. MCP Tools - Team Roster Helper

**File**: `src/giljo_mcp/tools/orchestration.py`

**New helper function**:
```python
async def _build_team_roster(
    db: AsyncSession,
    project_id: str,
    tenant_key: str
) -> List[Dict[str, str]]:
    """
    Build team roster for agent communication.

    Returns list of all agents in project with their IDs:
    [
        {"agent_type": "orchestrator", "agent_id": "uuid", "job_id": "uuid", "name": "Orchestrator"},
        {"agent_type": "implementer", "agent_id": "uuid", "job_id": "uuid", "name": "Implementer"},
        ...
    ]
    """
    from sqlalchemy import select

    stmt = (
        select(MCPAgentJob)
        .where(
            MCPAgentJob.project_id == project_id,
            MCPAgentJob.tenant_key == tenant_key,
            MCPAgentJob.status.in_(['waiting', 'active', 'completed'])  # Exclude cancelled/failed
        )
        .order_by(
            # Orchestrator first, then alphabetically
            case(
                (MCPAgentJob.agent_type == 'orchestrator', 0),
                else_=1
            ),
            MCPAgentJob.agent_type
        )
    )

    result = await db.execute(stmt)
    jobs = result.scalars().all()

    roster = []
    for job in jobs:
        roster.append({
            "agent_type": job.agent_type,
            "agent_id": job.agent_id,
            "job_id": str(job.id),
            "name": job.agent_type.capitalize()
        })

    return roster
```

---

### 4. MCP Tools - Update get_orchestrator_instructions()

**File**: `src/giljo_mcp/tools/orchestration.py`

**Modify existing function** (~line 1507):
```python
@mcp_server.tool()
async def get_orchestrator_instructions(
    orchestrator_id: str = Field(..., description="Orchestrator job UUID"),
    tenant_key: str = Field(..., description="Tenant isolation key"),
) -> str:
    """
    Fetch orchestrator mission with context prioritization and orchestration (thin client architecture).

    ENHANCED (Handover 0260): Now returns mode-specific instructions and team roster.
    """
    async with get_db_session_context() as db:
        # ... existing code to fetch job, product, project ...

        # Get execution mode from job metadata
        execution_mode = job.metadata.get('execution_mode', 'multi_terminal') if job.metadata else 'multi_terminal'

        # Build team roster
        team_roster = await _build_team_roster(db, str(job.project_id), tenant_key)

        # ... existing code to build condensed mission ...

        # Build mode-specific instructions
        if execution_mode == 'claude_code':
            spawning_instructions = _build_claude_code_instructions(team_roster, tenant_key)
            mode_section = f"""

## Execution Mode: Claude Code CLI

{spawning_instructions}

"""
        else:
            coordination_instructions = _build_multi_terminal_instructions(team_roster)
            mode_section = f"""

## Execution Mode: Multi-Terminal

{coordination_instructions}

"""

        # Build team roster section
        roster_section = _build_roster_section(team_roster)

        # Combine all sections
        final_instructions = f"""
{condensed_mission}

{mode_section}

{roster_section}

## Next Steps
1. Review your mission above
2. {'Spawn subagents using Task tool' if execution_mode == 'claude_code' else 'Wait for user to launch agents'}
3. Coordinate with team via MCP tools
4. Monitor progress and respond to blockers
5. At completion, use close_project_and_update_memory()
"""

        return final_instructions


def _build_claude_code_instructions(team_roster: List[Dict], tenant_key: str) -> str:
    """Build spawning instructions for Claude Code CLI mode."""

    # Filter out orchestrator from roster
    agents = [a for a in team_roster if a['agent_type'] != 'orchestrator']

    if not agents:
        return "No specialist agents assigned. Check agent template manager."

    instructions = [
        "You are operating in Claude Code CLI mode.",
        "",
        "Spawn subagents using the Task tool with @ mentions:",
        ""
    ]

    for agent in agents:
        instructions.append(
            f"@{agent['agent_type']} - You are agent {agent['agent_id']}, job {agent['job_id']}.\n"
            f"Fetch your mission: get_agent_mission('{agent['job_id']}', '{tenant_key}')"
        )
        instructions.append("")

    instructions.extend([
        "All agents run in THIS terminal. You can see their output directly.",
        "Use MCP tools for status tracking and inter-agent coordination if needed."
    ])

    return "\n".join(instructions)


def _build_multi_terminal_instructions(team_roster: List[Dict]) -> str:
    """Build coordination instructions for multi-terminal mode."""

    instructions = [
        "You are coordinating agents in separate terminal windows.",
        "",
        "The user will manually launch each agent. You should:",
        "- Monitor agent progress via WebSocket updates in the dashboard",
        "- Send instructions via: send_message(to_agent_id='<agent_id>', message='<content>')",
        "- Broadcast to all agents: send_message(to_agent_id='broadcast', message='<content>')",
        "- Check for responses via: get_next_instruction(job_id='<your_job_id>', ...)",
        "",
        "Each agent will run in their own terminal window with their own prompt.",
        "The dashboard will show real-time status updates and message notifications."
    ]

    return "\n".join(instructions)


def _build_roster_section(team_roster: List[Dict]) -> str:
    """Build team roster section for communication reference."""

    lines = [
        "## Team Roster",
        "",
        "Your team for this project:",
        ""
    ]

    for agent in team_roster:
        lines.append(f"- **{agent['name']}** ({agent['agent_type']})")
        lines.append(f"  - Agent ID: `{agent['agent_id']}`")
        lines.append(f"  - Job ID: `{agent['job_id']}`")
        lines.append("")

    lines.extend([
        "### MCP Communication Commands",
        "",
        "```python",
        "# Send direct message",
        "send_message(to_agent_id='<agent_id_from_roster>', message='<content>', priority='medium')",
        "",
        "# Broadcast to all agents",
        "send_message(to_agent_id='broadcast', message='<content>', priority='high')",
        "",
        "# Check for incoming messages",
        "get_next_instruction(job_id='<your_job_id>', agent_type='orchestrator', tenant_key='<tenant_key>')",
        "```"
    ])

    return "\n".join(lines)
```

---

### 5. MCP Tools - Update get_agent_mission()

**File**: `src/giljo_mcp/tools/orchestration.py`

**Modify existing function** (~line 306):
```python
@mcp_server.tool()
async def get_agent_mission(
    job_id: str = Field(..., description="Agent job UUID"),
    tenant_key: str = Field(..., description="Tenant isolation key"),
) -> str:
    """
    Fetch agent-specific mission from spawned job.

    ENHANCED (Handover 0260): Now includes team roster and communication instructions.
    """
    async with get_db_session_context() as db:
        # ... existing code to fetch job and mission ...

        # Get execution mode (from orchestrator job or own metadata)
        execution_mode = job.metadata.get('execution_mode', 'multi_terminal') if job.metadata else 'multi_terminal'

        # Build team roster
        team_roster = await _build_team_roster(db, str(job.project_id), tenant_key)

        # Build communication instructions
        communication_section = _build_agent_communication_section(team_roster, execution_mode)

        # Combine mission with communication instructions
        enhanced_mission = f"""
{job.mission}

{communication_section}

## Next Steps
1. Read CLAUDE.md in project folder for coding standards
2. Check MCP health: health_check()
3. Acknowledge job: acknowledge_job(job_id='{job_id}', agent_id='{job.agent_id}')
4. Begin work on your mission above
5. Report progress regularly: report_progress(job_id='{job_id}', ...)
6. Check for orchestrator messages: get_next_instruction(job_id='{job_id}', ...)
7. Complete job: complete_job(job_id='{job_id}', result={{...}})
"""

        return enhanced_mission


def _build_agent_communication_section(team_roster: List[Dict], execution_mode: str) -> str:
    """Build communication instructions for specialist agents."""

    lines = [
        "## Your Team",
        "",
        "You are working with the following agents:",
        ""
    ]

    for agent in team_roster:
        lines.append(f"- **{agent['name']}** ({agent['agent_type']})")
        lines.append(f"  - Agent ID: `{agent['agent_id']}`")
        lines.append(f"  - Job ID: `{agent['job_id']}`")
        lines.append("")

    if execution_mode == 'claude_code':
        lines.extend([
            "### Execution Mode: Claude Code CLI",
            "",
            "You are running in Claude Code CLI mode alongside other agents in one terminal.",
            "The orchestrator can see your output directly.",
            "",
            "For urgent coordination, use MCP communication:",
            "```python",
            "send_message(to_agent_id='<agent_id>', message='<content>')",
            "```"
        ])
    else:
        lines.extend([
            "### Execution Mode: Multi-Terminal",
            "",
            "You are running in your own terminal window. Other agents are in separate terminals.",
            "You MUST communicate via MCP tools for all coordination:",
            "",
            "```python",
            "# Send message to specific agent",
            "send_message(to_agent_id='<agent_id_from_roster>', message='<content>')",
            "",
            "# Send message to orchestrator",
            "send_message(to_agent_id='<orchestrator_agent_id>', message='<content>')",
            "",
            "# Broadcast to all agents",
            "send_message(to_agent_id='broadcast', message='<content>')",
            "",
            "# Check for incoming messages",
            "get_next_instruction(job_id='<your_job_id>', agent_type='<your_type>', tenant_key='<tenant_key>')",
            "```"
        ])

    return "\n".join(lines)
```

---

## Testing Strategy

### Integration Tests

**File**: `tests/integration/test_execution_mode_flow.py`

```python
"""Integration tests for Claude Code CLI mode execution flow."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import MCPAgentJob, Project, Product, User
from src.giljo_mcp.tools.orchestration import (
    get_orchestrator_instructions,
    get_agent_mission,
    _build_team_roster,
)


@pytest.mark.asyncio
async def test_execution_mode_claude_code(db: AsyncSession, test_user: User):
    """Test orchestrator instructions in Claude Code CLI mode."""

    # Create test data
    product = Product(name="Test Product", tenant_key=test_user.tenant_key)
    db.add(product)
    await db.flush()

    project = Project(
        name="Test Project",
        product_id=product.id,
        tenant_key=test_user.tenant_key
    )
    db.add(project)
    await db.flush()

    # Create orchestrator job with Claude Code mode
    orchestrator = MCPAgentJob(
        agent_type="orchestrator",
        agent_id="orch-123",
        project_id=project.id,
        tenant_key=test_user.tenant_key,
        status="active",
        metadata={"execution_mode": "claude_code"}
    )
    db.add(orchestrator)

    # Create specialist agent jobs
    implementer = MCPAgentJob(
        agent_type="implementer",
        agent_id="impl-456",
        project_id=project.id,
        tenant_key=test_user.tenant_key,
        status="waiting",
        mission="Implement login feature"
    )
    db.add(implementer)

    await db.commit()

    # Get orchestrator instructions
    instructions = await get_orchestrator_instructions(
        orchestrator_id=str(orchestrator.id),
        tenant_key=test_user.tenant_key
    )

    # Verify Claude Code mode instructions
    assert "Claude Code CLI mode" in instructions
    assert "Task tool" in instructions
    assert "@implementer" in instructions
    assert f"agent {implementer.agent_id}" in instructions
    assert f"job {implementer.id}" in instructions
    assert "get_agent_mission" in instructions

    # Verify team roster included
    assert "Team Roster" in instructions
    assert implementer.agent_id in instructions


@pytest.mark.asyncio
async def test_execution_mode_multi_terminal(db: AsyncSession, test_user: User):
    """Test orchestrator instructions in multi-terminal mode."""

    # Create test data (similar to above)
    product = Product(name="Test Product", tenant_key=test_user.tenant_key)
    db.add(product)
    await db.flush()

    project = Project(
        name="Test Project",
        product_id=product.id,
        tenant_key=test_user.tenant_key
    )
    db.add(project)
    await db.flush()

    # Create orchestrator job with multi-terminal mode (default)
    orchestrator = MCPAgentJob(
        agent_type="orchestrator",
        agent_id="orch-123",
        project_id=project.id,
        tenant_key=test_user.tenant_key,
        status="active",
        metadata={"execution_mode": "multi_terminal"}
    )
    db.add(orchestrator)

    implementer = MCPAgentJob(
        agent_type="implementer",
        agent_id="impl-456",
        project_id=project.id,
        tenant_key=test_user.tenant_key,
        status="waiting",
        mission="Implement login feature"
    )
    db.add(implementer)

    await db.commit()

    # Get orchestrator instructions
    instructions = await get_orchestrator_instructions(
        orchestrator_id=str(orchestrator.id),
        tenant_key=test_user.tenant_key
    )

    # Verify multi-terminal mode instructions
    assert "Multi-Terminal" in instructions
    assert "separate terminal windows" in instructions
    assert "send_message" in instructions
    assert "manually launch each agent" in instructions

    # Should NOT have Claude Code spawning instructions
    assert "@implementer" not in instructions
    assert "Task tool" not in instructions

    # Verify team roster included
    assert "Team Roster" in instructions
    assert implementer.agent_id in instructions


@pytest.mark.asyncio
async def test_agent_mission_includes_team_roster(db: AsyncSession, test_user: User):
    """Test that agent missions include team roster for communication."""

    # Create test data
    product = Product(name="Test Product", tenant_key=test_user.tenant_key)
    db.add(product)
    await db.flush()

    project = Project(
        name="Test Project",
        product_id=product.id,
        tenant_key=test_user.tenant_key
    )
    db.add(project)
    await db.flush()

    orchestrator = MCPAgentJob(
        agent_type="orchestrator",
        agent_id="orch-123",
        project_id=project.id,
        tenant_key=test_user.tenant_key,
        status="active"
    )
    db.add(orchestrator)

    implementer = MCPAgentJob(
        agent_type="implementer",
        agent_id="impl-456",
        project_id=project.id,
        tenant_key=test_user.tenant_key,
        status="waiting",
        mission="Implement login feature",
        metadata={"execution_mode": "multi_terminal"}
    )
    db.add(implementer)

    await db.commit()

    # Get agent mission
    mission = await get_agent_mission(
        job_id=str(implementer.id),
        tenant_key=test_user.tenant_key
    )

    # Verify team roster included
    assert "Your Team" in mission
    assert orchestrator.agent_id in mission
    assert "Orchestrator" in mission

    # Verify communication instructions
    assert "send_message" in mission
    assert "get_next_instruction" in mission


@pytest.mark.asyncio
async def test_team_roster_builder(db: AsyncSession, test_user: User):
    """Test team roster generation helper."""

    # Create test data
    product = Product(name="Test Product", tenant_key=test_user.tenant_key)
    db.add(product)
    await db.flush()

    project = Project(
        name="Test Project",
        product_id=product.id,
        tenant_key=test_user.tenant_key
    )
    db.add(project)
    await db.flush()

    # Create multiple agent jobs
    jobs = [
        MCPAgentJob(
            agent_type="orchestrator",
            agent_id="orch-123",
            project_id=project.id,
            tenant_key=test_user.tenant_key,
            status="active"
        ),
        MCPAgentJob(
            agent_type="implementer",
            agent_id="impl-456",
            project_id=project.id,
            tenant_key=test_user.tenant_key,
            status="waiting"
        ),
        MCPAgentJob(
            agent_type="tester",
            agent_id="test-789",
            project_id=project.id,
            tenant_key=test_user.tenant_key,
            status="waiting"
        ),
    ]

    for job in jobs:
        db.add(job)

    await db.commit()

    # Build roster
    from src.giljo_mcp.tools.orchestration import _build_team_roster
    roster = await _build_team_roster(db, str(project.id), test_user.tenant_key)

    # Verify roster structure
    assert len(roster) == 3

    # Verify orchestrator is first
    assert roster[0]['agent_type'] == 'orchestrator'
    assert roster[0]['agent_id'] == 'orch-123'

    # Verify all required fields
    for agent in roster:
        assert 'agent_type' in agent
        assert 'agent_id' in agent
        assert 'job_id' in agent
        assert 'name' in agent
```

---

## Success Criteria

- [x] UI toggle state flows from JobsTab → Backend endpoint
- [ ] Execution mode stored in `MCPAgentJob.metadata['execution_mode']`
- [ ] `get_orchestrator_instructions()` returns mode-specific spawning/coordination instructions
- [ ] `get_orchestrator_instructions()` includes team roster with all agent IDs
- [ ] `get_agent_mission()` includes team roster for agent communication
- [ ] Integration tests verify both modes work end-to-end
- [ ] Team roster builder function tested and working
- [ ] CLAUDE.md updated with new workflow

---

## Files Modified

### Backend
- `api/endpoints/orchestration.py` - New endpoint `PUT /jobs/{job_id}/execution-mode`
- `src/giljo_mcp/tools/orchestration.py` - Enhanced MCP tools with mode-awareness and team roster

### Frontend
- `frontend/src/components/projects/JobsTab.vue` - Wire toggle to backend
- `frontend/src/api/index.js` - Add execution mode API call

### Tests
- `tests/integration/test_execution_mode_flow.py` - Integration tests for both modes

### Documentation
- `handovers/0260_claude_code_cli_mode_implementation.md` - This handover
- `CLAUDE.md` - Updated workflow documentation

---

## Timeline

**Total Estimated**: 4-6 hours

1. ✅ Create handover document (30 min) - DONE
2. ⏳ Frontend wiring (1 hour) - IN PROGRESS
3. ⏳ Backend endpoint (1 hour)
4. ⏳ Team roster helper (30 min)
5. ⏳ MCP tool updates (2 hours)
6. ⏳ Integration tests (1 hour)
7. ⏳ Documentation (30 min)

---

## Notes

### Design Decisions

1. **Execution mode stored in orchestrator job metadata**
   - Rationale: Mode is set once at launch, doesn't change during execution
   - Alternative: Store in project metadata (rejected - mode is job-specific)

2. **Team roster built dynamically from database**
   - Rationale: Always accurate, reflects current job state
   - Alternative: Cache in job metadata (rejected - can become stale)

3. **Mode defaults to multi-terminal**
   - Rationale: Safer default, works with all CLI tools
   - Alternative: Default to claude_code (rejected - assumes Claude Code CLI installed)

### Future Enhancements

1. **Agent template version checking** (referenced in Dynamic_context.md)
   - Compare agent templates on MCP server vs Claude Code CLI folders
   - Warn user if templates are out of sync

2. **Auditable functions for messages** (referenced in workflow diagram)
   - Make messages part of auditable trace
   - Currently user is just informed via WebSocket

3. **Project reactivation with agent restoration**
   - When project is deactivated and reactivated, restore agent jobs
   - Preserve execution mode across project lifecycle

---

**Status**: Implementation in progress (Phase 1 - Frontend wiring)
