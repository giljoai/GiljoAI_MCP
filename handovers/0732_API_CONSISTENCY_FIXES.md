# Handover 0732: API Consistency Fixes

**Series:** 0700 Code Health Audit Follow-Up
**Priority:** P3 - LOW (Minor Polish)
**Risk Level:** LOW
**Estimated Effort:** 2-4 hours
**Prerequisites:** Handover 0725 Audit Complete
**Status:** READY

---

## Mission Statement

Fix minor API inconsistencies identified in the 0725 audit to improve API design consistency.

**Current Status:** 1 API URL naming violation, 2 endpoint files with inconsistent error handling.

---

## Part 1: API URL Naming Convention Fix

**Severity:** LOW - Single violation
**Breaking Change:** YES - Frontend must update

### The Violation

**File:** `api/endpoints/users.py`
**Lines:** 993, 1005

**Current:**
```python
@router.get("/me/settings/execution_mode")  # Line 993
async def get_execution_mode(...)

@router.put("/me/settings/execution_mode")  # Line 1005
async def update_execution_mode(...)
```

**Should Be:**
```python
@router.get("/me/settings/execution-mode")  # kebab-case
async def get_execution_mode(...)

@router.put("/me/settings/execution-mode")  # kebab-case
async def update_execution_mode(...)
```

**Standard:** API URLs use kebab-case (hyphen-separated)

**Compliant Examples:**
- `/api/vision-documents`
- `/api/mcp-installer`
- `/api/ai-tools`
- `/{project_id}/close-out`

---

### Implementation Steps

1. **Update Backend Endpoint (5 minutes):**
   ```python
   # File: api/endpoints/users.py
   # Change both lines 993 and 1005
   @router.get("/me/settings/execution-mode")  # Fixed
   async def get_execution_mode(...)

   @router.put("/me/settings/execution-mode")  # Fixed
   async def update_execution_mode(...)
   ```

2. **Find Frontend API Calls (10 minutes):**
   ```bash
   # Search frontend for execution_mode endpoint usage
   grep -r "execution_mode" frontend/src/

   # Likely in:
   # - frontend/src/views/UserSettings.vue
   # - frontend/src/stores/userSettings.js
   # - frontend/src/api/settings.js (if exists)
   ```

3. **Update Frontend Calls (15 minutes):**
   ```javascript
   // BEFORE
   await fetch('/api/me/settings/execution_mode')

   // AFTER
   await fetch('/api/me/settings/execution-mode')
   ```

4. **Update Integration Tests (15 minutes):**
   ```bash
   # Find test files
   grep -r "execution_mode" tests/

   # Update test URLs
   # Likely in tests/api/test_users_api.py or similar
   ```

---

### Testing

```bash
# Backend test
curl -X GET http://localhost:7272/api/me/settings/execution-mode \
  -H "Authorization: Bearer <token>"

# Should return 200, not 404

# Integration test
pytest tests/api/test_users_api.py -k execution_mode
```

---

## Part 2: Inconsistent Error Response Formats

**Severity:** LOW - Architectural inconsistency
**Count:** 2 endpoint files

### Files Affected

1. **api/endpoints/configuration.py**
   - Lines 573, 584, 587
   - Direct dict error returns

2. **api/endpoints/database_setup.py**
   - Lines 113, 118
   - Direct dict error returns

---

### Current Pattern (Anti-pattern)

```python
# configuration.py:573
if not config_updated:
    return {"error": "Configuration update failed"}  # ❌ Dict

# database_setup.py:113
if not database_ready:
    return {"error": "Database not ready", "status": "error"}  # ❌ Dict
```

### Target Pattern (HTTPException)

```python
# Use HTTPException for errors
if not config_updated:
    raise HTTPException(
        status_code=500,
        detail="Configuration update failed"
    )

if not database_ready:
    raise HTTPException(
        status_code=503,
        detail="Database not ready"
    )
```

---

### Implementation Steps

1. **Update configuration.py (30 minutes):**
   - Find lines 573, 584, 587
   - Replace dict returns with HTTPException
   - Import HTTPException from fastapi
   - Choose appropriate status codes (400, 404, 500, etc.)

2. **Update database_setup.py (30 minutes):**
   - Find lines 113, 118
   - Replace dict returns with HTTPException
   - Use 503 for service unavailable

3. **Update Tests (30 minutes):**
   - Tests may expect dict responses
   - Update to expect HTTP status codes
   - Verify error handling still works

---

### Example Refactoring

**Before:**
```python
# configuration.py:573
@router.post("/config/update")
async def update_config(...):
    result = await service.update_config(...)
    if not result["success"]:
        return {"error": result["message"]}  # ❌
    return result["data"]
```

**After:**
```python
# configuration.py:573
@router.post("/config/update")
async def update_config(...):
    result = await service.update_config(...)
    if not result["success"]:
        raise HTTPException(  # ✅
            status_code=500,
            detail=result["message"]
        )
    return result["data"]
```

---

## Part 3: Remove HTTPException from Service Layer (If Found)

**Severity:** LOW - Architectural boundary violation

**Note:** Audit findings mentioned `ProductService` has HTTPException usage (anti-pattern).

**Pattern:**
- Services should raise domain exceptions
- Endpoints should catch and convert to HTTPException

**Investigation Required:**
```bash
# Find HTTPException in service layer
grep -r "HTTPException" src/giljo_mcp/services/

# If found, refactor to use domain exceptions
```

**Example Refactoring:**
```python
# BEFORE (anti-pattern)
class ProductService:
    async def get_product(self, product_id: str):
        product = await repo.get(product_id)
        if not product:
            raise HTTPException(404, "Product not found")  # ❌ Service layer
        return product

# AFTER (correct)
class ProductService:
    async def get_product(self, product_id: str):
        product = await repo.get(product_id)
        if not product:
            raise ResourceNotFoundError("Product not found")  # ✅ Domain exception
        return product

# Endpoint catches and converts
@router.get("/products/{product_id}")
async def get_product_endpoint(product_id: str):
    try:
        product = await service.get_product(product_id)
        return product
    except ResourceNotFoundError as e:
        raise HTTPException(404, str(e))  # ✅ Endpoint layer
```

---

## Success Criteria

- [ ] API URL renamed to kebab-case (/execution-mode)
- [ ] Frontend API calls updated
- [ ] Integration tests updated
- [ ] configuration.py error returns use HTTPException
- [ ] database_setup.py error returns use HTTPException
- [ ] HTTPException removed from service layer (if present)
- [ ] All tests pass
- [ ] Ruff linting clean
- [ ] API documentation updated (if generated)

---

## Files to Modify

**Backend:**
1. `api/endpoints/users.py` (Lines 993, 1005)
2. `api/endpoints/configuration.py` (Lines 573, 584, 587)
3. `api/endpoints/database_setup.py` (Lines 113, 118)
4. `src/giljo_mcp/services/product_service.py` (if HTTPException found)

**Frontend:**
- Files calling `/me/settings/execution_mode` endpoint
- Likely `frontend/src/views/UserSettings.vue`
- Likely `frontend/src/stores/` or `frontend/src/api/`

**Tests:**
- `tests/api/test_users_api.py` (execution_mode tests)
- `tests/api/test_configuration.py` (error handling tests)
- `tests/api/test_database_setup.py` (error handling tests)

---

## Documentation Updates

If API documentation is auto-generated (OpenAPI/Swagger):
- Regenerate docs after URL changes
- Verify error response schemas updated

---

## Breaking Changes Coordination

**API URL Change:**
- **Version:** Should be in v2.0 or coordinate with frontend team
- **Migration:** Add deprecation warning in v1.x
- **Timeline:** Allow 1-2 release cycles for migration

**Alternative (Backward Compatible):**
Support both URLs temporarily:
```python
# Support both for transition
@router.get("/me/settings/execution_mode")  # Legacy
@router.get("/me/settings/execution-mode")  # New
async def get_execution_mode(...):
    # Same handler
```

---

## Testing Commands

```bash
# Backend tests
pytest tests/api/test_users_api.py -k execution
pytest tests/api/test_configuration.py
pytest tests/api/test_database_setup.py

# Lint check
ruff check api/endpoints/

# Full suite
pytest tests/
```

---

## Reference

**Audit Report:** `handovers/0725_AUDIT_REPORT.md` (Lines 244-262)
**Naming Findings:** `handovers/0725_findings_naming.md` (Lines 126-146)
**Architecture Findings:** `handovers/0725_findings_architecture.md` (Lines 130-143)
