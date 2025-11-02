# Handover 0080a: Orchestrator Succession Slash Command Implementation

**Date**: 2025-11-02
**Status**: Pending Implementation
**Priority**: Medium
**Parent Handover**: 0080 (Orchestrator Succession Architecture)
**Scope**: User-facing slash command for manual orchestrator succession

---

## Executive Summary

Implements `/gil_handover` slash command enabling users to manually trigger orchestrator succession from within Claude Code / Codex CLI. This completes the Handover 0080 succession workflow with a clean, user-friendly trigger mechanism.

**Key Decision**: **Orchestrator-only succession** (no succession for specialized agents like frontend-dev, tester, etc.)

---

## Problem Statement

**Current Gap in Handover 0080:**
- ✅ Database schema complete (instance_number, handover_to, etc.)
- ✅ Backend succession logic complete (OrchestratorSuccessionManager)
- ✅ MCP tools complete (create_successor_orchestrator)
- ✅ UI components complete (SuccessionTimeline, LaunchSuccessorDialog)
- ❌ **No user-facing slash command for manual trigger**

**Why We Can't Auto-Detect 90% Context:**
- Claude Code / Codex CLI do not expose context usage APIs
- No callback/hook exists when approaching context limits
- Token counting would be estimation only (unreliable)

**Solution**: Manual succession via slash command (user controls when to hand over)

---

## Solution Design

### 1. Slash Command Interface

**Command**: `/gil_handover`

**Aliases** (future): `/gil_succession`, `/gil_handoff`

**Usage**:
```bash
# Trigger succession for current project's orchestrator
/gil_handover

# Optional: Explicit orchestrator job ID
/gil_handover orch-6adbec5c-9e11-46b4-ad8b-060c69a8d124
```

**Expected Output**:
```
✅ Successor orchestrator created (Instance 2)

📋 Handover Summary:
   Project: ProductVision Dashboard (60% complete)
   Active Agents:
     • frontend-dev (working on component refactor)
     • backend-api (waiting for schema approval)
   Pending Decisions:
     • API endpoint naming convention
     • Authentication method selection
   Next Steps: Implement API endpoints, then frontend integration

🚀 Launch Instance 2:

   export GILJO_MCP_SERVER_URL=http://10.1.0.164:7272
   export GILJO_AGENT_JOB_ID=orch-a1b2c3d4-5e6f-7890-1234-567890abcdef
   export GILJO_PROJECT_ID=6adbec5c-9e11-46b4-ad8b-060c69a8d124

   codex mcp add giljo-orchestrator

📌 Copy the above command and run in a new terminal to launch your successor orchestrator.

---

Instance 1 has been marked complete. View succession history in the web dashboard → Jobs tab.
```

---

### 2. Scope Decision: Orchestrator-Only

**Design Decision**: Succession is **ONLY** available for orchestrator agents.

**Rationale**:
1. **Design Intent**: Handover 0080 specifically addresses orchestrator context limits
2. **Practical Reality**: Orchestrators accumulate context over days/weeks (50-100+ messages), while specialized agents complete tasks in hours (5-20 messages)
3. **Clear UX**: Users understand "orchestrator manages project, can hand over"
4. **Matches Problem Statement**: Orchestrator context exhaustion, not specialized agent exhaustion

**Agent Context Comparison**:
| Agent Type | Typical Messages | Duration | Succession Needed? |
|------------|-----------------|----------|-------------------|
| Orchestrator | 50-100+ | Days/Weeks | ✅ Yes |
| Frontend Dev | 10-20 | Hours | ❌ No |
| Backend API | 10-25 | Hours | ❌ No |
| Tester | 5-10 | Minutes/Hours | ❌ No |
| Code Reviewer | 5-15 | Hours | ❌ No |
| Documenter | 10-20 | Hours | ❌ No |

**Future Expansion**: Database schema already supports succession for any agent type. If we discover complex specialized agents hitting context limits in Phase 2, we can easily expand to specific agent types without database changes.

---

### 3. Implementation Components

#### A. Slash Command Handler

**File**: `src/giljo_mcp/slash_commands/handover.py` (NEW)

```python
"""
Slash command handler for /gil_handover
Triggers orchestrator succession
"""
from typing import Optional
from datetime import datetime, timezone
from giljo_mcp.orchestrator_succession import OrchestratorSuccessionManager
from giljo_mcp.database_manager import DatabaseManager

async def handle_gil_handover(
    db: DatabaseManager,
    tenant_key: str,
    project_id: Optional[str] = None,
    orchestrator_job_id: Optional[str] = None
) -> dict:
    """
    Handle /gil_handover slash command

    Args:
        db: Database manager instance
        tenant_key: Current tenant key
        project_id: Optional project ID (auto-detected if not provided)
        orchestrator_job_id: Optional explicit orchestrator job ID

    Returns:
        {
            "success": bool,
            "message": str,
            "successor_id": str,
            "launch_prompt": str,
            "handover_summary": dict
        }
    """
    async with db.get_session() as session:
        succession_mgr = OrchestratorSuccessionManager(session, tenant_key)

        # Get current orchestrator
        if not orchestrator_job_id:
            orchestrator = await succession_mgr.get_active_orchestrator(project_id)
            if not orchestrator:
                return {
                    "success": False,
                    "message": "❌ No active orchestrator found. Only orchestrators can trigger succession.",
                    "error": "NO_ORCHESTRATOR"
                }
        else:
            orchestrator = await session.get(MCPAgentJob, orchestrator_job_id)
            if not orchestrator or orchestrator.agent_type != 'orchestrator':
                return {
                    "success": False,
                    "message": "❌ Invalid orchestrator job ID or agent is not an orchestrator.",
                    "error": "INVALID_ORCHESTRATOR"
                }

        # Generate handover summary
        handover_summary = succession_mgr.generate_handover_summary(orchestrator)

        # Create successor
        successor = succession_mgr.create_successor(
            orchestrator=orchestrator,
            reason="manual"  # User-triggered via slash command
        )

        # Mark orchestrator as complete with handover
        succession_mgr.complete_handover(
            orchestrator=orchestrator,
            successor=successor,
            handover_summary=handover_summary
        )

        await session.commit()

        # Generate launch prompt
        launch_prompt = generate_launch_prompt(
            server_url=os.getenv("GILJO_MCP_SERVER_URL", "http://localhost:7272"),
            job_id=successor.job_id,
            project_id=orchestrator.project_id,
            handover_summary=handover_summary
        )

        return {
            "success": True,
            "message": f"✅ Successor orchestrator created (Instance {successor.instance_number})",
            "successor_id": successor.job_id,
            "launch_prompt": launch_prompt,
            "handover_summary": handover_summary
        }


def generate_launch_prompt(
    server_url: str,
    job_id: str,
    project_id: str,
    handover_summary: dict
) -> str:
    """Generate formatted launch prompt for successor"""
    return f"""
export GILJO_MCP_SERVER_URL={server_url}
export GILJO_AGENT_JOB_ID={job_id}
export GILJO_PROJECT_ID={project_id}

# Handover Summary:
# Project: {handover_summary.get('project_name', 'Unknown')} ({handover_summary.get('project_status', 'Unknown')}% complete)
# Active Agents: {len(handover_summary.get('active_agents', []))} agents
# Next Steps: {handover_summary.get('next_steps', 'Continue project work')}

codex mcp add giljo-orchestrator
""".strip()
```

#### B. Slash Command Registration

**File**: `src/giljo_mcp/slash_commands/__init__.py` (NEW)

```python
"""
Slash command registry for GiljoAI
Maps /gil_* commands to handler functions
"""
from typing import Callable, Dict
from .handover import handle_gil_handover

# Slash command registry
SLASH_COMMANDS: Dict[str, Callable] = {
    "gil_handover": handle_gil_handover,
    # Future commands:
    # "gil_activate": handle_gil_activate,
    # "gil_launch": handle_gil_launch,
    # "gil_status": handle_gil_status,
}

def get_slash_command(command_name: str) -> Callable | None:
    """Get handler for slash command"""
    return SLASH_COMMANDS.get(command_name)
```

#### C. API Endpoint

**File**: `api/endpoints/slash_commands.py` (NEW)

```python
"""
Slash command HTTP endpoints
Allows MCP adapter to route slash commands via HTTP
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any
from api.app import state
from src.giljo_mcp.slash_commands import get_slash_command

router = APIRouter(prefix="/slash", tags=["slash-commands"])

class SlashCommandRequest(BaseModel):
    command: str  # e.g., "gil_handover"
    tenant_key: str
    project_id: Optional[str] = None
    arguments: Dict[str, Any] = {}

@router.post("/execute")
async def execute_slash_command(request: SlashCommandRequest):
    """Execute a slash command via HTTP"""
    handler = get_slash_command(request.command)

    if not handler:
        raise HTTPException(
            status_code=404,
            detail=f"Slash command /{request.command} not found"
        )

    result = await handler(
        db=state.db_manager,
        tenant_key=request.tenant_key,
        project_id=request.project_id,
        **request.arguments
    )

    return result
```

#### D. MCP Adapter Integration

**File**: `src/giljo_mcp/mcp_adapter.py` (UPDATE)

Add slash command routing:

```python
async def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handle MCP tool call (including slash commands)"""

    # Check if this is a slash command
    if tool_name.startswith("gil_"):
        return await self.call_api(
            "/slash/execute",
            json={
                "command": tool_name,
                "tenant_key": self.tenant_key,
                "project_id": self.project_id,
                "arguments": arguments
            }
        )

    # ... existing tool routing ...
```

---

### 4. UI Integration

#### A. "Hand Over" Button (Orchestrator Cards Only)

**File**: `frontend/src/components/projects/AgentCardEnhanced.vue` (UPDATE)

```vue
<template>
  <v-card>
    <!-- Agent card header, status, etc. -->

    <!-- Succession Controls (Orchestrator Only) -->
    <div v-if="isOrchestrator" class="succession-controls">
      <!-- Working orchestrator: Show "Hand Over" button -->
      <v-btn
        v-if="agent.status === 'working'"
        color="warning"
        size="small"
        @click="triggerSuccession"
      >
        <v-icon>mdi-hand-wave</v-icon>
        Hand Over
      </v-btn>

      <!-- Waiting successor: Show "Launch Successor" button -->
      <v-btn
        v-if="agent.status === 'waiting' && agent.spawned_by"
        color="primary"
        size="small"
        @click="openLaunchDialog"
      >
        <v-icon>mdi-rocket-launch</v-icon>
        Launch Successor
      </v-btn>

      <!-- Complete with handover: Show link to successor -->
      <div v-if="agent.status === 'complete' && agent.handover_to" class="handover-link">
        <v-chip size="small" color="warning">
          <v-icon start>mdi-arrow-right</v-icon>
          Handed to Instance {{ agent.instance_number + 1 }}
        </v-chip>
      </div>
    </div>
  </v-card>
</template>

<script setup>
const isOrchestrator = computed(() => props.agent.agent_type === 'orchestrator')

async function triggerSuccession() {
  try {
    const result = await api.post(`/agent_jobs/${props.agent.job_id}/trigger_succession`)

    // Show launch dialog with generated prompt
    launchDialogData.value = {
      successorId: result.data.successor_id,
      launchPrompt: result.data.launch_prompt,
      handoverSummary: result.data.handover_summary
    }
    showLaunchDialog.value = true

  } catch (error) {
    // Show error notification
  }
}
</script>
```

#### B. Specialized Agents: No Succession Button

**Frontend Dev / Backend API / Tester / etc.**:
- No "Hand Over" button
- No succession controls
- Simple "Complete" status when done

---

### 5. Error Handling

**Error Cases**:

| Error | Message | HTTP Status |
|-------|---------|-------------|
| No active orchestrator | ❌ No active orchestrator found. Only orchestrators can trigger succession. | 404 |
| Invalid orchestrator ID | ❌ Invalid orchestrator job ID or agent is not an orchestrator. | 400 |
| Orchestrator already complete | ❌ This orchestrator has already been handed over to Instance {N}. | 409 |
| Successor already exists | ❌ Successor already created. Launch Instance {N} instead. | 409 |
| Database error | ❌ Failed to create successor. Please try again. | 500 |
| Multi-tenant violation | ❌ Orchestrator not found or access denied. | 403 |

---

## Benefits

### User Experience
✅ **Simple trigger**: Type `/gil_handover` (10 characters)
✅ **Clear output**: Formatted handover summary + launch prompt
✅ **Copy-paste ready**: Launch prompt ready to execute
✅ **Manual control**: User decides when to hand over (no surprises)

### Technical
✅ **Orchestrator-only**: Clean scope, no confusion
✅ **Integrates with existing patterns**: Follows 0037/0038 slash command design
✅ **Leverages existing backend**: Uses OrchestratorSuccessionManager
✅ **Multi-tenant safe**: Enforces tenant isolation

### Operational
✅ **No automatic guessing**: No unreliable token estimation
✅ **User education**: Teaches when to hand over (40-50 messages, long projects)
✅ **Future-proof**: Database schema supports expansion to other agents

---

## Testing Strategy

### Unit Tests

**File**: `tests/test_slash_commands.py` (NEW)

```python
async def test_gil_handover_creates_successor():
    """Test /gil_handover creates successor orchestrator"""

async def test_gil_handover_orchestrator_only():
    """Test /gil_handover rejects non-orchestrator agents"""

async def test_gil_handover_generates_launch_prompt():
    """Test launch prompt generation"""

async def test_gil_handover_multi_tenant_isolation():
    """Test tenant isolation enforced"""
```

### Integration Tests

```python
async def test_slash_command_via_api():
    """Test /slash/execute endpoint"""

async def test_slash_command_via_mcp_adapter():
    """Test MCP adapter routing"""
```

### UI Tests

```python
def test_hand_over_button_orchestrator_only():
    """Test button only shows on orchestrator cards"""

def test_launch_dialog_displays_prompt():
    """Test launch dialog shows generated prompt"""
```

---

## Documentation Updates

### 1. User Guide

**File**: `docs/user_guides/orchestrator_succession_guide.md` (UPDATE)

Add section:

```markdown
## Triggering Succession via Slash Command

When working with an orchestrator in Claude Code or Codex CLI, you can manually trigger succession:

1. **Type the command**: `/gil_handover`
2. **Review the handover summary**: Shows project status, active agents, next steps
3. **Copy the launch prompt**: Generated command to start Instance 2
4. **Open new terminal**: Paste and run the command
5. **Instance 2 starts**: Fresh context window, picks up where Instance 1 left off

**When to trigger:**
- After 40-50 messages
- When conversation feels "long"
- Before major phase transitions
- When approaching context fatigue
```

### 2. Quick Reference

**File**: `docs/quick_reference/succession_quick_ref.md` (UPDATE)

```markdown
## Slash Command

**Trigger succession:**
```bash
/gil_handover
```

**Output:** Launch prompt for Instance 2
```

---

## Implementation Checklist

### Backend
- [ ] Create `src/giljo_mcp/slash_commands/handover.py`
- [ ] Create `src/giljo_mcp/slash_commands/__init__.py`
- [ ] Create `api/endpoints/slash_commands.py`
- [ ] Update `src/giljo_mcp/mcp_adapter.py` (slash command routing)
- [ ] Register `/slash` router in `api/app.py`

### Frontend
- [ ] Update `AgentCardEnhanced.vue` (orchestrator-only "Hand Over" button)
- [ ] Ensure `LaunchSuccessorDialog.vue` displays launch prompt
- [ ] Add succession controls styling
- [ ] Hide succession buttons on non-orchestrator agents

### Testing
- [ ] Unit tests: `tests/test_slash_commands.py`
- [ ] API tests: `tests/api/test_slash_commands_api.py`
- [ ] UI tests: Verify button visibility logic

### Documentation
- [ ] Update user guide
- [ ] Update quick reference
- [ ] Update CLAUDE.md (add `/gil_handover` reference)

---

## Related Handovers

- **Handover 0080**: Orchestrator Succession Architecture (parent)
- **Handover 0037/0038**: MCP Slash Commands Implementation (pattern reference)
- **Handover 0083**: Harmonize User-Facing Slash Commands (future - `/gil_*` standardization)

---

## Sign-Off

**Status**: Ready for implementation
**Complexity**: Low (leverages existing 0080 backend)
**Estimated Effort**: 1-2 days
**Priority**: Medium
**Dependencies**: Handover 0080 complete ✅

**Approved By**: User (2025-11-02)
**Implementation Date**: TBD
