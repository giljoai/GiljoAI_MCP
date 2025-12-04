# Message Counter E2E Tests - Complete Guide

## Overview

This document describes the comprehensive Playwright E2E tests for message counter functionality in the JobsTab component. These tests verify that message counters update correctly in real-time when messages are sent to agents via the API.

**Status**: TDD (Test-Driven Development) - Tests are written FIRST, before implementation is complete.

**Test File**: `/f/GiljoAI_MCP/frontend/tests/e2e/message-counters.spec.js`

**Helpers**:
- `/f/GiljoAI_MCP/frontend/tests/e2e/helpers.ts` (existing)
- `/f/GiljoAI_MCP/frontend/tests/e2e/helpers-message-counters.ts` (new)

---

## Test Environment

### Prerequisites

1. **Backend Running**: `http://localhost:7272`
2. **Frontend Dev Server**: `http://localhost:7274`
3. **Database**: PostgreSQL running with GiljoAI schema
4. **Test User**:
   - Username: `patrik`
   - Password: `***REMOVED***`

### Setup Script

```bash
# Terminal 1: Start backend
cd /f/GiljoAI_MCP
python startup.py

# Terminal 2: Start frontend
cd /f/GiljoAI_MCP/frontend
npm run dev

# Terminal 3: Run tests
cd /f/GiljoAI_MCP/frontend
npm run test:e2e -- message-counters.spec.js
```

---

## Test Scenarios

### Test 1: Broadcast Message Counters

**File**: `message-counters.spec.js` (Lines: TBD)

**Purpose**: Verify that broadcast messages increment counters for all agents.

**Scenario**:
```
Given: 5 agents are spawned in a project
When:  Orchestrator sends broadcast message (to_agents=["all"])
Then:
  - "Messages Sent" counter on ORCHESTRATOR card increments by 1
  - "Messages Waiting" counter increments by 1 on ALL agent cards
  - Updates happen in real-time via WebSocket (no page refresh needed)
```

**Expected Behavior**:
- Each agent receives the broadcast message
- All counters update simultaneously
- WebSocket event `message:sent` is emitted
- DOM reflects changes within 2 seconds

**Test Steps**:
1. Navigate to Jobs Dashboard
2. Record initial counter state for all agents
3. Send broadcast message via API
4. Wait for WebSocket event
5. Verify orchestrator "Messages Sent" incremented
6. Verify ALL agents "Messages Waiting" incremented

**Current Status**: WILL FAIL - Requires counter update implementation

---

### Test 2: Direct Message Counters

**File**: `message-counters.spec.js` (Lines: TBD)

**Purpose**: Verify that direct messages only increment counters for the recipient.

**Scenario**:
```
Given: Multiple agents are spawned
When:  Orchestrator sends direct message to ONE agent
Then:
  - "Messages Sent" counter increments on ORCHESTRATOR card
  - "Messages Waiting" increments ONLY on recipient agent
  - Other agents' counters remain unchanged
```

**Expected Behavior**:
- Only recipient agent receives the message
- Other agents are unaffected
- Counters are precise (no over/under counting)
- Updates are real-time via WebSocket

**Test Steps**:
1. Identify target agent (first non-orchestrator)
2. Record initial counters for all agents
3. Send direct message to target agent
4. Verify orchestrator "Messages Sent" incremented
5. Verify target agent "Messages Waiting" incremented
6. Verify all other agents' counters unchanged

**Current Status**: WILL FAIL - Requires routing to specific agent

---

### Test 3: Counter Persistence

**File**: `message-counters.spec.js` (Lines: TBD)

**Purpose**: Verify that counters persist correctly after page reload.

**Scenario**:
```
Given: Messages have been sent (counters showing > 0)
When:  User refreshes the page
Then:
  - All counters persist with correct values
  - No counters reset to 0
  - Values match pre-reload state exactly
```

**Expected Behavior**:
- Page reload doesn't lose message data
- Counters are loaded from backend on page load
- No race conditions or timing issues
- Consistent values before and after reload

**Test Steps**:
1. Send test broadcast message
2. Record counter state before reload
3. Reload the page
4. Record counter state after reload
5. Compare all counter values
6. Verify they match exactly

**Current Status**: WILL FAIL - Requires counter persistence implementation

---

### Test 4: Real-time Counter Updates

**File**: `message-counters.spec.js` (Lines: TBD)

**Purpose**: Verify that WebSocket delivers counter updates in real-time.

**Scenario**:
```
Given: User is viewing Jobs Dashboard
When:  Agent sends messages in background (via API)
Then:
  - Counter updates immediately (< 2 seconds)
  - No page refresh required
  - Multiple rapid messages update correctly
```

**Expected Behavior**:
- WebSocket events arrive quickly
- UI responds within 2 seconds
- No polling delays
- Counters accurately reflect all messages

**Test Steps**:
1. Record initial counter state
2. Set up WebSocket message listener
3. Send 3 rapid broadcast messages
4. Measure time to counter update
5. Verify counter equals initial + 3
6. Verify update time < 2 seconds

**Current Status**: WILL FAIL - Requires WebSocket broadcasting

---

### Test 5: Message Status Transitions

**File**: `message-counters.spec.js` (Lines: TBD)

**Purpose**: Verify counters reflect message status changes.

**Scenario**:
```
Given: A message is sent to an agent
When:  Agent acknowledges the message
Then:
  - "Messages Waiting" counter decrements
  - "Messages Read" counter increments
```

**Expected Behavior**:
- Counters track message lifecycle
- Status transitions are reflected immediately
- No data inconsistency

**Test Steps**:
1. Record initial counters
2. Send message to target agent
3. Wait for "Messages Waiting" to increment
4. Call acknowledge endpoint
5. Verify "Messages Waiting" decrements
6. Verify "Messages Read" increments

**Current Status**: SKELETON - Acknowledge endpoint not yet implemented

---

### Test 6: Multiple Concurrent Messages

**File**: `message-counters.spec.js` (Lines: TBD)

**Purpose**: Verify counters handle concurrent messages correctly.

**Scenario**:
```
Given: Multiple agents are active
When:  Different messages sent to different agents simultaneously
Then:
  - Each agent's counters reflect only its messages
  - Counters don't conflict or race
  - Total accuracy maintained
```

**Expected Behavior**:
- No race conditions
- Counters remain consistent
- Each agent's queue is independent
- Concurrent updates don't corrupt state

**Test Steps**:
1. Get 2+ target agents
2. Record initial counters
3. Send concurrent messages to different agents
4. Wait for orchestrator "Messages Sent" to increment
5. Verify each agent received its message
6. Verify no counters affected other agents

**Current Status**: WILL FAIL - Requires concurrent message handling

---

## Test Helpers

### From `helpers-message-counters.ts`

#### `getAgentCard(page, agentType, indexIfMultiple)`
Get the agent row/card element for a specific agent type.

```javascript
const orchestratorRow = getAgentCard(page, 'orchestrator')
const implementerRow = getAgentCard(page, 'implementer', 0)
```

#### `getMessageCounterValue(page, agentType, counterType)`
Get the current value of a specific counter.

```javascript
const sentCount = await getMessageCounterValue(page, 'orchestrator', 'sent')
const waitingCount = await getMessageCounterValue(page, 'implementer', 'waiting')
const readCount = await getMessageCounterValue(page, 'tester', 'read')
```

#### `createTestProject(page, name)`
Create a test project via API.

```javascript
const projectId = await createTestProject(page, 'Test Project')
```

#### `spawnTestAgents(page, projectId, agentTypes)`
Spawn test agents for a project.

```javascript
const agentIds = await spawnTestAgents(page, projectId, ['orchestrator', 'implementer', 'tester'])
```

#### `sendTestMessage(page, projectId, toAgents, content, fromAgent)`
Send a message via API.

```javascript
// Broadcast message
await sendTestMessage(page, projectId, ['all'], 'Broadcast message', 'orchestrator')

// Direct message to specific agent
await sendTestMessage(page, projectId, ['implementer'], 'Direct message', 'orchestrator')
```

#### `waitForMessageCounter(page, agentType, counterType, expectedValue, timeout)`
Wait for counter to reach exact value.

```javascript
await waitForMessageCounter(page, 'orchestrator', 'sent', 5, 15000)
```

#### `waitForMessageCounterAtLeast(page, agentType, counterType, minValue, timeout)`
Wait for counter to reach minimum value.

```javascript
await waitForMessageCounterAtLeast(page, 'implementer', 'waiting', 1, 10000)
```

#### `getCounterSnapshot(page)`
Get snapshot of all agent counters.

```javascript
const snapshot = await getCounterSnapshot(page)
// Returns: {
//   orchestrator: { sent: 5, waiting: 2, read: 3 },
//   implementer: { sent: 0, waiting: 1, read: 0 },
//   tester: { sent: 0, waiting: 1, read: 0 }
// }
```

#### `verifyCounterChanges(beforeSnapshot, afterSnapshot, expectedChanges)`
Compare two snapshots and verify expected changes.

```javascript
const before = await getCounterSnapshot(page)
await sendTestMessage(page, projectId, ['all'], 'Test')
const after = await getCounterSnapshot(page)

const changed = verifyCounterChanges(before, after, {
  'orchestrator': { sentDelta: 1 },
  'implementer': { waitingDelta: 1 },
  'tester': { waitingDelta: 1 }
})
```

---

## Running the Tests

### Run All Message Counter Tests

```bash
cd /f/GiljoAI_MCP/frontend
npm run test:e2e -- message-counters.spec.js
```

### Run Single Test

```bash
npm run test:e2e -- message-counters.spec.js -g "Broadcast Message Counters"
```

### Run with Debug Output

```bash
npm run test:e2e -- message-counters.spec.js --debug
```

### Run with Video Recording

```bash
npm run test:e2e -- message-counters.spec.js --video=on
```

### Run on Specific Browser

```bash
npm run test:e2e -- message-counters.spec.js --project=chromium
npm run test:e2e -- message-counters.spec.js --project=firefox
npm run test:e2e -- message-counters.spec.js --project=webkit
```

---

## Expected Failures (TDD Approach)

Since these tests are written FIRST (TDD), many will fail initially. Here are the expected failures:

### Test 1: Broadcast Message Counters - WILL FAIL
**Reason**: Counter update logic not yet implemented
**Error**: `Timeout waiting for orchestrator "Messages Sent" to increment`
**Fix Needed**: Implement counter update in JobsTab component

### Test 2: Direct Message Counters - WILL FAIL
**Reason**: Message routing to specific agents may not update counters
**Error**: `Timeout waiting for target agent "Messages Waiting" to increment`
**Fix Needed**: Verify message routing and counter updates for direct messages

### Test 3: Counter Persistence - WILL FAIL
**Reason**: Counters may not be loaded from backend on page reload
**Error**: `Counter value mismatch after page reload`
**Fix Needed**: Implement counter persistence in store

### Test 4: Real-time Updates - WILL FAIL
**Reason**: WebSocket events may not trigger counter updates
**Error**: `Timeout waiting for counter to update`
**Fix Needed**: Implement WebSocket event listeners in JobsTab

### Test 5: Status Transitions - WILL FAIL
**Reason**: Acknowledge endpoint not implemented
**Error**: `404 POST /api/messages/{id}/acknowledge`
**Fix Needed**: Implement acknowledge endpoint and counter transitions

### Test 6: Concurrent Messages - WILL FAIL
**Reason**: Race conditions in concurrent message handling
**Error**: `Counter mismatch in concurrent scenario`
**Fix Needed**: Ensure thread-safe counter updates

---

## Debugging Failed Tests

### Step 1: Check Test Output
```bash
# Look for specific error messages
npm run test:e2e -- message-counters.spec.js --reporter=html
# Open: frontend/playwright-report/index.html
```

### Step 2: Enable Video Recording
```bash
# Re-run test with video
npm run test:e2e -- message-counters.spec.js --video=on
# Check: frontend/test-results/message-counters-chrome/
```

### Step 3: Use Playwright Inspector
```bash
npm run test:e2e -- message-counters.spec.js --debug
# Step through test execution in Playwright Inspector
```

### Step 4: Check Network Tab
```javascript
// In test, listen for API responses
page.on('response', response => {
  console.log(`[API] ${response.request().method()} ${response.url()} - ${response.status()}`)
})
```

### Step 5: Check WebSocket Events
```javascript
// In test, listen for WebSocket events
page.on('console', msg => {
  console.log(`[Console] ${msg.text()}`)
})
```

### Step 6: Inspect Element State
```javascript
// Dump HTML of agent table
const html = await page.content()
console.log(html)
```

---

## Counter Implementation Checklist

### Backend Requirements

- [ ] `POST /api/messages` - Send message endpoint
  - [ ] Validate `to_agents` parameter
  - [ ] Create message record in database
  - [ ] Emit WebSocket event `message:sent`

- [ ] Message schema includes:
  - [ ] `from_agent` field
  - [ ] `to_agents` list
  - [ ] `status` field (pending/sent/acknowledged/read)
  - [ ] `created_at` timestamp

- [ ] WebSocket broadcast includes:
  - [ ] Message metadata
  - [ ] Recipient agent list
  - [ ] Current message counters

### Frontend Requirements

- [ ] JobsTab component:
  - [ ] Load agents with message data on mount
  - [ ] Subscribe to WebSocket `message:sent` event
  - [ ] Update counter on message arrival
  - [ ] Persist counters in store

- [ ] Message counter display:
  - [ ] `getMessagesSent(agent)` - Count outbound messages
  - [ ] `getMessagesWaiting(agent)` - Count pending/sent messages
  - [ ] `getMessagesRead(agent)` - Count acknowledged/read messages

- [ ] Real-time updates:
  - [ ] WebSocket listener for `message:sent`
  - [ ] Counter increment on event arrival
  - [ ] DOM update via Vue reactivity

- [ ] Counter persistence:
  - [ ] Load message data from API on page load
  - [ ] Store message state in Pinia
  - [ ] Hydrate counters from store

---

## Implementation Progress Tracking

Track implementation progress as you fix failing tests:

```markdown
## Implementation Status

- [ ] Test 1: Broadcast Message Counters
  - [ ] Backend: Emit WebSocket event for broadcast
  - [ ] Frontend: Listen and update DOM
  - [ ] Test: PASSING

- [ ] Test 2: Direct Message Counters
  - [ ] Backend: Route message to specific agent
  - [ ] Frontend: Update only recipient counter
  - [ ] Test: PASSING

- [ ] Test 3: Counter Persistence
  - [ ] Backend: Load messages on page load
  - [ ] Frontend: Hydrate store from API
  - [ ] Test: PASSING

- [ ] Test 4: Real-time Updates
  - [ ] Backend: Optimize WebSocket events
  - [ ] Frontend: Ensure update within 2 seconds
  - [ ] Test: PASSING

- [ ] Test 5: Status Transitions
  - [ ] Backend: Implement acknowledge endpoint
  - [ ] Frontend: Update counter on acknowledgement
  - [ ] Test: PASSING

- [ ] Test 6: Concurrent Messages
  - [ ] Backend: Thread-safe counter updates
  - [ ] Frontend: Race condition prevention
  - [ ] Test: PASSING
```

---

## Next Steps for TDD Agent

1. **Run tests**: Execute test suite and capture failures
2. **Document failures**: Record specific error messages
3. **Analyze gaps**: Identify missing functionality
4. **Implement fixes**: Add counter logic to JobsTab
5. **Verify**: Re-run tests until all pass
6. **Optimize**: Improve performance and reliability

---

## Related Files

**Component**: `/f/GiljoAI_MCP/frontend/src/components/projects/JobsTab.vue`

**Counter Methods**:
- `getMessagesSent(agent)` - Line 481
- `getMessagesWaiting(agent)` - Line 491
- `getMessagesRead(agent)` - Line 501

**API Endpoints**:
- `POST /api/messages` - `/f/GiljoAI_MCP/api/endpoints/messages.py`
- WebSocket manager - `/f/GiljoAI_MCP/api/websocket.py`

**Store**: `/f/GiljoAI_MCP/frontend/src/stores/projectJobsStore.js`

---

## Contact & Support

For questions about this test suite:
- Check this guide first
- Review test comments for details
- Check Playwright documentation: https://playwright.dev/
- Review Vue Test Utils docs: https://test-utils.vuejs.org/

---

**Last Updated**: December 4, 2025
**Status**: TDD - Tests Written, Implementation Pending
**Coverage**: 6 test scenarios, 100+ assertions
