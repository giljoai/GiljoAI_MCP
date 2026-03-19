# Project State Management

**Document Version**: 1.0
**Implementation Date**: October 28, 2025
**Status**: Production Ready
**Related Handover**: 0071 - Simplified Project State Management

---

## Overview

GiljoAI MCP uses a simplified 5-state project lifecycle that provides clear semantics and intuitive transitions. The state machine ensures only ONE active project per product at any time, maintaining context clarity for agents and orchestrator.

**Key Principle**: Single Active Project per Product - only one project can be in "active" status for each product, enforced at both database and application levels.

---

## Project States

### Active

**Description**: Project currently being worked on by agents and orchestrator.

**Characteristics**:
- Receives agent assignments
- Visible in main projects view
- Orchestrator assigns missions to this project
- Real-time WebSocket updates

**Actions Available**:
- **Deactivate** - Pause work, free the active slot
- **Complete** - Mark as successfully finished
- **Cancel** - Abandon the project
- **Delete** - Soft delete (10-day recovery window)

**Limits**: Only ONE active project per product (database enforced).

**Use Case**: Your primary focus project that agents are currently working on.

---

### Inactive

**Description**: Project paused, not currently receiving agent work.

**Characteristics**:
- Work preserved (all context, missions, agents saved)
- Not consuming active resources
- Can be reactivated at any time
- Visible in main projects view

**Actions Available**:
- **Activate** - Resume work (becomes active project)
- **Delete** - Soft delete (10-day recovery window)

**Use Case**: Temporarily stop work to focus on another project within the same product.

**Example Scenario**: You have "Website Redesign" active but need to switch focus to "Bug Fixes" for a week. Deactivate "Website Redesign" (becomes inactive), then activate "Bug Fixes."

---

### Completed

**Description**: Project finished successfully.

**Characteristics**:
- All work preserved for reference
- Mission and context available for review
- Agent assignments preserved (set to inactive)
- Visible in completed projects filter

**Actions Available**:
- **Reopen** - Reactivate for additional work
- **Delete** - Soft delete (10-day recovery window)

**Use Case**: Project goals achieved, work successfully delivered.

**Data Preservation**: All project data remains intact for future reference or reopening.

---

### Cancelled

**Description**: Project abandoned before completion.

**Characteristics**:
- All work preserved
- Clear distinction from completed projects
- Agent assignments preserved
- Visible in cancelled projects filter

**Actions Available**:
- **Reopen** - Reactivate if you change your mind
- **Delete** - Soft delete (10-day recovery window)

**Use Case**: Project requirements changed, scope invalidated, or decision made to abandon.

**Difference from Complete**: Cancelled indicates the project was not finished by choice, not successfully delivered.

---

### Deleted

**Description**: Soft deleted with 10-day recovery window before permanent purge.

**Characteristics**:
- Immediately hidden from all normal views
- Recoverable for 10 days via Settings → Database tab
- Countdown timer shows days until permanent purge
- Auto-purged after 10 days (on application startup)

**Actions Available**:
- **Restore** - Recover to inactive status (within 10 days only)

**Use Case**: Accidental deletion or cleanup while preserving recovery option.

**Permanent Purge**: After 10 days, project and all related data (agents, tasks, messages, jobs) are permanently deleted via cascade.

---

## State Transitions

### Visual State Machine

```
                                    ┌──────────┐
                    ┌───────────────┤  ACTIVE  ├───────────────┐
                    │               └────┬─────┘               │
                    │                    │                     │
              [Deactivate]          [Complete]            [Cancel]
                    │                    │                     │
                    ▼                    ▼                     ▼
              ┌──────────┐         ┌──────────┐         ┌──────────┐
              │ INACTIVE │         │COMPLETED │         │CANCELLED │
              └────┬─────┘         └────┬─────┘         └────┬─────┘
                   │                    │                     │
              [Activate]            [Reopen]            [Reopen]
                   │                    │                     │
                   └────────────────────┴─────────────────────┘
                                        │
                                    [Delete]
                                        │
                                        ▼
                                  ┌──────────┐
                                  │ DELETED  │◄──────────┐
                                  └────┬─────┘           │
                                       │            [Delete from
                                  [Restore]         any state]
                                       │
                                       └─────────► INACTIVE
                                   (within 10 days)
```

### Transition Rules

**From ACTIVE**:
- → INACTIVE: Deactivate (frees active slot)
- → COMPLETED: Complete successfully
- → CANCELLED: Abandon project
- → DELETED: Soft delete

**From INACTIVE**:
- → ACTIVE: Activate (only if no other project active for this product)
- → DELETED: Soft delete

**From COMPLETED or CANCELLED**:
- → ACTIVE: Reopen (only if no other project active for this product)
- → DELETED: Soft delete

**From DELETED**:
- → INACTIVE: Restore (within 10 days only)
- → PURGED: Automatic after 10 days (permanent, no recovery)

---

## How to Deactivate a Project

**Purpose**: Free up the active project slot to work on a different project.

**Steps**:

1. **Navigate to Projects Page**
   - Click "Projects" in the left navigation menu

2. **Find Active Project**
   - Look for project with green "Active" status badge
   - Only one project should show as active per product

3. **Click Status Badge**
   - Click the green "Active" badge on the project card
   - Status menu dropdown appears

4. **Select "Deactivate"**
   - Click "Deactivate" option in dropdown
   - Confirmation dialog appears

5. **Confirm Action**
   - Review project name in confirmation dialog
   - Click "Deactivate" button to confirm
   - Or click "Cancel" to abort

6. **Project Status Changes**
   - Status badge changes from green "Active" to gray "Inactive"
   - Project removed from active slot
   - Real-time WebSocket update notifies all connected clients

**Effect**: The project is paused, and the active slot is now available for another project to become active.

**Data Preservation**: All project data remains intact (mission, context, agent assignments, task history).

---

## How to Activate a Project

**Purpose**: Resume work on an inactive project by making it the active project.

**Steps**:

1. **Navigate to Projects Page**

2. **Find Inactive Project**
   - Look for project with gray "Inactive" status badge

3. **Click Status Badge**
   - Status menu dropdown appears

4. **Select "Activate"**
   - Click "Activate" option in dropdown

5. **Validation Check**
   - System checks if another project is already active for this product
   - If validation passes: Project status changes to "Active"
   - If validation fails: Error message displayed

**Error Scenario**: If another project is already active:

```
Error: Another project ('Website Redesign') is already active for this product.
Please deactivate it first.
```

**Resolution**: Deactivate the currently active project first, then activate your desired project.

**Single Active Rule**: Only ONE project can be active per product at any time.

---

## Single Active Project Rule

### Purpose

Ensures clear focus for orchestrator and agents by limiting active work to a single project per product.

**Benefits**:
- **Clear Context**: Agents receive unambiguous project context
- **Better Resource Allocation**: Focus computational resources on one project
- **Simpler Mental Model**: Users understand which project is currently active
- **Orchestrator Clarity**: Mission assignments always target the active project

### Enforcement Layers

**1. Database Constraint** (Primary):
```sql
CREATE UNIQUE INDEX idx_project_single_active_per_product
ON projects (product_id)
WHERE status = 'active';
```
- Atomic enforcement (no race conditions)
- PostgreSQL partial unique index
- Immediate constraint violation error if violated

**2. API Validation** (Secondary):
- Endpoint validates no other active project exists before activation
- Clear error messages with resolution hints
- Rich context returned (name of conflicting project)

**3. Frontend Validation** (Tertiary):
- UI prevents simultaneous activation attempts
- Warning messages guide users
- Real-time WebSocket updates prevent stale state

### Error Messages

**Activation Blocked**:
```json
{
  "detail": "Another project ('Website Redesign') is already active for this product. Please deactivate it first."
}
```

**Database Constraint Violation** (if somehow bypassed):
```
Duplicate key value violates unique constraint "idx_project_single_active_per_product"
```

---

## View Deleted Projects

### Purpose

Recover accidentally deleted projects within the 10-day recovery window.

### Steps

1. **Navigate to Settings**
   - Click avatar dropdown (top-right)
   - Select "Settings"

2. **Open Database Tab**
   - Click "Database" tab in settings panel

3. **Scroll to Deleted Projects Section**
   - Section displays table of deleted projects
   - Shows only deleted projects for **active product**

4. **Review Deleted Projects**
   - Table columns:
     - Project Name
     - Product Name
     - Deleted Date
     - Days Until Purge (countdown)

5. **Restore Project** (optional)
   - Click "Restore" button next to project
   - Confirmation dialog appears
   - Click "Restore" to confirm
   - Project restored to "Inactive" status

### Product Scoping

**Important**: View Deleted shows only deleted projects for the **currently active product**.

**Behavior**:
- **Active Product Exists**: Shows that product's deleted projects
- **No Active Product**: Shows empty state (no deleted projects)

**Rationale**: Reduces clutter by filtering deleted projects to relevant product context.

**Example**:
- Active Product: "Website Redesign"
- Deleted Projects shown: Only projects under "Website Redesign" product
- Other products' deleted projects: Not shown (switch active product to view)

### Recovery Window

**Duration**: 10 days from deletion

**Countdown Display**:
- "9 days until purge"
- "3 days until purge"
- "< 1 day until purge" (urgent warning)

**Auto-Purge**: Projects automatically purged on next application startup after 10 days.

**Permanent Deletion**: After purge, project and all related data are permanently deleted (no recovery possible).

---

## Best Practices

### When to Deactivate

**Use Deactivate when**:
- Temporarily pausing work on a project
- Switching focus to another project
- Need to free up the active project slot
- Project on hold pending external dependencies

**Example**: Working on "Mobile App" but need to handle urgent "Bug Fixes" project. Deactivate "Mobile App," activate "Bug Fixes."

### When to Complete

**Use Complete when**:
- Project goals successfully achieved
- All deliverables completed
- Work ready for production/delivery
- No further development planned

**Example**: "Website Redesign" finished, tested, and deployed. Mark as completed.

### When to Cancel

**Use Cancel when**:
- Project requirements changed significantly
- Decision made to abandon project
- Scope invalidated by external factors
- Project no longer aligns with goals

**Example**: "Mobile App" cancelled due to shift in business strategy.

### When to Delete

**Use Delete when**:
- Cleaning up old/test projects
- Project no longer needed for reference
- Confident you won't need to recover the project
- Want to remove clutter from project list

**Note**: 10-day recovery window provides safety net for accidental deletions.

---

## Differences from Previous Version

### Removed Features

**Pause/Resume**:
- **Before**: Projects could be "paused" (ambiguous state)
- **After**: Replaced with "Deactivate" (clearer terminology)
- **Rationale**: "Pause" was confusing - unclear if project was active or not

**Archived Status**:
- **Before**: Projects could be marked "archived"
- **After**: Removed, use "Inactive" instead
- **Rationale**: Redundant with completed/cancelled states

### Changed Features

**State Machine Simplification**:
- **Before**: 6 states (active, paused, archived, completed, cancelled, deleted)
- **After**: 5 states (active, inactive, completed, cancelled, deleted)
- **Reduction**: 17% fewer states, clearer semantics

**Product Switch Cascade**:
- **Before**: Switching products would "pause" all projects
- **After**: Switching products sets projects to "inactive"
- **Consistency**: Uses same terminology across all workflows

### Added Features

**Deactivate Endpoint**:
- **New**: POST /projects/{id}/deactivate
- **Purpose**: Explicit action to free active slot
- **Benefit**: Clear API semantics, better than generic PATCH

**Product-Scoped View Deleted**:
- **New**: Deleted projects filtered by active product
- **Benefit**: Less clutter, more relevant recovery list
- **UX**: Cleaner recovery experience

**Enhanced Validation**:
- **New**: Single active validation with rich error messages
- **Example**: "Another project 'X' is already active..."
- **Benefit**: Clear guidance on resolution

---

## API Reference

For complete API documentation, see:
- [Projects API Endpoints](../api/projects_endpoints.md)
- [OpenAPI Spec](http://localhost:7272/docs)

**Key Endpoints**:
- POST /projects/{id}/deactivate - Deactivate active project
- PATCH /projects/{id} - Update project (includes activation with validation)
- GET /projects/deleted - List deleted projects (product-scoped)
- POST /projects/{id}/restore - Restore deleted project

---

## Troubleshooting

### Cannot Activate Project

**Error**: "Another project 'X' is already active for this product."

**Solution**:
1. Identify the currently active project (shown in error message)
2. Navigate to that project
3. Deactivate it via status badge → Deactivate
4. Return to desired project and activate

### Cannot Deactivate Project

**Error**: "Cannot deactivate project with status 'inactive'."

**Cause**: Project is not currently active.

**Solution**: Only active projects can be deactivated. Check project status badge.

### Deleted Projects Not Showing

**Issue**: View Deleted shows no projects, but you know you deleted some.

**Possible Causes**:
1. **Wrong Product Context**: View Deleted is scoped to active product. Switch active product.
2. **Already Purged**: Projects deleted > 10 days ago are auto-purged.
3. **Different Tenant**: Multi-tenant isolation - ensure you're logged in as correct user.

**Solution**: Switch to the product that owned the deleted projects.

### Project Auto-Purged

**Issue**: Deleted project disappeared before 10 days.

**Unlikely**: Auto-purge only runs on startup and respects 10-day window.

**Check**: Verify deleted_at timestamp in database (if admin access available).

**Prevention**: Restore deleted projects promptly if you might need them.

---

## Related Documentation

- [Project API Endpoints](../api/projects_endpoints.md) - Complete API reference
- [Server Architecture](../SERVER_ARCHITECTURE_TECH_STACK.md) - Database schema and constraints
- [Handover 0070](../../handovers/completed/harmonized/0070_project_soft_delete_recovery-C.md) - Soft delete implementation
- [Handover 0050b](../../handovers/completed/harmonized/0050b_single_active_project_per_product-C.md) - Single active project architecture

---

**Last Updated**: October 28, 2025
**Document Maintainer**: Documentation Manager Agent
**Handover Reference**: 0071 - Simplified Project State Management
