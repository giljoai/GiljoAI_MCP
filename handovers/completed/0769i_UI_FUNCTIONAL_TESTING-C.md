# 0769i: UI & Functional Testing (Browser-Based)

**Series:** 0769 (Code Quality & Fragility Remediation Sprint)
**Phase:** 9 of 9 (extension — final)
**Branch:** `feature/0769-quality-sprint`
**Priority:** HIGH — no manual verification after major refactors
**Estimated Time:** 1-2 hours

### Reference Documents
- **Audit report:** `handovers/0769_CODE_QUALITY_FRAGILITY_AUDIT.md`
- **Project rules:** `CLAUDE.md`

### Tracking Files
- **Chain log:** `prompts/0769_chain/chain_log.json`

---

## Context

The 0769 sprint (phases a-g) made significant changes: service splits, design token replacements, event router restructuring, WebSocket reconnect fixes, config consolidation, and startup hardening. All automated checks pass (ruff, ESLint, vitest), but nobody has verified the application actually works end-to-end in a browser.

This phase performs manual browser-based verification using the Chrome automation plugin against the live development server.

---

## Test Environment

- **URL:** `https://10.1.0.116:7274/home`
- **Backend port:** 7272
- **Frontend port:** 7274
- **Credentials:** User logs in manually (agent does NOT enter passwords)
- **Protocol:** HTTPS (self-signed cert — accept security warning if prompted)

---

## Scope

### Test Suite 1: Application Startup & Login

1. Navigate to `https://10.1.0.116:7274`
2. Verify login page loads without console errors
3. User logs in manually
4. Verify redirect to dashboard/home
5. Check browser console for JavaScript errors

### Test Suite 2: Dashboard Verification

After login:
1. Verify dashboard loads completely
2. Check that stat boxes render (not blank/broken)
3. Verify DonutChart renders (0769d replaced hardcoded colors with tokens)
4. Check Recent Projects list renders with formatted dates (0769d introduced useFormatDate)
5. Check navigation drawer renders correctly (0769d fixed border violations)
6. Check AppBar renders correctly
7. Check browser console for errors

### Test Suite 3: WebSocket Connectivity

1. Check that WebSocket connection establishes (0769e fixed reconnect race)
2. Verify no duplicate connection warnings in console
3. Check that real-time status indicators update (if any agents are running)

### Test Suite 4: Project View

1. Navigate to Projects view
2. Verify project list loads
3. Check that status badges render correctly (0769b confirmed display-only v-chip)
4. Check filter chips render (0769b fixed taxonomy filter selectors)
5. Verify date formatting consistency (should use new useFormatDate composable)

### Test Suite 5: Product View

1. Navigate to Products view
2. Verify product list loads
3. Open a product detail dialog
4. Verify tab order is correct (0769b found: setup, info, ... not basic, vision, ...)
5. Check product form fields render correctly

### Test Suite 6: Settings View

1. Navigate to Settings
2. Verify all settings tabs load
3. Check integration cards render correctly (0769b updated text: "Git + GiljoAI 360 Memory")
4. Check Network settings tab (0769b updated HTTPS instructions text)
5. Check MCP integration card description

### Test Suite 7: Console Error Audit

After navigating through all major views:
1. Read browser console for any JavaScript errors
2. Read browser console for any failed network requests (4xx, 5xx)
3. Read browser console for any WebSocket errors
4. Document ALL errors found with the page/route where they occurred

---

## Error Handling Protocol

**If any test reveals an unexpected UI behavior:**
1. Take a screenshot or note the exact state
2. Check the browser console for the error
3. Check if the error relates to a 0769 sprint change
4. If it's a regression from the sprint: document in chain log `blockers_encountered` and STOP
5. If it's a pre-existing issue: document in chain log `deviations` as "pre-existing" and continue

**If the application fails to load or crashes:**
1. Check if the backend is running on port 7272
2. Check if the frontend is running on port 7274
3. If ports are locked: `netstat -ano | findstr :7272` and `netstat -ano | findstr :7274` to find PIDs
4. Ask the user for direction before force-stopping any processes

---

## Agent Protocols (MANDATORY)

### Rejection Authority
If a UI element looks different but functions correctly, that is NOT a failure. Only flag actual broken functionality, JavaScript errors, or missing data.

### Flow Investigation
If you find a console error, trace it to the source component. Check if the component was modified in the 0769 sprint (check git log). If the error predates the sprint, note it as pre-existing.

### Pause and Ask
If you encounter ANY unexpected reaction — a page that won't load, a component that crashes, a WebSocket that won't connect — PAUSE and ask the user for input. Do NOT try to fix production code during UI testing.

---

## What NOT To Do

- Do NOT enter passwords or sensitive credentials (user logs in manually)
- Do NOT modify any source code
- Do NOT restart the backend or frontend without asking the user
- Do NOT force-stop processes without asking the user
- Do NOT create or delete any data in the application (read-only testing)
- Do NOT accept cookies or terms without asking the user

---

## Acceptance Criteria

- [ ] Application loads and login works
- [ ] Dashboard renders correctly (stat boxes, charts, recent projects)
- [ ] WebSocket connects without errors
- [ ] Project view loads and displays correctly
- [ ] Product view loads with correct tab order
- [ ] Settings view loads with correct integration card text
- [ ] Browser console has zero JavaScript errors (or all errors documented as pre-existing)
- [ ] All findings documented in chain log

---

## Chain Execution Instructions

### Step 1: Read Chain Log
Read `prompts/0769_chain/chain_log.json`
- Check `orchestrator_directives`
- Review 0769h's `notes_for_next` for any startup issues found

### Step 2: Mark Session Started
Update your session: `"status": "in_progress", "started_at": "<timestamp>"`

### Step 3: Execute Test Suites
Work through Test Suites 1-7 in order. Document results for each suite.

### Step 4: Update Chain Log
This is the FINAL session. Update your session AND:
- Set `chain_summary` with overall sprint results (including UI testing)
- Set `final_status` to `"complete"`
- Document all console errors found
- Note any pre-existing issues vs regressions

### Step 5: STOP
This is the last phase. Commit chain log update and exit.
