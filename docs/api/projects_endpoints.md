# Projects API Endpoints

**Document Version**: 1.0
**Implementation Date**: October 28, 2025
**Status**: Production Ready
**Related Handover**: 0071 - Simplified Project State Management

---

## Overview

This document provides complete API reference for project management endpoints, with focus on the simplified 5-state project lifecycle and enhanced validation rules introduced in Handover 0071.

**Base URL**: `http://your-server:7272/api/v1`

**Authentication**: All endpoints require Bearer token authentication.

---

## Activation Rules and Constraints (Handovers 0050b/0071)

- Single Active Project per Product (0050b): Only ONE project may be `active` for a given product at any time.
- Enforcement:
  - Database: partial unique index on `projects(product_id) WHERE status = 'active'`.
  - API: activation endpoints validate and return clear errors if another project is active.
- Product Switch Cascade: when the active product changes, previously active projects under the old product are set to Inactive (see features/project_state_management.md).

See also: features/project_state_management.md and SERVER_ARCHITECTURE_TECH_STACK.md for full rationale and schema details.

## Table of Contents

1. [POST /projects/{project_id}/deactivate](#post-projectsproject_iddeactivate)
2. [PATCH /projects/{project_id}](#patch-projectsproject_id)
3. [GET /projects/deleted](#get-projectsdeleted)
4. [POST /projects/{project_id}/restore](#post-projectsproject_idrestore)
5. [Common Error Responses](#common-error-responses)
7. [WebSocket Events](#websocket-events)

---

## POST /projects/{project_id}/deactivate

Deactivate an active project, freeing up the active project slot for the product.

### Authentication

**Required**: Bearer token in Authorization header

### Request

**Endpoint**: `POST /api/v1/projects/{project_id}/deactivate`

**Path Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project_id` | string (UUID) | Yes | ID of project to deactivate |

**Headers**:
```http
Authorization: Bearer {your_jwt_token}
Content-Type: application/json
```

**Request Body**: None required

### Response

**Success (200 OK)**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "tenant_key": "default",
  "product_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "name": "Website Redesign",
  "alias": "WEBR01",
  "mission": "Redesign company website with modern UI/UX",
  "status": "inactive",
  "created_at": "2025-10-28T10:00:00Z",
  "updated_at": "2025-10-28T14:30:00Z",
  "completed_at": null,
  "deleted_at": null
}
```

**Response Fields**:
| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Project UUID |
| `tenant_key` | string | Multi-tenant isolation key |
| `product_id` | string | Parent product UUID |
| `name` | string | Project name |
| `alias` | string | Short project alias (e.g., WEBR01) |
| `mission` | string | Project mission statement |
| `status` | string | Project status (now "inactive") |
| `created_at` | string (ISO 8601) | Creation timestamp |
| `updated_at` | string (ISO 8601) | Last update timestamp |
| `completed_at` | string (ISO 8601) | Completion timestamp (null) |
| `deleted_at` | string (ISO 8601) | Deletion timestamp (null) |

### Error Responses

**404 Not Found** - Project does not exist:
```json
{
  "detail": "Project not found"
}
```

**403 Forbidden** - Wrong tenant:
```json
{
  "detail": "Not authorized to access this project"
}
```

**400 Bad Request** - Project not active:
```json
{
  "detail": "Cannot deactivate project with status 'inactive'. Only active projects can be deactivated."
}
```

**400 Bad Request** - Project deleted:
```json
{
  "detail": "Cannot deactivate project with status 'deleted'. Only active projects can be deactivated."
}
```

**503 Service Unavailable** - Database unavailable:
```json
{
  "detail": "Database not available"
}
```

### WebSocket Event

After successful deactivation, a WebSocket event is broadcast to all clients in the same tenant:

**Event**: `project:deactivated`

**Payload**:
```json
{
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "inactive",
  "tenant_key": "default",
  "product_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7"
}
```

### Data Preservation

Deactivating a project preserves all data:
- ✅ Project metadata (name, alias, mission)
- ✅ Mission created by orchestrator
- ✅ Assigned agents (set to inactive status)
- ✅ All generated context
- ✅ MCP communication history
- ✅ Task history
- ✅ Agent job records

**Nothing is deleted**. The project is simply marked as inactive and removed from the active slot.

### Use Cases

**Use deactivate when**:
1. Temporarily stopping work on a project
2. Switching focus to another project
3. Need to free up the active project slot
4. Project on hold pending external dependencies

**Example Workflow**:
```bash
# User has "Mobile App" active but needs to work on "Bug Fixes"

# Step 1: Deactivate current active project
curl -X POST \
  https://your-server/api/v1/projects/550e8400-e29b-41d4-a716-446655440000/deactivate \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json"

# Step 2: Activate the desired project (via PATCH endpoint)
curl -X PATCH \
  https://your-server/api/v1/projects/7c9e6679-7425-40de-944b-e07fc1f90ae7 \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{"status": "active"}'
```

---

## PATCH /projects/{project_id}

Update project properties, including status transitions.

### Enhanced Validation (Handover 0071)

**New Validation**: When activating a project (setting `status` to `"active"`), the endpoint now validates that no other project is active for the same product.

### Authentication

**Required**: Bearer token in Authorization header

### Request

**Endpoint**: `PATCH /api/v1/projects/{project_id}`

**Path Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project_id` | string (UUID) | Yes | ID of project to update |

**Headers**:
```http
Authorization: Bearer {your_jwt_token}
Content-Type: application/json
```

**Request Body**:
```json
{
  "status": "active"
}
```

**Updatable Fields**:
| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Project name |
| `mission` | string | Project mission statement |
| `status` | string | Project status (active, inactive, completed, cancelled) |

### Response

**Success (200 OK)**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "tenant_key": "default",
  "product_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "name": "Website Redesign",
  "status": "active",
  "updated_at": "2025-10-28T14:45:00Z"
}
```

### Error Responses

**400 Bad Request** - Another project already active:
```json
{
  "detail": "Another project ('Mobile App') is already active for this product. Please deactivate it first."
}
```

**Example Error Scenario**:
```bash
# Attempt to activate project when another is already active
curl -X PATCH \
  https://your-server/api/v1/projects/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{"status": "active"}'

# Response (if another project is active):
# HTTP 400 Bad Request
# {
#   "detail": "Another project ('Mobile App') is already active for this product. Please deactivate it first."
# }
```

**Resolution**: Deactivate the currently active project first, then activate the desired project.

**404 Not Found** - Project does not exist:
```json
{
  "detail": "Project not found"
}
```

**403 Forbidden** - Wrong tenant:
```json
{
  "detail": "Not authorized to access this project"
}
```

### Database Constraint

The single active project rule is enforced by a database constraint:

```sql
CREATE UNIQUE INDEX idx_project_single_active_per_product
ON projects (product_id)
WHERE status = 'active';
```

**Constraint Behavior**:
- Atomic enforcement (no race conditions)
- Immediate error on violation
- Application catches constraint violation and returns user-friendly error

**Database Error** (if constraint violated):
```
Duplicate key value violates unique constraint "idx_project_single_active_per_product"
```

**Application Handling**: API layer catches this and returns:
```json
{
  "detail": "Another project is already active for this product. Database constraint violation."
}
```

### Valid Status Transitions

**From ACTIVE**:
- → `inactive` (deactivate)
- → `completed` (complete successfully)
- → `cancelled` (abandon)

**From INACTIVE**:
- → `active` (activate - validates single active rule)

**From COMPLETED or CANCELLED**:
- → `active` (reopen - validates single active rule)

**Invalid Transitions**:
- Any status → `deleted` (use DELETE endpoint instead)

---

## GET /projects/deleted

List deleted projects with recovery countdown (product-scoped).

### Enhanced Filtering (Handover 0071)

**New Behavior**: Returns only deleted projects for the **active product**.

**Product Scoping Logic**:
1. Find active product for current tenant
2. If active product exists: Return that product's deleted projects
3. If no active product: Return empty array `[]`

### Authentication

**Required**: Bearer token in Authorization header

### Request

**Endpoint**: `GET /api/v1/projects/deleted`

**Headers**:
```http
Authorization: Bearer {your_jwt_token}
```

**Query Parameters**: None

### Response

**Success (200 OK)**:
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Old Website Redesign",
    "product_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "product_name": "Main Product",
    "deleted_at": "2025-10-20T10:00:00Z",
    "days_until_purge": 2
  },
  {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "name": "Test Project",
    "product_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "product_name": "Main Product",
    "deleted_at": "2025-10-25T15:30:00Z",
    "days_until_purge": 7
  }
]
```

**Response Fields**:
| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Project UUID |
| `name` | string | Project name |
| `product_id` | string | Parent product UUID |
| `product_name` | string | Parent product name |
| `deleted_at` | string (ISO 8601) | Deletion timestamp |
| `days_until_purge` | integer | Days remaining before permanent deletion |

**Empty Response** (no active product):
```json
[]
```

**Empty Response** (active product exists, no deleted projects):
```json
[]
```

### Purge Countdown Calculation

**Formula**: `days_until_purge = 10 - DAYS_BETWEEN(NOW(), deleted_at)`

**Examples**:
- Deleted today: `days_until_purge = 10`
- Deleted 3 days ago: `days_until_purge = 7`
- Deleted 9 days ago: `days_until_purge = 1`
- Deleted 10+ days ago: Auto-purged (won't appear in results)

**Auto-Purge**: Projects with `days_until_purge <= 0` are automatically purged on next application startup.

### Use Case

**Scenario**: User wants to recover accidentally deleted projects.

**Example**:
```bash
# List deleted projects for active product
curl -X GET \
  https://your-server/api/v1/projects/deleted \
  -H "Authorization: Bearer your-token"

# Response shows deleted projects with recovery window:
# [
#   {
#     "id": "550e8400-e29b-41d4-a716-446655440000",
#     "name": "Old Website Redesign",
#     "product_name": "Main Product",
#     "deleted_at": "2025-10-20T10:00:00Z",
#     "days_until_purge": 2  ⚠️ Urgent - only 2 days left!
#   }
# ]

# Restore the project (see next endpoint)
curl -X POST \
  https://your-server/api/v1/projects/550e8400-e29b-41d4-a716-446655440000/restore \
  -H "Authorization: Bearer your-token"
```

### Multi-Tenant Isolation

**Enforcement**: All queries filtered by `tenant_key` from JWT token.

**Cross-Tenant Protection**: Users can only see deleted projects from their own tenant, scoped to their active product.

**Example**:
- Tenant A active product: "Product X"
- Tenant A deleted projects shown: Only "Product X" deleted projects
- Tenant B deleted projects: Not visible to Tenant A

---

## POST /projects/{project_id}/restore

Restore a deleted project to inactive status.

### Authentication

**Required**: Bearer token in Authorization header

### Request

**Endpoint**: `POST /api/v1/projects/{project_id}/restore`

**Path Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project_id` | string (UUID) | Yes | ID of deleted project to restore |

**Headers**:
```http
Authorization: Bearer {your_jwt_token}
Content-Type: application/json
```

**Request Body**: None required

### Response

**Success (200 OK)**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "tenant_key": "default",
  "product_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "name": "Website Redesign",
  "status": "inactive",
  "deleted_at": null,
  "updated_at": "2025-10-28T15:00:00Z"
}
```

**Restored Status**: Projects are always restored to `"inactive"` status (safe default).

**Reason**: Prevents accidentally activating a project when another project is already active for the product.

### Error Responses

**404 Not Found** - Project does not exist or not deleted:
```json
{
  "detail": "Deleted project not found"
}
```

**400 Bad Request** - Project not deleted:
```json
{
  "detail": "Project is not deleted (status: 'active'). Only deleted projects can be restored."
}
```

**410 Gone** - Project purged (>10 days):
```json
{
  "detail": "Project was permanently purged. Recovery window expired."
}
```

**403 Forbidden** - Wrong tenant:
```json
{
  "detail": "Not authorized to access this project"
}
```

### Recovery Window

**Duration**: 10 days from deletion

**Purge Behavior**:
- Projects older than 10 days: Auto-purged on application startup
- Purged projects: Permanently deleted (cannot be restored)

**Cascade Delete on Purge**:
When a project is purged, all related data is permanently deleted:
- Agents assigned to project
- Tasks created for project
- Messages in project context
- Agent jobs for project

### Use Case

**Example**: User accidentally deleted a project and wants to recover it.

```bash
# Step 1: List deleted projects
curl -X GET \
  https://your-server/api/v1/projects/deleted \
  -H "Authorization: Bearer your-token"

# Response shows deleted projects with countdown:
# [
#   {
#     "id": "550e8400-e29b-41d4-a716-446655440000",
#     "name": "Website Redesign",
#     "days_until_purge": 8
#   }
# ]

# Step 2: Restore the project
curl -X POST \
  https://your-server/api/v1/projects/550e8400-e29b-41d4-a716-446655440000/restore \
  -H "Authorization: Bearer your-token"

# Response:
# {
#   "id": "550e8400-e29b-41d4-a716-446655440000",
#   "name": "Website Redesign",
#   "status": "inactive",  ← Restored to inactive
#   "deleted_at": null     ← No longer deleted
# }

# Step 3: Activate if desired (via PATCH endpoint)
curl -X PATCH \
  https://your-server/api/v1/projects/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{"status": "active"}'
```

### Idempotency

**Behavior**: Restoring an already-restored project is safe (idempotent).

**Example**:
- First restore: Sets `status = 'inactive'`, `deleted_at = NULL`
- Second restore: Returns 400 error ("Project is not deleted")

---

## Common Error Responses

### Authentication Errors

**401 Unauthorized** - Missing or invalid token:
```json
{
  "detail": "Not authenticated"
}
```

**Resolution**: Include valid JWT token in Authorization header.

### Authorization Errors

**403 Forbidden** - Wrong tenant:
```json
{
  "detail": "Not authorized to access this project"
}
```

**Cause**: Project belongs to different tenant than authenticated user.

**Multi-Tenant Isolation**: All endpoints enforce tenant isolation via `tenant_key` filtering.

### Validation Errors

**400 Bad Request** - Invalid status transition:
```json
{
  "detail": "Invalid status transition from 'deleted' to 'active'"
}
```

**422 Unprocessable Entity** - Invalid request body:
```json
{
  "detail": [
    {
      "loc": ["body", "status"],
      "msg": "value is not a valid enumeration member; permitted: 'active', 'inactive', 'completed', 'cancelled'",
      "type": "type_error.enum"
    }
  ]
}
```

### Database Errors

**503 Service Unavailable** - Database connection failure:
```json
{
  "detail": "Database not available"
}
```

**Resolution**: Check database connection, ensure PostgreSQL is running.

**500 Internal Server Error** - Unexpected server error:
```json
{
  "detail": "Internal server error"
}
```

**Resolution**: Check server logs for detailed error information.

---

## WebSocket Events

### Overview

All project state changes trigger WebSocket events broadcast to all clients in the same tenant.

**Connection**: `ws://your-server:7272/ws/{client_id}?token={jwt_token}`

**Authentication**: JWT token required via query parameter.

### Event: project:deactivated

**Trigger**: Project deactivated via POST /projects/{id}/deactivate

**Payload**:
```json
{
  "event": "project:deactivated",
  "data": {
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "inactive",
    "tenant_key": "default",
    "product_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7"
  }
}
```

### Event: project:updated

**Trigger**: Project updated via PATCH /projects/{id}

**Payload**:
```json
{
  "event": "project:updated",
  "data": {
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "active",
    "tenant_key": "default",
    "updated_fields": ["status"]
  }
}
```

### Event: project:restored

**Trigger**: Project restored via POST /projects/{id}/restore

**Payload**:
```json
{
  "event": "project:restored",
  "data": {
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "inactive",
    "tenant_key": "default",
    "deleted_at": null
  }
}
```

### Client-Side Handling

**Example (JavaScript)**:
```javascript
const ws = new WebSocket(`ws://your-server:7272/ws/client-123?token=${token}`);

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);

  if (message.event === 'project:deactivated') {
    console.log(`Project ${message.data.project_id} deactivated`);
    // Update UI to reflect inactive status
    updateProjectStatus(message.data.project_id, 'inactive');
  }

  if (message.event === 'project:updated') {
    console.log(`Project ${message.data.project_id} updated`);
    // Reload project data
    fetchProjectDetails(message.data.project_id);
  }
};
```

---

## Rate Limiting

**Default Limit**: 60 requests per minute per IP address

**Headers** (included in response):
```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1698505200
```

**429 Too Many Requests**:
```json
{
  "detail": "Rate limit exceeded. Try again in 30 seconds."
}
```

---

## Related Documentation

- [Project State Management Guide](../features/project_state_management.md) - User guide
- [Server Architecture](../SERVER_ARCHITECTURE_TECH_STACK.md) - Database schema
- [OpenAPI Specification](http://localhost:7272/docs) - Interactive API docs
- [Handover 0071](../../handovers/0071_simplified_project_state_management.md) - Implementation details

---

**Last Updated**: October 28, 2025
**Document Maintainer**: Documentation Manager Agent
**API Version**: v1
