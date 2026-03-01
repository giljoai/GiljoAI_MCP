# 0750g: Frontend Cleanup

**Series:** 0750 (Code Quality Cleanup Sprint)
**Phase:** 7 of 7 (FINAL)
**Branch:** `0750-cleanup-sprint`
**Priority:** LOW — cosmetic/maintainability

### Reference Documents
- **Roadmap:** `handovers/CLEANUP_ROADMAP_2026_02_28.md` (Phase 7 section)
- **Audit report:** `handovers/CODE_QUALITY_AUDIT_REPORT_2026_02_28.md` (M-18 through M-27)
- **Mid-point audit:** `prompts/0750_chain/midpoint_audit.json` (remaining frontend findings)
- **Previous phase notes:** Read `prompts/0750_chain/chain_log.json` session 0750f `notes_for_next`

### Tracking Files (update these when done)
- **Chain log:** `prompts/0750_chain/chain_log.json`
- **Progress tracker:** `handovers/0700_series/0750_cleanup_progress.json`

---

## Context

This is the final cleanup phase. Phase 6 already removed dead frontend functions, orphan emits, and unused props (H-6, H-10-12, H-20-23). This phase addresses the remaining cosmetic and maintainability items: CSS overrides, duplicated utilities, stale backend references, accessibility, and design tokens.

**NOTE:** The `frontend/node_modules` directory may be corrupted (see `handovers/NPM_VITE_corruption_report.md`). If `npm run build` fails due to missing dependencies, run `rm -rf frontend/node_modules && npm install --prefix frontend` first. If that also fails, skip build verification and note it as a blocker.

---

## Scope

### 7A: Extract duplicated `copyToClipboard` (M-18)

The `copyToClipboard` utility is duplicated in 6+ component files.

- [ ] Search for all `copyToClipboard` implementations:
  ```bash
  grep -rn "copyToClipboard\|navigator.clipboard" frontend/src/ --include="*.vue" --include="*.ts" --include="*.js"
  ```
- [ ] Create `frontend/src/composables/useClipboard.ts`:
  ```typescript
  export function useClipboard() {
    async function copyToClipboard(text: string): Promise<boolean> {
      try {
        await navigator.clipboard.writeText(text)
        return true
      } catch {
        return false
      }
    }
    return { copyToClipboard }
  }
  ```
  Adapt the implementation to match whatever the existing duplicated code does (it may include toast notifications or error handling).
- [ ] Update all components to import from the composable instead
- [ ] Verify no duplicated implementations remain

### 7B: Remove `!important` overrides (M-24)

The mid-point audit found 113 `!important` declarations.

- [ ] Find all `!important` uses:
  ```bash
  grep -rn "!important" frontend/src/ --include="*.vue" --include="*.css" --include="*.scss"
  ```
- [ ] For each `!important`:
  - **Can it be replaced with a more specific CSS selector?** → Remove `!important`, use specificity
  - **Is it overriding a Vuetify framework default?** → Try using Vuetify's class-based approach instead
  - **Is it compensating for a verified framework bug?** → Leave it with a comment explaining why
  - **Is it in a scoped style?** → May be safe to remove if no parent conflicts
- [ ] Target: reduce by >50% (from 113 to <57)

### 7C: Replace hardcoded colors with design tokens (M-25)

- [ ] Find hardcoded color values:
  ```bash
  grep -rn "#[0-9a-fA-F]\{3,8\}\|rgb(" frontend/src/ --include="*.vue" | grep -v "node_modules"
  ```
- [ ] For each hardcoded color:
  - Is it a theme color that should use a Vuetify token? → Replace with `rgb(var(--v-theme-primary))` or equivalent
  - Is it a one-off decorative color? → Leave as-is
- [ ] Check if a theme configuration exists in `frontend/src/plugins/vuetify.ts` or similar

### 7D: Fix stale backend references (from audit)

- [ ] Search for references to removed backend features:
  ```bash
  grep -rn "acknowledge_job\|MCPAgentJob\|agent_job" frontend/src/ --include="*.vue" --include="*.ts" --include="*.js"
  ```
- [ ] Remove or update any references to deleted backend APIs
- [ ] Note: Phase 6 already removed some of these (H-6: `api.agentJobs.acknowledge()`)

### 7E: Add ARIA labels (M-27)

- [ ] Find interactive elements without accessibility labels:
  ```bash
  grep -rn "<v-btn\|<v-icon\|<button\|<a " frontend/src/ --include="*.vue" | grep -v "aria-label"
  ```
- [ ] Add `aria-label` to buttons and interactive icons that lack descriptive text
- [ ] Focus on the most-used components: navigation, action buttons, toolbar icons

### 7F: Clean dead Pinia store state (from audit)

- [ ] Check Pinia stores for state properties that are set but never read:
  ```bash
  grep -rn "state:" frontend/src/stores/ --include="*.ts" --include="*.js"
  ```
- [ ] For each store, compare defined state keys against actual reads across components
- [ ] Remove confirmed dead state properties

### 7G: Build verification

```bash
cd frontend && npm run build
```

Must succeed with zero errors. Warnings are acceptable but note the count.

If npm/node_modules is broken: note it as a blocker and skip this step.

---

## What NOT To Do

- Do NOT change frontend dict-return patterns (Vue composable return objects) — these are intentional
- Do NOT restructure components or change routing
- Do NOT modify backend code
- Do NOT remove `!important` declarations blindly — investigate each one
- Do NOT add new dependencies
- Do NOT change the Vuetify version or theme structure

---

## Acceptance Criteria

- [ ] `copyToClipboard` exists in one shared composable, not duplicated
- [ ] `!important` count reduced by >50% (from 113 to <57)
- [ ] No references to deleted backend features (`acknowledge_job`, dead `agent_job` endpoints)
- [ ] ARIA labels added to key interactive elements
- [ ] Dead Pinia store state removed
- [ ] `npm run build` succeeds (or blocker documented)
- [ ] No behavioral changes — UI looks and functions identically

---

## Completion Steps

### Step 1: Verify branch
```bash
git branch --show-current
# Must show: 0750-cleanup-sprint
```

### Step 2: Commit
```bash
git add frontend/
git commit -m "cleanup(0750g): Frontend cleanup — shared composable, reduce !important, ARIA labels, design tokens"
```

### Step 3: Record commit hash
```bash
git rev-parse --short HEAD
```

### Step 4: Update chain log
Read `prompts/0750_chain/chain_log.json`, update session `0750g`:
- Set `"status": "complete"`
- Set timestamps
- Fill in `"tasks_completed"`
- Fill in `"notes_for_next"`: this is the last phase — note what's left for future work
- Fill in `"summary"`: 2-3 sentences

### Step 5: Update progress tracker
Read `handovers/0700_series/0750_cleanup_progress.json`, update `phases[6]`:
- Set `"status": "complete"`
- Set `"commits"` array
- Set `"notes"` with !important count before/after

### Step 6: Done
Do NOT spawn the next terminal.
Print "0750g COMPLETE" as your final message with !important count and build status.
