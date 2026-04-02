# 0873 — Style Centralization Sweep

**Edition Scope:** CE
**Priority:** HIGH
**Estimated Sessions:** 15 (0873a through 0873o)
**Branch:** `feature/0870-design-harmonization` (continues on same branch)

---

## Objective

The 0870/0871/0872 series established the correct design tokens, global classes, and shared components — but inlined the raw CSS implementation into ~66 scoped style blocks instead of using the centralized classes. This series replaces every hardcoded value with its token/class equivalent so that one change in `main.scss` or `design-tokens.scss` propagates everywhere.

**Rule:** After this series, a `grep` for any hardcoded value listed below should return ZERO hits in `frontend/src/views/` and `frontend/src/components/` (excluding `design-tokens.scss` and `main.scss` where they are defined).

---

## Reference Files (READ THESE FIRST)

- `frontend/src/styles/design-tokens.scss` — all token definitions
- `frontend/src/styles/main.scss` — global classes (smooth-border, icon-interactive, etc.)
- `frontend/src/styles/agent-colors.scss` — agent color classes
- `frontend/design-system-sample-v2.html` — visual reference for every pattern

---

## Sub-Handover Breakdown

### 0873a — Frame & Smooth-Border Enforcement

**Goal:** Replace every hardcoded `box-shadow: inset 0 0 0 1px` with the `smooth-border` class.

**Token/class reference:**
- `.smooth-border` → `box-shadow: inset 0 0 0 1px var(--smooth-border-color, rgba(255,255,255,0.10))`
- `.smooth-border-2` → 2px variant
- `.smooth-border-accent` → 2px brand yellow

**Find pattern:**
```bash
grep -rn "box-shadow: inset 0 0 0 1px" frontend/src/views/ frontend/src/components/ --include="*.vue" --include="*.scss"
```

**Exclude from changes:** `main.scss` (definition), `design-tokens.scss`, `design-system-sample-v2.html`

**Files to fix (18 known):**

Views:
1. `TasksView.vue` — `.task-table-card` (line ~832), `.filter-search :deep(.v-field)` (line ~851), `.filter-select :deep(.v-field)` (line ~864)
2. `ProjectsView.vue` — `:deep(.v-card)` blanket rule (line ~1548), `.project-filter-bar` (line ~1535)
3. `MessagesView.vue` — scoped card styling (line ~104, ~108)
4. `WelcomeView.vue` — 4 occurrences (lines ~567, ~637, ~676, ~744)
5. `SystemSettings.vue` — line ~346
6. `UserSettings.vue` — line ~524

Components:
7. `JobsTab.vue` — `.table-container` and badges (lines ~966, ~1317, ~1359, ~1385, ~1399, ~1403)
8. `LaunchTab.vue` — line ~411
9. `ProductSelector.vue` — lines ~58, ~63
10. `AgentJobModal.vue` — lines ~243, ~248
11. `BroadcastPanel.vue` — lines ~503, ~508
12. `ProjectTabs.vue` — lines ~876, ~880, ~906
13. `ProductForm.vue` — line ~1118
14. `AgentTableView.vue` — line ~265
15. `NavigationDrawer.vue` — lines ~224, ~237
16. `StatusChip.vue` — lines ~115, ~126
17. `SetupWizardOverlay.vue` — lines ~349, ~551

**How to fix each:**

For container elements (v-card, div panels):
- Add `class="smooth-border"` to the template element
- Remove the `box-shadow: inset` line from scoped CSS
- If the element also needs `border: none !important`, the `smooth-border` class handles that

For `:deep(.v-field)` input overrides (filter inputs):
- These are Vuetify internal elements — you CANNOT add a class to `.v-field` directly
- Keep the `:deep(.v-field)` rule BUT replace the hardcoded value with the token:
  ```scss
  .filter-search :deep(.v-field) {
    box-shadow: inset 0 0 0 1px var(--smooth-border-color, rgba(255, 255, 255, 0.10));
  }
  ```
- This is acceptable — `:deep()` overrides of Vuetify internals cannot use utility classes

For focus states (e.g. `box-shadow: inset 0 0 0 1px rgba($color-brand-yellow, 0.3)`):
- These are interactive states, keep in scoped CSS — they are NOT candidates for smooth-border class
- Leave them as-is

**Special case — ProjectsView blanket rule:**
The `:deep(.v-card)` rule on line ~1547 applies smooth-border to ALL v-cards in the component. Replace with explicit `smooth-border` class on each v-card in the template, then delete the blanket rule. This prevents unintended styling of nested dialog v-cards.

**Verification:**
```bash
# Should return ZERO hits (excluding definitions and :deep() Vuetify overrides)
grep -rn "box-shadow: inset 0 0 0 1px" frontend/src/views/ frontend/src/components/ --include="*.vue" | grep -v ":deep(" | grep -v "focus"
```

**Tests:** Run full Vitest suite.

---

### 0873b — Border-Radius Token Enforcement

**Goal:** Replace every hardcoded `border-radius` pixel value with the corresponding design token.

**Token reference (from design-tokens.scss):**
- `$border-radius-sharp: 4px` — scrollbar thumbs, tight inputs, code blocks
- `$border-radius-default: 8px` — panels, buttons, standard elements
- `$border-radius-rounded: 16px` — cards, containers, main panels
- `$border-radius-pill: 9999px` — pills, tags, chips, fully rounded

**Find pattern:**
```bash
grep -rn "border-radius:" frontend/src/views/ frontend/src/components/ --include="*.vue" --include="*.scss"
```

**Exclude from changes:** `design-tokens.scss` (definitions), `main.scss` (global classes), `design-system-sample-v2.html`

**Mapping rules:**
| Hardcoded Value | Replace With | Context |
|----------------|-------------|---------|
| `4px` | `$border-radius-sharp` | Small elements, code blocks |
| `6px` | `$border-radius-sharp` (or keep if intentional — use judgment) |
| `8px` | `$border-radius-default` | Standard elements |
| `10px` | `$border-radius-default` (round to 8px — see note) |
| `12px` | `$border-radius-default` (round to 8px or create `$border-radius-md: 12px` if 5+ uses) |
| `16px` | `$border-radius-rounded` | Cards, containers |
| `9999px` | `$border-radius-pill` | Pills, chips |
| `50%` | KEEP as-is — this is for circles (dot indicators, avatars) |

**NOTE on 10px and 12px:** Count how many files use each. If 5+ files use `12px`, create a new token `$border-radius-md: 12px` in design-tokens.scss. If fewer, round to `$border-radius-default` (8px). Same logic for `10px`. Document your decision in the commit message.

**Files affected:** ~66 files. Work through views first (11 files), then components.

**Each file procedure:**
1. Open the `<style>` block
2. Find every `border-radius:` declaration
3. Check if it already uses a token (skip if so)
4. Replace the pixel value with the correct token
5. Ensure the file has `@use '../styles/design-tokens' as *;` at the top of the style block (add if missing)

**Important:** Files using `<style lang="scss" scoped>` need the `@use` import. Files using `<style scoped>` (no lang="scss") cannot use SCSS tokens — convert them to `<style lang="scss" scoped>` first and add the import.

**Verification:**
```bash
# Should return ZERO hits for hardcoded pixel values (excluding 50% circles and definitions)
grep -rn "border-radius: [0-9]" frontend/src/views/ frontend/src/components/ --include="*.vue" | grep -v "50%" | grep -v "design-tokens"
```

**Tests:** Run full Vitest suite.

---

### 0873c — Table Header Pattern Extraction

**Goal:** Extract the repeated table header styling pattern into a shared mixin or class.

**The pattern (duplicated in 15+ files):**
```scss
font-size: 0.6rem !important;
text-transform: uppercase;
letter-spacing: 0.06em;
color: $color-text-muted !important;
font-weight: 500 !important;
```

**Step 1 — Create shared mixin in `main.scss`:**
```scss
// Table header label — compact uppercase label used in all data tables
// Applied via :deep() to Vuetify table headers
@mixin table-header-label {
  font-size: 0.6rem !important;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: $color-text-muted !important;
  font-weight: 500 !important;
}
```

Also add a utility class in `main.scss`:
```scss
.table-header-label {
  @include table-header-label;
}
```

**Step 2 — Find all duplicates:**
```bash
grep -rn "font-size: 0.6rem" frontend/src/views/ frontend/src/components/ --include="*.vue"
```

**Files to fix (known):**
1. `TasksView.vue` — `:deep(.v-data-table__thead th)` block
2. `ProjectsView.vue` — `:deep(.v-data-table__thead th)` block
3. `JobsTab.vue` — `.agents-table thead th` block, `.execution-order-title`
4. `LaunchTab.vue` — table header styling
5. `AgentTableView.vue` — if present
6. `RecentProjectsList.vue` — list header
7. `RecentMemoriesList.vue` — list header

**How to fix each:**
- Replace the 5-line block with `@include table-header-label;`
- Ensure the file imports main.scss or design-tokens.scss (for the mixin)

**Also extract table row separator pattern:**
```scss
// Row separators
@mixin table-row-separator {
  border-bottom: 1px solid rgba(255, 255, 255, 0.04) !important;
}
```

Find: `grep -rn "rgba(255, 255, 255, 0.04)" frontend/src/ --include="*.vue"`

**Verification:**
```bash
# The raw pattern should only exist in main.scss (definition)
grep -rn "font-size: 0.6rem" frontend/src/views/ frontend/src/components/ --include="*.vue"
# Should return ZERO
```

**Tests:** Run full Vitest suite.

---

### 0873d — Modal & Dialog Standardization

**Goal:** Standardize dialog framing, scrollable body, and text colors.

**Step 1 — Create shared dialog classes in `main.scss`:**
```scss
.dialog-body-scroll {
  max-height: 70vh;
  overflow-y: auto;
}

.dialog-card {
  @extend .smooth-border;
  border-radius: $border-radius-rounded;
}
```

**Step 2 — Find all dialogs:**
```bash
grep -rn "v-dialog" frontend/src/components/ --include="*.vue" -l
```

**Step 3 — For each dialog:**
- Replace inline `style="max-height: 70vh; overflow-y: auto;"` with `class="dialog-body-scroll"`
- Replace hardcoded `style="color: #8895a8"` with `class="text-muted-a11y"` (already exists in main.scss)
- Replace hardcoded `style="color: #a3aac4"` with a new `.text-secondary-a11y` class (create in main.scss if not exists)
- Ensure dialog v-card uses `smooth-border` class

**Key files (36 total):** ProductDetailsDialog, AddTypeModal, ProjectReviewModal, AgentJobModal, HandoverModal, ManualCloseoutModal, CloseoutModal, AgentMissionEditModal, AgentDetailsModal, MessageAuditModal, ProductTuningReview, DeletedProductsRecoveryDialog, AgentTipsDialog, LicensingDialog, GitAdvancedSettingsDialog, UserProfileDialog, ActivationWarningDialog, and others.

**Verification:**
```bash
grep -rn 'style="color: #8895a8"' frontend/src/ --include="*.vue"
grep -rn 'style="color: #a3aac4"' frontend/src/ --include="*.vue"
grep -rn 'max-height: 70vh' frontend/src/ --include="*.vue" | grep "style="
# All should return ZERO
```

**Tests:** Run full Vitest suite.

---

### 0873e — Transition & Animation Tokens

**Goal:** Create shared transition tokens and replace hardcoded `transition:` declarations.

**Step 1 — Add tokens to `design-tokens.scss`:**
```scss
// Transition durations
$transition-fast: 0.15s;
$transition-normal: 0.25s;
$transition-slow: 0.4s;

// Common transitions
$transition-hover: background $transition-fast, color $transition-fast;
$transition-transform: transform $transition-normal ease;
$transition-all-fast: all $transition-fast ease;
```

**Step 2 — Find all hardcoded transitions:**
```bash
grep -rn "transition:" frontend/src/views/ frontend/src/components/ --include="*.vue"
```

**Step 3 — Replace each with the appropriate token:**
| Hardcoded | Replace With |
|-----------|-------------|
| `transition: background 0.15s` | `transition: background $transition-fast` |
| `transition: all 0.15s ease` | `transition: $transition-all-fast` |
| `transition: all 0.15s` | `transition: $transition-all-fast` |
| `transition: transform 0.2s` | `transition: transform $transition-normal ease` |
| `transition: opacity 0.3s` | `transition: opacity $transition-normal` |

**Leave alone:** Component-specific `@keyframes` animations (pulse, fade, slide) — these are not candidates for token replacement. Only standardize the timing values within them.

**Verification:**
```bash
grep -rn "transition:.*0\.\(15\|2\|25\|3\)s" frontend/src/views/ frontend/src/components/ --include="*.vue"
# Should return ZERO (all should use tokens)
```

**Tests:** Run full Vitest suite.

---

### 0873f — Button Style Consolidation

**Goal:** Ensure all buttons use Vuetify variants, global classes (`.btn-*`, `.pill-button`), or scoped classes — no inline button styling.

**Find inline button styles:**
```bash
grep -rn 'style=".*background.*border.*radius' frontend/src/ --include="*.vue" | grep -i "btn\|button"
```

**Key issues to fix:**
1. Color swatch picker buttons in `AddTypeModal.vue` — extract to `.color-swatch-btn` class
2. Any `v-btn` with inline `style=` for colors — use Vuetify `color=` prop or scoped class instead
3. Filter clear buttons — ensure consistent styling across TasksView, ProjectsView

**Do NOT change:** Dynamic `:style` bindings that compute colors from data (agent colors, status colors) — these must remain dynamic. But extract the static properties (border-radius, padding, font-size) to a class.

**Tests:** Run full Vitest suite.

---

### 0873g — Text Color Token Enforcement

**Goal:** Replace all hardcoded text color hex values with SCSS tokens or CSS custom properties.

**Token reference:**
- `$color-text-primary` / `var(--text-primary)` → `#e1e1e1`
- `$color-text-secondary` / `var(--text-secondary)` → `#a3aac4`
- `$color-text-muted` / `var(--text-muted)` → `#8895a8`
- `$color-brand-yellow` → `#ffc300`

**Find patterns:**
```bash
grep -rn "#8895a8" frontend/src/ --include="*.vue" | grep -v "design-tokens\|main.scss\|design-system"
grep -rn "#a3aac4" frontend/src/ --include="*.vue" | grep -v "design-tokens\|main.scss\|design-system"
grep -rn "#e1e1e1" frontend/src/ --include="*.vue" | grep -v "design-tokens\|main.scss\|design-system"
grep -rn "#5a6a80" frontend/src/ --include="*.vue"  # OLD muted - should be ZERO already
```

**How to fix:**
- In `<style>` blocks: replace hex with SCSS variable (`$color-text-muted`)
- In `<template>` inline styles: replace with CSS class (`.text-muted-a11y`, create `.text-secondary-a11y` if needed)
- In `:style` bindings: replace hex string with CSS custom property reference

**Tests:** Run full Vitest suite.

---

### 0873h — Dropdown & Select Patterns

**Goal:** Standardize v-select and v-menu overrides.

**Find patterns:**
```bash
grep -rn "v-select\|v-menu\|v-autocomplete" frontend/src/ --include="*.vue" -l
```

**Audit each for:**
- Consistent `variant=` prop usage (should be `"solo"` + `flat` for filter selects)
- Consistent `density=` prop usage
- Any scoped CSS overrides on `.v-field` — should use the same smooth-border pattern from 0873a

**This is primarily an audit handover.** Create a checklist, verify consistency, fix deviations.

**Tests:** Run full Vitest suite.

---

### 0873i — Scrollbar Standardization

**Goal:** Ensure all scrollbar styling is in `main.scss` global scope. Remove component-level overrides.

**Find patterns:**
```bash
grep -rn "scrollbar" frontend/src/ --include="*.vue" --include="*.scss"
```

**Known files with component-level scrollbar styles:**
1. `LaunchTab.vue`
2. `NotificationDropdown.vue`

**Fix:** If the component needs a different scrollbar width/color, use a CSS class that inherits from the global style. If it's identical to the global style, just delete it.

**Tests:** Run full Vitest suite.

---

### 0873j — Loading & Skeleton State Documentation

**Goal:** Document the loading state pattern in V2 design template. Audit for consistency.

**Standard pattern (already in use):**
- `v-progress-circular indeterminate` for button/inline loading
- `v-progress-linear indeterminate` for page/section loading
- Custom `@keyframes pulse` for health indicators

**Audit:** Verify all async operations have a loading indicator. Flag any that don't.

**Find:**
```bash
grep -rn "v-progress-circular\|v-progress-linear\|loading" frontend/src/ --include="*.vue" -l
```

Cross-reference with files that make API calls:
```bash
grep -rn "await.*api\.\|\.get(\|\.post(\|\.put(\|\.delete(" frontend/src/ --include="*.vue" -l
```

Any file in the second list but NOT in the first list is missing a loading indicator.

**Tests:** Run full Vitest suite.

---

### 0873k — Toast & Notification Consistency

**Goal:** Audit all toast messages for consistent tone and patterns.

**Find:**
```bash
grep -rn "useToast\|showSuccess\|showError\|showWarning\|showInfo" frontend/src/ --include="*.vue" --include="*.js" --include="*.ts"
```

**Audit each for:**
- Success messages: consistent format (e.g., "Project created successfully" not "Created!")
- Error messages: plain language, suggests recovery action
- Warning messages: explains what and why

**This is an audit + report handover.** Fix obviously bad messages. Flag subjective ones for human review.

**Tests:** Run full Vitest suite.

---

### 0873L — V2 Design Template Update

**Goal:** Add missing sections to `design-system-sample-v2.html` for categories that exist in the codebase but aren't documented.

**Sections to add:**
- Modal/Dialog patterns (standard dialog card, scroll body, footer button layout)
- Transition/animation tokens (fast/normal/slow with live demo)
- Scrollbar styling (global pattern + code snippet)
- Loading states (progress-circular, progress-linear, pulse animation)
- Toast/notification patterns (success/error/warning/info examples)
- Form validation patterns (input error states, helper text)

**Update TOC** to reflect new sections.

**Reference:** Follow the exact same HTML/CSS patterns used in existing V2 sections. Use `.card`, `.card-elevated`, `.grid-*`, `.token-label`, `.token-value` classes.

**Tests:** Open the HTML file in browser, verify all sections render correctly.

---

### 0873m — Final Style Audit & Verification

**Goal:** Full codebase grep to verify zero remaining hardcoded CSS values.

**Run ALL verification greps from 0873a through 0873k.** Every one should return zero hits (excluding definition files).

**Master checklist:**
```bash
# Frames
grep -rn "box-shadow: inset 0 0 0 1px" frontend/src/views/ frontend/src/components/ --include="*.vue" | grep -v ":deep(" | grep -v "focus" | wc -l
# Border radius
grep -rn "border-radius: [0-9]" frontend/src/views/ frontend/src/components/ --include="*.vue" | grep -v "50%" | wc -l
# Table headers
grep -rn "font-size: 0.6rem" frontend/src/views/ frontend/src/components/ --include="*.vue" | wc -l
# Text colors
grep -rn "#8895a8\|#a3aac4\|#e1e1e1" frontend/src/views/ frontend/src/components/ --include="*.vue" | wc -l
# Transitions
grep -rn "transition:.*0\.15s\|transition:.*0\.2s\|transition:.*0\.3s" frontend/src/views/ frontend/src/components/ --include="*.vue" | wc -l
```

**If any grep returns >0:** Fix the remaining files. Document exceptions (e.g., `:deep()` Vuetify overrides that genuinely cannot use classes).

**Final step:** Run full Vitest suite. All 1916 tests must pass.

---

### 0873n — H4: Terminology & Icon Standardization

**Goal:** Fix inconsistent terminology, icon choices, and empty state patterns across all views and components. Based on Nielsen Heuristic #4 (Consistency & Standards) audit.

**This handover has 5 sub-tasks. Do them in order.**

#### Sub-task 1: Cancel vs Close terminology

**Rule to enforce:**
- **"Cancel"** → dialog has a form / editable data (discards changes)
- **"Close"** → dialog is read-only / informational (nothing to discard)

**Find all dialog action buttons:**
```bash
grep -rn "Cancel\|Close" frontend/src/ --include="*.vue" | grep -i "v-btn\|v-card-actions\|@click.*dialog\|@click.*close\|@click.*cancel"
```

**Known files to check (22 instances):**

Should use **"Cancel"** (editable dialogs):
1. `UserProfileDialog.vue` — has form → "Cancel" ✓ (already correct)
2. `TasksView.vue` — edit task dialog → "Cancel" ✓ (already correct)
3. `ProjectsView.vue` — create/edit project → should be "Cancel"
4. `TemplateManager.vue` — edit template → should be "Cancel"
5. `AgentMissionEditModal.vue` — edit mission → "Cancel" ✓ (already correct)
6. `InviteMemberDialog.vue` — invite form → should be "Cancel"
7. `ProductForm.vue` — product creation → should be "Cancel"

Should use **"Close"** (read-only dialogs):
1. `ProductDetailsDialog.vue` — info display → "Close" ✓ (already correct)
2. `AgentDetailsModal.vue` — info display → should be "Close"
3. `DeletedProductsRecoveryDialog.vue` — recovery list → should be "Close"
4. `ProjectReviewModal.vue` — review display → should be "Close"
5. `MessageAuditModal.vue` — message history → should be "Close"
6. `AgentTipsDialog.vue` — reference info → should be "Close"
7. `LicensingDialog.vue` — license info → should be "Close"
8. `HandoverModal.vue` — handover info → should be "Close"

**For each file:** Open, find the cancel/close button text, verify it matches the rule. Fix if wrong.

#### Sub-task 2: Delete icon standardization

**Rule to enforce:**
| Action | Icon | When |
|--------|------|------|
| Soft delete (move to trash) | `mdi-delete` | Default delete action |
| Permanent delete | `mdi-delete-forever` | Irreversible purge from trash |
| Restore from trash | `mdi-delete-restore` | Recovery action |
| Clear/sweep batch | `mdi-delete-sweep` | Bulk clear operations |

**Do NOT use:** `mdi-trash-can`, `mdi-delete-alert`, `mdi-delete-outline` — these create visual inconsistency.

**Find all delete icons:**
```bash
grep -rn "mdi-delete\|mdi-trash" frontend/src/ --include="*.vue"
```

**Known fixes:**
1. `ProjectsView.vue:668` — change `mdi-trash-can` → `mdi-delete-restore` (it's a recovery action in deleted projects list)
2. `TasksView.vue` — verify uses `mdi-delete` for delete action
3. `DeletedProductsRecoveryDialog.vue` — verify uses `mdi-delete-restore` for restore, `mdi-delete-forever` for permanent

#### Sub-task 3: Edit and Settings icon standardization

**Rules:**
- Edit action: always `mdi-pencil` (filled, not outline)
- Settings/config: always `mdi-cog` (filled, not outline)

**Find outliers:**
```bash
grep -rn "mdi-pencil-outline" frontend/src/ --include="*.vue"
grep -rn "mdi-cog-outline" frontend/src/ --include="*.vue"
```

**Known fixes:**
1. `AiToolConfigWizard.vue:68` — change `mdi-pencil-outline` → `mdi-pencil`
2. `WelcomeView.vue:50` — change `mdi-cog-outline` → `mdi-cog`
3. `ProductIntroTour.vue` — check and fix if `mdi-cog-outline` present

#### Sub-task 4: Create EmptyState shared component

**Goal:** Create `frontend/src/components/common/EmptyState.vue` — a reusable empty state component.

**Props:**
```
icon: String (required) — MDI icon name, e.g. "mdi-clipboard-text-outline"
title: String (required) — heading text, e.g. "No tasks yet"
description: String (optional) — body text
actionLabel: String (optional) — button text, e.g. "Create Task"
actionIcon: String (optional) — button icon
```

**Emit:** `@action` when the button is clicked.

**Template:**
```vue
<template>
  <div class="empty-state">
    <v-icon :icon="icon" size="48" class="empty-state-icon" />
    <div class="empty-state-title">{{ title }}</div>
    <div v-if="description" class="empty-state-description">{{ description }}</div>
    <v-btn
      v-if="actionLabel"
      variant="flat"
      color="primary"
      class="empty-state-action"
      :prepend-icon="actionIcon"
      @click="$emit('action')"
    >
      {{ actionLabel }}
    </v-btn>
  </div>
</template>
```

**Styles (scoped, using tokens):**
```scss
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  text-align: center;
}
.empty-state-icon {
  color: $color-text-muted;
  margin-bottom: 16px;
  opacity: 0.6;
}
.empty-state-title {
  font-family: 'Outfit', sans-serif;
  font-size: 1rem;
  font-weight: 500;
  color: $color-text-secondary;
  margin-bottom: 8px;
}
.empty-state-description {
  font-size: 0.82rem;
  color: $color-text-muted;
  max-width: 400px;
  margin-bottom: 20px;
}
```

#### Sub-task 5: Replace inline empty states with EmptyState component

**Find all inline empty states:**
```bash
grep -rn "No.*yet\|no-data\|empty-state\|Nothing to show\|No items\|No results" frontend/src/ --include="*.vue"
```

**Known files to convert:**
1. `TasksView.vue:314-327` — has icon + heading + description → use `<EmptyState>`
2. `LaunchTab.vue:32-33` — has icon + text → use `<EmptyState>`
3. `MessageList.vue:11-20` — has `.empty-state` class → use `<EmptyState>`
4. `MessageAuditModal.vue:94-101` — has icon + message → use `<EmptyState>`

**For each:** Replace the inline HTML with `<EmptyState icon="..." title="..." description="..." />`. Preserve the original icon and text.

#### Sub-task 6: Fix date formatting outliers

**2 files bypass the `useFormatDate()` composable:**
1. `MessageItem.vue:198` — uses `timestamp.toLocaleDateString()`
2. `BroadcastPanel.vue:388` — uses `date.toLocaleDateString()`

**Fix:** Import `useFormatDate` and use `formatDateTime()` or `formatDate()` instead.

**Verification:**
```bash
# Should return ZERO
grep -rn "toLocaleDateString\|toLocaleTimeString" frontend/src/ --include="*.vue"
# Icon consistency
grep -rn "mdi-pencil-outline\|mdi-cog-outline\|mdi-trash-can" frontend/src/ --include="*.vue"
# Should return ZERO
```

**Tests:** Run full Vitest suite.

---

### 0873o — H9: Silent Error Elimination & Message Quality

**Goal:** Ensure every catch block gives user feedback, every error message is plain language with a recovery suggestion, and form validation names the field. Based on Nielsen Heuristic #9 (Error Recovery) audit.

**This handover has 4 sub-tasks. Do them in order.**

#### Sub-task 1: Eliminate silent catch blocks

**Rule:** Every `catch` block that handles a user-initiated operation MUST show a toast. No exceptions.

**Find all silent catch blocks:**
```bash
grep -rn "catch" frontend/src/views/ frontend/src/components/ --include="*.vue" -A5 | grep -B1 "console.error\|console.log" | grep -v "toast\|showError\|showWarning"
```

**Critical files with silent failures (fix these first):**

1. **`DashboardView.vue`** — 4 silent catch blocks:
   - `fetchDashboardData()` (~line 398) — add: `showError('Unable to load dashboard data. Try refreshing the page.')`
   - `fetchCallCounts()` (~line 410) — add: `showError('Unable to load activity counts.')`
   - `fetchSystemStats()` (~line 421) — add: `showError('Unable to load system statistics.')`
   - `checkSetupStatus()` (~line 439) — add: `showWarning('Unable to check setup status.')`

2. **`ProjectsView.vue`** — 3 silent catch blocks + 1 alert():
   - `deleteProject()` (~line 1283) — add: `showError('Failed to delete project. Please try again.')`
   - `purgeDeletedProject()` (~line 1313) — REPLACE `alert()` with: `showError('Failed to permanently delete project.')`
   - `purgeAllDeleted()` (~line 1331) — add: `showError('Failed to purge deleted projects.')`

3. **`ApiKeyManager.vue`** — 2 TODO catch blocks:
   - `loadKeys()` (~line 194) — add: `showError('Unable to load API keys. Try refreshing the page.')`
   - `revokeKey()` (~line 234) — add: `showError('Failed to revoke API key. Please try again.')`

**For each file:**
1. Import `useToast` if not already imported: `const { showError, showWarning } = useToast()`
2. Add the toast call inside the catch block, AFTER the existing console.error (keep the console.error for debugging)
3. Do NOT remove any existing error handling logic — only ADD toast feedback

**After fixing known files, sweep for any remaining silent catches:**
```bash
grep -rn "catch.*{" frontend/src/views/ frontend/src/components/ --include="*.vue" -A10 | grep -v "toast\|showError\|showWarning\|showSuccess\|showInfo"
```

Review each result. If the catch block handles a user-visible operation and has no toast, add one.

#### Sub-task 2: Replace browser alert() calls

**Find:**
```bash
grep -rn "alert(" frontend/src/ --include="*.vue" | grep -v "mdi-alert\|v-alert\|alert-circle\|alert-outline"
```

**Rule:** Never use `window.alert()`. Always use `showError()` or `showWarning()` from `useToast()`.

**Known instances:**
1. `ProjectsView.vue:1293` — replace `alert('Failed to permanently delete...')` with `showError('Failed to permanently delete project.')`

Fix ALL instances found by the grep.

#### Sub-task 3: Add recovery suggestions to generic error messages

**Find all "Failed to" messages:**
```bash
grep -rn "Failed to\|failed to\|Could not\|could not\|Unable to\|unable to" frontend/src/ --include="*.vue"
```

**Rule:** Every error message must follow this pattern:
```
"[What failed]. [Recovery suggestion]."
```

**Examples of BAD → GOOD:**
| BAD (current) | GOOD (replacement) |
|---------------|-------------------|
| "Failed to change product status" | "Failed to change product status. Check if another product is active and try again." |
| "Failed to activate product" | "Failed to activate product. Ensure no other product is currently active." |
| "Failed to delete vision document" | "Failed to delete vision document. The file may be in use — try again in a moment." |
| "Failed to load data" | "Failed to load data. Check your connection and refresh the page." |
| "An error occurred" | NEVER use this. Always be specific about what failed. |

**For each "Failed to X" message:** Add a second sentence with a concrete recovery action. Use these standard recovery phrases:
- Network issues: "Check your connection and refresh the page."
- Conflict/state issues: "Try refreshing the page to get the latest state."
- Permission issues: "You may not have permission for this action."
- Retry issues: "Please try again in a moment."

#### Sub-task 4: Make form validation messages field-specific

**Find generic validation messages:**
```bash
grep -rn "This field is required\|Required\|Invalid" frontend/src/ --include="*.vue" | grep "rules\|rule\|validate"
```

**Rule:** Every validation message must name the field and state the constraint.

**Known fixes:**
1. `UserManager.vue:136` — change `'This field is required'` → `'Username is required'`
2. `UserManager.vue:137` — change `'Invalid email format'` → `'Enter a valid email (e.g. user@company.com)'`
3. `Login.vue:181` — change `'This field is required'` → `'Username is required'` / `'Password is required'` (split by field)
4. `ProductForm.vue:69` — change `'Name is required'` → `'Product name is required'`

**For each validation rule:** Replace generic messages with field-specific messages that include what's expected.

**Verification:**
```bash
# Should return ZERO browser alerts
grep -rn "alert(" frontend/src/ --include="*.vue" | grep -v "mdi-alert\|v-alert\|alert-circle\|alert-outline" | wc -l
# Should return ZERO generic messages
grep -rn "This field is required" frontend/src/ --include="*.vue" | wc -l
# Should return ZERO silent critical catches (manual review needed)
```

**Tests:** Run full Vitest suite.

---

## Execution Strategy

```
0873a (frames) + 0873b (border-radius) — FIRST, foundational
     ↓
0873c (tables) + 0873g (text colors) — can run in parallel
     ↓
0873d (modals) + 0873e (transitions) + 0873f (buttons) — can run in parallel
     ↓
0873h (dropdowns) + 0873i (scrollbars) — can run in parallel
     ↓
0873j (loading) + 0873k (toasts) — audit passes, can run in parallel
     ↓
0873L (V2 template update) — after all style fixes are in
     ↓
0873m (final style verification)
     ↓
0873n (H4 terminology + icons + EmptyState) + 0873o (H9 silent errors + messages) — can run in parallel
```

## Important Notes for Executing Agent

- **Do NOT introduce visual changes in 0873a–m.** Every replacement must produce the exact same rendered output. If a token value differs from the hardcoded value by even 1px, investigate before replacing.
- **0873n WILL introduce minor visual changes** (new EmptyState component). This is intentional — the goal is consistency, not pixel-identical output.
- **0873o WILL introduce new toast messages** where none existed. This is intentional — silent failures are UX bugs.
- **Test after every file change.** Do not batch 20 files and test at the end.
- **Commit after each sub-handover.** One commit per 0873x session.
- **If a hardcoded value doesn't match any token:** Do not create a new token without checking if the value is intentional (a one-off) or a mistake (should match a token). Ask the user if unsure.
