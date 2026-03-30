# 0769d: Frontend Design Token Remediation

**Series:** 0769 (Code Quality & Fragility Remediation Sprint)
**Phase:** 4 of 7
**Branch:** `feature/0769-quality-sprint`
**Priority:** HIGH — 396 hardcoded colors (baseline was 0)
**Estimated Time:** 4 hours

### Reference Documents
- **Audit report:** `handovers/0769_CODE_QUALITY_FRAGILITY_AUDIT.md` (sections H5, H6, M4, M5, M6)
- **Design tokens:** `frontend/src/styles/design-tokens.scss`
- **Project rules:** `CLAUDE.md` (smooth-border rule)

### Tracking Files
- **Chain log:** `prompts/0769_chain/chain_log.json`

---

## Context

The 0765c sprint established zero hardcoded colors as the baseline. After the setup wizard (0855) and dashboard redesign sprints, 396 hardcoded color occurrences have accumulated across 55 `.vue` files. This phase replaces them with design tokens and fixes related CSS violations.

---

## Pre-Work

Before starting, read these files to understand the token system:
- `frontend/src/styles/design-tokens.scss` — the canonical color tokens
- `frontend/src/styles/variables.scss` — Vuetify theme overrides
- `frontend/src/styles/agent-colors.scss` — agent-specific colors
- `frontend/src/styles/main.scss` — global styles including `smooth-border`

---

## Scope

### Task 1: Fix ESLint Errors (2 minutes)

Fix these before anything else:
- `frontend/src/views/ProjectsView.vue:1211` — change `let keys` to `const keys`
- `frontend/src/components/dashboard/RecentProjectsList.vue:55` — replace string concatenation with template literal

### Task 2: Replace Hardcoded Colors (main task)

Work through files by severity. For each hardcoded hex/rgb value, find the matching design token or create one if it represents a recurring pattern.

**Common mappings:**
- `#ffffff` / `white` → `$color-surface` or Vuetify `surface` theme color
- `#000000` / `black` → `$color-on-surface` or Vuetify theme
- `#ffc300` / `rgb(255,195,0)` → `$color-brand-yellow` (GiljoAI brand)
- `#4caf50` → `$color-status-success`
- `#f44336` / `#ff5252` → `$color-status-error`
- `#ff9800` → `$color-status-warning`
- `#2196f3` → `$color-status-info`
- `#9e9e9e` → `$color-text-muted`
- `rgba(0,0,0,0.12)` → `$color-border-subtle`
- `rgba(255,255,255,0.12)` → `$color-border-light`

**Top priority files (highest occurrence count):**

| File | Count | Notes |
|------|-------|-------|
| `components/projects/JobsTab.vue` | 41 | Phase colors, borders, active indicators |
| `components/setup/SetupStep3Commands.vue` | 29 | Brand yellow, dark backgrounds |
| `components/setup/SetupWizardOverlay.vue` | 28 | Gradient backgrounds, progress bar |
| `components/setup/SetupStep2Connect.vue` | 25 | Dark theme overrides |
| `components/projects/MessageAuditModal.vue` | 18 | Border colors, backgrounds |
| `views/DashboardView.vue` | 17 | Stat boxes, chart colors |

**If a color has no existing token and appears 3+ times:** Create a new token in `design-tokens.scss`.

**If a color appears only once and is clearly intentional (e.g., a specific chart color):** Add a comment `/* design-token-exempt: <reason> */` rather than creating a token for a single use.

### Task 3: Fix CSS Border Violations (12 instances)

Replace CSS `border` on rounded elements with the `smooth-border` class or `box-shadow: inset` pattern. Per CLAUDE.md rules.

**Violations to fix:**
1. `StatusChip.vue:114` — `.status-chip--stale` border
2. `StatusChip.vue:124` — `.health-indicator` border (50% radius)
3. `DashboardView.vue:584` — `.stat-icon-box` border (8px radius)
4. `ProductsView.vue:1112` — border on rounded element
5. `JobsTab.vue:1126` — active job indicator border
6. `JobsTab.vue:1324` — job border
7. `JobsTab.vue:1358` — job border
8. `AgentJobModal.vue:212` — rounded element border
9. `ProjectTabs.vue:845` — border on rounded element
10. `NavigationDrawer.vue:212` — rounded nav element
11. `ProjectsView.vue:1544` — border
12. `ProjectsView.vue:1585` — border

**Use** `smooth-border` class (1px), `smooth-border-2` (2px), or `smooth-border-accent` (brand yellow). For custom colors: `style="--smooth-border-color: <token>"`.

### Task 4: Fix Suspect !important Overrides (~15)

Replace hardcoded color `!important` overrides with token-based values:
- `DashboardView.vue:562-622` (8 instances with hardcoded hex)
- `SetupWizardOverlay.vue:682` (hardcoded `#8f97b7`)
- `SetupStep3Commands.vue:432-433` (hardcoded `#ffc300`)
- `SetupStep2Connect.vue:560-561` (hardcoded `#1e3147`)
- `ProductsView.vue:1159-1160` (hardcoded brand color)

Keep the `!important` if needed for Vuetify specificity, but replace the hardcoded color with a token.

### Task 5: Extract useFormatDate Composable

Create `frontend/src/composables/useFormatDate.js` with:
- `formatDate(dateString)` — returns localized date string
- `formatDateTime(dateString)` — returns localized date + time
- `formatDateCompact(dateString)` — returns compact format

Replace 11 implementations:
1. `components/ApiKeyManager.vue:238-241`
2. `components/UserManager.vue:445-448`
3. `components/org/MemberList.vue:101-103`
4. `components/products/ProductForm.vue:889-891`
5. `components/products/ProductDetailsDialog.vue:646-649`
6. `components/orchestration/CloseoutModal.vue:368-388`
7. `components/projects/ProjectReviewModal.vue:370-373`
8. `views/ProjectsView.vue:830,843`
9. `views/ProductsView.vue:573-576`
10. `views/ProductDetailView.vue:55`
11. `components/dashboard/RecentProjectsList.vue:52-56`

### Task 6: Remove Dead Code

- Delete `AgentExport.vue:152-158` (`generateToken` function — dead, uses old localStorage auth)
- Remove unused `statusIcon` computed from `StatusBadge.vue:66`
- Remove unused `getPhaseColor` from `JobsTab.vue:485`

---

## What NOT To Do

- Do NOT change component behavior or logic — only styling and formatting
- Do NOT modify test files — 0769b already stabilized them
- Do NOT restructure component files or extract new components
- Do NOT change Vuetify theme configuration — only use existing tokens or add to `design-tokens.scss`

---

## Acceptance Criteria

- [ ] `npx eslint frontend/src/ --max-warnings 8` passes (0 errors, <= 8 warnings)
- [ ] Zero hardcoded hex colors outside of `design-tokens.scss`, `variables.scss`, `agent-colors.scss` (grep verification)
- [ ] All 12 border violations fixed (smooth-border class or box-shadow)
- [ ] `useFormatDate` composable exists and replaces 11 implementations
- [ ] Dead code removed (generateToken, statusIcon, getPhaseColor)
- [ ] `npx vitest run` passes with 0 failures (tests from 0769b must still pass)
- [ ] `npm run build` succeeds

---

## Chain Execution Instructions

### Step 1: Read Chain Log
Read `prompts/0769_chain/chain_log.json`
- Check `orchestrator_directives`
- Review 0769c's `notes_for_next` for any backend changes that affect frontend

### Step 2: Mark Session Started
Update your session: `"status": "in_progress", "started_at": "<timestamp>"`

### Step 3: Execute Handover Tasks
Work through Tasks 1-6. Run ESLint after Task 1, then periodically during Task 2.

### Step 4: Update Chain Log
In `notes_for_next`, include:
- New tokens added to design-tokens.scss
- Any components where structure changed (border -> smooth-border class)
- useFormatDate composable path and exports

### Step 5: STOP
Do NOT spawn the next terminal. Commit chain log update and exit.
