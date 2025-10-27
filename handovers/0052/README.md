---
Handover 0052: Field Priority Unassigned Category
Date: 2025-10-27
Status: Ready for Implementation
Priority: MEDIUM
Complexity: LOW
Duration: 4-6 hours
---

# Executive Summary

The GiljoAI MCP Server's Field Priority Configuration system (Handover 0048) currently allows users to remove fields from priority categories using an "x" button, but provides no way to recover them. Once removed, fields disappear entirely from the interface, creating a frustrating dead-end UX pattern.

This handover implements a fourth draggable category called **"Unassigned"** that serves as a holding area for fields removed from P1/P2/P3. This provides users with a complete view of all available fields and enables recovery of accidentally removed fields through simple drag-and-drop.

**Key Benefits**:
- Zero data loss - removed fields are always visible and recoverable
- Complete field inventory - users can see all 13 available fields
- Consistent UX - follows standard drag-and-drop patterns
- Frontend-only implementation - zero backend changes required
- Backward compatible - existing configurations work unchanged

**Technical Scope**: Frontend-only changes to `frontend/src/views/UserSettings.vue` and new composable `frontend/src/composables/useFieldPriority.js` (~150 lines of code).

---

# Business Justification

## Problem Statement

### Current Behavior

Users managing field priorities in **User Settings → General → Field Priority Configuration** encounter a critical UX flaw:

1. **User removes field from Priority 2** (clicks "x" button on "Database" field)
2. **Field disappears completely** from the interface
3. **No recovery path** - field is gone from UI
4. **User confused** - "Where did it go? How do I get it back?"
5. **User must reload page** to reset configuration (loses other changes)

### User Impact

- **Data Loss**: Users lose track of removed fields
- **Confusion**: No clear mental model for "where did it go?"
- **Frustration**: Cannot recover from accidental removal
- **Time Waste**: Must reload page and reconfigure everything
- **Reduced Confidence**: Users afraid to experiment with field priorities

### Root Cause

The current implementation computes removed fields but doesn't display them:

```javascript
// frontend/src/views/UserSettings.vue (current)
const assignedFields = computed(() => {
  return [
    ...priority1Fields.value,
    ...priority2Fields.value,
    ...priority3Fields.value
  ]
})

// Removed fields computed but NEVER SHOWN
const removedFields = computed(() => {
  return ALL_FIELDS.filter(f => !assignedFields.value.includes(f))
})
```

## Solution Overview

Add a fourth draggable category called **"Unassigned"** that:

1. **Shows removed fields** - displays all fields not in P1/P2/P3
2. **Enables recovery** - drag from Unassigned back to priority category
3. **Provides transparency** - user sees all 13 fields at all times
4. **Maintains consistency** - uses same drag-and-drop UX as other categories

### Visual Comparison

**Before (Current)**:
```
┌─────────────────────────────────────────┐
│ Priority 1 (Always Included)            │
│ ┌─────────────────────────────────────┐ │
│ │ Tech Stack > Languages               │ │
│ │ Tech Stack > Backend          [x]    │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ Priority 2 (High Priority)              │
│ ┌─────────────────────────────────────┐ │
│ │ Database                      [x]    │ │  ← User clicks [x]
│ └─────────────────────────────────────┘ │
│                                         │
│ Priority 3 (Medium Priority)            │
│ ┌─────────────────────────────────────┐ │
│ │ (empty)                             │ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘

Result: "Database" field disappears entirely ❌
```

**After (With Unassigned)**:
```
┌─────────────────────────────────────────┐
│ Priority 1 (Always Included)            │
│ ┌─────────────────────────────────────┐ │
│ │ Tech Stack > Languages               │ │
│ │ Tech Stack > Backend          [x]    │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ Priority 2 (High Priority)              │
│ ┌─────────────────────────────────────┐ │
│ │ (empty)                             │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ Priority 3 (Medium Priority)            │
│ ┌─────────────────────────────────────┐ │
│ │ (empty)                             │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ Unassigned (Not Included in Missions)   │  ← NEW CATEGORY
│ ┌─────────────────────────────────────┐ │
│ │ Database                      [x]    │ │  ← Field moved here
│ │ Features > Core Features      [x]    │ │
│ │ Test Config > Strategy        [x]    │ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘

Result: "Database" field visible and recoverable ✅
```

## Why This Matters

### 1. Aligns with Mission-Based Architecture

The field priority system is central to the 70% token reduction achieved through focused context delivery (Handover 0020). Users need confidence to experiment with field priorities without fear of losing fields.

**Impact**: Improved user confidence → Better field priority configurations → More efficient agent missions

### 2. Completes the Field Priority UX

This is the final piece of the Field Priority Configuration system started in Handover 0048 and enhanced in Handover 0049. Without field recovery, the system feels incomplete.

**Impact**: Professional, polished UX that meets user expectations

### 3. Low Implementation Cost, High Value

- **4-6 hours of development time**
- **Zero backend changes** (frontend-only)
- **Zero breaking changes** (fully backward compatible)
- **Significant UX improvement** (eliminates major pain point)

**Impact**: High ROI feature with minimal risk

---

# Solution Design

## Architectural Overview

### Data Flow

```
ALL_FIELDS (13 total, constant)
    ↓
User assigns to priority categories
    ↓
┌──────────────────────────────────────────┐
│ Priority 1: [languages, backend]         │
│ Priority 2: [frontend, database]         │
│ Priority 3: [architecture.pattern]       │
│ Unassigned: [ALL_FIELDS - (P1+P2+P3)]   │ ← COMPUTED
└──────────────────────────────────────────┘
    ↓
Save to backend: { fields: { "tech_stack.languages": 1, ... } }
    ↓
Unassigned fields have NO entry in saved config (implicit)
```

### Key Design Decisions

#### 1. Frontend-Only Implementation

**Decision**: No backend changes required.

**Rationale**:
- Backend only stores assigned fields: `{ "tech_stack.languages": 1, "tech_stack.backend": 1 }`
- Unassigned fields have NO database entry (not `0` or `null`, just absent)
- Frontend computes unassigned = `ALL_FIELDS - assigned_fields`
- This is consistent with current backend API contract (Handover 0048)

**Benefits**:
- Zero API changes
- Zero database migration
- Zero breaking changes
- Faster implementation (4-6 hours vs 1-2 days)

#### 2. Computed Unassigned Category

**Decision**: Unassigned category is dynamically computed, not stored.

**Rationale**:
- Single source of truth: The list of all possible fields (ALL_FIELDS)
- Unassigned = Set difference operation
- Always accurate (can't get out of sync)
- No additional state management needed

**Implementation**:
```javascript
const unassignedFields = computed(() => {
  const assigned = new Set([
    ...priority1Fields.value,
    ...priority2Fields.value,
    ...priority3Fields.value
  ])
  return ALL_FIELDS.filter(field => !assigned.has(field))
})
```

#### 3. Token Calculation

**Decision**: Unassigned fields contribute 0 tokens to mission context.

**Rationale**:
- Unassigned fields are NOT included in agent missions
- Token budget calculation only counts P1 + P2 + P3 fields
- Consistent with existing token visualization (Handover 0049)

**Formula**:
```
Total Tokens = (P1 tokens) + (P2 tokens) + (P3 tokens) + 500 (overhead)
Unassigned Tokens = 0 (not included)
```

#### 4. Drag-and-Drop UX

**Decision**: Unassigned category supports full drag-and-drop like P1/P2/P3.

**Capabilities**:
- **Drag FROM Unassigned TO P1/P2/P3**: Assigns priority to field
- **Drag FROM P1/P2/P3 TO Unassigned**: Removes priority from field
- **Remove button ([x])**: Moves field to Unassigned (same as dragging)
- **No dragging WITHIN Unassigned**: Order doesn't matter for unassigned fields

**Implementation**: Uses existing `vuedraggable` library (already in project).

## Component Structure

### Modified Components

**File**: `frontend/src/views/UserSettings.vue`

Changes:
1. Add `unassignedFields` computed property
2. Add fourth draggable container in template
3. Update remove button handler to move to Unassigned (instead of delete)
4. Add visual styling for Unassigned category (lighter background, no token count)

**New File**: `frontend/src/composables/useFieldPriority.js`

Purpose: Extract field priority logic into reusable composable.

Exports:
- `priority1Fields` - Reactive array of P1 fields
- `priority2Fields` - Reactive array of P2 fields
- `priority3Fields` - Reactive array of P3 fields
- `unassignedFields` - Computed array of unassigned fields
- `moveToCategory(field, category)` - Move field to priority category
- `removeFromPriority(field)` - Move field to Unassigned
- `ALL_FIELDS` - Constant list of all 13 fields

### Visual Design

**Unassigned Category Styling**:
- **Background**: Lighter gray (`grey-lighten-4` vs `grey-lighten-2` for priority categories)
- **Border**: Dashed border (vs solid for priority categories)
- **Label**: "Unassigned (Not Included in Missions)" with info icon
- **Tooltip**: "Fields in this category are NOT sent to AI agents. Drag to a priority category to include them in missions."
- **Token Badge**: Hidden (no token contribution)

---

# Implementation Plan

## Timeline: 4-6 Hours

### Phase 1: Extract Field Priority Logic (1.5 hours)

**Objective**: Create reusable composable for field priority management.

**File**: `frontend/src/composables/useFieldPriority.js` (NEW)

**Tasks**:
1. Define `ALL_FIELDS` constant (13 fields)
2. Create reactive refs for P1/P2/P3 fields
3. Create computed `unassignedFields`
4. Implement `moveToCategory()` method
5. Implement `removeFromPriority()` method
6. Add JSDoc comments

**Estimated Lines of Code**: ~120 lines

### Phase 2: Update UserSettings View (2 hours)

**Objective**: Integrate Unassigned category into field priority UI.

**File**: `frontend/src/views/UserSettings.vue`

**Tasks**:
1. Import and use `useFieldPriority` composable
2. Add fourth draggable container for Unassigned category
3. Update remove button handlers
4. Add visual styling for Unassigned category
5. Update token calculation display (exclude unassigned)
6. Add tooltips and help text

**Estimated Lines of Code**: ~50 lines added/modified

### Phase 3: Testing (1 hour)

**Objective**: Comprehensive testing of all drag-and-drop scenarios.

**Test Scenarios**:
1. **Initial Load**: Unassigned shows fields not in P1/P2/P3
2. **Drag to Unassigned**: Field moves from P1 to Unassigned
3. **Drag from Unassigned**: Field moves to P2
4. **Remove Button**: Clicking [x] on P1 field moves to Unassigned
5. **Token Calculation**: Token count excludes unassigned fields
6. **Save/Load**: Configuration persists correctly (no unassigned in DB)
7. **Edge Case**: All fields in Unassigned (P1/P2/P3 empty)
8. **Edge Case**: No fields in Unassigned (all assigned)

### Phase 4: Documentation & Polish (0.5-1 hour)

**Objective**: Update documentation and add help text.

**Tasks**:
1. Update user-facing help text in UI
2. Add tooltips for Unassigned category
3. Update this handover with implementation notes
4. Create implementation summary

---

# Files to Modify

## New Files (1)

### 1. `frontend/src/composables/useFieldPriority.js` (~120 lines)

Purpose: Reusable composable for field priority management.

Key exports:
- `ALL_FIELDS` constant
- `priority1Fields`, `priority2Fields`, `priority3Fields` refs
- `unassignedFields` computed
- `moveToCategory()`, `removeFromPriority()` methods

## Modified Files (1)

### 2. `frontend/src/views/UserSettings.vue` (+50 lines)

Changes:
- Import `useFieldPriority` composable
- Replace inline field management with composable
- Add fourth draggable container template
- Update remove button handlers
- Add Unassigned category styling

**Total Lines of Code**: ~170 lines (120 new + 50 modified)

---

# API Impact

**ZERO API CHANGES REQUIRED**

This is a purely frontend UX enhancement. The existing field priority API (from Handover 0048) already supports the necessary operations:

## Existing Endpoints (Used, Not Modified)

### GET /api/v1/users/me/settings

**Response**:
```json
{
  "field_priority_config": {
    "version": "1.0",
    "token_budget": 2000,
    "fields": {
      "tech_stack.languages": 1,
      "tech_stack.backend": 1,
      "tech_stack.frontend": 2
    }
  }
}
```

**Unassigned Fields**: Implicitly any field NOT in the `fields` object.

### PATCH /api/v1/users/me/settings

**Request**:
```json
{
  "field_priority_config": {
    "fields": {
      "tech_stack.languages": 1,
      "tech_stack.backend": 1
    }
  }
}
```

**Unassigned Fields**: Automatically computed by frontend as `ALL_FIELDS - assigned`.

---

# Testing Strategy

## Unit Tests

**NOT REQUIRED** for this handover (frontend-only, no complex logic).

Optional: Test `useFieldPriority.js` composable if time permits.

## Manual Testing Scenarios

### Scenario 1: Initial Load with Default Config

**Steps**:
1. Open User Settings → General
2. Scroll to Field Priority Configuration

**Expected**:
- P1 shows 2 default fields
- P2 shows 3 default fields
- P3 shows 2 default fields
- Unassigned shows 6 remaining fields

### Scenario 2: Drag Field to Unassigned

**Steps**:
1. Drag "Database" from P2 to Unassigned
2. Verify token count decreases
3. Save changes
4. Reload page

**Expected**:
- "Database" appears in Unassigned category
- Token count reflects removal
- After reload, "Database" still in Unassigned
- Backend has NO entry for `tech_stack.database`

### Scenario 3: Drag Field from Unassigned to Priority

**Steps**:
1. Drag "Features > Core" from Unassigned to P1
2. Verify token count increases
3. Save changes

**Expected**:
- "Features > Core" appears in P1
- Token count reflects addition
- Backend has `"features.core": 1`

### Scenario 4: Remove Button Moves to Unassigned

**Steps**:
1. Click [x] button on "Tech Stack > Frontend" in P2
2. Verify field appears in Unassigned

**Expected**:
- Field immediately moves to Unassigned
- Token count updates
- No error messages

### Scenario 5: All Fields in Unassigned

**Steps**:
1. Remove all fields from P1/P2/P3
2. Verify all 13 fields in Unassigned

**Expected**:
- P1/P2/P3 show "Drag fields here" placeholder
- Unassigned shows all 13 fields
- Token count = 500 (structure only)

### Scenario 6: No Fields in Unassigned

**Steps**:
1. Assign all 13 fields to P1/P2/P3
2. Verify Unassigned is empty

**Expected**:
- Unassigned shows "All fields assigned" placeholder
- Token count reflects all fields

### Scenario 7: Token Calculation Accuracy

**Steps**:
1. Start with default config
2. Move field from P2 to Unassigned
3. Verify token count decreases by field's token contribution
4. Move field from Unassigned to P3
5. Verify token count increases by field's token contribution

**Expected**:
- Token counts match expected values
- Real-time updates as fields move

### Scenario 8: Backward Compatibility

**Steps**:
1. Load existing user with saved field priority config (pre-Handover 0052)
2. Verify fields appear correctly

**Expected**:
- Assigned fields appear in correct priority categories
- Unassigned fields computed correctly
- No errors or missing fields

## Cross-Browser Testing

**Required Browsers**:
- Chrome (latest) - PRIMARY
- Firefox (latest) - HIGH
- Edge (latest) - MEDIUM

**Drag-and-Drop Focus**: Ensure vuedraggable works correctly in all browsers.

## Accessibility Testing

**Requirements**:
- Keyboard navigation (Tab/Shift+Tab through categories)
- Screen reader support (ARIA labels for drag-and-drop)
- Focus indicators visible when navigating with keyboard

---

# Success Criteria

## Functional Requirements

- [ ] Unassigned category displays all fields not in P1/P2/P3
- [ ] Dragging field to Unassigned removes it from priority category
- [ ] Dragging field from Unassigned assigns it to target priority category
- [ ] Remove button ([x]) moves field to Unassigned
- [ ] Token calculation excludes unassigned fields
- [ ] Save/load operations work correctly (unassigned fields not saved to backend)
- [ ] All 13 fields visible at all times (no disappearing fields)

## User Experience Requirements

- [ ] Unassigned category visually distinct (dashed border, lighter background)
- [ ] Tooltip explains "Not Included in Missions" for Unassigned
- [ ] Drag-and-drop smooth and responsive
- [ ] Token count updates in real-time during drag operations
- [ ] No flash of unstyled content on page load

## Technical Requirements

- [ ] Zero API changes (backend unchanged)
- [ ] Zero breaking changes (existing configs work)
- [ ] No console errors during any operation
- [ ] Performance: Drag operations complete in <100ms
- [ ] Accessibility: Keyboard navigation functional

---

# Related Handovers

- **Handover 0048**: Product Field Priority Configuration (COMPLETE)
  - Established field priority system and backend API
  - This handover completes the UX by adding field recovery

- **Handover 0049**: Active Product Token Visualization (COMPLETE)
  - Real-time token calculation tied to active product
  - This handover ensures token counts reflect unassigned fields correctly

- **Handover 0051**: Product Form Auto-Save & UX Polish (IN PROGRESS)
  - Related UX improvement work
  - May share some UX patterns for field management

---

# Risk Assessment

**Priority**: MEDIUM (UX improvement, not critical)
**Complexity**: LOW (simple computed property + template change)
**Risk**: LOW (frontend-only, no breaking changes)

## Risk Mitigation

### Risk 1: Drag-and-Drop Library Issues

**Mitigation**: vuedraggable already used successfully in project (field reordering). Reuse existing patterns.

### Risk 2: Token Calculation Confusion

**Mitigation**: Clear visual indicators that unassigned fields = 0 tokens. Add help text and tooltips.

### Risk 3: User Confusion About Unassigned

**Mitigation**:
- Clear label: "Unassigned (Not Included in Missions)"
- Tooltip: "Fields in this category are NOT sent to AI agents"
- Visual differentiation (dashed border, lighter background)

### Risk 4: Performance with 13 Fields

**Mitigation**: 13 fields is trivial for Vue reactivity. No performance concerns.

---

# Implementation Notes

## Rollback Plan

**If Issues Arise**:
1. `git revert <commit-hash>` (single commit)
2. Delete `frontend/src/composables/useFieldPriority.js`
3. Restore original `UserSettings.vue`

**Risk**: VERY LOW - Frontend-only change, no data migration, fully reversible.

## Future Enhancements

### 1. Bulk Assignment

Allow selecting multiple fields in Unassigned and assigning them all at once to a priority category.

**Estimated Effort**: 2-3 hours

### 2. Search/Filter Fields

Add search box to filter fields by name (useful if field count grows beyond 13).

**Estimated Effort**: 1-2 hours

### 3. Field Descriptions

Show brief description of each field on hover (e.g., "Tech Stack > Languages: Programming languages used in this product").

**Estimated Effort**: 2-3 hours

### 4. Import/Export Priority Configs

Allow users to export field priority config as JSON and import into other products.

**Estimated Effort**: 3-4 hours

---

# Sign-Off Checklist

Before marking this handover complete:

- [ ] `useFieldPriority.js` composable created and tested
- [ ] `UserSettings.vue` updated with Unassigned category
- [ ] All 8 manual test scenarios pass
- [ ] Token calculation accuracy verified
- [ ] Cross-browser testing complete (Chrome, Firefox, Edge)
- [ ] Accessibility testing complete (keyboard navigation)
- [ ] No console errors during any operation
- [ ] Code committed with descriptive message
- [ ] This handover updated with completion notes
- [ ] User-facing documentation updated (if needed)

---

**Handover Status**: Ready for Implementation
**Estimated Duration**: 4-6 hours
**Next Steps**: Begin Phase 1 (Extract Field Priority Logic)

**Created By**: Documentation Manager Agent
**Date**: 2025-10-27
**Review Date**: 2026-04-27 (6 months)

---

**End of Handover 0052 - README.md**
