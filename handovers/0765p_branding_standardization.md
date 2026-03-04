# Handover: 0765p — Branding Standardization

## Context
The design system sample page (`frontend/public/design-system-sample.html`) was built in 0765m as the **single source of truth** for all frontend design decisions. Several SCSS/CSS config files still diverge from it. Your job is to reconcile them.

## Source of Truth
`frontend/public/design-system-sample.html` — read this file first. It contains all approved colors, typography, spacing, elevation, and border radius values.

## Files to Fix

### 1. `frontend/src/styles/design-tokens.scss`
- **Agent colors**: Must match values in `frontend/src/config/agentColors.js` (canonical source)
- **Status colors**: Must match values in `frontend/src/config/statusConfig.js` (canonical: waiting=#FFD700, working=#FFFFFF, blocked=#FF9800, complete=#67BD6D, failure=#C6298C)
- **Font family**: Remove Cairo declaration, use `Roboto, sans-serif`
- **Primary text color**: Change `#e0e0e0` to `#e1e1e1`
- **Border radius scale**: Replace with unified 4-token scale: sharp=4px, default=8px, rounded=16px, pill=9999px
- **Shadow/elevation scale**: Replace invisible black shadows with surface lightening: Flat=#0e1c2d, Raised=#182739, Elevated=#1e3147, Overlay=#243b53

### 2. `frontend/src/styles/agent-colors.scss`
- **Status CSS vars**: Must match `statusConfig.js` values (see above)

### 3. Cross-reference check
After fixing, verify no Vue components use the OLD values directly. Search for any hardcoded references to the old token values that would break.

## Approach
1. Read the design system sample page to understand all approved values
2. Read `agentColors.js` and `statusConfig.js` as canonical JS sources
3. Read `design-tokens.scss` and `agent-colors.scss` current state
4. Make corrections to match the approved design system
5. Verify frontend builds clean after changes
6. Run `npm run build` to confirm no regressions

## What NOT to do
- Do NOT change any Vue component files — only SCSS/CSS config files
- Do NOT change `agentColors.js` or `statusConfig.js` — those are canonical
- Do NOT add or remove design tokens — only correct existing values
- Do NOT touch `variables.scss` Vuetify overrides unless they conflict with the unified radius/elevation scale

## Commit Strategy
Single commit: `style(0765p): Standardize design tokens to match branding guide`

---

## Chain Execution Instructions

### Step 1: Read Chain Log
Read `prompts/0765_chain/chain_log.json`
- Verify previous sessions completed
- Check for any blockers

### Step 2: Mark Session Started
Update your session entry: `"status": "in_progress", "started_at": "<timestamp>"`

### Step 3: Execute Tasks
1. Read the design system sample page
2. Read canonical JS sources (agentColors.js, statusConfig.js)
3. Read and fix design-tokens.scss
4. Read and fix agent-colors.scss
5. Verify frontend builds clean
6. Commit

### Step 4: Update Chain Log
Update your session with:
- `tasks_completed`: What you actually fixed
- `deviations`: Any changes from plan
- `blockers_encountered`: Issues hit
- `notes_for_next`: Color discrepancies found or remaining
- `summary`: 2-3 sentence summary
- `status`: "complete"
- `completed_at`: "<timestamp>"

### Step 5: Done
Do NOT spawn another terminal. Report completion via chain log.
