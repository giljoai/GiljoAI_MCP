# Handover 0731d: API Endpoint Updates + Final Validation

**Handover ID:** 0731d
**Series:** 0731 Typed Service Returns (Part 4/4 - FINAL)
**Phase:** API Endpoint Updates & Validation
**Priority:** P1 - HIGH
**Estimated Effort:** 4-8 hours
**Status:** BLOCKED (needs 0731c)
**Branch:** `feature/0731-typed-service-returns`
**Dependencies:** 0731c (ALL services must have typed returns)

---

## 1. Mission & Context

### What We're Doing
This is the FINAL phase. All 14 services now return typed models and raise exceptions (completed in 0731b+c). API endpoints still contain dict-checking patterns like `if result["success"]`. This phase removes those patterns and updates endpoints to use typed returns directly.

### Why This Phase Exists
The global exception handler (`api/exception_handlers.py`) already maps domain exceptions to HTTP responses. With services now raising exceptions instead of returning error dicts, endpoints no longer need:
- `if result["success"]` checks
- Manual HTTPException construction from dict errors
- `raise_for_service_result()` utility calls

### After This Phase
- Zero `result["success"]` patterns in endpoint code
- Zero `dict[str, Any]` return annotations in service code
- Clean, typed flow: Service returns model -> Endpoint returns response -> Client gets JSON
- Exceptions flow: Service raises -> Global handler catches -> Client gets HTTP error

---

## 2. What Will Change

### Modified Endpoint Files
Check chain log `notes_for_next` from 0731b and 0731c for the definitive list. Expected files:

**Products endpoints:**
- `api/endpoints/products/crud.py`
- `api/endpoints/products/lifecycle.py`
- `api/endpoints/products/vision.py`
- `api/endpoints/products/git_integration.py`

**Other endpoints:**
- `api/endpoints/orgs.py`
- `api/endpoints/users.py`
- `api/endpoints/auth.py`
- `api/endpoints/tasks.py`
- `api/endpoints/projects.py`
- `api/endpoints/messages.py`
- `api/endpoints/orchestration.py`
- `api/endpoints/templates.py`
- `api/endpoints/settings.py`
- `api/endpoints/configuration.py`

### Potentially Removed Files
- Any `raise_for_service_result` utility (if it exists)

### Modified Test Files
- All endpoint test files that mock service returns with dicts

---

## 3. Embedded Coding Principles

You MUST follow these principles:

1. **Use Serena MCP tools** for code exploration
2. **Follow TDD**: Update endpoint tests FIRST
3. **One endpoint file at a time**: Complete and verify each
4. **IMPORTANT**: `api/endpoints/products/` is gitignored - use `git add -f` for files there
5. **Preserve response schemas**: If endpoints use Pydantic response models (e.g., `ProductResponse`), keep those - just change how they're constructed (from dict data to typed service returns)
6. **Global exception handler**: Verify it covers all cases - do NOT add per-endpoint try/except (0750a just removed those!)
7. **Clean code**: Remove ALL dict-checking patterns
8. **Use subagents**: One per endpoint group

---

## 4. Implementation Details

### The Transformation Pattern

**Before (dict-checking):**
```python
@router.get("/{org_id}")
async def get_organization(org_id: str, current_user: User = Depends(get_current_user)):
    service = OrgService(db_manager, current_user.tenant_key)
    result = await service.get_organization(org_id)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["error"])
    return result["data"]
```

**After (typed returns - clean):**
```python
@router.get("/{org_id}")
async def get_organization(org_id: str, current_user: User = Depends(get_current_user)):
    service = OrgService(db_manager, current_user.tenant_key)
    return await service.get_organization(org_id)
    # ResourceNotFoundError raised by service -> caught by global handler -> 404
```

### What to Remove From Each Endpoint

1. `if result["success"]` / `if not result["success"]` checks
2. `result["data"]` unwrapping (service now returns the data directly)
3. `result["error"]` extraction for HTTPException
4. `raise HTTPException(status_code=..., detail=result["error"])` (global handler does this)
5. Any `raise_for_service_result(result)` calls
6. Import of `raise_for_service_result` if it exists

### What to KEEP

1. Authentication/authorization decorators (`Depends(get_current_user)`)
2. Request validation (Pydantic request models)
3. Response model annotations on routes (e.g., `response_model=ProductResponse`)
4. Endpoint-specific response construction (e.g., building `ProductResponse` from service data)
5. WebSocket event emissions (if any remain after 0750a cleanup)

### ProductResponse Construction Pattern

Some endpoints construct `ProductResponse` manually from service data:
```python
# This pattern may need updating if ProductService now returns Product model:
product = await service.get_product(product_id)  # Now returns Product, not dict
return ProductResponse(
    id=str(product.id),
    name=product.name,
    # ... map from SQLAlchemy model to Pydantic response
)
```

This is fine - keep it. The change is just that `product` is now a typed `Product` model instead of `result["data"]`.

---

## 5. TDD Workflow

For each endpoint file:

```python
# Step 1: Update test to mock service with typed returns
async def test_get_organization(client, mock_org_service):
    mock_org_service.get_organization.return_value = Organization(id="123", name="Test")
    # NOT: mock_org_service.get_organization.return_value = {"success": True, "data": {...}}

    response = await client.get("/api/orgs/123")
    assert response.status_code == 200

# Step 2: Update test for error case
async def test_get_organization_not_found(client, mock_org_service):
    mock_org_service.get_organization.side_effect = ResourceNotFoundError("Not found")
    # NOT: mock_org_service.get_organization.return_value = {"success": False, "error": "Not found"}

    response = await client.get("/api/orgs/nonexistent")
    assert response.status_code == 404
```

---

## 6. Serena MCP Usage Requirements

Use Serena to:
1. Find all endpoints that call each service method
2. Verify endpoint response model annotations
3. Check for any `raise_for_service_result` utility location

---

## 7. Testing Requirements

After each endpoint file:
```bash
pytest tests/endpoints/test_<endpoint>.py -v  # or similar path
```

Final comprehensive check:
```bash
# Verify zero dict-checking patterns remain
grep -r 'result\["success"\]' api/endpoints/ | wc -l  # Should be 0
grep -r "raise_for_service_result" api/ | wc -l  # Should be 0

# Verify zero dict return annotations in services
grep -r "-> dict\[str, Any\]" src/giljo_mcp/services/ | wc -l  # Should be 0

# Build check
cd frontend && npm run build  # Should pass (no backend changes affect frontend)
```

---

## 8. Definition of Done

- [ ] All endpoint files updated to use typed service returns
- [ ] Zero `result["success"]` patterns remaining in endpoint code
- [ ] Zero `dict[str, Any]` return annotations in service code
- [ ] All endpoint tests updated for typed mocks
- [ ] All tests passing
- [ ] Frontend build passes
- [ ] No redundant try/except blocks added (global handler covers all cases)
- [ ] Changes committed
- [ ] Completion report written
- [ ] Chain marked complete
- [ ] Branch ready for merge

---

## 9. Git Commit Standards

Commit after each endpoint group:

```bash
git commit -m "refactor(0731d): Update product endpoints for typed service returns

Remove dict-checking patterns from crud.py, lifecycle.py, vision.py,
git_integration.py. Services now return typed models and raise exceptions.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

Final commit:
```bash
git commit -m "chore(0731d): Final validation + completion report

Zero dict wrappers remaining. All services return typed models. All endpoints
use typed returns. Architecture score improvement documented.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## 10. STOP Boundary

## CHAIN COMPLETE - This is the LAST session.

---

## Chain Execution Instructions

### Step 1: Read Chain Log
Read `prompts/0731_chain/chain_log.json`. Review ALL previous sessions' `notes_for_next`.
Verify 0731a, 0731b, 0731c are all `complete`. If any are not, STOP and report.

### Step 2: Execute Handover Tasks

**CRITICAL: Use Task tool to spawn subagents for this work. Do NOT do all work directly.**

Recommended: Spawn agents per endpoint group:

```
Task(subagent_type="tdd-implementor", prompt="Update product endpoints (api/endpoints/products/crud.py, lifecycle.py, vision.py, git_integration.py) to use typed service returns. Remove all result['success'] checking patterns. Services now return models directly and raise exceptions. Update tests first. IMPORTANT: use git add -f for files in api/endpoints/products/ due to gitignore. Commit when done.")
```

```
Task(subagent_type="tdd-implementor", prompt="Update remaining endpoints (orgs.py, users.py, auth.py, tasks.py, projects.py, messages.py, orchestration.py, templates.py, settings.py, configuration.py) in api/endpoints/ to use typed service returns. Remove all result['success'] checking patterns. Update tests first. Commit when done.")
```

### Step 3: Final Verification
```bash
# Zero dict patterns remaining
grep -r 'result\["success"\]' api/endpoints/
grep -r "-> dict\[str, Any\]" src/giljo_mcp/services/

# Tests pass
pytest tests/ -x -q --timeout=30

# Frontend builds
cd frontend && npm run build
```

### Step 4: Write Completion Report
Create `handovers/0731_COMPLETION_REPORT.md`:
- Summary of all work across 0731a-d
- Total methods refactored
- Total lines changed
- Before/after code examples
- Architecture score impact

### Step 5: Update Chain Log - COMPLETE CHAIN
Update `prompts/0731_chain/chain_log.json`:
- Update session 0731d with results
- Set `"final_status": "complete"`
- Set `"chain_summary"`: Full summary of all 4 sessions

### Step 6: CHAIN COMPLETE
This is the LAST session. Do NOT spawn another terminal.

1. Print a summary of everything done across the chain
2. Report whether the branch is ready to merge to master
3. If ready: "Branch `feature/0731-typed-service-returns` is ready for merge. Run: `git checkout master && git merge feature/0731-typed-service-returns`"
4. If NOT ready: explain what remains
