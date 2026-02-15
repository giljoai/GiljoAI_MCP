# Handover 0730c: Update API Endpoints

**Series:** 0700 Code Cleanup → 0730 Service Response Models (Phase 3 of 4)
**Handover ID:** 0730c
**Priority:** P2 - MEDIUM
**Estimated Effort:** 2-4 hours
**Status:** BLOCKED (waiting for 0730b completion)
**Date Created:** 2026-02-08
**Date Updated:** 2026-02-08

---

## 1. Metadata

**Dependencies:**
- **Depends On:** 0730a (exception mapping), 0730b (service refactoring complete)
- **Blocks:** 0730d (testing and validation)
- **Prerequisites:** All services must return models and raise exceptions (verified via 0730b completion)

**Recommended Agent:** Backend Integration Tester

**Estimated Complexity:** 2-4 hours (45-60 endpoint updates across 9 API files)

---

## 2. Summary

**Mission:** Update API endpoints to remove dict checking logic and rely on exception-based error handling from refactored services.

**Executive Summary:**
After services have been refactored in 0730b to return Pydantic models and raise domain exceptions, API endpoints must be simplified to remove manual error checking. This phase removes ~50-70 instances of `if not result["success"]` pattern and enables proper HTTP status codes (404, 409, 422) via exception handlers. The refactoring follows the patterns documented in `docs/architecture/api_exception_handling.md` and completes the service-to-API integration.

**Expected Outcome:** Clean, minimal endpoint code that propagates exceptions to handlers in `api/exception_handlers.py`, resulting in proper REST semantics with correct HTTP status codes.

---

## 3. Context

### Why This Matters

**Business Value:**
- **Simplified Codebase:** Reduces endpoint complexity by removing boilerplate error checking
- **Proper REST Semantics:** HTTP status codes match REST standards (404 for not found, 409 for conflicts)
- **Maintainability:** Fewer lines of code, less duplication, easier to debug
- **Type Safety:** Endpoints return Pydantic models instead of untyped dicts

**Background:**
The 0730 series is eliminating dict wrapper anti-patterns from the service layer. Phase 0730a designed the exception mapping, 0730b refactored services to use exceptions, and this phase (0730c) updates API endpoints to consume the refactored services. Without this phase, endpoints would continue checking for dict wrappers that no longer exist.

**Architectural Context:**
The exception handlers in `api/exception_handlers.py` are already configured to convert domain exceptions (ResourceNotFoundError, ValidationError, etc.) to appropriate HTTP responses. Endpoints need only propagate exceptions upward.

**Related Work:**
- 0730a: Created `docs/architecture/exception_mapping.md` (exception-to-HTTP mapping)
- 0730b: Refactored 121 service methods to return models/raise exceptions
- 0730d: Will validate all changes with comprehensive testing

---

## 4. Technical Details

### Architecture Overview

**Current Pattern (Anti-Pattern - To Remove):**
```python
@router.get("/{org_id}/")
async def get_org(
    org_id: str,
    current_user: User = Depends(get_current_active_user),
    org_service: OrgService = Depends(get_org_service),
) -> OrgResponse:
    """Get organization by ID."""
    result = await org_service.get_org(org_id)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    return OrgResponse(**result["data"])
```

**Target Pattern (Clean - To Implement):**
```python
@router.get("/{org_id}/", response_model=OrgResponse)
async def get_org(
    org_id: str,
    current_user: User = Depends(get_current_active_user),
    org_service: OrgService = Depends(get_org_service),
) -> OrgResponse:
    """Get organization by ID.

    Raises:
        ResourceNotFoundError: Organization not found (404)
    """
    # Service raises ResourceNotFoundError if not found
    # Exception handler in api/exception_handlers.py converts to HTTP 404
    org = await org_service.get_org(org_id)
    return OrgResponse.from_orm(org)
```

**Key Changes:**
1. Remove `result` variable and dict checking
2. Call service method directly
3. Let exceptions propagate to exception handlers
4. Simplify return statement
5. Add `response_model` parameter to decorator
6. Add `Raises` docstring section for documentation

### Scope: Files Affected

**Primary API Files (45-60 endpoints total):**
- `api/endpoints/organizations/crud.py` - 5 instances
- `api/endpoints/organizations/members.py` - 5 instances
- `api/endpoints/users.py` - 17 instances
- `api/endpoints/tasks.py` - 9 instances
- `api/endpoints/products/*.py` - Multiple instances
- `api/endpoints/projects/*.py` - Multiple instances
- `api/endpoints/context.py` - 1 instance
- `api/endpoints/vision_documents.py` - 3 instances

**Supporting File:**
- `api/exception_handlers.py` - Verify handlers exist (no changes expected)

### Exception Handler Verification

**Handlers Already Configured (No Changes Needed):**
- `BaseGiljoError` → Maps to exception's `default_status_code`
- `ResourceNotFoundError` → 404
- `AlreadyExistsError` → 409
- `ValidationError` → 400
- `AuthenticationError` → 401
- `AuthorizationError` → 403
- `DatabaseError` → 500
- `RequestValidationError` → 422 (FastAPI/Pydantic)
- `HTTPException` → Pass through (backward compatibility)

**Verification Step:**
Read `api/exception_handlers.py` to confirm all handlers registered. If gaps found, add following pattern:

```python
@app.exception_handler(SpecificError)
async def specific_error_handler(request: Request, exc: SpecificError):
    return JSONResponse(
        status_code=exc.default_status_code,
        content=exc.to_dict(),
    )
```

### Common Migration Patterns

**Pattern 1: Simple GET (Not Found)**
```python
# BEFORE
result = await service.get_item(item_id)
if not result["success"]:
    raise HTTPException(status_code=400, detail=result["error"])
return ItemResponse(**result["data"])

# AFTER
item = await service.get_item(item_id)  # Raises ResourceNotFoundError if not found
return ItemResponse.from_orm(item)
```

**Pattern 2: POST Create (Duplicate Check)**
```python
# BEFORE
result = await service.create_item(item_data)
if not result["success"]:
    raise HTTPException(status_code=400, detail=result["error"])
return ItemResponse(**result["data"])

# AFTER
item = await service.create_item(item_data)  # Raises AlreadyExistsError if duplicate
return ItemResponse.from_orm(item)
```

**Pattern 3: LIST Endpoint**
```python
# BEFORE
result = await service.list_items()
if not result["success"]:
    raise HTTPException(status_code=400, detail=result["error"])
return [ItemResponse(**item) for item in result["data"]]

# AFTER
items = await service.list_items()  # Returns list[Item]
return [ItemResponse.from_orm(item) for item in items]
```

**Pattern 4: DELETE Endpoint**
```python
# BEFORE
result = await service.delete_item(item_id)
if not result["success"]:
    raise HTTPException(status_code=404, detail=result["error"])
return {"message": "Item deleted"}

# AFTER (204 No Content)
@router.delete("/{item_id}", status_code=204)
async def delete_item(item_id: str, service: ItemService = Depends()):
    await service.delete_item(item_id)  # Raises ResourceNotFoundError if not found
    # No return body for 204 No Content
```

---

## 5. Implementation Plan

### Coding Principles (FROM handover_instructions.md)

**You MUST follow these principles:**

1. ✅ **Chef's Kiss Quality:** Production-grade code ONLY - no shortcuts, no bandaids, no "good enough"
2. ✅ **Cross-Platform Paths:** Use `pathlib.Path()` for all file operations (NEVER hardcoded `F:\`)
3. ✅ **Serena MCP for Code Navigation:** Use `find_symbol`, `get_symbols_overview`, `find_referencing_symbols` (NOT full file reads)
4. ✅ **Multi-Tenant Isolation:** All database queries filtered by `tenant_key` (already handled by services)
5. ✅ **Exception-Based Error Handling:** Let exceptions propagate, remove dict checks
6. ✅ **Pydantic Response Models:** Add `response_model` parameter to all endpoints
7. ✅ **Proper HTTP Status Codes:** 404, 409, 400, 403 (NOT generic 400 for everything)
8. ✅ **Type Hints:** Explicit return type annotations on all functions
9. ✅ **Docstrings:** Add `Raises` section documenting exceptions
10. ✅ **Clean Refactoring:** DELETE old code, don't comment out

### TDD Workflow (MANDATORY)

For each endpoint refactoring:

1. **Write the test FIRST** (it should fail initially - red phase)
   - Test expects exception instead of dict checking
   - Test verifies correct HTTP status code (404, 409, etc.)

2. **Write minimal code** to make test pass (green phase)
   - Update endpoint following migration pattern
   - Remove dict checking logic

3. **Refactor** for quality (refactor phase)
   - Add docstring `Raises` section
   - Verify `response_model` parameter present

4. **Commit** with test + implementation together
   - One commit per endpoint file
   - Follow git commit standards (see section 9)

### Serena MCP Workflow (REQUIRED for Code Navigation)

**DO NOT read entire files.** Use symbolic navigation:

**Step 1: Find all endpoints with dict checking**
```python
mcp__serena__search_for_pattern(
    substring_pattern='if not result\\["success"\\]',
    relative_path="api/endpoints"
)
```

**Step 2: Get endpoint symbols**
```python
mcp__serena__get_symbols_overview(
    relative_path="api/endpoints/organizations/crud.py"
)
```

**Step 3: Read specific endpoint**
```python
mcp__serena__find_symbol(
    name_path_pattern="get_organization",
    relative_path="api/endpoints/organizations/crud.py",
    include_body=True
)
```

**Step 4: Find test files**
```python
mcp__serena__find_file(
    file_mask="*org*.py",
    relative_path="tests/api"
)
```

**Step 5: Update endpoint using symbolic edit**
```python
mcp__serena__replace_symbol_body(
    name_path="get_organization",
    relative_path="api/endpoints/organizations/crud.py",
    body="""async def get_organization(
    org_id: str,
    current_user: User = Depends(get_current_active_user),
    org_service: OrgService = Depends(get_org_service),
) -> OrgResponse:
    \"\"\"Get organization by ID.

    Raises:
        ResourceNotFoundError: Organization not found (404)
    \"\"\"
    org = await org_service.get_organization(org_id)
    return OrgResponse.from_orm(org)"""
)
```

### Step-by-Step Implementation (2-4 hours)

**Phase 1: Exception Handler Verification (15 minutes)**

1. Read `api/exception_handlers.py` using Serena MCP:
   ```python
   mcp__serena__get_symbols_overview(relative_path="api/exception_handlers.py")
   ```

2. Verify handlers exist for:
   - `BaseGiljoError` (catch-all)
   - `ResourceNotFoundError` (404)
   - `AlreadyExistsError` (409)
   - `ValidationError` (400)
   - `AuthenticationError` (401)
   - `AuthorizationError` (403)
   - `DatabaseError` (500)
   - `RequestValidationError` (422)

3. If gaps found: Add exception handlers following existing pattern

4. **Checkpoint:** All exception handlers verified complete

**Phase 2: Priority 1 - High-Traffic Endpoints (1-1.5 hours)**

**File: `api/endpoints/organizations/crud.py`** (~5 endpoints)

1. Find dict checking patterns using Serena:
   ```bash
   mcp__serena__search_for_pattern(
       substring_pattern='if not result\\["success"\\]',
       relative_path="api/endpoints/organizations/crud.py"
   )
   ```

2. For each endpoint:
   - Write test FIRST (TDD red phase)
   - Update endpoint following migration pattern
   - Run test to verify (TDD green phase)
   - Add docstring `Raises` section (refactor phase)

3. Run integration tests:
   ```bash
   pytest tests/api/test_orgs_api.py -v
   ```

4. Commit changes:
   ```bash
   git add api/endpoints/organizations/crud.py tests/api/test_orgs_api.py
   git commit -m "refactor(0730c): Remove dict checking from organizations/crud endpoints"
   ```

5. **Checkpoint:** Organizations CRUD endpoints updated, tests passing

**File: `api/endpoints/organizations/members.py`** (~5 endpoints)

Repeat same process as above.

**File: `api/endpoints/users.py`** (~17 endpoints)

Repeat same process as above.

**Checkpoint:** Priority 1 files complete, all tests passing

**Phase 3: Priority 2 - Task/Project Endpoints (45-60 minutes)**

**Files:**
- `api/endpoints/tasks.py` (~9 endpoints)
- `api/endpoints/projects/*.py` (multiple endpoints)
- `api/endpoints/products/*.py` (multiple endpoints)

Follow same TDD workflow for each file.

**Checkpoint:** Priority 2 files complete, all tests passing

**Phase 4: Priority 3 - Remaining Endpoints (30-45 minutes)**

**Files:**
- `api/endpoints/context.py` (~1 endpoint)
- `api/endpoints/vision_documents.py` (~3 endpoints)
- `api/endpoints/messages.py` (if any remaining)

Follow same TDD workflow for each file.

**Checkpoint:** All endpoint files updated, all tests passing

**Phase 5: Final Validation (30-60 minutes)**

1. **Verify no dict checking logic remains:**
   ```bash
   grep -r "result\[\"success\"\]" api/endpoints/ --include="*.py" | wc -l
   # Expected: 0

   grep -r "not result\[\"success\"\]" api/endpoints/ --include="*.py" | wc -l
   # Expected: 0
   ```

2. **Run all API integration tests:**
   ```bash
   pytest tests/api/ -v
   ```

3. **Check coverage:**
   ```bash
   pytest tests/api/ --cov=api/endpoints/ --cov-report=term-missing
   ```

4. **Run full test suite (check for regressions):**
   ```bash
   pytest tests/ -v
   ```

5. **Verify pre-commit hooks pass:**
   ```bash
   pre-commit run --all-files
   ```

6. **Manual spot check (optional but recommended):**
   - Create organization via dashboard (verify 409 on duplicate)
   - Get organization (verify 404 on not found)
   - Update organization (verify 404 on not found, 422 on validation error)

**Checkpoint:** All validation complete, ready for 0730d

---

## 6. Testing Requirements

### Unit Tests (Per Endpoint)

**Test Structure:**
```python
@pytest.mark.asyncio
async def test_get_org_not_found(client, mock_org_service):
    """Test GET /orgs/{id} returns 404 when organization not found."""
    mock_org_service.get_organization.side_effect = ResourceNotFoundError(
        message="Organization not found",
        context={"org_id": "invalid-id"}
    )

    response = await client.get("/api/orgs/invalid-id")

    assert response.status_code == 404
    assert response.json()["error_code"] == "RESOURCE_NOT_FOUND_ERROR"

@pytest.mark.asyncio
async def test_get_org_success(client, mock_org_service, sample_org):
    """Test GET /orgs/{id} returns organization on success."""
    mock_org_service.get_organization.return_value = sample_org

    response = await client.get(f"/api/orgs/{sample_org.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(sample_org.id)
```

**Test Coverage Requirements:**
- ✅ Success case (200/201)
- ✅ Not found case (404)
- ✅ Duplicate case (409)
- ✅ Validation error case (400/422)
- ✅ Authorization error case (403)

### Integration Tests

**Run after each file update:**
```bash
# Per file
pytest tests/api/test_orgs_api.py -v
pytest tests/api/test_users_api.py -v
pytest tests/api/test_tasks_api.py -v

# All API tests
pytest tests/api/ -v

# Full suite (regression check)
pytest tests/ -v
```

**Coverage Target:** >80% maintained (same as before refactoring)

### Manual Testing

**Test Workflow 1: Organization CRUD**
1. Create organization → Verify 201 on success, 409 on duplicate
2. Get organization → Verify 200 on success, 404 on not found
3. Update organization → Verify 200 on success, 404 on not found, 422 on validation error
4. Delete organization → Verify 204 on success, 404 on not found

**Test Workflow 2: User Management**
1. Create user → Verify 201 on success, 409 on duplicate email
2. Authenticate user → Verify 200 on valid credentials, 401 on invalid
3. Update user → Verify 200 on success, 404 on not found

---

## 7. Dependencies & Integration

### Upstream Dependencies

**Requires Completion:**
- **0730a:** Exception mapping documentation complete
- **0730b:** All services refactored to return models and raise exceptions

**Verification Before Starting:**
```bash
# Check that 0730b marked complete in orchestrator state
cat handovers/0700_series/orchestrator_state.json | grep "0730b"
# Should show: "status": "complete"

# Verify services raise exceptions (spot check)
mcp__serena__find_symbol(
    name_path_pattern="OrgService/get_organization",
    relative_path="src/giljo_mcp/services/org_service.py",
    include_body=True
)
# Should see: raise ResourceNotFoundError(...)
```

### Downstream Dependencies

**This Handover Blocks:**
- **0730d:** Testing and validation (cannot start until all endpoints updated)

**Integration Points:**
- Exception handlers in `api/exception_handlers.py` (no changes needed)
- Pydantic response models in `api/schemas/` (may need updates)
- API tests in `tests/api/` (will need updates for new patterns)

### Side Effects

**Frontend Impact:**
HTTP status codes may change from generic 400 to proper codes (404, 409, 422). Frontend error handling should already handle these, but note for future work if display issues arise.

**No Breaking Changes Expected:**
Exception handlers return same `{"detail": "..."}` format in error responses. Only status codes improve.

---

## 8. Success Criteria

### Definition of Done

**Code Quality:**
- [ ] All code follows TDD (tests written first, then implementation)
- [ ] >80% test coverage maintained (verify with `pytest --cov`)
- [ ] No hardcoded paths (all use `pathlib.Path` if needed)
- [ ] All endpoints have `response_model` parameter
- [ ] Docstrings include `Raises` section for exceptions
- [ ] Serena MCP tools used for symbol-based refactoring (NOT full file reads)

**Functionality:**
- [ ] Zero `if not result["success"]` patterns remaining in endpoints
- [ ] Zero `result["error"]` patterns remaining in endpoints
- [ ] Service methods called directly (no dict unpacking)
- [ ] Return statements simplified (return model directly)
- [ ] Exception handlers verified complete

**Testing:**
- [ ] All API integration tests passing: `pytest tests/api/ -v`
- [ ] Proper HTTP status codes returned (404, 409, 422, etc.)
- [ ] Exception messages clear and consistent
- [ ] Full test suite passing (zero regressions): `pytest tests/ -v`
- [ ] Coverage >80%: `pytest tests/api/ --cov=api/endpoints/`

**Documentation:**
- [ ] Docstrings updated with `Raises` sections
- [ ] Code comments for complex logic only (not for obvious changes)
- [ ] comms_log.json updated with completion message

**Integration:**
- [ ] Pre-commit hooks passing: `pre-commit run --all-files`
- [ ] No lint errors: `ruff api/; black api/`
- [ ] Git commits follow standards (see section 9)

**CRITICAL:**
- [ ] Stopped at phase boundary - did NOT proceed to 0730d
- [ ] Reported completion to user
- [ ] Awaiting user approval for next phase

### Validation Commands

```bash
# Verify no dict checking logic remains
grep -r "result\[\"success\"\]" api/endpoints/ --include="*.py"
# Expected: No output (empty)

grep -r "not result\[\"success\"\]" api/endpoints/ --include="*.py"
# Expected: No output (empty)

# Run all API tests
pytest tests/api/ -v

# Check integration test coverage
pytest tests/api/ --cov=api/endpoints/ --cov-report=term-missing

# Run full test suite (check for regressions)
pytest tests/ -v

# Verify pre-commit hooks pass
pre-commit run --all-files
```

---

## 9. Rollback Plan

### If Things Go Wrong

**Scenario 1: Tests Fail After Endpoint Update**

**Symptoms:** Integration tests fail with unexpected errors after updating endpoint

**Diagnosis:**
```bash
# Check exact error
pytest tests/api/test_orgs_api.py -v -s

# Verify service still raises exceptions
mcp__serena__find_symbol(
    name_path_pattern="OrgService/get_organization",
    relative_path="src/giljo_mcp/services/org_service.py",
    include_body=True
)
```

**Rollback:**
```bash
# Revert specific file
git checkout HEAD -- api/endpoints/organizations/crud.py

# Re-run tests to confirm rollback successful
pytest tests/api/test_orgs_api.py -v
```

**Root Cause:** Service may not have been refactored in 0730b, or exception handler missing

**Scenario 2: Wrong HTTP Status Codes Returned**

**Symptoms:** Tests expect 404 but get 500, or expect 409 but get 400

**Diagnosis:**
```bash
# Check exception handlers
mcp__serena__get_symbols_overview(relative_path="api/exception_handlers.py")

# Verify handler for specific exception exists
mcp__serena__find_symbol(
    name_path_pattern="resource_not_found_handler",
    relative_path="api/exception_handlers.py",
    include_body=True
)
```

**Fix:**
Add missing exception handler to `api/exception_handlers.py` following pattern:
```python
@app.exception_handler(SpecificError)
async def specific_error_handler(request: Request, exc: SpecificError):
    return JSONResponse(
        status_code=exc.default_status_code,
        content=exc.to_dict(),
    )
```

**Scenario 3: Pre-Commit Hooks Fail**

**Symptoms:** Commit blocked by ruff/black/mypy errors

**Diagnosis:**
```bash
# Run hooks to see exact errors
pre-commit run --all-files
```

**Fix:**
```bash
# Auto-fix formatting
black api/endpoints/
ruff --fix api/endpoints/

# Re-run to verify
pre-commit run --all-files
```

**Do NOT use `--no-verify` to bypass hooks without user approval.**

### Emergency Rollback (Full Phase)

**If multiple files broken and cannot fix quickly:**

```bash
# Stash all changes
git stash push -m "0730c failed - rolling back"

# Verify working state restored
pytest tests/api/ -v

# Report to user with details
echo "0730c rollback complete. Stashed changes in git stash."
git stash list
```

**Report to user:** Explain what failed, provide stash reference, await guidance.

---

## 10. Resources

### Related Handovers
- [0730a: Design Response Models](./0730a_DESIGN_RESPONSE_MODELS.md) - Exception mapping documentation
- [0730b: Refactor Services](./0730b_REFACTOR_SERVICES.md) - Service layer refactoring
- [0730d: Testing Validation](./0730d_TESTING_VALIDATION.md) - Final validation phase

### Documentation
- [API Exception Handling](../docs/architecture/api_exception_handling.md) - Migration patterns
- [Exception Mapping](../docs/architecture/exception_mapping.md) - Exception-to-HTTP mapping
- [Service Response Models](../docs/architecture/service_response_models.md) - Design rationale
- [SERVICES.md](../docs/SERVICES.md) - Service layer patterns
- [TESTING.md](../docs/TESTING.md) - Testing patterns and coverage

### Code References
- `api/exception_handlers.py` - Exception-to-HTTP mapping handlers
- `api/endpoints/` - All endpoint files to update
- `api/schemas/` - Pydantic response models
- `tests/api/` - Integration test files
- `src/giljo_mcp/exceptions.py` - Domain exception hierarchy

### External Resources
- [FastAPI Exception Handling](https://fastapi.tiangolo.com/tutorial/handling-errors/) - Official docs
- [Pydantic Models](https://docs.pydantic.dev/latest/concepts/models/) - Response model patterns
- [HTTP Status Codes](https://httpstatuses.com/) - REST semantics reference

---

## 11. 🛑 CRITICAL: STOP AFTER COMPLETION

**DO NOT PROCEED TO NEXT PHASE WITHOUT EXPLICIT USER APPROVAL**

After completing this handover:

1. ✅ Create all deliverables listed in Success Criteria
2. ✅ Update `handovers/0700_series/comms_log.json` with completion message:
   ```json
   {
     "timestamp": "2026-02-08T[TIME]Z",
     "from": "0730c",
     "to": "orchestrator",
     "type": "completion",
     "message": "0730c API endpoint updates COMPLETE",
     "endpoints_updated": "~50-70",
     "dict_checks_removed": "~50-70",
     "tests_passing": "100%"
   }
   ```
3. ✅ Mark handover status as COMPLETE in `handovers/0700_series/orchestrator_state.json`:
   ```json
   {
     "id": "0730c",
     "status": "complete",
     "phase": "api_updates",
     "completion_date": "2026-02-08",
     "endpoints_updated": "~50-70",
     "dict_checks_removed": "~50-70"
   }
   ```
4. 🛑 **STOP IMMEDIATELY AND REPORT TO USER**
5. ❌ **DO NOT start next handover (0730d)**
6. ❌ **DO NOT read kickoff prompt for 0730d**
7. ❌ **DO NOT interpret "Blocks: 0730d" as permission to proceed**

**This is a hard phase boundary.**

User will review deliverables and provide NEW kickoff prompt if approved to proceed to 0730d.

**Attempting to continue to the next phase without user approval violates project workflow and will result in work being discarded.**

---

## Git Commit Standards

**Commit message format:**
```
<type>(<scope>): <subject>

<body - optional>

```

**Types:** feat, fix, refactor, test, docs, chore
**Scope:** Handover ID (0730c)
**Subject:** Imperative mood, <50 chars

**Example (Per File Commit):**
```
refactor(0730c): Remove dict checking from organizations/crud endpoints

- Removed if not result["success"] pattern from 5 endpoints
- Added response_model parameter to all endpoints
- Exceptions now propagate to handlers (404, 409, etc.)
- All tests updated and passing

```

**Example (Final Commit After All Files):**
```
refactor(0730c): Complete API endpoint dict checking removal

Phase 3 of 0730 series - API layer cleanup

- Updated ~50-70 endpoints across 9 API files
- Removed all if not result["success"] patterns
- Added response_model parameters throughout
- Proper HTTP status codes via exception handlers
- All integration tests passing (100%)

Files modified:
- api/endpoints/organizations/crud.py (5 endpoints)
- api/endpoints/organizations/members.py (5 endpoints)
- api/endpoints/users.py (17 endpoints)
- api/endpoints/tasks.py (9 endpoints)
- api/endpoints/products/*.py (multiple)
- api/endpoints/projects/*.py (multiple)
- api/endpoints/context.py (1 endpoint)
- api/endpoints/vision_documents.py (3 endpoints)

```

---

**Document Version:** 2.0 (Complete Rewrite)
**Last Updated:** 2026-02-08
**Status:** Ready for execution after 0730b completion
