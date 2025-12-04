# Handover 0287: Launch Button Staging Complete - Test Execution Guide

## Quick Start

### 1. Setup Environment

```bash
cd F:\GiljoAI_MCP\frontend

# Ensure dependencies are installed
npm install

# Verify Playwright is installed
npm ls @playwright/test
```

### 2. Configure Test URL

The test expects to run against the GiljoAI frontend. Set the base URL:

**Option A: Use Default (localhost)**
```bash
npm run test:e2e -- tests/e2e/launch-button-staging-complete.spec.js
```

**Option B: Use Custom Server (10.1.0.164)**
```bash
set PLAYWRIGHT_TEST_BASE_URL=http://10.1.0.164:7274
npm run test:e2e -- tests/e2e/launch-button-staging-complete.spec.js
```

**Option C: Use PowerShell**
```powershell
$env:PLAYWRIGHT_TEST_BASE_URL = "http://10.1.0.164:7274"
npm run test:e2e -- tests/e2e/launch-button-staging-complete.spec.js
```

### 3. Run Tests

```bash
# Run all tests in the file
npm run test:e2e -- tests/e2e/launch-button-staging-complete.spec.js

# Run specific test case
npm run test:e2e -- tests/e2e/launch-button-staging-complete.spec.js -g "launch_button_enables_after_staging"

# Run with UI mode (interactive)
npm run test:e2e -- tests/e2e/launch-button-staging-complete.spec.js --ui

# Run with debugging
npm run test:e2e -- tests/e2e/launch-button-staging-complete.spec.js --debug
```

## Test Cases

### 1. launch_button_enables_after_staging_without_refresh

**What It Tests:**
- Button starts disabled (grey)
- After staging, "Launch jobs" button becomes enabled (yellow)
- No page refresh occurs during state change

**Expected Duration:** 30-40 seconds
- Staging prompt generation: 2-5s
- WebSocket events: 3-15s
- Total: < 30s timeout

**Success Criteria:**
- Launch button transitions from disabled to enabled
- Button color changes to yellow
- URL remains unchanged
- Stage button shows "Orchestrator Active"

**Failures May Indicate:**
- WebSocket events not received (check backend)
- Store not updating (check event handlers in ProjectTabs.vue)
- Button click not triggering staging (verify API endpoint)

---

### 2. orchestrator_active_button_appears_after_staging

**What It Tests:**
- Stage button text changes from "Stage project" to "Orchestrator Active"
- Stage button becomes disabled
- No page refresh

**Expected Duration:** 20-30 seconds
- Prompt generation: 2-5s
- Button state update: 1-2s

**Success Criteria:**
- Stage button text updates without page reload
- Button is disabled after orchestrator activation
- Initial and final URLs match

**Failures May Indicate:**
- WebSocket mission_updated event not updating component
- Button state logic incomplete
- Page redirected unexpectedly

---

### 3. launch_button_enables_with_agents_spawning

**What It Tests:**
- Launch button enables once both mission AND agents exist
- Real-time button state changes as agents spawn

**Expected Duration:** 35-45 seconds
- Staging: 2-5s
- Agent spawning: 5-15s
- Button state updates: 1-2s

**Success Criteria:**
- Launch button remains disabled until agents appear
- Button enables when agents are populated
- Button is immediately clickable

**Failures May Indicate:**
- Agent creation events not triggering button update
- Store.agents not populated correctly
- readyToLaunch logic incomplete

---

### 4. staging_prompt_copied_to_clipboard

**What It Tests:**
- Clipboard notification appears after stage click
- Button shows loading state during request
- Button returns to normal state after completion

**Expected Duration:** 5-10 seconds
- Prompt generation: 2-5s
- Toast notification: instant

**Success Criteria:**
- Success toast appears with "copied" message
- Toast appears within 5 seconds
- Button loading state visible

**Failures May Indicate:**
- Clipboard API not working
- Toast notification not rendering
- API endpoint not responding

---

### 5. websocket_events_trigger_button_update

**What It Tests:**
- WebSocket events are received from server
- Button state changes correlate with events
- No polling/manual refresh needed

**Expected Duration:** 30-40 seconds

**Success Criteria:**
- WebSocket messages captured (optional - some transports may not expose this)
- Button state updates without manual refresh
- URL remains constant

**Failures May Indicate:**
- WebSocket connection not established
- Events not being transmitted
- Frontend event handlers not registered

---

## Test Environment Requirements

### Backend

- GiljoAI API running on localhost:7272 or custom host:port
- PostgreSQL database initialized with schema
- Sample project created with ID: `555d0207-4f30-498a-9c44-9904804270ee`
- Test user account:
  - Username: `patrik`
  - Password: `***REMOVED***`

### Frontend

- Vue 3 dev server running on localhost:7274 or custom host:port
- Pinia store initialized with projectTabs module
- WebSocket connection active
- Browser console errors: none (warnings OK)

### Network

- Backend and frontend on same network or both localhost
- WebSocket port accessible (usually same port as HTTP)
- No firewall blocking WebSocket upgrades

## Monitoring Test Execution

### Console Logs

Tests output detailed logs to help debug issues:

```
[Test] Initial state:
  - Stage button text: Stage project
  - Launch button disabled: true
[Test] Clicking "Stage Project" button...
[Test] Staging prompt generated and copied to clipboard
[Test] Waiting for staging to complete via WebSocket events...
[Test] Launch button enabled successfully
[Test] Launch button color verified: yellow (enabled)
[Test] Stage button text after staging: Orchestrator Active
```

### Browser DevTools

Monitor test execution in real-time:

```bash
# Run with --headed to see browser
npm run test:e2e -- tests/e2e/launch-button-staging-complete.spec.js --headed

# Run with --debug for interactive debugging
npm run test:e2e -- tests/e2e/launch-button-staging-complete.spec.js --debug
```

In debug mode:
- Step through test execution
- Inspect element selectors
- View WebSocket messages
- Check console for errors

### Test Report

After tests complete:

```bash
# View HTML report
npm run test:e2e:report

# Reports generated in:
# - playwright-report/index.html (HTML)
# - test-results/junit.xml (JUnit for CI/CD)
```

Report includes:
- Test duration
- Screenshots of failures
- Video of test execution (on failure)
- Full execution trace

## Troubleshooting

### Button Never Enables

**Symptoms:**
- Test times out waiting for launch button to enable
- Stage button never shows "Orchestrator Active"
- Button color stays grey

**Debugging Steps:**
1. Check backend logs for orchestrator creation failure
2. Verify WebSocket connection open (DevTools > Network > WS)
3. Check browser console for JavaScript errors
4. Verify projectTabs store hasListeners for WebSocket events
5. Check API response status codes

**Fix:**
```bash
# Check if orchestrator exists
PGPASSWORD=$DB_PASSWORD psql -U postgres -d giljo_mcp -c \
  "SELECT id, status FROM mcp_agent_jobs \
   WHERE project_id = '555d0207-4f30-498a-9c44-9904804270ee' \
   AND agent_type = 'orchestrator' \
   ORDER BY created_at DESC LIMIT 1;"
```

### WebSocket Events Not Received

**Symptoms:**
- WebSocket messages: 0 captured
- Button state doesn't update
- Page must be refreshed to see changes

**Debugging Steps:**
1. Verify WebSocket URL in browser DevTools
2. Check for CORS/upgrade errors
3. Verify server WebSocket handler registered
4. Check if events are broadcast to correct tenant

**Fix:**
```javascript
// In browser console during test
window.ws.send(JSON.stringify({
  type: 'subscribe',
  project_id: '555d0207-4f30-498a-9c44-9904804270ee'
}))
```

### Timeout Errors

**Symptoms:**
- "Timeout waiting for WebSocket event"
- "Timeout waiting for button to enable"
- Tests consistently fail at 30 second mark

**Solutions:**
1. Increase timeout: Edit test file, change `timeout: 30000` to `timeout: 60000`
2. Check network latency: Ping backend, verify response times < 1s
3. Verify backend not overloaded
4. Check for stalled API calls

**Increase Timeout:**
```javascript
// In test file
test.setTimeout(60000) // 60 seconds

// Or for entire describe block
test.describe('Suite', () => {
  test.describe.configure({ timeout: 60000 })
})
```

### Page Refresh Unexpectedly

**Symptoms:**
- URL changed or reset
- Test fails with "URL mismatch"
- Page appears to reload

**Debugging:**
1. Check for router redirects
2. Verify no automatic page reload code
3. Check for hard navigation in event handlers
4. Verify localStorage/sessionStorage not cleared

**Fix:**
- Review ProjectTabs.vue for any `window.location` assignments
- Check router guards for unexpected redirects
- Verify event handlers don't call `page.reload()`

### Clipboard Copy Fails

**Symptoms:**
- Toast notification appears but with error
- "All copy methods failed" in console
- Test continues but clipboard.copy reported failing

**Note:** Tests will pass even if clipboard fails (test only checks for toast, not actual clipboard content)

**Workaround:**
- Copy functionality works in production
- Test focuses on button state, not clipboard verification

## Performance Benchmarks

Expected test execution times on typical hardware:

| Test | Min | Typical | Max |
|------|-----|---------|-----|
| launch_button_enables_after_staging | 25s | 35s | 45s |
| orchestrator_active_button_appears | 15s | 25s | 30s |
| launch_button_enables_with_agents | 30s | 40s | 50s |
| staging_prompt_copied_to_clipboard | 5s | 8s | 12s |
| websocket_events_trigger_button_update | 25s | 35s | 45s |
| **Total Suite** | **2:15m** | **2:45m** | **3:30m** |

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Playwright E2E Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - run: npm ci
      - run: npx playwright install
      - run: npm run test:e2e -- --reporter=junit
      - uses: actions/upload-artifact@v3
        if: always()
        with:
          name: test-results
          path: |
            test-results/
            playwright-report/
```

### JUnit Report

Tests output JUnit XML for CI integration:

```xml
<testsuites>
  <testsuite name="launch-button-staging-complete.spec.js">
    <testcase name="launch_button_enables_after_staging_without_refresh" time="35.2"/>
    <testcase name="orchestrator_active_button_appears_after_staging" time="22.1"/>
    <testcase name="launch_button_enables_with_agents_spawning" time="38.5"/>
    <testcase name="staging_prompt_copied_to_clipboard" time="6.8"/>
    <testcase name="websocket_events_trigger_button_update" time="34.2"/>
  </testsuite>
</testsuites>
```

## Success Criteria

All tests pass when:

- ✅ Buttons transition states without page refresh
- ✅ WebSocket events update UI in real-time
- ✅ No JavaScript console errors
- ✅ All assertions pass
- ✅ Test completes within timeout

## Rollback

If tests fail systematically:

1. Verify backend is working: `curl http://localhost:7272/api/health`
2. Verify frontend is loaded: Visit `http://localhost:7274` in browser
3. Check for recent code changes in ProjectTabs.vue
4. Review WebSocket event handler registration
5. Verify Pinia store listeners are attached

## Next Steps

After tests pass:

1. Commit test file: `git add tests/e2e/launch-button-staging-complete.spec.js`
2. Include in CI/CD pipeline
3. Run on every PR to prevent regressions
4. Add more E2E tests for other workflows

## Questions / Issues

For test-related issues:
1. Check console logs for detailed error messages
2. Review browser DevTools during test execution (--headed mode)
3. Check backend logs for API failures
4. Verify test configuration matches your environment

---

**Created:** December 3, 2025
**Handover:** 0287
**Test File:** `frontend/tests/e2e/launch-button-staging-complete.spec.js`
