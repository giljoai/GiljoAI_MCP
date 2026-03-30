# Phase B: Project Creation

**Suite:** UI Functional Test Suite (0769-UI)
**Prerequisite:** Phase A complete (test product exists)
**Creates data:** Yes — 1 test project

---

## Steps

### B1. Navigate to Projects
1. Click "Projects" in navigation drawer
2. **Verify:** Projects page loads with existing projects
3. **Verify:** Zero console errors

### B2. Create New Project
1. Click "New Project" button
2. Fill in project form:
   - **Name:** `UI Test Project - [date]`
   - **Description:** `Automated UI test project for quality verification`
   - **Product:** Select the test product from Phase A
   - **Project type/taxonomy:** Select any available type (e.g., TST)
3. Save/submit the project
4. **Verify:** Project appears in the project list
5. **Verify:** Status shows as "Inactive" (newly created)
6. **Verify:** Taxonomy ID is assigned (e.g., TST-XXXX)
7. **Verify:** Date formatting is correct (useFormatDate composable)
8. **Verify:** Zero console errors

### B3. Verify Project Detail
1. Click on the project row to open details
2. **Verify:** Project tabs load (check which tabs are visible for inactive project)
3. **Verify:** Product association is displayed
4. **Verify:** Status badge renders correctly (display-only v-chip)
5. **Verify:** Zero console errors

### B4. Test Project Actions Menu
1. Click the "Project actions" button for the test project
2. **Verify:** Actions menu opens with appropriate options
3. **Verify:** Options match project status (inactive: activate, edit, delete, etc.)
4. Close menu without taking action
5. **Verify:** Zero console errors

---

## Pass Criteria
- [ ] Project created and linked to test product
- [ ] Project appears in list with correct taxonomy ID
- [ ] Status badge renders correctly
- [ ] Date formatting is consistent
- [ ] Actions menu shows correct options
- [ ] Zero console errors throughout

## Cleanup
Note the project ID for use in Phase C. Do NOT delete yet.
