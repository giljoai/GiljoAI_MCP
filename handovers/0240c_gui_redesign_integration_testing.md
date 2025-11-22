# Handover 0240c: GUI Redesign Integration Testing

**Status**: Ready for Implementation
**Priority**: High
**Estimated Effort**: 4-6 hours
**Dependencies**: 0240a AND 0240b (must be merged first)
**Part of**: GUI Redesign Series (0240a-0240d)
**Tool**: 🖥️ CLI (Local)
**Parallel Execution**: ❌ No (Sequential after 0240a & 0240b merge)

---

## Before You Begin

**REQUIRED READING**:
1. **F:\GiljoAI_MCP\handovers\QUICK_LAUNCH.txt**
2. **F:\GiljoAI_MCP\handovers\013A_code_review_architecture_status.md**

**Prerequisites**:
- ✅ **0240a** (Launch Tab Visual Redesign) - MUST be merged to master
- ✅ **0240b** (Implement Tab Component Refactor) - MUST be merged to master
- ✅ Backend server running on `10.1.0.164:7274`
- ✅ PostgreSQL database accessible
- ✅ Frontend built with both handover changes

---

## 🎯 Objective

Perform comprehensive integration testing of merged GUI redesign changes (0240a + 0240b) to verify visual consistency, functional correctness, WebSocket real-time updates, and cross-browser compatibility. This ensures the redesigned Launch/Implement tabs match the PDF vision document and work flawlessly in production.

---

## ⚠️ Problem Statement

**What's Being Tested**:
- Launch Tab visual styling from 0240a (panels, buttons, agent cards)
- Implement Tab status board table from 0240b (6 new components)
- WebSocket real-time updates with new table structure
- Cross-browser rendering (Chrome, Firefox, Edge)
- Responsive design (mobile, tablet, desktop)
- End-to-end user workflows (Stage → Launch → Monitor)

**Why Integration Testing Needed**:
- Unit tests verify components in isolation - need to test integrated behavior
- WebSocket updates may fail with new table structure
- Visual regressions possible when merging two parallel branches
- Real-world user flows untested (create project → stage → launch → monitor agents)

**User Impact**:
- Bugs in production harm credibility
- WebSocket failures break real-time monitoring
- Visual glitches reduce perceived quality
- Cross-browser issues limit accessibility

---

## ✅ Solution Approach

**High-Level Strategy**:
1. **Manual UI Testing** - Navigate through Launch/Implement tabs, verify visual design
2. **Functional Testing** - Test all interactions (buttons, dropdowns, actions)
3. **WebSocket Testing** - Verify real-time updates with backend events
4. **Responsive Testing** - Test on mobile/tablet/desktop viewports
5. **Cross-Browser Testing** - Verify Chrome, Firefox, Edge rendering
6. **Performance Testing** - Check bundle size, load time, rendering performance
7. **Bug Fixes** - Address any issues found during testing

**Key Principles**:
- **Test on actual deployment** - Use `http://10.1.0.164:7274` (not localhost)
- **Test with real data** - Use existing projects or create test projects
- **Test WebSocket events** - Simulate backend updates (status changes, messages)
- **Test edge cases** - Empty states, long text, many agents, network errors

---

## 📝 Testing Tasks

### Task 1: Pre-Testing Setup (30 minutes)

**Verify Prerequisites**:
1. **Check branch merges**:
   ```bash
   git log --oneline -10
   # Should show commits from 0240a and 0240b
   ```

2. **Rebuild frontend**:
   ```bash
   cd frontend
   npm run build
   ```

3. **Restart backend server** (if needed):
   ```bash
   python startup.py
   ```

4. **Verify backend accessible**:
   ```bash
   curl http://10.1.0.164:7274/api/health
   # Should return {"status": "healthy"}
   ```

5. **Create test project** (if none exist):
   - Navigate to `http://10.1.0.164:7274/projects`
   - Click "Create New Project"
   - Fill in project details
   - Save project

---

### Task 2: Launch Tab Visual Testing (1 hour)

**Test Scenario**: Verify Launch Tab matches PDF slides 2-9

**Steps**:
1. Navigate to `http://10.1.0.164:7274/projects/{project_id}?via=jobs&tab=launch`

2. **Verify Panel Styling** (0240a Task 1):
   - [ ] Project Description panel has rounded border (no elevation shadow)
   - [ ] Orchestrator Mission panel has rounded border
   - [ ] Panel headers are UPPERCASE with smaller font
   - [ ] Panel backgrounds use subtle dark theme color
   - [ ] Custom scrollbars visible when content overflows

3. **Verify Mission Panel Typography** (0240a Task 2):
   - [ ] Orchestrator Mission text uses monospace font
   - [ ] Long mission prompts wrap correctly
   - [ ] Custom scrollbar appears when mission exceeds max-height

4. **Verify Button Styling** (0240a Task 3):
   - [ ] "Stage Project" button has yellow outlined border
   - [ ] "Launch Jobs" button has yellow filled background
   - [ ] Icons appear to left of button text
   - [ ] Buttons are appropriately sized (large)

5. **Verify Orchestrator Card** (0240a Task 4):
   - [ ] Lock icon appears next to "Orchestrator" name
   - [ ] Info button (ℹ️) appears on right side
   - [ ] Hover shows subtle background change
   - [ ] Click info button triggers action (console log or modal)

6. **Verify Agent Team Cards** (0240a Task 5):
   - [ ] Cards have consistent styling with rounded borders
   - [ ] Horizontal scroll works smoothly
   - [ ] Edit button (pencil icon) appears on each card
   - [ ] Cards show agent type icon with color

7. **Verify Empty States** (0240a Task 6):
   - [ ] Empty mission panel shows document icon
   - [ ] "Mission will appear after staging..." text centered
   - [ ] Empty agent team shows appropriate message

**Screenshot Comparison**:
- Take screenshots of Launch Tab
- Compare with PDF slides 2-9
- Note any visual differences

**Issues Found**: [Document any visual bugs here]

---

### Task 3: Implement Tab Component Testing (1.5 hours)

**Test Scenario**: Verify Implement Tab status board table matches PDF slides 10-27

**Steps**:
1. Navigate to `http://10.1.0.164:7274/projects/{project_id}?via=jobs&tab=implement`

2. **Verify Status Board Table Structure** (0240b Task 5):
   - [ ] Table displays with 8 columns:
     1. Agent Type (avatar + name)
     2. Agent ID (8-char UUID)
     3. Agent Status (StatusChip component)
     4. Job Read (checkmark indicator)
     5. Job Acknowledged (checkmark indicator)
     6. Messages Sent (count)
     7. Messages Waiting (count, yellow if > 0)
     8. Messages Read (count)
     9. Actions (icon buttons)
   - [ ] Table headers are UPPERCASE with smaller font
   - [ ] Rows have bottom border separation
   - [ ] Hover state shows subtle background change

3. **Verify StatusChip Component** (0240b Task 2):
   - [ ] Status chip shows correct icon and color per status
   - [ ] Health indicator overlay appears (warning/critical)
   - [ ] Health indicator has pulse animation
   - [ ] Staleness warning icon appears for jobs inactive >10 min
   - [ ] Tooltip shows health status and failure count
   - [ ] Tooltip shows last activity time

4. **Verify JobReadAckIndicators** (0240b Task 3):
   - [ ] Green checkmark appears when job_read = true
   - [ ] Dash appears when job_read = false
   - [ ] Same behavior for job_acknowledged column

5. **Verify ActionIcons Component** (0240b Task 4):
   - [ ] **Play button** (▶️):
     - Appears for launchable agents (waiting/blocked status)
     - Hidden for working/complete/cancelled agents
     - Tooltip shows "Launch {agent_type} agent"
     - Click triggers console log or launch action
   - [ ] **Copy button** (📋):
     - Appears for all agents
     - Click copies prompt to clipboard
     - Tooltip shows "Copy prompt to clipboard"
   - [ ] **Message button** (💬):
     - Appears for all agents
     - Shows red badge when messages_waiting > 0
     - Disabled when messages_sent = 0
     - Tooltip shows "View message transcript"
   - [ ] **Info button** (ℹ️):
     - Appears for all agents
     - Tooltip shows "View agent template"
     - Click triggers console log or modal
   - [ ] **Cancel button** (✖️):
     - Only appears for working/waiting/blocked agents
     - Red color
     - Click shows confirmation dialog
     - Dialog has "Cancel" and "Confirm" buttons

6. **Verify Table Sorting** (0240b Task 5):
   - [ ] Agents sorted by status priority:
     1. working (first)
     2. blocked
     3. waiting
     4. complete
     5. failed
     6. cancelled
     7. decommissioned (last)
   - [ ] Within same status, sorted alphabetically by agent_type

7. **Verify Message Recipient Dropdown** (0240b Task 6):
   - [ ] Dropdown shows "Send to" label
   - [ ] Options: "Orchestrator" and "Broadcast (All Agents)"
   - [ ] Selected value updates textarea label
   - [ ] Dropdown has appropriate width (~220px)

8. **Verify Claude Code CLI Toggle** (existing feature):
   - [ ] Toggle switch appears above table
   - [ ] Toggle label: "Using Claude Code Subagents"
   - [ ] When enabled, only orchestrator shows play button
   - [ ] When disabled, all launchable agents show play button

**Screenshot Comparison**:
- Take screenshots of Implement Tab
- Compare with PDF slides 10-27
- Note any visual differences

**Issues Found**: [Document any component bugs here]

---

### Task 4: WebSocket Real-Time Updates Testing (1 hour)

**Test Scenario**: Verify table updates in real-time when backend emits WebSocket events

**Setup**:
1. Open browser DevTools → Network → WS filter
2. Verify WebSocket connection established to `ws://10.1.0.164:7274/ws`
3. Keep Implement Tab visible

**Test Cases**:

**Test 4.1: Agent Status Change**
1. Trigger agent status change (via backend or database update)
   ```sql
   UPDATE mcp_agent_jobs
   SET status = 'working'
   WHERE job_id = 'abc123';
   ```
2. Verify backend emits `job:table_update` WebSocket event
3. **Expected**: Status chip updates immediately (within 1 second)
4. **Expected**: Table re-sorts if status priority changed

**Test 4.2: Message Count Update**
1. Send message to agent (via message composer)
2. Verify backend emits `job:table_update` event
3. **Expected**: `messages_sent` count increments
4. **Expected**: `messages_waiting` count increments
5. **Expected**: Red badge appears on message button

**Test 4.3: Health Status Change**
1. Trigger health status change (simulate health check failure)
2. **Expected**: Health indicator overlay appears on status chip
3. **Expected**: Pulse animation starts
4. **Expected**: Tooltip shows new health status

**Test 4.4: Job Read/Acknowledged**
1. Mark job as read (via API call or database update)
2. **Expected**: Green checkmark appears in "Job Read" column
3. Repeat for "Job Acknowledged" column

**Test 4.5: New Agent Added**
1. Launch new agent (via "Stage Project" → "Launch Jobs")
2. **Expected**: New row appears in table
3. **Expected**: Table re-sorts with new agent in correct position

**WebSocket Debugging**:
If updates don't appear:
- Check DevTools console for WebSocket errors
- Verify `useJobsWebSocket` composable subscribed correctly
- Check if `job:table_update` event handler called
- Verify reactive data updates (`agents` array)

**Issues Found**: [Document any WebSocket bugs here]

---

### Task 5: Responsive Design Testing (45 minutes)

**Test Scenario**: Verify UI works on mobile, tablet, and desktop viewports

**Testing Browsers**:
- Chrome DevTools → Toggle device toolbar (Ctrl+Shift+M)

**Viewports to Test**:
1. **Mobile** (375x667 - iPhone SE):
   - [ ] Launch Tab: Buttons stack vertically
   - [ ] Launch Tab: Panels have reduced padding
   - [ ] Implement Tab: Table scrolls horizontally
   - [ ] Message composer: Dropdown and textarea stack vertically

2. **Tablet** (768x1024 - iPad):
   - [ ] Launch Tab: Agent cards have medium width
   - [ ] Implement Tab: Table fits comfortably
   - [ ] All interactive elements easily tappable

3. **Desktop** (1920x1080):
   - [ ] Launch Tab: Panels use larger max-height for scrollable areas
   - [ ] Implement Tab: Table uses full width effectively
   - [ ] All spacing and sizing optimal

**Issues Found**: [Document any responsive design bugs here]

---

### Task 6: Cross-Browser Compatibility Testing (45 minutes)

**Test Scenario**: Verify UI renders correctly across browsers

**Browsers to Test**:
1. **Chrome (latest)**:
   - [ ] Launch Tab renders correctly
   - [ ] Implement Tab table renders correctly
   - [ ] Custom scrollbars display
   - [ ] All interactions work

2. **Firefox (latest)**:
   - [ ] Launch Tab renders correctly
   - [ ] Implement Tab table renders correctly
   - [ ] Custom scrollbars display (may differ from Chrome)
   - [ ] All interactions work

3. **Edge (latest)**:
   - [ ] Launch Tab renders correctly
   - [ ] Implement Tab table renders correctly
   - [ ] Custom scrollbars display
   - [ ] All interactions work

**Common Issues to Check**:
- CSS Grid/Flexbox rendering differences
- Custom scrollbar styling (Firefox uses different properties)
- Vuetify component rendering quirks
- Icon rendering (MDI icons)

**Issues Found**: [Document any browser-specific bugs here]

---

### Task 7: Performance Testing (30 minutes)

**Test Scenario**: Verify GUI redesign doesn't degrade performance

**Metrics to Check**:

1. **Bundle Size**:
   ```bash
   cd frontend
   npm run build
   ls -lh dist/assets/*.js
   ```
   - **Expected**: Bundle size increase <5% from previous version
   - **Baseline**: [Record current size]
   - **After 0240a+b**: [Record new size]

2. **Initial Load Time**:
   - Open DevTools → Network tab
   - Hard refresh (Ctrl+Shift+R)
   - Check "Load" time in Network tab footer
   - **Expected**: Load time <3 seconds

3. **Table Rendering Performance**:
   - Create project with 20+ agents (or mock data)
   - Navigate to Implement Tab
   - Check DevTools → Performance → Record page load
   - **Expected**: Table renders in <500ms

4. **WebSocket Update Latency**:
   - Trigger status change
   - Measure time from WebSocket event to DOM update
   - **Expected**: <100ms latency

**Issues Found**: [Document any performance regressions here]

---

### Task 8: End-to-End User Workflow Testing (1 hour)

**Test Scenario**: Complete user workflows from project creation to agent monitoring

**Workflow 1: Create Project → Stage → Launch → Monitor**

**Steps**:
1. **Create New Project**:
   - Navigate to `http://10.1.0.164:7274/projects`
   - Click "Create New Project"
   - Fill in project name, description
   - Click "Save"
   - **Expected**: Redirected to Launch Tab

2. **Stage Project**:
   - Click "Stage Project" button
   - **Expected**: Button shows loading state
   - **Expected**: Orchestrator Mission panel populates with prompt
   - **Expected**: Mission text uses monospace font
   - **Expected**: "Launch Jobs" button becomes enabled

3. **Launch Jobs**:
   - Click "Launch Jobs" button
   - **Expected**: Switch to Implement Tab
   - **Expected**: Status board table appears
   - **Expected**: Orchestrator row appears with "working" status

4. **Monitor Agents**:
   - Wait for WebSocket updates
   - **Expected**: Status chips update in real-time
   - **Expected**: Message counts increment
   - **Expected**: Table re-sorts when statuses change

5. **Interact with Agents**:
   - Click "Copy Prompt" button on orchestrator
   - **Expected**: Prompt copied to clipboard
   - **Expected**: Success toast appears (if implemented)
   - Click "View Messages" button
   - **Expected**: Message transcript opens (or console log)

**Workflow 2: Send Message → View Response**

**Steps**:
1. Navigate to Implement Tab
2. Select "Orchestrator" in message recipient dropdown
3. Type message in textarea
4. Click "Send" button
5. **Expected**: Message sent via WebSocket
6. **Expected**: `messages_sent` count increments in table
7. **Expected**: Orchestrator responds (if logic implemented)
8. **Expected**: `messages_waiting` count increments
9. **Expected**: Red badge appears on message button

**Workflow 3: Cancel Agent**

**Steps**:
1. Navigate to Implement Tab
2. Find working/waiting agent
3. Click "Cancel" button (✖️)
4. **Expected**: Confirmation dialog appears
5. Click "Confirm"
6. **Expected**: Agent status changes to "cancelled"
7. **Expected**: Table re-sorts
8. **Expected**: Cancel button disappears

**Issues Found**: [Document any workflow bugs here]

---

## 🧪 Testing Checklist

### Launch Tab (0240a)
- [ ] Panel styling matches PDF (rounded borders, no elevations)
- [ ] Panel headers are uppercase
- [ ] Mission panel uses monospace font
- [ ] Custom scrollbars visible and functional
- [ ] "Stage Project" button has yellow outlined border
- [ ] "Launch Jobs" button has yellow filled background
- [ ] Orchestrator card shows lock icon and info button
- [ ] Agent Team cards have consistent styling
- [ ] Empty states show correct icons
- [ ] Responsive design works (mobile/tablet/desktop)

### Implement Tab (0240b)
- [ ] Status board table has 8 columns
- [ ] Table headers are uppercase
- [ ] Status chips show correct icons and colors
- [ ] Health indicators appear with pulse animation
- [ ] Staleness warnings appear for inactive jobs
- [ ] Read/acknowledged checkmarks work
- [ ] Action icons appear (play/copy/message/info/cancel)
- [ ] Claude Code CLI toggle affects play button visibility
- [ ] Message recipient dropdown functional
- [ ] Table sorting by status priority works

### WebSocket Real-Time Updates
- [ ] Status changes update table immediately
- [ ] Message counts update dynamically
- [ ] Health status changes appear in real-time
- [ ] New agents appear in table when launched
- [ ] Table re-sorts when priorities change

### Cross-Browser Compatibility
- [ ] Chrome renders correctly
- [ ] Firefox renders correctly
- [ ] Edge renders correctly
- [ ] Custom scrollbars work across browsers

### Performance
- [ ] Bundle size increase <5%
- [ ] Initial load time <3 seconds
- [ ] Table renders in <500ms
- [ ] WebSocket update latency <100ms

### End-to-End Workflows
- [ ] Create → Stage → Launch → Monitor workflow works
- [ ] Send message → View response workflow works
- [ ] Cancel agent workflow works

---

## ✅ Success Criteria

**Must Have**:
- [ ] All Launch Tab visual elements match PDF slides 2-9
- [ ] All Implement Tab components match PDF slides 10-27
- [ ] WebSocket real-time updates work correctly
- [ ] Responsive design works on mobile/tablet/desktop
- [ ] Cross-browser compatibility (Chrome, Firefox, Edge)
- [ ] No console errors in browser DevTools
- [ ] No visual regressions from previous UI
- [ ] All end-to-end workflows complete successfully
- [ ] Performance metrics within acceptable ranges

**Nice to Have**:
- [ ] Accessibility compliance (ARIA labels, keyboard navigation)
- [ ] Smooth animations/transitions
- [ ] Loading states for async actions
- [ ] Error handling for network failures

---

## 🐛 Bug Fix Process

If bugs are found during testing:

1. **Document the bug**:
   - Description of issue
   - Steps to reproduce
   - Expected vs actual behavior
   - Browser/viewport where found
   - Screenshot/video if applicable

2. **Prioritize bugs**:
   - **P0 (Blocker)**: Breaks core functionality (e.g., table doesn't render)
   - **P1 (High)**: Degrades UX significantly (e.g., WebSocket updates don't work)
   - **P2 (Medium)**: Minor visual issues (e.g., spacing off by 2px)
   - **P3 (Low)**: Nice-to-have improvements

3. **Fix bugs**:
   - Start with P0 blockers
   - Create fix in same branch or new bugfix branch
   - Re-test after each fix
   - Update unit tests if needed

4. **Document fixes**:
   - List all bugs found
   - List all fixes applied
   - Note any deviations from original handovers

---

## 🔄 Rollback Plan

If critical bugs cannot be fixed in reasonable time:

1. **Identify which handover has the bug**:
   - 0240a (Launch Tab) or 0240b (Implement Tab)

2. **Revert problematic handover**:
   ```bash
   # If 0240a has critical bug
   git revert <commit-hash-of-0240a>

   # If 0240b has critical bug
   git revert <commit-hash-of-0240b>

   # If both have issues
   git revert <commit-hash-of-0240b>
   git revert <commit-hash-of-0240a>
   ```

3. **Rebuild frontend**:
   ```bash
   cd frontend
   npm run build
   ```

4. **Restart backend** (if needed):
   ```bash
   python startup.py
   ```

5. **Verify old UI restored**:
   - Navigate to `http://10.1.0.164:7274`
   - Confirm previous UI displayed
   - Test core functionality works

**No database changes** - pure frontend redesign, safe to revert.

---

## 📚 Related Handovers

**Depends on**:
- **0240a**: Launch Tab Visual Redesign (MUST be merged)
- **0240b**: Implement Tab Component Refactor (MUST be merged)

**Blocks**: None
**Related**:
- **0240d**: GUI Redesign Documentation (can run in parallel)

**Part of Series**: GUI Redesign (0240a-0240d)

---

## 🛠️ Tool Justification: Why CLI?

**CLI Required For**:
- ✅ **Backend server access** - Testing requires running backend at 10.1.0.164:7274
- ✅ **Database access** - May need to trigger status changes via SQL
- ✅ **WebSocket testing** - Requires live backend WebSocket connection
- ✅ **Integration testing** - Full stack (frontend + backend + database) needed
- ✅ **Performance profiling** - DevTools profiling requires local browser

**Why NOT CCW**:
- ❌ CCW cannot access deployment server (10.1.0.164:7274)
- ❌ CCW cannot run database queries
- ❌ CCW cannot test WebSocket connections
- ❌ CCW cannot perform browser-based testing

**Sequential Execution**:
- Must wait for 0240a AND 0240b to be merged
- Cannot run in parallel with 0240d (documentation can run during testing)

---

## 🎯 Execution Notes for AI Agent

**Testing Strategy**:
1. **Be thorough** - This is the quality gate before user acceptance
2. **Test edge cases** - Empty states, long text, many agents, network errors
3. **Test real scenarios** - Use actual backend, not mocked data
4. **Document everything** - Screenshots, bug reports, performance metrics

**Common Pitfalls**:
- Don't skip cross-browser testing (Firefox may render differently)
- Don't assume WebSocket works - test with real events
- Don't test on localhost - use `10.1.0.164:7274`
- Don't ignore console errors - investigate all warnings

**Bug Fix Priorities**:
- P0: Fix immediately (blocks user acceptance)
- P1: Fix before handover complete
- P2: Fix if time permits, otherwise create ticket
- P3: Create ticket for future improvement

---

## 📝 Completion Summary (To be filled after execution)

**Status**: ⏳ Ready for Implementation
**Completed**: [Date]
**Actual Effort**: [X hours vs 4-6 estimated]

**Testing Results**:

**Bugs Found**: [X total]
- **P0 Blockers**: [X found, X fixed]
- **P1 High**: [X found, X fixed]
- **P2 Medium**: [X found, X fixed]
- **P3 Low**: [X found, X deferred]

**Bug Details**:
1. [Bug description, priority, fix applied]
2. [Bug description, priority, fix applied]
...

**Performance Metrics**:
- Bundle size: [X KB before] → [X KB after] ([+/-X%])
- Load time: [X seconds]
- Table render time: [X ms]
- WebSocket latency: [X ms]

**Browser Compatibility**:
- Chrome: [✅ Pass / ❌ Fail - details]
- Firefox: [✅ Pass / ❌ Fail - details]
- Edge: [✅ Pass / ❌ Fail - details]

**Key Decisions**:
- [Any deviations from test plan]
- [Any bugs deferred to future handovers]

**Next Steps**:
→ **0240d** (GUI Redesign Documentation) - Update docs with final implementation
→ User Acceptance Testing
→ Deploy to production
