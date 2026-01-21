# Handover 0428: ProjectTabs Sticky Header + Scrollable Content

**Status**: COMPLETE
**Priority**: Medium
**Assigned Agent**: ux-designer
**Completed**: 2026-01-20

## Objective

Restructure ProjectTabs/LaunchTab to have:
1. **STICKY HEADER**: Tabs + action buttons + execution mode bar (always visible)
2. **SCROLLABLE CONTENT**: Three-panel layout scrolls independently below

## Current Structure Analysis

```
ProjectTabs.vue (794 lines, 116 lines CSS)
├── tabs-header-container (tabs + action buttons)
└── v-window (content)
    └── LaunchTab.vue (865 lines, 355 lines CSS)
        ├── execution-mode-toggle-bar (NEEDS TO MOVE UP)
        └── main-container (three-panels)
```

**Issues Identified**:
- Execution mode bar is inside LaunchTab but should be sticky with tabs
- v-tabs used instead of v-btn-toggle (inconsistent with Settings pages)
- Heavy CSS can be simplified using existing global-tabs.scss patterns

## Target Structure

```
ProjectTabs.vue
├── STICKY HEADER (flex: 0 0 auto)
│   ├── v-btn-toggle (tabs) - replaces v-tabs
│   ├── action-buttons (GitHub, Serena, Stage, Launch, Closeout)
│   └── execution-mode-toggle-bar (MOVED FROM LaunchTab)
├── SCROLLABLE CONTENT (flex: 1, overflow-y: auto)
    └── bordered-tabs-content wrapper
        └── v-window
            └── LaunchTab.vue (simplified)
                └── main-container (three-panels)
```

## Implementation Steps

### Step 1: Update ProjectTabs.vue Template Structure

**1.1 Replace v-tabs with v-btn-toggle**
- Use same pattern as UserSettings.vue
- Props: `mandatory`, `variant="outlined"`, `divided`, `rounded="t-lg"`, `color="primary"`

**1.2 Create sticky header section**
```html
<div class="sticky-header">
  <!-- v-btn-toggle -->
  <!-- action-buttons -->
  <!-- execution-mode-toggle-bar (moved from LaunchTab) -->
</div>
```

**1.3 Wrap content in scrollable container**
```html
<div class="scrollable-content bordered-tabs-content">
  <v-window>...</v-window>
</div>
```

### Step 2: Move Execution Mode Bar to ProjectTabs

**2.1 Move template code** (lines 5-25 of LaunchTab.vue)
- Copy entire execution-mode-toggle-bar div to ProjectTabs
- Place after action-buttons section

**2.2 Move related state and methods**:
- `usingClaudeCodeSubagents` ref
- `isExecutionModeLocked` computed
- `toggleExecutionMode()` function
- Watch for `props.project?.execution_mode`

**2.3 Update props/emits**:
- Remove `execution-mode-changed` emit from LaunchTab
- Handle execution mode state entirely in ProjectTabs

### Step 3: Simplify LaunchTab.vue

**3.1 Remove execution mode bar**
- Delete template lines 5-25
- Delete related script (refs, computed, functions, watch)
- Delete related CSS (~85 lines)

**3.2 Simplify wrapper**
- Remove `min-height: 100vh` (parent handles height)
- Remove outer padding (parent's bordered-tabs-content handles it)

### Step 4: Update CSS

**4.1 ProjectTabs.vue CSS updates**
```scss
.project-tabs-container {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.sticky-header {
  flex: 0 0 auto;
  position: sticky;
  top: 0;
  z-index: 10;
  background: rgb(var(--v-theme-surface));
}

.scrollable-content {
  flex: 1;
  overflow-y: auto;
  min-height: 0; /* Important for flex overflow */
}
```

**4.2 Remove redundant CSS**
- ProjectTabs: ~30 lines can be removed (absorbed by global styles)
- LaunchTab: ~85 lines can be removed (execution mode bar CSS)

## Files to Modify

| File | Changes |
|------|---------|
| `frontend/src/components/projects/ProjectTabs.vue` | Replace v-tabs with v-btn-toggle, add sticky header, move execution mode bar |
| `frontend/src/components/projects/LaunchTab.vue` | Remove execution mode bar, simplify CSS |

## CSS Reduction Estimate

| File | Before | After | Reduction |
|------|--------|-------|-----------|
| ProjectTabs.vue | 116 lines | ~80 lines | -36 lines |
| LaunchTab.vue | 355 lines | ~270 lines | -85 lines |
| **Total** | 471 lines | 350 lines | **-121 lines (26%)** |

## Verification

1. **Visual Check**:
   - Tabs match SystemSettings/UserSettings styling
   - Header stays fixed when scrolling content
   - Content scrolls independently
   - Execution mode bar visible and functional

2. **Functional Check**:
   - Tab switching works (Launch ↔ Jobs)
   - Execution mode toggle works and persists
   - Execution mode lock works (after staging)
   - Stage Project / Launch Jobs buttons work
   - Integration icons (GitHub, Serena) work

3. **Responsive Check**:
   - Mobile breakpoint still works
   - Three-panel layout adapts properly

## Risk Assessment

**Low Risk**:
- Template restructuring is straightforward
- Existing global-tabs.scss already has required styles
- No database or API changes

**Medium Risk**:
- Moving execution mode state between components
- Ensuring all watchers and emits work correctly

**Mitigation**:
- Test each step incrementally
- Keep git commits granular for easy rollback

## Completion Criteria

- [x] v-btn-toggle replaces v-tabs in ProjectTabs
- [x] Execution mode bar moved to ProjectTabs sticky header
- [x] Content scrolls independently while header stays fixed
- [x] All functionality preserved (tab switching, execution mode, buttons)
- [x] CSS organized (execution mode styles moved to ProjectTabs, LaunchTab simplified)
- [x] No regression in JobsTab behavior
- [x] Build succeeds with no errors

## Implementation Summary

### Changes Made to ProjectTabs.vue:
1. Replaced `<v-tabs>` with `<v-btn-toggle>` (matching UserSettings.vue pattern)
2. Created sticky header container with tabs, action buttons, and execution mode bar
3. Moved execution mode toggle bar from LaunchTab
4. Added scrollable content wrapper with `bordered-tabs-content` class
5. Added `useToast` import for toast notifications
6. Added execution mode state management (usingClaudeCodeSubagents, isExecutionModeLocked, toggleExecutionMode)
7. Added CSS for sticky header, scrollable content, and execution mode toggle bar (~80 lines)

### Changes Made to LaunchTab.vue:
1. Removed execution mode toggle bar template (lines 5-25)
2. Removed `useToast` import and related state
3. Removed `execution-mode-changed` emit
4. Removed execution mode state (usingClaudeCodeSubagents ref, isExecutionModeLocked computed)
5. Removed `toggleExecutionMode()` function
6. Removed watch for `props.project?.execution_mode`
7. Removed execution mode toggle bar CSS (~85 lines)
8. Removed `min-height: 100vh` from wrapper
9. Fixed bug: replaced `showToastNotification()` call with local toast state in `handleAgentEdit()`

### Line Count Changes:
| File | Before | After | Change |
|------|--------|-------|--------|
| ProjectTabs.vue | 794 lines | 976 lines | +182 lines (execution mode moved in) |
| LaunchTab.vue | 865 lines | 677 lines | -188 lines (execution mode removed) |

### Build Verification:
- Frontend build completed successfully in 2.78s
- No TypeScript/Vue compilation errors

## Round 2 Fixes (User Feedback)

### Issue: Sticky header wasn't actually sticky
**Root Cause**: `position: sticky` doesn't work inside an `overflow-y: auto` container. The sticky element must be a direct child of the scrolling container.

### Solution: Flexbox Layout

**ProjectLaunchView.vue Changes**:
1. Simplified template - removed duplicate loading/error states
2. Removed old sticky-header div (project name now in ProjectTabs)
3. Made `project-content` a simple flex container that lets ProjectTabs control layout
4. Removed all old CSS (sticky-header, scrollable-content, project-name styles)

**ProjectTabs.vue Changes**:
1. Changed root from `<v-card>` to `<div>` (removed v-card styling)
2. Added project name/ID to sticky header (moved from ProjectLaunchView)
3. Fixed CSS for proper sticky + scrollable flex layout:
   - Container: `height: 100%`, `overflow: hidden`, `display: flex`, `flex-direction: column`
   - Sticky header: `flex: 0 0 auto` (don't grow, don't shrink)
   - Scrollable content: `flex: 1`, `overflow-y: auto`, `min-height: 0`
4. Removed border-bottom line from sticky-header
5. Removed bordered-tabs-content styling

### Key CSS Pattern for Sticky Header + Scrollable Content:
```scss
.container {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden; /* Critical: prevents body scroll */
}

.sticky-header {
  flex: 0 0 auto; /* Fixed size, doesn't scroll */
}

.scrollable-content {
  flex: 1; /* Takes remaining space */
  overflow-y: auto; /* Scrolls independently */
  min-height: 0; /* Critical for flex overflow */
}
```

## Round 3 Fixes (User Clarification - No Page Scroll)

### User Requirement
- Page doesn't scroll at all
- Only individual data panels (Project Description, Orchestrator Mission, Agent Team) have their own scrollbars
- Tabs connect to bordered content box (like Settings pages)
- Action buttons and Execution Mode toggle moved INSIDE the bordered box

### Final Structure
```
ProjectTabs.vue (no page scroll):
├── .project-header (Project: name + ID)
├── .tabs-toggle (v-btn-toggle connected to box below)
└── .bordered-tabs-content (main box)
    ├── .action-buttons-row (GitHub, Serena, Stage, Launch)
    ├── .execution-mode-toggle-bar
    └── .tabs-content (v-window)
        └── LaunchTab.vue
            └── .three-panels (each panel scrolls independently)
```

### Changes Made

**ProjectTabs.vue**:
1. Simplified template - tabs outside bordered box, connect visually
2. Action buttons row moved inside bordered box
3. Execution mode toggle moved inside bordered box
4. Removed all sticky/scrollable wrappers - page doesn't scroll
5. CSS: `.tabs-toggle` with `margin-bottom: -1px` to connect to box
6. CSS: `.bordered-tabs-content` with `border-radius: 0 8px 8px 8px` (no top-left where tabs connect)

**LaunchTab.vue**:
1. Removed wrapper padding/border (already inside bordered box)
2. Made `.three-panels` use flex to fill available space
3. Each `.panel` is a flex column with `min-height: 0` for overflow
4. Each `.panel-content` has `overflow-y: auto` for independent scrolling

### Build Verification
- Frontend build completed successfully in 3.75s
