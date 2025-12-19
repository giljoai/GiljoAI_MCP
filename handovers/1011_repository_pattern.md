# Handover 1011: Repository Pattern Standardization

**Date**: 2025-12-18
**Status**: Pending
**Parent**: 1000 (Greptile Remediation)
**Risk**: HIGH
**Tier**: 3 (Staging + Full Test Suite)
**Estimated Effort**: 6 hours (spread across multiple sessions)

---

## Mission

Reduce direct SQLAlchemy queries in API endpoints by standardizing on the repository pattern. Ensure consistent database access patterns, maintain tenant isolation, and improve code maintainability across the entire application.

---

## Context

**Problem**: Currently, many API endpoints contain direct SQLAlchemy queries (e.g., `session.execute(select(Model).where(...))`), leading to:
- Inconsistent query patterns across endpoints
- Difficult-to-maintain database access logic
- Risk of tenant isolation bypass
- Harder to test and mock database operations

**Solution**: Migrate to repository pattern where:
- Each model has a dedicated repository class
- Repositories encapsulate all database queries
- Tenant filtering is centralized and guaranteed
- Endpoints become thinner and more testable

---

## Files to Modify

### Repositories (Expand)
- `src/giljo_mcp/repositories/base.py` (may need enhancements)
- `src/giljo_mcp/repositories/*.py` (create missing repositories)

### Endpoints (40+ files)
- `api/endpoints/admin.py`
- `api/endpoints/agent_job.py`
- `api/endpoints/agent_message.py`
- `api/endpoints/agent_template.py`
- `api/endpoints/auth.py`
- `api/endpoints/context.py`
- `api/endpoints/dashboard.py`
- `api/endpoints/orchestration.py`
- `api/endpoints/product.py`
- `api/endpoints/project.py`
- `api/endpoints/settings.py`
- `api/endpoints/task.py`
- `api/endpoints/vision.py`
- _(and ~30 more endpoint files)_

---

## Why This is HIGH Risk

1. **Touches 40+ endpoint files** - Large surface area for bugs
2. **Changes database access patterns** - Could introduce race conditions or performance issues
3. **Tenant isolation critical** - Any mistake could leak data across tenants
4. **Must be incremental** - Cannot migrate all files at once without massive testing effort

**Critical Safety Requirements**:
- Preserve all existing tenant_key filtering
- Maintain existing query logic (no optimization during migration)
- Test each file independently before moving to next
- Stop immediately if any test fails

---

## Pre-Implementation Research (MANDATORY)

Before writing any code, complete this research phase:

### 1. Inventory Existing Repositories
```python
# Use Serena tools to explore repository architecture
get_symbols_overview("src/giljo_mcp/repositories/base.py")
```

List all existing repository classes:
```bash
# Find all repository files
glob "src/giljo_mcp/repositories/*.py"
```

### 2. Identify Direct Queries in Endpoints
```python
# Search for direct SQLAlchemy select() calls
search_for_pattern(
    substring_pattern="select\\(",
    relative_path="api/endpoints",
    context_lines_before=2,
    context_lines_after=2
)

# Search for direct session.execute() calls
search_for_pattern(
    substring_pattern="session\\.execute",
    relative_path="api/endpoints",
    context_lines_before=2,
    context_lines_after=2
)
```

### 3. Model-Repository Mapping
Create a mapping table:

| Model | Has Repository? | Endpoints Using It | Priority |
|-------|----------------|-------------------|----------|
| Project | Yes/No | project.py, dashboard.py | High |
| AgentJob | Yes/No | agent_job.py, orchestration.py | High |
| Product | Yes/No | product.py, context.py | Medium |
| ... | ... | ... | ... |

### 4. Query Pattern Analysis
Identify high-frequency query patterns:
- Simple lookups by ID + tenant_key
- List queries with filtering
- Join queries across tables
- Complex aggregations

---

## DO NOT

- ❌ Change all 40+ files at once
- ❌ Modify query logic while migrating (no optimizations)
- ❌ Remove tenant_key filtering
- ❌ Skip testing between file changes
- ❌ Combine repository creation with endpoint migration
- ❌ Change database schema during this handover

---

## Phased Approach (REQUIRED)

### Phase 1: Audit & Planning (No Code Changes)
**Goal**: Understand current state and create migration roadmap

**Tasks**:
1. Count direct queries per endpoint (from Pre-Implementation Research)
2. Identify top 5 most-queried models
3. Document existing repository coverage
4. Create prioritized migration list (high-usage endpoints first)
5. Estimate effort per endpoint (simple = 30min, complex = 2hr)

**Deliverable**: Migration plan document with priority order

---

### Phase 2: Repository Creation (One Model at a Time)
**Goal**: Create repositories for models that don't have them

**Process for Each Model**:
1. Create repository class in `src/giljo_mcp/repositories/[model]_repository.py`
2. Implement common methods:
   - `get_by_id(id: str, tenant_key: str) -> Optional[Model]`
   - `list(tenant_key: str, filters: dict = None) -> List[Model]`
   - `create(data: dict, tenant_key: str) -> Model`
   - `update(id: str, data: dict, tenant_key: str) -> Model`
   - `delete(id: str, tenant_key: str) -> bool`
3. **CRITICAL**: All methods MUST filter by `tenant_key`
4. Write unit tests for repository
5. Migrate **ONE** endpoint to use new repository
6. Verify endpoint tests pass
7. STOP if tests fail - debug before continuing

**Example: Creating ProjectRepository**
```python
# src/giljo_mcp/repositories/project_repository.py
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.giljo_mcp.models import Project
from src.giljo_mcp.repositories.base import BaseRepository

class ProjectRepository(BaseRepository[Project]):
    """Repository for Project model with tenant isolation."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Project)

    async def get_by_id(
        self,
        project_id: str,
        tenant_key: str
    ) -> Optional[Project]:
        """Get project by ID with tenant filtering."""
        stmt = select(Project).where(
            Project.id == project_id,
            Project.tenant_key == tenant_key
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_active(
        self,
        tenant_key: str
    ) -> List[Project]:
        """List all active projects for tenant."""
        stmt = select(Project).where(
            Project.tenant_key == tenant_key,
            Project.deleted_at.is_(None)
        ).order_by(Project.created_at.desc())
        result = await self.session.execute(stmt)
        return result.scalars().all()
```

**Verification Per Repository**:
1. Write unit tests: `tests/repositories/test_[model]_repository.py`
2. Test tenant isolation (queries with wrong tenant_key return nothing)
3. Test all CRUD operations
4. Run: `pytest tests/repositories/test_[model]_repository.py -v`

---

### Phase 3: Endpoint Migration (Incremental)
**Goal**: Migrate endpoints one file at a time to use repositories

**Process for Each Endpoint File**:
1. Pick ONE endpoint file (start with simplest)
2. Identify all direct queries in that file
3. Replace with repository method calls
4. Keep original query code as comments (for rollback)
5. Run endpoint-specific tests: `pytest tests/endpoints/test_[endpoint].py -v`
6. Manual smoke test critical operations
7. Verify tenant isolation still works
8. STOP if any test fails - rollback and debug
9. Commit the single-file change
10. Move to next file

**Example Migration**:

**Before** (direct query in `api/endpoints/project.py`):
```python
@router.get("/projects/{project_id}")
async def get_project(
    project_id: str,
    session: AsyncSession = Depends(get_db),
    tenant_key: str = Depends(get_tenant_key)
):
    # Direct SQLAlchemy query
    stmt = select(Project).where(
        Project.id == project_id,
        Project.tenant_key == tenant_key
    )
    result = await session.execute(stmt)
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project
```

**After** (using repository):
```python
@router.get("/projects/{project_id}")
async def get_project(
    project_id: str,
    session: AsyncSession = Depends(get_db),
    tenant_key: str = Depends(get_tenant_key)
):
    # Using repository pattern
    repo = ProjectRepository(session)
    project = await repo.get_by_id(project_id, tenant_key)

    # Original query (for rollback reference):
    # stmt = select(Project).where(
    #     Project.id == project_id,
    #     Project.tenant_key == tenant_key
    # )
    # result = await session.execute(stmt)
    # project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project
```

**Verification Per Endpoint File**:
1. Run endpoint tests: `pytest tests/endpoints/test_[endpoint].py -v`
2. Manual test CRUD operations via API
3. Verify tenant isolation: attempt to access another tenant's resources (should fail)
4. Check no SQL injection introduced (use parameterized queries)
5. Performance check: no significant slowdown

---

## Migration Priority List

Prioritize endpoints by:
1. **High-usage endpoints** (dashboard, project, agent_job)
2. **Simple query patterns** (single-table lookups)
3. **Critical security** (auth, admin endpoints)

**Suggested Order**:
1. `project.py` (high usage, simple queries)
2. `agent_job.py` (high usage, moderate complexity)
3. `product.py` (medium usage, simple)
4. `dashboard.py` (high usage, read-only)
5. `orchestration.py` (critical, complex - save for later)
6. `auth.py` (security-critical - handle carefully)
7. _(remaining 30+ files in order of usage/simplicity)_

---

## Testing Strategy

### Repository Tests
```bash
# Create test file for each repository
# tests/repositories/test_project_repository.py

pytest tests/repositories/ -v --cov=src/giljo_mcp/repositories
```

### Endpoint Tests (Per File)
```bash
# Test individual endpoint after migration
pytest tests/endpoints/test_project.py -v

# Test tenant isolation specifically
pytest tests/integration/test_tenant_isolation.py -v
```

### Full Test Suite (Before Final Commit)
```bash
# Run all tests to ensure no regressions
pytest tests/ --cov=src/giljo_mcp --cov=api -v

# Check coverage remains >80%
pytest tests/ --cov=src/giljo_mcp --cov=api --cov-report=html
```

---

## Cascade Risk

**Risk Level**: HIGH

**Why**:
- Touches database layer across entire application
- Changes how tenant isolation is enforced
- Could introduce subtle bugs in query logic
- Performance implications if repositories are inefficient

**Mitigation**:
- Incremental migration (one file at a time)
- Comprehensive testing after each change
- Keep original query code as comments (easy rollback)
- Peer review of repository implementations
- Load testing critical endpoints

---

## Rollback Plan

**Per-File Rollback**:
1. Restore original query code from comments
2. Remove repository import and instantiation
3. Re-run tests to confirm rollback
4. Commit rollback with clear message

**Full Rollback**:
1. Revert git commits for this handover
2. Repositories remain in codebase (no harm)
3. Endpoints continue using direct queries
4. Re-assess repository pattern after addressing root cause

---

## Success Criteria

- [ ] All models have dedicated repository classes
- [ ] No direct SQLAlchemy queries in endpoint files
- [ ] All tenant filtering preserved and tested
- [ ] Full test suite passes (>80% coverage)
- [ ] No performance regression (response times within 10% of baseline)
- [ ] Code is more maintainable (easier to add new queries)
- [ ] Tenant isolation verified through integration tests

---

## Implementation Checklist

### Research Phase
- [ ] Inventory existing repositories
- [ ] Count direct queries per endpoint
- [ ] Map models to endpoints
- [ ] Identify high-frequency query patterns
- [ ] Create prioritized migration list

### Repository Creation
- [ ] Create repository for Model 1
- [ ] Write unit tests for repository
- [ ] Migrate ONE endpoint to use repository
- [ ] Verify tests pass
- [ ] Repeat for remaining models

### Endpoint Migration
- [ ] Migrate endpoint file 1
- [ ] Test endpoint file 1
- [ ] Commit endpoint file 1
- [ ] Repeat for all 40+ endpoint files

### Final Validation
- [ ] Run full test suite
- [ ] Performance testing
- [ ] Tenant isolation verification
- [ ] Code review
- [ ] Update documentation

---

## Notes for Implementer

**Key Principles**:
1. **Incremental is key** - Don't try to do everything at once
2. **Test constantly** - After every single file migration
3. **Preserve logic** - Don't optimize queries during migration
4. **Tenant safety** - Double-check tenant_key filtering in every repository method
5. **Rollback ready** - Keep original code commented for easy reversion

**Common Pitfalls**:
- Forgetting tenant_key in repository methods
- Changing query logic while migrating (scope creep)
- Not testing tenant isolation
- Migrating too many files before testing

**Best Practices**:
- Create repository test file before implementation
- Use type hints for better IDE support
- Document complex query patterns in repository docstrings
- Consider caching for frequently-accessed data (future optimization)

---

## Related Documentation

- [docs/SERVICES.md](../docs/SERVICES.md) - Service layer patterns
- [docs/TESTING.md](../docs/TESTING.md) - Testing strategy
- [docs/SERVER_ARCHITECTURE_TECH_STACK.md](../docs/SERVER_ARCHITECTURE_TECH_STACK.md) - System architecture

---

## Estimated Timeline

**Total Effort**: 6 hours (spread across multiple sessions)

- Research Phase: 1 hour
- Repository Creation: 2 hours (5-10 repositories @ 15-20 min each)
- Endpoint Migration: 2.5 hours (40+ files @ 3-5 min each for simple, 15-30 min for complex)
- Testing & Validation: 30 minutes
- Documentation: Included in above

**Recommended Approach**: Work in 1-2 hour sessions, migrating 5-10 endpoint files per session.

---

**Last Updated**: 2025-12-18
**Owner**: TBD
**Reviewer**: System Architect
