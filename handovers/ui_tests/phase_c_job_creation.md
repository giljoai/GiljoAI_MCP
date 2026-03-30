# Phase C: Agent Job Creation

**Suite:** UI Functional Test Suite (0769-UI)
**Prerequisite:** Phase B complete (test project exists, inactive)
**Creates data:** Yes — activates project, may create 1 agent job

---

## Steps

### C1. Activate the Test Project
1. Navigate to Projects view
2. Find the test project from Phase B
3. Click "Activate project" button
4. **Verify:** Project status changes to "Active"
5. **Verify:** Status badge updates to "Active"
6. **Verify:** WebSocket event received (check for real-time update)
7. **Verify:** Zero console errors

### C2. Navigate to Jobs View
1. Click "Jobs" in navigation drawer (or the Jobs tab within the project)
2. **Verify:** Jobs view loads
3. **Verify:** The test project is selected/visible
4. **Verify:** Zero console errors

### C3. View Job Details (if any exist)
1. If there are existing jobs from project activation, click on one
2. **Verify:** Job detail modal/panel opens
3. **Verify:** Agent status displays correctly
4. **Verify:** Job metadata (phase, status, timestamps) renders
5. **Verify:** Zero console errors

### C4. Verify Project Tabs with Active Project
1. Navigate back to Projects, click on the active test project
2. **Verify:** Additional tabs are now visible (Jobs tab, Messages tab, etc.)
3. **Verify:** Tab navigation works between all tabs
4. **Verify:** Zero console errors

---

## Pass Criteria
- [ ] Project activated successfully
- [ ] Status badge updates in real-time
- [ ] Jobs view loads and displays correctly
- [ ] Project tabs reflect active state
- [ ] Zero console errors throughout

## Cleanup
Keep project active for Phase H (project launch test).
