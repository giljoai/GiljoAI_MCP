# GiljoAI Live Testing Checklist - 2025-11-29

**Purpose**: Comprehensive test checklist for validating the complete GiljoAI workflow from "Stage Project" to "Close Project"

**Pre-Test Status**: System is 97% ready with WebSocket bug fixed

---

## Pre-Test Setup Checklist

### 1. Server & Database
- [ ] PostgreSQL running (password: 4010)
- [ ] Run `python startup.py` to start server
- [ ] Verify server running at http://localhost:7274
- [ ] Check database migrations complete

### 2. User & Authentication
- [ ] Admin user exists (or create via /welcome)
- [ ] Can login successfully
- [ ] API key generated for MCP

### 3. MCP Integration
- [ ] MCP configuration in Claude Code CLI complete
- [ ] API key added to MCP config
- [ ] Test MCP connection: `mcp__giljo-mcp__health_check()`

### 4. Agent Templates (Critical for Claude Code CLI)
- [ ] Agent templates exported to `~/.claude/agents/`:
  - [ ] implementer.md
  - [ ] tester.md
  - [ ] debugger.md
  - [ ] documentation-manager.md
  - [ ] security-analyst.md
- [ ] Templates contain MCP behavior instructions

---

## Phase 1: Product & Project Setup

### Create Product
- [ ] Navigate to Products page
- [ ] Click "Create Product"
- [ ] Fill in product details:
  - [ ] Product name
  - [ ] Description
  - [ ] Vision document (optional)
  - [ ] Tech stack fields
  - [ ] Testing methodology
- [ ] Save product
- [ ] Verify product card appears

### Activate Product
- [ ] Click "Activate" on product card
- [ ] Verify "Active" badge appears
- [ ] Check header shows active product

### Create Project
- [ ] Navigate to Projects
- [ ] Click "Create Project"
- [ ] Enter project name
- [ ] Enter project description
- [ ] Save project
- [ ] Verify project appears in list

### Activate Project
- [ ] Click "Activate" on project
- [ ] Verify only one project active
- [ ] Check "Launch Project" button appears

---

## Phase 2: Stage Project (7-Task Workflow)

### Launch Tab
- [ ] Click "Launch Project" or navigate to Jobs
- [ ] Verify LaunchTab displays
- [ ] See "Stage Project" button
- [ ] Empty "Orchestrator Generated Mission" window visible
- [ ] Orchestrator agent card present

### Stage Project
- [ ] Click "Stage Project" button
- [ ] Copy orchestrator prompt
- [ ] Paste in Claude Code CLI terminal
- [ ] Monitor orchestrator execution of 7 tasks:

#### Task 1: Identity Verification ✓
- [ ] Orchestrator verifies its identity
- [ ] Confirms orchestrator_id matches

#### Task 2: MCP Health Check ✓
- [ ] Calls `health_check()`
- [ ] Verifies response < 2 seconds
- [ ] Lists available MCP tools

#### Task 3: Environment Understanding ✓
- [ ] Reads CLAUDE.md
- [ ] Understands project context

#### Task 4: Agent Discovery ✓
- [ ] Calls `get_available_agents()`
- [ ] Lists available agent templates
- [ ] No hardcoded agent list

#### Task 5: Context & Mission Creation ✓
- [ ] Fetches product context
- [ ] Creates comprehensive mission
- [ ] Calls `update_project_mission()`
- [ ] Mission appears in UI

#### Task 6: Agent Job Spawning ✓
- [ ] Calls `spawn_agent_job()` for each agent
- [ ] Agent cards appear in UI
- [ ] Each has unique agent_id
- [ ] Status shows "Waiting." (not "Pending")

#### Task 7: Project Activation ✓
- [ ] Project marked as active
- [ ] "Launch Jobs" button appears

### Verify UI Updates
- [ ] Mission text displayed in window
- [ ] Agent cards show correct status ("Waiting.")
- [ ] All expected agents present
- [ ] WebSocket updates received

---

## Phase 3: Implementation - Claude Code CLI Mode

### Toggle Claude Code CLI Mode
- [ ] Navigate to Implementation tab
- [ ] Toggle "Claude Code CLI Mode" ON
- [ ] Verify only orchestrator copy button enabled
- [ ] All other agent buttons disabled

### Launch Orchestrator
- [ ] Copy orchestrator prompt (only enabled button)
- [ ] Paste in Claude Code CLI terminal
- [ ] Orchestrator reads mission from MCP

### Native Subagent Spawning (Type 2)
- [ ] Orchestrator looks for `.md` templates
- [ ] Finds templates in `~/.claude/agents/`
- [ ] Spawns subagents using Claude's native feature
- [ ] Passes agent_id, job_id to each subagent

### Agent Execution
- [ ] Each subagent calls `get_agent_mission(job_id)`
- [ ] Agents fetch their missions from database
- [ ] Agents update status to "Working..."
- [ ] Monitor agent execution

### Status Updates
- [ ] Check JobsTab shows "Working..." status
- [ ] WebSocket updates received in real-time
- [ ] Status badges display correct colors

---

## Phase 4: Implementation - Multi-Terminal Mode

### Reset for Multi-Terminal Test
- [ ] Cancel current jobs if needed
- [ ] Toggle "Claude Code CLI Mode" OFF
- [ ] Verify ALL agent copy buttons enabled

### Launch Agents in Separate Terminals
- [ ] Copy orchestrator prompt
- [ ] Paste in terminal 1
- [ ] Copy implementer prompt
- [ ] Paste in terminal 2
- [ ] Copy tester prompt
- [ ] Paste in terminal 3
- [ ] (Continue for all agents)

### Direct MCP Connection (No Type 2 Spawning)
- [ ] Each agent fetches job via `get_agent_mission()`
- [ ] Each connects directly to MCP server
- [ ] No native Claude spawning occurs

---

## Phase 5: Agent Communication & Messages

### Test Message System
- [ ] Orchestrator sends broadcast message
- [ ] Agents receive messages
- [ ] Check message appears in UI Message Center

### Test JSONB Queue
- [ ] Agent sends message via `send_mcp_message()`
- [ ] Another agent reads via `read_mcp_messages()`
- [ ] Message acknowledged

### Test Messages Table
- [ ] Send message via UI
- [ ] Agent receives via `receive_messages()`
- [ ] Verify persistence in database

---

## Phase 6: Job Completion

### Agent Status Transitions
- [ ] Agent completes work
- [ ] Status changes to "Complete"
- [ ] WebSocket event received
- [ ] UI updates to show completion

### All Agents Complete
- [ ] All agent cards show "Complete"
- [ ] Project ready for closeout

---

## Phase 7: Project Closeout & 360 Memory

### Close Project
- [ ] Click "Close Project" button (if available)
- [ ] Or use MCP tool: `close_project_and_update_memory()`
- [ ] Enter summary and key outcomes
- [ ] Submit closeout

### Verify 360 Memory Update
- [ ] Check Product.product_memory updated
- [ ] Sequential history entry added
- [ ] GitHub commits captured (if enabled)
- [ ] Timestamp recorded

### Agent Decommissioning
- [ ] Agents status set to "decommissioned"
- [ ] Agents no longer accessible via MCP
- [ ] Project marked as complete

---

## Phase 8: Advanced Features

### Orchestrator Handover (90% Context)
- [ ] Monitor context usage
- [ ] At 90%, handover prompt appears
- [ ] Create successor orchestrator
- [ ] Verify context passed to new instance
- [ ] Original orchestrator decommissioned

### Project Reactivation
- [ ] Find completed project
- [ ] Click "Reactivate"
- [ ] Agents restored from decommissioned state
- [ ] Can continue work

---

## Edge Case Testing

### Error Handling
- [ ] Test with missing agent templates
- [ ] Test MCP connection failure
- [ ] Test invalid status transitions
- [ ] Test WebSocket disconnection

### Concurrent Operations
- [ ] Multiple agents updating status
- [ ] Simultaneous message sending
- [ ] Multiple users (different tenants)

### Status System
- [ ] Test all 7 status values display correctly
- [ ] Test invalid status rejection
- [ ] Test API alias translation

---

## Post-Test Validation

### Database Verification
```sql
-- Check agent jobs
SELECT agent_id, status, agent_type FROM mcp_agent_jobs
WHERE project_id = 'YOUR_PROJECT_ID';

-- Check messages
SELECT * FROM messages WHERE project_id = 'YOUR_PROJECT_ID';

-- Check 360 memory
SELECT product_memory FROM products WHERE id = 'YOUR_PRODUCT_ID';
```

### Log Review
- [ ] Check server logs for errors
- [ ] Review WebSocket connection logs
- [ ] Check MCP tool execution logs

### Performance Metrics
- [ ] Stage project < 10 seconds
- [ ] Agent spawning < 2 seconds each
- [ ] WebSocket updates < 500ms
- [ ] Message delivery < 1 second

---

## Known Issues to Watch For

1. **WebSocket Bug (FIXED)**: Previously sent "pending" instead of "waiting" - verify fix working
2. **Missing Frontend Status**: "blocked" and "decommissioned" may not display correctly
3. **Template Export**: Claude Code CLI requires manual template export
4. **Documentation**: flow.md shows 5 tasks but implementation has 7 (better)

---

## Success Criteria

✅ **Core Workflow**
- [ ] Complete flow from Stage to Close works
- [ ] Both spawning modes work (Claude CLI & Multi-terminal)
- [ ] All 7 staging tasks execute successfully
- [ ] Agents execute and complete jobs

✅ **Communication**
- [ ] Messages delivered between agents
- [ ] WebSocket real-time updates work
- [ ] Status transitions display correctly

✅ **Data Persistence**
- [ ] Missions stored and retrieved
- [ ] 360 memory updates correctly
- [ ] Project history maintained

✅ **User Experience**
- [ ] UI responsive and updates in real-time
- [ ] Status badges show correct colors
- [ ] Copy prompts work correctly
- [ ] No console errors

---

## Test Report Template

**Date**: 2025-11-29
**Tester**: [Name]
**Environment**: [Local/Network]
**Result**: [PASS/FAIL]

### Summary
- Total Tests: ___
- Passed: ___
- Failed: ___
- Blocked: ___

### Critical Issues Found
1. [Issue description]
2. [Issue description]

### Recommendations
1. [Recommendation]
2. [Recommendation]

---

## Notes

- This checklist follows the exact workflow described in `start_to_finish_agent_FLOW.md`
- Pay special attention to the two types of spawning (Type 1: MCP, Type 2: Claude CLI)
- WebSocket bug has been fixed but needs verification
- The system implements 7 staging tasks (better than documented 5)
- All core components are implemented and ready for testing