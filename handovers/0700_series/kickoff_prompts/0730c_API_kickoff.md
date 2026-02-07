# Kickoff Prompt: 0730c Update API Endpoints

**Agent Role:** backend-integration-tester
**Estimated Time:** 2-4 hours
**Prerequisites:** 0730b COMPLETE, read this entire prompt before starting

---

## Your Mission

You are a **backend-integration-tester** agent executing **Handover 0730c: Update API Endpoints**.

Your goal is to update ~50-70 API endpoints to remove dict checking logic and rely on exception-based error handling from refactored services.

**This is Phase 3 of 4** in the 0730 Service Response Models series. Services have been refactored in 0730b to return models and raise exceptions. You need to simplify endpoints to match.

---

## Critical Context

**Full Handover Specification:**
Read `F:\GiljoAI_MCP\handovers\0730c_UPDATE_API_ENDPOINTS.md` completely before starting.

**Required Reading (from 0730a):**
- `docs/architecture/api_exception_handling.md` - API pattern guide

**Project:** GiljoAI MCP v1.0 - Multi-tenant agent orchestration server
**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy, PostgreSQL
**Branch:** feature/0700-code-cleanup-series

**IMPORTANT:** Services already refactored in 0730b - they now return models and raise exceptions. Endpoints just need to remove dict checking logic.

---

## Scope: ~50-70 Endpoint Functions

**Priority 1** (1-1.5 hours):
- api/endpoints/orgs.py (8-12 functions)
- api/endpoints/users.py (6-10 functions)
- api/endpoints/products.py (6-8 functions)

**Priority 2** (45-60 minutes):
- api/endpoints/tasks.py (6-8 functions)
- api/endpoints/projects.py (5-7 functions)
- api/endpoints/messages.py (4-6 functions)

**Priority 3** (30-45 minutes):
- api/endpoints/orchestration.py (4-6 functions)
- api/endpoints/context.py (3-4 functions)
- api/endpoints/templates.py (3-4 functions)

---

## Migration Pattern

### Current Pattern (to remove):

```python
@router.get("/{org_id}/")
async def get_org(
    org_id: str,
    org_service: OrgService = Depends(get_org_service),
) -> OrgResponse:
    result = await org_service.get_org(org_id)

    if not result["success"]:  # ← REMOVE THIS
        raise HTTPException(status_code=400, detail=result["error"])

    return OrgResponse(**result["data"])  # ← SIMPLIFY THIS
```

### Target Pattern:

```python
@router.get("/{org_id}/")
async def get_org(
    org_id: str,
    org_service: OrgService = Depends(get_org_service),
) -> OrgResponse:
    """Get organization by ID.

    Raises:
        OrgNotFoundError: Organization not found (404)
    """
    # Service raises OrgNotFoundError if not found
    # Exception handler converts to HTTP 404
    org = await org_service.get_org(org_id)
    return OrgResponse.from_orm(org)
```

**Key changes:**
1. Remove `result` variable and dict checking
2. Call service method directly
3. Let exceptions propagate
4. Simplify return statement
5. Add Raises docstring section

---

## Step-by-Step Instructions

### Step 1: Verify Exception Handlers (15 minutes)

**Read:** `api/exception_handlers.py`

**Verify handlers exist for:**
- NotFoundError → 404
- AlreadyExistsError → 409
- ValidationError → 422
- UnauthorizedError → 403
- AuthenticationError → 401
- InternalServerError → 500

**If gaps found, add handlers:**
```python
@app.exception_handler(OrgNotFoundError)
async def org_not_found_handler(request: Request, exc: OrgNotFoundError):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(exc)},
    )
```

### Step 2: Update Endpoints by File (2-3 hours)

**For each API file:**

1. **Search for dict checking patterns:**
   ```bash
   grep -n "result\[\"success\"\]" api/endpoints/orgs.py
   ```

2. **Use Serena MCP for efficiency:**
   ```python
   # Get overview of endpoint functions
   mcp__serena__get_symbols_overview(relative_path="api/endpoints/orgs.py")

   # Read specific endpoint
   mcp__serena__find_symbol(
       name_path_pattern="get_org",
       relative_path="api/endpoints/orgs.py",
       include_body=True
   )
   ```

3. **For each endpoint function:**
   - Remove `result = ` assignment
   - Remove `if not result["success"]:` block
   - Change service call to direct assignment
   - Update return statement to use model directly
   - Add Raises section to docstring

4. **Update using symbolic edit:**
   ```python
   mcp__serena__replace_symbol_body(
       name_path="get_org",
       relative_path="api/endpoints/orgs.py",
       body="""async def get_org(
       org_id: str,
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

5. **Test after each file:**
   ```bash
   pytest tests/api/test_orgs_api.py -v
   ```

6. **Fix any test failures:**
   - Update tests to expect proper HTTP status codes
   - Verify exception messages correct

7. **Commit after each file:**
   ```bash
   git add api/endpoints/orgs.py tests/api/test_orgs_api.py
   git commit -m "refactor(0730c): Remove dict checking from orgs endpoints (12 functions)

   - Services now raise exceptions instead of returning dicts
   - Endpoints simplified to rely on exception handlers
   - Proper HTTP status codes (404, 409, etc.)

   Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
   ```

### Step 3: Final Validation (30 minutes)

```bash
# Verify no dict checking remains
grep -r "result\[\"success\"\]" api/endpoints/ --include="*.py"
# Expected: No results

# Run all API tests
pytest tests/api/ -v

# Run full test suite
pytest tests/ -v

# Manual spot check via dashboard
# - Create org (should return 409 if duplicate)
# - Get org (should return 404 if not found)
# - Update org (should return 404 if not found)
```

---

## Common Patterns Reference

### Pattern 1: Simple GET
```python
# Before:
result = await service.get_item(item_id)
if not result["success"]:
    raise HTTPException(status_code=400, detail=result["error"])
return ItemResponse(**result["data"])

# After:
item = await service.get_item(item_id)
return ItemResponse.from_orm(item)
```

### Pattern 2: CREATE
```python
# Before:
result = await service.create_item(item_data)
if not result["success"]:
    raise HTTPException(status_code=400, detail=result["error"])
return ItemResponse(**result["data"])

# After:
item = await service.create_item(item_data)
return ItemResponse.from_orm(item)
```

### Pattern 3: LIST
```python
# Before:
result = await service.list_items()
if not result["success"]:
    raise HTTPException(status_code=400, detail=result["error"])
return [ItemResponse(**item) for item in result["data"]]

# After:
items = await service.list_items()
return [ItemResponse.from_orm(item) for item in items]
```

---

## Success Criteria

You are COMPLETE when:
1. ✅ All dict checking logic removed from endpoints
2. ✅ All API integration tests passing
3. ✅ Exception handlers verified complete
4. ✅ Proper HTTP status codes returned (404, 409, 422)
5. ✅ Docstrings updated with Raises sections
6. ✅ Validation commands pass
7. ✅ Manual testing successful
8. ✅ Ready for 0730d (final validation)

---

## Validation Commands

```bash
# Verify no dict checking
grep -r "result\[\"success\"\]" api/endpoints/ --include="*.py"
grep -r "not result\[\"success\"\]" api/endpoints/ --include="*.py"

# Run API tests
pytest tests/api/ -v

# Check coverage
pytest tests/api/ --cov=api/endpoints/ --cov-report=term-missing

# Full test suite
pytest tests/ -v

# Pre-commit hooks
pre-commit run --all-files
```

---

## Troubleshooting

**If tests fail:**
- Check if test expects old dict format - update test
- Verify HTTP status code is correct (404 not 400)
- Ensure exception message matches test expectation
- Check exception handler is registered

**If exception not caught:**
- Verify handler exists in api/exception_handlers.py
- Check exception is imported correctly
- Ensure handler is registered with app

**If wrong HTTP code:**
- Check exception type matches error scenario
- Verify exception handler maps to correct code
- Update exception type if needed

---

## Handoff Protocol

When complete, update tracking:

**Update `handovers/0700_series/comms_log.json`:**
```json
{
  "timestamp": "2026-02-07T[TIME]Z",
  "from": "0730c",
  "to": "orchestrator",
  "type": "phase_complete",
  "phase": "api_updates",
  "summary": {
    "endpoints_updated": "~60",
    "dict_checks_removed": "~60",
    "tests_passing": "100%",
    "exception_handlers_verified": true
  },
  "key_outcomes": [
    "All dict checking logic removed",
    "Proper HTTP status codes (404, 409, 422)",
    "Exception handlers verified complete",
    "All API tests passing"
  ],
  "ready_for": ["0730d"]
}
```

**Mark ready:** Update `handovers/0700_series/orchestrator_state.json` to mark 0730c COMPLETE.

---

## Resources

**Critical Files:**
- `handovers/0730c_UPDATE_API_ENDPOINTS.md` - Full specification
- `docs/architecture/api_exception_handling.md` - Pattern guide (from 0730a)
- `api/exception_handlers.py` - Exception-to-HTTP mapping
- `api/endpoints/*.py` - All endpoint files
- `tests/api/*.py` - Integration test files

---

## Important Notes

1. **Verify Handlers First** - Check exception_handlers.py before starting
2. **Use Serena MCP** - Symbolic editing is faster
3. **Test Frequently** - After each file update
4. **Commit Per File** - Easier rollback
5. **Watch HTTP Codes** - 404, 409, 422 not generic 400
6. **Update Docstrings** - Add Raises sections
7. **Pattern Consistency** - Similar endpoints = similar code
8. **Don't Skip Testing** - Integration tests catch issues
9. **Frontend Impact** - Note status code changes
10. **Quality Over Speed** - Verify thoroughly

---

**Ready to start?**

1. Read full handover specification
2. Verify exception handlers exist
3. Begin Priority 1: orgs.py, users.py, products.py

Good luck! This should be straightforward - services already refactored.
