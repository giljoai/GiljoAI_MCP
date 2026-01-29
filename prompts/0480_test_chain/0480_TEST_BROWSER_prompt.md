# Terminal Session: 0480-TEST-BROWSER - Browser E2E Tests

## Mission
Execute browser-based E2E tests using Chrome extension for the 0480 Exception Handling Migration.

## Test Plan Reference
**READ THIS FIRST**: `F:\GiljoAI_MCP\handovers\0480_TEST_PLAN.md`

## Credentials
- Username: patrik
- Password: ***REMOVED***
- Backend: http://localhost:7272
- Frontend: http://localhost:7274

## Your Tasks

### 1. Login to Application
- Navigate to http://localhost:7274
- Login with credentials above
- Verify dashboard loads

### 2. Test Project List Display
- Navigate to Projects tab
- Verify projects display (not empty/error)
- Screenshot: `tests/reports/screenshots/0480_projects_list.png`

### 3. Test Task List Display
- Click on a project
- Verify tasks display
- Screenshot: `tests/reports/screenshots/0480_tasks_list.png`

### 4. Test Error Handling in UI
- Try to access non-existent project URL
- Verify error message displays cleanly (not raw stack trace)
- Screenshot: `tests/reports/screenshots/0480_error_display.png`

### 5. Test Orchestrator Launch
- Create new project or use existing
- Click "Launch Orchestrator"
- Verify JobsTab updates with new job
- Screenshot: `tests/reports/screenshots/0480_orchestrator_launch.png`

### 6. Test Settings Pages
- Navigate to My Settings
- Test Context Depth configuration
- Test Field Priority configuration
- Verify saves work without error

### 7. Test Admin Settings (if admin user)
- Navigate to Admin Settings
- Verify all tabs load
- Test a setting change

### 8. Create Summary Report
Write results to `F:\GiljoAI_MCP\tests\reports\0480_TEST_BROWSER_RESULTS.md`:
- All screenshots taken
- Any UI errors observed
- Pass/Fail status for each test

## Success Criteria
- All UI pages load without error
- Projects and tasks display correctly
- Error messages are user-friendly
- Settings save without crash

## On Completion
Create final summary:
```
=== 0480 TESTING COMPLETE ===
Browser E2E: [PASS/FAIL]
- Projects display: [✓/✗]
- Tasks display: [✓/✗]
- Error handling: [✓/✗]
- Settings: [✓/✗]

See full report: tests/reports/0480_TEST_BROWSER_RESULTS.md
```
