# Phase H: Project Launch with Context Verification

**Suite:** UI Functional Test Suite (0769-UI)
**Prerequisite:** Phase A-C complete (test product + project exist, project active)
**Creates data:** Yes — launches project with 1 agent (keep light)

---

## Steps

### H1. Verify Pre-Launch State
1. Navigate to the test project from Phase B/C
2. **Verify:** Project is in "Active" status
3. **Verify:** Product association visible
4. **Verify:** Context settings from Phase G are reflected
5. **Verify:** Zero console errors

### H2. Launch Project (Staging)
1. Click the launch/staging button for the project
2. **Verify:** Project enters staging mode
3. **Verify:** Staging UI appears (agent constellation picker, mission editor)
4. **Verify:** Context chunks are visible in the staging view
5. **Verify:** Zero console errors

### H3. Configure Minimal Agent Constellation
1. In staging, configure exactly 1 agent (keep it light)
2. Select an agent template
3. Provide a simple mission: "List the project files and summarize the product context."
4. **Verify:** Agent appears in the constellation view
5. **Verify:** Zero console errors

### H4. Execute Launch
1. Launch the staged project
2. **Verify:** Project status changes to reflect launch
3. **Verify:** Agent job is created and visible in Jobs tab
4. **Verify:** WebSocket updates arrive (agent status changes)
5. **Verify:** Messages appear in the Messages tab as the agent works
6. Wait for the agent to complete (should be quick with a simple mission)
7. **Verify:** Agent completes and project can be closed out
8. **Verify:** Zero console errors

### H5. Verify Context Was Used
1. Check agent messages — does the agent reference product context?
2. **Verify:** Context chunks were delivered to the agent
3. **Verify:** Vision document content (if chunked in Phase A) was included

---

## Pass Criteria
- [ ] Project launches from staging
- [ ] Agent job created and runs
- [ ] WebSocket real-time updates work
- [ ] Context from product/vision doc is delivered to agent
- [ ] Agent completes and project can close
- [ ] Zero console errors throughout

## Cleanup
Complete/cancel the project after testing. Delete if desired.

## Important
- **Max 1 agent** — this is a light verification test, not a stress test
- **Simple mission** — agent should complete in under 2 minutes
- If agent hangs or errors, STOP and ask user for direction
