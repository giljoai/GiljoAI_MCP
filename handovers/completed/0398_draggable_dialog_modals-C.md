# Handover: Draggable Dialog Modals

**Date:** 2026-02-12
**From Agent:** Claude Opus 4.6 (assessment session)
**To Agent:** ux-designer / tdd-implementor
**Priority:** Medium
**Estimated Complexity:** 4-6 hours
**Status:** Not Started

---

## Task Summary

Make all popup/modal dialogs draggable by their title bar across the entire GiljoAI dashboard. Currently all 41 `v-dialog` instances across 28 Vue files are static/centered. Users should be able to click-and-drag the title bar to reposition any modal.

**Why:** Dialogs frequently obscure content users need to reference while the dialog is open. Draggable modals improve workflow efficiency without changing any existing functionality.

**Expected Outcome:** Every dialog in the application can be repositioned by dragging its title bar. Position resets on close. Visual cursor affordance on hover.

---

## Context and Background

### Current State
- **Framework:** Vue 3 + Vuetify 3
- **Dialog component:** Vuetify `v-dialog` (renders content inside a fixed overlay)
- **Centralized wrapper:** `BaseDialog.vue` exists at `frontend/src/components/common/BaseDialog.vue` but only 3 files use it
- **Pattern:** All dialogs follow `<v-dialog>` > `<v-card>` > `<v-card-title>` structure - title bar is the natural drag handle

### Inventory (41 dialog instances across 28 files)

**Heavy files (multiple dialogs):**
- `TemplateManager.vue` - 6 dialogs (edit, preview, delete, history, reset, diff)
- `UserManager.vue` - 4 dialogs (user, password, reset password, status)
- `ProjectsView.vue` - 3 dialogs (create, deleted, mission)
- `StartupQuickStart.vue` - 3 dialogs (details, shortcuts, help)
- `TemplateArchive.vue` - 2 dialogs (diff, restore)

**Single dialog files (21 files):**
- `TasksView.vue`, `OrganizationSettings.vue`, `ProjectLaunchView.vue`
- `AiToolConfigWizard.vue`, `UserProfileDialog.vue`, `ForgotPasswordPin.vue`
- `ConnectionStatus.vue`, `GitAdvancedSettingsDialog.vue`, `InviteMemberDialog.vue`
- `OrchestratorCard.vue`, `ManualCloseoutModal.vue`, `CloseoutModal.vue`
- `AgentJobModal.vue`, `AgentMissionEditModal.vue`, `AgentDetailsModal.vue`
- `StatusBadge.vue`, `ActionIcons.vue`, `ProductIntroTour.vue`
- `MessageAuditModal.vue`, `CodexConfigModal.vue`, `GeminiConfigModal.vue`
- `ClaudeConfigModal.vue`, `BaseDialog.vue`

---

## Technical Details

### Architecture Decision: Custom Vue Directive (`v-draggable`)

A custom directive is the least invasive approach - each dialog only needs a single attribute added to its `<v-card>` element.

**Why directive over composable:**
- No script changes needed per component (template-only change)
- Works identically on BaseDialog and raw v-dialog usage
- Single registration point (global directive in main.js)

### Implementation Approach

The directive attaches to the `<v-card>` inside each `<v-dialog>`. On mount, it finds the `<v-card-title>` child element and attaches mousedown/mousemove/mouseup listeners. Position is applied via CSS `transform: translate(x, y)` on the v-card.

**Key behaviors:**
1. **Drag handle:** `v-card-title` element only (not the entire card)
2. **Cursor:** `cursor: move` on title bar hover, `cursor: grabbing` during drag
3. **Bounds:** Prevent dragging entirely off-screen (keep at least 50px visible)
4. **Reset on close:** Position returns to center when dialog closes and reopens
5. **Touch support:** Include `touchstart`/`touchmove`/`touchend` for mobile
6. **Z-index:** No changes needed - Vuetify's overlay system handles stacking

### Key Files to Create/Modify

**New file (1):**
- `frontend/src/directives/draggable.js` - The custom directive (~60-80 lines)

**Modified files (29):**
- `frontend/src/main.js` - Register directive globally: `app.directive('draggable', draggable)`
- 28 Vue files listed above - Add `v-draggable` attribute to each `<v-card>` inside `<v-dialog>`

**No backend changes required.**

---

## Implementation Plan

### Phase 1: Directive Implementation (TDD)

**Test first:** `frontend/tests/unit/directives/draggable.spec.js`
- Test: directive mounts and finds title bar element
- Test: mousedown on title starts tracking
- Test: mousemove updates transform translate
- Test: mouseup stops tracking
- Test: position resets when element is unmounted/remounted
- Test: drag does not activate when clicking card body (only title)
- Test: bounds checking prevents off-screen drag

**Then implement:** `frontend/src/directives/draggable.js`
```javascript
// Pseudocode structure
export const draggable = {
  mounted(el) {
    const handle = el.querySelector('.v-card-title')
    if (!handle) return

    let isDragging = false
    let startX, startY, offsetX = 0, offsetY = 0

    handle.style.cursor = 'move'
    handle.style.userSelect = 'none'

    handle.addEventListener('mousedown', onMouseDown)
    // ... mousemove on document, mouseup on document
    // Apply: el.style.transform = `translate(${offsetX}px, ${offsetY}px)`
  },
  unmounted(el) {
    // Cleanup listeners
  }
}
```

**Register globally in `main.js`:**
```javascript
import { draggable } from './directives/draggable'
app.directive('draggable', draggable)
```

**Recommended Agent:** `tdd-implementor`

### Phase 2: Rollout to All Dialogs (Mechanical)

Add `v-draggable` to each dialog's `<v-card>`:

**Before:**
```html
<v-dialog v-model="showDialog" max-width="600">
  <v-card>
```

**After:**
```html
<v-dialog v-model="showDialog" max-width="600">
  <v-card v-draggable>
```

This is a mechanical change across 28 files. Each change is a single attribute addition - no logic changes needed.

**Special cases to handle:**
- `BaseDialog.vue` - Add `v-draggable` to the inner `<v-card class="base-dialog-card">` (line 9). This covers the 3 files using BaseDialog automatically.
- `ManualCloseoutModal.vue` and `CloseoutModal.vue` - These use `:fullscreen="isMobile"`. The directive should detect fullscreen and disable dragging (no point dragging a fullscreen dialog).
- `TemplateManager.vue` line 619 - `historyDialog` wraps `<TemplateArchive>` not `<v-card>`. May need to add v-draggable inside `TemplateArchive.vue` instead.

**Recommended Agent:** `ux-designer`

### Phase 3: Visual Polish and Edge Cases

- Add subtle visual feedback: slight box-shadow increase while dragging
- Verify scrollable dialogs (`ConnectionStatus.vue`, `TemplateManager.vue` history/diff) work correctly
- Verify persistent dialogs still block outside clicks correctly
- Test with `:fullscreen="isMobile"` dialogs - directive should no-op in fullscreen mode
- Test keyboard accessibility is not affected (Tab, Escape still work)

**Recommended Agent:** `frontend-tester`

---

## Testing Requirements

### Unit Tests
- `frontend/tests/unit/directives/draggable.spec.js`
- Directive mount/unmount lifecycle
- Mouse event tracking (down, move, up)
- Touch event tracking (start, move, end)
- Bounds checking
- Position reset on remount
- Fullscreen detection (disable drag)

### Integration Tests
- Pick 3 representative dialogs to verify:
  1. Simple dialog (`ActionIcons.vue` confirm dialog)
  2. BaseDialog-based dialog (`TasksView.vue`)
  3. Scrollable dialog (`ConnectionStatus.vue` debug panel)
- Verify drag works, position resets on close, and dialog functionality is unchanged

### Manual Testing
1. Open any dialog -> hover title bar -> cursor shows `move`
2. Click and drag title bar -> dialog follows mouse
3. Release -> dialog stays in new position
4. Close and reopen -> dialog returns to center
5. Try dragging off-screen -> dialog stops at viewport edge
6. Open scrollable dialog -> scroll still works, drag only on title bar
7. Mobile/touch: touch-drag title bar works

---

## Dependencies and Blockers

**Dependencies:** None - pure frontend work, no backend or database changes.

**NPM packages:** None needed - pure vanilla JS mouse/touch events.

**Blockers:** None identified.

---

## Success Criteria

- [ ] Custom `v-draggable` directive created with full test coverage
- [ ] Directive registered globally in `main.js`
- [ ] All 41 dialog instances across 28 files have `v-draggable` applied
- [ ] Title bar shows `cursor: move` on hover
- [ ] Dialogs can be repositioned by dragging title bar
- [ ] Position resets when dialog closes and reopens
- [ ] Dialogs cannot be dragged entirely off-screen
- [ ] Fullscreen dialogs are not affected
- [ ] Scrollable dialog content still scrolls correctly
- [ ] No regressions in dialog open/close/persistent behavior
- [ ] Touch support works on mobile viewports
- [ ] All existing tests still pass

---

## Rollback Plan

**Low risk - easy rollback:**
1. Remove `v-draggable` attribute from all 28 files (revert template changes)
2. Remove directive registration from `main.js`
3. Delete `frontend/src/directives/draggable.js` and its test file
4. No database, API, or state changes to revert

---

## Additional Resources

- [Vuetify v-dialog docs](https://vuetifyjs.com/en/components/dialogs/)
- [Vue Custom Directives](https://vuejs.org/guide/reusability/custom-directives.html)
- `frontend/src/components/common/BaseDialog.vue` - Centralized dialog wrapper (reference implementation)
- `frontend/src/main.js` - Global directive registration point
