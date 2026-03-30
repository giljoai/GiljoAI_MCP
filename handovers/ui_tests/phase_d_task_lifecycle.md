# Phase D: Task Creation & Graduation to Project

**Suite:** UI Functional Test Suite (0769-UI)
**Prerequisite:** Phase A complete (test product exists)
**Creates data:** Yes — 1-2 tasks, may graduate 1 to project

---

## Steps

### D1. Navigate to Tasks
1. Click "Tasks" in navigation drawer
2. **Verify:** Tasks view loads
3. **Verify:** Existing tasks visible (if any)
4. **Verify:** Zero console errors

### D2. Create a New Task
1. Find the "Add task" or "New task" input/button
2. Create a task:
   - **Title:** `UI Test Task - [date]`
   - **Description:** `Test task for UI quality verification`
   - **Product:** Select the test product from Phase A
3. Submit the task
4. **Verify:** Task appears in the task list
5. **Verify:** Task status shows as "Open" or default status
6. **Verify:** Zero console errors

### D3. Task Status Changes
1. Find the newly created task
2. Change its status (e.g., Open -> In Progress)
3. **Verify:** Status updates in real-time
4. **Verify:** Status badge renders correctly
5. **Verify:** Zero console errors

### D4. Graduate Task to Project
1. Find the option to graduate/promote the task to a project
2. Execute the graduation
3. **Verify:** A new project is created from the task
4. **Verify:** The task is linked to or replaced by the project
5. **Verify:** The new project appears in the Projects view
6. **Verify:** Zero console errors

---

## Pass Criteria
- [ ] Task created successfully
- [ ] Task status changes work
- [ ] Task graduation creates a project
- [ ] Zero console errors throughout

## Cleanup
Delete the test task and graduated project after testing (or note for later cleanup).
