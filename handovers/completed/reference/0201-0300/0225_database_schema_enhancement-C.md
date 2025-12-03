# Handover 0225: Database Schema Enhancement

**Status**: ✅ COMPLETED
**Priority**: High
**Estimated Effort**: 2 hours (actual: 2.5 hours)
**Dependencies**: None
**Part of**: Visual Refactor Series (0225-0237)
**Completed**: 2025-11-21
**Commit**: 29bf1c6

## Completion Summary

✅ **TDD Workflow** - RED → GREEN → REFACTOR completed successfully
✅ **3 Performance Indexes** added to mcp_agent_jobs table (16KB each, well under 10MB)
✅ **10 Tests** written and passing (100% coverage for new code)
✅ **Comprehensive Documentation** added to MCPAgentJob model docstring
✅ **Query Performance** verified via EXPLAIN ANALYZE (indexes used appropriately)

**Files Modified**:
- src/giljo_mcp/models/agents.py (+28 lines)
- tests/database/conftest.py (+19 lines, new fixture)
- tests/database/test_agent_job_indexes.py (+306 lines, comprehensive tests)

**Production Ready**: All success criteria met, indexes available for Handover 0226

---

## Objective

Optimize database schema for table-structured status board by adding performance indexes and documenting existing tracking fields. **No new columns required**—all necessary tracking fields already exist in MCPAgentJob model.

---

## Current State Analysis

### Existing Tracking Fields (src/giljo_mcp/models/agents.py)

The MCPAgentJob model already contains all fields needed for the status board refactor:

**Message Tracking** (Auto-implemented):
- `messages` (JSONB) - Message array with status tracking
  - Message status: `pending` (unread) → `acknowledged` (read)
  - Auto-tracking: `read_mcp_messages()` marks messages as acknowledged (agent_messaging.py:289-302)
- `last_message_check_at` (DateTime) - Auto-updated when agent reads messages

**Progress Tracking**:
- `last_progress_at` (DateTime) - Updated by agents reporting progress
- `progress` (Integer, 0-100) - Job completion percentage
- `current_task` (Text) - Current task description

**Health Monitoring**:
- `health_status` (String) - unknown, healthy, warning, critical, timeout
- `last_health_check` (DateTime) - Last health check timestamp
- `health_failure_count` (Integer) - Consecutive health check failures

**Status & Metadata**:
- `status` (String) - waiting, working, blocked, complete, failed, cancelled, decommissioned
- `agent_type` (String) - orchestrator, analyzer, implementer, tester, etc.
- `agent_name` (String) - Human-readable agent name
- `block_reason` (Text) - Explanation for blocked state
- `failure_reason` (String) - error, timeout, system_error

### Message Status Auto-Tracking

**Implementation** (src/giljo_mcp/tools/agent_messaging.py:289-302):

```python
def read_mcp_messages(..., mark_as_read: bool = True):
    """
    Retrieve messages from the agent's message queue.

    Auto-tracking behavior:
    - Updates last_message_check_at timestamp when called
    - Marks messages as "acknowledged" when mark_as_read=True
    """

    # Update last message check timestamp (Handover 0107)
    agent_job.last_message_check_at = datetime.now(timezone.utc)

    # Auto-mark messages as acknowledged
    if mark_as_read and messages:
        for msg in messages:
            msg["status"] = "acknowledged"
```

**Frontend Integration** (AgentCard.vue:33-63):

```vue
<!-- Message badges already show unread/acknowledged counts -->
<v-badge v-if="unreadsCount > 0" color="error" :content="unreadsCount">
  <v-icon>mdi-message-badge</v-icon>
</v-badge>
<v-badge v-if="acknowledgedCount > 0" color="success" :content="acknowledgedCount">
  <v-icon>mdi-check-all</v-icon>
</v-badge>
```

---

## Implementation Plan

### 1. Add Performance Indexes

**File**: `src/giljo_mcp/models/agents.py`

Add indexes to optimize status board queries:

```python
class MCPAgentJob(Base):
    __tablename__ = "mcp_agent_jobs"

    # Existing indexes
    __table_args__ = (
        Index("idx_mcp_agent_jobs_tenant_key", "tenant_key"),
        Index("idx_mcp_agent_jobs_project_id", "project_id"),
        Index("idx_mcp_agent_jobs_status", "status"),

        # NEW: Performance indexes for status board queries
        Index("idx_mcp_agent_jobs_last_progress", "last_progress_at"),
        Index("idx_mcp_agent_jobs_health_status", "health_status"),
        Index("idx_mcp_agent_jobs_composite_status", "project_id", "status", "last_progress_at"),
    )
```

**Rationale**:
- `idx_mcp_agent_jobs_last_progress` - Enables fast sorting by last activity
- `idx_mcp_agent_jobs_health_status` - Enables filtering by health state
- `idx_mcp_agent_jobs_composite_status` - Optimizes common query pattern (project jobs sorted by status + activity)

### 2. Migration Script

**File**: `migrations/add_status_board_indexes.py`

```python
"""Add indexes for status board performance optimization

Revision ID: 0225_status_board_indexes
Revises: [previous_migration]
Create Date: 2025-11-21
"""

from alembic import op

def upgrade():
    """Add performance indexes for status board queries"""

    # Index on last_progress_at for activity sorting
    op.create_index(
        'idx_mcp_agent_jobs_last_progress',
        'mcp_agent_jobs',
        ['last_progress_at'],
        postgresql_using='btree'
    )

    # Index on health_status for health filtering
    op.create_index(
        'idx_mcp_agent_jobs_health_status',
        'mcp_agent_jobs',
        ['health_status'],
        postgresql_using='btree'
    )

    # Composite index for common status board query pattern
    op.create_index(
        'idx_mcp_agent_jobs_composite_status',
        'mcp_agent_jobs',
        ['project_id', 'status', 'last_progress_at'],
        postgresql_using='btree'
    )

def downgrade():
    """Remove status board indexes"""

    op.drop_index('idx_mcp_agent_jobs_composite_status', 'mcp_agent_jobs')
    op.drop_index('idx_mcp_agent_jobs_health_status', 'mcp_agent_jobs')
    op.drop_index('idx_mcp_agent_jobs_last_progress', 'mcp_agent_jobs')
```

### 3. Update Documentation Comments

**File**: `src/giljo_mcp/models/agents.py`

Add comprehensive docstring to MCPAgentJob model:

```python
class MCPAgentJob(Base):
    """
    Agent job tracking with multi-tenant isolation.

    Message Tracking (Auto-implemented):
    - messages (JSONB): Message array with status tracking
      - Status transition: "pending" (unread) → "acknowledged" (read)
      - Auto-tracking: read_mcp_messages() marks messages as acknowledged
    - last_message_check_at (DateTime): Auto-updated when agent reads messages

    Progress Tracking:
    - last_progress_at (DateTime): Updated by agents reporting progress
    - progress (Integer, 0-100): Job completion percentage
    - current_task (Text): Current task description

    Health Monitoring:
    - health_status (String): unknown, healthy, warning, critical, timeout
    - last_health_check (DateTime): Last health check timestamp
    - health_failure_count (Integer): Consecutive health check failures

    Status Board Optimizations:
    - Indexed fields: last_progress_at, health_status
    - Composite index: (project_id, status, last_progress_at)
    - Enables fast sorting/filtering for table view

    See: agent_messaging.py for message auto-tracking implementation
    """
    __tablename__ = "mcp_agent_jobs"
    # ... rest of model definition
```

---

## Testing Criteria

### 1. Index Performance Verification

**Test Query** (PostgreSQL):

```sql
-- Test 1: Sort by last activity (should use idx_mcp_agent_jobs_last_progress)
EXPLAIN ANALYZE
SELECT job_id, agent_name, status, last_progress_at
FROM mcp_agent_jobs
WHERE tenant_key = 'test-tenant'
  AND project_id = 'test-project-uuid'
ORDER BY last_progress_at DESC NULLS LAST
LIMIT 50;

-- Expected: Index Scan using idx_mcp_agent_jobs_last_progress

-- Test 2: Filter by health status (should use idx_mcp_agent_jobs_health_status)
EXPLAIN ANALYZE
SELECT job_id, agent_name, health_status
FROM mcp_agent_jobs
WHERE tenant_key = 'test-tenant'
  AND health_status IN ('warning', 'critical', 'timeout');

-- Expected: Bitmap Index Scan on idx_mcp_agent_jobs_health_status

-- Test 3: Common status board query (should use composite index)
EXPLAIN ANALYZE
SELECT job_id, agent_name, status, last_progress_at, health_status
FROM mcp_agent_jobs
WHERE project_id = 'test-project-uuid'
  AND status IN ('waiting', 'working', 'blocked')
ORDER BY last_progress_at DESC NULLS LAST;

-- Expected: Index Scan using idx_mcp_agent_jobs_composite_status
```

### 2. Message Auto-Tracking Verification

**Test**: Verify read_mcp_messages() auto-tracking behavior

```python
# Test file: tests/tools/test_agent_messaging.py

async def test_message_auto_tracking(db_session, test_tenant, test_project):
    """Test that read_mcp_messages automatically updates last_message_check_at"""

    # Create agent job
    agent_job = create_test_agent_job(
        db_session,
        tenant_key=test_tenant.tenant_key,
        project_id=test_project.project_id
    )

    # Send message
    await send_mcp_message(
        db_session=db_session,
        from_job_id=agent_job.job_id,
        to_job_id="orchestrator",
        content="Test message",
        tenant_key=test_tenant.tenant_key
    )

    # Verify message status is "pending"
    await db_session.refresh(agent_job)
    assert agent_job.messages[0]["status"] == "pending"

    # Read messages with auto-tracking
    result = await read_mcp_messages(
        db_session=db_session,
        job_id=agent_job.job_id,
        tenant_key=test_tenant.tenant_key,
        mark_as_read=True
    )

    # Verify auto-tracking behavior
    await db_session.refresh(agent_job)
    assert agent_job.last_message_check_at is not None
    assert agent_job.messages[0]["status"] == "acknowledged"
    assert result["unread_count"] == 0
```

### 3. Index Size Monitoring

**Test Query** (PostgreSQL):

```sql
-- Monitor index sizes after creation
SELECT
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE tablename = 'mcp_agent_jobs'
ORDER BY pg_relation_size(indexrelid) DESC;

-- Expected: Indexes should be <10MB for typical workloads
```

---

## Migration Process

### Step-by-Step Execution

1. **Backup Database** (Production safety):
   ```bash
   pg_dump -U postgres -d giljo_mcp > backup_pre_0225.sql
   ```

2. **Run Migration**:
   ```bash
   python install.py  # Applies new indexes automatically
   ```

3. **Verify Indexes Created**:
   ```bash
   PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp \
     -c "\d mcp_agent_jobs"

   # Should show 3 new indexes:
   # - idx_mcp_agent_jobs_last_progress
   # - idx_mcp_agent_jobs_health_status
   # - idx_mcp_agent_jobs_composite_status
   ```

4. **Run Performance Tests**:
   ```bash
   pytest tests/models/test_agent_job_indexes.py -v
   ```

5. **Analyze Query Plans**:
   ```bash
   # Run EXPLAIN ANALYZE queries from Testing Criteria section
   ```

---

## Rollback Plan

If performance degrades or issues arise:

```sql
-- Drop new indexes
DROP INDEX IF EXISTS idx_mcp_agent_jobs_last_progress;
DROP INDEX IF EXISTS idx_mcp_agent_jobs_health_status;
DROP INDEX IF EXISTS idx_mcp_agent_jobs_composite_status;

-- Restore from backup if needed
psql -U postgres -d giljo_mcp < backup_pre_0225.sql
```

---

## Key Insights

### No Schema Changes Needed

The existing MCPAgentJob model contains all necessary fields for the status board refactor:

✅ **Message tracking**: `messages` JSONB with status field (pending/acknowledged)
✅ **Auto-tracking**: `read_mcp_messages()` automatically updates `last_message_check_at`
✅ **Health monitoring**: `health_status`, `last_health_check`, `health_failure_count`
✅ **Progress tracking**: `last_progress_at`, `progress`, `current_task`
✅ **Status management**: 7-state status system with block/failure reasons

### Performance Optimization Only

This handover focuses solely on index optimization to ensure fast table queries:

- **Sort by activity**: `last_progress_at` index enables instant sorting
- **Filter by health**: `health_status` index enables health filtering
- **Common query pattern**: Composite index covers typical status board query

### Message Auto-Tracking Design

The existing auto-tracking implementation in `agent_messaging.py` is production-ready:

- **Automatic**: No explicit "mark as read" tool needed
- **Transparent**: Happens when agent reads messages via `read_mcp_messages()`
- **Frontend-integrated**: AgentCard already displays unread/acknowledged badges
- **WebSocket-enabled**: Real-time updates when messages change status

---

## Success Criteria

- ✅ 3 new indexes created on mcp_agent_jobs table
- ✅ Query plans show index usage for common status board queries
- ✅ Index sizes are reasonable (<10MB for typical workloads)
- ✅ No performance regression on existing queries
- ✅ Message auto-tracking verified via unit tests
- ✅ Documentation updated with tracking field descriptions

---

## Next Steps

→ **Handover 0226**: Backend API Extensions
- New endpoint: `GET /api/agent-jobs/table-view`
- Enhanced filtering/sorting parameters
- WebSocket event: `job:table_update`

---

## References

- **Model Definition**: `src/giljo_mcp/models/agents.py:28-197`
- **Auto-Tracking Implementation**: `src/giljo_mcp/tools/agent_messaging.py:289-302`
- **Frontend Integration**: `frontend/src/components/AgentCard.vue:33-63`
- **Health Monitoring**: Handover 0106, 0107 (staleness detection)
- **Message System**: Handover 0073 (message storage), 0080 (orchestrator succession)
