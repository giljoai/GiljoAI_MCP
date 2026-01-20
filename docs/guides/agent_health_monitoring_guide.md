# Agent Health Monitoring System Developer Guide

**Handover 0106 Implementation**

## Overview

Production-grade background health monitoring service for detecting and responding to agent job health issues.

**Status**: ✅ IMPLEMENTED (TDD Complete)

**Coverage**: 30+ unit tests, 10+ integration tests

## Components

### 1. Health Configuration (`health_config.py`)

```python
from src.giljo_mcp.monitoring import HealthCheckConfig

config = HealthCheckConfig(
    waiting_timeout_minutes=2,        # Jobs stuck in 'waiting'
    active_no_progress_minutes=5,     # Active jobs without progress
    heartbeat_timeout_minutes=10,     # Default silence timeout
    scan_interval_seconds=300,        # 5 minutes
    auto_fail_on_timeout=False,       # Conservative default
    notify_orchestrator=True,
    timeout_overrides={
        "orchestrator": 15,  # Orchestrators get more time
        "implementer": 10,
        "tester": 8,
        "reviewer": 6,
        "documenter": 5,
        "analyzer": 5
    }
)
```

**Agent-Type-Specific Timeouts**:
- Orchestrators: 15 minutes (complex orchestration needs time)
- Implementers: 10 minutes (coding tasks)
- Testers: 8 minutes (test execution)
- Reviewers: 6 minutes (code review)
- Analyzers/Documenters: 5 minutes (faster tasks)

### 2. Health Monitor (`agent_health_monitor.py`)

```python
from src.giljo_mcp.monitoring import AgentHealthMonitor
from src.giljo_mcp.database import DatabaseManager
from api.websocket import WebSocketManager

# Initialize
db_manager = DatabaseManager()
ws_manager = WebSocketManager()

monitor = AgentHealthMonitor(db_manager, ws_manager, config)

# Start background monitoring
await monitor.start()

# Stop gracefully
await monitor.stop()
```

### 3. Detection Algorithms

**1. Waiting Timeout Detection**
- **Trigger**: Jobs stuck in 'waiting' state
- **Threshold**: 2 minutes (default)
- **Health State**: `critical`
- **Issue**: Agent never acknowledged job
- **Action**: Check if agent received job, manual intervention required

**2. Stalled Job Detection**
- **Trigger**: Active jobs without progress updates
- **Thresholds**:
  - 5-7 minutes: `warning`
  - 7-10 minutes: `critical`
  - >10 minutes: `timeout`
- **Issue**: Agent stopped reporting progress
- **Action**: Check agent logs, may need restart

**3. Heartbeat Failure Detection**
- **Trigger**: Complete silence (no activity)
- **Threshold**: Agent-type-specific (5-15 minutes)
- **Health State**: `timeout`
- **Issue**: Agent completely unresponsive
- **Action**: Auto-fail or manual intervention

### 4. Database Schema

**New Fields in `mcp_agent_jobs`**:

```sql
-- Health monitoring fields (Handover 0106)
last_health_check TIMESTAMP WITH TIME ZONE NULL,
health_status VARCHAR(20) DEFAULT 'unknown' NOT NULL,
health_failure_count INTEGER DEFAULT 0 NOT NULL,

-- Constraints
CONSTRAINT ck_mcp_agent_job_health_status
    CHECK (health_status IN ('unknown', 'healthy', 'warning', 'critical', 'timeout')),
CONSTRAINT ck_mcp_agent_job_health_failure_count
    CHECK (health_failure_count >= 0)
```

**Index**:
```sql
CREATE INDEX idx_mcp_agent_jobs_health_status
    ON mcp_agent_jobs (tenant_key, health_status);
```

**Migration**: `migrations/versions/20251105_0106b_add_health_fields.py`

### 5. WebSocket Events

**Health Alert Event** (`agent:health_alert`):
```json
{
  "type": "agent:health_alert",
  "data": {
    "job_id": "uuid",
    "agent_type": "implementer",
    "health_state": "warning",
    "issue_description": "No progress for 6.2 minutes",
    "minutes_since_update": 6.2,
    "recommended_action": "Check agent logs, may need manual restart"
  },
  "timestamp": "2025-11-05T12:34:56.789Z"
}
```

**Auto-Fail Event** (`agent:auto_failed`):
```json
{
  "type": "agent:auto_failed",
  "data": {
    "job_id": "uuid",
    "agent_type": "implementer",
    "reason": "Complete silence for 15.3 minutes (timeout: 10m)",
    "auto_failed": true
  },
  "timestamp": "2025-11-05T12:34:56.789Z"
}
```

## Usage

### Basic Setup

```python
from src.giljo_mcp.monitoring import AgentHealthMonitor, HealthCheckConfig
from src.giljo_mcp.database import DatabaseManager
from api.websocket import WebSocketManager

# Create manager instances
db_manager = DatabaseManager()
ws_manager = WebSocketManager()

# Configure monitoring
config = HealthCheckConfig(
    scan_interval_seconds=300,  # 5 minutes
    auto_fail_on_timeout=False  # Conservative
)

# Create and start monitor
monitor = AgentHealthMonitor(db_manager, ws_manager, config)
await monitor.start()
```

### Integration with Startup

Add to `startup.py`:

```python
from src.giljo_mcp.monitoring import AgentHealthMonitor, HealthCheckConfig

async def start_health_monitoring(db_manager, ws_manager):
    """Start background health monitoring."""
    config = HealthCheckConfig(
        scan_interval_seconds=300,
        auto_fail_on_timeout=False
    )

    monitor = AgentHealthMonitor(db_manager, ws_manager, config)
    await monitor.start()

    return monitor

# In main startup flow:
health_monitor = await start_health_monitoring(db_manager, ws_manager)
```

### Configuration via `config.yaml`

Add to config.yaml:

```yaml
health_monitoring:
  enabled: true
  scan_interval_seconds: 300  # 5 minutes
  auto_fail_on_timeout: false
  waiting_timeout_minutes: 2
  active_no_progress_minutes: 5
  heartbeat_timeout_minutes: 10
  timeout_overrides:
    orchestrator: 15
    implementer: 10
    tester: 8
    reviewer: 6
    documenter: 5
    analyzer: 5
```

### Progress Tracking Integration

Agents should update `job_metadata.last_progress_update`:

```python
# When agent reports progress
job.job_metadata = {
    **job.job_metadata,
    "last_progress_update": datetime.now(timezone.utc).isoformat(),
    "progress_updates_count": job.job_metadata.get("progress_updates_count", 0) + 1
}

# Reset health status
job.health_status = "healthy"
job.health_failure_count = 0

session.commit()
```

## Testing

### Unit Tests

```bash
# Run all monitoring tests
pytest tests/unit/monitoring/test_agent_health_monitor.py -v

# Run specific test class
pytest tests/unit/monitoring/test_agent_health_monitor.py::TestAgentHealthMonitor -v

# Run integration tests
pytest tests/integration/test_health_monitoring_e2e.py -v
```

### Test Coverage

**Unit Tests (30+)**:
- Configuration dataclass tests
- Monitor lifecycle (start, stop, recovery)
- Detection algorithm tests (waiting, stalled, heartbeat)
- Agent-type-specific timeouts
- Health status escalation
- Auto-fail functionality
- Multi-tenant isolation
- Error recovery
- Progress/activity time extraction

**Integration Tests (10+)**:
- Full monitoring lifecycle
- E2E waiting timeout detection
- E2E stalled job detection
- E2E auto-fail on timeout
- Multiple tenant monitoring
- Healthy jobs not flagged
- Progressive health degradation
- Concurrent health checks
- Database error recovery
- Health status transitions

## Architecture Decisions

### 1. Background Task Pattern

**Why**: Non-blocking monitoring that doesn't interfere with agent execution.

**Implementation**:
```python
async def _monitoring_loop(self):
    while self.running:
        try:
            await self._run_health_check_cycle()
        except Exception as e:
            logger.error(f"Health check cycle failed: {e}", exc_info=True)

        await asyncio.sleep(self.config.scan_interval_seconds)
```

### 2. Three-Tier Escalation

**Why**: Gradual escalation prevents false positives while ensuring timely detection.

**Levels**:
- Warning (5-7 min): Early alert, no action
- Critical (7-10 min): Serious concern, notify orchestrator
- Timeout (>10 min): Auto-fail or manual intervention

### 3. Agent-Type-Specific Timeouts

**Why**: Different agent types have different execution characteristics.

**Orchestrators**: 15 minutes (complex planning needs time)
**Implementers**: 10 minutes (coding tasks)
**Testers**: 8 minutes (test execution)
**Others**: 5-6 minutes (faster tasks)

### 4. Conservative Auto-Fail Default

**Why**: Safety first - avoid prematurely killing jobs.

**Default**: `auto_fail_on_timeout=False`

**Operators** can enable auto-fail if confident in detection accuracy.

### 5. Multi-Tenant Isolation

**Why**: Security and data isolation in multi-tenant environments.

**Implementation**:
- All queries filter by `tenant_key`
- WebSocket broadcasts respect tenant boundaries
- Health checks run per-tenant

## Monitoring Loop Flow

```
1. Start monitoring loop
   ↓
2. Get all tenants from database
   ↓
3. For each tenant:
   ↓
   3a. Detect waiting timeouts
   ↓
   3b. Detect stalled jobs
   ↓
   3c. Detect heartbeat failures
   ↓
   3d. For each unhealthy job:
       - Update health_status
       - Increment health_failure_count
       - Update last_health_check
       - Auto-fail if configured
       - Broadcast WebSocket event
   ↓
4. Sleep for scan_interval_seconds
   ↓
5. Repeat (while running)
```

## Error Handling

**Monitor Continues After Errors**:
```python
try:
    await self._run_health_check_cycle()
except Exception as e:
    logger.error(f"Health check cycle failed: {e}", exc_info=True)
    # Monitor continues - don't crash on transient errors
```

**Graceful Shutdown**:
```python
async def stop(self):
    self.running = False
    if self._task:
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass  # Expected
```

## Performance Considerations

**Database Queries**:
- Indexed queries (`tenant_key`, `status`, `health_status`)
- Batch processing per tenant
- Efficient filtering in SQL (not in Python)

**Scan Interval**:
- Default: 5 minutes (good balance)
- Configurable for different environments
- Production: 5 minutes
- Development: 1-2 minutes for testing

**Resource Usage**:
- Lightweight background task
- Minimal CPU (sleep between scans)
- Database queries are efficient (indexed)

## Future Enhancements

**Potential additions** (not in current scope):

1. **Health History Tracking**: Store health events in database
2. **Metrics Export**: Prometheus/Grafana integration
3. **Slack/Email Alerts**: Notify operators of critical issues
4. **Adaptive Timeouts**: Machine learning for optimal thresholds
5. **Job Restart**: Automatic job restart on failure
6. **Health Dashboard**: UI for viewing health status

## Troubleshooting

**Monitor not starting**:
```python
# Check logs
logger.info("Agent health monitor started")  # Should see this

# Verify task is running
assert monitor.running is True
assert monitor._task is not None
```

**False positives**:
```python
# Increase timeouts for specific agent types
config = HealthCheckConfig(
    timeout_overrides={
        "orchestrator": 20,  # Increase if needed
        "implementer": 15
    }
)
```

**Jobs not updating health**:
```python
# Ensure agents report progress
job.job_metadata = {
    **job.job_metadata,
    "last_progress_update": datetime.now(timezone.utc).isoformat()
}
job.health_status = "healthy"
session.commit()
```

## References

**Files**:
- `src/giljo_mcp/monitoring/agent_health_monitor.py` - Core monitor
- `src/giljo_mcp/monitoring/health_config.py` - Configuration
- `src/giljo_mcp/models.py` - Database schema
- `api/websocket.py` - WebSocket events
- `migrations/versions/20251105_0106b_add_health_fields.py` - Migration

**Tests**:
- `tests/unit/monitoring/test_agent_health_monitor.py` - Unit tests
- `tests/integration/test_health_monitoring_e2e.py` - Integration tests

**Handover**: `handovers/0107_agent_monitoring_and_graceful_cancellation.md`
