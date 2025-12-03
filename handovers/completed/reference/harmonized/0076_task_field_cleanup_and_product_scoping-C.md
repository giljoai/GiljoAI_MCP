# Handover 0076: Task Field Cleanup and Product Scoping

**Date**: 2025-01-30
**Status**: Ready for Implementation (ARCHIVED)
**Priority**: Medium
**Estimated Effort**: 4-6 hours

## Overview

Cleanup task management system by removing unused fields, implementing product-scoped task filtering, and adding task-to-project conversion functionality.

## Context

The current task system has fields that were added for future functionality but are not needed:
- **Assign to team member**: Cross-user assignment not implemented yet
- **Assign to agent**: Agent assignment logic doesn't exist and may never be needed

Additionally, the task filtering needs to align with the single active product architecture introduced in Handover 0050.

## Goals

1. **Remove Unused Fields**
   - Remove "assigned_to_user_id" field (team member assignment)
   - Remove "assigned_to_agent_id" field (agent assignment)
   - Clean up all related logic, UI components, and database schema
   - Ensure no cascading effects on application functionality

2. **Implement Product-Scoped Task Filtering**
   - Change "My Tasks" filter to "Product Tasks" (tasks for currently active product)
   - Add "All Tasks" filter for tasks with `product_id = NULL`
   - Align with single active product architecture (Handover 0050)

3. **Add Task-to-Project Conversion**
   - New "Convert to Project" button in task UI
   - Copy task title → project title
   - Copy task description → project description
   - Keep other task fields unchanged

## Technical Details

### 1. Database Changes

**File**: `src/giljo_mcp/models.py`

**Current Task Model Fields to Remove**:
```python
# Remove these fields from Task model
assigned_to_user_id = Column(String, ForeignKey('users.id'), nullable=True)
assigned_to_agent_id = Column(String, ForeignKey('agents.id'), nullable=True)
```

**Migration Considerations**:
- Check for existing data in these columns before removal
- Create migration script if needed (or rely on `install.py` for fresh setups)
- Ensure foreign key constraints are properly dropped

**Existing Fields to Keep**:
```python
product_id = Column(String, ForeignKey('products.id'), nullable=True)  # Important for scoping
created_by_user_id = Column(String, ForeignKey('users.id'))  # Task creator
parent_task_id = Column(String, ForeignKey('tasks.id'), nullable=True)  # Hierarchy
status = Column(String, default='pending')  # pending, in_progress, completed, blocked
priority = Column(String, default='medium')  # low, medium, high, critical
title = Column(String, nullable=False)
description = Column(Text)
# ... other fields
```

### 2. API Endpoint Changes

**File**: `api/endpoints/tasks.py`

**Remove Assignment Logic**:
- Remove `assigned_to_user_id` from task creation/update endpoints
- Remove `assigned_to_agent_id` from task creation/update endpoints
- Remove any validation logic for these fields
- Update Pydantic models (TaskCreate, TaskUpdate, TaskResponse)

**Update Task Filtering**:
```python
# OLD: Filter by user assignment
if task_filter == "my_tasks":
    where_clauses.append(Task.assigned_to_user_id == current_user.id)

# NEW: Filter by product scope
if task_filter == "product_tasks":
    # Get active product for current tenant
    active_product = await get_active_product(tenant_key)
    if active_product:
        where_clauses.append(Task.product_id == active_product.id)
    else:
        # No active product, return empty list
        where_clauses.append(Task.id == None)  # Always false

elif task_filter == "all_tasks":
    # Tasks with NULL product_id (created via MCP without active product)
    where_clauses.append(Task.product_id.is_(None))
```

**Add Task-to-Project Conversion Endpoint**:
```python
@router.post("/{task_id}/convert-to-project", response_model=ProjectResponse)
async def convert_task_to_project(
    task_id: str,
    tenant_key: str = Depends(get_tenant_key),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Convert a task to a project.
    Copies: task.title -> project.name, task.description -> project.description
    """
    # 1. Fetch task
    task = await db.get(Task, task_id)
    if not task or task.tenant_key != tenant_key:
        raise HTTPException(status_code=404, detail="Task not found")

    # 2. Get active product (required for project creation per Handover 0050)
    active_product = await get_active_product(tenant_key, db)
    if not active_product:
        raise HTTPException(
            status_code=400,
            detail="No active product. Please activate a product before converting tasks to projects."
        )

    # 3. Create project from task
    new_project = Project(
        id=str(uuid.uuid4()),
        tenant_key=tenant_key,
        product_id=active_product.id,
        name=task.title,  # Copy title
        description=task.description,  # Copy description
        status='active',
        created_by_user_id=current_user.id,
        created_at=datetime.now(timezone.utc)
    )

    db.add(new_project)

    # 4. Optional: Update task status to indicate it was converted
    task.status = 'completed'  # Or add a new status 'converted'?

    await db.commit()
    await db.refresh(new_project)

    return new_project
```

### 3. Frontend Changes

**File**: `frontend/src/views/TasksView.vue`

**Remove Assignment UI Elements**:

1. **Remove from Create/Edit Task Dialog** (lines ~437-550):
```vue
<!-- DELETE: Assign to User Field -->
<v-select
  v-model="currentTask.assigned_to_user_id"
  :items="users"
  item-title="username"
  item-value="id"
  label="Assign to User"
  ...
/>

<!-- DELETE: Assign to Agent Field -->
<v-select
  v-model="currentTask.assigned_to_agent_id"
  :items="agents"
  item-title="name"
  item-value="id"
  label="Assign to Agent"
  ...
/>
```

2. **Remove from Task Display** (if shown in table/cards):
- Remove any assignment indicator icons
- Remove assigned user/agent columns from data table headers

3. **Update Filter Chips** (lines ~79-92):
```vue
<!-- OLD -->
<v-chip-group v-model="taskFilter" mandatory>
  <v-chip value="my_tasks">
    <v-icon start>mdi-account</v-icon>
    My Tasks
  </v-chip>
  <v-chip v-if="user && user.role === 'admin'" value="all">
    <v-icon start>mdi-account-group</v-icon>
    All Tasks
  </v-chip>
</v-chip-group>

<!-- NEW -->
<v-chip-group v-model="taskFilter" mandatory>
  <v-chip value="product_tasks">
    <v-icon start>mdi-package-variant</v-icon>
    Product Tasks
  </v-chip>
  <v-chip value="all_tasks">
    <v-icon start>mdi-format-list-bulleted</v-icon>
    All Tasks
  </v-chip>
</v-chip-group>
```

4. **Add Convert to Project Button**:

Add to task actions menu or bulk actions:

```vue
<!-- In task row actions (item.actions slot) -->
<v-menu>
  <template v-slot:activator="{ props }">
    <v-btn icon="mdi-dots-vertical" v-bind="props" size="small" />
  </template>
  <v-list>
    <v-list-item @click="editTask(item)">
      <v-list-item-title>
        <v-icon start>mdi-pencil</v-icon>
        Edit
      </v-list-item-title>
    </v-list-item>

    <!-- NEW: Convert to Project -->
    <v-list-item @click="convertTaskToProject(item)">
      <v-list-item-title>
        <v-icon start>mdi-folder-arrow-up</v-icon>
        Convert to Project
      </v-list-item-title>
    </v-list-item>

    <v-list-item @click="deleteTask(item)">
      <v-list-item-title>
        <v-icon start>mdi-delete</v-icon>
        Delete
      </v-list-item-title>
    </v-list-item>
  </v-list>
</v-menu>
```

**Add Conversion Function**:
```javascript
async function convertTaskToProject(task) {
  try {
    // Show confirmation dialog
    const confirmed = await showConfirmDialog(
      'Convert to Project?',
      `Convert task "${task.title}" to a new project?`,
      'This will create a new project with the task's title and description.'
    )

    if (!confirmed) return

    // Call API
    const response = await api.tasks.convertToProject(task.id)

    // Show success message
    showSnackbar('Task converted to project successfully', 'success')

    // Refresh tasks list
    await fetchTasks()

    // Optional: Navigate to new project
    router.push(`/projects/${response.data.id}`)

  } catch (error) {
    console.error('Error converting task to project:', error)
    showSnackbar('Failed to convert task to project', 'error')
  }
}
```

**File**: `frontend/src/services/api.js`

Add new API method:
```javascript
tasks: {
  // ... existing methods
  convertToProject: (taskId) => apiClient.post(`/api/v1/tasks/${taskId}/convert-to-project`),
}
```

### 4. Task Store Updates

**File**: `frontend/src/stores/tasks.js`

**Remove Assignment Fields**:
```javascript
// Remove from task state/actions
assigned_to_user_id: null,  // DELETE
assigned_to_agent_id: null,  // DELETE
```

**Update Filter Logic**:
```javascript
// OLD
const filteredTasks = computed(() => {
  let filtered = tasks.value

  if (taskFilter.value === 'my_tasks') {
    filtered = filtered.filter(t => t.assigned_to_user_id === currentUser.id)
  }

  return filtered
})

// NEW
const filteredTasks = computed(() => {
  let filtered = tasks.value

  if (taskFilter.value === 'product_tasks') {
    const activeProduct = productStore.activeProduct
    filtered = filtered.filter(t => t.product_id === activeProduct?.id)
  } else if (taskFilter.value === 'all_tasks') {
    filtered = filtered.filter(t => t.product_id === null)
  }

  return filtered
})
```

### 5. MCP Tool Updates

**File**: `src/giljo_mcp/tools/task_tools.py`

**Remove Assignment Parameters**:
```python
# OLD
@mcp.tool()
async def create_task(
    title: str,
    description: str,
    assigned_to_user_id: Optional[str] = None,  # DELETE
    assigned_to_agent_id: Optional[str] = None,  # DELETE
    ...
):
    pass

# NEW
@mcp.tool()
async def create_task(
    title: str,
    description: str,
    product_id: Optional[str] = None,  # Keep for product scoping
    ...
):
    """
    Create a new task.

    If product_id is None, task will appear in "All Tasks" filter.
    If product_id is provided, task will appear in "Product Tasks" for that product.
    """
    pass
```

## Implementation Checklist

### Phase 1: Database Cleanup
- [ ] Review Task model for assignment field usage
- [ ] Create database migration (if needed) to drop columns
- [ ] Update `src/giljo_mcp/models.py` - remove assignment fields
- [ ] Test database changes with `install.py`

### Phase 2: Backend API Updates
- [ ] Update `api/endpoints/tasks.py` - remove assignment logic
- [ ] Update Pydantic models (TaskCreate, TaskUpdate, TaskResponse)
- [ ] Implement product-scoped filtering (product_tasks, all_tasks)
- [ ] Add `convert-to-project` endpoint
- [ ] Update MCP tools in `src/giljo_mcp/tools/task_tools.py`
- [ ] Write/update API tests

### Phase 3: Frontend Updates
- [ ] Update `frontend/src/views/TasksView.vue` - remove assignment UI
- [ ] Change filter chips: "My Tasks" → "Product Tasks", add "All Tasks"
- [ ] Add "Convert to Project" button/menu item
- [ ] Implement conversion function
- [ ] Update `frontend/src/services/api.js` with new endpoint
- [ ] Update `frontend/src/stores/tasks.js` - remove assignment fields
- [ ] Test UI changes

### Phase 4: Testing & Validation
- [ ] Test task creation with active product (should set product_id)
- [ ] Test task creation with no active product (product_id = NULL)
- [ ] Test "Product Tasks" filter (shows only active product tasks)
- [ ] Test "All Tasks" filter (shows only NULL product tasks)
- [ ] Test task-to-project conversion
- [ ] Verify no cascading errors from field removal
- [ ] Test MCP task creation from Claude Code/Codex/Gemini

## Edge Cases & Considerations

1. **Existing Tasks with Assignment Data**
   - Migration should handle existing `assigned_to_user_id` and `assigned_to_agent_id` values
   - Option 1: Drop columns (data loss acceptable if no active usage)
   - Option 2: Create migration to clear values first, then drop columns

2. **Task Conversion with No Active Product**
   - User should see clear error: "Please activate a product before converting tasks to projects"
   - Align with single active product constraint (Handover 0050)

3. **Task Hierarchy After Conversion**
   - If a task has subtasks, what happens?
   - Option 1: Only allow conversion of tasks without children
   - Option 2: Convert parent task, keep subtasks as tasks
   - **Recommended**: Option 1 (simpler, clearer)

4. **Task Status After Conversion**
   - Should converted task be marked as 'completed' or have new status 'converted'?
   - **Recommended**: Mark as 'completed' to avoid adding new status type

5. **MCP Task Creation Without Active Product**
   - If user creates task via MCP with no active product, set `product_id = NULL`
   - These tasks appear in "All Tasks" filter only
   - User can manually assign product later (future enhancement)

## Related Handovers

- **Handover 0050**: Single Active Product Architecture
- **Handover 0050b**: Single Active Project Per Product
- **Handover 0070**: Project Soft Delete with Recovery

## Success Criteria

✅ Assignment fields removed from database, API, and UI
✅ "Product Tasks" filter shows tasks for active product only
✅ "All Tasks" filter shows tasks with NULL product_id
✅ "Convert to Project" button creates project with task title/description
✅ No cascading errors or broken functionality
✅ MCP task creation works with and without active product
✅ All existing tests pass

## Notes

- This handover focuses on cleanup and alignment with existing product-scoping architecture
- Assignment functionality may be re-introduced in future if multi-user collaboration is needed
- Task-to-project conversion is one-way (no project-to-task conversion)
- Consider adding "Converted from Task" metadata to projects for audit trail (optional)

## Questions for User

1. Should converted tasks be deleted or marked as 'completed'?
   - **Recommended**: Mark as 'completed' (preserves history)

2. Should we prevent conversion of tasks with subtasks?
   - **Recommended**: Yes (simpler logic)

3. Should we add a "Convert to Project" bulk action for multiple tasks?
   - **Recommended**: Future enhancement (not in this handover)
