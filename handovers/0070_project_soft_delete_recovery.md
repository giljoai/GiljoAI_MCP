# Handover 0070: Project Soft Delete with Recovery UI

**Date**: 2025-10-27
**Status**: Planning Complete - Ready for Implementation
**Priority**: High - User Experience Enhancement
**Complexity**: Medium (5-8 files, ~300-400 lines)

---

## Executive Summary

Implement production-grade soft delete for projects with 10-day recovery window and user-facing recovery UI. Current DELETE endpoint "closes" projects (status change) causing user confusion. New system provides true delete UX with safety net.

**Current Problem**:
- Frontend "Delete" button calls backend DELETE endpoint
- Backend DELETE actually "closes" project (status="closed")
- Requires `summary` parameter (422 error without it)
- User confusion: "I deleted it but it's still there?"
- No recovery mechanism

**Solution**:
- Soft delete: Set `status="deleted"` + `deleted_at` timestamp
- Filter deleted projects from all views (invisible to user)
- Recovery UI in Settings → Database tab
- Auto-purge after 10 days
- Clear user messaging about recovery options

---

## Architecture Design

### Database Layer

**Migration**: Add `deleted_at` column to projects table
```sql
ALTER TABLE projects ADD COLUMN deleted_at TIMESTAMP NULL;
CREATE INDEX idx_projects_deleted_at ON projects(deleted_at) WHERE deleted_at IS NOT NULL;
```

**Query Pattern**: All project queries filter deleted projects
```sql
-- Before
SELECT * FROM projects WHERE tenant_key = ?

-- After
SELECT * FROM projects
WHERE tenant_key = ?
  AND (status != 'deleted' OR deleted_at IS NULL)
```

### API Layer

**DELETE Endpoint** (`/api/v1/projects/{project_id}`):
- Remove `summary` parameter requirement
- Set `status="deleted"`
- Set `deleted_at=NOW()`
- Broadcast WebSocket update
- Return success with recovery info

**New RESTORE Endpoint** (`POST /api/v1/projects/{project_id}/restore`):
- Verify project exists and is deleted
- Set `status="inactive"` (safe default)
- Set `deleted_at=NULL`
- Broadcast WebSocket update
- Return restored project data

**New GET DELETED Endpoint** (`GET /api/v1/projects/deleted`):
- Return all deleted projects for tenant
- Include days until purge (calculated from `deleted_at`)
- Filter by `deleted_at IS NOT NULL`
- Order by `deleted_at DESC`

**Purge Logic** (Background task or manual):
- Query: `deleted_at < NOW() - INTERVAL '10 days'`
- Cascade delete: agents, tasks, messages
- Log purge actions
- Run daily at 2 AM (or on-demand)

### Frontend Layer

**ProjectsView.vue**: Update delete flow
1. Confirmation dialog: "Delete project 'X'?"
2. On confirm → API DELETE call
3. Success modal:
   ```
   Project deleted from view

   Will be permanently purged in 10 days.
   To recover: Settings → Database → Deleted Projects

   [OK]
   ```
4. Remove from list immediately

**UserSettings.vue**: Add Database tab
- New tab: "Database" (next to API Keys, Integrations)
- Section: "Deleted Projects"
- Table columns:
  - Project Name
  - Product (parent product name)
  - Deleted Date (formatted)
  - Purge In (countdown: "9 days")
  - Actions: [Restore] button
- Empty state: "No deleted projects"
- Restore confirmation: "Restore project 'X'? It will return as inactive."

**projects.js store**: Add functions
```javascript
// Fetch deleted projects
async fetchDeletedProjects()

// Restore project
async restoreProject(projectId)
```

### Multi-Tenant Isolation

**Critical**: All queries filtered by tenant_key
- GET deleted projects: `WHERE tenant_key = ? AND deleted_at IS NOT NULL`
- Restore: Verify `tenant_key` matches authenticated user
- Purge: Only purge within tenant boundary

---

## Implementation Phases

### Phase 1: Database Migration (1 hour)
**Files**: 1 new migration

- [x] Create migration `20251027_project_soft_delete.py`
- [x] Add `deleted_at TIMESTAMP NULL` column
- [x] Add index on `deleted_at`
- [x] Test migration up/down
- [x] Verify no breaking changes to existing queries

### Phase 2: Backend API (3 hours)
**Files**: 1 modified (projects.py)

- [x] Modify DELETE endpoint:
  - Remove `summary` parameter requirement
  - Set `status="deleted"`, `deleted_at=NOW()`
  - Return success with recovery message
- [x] Add GET `/projects/deleted` endpoint:
  - Return deleted projects for tenant
  - Include purge countdown
- [x] Add POST `/projects/{id}/restore` endpoint:
  - Restore project to inactive status
  - Clear `deleted_at`
- [x] Update base project queries to filter deleted
- [x] Add purge function (manual trigger for now)

### Phase 3: Frontend Delete Flow (2 hours)
**Files**: 2 modified (ProjectsView.vue, projects.js)

- [x] Update delete confirmation dialog
- [x] Add success modal with recovery instructions
- [x] Update projects store with restore function
- [x] Test delete → modal → recovery message

### Phase 4: Recovery UI (3 hours)
**Files**: 1 modified (UserSettings.vue)

- [x] Add "Database" tab to UserSettings
- [x] Create deleted projects table component
- [x] Display project name, product, deleted date, countdown
- [x] Add [Restore] button with confirmation
- [x] Handle restore success/error
- [x] Test full recovery flow

### Phase 5: Query Filtering (2 hours)
**Files**: Review all project queries

- [x] Audit all `SELECT * FROM projects` queries
- [x] Add `WHERE (status != 'deleted' OR deleted_at IS NULL)` filter
- [x] Update filtered computed properties in frontend
- [x] Verify deleted projects invisible everywhere except recovery UI

### Phase 6: Testing (2 hours)

- [x] Unit tests: Soft delete, restore, purge logic
- [x] Integration tests: Full delete → restore flow
- [x] Multi-tenant isolation tests
- [x] Edge cases: Restore twice, delete deleted project
- [x] WebSocket broadcast verification

---

## Files to Modify

### New Files (1)
1. `migrations/versions/20251027_project_soft_delete.py` (~80 lines)

### Modified Files (4)
2. `api/endpoints/projects.py` (+150 lines)
   - Modify DELETE endpoint
   - Add GET /deleted endpoint
   - Add POST /restore endpoint
   - Add purge function
3. `frontend/src/views/ProjectsView.vue` (+80 lines)
   - Update delete confirmation
   - Add success modal
4. `frontend/src/views/UserSettings.vue` (+120 lines)
   - Add Database tab
   - Create deleted projects table
5. `frontend/src/stores/projects.js` (+40 lines)
   - Add fetchDeletedProjects()
   - Add restoreProject()

**Total**: ~470 lines across 5 files

---

## User Experience Flow

### Delete Flow
1. User clicks trash icon on project "MyProject"
2. Dialog: "Delete project 'MyProject'?" [Cancel] [Delete]
3. User clicks Delete
4. Modal appears:
   ```
   ✓ Project deleted from view

   MyProject will be permanently purged in 10 days.

   To recover before then:
   Settings → Database → Deleted Projects

   [OK]
   ```
5. Project disappears from list immediately
6. Dashboard stats update (one less project)

### Recovery Flow
1. User clicks avatar → Settings
2. Navigates to "Database" tab
3. Sees table:
   ```
   Deleted Projects

   Name        Product        Deleted        Purge In    Actions
   MyProject   TinyContacts   Oct 27, 2025   9 days      [Restore]
   OldTest     Test           Oct 20, 2025   2 days      [Restore]
   ```
4. User clicks [Restore] on "MyProject"
5. Confirmation: "Restore project 'MyProject'? It will return as inactive."
6. User confirms
7. Success message: "Project restored successfully"
8. Project appears back in Projects list (status: inactive)

### Purge Flow (Automated)
1. Daily task runs at 2 AM
2. Queries: `deleted_at < NOW() - INTERVAL '10 days'`
3. For each expired project:
   - Delete child agents
   - Delete child tasks
   - Delete child messages
   - Delete project record
4. Log: "Purged 3 projects older than 10 days"

---

## Technical Considerations

### Purge Strategy Options

**Option A: Background Task** (Recommended)
- Add to existing task scheduler (if exists)
- Or use simple Python `schedule` library
- Runs daily at 2 AM
- **Pro**: Automatic, reliable, true "10 days" promise
- **Con**: Requires background process

**Option B: On-Demand via API**
- Endpoint: `POST /admin/purge-deleted`
- Manual trigger (cron job or user action)
- **Pro**: Simple, no scheduler needed
- **Con**: Not truly automatic

**Option C: On Application Restart**
- Purge on `startup.py` launch
- **Pro**: Zero infrastructure
- **Con**: Unpredictable timing, might never run

**Recommendation**: Start with Option C (startup purge), upgrade to Option A later if needed.

### Cascade Delete Rules

When permanently purging project:
```
Project (deleted)
  ├── Agents (CASCADE DELETE)
  ├── Tasks (CASCADE DELETE)
  ├── Messages (CASCADE DELETE)
  └── Agent Jobs (CASCADE DELETE)
```

**Implementation**:
```python
# In purge function
async def purge_expired_projects():
    expired = await get_expired_deleted_projects()
    for project in expired:
        # Cascade delete
        await delete_project_agents(project.id)
        await delete_project_tasks(project.id)
        await delete_project_messages(project.id)
        await delete_project_jobs(project.id)

        # Finally delete project
        await session.delete(project)
        logger.info(f"Purged project {project.name} (id: {project.id})")
```

### Query Performance

**Index Strategy**:
```sql
-- For deleted projects query
CREATE INDEX idx_projects_deleted_at ON projects(deleted_at)
WHERE deleted_at IS NOT NULL;

-- For filtering non-deleted projects (most queries)
-- Existing indexes on tenant_key, status are sufficient
```

**Query Pattern**:
```python
# Fast query for non-deleted projects
query = select(Project).where(
    Project.tenant_key == tenant_key,
    or_(Project.status != "deleted", Project.deleted_at.is_(None))
)
```

### WebSocket Events

**Delete Event**:
```json
{
  "type": "project:deleted",
  "project_id": "uuid",
  "message": "Project will be purged in 10 days"
}
```

**Restore Event**:
```json
{
  "type": "project:restored",
  "project_id": "uuid",
  "project_data": { ... }
}
```

---

## Success Criteria

### Functional Requirements
- [x] Projects can be soft deleted (status="deleted", deleted_at set)
- [x] Deleted projects invisible in all normal views
- [x] Deleted projects appear in Settings → Database tab
- [x] Users can restore deleted projects
- [x] Restored projects return as inactive status
- [x] Projects older than 10 days are purged permanently
- [x] Purge cascades to child records (agents, tasks, messages)

### User Experience Requirements
- [x] Clear messaging about 10-day recovery window
- [x] Easy access to recovery UI (Settings → Database)
- [x] Countdown shows days until purge
- [x] Confirmation dialogs prevent accidental actions
- [x] Success/error messages for all actions

### Technical Requirements
- [x] Multi-tenant isolation maintained
- [x] No breaking changes to existing functionality
- [x] WebSocket broadcasts for real-time updates
- [x] Database queries remain performant
- [x] Migration is reversible (down migration works)

### Testing Requirements
- [x] Unit tests for soft delete logic
- [x] Integration tests for full delete → restore flow
- [x] Multi-tenant isolation verified
- [x] Edge cases covered (restore twice, delete deleted, etc.)
- [x] Purge logic tested (both manual and automated)

---

## Edge Cases & Error Handling

### Edge Case 1: Restore Already Active Project
**Scenario**: Project restored while another project is active under same product
**Handling**:
- Check Handover 0050b constraint (one active project per product)
- Restore as inactive (safe default)
- User must manually activate after restore

### Edge Case 2: Delete Already Deleted Project
**Scenario**: DELETE called on project with status="deleted"
**Handling**:
- Return 400 Bad Request: "Project already deleted"
- Frontend should prevent this (hide delete button)

### Edge Case 3: Restore Non-Existent or Purged Project
**Scenario**: Restore called on purged project
**Handling**:
- Return 404 Not Found: "Project not found or already purged"
- Frontend shows error message

### Edge Case 4: Product Deleted While Projects Deleted
**Scenario**: Product deleted, has soft-deleted projects
**Handling**:
- Cascade product delete should purge soft-deleted projects
- Or: Block product deletion if has deleted projects
- **Recommendation**: Cascade purge (cleaner)

### Edge Case 5: Concurrent Restore Attempts
**Scenario**: Multiple users restore same project simultaneously
**Handling**:
- Database transaction ensures atomic update
- Second restore returns success (idempotent)

---

## Migration Strategy

### Migration File: `20251027_project_soft_delete.py`

```python
"""Add soft delete support to projects

Revision ID: 20251027_project_soft_delete
Revises: 20251027_single_active_project_per_product
Create Date: 2025-10-27
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = '20251027_project_soft_delete'
down_revision = '20251027_single_active_project_per_product'

def upgrade():
    # Add deleted_at column
    op.add_column('projects',
        sa.Column('deleted_at', sa.TIMESTAMP(), nullable=True)
    )

    # Add index for performance
    op.execute(text("""
        CREATE INDEX idx_projects_deleted_at
        ON projects(deleted_at)
        WHERE deleted_at IS NOT NULL
    """))

    print("[Handover 0070] Added deleted_at column and index")

def downgrade():
    op.drop_index('idx_projects_deleted_at', table_name='projects')
    op.drop_column('projects', 'deleted_at')
    print("[Handover 0070] Removed soft delete support")
```

---

## Documentation Updates

### Files to Update
1. `CLAUDE.md` - Add Handover 0070 section
2. `docs/SERVER_ARCHITECTURE_TECH_STACK.md` - Document soft delete pattern
3. `docs/README_FIRST.md` - Mention recovery UI feature
4. `handovers/0070_IMPLEMENTATION_STATUS.md` - Create status tracking doc

---

## Rollback Plan

**If implementation fails**:
1. Revert migration: `alembic downgrade -1`
2. Revert code changes via git
3. Frontend still works (DELETE endpoint still exists)

**Breaking Changes**: None
- Migration is additive (adds column, doesn't remove)
- API endpoints are new or modified (not removed)
- Frontend changes are isolated

---

## Future Enhancements

**Post-0070 Improvements**:
1. Extend to Products (soft delete products)
2. Extend to Agents (soft delete agents)
3. Export deleted data before purge
4. Configurable retention period (10/30/90 days)
5. Bulk restore/purge operations
6. Admin panel (if added later)

---

## Related Handovers

- **Handover 0050**: Single Active Product Architecture
- **Handover 0050b**: Single Active Project Per Product
- **Handover 0070**: This handover (Project Soft Delete + Recovery)

---

## Implementation Notes for Subagents

### Backend Agent (backend-integration-tester)
**Phases 1-2**: Database + API
- Create migration with `deleted_at` column
- Modify DELETE endpoint (remove summary requirement)
- Add GET `/projects/deleted` endpoint
- Add POST `/projects/{id}/restore` endpoint
- Add purge function (startup.py integration)
- Update base queries to filter deleted projects
- Write unit tests

### UX Designer Agent (ux-designer)
**Phases 3-4**: Frontend
- Update ProjectsView delete flow with new modal
- Add Database tab to UserSettings
- Create deleted projects table component
- Add restore functionality
- Ensure proper error handling
- Match existing UI patterns (Vuetify components)

### Documentation Manager Agent (documentation-manager)
**Phase 6**: Documentation
- Update CLAUDE.md
- Update architecture docs
- Create implementation status doc
- Document API endpoints
- Add user guide section

---

**Status**: Ready for implementation
**Next Step**: Launch subagents for Phases 1-6
**Expected Duration**: 1 day (12-16 hours total)

---

**END OF HANDOVER DOCUMENT**
