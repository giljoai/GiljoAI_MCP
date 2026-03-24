# Agent Jobs API Endpoints

**Document Version**: 1.0
**Implementation Date**: December 20, 2025
**Status**: Production Ready
**Related Handover**: 0366d - Agent Job Dual-Model Architecture

---

## Overview

This document provides complete API reference for agent job management endpoints, with focus on the dual-model architecture (AgentJob + AgentExecution) introduced in Handover 0366d. The dual-model separates persistent work orders from individual agent execution instances, enabling orchestrator succession tracking.

**Base URL**: `http://your-server:7272/api/v1`

**Authentication**: All endpoints require Bearer token authentication.

---

## Architecture Overview

GiljoAI MCP uses a dual-model architecture for agent job management:

- **AgentJob**: Persistent work order (mission, objectives) that survives agent succession
- **AgentExecution**: Individual agent instance working on a job (changes on succession)

This separation enables:
- Multiple agents to work on the same job sequentially (orchestrator succession)
- Full succession history tracking (who worked when, why they handed over)
- Context continuity across agent transitions (handover summaries)

---

## Table of Contents

1. [GET /jobs/{job_id}](#get-jobsjob_id)
2. [GET /jobs/{job_id}/executions](#get-jobsjob_idexecutions)
3. [GET /jobs/{job_id}/executions/{execution_id}](#get-jobsjob_idexecutionsexecution_id)
4. [Common Error Responses](#common-error-responses)
5. [WebSocket Events](#websocket-events)

---

## GET /jobs/{job_id}

Retrieve comprehensive job details including current execution information.

### Authentication

**Required**: Bearer token in Authorization header

### Request

**Endpoint**: `GET /api/v1/jobs/{job_id}`

**Path Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `job_id` | string (UUID) | Yes | Job ID to retrieve |

**Headers**:
```http
Authorization: Bearer {your_jwt_token}
Content-Type: application/json
```

**Request Body**: None

### Response

**Success (200 OK)**:
```json
{
  "id": 42,
  "job_id": "job_550e8400-e29b-41d4-a716-446655440000",
  "tenant_key": "tenant_abc123",
  "project_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "agent_type": "orchestrator",
  "agent_name": "Backend Refactoring Orchestrator",
  "mission": "Refactor backend services to improve modularity and testability",
  "status": "active",
  "progress": 65,
  "spawned_by": "agent_parent123",
  "tool_type": "claude-code",
  "context_chunks": ["chunk_abc", "chunk_xyz"],
  "messages": [
    {
      "id": "msg_001",
      "type": "user_message",
      "content": "Focus on the authentication service first",
      "timestamp": "2025-12-20T10:00:00Z",
      "acknowledged": true
    }
  ],
  "started_at": "2025-12-20T09:00:00Z",
  "completed_at": null,
  "created_at": "2025-12-20T08:55:00Z",
  "updated_at": "2025-12-20T10:30:00Z",
  "mission_acknowledged_at": "2025-12-20T09:01:00Z",
  "steps": {
    "completed": 4,
    "total": 7
  }
}
```

**Response Fields**:
| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Internal database ID |
| `job_id` | string | Unique job identifier (UUID) |
| `tenant_key` | string | Multi-tenant isolation key |
| `project_id` | string | Parent project UUID (nullable) |
| `agent_type` | string | Agent type (orchestrator, implementer, tester, etc.) |
| `agent_name` | string | Human-readable display name (nullable) |
| `mission` | string | Agent mission/instructions |
| `status` | string | Job status (active, completed, cancelled) |
| `progress` | integer | Completion progress 0-100% |
| `spawned_by` | string | Parent agent ID who spawned this job (nullable) |
| `tool_type` | string | AI coding agent assigned (claude-code, codex, gemini, universal) |
| `context_chunks` | array | Context chunk IDs associated with job |
| `messages` | array | Communication messages for agent |
| `started_at` | string (ISO 8601) | When first execution started (nullable) |
| `completed_at` | string (ISO 8601) | When job finished (nullable) |
| `created_at` | string (ISO 8601) | Job creation timestamp |
| `updated_at` | string (ISO 8601) | Last update timestamp (nullable) |
| `mission_acknowledged_at` | string (ISO 8601) | When agent first fetched mission (nullable) |
| `steps` | object | Todo-style progress {completed, total} (nullable) |

### Use Cases

- **Dashboard Display**: Show current job status, progress, and active agent
- **Agent Monitoring**: Check if agent acknowledged mission, last activity
- **Context Awareness**: Retrieve mission and context chunks for debugging
- **Message History**: View communication history between user and agent

### Error Responses

**404 Not Found** - Job does not exist or wrong tenant:
```json
{
  "detail": "Job not found"
}
```

**401 Unauthorized** - Missing or invalid authentication:
```json
{
  "detail": "Not authenticated"
}
```

**403 Forbidden** - Wrong tenant:
```json
{
  "detail": "Not authorized to access this job"
}
```

**500 Internal Server Error** - Database or service error:
```json
{
  "detail": "Internal server error retrieving job"
}
```

---

## GET /jobs/{job_id}/executions

List all agent execution instances for a specific job, showing complete succession timeline.

### Authentication

**Required**: Bearer token in Authorization header

### Request

**Endpoint**: `GET /api/v1/jobs/{job_id}/executions`

**Path Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `job_id` | string (UUID) | Yes | Job ID to retrieve executions for |

**Headers**:
```http
Authorization: Bearer {your_jwt_token}
Content-Type: application/json
```

**Request Body**: None

### Response

**Success (200 OK)**:
```json
[
  {
    "agent_id": "agent_a1b2c3d4e5f6",
    "job_id": "job_550e8400-e29b-41d4-a716-446655440000",
    "status": "complete",
    "progress": 100,
    "spawned_by": "orchestrator_parent_xyz",
    "succeeded_by": "agent_e5f6g7h8i9j0",
    "created_at": "2025-12-20T08:55:00Z",
    "updated_at": "2025-12-20T11:30:00Z"
  },
  {
    "agent_id": "agent_e5f6g7h8i9j0",
    "job_id": "job_550e8400-e29b-41d4-a716-446655440000",
    "status": "working",
    "progress": 65,
    "spawned_by": "agent_a1b2c3d4e5f6",
    "succeeded_by": null,
    "created_at": "2025-12-20T11:32:00Z",
    "updated_at": "2025-12-20T14:15:00Z"
  }
]
```

**Response Fields** (per execution):
| Field | Type | Description |
|-------|------|-------------|
| `agent_id` | string | Unique agent execution identifier (UUID) |
| `job_id` | string | Parent job identifier (UUID) |
| `status` | string | Execution status (waiting, working, blocked, complete, failed, cancelled, decommissioned) |
| `progress` | integer | Execution progress 0-100% |
| `spawned_by` | string | Agent ID who spawned this executor (nullable) |
| `succeeded_by` | string | Agent ID who took over from this executor (nullable) |
| `created_at` | string (ISO 8601) | When execution was created |
| `updated_at` | string (ISO 8601) | Last update timestamp (nullable) |

### Use Cases

- **Succession Timeline**: Display visual timeline of agent handovers
- **History Analysis**: Understand how work progressed through different agents
- **Debugging**: Trace which agent worked when, identify problematic executions
- **Context Tracking**: See succession reasons (context_limit, manual, phase_transition)

### Sorting

Executions are returned sorted by `created_at` ascending (chronological order).

### Error Responses

**404 Not Found** - Job does not exist or wrong tenant:
```json
{
  "detail": "Job not found"
}
```

**401 Unauthorized** - Missing or invalid authentication:
```json
{
  "detail": "Not authenticated"
}
```

**403 Forbidden** - Wrong tenant:
```json
{
  "detail": "Not authorized to access this job"
}
```

---

## GET /jobs/{job_id}/executions/{execution_id}

Retrieve detailed information about a specific agent execution instance.

### Authentication

**Required**: Bearer token in Authorization header

### Request

**Endpoint**: `GET /api/v1/jobs/{job_id}/executions/{execution_id}`

**Path Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `job_id` | string (UUID) | Yes | Parent job ID |
| `execution_id` | string (UUID) | Yes | Agent execution ID to retrieve |

**Headers**:
```http
Authorization: Bearer {your_jwt_token}
Content-Type: application/json
```

**Request Body**: None

### Response

**Success (200 OK)**:
```json
{
  "agent_id": "agent_a1b2c3d4e5f6",
  "job_id": "job_550e8400-e29b-41d4-a716-446655440000",
  "status": "complete",
  "progress": 100,
  "current_task": "Completed service layer refactoring",
  "succession_reason": "context_limit",
  "handover_summary": {
    "completed_tasks": ["Service extraction", "Endpoint modularization", "Test coverage"],
    "pending_tasks": ["Final integration testing", "Documentation updates"],
    "key_decisions": ["Used Pydantic for validation", "Chose async pattern"]
  },
  "spawned_by": "orchestrator_parent_xyz",
  "succeeded_by": "agent_e5f6g7h8i9j0",
  "started_at": "2025-12-20T08:55:00Z",
  "completed_at": "2025-12-20T11:30:00Z",
  "decommissioned_at": "2025-12-20T11:32:00Z",
  "created_at": "2025-12-20T08:55:00Z",
  "updated_at": "2025-12-20T11:30:00Z"
}
```

**Response Fields**:
| Field | Type | Description |
|-------|------|-------------|
| `agent_id` | string | Unique agent execution identifier (UUID) |
| `job_id` | string | Parent job identifier (UUID) |
| `status` | string | Execution status (waiting, working, blocked, complete, failed, cancelled, decommissioned) |
| `progress` | integer | Execution progress 0-100% |
| `current_task` | string | Description of current/last task (nullable) |
| `succession_reason` | string | Why succession occurred (context_limit, manual, phase_transition) (nullable) |
| `handover_summary` | object | Compressed state transfer for successor (nullable) |
| `spawned_by` | string | Agent ID who spawned this executor (nullable) |
| `succeeded_by` | string | Agent ID who took over from this executor (nullable) |
| `started_at` | string (ISO 8601) | When execution started (nullable) |
| `completed_at` | string (ISO 8601) | When execution finished (nullable) |
| `decommissioned_at` | string (ISO 8601) | When execution was retired after succession (nullable) |
| `created_at` | string (ISO 8601) | When execution was created |
| `updated_at` | string (ISO 8601) | Last update timestamp (nullable) |

### Use Cases

- **Detailed Execution View**: Show full execution details in UI
- **Handover Analysis**: Inspect succession reason and handover summary
- **Context Tracking**: Monitor context usage for orchestrators
- **Debugging**: Understand why execution ended, what state was transferred

### Error Responses

**404 Not Found** - Job or execution does not exist, or wrong tenant:
```json
{
  "detail": "Execution not found"
}
```

**401 Unauthorized** - Missing or invalid authentication:
```json
{
  "detail": "Not authenticated"
}
```

**403 Forbidden** - Wrong tenant:
```json
{
  "detail": "Not authorized to access this execution"
}
```

---

## Common Error Responses

All endpoints may return these common errors:

### 401 Unauthorized
**Cause**: Missing or invalid Bearer token

```json
{
  "detail": "Not authenticated"
}
```

**Solution**: Include valid JWT token in Authorization header

### 403 Forbidden
**Cause**: Multi-tenant isolation (wrong tenant_key)

```json
{
  "detail": "Not authorized to access this resource"
}
```

**Solution**: Ensure user has access to the requested tenant

### 404 Not Found
**Cause**: Resource does not exist or wrong tenant

```json
{
  "detail": "Resource not found"
}
```

**Solution**: Verify resource ID and tenant access

### 500 Internal Server Error
**Cause**: Database connection, service error, or unexpected exception

```json
{
  "detail": "Internal server error"
}
```

**Solution**: Check server logs, verify database connectivity

### 503 Service Unavailable
**Cause**: Database unavailable

```json
{
  "detail": "Database not available"
}
```

**Solution**: Verify PostgreSQL is running and accessible

---

## WebSocket Events

The agent jobs system emits real-time WebSocket events for UI synchronization. All events are tenant-scoped (no cross-tenant leakage).

### Event: execution:created

Emitted when a new agent execution is spawned (succession or initial spawn).

**Payload**:
```json
{
  "event_type": "execution:created",
  "tenant_key": "tenant_abc123",
  "job_id": "job_550e8400-e29b-41d4-a716-446655440000",
  "execution": {
    "agent_id": "agent_e5f6g7h8i9j0",
    "job_id": "job_550e8400-e29b-41d4-a716-446655440000",
    "status": "waiting",
    "progress": 0,
    "spawned_by": "agent_a1b2c3d4e5f6",
    "succeeded_by": null,
    "created_at": "2025-12-20T11:32:00Z",
    "updated_at": null
  }
}
```

**Use Case**: Update UI to show new agent instance in succession timeline

### Event: execution:status_changed

Emitted when an execution status changes (waiting → working, working → complete, etc.).

**Payload**:
```json
{
  "event_type": "execution:status_changed",
  "tenant_key": "tenant_abc123",
  "job_id": "job_550e8400-e29b-41d4-a716-446655440000",
  "agent_id": "agent_e5f6g7h8i9j0",
  "old_status": "waiting",
  "new_status": "working",
  "timestamp": "2025-12-20T11:35:00Z"
}
```

**Use Case**: Update status indicators in real-time, trigger UI transitions

### Event: execution:progress_update

Emitted when an execution reports progress (context usage, task completion).

**Payload**:
```json
{
  "event_type": "execution:progress_update",
  "tenant_key": "tenant_abc123",
  "job_id": "job_550e8400-e29b-41d4-a716-446655440000",
  "agent_id": "agent_e5f6g7h8i9j0",
  "progress": 45,
  "current_task": "Implementing test coverage",
  "timestamp": "2025-12-20T12:15:00Z"
}
```

**Use Case**: Update progress bars, context gauges, current task display

### Event: job:completed

Emitted when a job completes (all executions finished).

**Payload**:
```json
{
  "event_type": "job:completed",
  "tenant_key": "tenant_abc123",
  "job_id": "job_550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "completed_at": "2025-12-20T15:00:00Z",
  "final_execution_id": "agent_e5f6g7h8i9j0"
}
```

**Use Case**: Move job card to "Completed" column, show completion notification

---

## Multi-Tenant Isolation

All endpoints enforce strict multi-tenant isolation:

- All queries filter by `tenant_key` from authenticated user's JWT token
- Cross-tenant access returns 404 (not 403, to avoid leaking existence)
- WebSocket events are tenant-scoped (no cross-tenant broadcast)
- Database indexes include `tenant_key` for performance

---

## Related Documentation

- **User Guide**: [docs/user_guides/agent_monitoring_guide.md](../user_guides/agent_monitoring_guide.md)
- **Architecture**: [docs/SERVER_ARCHITECTURE_TECH_STACK.md](../SERVER_ARCHITECTURE_TECH_STACK.md)
- **Orchestrator**: [docs/ORCHESTRATOR.md](../ORCHESTRATOR.md)
- **Handover**: [handovers/0366d-4_installation_documentation.md](../../handovers/0366d-4_installation_documentation.md)

---

## Support

For implementation details or questions:
1. Check related documentation above
2. Review source code in `api/endpoints/agent_jobs/`
3. Consult database schema in `src/giljo_mcp/models/agent_identity.py`
4. Check service layer in `src/giljo_mcp/services/orchestration_service.py`
