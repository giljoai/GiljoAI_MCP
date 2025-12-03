# Handover 0071: Simplified Project State Management

**Date**: 2025-10-28
**Status**: Specification
**Dependencies**: Handover 0050, 0050b, 0070
**Related**: `handovers/Projectlist flow.md`

## Overview

Simplification of project state management by removing the pause/resume feature and consolidating to a cleaner state machine. This handover addresses gaps identified between the specification in "Projectlist flow.md" and the current implementation.

## User Decisions

Based on discussion and review of the specification document:

1. **Remove Pause/Resume** - Eliminate pause/resume complexity in favor of simpler inactive state
2. **Deactivate = Inactive** - Single deactivation operation that frees up the active project slot
3. **View Deleted Scoping** - Filter deleted projects to show only those from the active product
4. **Application-Level Constraint** - Enforce "single active project per product" at application level (not database)

## Current State Analysis

### What's Working (80%+ complete)
- ✅ Single active product per tenant (Handover 0050)
- ✅ Cascade deactivation of projects when switching products (Handover 0050b)
- ✅ Soft delete with 10-day recovery window (Handover 0070)
- ✅ Product-scoped tenancy

### Gaps Identified
- ❌ Pause/resume adds unnecessary complexity
- ❌ No "deactivate" project endpoint
- ❌ View Deleted shows all tenant's deleted projects (not product-scoped)
- ❌ Missing application validation for "single active project per product"
- ❌ "Archived" status is redundant and unused

## Simplified State Machine

### Project States

**Active States:**
- **active** - One per product. Currently being worked on by agents/orchestrator
- **inactive** - Not currently worked on. Can be reactivated. Frees up active slot
- **completed** - Finished successfully. Historical record
- **cancelled** - Abandoned. Historical record
- **deleted** - Soft deleted. 10-day recovery window (Handover 0070)

### State Transitions

```
inactive ──(activate)──> active
   ↑                        │
   │                        ├──(deactivate)──> inactive
   │                        ├──(complete)────> completed
   │                        ├──(cancel)──────> cancelled
   │                        └──(delete)──────> deleted
   │
   └──────(activate)─────── inactive
   └──────(complete)─────── completed
   └──────(cancel)───────── cancelled
   └──────(delete)───────── deleted

deleted ──(restore within 10 days)──> inactive
deleted ──(after 10 days)──────────> [PURGED]
```

### Removed States
- ~~**paused**~~ - Removed. Use "inactive" instead
- ~~**archived**~~ - Removed. Redundant with "inactive"

## Implementation Requirements

### 1. Remove Pause/Resume Feature

**Backend:**
- Remove pause/resume logic from `src/giljo_mcp/orchestrator.py`:
  - Delete `pause_project()` method (line 696)
  - Delete `resume_project()` method (line 726)
  - Remove any pause-specific context monitoring logic

- Update `api/endpoints/products.py` product switch cascade (line 728):
  ```python
  # OLD: proj.status = "paused"
  # NEW:
  proj.status = "inactive"
  logger.info(f"[Handover 0071] Deactivating project '{proj.name}' (parent product deactivated)")
  ```

**Frontend:**
- `frontend/src/views/ProjectsView.vue`:
  - Remove 'pause' action handler (line 644-646)
  - Remove 'resume' action handler (line 647-649)
  - Remove "Paused" status filter chip
  - Remove paused project count display

- `frontend/src/components/StatusBadge.vue`:
  - Remove 'paused' status configuration
  - Remove 'resume' action from statusActions
  - Remove pause-specific icons/colors

- `frontend/src/stores/projects.js`:
  - Remove `pauseProject()` method
  - Remove `resumeProject()` method (if it exists)

- `frontend/src/utils/constants.js`:
  - Remove `PAUSED: 'paused'` constant

### 2. Add Deactivate Project Feature

**Backend Endpoint:**
Create new endpoint in `api/endpoints/projects.py`:

```python
@router.post("/{project_id}/deactivate", response_model=ProjectResponse)
async def deactivate_project(
    project_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Deactivate a project (Handover 0071)

    Sets project status to 'inactive', freeing up the active project slot.
    This allows another project to be activated for this product.

    Rules:
    - Can deactivate from 'active' status only
    - Frees up active project slot (single active per product)
    - Does NOT delete missions/agents/context (keep for reactivation)
    """
    from api.app import state

    logger = logging.getLogger(__name__)

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        async with state.db_manager.get_session_async() as db:
            # Get project
            result = await db.execute(
                select(Project).where(
                    Project.id == project_id,
                    Project.tenant_key == current_user.tenant_key
                )
            )
            project = result.scalar_one_or_none()

            if not project:
                raise HTTPException(status_code=404, detail="Project not found")

            if project.status != "active":
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot deactivate project with status '{project.status}'"
                )

            # Deactivate
            project.status = "inactive"
            await db.commit()
            await db.refresh(project)

            logger.info(f"[Handover 0071] Project '{project.name}' deactivated")

            return ProjectResponse.from_orm(project)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to deactivate project: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
```

**Frontend:**
- Add `deactivateProject()` method to `frontend/src/stores/projects.js`:
  ```javascript
  async function deactivateProject(id) {
    loading.value = true
    error.value = null
    try {
      await api.projects.deactivate(id)
      await fetchProjects()
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }
  ```

- Add API method to `frontend/src/services/api.js`:
  ```javascript
  projects: {
    // ...existing methods...
    deactivate: (id) => apiClient.post(`/api/v1/projects/${id}/deactivate`),
  }
  ```

- Update `frontend/src/views/ProjectsView.vue` action handler:
  ```javascript
  case 'deactivate':
    await projectStore.deactivateProject(projectId)
    break
  ```

- Update `frontend/src/components/StatusBadge.vue`:
  ```javascript
  const statusActions = {
    active: ['deactivate', 'complete', 'cancel', 'delete'],
    inactive: ['activate', 'delete'],
    completed: ['reopen', 'delete'],
    cancelled: ['reopen', 'delete']
  }

  const actionConfig = {
    deactivate: {
      label: 'Deactivate',
      icon: 'mdi-pause-circle-outline',
      newStatus: 'inactive',
      destructive: false,
      requiresConfirm: true
    }
  }
  ```

### 3. Application-Level Single Active Project Enforcement

Add validation in `api/endpoints/projects.py` activation endpoint (around line 429):

```python
async def activate_project(project_id: str, ...):
    """Activate a project (Handover 0071 validation)"""

    # ... existing product validation ...

    # Handover 0071: Enforce single active project per product
    active_check = await db.execute(
        select(Project).where(
            Project.product_id == project.product_id,
            Project.status == "active",
            Project.id != project_id
        )
    )
    existing_active = active_check.scalar_one_or_none()

    if existing_active:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Another project ('{existing_active.name}') is already active "
                f"for this product. Please deactivate it first."
            )
        )

    # Proceed with activation
    project.status = "active"
    await db.commit()
```

### 4. Filter View Deleted by Active Product

Update `api/endpoints/projects.py` deleted endpoint (line 289):

```python
@router.get("/deleted", response_model=list[DeletedProjectResponse])
async def list_deleted_projects(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    List deleted projects for the ACTIVE product only (Handover 0071).

    Returns empty list if no active product.
    """
    from api.app import state
    from src.giljo_mcp.models import Project, Product

    # ... existing setup ...

    async with state.db_manager.get_session_async() as session:
        # Get active product first
        active_product_result = await session.execute(
            select(Product).where(
                Product.tenant_key == current_user.tenant_key,
                Product.is_active == True
            )
        )
        active_product = active_product_result.scalar_one_or_none()

        if not active_product:
            logger.info(f"[Handover 0071] No active product - returning empty deleted list")
            return []

        # Query deleted projects ONLY for active product
        stmt = select(Project, Product).outerjoin(
            Product, Project.product_id == Product.id
        ).where(
            Project.tenant_key == current_user.tenant_key,
            Project.product_id == active_product.id,  # NEW: Product filter
            Project.deleted_at.isnot(None)
        ).order_by(Project.deleted_at.desc())

        # ... rest of existing logic ...

        logger.info(
            f"[Handover 0071] Retrieved {len(deleted_projects)} deleted projects "
            f"for active product '{active_product.name}'"
        )
        return deleted_projects
```

### 5. Remove "Archived" Status

**Backend:**
- No changes needed (archived never implemented)

**Frontend:**
- `frontend/src/components/StatusBadge.vue`:
  - Remove 'archived' from validator (line 136)
  - Remove archived status config (lines 184-187)
  - Remove 'archive' action config (lines 243-247)
  - Remove archived from statusActions (line 282)
  - Remove archive confirmation text (lines 321-323)

- `frontend/src/utils/constants.js`:
  - Remove `ARCHIVED: 'archived'` constant

### 6. Update Frontend Status Displays

**ProjectsView.vue:**
- Update status filter options to remove "Paused" and "Archived"
- Update status counts to exclude paused/archived
- Ensure "Inactive" filter chip is present and functional

**StatusBadge.vue:**
- Ensure "inactive" status has proper styling:
  ```javascript
  inactive: {
    label: 'Inactive',
    color: 'grey',
    icon: 'mdi-stop-circle-outline'
  }
  ```

## Data Preservation Rules

### Deactivate (Active → Inactive)
**Preserves:**
- Project metadata (name, description, dates)
- Mission created by orchestrator
- Assigned agents
- All context generated for the project
- MCP communication history

**Effect:**
- Frees up active project slot
- Can be reactivated later
- Agents remain assigned but inactive

### Delete (Any → Deleted)
**Soft Delete (0-10 days):**
- Sets `deleted_at` timestamp
- Status = 'deleted'
- Appears in "View Deleted" for active product
- Can be restored

**Hard Delete (After 10 days):**
- Permanent deletion
- Cascades to missions, agent assignments, context, MCP history

### Complete (Active → Completed)
**Preserves:**
- All project data
- Historical record of completion
- Missions, agents, context, MCP history

**Effect:**
- Frees up active project slot
- Can be reopened if needed

### Cancel (Active/Inactive → Cancelled)
**Preserves:**
- All project data
- Historical record
- Missions, agents, context

**Effect:**
- Frees up active project slot
- Can be reopened if needed

## Multi-Tenant Isolation

All operations maintain strict tenant isolation:
- Projects belong to tenant via product relationship
- Deleted projects filtered by active product (which is tenant-scoped)
- No cross-tenant project visibility

## UI/UX Changes

### Projects Page

**Status Filter Chips:**
- Active (count)
- Inactive (count)
- Completed (count)
- Cancelled (count)
- ~~Paused (removed)~~
- ~~Archived (removed)~~

**View Deleted Button:**
- Shows count for active product only
- Opens modal with deleted projects from active product
- Disabled if no active product selected

**Action Buttons:**
- Active projects: Deactivate, Complete, Cancel, Delete
- Inactive projects: Activate, Delete
- Completed projects: Reopen, Delete
- Cancelled projects: Reopen, Delete

### Status Badge Colors

| Status | Color | Icon |
|--------|-------|------|
| active | success (green) | mdi-play-circle |
| inactive | grey | mdi-stop-circle-outline |
| completed | info (blue) | mdi-check-circle |
| cancelled | warning (orange) | mdi-cancel |
| deleted | error (red) | mdi-delete |

## Testing Checklist

### Backend Tests
- [ ] Deactivate endpoint: Only works on active projects
- [ ] Deactivate endpoint: Frees up active slot
- [ ] Activate validation: Rejects if another project active for product
- [ ] Activate validation: Clear error message
- [ ] View Deleted: Returns empty list when no active product
- [ ] View Deleted: Filters by active product correctly
- [ ] Product switch: Cascades inactive (not paused) to projects

### Frontend Tests
- [ ] Deactivate button appears on active projects
- [ ] Deactivate action updates UI correctly
- [ ] Status filter chips exclude paused/archived
- [ ] View Deleted count matches active product's deleted projects
- [ ] Inactive status badge displays correctly
- [ ] Cannot activate second project (validation error shown)

### Integration Tests
- [ ] Product switch → Projects become inactive
- [ ] Deactivate project → Can activate different project
- [ ] Delete project from inactive state → Appears in View Deleted
- [ ] Restore deleted project → Returns to inactive state
- [ ] Complete active project → Frees slot for new active project

## Migration Notes

**Existing Paused Projects:**
Run migration to convert paused → inactive:

```sql
-- Convert all paused projects to inactive
UPDATE projects
SET status = 'inactive'
WHERE status = 'paused';
```

**Existing Archived Projects:**
No action needed (archived was never implemented in database)

## Files Modified

### Backend
- `api/endpoints/projects.py` - Add deactivate endpoint, update activation validation, filter deleted by product
- `api/endpoints/products.py` - Update cascade logic (paused → inactive)
- `src/giljo_mcp/orchestrator.py` - Remove pause/resume methods

### Frontend
- `frontend/src/views/ProjectsView.vue` - Remove pause/resume actions, add deactivate
- `frontend/src/components/StatusBadge.vue` - Remove pause/archive, update actions
- `frontend/src/stores/projects.js` - Remove pause methods, add deactivate
- `frontend/src/services/api.js` - Add deactivate endpoint
- `frontend/src/utils/constants.js` - Remove PAUSED, ARCHIVED constants

## Success Criteria

1. ✅ Pause/resume feature completely removed
2. ✅ Deactivate works and frees up active slot
3. ✅ Application validates single active project per product
4. ✅ View Deleted shows only active product's deleted projects
5. ✅ Product switch cascades inactive (not paused)
6. ✅ Archived status removed from codebase
7. ✅ All existing tests updated and passing
8. ✅ No references to "paused" or "archived" in code

## Related Documentation

- **Handover 0050**: Single Active Product Architecture
- **Handover 0050b**: Single Active Project Per Product
- **Handover 0070**: Project Soft Delete with Recovery
- **Specification**: `handovers/Projectlist flow.md`

## Notes

- This handover simplifies the state machine from 6 states to 5 states
- Removes orchestrator complexity around pause/resume state restoration
- Maintains backward compatibility: paused → inactive migration is straightforward
- Application-level validation chosen over database constraint for flexibility
- View Deleted scoping improves UX by reducing clutter

---

**Implementation Status**: Not Started
**Estimated Effort**: 4-6 hours
**Priority**: Medium (Quality of Life improvement)