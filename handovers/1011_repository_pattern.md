# Handover 1011: Repository Pattern Standardization

**Date**: 2025-12-24 (Revised)
**Status**: Pending
**Parent**: 1000 (Greptile Remediation)
**Risk**: MEDIUM (reduced from HIGH after research)
**Tier**: 2 (Standard Implementation)
**Estimated Effort**: 4 hours

---

## Mission

Migrate remaining direct SQLAlchemy queries in API endpoints to repository pattern. Achieve 100% consistency in database access patterns with guaranteed tenant isolation.

---

## Research Summary (Completed 2025-12-24)

### Actual Scope (Much Smaller Than Originally Estimated)

| Metric | Original Estimate | Actual |
|--------|-------------------|--------|
| Files to modify | 40+ | **9** |
| Direct queries | Unknown | **67** |
| Risk level | HIGH | **MEDIUM** |

### Existing Infrastructure (Already in Place)

**Repositories (3):**
- `AgentJobRepository` - `src/giljo_mcp/repositories/agent_job_repository.py`
- `ContextRepository` - `src/giljo_mcp/repositories/context_repository.py`
- `VisionDocumentRepository` - `src/giljo_mcp/repositories/vision_document_repository.py`
- `BaseRepository` - `src/giljo_mcp/repositories/base.py`

**Services (17):** Already handle 95% of database operations via service layer.

---

## Files Requiring Migration (9 files, 67 queries)

| File | Query Count | Priority | Complexity |
|------|-------------|----------|------------|
| `api/endpoints/statistics.py` | 32 | **P1** | HIGH |
| `api/endpoints/templates/crud.py` | 12 | **P2** | MEDIUM |
| `api/endpoints/templates/history.py` | 7 | **P2** | MEDIUM |
| `api/endpoints/configuration.py` | 5 | **P3** | LOW |
| `api/endpoints/agent_jobs/operations.py` | 4 | **P3** | LOW |
| `api/endpoints/setup.py` | 2 | **P4** | LOW |
| `api/endpoints/agent_templates.py` | 2 | **P4** | LOW |
| `api/endpoints/templates/preview.py` | 2 | **P4** | LOW |
| `api/endpoints/mcp_installer.py` | 1 | **P4** | LOW |

---

## Implementation Plan

### Phase 1: Create StatisticsRepository (1.5 hours)

**Target**: `statistics.py` - 32 queries (48% of total)

**Create**: `src/giljo_mcp/repositories/statistics_repository.py`

```python
# src/giljo_mcp/repositories/statistics_repository.py
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from src.giljo_mcp.repositories.base import BaseRepository

class StatisticsRepository:
    """Repository for statistics and reporting queries with tenant isolation."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_project_count(self, tenant_key: str) -> int:
        """Count projects for tenant."""
        # Migrate from direct query in statistics.py
        pass

    async def get_agent_job_stats(self, tenant_key: str) -> Dict[str, Any]:
        """Get agent job statistics for tenant."""
        pass

    async def get_message_stats(self, tenant_key: str) -> Dict[str, Any]:
        """Get message statistics for tenant."""
        pass

    # ... additional methods based on actual queries in statistics.py
```

**Tasks**:
1. Read `api/endpoints/statistics.py` to identify all 32 query patterns
2. Create `StatisticsRepository` with methods for each query type
3. All methods MUST include `tenant_key` parameter
4. Write unit tests: `tests/repositories/test_statistics_repository.py`
5. Migrate `statistics.py` to use repository
6. Verify all tests pass

---

### Phase 2: Extend TemplateService (1 hour)

**Target**: `templates/*.py` - 21 queries (31% of total)

**Existing**: `src/giljo_mcp/services/template_service.py`

**Tasks**:
1. Read `api/endpoints/templates/crud.py` (12 queries)
2. Read `api/endpoints/templates/history.py` (7 queries)
3. Read `api/endpoints/templates/preview.py` (2 queries)
4. Add missing methods to existing `TemplateService`
5. Migrate all three template endpoint files
6. Verify tests pass

---

### Phase 3: Configuration & Setup (45 minutes)

**Target**: `configuration.py` (5) + `setup.py` (2) = 7 queries

**Option A**: Create `ConfigurationRepository`
**Option B**: Extend existing `ConfigService`

**Tasks**:
1. Read both files to understand query patterns
2. Choose Option A or B based on complexity
3. Implement and migrate
4. Verify tests pass

---

### Phase 4: Remaining Files (45 minutes)

**Target**: 7 queries across 3 files

| File | Queries | Approach |
|------|---------|----------|
| `agent_jobs/operations.py` | 4 | Extend `AgentJobRepository` |
| `agent_templates.py` | 2 | Use `TemplateService` |
| `mcp_installer.py` | 1 | Inline or `ConfigService` |

---

## Repository Pattern Requirements

### Every Repository Method MUST:

```python
async def example_method(
    self,
    resource_id: str,
    tenant_key: str,  # REQUIRED - always filter by tenant
    **kwargs
) -> Optional[Model]:
    stmt = select(Model).where(
        Model.id == resource_id,
        Model.tenant_key == tenant_key  # CRITICAL: Tenant isolation
    )
    result = await self.session.execute(stmt)
    return result.scalar_one_or_none()
```

### Tenant Isolation Rules:
- Every SELECT must filter by `tenant_key`
- Every INSERT must set `tenant_key`
- Every UPDATE/DELETE must verify `tenant_key`
- NEVER expose methods without `tenant_key` parameter

---

## Testing Strategy

### Per-Repository Tests

```bash
# After creating each repository
pytest tests/repositories/test_[name]_repository.py -v
```

### Per-Endpoint Migration Tests

```bash
# After migrating each endpoint file
pytest tests/endpoints/test_[name].py -v
```

### Tenant Isolation Verification

```bash
# Run dedicated tenant isolation tests
pytest tests/integration/test_tenant_isolation.py -v
```

### Final Validation

```bash
# Full test suite before closing handover
pytest tests/ -v --tb=short
```

---

## Rollback Plan

**Per-File Rollback**:
1. Keep original query code as comments during migration
2. If tests fail, uncomment original code
3. Remove repository calls
4. Debug and retry

**Example**:
```python
# Using repository (new)
repo = StatisticsRepository(session)
count = await repo.get_project_count(tenant_key)

# Original query (rollback reference):
# stmt = select(func.count(Project.id)).where(Project.tenant_key == tenant_key)
# result = await session.execute(stmt)
# count = result.scalar()
```

---

## Success Criteria

- [ ] All 67 direct queries migrated to repository/service methods
- [ ] Zero direct `session.execute(select(...))` in endpoint files
- [ ] All repository methods include `tenant_key` parameter
- [ ] Full test suite passes
- [ ] No performance regression

---

## Files to Create/Modify

### New Files
- `src/giljo_mcp/repositories/statistics_repository.py`
- `tests/repositories/test_statistics_repository.py`

### Modified Files
- `src/giljo_mcp/services/template_service.py` (extend)
- `src/giljo_mcp/services/config_service.py` (extend)
- `src/giljo_mcp/repositories/agent_job_repository.py` (extend)
- `api/endpoints/statistics.py`
- `api/endpoints/templates/crud.py`
- `api/endpoints/templates/history.py`
- `api/endpoints/templates/preview.py`
- `api/endpoints/configuration.py`
- `api/endpoints/setup.py`
- `api/endpoints/agent_jobs/operations.py`
- `api/endpoints/agent_templates.py`
- `api/endpoints/mcp_installer.py`

---

## Verification Commands

```bash
# Find remaining direct queries (should be 0 after completion)
grep -r "session\.execute\(select" api/endpoints/ | wc -l

# Run all tests
pytest tests/ -v --tb=short

# Check coverage
pytest tests/ --cov=src/giljo_mcp --cov=api --cov-report=term-missing
```

---

## Agent Assignments

**Recommended**: Use `database-expert` subagent for implementation
**Support**: Use `backend-tester` for validation

---

## Notes for Implementer

1. **Start with Phase 1** (`statistics.py`) - it's 48% of the work
2. **Read each file first** - understand query patterns before coding
3. **Test after each file** - don't batch migrations
4. **Keep original code as comments** - easy rollback
5. **Tenant isolation is CRITICAL** - double-check every method

---

**Last Updated**: 2025-12-24
**Revised By**: Research phase completed, scope reduced from 40+ to 9 files
