# Agent Jobs API Reference

**Version**: 1.0
**Date**: 2025-10-19
**Last Updated**: 2025-01-05 (Harmonized)
**Base URL**: `http://localhost:7272/api/agent-jobs`
**Harmonization Status**: ✅ Aligned with codebase

---

## Quick Links to Harmonized Documents

- **[Simple_Vision.md](../handovers/Simple_Vision.md)** - User journey & agent job lifecycle explanation
- **[start_to_finish_agent_FLOW.md](../handovers/start_to_finish_agent_FLOW.md)** - Technical verification of job flow

**Agent Job Status Lifecycle** (verified in codebase):
- Initial state: **"waiting"** (not "pending")
- Full lifecycle: **waiting → active → working → complete/failed/blocked**
- Source: Verified in start_to_finish_agent_FLOW.md lines 1119, 1276, 1361

**Current Agent Templates** (6 default templates):
- orchestrator, implementer, tester, analyzer, reviewer, documenter
- Source: `src/giljo_mcp/template_seeder.py::_get_default_templates_v103()`

⚠️ **Documentation Note**: Some code examples in this document may show `status="pending"` from earlier documentation. The correct initial status in the codebase is `status="waiting"`. When implementing, always use "waiting" as the initial job status.

---

## Table of Contents
5. [Error Handling](#error-handling)
6. [WebSocket Events](#websocket-events)
7. [Rate Limiting](#rate-limiting)

## Overview

The Agent Jobs API provides comprehensive job management for multi-agent orchestration. All endpoints enforce:

- **Authentication**: Bearer token required
- **Multi-Tenant Isolation**: Jobs filtered by `tenant_key`
- **Role-Based Access Control**: Admin-only operations
- **Real-Time Events**: WebSocket notifications for job updates

### Capabilities

- Create and manage agent jobs
- Track job lifecycle (waiting → active → working → completed/failed/blocked)
- Coordinate parent-child job hierarchies
- Send messages between agents
- Query jobs with flexible filtering
- Real-time WebSocket event broadcasting

## Authentication

All endpoints require a valid JWT access token.

### Get Access Token

```bash
# Login
curl -X POST http://localhost:7272/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your_username",
    "password": "your_password"
  }'

# Response
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "username": "your_username",
    "role": "admin",
    "tenant_key": "tenant-123"
  }
}
```

### Use Token in Requests

```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  http://localhost:7272/api/agent-jobs
```

## Endpoint Summary

| Method | Endpoint | Description | Auth | Admin Only |
|--------|----------|-------------|------|-----------|
| POST | `/` | Create job | Yes | Yes |
| GET | `/` | List jobs | Yes | No |
| GET | `/{job_id}` | Get job | Yes | No |
| PATCH | `/{job_id}` | Update job | Yes | Yes |
| DELETE | `/{job_id}` | Delete job | Yes | Yes |
| POST | `/{job_id}/acknowledge` | Acknowledge job | Yes | No |
| POST | `/{job_id}/complete` | Complete job | Yes | No |
| POST | `/{job_id}/fail` | Fail job | Yes | No |
| POST | `/{job_id}/messages` | Send message | Yes | No |
| GET | `/{job_id}/messages` | Get messages | Yes | No |
| POST | `/{job_id}/messages/{id}/acknowledge` | Acknowledge message | Yes | No |
| POST | `/{job_id}/spawn-children` | Spawn child jobs | Yes | No |
| GET | `/{job_id}/hierarchy` | Get hierarchy | Yes | No |

### HTTP Status Codes

| Code | Meaning | When Used |
|------|---------|-----------|
| 200 | OK | Successful GET/PATCH/POST |
| 201 | Created | Successful job/message creation |
| 204 | No Content | Successful DELETE |
| 400 | Bad Request | Invalid input, status transition error |
| 401 | Unauthorized | Missing/invalid token |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Job not found (includes multi-tenant isolation) |
| 500 | Internal Server Error | Server error |

## Request/Response Examples

### 1. Create Job

Create a new agent job (admin only).

**Request**:
```http
POST /api/agent-jobs
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
  "agent_type": "implementer",
  "mission": "Implement user authentication feature",
  "spawned_by": null,
  "context_chunks": ["chunk-001", "chunk-002"]
}
```

**Response** (201 Created):
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Job created successfully"
}
```

**Request Schema**:
```typescript
{
  agent_type: string;      // Required: orchestrator, implementer, analyzer, tester, etc.
  mission: string;         // Required: Job instructions/description
  spawned_by?: string;     // Optional: Parent job_id
  context_chunks?: string[]; // Optional: Context chunk IDs for loading
}
```

**cURL Example**:
```bash
curl -X POST http://localhost:7272/api/agent-jobs \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "implementer",
    "mission": "Implement feature X",
    "context_chunks": ["chunk-001"]
  }'
```

### 2. List Jobs

List jobs with optional filtering and pagination.

**Request**:
```http
GET /api/agent-jobs?status=pending&agent_type=implementer&limit=10&offset=0
Authorization: Bearer YOUR_TOKEN
```

**Response** (200 OK):
```json
{
  "jobs": [
    {
      "id": 1,
      "job_id": "550e8400-e29b-41d4-a716-446655440000",
      "tenant_key": "tenant-123",
      "agent_type": "implementer",
      "mission": "Implement feature X",
      "status": "waiting",
      "spawned_by": null,
      "context_chunks": ["chunk-001"],
      "messages": [],
      "acknowledged": false,
      "started_at": null,
      "completed_at": null,
      "created_at": "2025-10-19T10:30:00Z"
    }
  ],
  "total": 1
}
```

**Query Parameters**:
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| status | string | Filter by status (pending, active, completed, failed) | None |
| agent_type | string | Filter by agent type | None |
| spawned_by | string | Filter by parent job_id | None |
| limit | integer | Max results (1-100) | 100 |
| offset | integer | Skip N results | 0 |

**cURL Example**:
```bash
# Get all pending jobs
curl "http://localhost:7272/api/agent-jobs?status=pending" \
  -H "Authorization: Bearer $TOKEN"

# Get implementer jobs
curl "http://localhost:7272/api/agent-jobs?agent_type=implementer&limit=20" \
  -H "Authorization: Bearer $TOKEN"
```

### 3. Get Job

Retrieve a specific job by ID.

**Request**:
```http
GET /api/agent-jobs/550e8400-e29b-41d4-a716-446655440000
Authorization: Bearer YOUR_TOKEN
```

**Response** (200 OK):
```json
{
  "id": 1,
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "tenant_key": "tenant-123",
  "agent_type": "implementer",
  "mission": "Implement feature X",
  "status": "waiting",
  "spawned_by": null,
  "context_chunks": ["chunk-001"],
  "messages": [],
  "acknowledged": false,
  "started_at": null,
  "completed_at": null,
  "created_at": "2025-10-19T10:30:00Z"
}
```

**cURL Example**:
```bash
curl http://localhost:7272/api/agent-jobs/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer $TOKEN"
```

### 4. Update Job

Update job status or metadata (admin only).

**Request**:
```http
PATCH /api/agent-jobs/550e8400-e29b-41d4-a716-446655440000
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
  "status": "working"
}
```

**Response** (200 OK):
```json
{
  "id": 1,
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "working",
  ...
}
```

**Request Schema**:
```typescript
{
  status?: string;  // Optional: New status (must be valid transition)
}
```

**cURL Example**:
```bash
curl -X PATCH http://localhost:7272/api/agent-jobs/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "failed"}'
```

### 5. Delete Job

Delete a job (admin only).

**Request**:
```http
DELETE /api/agent-jobs/550e8400-e29b-41d4-a716-446655440000
Authorization: Bearer YOUR_TOKEN
```

**Response** (204 No Content):
```
(empty body)
```

**cURL Example**:
```bash
curl -X DELETE http://localhost:7272/api/agent-jobs/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### 6. Acknowledge Job

Acknowledge a job (pending → active). Idempotent operation.

**Request**:
```http
POST /api/agent-jobs/550e8400-e29b-41d4-a716-446655440000/acknowledge
Authorization: Bearer YOUR_TOKEN
```

**Response** (200 OK):
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "working",
  "started_at": "2025-10-19T10:35:00Z",
  "message": "Job acknowledged successfully"
}
```

**cURL Example**:
```bash
curl -X POST http://localhost:7272/api/agent-jobs/550e8400-e29b-41d4-a716-446655440000/acknowledge \
  -H "Authorization: Bearer $TOKEN"
```

### 7. Complete Job

Mark job as completed (active → completed).

**Request**:
```http
POST /api/agent-jobs/550e8400-e29b-41d4-a716-446655440000/complete
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
  "result": {
    "status": "success",
    "files_modified": ["src/auth.py"],
    "tests_passed": true
  }
}
```

**Response** (200 OK):
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "completed_at": "2025-10-19T10:45:00Z",
  "message": "Job completed successfully"
}
```

**Request Schema**:
```typescript
{
  result?: object;  // Optional: Result data (stored in messages)
}
```

**cURL Example**:
```bash
curl -X POST http://localhost:7272/api/agent-jobs/550e8400-e29b-41d4-a716-446655440000/complete \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"result": {"status": "success"}}'
```

### 8. Fail Job

Mark job as failed (pending/active → failed).

**Request**:
```http
POST /api/agent-jobs/550e8400-e29b-41d4-a716-446655440000/fail
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
  "error": {
    "type": "implementation_error",
    "message": "Failed to implement feature due to missing dependencies"
  }
}
```

**Response** (200 OK):
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "failed",
  "completed_at": "2025-10-19T10:40:00Z",
  "message": "Job failed"
}
```

**Request Schema**:
```typescript
{
  error?: object;  // Optional: Error data (stored in messages)
}
```

**cURL Example**:
```bash
curl -X POST http://localhost:7272/api/agent-jobs/550e8400-e29b-41d4-a716-446655440000/fail \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"error": {"type": "timeout", "message": "Job timed out"}}'
```

### 9. Send Message

Send a message to a job for agent-to-agent communication.

**Request**:
```http
POST /api/agent-jobs/550e8400-e29b-41d4-a716-446655440000/messages
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
  "role": "orchestrator",
  "type": "instruction",
  "content": "Please use TDD approach for this implementation"
}
```

**Response** (201 Created):
```json
{
  "message_id": "0",
  "timestamp": "2025-10-19T10:36:00Z",
  "role": "orchestrator",
  "type": "instruction",
  "content": "Please use TDD approach for this implementation",
  "acknowledged": false
}
```

**Request Schema**:
```typescript
{
  role: string;    // Required: orchestrator, implementer, system, etc.
  type: string;    // Required: instruction, question, response, error, etc.
  content: any;    // Required: Message content (any JSON type)
}
```

**cURL Example**:
```bash
curl -X POST http://localhost:7272/api/agent-jobs/550e8400-e29b-41d4-a716-446655440000/messages \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "role": "orchestrator",
    "type": "instruction",
    "content": "Use bcrypt for password hashing"
  }'
```

### 10. Get Messages

Retrieve all messages for a job.

**Request**:
```http
GET /api/agent-jobs/550e8400-e29b-41d4-a716-446655440000/messages
Authorization: Bearer YOUR_TOKEN
```

**Response** (200 OK):
```json
{
  "messages": [
    {
      "message_id": "0",
      "role": "orchestrator",
      "type": "instruction",
      "content": "Please use TDD approach",
      "timestamp": "2025-10-19T10:36:00Z",
      "acknowledged": false
    },
    {
      "message_id": "1",
      "role": "implementer",
      "type": "response",
      "content": "Acknowledged, starting TDD implementation",
      "timestamp": "2025-10-19T10:37:00Z",
      "acknowledged": true
    }
  ]
}
```

**cURL Example**:
```bash
curl http://localhost:7272/api/agent-jobs/550e8400-e29b-41d4-a716-446655440000/messages \
  -H "Authorization: Bearer $TOKEN"
```

### 11. Acknowledge Message

Acknowledge a specific message.

**Request**:
```http
POST /api/agent-jobs/550e8400-e29b-41d4-a716-446655440000/messages/0/acknowledge
Authorization: Bearer YOUR_TOKEN
```

**Response** (200 OK):
```json
{
  "message_id": "0",
  "timestamp": "2025-10-19T10:36:00Z",
  "role": "orchestrator",
  "type": "instruction",
  "content": "Please use TDD approach",
  "acknowledged": true
}
```

**cURL Example**:
```bash
curl -X POST http://localhost:7272/api/agent-jobs/550e8400-e29b-41d4-a716-446655440000/messages/0/acknowledge \
  -H "Authorization: Bearer $TOKEN"
```

### 12. Spawn Child Jobs

Create child jobs from a parent job.

**Request**:
```http
POST /api/agent-jobs/parent-job-id/spawn-children
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
  "children": [
    {
      "agent_type": "analyzer",
      "mission": "Analyze requirements",
      "context_chunks": ["req-001"]
    },
    {
      "agent_type": "implementer",
      "mission": "Implement backend",
      "context_chunks": ["backend-spec"]
    },
    {
      "agent_type": "tester",
      "mission": "Write tests",
      "context_chunks": ["test-spec"]
    }
  ]
}
```

**Response** (201 Created):
```json
{
  "parent_job_id": "parent-job-id",
  "child_job_ids": [
    "child-1-id",
    "child-2-id",
    "child-3-id"
  ],
  "message": "3 child jobs spawned successfully"
}
```

**Request Schema**:
```typescript
{
  children: Array<{
    agent_type: string;
    mission: string;
    context_chunks?: string[];
  }>;
}
```

**cURL Example**:
```bash
curl -X POST http://localhost:7272/api/agent-jobs/parent-job-id/spawn-children \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "children": [
      {
        "agent_type": "implementer",
        "mission": "Implement feature A"
      },
      {
        "agent_type": "implementer",
        "mission": "Implement feature B"
      }
    ]
  }'
```

### 13. Get Job Hierarchy

Retrieve parent job and all children.

**Request**:
```http
GET /api/agent-jobs/parent-job-id/hierarchy
Authorization: Bearer YOUR_TOKEN
```

**Response** (200 OK):
```json
{
  "parent": {
    "id": 1,
    "job_id": "parent-job-id",
    "agent_type": "orchestrator",
    "mission": "Coordinate implementation",
    "status": "working",
    ...
  },
  "children": [
    {
      "id": 2,
      "job_id": "child-1-id",
      "agent_type": "analyzer",
      "mission": "Analyze requirements",
      "status": "completed",
      "spawned_by": "parent-job-id",
      ...
    },
    {
      "id": 3,
      "job_id": "child-2-id",
      "agent_type": "implementer",
      "mission": "Implement backend",
      "status": "working",
      "spawned_by": "parent-job-id",
      ...
    }
  ],
  "total_children": 2
}
```

**cURL Example**:
```bash
curl http://localhost:7272/api/agent-jobs/parent-job-id/hierarchy \
  -H "Authorization: Bearer $TOKEN"
```

## Error Handling

### Error Response Format

All errors follow this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common Errors

#### 400 Bad Request - Invalid Status Transition

```bash
# Try to complete an already completed job
curl -X POST http://localhost:7272/api/agent-jobs/completed-job-id/complete \
  -H "Authorization: Bearer $TOKEN"
```

**Response**:
```json
{
  "detail": "Invalid status transition from 'completed' to 'completed'. Valid transitions: none (terminal state)"
}
```

**Valid Status Transitions**:
```
pending -> active (acknowledge)
pending -> failed (fail)
active -> completed (complete)
active -> failed (fail)
completed -> TERMINAL (no further transitions)
failed -> TERMINAL (no further transitions)
```

#### 401 Unauthorized - Missing Token

```bash
curl http://localhost:7272/api/agent-jobs
```

**Response**:
```json
{
  "detail": "Not authenticated"
}
```

#### 403 Forbidden - Insufficient Permissions

```bash
# Regular user tries to create job (admin only)
curl -X POST http://localhost:7272/api/agent-jobs \
  -H "Authorization: Bearer $REGULAR_USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"agent_type": "implementer", "mission": "Test"}'
```

**Response**:
```json
{
  "detail": "Admin access required to create jobs"
}
```

#### 404 Not Found - Job Not Found

```bash
# Job doesn't exist or belongs to different tenant
curl http://localhost:7272/api/agent-jobs/non-existent-job-id \
  -H "Authorization: Bearer $TOKEN"
```

**Response**:
```json
{
  "detail": "Job not found"
}
```

**Note**: Multi-tenant isolation returns 404 (not 403) for cross-tenant access to prevent tenant enumeration.

### Troubleshooting Guide

| Error | Possible Causes | Solutions |
|-------|----------------|-----------|
| 401 Unauthorized | Missing/expired token | Re-authenticate, get new token |
| 403 Forbidden | Non-admin user | Use admin account for restricted endpoints |
| 404 Not Found | Wrong job_id, cross-tenant access | Verify job_id, check tenant_key matches |
| 400 Bad Request | Invalid status transition | Check current status, use valid transition |
| 500 Internal Server Error | Database connection, server error | Check logs, verify DB connection |

## WebSocket Events

Real-time job updates are broadcast via WebSocket.

### Connect to WebSocket

```javascript
const ws = new WebSocket('ws://localhost:7272/ws/client-id');

ws.onopen = () => {
  console.log('Connected to job events');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Job event:', data);
};
```

### Event Types

#### agent_job:created

Fired when a job is created.

```json
{
  "type": "agent_job:created",
  "data": {
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "agent_type": "implementer",
    "status": "waiting",
    "tenant_key": "tenant-123",
    "created_at": "2025-10-19T10:30:00Z"
  }
}
```

#### agent_job:acknowledged

Fired when a job is acknowledged.

```json
{
  "type": "agent_job:acknowledged",
  "data": {
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "working",
    "started_at": "2025-10-19T10:35:00Z"
  }
}
```

#### agent_job:completed

Fired when a job completes successfully.

```json
{
  "type": "agent_job:completed",
  "data": {
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "completed",
    "completed_at": "2025-10-19T10:45:00Z"
  }
}
```

#### agent_job:failed

Fired when a job fails.

```json
{
  "type": "agent_job:failed",
  "data": {
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "failed",
    "completed_at": "2025-10-19T10:40:00Z",
    "error": {
      "type": "timeout",
      "message": "Job timed out after 30 minutes"
    }
  }
}
```

### Subscription Patterns

```javascript
// Subscribe to all job events
ws.onmessage = (event) => {
  const { type, data } = JSON.parse(event.data);

  switch (type) {
    case 'agent_job:created':
      console.log('New job:', data.job_id);
      break;

    case 'agent_job:acknowledged':
      console.log('Job started:', data.job_id);
      break;

    case 'agent_job:completed':
      console.log('Job completed:', data.job_id);
      break;

    case 'agent_job:failed':
      console.error('Job failed:', data.job_id, data.error);
      break;
  }
};
```

### Multi-Tenant Isolation

WebSocket events are scoped to the user's tenant. Users only receive events for jobs in their tenant.

## Rate Limiting

Currently, there is no rate limiting implemented. For production deployments, consider:

- **Per-user limits**: 100 requests/minute
- **Per-endpoint limits**: 10 job creations/minute
- **WebSocket connections**: 5 concurrent connections per user

Implementation example:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/agent-jobs")
@limiter.limit("10/minute")
async def create_job(...):
    pass
```

## Best Practices

### 1. Job Lifecycle Management

Always follow proper status transitions:

```bash
# 1. Create job
JOB_ID=$(curl -X POST .../agent-jobs -d '...' | jq -r '.job_id')

# 2. Acknowledge before starting work
curl -X POST .../agent-jobs/$JOB_ID/acknowledge

# 3. Complete or fail when done
curl -X POST .../agent-jobs/$JOB_ID/complete -d '{"result": {...}}'
```

### 2. Message Acknowledgment

Acknowledge messages to track processing:

```bash
# 1. Get messages
MESSAGES=$(curl .../agent-jobs/$JOB_ID/messages)

# 2. Process each message
for msg_id in $(echo $MESSAGES | jq -r '.messages[].message_id'); do
  # Process message...

  # 3. Acknowledge after processing
  curl -X POST .../agent-jobs/$JOB_ID/messages/$msg_id/acknowledge
done
```

### 3. Parent-Child Coordination

Coordinate child jobs properly:

```bash
# 1. Create parent
PARENT_ID=$(curl -X POST .../agent-jobs -d '...' | jq -r '.job_id')

# 2. Spawn children
CHILDREN=$(curl -X POST .../agent-jobs/$PARENT_ID/spawn-children -d '...')

# 3. Wait for all children to complete
# (poll or use WebSocket events)

# 4. Aggregate results and complete parent
curl -X POST .../agent-jobs/$PARENT_ID/complete -d '{"result": {...}}'
```

### 4. Error Handling

Always handle errors gracefully:

```javascript
async function acknowledgeJob(jobId) {
  try {
    const response = await fetch(`/api/agent-jobs/${jobId}/acknowledge`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` }
    });

    if (!response.ok) {
      const error = await response.json();
      console.error('Failed to acknowledge job:', error.detail);
      return null;
    }

    return await response.json();
  } catch (error) {
    console.error('Network error:', error);
    return null;
  }
}
```

## Summary

The Agent Jobs API provides comprehensive job management for multi-agent orchestration:

- **13 REST endpoints** for CRUD, status management, messaging, and hierarchy
- **Multi-tenant isolation** via tenant_key filtering
- **Role-based access control** (admin-only operations)
- **Real-time WebSocket events** for job updates
- **Flexible querying** with status, agent_type, and pagination filters

For more information:
- [Validation Guide](../HANDOVER_0019_VALIDATION_GUIDE.md) - Manual testing procedures
- [Testing Guide](../testing/HANDOVER_0019_TESTING_GUIDE.md) - Running automated tests
- [Security Verification](../security/HANDOVER_0019_TENANT_ISOLATION_VERIFICATION.md) - Multi-tenant isolation testing
