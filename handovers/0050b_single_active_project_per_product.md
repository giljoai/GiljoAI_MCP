---
Handover 0050b: Single Active Project Per Product Architecture
Date: 2025-10-27
Status: Ready for Implementation
Priority: HIGH
Complexity: MEDIUM
Duration: 1-2 days
Parent: Handover 0050 (Single Active Product Architecture)
---

# Executive Summary

Building on **Handover 0050** (single active product per tenant), this handover extends the single-active architecture to the **project level**: only ONE project can be active per product at any time.

**Key Principle**: Mission-based orchestration operates on a single product → single project context. Multiple active projects would create the same context confusion and token budget issues that Handover 0050 solved at the product level.

This handover implements:
1. Database constraint: One active project per product
2. Cascade deactivation: Switching products deactivates all projects under previous product
3. Enhanced warning dialog: Shows project impact when switching products
4. Product-scoped project views: Only show projects for active product

---

# Problem Statement

## Current State

**Database Evidence:**
```sql
-- Current state: Multiple active projects exist simultaneously
SELECT tenant_key, COUNT(*) as active_count
FROM projects
WHERE status = 'active'
GROUP BY tenant_key;

-- Result: tenant has 2 active projects (context confusion!)
```

**Architecture Gap:**
- Products already have single-active enforcement (Handover 0050)
- Projects do NOT have single-active enforcement
- Projects are NOT filtered by active product in UI
- Switching products does NOT cascade to deactivate projects

## Risks Without This Implementation

1. **Context Confusion**: Multiple active projects create ambiguous agent context
2. **Token Budget Chaos**: Which project's context budget applies?
3. **Mission Integrity**: Agents receive mixed project contexts
4. **User Mental Model**: Which project is "really" active?
5. **Inconsistent Architecture**: Products are single-active, projects are not

---

# Architectural Decision

## Decision Context

Handover 0050 established single active product per tenant. This handover extends that pattern to projects, creating a consistent two-level hierarchy:

```
Tenant
  └── ONE Active Product
        └── ONE Active Project
              └── Multiple Agents
```

## Options Considered

### Option A: Single Active Project Per Product (SELECTED)

**Architecture**:
- Only ONE project can have `status='active'` per product
- Activating a project deactivates all others under same product
- Switching products deactivates all projects under previous product
- Projects view filters to show only active product's projects

**Enforcement**:
- Database: Partial unique index on (product_id, status='active')
- API: Cascade deactivation when switching products
- Frontend: Product-scoped project filtering

**User Experience**:
```
User switches from Product A → Product B
  → Warning: "This will deactivate Product A and its 2 active projects"
  → User confirms
  → Product A deactivated
  → All projects under Product A deactivated
  → Product B activated
  → Projects view shows only Product B's projects
```

**Pros**:
- Consistent with Handover 0050 pattern
- Clean mental model (one focus at all levels)
- Prevents context confusion
- Simple implementation (reuse 0050 patterns)
- No breaking changes

**Cons**:
- Cannot work on multiple projects simultaneously
- Must switch products to access different project

**Complexity**: MEDIUM
**Implementation Time**: 1-2 days
**Risk**: LOW (established pattern)

---

### Option B: Multiple Active Projects (with Priority)

**Architecture**:
- Multiple projects can be active per product
- Add priority field (1-10) to projects
- Highest priority project is "primary" for agent context

**Pros**:
- Flexibility to monitor multiple projects

**Cons**:
- Confusing mental model (which is "really" active?)
- Token budget allocation complexity
- Violates Handover 0050 architecture principles
- Requires additional UI complexity

**Complexity**: HIGH
**Implementation Time**: 3-5 days
**Risk**: MEDIUM

---

### Option C: No Constraint (Status Quo)

**Architecture**:
- Leave as-is, no constraints

**Pros**:
- No implementation effort

**Cons**:
- Context confusion continues
- Architectural inconsistency with 0050
- Risk of token budget issues
- Poor user experience

**Rejected**: Does not solve the problem

---

## Selected Option: A (Single Active Project Per Product)

**Decision**: Implement single active project per product with cascade deactivation.

### Rationale

#### 1. Architecture Consistency
- Handover 0050 established single-active pattern for products
- Projects are children of products
- Extending pattern creates consistent hierarchy
- Mental model: ONE active entity at each level

#### 2. Context Clarity
- Agents operate on single project context
- Clear token budget (project-specific)
- No ambiguity in mission assignment
- Focused orchestration

#### 3. User Mental Model
User thinks: "What am I working on?"
- Answer: One product → One project → Clear focus
- No confusion about which project is "really" active

#### 4. Implementation Simplicity
- Reuse Handover 0050 patterns
- Same defense-in-depth approach
- Proven migration strategy
- Low risk

---

# Implementation Plan

## Overview

This implementation mirrors Handover 0050's structure with 5 phases. Each phase is independently testable.

**Total Estimated Lines of Code**: ~350 lines across 6 files (5 modified, 1 new migration)

---

## Phase 1: Database Defense-in-Depth (4 hours)

### Objective
Ensure only one project can be active per product at database level.

### Implementation Steps

#### Step 1.1: Create Migration File

**File**: `migrations/versions/20251027_single_active_project_per_product.py`

```python
"""single_active_project_per_product

Handover 0050b: Enforce single active project per product architecture.

This migration implements:
1. Resolves any existing multi-active-project conflicts (keeps most recent)
2. Adds partial unique index to prevent multiple active projects per product
3. Ensures database-level atomicity for project activation

Revision ID: 20251027_single_proj
Revises: 20251027_single_active
Create Date: 2025-10-27 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = '20251027_single_proj'
down_revision: Union[str, None] = '20251027_single_active'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add single active project enforcement.

    Strategy:
    1. Find products with multiple active projects
    2. For each conflict, keep most recently updated project, deactivate others
    3. Add partial unique index to prevent future conflicts
    """

    # Get database connection
    connection = op.get_bind()

    print("\n[Handover 0050b Migration] Starting single active project per product enforcement...\n")

    # Step 1: Find conflicts (products with multiple active projects)
    conflicts_query = text("""
        SELECT product_id, COUNT(*) as active_count
        FROM projects
        WHERE status = 'active' AND product_id IS NOT NULL
        GROUP BY product_id
        HAVING COUNT(*) > 1
    """)

    conflicts = connection.execute(conflicts_query).fetchall()

    if conflicts:
        print(f"[Handover 0050b Migration] Found {len(conflicts)} products with multiple active projects")

        for product_id, active_count in conflicts:
            print(f"[Handover 0050b Migration] Product {product_id}: {active_count} active projects - resolving...")

            # Get all active projects for this product, ordered by updated_at DESC
            projects_query = text("""
                SELECT id, name, updated_at
                FROM projects
                WHERE product_id = :product_id AND status = 'active'
                ORDER BY updated_at DESC NULLS LAST
            """)

            projects = connection.execute(projects_query, {"product_id": product_id}).fetchall()

            if projects:
                # Keep the most recently updated project
                keep_project = projects[0]
                print(f"[Handover 0050b Migration]   Keeping: {keep_project.name} (most recent)")

                # Deactivate all others
                for project in projects[1:]:
                    deactivate_query = text("""
                        UPDATE projects
                        SET status = 'paused'
                        WHERE id = :project_id
                    """)
                    connection.execute(deactivate_query, {"project_id": project.id})
                    print(f"[Handover 0050b Migration]   Deactivated: {project.name}")
    else:
        print("[Handover 0050b Migration] No conflicts found - all products have 0 or 1 active projects")

    print("\n[Handover 0050b Migration] Adding partial unique index for single active project enforcement...")

    # Step 2: Create partial unique index
    op.create_index(
        'idx_project_single_active_per_product',
        'projects',
        ['product_id'],
        unique=True,
        postgresql_where=text("status = 'active'")
    )

    print("[Handover 0050b Migration] Migration complete - single active project enforcement enabled\n")


def downgrade() -> None:
    """
    Remove single active project enforcement.

    WARNING: This allows multiple active projects per product again.
    """
    print("\n[Handover 0050b Migration] Removing single active project enforcement...")

    op.drop_index(
        'idx_project_single_active_per_product',
        table_name='projects',
        postgresql_where=text("status = 'active'")
    )

    print("[Handover 0050b Migration] Downgrade complete - constraint removed\n")
```

**Key Features**:
- Auto-resolves conflicts (keeps most recent, deactivates others)
- Idempotent (safe to run multiple times)
- Detailed logging
- Rollback safe

---

## Phase 2: Backend API Enhancements (3 hours)

### Objective
Update product activation endpoint to cascade project deactivation.

### Implementation Steps

#### Step 2.1: Enhance Product Activation Response

**File**: `api/endpoints/products.py`

**Modify**: `activate_product()` function

**Add after line 626 (before commit)**:
```python
# Handover 0050b: Deactivate all projects under the previous active product
if current_active:
    from src.giljo_mcp.models import Project

    # Get all active projects under previous product
    prev_projects_query = select(Project).where(
        Project.product_id == current_active["id"],
        Project.status == "active"
    )
    prev_projects_result = await db.execute(prev_projects_query)
    prev_active_projects = prev_projects_result.scalars().all()

    # Deactivate them
    for proj in prev_active_projects:
        proj.status = "paused"
        logger.info(f"[0050b] Deactivating project '{proj.name}' (parent product deactivated)")
```

**Update Response Model** (line 62):
```python
class ActiveProductInfo(BaseModel):
    """Minimal active product info for efficient responses"""
    id: str
    name: str
    description: Optional[str]
    activated_at: datetime
    active_projects_count: int  # NEW FIELD (0050b)
```

**Update Helper Function** `get_active_product_info()` (line 610):
```python
async def get_active_product_info(db, tenant_key: str) -> Optional[Dict[str, Any]]:
    """Get active product summary info for tenant (<10ms)"""
    from sqlalchemy import func, select
    from src.giljo_mcp.models import Product, Project

    # Find currently active product
    result = await db.execute(
        select(Product)
        .where(
            Product.tenant_key == tenant_key,
            Product.is_active == True
        )
    )
    active_product = result.scalar_one_or_none()

    if not active_product:
        return None

    # Count active projects (Handover 0050b)
    count_result = await db.execute(
        select(func.count(Project.id))
        .where(
            Project.product_id == active_product.id,
            Project.status == 'active'  # Changed from Project.is_active
        )
    )
    active_projects_count = count_result.scalar() or 0

    return {
        "id": str(active_product.id),
        "name": active_product.name,
        "description": active_product.description,
        "activated_at": active_product.updated_at or active_product.created_at,
        "active_projects_count": active_projects_count  # NEW
    }
```

---

#### Step 2.2: Add Project Count to Projects Endpoint

**File**: `api/endpoints/projects.py`

**No changes needed** - existing validation from Phase 4 of 0050 already prevents activating projects with inactive parent product.

---

## Phase 3: Frontend Enhancements (4 hours)

### Objective
1. Filter projects by active product
2. Enhance warning dialog to show project deactivation

### Implementation Steps

#### Step 3.1: Update Warning Dialog

**File**: `frontend/src/components/products/ActivationWarningDialog.vue`

**Find** (around line 30):
```vue
<v-alert type="info" variant="tonal" class="mb-4">
  Activating <strong>{{ newProductName }}</strong> will deactivate
  <strong>{{ previousProduct.name }}</strong>.
</v-alert>
```

**Replace With**:
```vue
<v-alert type="info" variant="tonal" class="mb-4">
  Activating <strong>{{ newProductName }}</strong> will deactivate
  <strong>{{ previousProduct.name }}</strong>.
</v-alert>

<!-- Handover 0050b: Show project deactivation impact -->
<v-alert
  v-if="previousProduct.active_projects_count > 0"
  type="warning"
  variant="tonal"
  class="mb-4"
>
  <div class="font-weight-bold mb-2">Project Impact:</div>
  <strong>{{ previousProduct.active_projects_count }}</strong>
  active project{{ previousProduct.active_projects_count > 1 ? 's' : '' }}
  under <strong>{{ previousProduct.name }}</strong> will be paused.

  <div class="text-caption mt-2">
    Only one project can be active at a time. You can reactivate
    projects after switching back to this product.
  </div>
</v-alert>
```

---

#### Step 3.2: Add Product Filtering to Projects View

**File**: `frontend/src/views/ProjectsView.vue`

**Add Import** (top of script):
```javascript
import { useProductStore } from '@/stores/products'
```

**Add State**:
```javascript
const productStore = useProductStore()
const activeProduct = computed(() => productStore.activeProduct)
```

**Add Computed Filter**:
```javascript
// Handover 0050b: Filter projects by active product
const filteredProjects = computed(() => {
  if (!activeProduct.value) {
    // No active product - show warning message
    return []
  }

  // Show only projects for active product
  return projects.value.filter(p => p.product_id === activeProduct.value.id)
})
```

**Update Template** - Replace `v-for="item in projects"` with:
```vue
<!-- Handover 0050b: Show only active product's projects -->
<v-alert
  v-if="!activeProduct"
  type="info"
  variant="tonal"
  class="ma-4"
>
  No active product selected. Please activate a product to view its projects.
</v-alert>

<v-data-table
  v-else
  :items="filteredProjects"
  :headers="headers"
  ...
>
```

**Add Product Context Header**:
```vue
<!-- Add above data table -->
<v-toolbar flat color="transparent" class="mb-4">
  <v-toolbar-title>
    Projects for: <strong>{{ activeProduct?.name || 'No Active Product' }}</strong>
  </v-toolbar-title>
  <v-spacer />
  <v-chip
    v-if="filteredProjects.length > 0"
    color="primary"
    variant="flat"
    size="small"
  >
    {{ filteredProjects.length }} project{{ filteredProjects.length !== 1 ? 's' : '' }}
  </v-chip>
</v-toolbar>
```

---

## Phase 4: Testing (2 hours)

### Unit Tests

**File**: `tests/unit/test_single_active_project.py`

```python
"""
Unit tests for Handover 0050b: Single Active Project Per Product
"""
import pytest
from src.giljo_mcp.models import Product, Project

@pytest.mark.asyncio
async def test_only_one_active_project_per_product(db_session, test_tenant):
    """Database constraint prevents multiple active projects per product"""

    # Create product
    product = Product(
        tenant_key=test_tenant,
        name="Test Product",
        is_active=True
    )
    db_session.add(product)
    await db_session.commit()

    # Create first active project - should succeed
    project1 = Project(
        tenant_key=test_tenant,
        product_id=product.id,
        name="Project 1",
        mission="Mission 1",
        status="active"
    )
    db_session.add(project1)
    await db_session.commit()

    # Try to create second active project - should fail with constraint
    project2 = Project(
        tenant_key=test_tenant,
        product_id=product.id,
        name="Project 2",
        mission="Mission 2",
        status="active"
    )
    db_session.add(project2)

    with pytest.raises(Exception) as exc_info:
        await db_session.commit()

    assert "idx_project_single_active_per_product" in str(exc_info.value)


@pytest.mark.asyncio
async def test_multiple_paused_projects_allowed(db_session, test_tenant):
    """Multiple paused projects are allowed per product"""

    product = Product(
        tenant_key=test_tenant,
        name="Test Product",
        is_active=True
    )
    db_session.add(product)
    await db_session.commit()

    # Create multiple paused projects - should succeed
    for i in range(3):
        project = Project(
            tenant_key=test_tenant,
            product_id=product.id,
            name=f"Project {i}",
            mission=f"Mission {i}",
            status="paused"
        )
        db_session.add(project)

    await db_session.commit()  # Should succeed


@pytest.mark.asyncio
async def test_product_switch_deactivates_projects(api_client, test_tenant, test_user):
    """Switching products deactivates previous product's projects"""

    # Create Product A with active project
    # Create Product B
    # Activate Product B
    # Verify Product A's project is deactivated

    # ... implementation
```

### Integration Tests

**File**: `tests/integration/test_product_project_cascade.py`

Test scenarios:
1. Switch products → verify project deactivation
2. Activate product with no projects → no errors
3. Delete product → cascades to projects
4. Multi-tenant isolation

---

## Phase 5: Documentation (1 hour)

### Documentation Updates

**Files to Update**:

1. **CLAUDE.md**:
```markdown
**Single Active Project Per Product (Handover 0050b)**:
- ✅ Only ONE project active per product at any time
- ✅ Database constraint via partial unique index
- ✅ Cascade deactivation when switching products
- ✅ Product-scoped project filtering in UI
```

2. **Update** `handovers/0050_IMPLEMENTATION_STATUS.md`:
   - Add note referencing 0050b extension

3. **Create** `handovers/0050b_IMPLEMENTATION_STATUS.md`:
   - Track progress through 5 phases

---

# Files to Modify

## Backend (Python)

1. **migrations/versions/20251027_single_active_project_per_product.py** (NEW - 150 lines)
   - Auto-resolve conflicts
   - Add partial unique index

2. **api/endpoints/products.py** (+50 lines)
   - Cascade project deactivation
   - Add active_projects_count to response

## Frontend (Vue/JavaScript)

3. **frontend/src/components/products/ActivationWarningDialog.vue** (+20 lines)
   - Show project deactivation impact

4. **frontend/src/views/ProjectsView.vue** (+80 lines)
   - Filter projects by active product
   - Show product context header
   - Add "no active product" message

## Tests (Python)

5. **tests/unit/test_single_active_project.py** (NEW - 100 lines)
6. **tests/integration/test_product_project_cascade.py** (NEW - 120 lines)

**Total**: ~520 lines across 6 files

---

# Success Criteria

## Functional Requirements
- ✅ Only one project can be active per product (database enforced)
- ✅ Switching products deactivates previous product's projects
- ✅ Warning dialog shows project impact
- ✅ Projects view filtered by active product
- ✅ Multi-tenant isolation maintained

## User Experience Requirements
- ✅ Clear warning before product switch
- ✅ Project count visible in warning
- ✅ Product context visible in projects view
- ✅ "No active product" message when none selected

## Technical Requirements
- ✅ Database constraint prevents violations
- ✅ Migration auto-resolves conflicts
- ✅ Cascade deactivation in API
- ✅ No breaking changes
- ✅ Test coverage >80%

---

# Related Handovers

- **Handover 0050**: Single Active Product Architecture (PARENT - COMPLETE)
  - Established single-active pattern
  - This handover extends pattern to projects

---

# Risk Assessment

**Complexity**: MEDIUM
- Reuses proven patterns from 0050
- Clear implementation path
- Well-understood requirements

**Risk**: LOW
- No breaking changes
- Additive only
- Migration auto-resolves conflicts
- Independent rollback possible

**Performance Impact**: Minimal
- Single additional query per product switch
- Efficient partial unique index

---

# Timeline Estimate

**Day 1**:
- Phase 1: Database (2 hours)
- Phase 2: Backend API (3 hours)

**Day 2**:
- Phase 3: Frontend (4 hours)
- Phase 4: Testing (2 hours)
- Phase 5: Documentation (1 hour)

**Total**: 12 hours (1.5 days)

---

# Sign-Off Checklist

Before marking this handover complete:
- [ ] All 5 phases implemented
- [ ] Database migration tested
- [ ] Product switch cascades to projects
- [ ] Warning dialog shows project count
- [ ] Projects filtered by active product
- [ ] All tests passing (>80% coverage)
- [ ] Documentation updated
- [ ] Manual UAT passed
- [ ] No console errors

---

**Decision Recorded By**: System Architect
**Date**: 2025-10-27
**Parent Handover**: 0050 (Single Active Product Architecture)

---

**End of Handover 0050b**
