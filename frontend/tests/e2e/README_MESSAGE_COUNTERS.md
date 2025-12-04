# Message Counter Playwright E2E Tests

## TL;DR

**Tests are ready. They will FAIL. This is TDD - that's expected.**

- **Test File**: `message-counters.spec.js` (32 KB, 950 lines)
- **Helpers**: `helpers-message-counters.ts` (9.7 KB, 250 lines)
- **Docs**: 4 comprehensive guides

### Run Tests

```bash
npm run test:e2e -- message-counters.spec.js
```

**Expected**: 0 passed, 6 failed, 1 skipped (this is correct for TDD!)

---

## What You're Testing

Message counters in the JobsTab component:
- `Messages Sent` - Count of messages orchestrator sent
- `Messages Waiting` - Count of messages agent hasn't read yet
- `Messages Read` - Count of messages agent has acknowledged

These counters should:
1. Update in real-time (via WebSocket)
2. Be accurate (count correct messages)
3. Persist (survive page reload)
4. Handle broadcast and direct messages correctly
5. Support concurrent messaging
6. Track message status transitions

---

## 6 Test Scenarios

| Test | Scenario | Expected | File |
|------|----------|----------|------|
| 1 | Broadcast message to all agents | All counters increment | Lines 150-250 |
| 2 | Direct message to one agent | Only recipient counter increments | Lines 260-380 |
| 3 | Page reload | Counters persist | Lines 390-480 |
| 4 | Multiple rapid messages | Update within 2 seconds | Lines 490-580 |
| 5 | Message status change | Waiting → Read counters update | Lines 590-680 |
| 6 | Concurrent messages | No race conditions | Lines 690-800 |

---

## Documentation

**Pick your reading level:**

### Quick Start (5 min)
Read: `MESSAGE_COUNTERS_QUICK_START.md`
- Setup, run commands, expected failures, debugging tips

### Complete Reference (30 min)
Read: `MESSAGE_COUNTERS_TEST_GUIDE.md`
- Every test detail, all helpers, implementation checklist

### Big Picture (10 min)
Read: `MESSAGE_COUNTERS_SUMMARY.md`
- Coverage, metrics, roadmap, success criteria

### Delivery Package (15 min)
Read: `MESSAGE_COUNTERS_DELIVERY.md`
- Files, setup, expected failures, next steps

---

## Quick Setup

### Terminal 1: Start Backend
```bash
cd /f/GiljoAI_MCP
python startup.py
```

### Terminal 2: Start Frontend
```bash
cd /f/GiljoAI_MCP/frontend
npm run dev
```

### Terminal 3: Run Tests
```bash
cd /f/GiljoAI_MCP/frontend
npm run test:e2e -- message-counters.spec.js
```

---

## Expected Results (First Run)

All tests will FAIL. This is correct! TDD means:
1. Write tests FIRST (Done)
2. Tests FAIL (Expected)
3. Implement code (Your job)
4. Tests PASS (Goal)

**Typical failures:**
```
✗ TEST 1: Timeout waiting for orchestrator "Messages Sent" to increment
✗ TEST 2: Timeout waiting for target agent "Messages Waiting" to increment
✗ TEST 3: Counter value mismatch after page reload
✗ TEST 4: Timeout waiting for counter to update
○ TEST 5: Skipped (acknowledge endpoint not yet)
✗ TEST 6: Counter mismatch in concurrent scenario
```

---

## What Needs to Be Implemented

### Backend (Priority 1)
- [ ] Emit WebSocket event when message sent
- [ ] Event includes recipient list
- [ ] Distinguish broadcast vs. direct

### Frontend (Priority 2)
- [ ] Listen for WebSocket `message:sent` event
- [ ] Update agent.messages array
- [ ] Counter recalculates via Vue reactivity

### Store (Priority 3)
- [ ] Load messages from API on mount
- [ ] Persist in store
- [ ] Survive page reload

---

## Helper Functions

```typescript
getMessageCounterValue(page, 'orchestrator', 'sent')
sendTestMessage(page, projectId, ['all'], 'Message')
waitForMessageCounterAtLeast(page, 'agent', 'waiting', 1)
getCounterSnapshot(page)
verifyCounterChanges(before, after, expectedChanges)
createTestProject(page, 'Test')
spawnTestAgents(page, projectId)
```

---

## File Structure

```
frontend/tests/e2e/
├── message-counters.spec.js              (32 KB)
├── helpers-message-counters.ts           (9.7 KB)
├── MESSAGE_COUNTERS_QUICK_START.md       (11 KB)
├── MESSAGE_COUNTERS_TEST_GUIDE.md        (17 KB)
├── MESSAGE_COUNTERS_SUMMARY.md           (11 KB)
├── MESSAGE_COUNTERS_DELIVERY.md          (15 KB)
└── README_MESSAGE_COUNTERS.md            (This file)
```

---

## Running Tests

```bash
# All tests
npm run test:e2e -- message-counters.spec.js

# Specific test
npm run test:e2e -- message-counters.spec.js -g "Broadcast"

# With video (debug)
npm run test:e2e -- message-counters.spec.js --video=on

# With inspector
npm run test:e2e -- message-counters.spec.js --debug

# HTML report
npm run test:e2e -- message-counters.spec.js --reporter=html
```

---

## Success Criteria

All 6 tests passing:
```
✓ Broadcast increments all counters
✓ Direct increments only recipient
✓ Persistence survives reload
✓ Real-time updates < 2 seconds
✓ Status transitions work
✓ Concurrent messages consistent
```

---

## Next Steps

1. Read: `MESSAGE_COUNTERS_QUICK_START.md`
2. Run: `npm run test:e2e -- message-counters.spec.js`
3. Capture failures
4. Implement fixes
5. Re-run tests
6. Celebrate when green!

---

**Status**: Ready to Execute
**Approach**: Test-Driven Development (TDD)
**Quality**: Production Grade
