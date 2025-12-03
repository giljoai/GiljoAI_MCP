# Handover 0242c: Integration Testing & Polish

**Status**: 🟡 Pending
**Priority**: P1 (High)
**Estimated Effort**: 2-3 hours
**Tool**: CLI (Local) - Integration testing with backend server
**Subagent**: frontend-tester (E2E testing, cross-browser validation)
**Dependencies**: ✅ 0242a AND 0242b must be complete first

---

## Executive Summary

Comprehensive end-to-end integration testing for the 0242 GUI redesign series. Verify complete workflows (Stage → Launch → Implement → Messages), WebSocket event integration, cross-browser compatibility, and performance validation.

**This handover focuses on verification and bug fixing**, NOT new features.

**Goals**:
1. E2E workflow validation (Stage → Launch → Implement → Messages)
2. WebSocket event verification (mission_updated, agent:created, agent:updated)
3. Cross-browser compatibility (Chrome, Firefox, Edge)
4. Performance validation (bundle size, render time, latency)
5. Bug fixing buffer (address any issues found)

---

## Test Environment Setup

### Prerequisites
1. **Backend Server Running**:
   ```bash
   python startup.py
   # Expected: API server running on http://10.1.0.164:7274
   ```

2. **Frontend Dev Server Running**:
   ```bash
   cd frontend
   npm install  # Ensure dependencies installed
   npm run dev
   # Expected: Dev server running on http://10.1.0.164:5173
   ```

3. **Test Database** (use existing `giljo_mcp` database):
   ```bash
   # Verify database connection
   PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "\dt"
   # Expected: List of tables (mcp_projects, mcp_agent_jobs, etc.)
   ```

4. **Test Project** (use existing project or create new):
   ```bash
   # Create test project via UI:
   # 1. Navigate to http://10.1.0.164:7274/projects
   # 2. Click "New Project"
   # 3. Name: "0242c Integration Test"
   # 4. Description: "Test project for 0242c E2E validation"
   # 5. Save project ID for testing
   ```

---

## Detailed Test Scenarios

### Scenario 1: E2E Workflow - Fresh Project (Stage → Launch → Implement)

**Duration**: 20 minutes

**Objective**: Verify complete workflow from project creation to agent monitoring.

**Steps**:

1. **Navigate to Launch Tab**:
   ```
   URL: http://10.1.0.164:7274/projects/{project-id}?via=launch
   ```

2. **Verify Initial State**:
   - [ ] Project Description panel shows `project.description`
   - [ ] Orchestrator Mission panel shows document icon (empty state)
   - [ ] Agent Team panel shows "No agents yet" (empty state)
   - [ ] "Stage project" button: Yellow outlined, top left
   - [ ] "Waiting:" status: Center, yellow italic
   - [ ] "Launch jobs" button: Grey (disabled), top right

3. **Click "Stage Project" Button**:
   - [ ] Clipboard copy modal appears
   - [ ] Modal shows "Thin Client Prompt" text
   - [ ] Modal has "Copy to Clipboard" button
   - [ ] Click "Copy to Clipboard"
   - [ ] Success message: "Prompt copied to clipboard"

4. **Verify Mission Panel Update** (WebSocket event):
   - [ ] Orchestrator Mission panel updates with mission text
   - [ ] Document icon disappears
   - [ ] Mission text appears in monospace font
   - [ ] "Copy" button appears in mission panel
   - [ ] Mission text is scrollable (if long)

5. **Verify Launch Button Enabled**:
   - [ ] "Launch jobs" button changes to yellow (enabled)
   - [ ] Button text: "Launch jobs"
   - [ ] Button position: Top right

6. **Click "Launch Jobs" Button**:
   - [ ] Navigation to Implement Tab: `?via=jobs`
   - [ ] URL updates to `/projects/{project-id}?via=jobs`

7. **Verify Implement Tab Initial State**:
   - [ ] Table container visible with border
   - [ ] Table headers: 9 columns (Agent Type, Agent ID, Agent Status, etc.)
   - [ ] Orchestrator row appears
   - [ ] Orchestrator Agent Type: "Or" avatar + "Orchestrator" text
   - [ ] Orchestrator Agent ID: Full UUID (grey monospace)
   - [ ] Orchestrator Agent Status: "Waiting..." (yellow italic)
   - [ ] Claude toggle section visible (OFF state, grey dot)

8. **Wait for Agent Creation** (WebSocket events):
   - [ ] New agent rows appear (Analyzer, Implementor, Tester)
   - [ ] Each agent has correct avatar color
   - [ ] Each agent has unique UUID
   - [ ] Each agent status shows "Waiting..." initially

9. **Monitor Status Updates** (WebSocket events):
   - [ ] Orchestrator status changes to "Working..."
   - [ ] Agent statuses update dynamically (NOT hardcoded)
   - [ ] Status text remains yellow italic
   - [ ] Status changes reflected in real-time

**Expected Timeline**:
- Stage → Mission appears: <5 seconds
- Launch → Navigate to Implement: <1 second
- Agent creation events: 5-30 seconds (depends on orchestrator)
- Status updates: Real-time (<1 second latency)

**Failure Conditions**:
- Mission text does not appear after staging (WebSocket issue)
- Launch button remains grey after mission appears (reactivity issue)
- Agent rows do not appear after launch (WebSocket issue)
- Status column shows hardcoded "Waiting." (NOT dynamic)

---

### Scenario 2: WebSocket Event Verification

**Duration**: 10 minutes

**Objective**: Verify WebSocket events trigger UI updates correctly.

**Steps**:

1. **Open DevTools**:
   - Press `F12` or right-click → Inspect
   - Navigate to **Network** tab
   - Click **WS** (WebSocket filter)

2. **Verify WebSocket Connection**:
   - [ ] WebSocket connection established (Status: 101 Switching Protocols)
   - [ ] URL: `ws://10.1.0.164:7274/socket.io/...`
   - [ ] Connection state: **Open**

3. **Trigger "Stage Project"**:
   - [ ] Click "Stage project" button
   - [ ] In WS tab, filter for `mission_updated` event
   - [ ] Verify payload contains `mission` field with thin client prompt text

4. **Verify Mission Panel Update**:
   - [ ] Mission text appears in Orchestrator Mission panel
   - [ ] Text matches payload from `mission_updated` event
   - [ ] Update occurs within 1 second of event

5. **Trigger "Launch Jobs"**:
   - [ ] Click "Launch jobs" button
   - [ ] In WS tab, filter for `agent:created` events
   - [ ] Verify multiple events fire (Orchestrator, Analyzer, Implementor, Tester)

6. **Verify Agent Cards Appear** (Launch Tab):
   - [ ] Navigate back to Launch Tab (`?via=launch`)
   - [ ] Agent Team panel shows agent cards
   - [ ] Cards match agents from `agent:created` events
   - [ ] No duplicate cards (Set prevents duplicates)

7. **Verify Agent Rows Appear** (Implement Tab):
   - [ ] Navigate to Implement Tab (`?via=jobs`)
   - [ ] Table shows all agent rows
   - [ ] Rows match agents from `agent:created` events

8. **Monitor `agent:updated` Events**:
   - [ ] In WS tab, filter for `agent:updated` events
   - [ ] Verify events fire periodically (status changes)
   - [ ] Verify payload contains `id` and `status` fields

9. **Verify Status Column Updates**:
   - [ ] Status column updates dynamically
   - [ ] Status text matches payload from `agent:updated` event
   - [ ] Update occurs within 1 second of event
   - [ ] Yellow italic styling preserved

**WebSocket Event Payloads** (expected format):

```json
// mission_updated event
{
  "event": "mission_updated",
  "data": {
    "project_id": "uuid",
    "mission": "Thin client prompt text..."
  }
}

// agent:created event
{
  "event": "agent:created",
  "data": {
    "id": "uuid",
    "type": "Orchestrator",
    "status": "Waiting...",
    "project_id": "uuid"
  }
}

// agent:updated event
{
  "event": "agent:updated",
  "data": {
    "id": "uuid",
    "status": "Working...",
    "messages_sent": 5,
    "messages_read": 3
  }
}
```

**Failure Conditions**:
- WebSocket connection fails (Status: Error)
- Events fire but UI does not update (handler issue)
- Agent rows appear but status never updates (hardcoded text issue)
- Duplicate agent cards appear (Set not working)

---

### Scenario 3: Cross-Browser Compatibility

**Duration**: 30 minutes

**Objective**: Verify GUI renders correctly in Chrome, Firefox, and Edge.

**Test Matrix**:

| Browser | Version | OS | Tested By |
|---------|---------|----|-----------|
| Chrome | 130+ | Windows | Frontend-Tester |
| Firefox | 120+ | Windows | Frontend-Tester |
| Edge | 130+ | Windows | Frontend-Tester |

**Steps for Each Browser**:

1. **Launch Tab Layout**:
   - [ ] Unified container border visible (2px, 16px radius)
   - [ ] Three-panel grid renders correctly (equal widths)
   - [ ] Top action bar: Stage left, Waiting center, Launch right
   - [ ] Button colors correct (Stage yellow outlined, Launch grey/yellow)
   - [ ] Orchestrator avatar: Tan color (#d4a574)
   - [ ] Panel headers: NOT uppercase

2. **Implement Tab Layout**:
   - [ ] Table container border visible (2px, 16px radius)
   - [ ] Table columns: 9 headers, correct widths
   - [ ] Agent Type column: Avatar + name, correct alignment
   - [ ] Agent ID column: Full UUID, monospace font
   - [ ] Agent Status column: Yellow italic text
   - [ ] Action icons: Play/Folder yellow, Info white
   - [ ] Claude toggle: Correct layout (label, indicator, status)

3. **WebSocket Events** (all browsers):
   - [ ] `mission_updated` event triggers mission panel update
   - [ ] `agent:created` event triggers agent row/card creation
   - [ ] `agent:updated` event triggers status column update

4. **Clipboard Copy** (all browsers):
   - [ ] Click "Copy" button in mission panel
   - [ ] Success message appears
   - [ ] Paste clipboard content → Verify mission text copied

5. **Console Errors** (all browsers):
   - [ ] Open DevTools → Console
   - [ ] Verify no errors logged
   - [ ] Verify no warnings (acceptable: dev-mode warnings)

**Cross-Browser Compatibility Checklist**:
- [ ] Chrome: All tests passing
- [ ] Firefox: All tests passing
- [ ] Edge: All tests passing
- [ ] No layout differences between browsers
- [ ] No color rendering differences
- [ ] No font rendering issues
- [ ] WebSocket events work in all browsers

**Failure Conditions**:
- Layout breaks in specific browser (CSS compatibility issue)
- Colors render differently (color space issue)
- WebSocket events fail in specific browser (browser API issue)
- Clipboard copy fails in specific browser (fallback not working)

---

### Scenario 4: Performance Validation

**Duration**: 20 minutes

**Objective**: Verify bundle size, render time, and WebSocket latency meet targets.

**Steps**:

1. **Build Frontend for Production**:
   ```bash
   cd frontend
   npm run build
   # Expected: Build completes without errors
   # Output: dist/ folder created
   ```

2. **Check Bundle Size**:
   ```bash
   # Windows PowerShell
   cd frontend\dist\assets
   dir *.js
   # Expected: Main bundle < 700 KB gzipped
   ```

   **Expected Output**:
   ```
   index-abc123.js         520 KB
   vendor-def456.js        180 KB
   LaunchTab-ghi789.js      45 KB
   JobsTab-jkl012.js        50 KB
   ```

   **Validation**:
   - [ ] Total JS bundle size < 800 KB (uncompressed)
   - [ ] Gzipped size < 700 KB (estimate: ~30% compression)
   - [ ] No single file > 600 KB

3. **Check CSS Bundle Size**:
   ```bash
   cd frontend\dist\assets
   dir *.css
   # Expected: CSS bundle < 200 KB
   ```

   **Validation**:
   - [ ] Total CSS bundle size < 200 KB
   - [ ] Vuetify CSS included (expected ~100 KB)

4. **Initial Page Load Performance**:
   - Open Chrome DevTools → **Performance** tab
   - Click **Record** button
   - Navigate to Launch Tab: `http://10.1.0.164:7274/projects/{id}?via=launch`
   - Wait 3 seconds
   - Click **Stop** button

   **Metrics to Check**:
   - [ ] **First Contentful Paint (FCP)**: < 1 second
   - [ ] **Largest Contentful Paint (LCP)**: < 2 seconds
   - [ ] **Time to Interactive (TTI)**: < 3 seconds
   - [ ] **Total Blocking Time (TBT)**: < 300ms

5. **Component Render Time**:
   - Open Chrome DevTools → **Performance** tab
   - Click **Record** button
   - Click "Launch jobs" button (navigate to Implement Tab)
   - Wait 2 seconds
   - Click **Stop** button

   **Metrics to Check**:
   - [ ] **Initial render**: < 500ms
   - [ ] **Table render** (9 columns, 4 rows): < 200ms
   - [ ] **No layout shifts** (Cumulative Layout Shift = 0)

6. **WebSocket Event Latency**:
   - Open Chrome DevTools → **Console**
   - Run this script:
     ```javascript
     // Measure mission_updated latency
     const start = Date.now()
     socket.on('mission_updated', (data) => {
       const latency = Date.now() - start
       console.log(`mission_updated latency: ${latency}ms`)
     })
     // Trigger "Stage project" button
     ```

   **Expected Latency**:
   - [ ] `mission_updated` event: < 100ms
   - [ ] `agent:created` event: < 100ms
   - [ ] `agent:updated` event: < 100ms

7. **Memory Leak Detection**:
   - Open Chrome DevTools → **Memory** tab
   - Take heap snapshot (Snapshot 1)
   - Navigate between Launch/Implement tabs 10 times
   - Take heap snapshot (Snapshot 2)
   - Compare snapshots

   **Validation**:
   - [ ] Memory increase < 10 MB after 10 navigations
   - [ ] No detached DOM nodes (indicates memory leak)
   - [ ] WebSocket connections properly closed

**Performance Targets** (summary):
| Metric | Target | Acceptable | Failure |
|--------|--------|------------|---------|
| Bundle size (gzipped) | < 700 KB | < 800 KB | > 800 KB |
| First Contentful Paint | < 1s | < 1.5s | > 2s |
| Time to Interactive | < 3s | < 4s | > 5s |
| Component render | < 500ms | < 700ms | > 1s |
| WebSocket latency | < 100ms | < 200ms | > 300ms |
| Memory increase | < 10 MB | < 20 MB | > 30 MB |

**Failure Conditions**:
- Bundle size exceeds 800 KB (optimization needed)
- Initial render > 2 seconds (blocking issue)
- WebSocket latency > 300ms (network issue)
- Memory leak detected (detached nodes, unclosed connections)

---

### Scenario 5: Bug Fixing Buffer

**Duration**: 30-90 minutes (variable)

**Objective**: Address any issues found during E2E testing, WebSocket verification, cross-browser testing, or performance validation.

**Bug Triage Process**:

1. **Document Bug** (create issue):
   ```markdown
   **Bug Title**: [0242c] [Component] Brief description

   **Steps to Reproduce**:
   1. Navigate to...
   2. Click...
   3. Observe...

   **Expected Behavior**: ...
   **Actual Behavior**: ...
   **Screenshots**: (attach if applicable)
   **Browser**: Chrome 130 / Firefox 120 / Edge 130
   **Severity**: P0 (blocker) / P1 (high) / P2 (medium) / P3 (low)
   ```

2. **Prioritize Bugs**:
   - **P0 (Blocker)**: Prevents workflow completion (e.g., WebSocket connection fails)
   - **P1 (High)**: Major visual/functional issue (e.g., status column hardcoded)
   - **P2 (Medium)**: Minor visual issue (e.g., border color slightly off)
   - **P3 (Low)**: Cosmetic issue (e.g., tooltip text unclear)

3. **Fix Priority Order**:
   - P0 bugs: Fix immediately (blocks completion)
   - P1 bugs: Fix in this handover (impacts user experience)
   - P2 bugs: Fix if time permits (polish)
   - P3 bugs: Defer to future handover (not critical)

**Common Bug Categories**:

**Category 1: WebSocket Event Issues**
- **Symptom**: Mission text does not appear after staging
- **Likely Cause**: `mission_updated` event handler not firing
- **Fix**: Check socket event registration in `<script>` (may need to uncomment)

**Category 2: Hardcoded Status Text**
- **Symptom**: Agent Status column always shows "Waiting."
- **Likely Cause**: Template still has hardcoded text instead of `{{ agent.status }}`
- **Fix**: Replace `<td>Waiting.</td>` with `<td>{{ agent.status || 'Waiting...' }}</td>`

**Category 3: Layout Misalignment**
- **Symptom**: Table columns not matching screenshot proportions
- **Likely Cause**: CSS Grid template columns incorrect
- **Fix**: Adjust `grid-template-columns` values to match Task 2 proportions

**Category 4: Icon Color Issues**
- **Symptom**: Info icon is yellow instead of white
- **Likely Cause**: Icon color attribute incorrect
- **Fix**: Change `color="yellow-darken-2"` to `color="white"` for Info icon

**Category 5: Cross-Browser Issues**
- **Symptom**: Layout breaks in Firefox
- **Likely Cause**: Browser-specific CSS rendering
- **Fix**: Add vendor prefixes or use CSS fallbacks

**Bug Fix Workflow**:
1. Identify bug category
2. Locate affected file (`LaunchTab.vue` or `JobsTab.vue`)
3. Verify issue in DevTools (inspect element, check styles)
4. Apply fix (modify template or style section only)
5. Test fix locally (`npm run dev`)
6. Run unit tests (`npm test`)
7. Verify fix in all browsers (Chrome, Firefox, Edge)
8. Document fix in commit message

**Bug Fix Commit Template**:
```bash
git add frontend/src/components/projects/[Component].vue
git commit -m "fix(0242c): [brief description]

Issue: [describe problem]
Root Cause: [explain why it happened]
Fix: [explain what was changed]

Testing:
- Manual test: [describe verification]
- Unit tests: [number] passing
- Cross-browser: Chrome/Firefox/Edge verified

Handover: 0242c
Severity: P0/P1/P2/P3"
```

---

## Success Criteria

### E2E Workflow
- ✅ Fresh project workflow (Stage → Launch → Implement) completes without errors
- ✅ Mission text appears within 5 seconds of staging
- ✅ Launch button enables after mission appears
- ✅ Navigation to Implement Tab successful
- ✅ Agent rows appear within 30 seconds of launch

### WebSocket Events
- ✅ `mission_updated` event verified in DevTools WS tab
- ✅ `agent:created` events verified (multiple agents)
- ✅ `agent:updated` events verified (status changes)
- ✅ Mission panel updates on `mission_updated` event
- ✅ Agent rows/cards appear on `agent:created` event
- ✅ Status column updates on `agent:updated` event

### Cross-Browser Compatibility
- ✅ Chrome: All tests passing, no layout issues
- ✅ Firefox: All tests passing, no layout issues
- ✅ Edge: All tests passing, no layout issues
- ✅ No console errors in any browser
- ✅ Clipboard copy works in all browsers

### Performance
- ✅ Bundle size < 700 KB (gzipped)
- ✅ First Contentful Paint < 1 second
- ✅ Time to Interactive < 3 seconds
- ✅ Component render < 500ms
- ✅ WebSocket latency < 100ms
- ✅ No memory leaks detected

### Bug Fixing
- ✅ All P0 bugs fixed (blockers)
- ✅ All P1 bugs fixed (high priority)
- ✅ P2 bugs fixed if time permits
- ✅ All fixes verified in cross-browser testing
- ✅ All unit tests passing after fixes (78 total: 29 Launch + 49 Implement)

---

## Files to Modify (Bug Fixes Only)

### If Bugs Found
- **`frontend/src/components/projects/LaunchTab.vue`** (bug fixes only)
- **`frontend/src/components/projects/JobsTab.vue`** (bug fixes only)
- **Test files** (update if behavior changes due to bug fixes)

### Do NOT Modify
- Backend code (unless WebSocket issue confirmed server-side)
- Database schema
- Service layer logic

---

## Testing Commands

```bash
# Frontend directory
cd frontend

# Install dependencies (if needed)
npm install

# Run full test suite (0242a + 0242b)
npm test

# Run with coverage
npm test --coverage

# Expected output:
# Test Files  2 passed (2)
#      Tests  78 passed (78)
#   Coverage  >80% (target)

# Build for production
npm run build

# Check bundle sizes
cd dist/assets
dir *.js    # Windows
ls -lh *.js # Linux/Mac

# Lint check
npm run lint

# Development server (manual testing)
npm run dev
```

---

## Manual Testing Checklist

**Before Starting**:
- [ ] Backend server running (`python startup.py`)
- [ ] Frontend dev server running (`npm run dev`)
- [ ] Test project created (note project ID)
- [ ] Browser DevTools open (Console + Network tabs)

**Launch Tab (0242a)**:
- [ ] Unified container border (2px, rgba, 16px radius)
- [ ] Three-panel grid (equal widths, 24px gap)
- [ ] Top action bar (Stage left, Waiting center, Launch right)
- [ ] Button colors (Stage yellow outlined, Launch grey→yellow)
- [ ] Orchestrator avatar (tan #d4a574)
- [ ] Mission panel empty state (document icon)
- [ ] Mission panel mission state (text + copy button)

**Implement Tab (0242b)**:
- [ ] Table container border (2px, rgba, 16px radius)
- [ ] Table columns (9 headers, correct proportions)
- [ ] Agent Type column (avatar + name)
- [ ] Agent ID column (full UUID, monospace)
- [ ] Agent Status column (yellow italic, DYNAMIC)
- [ ] Action icons (Play/Folder yellow, Info white)
- [ ] Claude toggle (green dot ON, grey dot OFF)

**WebSocket Events**:
- [ ] `mission_updated` event fires (DevTools WS tab)
- [ ] Mission panel updates (LaunchTab)
- [ ] `agent:created` events fire (DevTools WS tab)
- [ ] Agent rows appear (JobsTab)
- [ ] Agent cards appear (LaunchTab Agent Team panel)
- [ ] `agent:updated` events fire (DevTools WS tab)
- [ ] Status column updates (JobsTab)

**Cross-Browser** (repeat above in each browser):
- [ ] Chrome: All checks passing
- [ ] Firefox: All checks passing
- [ ] Edge: All checks passing

**Performance**:
- [ ] Bundle size < 700 KB (gzipped)
- [ ] First Contentful Paint < 1s
- [ ] Component render < 500ms
- [ ] WebSocket latency < 100ms

---

## Rollback Plan

If critical issues (P0 blockers) cannot be resolved:

1. **Document Issue**:
   ```bash
   # Create GitHub issue
   Title: "[0242c] Critical Issue - Cannot Complete Testing"
   Description: [detailed problem description]
   Severity: P0 (Blocker)
   ```

2. **Rollback to 0241 State**:
   ```bash
   git stash save "0242c testing in-progress"
   git checkout handovers/completed/0241_emergency_gui_fix_match_screenshots-C.md
   git checkout frontend/src/components/projects/LaunchTab.vue
   git checkout frontend/src/components/projects/JobsTab.vue
   ```

3. **Notify Team**:
   - Post in project chat: "0242c blocked by [issue], rolled back to 0241"
   - Tag relevant developers for investigation

4. **Investigation**:
   - Root cause analysis (WebSocket server issue? Browser compatibility?)
   - Determine if issue is frontend (0242 series) or backend
   - Plan remediation approach

---

## Next Steps

**Upon Completion of 0242c**:
1. ✅ All E2E scenarios passing
2. ✅ WebSocket events verified in DevTools
3. ✅ Cross-browser compatible (Chrome, Firefox, Edge)
4. ✅ Performance targets met
5. ✅ All P0 and P1 bugs fixed
6. ✅ All 78 tests passing (29 Launch + 49 Implement)
7. ✅ Git commit created:
   ```bash
   git add frontend/src/components/projects/LaunchTab.vue
   git add frontend/src/components/projects/JobsTab.vue
   git add frontend/tests/unit/components/projects/*.spec.js
   git commit -m "test(0242c): Integration testing complete

   E2E Workflows:
   - Stage → Launch → Implement (verified)
   - WebSocket events (mission_updated, agent:created, agent:updated)
   - Clipboard copy functionality

   Cross-Browser:
   - Chrome 130: ✅ All tests passing
   - Firefox 120: ✅ All tests passing
   - Edge 130: ✅ All tests passing

   Performance:
   - Bundle size: <700 KB gzipped
   - First Contentful Paint: <1s
   - WebSocket latency: <100ms

   Bug Fixes:
   - [List any bugs fixed during testing]

   Handover: 0242c
   Tests: 78 passing (29 Launch + 49 Implement)
   Status: Ready for 0242d ✅"
   ```

8. **Proceed to Handover 0242d**: Documentation and archival

---

## Notes for Frontend-Tester Subagent

**Your Mission**:
- Verify E2E workflows (Stage → Launch → Implement)
- Monitor WebSocket events in DevTools (Network → WS tab)
- Test in all three browsers (Chrome, Firefox, Edge)
- Measure performance metrics (bundle size, render time, latency)
- Fix any P0/P1 bugs found during testing

**Communication**:
- Report progress after each scenario (1-5)
- Share screenshots of any bugs found
- Document bug severity and impact
- Verify fixes in all browsers before marking complete
- Ask questions if behavior is unclear

**Quality Checklist Before Marking Complete**:
- [ ] All E2E scenarios passing (Stage → Launch → Implement)
- [ ] WebSocket events verified in DevTools (mission_updated, agent:created, agent:updated)
- [ ] Cross-browser testing complete (Chrome, Firefox, Edge)
- [ ] Performance targets met (bundle size, render time, latency)
- [ ] All P0 bugs fixed (blockers)
- [ ] All P1 bugs fixed (high priority)
- [ ] All 78 tests passing (29 Launch + 49 Implement)
- [ ] No console errors in any browser
- [ ] Manual checklist 100% complete

**Testing Order**:
1. Run automated tests first (`npm test`)
2. Then E2E workflow testing (manual)
3. Then WebSocket event verification (DevTools)
4. Then cross-browser testing (Chrome → Firefox → Edge)
5. Then performance validation (build + measure)
6. Finally bug fixing (if issues found)
