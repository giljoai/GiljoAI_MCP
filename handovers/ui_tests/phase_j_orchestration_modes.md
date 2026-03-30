# Phase J: Orchestration Modes — Multi-Terminal & Subagent Staging

**Suite:** UI Functional Test Suite (0769-UI)
**Prerequisite:** Phase A-C complete (test product + project exist)
**Creates data:** Yes — launches 1 light project to test mode selection

---

## Steps

### J1. Create or Reuse Test Project
1. Create a new project or reuse the test project from Phase B
2. Ensure project is in "Active" status
3. **Verify:** Zero console errors

### J2. Enter Staging — Multi-Terminal Mode
1. Start staging the project
2. Select "Multi-Terminal" execution mode
3. **Verify:** Multi-terminal configuration UI appears
4. **Verify:** Agent assignment to terminals is visible
5. Configure 1 agent with a simple mission
6. **Verify:** Zero console errors

### J3. Switch to Subagent Mode — Claude
1. Change execution mode to Claude subagent mode
2. **Verify:** UI updates to show subagent configuration
3. **Verify:** Claude-specific options appear
4. **Verify:** Zero console errors

### J4. Switch to Subagent Mode — Codex
1. Change execution mode to Codex subagent mode
2. **Verify:** UI updates for Codex configuration
3. **Verify:** Codex-specific options appear
4. **Verify:** Zero console errors

### J5. Switch to Subagent Mode — Gemini
1. Change execution mode to Gemini subagent mode
2. **Verify:** UI updates for Gemini configuration
3. **Verify:** Gemini-specific options appear
4. **Verify:** Zero console errors

### J6. Light Launch Test
1. Pick one execution mode (whichever is most stable)
2. Configure 1 agent with mission: "Confirm tool connectivity and list available tools."
3. Launch the project
4. **Verify:** Agent spawns in the selected mode
5. **Verify:** WebSocket updates show agent progress
6. **Verify:** Agent completes or can be cancelled
7. **Verify:** Zero console errors

### J7. Verify Mode Persistence
1. After launch, check that the execution mode is recorded on the project
2. **Verify:** Project detail shows the execution mode used
3. **Verify:** Zero console errors

---

## Pass Criteria
- [ ] Multi-terminal mode UI loads and configures correctly
- [ ] Subagent mode switching works (Claude, Codex, Gemini)
- [ ] Each mode shows appropriate configuration options
- [ ] Light launch succeeds in at least one mode
- [ ] Execution mode persists on the project record
- [ ] Zero console errors throughout

## Cleanup
Complete/cancel the test project after testing.

## Important
- **Max 1 agent, simple mission** — this tests the UI, not the AI
- If mode switching causes errors, document and STOP
- If an agent hangs, wait 60 seconds then ask user for direction
