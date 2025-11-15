# Handover 0515e: Integration Testing [CLI]

**Execution Environment**: CLI (Claude Code CLI - Local)
**Duration**: 4-6 hours
**Dependencies**: ALL 0515a-d must be complete and merged
**Branch**: Work on master after all merges

---

## Why CLI?
- Requires live backend and database
- Need to test full stack integration
- WebSocket testing needs real server
- Performance metrics require local environment

---

## Scope

Comprehensive testing of all frontend consolidation work to ensure no regressions and verify improvements.

---

## Test Environment Setup

### Pre-Testing Checklist
```bash
# Ensure all branches merged
git log --oneline -10  # Should show 0515a,b,c,d commits

# Clean environment
cd frontend
rm -rf node_modules
npm install
npm run build  # Should succeed

# Start backend
cd ..
python startup.py --dev

# Start frontend
cd frontend
npm run dev
```

---

## Test Suite

### 1. Component Consolidation Tests (from 0515a)

#### Test: Agent Card Variants
```javascript
// Manual testing in browser
// 1. Navigate to Dashboard
// 2. Verify agent cards display correctly
// 3. Check each variant:
//    - Minimal (in sidebar)
//    - Detailed (in main view)
//    - Job variant (in jobs tab)

// Console verification
document.querySelectorAll('.agent-card').length  // Should show cards
document.querySelectorAll('.agent-card--minimal')  // Should exist
document.querySelectorAll('.agent-card--detailed')  // Should exist
```

#### Test: Status Badges
- Create agents in different states
- Verify badges show correct colors:
  - `pending` → yellow
  - `active` → blue
  - `completed` → green
  - `failed` → red

#### Test: Loading States
- Trigger long-running operations
- Verify single loading spinner type
- No duplicate spinners

#### Test: No Duplicate Components
```bash
# Verify old components deleted
ls frontend/src/components/agents/AgentCard*.vue
# Should only show AgentCard.vue

ls frontend/src/components/common/*Badge*.vue
# Should only show StatusBadge.vue
```

---

### 2. API Centralization Tests (from 0515b)

#### Test: No Direct axios in Components
```bash
# Should return nothing
grep -r "import axios" frontend/src/components/
grep -r "from 'axios'" frontend/src/views/
```

#### Test: Service Layer Works
```javascript
// Browser console test
import { productService } from '@/services/productService'
await productService.list()  // Should return products

import { projectService } from '@/services/projectService'
await projectService.list()  // Should return projects
```

#### Test: Error Handling
1. Stop backend server
2. Try to create a product
3. Should show user-friendly error message
4. No console errors about unhandled promises

#### Test: Auth Token Attachment
1. Open Network tab
2. Make any API call
3. Verify `Authorization: Bearer` header present

#### Test: 401 Handling
1. Manually expire token in localStorage
2. Make API call
3. Should redirect to login

---

### 3. WebSocket V2 Tests (from 0515c)

#### Test: Connection Establishment
```javascript
// Browser console
const wsStore = window.$pinia._s.get('websocket')
console.log(wsStore.isConnected)  // Should be true
console.log(wsStore.connectionState)  // Should be 'connected'
```

#### Test: Real-time Updates
1. Open app in two browser tabs
2. In tab 1: Create an agent job
3. In tab 2: Should see agent appear immediately
4. In tab 1: Update agent status
5. In tab 2: Should see status change immediately

#### Test: Reconnection
1. Open Network tab > WS
2. In console: `wsStore.disconnect()`
3. Wait 2 seconds
4. Should see reconnection attempts with exponential backoff
5. Should reconnect automatically

#### Test: Multi-tenant Isolation
1. Login as User A
2. Create agent job
3. Login as User B in incognito
4. Should NOT see User A's updates

#### Test: Memory Leaks
```javascript
// Check subscription cleanup
// 1. Navigate between pages multiple times
// 2. In console:
const wsStore = window.$pinia._s.get('websocket')
console.log(wsStore.ws.listeners.size)  // Should not grow indefinitely
```

---

### 4. Cleanup Verification (from 0515d)

#### Test: Old Files Removed
```bash
# Should not exist
ls frontend/src/websocket.js  # Should error
ls frontend/src/flowWebSocket.js  # Should error
```

#### Test: No Broken Imports
```bash
# Build should succeed
cd frontend
npm run build

# No errors in browser console
# Check for 404s in Network tab
```

---

### 5. Performance Tests

#### Test: Bundle Size
```bash
cd frontend
npm run build

# Check dist size
du -sh dist/
# Should be ~10% smaller than before consolidation

# Check JS bundle specifically
ls -lah dist/assets/*.js | head -5
# Largest file should be smaller
```

#### Test: Load Time
1. Open Network tab
2. Disable cache
3. Hard refresh
4. Check total load time
5. Should be faster than before

#### Test: Component Render Speed
1. Navigate to page with many components
2. Open Performance tab
3. Start recording
4. Interact with UI
5. Stop recording
6. Check for long tasks (>50ms)

---

## Integration Scenarios

### Scenario 1: Product to Project Flow
1. Create new product
2. Upload vision document
3. Create project from product
4. Launch orchestrator
5. Verify all real-time updates work
6. Check no console errors

### Scenario 2: Agent Job Lifecycle
1. Spawn agent job
2. Verify WebSocket updates status
3. Acknowledge job
4. Complete job
5. Verify UI updates at each step

### Scenario 3: Multi-Component Interaction
1. Open Dashboard
2. Have agents, projects, products visible
3. Make changes
4. All components should update via centralized API
5. No duplicate API calls in Network tab

---

## Regression Testing

### Critical Paths to Test
- [ ] User login/logout
- [ ] Product CRUD operations
- [ ] Project lifecycle (create → activate → complete)
- [ ] Agent job management
- [ ] Vision document upload
- [ ] Settings persistence
- [ ] WebSocket reconnection after network loss

### Edge Cases
- [ ] Large file upload (>10MB)
- [ ] 50+ agents displayed
- [ ] Rapid status changes
- [ ] Network disconnection during operation
- [ ] Token expiration during session

---

## Performance Metrics

Record these metrics:

| Metric | Before | After | Target |
|--------|--------|-------|--------|
| Bundle Size | ? MB | ? MB | -10% |
| Initial Load | ? ms | ? ms | <3s |
| API Response Time | ? ms | ? ms | <200ms |
| WebSocket Latency | ? ms | ? ms | <50ms |
| Component Count | ? | ? | -15 files |
| Memory Usage | ? MB | ? MB | No increase |

---

## Success Criteria

### Functional
- [ ] All CRUD operations work
- [ ] Real-time updates functioning
- [ ] No console errors
- [ ] No broken UI elements
- [ ] Auth flow works

### Performance
- [ ] Bundle size reduced by 10%+
- [ ] Load time improved
- [ ] No memory leaks
- [ ] Smooth animations

### Code Quality
- [ ] No duplicate components
- [ ] No direct axios calls
- [ ] Single WebSocket implementation
- [ ] Centralized API calls

---

## Issues Log

Document any issues found:

| Issue | Severity | Component | Resolution |
|-------|----------|-----------|------------|
| | | | |

---

## Final Checklist

- [ ] All tests pass
- [ ] No regressions found
- [ ] Performance improved
- [ ] Documentation updated
- [ ] Ready for production

---

## Sign-off

After all testing complete:

```bash
git add -A
git commit -m "test: Complete 0515 integration testing

All frontend consolidation work verified:
- Component consolidation working
- API centralization complete
- WebSocket V2 migration successful
- Old files cleaned up
- Performance improved by X%

Ready for production deployment"
```

---

**End of 0515e Scope**