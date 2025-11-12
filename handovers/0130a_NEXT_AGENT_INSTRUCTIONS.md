# NEXT AGENT INSTRUCTIONS - Handover 0130a
**For**: Claude Code CLI (Local Testing & Migration)
**From**: Claude Code (CCW - Implementation Complete)
**Date**: 2025-11-12
**Branch**: `claude/project-0130-011CV3JKpB4XGFChYMTuFeh5`

---

## 🎯 Your Mission

Test and migrate the new WebSocket V2 implementation locally. The V2 system is **COMPLETE and READY** but **NOT YET ACTIVE**. Your job is to:
1. ✅ Test the V2 implementation locally
2. ✅ Execute the migration carefully
3. ✅ Validate everything works
4. ✅ Report results

---

## 📋 Context: What Was Done

### Implementation Complete (2025-11-12)
The previous agent (CCW) implemented WebSocket V2 - a consolidation of the 4-layer WebSocket architecture into a clean 2-layer system.

**New Files Created:**
1. `frontend/src/stores/websocketV2.js` (~700 lines) - Consolidated Pinia store
2. `frontend/src/composables/useWebSocketV2.js` (~250 lines) - Vue composable
3. `frontend/src/stores/websocketIntegrations.js` (~300 lines) - Store integrations
4. `frontend/src/components/WebSocketV2Test.vue` (~250 lines) - Test component

**Documentation:**
- `handovers/0130a_websocket_consolidation.md` - Original handover spec
- `handovers/0130a_MIGRATION_GUIDE.md` - Step-by-step migration instructions
- `handovers/0130a_COMPLETION_SUMMARY.md` - What was built and why

**Status:**
- ✅ Implementation complete
- ✅ 100% feature parity with old system
- ✅ Committed and pushed to branch
- ⚠️ **NOT YET ACTIVE** (old system still in use)

---

## 🔍 Step 1: Understand What You're Working With

### Read These Documents First (in order):
1. **`handovers/0130a_COMPLETION_SUMMARY.md`** (10 min read)
   - Understand what was built
   - Architecture comparison
   - Features preserved
   - Why this was done

2. **`handovers/0130a_MIGRATION_GUIDE.md`** (15 min read)
   - Migration strategy
   - Step-by-step instructions
   - Rollback plan
   - Testing checklist

### Current State:
```
Old System (ACTIVE):
- frontend/src/services/websocket.js
- frontend/src/services/flowWebSocket.js
- frontend/src/stores/websocket.js
- frontend/src/composables/useWebSocket.js

New System (READY, NOT ACTIVE):
- frontend/src/stores/websocketV2.js
- frontend/src/composables/useWebSocketV2.js
- frontend/src/stores/websocketIntegrations.js
- frontend/src/components/WebSocketV2Test.vue
```

---

## 🧪 Step 2: Test V2 Implementation Locally

### 2.1 Start the Application
```bash
# Pull latest changes
git pull origin claude/project-0130-011CV3JKpB4XGFChYMTuFeh5

# Start backend
cd /home/user/GiljoAI_MCP
python startup.py

# Start frontend (new terminal)
cd frontend
npm run dev
```

### 2.2 Add Test Component to Routes
**File**: `frontend/src/router/index.js`

Add test route:
```javascript
{
  path: '/websocket-test',
  name: 'WebSocketTest',
  component: () => import('@/components/WebSocketV2Test.vue'),
  meta: { layout: 'default', requiresAuth: true }
}
```

### 2.3 Test V2 Independently
1. Navigate to `http://localhost:5173/websocket-test`
2. Test all scenarios:
   - ✅ Connection works
   - ✅ Reconnection after server restart
   - ✅ Message sending (connected and disconnected)
   - ✅ Subscription management
   - ✅ Debug panel shows correct info
   - ✅ No console errors

**Record results**: Note any issues in test output

### 2.4 Check Old System Still Works
1. Navigate to main app routes
2. Verify:
   - ✅ Connection status chip shows "Connected"
   - ✅ Real-time updates work (create a project, watch for updates)
   - ✅ No interference between V1 (old) and V2 (test component)

**Key Insight**: Both systems can coexist temporarily for testing

---

## 🚀 Step 3: Execute Migration (When Ready)

### ⚠️ CRITICAL: Read Migration Guide First
Before proceeding, read `handovers/0130a_MIGRATION_GUIDE.md` in full.

### Pre-Migration Checklist
- [ ] V2 tested successfully (Step 2)
- [ ] No issues found in V2 testing
- [ ] Backend is running and stable
- [ ] Git working directory is clean
- [ ] Ready to commit changes

### 3.1 Backup Old Files
```bash
cd /home/user/GiljoAI_MCP/frontend/src

# Backup old implementation
mv services/websocket.js services/websocket.js.backup-0130a
mv services/flowWebSocket.js services/flowWebSocket.js.backup-0130a
mv stores/websocket.js stores/websocket.old.js.backup-0130a
mv composables/useWebSocket.js composables/useWebSocket.old.js.backup-0130a
```

**Verify backups exist:**
```bash
ls -la services/*.backup-0130a stores/*.backup-0130a composables/*.backup-0130a
```

### 3.2 Rename V2 to Production
```bash
# Rename V2 files to production names
mv stores/websocketV2.js stores/websocket.js
mv composables/useWebSocketV2.js composables/useWebSocket.js

# websocketIntegrations.js stays as-is (new file)
```

**Verify renamed files:**
```bash
ls -la stores/websocket.js composables/useWebSocket.js stores/websocketIntegrations.js
```

### 3.3 Update DefaultLayout.vue
**File**: `frontend/src/layouts/DefaultLayout.vue`

**Add import at top:**
```javascript
import { setupWebSocketIntegrations } from '@/stores/websocketIntegrations'
```

**In `onMounted`, after `await wsStore.connect()`:**
```javascript
await wsStore.connect()
console.log('[DefaultLayout] WebSocket connected with automatic cookie authentication')

// ADD THIS LINE:
setupWebSocketIntegrations()
console.log('[DefaultLayout] WebSocket integrations setup complete')
```

### 3.4 Update Component Imports (13 components)

**Components to check** (may not all need changes):
1. `frontend/src/components/ConnectionStatus.vue`
2. `frontend/src/components/navigation/AppBar.vue`
3. `frontend/src/components/ActiveProductDisplay.vue`
4. `frontend/src/components/agent-flow/FlowCanvas.vue`
5. `frontend/src/components/orchestration/AgentCardGrid.vue`
6. `frontend/src/components/projects/AgentCardEnhanced.vue`
7. `frontend/src/components/projects/LaunchTab.vue`
8. `frontend/src/components/projects/ProjectTabs.vue`
9. `frontend/src/components/products/OrchestratorLaunchButton.vue`
10. `frontend/src/components/SubAgentTimelineHorizontal.vue`
11. `frontend/src/components/SubAgentTree.vue`
12. `frontend/src/layouts/DefaultLayout.vue` (already updated above)

**Search and replace pattern:**

Remove these imports (if they exist):
```javascript
import websocketService from '@/services/websocket'
import flowWebSocketService from '@/services/flowWebSocket'
```

Components should use either:
```javascript
import { useWebSocketStore } from '@/stores/websocket' // Store approach
// OR
import { useWebSocket } from '@/composables/useWebSocket' // Composable approach
```

**Use grep to find components:**
```bash
cd /home/user/GiljoAI_MCP/frontend/src
grep -r "websocketService\|flowWebSocketService" components/ layouts/ --include="*.vue"
```

**Update each component as needed**

### 3.5 Remove Test Route (cleanup)
**File**: `frontend/src/router/index.js`

Remove the test route we added in Step 2.2.

---

## ✅ Step 4: Validate Migration

### 4.1 Application Startup
```bash
# Restart dev server
cd /home/user/GiljoAI_MCP/frontend
npm run dev
```

**Check:**
- [ ] No build errors
- [ ] No console errors on app load
- [ ] App loads successfully

### 4.2 WebSocket Connection
**Open browser**: `http://localhost:5173`

**Check:**
- [ ] Connection status chip shows "Connected" (top right in AppBar)
- [ ] No console errors related to WebSocket
- [ ] Network tab shows WebSocket connection established

### 4.3 Real-Time Updates Test

**Test Projects:**
1. Create a new project
2. Watch for real-time updates in UI
3. Check console for WebSocket messages

**Test Agent Jobs:**
1. Spawn an orchestrator
2. Watch for agent status updates
3. Check AgentCard components update in real-time

**Test Messages:**
1. Navigate to messages view
2. Create a new message
3. Verify real-time update

### 4.4 Reconnection Test
1. Stop backend: `Ctrl+C` in terminal running `python startup.py`
2. Watch connection status chip change to "Disconnected" or "Reconnecting"
3. Restart backend: `python startup.py`
4. Watch connection status chip change to "Connected"
5. Verify toast notifications appear

### 4.5 Memory Leak Test (Chrome DevTools)
1. Open Chrome DevTools → Performance → Memory
2. Take heap snapshot (Snapshot 1)
3. Navigate between views 20 times (projects → agents → messages → repeat)
4. Take another heap snapshot (Snapshot 2)
5. Compare sizes - should be similar (±5 MB)
6. Check for detached DOM nodes - should be minimal

### 4.6 Component Cleanup Test
1. Open component that uses WebSocket (e.g., AgentCardEnhanced.vue)
2. Open Chrome DevTools → Sources → Set breakpoint in `onUnmounted`
3. Navigate away from that component
4. Verify `onUnmounted` is called
5. Check console for cleanup messages: `[useWebSocket] Component cleanup complete`

### 4.7 Debug Panel Test
1. Click connection status chip (top right)
2. Verify debug panel opens
3. Check all sections:
   - Connection Status (should show connected)
   - Statistics (messages sent/received)
   - Active Subscriptions (should list subscriptions)
   - Recent Events (should show connection history)
4. Try test actions (Force Reconnect, Send Test, etc.)

---

## 📊 Step 5: Report Results

### Success Criteria
**The migration is successful if ALL are true:**
- ✅ All tests in Step 4 pass
- ✅ Zero console errors
- ✅ Real-time updates work for all entity types
- ✅ Reconnection works correctly
- ✅ No memory leaks detected
- ✅ All 13 components work correctly

### Create Test Report
**File**: `handovers/0130a_TEST_RESULTS.md`

```markdown
# Handover 0130a Test Results

**Tested By**: Claude Code CLI (Local)
**Date**: [DATE]
**Branch**: claude/project-0130-011CV3JKpB4XGFChYMTuFeh5

## Test Environment
- OS: [OS]
- Node version: [VERSION]
- Python version: [VERSION]
- Browser: Chrome [VERSION]

## Test Results

### ✅ Step 2: V2 Testing (Pre-Migration)
- [ ] Connection works: PASS/FAIL
- [ ] Reconnection works: PASS/FAIL
- [ ] Message sending works: PASS/FAIL
- [ ] Subscriptions work: PASS/FAIL
- [ ] No console errors: PASS/FAIL
- [ ] Notes: [ANY OBSERVATIONS]

### ✅ Step 4: Migration Validation
- [ ] 4.1 Application startup: PASS/FAIL
- [ ] 4.2 WebSocket connection: PASS/FAIL
- [ ] 4.3 Real-time updates: PASS/FAIL
- [ ] 4.4 Reconnection test: PASS/FAIL
- [ ] 4.5 Memory leak test: PASS/FAIL
- [ ] 4.6 Component cleanup test: PASS/FAIL
- [ ] 4.7 Debug panel test: PASS/FAIL

## Issues Found
[List any issues, errors, or unexpected behavior]

## Overall Result
**PASS** / **FAIL**

## Recommendations
[Next steps, concerns, or observations]
```

---

## 🔄 Step 6: Rollback (If Needed)

### If ANY Test Fails:

**Option 1: Git Rollback**
```bash
cd /home/user/GiljoAI_MCP/frontend/src
git checkout -- stores/websocket.js composables/useWebSocket.js layouts/DefaultLayout.vue
# Restore any other changed components
```

**Option 2: Restore from Backups**
```bash
cd /home/user/GiljoAI_MCP/frontend/src

# Remove V2 files
mv stores/websocket.js stores/websocketV2.js
mv composables/useWebSocket.js composables/useWebSocketV2.js

# Restore backups
mv services/websocket.js.backup-0130a services/websocket.js
mv services/flowWebSocket.js.backup-0130a services/flowWebSocket.js
mv stores/websocket.old.js.backup-0130a stores/websocket.js
mv composables/useWebSocket.old.js.backup-0130a composables/useWebSocket.js
```

**Restart and verify old system works:**
```bash
npm run dev
```

**Document what failed:**
Create `handovers/0130a_ROLLBACK_REPORT.md` with:
- What test failed
- Error messages
- Steps to reproduce
- Screenshots if relevant

---

## 📝 Step 7: Commit Results

### If Migration Successful:
```bash
cd /home/user/GiljoAI_MCP

# Stage all changes
git add frontend/src/stores/websocket.js
git add frontend/src/composables/useWebSocket.js
git add frontend/src/stores/websocketIntegrations.js
git add frontend/src/layouts/DefaultLayout.vue
git add frontend/src/router/index.js  # If modified
git add handovers/0130a_TEST_RESULTS.md

# Commit
git commit -m "feat(0130a): WebSocket V2 Migration Complete - All Tests Pass

- Renamed V2 files to production names
- Backed up old 4-layer implementation
- Updated DefaultLayout.vue with integration setup
- Tested all WebSocket features: connection, reconnection, real-time updates
- Memory leak test: PASS
- All 13 components working correctly
- Zero console errors

Tests performed:
- Application startup
- WebSocket connection and reconnection
- Real-time updates (projects, agents, messages, tasks)
- Memory leak testing (Chrome DevTools)
- Component cleanup validation
- Debug panel functionality

Old system backed up:
- services/websocket.js.backup-0130a
- services/flowWebSocket.js.backup-0130a
- stores/websocket.old.js.backup-0130a
- composables/useWebSocket.old.js.backup-0130a

Architecture improved:
- 4 layers → 2 layers + integrations
- Single reconnection system
- Centralized subscriptions
- Memory leak prevention built-in

Handover: 0130a - WebSocket Consolidation
Status: COMPLETE and ACTIVE
"

# Push to branch
git push
```

### If Migration Failed:
```bash
cd /home/user/GiljoAI_MCP

# Stage rollback report
git add handovers/0130a_ROLLBACK_REPORT.md

# Commit rollback
git commit -m "docs(0130a): Migration rollback - issues found during testing

[Describe issue briefly]

See handovers/0130a_ROLLBACK_REPORT.md for details.

Migration was rolled back to old 4-layer system.
V2 implementation remains available for future retry.
"

# Push to branch
git push
```

---

## 🎓 Key Points for Next Agent

### Architecture Understanding
- **Old**: 4 layers (websocket.js → flowWebSocket.js → stores/websocket.js → useWebSocket.js)
- **New**: 2 layers (stores/websocket.js + composables/useWebSocket.js) + websocketIntegrations.js
- **Why**: Eliminate duplicate systems, improve maintainability, prevent memory leaks

### Critical Files
- **Pinia Store**: `stores/websocket.js` (formerly websocketV2.js)
- **Composable**: `composables/useWebSocket.js` (formerly useWebSocketV2.js)
- **Integrations**: `stores/websocketIntegrations.js` (NEW - must be called in DefaultLayout)

### Integration Setup
**MUST call** `setupWebSocketIntegrations()` in `DefaultLayout.vue` after WebSocket connects.
This is **NOT automatic** - it's an explicit setup function that routes WebSocket messages to other stores.

### Memory Leaks
The new composable (`useWebSocket.js`) **automatically cleans up** on component unmount:
- Unsubscribes from all subscriptions
- Removes all event handlers
- No manual cleanup needed in components

### Debugging
- Click connection status chip → Opens debug panel
- Shows: connection info, stats, subscriptions, event history
- Has test actions: force reconnect, send test message, etc.

### Safety Net
- Old system backed up with `.backup-0130a` suffix
- Easy rollback via git or backup restoration
- V2 can coexist with V1 temporarily for testing
- No data loss risk - frontend only changes

---

## 🆘 If You Get Stuck

### Common Issues

**Issue 1: "Cannot find module '@/stores/websocketIntegrations'"**
- Check file exists: `frontend/src/stores/websocketIntegrations.js`
- Check import in DefaultLayout.vue is correct
- Restart dev server: `npm run dev`

**Issue 2: WebSocket not connecting**
- Check backend is running: `python startup.py`
- Check WebSocket URL in browser Network tab
- Check console for error messages
- Verify `wsStore.connect()` is called in DefaultLayout.vue

**Issue 3: Real-time updates not working**
- Check `setupWebSocketIntegrations()` is called in DefaultLayout.vue
- Check console for WebSocket message routing
- Verify subscriptions are being created (debug panel)
- Check backend is sending WebSocket messages

**Issue 4: Memory leaks detected**
- Check `onUnmounted` is being called in components
- Verify cleanup messages in console: `[useWebSocket] Component cleanup complete`
- Check Chrome DevTools → Memory → Detached DOM nodes
- Report issue - may need to investigate specific component

**Issue 5: Console errors after migration**
- Check error message carefully
- Verify all imports are correct (no references to old service files)
- Check component is using `useWebSocket()` or `useWebSocketStore()` correctly
- Consider rollback if critical error

### Where to Find Help
1. **Migration Guide**: `handovers/0130a_MIGRATION_GUIDE.md`
2. **Completion Summary**: `handovers/0130a_COMPLETION_SUMMARY.md`
3. **Original Handover**: `handovers/0130a_websocket_consolidation.md`
4. **Roadmap Context**: `handovers/REFACTORING_ROADMAP_0120-0129.md`

### Decision Points
After successful migration, you'll need to decide:
1. **Execute 0130b-d?** (Remove flowWebSocket, merge duplicate components, centralize API calls)
2. **Skip to 0131?** (Production Readiness - monitoring, rate limiting, OSS files, deployment)

**Recommendation**: Skip to 0131 (Production Readiness is higher priority than frontend polish)

---

## ✅ Success! What Next?

### After Successful Migration:
1. **Monitor for 1 week** - Watch for any issues in production use
2. **Delete backups** - After 1 week of stability
3. **Archive handover** - Move to `handovers/completed/`
4. **Decision**: Execute 0130b-d OR skip to 0131 Production Readiness

### Update Roadmap:
Update `handovers/REFACTORING_ROADMAP_0120-0129.md`:
- Mark 0130a as "✅ COMPLETE and ACTIVE"
- Add migration date and test results
- Document decision on 0130b-d

---

## 📋 Final Checklist

Before you start:
- [ ] Read all documentation (completion summary, migration guide)
- [ ] Understand old vs new architecture
- [ ] Backend is running
- [ ] Frontend dev server is running
- [ ] Git working directory is clean

During testing:
- [ ] V2 tested independently (Step 2)
- [ ] No issues found in V2 testing
- [ ] Migration executed (Step 3)
- [ ] All validation tests pass (Step 4)
- [ ] Test results documented (Step 5)

After migration:
- [ ] All changes committed
- [ ] Changes pushed to branch
- [ ] Test results committed
- [ ] Roadmap updated
- [ ] Next steps decided (0130b-d or 0131)

---

**Good luck! The V2 implementation is solid and ready. Take your time, test thoroughly, and don't hesitate to rollback if needed.**

**Remember**: The current system works perfectly. We're improving architecture, not fixing bugs. Quality over speed!

---

**Created**: 2025-11-12
**For**: Claude Code CLI (Local Testing & Migration)
**From**: Claude Code CCW (Implementation Complete)
**Status**: Ready for Execution
