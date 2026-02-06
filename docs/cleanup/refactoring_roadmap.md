# GiljoAI MCP Architecture Refactoring Roadmap

**Version:** 1.0
**Created:** 2026-02-06
**Status:** Ready for Execution
**Author:** Orchestrator Coordinator

---

## Executive Summary

This roadmap transforms the GiljoAI MCP codebase from "functional feature additions" to "professional modular architecture" through incremental, testable phases. Each phase targets 10-15 files maximum, with clear entry/exit criteria and rollback strategies.

**Key Metrics:**
| Metric | Current | Target |
|--------|---------|--------|
| Circular Dependencies | 49 cycles | <5 cycles |
| High-Risk Hub Files | 8 files (20+ dependents) | 4 files (planned consolidation) |
| Orphan Modules | 271 files | <50 files (consolidated) |
| Test Coverage | ~80% | >85% |
| Coupling Score | High | Low-Medium |

**Timeline Estimate:** 8-12 phases, 2-4 hours per phase
**Total Effort:** 20-40 hours (incremental over weeks)

---

## Phase Overview

```
Phase 0: Preparation (Foundation)
    |
    +---> Phase 1: Model Layer Refactoring (LOW RISK)
    |         |
    |         +---> Phase 2: Exception & Enum Consolidation (LOW RISK)
    |
    +---> Phase 3: Repository Pattern Introduction (MEDIUM RISK)
              |
              +---> Phase 4: Service Layer Decoupling (MEDIUM RISK)
                        |
                        +---> Phase 5: API Endpoint Flattening (MEDIUM RISK)
                                  |
                                  +---> Phase 6: Dependency Injection Cleanup (HIGH RISK)
                                            |
                                            +---> Phase 7: Frontend Service Consolidation (LOW RISK)
                                                      |
                                                      +---> Phase 8: Circular Dependency Resolution (HIGH RISK)
                                                                |
                                                                +---> Phase 9: Final Polish & Documentation
```

---

## Phase 0: Preparation (Foundation)

**Risk Level:** LOW
**Files Affected:** 5-10 configuration/test files
**Estimated Effort:** 2-3 hours
**Prerequisite:** None

### Objectives

1. Create test coverage baseline
2. Freeze feature development (document current state)
3. Set up metrics tracking
4. Create backup branch strategy

### Tasks

#### 0.1 Generate Coverage Baseline
```bash
pytest tests/ --cov=src/giljo_mcp --cov=api --cov-report=html --cov-report=json
```
Save to: `docs/cleanup/coverage_baseline.json`

#### 0.2 Run Dependency Analysis Refresh
```bash
python -m src.giljo_mcp.cleanup.visualizer
```
Verify: `docs/cleanup/dependency_graph.html` is current

#### 0.3 Create Backup Branch
```bash
git checkout -b backup/pre-architecture-refactor
git push origin backup/pre-architecture-refactor
git checkout feature/0700-code-cleanup-series
```

#### 0.4 Document Current State
Create `docs/cleanup/architecture_baseline.md` with:
- Current circular dependency count
- High-risk file list
- Module coupling metrics

### Entry Criteria
- [ ] 0700a-h handovers complete
- [ ] All tests passing
- [ ] No pending changes

### Exit Criteria
- [ ] Coverage baseline JSON exists
- [ ] Backup branch created
- [ ] Architecture baseline documented
- [ ] Dependency graph current

### Rollback
- Trivial: Delete created files

---

## Phase 1: Model Layer Refactoring

**Risk Level:** LOW
**Files Affected:** 12 files
**Estimated Effort:** 3-4 hours
**Prerequisite:** Phase 0

### Problem Statement

The `src/giljo_mcp/models/__init__.py` file has **101 dependents** because it re-exports every model. This creates tight coupling and makes it impossible to import individual models without pulling the entire model layer.

### Objectives

1. Convert `models/__init__.py` from re-export to minimal facade
2. Update importers to use direct imports
3. Reduce `models/__init__.py` dependents from 101 to ~20

### Files to Modify

| File | Change Type | Risk |
|------|-------------|------|
| `src/giljo_mcp/models/__init__.py` | Major refactor | Medium |
| `src/giljo_mcp/models/agent_identity.py` | Minor imports | Low |
| `src/giljo_mcp/models/products.py` | Minor imports | Low |
| `src/giljo_mcp/models/projects.py` | Minor imports | Low |
| `src/giljo_mcp/models/auth.py` | Minor imports | Low |
| `src/giljo_mcp/models/config.py` | Minor imports | Low |
| `src/giljo_mcp/models/context.py` | Minor imports | Low |
| `src/giljo_mcp/models/settings.py` | Minor imports | Low |
| `src/giljo_mcp/models/templates.py` | Minor imports | Low |
| `src/giljo_mcp/models/organizations.py` | Minor imports | Low |
| `api/dependencies.py` | Update imports | Low |
| `api/endpoints/**/*.py` | Update imports (batch) | Low |

### Implementation Strategy

**Step 1:** Identify all `from src.giljo_mcp.models import X` patterns
```bash
grep -r "from src.giljo_mcp.models import" src/ api/ --include="*.py" | head -50
```

**Step 2:** Create model groupings in `__init__.py`:
```python
# src/giljo_mcp/models/__init__.py

# Core models (commonly used together)
from .agent_identity import AgentJob, AgentExecution, AgentTodoItem
from .products import Product, VisionDocument, Vision
from .projects import Project
from .auth import User, APIKey, MCPSession
from .base import Base

# Only export what's needed for facades
__all__ = [
    "Base",
    "AgentJob", "AgentExecution", "AgentTodoItem",
    "Product", "VisionDocument", "Vision", "Project",
    "User", "APIKey", "MCPSession",
]
```

**Step 3:** Update high-frequency importers to use direct imports:
```python
# Before:
from src.giljo_mcp.models import AgentJob, Product, Project

# After:
from src.giljo_mcp.models.agent_identity import AgentJob
from src.giljo_mcp.models.products import Product
from src.giljo_mcp.models.projects import Project
```

### Testing Strategy

1. After each file change, run:
   ```bash
   python -c "from src.giljo_mcp.models import *; print('OK')"
   pytest tests/unit/models/ -v
   ```

2. Full validation after phase:
   ```bash
   pytest tests/ -v --tb=short
   ```

### Expected Dependency Reduction

| File | Before | After |
|------|--------|-------|
| `models/__init__.py` | 101 dependents | ~25 dependents |

### Entry Criteria
- [ ] Phase 0 complete
- [ ] All tests passing

### Exit Criteria
- [ ] `models/__init__.py` dependents reduced to <30
- [ ] All imports use direct model imports
- [ ] All tests passing
- [ ] No new circular dependencies introduced

### Rollback
```bash
git checkout HEAD~1 -- src/giljo_mcp/models/
```

---

## Phase 2: Exception & Enum Consolidation

**Risk Level:** LOW
**Files Affected:** 8 files
**Estimated Effort:** 2-3 hours
**Prerequisite:** Phase 1

### Problem Statement

`src/giljo_mcp/exceptions.py` (28 dependents) and `src/giljo_mcp/enums.py` contain unused definitions and inconsistent patterns. Dead code audit identified 25+ unused exception classes and 23+ unused enum values.

### Objectives

1. Remove remaining unused exceptions identified in dead_code_audit.md
2. Consolidate enum definitions into domain-specific modules
3. Add proper `__all__` exports

### Files to Modify

| File | Change Type | Risk |
|------|-------------|------|
| `src/giljo_mcp/exceptions.py` | Remove unused exceptions | Low |
| `src/giljo_mcp/enums.py` | Split into domain enums | Medium |
| `src/giljo_mcp/models/enums.py` | New: Model-related enums | Low |
| `src/giljo_mcp/services/enums.py` | New: Service-related enums | Low |
| `api/enums.py` | New: API-related enums | Low |
| `src/giljo_mcp/exceptions.py` | Update imports | Low |
| Tests (5+ files) | Update imports | Low |

### Implementation Strategy

**Step 1:** Verify unused exceptions from vulture:
```bash
vulture src/giljo_mcp/exceptions.py --min-confidence 80
```

**Step 2:** Remove unused exceptions:
- `TemplateValidationError` (if never raised)
- `TemplateRenderError` (if never raised)
- `GitOperationError`, `GitAuthenticationError`, `GitRepositoryError` (if never raised)

**Step 3:** Create domain-specific exception modules (optional refinement):
```python
# src/giljo_mcp/exceptions/__init__.py
from .base import GiljoMCPError
from .auth import AuthenticationError, AuthorizationError
from .database import DatabaseError, ConnectionError
from .orchestration import OrchestrationError, AgentError
```

### Testing Strategy

1. After each exception removal:
   ```bash
   grep -r "ExceptionName" src/ api/ tests/
   pytest tests/ -v
   ```

### Expected Dependency Reduction

| File | Before | After |
|------|--------|-------|
| `exceptions.py` | 28 dependents | 20 dependents |
| `enums.py` | 20+ dependents | Split across domains |

### Entry Criteria
- [ ] Phase 1 complete
- [ ] All tests passing

### Exit Criteria
- [ ] Zero unused exceptions
- [ ] Enums split by domain (optional)
- [ ] All tests passing

### Rollback
```bash
git checkout HEAD~1 -- src/giljo_mcp/exceptions.py src/giljo_mcp/enums.py
```

---

## Phase 3: Repository Pattern Introduction

**Risk Level:** MEDIUM
**Files Affected:** 15 files
**Estimated Effort:** 4-5 hours
**Prerequisite:** Phase 2

### Problem Statement

`src/giljo_mcp/database.py` (57 dependents) is a monolithic database access layer. Services directly create sessions and run queries, leading to:
- Tight coupling to SQLAlchemy
- Duplicate query patterns
- Difficult to test without database

### Objectives

1. Create repository classes for major entities
2. Centralize common query patterns
3. Reduce `database.py` dependents from 57 to ~15

### Files to Create

| File | Purpose |
|------|---------|
| `src/giljo_mcp/repositories/__init__.py` | Repository exports |
| `src/giljo_mcp/repositories/base.py` | Base repository class (exists, enhance) |
| `src/giljo_mcp/repositories/agent_job_repository.py` | AgentJob queries |
| `src/giljo_mcp/repositories/product_repository.py` | Product queries |
| `src/giljo_mcp/repositories/project_repository.py` | Project queries |
| `src/giljo_mcp/repositories/user_repository.py` | User queries |

### Files to Modify

| File | Change Type | Risk |
|------|-------------|------|
| `src/giljo_mcp/services/orchestration_service.py` | Use repositories | Medium |
| `src/giljo_mcp/services/project_service.py` | Use repositories | Medium |
| `src/giljo_mcp/services/product_service.py` | Use repositories | Medium |
| `src/giljo_mcp/services/auth_service.py` | Use repositories | Medium |
| `src/giljo_mcp/database.py` | Simplify to session factory | Medium |
| Tests (5+ files) | Add repository tests | Low |

### Implementation Strategy

**Step 1:** Create base repository pattern:
```python
# src/giljo_mcp/repositories/base.py
from typing import Generic, TypeVar, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")

class BaseRepository(Generic[T]):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, id: str) -> Optional[T]:
        raise NotImplementedError

    async def get_all(self, tenant_key: str) -> List[T]:
        raise NotImplementedError

    async def create(self, entity: T) -> T:
        self.session.add(entity)
        await self.session.flush()
        return entity
```

**Step 2:** Implement AgentJobRepository first (highest usage):
```python
# src/giljo_mcp/repositories/agent_job_repository.py
from .base import BaseRepository
from ..models.agent_identity import AgentJob

class AgentJobRepository(BaseRepository[AgentJob]):
    async def get_by_id(self, job_id: str) -> Optional[AgentJob]:
        return await self.session.get(AgentJob, job_id)

    async def get_active_jobs(self, tenant_key: str) -> List[AgentJob]:
        stmt = select(AgentJob).where(
            AgentJob.tenant_key == tenant_key,
            AgentJob.status.in_(["pending", "running"])
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
```

**Step 3:** Migrate one service at a time, testing after each.

### Testing Strategy

1. Create repository unit tests with mock sessions
2. Run service tests after each migration
3. Full integration test after phase complete

### Expected Dependency Reduction

| File | Before | After |
|------|--------|-------|
| `database.py` | 57 dependents | ~15 dependents |
| Services | Direct DB access | Through repositories |

### Entry Criteria
- [ ] Phase 2 complete
- [ ] All tests passing

### Exit Criteria
- [ ] 4 repository classes created
- [ ] Major services migrated to repositories
- [ ] `database.py` simplified
- [ ] All tests passing

### Rollback
```bash
git checkout HEAD~1 -- src/giljo_mcp/repositories/ src/giljo_mcp/services/
```

---

## Phase 4: Service Layer Decoupling

**Risk Level:** MEDIUM
**Files Affected:** 12 files
**Estimated Effort:** 4-5 hours
**Prerequisite:** Phase 3

### Problem Statement

`OrchestrationService` and `ProjectService` have circular dependencies through `project_closeout.py`. The dependency chain:
```
orchestration_service.py -> project_service.py -> project_closeout.py -> orchestration_service.py
```

### Objectives

1. Break circular dependency between OrchestrationService and ProjectService
2. Extract shared operations into separate modules
3. Introduce dependency injection patterns

### Files to Modify

| File | Change Type | Risk |
|------|-------------|------|
| `src/giljo_mcp/services/orchestration_service.py` | Decouple | Medium |
| `src/giljo_mcp/services/project_service.py` | Decouple | Medium |
| `src/giljo_mcp/tools/project_closeout.py` | Extract interface | Medium |
| `src/giljo_mcp/services/closeout_service.py` | New: Shared closeout | Low |
| `src/giljo_mcp/services/__init__.py` | Update exports | Low |
| `api/endpoints/projects/*.py` | Update imports | Low |
| Tests (5+ files) | Update for new structure | Low |

### Implementation Strategy

**Step 1:** Analyze the circular dependency:
```bash
# Find the cycle
grep -n "from.*project_service" src/giljo_mcp/tools/project_closeout.py
grep -n "from.*orchestration_service" src/giljo_mcp/services/project_service.py
```

**Step 2:** Extract shared operations to new service:
```python
# src/giljo_mcp/services/closeout_service.py
class CloseoutService:
    """Handles project completion operations without circular imports."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.agent_repo = AgentJobRepository(session)
        self.project_repo = ProjectRepository(session)

    async def complete_project(self, project_id: str, tenant_key: str) -> dict:
        # Move logic from project_closeout.py here
        pass
```

**Step 3:** Update imports in both services to use CloseoutService

### Testing Strategy

1. Run circular dependency detector after changes:
   ```bash
   python -m src.giljo_mcp.cleanup.visualizer
   ```
2. Verify cycle count reduced
3. Full test suite

### Expected Dependency Reduction

| Metric | Before | After |
|--------|--------|-------|
| Circular cycles involving services | ~20 | <5 |

### Entry Criteria
- [ ] Phase 3 complete
- [ ] All tests passing

### Exit Criteria
- [ ] OrchestrationService <-> ProjectService cycle broken
- [ ] CloseoutService created and tested
- [ ] Circular dependency count reduced
- [ ] All tests passing

### Rollback
```bash
git checkout HEAD~1 -- src/giljo_mcp/services/ src/giljo_mcp/tools/
```

---

## Phase 5: API Endpoint Flattening

**Risk Level:** MEDIUM
**Files Affected:** 15 files
**Estimated Effort:** 3-4 hours
**Prerequisite:** Phase 4

### Problem Statement

The `api/endpoints/` structure has excessive nesting and 271 "orphan" modules. Many endpoints have duplicate dependency patterns and boilerplate.

### Objectives

1. Consolidate endpoint dependencies into a single module
2. Remove duplicate `dependencies.py` files across subfolders
3. Standardize endpoint patterns

### Files to Modify

| File | Change Type | Risk |
|------|-------------|------|
| `api/endpoints/dependencies.py` | Consolidate all deps | Medium |
| `api/endpoints/agent_jobs/dependencies.py` | Remove (merge up) | Low |
| `api/endpoints/products/dependencies.py` | Remove (merge up) | Low |
| `api/endpoints/projects/dependencies.py` | Remove (merge up) | Low |
| `api/endpoints/templates/dependencies.py` | Remove (merge up) | Low |
| `api/endpoints/organizations/` | Update imports | Low |
| All endpoint files | Update imports | Low |

### Implementation Strategy

**Step 1:** Audit duplicate dependencies:
```bash
find api/endpoints -name "dependencies.py" -exec wc -l {} \;
```

**Step 2:** Merge into single `api/endpoints/dependencies.py`:
```python
# api/endpoints/dependencies.py

# Common dependencies
async def get_db() -> AsyncSession: ...
async def get_current_user() -> User: ...
async def get_tenant_key() -> str: ...

# Domain-specific dependencies
async def get_product(product_id: str, ...) -> Product: ...
async def get_project(project_id: str, ...) -> Project: ...
async def get_agent_job(job_id: str, ...) -> AgentJob: ...
```

**Step 3:** Update all endpoint files to import from consolidated location

### Testing Strategy

1. After merging each dependencies.py:
   ```bash
   pytest tests/api/ -v
   ```
2. Verify no import errors across all endpoints

### Expected Dependency Reduction

| Metric | Before | After |
|--------|--------|-------|
| `dependencies.py` files | 5+ | 1 |
| Duplicate dependency code | ~200 lines | 0 |

### Entry Criteria
- [ ] Phase 4 complete
- [ ] All tests passing

### Exit Criteria
- [ ] Single consolidated dependencies.py
- [ ] Subfolder dependencies.py files removed
- [ ] All endpoints using centralized deps
- [ ] All tests passing

### Rollback
```bash
git checkout HEAD~1 -- api/endpoints/
```

---

## Phase 6: Dependency Injection Cleanup

**Risk Level:** HIGH
**Files Affected:** 15 files
**Estimated Effort:** 5-6 hours
**Prerequisite:** Phase 5

### Problem Statement

`api/dependencies.py` (26 dependents) and `src/giljo_mcp/auth/dependencies.py` (47 dependents) contain overlapping functionality and create tight coupling.

### Objectives

1. Unify dependency injection patterns
2. Create clear hierarchy: Core DI -> Auth DI -> API DI
3. Reduce total dependents through consolidation

### Files to Modify

| File | Change Type | Risk |
|------|-------------|------|
| `api/dependencies.py` | Refactor to use core | High |
| `src/giljo_mcp/auth/dependencies.py` | Extract to core | High |
| `src/giljo_mcp/core/dependencies.py` | New: Core DI module | Medium |
| `api/app.py` | Update DI setup | High |
| `api/endpoints/**/*.py` | Update imports | Medium |
| Tests (10+ files) | Update for new DI | Low |

### Implementation Strategy

**Step 1:** Create core dependency module:
```python
# src/giljo_mcp/core/dependencies.py
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

class DependencyContainer:
    """Centralized dependency injection container."""

    @staticmethod
    async def get_session() -> AsyncSession:
        async with async_session_maker() as session:
            yield session

    @staticmethod
    async def get_tenant_key(request: Request) -> str:
        # Extract from header or session
        pass
```

**Step 2:** Migrate auth dependencies to use core container
**Step 3:** Migrate API dependencies to use auth layer
**Step 4:** Update all endpoints incrementally

### Testing Strategy

1. Create DI container unit tests
2. Test each layer in isolation
3. Full integration test after all layers migrated

### Expected Dependency Reduction

| File | Before | After |
|------|--------|-------|
| `api/dependencies.py` | 26 dependents | ~10 dependents |
| `auth/dependencies.py` | 47 dependents | ~15 dependents |
| `core/dependencies.py` | (new) | ~30 dependents (consolidated) |

### Entry Criteria
- [ ] Phase 5 complete
- [ ] All tests passing
- [ ] Backup branch updated

### Exit Criteria
- [ ] Core DI container created
- [ ] Clear DI hierarchy established
- [ ] Total dependents reduced
- [ ] All tests passing

### Rollback
```bash
git checkout HEAD~1 -- api/ src/giljo_mcp/auth/ src/giljo_mcp/core/
```

---

## Phase 7: Frontend Service Consolidation

**Risk Level:** LOW
**Files Affected:** 15 files
**Estimated Effort:** 3-4 hours
**Prerequisite:** Phase 6

### Problem Statement

Frontend has 170+ components with many "orphan" modules that aren't imported anywhere. Services and composables are scattered.

### Objectives

1. Identify and remove truly unused frontend components
2. Consolidate API services
3. Standardize composable patterns

### Files to Analyze/Modify

| Area | Action |
|------|--------|
| `frontend/src/services/` | Consolidate into single api.js |
| `frontend/src/composables/` | Audit and consolidate |
| `frontend/src/stores/` | Remove duplicate stores |
| `frontend/src/components/` | Remove orphan components |

### Implementation Strategy

**Step 1:** Audit orphan components:
```bash
# Run visualizer for frontend
cd frontend
npm run lint -- --report-unused-disable-directives
```

**Step 2:** Verify each "orphan" is truly unused (some may be lazy-loaded)

**Step 3:** Remove confirmed orphan components

**Step 4:** Consolidate services:
```javascript
// frontend/src/services/api.js
// Single unified API service
export const apiService = {
  products: { ... },
  projects: { ... },
  agents: { ... },
  auth: { ... }
}
```

### Testing Strategy

1. Run frontend tests after each removal:
   ```bash
   cd frontend && npm run test
   ```
2. Manual smoke test after consolidation

### Expected Improvements

| Metric | Before | After |
|--------|--------|-------|
| Orphan frontend files | ~80 | <20 |
| Service files | 5+ | 1-2 |

### Entry Criteria
- [ ] Phase 6 complete
- [ ] Backend tests passing

### Exit Criteria
- [ ] Orphan components removed or justified
- [ ] Services consolidated
- [ ] Frontend tests passing

### Rollback
```bash
git checkout HEAD~1 -- frontend/
```

---

## Phase 8: Circular Dependency Resolution

**Risk Level:** HIGH
**Files Affected:** 20+ files
**Estimated Effort:** 6-8 hours
**Prerequisite:** Phase 7

### Problem Statement

49 circular dependency cycles remain. The largest cycles involve:
- `api/app.py` <-> `auth/__init__.py` <-> `api/dependencies.py`
- `orchestration_service.py` <-> `project_service.py` <-> `project_closeout.py`

### Objectives

1. Reduce circular dependencies from 49 to <5
2. Break all service-level cycles
3. Eliminate API-level cycles through lazy imports

### Strategy

**For Service Cycles:**
- Use dependency injection to break direct imports
- Create interface protocols for cross-service communication

**For API Cycles:**
- Use FastAPI's dependency system instead of direct imports
- Lazy import patterns where necessary

**For Auth Cycles:**
- Extract shared auth utilities to separate module
- Use TYPE_CHECKING imports for type hints

### Implementation Pattern
```python
# Use TYPE_CHECKING for type hints only
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .project_service import ProjectService

# Use dependency injection at runtime
class OrchestrationService:
    def __init__(self, project_service: "ProjectService"):
        self.project_service = project_service
```

### Testing Strategy

1. After each cycle break:
   ```bash
   python -m src.giljo_mcp.cleanup.visualizer
   ```
2. Verify cycle count reduced
3. Full test suite after phase

### Expected Improvements

| Metric | Before | After |
|--------|--------|-------|
| Circular cycles | 49 | <5 |
| Import time | Current | Faster |

### Entry Criteria
- [ ] Phase 7 complete
- [ ] All tests passing
- [ ] Backup branch updated

### Exit Criteria
- [ ] <5 circular dependencies
- [ ] All tests passing
- [ ] Import time improved

### Rollback
```bash
git checkout backup/pre-architecture-refactor
```

---

## Phase 9: Final Polish & Documentation

**Risk Level:** LOW
**Files Affected:** 10-15 files
**Estimated Effort:** 3-4 hours
**Prerequisite:** Phase 8

### Objectives

1. Generate final metrics report
2. Update CLAUDE.md with new architecture patterns
3. Create architecture decision records (ADRs)
4. Update API documentation

### Deliverables

1. `docs/cleanup/architecture_final.md` - Final metrics comparison
2. `docs/architecture/ADR-001-repository-pattern.md` - Why we use repositories
3. `docs/architecture/ADR-002-service-decoupling.md` - Service layer patterns
4. Updated `CLAUDE.md` with new patterns

### Entry Criteria
- [ ] Phase 8 complete
- [ ] All tests passing

### Exit Criteria
- [ ] Final metrics documented
- [ ] ADRs written
- [ ] CLAUDE.md updated
- [ ] All documentation current

---

## Appendix A: Risk Mitigation Strategies

### Pre-Phase Checklist (Every Phase)

- [ ] All tests passing
- [ ] Clean git status (committed or stashed)
- [ ] Backup branch up to date
- [ ] Coverage report generated

### During Phase

- [ ] Commit after each significant change
- [ ] Run tests after each file modification
- [ ] Document unexpected findings

### Post-Phase Checklist

- [ ] All tests passing
- [ ] No new ruff warnings
- [ ] Dependency graph regenerated
- [ ] Metrics compared to baseline

### Emergency Rollback

```bash
# Full rollback to pre-refactor state
git checkout backup/pre-architecture-refactor
git checkout -b recovery/architecture-$(date +%Y%m%d)
```

---

## Appendix B: Metrics Tracking Template

```json
{
  "phase": "X",
  "date": "YYYY-MM-DD",
  "before": {
    "circular_deps": 49,
    "hub_file_dependents": {
      "models/__init__.py": 101,
      "database.py": 57,
      "auth/dependencies.py": 47
    },
    "test_count": 0,
    "test_pass_rate": "100%"
  },
  "after": {
    "circular_deps": 0,
    "hub_file_dependents": {},
    "test_count": 0,
    "test_pass_rate": "0%"
  },
  "files_modified": [],
  "notes": ""
}
```

---

## Appendix C: Agent Assignment Recommendations

| Phase | Primary Agent | Supporting Agents |
|-------|---------------|-------------------|
| 0 | tdd-implementor | - |
| 1 | tdd-implementor | database-expert |
| 2 | tdd-implementor | system-architect |
| 3 | database-expert | tdd-implementor |
| 4 | system-architect | tdd-implementor |
| 5 | tdd-implementor | - |
| 6 | system-architect | tdd-implementor, network-security-engineer |
| 7 | frontend-tester | ux-designer |
| 8 | system-architect | tdd-implementor |
| 9 | documentation-manager | system-architect |

---

## Appendix D: Quick Reference Commands

```bash
# Regenerate dependency graph
python -m src.giljo_mcp.cleanup.visualizer

# Check circular dependencies
python -c "import json; d=json.load(open('handovers/0700_series/dependency_analysis.json')); print(f'Cycles: {len(d[\"circular_dependencies\"])}')"

# Generate coverage report
pytest tests/ --cov=src/giljo_mcp --cov-report=html

# Lint check
ruff check src/ api/

# Import verification
python -c "from src.giljo_mcp.models import *; from api.app import app; print('All imports OK')"

# Full test suite
pytest tests/ -v --tb=short
```

---

**Document End**

*Last Updated: 2026-02-06*
*Author: Orchestrator Coordinator*
*Series: 0700 Code Cleanup*
