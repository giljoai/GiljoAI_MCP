# Message Counters E2E Tests - Quick Start Guide

## TL;DR

These are **TDD tests** - they are written FIRST and will FAIL until the implementation is complete.

**Test File**: `frontend/tests/e2e/message-counters.spec.js`

**6 Test Scenarios**:
1. Broadcast message counters (all agents receive)
2. Direct message counters (one agent receives)
3. Counter persistence (values survive page reload)
4. Real-time counter updates (WebSocket driven)
5. Message status transitions (pending → acknowledged)
6. Concurrent messages (no race conditions)

---

## Setup (One Time)

```bash
# Make sure you're in the GiljoAI_MCP directory
cd /f/GiljoAI_MCP

# Start Backend (Terminal 1)
python startup.py
# Should see: "Uvicorn running on http://0.0.0.0:7272"

# Start Frontend (Terminal 2)
cd frontend
npm run dev
# Should see: "Local: http://localhost:7274"

# Keep both running!
```

---

## Run the Tests

```bash
# Terminal 3: Run E2E tests
cd frontend

# Run all message counter tests
npm run test:e2e -- message-counters.spec.js

# Run single test
npm run test:e2e -- message-counters.spec.js -g "Broadcast"

# Run with video recording (helpful for debugging)
npm run test:e2e -- message-counters.spec.js --video=on

# Run with Playwright Inspector (step through test)
npm run test:e2e -- message-counters.spec.js --debug
```

---

## Expected Results

### Current Status: ALL TESTS WILL FAIL

This is expected! TDD means:
- Tests are written FIRST
- Tests FAIL until code is implemented
- Implementation comes NEXT

### Example Failure Output

```
Test 1: Broadcast Message Counters
  FAIL: Timeout waiting for orchestrator "Messages Sent" to increment
  Reason: Counter update logic not yet implemented
  Expected: Counter increments by 1
  Actual: Counter remains 0

Test 2: Direct Message Counters
  FAIL: Timeout waiting for target agent "Messages Waiting" to increment
  Reason: Message routing or counter update missing
  Expected: Counter increments by 1
  Actual: Counter remains 0
```

---

## Test Walkthrough (What Each Test Does)

### Test 1: Broadcast Message Counters

```javascript
Given: 5 agents in a project
When:  Send broadcast message (to_agents=["all"])
Then:
  - Orchestrator "Messages Sent" += 1
  - ALL agents "Messages Waiting" += 1
  - Updates in real-time (< 2 seconds)
```

**What's Being Tested**:
- Broadcasting to multiple agents
- Counter accuracy (no off-by-one errors)
- Real-time updates via WebSocket

**Why It Might Fail**:
- Counter update logic missing
- WebSocket not broadcasting to all agents
- Frontend not listening for messages

---

### Test 2: Direct Message Counters

```javascript
Given: Multiple agents
When:  Send message to ONE agent (to_agents=["implementer"])
Then:
  - Orchestrator "Messages Sent" += 1
  - Target agent "Messages Waiting" += 1
  - Other agents "Messages Waiting" unchanged
```

**What's Being Tested**:
- Direct message routing
- Selective counter updates
- No counter pollution

**Why It Might Fail**:
- Message not routed to correct agent
- All agents receiving broadcast instead
- Counter not incremented for recipient

---

### Test 3: Counter Persistence

```javascript
Given: Messages sent (counters > 0)
When:  Page reload
Then:
  - Counters show same values
  - No reset to 0
  - Data persisted in backend
```

**What's Being Tested**:
- Backend persistence
- Frontend hydration on load
- No data loss on reload

**Why It Might Fail**:
- Counters loaded from frontend state (not backend)
- Page reload clears store without reloading
- Backend doesn't persist message data

---

### Test 4: Real-time Counter Updates

```javascript
Given: Viewing Jobs Dashboard
When:  Send 3 rapid messages
Then:
  - Counter updates within 2 seconds
  - No refresh needed
  - Accurate count (0 → 3)
```

**What's Being Tested**:
- WebSocket performance
- Real-time DOM updates
- No polling delays

**Why It Might Fail**:
- WebSocket events not emitted
- Frontend not listening
- Update delay > 2 seconds

---

### Test 5: Status Transitions

```javascript
Given: Message sent to agent
When:  Message status changes (pending → acknowledged)
Then:
  - "Messages Waiting" -= 1
  - "Messages Read" += 1
```

**What's Being Tested**:
- Message lifecycle tracking
- Counter state machine
- Status change handling

**Why It Might Fail**:
- Acknowledge endpoint not implemented
- Status not updated in database
- Counter not recalculated on status change

---

### Test 6: Concurrent Messages

```javascript
Given: Multiple agents
When:  Send different messages to different agents simultaneously
Then:
  - Each agent counter reflects only its messages
  - No race conditions
  - Consistent state
```

**What's Being Tested**:
- Concurrent message handling
- No race conditions
- Atomic counter updates

**Why It Might Fail**:
- Race condition in database updates
- Counter calculation not thread-safe
- WebSocket event ordering wrong

---

## Understanding Test Output

### Verbose Output (-v flag)

```bash
npm run test:e2e -- message-counters.spec.js -v
```

Shows detailed execution:
```
[Test 1] Starting: Broadcast Message Counters
[Test 1] Checking initial counter state...
[Test 1] Initial orchestrator state:
  - Messages Sent: 0
  - Messages Waiting: 0
[Test 1] Total agents: 5
[Test 1] Sending broadcast message via API...
[Test 1] Broadcast message sent: msg-123456
[Test 1] Waiting for WebSocket message update event...
[Test 1] Timeout waiting for orchestrator "Messages Sent" to increment
FAIL: Timeout error
```

### Video Recording (--video=on)

Records test execution as video:
```bash
npm run test:e2e -- message-counters.spec.js --video=on
# Watch: frontend/test-results/message-counters-chrome/
```

Shows exactly what the browser sees.

### HTML Report (--reporter=html)

```bash
npm run test:e2e -- message-counters.spec.js --reporter=html
# Open: frontend/playwright-report/index.html
```

Interactive report with:
- Screenshots on failure
- Detailed timings
- Network requests
- Console logs

---

## Debugging Tips

### 1. Check Backend Is Running

```bash
# In PowerShell
curl http://localhost:7272/api/health
# Should respond with 200 OK
```

### 2. Check Frontend Is Running

```bash
# In browser, go to:
# http://localhost:7274
# Should see login page
```

### 3. Check Test User Exists

Login manually with: `patrik` / `***REMOVED***`

If login fails, create user:
```bash
python -c "
from src.giljo_mcp.cli import create_user
create_user('patrik', '***REMOVED***', admin=True)
"
```

### 4. Check Message API Works

```powershell
# In PowerShell
$headers = @{
    'Content-Type' = 'application/json'
}
$body = @{
    to_agents = @('all')
    content = 'Test message'
    project_id = 'test-project'
    message_type = 'broadcast'
    priority = 'normal'
} | ConvertTo-Json

Invoke-RestMethod -Uri 'http://localhost:7272/api/messages' -Headers $headers -Body $body -Method Post
```

### 5. Check WebSocket Connection

```javascript
// In browser console (F12)
// Go to: http://localhost:7274
// Try to connect to WebSocket

const ws = new WebSocket('ws://localhost:7272/ws')
ws.onopen = () => console.log('WebSocket connected!')
ws.onmessage = (e) => console.log('Message:', e.data)
ws.onerror = (e) => console.error('Error:', e)
```

---

## Test Infrastructure

### Files Created

1. **Test File**:
   - `/f/GiljoAI_MCP/frontend/tests/e2e/message-counters.spec.js`
   - 800+ lines of test code
   - 6 complete test scenarios
   - Comprehensive comments

2. **Helper Functions**:
   - `/f/GiljoAI_MCP/frontend/tests/e2e/helpers-message-counters.ts`
   - Reusable message counter testing utilities
   - Counter snapshots, comparisons, etc.

3. **Documentation**:
   - `/f/GiljoAI_MCP/frontend/tests/e2e/MESSAGE_COUNTERS_TEST_GUIDE.md`
   - Complete reference guide
   - Implementation checklist

4. **Quick Start**:
   - `/f/GiljoAI_MCP/frontend/tests/e2e/MESSAGE_COUNTERS_QUICK_START.md`
   - This file

### Available Helpers

```typescript
// From helpers-message-counters.ts

getAgentCard(page, agentType)
// Get agent row/card element

getMessageCounterValue(page, agentType, 'sent'|'waiting'|'read')
// Get counter value

createTestProject(page, name)
// Create project via API

spawnTestAgents(page, projectId, agentTypes)
// Spawn test agents

sendTestMessage(page, projectId, toAgents, content)
// Send message via API

waitForMessageCounter(page, agentType, 'sent'|'waiting'|'read', value)
// Wait for counter to reach exact value

getCounterSnapshot(page)
// Get all counters at once

verifyCounterChanges(before, after, expectedChanges)
// Compare counter deltas
```

---

## What Needs to Be Implemented

To make these tests pass, you need to implement:

### Backend

1. **Message Sending**:
   - `POST /api/messages` - Already exists, may need fixes
   - Emit WebSocket event on message sent
   - Emit event to specific agents (for direct) or all (for broadcast)

2. **Message Storage**:
   - Store `from_agent` field
   - Store `to_agents` list
   - Store `status` (pending/sent/acknowledged/read)

3. **WebSocket Broadcasting**:
   - Emit `message:sent` event
   - Include message metadata
   - Include recipient list

### Frontend

1. **Counter Display**:
   - Already in JobsTab.vue (lines 481-510)
   - Methods exist but may not be calculating correctly

2. **Real-time Updates**:
   - Listen for WebSocket `message:sent` event
   - Update agent.messages array
   - Trigger counter recalculation

3. **Counter Persistence**:
   - Load messages from API on page load
   - Store in Pinia store
   - Hydrate from store on mount

---

## Success Criteria

All 6 tests passing:

```
✓ Test 1: Broadcast Message Counters (completed in 5s)
✓ Test 2: Direct Message Counters (completed in 4s)
✓ Test 3: Counter Persistence (completed in 6s)
✓ Test 4: Real-time Counter Updates (completed in 3s)
✓ Test 5: Message Status Transitions (completed in 5s)
✓ Test 6: Concurrent Messages (completed in 7s)

Total: 6 passed, 0 failed, 0 skipped (30s)
```

---

## Next Steps

1. **Run tests** → capture failures
2. **Review failures** → identify what's missing
3. **Implement fixes** → add counter logic
4. **Re-run tests** → verify passing
5. **Repeat** until all green

---

## Questions?

- Check the detailed guide: `MESSAGE_COUNTERS_TEST_GUIDE.md`
- Review test comments: `message-counters.spec.js`
- Check helper docs: `helpers-message-counters.ts`
- Verify backend is running and accessible
- Check that test user exists (`patrik`)

Good luck! This is a comprehensive TDD test suite that will ensure message counters work perfectly end-to-end.

---

**Test Suite Created**: December 4, 2025
**Status**: TDD Ready (tests fail, awaiting implementation)
**Coverage**: 6 scenarios, 20+ assertions per test
