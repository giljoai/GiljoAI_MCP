# Exception Mapping for Service Layer

**Handover:** 0730a Design Response Models
**Created:** 2026-02-07
**Purpose:** Document exception-to-HTTP-status mapping and exception hierarchy for service layer migration

---

## Exception Hierarchy Overview

The GiljoAI MCP exception hierarchy is defined in `src/giljo_mcp/exceptions.py`. All exceptions inherit from `BaseGiljoError` and carry a `default_status_code` for HTTP response mapping.

```
BaseGiljoError (500)
├── ConfigurationError (500)
│   └── ConfigValidationError (500)
├── TemplateError (500)
│   └── TemplateNotFoundError (404)
├── OrchestrationError (500)
│   ├── AgentCreationError (500)
│   ├── AgentCommunicationError (500)
│   ├── ProjectStateError (500)
│   └── HandoffError (500)
├── DatabaseError (500)
│   ├── DatabaseConnectionError (500)
│   ├── DatabaseMigrationError (500)
│   └── DatabaseIntegrityError (500)
├── ValidationError (400)
│   ├── SchemaValidationError (400)
│   └── DataValidationError (400)
├── QueueError (500)
│   ├── ConsistencyError (500)
│   └── MessageDeliveryError (500)
├── APIError (500)
│   ├── AuthenticationError (401)
│   ├── AuthorizationError (403)
│   └── RateLimitError (429)
├── ResourceError (500)
│   ├── ResourceNotFoundError (404)
│   ├── ResourceExhaustedError (500)
│   └── RetryExhaustedError (500)
├── ContextError (500)
│   └── ContextLimitError (500)
├── SessionError (500)
│   └── SessionExpiredError (500)
├── FileSystemError (500)
│   ├── GiljoFileNotFoundError (500)
│   └── GiljoPermissionError (500)
├── MCPError (500)
│   ├── ToolError (500)
│   └── ProtocolError (500)
└── VisionError (500)
    ├── VisionChunkingError (500)
    └── VisionParsingError (500)
```

---

## HTTP Status Code Mapping

| HTTP Status | Exception Class | Use Case |
|-------------|-----------------|----------|
| **400** | `ValidationError` | Invalid input, schema validation failure |
| **401** | `AuthenticationError` | Invalid credentials, missing token |
| **403** | `AuthorizationError` | Insufficient permissions, access denied |
| **404** | `ResourceNotFoundError` | Entity not found (user, org, product, etc.) |
| **404** | `TemplateNotFoundError` | Agent template not found |
| **409** | `AlreadyExistsError` | **PROPOSED** - Duplicate resource (slug, username) |
| **422** | FastAPI `RequestValidationError` | Request body validation (handled separately) |
| **429** | `RateLimitError` | Rate limit exceeded |
| **500** | `BaseGiljoError` | Catch-all for internal errors |
| **500** | `DatabaseError` | Database operation failures |
| **500** | `OrchestrationError` | Agent spawning, workflow failures |

---

## Exception Hierarchy Gap Analysis

### Missing Exception: AlreadyExistsError (409)

**Current State:** Services return `{"success": False, "error": "... already exists"}` for duplicate resources.

**Proposed Addition:**
```python
class AlreadyExistsError(BaseGiljoError):
    """Raised when attempting to create a resource that already exists."""
    default_status_code: int = 409
```

**Use Cases:**
- OrgService: `create_organization` - slug already exists
- OrgService: `invite_member` - user already a member
- UserService: `create_user` - username/email already exists
- ProductService: `create_product` - product name already exists

**Implementation Location:** Add to `src/giljo_mcp/exceptions.py`

---

### Gap: ProjectStateError Should Be 400, Not 500

**Current State:** `ProjectStateError` inherits `default_status_code = 500` from `OrchestrationError`.

**Issue:** Invalid state transitions (e.g., trying to complete a non-active project) are **client errors**, not server errors. The client is requesting an invalid operation.

**Proposed Fix:**
```python
class ProjectStateError(OrchestrationError):
    """Raised when project state is invalid for requested operation."""
    default_status_code: int = 400  # Override to 400 for client error
```

**Use Cases:**
- `complete_project` - project not in completable state
- `activate_project` - project already active or in invalid state
- `deactivate_project` - cannot deactivate with current status
- `cancel_staging` - cannot cancel staging for project with current status
- `change_execution_mode` - cannot change mode after staging

**Implementation Location:** Update in `src/giljo_mcp/exceptions.py` during 0730b

---

## Service-Specific Exception Usage

### OrgService Exceptions

| Method | Error Condition | Exception | HTTP |
|--------|-----------------|-----------|------|
| `create_organization` | Slug exists | `AlreadyExistsError` | 409 |
| `create_organization` | DB error | `DatabaseError` | 500 |
| `get_organization` | Org not found | `ResourceNotFoundError` | 404 |
| `update_organization` | Org not found | `ResourceNotFoundError` | 404 |
| `delete_organization` | Org not found | `ResourceNotFoundError` | 404 |
| `invite_member` | Already member | `AlreadyExistsError` | 409 |
| `invite_member` | Invalid role | `ValidationError` | 400 |
| `remove_member` | Not a member | `ResourceNotFoundError` | 404 |
| `remove_member` | Is owner | `AuthorizationError` | 403 |
| `change_member_role` | Not a member | `ResourceNotFoundError` | 404 |
| `change_member_role` | Is owner | `AuthorizationError` | 403 |
| `change_member_role` | Invalid role | `ValidationError` | 400 |
| `transfer_ownership` | Not owner | `AuthorizationError` | 403 |
| `transfer_ownership` | New owner not member | `ResourceNotFoundError` | 404 |

### UserService Exceptions

| Method | Error Condition | Exception | HTTP |
|--------|-----------------|-----------|------|
| `get_user` | User not found | `ResourceNotFoundError` | 404 |
| `create_user` | Username exists | `ValidationError` | 400 |
| `create_user` | Email exists | `ValidationError` | 400 |
| `update_user` | User not found | `ResourceNotFoundError` | 404 |
| `delete_user` | User not found | `ResourceNotFoundError` | 404 |
| `change_role` | User not found | `ResourceNotFoundError` | 404 |
| `change_role` | Invalid role | `ValidationError` | 400 |
| `change_password` | User not found | `ResourceNotFoundError` | 404 |
| `change_password` | Wrong password | `AuthenticationError` | 401 |
| `reset_password` | User not found | `ResourceNotFoundError` | 404 |
| `verify_password` | User not found | `ResourceNotFoundError` | 404 |

### ProductService Exceptions

| Method | Error Condition | Exception | HTTP |
|--------|-----------------|-----------|------|
| `create_product` | Name exists | `ValidationError` | 400 |
| `create_product` | Invalid platforms | `ValidationError` | 400 |
| `get_product` | Product not found | `ResourceNotFoundError` | 404 |
| `update_product` | Product not found | `ResourceNotFoundError` | 404 |
| `delete_product` | Product not found | `ResourceNotFoundError` | 404 |
| `restore_product` | Product not found | `ResourceNotFoundError` | 404 |
| `upload_vision_document` | Product not found | `ResourceNotFoundError` | 404 |
| `upload_vision_document` | Chunking failed | `VisionChunkingError` | 400 |

### TaskService Exceptions

| Method | Error Condition | Exception | HTTP |
|--------|-----------------|-----------|------|
| `log_task` | Missing product_id | `ValidationError` | 400 |
| `get_task` | Task not found | `ResourceNotFoundError` | 404 |
| `update_task` | Task not found | `ResourceNotFoundError` | 404 |
| `delete_task` | Task not found | `ResourceNotFoundError` | 404 |
| `change_status` | Invalid status | `ValidationError` | 400 |

### ProjectService Exceptions

| Method | Error Condition | Exception | HTTP |
|--------|-----------------|-----------|------|
| `get_project` | Project not found | `ResourceNotFoundError` | 404 |
| `update_project_mission` | Project not found | `ResourceNotFoundError` | 404 |
| `complete_project` | Invalid state | `ProjectStateError` | 400 |
| `activate_project` | Invalid state | `ProjectStateError` | 400 |

### MessageService Exceptions

| Method | Error Condition | Exception | HTTP |
|--------|-----------------|-----------|------|
| `send_message` | Project not found | `ResourceNotFoundError` | 404 |
| `complete_message` | Message not found | `ResourceNotFoundError` | 404 |
| `acknowledge_message` | Message not found | `ResourceNotFoundError` | 404 |

### OrchestrationService Exceptions

| Method | Error Condition | Exception | HTTP |
|--------|-----------------|-----------|------|
| `spawn_agent_job` | Template not found | `TemplateNotFoundError` | 404 |
| `spawn_agent_job` | Creation failed | `AgentCreationError` | 500 |
| `get_agent_mission` | Job not found | `ResourceNotFoundError` | 404 |
| `create_successor_orchestrator` | Handoff failed | `HandoffError` | 500 |

### TemplateService Exceptions

| Method | Error Condition | Exception | HTTP |
|--------|-----------------|-----------|------|
| `get_template` | Template not found | `TemplateNotFoundError` | 404 |
| `create_template` | No tenant context | `ValidationError` | 400 |
| `update_template` | Template not found | `TemplateNotFoundError` | 404 |

---

## Migration Pattern

### Current Pattern (Dict Wrapper)

```python
async def get_organization(self, org_id: str) -> dict[str, Any]:
    try:
        org = await self.session.get(Organization, org_id)
        if not org:
            return {"success": False, "error": "Organization not found"}
        return {"success": True, "data": org}
    except SQLAlchemyError as e:
        return {"success": False, "error": str(e)}
```

### Target Pattern (Exception-Based)

```python
async def get_organization(self, org_id: str) -> Organization:
    try:
        org = await self.session.get(Organization, org_id)
        if not org:
            raise ResourceNotFoundError(
                message="Organization not found",
                context={"org_id": org_id}
            )
        return org
    except SQLAlchemyError as e:
        raise DatabaseError(
            message=f"Failed to get organization: {e}",
            context={"org_id": org_id}
        ) from e
```

### Key Differences

1. **Return Type:** `dict[str, Any]` → Domain model (e.g., `Organization`)
2. **Error Handling:** `{"success": False, "error": ...}` → Raise exception
3. **Success Case:** `{"success": True, "data": ...}` → Return value directly
4. **Exception Wrapping:** Catch DB exceptions and wrap in domain exceptions

---

## Exception Handler Configuration

The exception handlers in `api/exception_handlers.py` automatically map exceptions to HTTP responses:

```python
@app.exception_handler(BaseGiljoError)
async def giljo_exception_handler(request: Request, exc: BaseGiljoError):
    return JSONResponse(
        status_code=exc.default_status_code,
        content=exc.to_dict()
    )
```

### Response Format

All domain exceptions return a consistent JSON structure:

```json
{
    "error_code": "RESOURCE_NOT_FOUND_ERROR",
    "message": "Organization not found",
    "context": {"org_id": "abc-123"},
    "timestamp": "2026-02-07T12:00:00Z",
    "status_code": 404
}
```

---

## Proposed Exception Additions

### 1. AlreadyExistsError (Required)

```python
class AlreadyExistsError(BaseGiljoError):
    """Raised when attempting to create a resource that already exists."""
    default_status_code: int = 409
```

**Why:** Currently, duplicate resource errors return dict wrappers. This exception enables proper 409 Conflict responses.

### 2. Consider: Service-Specific NotFound Variants (Optional)

While `ResourceNotFoundError` covers all cases, service-specific variants could improve error messages:

```python
class OrgNotFoundError(ResourceNotFoundError):
    """Raised when organization is not found."""
    pass  # Inherits 404 from parent

class UserNotFoundError(ResourceNotFoundError):
    """Raised when user is not found."""
    pass

class ProductNotFoundError(ResourceNotFoundError):
    """Raised when product is not found."""
    pass
```

**Recommendation:** NOT REQUIRED for 0730. The generic `ResourceNotFoundError` with context is sufficient. Service-specific variants can be added later if needed for specialized error handling.

---

## Validation Checklist

### Exception Hierarchy
- [x] `ResourceNotFoundError` available (404)
- [x] `ValidationError` available (400)
- [x] `AuthenticationError` available (401)
- [x] `AuthorizationError` available (403)
- [x] `DatabaseError` available (500)
- [ ] `AlreadyExistsError` needed (409) - **TO BE ADDED IN 0730b**

### Exception Handlers
- [x] `BaseGiljoError` handler registered
- [x] `RequestValidationError` handler registered (422)
- [x] `HTTPException` handler registered (backward compatibility)
- [x] Catch-all `Exception` handler registered (500)

---

## Implementation Notes for 0730b

1. **Add `AlreadyExistsError`** to `src/giljo_mcp/exceptions.py` before service refactoring
2. **Use consistent exception context** - always include entity IDs in context dict
3. **Wrap SQLAlchemy exceptions** in `DatabaseError` with original message
4. **Re-raise domain exceptions** without wrapping (pattern already used in UserService)

---

**Document Version:** 1.1
**Last Updated:** 2026-02-08
**Gaps Identified:** AlreadyExistsError (409), ProjectStateError (400)
