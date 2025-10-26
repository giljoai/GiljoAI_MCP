# Multi-Tool Agent Orchestration - API Reference

**Version**: 3.1.0
**Last Updated**: 2025-10-25
**Base URL**: `http://localhost:7272`

---

## Table of Contents

1. [Agent Endpoints](#agent-endpoints)
2. [Job Endpoints](#job-endpoints)
3. [Template Endpoints](#template-endpoints)
4. [MCP Tool Endpoints](#mcp-tool-endpoints)
5. [WebSocket Events](#websocket-events)
6. [Error Codes](#error-codes)

---

## Agent Endpoints

### POST /api/v1/agents

Create new agent (automatically routes to correct AI tool based on template).

**Request**:
```json
{
  "project_id": "proj_abc123",
  "agent_name": "Implementer-001",
  "role": "implementer",
  "mission": "Implement user authentication with JWT"
}
```

**Response**: `201 Created`
```json
{
  "id": "agent_xyz789",
  "name": "Implementer-001",
  "project_id": "proj_abc123",
  "role": "implementer",
  "status": "active",
  "mode": "codex",
  "job_id": "job_abc123",
  "mission": "Implement user authentication with JWT",
  "created_at": "2025-10-25T10:30:00Z",
  "health": {
    "status": "healthy",
    "context_used": 0
  }
}
```

**Error Responses**:
- `400 Bad Request`: Invalid parameters
- `403 Forbidden`: Permission denied (tenant isolation)
- `404 Not Found`: Project or template not found
- `500 Internal Server Error`: Server error

---

### GET /api/v1/agents/{id}/cli-prompt

Get CLI prompt for legacy mode agents (Codex/Gemini).

**Response**: `200 OK`
```json
{
  "agent_id": "agent_xyz789",
  "mode": "codex",
  "tool": "codex",
  "cli_prompt": "# OpenAI Codex Agent - GiljoAI MCP Integration\n\n[Full prompt content with MCP instructions...]",
  "requires_manual_start": true
}
```

**Use Case**: Frontend copies `cli_prompt` to clipboard for user to paste into CLI tool.

---

### GET /api/v1/agents/{id}

Get agent details.

**Response**: `200 OK`
```json
{
  "id": "agent_xyz789",
  "name": "Implementer-001",
  "project_id": "proj_abc123",
  "role": "implementer",
  "status": "active",
  "mode": "codex",
  "job_id": "job_abc123",
  "mission": "Implement user authentication with JWT",
  "context_used": 1500,
  "last_active": "2025-10-25T11:45:00Z",
  "created_at": "2025-10-25T10:30:00Z",
  "meta_data": {
    "cli_prompt": "[prompt]",
    "tool": "codex",
    "requires_manual_start": true
  }
}
```

---

## Job Endpoints

### GET /api/v1/jobs

List jobs with filtering.

**Query Parameters**:
- `status` (optional): Filter by status (waiting_acknowledgment, in_progress, completed, failed)
- `tool` (optional): Filter by AI tool (claude, codex, gemini)
- `agent_id` (optional): Filter by agent
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Results per page (default: 20)

**Response**: `200 OK`
```json
{
  "jobs": [
    {
      "id": "job_abc123",
      "agent_id": "agent_xyz789",
      "agent_name": "Implementer-001",
      "tool": "codex",
      "mode": "legacy_cli",
      "status": "in_progress",
      "progress": 65,
      "mission": "Implement user authentication with JWT",
      "created_at": "2025-10-25T10:30:00Z",
      "acknowledged_at": "2025-10-25T10:32:00Z",
      "last_update": "2025-10-25T11:45:00Z"
    }
  ],
  "total": 42,
  "page": 1,
  "page_size": 20
}
```

---

### GET /api/v1/jobs/{job_id}

Get job details.

**Response**: `200 OK`
```json
{
  "id": "job_abc123",
  "tenant_key": "tenant_xyz",
  "agent_id": "agent_xyz789",
  "agent_name": "Implementer-001",
  "tool": "codex",
  "mode": "legacy_cli",
  "mission": "Implement user authentication with JWT",
  "status": "in_progress",
  "priority": "normal",
  "progress": 65,
  "created_at": "2025-10-25T10:30:00Z",
  "acknowledged_at": "2025-10-25T10:32:00Z",
  "completed_at": null,
  "summary": null,
  "error_details": null,
  "parent_job_id": null,
  "meta_data": {}
}
```

---

### GET /api/v1/jobs/{job_id}/messages

Get inter-agent messages for job.

**Response**: `200 OK`
```json
{
  "messages": [
    {
      "message_id": "msg_001",
      "from_agent_id": "agent_xyz789",
      "from_agent_name": "Implementer-001",
      "to_agent_id": "agent_abc456",
      "to_agent_name": "Orchestrator-001",
      "message": "Question: Should token expiration be configurable?",
      "priority": "normal",
      "acknowledged": true,
      "created_at": "2025-10-25T11:20:00Z",
      "acknowledged_at": "2025-10-25T11:22:00Z"
    }
  ],
  "total": 1
}
```

---

### GET /api/v1/jobs/statistics

Get job statistics by tool.

**Response**: `200 OK`
```json
{
  "total_jobs": 42,
  "by_status": {
    "waiting_acknowledgment": 3,
    "in_progress": 8,
    "completed": 30,
    "failed": 1
  },
  "by_tool": {
    "claude": {
      "total": 15,
      "avg_completion_time_minutes": 45,
      "success_rate": 0.93
    },
    "codex": {
      "total": 18,
      "avg_completion_time_minutes": 30,
      "success_rate": 0.89
    },
    "gemini": {
      "total": 9,
      "avg_completion_time_minutes": 25,
      "success_rate": 0.88
    }
  },
  "avg_completion_time_minutes": 35,
  "overall_success_rate": 0.90
}
```

---

## Template Endpoints

### PATCH /api/v1/templates/{id}

Update template (including preferred_tool).

**Request**:
```json
{
  "preferred_tool": "codex",
  "content": "Updated template content...",
  "behavioral_rules": ["Rule 1", "Rule 2"],
  "success_criteria": ["Criterion 1", "Criterion 2"]
}
```

**Response**: `200 OK`
```json
{
  "id": "template_001",
  "tenant_key": "tenant_xyz",
  "name": "Implementer",
  "role": "implementer",
  "preferred_tool": "codex",
  "content": "Updated template content...",
  "version": "1.1.0",
  "updated_at": "2025-10-25T12:00:00Z"
}
```

---

### POST /api/v1/templates/export/claude-code

Export templates for Claude Code.

**Request**:
```json
{
  "tenant_key": "tenant_xyz",
  "include_product_specific": true
}
```

**Response**: `200 OK`
```json
{
  "export_id": "export_001",
  "download_url": "/api/v1/exports/export_001/download",
  "templates_count": 6,
  "created_at": "2025-10-25T12:00:00Z"
}
```

---

## MCP Tool Endpoints

### POST /mcp/get_pending_jobs

Get jobs waiting for agent acknowledgment.

**Request**:
```json
{
  "agent_id": "agent_xyz789",
  "tenant_key": "tenant_xyz"
}
```

**Response**: `200 OK`
```json
{
  "jobs": [
    {
      "job_id": "job_abc123",
      "mission": "Implement user authentication",
      "priority": "high",
      "created_at": "2025-10-25T10:30:00Z"
    }
  ]
}
```

---

### POST /mcp/acknowledge_job

Acknowledge job (agent started working).

**Request**:
```json
{
  "job_id": "job_abc123",
  "agent_id": "agent_xyz789",
  "tenant_key": "tenant_xyz"
}
```

**Response**: `200 OK`
```json
{
  "success": true,
  "message": "Job acknowledged, status updated to in_progress",
  "job_id": "job_abc123",
  "status": "in_progress"
}
```

---

### POST /mcp/report_progress

Report progress checkpoint.

**Request**:
```json
{
  "job_id": "job_abc123",
  "progress_data": {
    "percentage": 50,
    "message": "JWT token generation implemented",
    "details": "Created signing and verification logic"
  }
}
```

**Response**: `200 OK`
```json
{
  "success": true,
  "message": "Progress reported successfully",
  "job_id": "job_abc123",
  "progress": 50
}
```

---

### POST /mcp/get_next_instruction

Get latest instruction from Orchestrator.

**Request**:
```json
{
  "job_id": "job_abc123",
  "tenant_key": "tenant_xyz"
}
```

**Response**: `200 OK`
```json
{
  "instruction": "Updated requirement: Token expiration configurable via env var",
  "from_agent": "Orchestrator-001",
  "timestamp": "2025-10-25T11:25:00Z"
}
```

---

### POST /mcp/complete_job

Mark job as completed.

**Request**:
```json
{
  "job_id": "job_abc123",
  "summary": "User authentication implemented successfully. All tests passing.",
  "tenant_key": "tenant_xyz"
}
```

**Response**: `200 OK`
```json
{
  "success": true,
  "message": "Job marked as completed",
  "job_id": "job_abc123",
  "status": "completed",
  "completed_at": "2025-10-25T12:00:00Z"
}
```

---

### POST /mcp/report_error

Report critical error.

**Request**:
```json
{
  "job_id": "job_abc123",
  "error_details": {
    "error_type": "dependency_missing",
    "message": "jsonwebtoken package not found",
    "stack_trace": "[stack trace]",
    "recovery_suggestion": "Add jsonwebtoken to package.json"
  },
  "tenant_key": "tenant_xyz"
}
```

**Response**: `200 OK`
```json
{
  "success": true,
  "message": "Error reported, job marked as failed",
  "job_id": "job_abc123",
  "status": "failed"
}
```

---

### POST /mcp/send_message

Send message to another agent.

**Request**:
```json
{
  "from_agent_id": "agent_xyz789",
  "to_agent_id": "agent_abc456",
  "message": "Question: Should token expiration be configurable?",
  "priority": "normal",
  "tenant_key": "tenant_xyz"
}
```

**Response**: `200 OK`
```json
{
  "success": true,
  "message_id": "msg_001",
  "message": "Message sent successfully"
}
```

---

## WebSocket Events

Connect to WebSocket: `ws://localhost:7272/ws?tenant_key=<tenant_key>`

### agent:status_changed

Agent status changed.

**Event**:
```json
{
  "event": "agent:status_changed",
  "data": {
    "agent_id": "agent_xyz789",
    "agent_name": "Implementer-001",
    "project_id": "proj_abc123",
    "status": "active",
    "mode": "codex",
    "timestamp": "2025-10-25T10:30:00Z"
  }
}
```

---

### job:status_changed

Job status changed.

**Event**:
```json
{
  "event": "job:status_changed",
  "data": {
    "job_id": "job_abc123",
    "agent_id": "agent_xyz789",
    "status": "in_progress",
    "previous_status": "waiting_acknowledgment",
    "timestamp": "2025-10-25T10:32:00Z"
  }
}
```

---

### job:completed

Job completed successfully.

**Event**:
```json
{
  "event": "job:completed",
  "data": {
    "job_id": "job_abc123",
    "agent_id": "agent_xyz789",
    "summary": "User authentication implemented successfully",
    "completed_at": "2025-10-25T12:00:00Z"
  }
}
```

---

### job:failed

Job failed with error.

**Event**:
```json
{
  "event": "job:failed",
  "data": {
    "job_id": "job_abc123",
    "agent_id": "agent_xyz789",
    "error_details": {
      "error_type": "dependency_missing",
      "message": "jsonwebtoken package not found"
    },
    "failed_at": "2025-10-25T11:50:00Z"
  }
}
```

---

## Error Codes

### HTTP Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| 200 | OK | Successful operation |
| 201 | Created | Agent created successfully |
| 400 | Bad Request | Invalid parameters |
| 403 | Forbidden | Tenant isolation violation |
| 404 | Not Found | Resource not found |
| 500 | Internal Server Error | Server error |

### Application Error Codes

| Code | Description | HTTP Status |
|------|-------------|-------------|
| `invalid_input` | Invalid request parameters | 400 |
| `forbidden` | Permission denied (tenant mismatch) | 403 |
| `not_found` | Resource not found | 404 |
| `internal_error` | Unexpected server error | 500 |
| `rate_limited` | Too many requests | 429 |
| `job_not_found` | Job ID doesn't exist | 404 |
| `agent_not_found` | Agent ID doesn't exist | 404 |
| `template_not_found` | Template not found | 404 |
| `tool_not_supported` | AI tool not supported | 400 |

---

**Document Version**: 1.0
**Last Updated**: 2025-10-25
