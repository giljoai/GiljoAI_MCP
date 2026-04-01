# 0872 — Interactive Element Polish & Card Frame Consistency

**Edition Scope:** CE
**Priority:** HIGH
**Estimated Sessions:** 4 (0872a through 0872d)
**Branch:** `feature/0870-design-harmonization` (continues on same branch)

---

## Objective

Standardize interactive icon behavior, play button prominence, product card framing, and the AgentExport card layout inconsistency. These are the final visual polish items before the design harmonization branch can merge.

---

## Issues Identified

### 1. Inconsistent icon hover behavior
- **TasksView**: icons have subdued yellow color, highlight on hover — GOOD, this is the reference
- **LaunchTab (Staging)**: agent card edit/info icons are muted, hover only goes to `--text-secondary` — too subtle
- **JobsTab (Implementation)**: action icons are static, no visible hover reaction
- **ProductsView**: action icons have no hover reaction
- **Expected pattern**: all interactive icons should have `color: var(--text-muted)` default → `color: var(--brand-yellow)` on hover with `background: rgba(255,195,0,0.08)` tinted circle/square, `transition: all 0.15s`

### 2. Play/start button inconsistency
- **ProjectsView**: play button has slight hover reaction — OK but weak
- **JobsTab**: play/copy button has no hover reaction — broken
- **Expected pattern**: play buttons get a more prominent hover: `background: rgba(255,195,0,0.2)` → `rgba(255,195,0,0.3)` on hover, `transform: scale(1.08)`, `box-shadow: 0 0 8px rgba(255,195,0,0.2)` — makes it feel alive and clickable

### 3. Product card — no frame
- Product cards in ProductsView have no visible smooth-border frame
- Dashboard panels and Home cards have frames — inconsistent
- **Fix**: add `smooth-border` class to product cards

### 4. AgentExport card layout mismatch
- The "Skills, Commands and Agents Export" card uses `v-card variant="tonal"` for the inner button container — this creates a distinctly different visual from the MCP Integration card above and Serena card below which use smooth-border
- **Fix**: replace `variant="tonal"` with `variant="flat"` + `smooth-border` class, matching sibling cards

---

## Sub-Handover Breakdown

### 0872a — Global Interactive Icon Utility Class
**Scope:** Create a standardized interactive icon pattern in `main.scss` and apply it everywhere.
**Changes:**
- Add `.icon-interactive` global class to `main.scss`:
  ```scss
  .icon-interactive {
    color: var(--text-muted);
    cursor: pointer;
    transition: all 0.15s ease;
    border-radius: 6px;
    padding: 4px;
    &:hover {
      color: var(--brand-yellow, #ffc300);
      background: rgba(255, 195, 0, 0.08);
    }
  }
  ```
- Add `.icon-interactive-play` variant for play/start buttons:
  ```scss
  .icon-interactive-play {
    color: var(--brand-yellow, #ffc300);
    cursor: pointer;
    transition: all 0.2s ease;
    border-radius: 50%;
    background: rgba(255, 195, 0, 0.1);
    &:hover {
      background: rgba(255, 195, 0, 0.25);
      transform: scale(1.1);
      box-shadow: 0 0 10px rgba(255, 195, 0, 0.2);
    }
  }
  ```
- Refactor `LaunchTab.vue` — replace `.edit-icon` / `.info-icon` hover styles with `.icon-interactive` class
- Refactor `JobsTab.vue` — apply `.icon-interactive` to all action icons, `.icon-interactive-play` to play/copy button
- Refactor `AgentTableView.vue` — same treatment
- Refactor `ProjectsView.vue` — apply `.icon-interactive` to action icons, `.icon-interactive-play` to play buttons
- Refactor `ProductsView.vue` — apply `.icon-interactive` to all action icons, `.icon-interactive-play` to activate/play button
- Refactor `TasksView.vue` — verify it already has the correct pattern, align class naming if needed
- Any other view with interactive icons (MessagesView, BroadcastPanel, etc.) — apply same classes
**Files:** 1 SCSS + ~8 Vue files
**Tests:** Run full suite

### 0872b — Product Card Frame & AgentExport Layout
**Scope:** Fix product card framing and the export card visual mismatch.
**Changes:**
- `ProductsView.vue` — add `smooth-border` class to each product card (the v-card wrapping each product)
- `AgentExport.vue` — replace inner `v-card variant="tonal"` (the button container) with `v-card variant="flat" class="smooth-border"` to match MCP and Serena cards visually
- Verify the three integration cards (MCP, AgentExport, Serena) now have consistent framing when viewed together on the Integrations tab
**Files:** 2 Vue files
**Tests:** Run existing tests

### 0872c — Action Icon Audit & Sweep
**Scope:** Grep the entire frontend for any remaining inconsistent icon patterns.
**Changes:**
- `grep -r "cursor: pointer" --include="*.vue"` in scoped styles to find all clickable elements
- Verify every interactive icon uses either `.icon-interactive` or `.icon-interactive-play`
- Check modals: AgentDetailsModal, AgentJobModal, MessageAuditModal, TemplateManager — these all have action icons that should follow the pattern
- Check navigation: AppBar notification bell, user menu — verify hover states
- Report: list of files checked, how many were already correct, how many were fixed
**Files:** Estimated 5-10 Vue files
**Tests:** Run full suite

### 0872d — Final Visual Verification Commit
**Scope:** Final pass — run the app, verify every page visually, commit clean.
**Changes:**
- Open every main route in browser and verify:
  - Home: mascot glow, card frames, icon hovers
  - Dashboard: stat pills, project rows, memory rows
  - Products: card frames, icon hovers, play button glow
  - Projects: table styling, icon hovers, play button
  - Jobs Staging: agent card icons, pill tabs
  - Jobs Implementation: table icons, play button, composer
  - Tasks: icon hovers, chips
  - Messages: sender badges, pill tabs
  - Settings > all tabs: pill tabs, card frames
  - Settings > Integrations: 3 cards consistent, export buttons
  - Admin > all tabs: pill tabs, card frames
- Fix any final visual issues found
- Commit with verification note
- Update chain_log.json, set final_status complete
**Files:** As needed
**Tests:** Full suite

---

## Execution Strategy

```
0872a (global icon classes + refactor) — FIRST, foundation
     ↓
0872b + 0872c — can run in parallel (different files)
     ↓
0872d (verification) — LAST
```
