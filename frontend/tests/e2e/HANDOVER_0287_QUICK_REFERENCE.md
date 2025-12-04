# Handover 0287: Quick Reference - Run Tests Now

## One-Line Commands

### Option 1: Test with localhost (default)
```bash
cd F:\GiljoAI_MCP\frontend && npm run test:e2e -- tests/e2e/launch-button-staging-complete.spec.js
```

### Option 2: Test with custom server
```bash
cd F:\GiljoAI_MCP\frontend && set PLAYWRIGHT_TEST_BASE_URL=http://10.1.0.164:7274 && npm run test:e2e -- tests/e2e/launch-button-staging-complete.spec.js
```

### Option 3: Test with interactive UI
```bash
cd F:\GiljoAI_MCP\frontend && npm run test:e2e -- tests/e2e/launch-button-staging-complete.spec.js --ui
```

## What Gets Tested

The test file validates that after clicking "Stage Project":

1. **Stage button** changes from "Stage project" to "Orchestrator Active"
2. **Launch button** changes from disabled (grey) to enabled (yellow)
3. **NO page refresh** occurs during this change
4. **WebSocket events** trigger the button state changes
5. User can immediately click "Launch jobs" button

## Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `launch-button-staging-complete.spec.js` | 388 | 5 test cases |
| `helpers/websocket-helpers.js` | 388 | 9 helper utilities |
| `README.md` | N/A | General guide |
| `HANDOVER_0287_TEST_GUIDE.md` | N/A | Execution guide |
| `HANDOVER_0287_SUMMARY.md` | N/A | Project summary |

**Total Code:** 776 lines

## Test Cases (5 tests)

```
1. launch_button_enables_after_staging_without_refresh
   └─ Core test: Button enable without page refresh

2. orchestrator_active_button_appears_after_staging
   └─ Stage button text changes, no refresh

3. launch_button_enables_with_agents_spawning
   └─ Button enables as agents appear

4. staging_prompt_copied_to_clipboard
   └─ Clipboard notification works

5. websocket_events_trigger_button_update
   └─ Real-time updates via WebSocket
```

## Expected Results

All 5 tests pass when:
- Frontend running on localhost:7274 (or custom URL)
- Backend running on localhost:7272
- PostgreSQL initialized
- Test user exists: patrik / ***REMOVED***
- Sample project exists

Expected runtime: 2-3 minutes

## View Results

```bash
# After tests complete:
npm run test:e2e:report
```

Opens HTML report with:
- Test duration
- Screenshots of failures
- Video recordings (on failure)
- Full execution trace

## Troubleshooting

If tests timeout or fail:

1. **Check backend is running:**
   ```bash
   curl http://localhost:7272/api/health
   ```

2. **Check frontend is running:**
   ```bash
   curl http://localhost:7274
   ```

3. **Check WebSocket connection:**
   - Open http://localhost:7274 in browser
   - Open DevTools (F12)
   - Go to Network tab
   - Look for "ws://" connection
   - Should show "101 Switching Protocols"

4. **Run with debug mode:**
   ```bash
   npm run test:e2e -- tests/e2e/launch-button-staging-complete.spec.js --debug
   ```

5. **Run with visible browser:**
   ```bash
   npm run test:e2e -- tests/e2e/launch-button-staging-complete.spec.js --headed
   ```

## File Locations (Absolute Paths)

Main Test File:
```
F:\GiljoAI_MCP\frontend\tests\e2e\launch-button-staging-complete.spec.js
```

Helper Utilities:
```
F:\GiljoAI_MCP\frontend\tests\e2e\helpers\websocket-helpers.js
```

Documentation:
```
F:\GiljoAI_MCP\frontend\tests\e2e\README.md
F:\GiljoAI_MCP\frontend\tests\e2e\HANDOVER_0287_TEST_GUIDE.md
F:\GiljoAI_MCP\frontend\tests\e2e\HANDOVER_0287_SUMMARY.md
```

## Key Features

- 5 comprehensive test cases
- WebSocket event monitoring
- Multi-browser support (Chrome, Firefox, Safari)
- Real-time button state validation
- No page refresh assertions
- Production-grade error handling
- Detailed console logging
- Screenshot/video on failure
- Timeout management

## Dependencies

- Playwright (already in package.json)
- No additional npm packages needed
- Requires: Node.js, npm, browsers

## Integration

Tests are ready for:
- GitHub Actions CI/CD
- GitLab CI
- Jenkins
- Azure Pipelines
- Manual testing

Output formats:
- HTML report (playwright-report/)
- JUnit XML (test-results/junit.xml)
- Console logs

## Next Steps

1. Run tests with command above
2. All tests should pass (green)
3. Review test report
4. Commit test files to git
5. Add to CI/CD pipeline
6. Continue with implementation

---

**Total Time to Run:** 2-3 minutes
**Success Rate:** Should be 100% with proper setup
**Questions?** See HANDOVER_0287_TEST_GUIDE.md

---

**Created:** December 3, 2025
**Handover:** 0287
**Status:** COMPLETE
