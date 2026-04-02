# Styling Tokenization Audit

Date: 2026-04-02

Scope:
- Frontend audit of `frontend/src`
- Reference design reviewed from `frontend/design-system-sample-v2.html`

## Executive Summary

The frontend is not in a catastrophic state, but it is not fully standardized either.

There is a real design-token foundation already in place:
- global theme in `frontend/src/config/theme.js`
- shared SCSS tokens in `frontend/src/styles/design-tokens.scss`
- global utilities in `frontend/src/styles/main.scss`
- reusable tinted primitives like `TintedChip.vue`, `TintedBadge.vue`, `StatusBadge.vue`, `RoleBadge.vue`

The problem is consistency and enforcement. Styling is split across:
- global tokens
- component-scoped SCSS
- Vuetify props
- inline static styles
- dynamic `:style` bindings
- hard-coded color/config constants

Result: the application is in a mixed state. The token system exists, but the implementation is only partially standardized.

Assessment:
- Overall maintainability state: `moderate styling debt`
- Inline styling contamination: `material`
- Token adoption: `good foundation, inconsistent execution`

## Key Metrics

From `frontend/src`:

- Vue components: `96`
- Files checked (`.vue`, `.js`, `.ts`): `146`
- Files with inline style usage: `42`
- Total inline style occurrences: `110`
- Static inline style occurrences: `50`
- Dynamic inline style occurrences: `60`
- Static inline custom-property uses (`style="--..."`): `18`
- Files with any `<style>` block: `85`
- Files with `<style scoped>`: `32`
- Files importing `design-tokens`: `69`

Interpretation:
- token usage is widespread
- inline styling is also widespread
- the app has drifted into a hybrid styling model rather than a standardized one

## What Is Healthy

These are positive signs and worth preserving:

- `frontend/src/styles/design-tokens.scss` is substantial and maps well to the design reference palette, spacing, borders, elevation, and transitions.
- `frontend/src/styles/main.scss` already provides shared utilities like muted text, smooth borders, scrollbars, and interactive icon behavior.
- `frontend/src/main.js` loads global SCSS centrally.
- Reusable token-aware UI primitives already exist:
  - `frontend/src/components/ui/TintedChip.vue`
  - `frontend/src/components/ui/TintedBadge.vue`
  - `frontend/src/components/StatusBadge.vue`
  - `frontend/src/components/common/RoleBadge.vue`
- Many larger components do import `design-tokens.scss`, which means the team has already started standardizing.

## Where Contamination Exists

### 1. Inline styling is common in view-layer templates

Representative hotspots:

| File | Inline occurrences | Notes |
| --- | ---: | --- |
| `frontend/src/views/DashboardView.vue` | 12 | dynamic micro-bars plus repeated inline CSS custom properties |
| `frontend/src/components/projects/ProjectReviewModal.vue` | 8 | mixed static and dynamic inline styles in modal content |
| `frontend/src/components/products/ProductDetailsDialog.vue` | 8 | summary chips and scroll container inline rules |
| `frontend/src/views/ProjectsView.vue` | 7 | badge/dot/status styling mixed into template |
| `frontend/src/components/common/AgentTipsDialog.vue` | 5 | hard-coded inline background colors |
| `frontend/src/views/WelcomeView.vue` | 5 | presentation-heavy inline customizations |

Examples:
- `frontend/src/views/DashboardView.vue:135`
- `frontend/src/views/DashboardView.vue:139`
- `frontend/src/views/DashboardView.vue:143`
- `frontend/src/views/ProjectsView.vue:15`
- `frontend/src/components/projects/ProjectReviewModal.vue:142`
- `frontend/src/components/products/ProductDetailsDialog.vue:394`

### 2. Dynamic style bindings are often used for presentational patterns that should be componentized

Some `:style` bindings are justified:
- progress bar widths
- runtime-selected colors
- computed badge/chip tinting
- size/position values driven by data

But many current usages are repeated presentational patterns that should be abstracted instead:
- colored dots
- tinted chips/badges
- agent badges
- status pills
- small flex/layout overrides
- repeated scroll container sizing

Examples:
- `frontend/src/components/projects/AddTypeModal.vue:47`
- `frontend/src/components/projects/AddTypeModal.vue:66`
- `frontend/src/components/projects/AddTypeModal.vue:77`
- `frontend/src/views/ProjectsView.vue:357`
- `frontend/src/views/ProjectsView.vue:363`
- `frontend/src/components/projects/ProjectReviewModal.vue:103`
- `frontend/src/components/projects/ProjectReviewModal.vue:127`

This is the main sign that the system lacks standardized template components for common UI motifs.

### 3. Hard-coded color use still leaks outside the token layer

High hard-coded color density remains outside the shared token files.

Largest offenders from the scan:

| File | Hard-coded color refs |
| --- | ---: |
| `frontend/src/views/WelcomeView.vue` | 44 |
| `frontend/src/config/theme.js` | 25 |
| `frontend/src/views/TasksView.vue` | 23 |
| `frontend/src/views/ProductsView.vue` | 17 |
| `frontend/src/utils/constants.js` | 17 |
| `frontend/src/components/projects/JobsTab.vue` | 17 |
| `frontend/src/views/DashboardView.vue` | 16 |
| `frontend/src/components/projects/MessageAuditModal.vue` | 15 |
| `frontend/src/views/ProjectsView.vue` | 14 |

Not all of this is equally bad:
- `config/theme.js` is expected to define theme values
- `config/agentColors.js` is expected to hold canonical agent colors

But `utils/constants.js` and several view components still carry color authority that should live closer to the design-token layer.

### 4. Component-scoped styles are heavy, which increases drift risk

There are `32` scoped-style files and `85` total style blocks in Vue SFCs.

Scoped styles are not inherently wrong, but at this volume they usually mean:
- each feature defines its own local variant of the same patterns
- shared template semantics are weak
- visual consistency depends on discipline rather than system constraints

This matches what is visible in the codebase: the same badge/chip/dot/card patterns are reimplemented in multiple places.

## Contamination Types

### Low concern

These inline styles are generally acceptable:

- width based on runtime percentage
- color driven by live data where CSS classes would explode combinatorially
- CSS custom property injection when used as a clean token hook
- icon/image dimensions in isolated cases

Examples:
- `frontend/src/views/DashboardView.vue:83`
- `frontend/src/views/DashboardView.vue:102`
- `frontend/src/views/DashboardView.vue:121`
- `frontend/src/components/ui/TintedChip.vue`
- `frontend/src/components/ui/TintedBadge.vue`

### Medium concern

These should usually move into reusable classes or components:

- `style="max-height: 60vh; overflow-y: auto;"`
- `style="flex:1"`
- `style="width: 16px; height: 16px;"`
- repeated dot/badge geometry objects
- repeated static colors directly in templates

Examples:
- `frontend/src/components/products/ProductDetailsDialog.vue:394`
- `frontend/src/components/products/ProductDetailsDialog.vue:427`
- `frontend/src/components/projects/ProjectReviewModal.vue:16`
- `frontend/src/components/projects/ProjectReviewModal.vue:82`
- `frontend/src/components/common/AgentTipsDialog.vue:101`

### High concern

These indicate missing standard components or styling rules:

- repeated ad hoc tinted badge construction rather than using `TintedBadge`/`TintedChip`
- repeated status dot / taxonomy dot objects inline
- repeated agent-badge style functions across modules
- color constants split between tokens, config, and utility modules

Examples:
- `frontend/src/views/ProjectsView.vue:127`
- `frontend/src/components/projects/ProjectReviewModal.vue:103`
- `frontend/src/components/projects/ProjectReviewModal.vue:127`
- `frontend/src/components/dashboard/RecentMemoriesList.vue:104`
- `frontend/src/components/messages/BroadcastPanel.vue:415`
- `frontend/src/components/messages/MessageItem.vue:150`

## Architectural Assessment

Current styling model:

1. Shared token layer exists.
2. Shared global utility layer exists.
3. Reusable display primitives exist.
4. Feature components still bypass those primitives frequently.

That means the codebase is not missing a design system. It is missing strict usage patterns.

The real maintenance problem is not just inline CSS. It is:
- duplicate presentation logic
- weak ownership of visual primitives
- multiple sources of truth for colors and status styling

## Alignment With Reference Design

The reference file `frontend/design-system-sample-v2.html` emphasizes:
- clear tokenized palette
- standardized cards
- standardized buttons
- standardized chips/badges
- standardized inputs
- standardized tables
- consistent elevation and border behavior

The current app aligns with that intent at the token level, but not consistently at the implementation level.

Gap summary:
- palette: mostly aligned
- elevation/borders: partially aligned
- chip/badge patterns: partially aligned, but duplicated
- table/list presentation: inconsistent
- layout spacing and micro-elements: inconsistent
- inline contamination: too high for long-term low-cost maintenance

## Recommended Remediation

### Phase 1: establish enforcement

- Declare `design-tokens.scss`, `theme.js`, and `agentColors.js` as the only color-authority layers.
- Ban new static inline styles except for narrowly approved cases.
- Add ESLint or custom lint checks for:
  - static `style="..."`
  - direct hex colors in templates
  - repeated `:style="{ width, height, borderRadius ... }"` dot/badge objects

### Phase 2: standardize primitive components

Create or normalize these primitives and require usage:

- `AppDot` for colored circular indicators
- `AppStatusDot` for status initials/dots
- `AppAgentBadge` for agent square badges
- `AppScrollPanel` for repeated max-height/overflow panels
- `AppMetricCard` for dashboard mini-stat cards
- `AppTaxonomyBadge` for project type/taxonomy rendering

This will eliminate a large share of current inline style objects.

### Phase 3: collapse duplicate style logic

Consolidate repeated logic currently scattered across:
- `ProjectsView.vue`
- `ProjectReviewModal.vue`
- `DashboardView.vue`
- `JobsTab.vue`
- `MessageItem.vue`
- `BroadcastPanel.vue`
- `RecentMemoriesList.vue`

Move repeated tint logic into shared helpers plus shared presentational components.

### Phase 4: reduce component-local color authority

Refactor color decisions so that:
- status colors come from one status token/config source
- agent colors come from one agent token/config source
- project taxonomy chips use one badge primitive
- ad hoc swatch definitions in utility files are either tokenized or explicitly marked as data-domain values

## Priority Targets

If only a few files are addressed first, start here:

1. `frontend/src/views/DashboardView.vue`
2. `frontend/src/views/ProjectsView.vue`
3. `frontend/src/components/projects/ProjectReviewModal.vue`
4. `frontend/src/components/products/ProductDetailsDialog.vue`
5. `frontend/src/components/projects/AddTypeModal.vue`
6. `frontend/src/components/common/AgentTipsDialog.vue`

These files give the biggest immediate reduction in inline contamination and duplicate presentation logic.

## Bottom Line

The application is not in a bad enough state to justify a full styling rewrite.

It is in a bad enough state to justify a focused standardization pass.

Recommended decision:
- do not rebuild the design system
- do enforce it
- remove static inline styling aggressively
- keep dynamic inline styling only where it is truly data-driven
- replace repeated visual patterns with a small set of reusable primitives

That approach should simplify maintenance substantially without destabilizing the app.
