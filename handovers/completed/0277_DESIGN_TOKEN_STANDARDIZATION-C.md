# Handover 0277: Design Token Standardization — Radius & Shadow Consolidation

**Date:** 2026-03-30
**From Agent:** Claude Opus 4.6 orchestrator
**To Agent:** Next session
**Priority:** Medium
**Estimated Complexity:** 1 session, ~1-2 hours
**Status:** Not Started
**Edition Scope:** CE

---

## Task Summary

Consolidate three competing border-radius systems and two competing shadow systems into a single canonical set in `design-tokens.scss`. Remove the duplicate definitions from `variables.scss`. Total scope: ~15 file edits, zero behavior change — pure token renaming.

**Why now:** The design system HTML reference (`frontend/design-system-sample.html`) documents both systems side-by-side as a known discrepancy. The 0769d sprint standardized colors but left radius and shadows untouched. Cleaning this up before CE launch prevents future agents from picking the wrong token.

---

## Current State (The Problem)

### Border Radius — 3 competing token sets

**Set 1: `variables.scss` (lines 24-28) — Tailwind-style sizing**
```scss
$radius-sm: 4px;    // 2 uses (main.scss:48)
$radius-md: 8px;    // 2 uses (DashboardView.vue:571, :585)
$radius-lg: 12px;   // 3 uses (DashboardView.vue:566, :617, :626)
$radius-xl: 16px;   // 0 uses
$radius-full: 9999px; // 0 uses
```

**Set 2: `design-tokens.scss` (lines 159-162) — Semantic naming**
```scss
$border-radius-sharp: 4px;     // 4 uses (via aliases)
$border-radius-default: 8px;   // 4 uses (via aliases)
$border-radius-rounded: 16px;  // 4 uses (via aliases)
$border-radius-pill: 9999px;   // 4 uses (LaunchTab.vue:552)
```

**Set 3: `design-tokens.scss` (lines 165-179) — Aliases mapping to Set 2**
```scss
$radius-container, $radius-panel-content, $radius-small, $radius-medium,
$radius-large, $radius-pill, $radius-scrollbar
```

### Shadows — 2 competing systems

**Set 1: `variables.scss` (lines 31-34) — Tailwind-style box-shadows**
```scss
$shadow-sm: 0 1px 2px 0 rgba(0,0,0,0.05);   // 0 uses
$shadow-md: 0 4px 6px -1px rgba(0,0,0,0.1);  // 0 uses
$shadow-lg: 0 10px 15px -3px rgba(0,0,0,0.1); // 1 use (main.scss:129)
$shadow-xl: 0 20px 25px -5px rgba(0,0,0,0.1); // 0 uses
```

**Set 2: `design-tokens.scss` (lines 198-201) — Surface elevation colors**
```scss
$elevation-flat: #0e1c2d;     // 0 direct uses
$elevation-raised: #182739;   // 6 uses
$elevation-elevated: #1e3147; // 8 uses
$elevation-overlay: #243b53;  // 1 use
```

Note: `$elevation-*` are background colors, not box-shadows. They solve a different problem. Both should exist, but `$shadow-*` from variables.scss should move to design-tokens.scss.

---

## Target State (The Solution)

### Single canonical file: `design-tokens.scss`

**Border radius — keep semantic naming (Set 2), remove Set 1 and Set 3 aliases:**
```scss
// Border Radius (canonical — DO NOT add duplicates to variables.scss)
$border-radius-sharp: 4px;     // Tight corners, scrollbars, inputs
$border-radius-default: 8px;   // Panels, buttons, standard elements
$border-radius-rounded: 16px;  // Cards, containers
$border-radius-pill: 9999px;   // Pills, tags, chips
```

**Shadows — move from variables.scss to design-tokens.scss with semantic names:**
```scss
// Box Shadows (canonical — use alongside $elevation-* surface colors)
$shadow-subtle: 0 1px 2px 0 rgba(0,0,0,0.05);
$shadow-default: 0 4px 6px -1px rgba(0,0,0,0.1);
$shadow-strong: 0 10px 15px -3px rgba(0,0,0,0.1);
$shadow-dramatic: 0 20px 25px -5px rgba(0,0,0,0.1);
```

### Mapping table for find-and-replace

| Old Token | New Token | Value |
|-----------|-----------|-------|
| `$radius-sm` | `$border-radius-sharp` | 4px |
| `$radius-md` | `$border-radius-default` | 8px |
| `$radius-lg` | `$border-radius-rounded` | 16px → **NOTE: was 12px, now 16px — verify visual** |
| `$radius-xl` | `$border-radius-rounded` | 16px (same value) |
| `$radius-full` | `$border-radius-pill` | 9999px |
| `$radius-small` | `$border-radius-sharp` | 4px (alias removed) |
| `$radius-medium` | `$border-radius-default` | 8px (alias removed) |
| `$radius-large` | `$border-radius-rounded` | 16px (alias removed) |
| `$radius-container` | `$border-radius-rounded` | 16px (alias removed) |
| `$radius-panel-content` | `$border-radius-default` | 8px (alias removed) |
| `$radius-scrollbar` | `$border-radius-sharp` | 4px (alias removed) |
| `$radius-pill` | `$border-radius-pill` | 9999px (alias removed) |
| `$shadow-sm` | `$shadow-subtle` | (same value) |
| `$shadow-md` | `$shadow-default` | (same value) |
| `$shadow-lg` | `$shadow-strong` | (same value) |
| `$shadow-xl` | `$shadow-dramatic` | (same value) |

---

## Scope — Files to Modify

### Source Files (~10 files)

| File | Changes |
|------|---------|
| `frontend/src/styles/variables.scss` | Remove `$radius-sm/md/lg/xl/full` and `$shadow-sm/md/lg/xl` definitions (lines 24-34) |
| `frontend/src/styles/design-tokens.scss` | Remove alias block (lines 165-179). Add `$shadow-*` semantic tokens. Add comment: "canonical — DO NOT duplicate in variables.scss" |
| `frontend/src/styles/main.scss:48` | `$radius-sm` → `$border-radius-sharp` |
| `frontend/src/styles/main.scss:129` | `$shadow-lg` → `$shadow-strong` |
| `frontend/src/views/DashboardView.vue:566` | `$radius-lg` → `$border-radius-rounded` (was 12px, now 16px — verify visual) |
| `frontend/src/views/DashboardView.vue:571` | `$radius-md` → `$border-radius-default` |
| `frontend/src/views/DashboardView.vue:585` | `$radius-md` → `$border-radius-default` |
| `frontend/src/views/DashboardView.vue:617` | `$radius-lg` → `$border-radius-rounded` |
| `frontend/src/views/DashboardView.vue:626` | `$radius-lg` → `$border-radius-rounded` |
| `frontend/src/components/projects/LaunchTab.vue:465` | `$radius-medium` → `$border-radius-default` |
| `frontend/src/components/projects/LaunchTab.vue:481,486` | `$radius-scrollbar` → `$border-radius-sharp` |

### Documentation (~1 file)

| File | Changes |
|------|---------|
| `frontend/design-system-sample.html` | Update "Spacing & Elevation" section to show single canonical token set. Remove duplicate radius/shadow comparison table. |

---

## Implementation Steps

1. **Read the current files** — verify line numbers haven't shifted since this handover was written
2. **Add shadow tokens to design-tokens.scss** — `$shadow-subtle/default/strong/dramatic`
3. **Remove aliases from design-tokens.scss** — lines 165-179 (the `$radius-container` etc. block)
4. **Find and replace** — update all 10 source file references per mapping table
5. **Remove old definitions from variables.scss** — lines 24-34
6. **Run verification:**
   - `cd frontend && npm run build` (must succeed — SCSS compilation catches undefined tokens)
   - `cd frontend && npx vitest run` (must stay at 1,893 pass / 0 fail)
   - `cd frontend && npx eslint src/ --max-warnings 8` (must stay under budget)
7. **Visual check** — `$radius-lg` was 12px, `$border-radius-rounded` is 16px. DashboardView stat boxes will have slightly rounder corners. Open the dashboard in browser and verify it looks intentional, not broken. If 16px is too round for those elements, create `$border-radius-soft: 12px` as a new semantic token.
8. **Update design-system-sample.html** — show unified token table

---

## Agent Protocols (MANDATORY)

### Rejection Authority
If you find that `$radius-lg` (12px) vs `$border-radius-rounded` (16px) creates a visible regression on the dashboard stat boxes, do NOT force the mapping. Instead, create a new `$border-radius-soft: 12px` token for that specific visual need and document why.

### Flow Investigation
Before replacing any token, verify the component renders correctly with the new value. The `npm run build` check catches undefined tokens but NOT visual regressions. Open the app and check DashboardView after the change.

---

## What NOT To Do

- Do NOT change `$elevation-*` tokens — they are surface colors, not shadows, and are correct as-is
- Do NOT rename `$border-radius-*` tokens — they are the canonical names, keep them
- Do NOT modify any component logic — this is a pure styling token rename
- Do NOT change any token values (except the `$radius-lg` 12px→16px mapping — flag if visual issue)
- Do NOT touch backend code

---

## Acceptance Criteria

- [ ] `variables.scss` has zero radius or shadow token definitions (moved to design-tokens.scss)
- [ ] `design-tokens.scss` is the single source of truth for radius and shadow tokens
- [ ] Zero alias/redirect tokens remain (no `$radius-small` pointing to `$border-radius-sharp`)
- [ ] All 10 source files updated with canonical token names
- [ ] `npm run build` succeeds
- [ ] `npx vitest run` — 1,893 pass / 0 fail
- [ ] `design-system-sample.html` updated to show unified system
- [ ] Dashboard stat boxes visually verified (12px→16px radius change)
