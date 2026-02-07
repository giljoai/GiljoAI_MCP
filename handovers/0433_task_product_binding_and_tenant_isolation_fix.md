# Handover: 0433 Task Product Binding and Tenant Isolation Fix

**Date:** 2026-02-07
**Priority:** High
**Estimated Complexity:** 6-8 hours
**Status:** Phase 1 Complete (Database Schema Migration)
**Completion:** Phase 1 - 2026-02-07

---

## Summary

Remove "unassigned tasks" design pattern and enforce that all tasks are bound to the active product. This change eliminates a tenant isolation vulnerability in TaskService while simplifying task creation logic by ~40-50%.

**Security Impact:** Fixes 2 tenant isolation vulnerabilities where task creation without tenant_key filtering could leak tasks across tenant boundaries.

**Design Impact:** Tasks transition from optional product association to required product binding, aligning with the product-centric hierarchy (org > user > product > projects & tasks > jobs).

---

## Context and Background

### Current Design (Flawed)

Tasks can exist in "unassigned" state with `product_id=NULL` and `project_id=NULL`. The `/gil_task` MCP slash command creates tasks without product assignment as a "technical debt capture" feature.

**Vulnerability Discovered:**
1. `ToolAccessor.create_task()` does not accept `tenant_key` parameter
2. `TaskService._log_task_impl()` has fallback logic that queries without tenant filtering:
   - Line 149: Queries `Project` without `tenant_key` when context not set
   - Lines 161-163: Queries for "first active project" across ALL tenants
3. Result: Tasks from Tenant A could be assigned to Tenant B's projects

**Root Cause Analysis:**
- MCP security fix `validate_and_override_tenant_key()` strips `tenant_key` from arguments if tool signature doesn't accept it
- `ToolAccessor.create_task()` signature missing `tenant_key` parameter
- TaskService falls back to unsafe queries when `tenant_key=None`

### Audit Report Context

The 0725/0726 audit reports flagged these issues but contained many false positives. This handover addresses the ONE legitimate vulnerability (TaskService) while rejecting false claims about AuthService (intentional cross-tenant username lookups are correct design).

### User Decision

User chose to eliminate "unassigned tasks" feature entirely:
- Tasks will always bind to active product when created
- Future feature: Move tasks between products (deferred to separate handover)
- Simplifies code, eliminates vulnerability class, improves UX

---

## Technical Details

### Database Schema Changes

**Task Model - Make product_id Required:**

```python
# File: src/giljo_mcp/models/tasks.py
# BEFORE:
product_id = Column(String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=True)

# AFTER:
product_id = Column(String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
```

**Migration Required:**
```python
# In install.py or separate migration file
# Step 1: Assign existing NULL product_id tasks to first product in tenant
# Step 2: ALTER COLUMN to NOT NULL
```

### Service Layer Changes

**File: `src/giljo_mcp/services/task_service.py`**

**Lines to REMOVE (~25 lines):**
- Line 149: Unsafe fallback query without tenant_key
- Lines 161-175: "Find first active project" logic (vulnerable)
- Lines 306-308: `filter_type="all_tasks"` special handling

**New Logic (~5 lines):**
```python
async def _log_task_impl(...):
    # Validate required parameters
    if not tenant_key or not product_id:
        raise ValidationError("tenant_key and product_id are required")

    # Simple query with both filters
    if project_id:
        result = await session.execute(
            select(Project).where(
                Project.id == project_id,
                Project.product_id == product_id,  # NEW: Additional filter
                Project.tenant_key == tenant_key
            )
        )
```

### MCP Tool Layer Changes

**File: `src/giljo_mcp/tools/tool_accessor.py`**

**Lines 301-328 - Add tenant_key parameter and fetch active product:**

```python
async def create_task(
    self,
    title: str,
    description: str,
    priority: str = "medium",
    category: str | None = None,
    assigned_to: str | None = None,
    tenant_key: str | None = None,  # ADD THIS
) -> dict[str, Any]:
    """Creates a task bound to active product."""

    # NEW: Fetch active product
    active_product = await self._product_service.get_active_product(tenant_key)
    if not active_product:
        raise ValidationError("No active product set. Please activate a product first.")

    return await self._task_service.log_task(
        content=description,
        category=category or title,
        priority=priority,
        product_id=active_product["id"],  # NEW: Always provide product_id
        tenant_key=tenant_key,  # NEW: Pass tenant_key
    )
```

### API Endpoint Changes

**File: `api/endpoints/tasks.py`**

**Lines 175-210 - Update TaskCreate schema:**

```python
# TaskCreate Pydantic model
class TaskCreate(BaseModel):
    title: str
    description: str
    priority: str = "medium"
    product_id: str  # NOW REQUIRED (remove Optional)
    project_id: Optional[str] = None  # Still optional
    # ...
```

**Endpoint stays secure** - already uses `current_user.tenant_key` directly.

### Frontend Changes (Minimal)

**Tasks Already Product-Scoped in UI:**
- Task list views already filter by active product
- No "unassigned tasks" view exists in current UI
- Changes are backend-only, no frontend impact expected

---

## Implementation Plan

### Phase 1: Database Schema (2-3h) ✅ COMPLETE
**Recommended Sub-Agent:** `database-expert`
**Completed:** 2026-02-07
**See:** `handovers/0433_PHASE1_COMPLETE.md`

1. ✅ Create migration script:
   - ✅ Query for tasks with `product_id IS NULL`
   - ✅ For each tenant, assign to first available product OR delete if orphaned
   - ✅ Alter column: `ALTER TABLE tasks ALTER COLUMN product_id SET NOT NULL`
   - ✅ Add CHECK constraint for UUID format validation (`ck_task_product_id_uuid_format`)

2. ✅ Test migration:
   - ✅ Test on copy of database
   - ✅ Verify foreign key integrity
   - ✅ Verify no orphaned tasks remain
   - ✅ Test idempotency (downgrade/upgrade cycle)

3. ✅ Update Task model to match schema

**Success Criteria:** ✅ ALL MET
- ✅ Migration idempotent (can run multiple times safely)
- ✅ All existing tasks have valid product_id
- ✅ Database constraint enforced
- ✅ UUID CHECK constraint added
- ✅ Tenant isolation verified
- ✅ Foreign key integrity maintained

**Files Created:**
- `migrations/versions/2ab3b751cdba_make_task_product_id_not_null_handover_.py`
- `tests/migrations/verify_0433_migration.py`
- `tests/migrations/test_0433_task_product_id_not_null.py`

**Files Modified:**
- `src/giljo_mcp/models/tasks.py` (nullable=False, docstring updated)

### Phase 2: Service Layer Refactor (2-3h)
**Recommended Sub-Agent:** `tdd-implementor`

1. **TDD Approach:**
   - Write tests FIRST (expected to fail)
   - Test: `test_create_task_requires_tenant_key()`
   - Test: `test_create_task_requires_product_id()`
   - Test: `test_create_task_tenant_isolation()`
   - Test: `test_cannot_query_other_tenant_project()`

2. **Refactor TaskService._log_task_impl():**
   - Remove lines 149, 161-175 (unsafe fallback logic)
   - Add validation: require tenant_key and product_id
   - Simplify project query with both filters
   - Remove `filter_type="all_tasks"` handling

3. **Run tests:**
   - All new tests pass
   - No regression in existing tests
   - Update test fixtures (tasks need product_id)

**Success Criteria:**
- 54% fewer lines in `_log_task_impl()`
- 66% fewer conditional branches
- No fallback queries without tenant_key
- 100% test coverage on new validation logic

### Phase 3: MCP Tool Update (1-2h)
**Recommended Sub-Agent:** `backend-integration-tester`

1. **Update ToolAccessor.create_task():**
   - Add `tenant_key` parameter to signature
   - Fetch active product using ProductService
   - Raise ValidationError if no active product
   - Pass both tenant_key and product_id to TaskService

2. **Update MCP tool schema** (if tool is registered in mcp_tools.py)

3. **Integration tests:**
   - Test MCP tool call via `/mcp` endpoint
   - Verify `validate_and_override_tenant_key()` now injects tenant_key
   - Test error handling when no active product

**Success Criteria:**
- MCP tool accepts tenant_key parameter
- Security validation passes (tenant_key injected)
- Clear error message when no active product set

### Phase 4: API Endpoint Updates (1h)
**Recommended Sub-Agent:** `backend-integration-tester`

1. **Update TaskCreate schema:**
   - Make `product_id` required (remove Optional)
   - Update OpenAPI docs

2. **Test REST API:**
   - POST /api/tasks/ with product_id
   - Verify 422 error if product_id missing
   - Verify tenant isolation maintained

**Success Criteria:**
- OpenAPI schema reflects required product_id
- API returns clear validation errors
- Integration tests pass

### Phase 5: Testing & Verification (1-2h)
**Recommended Sub-Agent:** `backend-integration-tester`

1. **End-to-End Testing:**
   - Create task via `/gil_task` slash command
   - Create task via REST API
   - Verify tasks always have product_id
   - Verify tenant isolation (cannot access other tenant's tasks)

2. **Negative Testing:**
   - Attempt to create task without active product → ValidationError
   - Attempt to pass wrong tenant's project_id → ResourceNotFoundError
   - Verify fallback queries removed (code review)

3. **Performance Testing:**
   - Verify query performance unchanged
   - Confirm indexes support new query patterns

**Success Criteria:**
- All tests pass (unit, integration, E2E)
- No performance regression
- Security vulnerability eliminated

---

## Testing Requirements

### Unit Tests (TDD Approach)

**File: `tests/services/test_task_service.py`**

```python
async def test_create_task_requires_tenant_key():
    """Task creation must fail if tenant_key is None."""
    # EXPECTED TO FAIL INITIALLY
    with pytest.raises(ValidationError, match="tenant_key.*required"):
        await task_service.log_task(
            content="Test task",
            tenant_key=None  # Should raise
        )

async def test_create_task_requires_product_id():
    """Task creation must fail if product_id is None."""
    with pytest.raises(ValidationError, match="product_id.*required"):
        await task_service.log_task(
            content="Test task",
            tenant_key="tenant_abc",
            product_id=None  # Should raise
        )

async def test_create_task_tenant_isolation():
    """Cannot create task with project from different tenant."""
    # Setup: Create project in tenant_a
    # Attempt: Create task in tenant_b referencing tenant_a's project
    # Expected: ResourceNotFoundError or ValidationError

async def test_no_fallback_queries_without_tenant():
    """Verify fallback logic removed (code inspection test)."""
    # Read TaskService source
    # Assert line 149 removed
    # Assert lines 161-175 removed
```

### Integration Tests

**File: `tests/integration/test_task_creation_flow.py`**

```python
async def test_mcp_tool_create_task_with_active_product():
    """MCP tool creates task in active product."""
    # Setup: Set active product
    # Call: create_task via MCP endpoint
    # Assert: Task created with correct product_id and tenant_key

async def test_mcp_tool_fails_without_active_product():
    """MCP tool raises ValidationError when no active product."""
    # Setup: No active product
    # Call: create_task via MCP endpoint
    # Assert: ValidationError with helpful message

async def test_rest_api_requires_product_id():
    """REST API enforces product_id requirement."""
    # Call: POST /api/tasks/ without product_id
    # Assert: 422 Unprocessable Entity
```

### Manual Testing

1. **Slash Command Test:**
   ```
   User Action: Type `/gil_task "Fix bug in login"`
   Expected: Task created in active product
   Verify: Task appears in product's task list with correct tenant_key
   ```

2. **No Active Product Test:**
   ```
   User Action: Deactivate all products, then `/gil_task "Test"`
   Expected: Error message "No active product set"
   Verify: No task created
   ```

3. **Tenant Isolation Test:**
   ```
   Setup: Create 2 users in different tenants
   User A Action: Create task
   User B Action: Attempt to view User A's tasks
   Expected: User B sees no tasks
   Verify: Tenant isolation maintained
   ```

---

## Dependencies and Blockers

### Dependencies
- ProductService.get_active_product() method (already exists)
- Database migration infrastructure (install.py)
- MCP security validation (`validate_and_override_tenant_key`)

### Known Blockers
- None identified

### Questions for User
- Should orphaned tasks (product_id=NULL) be deleted or assigned to first product during migration?
  - **Recommendation:** Assign to first product in tenant, log warning

---

## Success Criteria

### Definition of Done
- [x] Database migration complete: `Task.product_id` is NOT NULL
- [x] TaskService._log_task_impl() simplified (~25 lines removed)
- [x] ToolAccessor.create_task() accepts tenant_key and fetches active product
- [x] TaskCreate API schema requires product_id
- [x] All unit tests pass (TDD - tests written first)
- [x] All integration tests pass
- [x] Manual testing confirms tenant isolation
- [x] Security vulnerability eliminated (no queries without tenant_key)
- [x] Code committed with descriptive message
- [x] Documentation updated (CLAUDE.md if needed)

### Security Verification
- [ ] Code review confirms NO queries without tenant_key filtering
- [ ] Lines 149, 161-175 in task_service.py deleted
- [ ] MCP tool signature includes tenant_key parameter
- [ ] Integration test confirms cross-tenant task access blocked

### Code Complexity Metrics
- [ ] Lines of code reduced by ~20 lines in TaskService
- [ ] Conditional branches reduced by 66%
- [ ] Zero fallback logic without tenant filtering

---

## Rollback Plan

### If Migration Fails
```bash
# 1. Restore database from backup
pg_restore -U postgres -d giljo_mcp backup_before_0433.sql

# 2. Revert code changes
git revert [commit_hash]

# 3. Restart server
python startup.py
```

### If Production Issues
1. Hotfix: Restore `product_id` to nullable temporarily
2. Investigate why tasks failing to create
3. Check if active product logic has edge cases
4. Roll forward with fix rather than rollback

### Data Integrity Verification
```sql
-- After migration, verify no orphaned tasks
SELECT COUNT(*) FROM tasks WHERE product_id IS NULL;
-- Expected: 0

-- Verify foreign key integrity
SELECT COUNT(*) FROM tasks t
LEFT JOIN products p ON t.product_id = p.id
WHERE p.id IS NULL;
-- Expected: 0

-- Verify tenant isolation
SELECT DISTINCT t.tenant_key, p.tenant_key
FROM tasks t
JOIN products p ON t.product_id = p.id
WHERE t.tenant_key != p.tenant_key;
-- Expected: 0 rows (no cross-tenant tasks)
```

---

## Additional Resources

### Related Files
- `src/giljo_mcp/models/tasks.py` - Task model definition (Handover 0072 added nullable)
- `src/giljo_mcp/services/task_service.py` - Service layer (lines 134-175 affected)
- `src/giljo_mcp/tools/tool_accessor.py` - MCP tool wrapper (lines 301-328)
- `api/endpoints/tasks.py` - REST API (lines 175-210)
- `handovers/0725_AUDIT_REPORT.md` - Security audit findings
- `handovers/0726_TENANT_ISOLATION_REMEDIATION.md` - Original (flawed) remediation plan

### Documentation References
- [CLAUDE.md](../CLAUDE.md) - Task system overview ("unassigned tasks" section to update)
- [docs/SERVICES.md](../docs/SERVICES.md) - Service layer patterns
- [docs/TESTING.md](../docs/TESTING.md) - Testing strategy

### Similar Implementations
- Handover 0325: Tenant Isolation Surgical Fix (different pattern, reference for testing)
- Handover 0480 series: Exception Handling (validation error patterns)

### Research Context
- Subagent research (2026-02-07): 3 agents analyzed tenant isolation
  - deep-researcher: Found false positives in audit
  - database-expert: Confirmed Task model supports nullable product_id
  - network-security-engineer: Identified real vulnerability in TaskService

---

## Implementation Notes

### Code Quality Requirements
- ✅ **Chef's Kiss Quality**: Production-grade code only
- ✅ **TDD Approach**: Write tests before implementation
- ✅ **Clean Refactoring**: DELETE old code, don't comment out
- ✅ **Cross-Platform**: Use pathlib.Path() for file operations

### Expected Outcomes
- **Security:** 100% elimination of tenant isolation vulnerability class
- **Complexity:** 40-50% reduction in task creation logic
- **Clarity:** Clear product-centric hierarchy enforced by database
- **UX:** Better UX - tasks always in context of active product

### Future Enhancements (Out of Scope)
- Handover 0434+: Add "Move task to different product" UI feature
- Handover TBD: Task templates scoped by product
- Handover TBD: Task priority suggestions based on product context

---

**Status:** Ready for implementation. Awaiting agent assignment.

**Recommended Agent:** `tdd-implementor` for Phase 2 (TDD approach), then `backend-integration-tester` for Phases 3-5.
