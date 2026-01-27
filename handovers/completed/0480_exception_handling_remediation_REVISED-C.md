# Exception Handling Architecture Remediation Series (0480) - REVISED

**Created**: 2026-01-26
**Revised**: 2026-01-27
**Status**: Ready for Implementation
**Priority**: HIGH (downgraded from CRITICAL)
**Total Estimated Effort**: 40-55 hours (reduced from 94-120)

---

## REVISION NOTES

### Why This Revision Was Needed

The original 0480 series was created with **memory fog** - the agent lost context and made critical errors:

1. **FALSE PREMISE**: Claimed services have "205+ HTTPException raises" - WRONG
   - **Reality**: Services use `return {"success": False, "error": ...}` dict pattern
   - Only 5 HTTPException raises exist in service layer (across 2 files)

2. **DUPLICATE INFRASTRUCTURE**: Proposed creating new exception hierarchy
   - **Reality**: `src/giljo_mcp/exceptions.py` already has 40+ exception classes
   - Existing: `BaseGiljoException`, `ValidationError`, `NotFoundError`, etc.

3. **FABRICATED CODE EXAMPLES**: "Before" snippets didn't match actual code

4. **OVER-ENGINEERED SCOPE**: 94-120 hours for work that should be ~50% smaller

### Audit Results (2026-01-27)

| Aspect | Original Claim | Reality | Score |
|--------|---------------|---------|-------|
| HTTPException count | 205+ in services | 5 total (2 files) | 2/10 |
| Exception hierarchy | None exists | 40+ classes exist | 1/10 |
| Service pattern | HTTPException raises | Dict returns | 2/10 |
| Estimated effort | 94-120 hours | 40-55 hours needed | 4/10 |

---

## Revised Series Overview

### Actual Problem Statement

- **Current State**: Services return `{"success": False, "error": "..."}` dicts
- **Existing Infrastructure**: `src/giljo_mcp/exceptions.py` has 40+ exception classes (UNUSED)
- **Target State**: Services raise exceptions → Global handler translates to HTTP → Frontend discriminates

### What Actually Needs to Be Done

1. **Add HTTP status codes** to existing `BaseGiljoException` class
2. **Register global exception handler** in FastAPI app
3. **Migrate services** from dict returns to raising exceptions
4. **Remove endpoint try/except** blocks (let exceptions bubble up)
5. **Frontend error handling** for typed error responses

### Revised Impact

- **Files Changed**: ~15 services, ~47 endpoint files, 1 new handler
- **Lines Changed**: ~800 lines modified (not removed)
- **Test Coverage**: 80+ new tests (reduced from 174)
- **Time Savings**: 50% reduction vs original estimate

---

## Revised Handover Breakdown

### Phase 1: Foundation (0480a REVISED) - 6-8 hours

**Changes to existing 0480a**:

1. **DO NOT** create new exception files - use existing `src/giljo_mcp/exceptions.py`
2. **ADD** `default_status_code` attribute to existing `BaseGiljoException`
3. **ADD** `to_dict()` method to existing `BaseGiljoException`
4. **CREATE** `api/exception_handlers.py` (global handler)
5. **REGISTER** handler in `api/app.py`

**Key Files**:
- MODIFY: `src/giljo_mcp/exceptions.py` (add HTTP mapping)
- CREATE: `api/exception_handlers.py` (global handler)
- MODIFY: `api/app.py` (register handler)

### Phase 2: Service Migration (0480b-0480d REVISED) - 20-28 hours

**0480b: Auth & Product Services** (8-10 hours)
- Migrate `auth_service.py` (16 dict returns → exceptions)
- Migrate `product_service.py` (14 dict returns → exceptions)

**0480c: Core Services** (8-10 hours)
- Migrate `project_service.py`
- Migrate `orchestration_service.py`
- Migrate `template_service.py`

**0480d: Remaining Services** (4-8 hours)
- Migrate `message_service.py`
- Migrate `context_service.py`
- Migrate remaining services

### Phase 3: Endpoint Cleanup (0480e REVISED) - 8-12 hours

**0480e: Remove Endpoint try/except**
- Remove redundant try/except from endpoints
- Let exceptions bubble to global handler
- 47 endpoint files to clean up

### Phase 4: Frontend & Testing (0480f-0480g REVISED) - 6-10 hours

**0480f: Frontend Error Handling** (4-6 hours)
- Update API interceptor for typed errors
- Toast manager for error categories
- Form validation error display

**0480g: Integration Testing** (2-4 hours)
- Test exception → HTTP translation
- Test frontend error display
- Regression tests

---

## Terminal Chaining Instructions

This series uses **multi-terminal chain execution** per MULTI_TERMINAL_CHAIN_STRATEGY.md.

### Prompt Directory

Create: `prompts/0480_chain/`

### Chain Execution

```powershell
# Terminal 1 (Green): Foundation
claude --dangerously-skip-permissions --print "$(cat prompts/0480_chain/0480a_foundation.md)"

# Terminal 2 (Blue): Service Migration - Auth & Product
claude --dangerously-skip-permissions --print "$(cat prompts/0480_chain/0480b_services_auth_product.md)"

# Terminal 3 (Yellow): Service Migration - Core
claude --dangerously-skip-permissions --print "$(cat prompts/0480_chain/0480c_services_core.md)"

# Terminal 4 (Cyan): Service Migration - Remaining
claude --dangerously-skip-permissions --print "$(cat prompts/0480_chain/0480d_services_remaining.md)"

# Terminal 5 (Magenta): Endpoint Cleanup
claude --dangerously-skip-permissions --print "$(cat prompts/0480_chain/0480e_endpoints.md)"

# Terminal 6 (White): Frontend & Testing
claude --dangerously-skip-permissions --print "$(cat prompts/0480_chain/0480f_frontend_testing.md)"
```

### Dependencies Graph (Revised)

```
0480a (Foundation) - MUST complete first
  └── 0480b (Auth & Product Services)
  └── 0480c (Core Services) - can run parallel with 0480b
  └── 0480d (Remaining Services) - after 0480b+c
        └── 0480e (Endpoint Cleanup) - after all services
              └── 0480f (Frontend & Testing) - after endpoints
```

---

## CRITICAL: Before/After Code Examples (ACCURATE)

### Service Method - ACTUAL Current State

```python
# src/giljo_mcp/services/product_service.py - ACTUAL CODE
async def get_product(self, product_id: str, tenant_key: str) -> dict:
    try:
        product = await self._get_product_by_id(product_id, tenant_key)
        if not product:
            return {"success": False, "error": "Product not found"}
        return {"success": True, "data": product.to_dict()}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

### Service Method - Target State

```python
# AFTER migration - raises domain exceptions
from src.giljo_mcp.exceptions import ResourceNotFoundError

async def get_product(self, product_id: str, tenant_key: str) -> Product:
    product = await self._get_product_by_id(product_id, tenant_key)
    if not product:
        raise ResourceNotFoundError(
            message=f"Product {product_id} not found",
            context={"product_id": product_id, "tenant_key": tenant_key}
        )
    return product
```

### Endpoint - ACTUAL Current State

```python
# api/endpoints/products.py - ACTUAL CODE
@router.get("/{product_id}")
async def get_product(product_id: str, ...):
    result = await service.get_product(product_id, tenant_key)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result["data"]
```

### Endpoint - Target State

```python
# AFTER migration - no try/except needed
@router.get("/{product_id}")
async def get_product(product_id: str, ...):
    return await service.get_product(product_id, tenant_key)
# Exception bubbles to global handler automatically
```

---

## Changes to Existing exceptions.py

### Add to BaseGiljoException

```python
class BaseGiljoException(Exception):
    """Base exception with HTTP status code mapping."""

    # ADD these attributes
    default_status_code: int = 500  # Override in subclasses

    def __init__(self, message: str, error_code: Optional[str] = None, context: Optional[dict] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__.upper()
        self.context = context or {}
        self.timestamp = datetime.now(timezone.utc)

    # ADD this method
    def to_dict(self) -> dict:
        """Serialize for JSON response."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
            "status_code": self.default_status_code
        }
```

### Add HTTP Codes to Existing Classes

```python
class ValidationError(BaseGiljoException):
    default_status_code = 400

class ResourceNotFoundError(ResourceError):
    default_status_code = 404

class AuthenticationError(APIError):
    default_status_code = 401

class AuthorizationError(APIError):
    default_status_code = 403

class DatabaseError(BaseGiljoException):
    default_status_code = 500
```

---

## Success Metrics (Revised)

### Code Quality
- **Dict returns removed**: 30+ `{"success": False, ...}` patterns → exceptions
- **Endpoint try/except removed**: 50+ redundant blocks deleted
- **Test coverage**: 80+ new exception path tests

### User Experience
- **Error types**: Generic → Specific (same as before)
- **Frontend discrimination**: Yes (same as before)

### Developer Productivity
- **Error handling code**: 60% reduction (revised from 70%)
- **Consistency**: All services use same pattern

---

## Deprecated Handovers

The following handovers from the original series are **deprecated**:

| Handover | Reason |
|----------|--------|
| 0480a (original) | Creates duplicate exception hierarchy |
| 0480b (original) | Base service class pattern not needed |
| 0480c (original) | Test infrastructure over-engineered |
| 0480h (original) | Frontend scope reduced |
| 0480i (original) | Testing scope reduced |
| 0480j (original) | Cleanup merged into other phases |

---

## Rollback Strategy

```bash
# Rollback entire series
git revert <0480a_commit>..<0480f_commit>

# Verify tests pass
pytest tests/ -v
```

---

## Related Documentation

- [CLAUDE.md](../../CLAUDE.md) - Project coding guidelines
- [src/giljo_mcp/exceptions.py](../../src/giljo_mcp/exceptions.py) - EXISTING exception hierarchy
- [MULTI_TERMINAL_CHAIN_STRATEGY.md](./Reference_docs/MULTI_TERMINAL_CHAIN_STRATEGY.md) - Chain execution protocol

---

**Document Version**: 2.0 (REVISED)
**Original Version**: 1.0 (2026-01-26, DEPRECATED)
**Revision Date**: 2026-01-27
**Author**: Claude (Opus 4.5)
**Status**: Ready for Implementation
