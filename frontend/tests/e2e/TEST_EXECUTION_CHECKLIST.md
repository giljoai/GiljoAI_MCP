# Admin Settings Identity Tab - Test Execution Checklist

**Handover**: 0434
**Date Created**: 2026-02-03
**Status**: Ready for Execution
**Test File**: `frontend/tests/e2e/admin-settings-identity.spec.js`

## Pre-Execution Setup

- [ ] Clone/update GiljoAI MCP repository
- [ ] Ensure PostgreSQL 18 is running
- [ ] Ensure backend API is running on `http://localhost:7272`
- [ ] Ensure frontend dev server is running on `http://localhost:7274`
- [ ] Verify test user "patrik" exists with admin/owner role
- [ ] Verify test user password is "***REMOVED***"

## Installation & Dependencies

```bash
# Navigate to frontend directory
cd frontend

# Install Playwright and dependencies
npm install

# Verify Playwright is installed
npx playwright --version
# Expected: Version 1.56.1 or higher
```

## Test Execution

### Full Test Suite

```bash
# Run all 10 tests
npx playwright test admin-settings-identity.spec.js

# Run with detailed output
npx playwright test admin-settings-identity.spec.js --reporter=verbose

# Run with HTML report
npx playwright test admin-settings-identity.spec.js --reporter=html
```

### Individual Tests

```bash
# Run TEST 1: Admin can access Identity tab
npx playwright test admin-settings-identity.spec.js -g "TEST 1"

# Run TEST 4: Admin can edit organization name
npx playwright test admin-settings-identity.spec.js -g "TEST 4"

# Run all tests with specific pattern
npx playwright test admin-settings-identity.spec.js -g "Identity"
```

### Debug Mode

```bash
# Interactive debugging with browser stepping
npx playwright test admin-settings-identity.spec.js --debug

# UI Mode with visual feedback
npx playwright test admin-settings-identity.spec.js --ui
```

## Test Execution Checklist

### Pre-Test Verification
- [ ] All 10 tests are listed in output
- [ ] Test descriptions are clear and descriptive
- [ ] No syntax errors reported
- [ ] File paths are correct

### Execution Progress
- [ ] TEST 1: Admin can access Identity tab - RUNNING
  - [ ] PASS - Admin access verified
  - [ ] FAIL - Check avatar menu implementation
- [ ] TEST 2: Non-admin cannot access Admin Settings - RUNNING
  - [ ] PASS - Access control verified
  - [ ] FAIL - Check route guard implementation
- [ ] TEST 3: Identity tab displays organization data - RUNNING
  - [ ] PASS - Organization data displays correctly
  - [ ] FAIL - Check organization data loading
- [ ] TEST 4: Admin can edit organization name - RUNNING
  - [ ] PASS - Organization update works
  - [ ] FAIL - Check API endpoint or form handling
- [ ] TEST 5: Admin Settings tab order is correct - RUNNING
  - [ ] PASS - Tab order verified
  - [ ] FAIL - Check tab button configuration
- [ ] TEST 6: Form reset button works - RUNNING
  - [ ] PASS - Reset functionality works
  - [ ] FAIL - Check Vue reactive state tracking
- [ ] TEST 7: Workspace card displays all fields - RUNNING
  - [ ] PASS - Layout is complete
  - [ ] FAIL - Check component template
- [ ] TEST 8: Members card displays all elements - RUNNING
  - [ ] PASS - Members UI is complete
  - [ ] FAIL - Check member list component
- [ ] TEST 9: Tab state persists during navigation - RUNNING
  - [ ] PASS - State management works
  - [ ] FAIL - Check Vue Router handling
- [ ] TEST 10: Error states are handled gracefully - RUNNING
  - [ ] PASS - Error handling works
  - [ ] FAIL - Check error alert component

## Expected Results

### Full Suite Execution
```
✓ TEST 1: Admin can access Identity tab (48s)
✓ TEST 2: Non-admin user cannot access Admin Settings (52s)
✓ TEST 3: Identity tab displays organization data (45s)
✓ TEST 4: Admin can edit organization name (60s)
✓ TEST 5: Admin Settings tab order is correct (35s)
✓ TEST 6: Form reset button works (42s)
✓ TEST 7: Workspace card displays all fields (38s)
✓ TEST 8: Members card displays all elements (40s)
✓ TEST 9: Identity tab state persists during navigation (55s)
✓ TEST 10: Error states are handled gracefully (42s)

Total: 10 passed (7m 37s)
```

### Success Criteria
- [ ] All 10 tests pass
- [ ] No timeout errors
- [ ] No element not found errors
- [ ] Console logs show expected flow
- [ ] No unhandled promise rejections
- [ ] HTML report generates successfully

## Test Data Verification

### Organization Data
- [ ] Organization name is populated correctly
- [ ] Organization slug is populated correctly
- [ ] Slug field is disabled (read-only)
- [ ] Members are displayed in list
- [ ] No error alerts appear

### Form State Management
- [ ] Save button disabled when form is clean
- [ ] Save button enabled when form is dirty
- [ ] Reset button reverts changes
- [ ] Form state persists across tab switches

## Failure Troubleshooting

### Common Issues

#### Tests Timing Out
- Check if servers are running
- Verify network connectivity
- Check for slow API responses
- Increase timeout values if needed

#### Element Not Found
- Verify data-test attributes in component
- Check if selectors changed
- Update selectors if component changed
- Take screenshot for debugging

#### API Errors
- Check backend server logs
- Verify database is accessible
- Check API endpoint implementations
- Review request/response formats

#### Authentication Failures
- Verify test user exists
- Check user password is correct
- Verify auth cookie is set
- Check token expiration

## Report Verification

### HTML Report
```bash
# Open HTML report after tests complete
open playwright-report/index.html
```

Report should contain:
- [ ] All 10 test results
- [ ] Pass/fail indicators
- [ ] Execution times
- [ ] Failed test details
- [ ] Screenshots (if available)
- [ ] Trace files (if enabled)

### Console Output
Expected console sections:
- [ ] Setup phase logs
- [ ] TEST 1-10 execution logs
- [ ] Assertion logs
- [ ] Final summary

## Post-Execution Tasks

### Documentation
- [ ] Update test results in handover documentation
- [ ] Record any failures and resolutions
- [ ] Note any new issues discovered
- [ ] Update test guide if needed

### Code Review
- [ ] Review any failed test implementations
- [ ] Check component changes if tests fail
- [ ] Update selectors if needed
- [ ] Refactor tests if improvements found

### Regression Testing
- [ ] Run full test suite weekly
- [ ] Add new tests for bugs found
- [ ] Maintain test coverage above 80%
- [ ] Update tests for new features

## CI/CD Integration

### GitHub Actions Workflow
```yaml
name: E2E Tests - Admin Settings

on: [push, pull_request]

jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Setup Node.js
        uses: actions/setup-node@v2
        with:
          node-version: '18'

      - name: Start servers
        run: |
          python startup.py &
          sleep 10

      - name: Install dependencies
        run: cd frontend && npm install

      - name: Run E2E tests
        run: npx playwright test admin-settings-identity.spec.js

      - name: Upload report
        if: always()
        uses: actions/upload-artifact@v2
        with:
          name: playwright-report
          path: frontend/playwright-report/
```

## Test Maintenance Schedule

### Weekly
- [ ] Run full test suite
- [ ] Review any failures
- [ ] Update test data if needed

### Monthly
- [ ] Review test coverage
- [ ] Check for flaky tests
- [ ] Update selectors if component changed
- [ ] Refactor tests for clarity

### Quarterly
- [ ] Review entire test suite
- [ ] Add new tests for new features
- [ ] Remove obsolete tests
- [ ] Update test documentation

## Sign-Off

- [ ] All tests executed
- [ ] All 10 tests passed
- [ ] HTML report reviewed
- [ ] No regressions found
- [ ] Documentation updated
- [ ] Ready for merge/deployment

## Notes & Issues Found

### Issues
(List any issues discovered during testing)

### Recommendations
(List any recommendations for improvement)

### Follow-Up Tasks
(List any follow-up tasks needed)

---

**Test File**: `frontend/tests/e2e/admin-settings-identity.spec.js`
**Test Guide**: `frontend/tests/e2e/ADMIN_SETTINGS_IDENTITY_TEST_GUIDE.md`
**Handover**: 0434
**Status**: Ready for Execution
