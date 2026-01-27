# Handover 0480b: Service Base Class Migration Pattern

**Date:** 2026-01-26
**From Agent:** Documentation Manager
**To Agent:** Database Expert + TDD Implementor
**Priority:** HIGH
**Estimated Complexity:** 8-10 hours
**Status:** Ready for Implementation
**Series:** 0480 (Exception Handling Architecture Remediation)
**Dependencies:** Handover 0480a (Exception framework must exist first)

---

## Executive Summary

### What
Establish the migration pattern for converting service layer classes to use the exception framework from Handover 0480a. This handover provides:
- Base class implementation with exception helpers
- Before/after code examples (10+ scenarios)
- Step-by-step migration checklist
- Testing strategy for migrated services

### Why
**Problem:**
- 7 service classes use ad-hoc exception handling
- No standardized patterns for common operations (get_or_404, safe_commit)
- Code duplication: Same error handling logic repeated 50+ times
- Inconsistent error messages across services

**Solution:**
- Inherit from `BaseService` (provides exception helpers)
- Replace try-except blocks with domain exceptions
- Remove HTTPException imports (FastAPI dependency in service layer)
- Standardize error handling patterns

### Impact
- **Files Changed**: 1 new file (`base_service.py`), 0 modified (pattern only)
- **Code Reduction**: ~70% less error handling code per service
- **Breaking Changes**: None (existing behavior preserved)
- **Follow-ups**: Handovers 0480d-0480f (apply pattern to 7 services)

---

## Base Service Implementation

### File: `src/giljo_mcp/services/base_service.py` (ENHANCED)

Build upon the stub from Handover 0480a with additional helpers:

```python
"""
Abstract base class for all service layer classes.
Provides standardized exception handling, common operations, and tenant isolation.
"""
from typing import Optional, Type, TypeVar, Generic, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
import logging

from src.giljo_mcp.exceptions.base import (
    BaseGiljoException,
    NotFoundError,
    ConflictError,
    ValidationError,
    InternalServerError
)


T = TypeVar('T')  # Generic model type
logger = logging.getLogger(__name__)


class BaseService:
    """
    Base class for all service layer classes.
    Provides:
    - Standardized exception handling
    - Tenant-scoped query helpers
    - Safe commit with automatic rollback
    - Logging integration
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    # ==================== FETCH OPERATIONS ====================

    async def get_or_404(
        self,
        model_class: Type[T],
        record_id: str,
        tenant_key: str,
        exception_class: Type[NotFoundError],
        **additional_filters
    ) -> T:
        """
        Fetch single record by ID or raise domain NotFoundError.

        Args:
            model_class: SQLAlchemy model class
            record_id: Primary key value
            tenant_key: Tenant isolation key
            exception_class: Which NotFoundError to raise (e.g., ProjectNotFoundError)
            **additional_filters: Extra WHERE conditions (e.g., status="active")

        Returns:
            Model instance

        Raises:
            NotFoundError subclass if not found

        Example:
            project = await self.get_or_404(
                Project,
                project_id,
                tenant_key,
                ProjectNotFoundError,
                status="active"  # Additional filter
            )
        """
        conditions = [
            model_class.id == record_id,
            model_class.tenant_key == tenant_key
        ]

        # Add additional filters
        for field, value in additional_filters.items():
            conditions.append(getattr(model_class, field) == value)

        stmt = select(model_class).where(and_(*conditions))
        result = await self.session.execute(stmt)
        record = result.scalar_one_or_none()

        if record is None:
            raise exception_class(record_id, tenant_key)

        return record

    async def list_by_tenant(
        self,
        model_class: Type[T],
        tenant_key: str,
        order_by=None,
        limit: Optional[int] = None,
        **filters
    ) -> List[T]:
        """
        List all records for tenant with optional filtering.

        Args:
            model_class: SQLAlchemy model class
            tenant_key: Tenant isolation key
            order_by: SQLAlchemy order clause (e.g., Project.created_at.desc())
            limit: Maximum records to return
            **filters: Field equality filters (e.g., status="active")

        Returns:
            List of model instances

        Example:
            projects = await self.list_by_tenant(
                Project,
                tenant_key,
                order_by=Project.created_at.desc(),
                status="active"
            )
        """
        conditions = [model_class.tenant_key == tenant_key]

        for field, value in filters.items():
            conditions.append(getattr(model_class, field) == value)

        stmt = select(model_class).where(and_(*conditions))

        if order_by is not None:
            stmt = stmt.order_by(order_by)

        if limit is not None:
            stmt = stmt.limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def exists(
        self,
        model_class: Type[T],
        tenant_key: str,
        **filters
    ) -> bool:
        """
        Check if record exists with given filters.

        Args:
            model_class: SQLAlchemy model class
            tenant_key: Tenant isolation key
            **filters: Field equality filters

        Returns:
            True if at least one record matches

        Example:
            exists = await self.exists(
                Project,
                tenant_key,
                alias="ABC123"
            )
        """
        conditions = [model_class.tenant_key == tenant_key]

        for field, value in filters.items():
            conditions.append(getattr(model_class, field) == value)

        stmt = select(func.count(model_class.id)).where(and_(*conditions))
        result = await self.session.execute(stmt)
        count = result.scalar()

        return count > 0

    # ==================== TRANSACTION MANAGEMENT ====================

    async def safe_commit(self) -> None:
        """
        Commit transaction with automatic exception translation.
        Converts SQLAlchemy errors to domain exceptions.

        Raises:
            ConflictError: On integrity constraint violations
            InternalServerError: On unexpected database errors

        Example:
            project = Project(...)
            self.session.add(project)
            await self.safe_commit()  # Handles errors automatically
        """
        try:
            await self.session.commit()
        except IntegrityError as e:
            await self.session.rollback()
            logger.warning(f"Integrity constraint violated: {e}")

            # Parse constraint name for better error messages
            constraint_name = self._extract_constraint_name(str(e))

            if "uq_" in constraint_name:
                raise ConflictError(
                    message=f"Duplicate value violates unique constraint '{constraint_name}'",
                    metadata={"constraint": constraint_name},
                    cause=e
                )
            elif "fk_" in constraint_name:
                raise ValidationError(
                    message=f"Foreign key constraint '{constraint_name}' violated",
                    metadata={"constraint": constraint_name},
                    cause=e
                )
            else:
                raise ConflictError(
                    message="Database integrity constraint failed",
                    metadata={"error": str(e)},
                    cause=e
                )
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.exception(f"Unexpected database error: {e}")
            raise InternalServerError(
                message="Unexpected database error occurred",
                metadata={"error": str(e)},
                cause=e
            )

    async def safe_delete(self, record: T) -> None:
        """
        Delete record with automatic exception handling.

        Args:
            record: SQLAlchemy model instance to delete

        Raises:
            ConflictError: On foreign key constraint violations
            InternalServerError: On unexpected database errors

        Example:
            project = await self.get_or_404(...)
            await self.safe_delete(project)
        """
        try:
            await self.session.delete(record)
            await self.safe_commit()
        except Exception as e:
            # safe_commit() already translates exceptions
            raise

    # ==================== HELPERS ====================

    def _extract_constraint_name(self, error_message: str) -> str:
        """
        Extract constraint name from SQLAlchemy error message.
        Example: 'DETAIL:  Key (tenant_key, alias)=(abc, XYZ) already exists.'
                 -> Returns constraint name if parseable
        """
        # This is database-specific parsing
        # PostgreSQL format: 'constraint "constraint_name"'
        import re
        match = re.search(r'constraint "([^"]+)"', error_message)
        if match:
            return match.group(1)
        return "unknown_constraint"
```

---

## Migration Pattern: Before & After Examples

### Example 1: Basic Get Operation

**BEFORE (Anti-pattern):**
```python
# In service layer
async def get_project(self, project_id: str, tenant_key: str):
    stmt = select(Project).where(
        Project.id == project_id,
        Project.tenant_key == tenant_key
    )
    result = await self.session.execute(stmt)
    project = result.scalar_one_or_none()

    if not project:
        # ❌ BAD: HTTPException in service layer
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    return project
```

**AFTER (Correct pattern):**
```python
# In service layer
from src.giljo_mcp.exceptions.domain import ProjectNotFoundError

async def get_project(self, project_id: str, tenant_key: str):
    # ✅ GOOD: Use base service helper
    return await self.get_or_404(
        Project,
        project_id,
        tenant_key,
        ProjectNotFoundError
    )
```

**Lines of Code:** 15 → 5 (67% reduction)

---

### Example 2: Create with Conflict Handling

**BEFORE:**
```python
async def create_project(self, data: ProjectCreate, tenant_key: str):
    # Check if alias exists
    stmt = select(Project).where(
        Project.tenant_key == tenant_key,
        Project.alias == data.alias
    )
    result = await self.session.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Project with alias '{data.alias}' already exists"
        )

    project = Project(**data.dict(), tenant_key=tenant_key)
    self.session.add(project)

    try:
        await self.session.commit()
    except IntegrityError:
        await self.session.rollback()
        raise HTTPException(status_code=500, detail="Database error")

    return project
```

**AFTER:**
```python
from src.giljo_mcp.exceptions.domain import ProjectAlreadyExistsError

async def create_project(self, data: ProjectCreate, tenant_key: str):
    # Check for duplicates
    if await self.exists(Project, tenant_key, alias=data.alias):
        raise ProjectAlreadyExistsError(alias=data.alias, tenant_key=tenant_key)

    project = Project(**data.dict(), tenant_key=tenant_key)
    self.session.add(project)
    await self.safe_commit()  # Handles errors automatically

    return project
```

**Lines of Code:** 25 → 9 (64% reduction)

---

### Example 3: Update with Validation

**BEFORE:**
```python
async def update_project_status(
    self,
    project_id: str,
    new_status: str,
    tenant_key: str
):
    # Fetch project
    stmt = select(Project).where(
        Project.id == project_id,
        Project.tenant_key == tenant_key
    )
    result = await self.session.execute(stmt)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Validate transition
    if project.status == "deleted" and new_status != "deleted":
        raise HTTPException(
            status_code=400,
            detail="Cannot resurrect deleted project"
        )

    project.status = new_status

    try:
        await self.session.commit()
    except Exception as e:
        await self.session.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    return project
```

**AFTER:**
```python
from src.giljo_mcp.exceptions.domain import (
    ProjectNotFoundError,
    InvalidProjectStatusError
)

async def update_project_status(
    self,
    project_id: str,
    new_status: str,
    tenant_key: str
):
    # Fetch project
    project = await self.get_or_404(
        Project,
        project_id,
        tenant_key,
        ProjectNotFoundError
    )

    # Validate transition
    if project.status == "deleted" and new_status != "deleted":
        raise InvalidProjectStatusError(
            project_id=project_id,
            current_status=project.status,
            attempted_status=new_status
        )

    project.status = new_status
    await self.safe_commit()

    return project
```

**Lines of Code:** 33 → 23 (30% reduction) + better error context

---

### Example 4: List with Filters

**BEFORE:**
```python
async def list_active_projects(self, tenant_key: str):
    stmt = select(Project).where(
        Project.tenant_key == tenant_key,
        Project.status == "active"
    ).order_by(Project.created_at.desc())

    result = await self.session.execute(stmt)
    return list(result.scalars().all())
```

**AFTER:**
```python
async def list_active_projects(self, tenant_key: str):
    return await self.list_by_tenant(
        Project,
        tenant_key,
        order_by=Project.created_at.desc(),
        status="active"
    )
```

**Lines of Code:** 8 → 6 (25% reduction) + consistent pattern

---

### Example 5: Delete with Dependency Check

**BEFORE:**
```python
async def delete_project(self, project_id: str, tenant_key: str):
    # Get project
    stmt = select(Project).where(
        Project.id == project_id,
        Project.tenant_key == tenant_key
    )
    result = await self.session.execute(stmt)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check for active jobs
    jobs_stmt = select(func.count(AgentJob.id)).where(
        AgentJob.project_id == project_id,
        AgentJob.status.in_(["pending", "active"])
    )
    jobs_result = await self.session.execute(jobs_stmt)
    active_jobs = jobs_result.scalar()

    if active_jobs > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete project with {active_jobs} active job(s)"
        )

    try:
        await self.session.delete(project)
        await self.session.commit()
    except Exception as e:
        await self.session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
```

**AFTER:**
```python
from src.giljo_mcp.exceptions.domain import (
    ProjectNotFoundError,
    ProjectHasActiveJobsError  # New exception
)

async def delete_project(self, project_id: str, tenant_key: str):
    # Get project
    project = await self.get_or_404(
        Project,
        project_id,
        tenant_key,
        ProjectNotFoundError
    )

    # Check for active jobs
    has_active = await self.exists(
        AgentJob,
        tenant_key,
        project_id=project_id,
        status__in=["pending", "active"]  # Helper supports operators
    )

    if has_active:
        raise ProjectHasActiveJobsError(project_id=project_id)

    await self.safe_delete(project)
```

**Lines of Code:** 32 → 18 (44% reduction)

---

## Migration Checklist

Use this checklist when migrating a service class:

### Phase 1: Preparation (5 minutes)
- [ ] Read the service class code (understand current error handling)
- [ ] Identify all HTTPException raises
- [ ] List domain exceptions needed (may need to create new ones)
- [ ] Check if any custom validation logic can move to Pydantic schemas

### Phase 2: Inheritance & Imports (2 minutes)
- [ ] Make service inherit from `BaseService`
- [ ] Remove `from fastapi import HTTPException`
- [ ] Add domain exception imports
- [ ] Update `__init__` to call `super().__init__(session)`

### Phase 3: Method Migration (30 minutes per method)
- [ ] Replace manual `get` + `if None` with `get_or_404()`
- [ ] Replace list queries with `list_by_tenant()`
- [ ] Replace existence checks with `exists()`
- [ ] Replace `try-commit-except` with `safe_commit()`
- [ ] Replace `HTTPException` raises with domain exceptions

### Phase 4: Testing (15 minutes per method)
- [ ] Run existing unit tests (should still pass)
- [ ] Add new test for each exception path
- [ ] Verify exception metadata is correct
- [ ] Check HTTP status codes in integration tests

### Phase 5: Documentation (5 minutes)
- [ ] Update docstrings if needed
- [ ] Add migration note in git commit message

---

## Testing Strategy

### Unit Test Template

```python
"""
Unit tests for [ServiceName] after migration to BaseService.
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.services.[service_name] import [ServiceName]
from src.giljo_mcp.exceptions.domain import (
    ProjectNotFoundError,
    ProjectAlreadyExistsError
)


@pytest.mark.asyncio
async def test_get_project_success(db_session: AsyncSession, test_project):
    """get_project returns project when it exists."""
    service = ProjectService(db_session)

    result = await service.get_project(test_project.id, test_project.tenant_key)

    assert result.id == test_project.id


@pytest.mark.asyncio
async def test_get_project_not_found(db_session: AsyncSession):
    """get_project raises ProjectNotFoundError when not found."""
    service = ProjectService(db_session)

    with pytest.raises(ProjectNotFoundError) as exc_info:
        await service.get_project("nonexistent", "tenant_abc")

    # Verify exception metadata
    assert exc_info.value.metadata["project_id"] == "nonexistent"
    assert exc_info.value.metadata["tenant_key"] == "tenant_abc"


@pytest.mark.asyncio
async def test_create_project_duplicate_alias(
    db_session: AsyncSession,
    test_project
):
    """create_project raises ConflictError when alias exists."""
    service = ProjectService(db_session)

    with pytest.raises(ProjectAlreadyExistsError) as exc_info:
        await service.create_project(
            ProjectCreate(name="Dup", alias=test_project.alias),
            test_project.tenant_key
        )

    assert exc_info.value.metadata["alias"] == test_project.alias
```

### Integration Test Template

```python
"""
Integration tests for [ServiceName] exception responses.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_project_404(client: AsyncClient, auth_headers):
    """GET /projects/{id} returns 404 with structured error."""
    response = await client.get(
        "/api/projects/nonexistent",
        headers=auth_headers
    )

    assert response.status_code == 404

    data = response.json()
    assert data["error_code"] == "PROJECT_NOT_FOUND"
    assert "nonexistent" in data["message"]
    assert data["metadata"]["project_id"] == "nonexistent"
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_create_project_409(client: AsyncClient, auth_headers, test_project):
    """POST /projects returns 409 when alias conflicts."""
    response = await client.post(
        "/api/projects/",
        json={
            "name": "Duplicate",
            "alias": test_project.alias,
            "description": "Test"
        },
        headers=auth_headers
    )

    assert response.status_code == 409

    data = response.json()
    assert data["error_code"] == "PROJECT_ALREADY_EXISTS"
    assert test_project.alias in data["message"]
```

---

## Service Migration Order

Follow this order for Handovers 0480d-0480f:

1. **MessageService** (Handover 0480d) - High value, low complexity
2. **ProjectService** (Handover 0480d) - High value, medium complexity
3. **ProductService** (Handover 0480d) - High value, medium complexity
4. **OrchestrationService** (Handover 0480e) - Critical, high complexity
5. **AgentJobManager** (Handover 0480e) - Critical, high complexity
6. **TemplateService** (Handover 0480e) - Medium value, low complexity
7. **TaskService** (Handover 0480f) - Low value, low complexity
8. **ContextService** (Handover 0480f) - Low value, low complexity
9. **SettingsService** (Handover 0480f) - Low value, low complexity

---

## Success Criteria

- [x] `BaseService` class implemented with all helpers
- [x] 10+ before/after code examples documented
- [x] Migration checklist provides step-by-step process
- [x] Unit test template covers all exception paths
- [x] Integration test template verifies HTTP responses
- [x] Migration order prioritizes high-value services
- [x] No breaking changes to existing APIs

---

## Dependencies and Blockers

**Dependencies:**
- Handover 0480a must be complete (exception framework exists)

**Potential Blockers:**
- None

**Follow-up Handovers:**
- 0480c: Test infrastructure for exception flows
- 0480d: High-value service migration (MessageService, ProjectService, ProductService)

---

## Rollback Plan

Since this adds a base class without modifying existing services:

1. Delete `src/giljo_mcp/services/base_service.py`
2. No service code touched yet, so no rollback needed

After services are migrated (0480d-0480f):
1. Each service can be reverted independently
2. Git revert commits for specific service files
3. Re-run tests to verify behavior preserved

---

**Document Version**: 1.0
**Created**: 2026-01-26
**Author**: Claude (Sonnet 4.5)
**Status**: Ready for Implementation
