# Handover 0950e: Frontend: Hardcoded Hex Color Sweep

**Date:** 2026-04-05
**From Agent:** Planning Session (0950 Pre-Release Quality Sprint)
**To Agent:** Next Session (ux-designer or frontend-tester profile)
**Priority:** Medium
**Estimated Complexity:** 2-3 hours
**Status:** Not Started
**Edition Scope:** CE
**Series:** 0950e of 0950 chain — read `prompts/0950_chain/chain_log.json` first
**Depends On:** 0950d must be complete

---

## 1. Task Summary

Replace all hardcoded hex color values in Vue components and JS files with the correct
design token — CSS custom property, SCSS variable, or utility function. Token definition
files (`design-tokens.scss`, `agentColors.js`, `colorUtils.js`) are explicitly exempted.
The end state: any color used in component code traces back to a named token; no magic
hex strings scattered across the codebase.

---

## 2. Context and Background

The design token system was established in the 0873 style centralization sprint.
Tokens live in:

- `frontend/src/styles/design-tokens.scss` — all SCSS variables (`$color-*`,
  `$elevation-*`, `$gradient-*`, `$border-radius-*`, etc.)
- `frontend/src/styles/main.scss` — CSS custom properties in `:root` (`--text-muted`,
  `--text-secondary`, `--color-bg-primary`, etc.) and utility classes
- `frontend/src/config/agentColors.js` — agent role hex values + `getAgentColor()`
- `frontend/src/utils/colorUtils.js` — `hexToRgba()` for inline tinted badge styles
- `frontend/src/styles/agent-colors.scss` — `var(--agent-*-primary)` CSS variables

Despite the 0873 sweep, hardcoded hex values likely remain in components that were
added or modified after the sweep, or in corner cases that the sweep missed. This
session finds and fixes them all.

**Important:** "Hardcoded hex" means a hex literal like `#12202e`, `#FFC300`, or
`rgba(18, 32, 46, 0.5)` used directly in a component's `<style>` block, inline
`style=""` attribute, or JavaScript logic — not in a token definition file.

---

## 3. Chain Execution Instructions (Orchestrator-Gated v3)

You are a session in the 0950 chain on branch `feature/0950-pre-release-quality`.

### Step 1: Read Chain Log and Directives
Read `/media/patrik/Work/GiljoAI_MCP/prompts/0950_chain/chain_log.json`.
- Check `orchestrator_directives` in your session entry (0950e). If it contains "STOP",
  halt immediately.
- Read 0950d's `notes_for_next` — it lists which `.vue` files were edited by 0950d.
  Those files are the highest priority since 0950d may have introduced new template
  elements without using token classes.

### Step 2: Verify Prerequisite
Confirm 0950d status is `"complete"` in the chain log. If not, STOP and report.

### Step 3: Mark Session Started
Update your entry in the chain log:
```json
"status": "in_progress"
```

### Step 4: Execute (see Section 5 below)

### Step 5: Update Chain Log Before Stopping
Fill in `tasks_completed`, `deviations`, `notes_for_next` (for 0950k — list any
components that are large or have complex style sections so the god-component split
session has context), `summary`, `status: "complete"`.

### Step 6: Commit and STOP
```bash
git add -A
git commit -m "cleanup(0950e): hex color sweep — replace hardcoded values with design tokens"
git add prompts/0950_chain/chain_log.json
git commit -m "docs: 0950e chain log — session complete"
```

Do NOT spawn the next terminal. The orchestrator handles that.

---

## 4. Critical Agent Rules (Read Before Touching Any File)

- **Before deleting ANY code:** verify zero upstream/downstream references using grep.
  A hex value in an inline style may be computed dynamically in the script section.
- **Tests that fail must be fixed or deleted — never skip.**
- **No commented-out code.** If you encounter existing commented-out blocks while
  editing a file, delete them.
- **Read `frontend/design-system-sample-v2.html`** as the authoritative UI/brand
  reference before resolving any color ambiguity.
- **Visual appearance must not change.** Every token you substitute must produce the
  same rendered color as the hex it replaces. If the token does not exist, add it to
  `design-tokens.scss` with a semantic name before using it.
- Commit with prefix `cleanup(0950e):` on all commits.

---

## 5. Implementation Plan

### Phase 1: Build the Violation List

```bash
grep -rn "#[0-9a-fA-F]\{3,8\}\b" \
  /media/patrik/Work/GiljoAI_MCP/frontend/src/ \
  --include="*.vue" --include="*.js"
```

This will produce a large list. Filter it down immediately.

### Phase 2: Apply the Exemption Filter

Remove from your working list all matches that fall into these categories:

| Exemption | Rationale |
|---|---|
| `frontend/src/styles/design-tokens.scss` | Token definitions — intentional hex |
| `frontend/src/styles/main.scss` | `:root` CSS variable definitions — intentional hex |
| `frontend/src/styles/variables.scss` | SCSS variable definitions — intentional hex |
| `frontend/src/styles/agent-colors.scss` | Agent CSS variable definitions |
| `frontend/src/config/agentColors.js` | Agent hex definitions (`AGENT_COLORS` map) |
| `frontend/src/utils/colorUtils.js` | Color utility functions |
| Lines that are pure comments | `// was #123456` or `/* old value */` |
| CSS custom property definitions | `--my-token: #hex` inside a `:root` or component `:root` block |
| Test files in `frontend/tests/` | Test fixtures may use literal hex for assertions |

Everything that remains after this filter is a genuine violation.

### Phase 3: Replace Each Violation

Use the lookup table below. If a hex is not listed, find the matching token in
`design-tokens.scss` or `main.scss` by value, or add a new token.

#### Background and Surface Colors

| Hex | Replace With | Context |
|---|---|---|
| `#0e1c2d` | `$color-background-primary` or `var(--color-bg-primary)` | Darkest navy background |
| `#12202e` | `$elevation-raised` or `rgb(var(--v-theme-surface))` | Card / panel surface |
| `#1e3147` | `$elevation-elevated` or `var(--color-bg-elevated)` | Modal background |
| `#243b53` | `$elevation-overlay` | Popovers, overlays |
| `rgba(14, 28, 45, ...)` | `$color-background-secondary` | Translucent containers |
| `rgba(20, 35, 50, ...)` | `$color-background-tertiary` | Panel content bg |

#### Text Colors

| Hex | Replace With | Context |
|---|---|---|
| `#8895a8` | `var(--text-muted)` or `.text-muted-a11y` class | Muted text, labels |
| `#a3aac4` | `var(--text-secondary)` or `.text-secondary-a11y` class | Secondary text |
| `#e1e1e1` | `$color-text-primary` | Main body text |
| `#9e9e9e` | `$color-text-muted` | Disabled/muted (design-token) |

#### Accent and Brand Colors

| Hex | Replace With | Context |
|---|---|---|
| `#ffc300` | `$color-brand-yellow` or `var(--color-accent-primary)` | Brand yellow |
| `#ffd93d` | `$gradient-brand-start` | Brand gradient start |
| `#6bcf7f` | `$gradient-brand-end` | Brand gradient end |
| `#c6298c` | `$color-accent-danger` or `var(--color-accent-danger)` | Danger/magenta |
| `#67bd6d` | `$color-accent-success` or `var(--color-accent-success)` | Success green |
| `#8b5cf6` | `$color-accent-special` or `var(--color-accent-special)` | Purple special |

#### Agent Colors

| Hex | Replace With | Context |
|---|---|---|
| `#D4B08A` | `getAgentColor('orchestrator').hex` or `var(--agent-orchestrator-primary)` | Orchestrator |
| `#E07872` | `getAgentColor('analyzer').hex` or `var(--agent-analyzer-primary)` | Analyzer |
| `#6DB3E4` | `getAgentColor('implementer').hex` or `var(--agent-implementer-primary)` | Implementer |
| `#5EC48E` | `getAgentColor('documenter').hex` or `var(--agent-documenter-primary)` | Documenter |
| `#AC80CC` | `getAgentColor('reviewer').hex` or `var(--agent-reviewer-primary)` | Reviewer |
| `#EDBA4A` | `getAgentColor('tester').hex` or `var(--agent-tester-primary)` | Tester |

For **inline tinted badge styles** that compute `rgba(agentColor, 0.15)`:
use `hexToRgba()` from `@/utils/colorUtils` — never hardcode the rgba value.

#### Border and Structural Colors

| Hex / rgba | Replace With | Context |
|---|---|---|
| `rgba(255, 255, 255, 0.10)` | `var(--border-subtle)` or `.smooth-border` class | Default smooth border |
| `rgba(255, 255, 255, 0.20)` | `$color-container-border` | Container border |
| `#315074` | `$color-scrollbar-thumb-background` | Scrollbar thumb |

#### Status Colors (use these exact tokens — no custom values)

| Hex | Replace With | Status |
|---|---|---|
| `#ffd700` | `$color-status-waiting` | Waiting |
| `#67bd6d` | `$color-status-complete` | Complete |
| `#ff9800` | `$color-status-blocked` | Blocked |
| `#c6298c` | `$color-status-failed` | Failed |

### Phase 4: Add Missing Tokens

If a genuine violation uses a color that does not match any existing token:

1. Open `frontend/src/styles/design-tokens.scss`.
2. Find the appropriate section (backgrounds, borders, text, status, etc.).
3. Add a new SCSS variable with a semantic name:
   ```scss
   $color-surface-input: #1a2d40;  // Text input field background
   ```
4. Use the new variable in the component.
5. Add a brief comment explaining the semantic meaning if it is not obvious from the name.

Do NOT create tokens named after their hex value (e.g., `$color-1a2d40` is wrong).
Name them after their role (e.g., `$color-surface-input`).

### Phase 5: Verify

```bash
# Spot-check: few remaining hits should all be in exempted files
grep -rn "#[0-9a-fA-F]\{3,8\}\b" \
  /media/patrik/Work/GiljoAI_MCP/frontend/src/ \
  --include="*.vue" --include="*.js" | \
  grep -v "design-tokens\|main.scss\|variables.scss\|agent-colors\|agentColors\|colorUtils\|tests/"

# Must be clean (output empty, or only exempted files)

# Run tests
cd /media/patrik/Work/GiljoAI_MCP/frontend && npx vitest run

# Build must succeed with no regressions
cd /media/patrik/Work/GiljoAI_MCP/frontend && npm run build
```

---

## 6. Files in Scope

All `.vue` and `.js` files in `frontend/src/` — except the explicitly exempted token
definition files listed in Section 5 Phase 2.

Files most likely to have violations (from historical patterns):
- Any file edited by 0950d (check 0950d `notes_for_next` in chain log)
- `frontend/src/components/projects/LaunchTab.vue` (complex styles)
- `frontend/src/components/orchestration/AgentTableView.vue`
- `frontend/src/views/ProjectsView.vue`
- `frontend/src/views/ProductDetailView.vue`
- `frontend/src/components/messages/MessageItem.vue`
- `frontend/src/components/navigation/AppBar.vue`

---

## 7. Testing Requirements

- `npm run build` completes successfully — no SCSS variable resolution errors
- `npx vitest run` — all tests pass, no new failures
- Grep output for inline hex in `.vue`/`.js` files (post-exemption filter) returns zero
- Visual spot-check: agent badges, dialog headers, status chips, muted text all render
  with correct colors — no obvious color regressions

---

## 8. Success Criteria

- Zero inline hardcoded hex literals in Vue component `<style>` blocks and `<template>`
  inline styles (outside exempted token definition files)
- Zero hardcoded hex literals in `.js` files outside `agentColors.js` and `colorUtils.js`
- Any color not covered by existing tokens has been added to `design-tokens.scss` with
  a semantic name
- `npm run build` clean
- All Vitest tests pass
- Visual appearance unchanged

---

## 9. Rollback Plan

All changes are mechanical token substitutions. Git revert is safe:
```bash
git revert HEAD
```
If a newly added `design-tokens.scss` variable causes an SCSS build error, revert
the token addition and use the inline hex temporarily until the naming is resolved.
No schema changes, no new runtime dependencies.

---

## 10. Additional Resources

- `frontend/src/styles/design-tokens.scss` — canonical SCSS variable definitions
- `frontend/src/styles/main.scss` — `:root` CSS custom properties and utility classes
- `frontend/src/config/agentColors.js` — `getAgentColor()` function and `AGENT_COLORS` map
- `frontend/src/utils/colorUtils.js` — `hexToRgba()` utility
- `frontend/src/styles/agent-colors.scss` — `var(--agent-*-primary)` CSS variables
- `frontend/design-system-sample-v2.html` — authoritative UI/brand reference (open in browser)
- `CLAUDE.md` — agent color palette section and smooth-border convention
- `prompts/0950_chain/chain_log.json` — orchestrator directives and 0950d notes

---

## Progress Updates

*(Agent updates this section during execution)*
