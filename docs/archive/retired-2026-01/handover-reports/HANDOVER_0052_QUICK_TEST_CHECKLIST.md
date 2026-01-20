# Quick Test Checklist - Context Priority Management (Handover 0052)

**Feature**: Context Priority Management with Unassigned Fields  
**Component**: `frontend/src/views/UserSettings.vue`  
**Estimated Time**: 45-60 minutes  
**Prepared**: 2025-01-27  

---

## Pre-Test Setup (5 minutes)

- [ ] Backend running: `python startup.py`
- [ ] Frontend running: `cd frontend && npm run dev`
- [ ] Browser: Chrome/Firefox/Edge (latest)
- [ ] DevTools open: F12
- [ ] URL: `http://localhost:7273/settings?tab=general`
- [ ] Active product exists in system
- [ ] Database accessible (PostgreSQL running)

---

## Phase 1: Bug Fix (5 minutes)

**Objective**: Verify resetGeneralSettings() bug is fixed

- [ ] **Test 1.1**: Click Reset button
  - [ ] No console errors
  - [ ] No "projectName" in error messages
  - [ ] Page doesn't crash
  - [ ] Settings unchanged (reset is for defaults)

- [ ] **Test 1.2**: Save after Reset
  - [ ] Click "Save Changes" button
  - [ ] Save completes successfully (200 OK)
  - [ ] No API errors
  - [ ] No console errors

**Status**: ✅ / ❌ (circle one)

---

## Phase 2: Unassigned Category (20 minutes)

**Objective**: Verify Unassigned Fields category works

### Feature Visibility
- [ ] Unassigned card visible with dashed border
- [ ] "Unassigned Fields" title visible
- [ ] "0 tokens" badge visible
- [ ] Scrollbar indicates multiple categories

### Remove Field Tests
- [ ] **Test 2.1**: Remove from Priority 1
  - [ ] Click X on Priority 1 field
  - [ ] Field moves to Unassigned
  - [ ] Token count decreases by 50
  - [ ] Save button enabled (blue)

- [ ] **Test 2.2**: Remove from Priority 2
  - [ ] Click X on Priority 2 field
  - [ ] Field moves to Unassigned
  - [ ] Token count decreases by 30

- [ ] **Test 2.3**: Remove from Priority 3
  - [ ] Click X on Priority 3 field
  - [ ] Field moves to Unassigned
  - [ ] Token count decreases by 20

### Drag Tests
- [ ] **Test 2.4**: Drag Priority 2 → Unassigned
  - [ ] Drag smoothly completes
  - [ ] Field in Unassigned after drop
  - [ ] Token count decreases by 30
  - [ ] No duplicates

- [ ] **Test 2.5**: Drag Unassigned → Priority 3
  - [ ] Drag smoothly completes
  - [ ] Field in Priority 3 after drop
  - [ ] Token count increases by 20
  - [ ] No duplicates

### All Unassigned Test
- [ ] **Test 2.6**: Remove all fields
  - [ ] All Priority categories empty
  - [ ] All 13 fields in Unassigned
  - [ ] Token count = 500 (mission overhead only)
  - [ ] "All fields are assigned to priorities" message visible

### Save & Reload Test
- [ ] **Test 2.7**: Save and verify persistence
  - [ ] Click "Save Field Priority"
  - [ ] Console: "Field priority config saved successfully"
  - [ ] Refresh page (F5)
  - [ ] Configuration restored correctly
  - [ ] All changes persisted

### Reset Test
- [ ] **Test 2.8**: Reset to Defaults
  - [ ] Click "Reset to Defaults" button
  - [ ] Priority 1, 2, 3 populated
  - [ ] Console: "reset to defaults" message
  - [ ] Unassigned has remaining fields

**Status**: ✅ / ❌ (circle one)

---

## Phase 3: Real-Time Token Estimation (15 minutes)

**Objective**: Verify token counter is real-time and accurate

### Real-Time Updates
- [ ] **Test 3.1**: Token updates during drag
  - [ ] Note current token count
  - [ ] Drag field from P1 to P2
  - [ ] Token count updates immediately (<100ms)
  - [ ] Count accurate: -20 (50→30 value change)

- [ ] **Test 3.2**: Token updates on remove
  - [ ] Note current token count
  - [ ] Click X on Priority 1 field
  - [ ] Token count decreases immediately
  - [ ] Decrease exactly -50 (P1 token cost)

### Color Indicator Tests
- [ ] **Test 3.3**: Token indicator color - GREEN
  - [ ] At <70% usage: indicator GREEN
  - [ ] Example: 450/2000 = 22% (green ✓)
  - [ ] Progress circle shows green

- [ ] **Test 3.4**: Token indicator color - YELLOW
  - [ ] At 70-90% usage: indicator YELLOW
  - [ ] Drag fields to P1 until 70%+
  - [ ] Progress circle shows yellow/orange
  - [ ] Percentage visible in circle

- [ ] **Test 3.5**: Token indicator color - RED
  - [ ] At >90% usage: indicator RED
  - [ ] Continue dragging to P1 until 90%+
  - [ ] Progress circle shows red
  - [ ] Warning color clear

### Active Product Data
- [ ] **Test 3.6**: Real product token data used
  - [ ] Token card shows product name
  - [ ] Token count ≠ static estimate
  - [ ] Example: 450 tokens (real data, not calculated)
  - [ ] Matches active product data

### Token Refresh
- [ ] **Test 3.7**: Token refresh after save
  - [ ] Move fields around
  - [ ] Click "Save Field Priority"
  - [ ] Console: "Active product token estimate loaded"
  - [ ] Token count refreshed from API
  - [ ] Accurate after save

**Status**: ✅ / ❌ (circle one)

---

## Phase 4: Edge Cases (10 minutes)

**Objective**: Verify error handling and edge cases

### Empty States
- [ ] **Test 4.1**: All fields assigned
  - [ ] Move all fields to priorities
  - [ ] Unassigned shows: "All fields are assigned to priorities"
  - [ ] Message centered with icon
  - [ ] No field chips visible

- [ ] **Test 4.2**: All fields unassigned
  - [ ] Remove all fields to Unassigned
  - [ ] Priority 1 shows: "No fields assigned to Priority 1"
  - [ ] Priority 2 shows: "No fields assigned to Priority 2"
  - [ ] Priority 3 shows: "No fields assigned to Priority 3"
  - [ ] Message visible in each card

### Rapid Operations
- [ ] **Test 4.3**: Rapid field movements
  - [ ] Quickly drag: Field A P1→P2→P3→Unassigned→P1
  - [ ] No duplicates (field appears once)
  - [ ] Total field count still = 13
  - [ ] Token count accurate throughout

### Save Button Logic
- [ ] **Test 4.4**: Save button enable/disable
  - [ ] Load page: button disabled (grey)
  - [ ] Drag field: button enabled (blue)
  - [ ] Click Save: button disabled (grey)
  - [ ] No changes: button stays disabled

**Status**: ✅ / ❌ (circle one)

---

## Accessibility (5 minutes)

- [ ] **Test A.1**: Keyboard navigation
  - [ ] Tab through all elements
  - [ ] Reach all buttons and fields
  - [ ] Focus indicators visible (outline)
  - [ ] Logical order (top to bottom)

- [ ] **Test A.2**: Touch targets
  - [ ] Field chips ≥48px height
  - [ ] Buttons ≥48px height
  - [ ] Mobile: ≥56px height (if testing)

**Status**: ✅ / ❌ (circle one)

---

## Code Quality (5 minutes)

- [ ] **Test C.1**: Console errors
  - [ ] Open DevTools Console
  - [ ] Clear console
  - [ ] Perform entire workflow
  - [ ] Check for console.error() messages
  - [ ] Result: **0 errors** or **errors found**

- [ ] **Test C.2**: API requests
  - [ ] Open DevTools Network tab
  - [ ] Click Save
  - [ ] Find POST to `/api/v1/users/field-priority-config`
  - [ ] Verify: 200 OK response
  - [ ] Unassigned fields NOT in request payload

**Status**: ✅ / ❌ (circle one)

---

## Performance (Optional)

- [ ] **Test P.1**: Token calculation speed
  - [ ] Open DevTools Performance tab
  - [ ] Start recording
  - [ ] Drag field: P1→P2
  - [ ] Stop recording
  - [ ] Token update: <100ms
  - [ ] Drag animation: 60fps (16.67ms per frame)

**Status**: ✅ / ❌ (circle one)

---

## Final Verification

### Critical Path Test (5 minutes)
Complete workflow in sequence:

1. [ ] Load page - UI appears
2. [ ] Drag field P1→P2 - token updates, save enabled
3. [ ] Click Save - saves successfully, API 200 OK
4. [ ] Refresh page - config persists
5. [ ] Drag field P2→Unassigned - field moves, token decreases
6. [ ] Click Reset to Defaults - original state restored
7. [ ] Save again - no errors

**Status**: ✅ PASS / ❌ FAIL

---

## Issues Found

**Issue #1**: [Describe any issue found]
- Reproduction steps:
- Expected result:
- Actual result:
- Severity: Critical / High / Medium / Low

**Issue #2**: [Describe any issue found]
- Reproduction steps:
- Expected result:
- Actual result:
- Severity: Critical / High / Medium / Low

**Total Issues Found**: _____

---

## Sign-Off

**Tester Name**: ________________________  
**Date**: ________________________  
**Time Spent**: _______ minutes  
**All Tests Passed**: ✅ YES / ❌ NO  

### Summary
```
Total Test Cases: 32
Tests Passed: _____
Tests Failed: _____
Success Rate: ____%

Major Issues: _____
Minor Issues: _____
```

### Recommendation
- [ ] **PASS** - Ready for production deployment
- [ ] **PASS WITH ISSUES** - Fix issues, re-test
- [ ] **FAIL** - Critical issues found, do not deploy

**Comments**:
```
[Any additional observations or notes]
```

---

## Next Steps

### If All Tests Pass:
1. Commit to git
2. Create PR with test results
3. Deploy to staging
4. Conduct UAT
5. Deploy to production

### If Tests Fail:
1. Document issues
2. Create bug report
3. Assign to developer
4. Fix and re-test
5. Repeat testing cycle

---

## Resources

- **Detailed Test Spec**: `TEST_RESULTS_0052.md`
- **Summary Document**: `TESTING_SUMMARY_0052.md`
- **Source Code**: `frontend/src/views/UserSettings.vue`
- **Handover 0052**: `handovers/0052_context_priority_unassigned_category.md`
- **Console Logs**: Look for `[USER SETTINGS]` prefix

---

## Key Verification Points

- ✅ resetGeneralSettings() contains no projectName reference
- ✅ Unassigned category UI fully visible
- ✅ Drag-and-drop works all 4 ways (P1↔P2, P2↔P3, P3↔Unassigned, etc.)
- ✅ Token counter updates real-time without save
- ✅ Configuration persists after page reload
- ✅ Reset to defaults works correctly
- ✅ No console errors during entire workflow
- ✅ All 13 fields always appear somewhere in UI
- ✅ Real product data used for token estimation
- ✅ Touch targets accessible (48px minimum)

---

**Quick Test Checklist Complete**  
**Ready for execution: 2025-01-27**  
**Time estimate: 45-60 minutes**  

