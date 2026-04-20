# Staging Cancellation Test Design Document
**Feature**: Cancel Project Staging - Delete Spawned Agents & Clear Mission
**Handover Context**: Backend integration testing for staging cancellation feature
**Author**: Backend Integration Tester Agent
**Date**: 2025-11-06

## Table of Contents
1. [Overview](#overview)
2. [Feature Specification](#feature-specification)
3. [Test Categories](#test-categories)
4. [Happy Path Tests](#happy-path-tests)
5. [Edge Case Tests](#edge-case-tests)
6. [Error Case Tests](#error-case-tests)
7. [Multi-Tenant Isolation Tests](#multi-tenant-isolation-tests)
8. [Race Condition Tests](#race-condition-tests)
9. [WebSocket Integration Tests](#websocket-integration-tests)
10. [Performance Considerations](#performance-considerations)
11. [Test Implementation Pseudocode](#test-implementation-pseudocode)
12. [Coverage Goals](#coverage-goals)

---

## Overview

The staging cancellation feature allows users to cancel a project after staging (orchestrator creates mission and spawns agents) but before launching agents. This provides a critical "undo" mechanism for the staging workflow.

**Key Requirements**:
- Delete all spawned agents (status='waiting', 'preparing')
- Preserve launched agents (status='active', 'working')
- Clear or preserve mission (TBD by architect)
- Fire WebSocket events for UI updates
- Maintain multi-tenant isolation
- Handle race conditions gracefully

**Architecture Components**:
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Models**: `Project`, `MCPAgentJob` (agent jobs table)
- **API**: FastAPI REST endpoints
- **Real-time**: WebSocket broadcasts via `WebSocketDependency`
- **Testing**: pytest + pytest-asyncio + httpx

---

## Feature Specification

### Staging Workflow Context

```
User Action              Database State                    Agent Status
──────────────────────────────────────────────────────────────────────────
1. Stage Project      → Orchestrator creates mission
                        Mission stored in project.mission

2. Orchestrator       → Spawns 5 agents                   status='waiting'
   Spawns Agents        - Backend Agent
                        - Frontend Agent
                        - Database Agent
                        - Testing Agent
                        - Documentation Agent

3. User Reviews       → User inspects agent grid
   Agent Grid           UI shows 5 spawned agents

4. CANCELLATION       → DELETE spawned agents             [DELETED]
   (This Feature)       CLEAR mission (TBD)
                        WebSocket: agent:deleted events

5. Launch Agent       → User changes mind, launches one   status='active'
   (After Cancel)       New agent created, old deleted
```

### Cancellation Behavior Matrix

| Scenario | Agent Status | Action | Preserve? |
|----------|-------------|--------|-----------|
| Spawned agents | `waiting`, `preparing` | DELETE | ❌ No |
| Launched agents | `active`, `working` | KEEP | ✅ Yes |
| Completed agents | `complete`, `failed` | KEEP | ✅ Yes |
| Orchestrator | `active` (type=orchestrator) | KEEP | ✅ Yes |
| Mission text | project.mission | CLEAR/PRESERVE | ⚠️ TBD |

### API Endpoint Design (Proposed)

```python
POST /api/projects/{project_id}/cancel-staging
Headers:
  Authorization: Bearer <token>
  Content-Type: application/json

Body (optional):
  {
    "clear_mission": true,  # TBD by architect (default: false)
    "reason": "User requested cancellation"
  }

Response (200 OK):
  {
    "success": true,
    "project_id": "uuid",
    "deleted_agents_count": 5,
    "mission_cleared": false,
    "timestamp": "2025-11-06T12:34:56Z"
  }

Response (400 Bad Request):
  {
    "error": "No staged agents to cancel",
    "project_id": "uuid"
  }

Response (404 Not Found):
  {
    "error": "Project not found"
  }
```

### WebSocket Events

```javascript
// Agent deletion event (fired for each deleted agent)
{
  type: "agent:deleted",
  tenant_key: "tk_123",
  project_id: "proj-uuid",
  agent: {
    job_id: "job-uuid",
    agent_type: "backend-agent",
    status: "waiting"  // Status before deletion
  },
  timestamp: "2025-11-06T12:34:56Z"
}

// Staging cancelled event (summary)
{
  type: "project:staging_cancelled",
  tenant_key: "tk_123",
  project_id: "proj-uuid",
  deleted_agents_count: 5,
  mission_cleared: false,
  timestamp: "2025-11-06T12:34:56Z"
}
```

---

## Test Categories

### 1. Happy Path Tests (8 tests)
Core functionality with expected successful outcomes.

### 2. Edge Case Tests (6 tests)
Boundary conditions and unusual but valid scenarios.

### 3. Error Case Tests (5 tests)
Invalid inputs and failure conditions.

### 4. Multi-Tenant Isolation Tests (4 tests)
Security-critical tenant isolation verification.

### 5. Race Condition Tests (4 tests)
Concurrent operations and timing conflicts.

### 6. WebSocket Integration Tests (5 tests)
Real-time event broadcasting validation.

---

## Happy Path Tests

### Test 1: Cancel After Orchestrator Stages (5 Agents Spawned)

**Scenario**: User stages project, orchestrator spawns 5 agents, user cancels.

**Setup**:
```python
- Create project (status='active')
- Create orchestrator agent (status='active', agent_type='orchestrator')
- Orchestrator generates mission (project.mission = "...")
- Orchestrator spawns 5 agents (status='waiting'):
  - Backend Agent
  - Frontend Agent
  - Database Agent
  - Testing Agent
  - Documentation Agent
```

**Action**:
```python
POST /api/projects/{project_id}/cancel-staging
```

**Expected Outcome**:
- ✅ All 5 spawned agents deleted from database
- ✅ Orchestrator agent preserved (status='active')
- ✅ Mission cleared or preserved (per architect decision)
- ✅ WebSocket events fired (5x agent:deleted + 1x project:staging_cancelled)
- ✅ HTTP 200 response with deleted_agents_count=5

**Database Verification**:
```python
assert db.query(MCPAgentJob).filter_by(
    project_id=project_id,
    status='waiting'
).count() == 0

assert db.query(MCPAgentJob).filter_by(
    project_id=project_id,
    agent_type='orchestrator',
    status='active'
).count() == 1
```

---

### Test 2: Cancel with One Agent Already Launched

**Scenario**: User launches 1 agent (becomes active), then cancels staging.

**Setup**:
```python
- Create project
- Orchestrator spawns 5 agents (status='waiting')
- User launches Backend Agent (status='active')
- 4 agents remain in 'waiting' state
```

**Action**:
```python
POST /api/projects/{project_id}/cancel-staging
```

**Expected Outcome**:
- ✅ 4 waiting agents deleted
- ✅ 1 active agent preserved (Backend Agent)
- ✅ Orchestrator preserved
- ✅ WebSocket events: 4x agent:deleted (not 5)
- ✅ Response: deleted_agents_count=4

**Critical Assertion**:
```python
# Verify launched agent NOT deleted
active_agent = db.query(MCPAgentJob).filter_by(
    project_id=project_id,
    agent_type='backend-agent',
    status='active'
).first()

assert active_agent is not None
assert active_agent.job_id == launched_agent_id
```

---

### Test 3: Cancel with No Agents Spawned (Orchestrator Created Mission Only)

**Scenario**: Orchestrator created mission but hasn't spawned agents yet.

**Setup**:
```python
- Create project
- Create orchestrator (status='active')
- Set project.mission = "Generated mission text"
- NO spawned agents
```

**Action**:
```python
POST /api/projects/{project_id}/cancel-staging
```

**Expected Outcome**:
- ✅ HTTP 200 or 400 (depends on implementation)
- ✅ deleted_agents_count=0
- ✅ Mission cleared (if clear_mission=true)
- ✅ Orchestrator preserved
- ✅ WebSocket event: project:staging_cancelled

**Note**: This is a valid cancellation (user changes mind before agent spawn).

---

### Test 4: Cancel Twice (Idempotent Operation)

**Scenario**: User clicks "Cancel Staging" button twice rapidly.

**Setup**:
```python
- Create project with 5 waiting agents
```

**Action**:
```python
# First cancellation
response1 = POST /api/projects/{project_id}/cancel-staging

# Second cancellation (immediate)
response2 = POST /api/projects/{project_id}/cancel-staging
```

**Expected Outcome**:
- ✅ First request: 200 OK, deleted_agents_count=5
- ✅ Second request: 200 OK (idempotent) or 400 (no agents to cancel)
- ✅ No errors or exceptions
- ✅ Database consistent state

**Idempotency Guarantee**:
```python
# Both requests succeed, operation is idempotent
assert response1.status_code == 200
assert response2.status_code in [200, 400]  # Both valid

# No duplicate deletions
assert db.query(MCPAgentJob).filter_by(
    project_id=project_id,
    status='waiting'
).count() == 0
```

---

### Test 5: Cancel with Multiple Orchestrator Instances (Succession)

**Scenario**: Orchestrator handed over to successor (Handover 0080), user cancels.

**Setup**:
```python
- Create project
- Orchestrator 1 (instance_number=1, handover_to=orch2_uuid)
- Orchestrator 2 (instance_number=2, status='active')
- Orchestrator 2 spawned 3 agents (status='waiting')
```

**Action**:
```python
POST /api/projects/{project_id}/cancel-staging
```

**Expected Outcome**:
- ✅ 3 waiting agents deleted (spawned by Orchestrator 2)
- ✅ Both orchestrators preserved
- ✅ Succession chain intact (handover_to links maintained)
- ✅ WebSocket events: 3x agent:deleted

**Succession Chain Verification**:
```python
# Verify succession lineage preserved
orch1 = db.query(MCPAgentJob).filter_by(
    project_id=project_id,
    agent_type='orchestrator',
    instance_number=1
).first()

orch2 = db.query(MCPAgentJob).filter_by(
    project_id=project_id,
    agent_type='orchestrator',
    instance_number=2
).first()

assert orch1 is not None
assert orch2 is not None
assert orch1.handover_to == orch2.job_id
```

---

### Test 6: Cancel with Mission Cleared

**Scenario**: User explicitly requests mission clearing during cancellation.

**Setup**:
```python
- Create project
- Set project.mission = "Generated mission (3000 tokens)"
- Spawn 5 agents (status='waiting')
```

**Action**:
```python
POST /api/projects/{project_id}/cancel-staging
Body: {"clear_mission": true}
```

**Expected Outcome**:
- ✅ All 5 agents deleted
- ✅ project.mission = NULL or ""
- ✅ Response: mission_cleared=true
- ✅ WebSocket event includes mission_cleared flag

**Database Verification**:
```python
project = db.query(Project).filter_by(id=project_id).first()
assert project.mission is None or project.mission == ""
```

---

### Test 7: Cancel with Mission Preserved

**Scenario**: User cancels staging but preserves mission for re-staging.

**Setup**:
```python
- Create project
- Set project.mission = "Generated mission (3000 tokens)"
- Spawn 5 agents
```

**Action**:
```python
POST /api/projects/{project_id}/cancel-staging
Body: {"clear_mission": false}  # Explicit preservation
```

**Expected Outcome**:
- ✅ All 5 agents deleted
- ✅ project.mission preserved (unchanged)
- ✅ Response: mission_cleared=false

**Use Case**: User wants to review/edit mission before re-staging.

---

### Test 8: Cancel and Re-Stage Workflow

**Scenario**: Complete workflow: Stage → Cancel → Stage Again → Launch.

**Steps**:
```python
1. Stage project (orchestrator spawns 5 agents)
2. Cancel staging (delete 5 agents)
3. Stage project again (orchestrator spawns 5 NEW agents)
4. Launch 1 agent successfully
```

**Verification**:
```python
# After step 2: No waiting agents
assert waiting_agents_count == 0

# After step 3: 5 new waiting agents (different UUIDs)
new_agents = db.query(MCPAgentJob).filter_by(
    project_id=project_id,
    status='waiting'
).all()
assert len(new_agents) == 5
assert all(a.job_id not in old_agent_ids for a in new_agents)

# After step 4: 1 active, 4 waiting
assert active_agents_count == 1
assert waiting_agents_count == 4
```

---

## Edge Case Tests

### Test 9: Cancel Project with No Orchestrator

**Scenario**: Project exists but has no orchestrator (edge case from manual testing).

**Setup**:
```python
- Create project (status='active')
- NO orchestrator created
- User attempts cancellation
```

**Expected Outcome**:
- ✅ HTTP 400 or 404 (no orchestrator to cancel)
- ✅ Clear error message
- ✅ No database changes

---

### Test 10: Cancel Project with All Agents in Terminal States

**Scenario**: All spawned agents already completed/failed.

**Setup**:
```python
- Create project
- Spawn 5 agents
- Mark all 5 as 'complete' or 'failed'
```

**Action**:
```python
POST /api/projects/{project_id}/cancel-staging
```

**Expected Outcome**:
- ✅ HTTP 200 or 400
- ✅ deleted_agents_count=0 (no waiting agents)
- ✅ Terminal agents preserved
- ✅ Message: "No staged agents to cancel"

---

### Test 11: Cancel with Agents in 'preparing' Status

**Scenario**: Some agents in 'preparing' state (transitioning to active).

**Setup**:
```python
- Create project
- 2 agents: status='waiting'
- 3 agents: status='preparing'
```

**Action**:
```python
POST /api/projects/{project_id}/cancel-staging
```

**Expected Outcome**:
- ✅ All 5 agents deleted (both 'waiting' and 'preparing')
- ✅ deleted_agents_count=5
- ✅ Status filter: `status IN ('waiting', 'preparing')`

**SQL Query Verification**:
```sql
DELETE FROM mcp_agent_jobs
WHERE project_id = 'uuid'
  AND tenant_key = 'tk_123'
  AND status IN ('waiting', 'preparing')
  AND agent_type != 'orchestrator';
```

---

### Test 12: Cancel with Large Agent Count (100 Agents)

**Scenario**: Performance test with 100 spawned agents.

**Setup**:
```python
- Create project
- Spawn 100 agents (status='waiting')
```

**Action**:
```python
POST /api/projects/{project_id}/cancel-staging
```

**Expected Outcome**:
- ✅ All 100 agents deleted
- ✅ Response time < 5 seconds
- ✅ 100 WebSocket events (or batched)
- ✅ Database transaction succeeds

**Performance Considerations**:
- Batch DELETE query (single transaction)
- Consider batching WebSocket events (10-20 per batch)
- UI should handle 100+ agent:deleted events gracefully

---

### Test 13: Cancel with Mixed Agent Types

**Scenario**: Project has orchestrator + sub-agents + spawned agents.

**Setup**:
```python
- Orchestrator (status='active')
- 2 sub-agents (status='active', spawned_by=orchestrator)
- 5 waiting agents (status='waiting', spawned_by=orchestrator)
```

**Action**:
```python
POST /api/projects/{project_id}/cancel-staging
```

**Expected Outcome**:
- ✅ 5 waiting agents deleted
- ✅ Orchestrator preserved
- ✅ 2 sub-agents preserved (already active)
- ✅ deleted_agents_count=5

---

### Test 14: Cancel Immediately After Staging

**Scenario**: User cancels <1 second after staging completes.

**Setup**:
```python
- Stage project (spawns 5 agents)
- Cancel immediately (within 100ms)
```

**Expected Outcome**:
- ✅ Cancellation succeeds
- ✅ No race conditions
- ✅ Consistent database state

**Race Condition Protection**:
- Database transaction isolation (READ COMMITTED)
- Agent deletion filter includes tenant_key (prevents cross-tenant)

---

## Error Case Tests

### Test 15: Cancel Non-Existent Project

**Scenario**: Project ID does not exist in database.

**Action**:
```python
POST /api/projects/00000000-0000-0000-0000-000000000000/cancel-staging
```

**Expected Outcome**:
- ✅ HTTP 404 Not Found
- ✅ Error message: "Project not found"
- ✅ No database changes

---

### Test 16: Cancel Without Permission (Authentication)

**Scenario**: User attempts to cancel project without valid JWT token.

**Action**:
```python
POST /api/projects/{project_id}/cancel-staging
Headers: [No Authorization header]
```

**Expected Outcome**:
- ✅ HTTP 401 Unauthorized
- ✅ Error message: "Authentication required"

---

### Test 17: Cancel with Database Error

**Scenario**: Database connection fails during deletion.

**Setup**:
```python
- Create project with 5 agents
- Mock database to raise exception during DELETE
```

**Expected Outcome**:
- ✅ HTTP 500 Internal Server Error
- ✅ Transaction rolled back (no partial deletions)
- ✅ All 5 agents still exist in database
- ✅ Error logged to application logs

**Atomicity Verification**:
```python
# After failed cancellation, all agents should still exist
agents = db.query(MCPAgentJob).filter_by(
    project_id=project_id,
    status='waiting'
).all()
assert len(agents) == 5  # No partial deletion
```

---

### Test 18: Cancel with Invalid Request Body

**Scenario**: Malformed JSON in request body.

**Action**:
```python
POST /api/projects/{project_id}/cancel-staging
Body: "invalid json{{"
```

**Expected Outcome**:
- ✅ HTTP 400 Bad Request
- ✅ Error message: "Invalid JSON"

---

### Test 19: Cancel with WebSocket Broadcast Failure

**Scenario**: WebSocket broadcast fails (no connected clients).

**Setup**:
```python
- Create project with 5 agents
- Mock WebSocket dependency to raise exception
```

**Expected Outcome**:
- ✅ Agents still deleted (core operation succeeds)
- ✅ WebSocket error logged
- ✅ HTTP 200 response (degraded but successful)
- ✅ Warning in response: "Events not broadcast"

**Graceful Degradation**:
```python
# Cancellation should succeed even if WebSocket fails
try:
    await ws_dep.broadcast_to_tenant(...)
except Exception as e:
    logger.warning(f"WebSocket broadcast failed: {e}")
    # Continue with cancellation
```

---

## Multi-Tenant Isolation Tests

### Test 20: Cannot Cancel Other Tenant's Staging

**Scenario**: Tenant A attempts to cancel Tenant B's project staging.

**Setup**:
```python
- Tenant A: tk_tenant_a
- Tenant B: tk_tenant_b
- Project B (tenant_key='tk_tenant_b') with 5 waiting agents
- User A authenticated (tenant_key='tk_tenant_a')
```

**Action**:
```python
# User A attempts to cancel Tenant B's project
POST /api/projects/{project_b_id}/cancel-staging
Headers: Authorization: Bearer <tenant_a_token>
```

**Expected Outcome**:
- ✅ HTTP 404 Not Found (project not visible to Tenant A)
- ✅ NO agents deleted
- ✅ Zero cross-tenant leakage
- ✅ Security audit log entry

**Database Query Verification**:
```sql
-- API endpoint MUST include tenant_key filter
SELECT * FROM projects
WHERE id = 'project_b_id'
  AND tenant_key = 'tk_tenant_a';  -- Returns 0 rows
```

---

### Test 21: Multi-Tenant Agent Deletion Filtering

**Scenario**: Verify tenant_key filter in DELETE query.

**Setup**:
```python
- Tenant A: Project with 3 agents (job_ids: A1, A2, A3)
- Tenant B: Project with 3 agents (job_ids: B1, B2, B3)
- Both projects have same UUID (collision test)
```

**Action**:
```python
# Tenant A cancels staging
POST /api/projects/{project_id}/cancel-staging
Headers: Authorization: Bearer <tenant_a_token>
```

**Expected Outcome**:
- ✅ Only Tenant A's 3 agents deleted (A1, A2, A3)
- ✅ Tenant B's 3 agents preserved (B1, B2, B3)
- ✅ WHERE clause includes tenant_key

**Critical SQL**:
```sql
DELETE FROM mcp_agent_jobs
WHERE project_id = 'uuid'
  AND tenant_key = 'tk_tenant_a'  -- CRITICAL FILTER
  AND status IN ('waiting', 'preparing');
```

---

### Test 22: Multi-Tenant WebSocket Isolation

**Scenario**: WebSocket events only sent to correct tenant.

**Setup**:
```python
- Tenant A: 2 connected WebSocket clients
- Tenant B: 2 connected WebSocket clients
- Tenant A cancels staging
```

**Expected Outcome**:
- ✅ Tenant A clients receive agent:deleted events
- ✅ Tenant B clients receive ZERO events
- ✅ WebSocket broadcast filtered by tenant_key

**WebSocket Event Verification**:
```python
await ws_dep.broadcast_to_tenant(
    tenant_key="tk_tenant_a",  # ONLY Tenant A clients
    event_type="agent:deleted",
    data={"agent": {...}}
)
```

---

### Test 23: Multi-Tenant Deletion Count Accuracy

**Scenario**: Verify deleted_agents_count reflects tenant-specific agents only.

**Setup**:
```python
- Tenant A: Project with 5 agents
- Tenant B: Project with 10 agents (different project)
- Same project name (collision test)
```

**Action**:
```python
# Tenant A cancels
response = POST /api/projects/{project_a_id}/cancel-staging
```

**Expected Outcome**:
- ✅ Response: deleted_agents_count=5 (not 15)
- ✅ Only Tenant A's agents counted

---

## Race Condition Tests

### Test 24: User Clicks Launch + Cancel Simultaneously

**Scenario**: User clicks "Launch Agent" and "Cancel Staging" at the same time.

**Setup**:
```python
- Project with 5 waiting agents
- Backend Agent UUID: agent_uuid
```

**Action**:
```python
# Concurrent requests (within 10ms)
import asyncio

async def test_race():
    launch_task = asyncio.create_task(
        launch_agent(agent_uuid)
    )
    cancel_task = asyncio.create_task(
        cancel_staging(project_id)
    )

    results = await asyncio.gather(
        launch_task,
        cancel_task,
        return_exceptions=True
    )
```

**Expected Outcomes (Both Valid)**:

**Outcome A**: Launch Wins
- ✅ Agent transitioned to 'active' (launch succeeded)
- ✅ Cancellation deleted 4 other agents (not the active one)
- ✅ deleted_agents_count=4

**Outcome B**: Cancel Wins
- ✅ Agent deleted before launch completed
- ✅ Launch request fails (404 agent not found)
- ✅ deleted_agents_count=5

**Database Consistency**:
- ✅ No deadlocks
- ✅ No partial state (agent half-deleted)
- ✅ Transaction isolation prevents corruption

---

### Test 25: Orchestrator Spawning While User Cancels

**Scenario**: Orchestrator actively spawning agents while user cancels.

**Setup**:
```python
- Orchestrator spawning agents (async loop)
- User cancels mid-spawn (after 2 agents, before agent 3)
```

**Timeline**:
```
T=0ms:  Orchestrator starts spawning
T=100ms: Agent 1 created (status='waiting')
T=200ms: Agent 2 created (status='waiting')
T=250ms: USER CANCELS STAGING
T=300ms: Agent 3 creation attempt (should fail or be deleted)
```

**Expected Outcome**:
- ✅ Agents 1 & 2 deleted
- ✅ Agent 3 either:
  - Not created (spawn aborted), OR
  - Created and immediately deleted
- ✅ Final state: 0 waiting agents

**Implementation Note**:
Orchestrator spawn loop should check for cancellation flag:
```python
async def spawn_agents():
    for agent_type in agent_types:
        if project.is_cancelling:  # Check flag
            logger.info("Spawn aborted due to cancellation")
            break
        await create_agent(agent_type)
```

---

### Test 26: Multiple Users Cancel Same Project

**Scenario**: Two admin users cancel the same project simultaneously.

**Setup**:
```python
- Project with 5 agents
- Admin User 1 (tenant_key='tk_123')
- Admin User 2 (tenant_key='tk_123', same tenant)
```

**Action**:
```python
# Concurrent cancellation requests
import asyncio

cancel1 = asyncio.create_task(
    client1.post(f"/api/projects/{project_id}/cancel-staging")
)
cancel2 = asyncio.create_task(
    client2.post(f"/api/projects/{project_id}/cancel-staging")
)

responses = await asyncio.gather(cancel1, cancel2)
```

**Expected Outcome**:
- ✅ One request: 200 OK, deleted_agents_count=5
- ✅ Other request: 200 OK (idempotent), deleted_agents_count=0
- ✅ Total agents deleted: 5 (not 10)
- ✅ No duplicate WebSocket events (5 events, not 10)

**Database Protection**:
```sql
-- DELETE is idempotent (second DELETE matches 0 rows)
DELETE FROM mcp_agent_jobs WHERE ...;
-- Returns: deleted_count = 5 (first request)
-- Returns: deleted_count = 0 (second request)
```

---

### Test 27: Cancel During Database Transaction

**Scenario**: Cancellation request arrives during ongoing database write.

**Setup**:
```python
- Project with 5 agents
- Simulate slow database transaction (agent creation in progress)
```

**Expected Outcome**:
- ✅ Transaction isolation (READ COMMITTED or higher)
- ✅ Cancellation waits for transaction lock
- ✅ No dirty reads or phantom agents
- ✅ Final state consistent

---

## WebSocket Integration Tests

### Test 28: Agent Deletion Events Broadcast Correctly

**Scenario**: Verify all agent:deleted events sent to correct clients.

**Setup**:
```python
- Project with 5 agents
- 3 WebSocket clients connected (same tenant)
```

**Action**:
```python
POST /api/projects/{project_id}/cancel-staging
```

**Expected Outcome**:
- ✅ Each client receives 5 agent:deleted events
- ✅ Event structure matches schema
- ✅ Events received within 2 seconds

**Event Validation**:
```python
for event in received_events:
    assert event["type"] == "agent:deleted"
    assert "agent" in event
    assert "job_id" in event["agent"]
    assert "agent_type" in event["agent"]
    assert event["tenant_key"] == "tk_123"
```

---

### Test 29: Project Staging Cancelled Summary Event

**Scenario**: Verify project:staging_cancelled summary event.

**Expected Outcome**:
- ✅ Summary event sent AFTER all agent:deleted events
- ✅ Event includes deleted_agents_count
- ✅ Event includes mission_cleared flag

**Event Order**:
```
1. agent:deleted (Backend Agent)
2. agent:deleted (Frontend Agent)
3. agent:deleted (Database Agent)
4. agent:deleted (Testing Agent)
5. agent:deleted (Documentation Agent)
6. project:staging_cancelled (SUMMARY)
```

---

### Test 30: WebSocket Events with No Connected Clients

**Scenario**: Cancellation when no clients connected.

**Setup**:
```python
- Project with 5 agents
- Zero WebSocket clients connected
```

**Expected Outcome**:
- ✅ Cancellation succeeds (no errors)
- ✅ Events logged but not sent
- ✅ HTTP 200 response

**Graceful Handling**:
```python
clients_notified = await ws_dep.broadcast_to_tenant(...)
# Returns 0 if no clients connected (not an error)
```

---

### Test 31: WebSocket Event Batching (100 Agents)

**Scenario**: Verify event batching for large agent counts.

**Setup**:
```python
- Project with 100 agents
- 2 WebSocket clients connected
```

**Expected Outcome**:
- ✅ Events batched (e.g., 10 events per batch)
- ✅ Clients receive all 100 events (no drops)
- ✅ UI remains responsive (no event flood)

**Batch Implementation**:
```python
# Batch events to avoid overwhelming clients
BATCH_SIZE = 10
for i in range(0, len(deleted_agents), BATCH_SIZE):
    batch = deleted_agents[i:i+BATCH_SIZE]
    await ws_dep.broadcast_batch(batch)
    await asyncio.sleep(0.1)  # Small delay between batches
```

---

### Test 32: WebSocket Reconnection During Cancellation

**Scenario**: Client reconnects during cancellation (receives partial events).

**Setup**:
```python
- Project with 10 agents
- Client connected, receives 3 events, disconnects
- Client reconnects mid-cancellation
```

**Expected Outcome**:
- ✅ Client receives remaining 7 events after reconnection
- ✅ No duplicate events
- ✅ Final UI state correct (10 agents deleted)

**Event Queue Handling**:
```python
# WebSocket should queue events during disconnect
# Deliver queued events on reconnection
```

---

## Performance Considerations

### Scalability Metrics

| Agent Count | Max Deletion Time | WebSocket Events | Database Queries |
|-------------|-------------------|------------------|------------------|
| 5 agents | <500ms | 5 + 1 summary | 1 DELETE |
| 50 agents | <2s | 50 + 1 (batched) | 1 DELETE |
| 100 agents | <5s | 100 + 1 (batched) | 1 DELETE |
| 500 agents | <20s | 500 + 1 (batched) | 1 DELETE |

### Database Optimization

**Single DELETE Query** (Critical):
```sql
-- EFFICIENT: Single query deletes all agents
DELETE FROM mcp_agent_jobs
WHERE project_id = 'uuid'
  AND tenant_key = 'tk_123'
  AND status IN ('waiting', 'preparing')
  AND agent_type != 'orchestrator'
RETURNING id, job_id, agent_type;  -- Return deleted rows for events
```

**AVOID Multiple Queries**:
```sql
-- INEFFICIENT: N queries for N agents
FOR each agent IN waiting_agents:
    DELETE FROM mcp_agent_jobs WHERE id = agent.id;
```

### WebSocket Event Batching

**Batching Strategy** (for 50+ agents):
```python
BATCH_SIZE = 20
BATCH_DELAY_MS = 100

for batch in chunked(deleted_agents, BATCH_SIZE):
    await ws_dep.broadcast_batch(
        tenant_key=tenant_key,
        event_type="agent:deleted",
        agents=batch
    )
    await asyncio.sleep(BATCH_DELAY_MS / 1000)
```

### Frontend Considerations

**UI Update Strategy**:
```javascript
// Handle large deletions efficiently
onStagingCancelled(event) {
  if (event.deleted_agents_count > 20) {
    // Batch UI update (re-render once)
    this.agentGrid.clear();
    this.agentGrid.loadAgents();  // Fetch fresh state
  } else {
    // Individual removals (smooth animation)
    event.agents.forEach(agent => {
      this.agentGrid.removeAgent(agent.job_id);
    });
  }
}
```

### Indexing Requirements

**Database Indexes** (ensure these exist):
```sql
-- Multi-tenant queries
CREATE INDEX idx_mcp_agent_jobs_tenant_project_status
ON mcp_agent_jobs (tenant_key, project_id, status);

-- Deletion query optimization
CREATE INDEX idx_mcp_agent_jobs_status_type
ON mcp_agent_jobs (status, agent_type);
```

---

## Test Implementation Pseudocode

### Integration Test Structure

```python
# tests/integration/test_staging_cancellation.py

import pytest
import pytest_asyncio
from uuid import uuid4
from httpx import AsyncClient
from sqlalchemy.orm import Session

from api.app import create_app
from api.dependencies.websocket import WebSocketDependency
from src.giljo_mcp.models import Project, MCPAgentJob, User
from tests.helpers.websocket_test_utils import MockWebSocketServer


@pytest_asyncio.fixture
async def test_app():
    """Create test FastAPI application"""
    app = create_app()
    return app


@pytest_asyncio.fixture
async def async_client(test_app, db_session):
    """Create authenticated async HTTP client"""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        # Mock authentication
        client.headers["Authorization"] = f"Bearer {test_jwt_token}"
        yield client


@pytest_asyncio.fixture
async def mock_websocket(db_session):
    """Mock WebSocket dependency for testing"""
    from unittest.mock import AsyncMock

    mock_ws = AsyncMock(spec=WebSocketDependency)
    mock_ws.broadcast_to_tenant = AsyncMock(return_value=3)
    return mock_ws


@pytest_asyncio.fixture
async def project_with_staged_agents(db_session):
    """
    Create project with orchestrator and 5 staged agents.

    Returns:
        dict: {
            "project": Project,
            "orchestrator": MCPAgentJob,
            "agents": List[MCPAgentJob],
            "tenant_key": str
        }
    """
    tenant_key = f"tk_test_{uuid4().hex[:16]}"

    # Create project
    project = Project(
        id=str(uuid4()),
        name="Test Project",
        tenant_key=tenant_key,
        status="active",
        mission="Generated mission text"
    )
    db_session.add(project)

    # Create orchestrator
    orchestrator = MCPAgentJob(
        job_id=str(uuid4()),
        tenant_key=tenant_key,
        project_id=project.id,
        agent_type="orchestrator",
        mission="Orchestrate project",
        status="active",
        messages=[]
    )
    db_session.add(orchestrator)

    # Create 5 staged agents
    agent_types = ["backend-agent", "frontend-agent", "database-agent",
                   "testing-agent", "documentation-agent"]
    agents = []

    for agent_type in agent_types:
        agent = MCPAgentJob(
            job_id=str(uuid4()),
            tenant_key=tenant_key,
            project_id=project.id,
            agent_type=agent_type,
            mission=f"Mission for {agent_type}",
            status="waiting",
            spawned_by=orchestrator.job_id,
            messages=[]
        )
        db_session.add(agent)
        agents.append(agent)

    await db_session.commit()

    return {
        "project": project,
        "orchestrator": orchestrator,
        "agents": agents,
        "tenant_key": tenant_key
    }


# ==========================================
# HAPPY PATH TESTS
# ==========================================

@pytest.mark.asyncio
class TestStagingCancellationHappyPath:
    """Happy path integration tests for staging cancellation"""

    async def test_cancel_after_orchestrator_stages_5_agents(
        self, async_client, db_session, project_with_staged_agents, mock_websocket
    ):
        """
        Test 1: Cancel after orchestrator stages (5 agents spawned)
        """
        # Arrange
        project = project_with_staged_agents["project"]
        agents = project_with_staged_agents["agents"]
        tenant_key = project_with_staged_agents["tenant_key"]

        # Act
        response = await async_client.post(
            f"/api/projects/{project.id}/cancel-staging"
        )

        # Assert: HTTP 200 response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["deleted_agents_count"] == 5
        assert data["project_id"] == str(project.id)

        # Assert: All 5 agents deleted from database
        remaining_agents = await db_session.execute(
            select(MCPAgentJob).filter_by(
                project_id=project.id,
                status="waiting"
            )
        )
        assert remaining_agents.scalars().all() == []

        # Assert: Orchestrator preserved
        orchestrator = await db_session.execute(
            select(MCPAgentJob).filter_by(
                project_id=project.id,
                agent_type="orchestrator"
            )
        )
        assert orchestrator.scalar_one() is not None

        # Assert: WebSocket events fired
        mock_websocket.broadcast_to_tenant.assert_called()
        call_args = mock_websocket.broadcast_to_tenant.call_args_list

        # 5 agent:deleted events + 1 project:staging_cancelled event
        assert len(call_args) == 6

        # Verify event types
        event_types = [call.kwargs["event_type"] for call in call_args]
        assert event_types.count("agent:deleted") == 5
        assert event_types.count("project:staging_cancelled") == 1


    async def test_cancel_with_one_agent_already_launched(
        self, async_client, db_session, project_with_staged_agents
    ):
        """
        Test 2: Cancel with one agent already launched
        """
        # Arrange
        project = project_with_staged_agents["project"]
        agents = project_with_staged_agents["agents"]

        # Launch first agent (Backend Agent)
        backend_agent = agents[0]
        backend_agent.status = "active"
        backend_agent.started_at = datetime.now(timezone.utc)
        await db_session.commit()

        # Act
        response = await async_client.post(
            f"/api/projects/{project.id}/cancel-staging"
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["deleted_agents_count"] == 4  # Not 5

        # Assert: Launched agent NOT deleted
        launched_agent = await db_session.get(MCPAgentJob, backend_agent.id)
        assert launched_agent is not None
        assert launched_agent.status == "active"

        # Assert: 4 waiting agents deleted
        waiting_agents = await db_session.execute(
            select(MCPAgentJob).filter_by(
                project_id=project.id,
                status="waiting"
            )
        )
        assert len(waiting_agents.scalars().all()) == 0


    async def test_cancel_with_no_agents_spawned(
        self, async_client, db_session, project_with_staged_agents
    ):
        """
        Test 3: Cancel with no agents spawned (orchestrator created mission only)
        """
        # Arrange
        project = project_with_staged_agents["project"]

        # Delete all spawned agents (simulate mission-only state)
        await db_session.execute(
            delete(MCPAgentJob).filter_by(
                project_id=project.id,
                status="waiting"
            )
        )
        await db_session.commit()

        # Act
        response = await async_client.post(
            f"/api/projects/{project.id}/cancel-staging"
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["deleted_agents_count"] == 0
        assert data["success"] is True


    async def test_cancel_twice_idempotent(
        self, async_client, db_session, project_with_staged_agents
    ):
        """
        Test 4: Cancel twice (idempotent operation)
        """
        # Arrange
        project = project_with_staged_agents["project"]

        # Act: First cancellation
        response1 = await async_client.post(
            f"/api/projects/{project.id}/cancel-staging"
        )

        # Act: Second cancellation (immediate)
        response2 = await async_client.post(
            f"/api/projects/{project.id}/cancel-staging"
        )

        # Assert: Both succeed
        assert response1.status_code == 200
        assert response2.status_code in [200, 400]  # Both valid

        data1 = response1.json()
        data2 = response2.json()

        assert data1["deleted_agents_count"] == 5
        assert data2["deleted_agents_count"] == 0  # Idempotent

        # Assert: No duplicate deletions
        remaining = await db_session.execute(
            select(MCPAgentJob).filter_by(
                project_id=project.id,
                status="waiting"
            )
        )
        assert len(remaining.scalars().all()) == 0


# ==========================================
# EDGE CASE TESTS
# ==========================================

@pytest.mark.asyncio
class TestStagingCancellationEdgeCases:
    """Edge case tests for staging cancellation"""

    async def test_cancel_with_agents_in_preparing_status(
        self, async_client, db_session, project_with_staged_agents
    ):
        """
        Test 11: Cancel with agents in 'preparing' status
        """
        # Arrange
        project = project_with_staged_agents["project"]
        agents = project_with_staged_agents["agents"]

        # Set 3 agents to 'preparing' status
        for i in range(3):
            agents[i].status = "preparing"
        await db_session.commit()

        # Act
        response = await async_client.post(
            f"/api/projects/{project.id}/cancel-staging"
        )

        # Assert: All 5 agents deleted (waiting + preparing)
        assert response.status_code == 200
        data = response.json()
        assert data["deleted_agents_count"] == 5

        # Verify both 'waiting' and 'preparing' deleted
        remaining = await db_session.execute(
            select(MCPAgentJob).filter_by(
                project_id=project.id
            ).filter(
                MCPAgentJob.status.in_(["waiting", "preparing"])
            )
        )
        assert len(remaining.scalars().all()) == 0


# ==========================================
# ERROR CASE TESTS
# ==========================================

@pytest.mark.asyncio
class TestStagingCancellationErrors:
    """Error case tests for staging cancellation"""

    async def test_cancel_non_existent_project(
        self, async_client, db_session
    ):
        """
        Test 15: Cancel non-existent project
        """
        # Arrange
        fake_project_id = str(uuid4())

        # Act
        response = await async_client.post(
            f"/api/projects/{fake_project_id}/cancel-staging"
        )

        # Assert
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["error"].lower()


    async def test_cancel_without_authentication(
        self, test_app, db_session, project_with_staged_agents
    ):
        """
        Test 16: Cancel without permission (authentication)
        """
        # Arrange
        project = project_with_staged_agents["project"]

        # Create client WITHOUT authentication
        async with AsyncClient(app=test_app, base_url="http://test") as client:
            # No Authorization header

            # Act
            response = await client.post(
                f"/api/projects/{project.id}/cancel-staging"
            )

            # Assert
            assert response.status_code == 401
            data = response.json()
            assert "authentication" in data["error"].lower() or \
                   "unauthorized" in data["error"].lower()


# ==========================================
# MULTI-TENANT ISOLATION TESTS
# ==========================================

@pytest.mark.asyncio
class TestStagingCancellationMultiTenant:
    """Multi-tenant isolation tests"""

    async def test_cannot_cancel_other_tenant_staging(
        self, async_client, db_session
    ):
        """
        Test 20: Cannot cancel other tenant's staging
        """
        # Arrange: Create Tenant A and Tenant B projects
        tenant_a = f"tk_tenant_a_{uuid4().hex[:8]}"
        tenant_b = f"tk_tenant_b_{uuid4().hex[:8]}"

        # Tenant B's project with agents
        project_b = Project(
            id=str(uuid4()),
            name="Tenant B Project",
            tenant_key=tenant_b,
            status="active"
        )
        db_session.add(project_b)

        # Tenant B's agents
        for i in range(5):
            agent = MCPAgentJob(
                job_id=str(uuid4()),
                tenant_key=tenant_b,
                project_id=project_b.id,
                agent_type=f"agent-{i}",
                mission="Mission",
                status="waiting",
                messages=[]
            )
            db_session.add(agent)

        await db_session.commit()

        # Configure client as Tenant A
        async_client.headers["X-Tenant-Key"] = tenant_a

        # Act: Tenant A attempts to cancel Tenant B's project
        response = await async_client.post(
            f"/api/projects/{project_b.id}/cancel-staging"
        )

        # Assert: 404 (project not visible)
        assert response.status_code == 404

        # Assert: NO agents deleted
        remaining = await db_session.execute(
            select(MCPAgentJob).filter_by(
                project_id=project_b.id,
                tenant_key=tenant_b,
                status="waiting"
            )
        )
        assert len(remaining.scalars().all()) == 5  # All preserved


# ==========================================
# RACE CONDITION TESTS
# ==========================================

@pytest.mark.asyncio
class TestStagingCancellationRaceConditions:
    """Race condition tests"""

    async def test_user_clicks_launch_and_cancel_simultaneously(
        self, async_client, db_session, project_with_staged_agents
    ):
        """
        Test 24: User clicks launch + cancel simultaneously
        """
        # Arrange
        project = project_with_staged_agents["project"]
        agents = project_with_staged_agents["agents"]
        backend_agent = agents[0]

        # Act: Concurrent requests
        import asyncio

        launch_task = asyncio.create_task(
            async_client.post(
                f"/api/agents/{backend_agent.job_id}/launch"
            )
        )

        cancel_task = asyncio.create_task(
            async_client.post(
                f"/api/projects/{project.id}/cancel-staging"
            )
        )

        results = await asyncio.gather(
            launch_task,
            cancel_task,
            return_exceptions=True
        )

        # Assert: No exceptions (both operations succeed or fail gracefully)
        for result in results:
            assert not isinstance(result, Exception)

        # Assert: Database in consistent state
        remaining = await db_session.execute(
            select(MCPAgentJob).filter_by(
                project_id=project.id,
                status="waiting"
            )
        )
        remaining_count = len(remaining.scalars().all())

        # Either launch won (1 active, 4 deleted) or cancel won (0 waiting)
        assert remaining_count in [0, 4]


# ==========================================
# WEBSOCKET INTEGRATION TESTS
# ==========================================

@pytest.mark.asyncio
class TestStagingCancellationWebSocket:
    """WebSocket integration tests"""

    async def test_agent_deletion_events_broadcast(
        self, async_client, db_session, project_with_staged_agents, mock_websocket
    ):
        """
        Test 28: Agent deletion events broadcast correctly
        """
        # Arrange
        project = project_with_staged_agents["project"]
        tenant_key = project_with_staged_agents["tenant_key"]

        # Act
        response = await async_client.post(
            f"/api/projects/{project.id}/cancel-staging"
        )

        # Assert: WebSocket broadcast called
        assert mock_websocket.broadcast_to_tenant.called

        # Assert: Event structure validation
        calls = mock_websocket.broadcast_to_tenant.call_args_list

        for call in calls:
            assert call.kwargs["tenant_key"] == tenant_key
            assert call.kwargs["event_type"] in [
                "agent:deleted",
                "project:staging_cancelled"
            ]

            if call.kwargs["event_type"] == "agent:deleted":
                data = call.kwargs["data"]
                assert "agent" in data
                assert "job_id" in data["agent"]
                assert "agent_type" in data["agent"]
```

---

## Coverage Goals

### Test Coverage Targets

| Component | Target Coverage | Tests |
|-----------|----------------|-------|
| API Endpoint (`/cancel-staging`) | 90%+ | 32 tests |
| Database Operations (DELETE queries) | 100% | 15 tests |
| Multi-Tenant Isolation | 100% | 4 tests |
| WebSocket Broadcasting | 85%+ | 5 tests |
| Error Handling | 95%+ | 5 tests |
| Race Conditions | 80%+ | 4 tests |

### Critical Paths (Must Test)

1. ✅ **Delete spawned agents** (status='waiting', 'preparing')
2. ✅ **Preserve launched agents** (status='active', 'working')
3. ✅ **Preserve orchestrator** (agent_type='orchestrator')
4. ✅ **Multi-tenant isolation** (tenant_key filtering)
5. ✅ **WebSocket event broadcasting**
6. ✅ **Transaction atomicity** (all-or-nothing deletion)
7. ✅ **Idempotency** (repeated cancellations safe)
8. ✅ **Race condition handling** (concurrent launch/cancel)

### Test Execution Plan

**Phase 1: Happy Path** (1 hour)
- Tests 1-8: Core functionality validation
- Run: `pytest tests/integration/test_staging_cancellation.py::TestStagingCancellationHappyPath`

**Phase 2: Edge Cases** (1 hour)
- Tests 9-14: Boundary conditions
- Run: `pytest tests/integration/test_staging_cancellation.py::TestStagingCancellationEdgeCases`

**Phase 3: Error Cases** (45 min)
- Tests 15-19: Failure scenarios
- Run: `pytest tests/integration/test_staging_cancellation.py::TestStagingCancellationErrors`

**Phase 4: Multi-Tenant** (30 min)
- Tests 20-23: Security validation
- Run: `pytest tests/integration/test_staging_cancellation.py::TestStagingCancellationMultiTenant`

**Phase 5: Race Conditions** (1 hour)
- Tests 24-27: Concurrency testing
- Run: `pytest tests/integration/test_staging_cancellation.py::TestStagingCancellationRaceConditions`

**Phase 6: WebSocket** (45 min)
- Tests 28-32: Real-time events
- Run: `pytest tests/integration/test_staging_cancellation.py::TestStagingCancellationWebSocket`

**Total Estimated Time**: 5 hours

---

## Summary

**Total Tests Designed**: 32 comprehensive integration tests

**Test Breakdown**:
- Happy Path: 8 tests
- Edge Cases: 6 tests
- Error Cases: 5 tests
- Multi-Tenant Isolation: 4 tests
- Race Conditions: 4 tests
- WebSocket Integration: 5 tests

**Key Deliverables**:
1. ✅ Complete test scenarios with expected outcomes
2. ✅ Integration test pseudocode structure
3. ✅ Edge cases identified and documented
4. ✅ Performance considerations (100+ agents)
5. ✅ Multi-tenant security validation
6. ✅ Race condition handling strategies
7. ✅ WebSocket event verification
8. ✅ Database optimization guidance

**Next Steps**:
1. Architect finalizes mission clearing behavior (clear vs. preserve)
2. Implementation agent develops API endpoint
3. Backend Integration Tester writes and runs these tests
4. Iterate on test failures and edge cases
5. Verify 90%+ test coverage achieved

---

**Document Version**: 1.0
**Last Updated**: 2025-11-06
**Review Status**: Ready for Architect Review
