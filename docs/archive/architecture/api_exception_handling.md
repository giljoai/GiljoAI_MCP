# API Endpoint Exception Handling

**Handover:** 0730a Design Response Models
**Created:** 2026-02-07
**Purpose:** Document API endpoint patterns for consuming services with exception-based error handling

---

## Overview

This document provides guidance for migrating API endpoints from dict-wrapper checking to exception propagation. The exception handlers in `api/exception_handlers.py` automatically convert domain exceptions to appropriate HTTP responses.

---

## Current Pattern (Anti-Pattern)

API endpoints currently check service return values for success:

```python
@router.get("/{org_id}")
async def get_organization(org_id: str, org_service: OrgService = Depends(get_org_service)):
    result = await org_service.get_organization(org_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result["data"]
```

**Problems:**
1. Boilerplate `if not result["success"]` in every endpoint
2. Inconsistent status codes (always 400 vs appropriate 404, 409, etc.)
3. Error messages not structured consistently
4. Service layer responsible for both business logic AND response formatting

---

## Target Pattern (Exception Propagation)

With exception-based services, endpoints simply call and return:

```python
@router.get("/{org_id}")
async def get_organization(org_id: str, org_service: OrgService = Depends(get_org_service)):
    org = await org_service.get_organization(org_id)
    return org  # Exception handlers catch ResourceNotFoundError → 404
```

**Benefits:**
1. Clean, minimal endpoint code
2. Correct HTTP status codes (404 for not found, 409 for conflicts, etc.)
3. Consistent error response format via exception handlers
4. Service layer focused on business logic only

---

## Exception Handler Verification

The handlers in `api/exception_handlers.py` are already configured to handle all domain exceptions:

### Handler: BaseGiljoError

```python
@app.exception_handler(BaseGiljoError)
async def giljo_exception_handler(request: Request, exc: BaseGiljoError):
    logger.error(f"{exc.error_code}: {exc.message}", extra={"context": exc.context})
    return JSONResponse(status_code=exc.default_status_code, content=exc.to_dict())
```

**Handles:**
- `ResourceNotFoundError` → 404
- `ValidationError` → 400
- `AuthenticationError` → 401
- `AuthorizationError` → 403
- `DatabaseError` → 500
- All other `BaseGiljoError` subclasses → Their `default_status_code`

### Handler: RequestValidationError

```python
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={...})
```

**Handles:** FastAPI/Pydantic request body validation failures

### Handler: HTTPException (Legacy)

```python
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(status_code=exc.status_code, content={...})
```

**Handles:** Legacy `HTTPException` raises during migration period

### Handler: Catch-All

```python
@app.exception_handler(Exception)
async def unexpected_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={...})
```

**Handles:** Any uncaught exceptions → 500

---

## Migration Examples

### Example 1: Simple GET (Not Found)

**Current:**
```python
@router.get("/{product_id}")
async def get_product(product_id: str, service: ProductService = Depends()):
    result = await service.get_product(product_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result["product"]
```

**Target:**
```python
@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: str, service: ProductService = Depends()):
    return await service.get_product(product_id)
    # ResourceNotFoundError → 404 automatically
```

### Example 2: POST Create (Duplicate Check)

**Current:**
```python
@router.post("/")
async def create_org(data: OrgCreate, service: OrgService = Depends()):
    result = await service.create_organization(
        name=data.name,
        owner_id=data.owner_id,
        tenant_key=data.tenant_key
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result["data"]
```

**Target:**
```python
@router.post("/", response_model=OrgResponse, status_code=201)
async def create_org(data: OrgCreate, service: OrgService = Depends()):
    return await service.create_organization(
        name=data.name,
        owner_id=data.owner_id,
        tenant_key=data.tenant_key
    )
    # AlreadyExistsError → 409 automatically
    # ValidationError → 400 automatically
```

### Example 3: PUT Update (Authorization)

**Current:**
```python
@router.put("/{org_id}/members/{user_id}/role")
async def change_role(org_id: str, user_id: str, role: str, service: OrgService = Depends()):
    result = await service.change_member_role(org_id, user_id, role)
    if not result["success"]:
        if "owner" in result["error"].lower():
            raise HTTPException(status_code=403, detail=result["error"])
        raise HTTPException(status_code=400, detail=result["error"])
    return result["data"]
```

**Target:**
```python
@router.put("/{org_id}/members/{user_id}/role", response_model=MembershipResponse)
async def change_role(org_id: str, user_id: str, role: str, service: OrgService = Depends()):
    return await service.change_member_role(org_id, user_id, role)
    # ResourceNotFoundError → 404 (not a member)
    # AuthorizationError → 403 (is owner)
    # ValidationError → 400 (invalid role)
```

### Example 4: DELETE with Confirmation

**Current:**
```python
@router.delete("/{task_id}")
async def delete_task(task_id: str, service: TaskService = Depends()):
    result = await service.delete_task(task_id)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["error"])
    return {"message": "Task deleted"}
```

**Target:**
```python
@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: str, service: TaskService = Depends()):
    await service.delete_task(task_id)
    # ResourceNotFoundError → 404 automatically
    # No return body for 204
```

---

## Affected Endpoint Files

Based on pattern search, these files contain `result["success"]` checks requiring migration:

### High Priority (Organization & User Endpoints)
- `api/endpoints/organizations/crud.py` - 5 instances
- `api/endpoints/organizations/members.py` - 5 instances
- `api/endpoints/users.py` - 17 instances

### Medium Priority (Core Resources)
- `api/endpoints/tasks.py` - 9 instances
- `api/endpoints/products/*.py` - Multiple instances
- `api/endpoints/projects/*.py` - Multiple instances

### Lower Priority
- `api/endpoints/context.py` - 1 instance
- `api/endpoints/vision_documents.py` - 3 instances

---

## Response Model Guidelines

### Use Pydantic Response Models

Define response models in `api/schemas/` for type safety and documentation:

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class OrgResponse(BaseModel):
    id: str
    name: str
    slug: str
    tenant_key: str
    is_active: bool
    settings: dict
    created_at: Optional[datetime]

    class Config:
        from_attributes = True  # Enable ORM mode
```

### Configure Endpoint Response Models

```python
@router.get("/{org_id}", response_model=OrgResponse)
async def get_organization(org_id: str, service: OrgService = Depends()):
    return await service.get_organization(org_id)
```

---

## Error Response Format

All domain exceptions produce consistent JSON responses:

```json
{
    "error_code": "RESOURCE_NOT_FOUND_ERROR",
    "message": "Organization not found",
    "context": {
        "org_id": "abc-123",
        "tenant_key": "tenant_xyz"
    },
    "timestamp": "2026-02-07T12:00:00.000000+00:00",
    "status_code": 404
}
```

### Error Code Patterns

- `RESOURCE_NOT_FOUND_ERROR` - Entity not found (404)
- `ALREADY_EXISTS_ERROR` - Duplicate resource (409)
- `VALIDATION_ERROR` - Invalid input (400)
- `AUTHENTICATION_ERROR` - Auth failure (401)
- `AUTHORIZATION_ERROR` - Permission denied (403)
- `DATABASE_ERROR` - DB operation failed (500)

---

## Testing Endpoint Changes

### Test Exception Propagation

```python
@pytest.mark.asyncio
async def test_get_org_not_found(client, mock_org_service):
    mock_org_service.get_organization.side_effect = ResourceNotFoundError(
        message="Organization not found",
        context={"org_id": "invalid-id"}
    )

    response = await client.get("/api/orgs/invalid-id")

    assert response.status_code == 404
    assert response.json()["error_code"] == "RESOURCE_NOT_FOUND_ERROR"
```

### Test Success Response

```python
@pytest.mark.asyncio
async def test_get_org_success(client, mock_org_service, sample_org):
    mock_org_service.get_organization.return_value = sample_org

    response = await client.get(f"/api/orgs/{sample_org.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(sample_org.id)
```

---

## Migration Checklist for 0730c

### Per Endpoint:
- [ ] Remove `if not result["success"]` check
- [ ] Remove manual `HTTPException` raise for errors
- [ ] Update return statement to return service result directly
- [ ] Add `response_model` parameter if not present
- [ ] Update test to expect exception instead of dict check

### Per File:
- [ ] Remove unused `HTTPException` import if no longer needed
- [ ] Verify all endpoints follow new pattern
- [ ] Run endpoint tests to confirm behavior

### Global:
- [ ] Verify exception handlers are registered in `api/app.py`
- [ ] Confirm no regressions in API behavior
- [ ] Update API documentation if response format changed

---

## Backward Compatibility

During migration, the `HTTPException` handler provides backward compatibility:

```python
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": "HTTP_ERROR",
            "message": exc.detail,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
```

This means endpoints can be migrated incrementally without breaking the API.

---

## Summary

1. **Services raise domain exceptions** instead of returning dict wrappers
2. **Endpoints propagate exceptions** instead of checking success flags
3. **Exception handlers convert to HTTP responses** automatically
4. **Correct status codes** (404, 409, etc.) used instead of generic 400
5. **Consistent error format** across all endpoints

---

**Document Version:** 1.1
**Last Updated:** 2026-02-08
