# 0740 Architecture Consistency Audit - Findings Report

**Audit**: #6 of 0740 Comprehensive Post-Cleanup Audit
**Auditor**: System Architect Agent
**Date**: 2026-02-10
**Branch**: feature/0730-service-response-models-v2
**Scope**: Service layer, API endpoints, tests, naming, imports, error handling

---

## Executive Summary

**Overall Architecture Consistency Score: 7.5 / 10**

The 0730 series (0730a-0730e) successfully established exception-based error handling across the service layer and significantly improved API endpoint consistency. However, several inconsistencies remain that prevent a higher score. The most critical findings are HTTPException leaking into a service file and bare ValueError usage where domain exceptions should be used.

| Category | Score | Notes |
|----------|-------|-------|
| Service Layer Pattern | 7/10 | 4 constructor patterns, HTTPException leak, ValueError usage |
| API Endpoint Pattern | 7/10 | 36 dict wrappers remain in 10 files |
| Test Pattern | 8/10 | Consistent pytest.raises pattern, good coverage |
| Naming Conventions | 8/10 | Minor Optional vs pipe-union split |
| Import Patterns | 9/10 | Uniform absolute imports, 1 structlog outlier |
| Error Handling | 7/10 | HTTPException in service, 8 bare ValueErrors |

**P0 (Critical)**: 0 issues
**P1 (High)**: 2 issues
**P2 (Medium)**: 4 issues
**P3 (Low)**: 5 issues
---

## 1. Service Layer Pattern Consistency

### 1.1 Services Audited (18 total: 12 primary, 6 utility)

**Primary Services** (database-backed, business logic):

| Service | File | Lines | Constructor | Tenant Pattern | Session Pattern | Return Type |
|---------|------|-------|-------------|----------------|-----------------|-------------|
| ProductService | product_service.py | 1774 | Pattern A (tenant_key) | Direct tenant_key | _get_session() | dict |
| ProjectService | project_service.py | 2687 | Pattern B (TenantManager) | TenantManager | _get_session() | dict |
| TaskService | task_service.py | 1101 | Pattern B (TenantManager) | TenantManager | _get_session() | dict |
| AuthService | auth_service.py | 921 | Pattern D (no tenant) | Cross-tenant | _get_session() | dict |
| OrchestrationService | orchestration_service.py | 3256 | Pattern B (TenantManager) | TenantManager | _get_session() | dict |
| AgentJobManager | agent_job_manager.py | 617 | Pattern A (tenant_key) | Direct tenant_key | _get_session() | dict |
| MessageService | message_service.py | 1292 | Pattern B (TenantManager) | TenantManager | _get_session() | dict |
| TemplateService | template_service.py | 1013 | Pattern A (tenant_key) | Direct tenant_key | db_manager.get_session_async() | dict |
| UserService | user_service.py | 1278 | Pattern A (tenant_key) | Direct tenant_key | _get_session() | dict |
| OrgService | org_service.py | 584 | Pattern C (raw session) | Via session | Direct session | ORM model |
| SettingsService | settings_service.py | 95 | Pattern C (raw session) | N/A | Direct session | dict |
| ContextService | context_service.py | 197 | Pattern A (tenant_key) | Direct tenant_key | _get_session() | dataclass |

**Utility Services** (non-database, infrastructure):

| Service | File | Lines | Purpose |
|---------|------|-------|---------|
| ConsolidationService | consolidation_service.py | 154 | DB consolidation |
| ConfigService | config_service.py | 84 | File I/O config |
| GitService | git_service.py | 319 | Subprocess git ops |
| VisionSummarizer | vision_summarizer.py | 316 | Pure computation |
| SerenaDetector | serena_detector.py | 166 | Subprocess detection |
| ClaudeConfigManager | claude_config_manager.py | 321 | File I/O config |
### 1.2 Constructor Pattern Analysis

Four distinct constructor patterns exist across services:

**Pattern A - Direct tenant_key (5 services)**:
ProductService, AgentJobManager, UserService, ContextService, TemplateService

    def __init__(self, db_manager, tenant_key, ...):
        self.db_manager = db_manager
        self.tenant_key = tenant_key

**Pattern B - TenantManager injection (4 services)**:
ProjectService, TaskService, OrchestrationService, MessageService

    def __init__(self, db_manager, tenant_manager, ...):
        self.db_manager = db_manager
        self.tenant_manager = tenant_manager

**Pattern C - Raw session (2 services)**:
OrgService, SettingsService

    def __init__(self, session):
        self.session = session

**Pattern D - No tenant (1 service)**:
AuthService

    def __init__(self, db_manager):
        self.db_manager = db_manager

**Finding [P2-1]**: 4 different constructor patterns creates cognitive overhead. Pattern A and Pattern B achieve the same goal (tenant isolation) through different mechanisms. This is an architectural inconsistency, though not a functional bug.

**Recommendation**: Standardize on Pattern A (direct tenant_key) for all tenant-aware services. TenantManager adds indirection without clear benefit in the current codebase. Pattern C (raw session) should be migrated to Pattern A with _get_session() for consistency and testability.

### 1.3 Session Management Pattern

Most services use _get_session() for test injection:

    async def _get_session(self):
        if self._test_session:
            return self._test_session
        return self.db_manager.get_session_async()

**Finding [P3-1]**: TemplateService does NOT implement _get_session(). It calls self.db_manager.get_session_async() directly in every method, making test session injection impossible without mocking.

- File: src/giljo_mcp/services/template_service.py
- Pattern: Uses db_manager.get_session_async() directly (no _get_session wrapper)

### 1.4 Return Type Consistency

| Return Pattern | Services |
|---------------|----------|
| dict | ProductService, ProjectService, TaskService, AuthService, OrchestrationService, AgentJobManager, MessageService, TemplateService, UserService, SettingsService |
| ORM model | OrgService |
| dataclass | ContextService |

**Finding [P3-2]**: OrgService returns SQLAlchemy ORM model instances directly from service methods. All other database-backed services return dicts. This forces the API layer to handle serialization differently for org endpoints.

- File: src/giljo_mcp/services/org_service.py
- Methods: create_organization(), get_organization(), list_organizations(), etc.

**Finding [P2-2]**: ContextService returns dataclass instances (ContextIndex, VisionDocument, etc.) instead of dicts. While dataclasses are superior to dicts for type safety, this is inconsistent with the rest of the service layer.

- File: src/giljo_mcp/services/context_service.py
- Note: This service appears to be a stub/placeholder, so this may be intentional.
---

## 2. API Endpoint Pattern Consistency

### 2.1 Endpoint Groups Audited

| Group | Files | Auth Pattern | Error Pattern | Response Pattern |
|-------|-------|-------------|---------------|------------------|
| auth | 1 | N/A (login) | HTTPException | Pydantic models |
| products | 3 | get_current_active_user | try/except->HTTPException | Pydantic models |
| projects | 3 | get_current_active_user | Service exceptions propagate | Manual dict->Pydantic |
| tasks | 1 | get_current_active_user | try/except->HTTPException | Pydantic models |
| users | 1 | get_current_active_user | try/except->HTTPException | Pydantic models |
| settings | 1 | get_current_active_user | try/except->HTTPException | Mixed (dict+Pydantic) |
| agent_jobs | 4 | get_current_active_user | try/except->HTTPException | Pydantic models |
| organizations | 1 | get_current_active_user | try/except->HTTPException | Manual serialization |
| messages | 2 | get_current_active_user | try/except->HTTPException | Pydantic models |
| templates | 2 | get_current_active_user | try/except->HTTPException | Pydantic models |
| orchestration | 2 | get_current_active_user | try/except->HTTPException | Mixed |
| mcp | 2 | API key | try/except->HTTPException | JSON-RPC |
| websocket | 1 | Token auth | try/except->close | N/A |
| context | 1 | get_current_active_user | try/except->HTTPException | Pydantic models |

### 2.2 Dict Wrapper Pattern (success: True/False)

Grep found 36 instances of success dict wrappers across 10 endpoint files:

| File | Count | Pattern |
|------|-------|---------|
| api/endpoints/agent_jobs/lifecycle.py | 7 | return {success: True, ...} |
| api/endpoints/agent_jobs/messaging.py | 5 | return {success: True, ...} |
| api/endpoints/agent_jobs/crud.py | 3 | return {success: True, ...} |
| api/endpoints/orchestration/crud.py | 4 | return {success: True, ...} |
| api/endpoints/orchestration/operations.py | 3 | return {success: True, ...} |
| api/endpoints/products/crud.py | 4 | return {success: True, ...} |
| api/endpoints/products/vision.py | 3 | return {success: True, ...} |
| api/endpoints/settings.py | 3 | return {success: True, ...} |
| api/endpoints/tasks.py | 2 | return {success: True, ...} |
| api/endpoints/auth.py | 2 | return {success: True, ...} |

**Finding [P2-3]**: 36 dict wrapper responses remain in API endpoints. The 0730b handover eliminated dict wrappers from services, but endpoints still return them. This creates an inconsistent API contract - some endpoints return Pydantic models, others return raw dicts with success keys.

**Note**: These are in the API layer (not services), so they do not violate the 0730b service-layer cleanup. However, they represent the next cleanup target for API response consistency.

### 2.3 Response Model Usage

Two patterns exist for API responses:

**Pattern 1 - Pydantic response_model (correct)**:

    @router.get("/", response_model=list[ProjectResponse])
    async def list_projects(...) -> list[ProjectResponse]:

**Pattern 2 - Manual dict construction (inconsistent)**:

    @router.post("/activate")
    async def activate_project(...):
        return {"success": True, "project": result}

Projects endpoints (crud.py) show a particularly verbose pattern where every endpoint manually constructs ProjectResponse from dict fields with .get() calls and hardcoded defaults. This is repeated 6 times across the file (lines 67-85, 114-135, 167-189, 225-243, 276-294, 337-355).

### 2.4 Project Endpoint Manual Mapping

**Finding [P3-3]**: The projects/crud.py file manually maps dict keys to ProjectResponse fields 6 times with identical boilerplate:

    return ProjectResponse(
        id=proj.get("id"),
        alias=proj.get("alias", ""),
        name=proj.get("name"),
        description=proj.get("description"),
        mission=proj.get("mission", ""),
        status=proj.get("status"),
        ...  # 15+ fields each time
    )

This should be extracted to a helper function like _to_project_response(proj: dict) -> ProjectResponse.
---

## 3. Test Pattern Consistency

### 3.1 Test Groups Audited

| Test Group | Files | Pattern | Fixtures |
|-----------|-------|---------|----------|
| services/ | 8 | pytest.raises + exception assertions | db_session, service fixtures |
| endpoints/ | 6 | httpx.AsyncClient + status assertions | test_client, auth fixtures |
| integration/ | 4 | Full stack with real DB | db_session, full fixtures |
| mcp/ | 3 | Tool function calls + assertions | mock fixtures |
| unit/ | 2 | Pure function tests | Minimal fixtures |

### 3.2 Exception Testing Pattern

All service tests follow a consistent pattern established by 0730b:

    async def test_method_raises_on_invalid_input(service):
        with pytest.raises(ValidationError, match="expected message"):
            await service.method(invalid_input)

This pattern is consistently applied across:
- test_product_service_exceptions.py
- test_agent_job_manager_exceptions.py
- test_project_service_exceptions.py
- test_task_service.py
- test_auth_service.py

### 3.3 Fixture Patterns

conftest.py uses PostgreSQL-backed fixtures with transaction rollback:

    @pytest.fixture
    async def db_session():
        async with engine.begin() as conn:
            session = AsyncSession(bind=conn)
            yield session
            await conn.rollback()

This pattern is consistent across all test groups.

**Finding [P3-4]**: No test files were found for OrgService or SettingsService exception handling. While basic functionality tests may exist, the exception-specific test pattern from 0730b has not been applied to these services.

---

## 4. Naming Convention Consistency

### 4.1 Type Annotation Style

Two styles coexist across the codebase:

| Style | Files Using | Example |
|-------|-------------|---------|
| Optional[X] (typing module) | 9 service files | Optional[str] = None |
| X or None (Python 3.10+) | 5 service files | str or None = None |

**Finding [P3-5]**: Mixed type annotation styles. The codebase targets Python 3.11+ (per CLAUDE.md), so the modern union syntax should be preferred everywhere. This is cosmetic but affects consistency.

Files using Optional[X]:
- product_service.py, project_service.py, task_service.py, auth_service.py
- orchestration_service.py, agent_job_manager.py, message_service.py
- template_service.py, user_service.py

Files using union syntax:
- context_service.py, settings_service.py, org_service.py
- consolidation_service.py, config_service.py

### 4.2 Method Naming

Services consistently use:
- create_X, get_X, list_Xs, update_X, delete_X (CRUD)
- activate_X, deactivate_X (lifecycle)
- get_X_by_Y (lookup variants)

No naming inconsistencies found in method names.

### 4.3 File Naming

All service files use snake_case.py consistently.
All endpoint files use snake_case.py consistently.
All test files use test_snake_case.py consistently.
---

## 5. Import Pattern Consistency

### 5.1 Service Layer Imports

All 18 service files use absolute imports from src.giljo_mcp.*:

    from src.giljo_mcp.models import Product, Project, Task
    from src.giljo_mcp.exceptions import ValidationError, ResourceNotFoundError
    from src.giljo_mcp.database import DatabaseManager

Only services/__init__.py uses relative imports (correct for package __init__).

### 5.2 Logging Import

| Pattern | Count | Files |
|---------|-------|-------|
| import logging; logger = logging.getLogger(__name__) | 17/18 | All except consolidation_service.py |
| import structlog; logger = structlog.get_logger(__name__) | 1/18 | consolidation_service.py |

**Finding [P2-4]**: ConsolidationService uses structlog while all other services use standard logging. Per CLAUDE.md, structured logging is reserved for critical paths (auth, DB, WebSocket, MCP orchestration). ConsolidationService does not fall into any of these categories.

- File: src/giljo_mcp/services/consolidation_service.py, lines 10, 20

### 5.3 Exception Imports

All services that raise exceptions import from src.giljo_mcp.exceptions:

    from src.giljo_mcp.exceptions import (
        ValidationError,
        ResourceNotFoundError,
        DatabaseError,
        ...
    )

No circular imports detected. No star imports found.
---

## 6. Error Handling Pattern Consistency

### 6.1 Service Layer Error Handling

**Target Pattern (established by 0730b)**:
- Services raise domain exceptions from src.giljo_mcp.exceptions
- No HTTPException in services
- No dict wrappers with success keys
- API layer catches domain exceptions and converts to HTTPException

**Grep Results**:
- success: True/False in services: **0 instances** (clean\!)
- raise HTTPException in services: **5 instances** (all in product_service.py)
- raise ValueError in services: **8 instances** across 4 files

### 6.2 HTTPException Leak

**Finding [P1-1]**: HTTPException imported and raised in ProductService.validate_project_path():

- File: src/giljo_mcp/services/product_service.py
- Lines: 1415-1448
- Import: Line 22 (from fastapi import HTTPException)
- Raises: HTTPException(status_code=400, ...) and HTTPException(status_code=404, ...)

This is a clear violation of the service layer pattern. HTTPException is a web framework concern that belongs exclusively in the API layer. The service should raise ValidationError or ResourceNotFoundError instead.

    # Current (WRONG - in service layer):
    raise HTTPException(status_code=400, detail="Invalid project path")

    # Correct:
    raise ValidationError("Invalid project path")

### 6.3 Bare ValueError Usage

**Finding [P1-2]**: 8 instances of bare ValueError across 4 service files:

| File | Line(s) | Context |
|------|---------|---------|
| product_service.py | 543 | Input validation |
| project_service.py | 200 | tenant_key validation |
| orchestration_service.py | 2529, 2533, 2545, 2572 | Parameter validation |
| settings_service.py | 52, 78 | Settings validation |

These should all use ValidationError from src/giljo_mcp/exceptions.py instead. The exception hierarchy provides ValidationError specifically for this purpose, with proper status_code=400 mapping.

### 6.4 Exception Hierarchy Usage

The BaseGiljoError hierarchy (22 classes) is well-designed and covers all common cases:

| Exception | HTTP Status | Usage Count (approx) |
|-----------|-------------|---------------------|
| ValidationError | 400 | High (most services) |
| ResourceNotFoundError | 404 | High (most services) |
| AuthenticationError | 401 | AuthService only |
| AuthorizationError | 403 | AuthService, endpoints |
| DatabaseError | 500 | Rare (wrapped by ORM) |
| DuplicateResourceError | 409 | ProductService, AuthService |
| ServiceUnavailableError | 503 | Rare |
| ConfigurationError | 500 | ConfigService |
| ProjectStateError | 400 | ProjectService |
| OrchestrationError | 500 | OrchestrationService |

The hierarchy is comprehensive and well-utilized across the codebase.
---

## 7. Summary of Findings

### P1 - High Priority (2 issues)

| ID | Finding | File | Lines | Impact |
|----|---------|------|-------|--------|
| P1-1 | HTTPException in ProductService | src/giljo_mcp/services/product_service.py | 1415-1448 | Service layer violation |
| P1-2 | 8 bare ValueError in 4 services | product_service.py:543, project_service.py:200, orchestration_service.py:2529/2533/2545/2572, settings_service.py:52/78 | Pattern violation |

### P2 - Medium Priority (4 issues)

| ID | Finding | File(s) | Impact |
|----|---------|---------|--------|
| P2-1 | 4 different constructor patterns | All services | Cognitive overhead, inconsistency |
| P2-2 | ContextService returns dataclasses (not dicts) | context_service.py | Return type inconsistency |
| P2-3 | 36 dict wrappers in 10 endpoint files | 10 API endpoint files | API contract inconsistency |
| P2-4 | structlog in ConsolidationService | consolidation_service.py:10,20 | Logging inconsistency |

### P3 - Low Priority (5 issues)

| ID | Finding | File(s) | Impact |
|----|---------|---------|--------|
| P3-1 | TemplateService missing _get_session() | template_service.py | Test injection not supported |
| P3-2 | OrgService returns ORM models | org_service.py | Return type inconsistency |
| P3-3 | Project endpoint manual mapping repeated 6x | api/endpoints/projects/crud.py | DRY violation |
| P3-4 | No exception tests for OrgService/SettingsService | tests/services/ | Test coverage gap |
| P3-5 | Mixed Optional[X] vs union syntax | 14 service files | Style inconsistency |
---

## 8. Recommended Next Steps

### Immediate (P1 fixes - low effort, high impact)

1. **Replace HTTPException in ProductService.validate_project_path()** with ValidationError/ResourceNotFoundError. Remove the fastapi HTTPException import from the service file. (~15 min)

2. **Replace 8 bare ValueError** instances with ValidationError from src/giljo_mcp/exceptions.py across 4 service files. (~30 min)

### Short-term (P2 fixes - medium effort)

3. **Standardize constructor pattern** to Pattern A (direct tenant_key) for all tenant-aware services. This requires updating ProjectService, TaskService, OrchestrationService, and MessageService constructors plus their dependency providers. (~2-4 hours)

4. **Replace structlog** in consolidation_service.py with standard logging. (~5 min)

5. **Add Pydantic response models** to replace the 36 dict wrapper endpoints. Create standardized SuccessResponse, ListResponse models. (~2-4 hours)

### Long-term (P3 fixes - as part of ongoing work)

6. **Add _get_session()** to TemplateService for test injection support.
7. **Convert OrgService** to return dicts (consistent with other services).
8. **Extract _to_project_response()** helper in projects/crud.py.
9. **Add exception tests** for OrgService and SettingsService.
10. **Standardize type annotations** to modern union syntax across all files.

---

## Appendix: Audit Methodology

### Files Analyzed

- **Services**: 18 files in src/giljo_mcp/services/
- **Exceptions**: src/giljo_mcp/exceptions.py (286 lines, 22 exception classes)
- **Endpoints**: 14+ groups across api/endpoints/
- **Tests**: 8+ groups across tests/
- **Dependencies**: api/endpoints/dependencies.py, all module-level dependencies.py

### Grep Searches Performed

| Search | Scope | Result |
|--------|-------|--------|
| success: True/False | services/ | 0 matches (clean) |
| success: True/False | endpoints/ | 36 matches in 10 files |
| raise HTTPException | services/ | 5 matches in product_service.py |
| raise ValueError | services/ | 8 matches in 4 files |
| structlog | services/ | 1 match in consolidation_service.py |
| Optional[ | services/ | 9 files |
| union None | services/ | 5 files |
| import logging | services/ | 17 files |

### Scoring Methodology

Each category scored 1-10 based on:
- **9-10**: Fully consistent, no deviations
- **7-8**: Minor deviations, no pattern violations
- **5-6**: Multiple deviations, some pattern violations
- **3-4**: Significant inconsistencies
- **1-2**: No established pattern

Overall score is weighted average with Error Handling and Service Layer weighted 2x.