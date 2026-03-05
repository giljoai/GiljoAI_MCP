# Handover 0765c: Design Token Migration

**Date:** 2026-03-02
**Priority:** MEDIUM
**Estimated effort:** 4-6 hours
**Branch:** `0760-perfect-score`
**Chain:** `prompts/0765_chain/chain_log.json` (session 0765c)
**Depends on:** 0765a (clean baseline), 0765b (CSS cleanup done first)
**Blocks:** None

---

## Objective

Migrate 108 hardcoded hex colors across 20 Vue files to use the existing design token infrastructure. The token system already exists (`design-tokens.scss`, `theme.js`, `agent-colors.scss`) — this is a migration task, not a greenfield design effort.

**Score impact:** ~9.1 -> ~9.2

---

## Pre-Conditions

1. 0765a and 0765b complete — orphan CSS already cleaned in 0765b
2. Existing design token infrastructure identified:
   - `frontend/src/styles/design-tokens.scss` — SCSS variables
   - `frontend/src/plugins/theme.js` — Vuetify theme configuration
   - `frontend/src/styles/agent-colors.scss` — Agent status colors
3. Read `prompts/0765_chain/chain_log.json` for predecessor notes

---

## Phase 1: Audit and Classify (~90 min)

### 1.1 Map All 108 Hardcoded Colors

Run this search across all Vue files:
```
grep -rn '#[0-9a-fA-F]\{3,8\}' frontend/src/ --include='*.vue'
```

For each match, record:
- File and line number
- The hex value
- Semantic meaning (what does this color represent?)
- Category: `primary`, `secondary`, `status`, `agent`, `decorative`, `background`, `text`, `border`

### 1.2 Group by Semantic Meaning

Expected categories based on research:

| Category | Expected Count | Examples |
|----------|---------------|---------|
| Agent status colors | ~15 | working=green, blocked=orange, silent=grey |
| UI state colors | ~20 | success, warning, error, info |
| Background/surface | ~25 | card backgrounds, section fills |
| Text/foreground | ~15 | headings, body, muted text |
| Border/divider | ~10 | separators, outlines |
| Decorative/brand | ~23 | gradients, accents, charts |

### 1.3 Map to Existing Tokens

For each color, determine:
1. Does an equivalent Vuetify theme token already exist? (e.g., `primary`, `secondary`, `error`, `success`)
2. Does `design-tokens.scss` already define it?
3. Does `agent-colors.scss` already define it?
4. Is a NEW custom token needed?

**Goal:** Minimize new tokens. Most hardcoded colors should map to existing Vuetify theme variables.

---

## Phase 2: Extend Token Infrastructure (~60 min)

### 2.1 Add Missing Custom Tokens

For colors that don't map to existing Vuetify tokens, add them to the theme system:

**File:** `frontend/src/plugins/theme.js`
- Add custom color tokens under the Vuetify `themes.light.colors` (and `dark` if dark mode exists)

**File:** `frontend/src/styles/design-tokens.scss`
- Add SCSS variables for any colors needed in non-Vuetify contexts (pure CSS)

### 2.2 Token Naming Convention

Follow the existing naming pattern in the codebase:
- Vuetify theme: camelCase (`surfaceVariant`, `statusWorking`)
- SCSS tokens: kebab-case with `$` prefix (`$surface-variant`, `$status-working`)
- CSS custom properties: kebab-case (`--v-theme-surface-variant`)

---

## Phase 3: Migration (~120 min)

### 3.1 Replacement Patterns

| Context | Hardcoded | Replacement |
|---------|-----------|-------------|
| Vuetify component props | `color="#4CAF50"` | `color="success"` |
| Inline styles | `style="color: #333"` | `style="color: rgb(var(--v-theme-on-surface))"` |
| CSS/SCSS blocks | `color: #666;` | `color: rgb(var(--v-theme-on-surface-variant));` |
| `<style>` sections | `background: #f5f5f5;` | `background: rgb(var(--v-theme-surface-variant));` |
| Template bindings | `:style="{ color: '#ff0000' }"` | `:style="{ color: 'rgb(var(--v-theme-error))' }"` |

### 3.2 File-by-File Migration

Process the 20 highest-impact files first. The research identified `JobsTab.vue` as having 26 hardcoded colors (most of any file).

**Priority order** (by hardcoded color count):
1. `JobsTab.vue` (~26 colors)
2. `ProjectTabs.vue`
3. `AgentTableView.vue`
4. `StatusBoard/` components
5. Remaining files

### 3.3 Agent Status Colors

The `agent-colors.scss` file already defines agent status colors. Ensure all agent-related color references use these:
- `working` -> green
- `blocked` -> orange/amber
- `silent` -> grey
- `waiting` -> blue
- `complete` -> teal
- `decommissioned` -> dark grey

---

## Phase 4: Verification (~30 min)

### 4.1 Visual Regression Check

After migration, visually verify key views:
- [ ] Projects list view — cards, status badges
- [ ] Project detail — tabs, agent table, jobs pane
- [ ] Status board — all agent states display correctly
- [ ] Settings views — forms, buttons

### 4.2 Grep Verification

Run the hardcoded color grep again. Target: reduce from 108 to under 10 (some colors in SVG paths or third-party integrations may be legitimate).

### 4.3 Build Verification

- `npm run build` — clean compilation
- No SCSS compilation warnings about undefined variables

---

## Cascading Impact Analysis

- **No backend impact** — purely frontend changes
- **No test changes** — unless tests assert specific hex color values (unlikely but check)
- **Dark mode:** If the app supports dark mode, token values will automatically adapt. Hardcoded hex values do NOT adapt — this migration improves dark mode support.
- **Installation:** No `install.py` changes needed

---

## Success Criteria

- [ ] All 108 hardcoded colors audited and classified
- [ ] Custom tokens added to theme system where needed
- [ ] Hardcoded hex colors reduced from 108 to <10
- [ ] Visual appearance unchanged (no color shifts)
- [ ] Frontend builds clean
- [ ] Chain log updated: 0765c = `complete`

---

## Completion Protocol

1. Frontend build clean
2. Update chain log
3. Write completion summary (max 400 words)
4. Commit: `cleanup(0765c): Migrate 108 hardcoded colors to design tokens`
