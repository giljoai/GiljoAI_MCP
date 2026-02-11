# Handover 0731b: Tier 1 Service Refactoring (69 methods)

**Handover ID:** 0731b
**Series:** 0731 Typed Service Returns (Part 2/4)
**Phase:** Tier 1 Service Refactoring
**Priority:** P1 - HIGH
**Estimated Effort:** 8-12 hours
**Status:** BLOCKED (needs 0731a)
**Branch:** `feature/0731-typed-service-returns`
**Dependencies:** 0731a (response models must exist)
**Blocks:** 0731c, 0731d

---

## 1. Mission & Context

### What We're Doing
Refactor the 3 highest-impact services to replace `dict[str, Any]` returns with typed returns and exception-based error handling. These 3 services account for 57% of all dict wrapper instances.

### Services in Scope

| Service | File | Dict Wrappers | Methods |
|---------|------|---------------|---------|
| OrgService | `src/giljo_mcp/services/org_service.py` | 33 | ~16 |
| UserService | `src/giljo_mcp/services/user_service.py` | 12-19 | ~12 |
| ProductService | `src/giljo_mcp/services/product_service.py` | 17 | ~15 |

### The Transformation Pattern

**Before (current anti-pattern):**
```python
async def get_organization(self, org_id: str) -> dict[str, Any]:
    org = await session.get(Organization, org_id)
    if not org:
        return {"success": False, "error": "Organization not found"}
    return {"success": True, "data": org}
```

**After (typed return + exception):**
```python
async def get_organization(self, org_id: str) -> Organization:
    org = await session.get(Organization, org_id)
    if not org:
        raise ResourceNotFoundError(
            message="Organization not found",
            context={"org_id": org_id}
        )
    return org
```

### Design Reference
- **Full method catalogue**: `docs/architecture/service_response_models.md`
- **Response models**: `src/giljo_mcp/schemas/service_responses.py` (created in 0731a)
- **Exception hierarchy**: `src/giljo_mcp/exceptions.py`
- **Chain log**: `prompts/0731_chain/chain_log.json` (check 0731a notes_for_next)

---

## 2. What Will Change

### Modified Files
- `src/giljo_mcp/services/org_service.py` - Remove dict wrappers, add exceptions
- `src/giljo_mcp/services/user_service.py` - Remove dict wrappers, add exceptions
- `src/giljo_mcp/services/product_service.py` - Remove dict wrappers, add exceptions

### Modified Test Files
- `tests/services/test_org_service.py` - Update for typed returns
- `tests/services/test_user_service.py` - Update for typed returns
- `tests/services/test_product_service.py` - Update for typed returns

---

## 3. Embedded Coding Principles

You MUST follow these principles:

1. **Use Serena MCP tools** for code exploration - find all callers of each method before changing its signature
2. **Follow TDD**: Update tests FIRST to expect new return types, then modify service code
3. **One service at a time**: Complete and commit OrgService before starting UserService
4. **Multi-tenant isolation**: Preserve `tenant_key` filtering in all queries - do not change query logic
5. **Exception imports**: Use existing exceptions from `src/giljo_mcp/exceptions.py` - do NOT create new exception classes
6. **Backward compatibility**: API endpoints will still check `result["success"]` until 0731d. If a service method is called by an endpoint, verify the endpoint can handle the new return type OR leave a temporary adapter (document in notes_for_next)
7. **Clean code**: Remove ALL dict wrapper construction code, don't leave commented-out versions
8. **Use subagents**: One `tdd-implementor` per service is the recommended pattern

---

## 4. Implementation Details

### Refactoring Rules

**Rule 1: Simple lookups return the model directly**
```python
# Before
return {"success": True, "data": org}
# After
return org
```

**Rule 2: Not-found cases raise ResourceNotFoundError**
```python
# Before
return {"success": False, "error": "Not found"}
# After
raise ResourceNotFoundError(message="Organization not found", context={"org_id": org_id})
```

**Rule 3: Validation failures raise ValidationError**
```python
# Before
return {"success": False, "error": "Invalid role"}
# After
raise ValidationError(message="Invalid role", context={"role": role})
```

**Rule 4: Authorization failures raise AuthorizationError**
```python
# Before
return {"success": False, "error": "Not authorized"}
# After
raise AuthorizationError(message="Only owner can transfer", context={"user_id": user_id})
```

**Rule 5: Duplicate/conflict raises AlreadyExistsError**
```python
# Before
return {"success": False, "error": "Already exists"}
# After
raise AlreadyExistsError(message="Slug already exists", context={"slug": slug})
```

**Rule 6: Delete operations return DeleteResult**
```python
# Before
return {"success": True, "data": {"deleted": True}}
# After
return DeleteResult(id=org_id)
```

**Rule 7: List operations return the list directly**
```python
# Before
return {"success": True, "data": members}
# After
return members  # list[OrgMembership]
```

**Rule 8: Methods already returning bool/str/None stay unchanged**

### Service Processing Order

1. **OrgService** (33 wrappers) - Start here, highest count
2. **UserService** (12-19 wrappers) - Medium complexity
3. **ProductService** (17 wrappers) - Highest integration risk (most endpoint callers)

### CRITICAL: Check Endpoint Callers

Before modifying each service method, use Serena to find all callers:
```
mcp__serena__find_referencing_symbols("get_organization")
```

If an endpoint calls the method and checks `result["success"]`, note it for 0731d. The service change will break that endpoint temporarily - this is expected and will be fixed in 0731d. However, if a method is called by OTHER services (not endpoints), those must be updated in this phase.

---

## 5. TDD Workflow

**MANDATORY: Update tests FIRST, then modify service code.**

For each service method:

```python
# Step 1: Update test to expect new return type
async def test_get_organization_returns_model(org_service):
    """get_organization should return Organization model directly."""
    result = await org_service.get_organization(test_org_id)
    assert isinstance(result, Organization)
    assert result.id == test_org_id

async def test_get_organization_not_found_raises(org_service):
    """get_organization should raise ResourceNotFoundError for missing org."""
    with pytest.raises(ResourceNotFoundError) as exc_info:
        await org_service.get_organization("nonexistent-id")
    assert "nonexistent-id" in str(exc_info.value.context)

# Step 2: Run test - it should FAIL (service still returns dict)
# Step 3: Modify service code
# Step 4: Run test - it should PASS
# Step 5: Run ALL service tests to verify no regressions
```

---

## 6. Serena MCP Usage Requirements

**REQUIRED** - Use these tools:

```
mcp__serena__get_symbols_overview(file_path) - List all methods in a service
mcp__serena__find_symbol("OrgService") - Find the class definition
mcp__serena__find_referencing_symbols("create_organization") - Find all callers
mcp__serena__replace_symbol_body(symbol_name, new_body) - Replace method implementations
```

Use Serena to:
1. Get current method signatures before modifying
2. Find ALL callers of each method (services AND endpoints)
3. Verify no circular dependencies between services
4. Replace method bodies efficiently using `replace_symbol_body`

---

## 7. Testing Requirements

After each service refactor:
```bash
pytest tests/services/test_org_service.py -v        # After OrgService
pytest tests/services/test_user_service.py -v        # After UserService
pytest tests/services/test_product_service.py -v     # After ProductService
```

After all three:
```bash
pytest tests/services/ -v  # All service tests
```

**Note from 0750a**: `pytest` full suite may hang without `pytest-timeout`. Use targeted test runs.

---

## 8. Definition of Done

- [ ] OrgService: All dict wrappers replaced with typed returns + exceptions
- [ ] UserService: All dict wrappers replaced with typed returns + exceptions
- [ ] ProductService: All dict wrappers replaced with typed returns + exceptions
- [ ] Tests updated FIRST (TDD) for all three services
- [ ] All service tests passing
- [ ] Serena MCP tools used for caller discovery
- [ ] No regressions in existing tests
- [ ] Each service committed separately
- [ ] Chain log updated with notes about endpoint impacts
- [ ] STOPPED - awaiting 0731c execution via chain

---

## 9. Git Commit Standards

Commit after EACH service (3 commits total):

```bash
# After OrgService
git commit -m "refactor(0731b): OrgService typed returns - remove 33 dict wrappers

Replace dict[str, Any] returns with typed model returns and exception-based
error handling. Tests updated first per TDD workflow.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"

# After UserService
git commit -m "refactor(0731b): UserService typed returns - remove N dict wrappers
..."

# After ProductService
git commit -m "refactor(0731b): ProductService typed returns - remove N dict wrappers
..."
```

---

## 10. STOP Boundary

## CRITICAL: STOP AFTER COMPLETION

**DO NOT PROCEED TO 0731c WITHOUT COMPLETING THE CHAIN STEPS BELOW.**

This phase is complete when all three Tier 1 services have typed returns.
Update the chain log, then spawn the next terminal.

---

## Chain Execution Instructions

### Step 1: Read Chain Log
Read `prompts/0731_chain/chain_log.json`. Check 0731a's `notes_for_next` for model details.
Verify 0731a status is `complete`. If not, STOP and report.
Mark your session as `"status": "in_progress", "started_at": "<timestamp>"`.

### Step 2: Execute Handover Tasks

**CRITICAL: Use Task tool to spawn subagents for this work. Do NOT do all work directly.**

Recommended: Spawn one tdd-implementor per service (sequentially, NOT parallel - each builds on shared test infrastructure):

```
Task(subagent_type="tdd-implementor", prompt="Refactor OrgService in src/giljo_mcp/services/org_service.py. Replace all dict[str, Any] returns with typed returns. Use ResourceNotFoundError, ValidationError, AuthorizationError, AlreadyExistsError from src/giljo_mcp/exceptions.py. Use DeleteResult from src/giljo_mcp/schemas/service_responses.py for delete operations. Follow TDD: update tests in tests/services/test_org_service.py FIRST. Use Serena MCP tools to find all callers before changing signatures. Reference: docs/architecture/service_response_models.md for the full method catalogue. Commit when done.")
```

Then for UserService and ProductService similarly.

### Step 3: Verify
After all three services:
1. Run `pytest tests/services/ -v` - all pass
2. Run `ruff check src/giljo_mcp/services/`

### Step 4: Update Chain Log
Update `prompts/0731_chain/chain_log.json` for session 0731b:
- `tasks_completed`: Methods changed per service
- `notes_for_next`: Which endpoint files need updating (from caller analysis)
- `summary`: 2-3 sentences
- `status`: "complete"

### Step 5: Spawn Next Terminal
**Use Bash tool to EXECUTE this command (Don't Just Print It!):**

```powershell
powershell.exe -Command "Start-Process wt -ArgumentList '--title \"0731c - Tier 2+3 Service Refactor\" --tabColor \"#9C27B0\" -d \"F:\GiljoAI_MCP\" cmd /k claude --dangerously-skip-permissions \"Execute handover 0731c. READ F:\GiljoAI_MCP\handovers\0731c_tier23_service_refactor.md for full instructions. Check chain log at F:\GiljoAI_MCP\prompts\0731_chain\chain_log.json first. Branch: feature/0731-typed-service-returns. Use Task subagents (tdd-implementor) for the refactoring work.\"' -Verb RunAs"
```

**CRITICAL: DO NOT SPAWN DUPLICATE TERMINALS!**
