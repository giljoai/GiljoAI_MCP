# Handover 0019: Agent Job Management System - User Validation Guide

**Version**: 1.0
**Date**: 2025-10-19
**Status**: Complete

## Table of Contents

1. [Overview](#overview)
2. [Quick Start Validation](#quick-start-validation)
3. [Component Validation](#component-validation)
4. [API Testing Examples](#api-testing-examples)
5. [WebSocket Testing](#websocket-testing)
6. [Database Queries](#database-queries)
7. [Complete Workflow Example](#complete-workflow-example)
8. [Troubleshooting](#troubleshooting)

## Overview

This guide provides step-by-step instructions for validating the Agent Job Management System implementation. The system enables agent-to-agent coordination through:

- **AgentJobManager**: Core job lifecycle management
- **AgentCommunicationQueue**: Message passing between agents
- **JobCoordinator**: Parent-child job orchestration
- **REST API**: 13 endpoints for job operations
- **WebSocket Events**: Real-time job status updates

### What You'll Validate

- Job creation, acknowledgment, and completion
- Parent-child job hierarchies
- Agent-to-agent messaging
- Multi-tenant isolation
- WebSocket event broadcasting
- Database integrity

## Quick Start Validation

### Prerequisites

Before you begin, ensure you have:

```bash
# PostgreSQL 18 running
psql -U postgres -l

# Python 3.11+ with dependencies
python --version
pip list | grep -E '(fastapi|sqlalchemy|asyncpg)'

# API server configuration
cat config.yaml | grep -A 5 'api:'
```

### 1. Database Setup Verification

Verify the `mcp_agent_jobs` table exists:

```bash
psql -U postgres -d giljo_mcp
```

```sql
-- Check table exists
\dt mcp_agent_jobs

-- Verify schema
\d mcp_agent_jobs

-- Expected columns:
-- id, tenant_key, job_id, agent_type, mission, status, spawned_by,
-- context_chunks (JSON), messages (JSONB), acknowledged, started_at,
-- completed_at, created_at

-- Verify indexes
\di idx_mcp_agent_jobs_*

-- Expected indexes:
-- idx_mcp_agent_jobs_tenant_status
-- idx_mcp_agent_jobs_tenant_type
-- idx_mcp_agent_jobs_job_id

-- Verify constraints
\d+ mcp_agent_jobs | grep -A 10 'Check constraints'

-- Expected constraint:
-- ck_mcp_agent_job_status CHECK (status IN ('pending', 'active', 'completed', 'failed'))
```

### 2. API Server Startup

Start the API server:

```bash
# Development mode
python startup.py --dev

# Production mode
python startup.py
```

Expected output:
```
INFO:     Starting API server on http://0.0.0.0:7272
INFO:     Application startup complete
INFO:     Uvicorn running on http://0.0.0.0:7272
```

### 3. Health Check

Verify the API is running:

```bash
curl http://localhost:7272/health

# Expected response:
# {"status": "healthy", "timestamp": "2025-10-19T..."}
```

### 4. Authentication Setup

Get an admin access token:

```bash
# Login as admin user
curl -X POST http://localhost:7272/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "your_admin_password"
  }'

# Response:
# {
#   "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
#   "token_type": "bearer",
#   "user": {...}
# }

# Save token for later use
export ADMIN_TOKEN="your_access_token_here"
```

## Component Validation

### AgentJobManager Validation

The AgentJobManager handles job lifecycle and status transitions.

#### Valid Status Transitions

```
pending -> active (acknowledge_job)
pending -> failed (fail_job)
active -> completed (complete_job)
active -> failed (fail_job)
completed -> [terminal state]
failed -> [terminal state]
```

#### Test Job Creation

```bash
curl -X POST http://localhost:7272/api/agent-jobs \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "implementer",
    "mission": "Implement feature X",
    "context_chunks": ["chunk-001", "chunk-002"]
  }'

# Expected response:
# {
#   "job_id": "550e8400-e29b-41d4-a716-446655440000",
#   "message": "Job created successfully"
# }
```

#### Test Job Retrieval

```bash
curl http://localhost:7272/api/agent-jobs/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Expected response:
# {
#   "id": 1,
#   "job_id": "550e8400-e29b-41d4-a716-446655440000",
#   "tenant_key": "tenant-123",
#   "agent_type": "implementer",
#   "mission": "Implement feature X",
#   "status": "pending",
#   "spawned_by": null,
#   "context_chunks": ["chunk-001", "chunk-002"],
#   "messages": [],
#   "acknowledged": false,
#   "started_at": null,
#   "completed_at": null,
#   "created_at": "2025-10-19T..."
# }
```

#### Test Status Transitions

```bash
# 1. Acknowledge job (pending -> active)
curl -X POST http://localhost:7272/api/agent-jobs/550e8400-e29b-41d4-a716-446655440000/acknowledge \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Expected response:
# {
#   "job_id": "550e8400-e29b-41d4-a716-446655440000",
#   "status": "active",
#   "started_at": "2025-10-19T...",
#   "message": "Job acknowledged successfully"
# }

# 2. Complete job (active -> completed)
curl -X POST http://localhost:7272/api/agent-jobs/550e8400-e29b-41d4-a716-446655440000/complete \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "result": {"status": "success", "output": "Feature X implemented"}
  }'

# Expected response:
# {
#   "job_id": "550e8400-e29b-41d4-a716-446655440000",
#   "status": "completed",
#   "completed_at": "2025-10-19T...",
#   "message": "Job completed successfully"
# }
```

#### Test Invalid Transition

```bash
# Try to complete an already completed job (should fail)
curl -X POST http://localhost:7272/api/agent-jobs/550e8400-e29b-41d4-a716-446655440000/complete \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "result": {"status": "retry"}
  }'

# Expected error (400 Bad Request):
# {
#   "detail": "Invalid status transition from 'completed' to 'completed'. Valid transitions: none (terminal state)"
# }
```

### AgentCommunicationQueue Validation

Test message passing between jobs.

#### Send Message

```bash
curl -X POST http://localhost:7272/api/agent-jobs/550e8400-e29b-41d4-a716-446655440000/messages \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "role": "orchestrator",
    "type": "instruction",
    "content": "Please analyze requirements before implementation"
  }'

# Expected response:
# {
#   "message_id": "0",
#   "timestamp": "2025-10-19T...",
#   "role": "orchestrator",
#   "type": "instruction",
#   "content": "Please analyze requirements before implementation",
#   "acknowledged": false
# }
```

#### Get Messages

```bash
curl http://localhost:7272/api/agent-jobs/550e8400-e29b-41d4-a716-446655440000/messages \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Expected response:
# {
#   "messages": [
#     {
#       "message_id": "0",
#       "role": "orchestrator",
#       "type": "instruction",
#       "content": "Please analyze requirements before implementation",
#       "timestamp": "2025-10-19T...",
#       "acknowledged": false
#     }
#   ]
# }
```

#### Acknowledge Message

```bash
curl -X POST http://localhost:7272/api/agent-jobs/550e8400-e29b-41d4-a716-446655440000/messages/0/acknowledge \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Expected response:
# {
#   "message_id": "0",
#   "timestamp": "2025-10-19T...",
#   "role": "orchestrator",
#   "type": "instruction",
#   "content": "Please analyze requirements before implementation",
#   "acknowledged": true
# }
```

### JobCoordinator Validation

Test parent-child job relationships.

#### Spawn Child Jobs

```bash
# Create parent job first
curl -X POST http://localhost:7272/api/agent-jobs \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "orchestrator",
    "mission": "Coordinate implementation of feature set"
  }'

# Save parent job_id
export PARENT_JOB_ID="parent-job-id-here"

# Spawn 3 child jobs
curl -X POST http://localhost:7272/api/agent-jobs/$PARENT_JOB_ID/spawn-children \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "children": [
      {
        "agent_type": "analyzer",
        "mission": "Analyze requirements",
        "context_chunks": ["req-001"]
      },
      {
        "agent_type": "implementer",
        "mission": "Implement backend",
        "context_chunks": ["backend-context"]
      },
      {
        "agent_type": "tester",
        "mission": "Write tests",
        "context_chunks": ["test-context"]
      }
    ]
  }'

# Expected response:
# {
#   "parent_job_id": "parent-job-id-here",
#   "child_job_ids": ["child-1-id", "child-2-id", "child-3-id"],
#   "message": "3 child jobs spawned successfully"
# }
```

#### Get Job Hierarchy

```bash
curl http://localhost:7272/api/agent-jobs/$PARENT_JOB_ID/hierarchy \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Expected response:
# {
#   "parent": {
#     "job_id": "parent-job-id-here",
#     "agent_type": "orchestrator",
#     "mission": "Coordinate implementation of feature set",
#     "status": "pending",
#     ...
#   },
#   "children": [
#     {
#       "job_id": "child-1-id",
#       "agent_type": "analyzer",
#       "mission": "Analyze requirements",
#       "spawned_by": "parent-job-id-here",
#       "status": "pending",
#       ...
#     },
#     {
#       "job_id": "child-2-id",
#       "agent_type": "implementer",
#       "mission": "Implement backend",
#       "spawned_by": "parent-job-id-here",
#       "status": "pending",
#       ...
#     },
#     {
#       "job_id": "child-3-id",
#       "agent_type": "tester",
#       "mission": "Write tests",
#       "spawned_by": "parent-job-id-here",
#       "status": "pending",
#       ...
#     }
#   ],
#   "total_children": 3
# }
```

## API Testing Examples

### List Jobs with Filtering

```bash
# Get all pending jobs
curl "http://localhost:7272/api/agent-jobs?status=pending&limit=10" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Get jobs for specific agent type
curl "http://localhost:7272/api/agent-jobs?agent_type=implementer" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Get child jobs for a parent
curl "http://localhost:7272/api/agent-jobs?spawned_by=$PARENT_JOB_ID" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Pagination
curl "http://localhost:7272/api/agent-jobs?limit=10&offset=20" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### Update Job Status

```bash
# Update job status via PATCH (admin only)
curl -X PATCH http://localhost:7272/api/agent-jobs/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "failed"
  }'

# Expected response:
# {
#   "job_id": "550e8400-e29b-41d4-a716-446655440000",
#   "status": "failed",
#   ...
# }
```

### Delete Job (Admin Only)

```bash
curl -X DELETE http://localhost:7272/api/agent-jobs/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Expected response: 204 No Content
```

### Error Scenarios

#### 404 Not Found

```bash
# Try to get non-existent job
curl http://localhost:7272/api/agent-jobs/non-existent-job-id \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Expected response (404):
# {
#   "detail": "Job not found"
# }
```

#### 403 Forbidden (Non-Admin)

```bash
# Try to create job as regular user
curl -X POST http://localhost:7272/api/agent-jobs \
  -H "Authorization: Bearer $REGULAR_USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "tester",
    "mission": "Test feature"
  }'

# Expected response (403):
# {
#   "detail": "Admin access required to create jobs"
# }
```

#### 400 Bad Request (Invalid Status Transition)

```bash
# Try invalid status transition
curl -X POST http://localhost:7272/api/agent-jobs/completed-job-id/acknowledge \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Expected response (400):
# {
#   "detail": "Invalid status transition from 'completed' to 'active'. Valid transitions: none (terminal state)"
# }
```

## WebSocket Testing

### Connect to WebSocket

Using JavaScript (browser console or Node.js):

```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:7272/ws/client-123');

ws.onopen = () => {
  console.log('Connected to agent job events');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received event:', data);
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  console.log('WebSocket connection closed');
};
```

Using Python:

```python
import asyncio
import websockets
import json

async def listen_events():
    uri = "ws://localhost:7272/ws/client-123"

    async with websockets.connect(uri) as websocket:
        print("Connected to WebSocket")

        async for message in websocket:
            event = json.loads(message)
            print(f"Received event: {event}")

asyncio.run(listen_events())
```

### Expected WebSocket Events

When you create, update, or complete jobs, you should receive:

```json
{
  "type": "agent_job:created",
  "data": {
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "agent_type": "implementer",
    "status": "pending",
    "tenant_key": "tenant-123",
    "created_at": "2025-10-19T..."
  }
}
```

```json
{
  "type": "agent_job:acknowledged",
  "data": {
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "active",
    "started_at": "2025-10-19T..."
  }
}
```

```json
{
  "type": "agent_job:completed",
  "data": {
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "completed",
    "completed_at": "2025-10-19T..."
  }
}
```

```json
{
  "type": "agent_job:failed",
  "data": {
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "failed",
    "completed_at": "2025-10-19T...",
    "error": {...}
  }
}
```

### Test WebSocket Events

1. Open WebSocket connection
2. Create a job via API
3. Verify `agent_job:created` event received
4. Acknowledge the job via API
5. Verify `agent_job:acknowledged` event received
6. Complete the job via API
7. Verify `agent_job:completed` event received

## Database Queries

### Verify Job Creation

```sql
-- Connect to database
psql -U postgres -d giljo_mcp

-- Check job exists
SELECT job_id, agent_type, status, tenant_key, acknowledged, created_at
FROM mcp_agent_jobs
WHERE job_id = '550e8400-e29b-41d4-a716-446655440000';

-- Expected result:
--  job_id                               | agent_type  | status  | tenant_key | acknowledged | created_at
-- --------------------------------------+-------------+---------+------------+--------------+------------
--  550e8400-e29b-41d4-a716-446655440000 | implementer | pending | tenant-123 | f            | 2025-10-19...
```

### Verify JSONB Messages

```sql
-- Check messages stored as JSONB
SELECT
  job_id,
  jsonb_array_length(messages) as message_count,
  messages
FROM mcp_agent_jobs
WHERE job_id = '550e8400-e29b-41d4-a716-446655440000';

-- Query messages with JSONB operators
SELECT
  job_id,
  jsonb_array_elements(messages)->>'role' as role,
  jsonb_array_elements(messages)->>'type' as type,
  jsonb_array_elements(messages)->>'content' as content,
  jsonb_array_elements(messages)->>'timestamp' as timestamp
FROM mcp_agent_jobs
WHERE job_id = '550e8400-e29b-41d4-a716-446655440000';
```

### Verify Parent-Child Relationships

```sql
-- Get parent and all children
SELECT
  job_id,
  agent_type,
  mission,
  status,
  spawned_by
FROM mcp_agent_jobs
WHERE job_id = 'parent-job-id'
   OR spawned_by = 'parent-job-id'
ORDER BY created_at;

-- Count children per parent
SELECT
  spawned_by as parent_job_id,
  COUNT(*) as child_count,
  array_agg(status) as child_statuses
FROM mcp_agent_jobs
WHERE spawned_by IS NOT NULL
GROUP BY spawned_by;
```

### Multi-Tenant Isolation Queries

```sql
-- Verify tenant isolation - should only return tenant-123 jobs
SELECT COUNT(*)
FROM mcp_agent_jobs
WHERE tenant_key = 'tenant-123';

-- Verify no cross-tenant data leakage
SELECT tenant_key, COUNT(*) as job_count
FROM mcp_agent_jobs
GROUP BY tenant_key;

-- Verify indexes are used (should use idx_mcp_agent_jobs_tenant_status)
EXPLAIN ANALYZE
SELECT * FROM mcp_agent_jobs
WHERE tenant_key = 'tenant-123' AND status = 'pending';
```

### Performance Queries

```sql
-- Check index usage
SELECT
  schemaname,
  tablename,
  indexname,
  idx_scan,
  idx_tup_read,
  idx_tup_fetch
FROM pg_stat_user_indexes
WHERE tablename = 'mcp_agent_jobs';

-- Find slow-running jobs
SELECT
  job_id,
  agent_type,
  status,
  started_at,
  EXTRACT(EPOCH FROM (NOW() - started_at)) as duration_seconds
FROM mcp_agent_jobs
WHERE status = 'active'
  AND started_at IS NOT NULL
ORDER BY duration_seconds DESC
LIMIT 10;
```

## Complete Workflow Example

This end-to-end scenario demonstrates the full agent job lifecycle:

### Scenario: Orchestrator Coordinates 3 Implementers

```bash
# 1. Create orchestrator parent job
curl -X POST http://localhost:7272/api/agent-jobs \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "orchestrator",
    "mission": "Coordinate implementation of user authentication feature"
  }' | jq -r '.job_id' > parent_job_id.txt

export PARENT_JOB_ID=$(cat parent_job_id.txt)

# 2. Acknowledge parent job
curl -X POST http://localhost:7272/api/agent-jobs/$PARENT_JOB_ID/acknowledge \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# 3. Spawn 3 child jobs
curl -X POST http://localhost:7272/api/agent-jobs/$PARENT_JOB_ID/spawn-children \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "children": [
      {
        "agent_type": "implementer",
        "mission": "Implement login endpoint",
        "context_chunks": ["auth-api-spec"]
      },
      {
        "agent_type": "implementer",
        "mission": "Implement JWT token generation",
        "context_chunks": ["jwt-spec"]
      },
      {
        "agent_type": "implementer",
        "mission": "Implement password hashing",
        "context_chunks": ["security-spec"]
      }
    ]
  }' | jq -r '.child_job_ids[]' > child_job_ids.txt

# Save child job IDs
export CHILD1=$(sed -n '1p' child_job_ids.txt)
export CHILD2=$(sed -n '2p' child_job_ids.txt)
export CHILD3=$(sed -n '3p' child_job_ids.txt)

# 4. Send message from parent to child 1
curl -X POST http://localhost:7272/api/agent-jobs/$CHILD1/messages \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "role": "orchestrator",
    "type": "instruction",
    "content": "Use bcrypt for password hashing with salt rounds=12"
  }'

# 5. Acknowledge child 1
curl -X POST http://localhost:7272/api/agent-jobs/$CHILD1/acknowledge \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# 6. Acknowledge and complete child 1
curl -X POST http://localhost:7272/api/agent-jobs/$CHILD1/complete \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "result": {
      "status": "success",
      "files_modified": ["api/auth/login.py"],
      "tests_passed": true
    }
  }'

# 7. Acknowledge child 2
curl -X POST http://localhost:7272/api/agent-jobs/$CHILD2/acknowledge \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# 8. Complete child 2
curl -X POST http://localhost:7272/api/agent-jobs/$CHILD2/complete \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "result": {
      "status": "success",
      "files_modified": ["api/auth/jwt.py"],
      "tests_passed": true
    }
  }'

# 9. Acknowledge child 3
curl -X POST http://localhost:7272/api/agent-jobs/$CHILD3/acknowledge \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# 10. Complete child 3
curl -X POST http://localhost:7272/api/agent-jobs/$CHILD3/complete \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "result": {
      "status": "success",
      "files_modified": ["api/auth/password.py"],
      "tests_passed": true
    }
  }'

# 11. Verify all children completed
curl http://localhost:7272/api/agent-jobs/$PARENT_JOB_ID/hierarchy \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  | jq '.children[] | {job_id, status}'

# Expected output:
# {
#   "job_id": "child-1-id",
#   "status": "completed"
# }
# {
#   "job_id": "child-2-id",
#   "status": "completed"
# }
# {
#   "job_id": "child-3-id",
#   "status": "completed"
# }

# 12. Aggregate results and complete parent
curl -X POST http://localhost:7272/api/agent-jobs/$PARENT_JOB_ID/complete \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "result": {
      "status": "success",
      "children_completed": 3,
      "children_failed": 0,
      "summary": "User authentication feature implemented successfully"
    }
  }'

# 13. Verify final hierarchy
curl http://localhost:7272/api/agent-jobs/$PARENT_JOB_ID/hierarchy \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### Expected Final State

```json
{
  "parent": {
    "job_id": "parent-job-id",
    "agent_type": "orchestrator",
    "mission": "Coordinate implementation of user authentication feature",
    "status": "completed",
    "acknowledged": true,
    "started_at": "2025-10-19T...",
    "completed_at": "2025-10-19T..."
  },
  "children": [
    {
      "job_id": "child-1-id",
      "agent_type": "implementer",
      "mission": "Implement login endpoint",
      "status": "completed",
      "spawned_by": "parent-job-id"
    },
    {
      "job_id": "child-2-id",
      "agent_type": "implementer",
      "mission": "Implement JWT token generation",
      "status": "completed",
      "spawned_by": "parent-job-id"
    },
    {
      "job_id": "child-3-id",
      "agent_type": "implementer",
      "mission": "Implement password hashing",
      "status": "completed",
      "spawned_by": "parent-job-id"
    }
  ],
  "total_children": 3
}
```

## Troubleshooting

### Common Issues

#### Issue: Jobs Not Appearing in Database

**Symptoms**: API returns 404 for recently created job

**Solution**:
```bash
# Check database connection
psql -U postgres -d giljo_mcp -c "SELECT COUNT(*) FROM mcp_agent_jobs;"

# Check API logs
tail -f logs/api.log | grep -i "agent_job"

# Verify tenant_key matches
psql -U postgres -d giljo_mcp -c "SELECT DISTINCT tenant_key FROM mcp_agent_jobs;"
```

#### Issue: WebSocket Not Receiving Events

**Symptoms**: WebSocket connected but no events received

**Solution**:
```javascript
// Check connection status
console.log('WebSocket readyState:', ws.readyState);
// 0 = CONNECTING, 1 = OPEN, 2 = CLOSING, 3 = CLOSED

// Verify tenant_key in WebSocket connection
// Events are only broadcast to same tenant
```

#### Issue: Invalid Status Transition Error

**Symptoms**: 400 error when trying to update job status

**Solution**:
```bash
# Check current status
curl http://localhost:7272/api/agent-jobs/JOB_ID \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  | jq '.status'

# Valid transitions:
# pending -> active (acknowledge)
# pending -> failed (fail)
# active -> completed (complete)
# active -> failed (fail)
# completed -> NONE (terminal)
# failed -> NONE (terminal)
```

#### Issue: Cross-Tenant Access

**Symptoms**: Cannot see jobs created by other users

**Solution**:
This is expected behavior. Multi-tenant isolation ensures:
- Jobs are filtered by `tenant_key`
- Users can only see jobs in their tenant
- Cross-tenant access returns 404 (not 403)

To verify:
```sql
-- Check your tenant_key
SELECT tenant_key FROM users WHERE username = 'your_username';

-- Check job's tenant_key
SELECT tenant_key FROM mcp_agent_jobs WHERE job_id = 'job-id';
```

#### Issue: Message Not Stored

**Symptoms**: Messages endpoint returns empty array

**Solution**:
```bash
# Verify message was sent successfully
curl -X POST http://localhost:7272/api/agent-jobs/JOB_ID/messages \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "role": "orchestrator",
    "type": "instruction",
    "content": "Test message"
  }' -v

# Check database directly
psql -U postgres -d giljo_mcp -c \
  "SELECT messages FROM mcp_agent_jobs WHERE job_id = 'job-id';"
```

### Performance Issues

#### Slow Job Queries

```sql
-- Check if indexes are being used
EXPLAIN ANALYZE
SELECT * FROM mcp_agent_jobs
WHERE tenant_key = 'tenant-123' AND status = 'pending';

-- Should show "Index Scan using idx_mcp_agent_jobs_tenant_status"

-- If not, rebuild indexes
REINDEX TABLE mcp_agent_jobs;
```

#### Large Message Arrays

JSONB message arrays are efficient for most use cases, but if you have jobs with 1000+ messages:

```sql
-- Check message array sizes
SELECT
  job_id,
  agent_type,
  jsonb_array_length(messages) as message_count
FROM mcp_agent_jobs
WHERE jsonb_array_length(messages) > 100
ORDER BY message_count DESC;

-- Consider archiving old messages or splitting into separate table
```

### Getting Help

If you encounter issues not covered here:

1. Check API logs: `logs/api.log`
2. Check database logs: PostgreSQL logs
3. Enable debug mode: `python startup.py --dev --log-level DEBUG`
4. Review test cases: `tests/test_agent_jobs_api.py`
5. Consult API reference: `docs/api/AGENT_JOBS_API_REFERENCE.md`

## Next Steps

After completing validation:

1. Review [Testing Guide](../testing/HANDOVER_0019_TESTING_GUIDE.md) for running automated tests
2. Review [API Reference](../api/AGENT_JOBS_API_REFERENCE.md) for complete endpoint documentation
3. Review [Security Verification](../security/HANDOVER_0019_TENANT_ISOLATION_VERIFICATION.md) for multi-tenant isolation testing
4. Integrate agent job system into your orchestration workflows

## Summary

You have validated:

- Job creation, lifecycle, and status transitions
- Parent-child job hierarchies
- Agent-to-agent messaging
- Multi-tenant isolation
- WebSocket real-time events
- Database integrity and performance

The Agent Job Management System is production-ready for agentic orchestration workflows.
