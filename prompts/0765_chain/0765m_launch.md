# Terminal Session: 0765m - Design System Sample Page

## Mission
Execute Handover 0765m — research the frontend design system and build a visual reference HTML page.
Branch: `0760-perfect-score`

## READ THESE FILES FIRST (in order)
1. `F:\GiljoAI_MCP\handovers\0765m_design_system_sample.md` — Your full task specification
2. `F:\GiljoAI_MCP\docs\guides\BRANDING_GUIDE.md` — Canonical color definitions
3. NOTE: The product uses DARK THEME ONLY (light theme was removed)

## CRITICAL: Protocol Requirements

### This is a READ + BUILD task
- Read the frontend config files to extract actual design tokens
- Build a self-contained HTML sample page
- Do NOT modify any existing files
- The HTML must use the ACTUAL values from the Vue config, not guesses
- No AI signatures in code or commits

### Use Subagents to Preserve Context Budget
**Use the Task tool to spawn subagents.**

| Task | Subagent Type | What to Delegate |
|------|---------------|-----------------|
| Research Vuetify theme | `deep-researcher` | Extract all theme colors from vuetify config, main.scss, design-tokens.scss |
| Research component patterns | `deep-researcher` | Extract button styles, card styles, typography from key Vue components |
| Build HTML page | `ux-designer` | Generate the self-contained sample HTML with all design tokens |

### Communication via Chain Log
1. **On start:** Set 0765m to `in_progress`
2. **On complete:** Set 0765m to `complete`, note any branding guide discrepancies

### Files to Research
- `frontend/src/plugins/vuetify.js` — Vuetify theme config
- `frontend/src/styles/main.scss` — global styles
- `frontend/src/styles/design-tokens.scss` — design tokens
- `frontend/src/styles/agent-colors.scss` — agent colors
- `frontend/src/config/agentColors.js` — JS color map
- `frontend/src/config/constants.js` — style constants
- `frontend/src/App.vue` — app shell
- `docs/guides/BRANDING_GUIDE.md` — branding reference

## When Done
1. Save HTML to `frontend/design-system-sample.html`
2. Update chain log (status=complete, summary with any discrepancies found)
3. Commit: `docs(0765m): Add design system sample page`
4. Report file location + discrepancies to user
5. Do NOT spawn another terminal
