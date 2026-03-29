# Handover 0842i: Product Setup Wizard — Vision-First Flow Redesign

**Date:** 2026-03-27
**Edition Scope:** CE
**From Agent:** Planning Session
**To Agent:** ux-designer
**Priority:** High
**Estimated Complexity:** 1.5 hours
**Status:** Not Started
**Standalone handover** (continuation of 0842 series, addresses tab flow issue)
**Depends on:** 0842d (analysis banner exists), 0842c (MCP tools exist)

---

## Task Summary

Restructure the product creation/edit wizard tabs so the vision document upload comes first (Tab 1), with a manual/AI mode choice that either lets the user fill fields by hand or locks the tabs while an AI agent populates them. Same tabs, same layout — just reordered and with a lock/unlock UX during analysis.

---

## Problem

The current tab order is backwards:

```
Tab 1: Product Info    → User types name, description, core features
Tab 2: Vision Docs     → User uploads the document that CONTAINS that info
Tab 3: Tech Stack      → User types what the doc already says
Tab 4: Architecture    → Same
Tab 5: Testing         → Same
```

The vision document is the *source* for most product fields, but it's on Tab 2 — after the user has already been asked to fill in fields manually. With the AI analysis feature (0842c), this is even more jarring: the user fills fields, then uploads a doc, then an agent re-fills the same fields.

---

## Proposed Flow

### Tab 1: Product Setup (renamed from "Product Info")

```
┌─────────────────────────────────────────────────┐
│  Product Name: [___________________________]     │
│  Codebase folder: [________________________]     │ (optional)
│                                                  │
│  ── Vision Document ──────────────────────────   │
│  Link your vision document or product proposal   │
│  [Choose file] (.md, .txt)                       │
│                                                  │
│  [uploaded: product_vision.md · 18,450 tokens]   │
│  Sumy summaries: ✅ 33% · ✅ 66%                │
│                                                  │
│  ── How would you like to set up this product? ─ │
│                                                  │
│  ○ I'll fill in the details manually             │
│  ○ I want my AI coding agent to analyze & fill   │
│                                                  │
│  [AI selected → STAGE ANALYSIS button appears]   │
│  [copies prompt to clipboard]                    │
│                                                  │
│  Custom extraction instructions (optional):      │
│  [textarea, only visible when AI selected]       │
└─────────────────────────────────────────────────┘
```

### Tabs 2-5: Same as today (Product Info, Tech Stack, Architecture, Testing)

- **When "Manual" selected**: Tabs are unlocked. User navigates and fills fields by hand. Normal flow.
- **When "AI Analysis" selected + prompt staged**: Tabs show a subtle locked state:
  - Tab buttons are `disabled` (greyed out, not clickable)
  - A small status indicator: "Waiting for AI analysis..." with a subtle pulse/spinner
  - When `vision:analysis_complete` WebSocket fires:
    - Tabs unlock
    - Fields populate from refreshed product data
    - Brief success toast: "AI populated N fields — review your configuration"
  - User then navigates tabs normally to review/edit

### Tab Rename

| Current | New |
|---------|-----|
| Product Info | Product Setup |
| Vision Docs | *(merged into Tab 1)* |
| Tech Stack | Tech Stack (unchanged) |
| Architecture | Architecture (unchanged) |
| Testing | Testing (unchanged) |

---

## Technical Details

### File to Modify

`frontend/src/components/products/ProductForm.vue` — this is the only file. All changes are within this component.

### Current Tab Structure (lines 65-93, 817)

```javascript
// Tab buttons: v-btn-toggle with dialogTab model
// Tab order: ['basic', 'vision', 'tech', 'arch', 'features']
// Tab content: v-window with v-window-item per tab
```

### Changes Required

**1. Merge "Vision Docs" content into "Product Info" tab**

Move the vision document upload section (currently `v-window-item value="vision"`, lines 159-346) into the `v-window-item value="basic"` tab. Place it after the Product Name and Codebase folder fields, before the Description field.

**2. Remove the Vision Docs tab button**

Remove the "Vision Docs" `v-btn` from the tab toggle (line 78-81). Update `tabOrder` array:

```javascript
// Before: ['basic', 'vision', 'tech', 'arch', 'features']
// After:  ['setup', 'info', 'tech', 'arch', 'features']
```

**3. Split remaining Product Info fields to Tab 2**

Tab 1 ("Product Setup") gets: Product Name, Codebase folder, Vision doc upload, Manual/AI choice.
Tab 2 ("Product Info") gets: Description, Core Features. These are the fields the user types manually OR the agent fills.

**4. Add mode selection radio**

```html
<v-radio-group v-model="setupMode" class="mt-4" hide-details>
  <v-radio label="I'll fill in the details manually" value="manual" />
  <v-radio label="I want my AI coding agent to analyze & fill" value="ai"
           :disabled="existingVisionDocuments.length === 0" />
</v-radio-group>
```

AI option disabled until a vision document is uploaded.

**5. Move analysis banner into Tab 1**

The existing `v-alert` analysis banner (lines 296-329) moves from the vision tab to Tab 1, shown only when `setupMode === 'ai'`. The "Stage Analysis" button and "No Thanks" button are already built — just relocate them.

Move the `extraction_custom_instructions` textarea (currently on vision tab) into Tab 1, visible only when `setupMode === 'ai'`.

**6. Add tab locking during analysis**

```javascript
const analysisInProgress = ref(false)

// When user clicks Stage Analysis:
function stageAnalysis() {
  // existing clipboard copy logic...
  analysisInProgress.value = true
}

// WebSocket handler (already wired):
// on vision:analysis_complete → analysisInProgress.value = false
```

In the template, disable tab buttons when locked:

```html
<v-btn value="info" :disabled="analysisInProgress" ...>Product Info</v-btn>
<v-btn value="tech" :disabled="analysisInProgress" ...>Tech Stack</v-btn>
<!-- etc. -->
```

Add a status indicator when locked (below the tabs, above the tab content):

```html
<v-alert v-if="analysisInProgress" type="info" variant="tonal" density="compact" class="mb-2">
  <v-progress-linear indeterminate color="info" class="mb-1" />
  Waiting for AI analysis... Paste the prompt in your coding tool.
</v-alert>
```

**7. Unlock + populate on WebSocket event**

The existing `vision:analysis_complete` handler already refreshes product data via `fetchProducts()`. After the refresh:
- `analysisInProgress.value = false` (tabs unlock)
- `loadProductData()` re-reads product fields into the form
- Fields appear populated in all tabs
- Toast: "AI populated N fields — review your configuration"

### What Stays the Same

- All field names, models, and API calls — unchanged
- The save/submit logic — unchanged
- The Sumy summarization flow — unchanged
- The MCP tools (gil_get_vision_doc, gil_write_product) — unchanged
- The WebSocket event handler — just add `analysisInProgress = false`
- Edit mode for existing products — fields pre-populate as before

### Edge Cases

- **No vision doc uploaded**: AI radio option disabled. Manual is default.
- **User selects AI, copies prompt, then switches to Manual**: Unlock tabs, let them type. If the agent later completes, fields update silently in the background (no lock shown since mode is manual).
- **User closes dialog while analysis in progress**: Reset `analysisInProgress` on dialog close. If the agent completes later, the WebSocket event still fires and updates the product in the store — next time user opens the dialog, fields are populated.
- **Edit mode (existing product)**: Same flow. User can re-upload a new vision doc and re-run analysis.

---

## Implementation Plan

### Phase 1: Tab Restructure

1. Rename Tab 1 button: "Product Info" → "Product Setup"
2. Create new Tab 2: "Product Info" with Description + Core Features (moved from Tab 1)
3. Move vision doc upload section from old Tab 2 into Tab 1
4. Remove "Vision Docs" tab button
5. Update `tabOrder` array and `v-window-item` values
6. Verify all existing functionality works (upload, Sumy, save)

### Phase 2: Mode Selection + Lock/Unlock

1. Add `setupMode` radio group to Tab 1 (manual/ai)
2. Move analysis banner + custom instructions textarea into Tab 1 (conditional on `setupMode === 'ai'`)
3. Add `analysisInProgress` ref
4. Disable tab buttons when `analysisInProgress === true`
5. Add "Waiting for AI analysis..." status indicator
6. Wire unlock to existing `vision:analysis_complete` WebSocket handler
7. Verify lock → prompt copy → agent completes → unlock → fields populated flow

---

## Testing Requirements

- Tab 1 shows name + codebase + vision upload + mode choice (manual test)
- AI radio disabled when no vision doc uploaded (manual test)
- Tab locking works when analysis staged (manual test)
- Tabs unlock on WebSocket event (manual test)
- Fields populated after unlock (manual test)
- Manual mode works identically to old flow (manual test)
- Save works from both modes (manual test)

## Success Criteria

- [ ] Tab 1 is "Product Setup" with vision doc upload merged in
- [ ] Tab 2 is "Product Info" with description + core features
- [ ] Vision Docs tab eliminated (content merged)
- [ ] Manual/AI radio choice works
- [ ] Tabs lock during AI analysis with progress indicator
- [ ] Tabs unlock when `vision:analysis_complete` fires
- [ ] Fields populate correctly after unlock
- [ ] Existing save/edit flow unchanged
- [ ] `smooth-border` on rounded elements, no `!important` overrides

## MANDATORY: Pre-Work Reading

1. `handovers/HANDOVER_INSTRUCTIONS.md` — quality gates, frontend code discipline
2. `handovers/VISION_DOC_ANALYSIS_SPEC_v2.md` — Sections 1 and 7
3. `handovers/Reference_docs/FLow_vision_doc1.png` — user journey (the fork at upload)

**CRITICAL: Use the `ux-designer` subagent for ALL implementation work.**

## Rollback Plan

- Revert `ProductForm.vue` to pre-change state
- Tab restructuring is purely within one component — no API, model, or service changes
