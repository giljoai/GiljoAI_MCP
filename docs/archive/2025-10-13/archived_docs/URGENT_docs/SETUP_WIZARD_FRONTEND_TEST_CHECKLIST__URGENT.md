# Setup Wizard Frontend Testing Checklist

**Version:** 1.0.0
**Date:** 2025-10-07
**Purpose:** Comprehensive manual testing checklist for setup wizard integration with SetupStateManager backend

---

## Overview

This checklist validates the complete setup wizard flow, ensuring proper integration with the new SetupStateManager backend architecture. All tests verify backward compatibility and correct handling of state persistence.

## Pre-Test Setup

### Backend Requirements
- [ ] PostgreSQL 18 running and accessible
- [ ] Backend API server running on port 7272 (or configured port)
- [ ] SetupStateManager initialized (setup_state.json should exist or be creatable)
- [ ] Database migrations completed

### Frontend Requirements
- [ ] Frontend dev server running on port 7274
- [ ] Browser DevTools console open for debugging
- [ ] Network tab open to monitor API calls
- [ ] localStorage cleared (or noted for state testing)

### Test Environment Info
- **OS:** _____________
- **Browser:** _____________
- **Backend Port:** _____________
- **Frontend Port:** _____________
- **Database Status:** _____________

---

## Test Suite 1: Fresh Install Flow

### Objective
Verify the complete first-time setup flow for a fresh installation.

### Prerequisites
- [ ] Reset setup state: `DELETE FROM setup_state` or remove `setup_state.json`
- [ ] Verify `GET /api/setup/status` returns `completed: false`

### Test Steps

#### 1.1 Router Guard Redirect
- [ ] Navigate to `http://localhost:7274/`
- [ ] **Expected:** Automatic redirect to `/setup`
- [ ] **Actual:** _______________
- [ ] Console shows: "Setup not completed, redirecting to setup wizard"

#### 1.2 Setup Wizard Loads
- [ ] Setup wizard page renders correctly
- [ ] **Expected:** Stepper shows 5 steps: Database, Attach Tools, Serena MCP, Network, Complete
- [ ] **Actual:** _______________
- [ ] No console errors
- [ ] Giljo logo displays (dark/light theme appropriate)

#### 1.3 Database Check Step (Step 1)
- [ ] Database check component renders
- [ ] Connection status indicator visible
- [ ] **Expected:** Database connection verified (PostgreSQL 18)
- [ ] **Actual:** _______________
- [ ] "Next" button enabled after verification
- [ ] Click "Next" advances to Step 2

#### 1.4 Attach Tools Step (Step 2)
- [ ] AI tools detection runs automatically
- [ ] **Expected:** Claude Code detected (if installed)
- [ ] **Actual:** _______________
- [ ] Tool cards display correctly
- [ ] Can select/deselect tools
- [ ] "Next" button navigates to Step 3
- [ ] "Back" button returns to Step 1

#### 1.5 Serena MCP Step (Step 3)
- [ ] Serena MCP component renders
- [ ] Toggle switch displays current state
- [ ] **Expected:** Serena initially disabled
- [ ] **Actual:** _______________
- [ ] Can enable/disable Serena
- [ ] "Next" button navigates to Step 4
- [ ] "Back" button returns to Step 2

#### 1.6 Network Configuration Step (Step 4)
- [ ] Network mode selector displays (Localhost / LAN)
- [ ] **Expected:** Localhost selected by default
- [ ] **Actual:** _______________
- [ ] LAN configuration fields hidden in localhost mode
- [ ] "Next" button navigates to Step 5
- [ ] "Back" button returns to Step 3

#### 1.7 Setup Complete Step (Step 5)
- [ ] Summary displays all configuration choices
- [ ] "Save and Exit" button visible
- [ ] Configuration preview accurate:
  - [ ] Deployment mode: Localhost
  - [ ] Tools attached: _______________
  - [ ] Serena enabled: _______________
- [ ] Click "Save and Exit"

#### 1.8 Localhost Mode Completion
- [ ] **Expected:** No API key modal (localhost mode)
- [ ] **Expected:** No restart modal (localhost mode)
- [ ] Loading overlay shows briefly: "Setup complete! Redirecting..."
- [ ] **Actual:** _______________
- [ ] Redirect to dashboard (`http://localhost:7274/`)
- [ ] Dashboard loads successfully

#### 1.9 Setup State Verification
- [ ] Navigate back to `/setup`
- [ ] **Expected:** Setup wizard accessible (for re-running)
- [ ] **Actual:** _______________
- [ ] API call `GET /api/setup/status` shows `completed: true`

### Test Results
- [ ] **PASS** - All steps completed successfully
- [ ] **FAIL** - Issues found (document below)

**Issues/Notes:**
```
_______________
_______________
_______________
```

---

## Test Suite 2: Localhost to LAN Conversion Flow

### Objective
Verify converting an existing localhost installation to LAN mode.

### Prerequisites
- [ ] Setup completed in localhost mode (from Test Suite 1)
- [ ] Backend running on localhost
- [ ] Know your LAN IP address: _______________

### Test Steps

#### 2.1 Access Setup Wizard
- [ ] Navigate to `http://localhost:7274/setup`
- [ ] **Expected:** Setup wizard loads (re-run mode)
- [ ] **Actual:** _______________
- [ ] Current configuration displayed

#### 2.2 Navigate to Network Step
- [ ] Click through wizard to Step 4 (Network Configuration)
- [ ] Previous settings preserved:
  - [ ] Tools attached: _______________
  - [ ] Serena enabled: _______________

#### 2.3 Select LAN Mode
- [ ] Click "LAN" mode radio button
- [ ] **Expected:** LAN configuration fields appear
- [ ] **Actual:** _______________
- [ ] Fields visible:
  - [ ] Server IP address
  - [ ] Hostname
  - [ ] Admin username
  - [ ] Admin password
  - [ ] Firewall configured checkbox

#### 2.4 Configure LAN Settings
- [ ] Enter Server IP: _______________
- [ ] Enter Hostname: `giljo.local`
- [ ] Enter Admin Username: `admin`
- [ ] Enter Admin Password: _______________
- [ ] Check "Firewall configured"
- [ ] Click "Next" to Step 5

#### 2.5 Review LAN Configuration
- [ ] Summary shows LAN mode selected
- [ ] LAN settings displayed:
  - [ ] Server IP: _______________
  - [ ] Hostname: _______________
  - [ ] Admin account configured: Yes
- [ ] Click "Save and Exit"

#### 2.6 LAN Confirmation Modal
- [ ] **Expected:** LAN confirmation modal appears
- [ ] **Actual:** _______________
- [ ] Modal title: "Confirm LAN Mode Configuration"
- [ ] Warning message displays security implications
- [ ] "Cancel" button visible
- [ ] "Yes, Configure for LAN" button visible

#### 2.7 Test Cancel Flow
- [ ] Click "Cancel"
- [ ] **Expected:** Modal closes, return to summary screen
- [ ] **Actual:** _______________
- [ ] Can re-click "Save and Exit" to retry

#### 2.8 Confirm LAN Configuration
- [ ] Click "Save and Exit" again
- [ ] LAN confirmation modal appears
- [ ] Click "Yes, Configure for LAN"
- [ ] **Expected:** Loading overlay: "Saving configuration..."
- [ ] **Actual:** _______________

#### 2.9 API Key Modal
- [ ] **Expected:** API key modal appears
- [ ] **Actual:** _______________
- [ ] Modal title: "Your API Key"
- [ ] API key displayed: `gk_xxxxxxxxxxxxxxxxxx`
- [ ] Warning message: "Save this API key securely"
- [ ] Copy button (clipboard icon) visible
- [ ] Confirmation checkbox visible
- [ ] "Continue" button visible but disabled

#### 2.10 Copy API Key
- [ ] Click copy button (clipboard icon)
- [ ] **Expected:** Icon changes to checkmark
- [ ] **Actual:** _______________
- [ ] API key copied to clipboard (verify by pasting): _______________
- [ ] Checkmark reverts to clipboard icon after 3 seconds

#### 2.11 Confirm API Key Saved
- [ ] Check "I have saved this API key securely"
- [ ] **Expected:** "Continue" button becomes enabled
- [ ] **Actual:** _______________
- [ ] Click "Continue"

#### 2.12 Restart Instructions Modal
- [ ] **Expected:** Restart modal appears
- [ ] **Actual:** _______________
- [ ] Modal title: "Restart Services Required"
- [ ] Success message: "Setup Complete! Configuration saved..."
- [ ] Platform-specific instructions displayed (Windows/macOS/Linux)
- [ ] Instructions include:
  - [ ] Stop backend only command
  - [ ] Start backend only command
  - [ ] Wait time (10-15 seconds)
  - [ ] Note: Frontend does not need restart

#### 2.13 Platform-Specific Instructions
**For Windows:**
- [ ] Instructions show: `stop_backend.bat`
- [ ] Instructions show: `start_backend.bat`
- [ ] Installation path displayed: _______________

**For macOS/Linux:**
- [ ] Instructions show: `./stop_backend.sh`
- [ ] Instructions show: `./start_backend.sh`

#### 2.14 Restart Backend Services
- [ ] Open terminal/command prompt
- [ ] Navigate to installation directory
- [ ] Run stop backend command
- [ ] **Expected:** Backend stops gracefully
- [ ] **Actual:** _______________
- [ ] Run start backend command
- [ ] **Expected:** Backend starts in LAN mode
- [ ] **Actual:** _______________
- [ ] Wait 10-15 seconds

#### 2.15 Verify LAN Mode Activation
- [ ] In restart modal, click "I've Restarted - Go to Dashboard"
- [ ] **Expected:** Redirect to dashboard
- [ ] **Actual:** _______________
- [ ] Dashboard loads successfully
- [ ] **Expected:** Green banner: "LAN Mode Activated"
- [ ] **Actual:** _______________

#### 2.16 Backend Configuration Verification
- [ ] Check backend logs for LAN mode activation
- [ ] Verify API binds to `0.0.0.0` (not `127.0.0.1`)
- [ ] Verify API key authentication enabled
- [ ] Try accessing from another device (if available): _______________

### Test Results
- [ ] **PASS** - All steps completed successfully
- [ ] **FAIL** - Issues found (document below)

**Issues/Notes:**
```
_______________
_______________
_______________
```

---

## Test Suite 3: Router Guard Behavior

### Objective
Verify router guards correctly handle setup completion status.

### Test Steps

#### 3.1 Fresh Install Redirect
- [ ] Clear setup state: `DELETE FROM setup_state`
- [ ] Navigate to `http://localhost:7274/`
- [ ] **Expected:** Redirect to `/setup`
- [ ] **Actual:** _______________

#### 3.2 Completed Setup Access
- [ ] Complete setup (any mode)
- [ ] Navigate to `http://localhost:7274/`
- [ ] **Expected:** Dashboard loads (no redirect)
- [ ] **Actual:** _______________

#### 3.3 Re-run Wizard Access
- [ ] With setup completed, navigate to `/setup`
- [ ] **Expected:** Setup wizard loads
- [ ] **Actual:** _______________
- [ ] Can modify configuration
- [ ] Can re-run setup process

#### 3.4 Direct Route Access
- [ ] Navigate to `http://localhost:7274/projects`
- [ ] **Expected:** Projects page loads (if setup complete)
- [ ] **Expected:** Redirect to `/setup` (if setup incomplete)
- [ ] **Actual:** _______________

#### 3.5 API Failure Handling
- [ ] Stop backend API
- [ ] Navigate to `http://localhost:7274/`
- [ ] **Expected:** Page loads (fails gracefully)
- [ ] Console message: "Setup status check unavailable"
- [ ] **Actual:** _______________

### Test Results
- [ ] **PASS** - All steps completed successfully
- [ ] **FAIL** - Issues found (document below)

**Issues/Notes:**
```
_______________
_______________
_______________
```

---

## Test Suite 4: Error Handling

### Objective
Verify graceful error handling throughout the wizard.

### Test Steps

#### 4.1 Network Error During Setup
- [ ] Start setup wizard
- [ ] Navigate to final step
- [ ] Stop backend API
- [ ] Click "Save and Exit"
- [ ] **Expected:** Error message displayed
- [ ] **Actual:** _______________
- [ ] User can retry or cancel

#### 4.2 Invalid Configuration
- [ ] Configure LAN mode
- [ ] Enter invalid IP address: `999.999.999.999`
- [ ] Try to proceed
- [ ] **Expected:** Validation error shown
- [ ] **Actual:** _______________

#### 4.3 Database Connection Failure
- [ ] Stop PostgreSQL
- [ ] Start setup wizard
- [ ] Database check step
- [ ] **Expected:** Connection error displayed
- [ ] **Actual:** _______________
- [ ] User can retry connection

#### 4.4 API Timeout
- [ ] Configure artificially slow API response
- [ ] Complete setup
- [ ] **Expected:** Loading indicator shows
- [ ] **Expected:** Timeout after reasonable duration
- [ ] **Actual:** _______________

### Test Results
- [ ] **PASS** - All steps completed successfully
- [ ] **FAIL** - Issues found (document below)

**Issues/Notes:**
```
_______________
_______________
_______________
```

---

## Test Suite 5: Browser Compatibility

### Objective
Verify wizard works across different browsers.

### Test Matrix

| Browser | Version | Fresh Install | LAN Conversion | Router Guards | Errors Handled | Pass/Fail |
|---------|---------|---------------|----------------|---------------|----------------|-----------|
| Chrome  | _______ | [ ]           | [ ]            | [ ]           | [ ]            | [ ]       |
| Edge    | _______ | [ ]           | [ ]            | [ ]           | [ ]            | [ ]       |
| Firefox | _______ | [ ]           | [ ]            | [ ]           | [ ]            | [ ]       |
| Safari  | _______ | [ ]           | [ ]            | [ ]           | [ ]            | [ ]       |

**Notes:**
```
_______________
_______________
_______________
```

---

## Test Suite 6: UI/UX Verification

### Objective
Verify visual and user experience quality.

### Test Steps

#### 6.1 Visual Consistency
- [ ] Logo displays correctly (light/dark theme)
- [ ] Stepper shows all steps clearly
- [ ] Step indicators update correctly
- [ ] Colors match Vuetify theme
- [ ] No layout shifts during navigation

#### 6.2 Responsive Design
- [ ] Desktop (1920x1080): [ ] PASS [ ] FAIL
- [ ] Laptop (1366x768): [ ] PASS [ ] FAIL
- [ ] Tablet (768x1024): [ ] PASS [ ] FAIL
- [ ] Mobile (375x667): [ ] PASS [ ] FAIL

#### 6.3 Accessibility
- [ ] Tab navigation works through all steps
- [ ] Focus indicators visible
- [ ] Screen reader compatible (test with NVDA/JAWS if available)
- [ ] ARIA labels present
- [ ] Color contrast meets WCAG AA standards

#### 6.4 User Feedback
- [ ] Loading states clear and visible
- [ ] Success messages displayed
- [ ] Error messages helpful and actionable
- [ ] Progress indicator shows current step
- [ ] Back navigation works correctly

### Test Results
- [ ] **PASS** - All steps completed successfully
- [ ] **FAIL** - Issues found (document below)

**Issues/Notes:**
```
_______________
_______________
_______________
```

---

## Test Suite 7: State Persistence

### Objective
Verify wizard state persists correctly across backend restarts and page reloads.

### Test Steps

#### 7.1 Backend State Persistence
- [ ] Complete setup (any mode)
- [ ] Restart backend API
- [ ] Navigate to dashboard
- [ ] **Expected:** `GET /api/setup/status` returns `completed: true`
- [ ] **Actual:** _______________

#### 7.2 Frontend State During Wizard
- [ ] Start setup wizard
- [ ] Progress to Step 3
- [ ] Refresh browser (F5)
- [ ] **Expected:** Wizard restarts from Step 1 (no session persistence in fresh install)
- [ ] **Actual:** _______________

#### 7.3 LocalStorage Flags
- [ ] Complete LAN setup
- [ ] Check localStorage: `giljo_lan_setup_complete`
- [ ] **Expected:** Value is `'true'`
- [ ] **Actual:** _______________
- [ ] Dashboard shows LAN banner

### Test Results
- [ ] **PASS** - All steps completed successfully
- [ ] **FAIL** - Issues found (document below)

**Issues/Notes:**
```
_______________
_______________
_______________
```

---

## Console Verification

Throughout all tests, monitor browser console for:

### Expected Console Messages
- [ ] `[WIZARD] Component mounted`
- [ ] `[WIZARD] Loaded installation info`
- [ ] `[WIZARD] Completing setup with config`
- [ ] `[WIZARD] Setup marked as complete`
- [ ] `Setup not completed, redirecting to setup wizard` (fresh install)

### Unexpected Console Messages
- [ ] No JavaScript errors
- [ ] No unhandled promise rejections
- [ ] No Vuetify warnings
- [ ] No 404 API errors

**Console Errors Found:**
```
_______________
_______________
_______________
```

---

## Network Monitoring

### API Calls to Verify

#### Setup Status Check
- [ ] `GET /api/setup/status`
- [ ] Response: `{ completed: true/false, ... }`

#### Installation Info
- [ ] `GET /api/setup/installation-info`
- [ ] Response: `{ installation_path: "...", platform: "..." }`

#### Complete Setup
- [ ] `POST /api/setup/complete`
- [ ] Request body includes: `tools_attached`, `network_mode`, `lan_config`
- [ ] Response: `{ success: true, api_key: "...", requires_restart: true/false }`

#### Database Verification
- [ ] `GET /api/setup/database/verify` (if implemented)

### Network Issues Found
```
_______________
_______________
_______________
```

---

## Overall Test Summary

### Test Suites Completed
- [ ] Test Suite 1: Fresh Install Flow
- [ ] Test Suite 2: Localhost to LAN Conversion Flow
- [ ] Test Suite 3: Router Guard Behavior
- [ ] Test Suite 4: Error Handling
- [ ] Test Suite 5: Browser Compatibility
- [ ] Test Suite 6: UI/UX Verification
- [ ] Test Suite 7: State Persistence

### Pass/Fail Summary
- **Total Tests:** _______
- **Passed:** _______
- **Failed:** _______
- **Skipped:** _______

### Critical Issues
```
Priority 1 (Blockers):
_______________

Priority 2 (Major):
_______________

Priority 3 (Minor):
_______________
```

### Acceptance Criteria Met
- [ ] Router guards work correctly with new state API
- [ ] Fresh install flow completes successfully
- [ ] Localhost to LAN conversion shows API key modal
- [ ] API key modal copy/confirm functionality works
- [ ] Restart modal appears after API key
- [ ] Dashboard banner renders for LAN mode
- [ ] No console errors during wizard flow
- [ ] Backward compatible with existing wizard
- [ ] Error messages display correctly

### Final Recommendation
- [ ] **APPROVED** - Ready for production
- [ ] **APPROVED WITH NOTES** - Minor issues, can deploy
- [ ] **NOT APPROVED** - Critical issues must be fixed

---

## Tester Information

**Tester Name:** _______________
**Date Tested:** _______________
**Environment:** _______________
**Build/Commit:** _______________

**Signature:** _______________
