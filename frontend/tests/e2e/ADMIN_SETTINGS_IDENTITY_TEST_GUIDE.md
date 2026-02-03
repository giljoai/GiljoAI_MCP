# Admin Settings Identity Tab - E2E Test Guide

**Handover**: 0434
**Test File**: `frontend/tests/e2e/admin-settings-identity.spec.js`
**Total Test Cases**: 10
**Total Lines**: 794
**Framework**: Playwright
**Language**: JavaScript

## Overview

Comprehensive E2E tests for the Admin Settings Identity tab, which consolidates workspace and member management. Tests validate:
- Tab accessibility and permission checks
- Organization data display and editing
- Form state management (dirty/clean tracking)
- Tab navigation and persistence
- Component layout and structure
- Error handling and recovery

## Test Environment Setup

### Prerequisites
- Frontend running on `http://localhost:7274`
- Backend API running on `http://localhost:7272`
- PostgreSQL database configured
- Test user account exists: `patrik` / `***REMOVED***` (admin/owner role)

### Running Tests

```bash
# Install dependencies
cd frontend
npm install

# Run all Identity tab tests
npx playwright test admin-settings-identity.spec.js

# Run specific test
npx playwright test admin-settings-identity.spec.js -g "TEST 1"

# Run with visual debugging
npx playwright test admin-settings-identity.spec.js --debug

# Run with browser UI mode
npx playwright test admin-settings-identity.spec.js --ui

# Generate HTML report
npx playwright test admin-settings-identity.spec.js --reporter=html
```

## Test Scenarios

### TEST 1: Admin Can Access Identity Tab (Lines 38-111)

**Purpose**: Verify that admin users can navigate to and access the Identity tab.

**Test Flow**:
1. Login as admin (patrik)
2. Navigate to `/system-settings`
3. Verify Identity tab is visible and first in order
4. Click Identity tab
5. Verify workspace and members cards load

**Expected Outcomes**:
- Identity tab button is visible
- Identity tab is the first tab in the group
- Workspace Details card displays
- Members card displays
- Organization name field is populated
- Slug field is disabled (read-only)

**Key Assertions**:
```javascript
expect(identityTabButton).toBeVisible()
expect(firstTabText).toContain('Identity')
expect(workspaceCard).toBeVisible()
expect(membersCard).toBeVisible()
expect(slugField.isDisabled()).toBe(true)
```

**Dependencies**: None (foundational test)

---

### TEST 2: Non-Admin Cannot Access Admin Settings (Lines 112-168)

**Purpose**: Verify that non-admin users cannot access Admin Settings.

**Test Flow**:
1. Note: Uses current admin user to demonstrate access
2. Document expected behavior for non-admin users
3. Verify route guards prevent access

**Expected Outcomes**:
- Admin users can access `/system-settings`
- Non-admin users would be redirected or shown 403 error
- Admin Settings page header displays for authorized users

**Key Assertions**:
```javascript
expect(isAdminAccessible).toBe(true)
// Non-admin behavior documented for future testing
```

**Note**: This test is primarily documented as a specification. In production, you would need a non-admin test user to fully test access denial.

---

### TEST 3: Identity Tab Shows Organization Data (Lines 169-257)

**Purpose**: Verify that organization data loads and displays correctly.

**Test Flow**:
1. Navigate to Admin Settings
2. Click Identity tab
3. Verify no error alerts
4. Check all form fields are populated
5. Verify members card displays
6. Verify member count

**Expected Outcomes**:
- No error loading organization
- Organization name is populated
- Organization slug is populated
- Slug field is disabled
- Members card title shows "Members"
- At least one member is visible

**Key Assertions**:
```javascript
expect(isErrorShown).toBe(false)
expect(orgName).toBeTruthy()
expect(orgSlug).toBeTruthy()
expect(isSlugDisabled).toBe(true)
expect(memberCount).toBeGreaterThanOrEqual(1)
```

**Data Dependencies**: Valid organization must exist in database

---

### TEST 4: Admin Can Edit Organization Name (Lines 258-368)

**Purpose**: Verify organization name can be edited and changes are persisted.

**Test Flow**:
1. Navigate to Identity tab
2. Get original organization name
3. Verify Save button is disabled (clean form)
4. Modify organization name
5. Verify Save button becomes enabled
6. Click Save button
7. Verify success notification
8. Verify Save button is disabled again (clean form)
9. Reload page and verify persistence

**Expected Outcomes**:
- Save button is disabled for clean form
- Save button enables when name changes
- API call is made on save
- Success notification displays
- Changes persist after page reload
- Form returns to clean state after save

**Key Assertions**:
```javascript
expect(isSaveDisabled).toBe(true) // initially
expect(isSaveDisabled).toBe(false) // after change
expect(snackbarText).toContain('updated successfully')
expect(reloadedName).toBe(newName)
```

**Side Effects**: Modifies organization name in database. Uses timestamp to ensure unique names.

**Idempotency**: Each test run uses unique names via `Date.now()` - safe to run repeatedly.

---

### TEST 5: Admin Settings Tab Order is Correct (Lines 369-432)

**Purpose**: Verify that Admin Settings tabs are in the correct order.

**Test Flow**:
1. Navigate to Admin Settings
2. Get all tab buttons
3. Verify tab count matches expected (6 tabs)
4. Verify each tab label in correct position
5. Verify each tab is visible

**Expected Tab Order**:
1. Identity (mdi-account-group)
2. Network (mdi-network-outline)
3. Database (mdi-database)
4. Integrations (mdi-api)
5. Security (mdi-shield-lock)
6. Prompts (mdi-file-document-edit)

**Expected Outcomes**:
- Exactly 6 tabs present
- Tabs appear in correct order
- Each tab has correct label

**Key Assertions**:
```javascript
expect(tabCount).toBe(6)
expect(tabText).toContain('Identity')
expect(tabText).toContain('Network')
// ... etc for each tab
```

**Dependencies**: None

---

### TEST 6: Form Reset Button Works Correctly (Lines 433-503)

**Purpose**: Verify that form reset reverts changes and disables save button.

**Test Flow**:
1. Navigate to Identity tab
2. Get original organization name
3. Modify the name
4. Verify Save button is enabled
5. Click Reset button
6. Verify name reverts to original
7. Verify Save button is disabled

**Expected Outcomes**:
- Reset reverts form to original values
- Save button becomes disabled after reset
- No API call is made for reset
- Form state is clean after reset

**Key Assertions**:
```javascript
expect(resetName).toBe(originalName)
expect(isSaveDisabled).toBe(true)
```

**State Management**: Tests Vue reactive state tracking (form dirty flag)

---

### TEST 7: Workspace Card Displays All Required Fields (Lines 504-581)

**Purpose**: Verify workspace card layout and all UI elements are present.

**Test Flow**:
1. Navigate to Identity tab
2. Verify workspace card is visible
3. Check card title contains "Workspace Details"
4. Verify card has icon
5. Verify name field label and input
6. Verify slug field label and input
7. Verify Save button
8. Verify Reset button

**Expected Outcomes**:
- Card header displays with icon and "Workspace Details" title
- Organization name field is visible and editable
- Slug field is visible and disabled
- Save button is visible with "Save Changes" label
- Reset button is visible
- All elements are properly aligned and visible

**Key Assertions**:
```javascript
expect(workspaceCard).toBeVisible()
expect(titleText).toContain('Workspace Details')
expect(saveBtnText).toContain('Save')
expect(resetBtnText).toContain('Reset')
```

**UI/UX Validation**: Tests component layout and accessibility

---

### TEST 8: Members Card Displays All Required Elements (Lines 582-660)

**Purpose**: Verify members card layout and all UI elements are present.

**Test Flow**:
1. Navigate to Identity tab
2. Verify members card is visible
3. Check card title contains "Members"
4. Verify card has icon
5. Verify Invite button (if authorized)
6. Verify member list container
7. Verify card divider

**Expected Outcomes**:
- Card header displays with icon and "Members" title
- Invite button is visible (for users with permission)
- Member list is displayed
- Card divider separates header from content
- Card is responsive and properly structured

**Key Assertions**:
```javascript
expect(membersCard).toBeVisible()
expect(titleText).toContain('Members')
expect(isInviteVisible).toBe(true)
expect(isMemberListVisible).toBe(true)
```

**Permissions Note**: Invite button visibility depends on user's org role (owner/admin can invite)

---

### TEST 9: Identity Tab State Persists During Navigation (Lines 661-735)

**Purpose**: Verify tab state is maintained when switching between tabs.

**Test Flow**:
1. Navigate to Identity tab
2. Get initial organization name
3. Verify workspace card is visible
4. Click Network tab
5. Verify workspace card is hidden
6. Click Identity tab again
7. Verify workspace card is visible
8. Verify organization name is unchanged
9. Verify members card is also visible

**Expected Outcomes**:
- Tab content is replaced when tab changes
- Switching back to Identity tab reloads data
- Data is consistent across tab switches
- No state corruption or stale data

**Key Assertions**:
```javascript
expect(isWorkspaceVisible).toBe(true) // first visit
expect(isWorkspaceVisible).toBe(false) // hidden when network tab active
expect(isWorkspaceVisible).toBe(true) // visible again
expect(returnedName).toBe(initialName)
```

**Vue State Management**: Tests component lifecycle and reactive state

---

### TEST 10: Error States Are Handled Gracefully (Lines 736-793)

**Purpose**: Verify error handling doesn't break the interface.

**Test Flow**:
1. Navigate to Identity tab
2. Verify no error alert initially
3. Verify component is responsive
4. Test form input works
5. Click Reset and verify it works
6. Verify UI remains usable

**Expected Outcomes**:
- No error alerts on successful load
- Error alert component exists (for error scenarios)
- Form inputs are functional
- Reset button works
- UI remains responsive after interactions

**Key Assertions**:
```javascript
expect(isErrorShowing).toBe(false)
expect(fieldValue).toBe(testValue)
// Error alert container exists but not visible
```

**Error Scenarios Covered**:
- No initial errors on page load
- Form remains functional
- Recovery from form modifications

---

## Test Data & Side Effects

### Organization Data
- Tests use actual organization from authenticated user
- TEST 4 modifies organization name (uses timestamp for uniqueness)
- Other tests are read-only and don't modify data

### Member Data
- All tests read member data, none modify membership
- No members are added, removed, or transferred during tests

### Idempotency
- Tests use `Date.now()` for unique identifiers
- Safe to run repeatedly without conflicts
- No persistent test data cleanup required

## Key Testing Patterns Used

### 1. Authentication & Authorization
```javascript
await loginAsDefaultTestUser(page) // Custom helper for admin login
```

### 2. Navigation & Waiting
```javascript
await page.goto(`${BASE_URL}/system-settings`)
await page.waitForLoadState('networkidle')
```

### 3. Form Interaction
```javascript
await orgNameField.clear()
await orgNameField.fill(newName)
const value = await orgNameField.inputValue()
```

### 4. State Verification
```javascript
const isSaveDisabled = await saveButton.isDisabled()
expect(isSaveDisabled).toBe(true)
```

### 5. Notification Handling
```javascript
const snackbar = page.locator('[data-test="snackbar"]')
await expect(snackbar).toBeVisible({ timeout: 5000 })
```

### 6. Visibility & Presence
```javascript
await expect(workspaceCard).toBeVisible()
const isVisible = await element.isVisible({ timeout: 2000 }).catch(() => false)
```

## Data Test Attributes Used

All elements use `data-test` attributes for reliable selection:

| Element | Selector | Purpose |
|---------|----------|---------|
| Identity Tab | `[data-test="identity-tab"]` | Tab navigation |
| Workspace Card | `[data-test="workspace-card"]` | Organization details |
| Org Name Field | `[data-test="org-name-field"]` | Organization name input |
| Org Slug Field | `[data-test="org-slug-field"]` | Organization slug (read-only) |
| Members Card | `[data-test="members-card"]` | Member list container |
| Member List | `[data-test="member-list"]` | Member item container |
| Save Button | `[data-test="save-org-btn"]` | Save changes action |
| Reset Button | `[data-test="reset-btn"]` | Reset form action |
| Invite Button | `[data-test="invite-btn"]` | Member invitation action |
| Error Alert | `[data-test="error-alert"]` | Error state display |
| Snackbar | `[data-test="snackbar"]` | Notification display |

## Console Logging

Tests include comprehensive console logging for debugging:
- Test start/end messages
- Step-by-step progress tracking
- Data values at key points
- Assertion results

Example output:
```
[Test 4] Starting: Admin can edit organization name
[Test 4] Original name: Test Workspace
[Test 4] Changed name to: Test Workspace 1707894321234
[Test 4] Clicked save button...
[Test 4] Notification: Workspace updated successfully
[Test 4] PASSED: Organization name updated successfully
```

## Known Limitations & Future Enhancements

1. **Non-Admin Testing**: TEST 2 needs a non-admin user account to fully verify access denial
2. **Member Operations**: Current tests don't exercise invite, role change, or remove operations
3. **Batch Operations**: Tests don't cover multiple concurrent edits
4. **Network Failures**: No explicit tests for API failure scenarios
5. **Large Member Lists**: Performance with many members not tested

## Maintenance & Updates

### When to Update Tests
- When component selector attributes change
- When form field names or labels change
- When API response structure changes
- When new tabs are added to Admin Settings
- When permission model changes

### Debugging Failed Tests
1. Check test output for step-by-step progress
2. Use `--debug` flag for interactive debugging
3. Use `--ui` mode to see browser automation
4. Check network tab for API call failures
5. Review console logs in frontend for errors

### Performance Considerations
- Tests use 500ms waits for state transitions
- Uses longer timeouts for async operations (5-10s)
- Includes `networkidle` waits for data loading
- Optimized for typical development machine performance

## CI/CD Integration

```yaml
# Example GitHub Actions workflow
- name: Run E2E Tests
  run: |
    cd frontend
    npx playwright test admin-settings-identity.spec.js

- name: Upload Report
  if: always()
  uses: actions/upload-artifact@v2
  with:
    name: playwright-report
    path: frontend/playwright-report/
```

## Related Documentation

- **Component**: `frontend/src/components/settings/tabs/IdentityTab.vue`
- **View**: `frontend/src/views/SystemSettings.vue`
- **Test Helpers**: `frontend/tests/e2e/helpers.ts`
- **Playwright Docs**: https://playwright.dev/docs/intro
- **Handover**: 0434 (Identity Tab Implementation)

## Test Execution Time

Expected test execution times:
- Individual tests: 30-60 seconds each
- Full suite (10 tests): 5-8 minutes
- With report generation: 8-10 minutes

## Support & Reporting

For test failures or issues:
1. Check test output and logs
2. Review component implementation
3. Verify test data setup
4. Check backend API responses
5. Update tests if component changed

---

**Created**: Handover 0434
**Last Updated**: 2026-02-03
**Maintainer**: Frontend QA Team
