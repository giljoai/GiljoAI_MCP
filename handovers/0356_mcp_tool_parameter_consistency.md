# Handover 0356: MCP Tool Parameter Consistency

**Date**: 2025-12-19
**Status**: Ready for Implementation
**Priority**: High (Blocking Alpha Trial)
**Estimated Effort**: 3-4 hours

---

## Context

Alpha trial testing revealed critical inconsistencies in MCP tool parameter handling that prevent agents from successfully communicating and coordinating. These issues surfaced when real agents attempted to use the messaging and coordination tools.

**Root Cause**: Inconsistent parameter signatures between MCP tool schemas (advertised in `tools/list`), ToolAccessor methods, and underlying service layer implementations.

**Impact**: Agents cannot send messages or coordinate work, blocking the entire orchestration workflow.

---

## Problem Statement

### Issue #3: `send_message` tenant_key Parameter Mismatch

**Error Observed**:
```
ToolAccessor.send_message() got an unexpected keyword argument 'tenant_key'
```

**Current State**:
- **MCP Schema** (`api/endpoints/mcp_http.py` lines 208-240): Does NOT include `tenant_key` in `inputSchema.required`
- **ToolAccessor** (`src/giljo_mcp/tools/tool_accessor.py` lines 226-243): Does NOT accept `tenant_key` parameter
- **MessageService** (`src/giljo_mcp/services/message_service.py` lines 98-107): DOES accept optional `tenant_key` parameter

**Agent Behavior**: Agents call `send_message(tenant_key=...)` based on orchestrator instructions that reference tenant isolation patterns from other tools.

**Inconsistency**: The MCP schema doesn't advertise `tenant_key`, ToolAccessor doesn't accept it, but MessageService does support it.

### Issue #9: Agent ID Inconsistency (job_id vs agent_type)

**Confusion Observed**: Tools inconsistently use `job_id`, `agent_id`, `agent_type`, and `agent_name` to identify agents.

**Current State**:

| Tool | Parameter Name | What It Means | Example Value |
|------|----------------|---------------|---------------|
| `spawn_agent_job` | `agent_type` | Category/role | "implementer" |
| `spawn_agent_job` | `agent_name` | Template name | "tdd-implementor" |
| `get_agent_mission` | `agent_job_id` | Job UUID | "abf6c4fd-..." |
| `send_message` | `to_agents` | List of targets | ["orchestrator"] |
| `receive_messages` | `agent_id` | Job UUID | "abf6c4fd-..." |
| `acknowledge_job` | `job_id` | Job UUID | "abf6c4fd-..." |
| `acknowledge_job` | `agent_id` | Agent identifier | (unclear) |

**Root Problem**: No clear universal identifier standard. Sometimes it's UUID (`job_id`), sometimes it's a type string (`agent_type`), sometimes it's a name string (`agent_name`).

---

## Investigation Findings

### 1. Current `send_message` Flow

**MCP HTTP Handler** (`api/endpoints/mcp_http.py:586`):
```python
"send_message": state.tool_accessor.send_message,
```

**ToolAccessor Signature** (`src/giljo_mcp/tools/tool_accessor.py:226-234`):
```python
async def send_message(
    self,
    to_agents: list[str],
    content: str,
    project_id: str,
    message_type: str = "direct",
    priority: str = "normal",
    from_agent: Optional[str] = None,
) -> dict[str, Any]:
```
- **NO `tenant_key` parameter**

**ToolAccessor Implementation** (`src/giljo_mcp/tools/tool_accessor.py:236-243`):
```python
return await self._message_service.send_message(
    to_agents=to_agents,
    content=content,
    project_id=project_id,
    message_type=message_type,
    priority=priority,
    from_agent=from_agent
)
```
- **Does NOT pass `tenant_key` to MessageService**

**MessageService Signature** (`src/giljo_mcp/services/message_service.py:98-107`):
```python
async def send_message(
    self,
    to_agents: list[str],
    content: str,
    project_id: str,
    message_type: str = "direct",
    priority: str = "normal",
    from_agent: Optional[str] = None,
    tenant_key: Optional[str] = None,  # ACCEPTS tenant_key
) -> dict[str, Any]:
```

**MessageService Implementation** (`src/giljo_mcp/services/message_service.py:136-147`):
```python
if tenant_key:
    result = await session.execute(
        select(Project).where(
            Project.tenant_key == tenant_key,
            Project.id == project_id
        )
    )
else:
    # Fallback for backward compatibility - will be deprecated
    result = await session.execute(
        select(Project).where(Project.id == project_id)
    )
```

**Analysis**:
- MessageService SUPPORTS tenant isolation via `tenant_key`
- ToolAccessor DOES NOT expose this capability to MCP clients
- This creates a security gap where tenant isolation is bypassed

### 2. Other Tools That Accept `tenant_key`

**Tools with `tenant_key` in their signatures**:
- `get_orchestrator_instructions(orchestrator_id, tenant_key)` - REQUIRED
- `spawn_agent_job(agent_type, agent_name, mission, project_id, tenant_key, ...)` - REQUIRED
- `get_agent_mission(agent_job_id, tenant_key)` - REQUIRED
- `orchestrate_project(project_id, tenant_key)` - REQUIRED
- `get_pending_jobs(agent_type, tenant_key)` - REQUIRED
- `acknowledge_job(job_id, agent_id, tenant_key)` - REQUIRED (via agent_coordination.py)
- `report_progress(job_id, ..., tenant_key)` - REQUIRED (via agent_coordination.py)
- `complete_job(job_id, result, tenant_key)` - REQUIRED (via agent_coordination.py)

**Pattern**: ALL coordination tools require explicit `tenant_key` for multi-tenant isolation.

**Exception**: `send_message` does NOT require `tenant_key`, creating an inconsistency.

### 3. Tenant Context Resolution

**Current Behavior** (`api/endpoints/mcp_http.py:573-574`):
```python
# Set tenant context
state.tenant_manager.set_current_tenant(session.tenant_key)
```

**How It Works**:
1. MCP HTTP handler extracts `tenant_key` from session (via API key lookup)
2. Sets global tenant context in `TenantManager`
3. Tools can call `self.tenant_manager.get_current_tenant()` to retrieve it

**Why This Is Problematic**:
- Relies on global state (`TenantManager.set_current_tenant()`)
- Race conditions possible in async environments
- Explicit parameters are more testable and traceable
- Not all tools use this pattern consistently

### 4. Agent Identification Standards

**Database Schema** (`src/giljo_mcp/models/agents.py`):
```python
class MCPAgentJob(Base):
    job_id = Column(String, primary_key=True)           # UUID (unique per agent instance)
    agent_type = Column(String)                         # Role category (e.g., "implementer")
    agent_name = Column(String)                         # Template name (e.g., "tdd-implementor")
    tenant_key = Column(String)                         # Multi-tenant isolation
    project_id = Column(String, ForeignKey("projects.id"))
```

**Relationships**:
- `job_id`: Unique identifier for THIS agent instance (UUID)
- `agent_type`: Shared category for all agents of same role
- `agent_name`: Specific template/configuration used to spawn agent
- `project_id`: Which project this agent belongs to
- `tenant_key`: Which tenant owns this agent

**Current Inconsistencies**:

1. **spawn_agent_job** uses `agent_type` + `agent_name` (both strings)
2. **get_agent_mission** uses `agent_job_id` (UUID)
3. **send_message** uses `to_agents` (list of strings - could be UUIDs OR agent_types)
4. **receive_messages** uses `agent_id` (UUID via job_id)
5. **acknowledge_job** uses both `job_id` (UUID) AND `agent_id` (unclear what this is)

**MessageService Resolution Logic** (`src/giljo_mcp/services/message_service.py:158-186`):
```python
resolved_to_agents = []
for agent_ref in to_agents:
    if agent_ref == 'all':
        # Broadcast - keep as-is
        resolved_to_agents.append('all')
    elif len(agent_ref) == 36 and '-' in agent_ref:
        # Already a UUID (job_id) - use directly
        resolved_to_agents.append(agent_ref)
    else:
        # Agent type string (e.g., "orchestrator") - resolve to job_id
        agent_result = await session.execute(
            select(MCPAgentJob).where(
                MCPAgentJob.project_id == project_id,
                MCPAgentJob.agent_type == agent_ref
            ).limit(1)
        )
        agent_job = agent_result.scalar_one_or_none()
        if agent_job:
            resolved_to_agents.append(agent_job.job_id)
```

**Analysis**: MessageService ALREADY handles both UUIDs and agent_type strings transparently. The ambiguity is intentional for flexibility, but should be documented.

---

## Implementation Plan

### Phase 1: Fix `send_message` tenant_key Parameter (2 hours)

#### 1.1 Update ToolAccessor Signature
**File**: `src/giljo_mcp/tools/tool_accessor.py`
**Lines**: 226-243

**Change**:
```python
# BEFORE
async def send_message(
    self,
    to_agents: list[str],
    content: str,
    project_id: str,
    message_type: str = "direct",
    priority: str = "normal",
    from_agent: Optional[str] = None,
) -> dict[str, Any]:
    """Send message to one or more agents (delegates to MessageService)"""
    return await self._message_service.send_message(
        to_agents=to_agents,
        content=content,
        project_id=project_id,
        message_type=message_type,
        priority=priority,
        from_agent=from_agent
    )

# AFTER
async def send_message(
    self,
    to_agents: list[str],
    content: str,
    project_id: str,
    tenant_key: Optional[str] = None,  # ADD THIS
    message_type: str = "direct",
    priority: str = "normal",
    from_agent: Optional[str] = None,
) -> dict[str, Any]:
    """
    Send message to one or more agents (delegates to MessageService)

    Args:
        to_agents: List of target agent job_ids or agent_types (e.g., ["orchestrator"])
        content: Message content
        project_id: Project UUID
        tenant_key: Tenant isolation key (optional - uses TenantManager if not provided)
        message_type: Message type (direct, broadcast, system)
        priority: Message priority (low, normal, high)
        from_agent: Sender agent identifier

    Returns:
        Success/error dict with message_id
    """
    # Use provided tenant_key or fallback to TenantManager
    if not tenant_key:
        tenant_key = self.tenant_manager.get_current_tenant()

    return await self._message_service.send_message(
        to_agents=to_agents,
        content=content,
        project_id=project_id,
        message_type=message_type,
        priority=priority,
        from_agent=from_agent,
        tenant_key=tenant_key  # ADD THIS
    )
```

**Rationale**:
- Makes `tenant_key` OPTIONAL (backward compatible)
- Fallback to `TenantManager` for HTTP MCP calls (where tenant context is set globally)
- Allows explicit tenant_key for direct API calls and tests
- Matches pattern used by other coordination tools

#### 1.2 Update MCP Schema
**File**: `api/endpoints/mcp_http.py`
**Lines**: 208-240

**Change**:
```python
# BEFORE
{
    "name": "send_message",
    "description": "Send a message to one or more agents. Use to_agents=['all'] for broadcast.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "to_agents": { ... },
            "content": { ... },
            "project_id": { ... },
            "message_type": { ... },
            "priority": { ... },
            "from_agent": { ... },
        },
        "required": ["to_agents", "content", "project_id"],
    },
},

# AFTER
{
    "name": "send_message",
    "description": "Send a message to one or more agents. Use to_agents=['all'] for broadcast. Supports both job_id (UUID) and agent_type (string) in to_agents list.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "to_agents": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of target agent job_ids (UUIDs) or agent_types (e.g., ['orchestrator']). Use ['all'] for broadcast to all agents in project.",
            },
            "content": {"type": "string", "description": "Message content"},
            "project_id": {"type": "string", "description": "Project UUID for the message"},
            "tenant_key": {
                "type": "string",
                "description": "Tenant isolation key (optional - uses session tenant if not provided)",
            },
            "message_type": {
                "type": "string",
                "enum": ["direct", "broadcast", "system"],
                "description": "Message type (default: direct)",
                "default": "direct",
            },
            "priority": {
                "type": "string",
                "enum": ["low", "normal", "high"],
                "description": "Message priority (default: normal)",
                "default": "normal",
            },
            "from_agent": {
                "type": "string",
                "description": "Sender agent job_id or agent_type (default: orchestrator)",
            },
        },
        "required": ["to_agents", "content", "project_id"],  # tenant_key NOT required
    },
},
```

**Rationale**:
- Add `tenant_key` to schema properties (NOT required)
- Improve documentation for `to_agents` (clarify UUID vs agent_type)
- Clarify broadcast behavior (`['all']`)
- Match pattern used by other MCP tools

#### 1.3 Update Tests
**File**: `tests/services/test_message_service.py`

**Add Test Case**:
```python
@pytest.mark.asyncio
async def test_send_message_with_explicit_tenant_key(db_session, tenant_key, product, project):
    """Test send_message with explicit tenant_key parameter"""
    from giljo_mcp.services.message_service import MessageService

    # Create message service without tenant manager
    message_service = MessageService(
        db_manager=db_manager,
        tenant_manager=tenant_manager,
        test_session=db_session
    )

    # Send message with explicit tenant_key
    result = await message_service.send_message(
        to_agents=["orchestrator"],
        content="Test message",
        project_id=str(project.id),
        tenant_key=tenant_key  # EXPLICIT
    )

    assert result["success"] is True
    assert "message_id" in result
```

### Phase 2: Standardize Agent Identification Documentation (1-2 hours)

#### 2.1 Create Agent Identification Guide
**File**: `docs/api/agent_identification.md`

**Content**:
```markdown
# Agent Identification Guide

## Overview

GiljoAI uses three distinct identifiers for agents. Understanding when to use each is critical for correct tool usage.

## Identifier Types

### 1. job_id (UUID)
- **Type**: String (UUID format: "abf6c4fd-68b9-4556-a268-467fa90db480")
- **Uniqueness**: Unique per agent INSTANCE
- **Use Cases**:
  - Retrieving agent-specific mission (`get_agent_mission`)
  - Receiving messages (`receive_messages`)
  - Acknowledging jobs (`acknowledge_job`)
  - Progress reporting (`report_progress`)
  - Job completion (`complete_job`)
- **Database**: `MCPAgentJob.job_id` (primary key)

### 2. agent_type (Role Category)
- **Type**: String (lowercase, e.g., "orchestrator", "implementer", "tester")
- **Uniqueness**: Shared by all agents of same ROLE
- **Use Cases**:
  - Spawning new agents (`spawn_agent_job`)
  - Broadcasting to role type (`send_message(to_agents=["orchestrator"])`)
  - Getting pending jobs for role (`get_pending_jobs`)
- **Database**: `MCPAgentJob.agent_type`

### 3. agent_name (Template Name)
- **Type**: String (kebab-case, e.g., "tdd-implementor", "frontend-tester")
- **Uniqueness**: Unique per agent TEMPLATE
- **Use Cases**:
  - Spawning agents with specific templates (`spawn_agent_job`)
  - Selecting agent configuration
- **Database**: `MCPAgentJob.agent_name`

## Tool Parameter Reference

| Tool | Parameter | Type | Example |
|------|-----------|------|---------|
| `spawn_agent_job` | `agent_type` | agent_type | "implementor" |
| `spawn_agent_job` | `agent_name` | agent_name | "tdd-implementor" |
| `get_agent_mission` | `agent_job_id` | job_id | "abf6c4fd-..." |
| `send_message` | `to_agents` | job_id OR agent_type | ["abf6c4fd-..."] OR ["orchestrator"] |
| `receive_messages` | `agent_id` | job_id | "abf6c4fd-..." |
| `acknowledge_job` | `job_id` | job_id | "abf6c4fd-..." |
| `acknowledge_job` | `agent_id` | job_id | "abf6c4fd-..." |
| `report_progress` | `job_id` | job_id | "abf6c4fd-..." |
| `complete_job` | `job_id` | job_id | "abf6c4fd-..." |

## send_message Special Behavior

The `send_message` tool accepts BOTH `job_id` (UUID) and `agent_type` (string) in the `to_agents` list:

```python
# Send to specific agent instance (by job_id)
send_message(to_agents=["abf6c4fd-68b9-4556-a268-467fa90db480"], ...)

# Send to first agent of type (by agent_type)
send_message(to_agents=["orchestrator"], ...)

# Broadcast to all agents in project
send_message(to_agents=["all"], ...)

# Mix of types (resolved transparently)
send_message(to_agents=["orchestrator", "abf6c4fd-...", "all"], ...)
```

**Resolution Logic** (in `MessageService.send_message`):
1. If `agent_ref == 'all'`: Keep as-is (broadcast)
2. If `len(agent_ref) == 36 and '-' in agent_ref`: Treat as job_id (UUID)
3. Else: Treat as agent_type, resolve to job_id via database lookup

## Best Practices

1. **Use job_id when targeting SPECIFIC agent instance**
   - Example: Responding to a message from a specific agent

2. **Use agent_type when targeting ANY agent of a ROLE**
   - Example: Broadcasting instructions to all testers

3. **Use agent_name when SPAWNING agents**
   - Example: Creating a new TDD implementor

4. **Always include tenant_key for cross-tenant safety**
   - Even though most tools accept it as optional, explicit is better

## Common Mistakes

### ❌ Wrong: Using agent_type where job_id is required
```python
# WRONG - get_agent_mission expects job_id, not agent_type
get_agent_mission(agent_job_id="orchestrator", tenant_key=...)
```

### ✅ Correct: Use job_id from spawn_agent_job response
```python
# Spawn agent and get job_id
spawn_result = spawn_agent_job(
    agent_type="orchestrator",
    agent_name="orchestrator-coordinator",
    ...
)
job_id = spawn_result["job_id"]

# Use job_id to get mission
get_agent_mission(agent_job_id=job_id, tenant_key=...)
```

### ❌ Wrong: Mixing parameter names inconsistently
```python
# WRONG - parameter is 'agent_id' not 'job_id'
receive_messages(job_id="abf6c4fd-...", ...)
```

### ✅ Correct: Check tool schema for exact parameter names
```python
# CORRECT - parameter is 'agent_id'
receive_messages(agent_id="abf6c4fd-...", ...)
```
```

#### 2.2 Update MCP Tool Descriptions

**File**: `api/endpoints/mcp_http.py`

**Update All Tools** to reference agent identification guide in descriptions:

```python
{
    "name": "get_agent_mission",
    "description": "Get agent-specific mission. Parameter agent_job_id expects job_id (UUID), not agent_type. See docs/api/agent_identification.md for identifier types.",
    # ...
}
```

### Phase 3: Integration Testing (1 hour)

#### 3.1 Create Integration Test
**File**: `tests/integration/test_agent_messaging.py`

```python
"""Integration tests for agent messaging with tenant isolation"""
import pytest
from uuid import uuid4

@pytest.mark.asyncio
async def test_send_message_with_tenant_isolation(
    db_session,
    tenant_manager,
    db_manager,
    websocket_manager
):
    """Test send_message enforces tenant isolation"""
    from giljo_mcp.services.message_service import MessageService
    from giljo_mcp.tools.tool_accessor import ToolAccessor
    from giljo_mcp.models import Project, Product

    # Create two tenants
    tenant_a = str(uuid4())
    tenant_b = str(uuid4())

    # Create products and projects for each tenant
    product_a = Product(id=str(uuid4()), name="Product A", tenant_key=tenant_a, is_active=True)
    project_a = Project(
        id=str(uuid4()),
        name="Project A",
        mission="Test mission",
        tenant_key=tenant_a,
        product_id=product_a.id,
        status="active"
    )

    product_b = Product(id=str(uuid4()), name="Product B", tenant_key=tenant_b, is_active=True)
    project_b = Project(
        id=str(uuid4()),
        name="Project B",
        mission="Test mission",
        tenant_key=tenant_b,
        product_id=product_b.id,
        status="active"
    )

    db_session.add_all([product_a, product_b, project_a, project_b])
    await db_session.commit()

    # Create ToolAccessor
    tool_accessor = ToolAccessor(
        db_manager=db_manager,
        tenant_manager=tenant_manager,
        websocket_manager=websocket_manager
    )

    # Test 1: Send message with correct tenant_key
    result_a = await tool_accessor.send_message(
        to_agents=["orchestrator"],
        content="Message for tenant A",
        project_id=str(project_a.id),
        tenant_key=tenant_a  # EXPLICIT
    )
    assert result_a["success"] is True

    # Test 2: Send message with WRONG tenant_key should fail
    result_wrong = await tool_accessor.send_message(
        to_agents=["orchestrator"],
        content="Cross-tenant message (should fail)",
        project_id=str(project_a.id),  # Project A
        tenant_key=tenant_b  # Tenant B (WRONG)
    )
    assert result_wrong["success"] is False
    assert "not found" in result_wrong.get("error", "").lower()

    # Test 3: Send message WITHOUT tenant_key (uses TenantManager)
    tenant_manager.set_current_tenant(tenant_a)
    result_implicit = await tool_accessor.send_message(
        to_agents=["orchestrator"],
        content="Message using TenantManager context",
        project_id=str(project_a.id)
        # NO tenant_key - should use TenantManager
    )
    assert result_implicit["success"] is True
```

#### 3.2 Run Full Test Suite
```bash
# Service layer tests
pytest tests/services/test_message_service.py -v

# Integration tests
pytest tests/integration/test_agent_messaging.py -v

# Full suite
pytest tests/ -k message --cov=src/giljo_mcp/services/message_service
```

---

## Files to Modify

### Core Implementation
1. `src/giljo_mcp/tools/tool_accessor.py` - Add `tenant_key` parameter to `send_message`
2. `api/endpoints/mcp_http.py` - Update MCP schema for `send_message` and improve tool descriptions

### Documentation
3. `docs/api/agent_identification.md` - NEW FILE: Agent identification guide
4. `docs/api/mcp_tools.md` - Update with agent identification reference

### Tests
5. `tests/services/test_message_service.py` - Add explicit tenant_key test
6. `tests/integration/test_agent_messaging.py` - NEW FILE: Integration tests

---

## Testing Strategy

### Unit Tests
- ✅ `test_send_message_with_explicit_tenant_key`: Verify explicit tenant_key works
- ✅ `test_send_message_without_tenant_key`: Verify TenantManager fallback works
- ✅ `test_send_message_tenant_isolation`: Verify cross-tenant messages fail

### Integration Tests
- ✅ `test_send_message_via_mcp_http`: Verify MCP HTTP endpoint accepts tenant_key
- ✅ `test_send_message_agent_type_resolution`: Verify agent_type resolves to job_id
- ✅ `test_send_message_broadcast`: Verify broadcast (`to_agents=['all']`) works

### Manual Testing
1. Call `send_message` via MCP HTTP with `tenant_key` parameter
2. Verify message appears in recipient's `receive_messages` response
3. Verify WebSocket events fire correctly
4. Verify tenant isolation (cannot send to other tenant's agents)

---

## Success Criteria

### Functional
- ✅ `send_message` accepts optional `tenant_key` parameter
- ✅ MCP schema advertises `tenant_key` in properties (not required)
- ✅ Explicit `tenant_key` takes precedence over TenantManager context
- ✅ Backward compatibility: existing calls without `tenant_key` still work
- ✅ Tenant isolation enforced: cross-tenant messages fail gracefully

### Documentation
- ✅ Agent identification guide published in `docs/api/`
- ✅ All MCP tool schemas reference agent identification guide
- ✅ Examples provided for common use cases

### Testing
- ✅ Unit tests pass for MessageService with tenant_key
- ✅ Integration tests pass for ToolAccessor send_message
- ✅ MCP HTTP endpoint tests pass
- ✅ No regressions in existing message tests

---

## Rollout Plan

### Stage 1: Implementation (2 hours)
1. Update ToolAccessor.send_message signature
2. Update MCP schema in mcp_http.py
3. Run unit tests to verify no regressions

### Stage 2: Documentation (1 hour)
1. Create agent identification guide
2. Update MCP tool descriptions
3. Add examples to orchestrator staging prompt

### Stage 3: Testing (1 hour)
1. Create integration tests
2. Run full test suite
3. Manual testing via MCP HTTP endpoint

### Stage 4: Alpha Trial Validation (30 minutes)
1. Re-run alpha trial scenario from Issue #3
2. Verify agents can successfully send messages
3. Verify orchestrator can coordinate agents

---

## Risk Assessment

### Low Risk
- **Backward Compatibility**: `tenant_key` is optional, existing calls work unchanged
- **Service Layer**: MessageService already supports `tenant_key`, no changes needed
- **Testing**: Comprehensive test coverage ensures no regressions

### Medium Risk
- **Documentation Debt**: Many existing docs may reference old parameter patterns
  - **Mitigation**: Focused update to agent identification guide, link from all tools

### High Risk
- **None identified**: Changes are additive and well-tested

---

## Dependencies

### Blocking
- None (standalone fix)

### Blocked By This
- Alpha trial testing (Issue #3 blocks progress)
- Agent coordination workflows
- Multi-tenant isolation validation

---

## Follow-Up Work

### Recommended (Not Blocking)
1. **Audit All MCP Tools**: Review all 30+ tools for parameter consistency
2. **Standardize Parameter Names**: Consider renaming `agent_id` → `job_id` everywhere
3. **Add Parameter Validation**: Validate UUID format for job_ids, enum values for agent_types
4. **Improve Error Messages**: Return clear errors when wrong identifier type used

### Future Enhancements
1. **Type Hints**: Add Python type hints for agent identifiers (NewType pattern)
2. **Pydantic Models**: Create shared request/response models for agent tools
3. **GraphQL Schema**: Consider GraphQL for more self-documenting API

---

## References

- **Issue #3**: Alpha trial agent messaging error
- **Issue #9**: Agent ID inconsistency
- **Handover 0325**: Multi-tenant isolation in MessageService
- **Handover 0295**: Messaging tool contract
- **Handover 0045**: Agent coordination tools

---

## Approval Required

- [ ] System Architect (parameter design)
- [ ] TDD Implementor (test coverage)
- [ ] Documentation Manager (agent identification guide)
- [ ] Orchestrator Coordinator (alpha trial validation)

---

## ⚠️ DEVELOPER DISCUSSION REQUIRED

**Before implementing this handover, discuss the following with the developer:**

### Options to Review

1. **tenant_key Parameter Strategy**
   - Option A: Add tenant_key to send_message for consistency (proposed)
   - Option B: Remove tenant_key requirement from other tools where possible
   - Option C: Document clearly which tools need it vs which don't
   - **Trade-offs**: Consistency vs backward compatibility vs API simplicity

2. **Agent Identification Standardization**
   - Option A: Standardize on job_id universally
   - Option B: Keep both job_id and agent_type, document when to use each
   - Option C: Add wrapper functions that accept either format
   - **Trade-offs**: Breaking changes vs clarity vs flexibility

3. **Error Message Improvements**
   - Should we add more descriptive errors when wrong identifier type is used?
   - Example: "Expected job_id (UUID), got agent_type 'analyzer'. Use job_id for this operation."

### Questions for Developer

- [ ] Is backward compatibility required for existing integrations?
- [ ] Should we deprecate agent_type parameters or keep them?
- [ ] What's the migration strategy if we standardize on job_id?

### Alpha Trial Reference

Review agent feedback for real-world context:
- `F:\TinyContacts\analyzer_feedback.md` - Lines 129-141 (Agent ID Confusion)
- `F:\TinyContacts\documenter_feedback.md` - Lines 93-97 (tenant_key error)

### Session Context

This handover originated from the **Alpha Trial Remediation Session** (2025-12-19).
See: `handovers/alpha_trial_remediation_roadmap.md` for full context and prioritization rationale.
