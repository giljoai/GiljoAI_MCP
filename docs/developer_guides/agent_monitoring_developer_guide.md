# Agent Monitoring & Graceful Cancellation - Developer Guide

**Version**: 3.1.1
**Date**: 2025-11-06
**Last Updated**: 2025-01-05 (Harmonized)
**Handover**: 0107
**Harmonization Status**: ✅ Aligned with codebase

---

## Quick Links to Harmonized Documents

- **[Simple_Vision.md](../../handovers/Simple_Vision.md)** - User journey & agent monitoring
- **[start_to_finish_agent_FLOW.md](../../handovers/start_to_finish_agent_FLOW.md)** - Agent execution flow

**Agent Job Status** (verified):
- Initial: **"waiting"** → active → working → complete/failed/blocked
- Monitoring applies during "active" and "working" states

**Agent Templates** (6 default):
- orchestrator, implementer, tester, analyzer, reviewer, documenter

---

This guide provides comprehensive technical documentation for the agent monitoring and graceful cancellation system implemented in Handover 0107. It covers architecture, database schema, API endpoints, MCP tools, background tasks, and testing strategies.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Database Schema](#database-schema)
3. [MCP Tools](#mcp-tools)
4. [API Endpoints](#api-endpoints)
5. [Background Monitoring](#background-monitoring)
6. [WebSocket Events](#websocket-events)
7. [Multi-Tenant Considerations](#multi-tenant-considerations)
8. [Testing Strategy](#testing-strategy)
9. [Implementation Details](#implementation-details)
10. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

### Design Philosophy

**Contextual Check-Ins (Not Timer-Based)**:
- Agents check in at natural workflow breaks (after todos, phases, before long tasks)
- More responsive than fixed timers (may check in <2 min)
- Aligns with how agents naturally work
- Most tasks complete in <5 minutes, ensuring regular updates

**Passive Monitoring (Not Active Control)**:
- System tracks agent activity but doesn't control external terminals
- Detects zombie agents via stale timestamps
- Warns users but doesn't auto-fail (user decides)
- Manual controls for stuck jobs

### Key Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Agent (External Terminal)                │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 1. Acknowledge Job                                    │  │
│  │ 2. Work on Task                                       │  │
│  │ 3. Check In After Todo ──> report_progress()         │  │
│  │ 4. Check for Commands ──> receive_messages()         │  │
│  │ 5. Handle Cancel Command (if received)               │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      GiljoAI MCP Server                      │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Database: last_progress_at, last_message_check_at     │  │
│  │ MCP Tools: report_progress, receive_messages          │  │
│  │ API Endpoints: cancel, force-fail, health             │  │
│  │ Background Task: monitor_agent_health (5 min)         │  │
│  │ WebSocket: job:progress_update, job:stale_warning     │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      Dashboard (Vue 3)                       │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Health Indicators: Green / Orange / Grey              │  │
│  │ Cancel Button: Graceful cancellation request          │  │
│  │ Force Stop: Manual intervention (last resort)         │  │
│  │ Real-Time Updates: WebSocket subscriptions            │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Database Schema

### New Fields (Migration 0107)

**File**: `migrations/versions/0107_agent_monitoring.py`

```python
def upgrade():
    # Add activity tracking timestamps
    op.add_column('mcp_agent_jobs',
        sa.Column('last_progress_at', sa.DateTime(timezone=True), nullable=True,
                  comment='Last time agent reported progress'))

    op.add_column('mcp_agent_jobs',
        sa.Column('last_message_check_at', sa.DateTime(timezone=True), nullable=True,
                  comment='Last time agent checked for messages'))

    # Extend status enum to include "cancelling"
    op.execute("""
        ALTER TABLE mcp_agent_jobs
        DROP CONSTRAINT IF EXISTS mcp_agent_jobs_status_check;

        ALTER TABLE mcp_agent_jobs
        ADD CONSTRAINT mcp_agent_jobs_status_check
        CHECK (status IN (
            'waiting',
            'preparing',
            'active',
            'working',
            'cancelling',  -- NEW
            'review',
            'complete',
            'failed',
            'blocked'
        ));
    """)
```

### SQLAlchemy Model

**File**: `src/giljo_mcp/models.py`

```python
class MCPAgentJob(Base):
    __tablename__ = 'mcp_agent_jobs'

    # ... existing fields ...

    # NEW: Activity tracking (Handover 0107)
    last_progress_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last time agent reported progress"
    )

    last_message_check_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last time agent checked for messages"
    )

    # Updated status field (includes 'cancelling')
    status = Column(
        String(50),
        default='waiting'
        # Valid: waiting, preparing, active, working, cancelling, review, complete, failed, blocked
    )
```

### Database Indexes

**Recommended** (for query performance):

```sql
-- Index for stale agent detection query
CREATE INDEX idx_agent_jobs_activity
ON mcp_agent_jobs(tenant_key, status, last_progress_at)
WHERE status IN ('active', 'working');

-- Index for message checking
CREATE INDEX idx_agent_jobs_message_check
ON mcp_agent_jobs(agent_id, last_message_check_at);
```

---

## MCP Tools

### Updated `report_progress()` Tool

**File**: `src/giljo_mcp/tools/agent_status.py`

```python
@mcp_tool(name="report_progress")
async def report_progress(
    job_id: str,
    progress: dict,
    tenant_key: str
) -> dict:
    """
    Report agent progress and update activity timestamp.

    Args:
        job_id: Job ID
        progress: {
            "task": "Current task description",
            "percent": 0-100,
            "todos_completed": int,
            "todos_remaining": int,
            "context_tokens_estimate": int
        }
        tenant_key: Tenant key

    Returns:
        {"success": True, "job_id": str}

    Side Effects:
        - Updates job.last_progress_at to current UTC time
        - Stores progress in job.meta_data['latest_progress']
        - Broadcasts job:progress_update WebSocket event
    """
    job = await get_job(job_id, tenant_key)

    # Update activity timestamp (CRITICAL for health monitoring)
    job.last_progress_at = datetime.now(timezone.utc)

    # Store progress in job metadata
    job.meta_data = job.meta_data or {}
    job.meta_data['latest_progress'] = progress
    job.updated_at = datetime.now(timezone.utc)

    await db.commit()

    # Broadcast to UI for real-time updates
    await broadcast_websocket_event({
        "event": "job:progress_update",
        "job_id": job_id,
        "progress": progress,
        "last_progress_at": job.last_progress_at.isoformat()
    })

    return {"success": True, "job_id": job_id}
```

### Updated `receive_messages()` Tool

**File**: `src/giljo_mcp/tools/agent_messaging.py`

```python
@mcp_tool(name="receive_messages")
async def receive_messages(
    agent_id: str,
    limit: int = 10,
    tenant_key: str = None
) -> dict:
    """
    Retrieve messages for agent and update message check timestamp.

    Args:
        agent_id: Agent ID (e.g., "implementer")
        limit: Maximum number of messages to retrieve
        tenant_key: Tenant key for multi-tenant isolation

    Returns:
        {
            "success": True,
            "messages": [
                {
                    "type": "cancel" | "pause" | "resume" | "instruction",
                    "reason": str,
                    "timestamp": str (ISO 8601),
                    "priority": "normal" | "high" | "critical"
                },
                ...
            ],
            "count": int
        }

    Side Effects:
        - Updates job.last_message_check_at to current UTC time
        - Messages marked as read (if applicable)
    """
    # Update last check timestamp (shows agent is responsive)
    job = await get_job_by_agent_id(agent_id, tenant_key)
    if job:
        job.last_message_check_at = datetime.now(timezone.utc)
        await db.commit()

    # Retrieve messages from communication queue
    messages = await get_messages_for_agent(agent_id, limit, tenant_key)

    return {
        "success": True,
        "messages": messages,
        "count": len(messages)
    }
```

### Agent Cancellation Manager

**File**: `src/giljo_mcp/agent_job_manager.py`

```python
async def request_job_cancellation(
    job_id: str,
    reason: str,
    tenant_key: str
) -> dict:
    """
    Request graceful job cancellation via message queue.

    Flow:
    1. Mark job as "cancelling"
    2. Send cancel message to agent
    3. Agent reads message on next check-in
    4. Agent stops work and calls complete_job()

    Args:
        job_id: Job ID to cancel
        reason: Human-readable reason for cancellation
        tenant_key: Tenant key

    Returns:
        {
            "success": True,
            "job_id": str,
            "status": "cancelling",
            "message": str
        }
    """
    job = await get_job(job_id, tenant_key)

    # Update status to "cancelling"
    job.status = "cancelling"
    await db.commit()

    # Send cancel message to agent
    await send_message(
        to_agent=job.agent_id,
        message={
            "type": "cancel",
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat()
        },
        priority="critical",
        tenant_key=tenant_key
    )

    # Broadcast status change to UI
    await broadcast_job_status_change(job_id, "cancelling")

    return {
        "success": True,
        "job_id": job_id,
        "status": "cancelling",
        "message": "Cancel request sent - agent will stop on next check-in"
    }


async def force_fail_job(
    job_id: str,
    reason: str,
    tenant_key: str
) -> dict:
    """
    Forcefully mark job as failed (for unresponsive agents).

    Use when agent doesn't respond to cancel request after 5+ minutes.

    WARNING: This does NOT terminate the external agent process.
    User must manually close the terminal.

    Args:
        job_id: Job ID to force fail
        reason: Human-readable reason
        tenant_key: Tenant key

    Returns:
        {"success": True, "job": dict}
    """
    job = await fail_job(
        job_id=job_id,
        error=f"Force failed by user: {reason}",
        tenant_key=tenant_key
    )

    return {"success": True, "job": job}
```

---

## API Endpoints

**File**: `api/endpoints/agent_jobs.py`

### POST `/api/v1/jobs/{job_id}/cancel`

Graceful cancellation request.

**Request**:
```json
{
  "reason": "User requested cancellation"
}
```

**Response**:
```json
{
  "success": true,
  "job_id": "abc-123",
  "status": "cancelling",
  "message": "Cancel request sent - agent will stop on next check-in"
}
```

**Implementation**:
```python
@router.post("/jobs/{job_id}/cancel")
async def cancel_job(
    job_id: str,
    cancellation: JobCancellationRequest,
    current_user = Depends(get_current_user)
):
    """Request graceful job cancellation."""
    result = await request_job_cancellation(
        job_id=job_id,
        reason=cancellation.reason,
        tenant_key=current_user.tenant_key
    )
    return result
```

### POST `/api/v1/jobs/{job_id}/force-fail`

Forcefully mark job as failed.

**Request**:
```json
{
  "reason": "Agent unresponsive"
}
```

**Response**:
```json
{
  "success": true,
  "job": {
    "id": "abc-123",
    "status": "failed",
    "error": "Force failed by user: Agent unresponsive"
  }
}
```

### GET `/api/v1/jobs/{job_id}/health`

Get agent health metrics.

**Response**:
```json
{
  "job_id": "abc-123",
  "status": "active",
  "last_progress_at": "2025-11-06T10:30:00Z",
  "last_message_check_at": "2025-11-06T10:31:00Z",
  "minutes_since_progress": 3,
  "is_stale": false
}
```

**Implementation**:
```python
@router.get("/jobs/{job_id}/health")
async def get_job_health(
    job_id: str,
    current_user = Depends(get_current_user)
):
    """Get agent health metrics."""
    job = await get_job(job_id, current_user.tenant_key)

    now = datetime.now(timezone.utc)

    health = {
        "job_id": job_id,
        "status": job.status,
        "last_progress_at": job.last_progress_at.isoformat() if job.last_progress_at else None,
        "last_message_check_at": job.last_message_check_at.isoformat() if job.last_message_check_at else None,
        "minutes_since_progress": None,
        "is_stale": False
    }

    if job.last_progress_at:
        time_since = now - job.last_progress_at
        minutes_since = int(time_since.total_seconds() / 60)
        health["minutes_since_progress"] = minutes_since
        health["is_stale"] = minutes_since > 10

    return health
```

---

## Background Monitoring

### Monitor Task

**File**: `src/giljo_mcp/job_monitoring.py` (NEW)

```python
import asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from src.giljo_mcp.models import MCPAgentJob
from src.giljo_mcp.database import get_db
from api.websocket import broadcast_websocket_event

async def monitor_agent_health():
    """
    Background task to detect stale agents.
    Runs every 5 minutes.

    Detects agents with no progress report in last 10 minutes.
    Broadcasts stale warnings but DOES NOT auto-fail jobs.
    """
    while True:
        try:
            async with get_db() as db:
                # Find active jobs without progress in last 10 minutes
                stale_threshold = datetime.now(timezone.utc) - timedelta(minutes=10)

                result = await db.execute(
                    select(MCPAgentJob).where(
                        MCPAgentJob.status.in_(['active', 'working']),
                        MCPAgentJob.last_progress_at < stale_threshold
                    )
                )
                stale_jobs = result.scalars().all()

                for job in stale_jobs:
                    # Calculate time since last update
                    time_since_update = datetime.now(timezone.utc) - job.last_progress_at
                    minutes_stale = int(time_since_update.total_seconds() / 60)

                    # Broadcast stale warning (don't auto-fail)
                    await broadcast_websocket_event({
                        "event": "job:stale_warning",
                        "job_id": job.id,
                        "agent_id": job.agent_id,
                        "minutes_stale": minutes_stale,
                        "message": f"Agent hasn't reported progress in {minutes_stale} minutes"
                    })

                    # Log for monitoring
                    logger.warning(f"[HEALTH] Stale job detected: {job.id} ({minutes_stale}m)")

        except Exception as e:
            logger.error(f"[HEALTH] Monitor error: {e}", exc_info=True)

        # Check every 5 minutes
        await asyncio.sleep(300)
```

### Startup Integration

**File**: `api/run_api.py`

```python
@app.on_event("startup")
async def start_health_monitor():
    """Start background health monitoring task on application startup."""
    asyncio.create_task(monitor_agent_health())
    logger.info("[STARTUP] Agent health monitor started")
```

### Why NOT Auto-Fail?

- Agents might be legitimately working on long tasks (10+ min)
- Network blips shouldn't kill jobs
- User knows best if agent is actually stuck
- Manual control better than false positives

---

## WebSocket Events

### `job:progress_update`

Emitted when agent reports progress.

```json
{
  "event": "job:progress_update",
  "job_id": "abc-123",
  "progress": {
    "task": "Implementing user authentication",
    "percent": 45,
    "todos_completed": 3,
    "todos_remaining": 5,
    "context_tokens_estimate": 12000
  },
  "last_progress_at": "2025-11-06T10:30:00Z"
}
```

### `job:stale_warning`

Emitted by background monitor when agent goes stale.

```json
{
  "event": "job:stale_warning",
  "job_id": "abc-123",
  "agent_id": "implementer",
  "minutes_stale": 15,
  "message": "Agent hasn't reported progress in 15 minutes"
}
```

### `job:status_changed`

Emitted when job status changes (including to "cancelling").

```json
{
  "event": "job:status_changed",
  "job_id": "abc-123",
  "old_status": "active",
  "new_status": "cancelling",
  "timestamp": "2025-11-06T10:35:00Z"
}
```

### `job:completed`

Emitted when job completes (including cancelled jobs).

```json
{
  "event": "job:completed",
  "job_id": "abc-123",
  "status": "complete",
  "result": {
    "status": "cancelled",
    "reason": "User requested cancellation",
    "partial_work": {
      "files_modified": ["api/auth.py", "tests/test_auth.py"],
      "todos_completed": 3,
      "todos_remaining": 5
    }
  }
}
```

---

## Multi-Tenant Considerations

### Tenant Isolation

**All operations enforce tenant_key filtering**:

```python
# Good - tenant isolated
job = await db.execute(
    select(MCPAgentJob).where(
        MCPAgentJob.id == job_id,
        MCPAgentJob.tenant_key == tenant_key
    )
)

# Bad - cross-tenant leak risk
job = await db.execute(
    select(MCPAgentJob).where(
        MCPAgentJob.id == job_id
    )
)
```

### Background Monitor

Monitor queries include tenant isolation:

```python
# Monitor only active jobs for this tenant
stale_jobs = await db.execute(
    select(MCPAgentJob).where(
        MCPAgentJob.tenant_key == tenant_key,  # Tenant isolation
        MCPAgentJob.status.in_(['active', 'working']),
        MCPAgentJob.last_progress_at < stale_threshold
    )
)
```

### WebSocket Events

Events include tenant context for filtering:

```python
await broadcast_websocket_event({
    "event": "job:stale_warning",
    "tenant_key": job.tenant_key,  # For client-side filtering
    "job_id": job.id,
    "minutes_stale": 15
})
```

---

## Testing Strategy

### Unit Tests

**Test File**: `tests/test_agent_monitoring.py`

```python
async def test_report_progress_updates_timestamp():
    """Verify report_progress updates last_progress_at."""
    job = await create_test_job()

    await report_progress(
        job_id=job.id,
        progress={"task": "Test", "percent": 50},
        tenant_key=job.tenant_key
    )

    updated_job = await get_job(job.id, job.tenant_key)
    assert updated_job.last_progress_at is not None
    assert updated_job.last_progress_at > job.created_at


async def test_receive_messages_updates_check_timestamp():
    """Verify receive_messages updates last_message_check_at."""
    job = await create_test_job()

    await receive_messages(
        agent_id=job.agent_id,
        limit=10,
        tenant_key=job.tenant_key
    )

    updated_job = await get_job(job.id, job.tenant_key)
    assert updated_job.last_message_check_at is not None


async def test_cancel_job_marks_status_cancelling():
    """Verify cancel request sets status to 'cancelling'."""
    job = await create_test_job(status="active")

    result = await request_job_cancellation(
        job_id=job.id,
        reason="Test cancellation",
        tenant_key=job.tenant_key
    )

    assert result["status"] == "cancelling"
    updated_job = await get_job(job.id, job.tenant_key)
    assert updated_job.status == "cancelling"


async def test_force_fail_marks_job_failed():
    """Verify force fail sets status to 'failed'."""
    job = await create_test_job(status="cancelling")

    result = await force_fail_job(
        job_id=job.id,
        reason="Unresponsive",
        tenant_key=job.tenant_key
    )

    updated_job = await get_job(job.id, job.tenant_key)
    assert updated_job.status == "failed"
    assert "Force failed" in updated_job.error
```

### Integration Tests

**Test File**: `tests/test_agent_monitoring_integration.py`

```python
async def test_stale_agent_detection():
    """Verify background monitor detects stale agents."""
    # Create job with old timestamp
    job = await create_test_job(status="active")
    job.last_progress_at = datetime.now(timezone.utc) - timedelta(minutes=15)
    await db.commit()

    # Run monitor (single iteration)
    await monitor_agent_health_once()

    # Verify stale warning broadcast
    events = get_websocket_events()
    assert any(e["event"] == "job:stale_warning" for e in events)


async def test_graceful_cancellation_flow():
    """Test end-to-end graceful cancellation."""
    # 1. Create active job
    job = await create_test_job(status="active")

    # 2. Request cancellation
    result = await request_job_cancellation(
        job_id=job.id,
        reason="Test",
        tenant_key=job.tenant_key
    )
    assert result["status"] == "cancelling"

    # 3. Agent receives cancel message
    messages = await receive_messages(
        agent_id=job.agent_id,
        tenant_key=job.tenant_key
    )
    assert any(m["type"] == "cancel" for m in messages["messages"])

    # 4. Agent completes with cancelled status
    await complete_job(
        job_id=job.id,
        result={"status": "cancelled", "reason": "User requested cancellation"},
        tenant_key=job.tenant_key
    )

    # 5. Verify final state
    updated_job = await get_job(job.id, job.tenant_key)
    assert updated_job.status == "complete"
```

### API Tests

**Test File**: `tests/api/test_agent_monitoring_endpoints.py`

```python
async def test_cancel_endpoint(test_client):
    """Test POST /api/v1/jobs/{job_id}/cancel."""
    job = await create_test_job(status="active")

    response = await test_client.post(
        f"/api/v1/jobs/{job.id}/cancel",
        json={"reason": "Test cancellation"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "cancelling"


async def test_health_endpoint(test_client):
    """Test GET /api/v1/jobs/{job_id}/health."""
    job = await create_test_job(status="active")
    job.last_progress_at = datetime.now(timezone.utc) - timedelta(minutes=3)
    await db.commit()

    response = await test_client.get(f"/api/v1/jobs/{job.id}/health")

    assert response.status_code == 200
    data = response.json()
    assert data["minutes_since_progress"] == 3
    assert data["is_stale"] == False


async def test_tenant_isolation_in_cancel(test_client):
    """Verify tenant isolation in cancel endpoint."""
    job_tenant_a = await create_test_job(tenant_key="tenant_a", status="active")

    # Try to cancel from tenant_b (should fail)
    response = await test_client.post(
        f"/api/v1/jobs/{job_tenant_a.id}/cancel",
        json={"reason": "Test"},
        headers={"Authorization": f"Bearer {get_token_for_tenant('tenant_b')}"}
    )

    assert response.status_code == 404  # Job not found for this tenant
```

---

## Implementation Details

### Check-In Protocol in Templates

**Template Section** (added to all agent templates):

```markdown
## CHECK-IN PROTOCOL (Handover 0107)

After completing each milestone, perform check-in routine:

### Contextual Check-In Points

✅ After completing a todo item
✅ After finishing a major phase/operation
✅ Before starting a long-running task (>5 minutes)
✅ When waiting for user input

❌ NOT timer-based (every 2 minutes)
✅ Natural break points in workflow

### Check-In Routine

1. **Report Progress**:
   report_progress(job_id="{job_id}", progress={...})

2. **Check for Commands**:
   messages = receive_messages(agent_id="{agent_id}")

3. **Handle Commands**:
   if message.type == "cancel":
       cleanup()
       complete_job(job_id="{job_id}", result={"status": "cancelled"})
       exit()
```

### Frontend Health Indicator Logic

**Component**: `frontend/src/components/projects/AgentCardEnhanced.vue`

```vue
<script>
computed: {
  minutesSinceLastUpdate() {
    if (!this.agent.last_progress_at) return null
    const lastUpdate = new Date(this.agent.last_progress_at)
    const now = new Date()
    return Math.floor((now - lastUpdate) / 60000)
  },

  isStale() {
    return this.minutesSinceLastUpdate > 10 &&
           ['active', 'working'].includes(this.status)
  },

  healthColor() {
    if (this.isStale) return 'warning'
    if (['active', 'working'].includes(this.status)) return 'success'
    if (this.status === 'cancelling') return 'warning'
    return 'grey'
  }
}
</script>
```

---

## Troubleshooting

### Monitor Not Running

**Symptoms**: No stale warnings appearing

**Check**:
```bash
# Check application logs
tail -f logs/app.log | grep HEALTH

# Look for startup message
grep "Agent health monitor started" logs/app.log
```

**Fix**:
1. Verify `start_health_monitor()` called in `app.on_event("startup")`
2. Check for exceptions in monitor task
3. Restart application

### Timestamps Not Updating

**Symptoms**: `last_progress_at` remains NULL

**Check**:
```sql
SELECT id, agent_id, status, last_progress_at, last_message_check_at
FROM mcp_agent_jobs
WHERE status IN ('active', 'working');
```

**Fix**:
1. Verify agent calling `report_progress()` correctly
2. Check MCP tool registration
3. Verify database migration applied

### Cancel Not Working

**Symptoms**: Agent doesn't stop after cancel request

**Check**:
1. Agent template includes check-in protocol?
2. Agent calling `receive_messages()` regularly?
3. Messages in communication queue?

**Debug Query**:
```sql
SELECT * FROM agent_communication_queue
WHERE to_agent = 'implementer'
AND tenant_key = 'tenant_key_here'
ORDER BY created_at DESC;
```

---

## Related Documentation

- **User Guide**: [docs/user_guides/agent_monitoring_guide.md](../user_guides/agent_monitoring_guide.md)
- **Handover Document**: [handovers/completed/0107_agent_monitoring_and_graceful_cancellation-C.md](../../handovers/completed/0107_agent_monitoring_and_graceful_cancellation-C.md)
- **Template Seeder**: [src/giljo_mcp/template_seeder.py](../../src/giljo_mcp/template_seeder.py)
- **API Endpoints**: [api/endpoints/agent_jobs.py](../../api/endpoints/agent_jobs.py)

---

## Version History

- **v3.1.1** (2025-11-06): Initial implementation (Handover 0107)
- Contextual check-in protocol
- Passive health monitoring
- Graceful cancellation system
- Force stop capability
