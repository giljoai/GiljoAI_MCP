# Handover 0730c: Update API Endpoints

**Series:** 0700 Code Cleanup → 0730 Service Response Models (Phase 3 of 4)
**Priority:** P2 - MEDIUM
**Estimated Effort:** 2-4 hours
**Prerequisites:** 0730b COMPLETE (all services refactored)
**Status:** BLOCKED (waiting for 0730b)
**Depends On:** 0730a (exception mapping), 0730b (service refactoring)
**Blocks:** 0730d

MISSION: Update API endpoints to remove dict checking logic and rely on exception-based error handling from refactored services

WHY THIS MATTERS:
- Simplifies endpoint code significantly
- Removes redundant error checking (services now handle this)
- Enables proper HTTP status codes from exception handlers
- Completes the service-to-API integration

CRITICAL: Services have been refactored in 0730b to return models and raise exceptions. Endpoints just need to remove dict checking logic.

---

## Scope: API Endpoints Affected

**Estimate:** ~50-70 endpoint functions across multiple API files

**Primary Files:**
- api/endpoints/orgs.py (endpoints using OrgService)
- api/endpoints/users.py (endpoints using UserService)
- api/endpoints/products.py (endpoints using ProductService)
- api/endpoints/tasks.py (endpoints using TaskService)
- api/endpoints/projects.py (endpoints using ProjectService)
- api/endpoints/messages.py (endpoints using MessageService)
- api/endpoints/orchestration.py (endpoints using OrchestrationService)
- api/endpoints/context.py (endpoints using ContextService)
- api/endpoints/templates.py (endpoints using TemplateService)

**Supporting File:**
- api/exception_handlers.py (verify exception-to-HTTP mappings exist)

---

## Migration Pattern

### Current Pattern (to remove):

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

### Target Pattern:

```python
@router.get("/{org_id}/")
async def get_org(
    org_id: str,
    current_user: User = Depends(get_current_active_user),
    org_service: OrgService = Depends(get_org_service),
) -> OrgResponse:
    """Get organization by ID.

    Raises:
        OrgNotFoundError: Organization not found (404)
    """
    # Service raises OrgNotFoundError if not found
    # Exception handler in api/exception_handlers.py converts to HTTP 404
    org = await org_service.get_org(org_id)
    return OrgResponse.from_orm(org)
```

**Key changes:**
1. Remove `result` variable and dict checking
2. Call service method directly
3. Let exceptions propagate to exception handlers
4. Simplify return statement
5. Add Raises docstring section for documentation

---

## Implementation Instructions

### Step 1: Verify Exception Handlers (15 minutes)

**Read:** api/exception_handlers.py

**Verify handlers exist for:**
- NotFoundError → 404
- AlreadyExistsError → 409
- ValidationError → 422
- UnauthorizedError → 403
- AuthenticationError → 401
- InternalServerError → 500

**If gaps found:**
Add exception handlers following existing pattern:

```python
@app.exception_handler(OrgNotFoundError)
async def org_not_found_handler(request: Request, exc: OrgNotFoundError):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(exc)},
    )
```

### Step 2: Update Endpoints by Service (2-3 hours)

**Process each API file systematically:**

1. **Search for dict checking patterns:**
   ```bash
   grep -n "result\[\"success\"\]" api/endpoints/orgs.py
   grep -n "not result\[\"success\"\]" api/endpoints/orgs.py
   ```

2. **For each endpoint function:**
   - Remove `result = ` assignment
   - Remove `if not result["success"]:` block
   - Change service call to direct assignment
   - Update return statement to use model directly
   - Add Raises section to docstring

3. **Use Serena MCP for efficiency:**
   ```python
   # Get symbols overview to find all endpoint functions
   mcp__serena__get_symbols_overview(relative_path="api/endpoints/orgs.py")

   # Read specific endpoint to update
   mcp__serena__find_symbol(
       name_path_pattern="get_org",
       relative_path="api/endpoints/orgs.py",
       include_body=True
   )
   ```

4. **Update endpoint using symbolic edit:**
   ```python
   mcp__serena__replace_symbol_body(
       name_path="get_org",
       relative_path="api/endpoints/orgs.py",
       body="""async def get_org(
       org_id: str,
       current_user: User = Depends(get_current_active_user),
       org_service: OrgService = Depends(get_org_service),
   ) -> OrgResponse:
       \"\"\"Get organization by ID.

       Raises:
           OrgNotFoundError: Organization not found (404)
       \"\"\"
       org = await org_service.get_org(org_id)
       return OrgResponse.from_orm(org)"""
   )
   ```

### Step 3: Test After Each File (30-60 minutes)

**Run integration tests for each updated file:**

```bash
# After updating orgs.py
pytest tests/api/test_orgs_api.py -v

# After updating users.py
pytest tests/api/test_users_api.py -v

# Continue for each file...
```

**Fix any test failures:**
- Tests may need updating if they check for dict responses
- Update tests to expect proper HTTP status codes
- Verify exception messages are correct

### Step 4: Final Validation (30 minutes)

```bash
# Run all API integration tests
pytest tests/api/ -v

# Verify no dict checking logic remains in endpoints
grep -r "result\[\"success\"\]" api/endpoints/ --include="*.py" | wc -l
# Should return 0

# Run full test suite
pytest tests/ -v

# Manual testing via dashboard (spot check)
# - Create org (409 if duplicate)
# - Get org (404 if not found)
# - Update org (404 if not found)
```

---

## Files to Update (Priority Order)

### Priority 1: High-Traffic Endpoints (1-1.5 hours)

**api/endpoints/orgs.py** - OrgService endpoints
- Estimated: 8-12 endpoint functions
- Pattern: Remove dict checking, return models directly

**api/endpoints/users.py** - UserService endpoints
- Estimated: 6-10 endpoint functions
- Pattern: Remove dict checking, return models directly

**api/endpoints/products.py** - ProductService endpoints
- Estimated: 6-8 endpoint functions
- Pattern: Remove dict checking, return models directly

### Priority 2: Task/Project Endpoints (45-60 minutes)

**api/endpoints/tasks.py** - TaskService endpoints
- Estimated: 6-8 endpoint functions
- Pattern: Remove dict checking, return models directly

**api/endpoints/projects.py** - ProjectService endpoints
- Estimated: 5-7 endpoint functions
- Pattern: Remove dict checking, return models directly

**api/endpoints/messages.py** - MessageService endpoints
- Estimated: 4-6 endpoint functions
- Pattern: Remove dict checking, return models directly

### Priority 3: Orchestration Endpoints (30-45 minutes)

**api/endpoints/orchestration.py** - OrchestrationService endpoints
- Estimated: 4-6 endpoint functions
- Pattern: Remove dict checking, return models directly

**api/endpoints/context.py** - ContextService endpoints
- Estimated: 3-4 endpoint functions
- Pattern: Remove dict checking, return models directly

**api/endpoints/templates.py** - TemplateService endpoints
- Estimated: 3-4 endpoint functions
- Pattern: Remove dict checking, return models directly

---

## Success Criteria

**CODE QUALITY:**
- ✅ Zero dict checking logic in API endpoints (`if not result["success"]:` removed)
- ✅ All endpoints rely on exception-based error handling
- ✅ Docstrings include Raises sections for documentation
- ✅ Return statements simplified (no dict unpacking)

**TESTING:**
- ✅ All API integration tests passing: `pytest tests/api/ -v`
- ✅ Proper HTTP status codes returned (404, 409, 422, etc.)
- ✅ Exception messages clear and consistent
- ✅ No regressions in full test suite

**EXCEPTION HANDLING:**
- ✅ All service exceptions mapped to HTTP status codes
- ✅ Exception handlers complete in api/exception_handlers.py
- ✅ Error responses consistent across all endpoints

**VALIDATION:**
- ✅ No dict checking patterns remain: `grep -r "result\[\"success\"\]" api/endpoints/`
- ✅ Manual testing successful for create/read/update/delete operations
- ✅ Error cases return proper HTTP status codes

---

## Validation Commands

```bash
# Verify no dict checking logic remains
grep -r "result\[\"success\"\]" api/endpoints/ --include="*.py"
# Should return nothing

grep -r "not result\[\"success\"\]" api/endpoints/ --include="*.py"
# Should return nothing

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

## Common Patterns

### Pattern 1: Simple GET endpoint

**Before:**
```python
result = await service.get_item(item_id)
if not result["success"]:
    raise HTTPException(status_code=400, detail=result["error"])
return ItemResponse(**result["data"])
```

**After:**
```python
item = await service.get_item(item_id)  # Raises ItemNotFoundError if not found
return ItemResponse.from_orm(item)
```

### Pattern 2: CREATE endpoint

**Before:**
```python
result = await service.create_item(item_data)
if not result["success"]:
    raise HTTPException(status_code=400, detail=result["error"])
return ItemResponse(**result["data"])
```

**After:**
```python
item = await service.create_item(item_data)  # Raises ItemAlreadyExistsError if duplicate
return ItemResponse.from_orm(item)
```

### Pattern 3: LIST endpoint

**Before:**
```python
result = await service.list_items()
if not result["success"]:
    raise HTTPException(status_code=400, detail=result["error"])
return [ItemResponse(**item) for item in result["data"]]
```

**After:**
```python
items = await service.list_items()  # Returns list[Item]
return [ItemResponse.from_orm(item) for item in items]
```

### Pattern 4: UPDATE endpoint

**Before:**
```python
result = await service.update_item(item_id, updates)
if not result["success"]:
    raise HTTPException(status_code=400, detail=result["error"])
return ItemResponse(**result["data"])
```

**After:**
```python
item = await service.update_item(item_id, updates)  # Raises ItemNotFoundError if not found
return ItemResponse.from_orm(item)
```

---

## Risks and Considerations

**BREAKING CHANGES:**
Risk: Frontend may depend on specific error response format
Mitigation: Exception handlers return same `{"detail": "..."}` format, just with proper HTTP codes

**STATUS CODE CHANGES:**
Risk: Some errors previously returned 400, now return proper codes (404, 409, etc.)
Impact: This is INTENTIONAL improvement - proper REST semantics
Mitigation: Update frontend error handling if needed (future work)

**TEST UPDATES:**
Risk: Integration tests may expect old dict format or wrong status codes
Mitigation: Update tests to expect proper HTTP status codes and model responses

**EXCEPTION HANDLER GAPS:**
Risk: Service may raise exception not handled in api/exception_handlers.py
Mitigation: Verify exception handlers in Step 1, add any missing handlers

---

## Reference Materials

**REQUIRED READING:**
- docs/architecture/exception_mapping.md (from 0730a)
- docs/architecture/api_exception_handling.md (from 0730a)

**CODE REFERENCES:**
- api/exception_handlers.py: Exception-to-HTTP mapping
- api/endpoints/: All endpoint files
- tests/api/: Integration test files

**DOCUMENTATION:**
- SERVER_ARCHITECTURE_TECH_STACK.md: API architecture
- TESTING.md: Integration testing patterns

---

## Recommended Sub-Agent

**Agent:** backend-integration-tester

**Why this agent:**
- API endpoint expertise
- Integration testing experience
- HTTP status code validation
- End-to-end workflow testing

---

## Definition of Done

1. ✅ All dict checking logic removed from endpoints
2. ✅ All API integration tests passing
3. ✅ Exception handlers verified complete
4. ✅ Proper HTTP status codes returned (404, 409, 422, etc.)
5. ✅ Docstrings updated with Raises sections
6. ✅ Validation commands all pass
7. ✅ Manual testing successful
8. ✅ Ready for 0730d (final validation)

---

## Timeline Estimate

- Exception Handler Verification: 15 minutes
- Priority 1 Endpoints: 1-1.5 hours
- Priority 2 Endpoints: 45-60 minutes
- Priority 3 Endpoints: 30-45 minutes
- Testing and Validation: 30-60 minutes

**TOTAL:** 2-4 hours (backend-integration-tester agent)

---

## Next Steps After Completion

**Handoff to 0730d (Final Validation):**
- All endpoints simplified
- Exception-based error handling complete
- Update comms_log.json with completion status
- Mark 0730c as COMPLETE in orchestrator_state.json
- Unblock 0730d for final validation

**Communication to Orchestrator:**
```json
{
  "from": "0730c",
  "to": "orchestrator",
  "status": "complete",
  "summary": {
    "endpoints_updated": "~50-70",
    "dict_checks_removed": "~50-70",
    "tests_passing": "100%",
    "exception_handlers_verified": true
  },
  "key_outcomes": [
    "All dict checking logic removed from endpoints",
    "Proper HTTP status codes now returned (404, 409, 422, etc.)",
    "Exception handlers verified complete",
    "All API integration tests passing"
  ],
  "ready_for": ["0730d"]
}
```

---

**Created:** 2026-02-07
**Status:** BLOCKED (waiting for 0730b)
**Priority:** P2 - MEDIUM
**Blocks:** 0730d

---

## Notes for Executor

1. **Verify Handlers First** - Check api/exception_handlers.py before updating endpoints
2. **Use Serena MCP** - Symbolic editing is much faster than reading entire files
3. **Test Frequently** - Run integration tests after each file update
4. **Commit Per File** - One commit per endpoint file for easier rollback
5. **Watch HTTP Codes** - Verify proper status codes (404, 409, etc.) not generic 400
6. **Update Docstrings** - Add Raises sections for documentation
7. **Pattern Consistency** - Similar endpoints should have similar code
8. **Don't Skip Testing** - Integration tests catch subtle issues
9. **Check Frontend Impact** - If status codes change, note for future frontend updates
10. **Quality Over Speed** - Better to take extra time and verify thoroughly

This phase should be straightforward - services already refactored in 0730b.
