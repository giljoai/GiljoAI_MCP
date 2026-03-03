# Handover 0765m: Design System Sample Page

**Date:** 2026-03-03
**Priority:** MEDIUM
**Estimated effort:** 1.5-2 hours
**Branch:** `0760-perfect-score`
**Chain:** `prompts/0765_chain/chain_log.json` (session 0765m)
**Depends on:** None (runs in parallel with 0765l)

---

## Objective

Build a standalone HTML sample page that maps the current Vue/Vuetify frontend design system to a visual reference. The user wants to see their actual theme rendered as a static page they can open in a browser to verify colors, spacing, typography, and component styles.

This is a READ + BUILD task — read the frontend config, extract the design system, and generate a sample HTML file.

---

## Pre-Conditions

1. Read the branding guide: `docs/guides/BRANDING_GUIDE.md`
2. Note: The product uses DARK THEME ONLY (light theme was removed)

---

## Phase 1: Research the Frontend Design System (~45 min)

Read these files to extract the actual design tokens, theme config, and component patterns:

### Vuetify Theme Config
- `frontend/src/plugins/vuetify.js` (or wherever Vuetify is configured) — extract theme colors (primary, secondary, accent, error, success, warning, info, background, surface)

### CSS/SCSS Design Tokens
- `frontend/src/styles/main.scss` — global styles, CSS custom properties
- `frontend/src/styles/design-tokens.scss` — design token definitions
- `frontend/src/styles/agent-colors.scss` — agent role color system

### JavaScript Color Config
- `frontend/src/config/agentColors.js` — agent color map
- `frontend/src/config/constants.js` — any color/style constants

### Component Patterns (sample 3-4 key components)
- `frontend/src/components/projects/ProjectTabs.vue` — main layout/tabs
- `frontend/src/components/projects/JobsTab.vue` — agent job cards
- `frontend/src/components/projects/AgentJobModal.vue` — modal dialog
- `frontend/src/App.vue` — app shell, navigation

### Branding Guide
- `docs/guides/BRANDING_GUIDE.md` — canonical color definitions

---

## Phase 2: Build the Sample HTML (~45 min)

Create a single self-contained HTML file at `frontend/design-system-sample.html` that shows:

### Layout Layers
1. **Background** — the outermost page background color
2. **Layer 1: Card/Panel** — a content card sitting on the background (elevated surface)
3. **Layer 2: Nested Card** — a card within a card (if the design uses this)
4. **Frame/Border** — border treatment on cards and containers

### Interactive Elements
5. **Button Primary** — main action button (with hover state)
6. **Button Secondary** — secondary action button
7. **Button Danger** — destructive action button
8. **Text Input** — form field with label, placeholder, and focus state
9. **Chip/Badge** — status badges (waiting, working, complete, blocked)

### Agent Role Colors
10. **Agent Color Swatches** — one swatch per agent role from the branding guide, showing:
    - Role name
    - Primary color hex
    - Dark variant
    - Light variant
    - A sample chip as it appears in the UI

### Status Colors
11. **Status Badge Row** — each status (waiting, working, complete, failure, blocked) rendered as it appears in the product

### Typography
12. **Heading hierarchy** — h1 through h4 with the actual font family and weights
13. **Body text** — paragraph text at standard size
14. **Monospace/code** — code snippets

### Spacing & Elevation
15. **Spacing scale** — show the spacing tokens (if defined) as visual boxes
16. **Elevation/shadow** — cards at different elevation levels

### Requirements for the HTML file:
- **Self-contained** — all CSS inline or in `<style>` tags, NO external dependencies
- **Dark theme only** — use the dark theme colors from Vuetify config
- **Annotated** — each element should show its CSS custom property name or hex value as a label
- **Responsive** — should look decent at 800px-1400px width
- **Accurate** — colors MUST match what the Vue app actually renders. Read the actual values from the config files, don't guess.

---

## Phase 3: Cross-Reference with Branding Guide (~15 min)

After building the sample, compare it against `docs/guides/BRANDING_GUIDE.md`:

1. Do the agent role colors in the sample match the branding guide?
2. Do the status badge colors match?
3. Are there any discrepancies between what's in the Vue config vs the branding guide?

Add a "Discrepancies" section at the bottom of the HTML page listing any mismatches found, with:
- What the branding guide says
- What the Vue config actually has
- Which file the Vue value comes from

---

## Cascading Impact Analysis

- **READ-ONLY research** on the frontend codebase
- **One new file created** — `frontend/design-system-sample.html`
- **Zero modifications** to any existing code

---

## Testing Requirements

- Open `frontend/design-system-sample.html` in a browser — verify it renders correctly
- No test suite impact (this is a standalone reference file)

---

## Success Criteria

- [ ] All Vuetify theme tokens extracted and rendered
- [ ] All agent role colors from branding guide shown as swatches
- [ ] All status badge colors shown
- [ ] Layout layers demonstrated (background, card, nested card, borders)
- [ ] Interactive elements shown (buttons, inputs, chips)
- [ ] Typography hierarchy shown
- [ ] Discrepancies section documents any branding guide vs actual config mismatches
- [ ] HTML is self-contained, dark theme, annotated with token names
- [ ] File saved to `frontend/design-system-sample.html`

---

## Completion Protocol

1. Save HTML file to `frontend/design-system-sample.html`
2. Update chain log: set 0765m to `complete`
3. Commit: `docs(0765m): Add design system sample page`
4. Report to user: file location, any discrepancies found
5. Do NOT spawn another terminal
