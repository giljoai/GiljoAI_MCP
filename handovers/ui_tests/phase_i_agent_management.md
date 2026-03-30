# Phase I: Agent Management

**Suite:** UI Functional Test Suite (0769-UI)
**Prerequisite:** User logged in
**Creates data:** No — configuration changes only

---

## Steps

### I1. Navigate to Agent Settings
1. Go to Settings > Agents tab
2. **Verify:** Agent template list loads
3. **Verify:** Available agent types displayed (orchestrator, worker, etc.)
4. **Verify:** Zero console errors

### I2. View Agent Templates
1. Review the available agent templates
2. **Verify:** Each template shows name, role, description
3. **Verify:** Template icons/images render correctly
4. **Verify:** Zero console errors

### I3. Toggle Agent Availability
1. Find an agent template toggle (enable/disable)
2. Toggle an agent off
3. **Verify:** Agent is marked as disabled
4. Toggle it back on
5. **Verify:** Agent is re-enabled
6. **Verify:** Changes persist
7. **Verify:** Zero console errors

### I4. Agent Constellation in Project Context
1. Navigate to a project (active one from Phase C)
2. Go to the agents/team tab
3. **Verify:** Current agent constellation displayed
4. **Verify:** Available agents match what's enabled in settings
5. **Verify:** Zero console errors

### I5. Modify Agent Constellation
1. If the project allows editing the constellation:
   - Add or remove an agent from the team
   - **Verify:** Change is reflected in the UI
   - Revert the change
2. **Verify:** Zero console errors

---

## Pass Criteria
- [ ] Agent templates load and display correctly
- [ ] Agent enable/disable toggles work and persist
- [ ] Constellation view in project matches agent settings
- [ ] Zero console errors throughout

## Important
- Do NOT launch any agents in this phase — only configure
- If constellation changes require staging, just verify the UI works, don't actually launch
