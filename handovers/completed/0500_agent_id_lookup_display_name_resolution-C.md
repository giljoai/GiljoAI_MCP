# Handover 0500: Agent ID Lookup by Display Name

**Status**: Ready for Implementation
**Priority**: P2 (Medium)
**Effort**: E1 (Simple - Phase 1), E2 with Phase 2
**Source**: MCP_ENHANCEMENT_LIST.md Item #28
**Created**: 2026-01-25
**Repository**: F:\GiljoAI_MCP

---

## Messaging System Overview

The messaging system supports three main use cases:

| Use Case | Method | Supported Formats |
|----------|--------|-------------------|
| **A) Agent-to-agent direct** | MCP `send_message()` | UUIDs, display names, resolution automatic |
| **B) Agent broadcast (exclude self)** | MCP `send_message(to_agents=['all'])` | Sender excluded (lines 179-184, 324-328) |
| **C) User → Agent via WebUI** | REST `POST /api/messages/send` | UUIDs, display names, `['all']` for broadcast |

**Key Files**:
- `src/giljo_mcp/services/message_service.py` - Core resolution logic
- `api/endpoints/messages.py` - REST endpoints for WebUI (Handover 0299)
- `api/endpoints/mcp_http.py` - MCP tool schema

---

## Problem Statement

When sending direct messages to agents, orchestrators believed they needed `agent_id` UUIDs but only had `agent_display_name` from spawn responses. This forced manual tracking of IDs:

```
| Display Name | agent_id |
|--------------|----------|
| analyzer-agent | 773dcdd2-554a-47bc-a88d-297971986296 |
| documenter-agent | 280ddf1b-8be3-4ed6-8295-fc2da1b6059f |
```

**Evidence** (Orchestrator D, 2026-01-19): After spawning 6 agents, had to build manual registry table to track agent_ids for direct messaging.

---

## Key Discovery: Resolution Already Exists

**Research finding**: `send_message()` already supports display name resolution server-side (Handover 0372).

**File**: `src/giljo_mcp/services/message_service.py` lines 162-214

```python
# Resolve agent_display_name strings to agent_id UUIDs
for agent_ref in to_agents:
    if agent_ref == 'all':
        # FAN-OUT: Query active agents in project
    elif len(agent_ref) == 36 and '-' in agent_ref:
        # Already a UUID - use directly
        resolved_to_agents.append(agent_ref)
    else:
        # Agent display name string - resolve to active execution
        exec_result = await session.execute(
            select(AgentExecution).join(AgentJob).where(
                and_(
                    AgentJob.project_id == project_id,
                    AgentExecution.agent_display_name == agent_ref,
                    AgentExecution.status.in_(["waiting", "working", "blocked"]),
                    AgentExecution.tenant_key == tenant_key
                )
            ).order_by(AgentExecution.instance_number.desc()).limit(1)
        )
        execution = exec_result.scalar_one_or_none()
        if execution:
            resolved_to_agents.append(execution.agent_id)
```

**Current Problem**: The MCP schema documentation is misleading:
```python
"to_agents": {
    "description": "List of target agent_id UUIDs. Use ['all'] for broadcast."
}
```

This makes orchestrators think only UUIDs are accepted, when display names already work.

---

## Implementation Plan

### Phase 1: Documentation Fix (Required - 30 min)

Update the MCP schema to accurately reflect existing capability.

**File**: `api/endpoints/mcp_http.py` lines 264-290

**Current** (misleading):
```python
"to_agents": {
    "type": "array",
    "items": {"type": "string"},
    "description": "List of target agent_id UUIDs. Use ['all'] for broadcast to all agents.",
}
```

**Updated** (accurate):
```python
"to_agents": {
    "type": "array",
    "items": {"type": "string"},
    "description": (
        "List of recipients. Accepts: "
        "(1) agent_id UUIDs for direct targeting, "
        "(2) agent_display_name strings (e.g., 'Implementer') for automatic resolution, "
        "(3) ['all'] for broadcast to all active agents in the project."
    ),
}
```

### Phase 2: Dedicated Lookup Tool (Optional - 2 hours)

If explicit agent ID lookup is needed (without sending a message), add a dedicated tool.

#### 2a. Add Tool Schema

**File**: `api/endpoints/mcp_http.py` - in `handle_tools_list` function (~line 260)

```python
{
    "name": "get_agent_by_display_name",
    "description": "Lookup agent_id UUID by display name within a project. Returns the active agent matching the display name.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "agent_display_name": {
                "type": "string",
                "description": "Display name of the agent (e.g., 'Implementer', 'Tester')"
            },
            "project_id": {
                "type": "string",
                "description": "Project ID to scope the lookup"
            },
            "tenant_key": {
                "type": "string",
                "description": "Tenant key for isolation"
            },
        },
        "required": ["agent_display_name", "project_id"],
    },
}
```

#### 2b. Add Tool to tool_map

**File**: `api/endpoints/mcp_http.py` - in `handle_tools_call` function (~line 700)

```python
tool_map = {
    # ... existing tools ...
    "get_agent_by_display_name": state.tool_accessor.get_agent_by_display_name,
}
```

#### 2c. Add ToolAccessor Method

**File**: `src/giljo_mcp/tools/tool_accessor.py`

```python
async def get_agent_by_display_name(
    self,
    agent_display_name: str,
    project_id: str,
    tenant_key: str | None = None
) -> dict[str, Any]:
    """
    Lookup agent_id UUID by display name within a project.

    Returns the most recent active agent matching the display name.
    Useful for orchestrators who need agent IDs for purposes other
    than sending messages (since send_message already auto-resolves).
    """
    effective_tenant = tenant_key or self.tenant_key
    if not effective_tenant:
        return {"success": False, "error": "tenant_key required"}

    async with self._get_session() as session:
        from sqlalchemy import select, and_
        from sqlalchemy.orm import joinedload
        from ..models import AgentExecution, AgentJob

        result = await session.execute(
            select(AgentExecution)
            .join(AgentJob)
            .options(joinedload(AgentExecution.job))
            .where(
                and_(
                    AgentJob.project_id == project_id,
                    AgentExecution.agent_display_name == agent_display_name,
                    AgentExecution.status.in_(["waiting", "working", "blocked"]),
                    AgentExecution.tenant_key == effective_tenant,
                )
            )
            .order_by(AgentExecution.instance_number.desc())
            .limit(1)
        )
        execution = result.scalar_one_or_none()

        if execution:
            return {
                "success": True,
                "agent_id": execution.agent_id,
                "agent_display_name": execution.agent_display_name,
                "agent_name": execution.agent_name,
                "job_id": execution.job_id,
                "status": execution.status,
                "instance_number": execution.instance_number,
            }

        return {
            "success": False,
            "error": f"No active agent found with display_name '{agent_display_name}' in project",
            "hint": "Check that agent is spawned and has status: waiting, working, or blocked"
        }
```

#### 2d. Add Tests

**File**: `tests/api/test_mcp_agent_lookup.py` (new file)

```python
"""Tests for get_agent_by_display_name MCP tool."""
import pytest
from uuid import uuid4

from src.giljo_mcp.models import AgentJob, AgentExecution
from tests.conftest import async_session_fixture


class TestGetAgentByDisplayName:
    """Test suite for agent lookup by display name."""

    @pytest.mark.asyncio
    async def test_lookup_existing_agent(self, async_session, tool_accessor):
        """Should return agent_id for existing active agent."""
        # Setup
        project_id = str(uuid4())
        job_id = str(uuid4())
        agent_id = str(uuid4())
        tenant_key = "test-tenant"

        job = AgentJob(
            job_id=job_id,
            tenant_key=tenant_key,
            project_id=project_id,
            mission="Test mission",
            job_type="Implementer",
            status="active",
        )
        execution = AgentExecution(
            agent_id=agent_id,
            job_id=job_id,
            tenant_key=tenant_key,
            agent_display_name="Implementer",
            agent_name="impl-1",
            status="working",
            instance_number=1,
        )
        async_session.add(job)
        async_session.add(execution)
        await async_session.commit()

        # Execute
        result = await tool_accessor.get_agent_by_display_name(
            agent_display_name="Implementer",
            project_id=project_id,
            tenant_key=tenant_key,
        )

        # Verify
        assert result["success"] is True
        assert result["agent_id"] == agent_id
        assert result["agent_display_name"] == "Implementer"
        assert result["status"] == "working"

    @pytest.mark.asyncio
    async def test_lookup_nonexistent_agent(self, async_session, tool_accessor):
        """Should return error for non-existent agent."""
        result = await tool_accessor.get_agent_by_display_name(
            agent_display_name="NonExistent",
            project_id=str(uuid4()),
            tenant_key="test-tenant",
        )

        assert result["success"] is False
        assert "No active agent found" in result["error"]

    @pytest.mark.asyncio
    async def test_lookup_returns_latest_instance(self, async_session, tool_accessor):
        """Should return highest instance_number for successor agents."""
        project_id = str(uuid4())
        job_id = str(uuid4())
        tenant_key = "test-tenant"

        job = AgentJob(
            job_id=job_id,
            tenant_key=tenant_key,
            project_id=project_id,
            mission="Test",
            job_type="Orchestrator",
            status="active",
        )

        # Instance 1 (old)
        exec1 = AgentExecution(
            agent_id=str(uuid4()),
            job_id=job_id,
            tenant_key=tenant_key,
            agent_display_name="Orchestrator",
            agent_name="orch",
            status="complete",  # Old instance completed
            instance_number=1,
        )

        # Instance 2 (current - successor)
        agent_id_2 = str(uuid4())
        exec2 = AgentExecution(
            agent_id=agent_id_2,
            job_id=job_id,
            tenant_key=tenant_key,
            agent_display_name="Orchestrator",
            agent_name="orch",
            status="working",  # Current instance
            instance_number=2,
        )

        async_session.add_all([job, exec1, exec2])
        await async_session.commit()

        result = await tool_accessor.get_agent_by_display_name(
            agent_display_name="Orchestrator",
            project_id=project_id,
            tenant_key=tenant_key,
        )

        assert result["success"] is True
        assert result["agent_id"] == agent_id_2
        assert result["instance_number"] == 2

    @pytest.mark.asyncio
    async def test_tenant_isolation(self, async_session, tool_accessor):
        """Should not find agents from other tenants."""
        project_id = str(uuid4())
        job_id = str(uuid4())

        job = AgentJob(
            job_id=job_id,
            tenant_key="tenant-A",
            project_id=project_id,
            mission="Test",
            job_type="Tester",
            status="active",
        )
        execution = AgentExecution(
            agent_id=str(uuid4()),
            job_id=job_id,
            tenant_key="tenant-A",
            agent_display_name="Tester",
            agent_name="test-1",
            status="working",
            instance_number=1,
        )
        async_session.add(job)
        async_session.add(execution)
        await async_session.commit()

        # Query with different tenant
        result = await tool_accessor.get_agent_by_display_name(
            agent_display_name="Tester",
            project_id=project_id,
            tenant_key="tenant-B",  # Different tenant
        )

        assert result["success"] is False
```

---

## Files to Modify

| File | Change | Phase |
|------|--------|-------|
| `api/endpoints/mcp_http.py` | Update `to_agents` description in send_message schema | 1 |
| `api/endpoints/mcp_http.py` | Add tool schema + tool_map entry | 2 |
| `src/giljo_mcp/tools/tool_accessor.py` | Add `get_agent_by_display_name` method | 2 |
| `tests/api/test_mcp_agent_lookup.py` | New test file | 2 |

---

## Verification Steps

### Phase 1 Verification
1. Read updated MCP schema via `/mcp` endpoint
2. Confirm `to_agents` description now mentions display names
3. Test `send_message()` with display name string (should work as before)

### Phase 2 Verification
1. Call `get_agent_by_display_name("Implementer", project_id, tenant_key)`
2. Verify returns `agent_id`, `status`, `instance_number`
3. Verify tenant isolation (different tenant returns not found)
4. Verify returns latest instance (successor handling)

---

## Related Items

- **Handover 0372**: Original implementation of display name resolution in `send_message()`
- **Item #6**: Agent registry in team context header (resolved separately)
- **Item #35**: Teammate registry in `get_agent_mission()` (resolved - agents get team roster)

---

## Acceptance Criteria

### Phase 1 (Documentation)
- [ ] MCP schema for `send_message()` documents all 3 input formats
- [ ] No code changes to resolution logic (already works)

### Phase 2 (Lookup Tool)
- [ ] `get_agent_by_display_name` tool registered in MCP
- [ ] Returns agent_id, display_name, job_id, status, instance_number
- [ ] Handles non-existent agents gracefully
- [ ] Returns latest instance for successor chains
- [ ] Enforces tenant isolation
- [ ] 4+ unit tests passing

---

## Recommendation

**Start with Phase 1 only.** The discovery that `send_message()` already resolves display names means the "manual registry tracking" pain point is actually a documentation issue, not a code issue.

Phase 2 can be deferred unless explicit lookup (without sending a message) is needed.

---

## Appendix: All Three Use Cases Verified

### A) Agent-to-Agent Direct Messages ✅

**MCP Tool**: `send_message(to_agents=["Implementer"], content="...", ...)`

**Resolution Logic** (`message_service.py` lines 191-214):
```python
else:
    # Agent display name string - resolve to active execution
    exec_result = await session.execute(
        select(AgentExecution).join(AgentJob).where(
            and_(
                AgentJob.project_id == project_id,
                AgentExecution.agent_display_name == agent_ref,  # <-- Display name lookup
                AgentExecution.status.in_(["waiting", "working", "blocked"]),
                AgentExecution.tenant_key == tenant_key
            )
        ).order_by(AgentExecution.instance_number.desc()).limit(1)
    )
```

### B) Agent Broadcast (Excluding Self) ✅

**MCP Tool**: `send_message(to_agents=["all"], from_agent="Orchestrator", ...)`

**Self-Exclusion Logic** (`message_service.py` lines 179-184, 324-328):
```python
# Expand to individual recipients (excluding sender)
sender_ref = from_agent or "orchestrator"
for execution in executions:
    # Skip sender - compare both agent_display_name and agent_id
    if (execution.agent_display_name == sender_ref or
        execution.agent_id == sender_ref):
        continue  # Excluded
```

### C) User Messaging via WebUI ✅

**Direct Message Endpoint** (`api/endpoints/messages.py` lines 108-148):
```python
@router.post("/send", response_model=dict)
async def send_message_from_ui(payload: MessageSendRequest, ...):
    result = await message_service.send_message(
        to_agents=payload.to_agents,  # Supports UUIDs, display names, or ['all']
        content=payload.content,
        from_agent="user",  # UI messages always from "user"
        tenant_key=current_user.tenant_key,
    )
```

**Broadcast Endpoint** (`api/endpoints/messages.py` lines 309-367):
```python
@router.post("/broadcast", response_model=dict)
async def broadcast_message(broadcast: BroadcastMessage, ...):
    message_result = await message_service.broadcast(
        content=broadcast.content,
        project_id=broadcast.project_id,
        from_agent=broadcast.from_agent or "user",
    )
```

---

## Summary

All three messaging use cases are **already fully functional**. The only issue is misleading MCP schema documentation that makes agents believe only UUIDs are accepted.

| What | Status |
|------|--------|
| Agent-to-agent (UUID) | ✅ Works |
| Agent-to-agent (display name) | ✅ Works (undocumented) |
| Broadcast (exclude self) | ✅ Works |
| User → Agent (WebUI direct) | ✅ Works |
| User → All (WebUI broadcast) | ✅ Works |
| MCP schema documentation | ❌ Misleading - says "UUIDs only" |

**Fix**: Update MCP schema description to document all supported formats.
