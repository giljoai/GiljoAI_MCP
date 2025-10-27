# Testing Plan: Product Form Auto-Save & UX Polish

**Date**: 2025-10-27
**Handover**: 0051

## Testing Strategy

### Testing Levels

1. **Unit Testing**: Auto-save composable functions
2. **Integration Testing**: Auto-save with ProductsView component
3. **Manual Testing**: User workflows and edge cases
4. **Cross-Browser Testing**: Chrome, Firefox, Safari, Edge
5. **Accessibility Testing**: Screen readers, keyboard navigation

## Critical Test Scenarios

### Scenario 1: Basic Save Flow

**Objective**: Verify product can be saved successfully with all tabs filled

**Prerequisites**:
- Database running
- User logged in
- Products page loaded

**Steps**:
1. Click "New Product" button
2. Fill "Basic Info" tab:
   - Name: "Test Product Auto-Save"
   - Description: "Testing auto-save feature"
3. Navigate to "Vision Docs" tab (optional, skip)
4. Navigate to "Tech Stack" tab:
   - Languages: "Python, JavaScript"
   - Frontend: "Vue 3, Vuetify"
   - Backend: "FastAPI, SQLAlchemy"
   - Database: "PostgreSQL"
   - Infrastructure: "Docker"
5. Navigate to "Architecture" tab:
   - Pattern: "Layered Architecture"
   - Design Patterns: "Repository, Factory"
   - API Style: "REST"
   - Notes: "Standard MVC approach"
6. Navigate to "Features & Testing" tab:
   - Core Features: "User auth, Product CRUD"
   - Testing Strategy: "TDD"
   - Coverage Target: 80
   - Frameworks: "pytest, Playwright"
7. Click "Save" button

**Expected Results**:
- ✅ Success toast message appears
- ✅ Dialog closes
- ✅ Product appears in products list
- ✅ Product card shows name and description
- ✅ Database query shows configData JSON populated
- ✅ Reopening product shows all fields filled correctly

**Test Data Verification**:
```sql
SELECT id, name, description, config_data FROM products
WHERE name = 'Test Product Auto-Save';
```

Expected `config_data`:
```json
{
  "tech_stack": {
    "languages": "Python, JavaScript",
    "frontend": "Vue 3, Vuetify",
    "backend": "FastAPI, SQLAlchemy",
    "database": "PostgreSQL",
    "infrastructure": "Docker"
  },
  "architecture": {
    "pattern": "Layered Architecture",
    "design_patterns": "Repository, Factory",
    "api_style": "REST",
    "notes": "Standard MVC approach"
  },
  "features": {
    "core": "User auth, Product CRUD"
  },
  "test_config": {
    "strategy": "TDD",
    "coverage_target": 80,
    "frameworks": "pytest, Playwright"
  }
}
```

---

### Scenario 2: Auto-Save to LocalStorage

**Objective**: Verify form data is automatically saved to LocalStorage as user types

**Prerequisites**:
- Browser DevTools open (Application tab)
- LocalStorage cleared

**Steps**:
1. Click "New Product" button
2. Open DevTools → Application → LocalStorage
3. Type in "Product Name" field: "Auto-Save Test"
4. Wait 600ms (debounce delay + buffer)
5. Check LocalStorage for key: `product_form_draft_new`
6. Fill "Tech Stack" → "Languages" field: "Python"
7. Wait 600ms
8. Check LocalStorage again

**Expected Results**:
- ✅ LocalStorage key `product_form_draft_new` created
- ✅ Value contains JSON with productForm data
- ✅ Data includes timestamp
- ✅ Data updates after each field change (debounced)

**Example LocalStorage Entry**:
```json
{
  "data": {
    "name": "Auto-Save Test",
    "description": "",
    "visionPath": "",
    "configData": {
      "tech_stack": {
        "languages": "Python",
        "frontend": "",
        "backend": "",
        "database": "",
        "infrastructure": ""
      },
      // ... other fields
    }
  },
  "timestamp": 1698765432000
}
```

---

### Scenario 3: Draft Recovery

**Objective**: Verify user can recover unsaved changes after closing dialog

**Prerequisites**:
- Scenario 2 completed (data in LocalStorage)

**Steps**:
1. With dialog open and data filled, click "Cancel" or close dialog
2. Click "New Product" again to reopen dialog
3. Observe restore confirmation dialog

**Expected Results**:
- ✅ Confirmation prompt appears: "Found unsaved changes from a previous session. Do you want to restore them?"
- ✅ If "OK" clicked: Form fields populated with cached data
- ✅ If "Cancel" clicked: Form fields empty, cache cleared

**Variations**:
- Test with "Yes" to restore
- Test with "No" to discard
- Verify cache cleared after "No"

---

### Scenario 4: Tab Navigation Persistence

**Objective**: Verify data persists when navigating between tabs

**Steps**:
1. Click "New Product"
2. Fill "Basic Info" → Name: "Tab Test"
3. Navigate to "Tech Stack" tab
4. Fill Languages: "JavaScript"
5. Navigate to "Architecture" tab
6. Fill Pattern: "Microservices"
7. Navigate back to "Basic Info" tab
8. Navigate back to "Tech Stack" tab
9. Navigate back to "Architecture" tab

**Expected Results**:
- ✅ "Basic Info" → Name still shows "Tab Test"
- ✅ "Tech Stack" → Languages still shows "JavaScript"
- ✅ "Architecture" → Pattern still shows "Microservices"
- ✅ No data loss during navigation

---

### Scenario 5: Save Status Indicator

**Objective**: Verify save status chip updates correctly

**Steps**:
1. Click "New Product"
2. Observe status chip (should not be visible or show "Saved")
3. Type in any field
4. Observe status chip immediately after typing
5. Wait 600ms (debounce + save time)
6. Observe status chip after save completes

**Expected Results**:
- ✅ Initial state: No chip or "Saved" chip
- ✅ During typing: "Unsaved changes" chip appears (yellow/warning)
- ✅ After auto-save: "Saved" chip appears (green/success)
- ✅ Chip includes appropriate icon (mdi-content-save-alert or mdi-check)

---

### Scenario 6: Unsaved Changes Warning (Dialog Close)

**Objective**: Verify warning appears when closing dialog with unsaved changes

**Steps**:
1. Click "New Product"
2. Type in any field: "Test"
3. Wait for auto-save (600ms)
4. Type more: "Test 123" (creating unsaved changes)
5. Immediately click "Cancel" button (before auto-save completes)

**Expected Results**:
- ✅ Browser confirmation dialog appears
- ✅ Message: "You have unsaved changes. Close without saving?"
- ✅ If "OK": Dialog closes, cache cleared
- ✅ If "Cancel": Dialog remains open, data preserved

---

### Scenario 7: Unsaved Changes Warning (Browser Refresh)

**Objective**: Verify warning appears when refreshing browser with unsaved changes

**Steps**:
1. Click "New Product"
2. Fill multiple fields
3. Ensure dialog is open
4. Press F5 or Ctrl+R to refresh browser

**Expected Results**:
- ✅ Browser shows default "Leave site?" warning
- ✅ Warning only appears if dialog is open AND has unsaved changes
- ✅ If confirmed: Page refreshes, cache preserved in LocalStorage
- ✅ If cancelled: Page doesn't refresh, data remains

---

### Scenario 8: Cache Cleared After Successful Save

**Objective**: Verify LocalStorage cache is cleared after successful save

**Prerequisites**:
- DevTools open (Application tab)
- LocalStorage visible

**Steps**:
1. Click "New Product"
2. Fill form fields
3. Wait for auto-save (verify cache in LocalStorage)
4. Click "Save" button
5. Wait for success toast
6. Check LocalStorage for `product_form_draft_new` key

**Expected Results**:
- ✅ Cache exists in LocalStorage before clicking "Save"
- ✅ After successful save: Cache key removed from LocalStorage
- ✅ Reopening dialog: No restore prompt (cache cleared)

---

### Scenario 9: Edit Existing Product

**Objective**: Verify auto-save works when editing existing product

**Steps**:
1. Create a product (or use existing)
2. Click "Edit" on product card
3. Verify form fields populated with existing data
4. Check LocalStorage for key: `product_form_draft_{product_id}`
5. Modify a field
6. Wait 600ms
7. Check LocalStorage value updated

**Expected Results**:
- ✅ Different cache key used for editing (includes product_id)
- ✅ Auto-save works same as create
- ✅ Existing data loaded correctly
- ✅ Changes tracked in cache

---

### Scenario 10: Multiple Products (Different Cache Keys)

**Objective**: Verify each product has its own cache key

**Steps**:
1. Click "New Product"
2. Fill name: "Product A"
3. Wait for auto-save
4. Note LocalStorage key: `product_form_draft_new`
5. Click "Cancel"
6. Create actual product "Product B" and save
7. Click "Edit" on "Product B"
8. Modify a field
9. Wait for auto-save
10. Check LocalStorage

**Expected Results**:
- ✅ Two different keys in LocalStorage:
  - `product_form_draft_new` (for abandoned new product)
  - `product_form_draft_{product_b_id}` (for editing Product B)
- ✅ Keys don't conflict
- ✅ Correct draft restored when reopening each dialog

---

### Scenario 11: Tab Validation Indicators

**Objective**: Verify error badges appear on tabs with validation issues

**Steps**:
1. Click "New Product"
2. Observe "Basic Info" tab (no badge initially)
3. Navigate to "Tech Stack" tab without filling name
4. Navigate back to "Basic Info" tab
5. Observe tab badge

**Expected Results**:
- ✅ Error badge (red dot) appears on "Basic Info" tab
- ✅ Badge appears because "Product Name" is required and empty
- ✅ Fill name field
- ✅ Badge disappears

---

### Scenario 12: Better Testing Strategy Dropdown

**Objective**: Verify testing strategy dropdown shows helpful descriptions

**Steps**:
1. Click "New Product"
2. Navigate to "Features & Testing" tab
3. Click "Testing Strategy" dropdown
4. Observe dropdown options

**Expected Results**:
- ✅ Each option shows title AND subtitle:
  - "TDD (Test-Driven Development)" / "Write tests before implementation code"
  - "BDD (Behavior-Driven Development)" / "Tests based on user stories and behavior specs"
  - etc.
- ✅ Selecting option works correctly
- ✅ Selected value saved to form

---

### Scenario 13: Network Failure Handling

**Objective**: Verify graceful handling when save API call fails

**Prerequisites**:
- DevTools open (Network tab)

**Steps**:
1. Click "New Product"
2. Fill all fields
3. Open DevTools → Network tab
4. Right-click → "Block request pattern" → `*/products/*`
5. Click "Save" button

**Expected Results**:
- ✅ Error toast appears: "Failed to save product"
- ✅ Dialog remains open (doesn't close)
- ✅ Form data preserved (can retry save)
- ✅ Cache still in LocalStorage
- ✅ User can unblock network and retry

**Cleanup**:
- Unblock network requests
- Retry save to verify it works

---

### Scenario 14: LocalStorage Quota Exceeded

**Objective**: Verify graceful handling when LocalStorage quota exceeded

**Prerequisites**:
- Need to simulate quota exceeded (tricky to test)

**Steps**:
1. Fill LocalStorage with dummy data (approach varies by browser)
2. Open product dialog
3. Fill form fields
4. Observe console for errors

**Expected Results**:
- ✅ No crashes or unhandled exceptions
- ✅ Console warning: "LocalStorage quota exceeded"
- ✅ Form still usable (falls back to memory-only)
- ✅ User can still click "Save" to persist to backend

**Note**: This scenario is difficult to test reliably. May skip for MVP.

---

### Scenario 15: Concurrent Editing (Same Product, Two Windows)

**Objective**: Identify behavior when same product edited in multiple windows

**Steps**:
1. Create/select a product
2. Click "Edit" on product card
3. Open same page in new browser window
4. Click "Edit" on same product in second window
5. Modify field in Window 1, wait for auto-save
6. Modify different field in Window 2, wait for auto-save
7. Save in Window 1
8. Check Window 2

**Expected Results**:
- ⚠️ **Current Limitation**: No conflict detection
- ⚠️ Last save wins (Window 2 will overwrite Window 1)
- ⚠️ LocalStorage cache per-window (not shared)

**Future Enhancement**:
- Add conflict detection
- Warn user about concurrent edits
- Implement merge strategies

**For Now**: Document limitation in user guide

---

## Edge Cases

### Edge Case 1: Empty Form Save Attempt

**Steps**:
1. Click "New Product"
2. Leave all fields empty
3. Click "Save"

**Expected**:
- ❌ Validation fails (name required)
- ✅ Error message shown
- ✅ Dialog remains open

---

### Edge Case 2: Very Long Field Values

**Steps**:
1. Fill fields with extremely long text (10,000+ characters)
2. Verify auto-save works
3. Click "Save"

**Expected**:
- ✅ Auto-save handles large data
- ✅ Backend accepts long text
- ✅ Database stores correctly (JSONB can handle large data)

---

### Edge Case 3: Special Characters in Fields

**Steps**:
1. Fill fields with special characters: `<script>alert('XSS')</script>`
2. Save product
3. Reopen product

**Expected**:
- ✅ Special characters escaped/sanitized
- ✅ No XSS vulnerabilities
- ✅ Data displayed correctly (Vue escapes by default)

---

### Edge Case 4: Rapid Tab Switching

**Steps**:
1. Open dialog
2. Rapidly switch between all 5 tabs (click tabs quickly)
3. Type in fields across different tabs rapidly

**Expected**:
- ✅ No data loss
- ✅ No race conditions
- ✅ Debouncing handles rapid changes correctly

---

### Edge Case 5: Dialog Opened Multiple Times Rapidly

**Steps**:
1. Click "New Product"
2. Immediately click "Cancel"
3. Click "New Product" again
4. Repeat 5 times rapidly

**Expected**:
- ✅ No memory leaks
- ✅ Watch handlers cleaned up properly
- ✅ Cache keys don't conflict

---

## Browser Compatibility Testing

### Browsers to Test

| Browser | Version | Priority | Notes |
|---------|---------|----------|-------|
| Chrome | Latest | HIGH | Primary development browser |
| Firefox | Latest | HIGH | Strong market share |
| Edge | Latest | MEDIUM | Windows users |
| Safari | Latest | MEDIUM | macOS users |
| Mobile Chrome | Latest | LOW | Mobile responsive |

### Test Matrix

For each browser, test:
- ✅ LocalStorage read/write
- ✅ Auto-save debouncing
- ✅ Restore prompt
- ✅ beforeunload event
- ✅ Confirm dialog behavior
- ✅ Tab navigation

---

## Accessibility Testing

### Keyboard Navigation

**Test**:
1. Navigate form using only Tab/Shift+Tab
2. Fill fields using keyboard only
3. Submit using Enter key

**Expected**:
- ✅ All fields keyboard-accessible
- ✅ Tab order logical
- ✅ Save button reachable via keyboard

### Screen Reader Testing

**Test**:
1. Enable screen reader (NVDA, JAWS, or VoiceOver)
2. Navigate form
3. Listen for save status announcements

**Expected**:
- ✅ Field labels read correctly
- ✅ Save status changes announced (aria-live)
- ✅ Error messages read aloud

---

## Performance Testing

### Metrics to Measure

1. **Auto-save latency**: Time from last keystroke to LocalStorage save
   - Target: < 500ms
2. **Form load time**: Time to populate form when editing
   - Target: < 100ms
3. **Memory usage**: Check for memory leaks during repeated open/close
   - Target: Stable memory, no growth
4. **CPU usage**: During auto-save with deep watching
   - Target: < 5% CPU

### Testing Tools

- Chrome DevTools Performance tab
- Vue DevTools (check component updates)
- Memory profiler (check for leaks)

---

## Regression Testing

### Existing Features to Verify

After implementing auto-save, verify these still work:

- ✅ Product creation (all tabs)
- ✅ Product editing
- ✅ Product deletion
- ✅ Vision document upload
- ✅ Product list display
- ✅ Product search/filter
- ✅ Product sorting
- ✅ Product activation/deactivation (Handover 0049)
- ✅ Product duplication (Handover 0050)

---

## Test Data

### Sample Product 1 (Minimal)

```json
{
  "name": "Minimal Product",
  "description": "",
  "configData": {
    "tech_stack": { "languages": "", "frontend": "", "backend": "", "database": "", "infrastructure": "" },
    "architecture": { "pattern": "", "design_patterns": "", "api_style": "", "notes": "" },
    "features": { "core": "" },
    "test_config": { "strategy": "TDD", "coverage_target": 80, "frameworks": "" }
  }
}
```

### Sample Product 2 (Full)

```json
{
  "name": "GiljoAI MCP Server",
  "description": "Multi-tenant AI agent orchestration server",
  "configData": {
    "tech_stack": {
      "languages": "Python 3.11+, JavaScript ES6+, TypeScript",
      "frontend": "Vue 3, Vuetify 3, Pinia, Vue Router, Axios",
      "backend": "FastAPI, SQLAlchemy 2.0, Alembic, asyncio, Pydantic",
      "database": "PostgreSQL 18, Redis 7, pgvector",
      "infrastructure": "Docker, Docker Compose, GitHub Actions, Ruff, Pytest"
    },
    "architecture": {
      "pattern": "Layered Architecture",
      "design_patterns": "Repository, Factory, Observer, Strategy, Singleton",
      "api_style": "REST, WebSocket",
      "notes": "Multi-tenant isolation, event-driven agent coordination"
    },
    "features": {
      "core": "Agent orchestration, Multi-tenant management, Real-time WebSocket, Vision document processing, Context-aware RAG"
    },
    "test_config": {
      "strategy": "TDD",
      "coverage_target": 85,
      "frameworks": "pytest, pytest-asyncio, pytest-cov, Playwright"
    }
  }
}
```

---

## Test Execution Checklist

### Pre-Testing Setup

- [ ] Database running and initialized
- [ ] Backend server running
- [ ] Frontend dev server running
- [ ] Browser DevTools ready
- [ ] Test data prepared
- [ ] LocalStorage cleared

### Testing Execution

- [ ] All Critical Scenarios (1-15) tested
- [ ] All Edge Cases tested
- [ ] Browser compatibility tested (Chrome, Firefox, Edge)
- [ ] Accessibility tested (keyboard, screen reader)
- [ ] Performance tested (metrics recorded)
- [ ] Regression tests passed

### Post-Testing

- [ ] All bugs documented
- [ ] Fixes implemented and retested
- [ ] Test results documented
- [ ] User guide updated
- [ ] Handover marked complete

---

## Bug Report Template

When finding bugs during testing:

```markdown
## Bug: [Brief Description]

**Severity**: Critical / High / Medium / Low
**Test Scenario**: [Scenario number and name]

### Steps to Reproduce
1. Step one
2. Step two
3. Step three

### Expected Behavior
What should happen

### Actual Behavior
What actually happened

### Environment
- Browser: Chrome 120
- OS: Windows 11
- Backend: Running locally
- Database: PostgreSQL 18

### Screenshots/Logs
[Attach console errors, screenshots]

### Possible Cause
[Developer hypothesis]

### Fix Implemented
[How it was fixed, if applicable]
```

---

## Success Criteria

All tests pass with:
- ✅ 0 critical bugs
- ✅ 0 high-severity bugs
- ✅ < 5 medium-severity bugs (documented as known issues)
- ✅ < 10 low-severity bugs (can be deferred)
- ✅ All critical scenarios pass in Chrome, Firefox, Edge
- ✅ Performance metrics meet targets
- ✅ No regressions in existing features

---

**Next**: Execute test plan and document results in completion report.
