# Handover 0300: Tenant Isolation Surgical Fix

**Status**: Ready for Implementation
**Priority**: HIGH (Security Fix)
**Type**: Security / Database Query Audit
**Estimated Effort**: 8-10 hours
**Created**: 2025-12-05

---

## Problem Statement

A comprehensive security audit of database queries across the GiljoAI MCP codebase revealed that **26 out of 48 queries (54%) are missing tenant_key filtering**. This creates a critical security vulnerability where:

- Users in one tenant could potentially access data from another tenant
- Cross-tenant data leakage is possible through unfiltered queries
- Multi-tenant isolation guarantees are violated at the database layer

**Impact**: This is a **HIGH priority security issue** that must be resolved before any organization-level governance features can be safely implemented.

---

## Context for New Agent

### Multi-Tenant Architecture
GiljoAI MCP uses a **per-user tenancy model** where each user is assigned a unique `tenant_key` at registration. All database queries MUST filter by `tenant_key` to prevent cross-tenant data access.

### Current State (Audit Results)
- **Total queries analyzed**: 48
- **Compliant queries**: 22 (46%)
- **Non-compliant queries**: 26 (54%)

### Compliant vs Non-Compliant Pattern

**✅ CORRECT (Compliant)**:
```python
# Always filter by tenant_key
project = await session.execute(
    select(Project)
    .where(Project.id == project_id)
    .where(Project.tenant_key == tenant_key)  # ✅ Tenant filter present
)
```

**❌ INCORRECT (Non-Compliant)**:
```python
# Missing tenant_key filter - SECURITY RISK
project = await session.execute(
    select(Project)
    .where(Project.id == project_id)  # ❌ No tenant filter
)
```

### Why This Matters
Without tenant filtering, a malicious user could:
1. Guess/enumerate UUIDs of other users' projects
2. Access or modify data belonging to other tenants
3. Bypass access controls entirely at the database level

---

## Scope: Files & Query Gaps

### 1. tools/orchestrator.py (13 gaps - HIGHEST EXPOSURE)

**Query Gaps**:
1. **Project lookup by ID** - Missing tenant_key filter
2. **Agent job creation** - No tenant_key validation on project
3. **Agent job updates** - No tenant_key filter on job queries
4. **Context fetching** - Product/project queries without tenant_key
5. **Orchestrator instructions** - Agent job lookup without tenant_key
6. **Workflow status** - Agent job aggregation without tenant_key
7. **Successor creation** - Job lookup without tenant_key
8. **Succession status** - Job context queries without tenant_key
9. **Available agents** - Agent template queries without tenant_key
10. **Agent spawning** - Project validation without tenant_key
11. **Agent mission fetch** - Job lookup without tenant_key
12. **Message operations** - Project/job lookups without tenant_key
13. **Job completion** - Job update without tenant_key filter

**Fix Strategy**:
- Add `.where(Model.tenant_key == tenant_key)` to ALL queries
- Validate tenant_key matches between related entities (e.g., job.tenant_key == project.tenant_key)
- Raise HTTP 403 Forbidden if tenant mismatch detected

---

### 2. tools/agent.py (6 gaps)

**Query Gaps**:
1. **get_pending_jobs()** - `select(AgentJob)` missing tenant_key filter
2. **acknowledge_job()** - Job lookup without tenant_key
3. **report_progress()** - Job update without tenant_key filter
4. **get_next_instruction()** - Message queries without tenant_key
5. **complete_job()** - Job update without tenant_key filter
6. **report_error()** - Job update without tenant_key filter

**Example Fix (acknowledge_job)**:
```python
# BEFORE (Non-Compliant)
job = await session.execute(
    select(AgentJob).where(AgentJob.id == job_id)
)

# AFTER (Compliant)
job = await session.execute(
    select(AgentJob)
    .where(AgentJob.id == job_id)
    .where(AgentJob.tenant_key == tenant_key)  # ✅ Added
)
if not job:
    raise HTTPException(status_code=403, detail="Job not found or access denied")
```

---

### 3. tools/project.py (4 gaps)

**Query Gaps**:
1. **create_project()** - Product validation without tenant_key
2. **switch_project()** - Project lookup without tenant_key
3. **update_project_mission()** - Project update without tenant_key filter
4. **List projects (implicit)** - If exists, likely missing tenant_key filter

**Example Fix (switch_project)**:
```python
# BEFORE (Non-Compliant)
project = await session.execute(
    select(Project).where(Project.id == project_id)
)

# AFTER (Compliant)
project = await session.execute(
    select(Project)
    .where(Project.id == project_id)
    .where(Project.tenant_key == tenant_key)  # ✅ Added
)
if not project:
    raise HTTPException(status_code=403, detail="Project not found or access denied")
```

---

### 4. tools/product.py (3 gaps)

**Query Gaps**:
1. **Product lookup by ID** - Missing tenant_key filter
2. **Product update** - No tenant_key filter on update query
3. **Product listing (if exists)** - Likely missing tenant_key filter

**Example Fix (product lookup)**:
```python
# BEFORE (Non-Compliant)
product = await session.execute(
    select(Product).where(Product.id == product_id)
)

# AFTER (Compliant)
product = await session.execute(
    select(Product)
    .where(Product.id == product_id)
    .where(Product.tenant_key == tenant_key)  # ✅ Added
)
if not product:
    raise HTTPException(status_code=403, detail="Product not found or access denied")
```

---

### 5. api/services/message_service.py (1 gap - DOCUMENTED)

**Query Gap**:
- **Line 111**: `select(Project).where(Project.id == project_id)` - NO tenant_key filter

**Fix**:
```python
# Line 111 - BEFORE
project = await session.execute(
    select(Project).where(Project.id == project_id)
)

# Line 111 - AFTER
project = await session.execute(
    select(Project)
    .where(Project.id == project_id)
    .where(Project.tenant_key == tenant_key)  # ✅ Added
)
```

---

## Standard Fix Pattern

### Pattern 1: Single Record Lookup
```python
# Query with tenant_key filter
result = await session.execute(
    select(Model)
    .where(Model.id == record_id)
    .where(Model.tenant_key == tenant_key)  # ✅ Required
)
record = result.scalar_one_or_none()

# Raise 403 if not found (could be wrong tenant OR doesn't exist)
if not record:
    raise HTTPException(
        status_code=403,
        detail=f"{Model.__name__} not found or access denied"
    )
```

### Pattern 2: Multiple Record Query
```python
# List query with tenant_key filter
result = await session.execute(
    select(Model)
    .where(Model.tenant_key == tenant_key)  # ✅ Required
    .where(Model.status == "active")  # Additional filters OK
)
records = result.scalars().all()
```

### Pattern 3: Related Entity Validation
```python
# When updating related entities, verify tenant_key matches
job = await session.execute(
    select(AgentJob)
    .where(AgentJob.id == job_id)
    .where(AgentJob.tenant_key == tenant_key)  # ✅ Required
)
job = job.scalar_one_or_none()
if not job:
    raise HTTPException(status_code=403, detail="Job not found or access denied")

# Verify related project also belongs to same tenant
project = await session.execute(
    select(Project)
    .where(Project.id == job.project_id)
    .where(Project.tenant_key == tenant_key)  # ✅ Double-check
)
project = project.scalar_one_or_none()
if not project:
    raise HTTPException(status_code=403, detail="Project tenant mismatch")
```

### Pattern 4: Update/Delete Operations
```python
# Update with tenant_key filter
result = await session.execute(
    update(Model)
    .where(Model.id == record_id)
    .where(Model.tenant_key == tenant_key)  # ✅ Required
    .values(status="completed")
)

# Verify row was actually updated (if rowcount == 0, wrong tenant or doesn't exist)
if result.rowcount == 0:
    raise HTTPException(
        status_code=403,
        detail=f"{Model.__name__} not found or access denied"
    )
```

---

## Implementation Plan

### Phase 1: MCP Tools Layer (Priority 1)
**Files**: `tools/orchestrator.py`, `tools/agent.py`, `tools/project.py`, `tools/product.py`

**Steps**:
1. Review each MCP tool function signature - ensure `tenant_key` parameter exists
2. Add `.where(Model.tenant_key == tenant_key)` to ALL database queries
3. Replace generic "not found" errors with HTTP 403 responses
4. Add tenant validation for related entities (e.g., job.tenant_key == project.tenant_key)

**Estimated Time**: 4-5 hours

---

### Phase 2: Service Layer Review (Priority 2)
**Files**: `api/services/message_service.py`, review other services

**Steps**:
1. Re-audit service layer for any missed gaps
2. Fix message_service.py line 111 (documented gap)
3. Verify all services follow tenant isolation pattern

**Estimated Time**: 1-2 hours

---

### Phase 3: Testing & Validation (Priority 3)
**Files**: `tests/tools/`, `tests/services/`, `tests/integration/`

**Steps**:
1. Add tenant isolation tests to EVERY fixed tool/service
2. Create cross-tenant access attempt tests (should raise 403)
3. Run full test suite, verify >80% coverage maintained
4. Manual testing: Create 2 users, attempt cross-tenant access

**Estimated Time**: 3-4 hours

---

## Test Requirements

### Unit Test Pattern (Add to Each Tool/Service)
```python
@pytest.mark.asyncio
async def test_tenant_isolation_blocks_cross_tenant_access():
    """Verify tenant_key filtering prevents cross-tenant data access."""
    async with get_test_db_session() as session:
        # Create two tenants
        tenant_a = "tenant-aaaa"
        tenant_b = "tenant-bbbb"

        # Create project for tenant A
        project_a = Project(
            id=uuid4(),
            name="Tenant A Project",
            tenant_key=tenant_a
        )
        session.add(project_a)
        await session.commit()

        # Attempt to access tenant A's project using tenant B's key
        with pytest.raises(HTTPException) as exc_info:
            await get_project(
                project_id=project_a.id,
                tenant_key=tenant_b,  # Wrong tenant
                session=session
            )

        # Verify 403 Forbidden response
        assert exc_info.value.status_code == 403
        assert "access denied" in exc_info.value.detail.lower()
```

### Integration Test Pattern
```python
@pytest.mark.asyncio
async def test_end_to_end_tenant_isolation():
    """Verify complete workflow respects tenant boundaries."""
    # Create two users with different tenants
    user_a = await create_test_user(username="user_a")
    user_b = await create_test_user(username="user_b")

    # User A creates project
    project_a = await create_project(
        name="Project A",
        tenant_key=user_a.tenant_key
    )

    # User B attempts to access User A's project
    with pytest.raises(HTTPException) as exc_info:
        await get_project(
            project_id=project_a.id,
            tenant_key=user_b.tenant_key  # Wrong tenant
        )

    assert exc_info.value.status_code == 403
```

---

## Acceptance Criteria

### ✅ Definition of Done
1. **All 26 non-compliant queries fixed** - Every query includes `.where(Model.tenant_key == tenant_key)`
2. **Cross-tenant access blocked** - Attempting to access another tenant's data raises HTTP 403
3. **Tests verify isolation** - Unit tests for each tool/service, integration tests for workflows
4. **No regressions** - Existing tests pass, >80% code coverage maintained
5. **Documentation updated** - CLAUDE.md, SERVICES.md reflect tenant isolation requirements
6. **Code review passed** - Orchestrator Coordinator reviews all changes

### ✅ Success Metrics
- **Zero** database queries missing tenant_key filter (re-audit after fix)
- **100%** of tools/services pass tenant isolation tests
- **No** cross-tenant data leakage possible through any code path

---

## Risk Mitigation

### Risk 1: Breaking Existing Functionality
**Mitigation**:
- Run full test suite after each file fix
- Deploy to staging environment for manual testing
- Keep changes atomic (one file at a time)

### Risk 2: False Positives (Legitimate Access Denied)
**Mitigation**:
- Verify tenant_key is correctly propagated through entire call chain
- Add detailed logging for 403 responses to debug issues
- Test with real user workflows, not just unit tests

### Risk 3: Performance Impact
**Mitigation**:
- Tenant_key columns already indexed (verify with `\d+ table_name` in psql)
- SQLAlchemy query plans should be unchanged (adding `.where()` is standard)
- Monitor query performance after deployment

---

## Follow-Up Work

### After This Handover
1. **Handover 0301**: Organization-Level Governance (blocked until tenant isolation fixed)
2. **Handover 0302**: Audit Logging for Tenant Isolation (capture all 403 events)
3. **Handover 0303**: Automated Tenant Isolation Testing (CI/CD integration)

---

## Notes for Implementation

### Quick Start Checklist
1. Read this handover completely
2. Pull latest `master` branch
3. Create feature branch: `git checkout -b fix/tenant-isolation-0300`
4. Start with `tools/orchestrator.py` (highest exposure)
5. Add tenant isolation test BEFORE fixing each function
6. Run tests after each fix: `pytest tests/tools/test_orchestrator.py -v`
7. Move to next file only when current file passes all tests
8. Final step: Full integration test suite

### Testing Commands
```bash
# Unit tests for specific file
pytest tests/tools/test_orchestrator.py -v

# All tenant isolation tests (after adding markers)
pytest -m tenant_isolation -v

# Full test suite with coverage
pytest tests/ --cov=src/giljo_mcp --cov-report=html

# Integration tests only
pytest tests/integration/ -v
```

### Database Verification
```bash
# Verify tenant_key indexes exist
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "\d+ mcp_projects"
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "\d+ mcp_agent_jobs"

# Check for any NULL tenant_keys (should be zero)
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "SELECT COUNT(*) FROM mcp_projects WHERE tenant_key IS NULL;"
```

---

## References

- **CLAUDE.md**: Multi-tenant architecture section
- **docs/SERVICES.md**: Service layer patterns (tenant_key parameter standard)
- **docs/TESTING.md**: Testing strategy and coverage requirements
- **Handover 0246**: Orchestrator workflow (context for orchestrator.py changes)
- **Handover 0088**: Thin client architecture (context for MCP tools)

---

**Created By**: Documentation Manager Agent
**Review Required**: Orchestrator Coordinator, Database Expert
**Security Classification**: HIGH - Contains security vulnerability details
**Next Action**: Assign to TDD Implementor for test-driven fix implementation
