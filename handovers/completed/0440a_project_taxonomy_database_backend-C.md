# Handover: Project Taxonomy & Series System - Phase 1a (Database & Backend)

**Date:** 2026-01-22
**From Agent:** Documentation Agent
**To Agent:** Database Expert + TDD Implementor
**Priority:** Medium
**Estimated Complexity:** 8-12 hours
**Status:** Ready for Implementation
**Series:** 0440 (Project Organization Enhancement)

---

## Task Summary

Implement a Project Taxonomy & Series System that allows users to organize projects similar to handovers (e.g., "BE-0042a" for Backend project #42, subseries 'a'). This handover covers Phase 1a: **Database Schema + Backend API**.

**Why It's Important:**
- Improves project discoverability and organization
- Provides visual categorization via color-coded types
- Enables logical project grouping by domain (Backend, Frontend, etc.)
- Optional adoption - existing projects remain unaffected

**Expected Outcome:**
- New `project_types` table with tenant-scoped type definitions
- Extended `projects` table with taxonomy fields
- CRUD API endpoints for managing project types
- Series number helper endpoints for easy assignment
- Seed data for 8 default project types per tenant

---

## Context and Background

**Related Features:**
- Handover numbering system (`handovers/0440a_...`, `handovers/0440b_...`)
- Agent template `tags` field (JSON array pattern reference)
- Multi-tenant isolation via `tenant_key` filtering

**User Requirements:**
- Users want to organize projects by domain/category
- Project aliases should be human-readable (e.g., "BE-0042a" vs random "A1B2C3")
- System should suggest next available series numbers
- Must support custom project types beyond defaults
- Color-coding for visual distinction in UI

**Architectural Decisions:**
- Lazy seeding: Default types created on first access per tenant (not during install)
- Nullable fields: Existing projects remain unaffected (optional adoption)
- Series uniqueness: Combination of `(tenant_key, project_type_id, series_number, subseries)` must be unique
- No type deletion if projects assigned: Prevents orphaned references

---

## Technical Details

### Files to Modify

#### 1. Database Models (`src/giljo_mcp/models/projects.py`)
Add new `ProjectType` class and extend `Project` model with taxonomy fields.

**New Model:**
```python
from sqlalchemy import UniqueConstraint

class ProjectType(Base):
    """
    Tenant-scoped project type definitions (e.g., Backend, Frontend, API).
    Used to categorize projects with abbreviations and visual colors.
    """
    __tablename__ = "project_types"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_key = Column(String(36), nullable=False, index=True)
    abbreviation = Column(String(4), nullable=False)  # "BE", "FE", "API" (2-4 uppercase chars)
    label = Column(String(50), nullable=False)  # "Backend", "Frontend"
    color = Column(String(7), nullable=False, default="#607D8B")  # Hex color (e.g., "#4CAF50")
    sort_order = Column(Integer, default=0)  # Display ordering
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    projects = relationship("Project", back_populates="project_type")

    __table_args__ = (
        UniqueConstraint('tenant_key', 'abbreviation', name='uq_project_type_abbr'),
        Index("idx_project_type_tenant", "tenant_key"),
    )
```

**Project Model Extensions:**
```python
# Add to existing Project class (line ~89, after meta_data column)
project_type_id = Column(
    String(36),
    ForeignKey('project_types.id', ondelete='SET NULL'),
    nullable=True,
    comment="Optional project type for categorization (e.g., Backend, Frontend)"
)
series_number = Column(
    Integer,
    nullable=True,
    comment="Sequential project number within type (1-9999)"
)
subseries = Column(
    String(1),
    nullable=True,
    comment="Subseries letter (a-z) for project variants"
)

# Add relationship (line ~119, in relationships section)
project_type = relationship("ProjectType", back_populates="projects")

# Add uniqueness constraint to __table_args__ (line ~130)
UniqueConstraint(
    'tenant_key', 'project_type_id', 'series_number', 'subseries',
    name='uq_project_taxonomy',
    comment="Ensures unique type+series+subseries combination per tenant"
),
```

**Computed Alias Logic:**
The existing `alias` field remains (6-char alphanumeric). Add a computed property for taxonomy-based display:

```python
# Add to Project class as a property
@property
def taxonomy_alias(self) -> str:
    """
    Generate taxonomy-based alias (e.g., 'BE-0042a' or '0042').
    Falls back to standard alias if taxonomy fields are NULL.
    """
    if not self.series_number:
        return self.alias

    # Format: TYPE-####subseries (e.g., BE-0042a)
    series = f"{self.series_number:04d}"  # Zero-padded 4 digits
    if self.subseries:
        series += self.subseries

    if self.project_type_id:
        # Fetch abbreviation (assumes relationship loaded)
        abbr = self.project_type.abbreviation if self.project_type else ""
        return f"{abbr}-{series}" if abbr else series

    return series
```

---

#### 2. Pydantic Schemas (`api/endpoints/projects/models.py`)

**Extend ProjectCreate:**
```python
class ProjectCreate(BaseModel):
    """Request model for project creation."""
    # ... existing fields ...
    project_type_id: Optional[str] = Field(None, description="Project type UUID")
    series_number: Optional[int] = Field(None, ge=1, le=9999, description="Series number (1-9999)")
    subseries: Optional[str] = Field(None, pattern=r'^[a-z]$', description="Subseries letter (a-z)")
```

**Extend ProjectUpdate:**
```python
class ProjectUpdate(BaseModel):
    """Request model for project updates."""
    # ... existing fields ...
    project_type_id: Optional[str] = None
    series_number: Optional[int] = Field(None, ge=1, le=9999)
    subseries: Optional[str] = Field(None, pattern=r'^[a-z]$')
```

**Extend ProjectResponse:**
```python
class ProjectResponse(BaseModel):
    """Response model for project details."""
    # ... existing fields ...
    project_type_id: Optional[str] = None
    series_number: Optional[int] = None
    subseries: Optional[str] = None
    taxonomy_alias: Optional[str] = None  # Computed field
```

**New Schemas for Project Types:**
```python
class ProjectTypeCreate(BaseModel):
    """Request model for creating project type."""
    abbreviation: str = Field(..., min_length=2, max_length=4, pattern=r'^[A-Z]+$')
    label: str = Field(..., min_length=1, max_length=50)
    color: str = Field(default="#607D8B", pattern=r'^#[0-9A-Fa-f]{6}$')
    sort_order: int = Field(default=0)

class ProjectTypeUpdate(BaseModel):
    """Request model for updating project type."""
    label: Optional[str] = Field(None, min_length=1, max_length=50)
    color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    sort_order: Optional[int] = None

class ProjectTypeResponse(BaseModel):
    """Response model for project type."""
    id: str
    tenant_key: str
    abbreviation: str
    label: str
    color: str
    sort_order: int
    project_count: int = 0  # Number of projects using this type
    created_at: datetime
    updated_at: datetime
```

---

#### 3. New API Module (`api/endpoints/project_types/`)

Create a new endpoint module following the modular pattern used in `api/endpoints/projects/`.

**File Structure:**
```
api/endpoints/project_types/
├── __init__.py          # Import routes
├── models.py            # Pydantic schemas (created above)
├── crud.py              # CRUD operations
└── dependencies.py      # Shared dependencies
```

**`api/endpoints/project_types/crud.py`:**
```python
"""
CRUD operations for project types.
Implements tenant-scoped type management with lazy seeding.
"""
from typing import List, Optional
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models.projects import ProjectType, Project
from .models import ProjectTypeCreate, ProjectTypeUpdate, ProjectTypeResponse

# Default project types seeded per tenant on first access
DEFAULT_PROJECT_TYPES = [
    {"abbr": "BE", "label": "Backend", "color": "#4CAF50"},
    {"abbr": "FE", "label": "Frontend", "color": "#2196F3"},
    {"abbr": "DB", "label": "Database", "color": "#FF9800"},
    {"abbr": "UI", "label": "UI/UX", "color": "#9C27B0"},
    {"abbr": "API", "label": "API/Integration", "color": "#00BCD4"},
    {"abbr": "INF", "label": "Infrastructure", "color": "#795548"},
    {"abbr": "DOC", "label": "Documentation", "color": "#607D8B"},
    {"abbr": "SEC", "label": "Security", "color": "#F44336"},
]

async def ensure_default_types_seeded(session: AsyncSession, tenant_key: str) -> None:
    """
    Lazy seed default project types for tenant if none exist.
    Idempotent - safe to call multiple times.
    """
    # Check if tenant has any types
    result = await session.execute(
        select(func.count(ProjectType.id)).where(ProjectType.tenant_key == tenant_key)
    )
    count = result.scalar()

    if count == 0:
        # Seed defaults
        for idx, default in enumerate(DEFAULT_PROJECT_TYPES):
            type_obj = ProjectType(
                tenant_key=tenant_key,
                abbreviation=default["abbr"],
                label=default["label"],
                color=default["color"],
                sort_order=idx
            )
            session.add(type_obj)
        await session.commit()

async def list_project_types(
    session: AsyncSession,
    tenant_key: str,
    include_counts: bool = True
) -> List[ProjectTypeResponse]:
    """
    List all project types for tenant with optional project counts.
    Triggers lazy seeding on first access.
    """
    await ensure_default_types_seeded(session, tenant_key)

    query = select(ProjectType).where(ProjectType.tenant_key == tenant_key).order_by(ProjectType.sort_order)
    result = await session.execute(query)
    types = result.scalars().all()

    # Count projects per type if requested
    type_counts = {}
    if include_counts:
        for pt in types:
            count_result = await session.execute(
                select(func.count(Project.id)).where(
                    and_(
                        Project.tenant_key == tenant_key,
                        Project.project_type_id == pt.id
                    )
                )
            )
            type_counts[pt.id] = count_result.scalar()

    return [
        ProjectTypeResponse(
            id=pt.id,
            tenant_key=pt.tenant_key,
            abbreviation=pt.abbreviation,
            label=pt.label,
            color=pt.color,
            sort_order=pt.sort_order,
            project_count=type_counts.get(pt.id, 0),
            created_at=pt.created_at,
            updated_at=pt.updated_at
        )
        for pt in types
    ]

async def create_project_type(
    session: AsyncSession,
    tenant_key: str,
    data: ProjectTypeCreate
) -> ProjectTypeResponse:
    """Create custom project type."""
    # Validate uniqueness
    existing = await session.execute(
        select(ProjectType).where(
            and_(
                ProjectType.tenant_key == tenant_key,
                ProjectType.abbreviation == data.abbreviation
            )
        )
    )
    if existing.scalar():
        raise ValueError(f"Project type with abbreviation '{data.abbreviation}' already exists")

    pt = ProjectType(
        tenant_key=tenant_key,
        abbreviation=data.abbreviation,
        label=data.label,
        color=data.color,
        sort_order=data.sort_order
    )
    session.add(pt)
    await session.commit()
    await session.refresh(pt)

    return ProjectTypeResponse(
        id=pt.id,
        tenant_key=pt.tenant_key,
        abbreviation=pt.abbreviation,
        label=pt.label,
        color=pt.color,
        sort_order=pt.sort_order,
        project_count=0,
        created_at=pt.created_at,
        updated_at=pt.updated_at
    )

async def update_project_type(
    session: AsyncSession,
    tenant_key: str,
    type_id: str,
    data: ProjectTypeUpdate
) -> ProjectTypeResponse:
    """Update existing project type (label, color, sort_order only)."""
    result = await session.execute(
        select(ProjectType).where(
            and_(
                ProjectType.id == type_id,
                ProjectType.tenant_key == tenant_key
            )
        )
    )
    pt = result.scalar_one_or_none()
    if not pt:
        raise ValueError(f"Project type {type_id} not found")

    # Update fields
    if data.label is not None:
        pt.label = data.label
    if data.color is not None:
        pt.color = data.color
    if data.sort_order is not None:
        pt.sort_order = data.sort_order

    await session.commit()
    await session.refresh(pt)

    # Get project count
    count_result = await session.execute(
        select(func.count(Project.id)).where(
            and_(
                Project.tenant_key == tenant_key,
                Project.project_type_id == pt.id
            )
        )
    )
    project_count = count_result.scalar()

    return ProjectTypeResponse(
        id=pt.id,
        tenant_key=pt.tenant_key,
        abbreviation=pt.abbreviation,
        label=pt.label,
        color=pt.color,
        sort_order=pt.sort_order,
        project_count=project_count,
        created_at=pt.created_at,
        updated_at=pt.updated_at
    )

async def delete_project_type(
    session: AsyncSession,
    tenant_key: str,
    type_id: str
) -> dict:
    """
    Delete project type if no projects are assigned.
    Prevents orphaned references.
    """
    result = await session.execute(
        select(ProjectType).where(
            and_(
                ProjectType.id == type_id,
                ProjectType.tenant_key == tenant_key
            )
        )
    )
    pt = result.scalar_one_or_none()
    if not pt:
        raise ValueError(f"Project type {type_id} not found")

    # Check for assigned projects
    count_result = await session.execute(
        select(func.count(Project.id)).where(
            and_(
                Project.tenant_key == tenant_key,
                Project.project_type_id == pt.id
            )
        )
    )
    project_count = count_result.scalar()

    if project_count > 0:
        raise ValueError(
            f"Cannot delete project type '{pt.label}' - {project_count} project(s) still using it"
        )

    await session.delete(pt)
    await session.commit()

    return {"success": True, "message": f"Project type '{pt.label}' deleted"}
```

**`api/endpoints/project_types/__init__.py`:**
```python
"""Project types API endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_session, get_tenant_key
from .crud import (
    list_project_types,
    create_project_type,
    update_project_type,
    delete_project_type
)
from .models import ProjectTypeCreate, ProjectTypeUpdate, ProjectTypeResponse

router = APIRouter()

@router.get("/", response_model=list[ProjectTypeResponse])
async def get_project_types(
    session: AsyncSession = Depends(get_session),
    tenant_key: str = Depends(get_tenant_key),
    include_counts: bool = True
):
    """List all project types for tenant."""
    return await list_project_types(session, tenant_key, include_counts)

@router.post("/", response_model=ProjectTypeResponse)
async def create_type(
    data: ProjectTypeCreate,
    session: AsyncSession = Depends(get_session),
    tenant_key: str = Depends(get_tenant_key)
):
    """Create custom project type."""
    try:
        return await create_project_type(session, tenant_key, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{type_id}", response_model=ProjectTypeResponse)
async def update_type(
    type_id: str,
    data: ProjectTypeUpdate,
    session: AsyncSession = Depends(get_session),
    tenant_key: str = Depends(get_tenant_key)
):
    """Update project type."""
    try:
        return await update_project_type(session, tenant_key, type_id, data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/{type_id}")
async def delete_type(
    type_id: str,
    session: AsyncSession = Depends(get_session),
    tenant_key: str = Depends(get_tenant_key)
):
    """Delete project type (only if no projects assigned)."""
    try:
        return await delete_project_type(session, tenant_key, type_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

---

#### 4. Series Helper Endpoints (`api/endpoints/projects/crud.py`)

Add two helper endpoints to the existing projects router for series number management:

```python
# Add to api/endpoints/projects/crud.py

async def get_next_series_number(
    session: AsyncSession,
    tenant_key: str,
    type_id: Optional[str] = None
) -> int:
    """
    Get next available series number for a project type.
    Returns 1 if no projects exist for this type.
    """
    query = select(func.max(Project.series_number)).where(
        Project.tenant_key == tenant_key
    )

    if type_id:
        query = query.where(Project.project_type_id == type_id)

    result = await session.execute(query)
    max_series = result.scalar()

    return (max_series or 0) + 1

async def get_available_series_numbers(
    session: AsyncSession,
    tenant_key: str,
    type_id: Optional[str] = None,
    limit: int = 5
) -> List[int]:
    """
    Get list of available series numbers (gaps in sequence).
    Returns up to `limit` suggestions.
    """
    query = select(Project.series_number).where(
        and_(
            Project.tenant_key == tenant_key,
            Project.series_number.isnot(None)
        )
    ).order_by(Project.series_number)

    if type_id:
        query = query.where(Project.project_type_id == type_id)

    result = await session.execute(query)
    used_numbers = set(result.scalars().all())

    if not used_numbers:
        return [1]

    # Find gaps
    available = []
    max_num = max(used_numbers)
    for i in range(1, max_num + 1):
        if i not in used_numbers:
            available.append(i)
            if len(available) >= limit:
                break

    # If no gaps, suggest next sequential
    if not available:
        available = [max_num + 1]

    return available
```

**Add routes to `api/endpoints/projects/__init__.py`:**
```python
@router.get("/next-series")
async def next_series(
    type_id: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
    tenant_key: str = Depends(get_tenant_key)
):
    """Get next available series number for project type."""
    return {"next_series": await get_next_series_number(session, tenant_key, type_id)}

@router.get("/available-series")
async def available_series(
    type_id: Optional[str] = None,
    limit: int = 5,
    session: AsyncSession = Depends(get_session),
    tenant_key: str = Depends(get_tenant_key)
):
    """Get list of available series numbers (gaps + next)."""
    return {"available": await get_available_series_numbers(session, tenant_key, type_id, limit)}
```

---

#### 5. Database Migration (`install.py`)

The migration will run automatically when users run `python install.py` or `python startup.py` (detects schema changes).

**Migration Logic (add to `install.py`):**
```python
# Add to migration detection logic (around line ~200)
def needs_taxonomy_migration(conn) -> bool:
    """Check if project_types table exists."""
    result = conn.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = 'project_types'
        );
    """))
    return not result.scalar()

# Add to migration execution (around line ~500)
if needs_taxonomy_migration(conn):
    logger.info("Applying project taxonomy migration...")

    # Create project_types table
    conn.execute(text("""
        CREATE TABLE project_types (
            id VARCHAR(36) PRIMARY KEY,
            tenant_key VARCHAR(36) NOT NULL,
            abbreviation VARCHAR(4) NOT NULL,
            label VARCHAR(50) NOT NULL,
            color VARCHAR(7) NOT NULL DEFAULT '#607D8B',
            sort_order INTEGER DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            CONSTRAINT uq_project_type_abbr UNIQUE (tenant_key, abbreviation)
        );
    """))

    # Create index
    conn.execute(text("""
        CREATE INDEX idx_project_type_tenant ON project_types(tenant_key);
    """))

    # Add columns to projects table
    conn.execute(text("""
        ALTER TABLE projects
        ADD COLUMN project_type_id VARCHAR(36),
        ADD COLUMN series_number INTEGER,
        ADD COLUMN subseries VARCHAR(1),
        ADD CONSTRAINT fk_project_type
            FOREIGN KEY (project_type_id)
            REFERENCES project_types(id)
            ON DELETE SET NULL;
    """))

    # Add uniqueness constraint
    conn.execute(text("""
        ALTER TABLE projects
        ADD CONSTRAINT uq_project_taxonomy
            UNIQUE (tenant_key, project_type_id, series_number, subseries);
    """))

    conn.commit()
    logger.info("✓ Project taxonomy migration complete")
```

**Note:** Lazy seeding of default types happens on first API access, NOT during install. This prevents unnecessary data creation for tenants who may never use the feature.

---

#### 6. Register Routes in Main App (`api/app.py`)

Add the new project_types router to the main FastAPI app:

```python
# Add to imports
from api.endpoints.project_types import router as project_types_router

# Add to route registration (around line ~150)
app.include_router(
    project_types_router,
    prefix="/api/project-types",
    tags=["project-types"]
)
```

---

## Validation Rules

Implement these validation rules in the Pydantic schemas and CRUD operations:

1. **Abbreviation:**
   - 2-4 uppercase characters only
   - Regex: `^[A-Z]{2,4}$`
   - Unique per tenant

2. **Series Number:**
   - Integer between 1-9999
   - Optional (nullable)

3. **Subseries:**
   - Single lowercase letter (a-z)
   - Regex: `^[a-z]$`
   - Optional (nullable)

4. **Color:**
   - Valid hex color code
   - Regex: `^#[0-9A-Fa-f]{6}$`

5. **Uniqueness:**
   - `(tenant_key, project_type_id, series_number, subseries)` must be unique
   - Database constraint enforces this

6. **Deletion Protection:**
   - Cannot delete a project type if any projects are assigned to it
   - Check enforced in `delete_project_type()` function

---

## Implementation Plan

### Phase 1: Database Schema (2-3 hours)
1. Create `ProjectType` model in `src/giljo_mcp/models/projects.py`
2. Extend `Project` model with taxonomy fields
3. Add `taxonomy_alias` property to Project class
4. Test models with SQLAlchemy 2.0 async patterns

**Testing Criteria:**
- Models can be imported without errors
- Foreign key relationships work correctly
- Uniqueness constraints enforced at DB level

---

### Phase 2: Pydantic Schemas (1-2 hours)
1. Create Pydantic models in `api/endpoints/project_types/models.py`
2. Extend existing `ProjectCreate`, `ProjectUpdate`, `ProjectResponse`
3. Add validation patterns (abbreviation uppercase, subseries lowercase, hex colors)

**Testing Criteria:**
- Schema validation catches invalid data (e.g., lowercase abbreviation)
- Optional fields work correctly
- Computed `taxonomy_alias` appears in responses

---

### Phase 3: CRUD Operations (3-4 hours)
1. Implement lazy seeding in `crud.py`
2. Create CRUD operations for project types
3. Add series helper functions
4. Implement deletion protection logic

**Testing Criteria:**
- Default types seeded on first access
- Cannot create duplicate abbreviations
- Cannot delete types with assigned projects
- Series helpers return correct suggestions

---

### Phase 4: API Endpoints (2-3 hours)
1. Create project_types router module
2. Add series helper endpoints to projects router
3. Register routes in `api/app.py`
4. Test with FastAPI auto-generated docs (`/docs`)

**Testing Criteria:**
- All endpoints accessible via Swagger UI
- Tenant isolation enforced (users only see their types)
- Error responses provide helpful messages

---

### Phase 5: Database Migration (1-2 hours)
1. Add migration detection to `install.py`
2. Implement table creation and column additions
3. Test with fresh database
4. Test with existing database (verify existing projects unaffected)

**Testing Criteria:**
- Fresh install creates tables correctly
- Upgrade path works (adds columns without data loss)
- Migration is idempotent (safe to run multiple times)

---

## Testing Requirements

### Unit Tests

**Test File:** `tests/test_project_taxonomy.py`

```python
"""Unit tests for project taxonomy system."""
import pytest
from sqlalchemy import select
from src.giljo_mcp.models.projects import Project, ProjectType
from api.endpoints.project_types.crud import (
    ensure_default_types_seeded,
    list_project_types,
    create_project_type,
    delete_project_type,
    get_next_series_number
)

@pytest.mark.asyncio
async def test_lazy_seeding(async_session, tenant_key):
    """Test default types are seeded on first access."""
    await ensure_default_types_seeded(async_session, tenant_key)

    result = await async_session.execute(
        select(ProjectType).where(ProjectType.tenant_key == tenant_key)
    )
    types = result.scalars().all()

    assert len(types) == 8  # 8 default types
    assert any(t.abbreviation == "BE" for t in types)
    assert any(t.abbreviation == "FE" for t in types)

@pytest.mark.asyncio
async def test_unique_abbreviation_constraint(async_session, tenant_key):
    """Test abbreviation uniqueness per tenant."""
    await ensure_default_types_seeded(async_session, tenant_key)

    # Try to create duplicate
    with pytest.raises(ValueError, match="already exists"):
        await create_project_type(
            async_session,
            tenant_key,
            ProjectTypeCreate(abbreviation="BE", label="Backend 2", color="#000000")
        )

@pytest.mark.asyncio
async def test_project_taxonomy_uniqueness(async_session, tenant_key, project_type):
    """Test series uniqueness constraint."""
    # Create first project
    project1 = Project(
        tenant_key=tenant_key,
        name="Test 1",
        description="Test",
        mission="Test mission",
        project_type_id=project_type.id,
        series_number=42,
        subseries="a"
    )
    async_session.add(project1)
    await async_session.commit()

    # Try to create duplicate taxonomy
    project2 = Project(
        tenant_key=tenant_key,
        name="Test 2",
        description="Test",
        mission="Test mission",
        project_type_id=project_type.id,
        series_number=42,
        subseries="a"
    )
    async_session.add(project2)

    with pytest.raises(Exception):  # Uniqueness constraint violation
        await async_session.commit()

@pytest.mark.asyncio
async def test_deletion_protection(async_session, tenant_key, project_type, project):
    """Test cannot delete type with assigned projects."""
    project.project_type_id = project_type.id
    await async_session.commit()

    with pytest.raises(ValueError, match="still using it"):
        await delete_project_type(async_session, tenant_key, project_type.id)

@pytest.mark.asyncio
async def test_next_series_number(async_session, tenant_key, project_type):
    """Test series number suggestion."""
    # No projects yet
    next_num = await get_next_series_number(async_session, tenant_key, project_type.id)
    assert next_num == 1

    # Create project with series 1
    project = Project(
        tenant_key=tenant_key,
        name="Test",
        description="Test",
        mission="Test mission",
        project_type_id=project_type.id,
        series_number=1
    )
    async_session.add(project)
    await async_session.commit()

    # Next should be 2
    next_num = await get_next_series_number(async_session, tenant_key, project_type.id)
    assert next_num == 2

@pytest.mark.asyncio
async def test_taxonomy_alias_property(async_session, tenant_key, project_type):
    """Test computed taxonomy_alias property."""
    project = Project(
        tenant_key=tenant_key,
        name="Test",
        description="Test",
        mission="Test mission",
        project_type_id=project_type.id,
        series_number=42,
        subseries="a"
    )
    async_session.add(project)
    await async_session.commit()
    await async_session.refresh(project)

    # Assumes project_type relationship is loaded
    assert project.taxonomy_alias == "BE-0042a"  # Assuming BE type
```

---

### Integration Tests

**Test File:** `tests/integration/test_project_types_api.py`

```python
"""Integration tests for project types API."""
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_list_project_types_lazy_seeds(client: AsyncClient, auth_headers):
    """Test that listing types triggers lazy seeding."""
    response = await client.get("/api/project-types/", headers=auth_headers)
    assert response.status_code == 200

    types = response.json()
    assert len(types) == 8  # 8 default types
    assert all("abbreviation" in t for t in types)
    assert all("color" in t for t in types)

@pytest.mark.asyncio
async def test_create_custom_type(client: AsyncClient, auth_headers):
    """Test creating custom project type."""
    response = await client.post(
        "/api/project-types/",
        json={
            "abbreviation": "TEST",
            "label": "Test Type",
            "color": "#FF5733",
            "sort_order": 10
        },
        headers=auth_headers
    )
    assert response.status_code == 200

    data = response.json()
    assert data["abbreviation"] == "TEST"
    assert data["label"] == "Test Type"
    assert data["color"] == "#FF5733"

@pytest.mark.asyncio
async def test_update_project_type(client: AsyncClient, auth_headers, project_type):
    """Test updating project type."""
    response = await client.put(
        f"/api/project-types/{project_type.id}",
        json={"label": "Updated Label", "color": "#00FF00"},
        headers=auth_headers
    )
    assert response.status_code == 200

    data = response.json()
    assert data["label"] == "Updated Label"
    assert data["color"] == "#00FF00"

@pytest.mark.asyncio
async def test_series_helpers(client: AsyncClient, auth_headers, project_type):
    """Test series number helper endpoints."""
    # Get next series
    response = await client.get(
        f"/api/projects/next-series?type_id={project_type.id}",
        headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["next_series"] == 1

    # Get available series
    response = await client.get(
        f"/api/projects/available-series?type_id={project_type.id}&limit=5",
        headers=auth_headers
    )
    assert response.status_code == 200
    assert len(response.json()["available"]) > 0

@pytest.mark.asyncio
async def test_project_creation_with_taxonomy(client: AsyncClient, auth_headers, project_type, product):
    """Test creating project with taxonomy fields."""
    response = await client.post(
        "/api/projects/",
        json={
            "name": "Backend Project",
            "description": "Test backend work",
            "product_id": product.id,
            "project_type_id": project_type.id,
            "series_number": 42,
            "subseries": "a"
        },
        headers=auth_headers
    )
    assert response.status_code == 200

    data = response.json()
    assert data["project_type_id"] == project_type.id
    assert data["series_number"] == 42
    assert data["subseries"] == "a"
    assert data["taxonomy_alias"] == "BE-0042a"
```

---

### Manual Testing Steps

1. **Fresh Install:**
   ```bash
   # Drop database and reinstall
   PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -c "DROP DATABASE IF EXISTS giljo_mcp_test;"
   PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -c "CREATE DATABASE giljo_mcp_test;"
   python install.py --test
   ```

2. **Test Lazy Seeding:**
   ```bash
   # Start server
   python startup.py

   # Login and navigate to /api/project-types/ in Swagger UI
   # Verify 8 default types appear
   ```

3. **Test CRUD Operations:**
   - Create custom type via Swagger UI
   - Update type label/color
   - Try to delete type (should fail if projects assigned)
   - Delete unused type (should succeed)

4. **Test Project Creation:**
   - Create project with type + series
   - Verify `taxonomy_alias` computed correctly
   - Try to create duplicate series (should fail)

5. **Test Tenant Isolation:**
   - Create second user account
   - Verify they get separate set of default types
   - Verify tenant A cannot see tenant B's types

---

## Dependencies and Blockers

**Dependencies:**
- None - this is a net-new feature

**Potential Blockers:**
- None identified

**External Requirements:**
- PostgreSQL database running
- SQLAlchemy 2.0 async patterns working

---

## Success Criteria

**Definition of Done:**
- ✅ `project_types` table created with proper constraints
- ✅ `projects` table extended with taxonomy fields
- ✅ Lazy seeding works (8 default types on first access)
- ✅ CRUD API endpoints functional
- ✅ Series helper endpoints return correct suggestions
- ✅ Validation rules enforced (abbreviation, series, subseries)
- ✅ Uniqueness constraints prevent duplicates
- ✅ Deletion protection prevents orphaned references
- ✅ Migration runs cleanly on fresh and existing databases
- ✅ Unit tests achieve >80% coverage
- ✅ Integration tests pass for all endpoints
- ✅ Manual testing confirms expected behavior
- ✅ Existing projects unaffected (optional adoption works)

---

## Rollback Plan

**If Migration Fails:**
```sql
-- Rollback script
ALTER TABLE projects DROP CONSTRAINT IF EXISTS fk_project_type;
ALTER TABLE projects DROP CONSTRAINT IF EXISTS uq_project_taxonomy;
ALTER TABLE projects DROP COLUMN IF EXISTS project_type_id;
ALTER TABLE projects DROP COLUMN IF EXISTS series_number;
ALTER TABLE projects DROP COLUMN IF EXISTS subseries;
DROP TABLE IF EXISTS project_types;
```

**If API Issues Occur:**
1. Remove project_types router registration from `api/app.py`
2. Restart server
3. Database remains intact for future retry

---

## Additional Resources

**Similar Implementations:**
- Agent template `tags` field: `src/giljo_mcp/models/templates.py` (line 97)
- Handover numbering: `handovers/HANDOVER_CATALOGUE.md`
- Multi-tenant patterns: `api/endpoints/projects/crud.py`

**Documentation to Update:**
- Phase 1b will handle frontend integration
- Phase 1c will update user documentation

**Related GitHub Issues:**
- None yet - this is a new enhancement

**External Resources:**
- SQLAlchemy 2.0 async documentation
- Pydantic validation patterns
- PostgreSQL unique constraints

---

## Notes for Implementer

**Recommended Sub-Agent:** **Database Expert** + **TDD Implementor**

**Why These Agents:**
- Database Expert handles schema design, constraints, and migration
- TDD Implementor writes tests first, ensures behavior correctness

**Key Patterns to Follow:**
1. Use SQLAlchemy 2.0 async patterns (`select()`, `AsyncSession`)
2. Always filter by `tenant_key` (multi-tenant isolation)
3. Use Pydantic for request/response validation
4. Follow existing CRUD patterns in `api/endpoints/projects/crud.py`
5. Lazy seeding pattern: check-then-seed on first access

**Common Pitfalls to Avoid:**
- Don't seed during install (lazy seeding only)
- Don't forget tenant_key filtering
- Don't allow deletion of types with projects assigned
- Don't use synchronous SQLAlchemy patterns (use async/await)
- Don't hardcode paths (use `pathlib.Path()`)

**Pro Tips:**
- Use Serena MCP tools to explore existing patterns before coding
- Test migration with both fresh and existing databases
- Use `EXPLAIN ANALYZE` to verify index usage on queries
- Consider adding database indexes if queries become slow

---

## Progress Updates

### 2026-01-22 - Initial Handover Created
**Status:** Ready for Implementation
**Next Steps:**
1. Assign to Database Expert agent
2. Create test database for development
3. Begin Phase 1 (Database Schema)
