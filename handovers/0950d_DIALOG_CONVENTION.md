# Handover 0950d: Frontend: Dialog Convention + text-medium-emphasis

**Date:** 2026-04-05
**From Agent:** Planning Session (0950 Pre-Release Quality Sprint)
**To Agent:** Next Session (ux-designer or frontend-tester profile)
**Priority:** Medium
**Estimated Complexity:** 2-3 hours
**Status:** Not Started
**Edition Scope:** CE
**Series:** 0950d of 0950 chain — read `prompts/0950_chain/chain_log.json` first
**Depends On:** 0950c must be complete

---

## 1. Task Summary

Audit all Vue components for two related convention violations:

1. **Dialog chrome:** Any `v-card-title` or `v-card-actions` inside a modal/dialog must
   be replaced with the centralized `.dlg-header` / `.dlg-footer` classes from `main.scss`.
   Regular card usage on page layouts is legitimate and must not be changed.

2. **text-medium-emphasis:** Vuetify's `text-medium-emphasis` class is explicitly banned
   by CLAUDE.md because it uses Vuetify's internal opacity stack, which fails WCAG AA
   contrast at certain zoom levels. Every occurrence must be replaced with a scoped CSS
   class using `color: #8895a8` (the `--text-muted` value, 4.98:1 ratio on `#12202e`).

This session produces zero feature changes. It is a mechanical convention pass.

---

## 2. Context and Background

The dialog anatomy convention was established in the 0873 style centralization sprint.
The `.dlg-header` / `.dlg-footer` classes live in
`frontend/src/styles/main.scss` (lines 346-418) and define:

- `.dlg-header` — plain default (flex row, icon + title + close)
- `.dlg-header--warning` — amber band, destructive confirmations
- `.dlg-header--primary` — yellow band (`$yellow`), major workflow actions
- `.dlg-header--danger` — magenta band, critical/irreversible actions
- `.dlg-header--sticky` — position sticky for scrollable dialogs
- `.dlg-footer` — flex row, right-aligned, `gap: 8px`, `padding: 10px 20px`
- `.dlg-close` — close button inside header (see sub-class in `.dlg-header`)

The `text-medium-emphasis` ban is in CLAUDE.md:
> Never use Vuetify's `text-medium-emphasis` class — use a scoped CSS class with
> `color: #8895a8` instead. `--text-muted` is `#8895a8` (4.98:1 on `#12202e`).

Two global utility classes already exist in `main.scss` for this:
- `.text-muted-a11y` — `color: var(--text-muted) !important` (maps to `#8895a8`)
- `.text-secondary-a11y` — `color: var(--text-secondary) !important` (maps to `#a3aac4`)

---

## 3. Chain Execution Instructions (Orchestrator-Gated v3)

You are a session in the 0950 chain on branch `feature/0950-pre-release-quality`.

### Step 1: Read Chain Log and Directives
Read `/media/patrik/Work/GiljoAI_MCP/prompts/0950_chain/chain_log.json`.
- Check `orchestrator_directives` in your session entry (0950d). If it contains "STOP",
  halt immediately.
- Read 0950c's `notes_for_next` — it lists which Vue component files 0950c edited.
  Do not edit the same files simultaneously unless 0950c is confirmed committed.

### Step 2: Verify Prerequisite
Confirm 0950c status is `"complete"` in the chain log. If not, STOP and report.

### Step 3: Mark Session Started
Update your entry in the chain log:
```json
"status": "in_progress"
```

### Step 4: Execute (see Section 5 below)

### Step 5: Update Chain Log Before Stopping
Fill in `tasks_completed`, `deviations`, `notes_for_next` (for 0950e — list all
`.vue` files edited so 0950e can plan its hex sweep accordingly), `summary`,
`status: "complete"`.

### Step 6: Commit and STOP
```bash
git add -A
git commit -m "cleanup(0950d): dialog convention — dlg-header/footer, remove text-medium-emphasis"
git add prompts/0950_chain/chain_log.json
git commit -m "docs: 0950d chain log — session complete"
```

Do NOT spawn the next terminal. The orchestrator handles that.

---

## 4. Critical Agent Rules (Read Before Touching Any File)

- **Before deleting ANY code:** verify zero upstream/downstream references using grep.
  A class name may be referenced via JavaScript (e.g., `classList.add`) or in tests.
- **Tests that fail must be fixed or deleted — never skip.**
- **No commented-out code.** If you encounter existing commented-out blocks while
  editing a file, delete them (0950c may have missed some).
- **Read `frontend/design-system-sample-v2.html`** as the authoritative UI/brand
  reference before making any styling decisions.
- Commit with prefix `cleanup(0950d):` on all commits.

---

## 5. Implementation Plan

### Phase 1: Audit v-card-title and v-card-actions

Run these searches from the repo root:

```bash
grep -rn "v-card-title" /media/patrik/Work/GiljoAI_MCP/frontend/src/ --include="*.vue"
grep -rn "v-card-actions" /media/patrik/Work/GiljoAI_MCP/frontend/src/ --include="*.vue"
```

For each hit, classify it:

**Dialog chrome (MUST convert):** The component contains a `<v-dialog>` or
`<v-overlay>` ancestor, and `v-card-title` / `v-card-actions` is used as the
modal header or footer. These are the violations to fix.

**Non-dialog card content (leave as-is):** The `v-card` lives directly on a page
view (dashboard, settings, products list) as a layout card — not inside a `v-dialog`.
These are legitimate Vuetify usage.

When in doubt: if the `v-card` is wrapped by `<v-dialog v-model="...">`, it is dialog
chrome. If it is rendered unconditionally in the page flow, it is a layout card.

### Phase 2: Convert Dialog Chrome

For each dialog-chrome violation, apply the conversion below.

**Before (typical violation pattern):**
```vue
<v-dialog v-model="dialog">
  <v-card>
    <v-card-title>
      <v-icon>mdi-cog</v-icon>
      Settings
      <v-spacer />
      <v-btn icon @click="dialog = false"><v-icon>mdi-close</v-icon></v-btn>
    </v-card-title>
    <!-- body -->
    <v-card-actions>
      <v-spacer />
      <v-btn text @click="dialog = false">Cancel</v-btn>
      <v-btn flat color="primary" @click="save">Save</v-btn>
    </v-card-actions>
  </v-card>
</v-dialog>
```

**After (correct convention):**
```vue
<v-dialog v-model="dialog">
  <v-card>
    <div class="dlg-header">
      <v-icon class="dlg-icon">mdi-cog</v-icon>
      <span class="dlg-title">Settings</span>
      <v-btn icon variant="text" class="dlg-close" @click="dialog = false">
        <v-icon>mdi-close</v-icon>
      </v-btn>
    </div>
    <!-- body -->
    <div class="dlg-footer">
      <v-spacer />
      <v-btn variant="text" @click="dialog = false">Cancel</v-btn>
      <v-btn variant="flat" color="primary" @click="save">Save</v-btn>
    </div>
  </v-card>
</v-dialog>
```

**Header variant selection:**
- Plain `.dlg-header` — default, neutral dialogs (settings, info, view)
- `.dlg-header .dlg-header--warning` — destructive confirmations (delete, remove)
- `.dlg-header .dlg-header--primary` — major workflow actions (launch, closeout, handover)
- `.dlg-header .dlg-header--danger` — critical/irreversible (data wipe, account removal)

Every dialog header must have a `.dlg-close` button. No exceptions.

Footer layout rule: `<v-spacer>` on the left, Cancel (variant="text") on the right
before the primary action (variant="flat").

### Phase 3: Remove text-medium-emphasis

Search:
```bash
grep -rn "text-medium-emphasis" /media/patrik/Work/GiljoAI_MCP/frontend/src/ --include="*.vue" --include="*.js"
```

For each occurrence:

**Option A — Use the global utility class (preferred when the element is a standalone
text span or div with no other muted styling):**
```vue
<!-- Before -->
<span class="text-medium-emphasis">Last seen 3 min ago</span>

<!-- After -->
<span class="text-muted-a11y">Last seen 3 min ago</span>
```

**Option B — Scoped CSS class (preferred when the element is a reusable component
or already has a meaningful CSS class):**

In `<template>`:
```vue
<!-- Before -->
<p class="text-medium-emphasis mb-0">{{ subtitle }}</p>

<!-- After -->
<p class="card-subtitle mb-0">{{ subtitle }}</p>
```

In `<style scoped>`:
```css
.card-subtitle {
  color: #8895a8;
}
```

Do not use `var(--text-muted)` inline in the template attribute — prefer the scoped
class pattern so it reads cleanly in the template.

Do not use `color: rgba(...)` — use the exact hex `#8895a8`. This is the WCAG AA
compliant value specified in CLAUDE.md.

### Phase 4: Verify

```bash
# Confirm no text-medium-emphasis remains
grep -rn "text-medium-emphasis" /media/patrik/Work/GiljoAI_MCP/frontend/src/

# Confirm no v-card-title / v-card-actions remain inside dialog chrome
# (check output manually — some legitimate non-dialog usages are expected)
grep -rn "v-card-title\|v-card-actions" /media/patrik/Work/GiljoAI_MCP/frontend/src/

# Run tests
cd /media/patrik/Work/GiljoAI_MCP/frontend && npx vitest run
```

---

## 6. Files in Scope

All `.vue` files in `frontend/src/components/` and `frontend/src/views/`.

Files most likely to contain dialog chrome violations (from codebase survey):
- `frontend/src/components/projects/AgentJobModal.vue`
- `frontend/src/components/projects/AgentMissionEditModal.vue`
- `frontend/src/components/projects/AgentDetailsModal.vue`
- `frontend/src/components/projects/HandoverModal.vue`
- `frontend/src/components/products/ProductDeleteDialog.vue`
- `frontend/src/components/products/ProductDetailsDialog.vue`
- `frontend/src/components/products/ActivationWarningDialog.vue`
- `frontend/src/components/products/DeletedProductsRecoveryDialog.vue`
- `frontend/src/components/org/InviteMemberDialog.vue`
- `frontend/src/components/orchestration/ManualCloseoutModal.vue`
- `frontend/src/components/orchestration/CloseoutModal.vue`
- `frontend/src/components/navigation/ConnectionDebugDialog.vue`
- `frontend/src/components/UserProfileDialog.vue`
- `frontend/src/components/LicensingDialog.vue`
- `frontend/src/components/GitAdvancedSettingsDialog.vue`

**Do NOT edit** `frontend/src/styles/main.scss` or `frontend/src/styles/design-tokens.scss`
in this session — those are token definition files, not convention violations.

**Do NOT touch hex color values** in component styles — that is the scope of 0950e.

---

## 7. Testing Requirements

- `grep -rn "text-medium-emphasis" frontend/src/` returns zero results
- All dialogs render with `.dlg-header` / `.dlg-footer` structure (visual spot-check)
- Every modal has a `.dlg-close` button
- `npx vitest run` — all tests pass, no new failures

---

## 8. Success Criteria

- Zero `text-medium-emphasis` usages in the entire `frontend/src/` tree
- All dialog modals use `.dlg-header` / `.dlg-footer` (no `v-card-title` /
  `v-card-actions` left in dialog chrome)
- Non-dialog `v-card-title` / `v-card-actions` usage in page layout cards is untouched
- All Vitest tests pass

---

## 9. Rollback Plan

All changes are mechanical template and class-name swaps. Git revert is safe:
```bash
git revert HEAD
```
No schema changes, no new dependencies, no logic changes.

---

## 10. Additional Resources

- `frontend/src/styles/main.scss` (lines 346–418) — `.dlg-header`, `.dlg-footer`,
  `.dlg-close`, header variants
- `frontend/design-system-sample-v2.html` — authoritative UI/brand reference with
  dialog anatomy examples (open in browser)
- `CLAUDE.md` — dialog anatomy and WCAG AA text conventions
- `prompts/0950_chain/chain_log.json` — orchestrator directives and 0950c notes

---

## Progress Updates

*(Agent updates this section during execution)*
