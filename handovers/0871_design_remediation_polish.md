# 0871 — Design System Remediation & Polish

**Edition Scope:** CE
**Priority:** HIGH
**Estimated Sessions:** 8 (0871a through 0871h)
**Dependencies:** 0870 complete (feature/0870-design-harmonization branch)
**Branch:** `feature/0870-design-harmonization` (continues on same branch)

---

## Objective

Remediate gaps identified in the 0870 post-implementation audit. The 0870 chain successfully updated colors, badges, and tokens across 89 components, but left structural patterns untouched: tab styles, outlined borders, component duplication, and missing polish effects. This series completes the harmonization to commercial-grade quality.

---

## Audit Findings (from visual inspection, 2026-03-31)

### Critical Gaps

1. **Tabs still use old underline style** — User Settings (6 tabs), Admin Settings (5 tabs), Jobs (Staging/Implementation), Messages (Timeline/Broadcast). Design system specifies pill-button toggles.
2. **Quick-launch and team cards on Home have outlined CSS borders** — should use `smooth-border` class (inset box-shadow).
3. **No mascot glow effect on Home** — design specifies `drop-shadow(yellow+green)` + radial gradient + float animation.
4. **Integration cards (Settings > Integrations) still old outlined style** — cards and Claude/Codex/Gemini export buttons need restyling.
5. **Messages page** — tabs are old style, sender avatars may still be round.
6. **~20 duplicate scoped muted text classes** — should be one global utility class.
7. **~8 duplicate `getAgentBadgeStyle()` functions** — should be one shared utility.
8. **No shared TintedChip component** — every view rebuilds its own chip markup.
9. **Design system sample v2 is thin** — needs comprehensive rewrite to be authoritative reference.
10. **Admin Settings cards** — still have old thin borders, not smooth-border.

---

## Sub-Handover Breakdown

### 0871a — Shared Component Extraction (Foundation)
**Scope:** Create reusable components and utilities that subsequent sessions depend on.
**Changes:**
- Create `frontend/src/components/ui/TintedChip.vue` — shared tinted chip component
  - Props: `color` (hex), `label` (string), `size` ('sm'|'default'), `pill` (boolean, default true)
  - Renders: `<span>` with `rgba(color, 0.15)` background + bright color text
  - Uses `hexToRgba` from `@/utils/colorUtils`
- Create `frontend/src/components/ui/TintedBadge.vue` — shared tinted badge component
  - Props: `color` (hex), `label` (string, 2-char), `size` (number, default 36)
  - Renders: square div, border-radius 8px, tinted bg + bright text
- Add `getAgentBadgeStyle(agentName)` to `@/utils/colorUtils.js`
  - Returns `{ backgroundColor, color, borderRadius }` style object
  - Import `getAgentColor` internally
  - Remove duplicate implementations from: LaunchTab, JobsTab, AgentTableView, BroadcastPanel, MessageItem, AgentDetailsModal, AgentJobModal, ProjectReviewModal, TemplateManager
- Add global `.text-muted-a11y` class to `main.scss`: `color: var(--text-muted)` (which is #8895a8)
  - Refactor all ~20 scoped `*-text-muted` classes to use global class instead
- Run tests to verify no regressions
**Files:** ~15 files (2 new components, 1 utility update, 1 SCSS, ~11 refactored Vue files)
**Tests:** Add unit tests for TintedChip, TintedBadge. Run full suite.

### 0871b — Tab-to-Pill Conversion: User Settings & Admin Settings
**Scope:** Replace Vuetify v-tabs with pill-button toggle pattern in both settings views.
**Changes:**
- `UserSettings.vue` — replace `v-tabs`/`v-tab` with a flex row of pill buttons. Active pill: `rgba(255,195,0,0.12)` background + `#ffc300` text. Inactive: transparent + `#8895a8` text + `smooth-border`. Each pill has icon + label matching current tabs (Startup, Notifications, Agents, Context, API Keys, Integrations).
- `SystemSettings.vue` — same treatment for Admin tabs (Identity, Network, Database, Security, Prompts).
- Tab content panels remain as `v-window`/`v-window-item` or conditional `v-if` — only the tab selector UI changes.
- Pill style reference: `border-radius: 9999px; padding: 8px 18px; font-size: 0.78rem; font-weight: 500;`
**Files:** 2 Vue files
**Tests:** Run existing tests

### 0871c — Tab-to-Pill Conversion: Jobs & Messages
**Scope:** Replace tabs in ProjectTabs and MessagesView.
**Changes:**
- `ProjectTabs.vue` — replace Staging/Implementation `v-tabs` with pill buttons. Include icons (rocket for Staging, code-braces for Implementation).
- `MessagesView.vue` — replace Message Timeline/Send Broadcast `v-tabs` with pill buttons.
- Ensure execution mode radio group in ProjectTabs gets pill-button styling (it's the radio group that 0870j noted lives in ProjectTabs, not LaunchTab).
**Files:** 2 Vue files
**Tests:** Run existing tests

### 0871d — Home Page Polish
**Scope:** Fix the Welcome/Home view gaps.
**Changes:**
- `WelcomeView.vue`:
  - Add mascot glow effect: `filter: drop-shadow(0 0 14px rgba(255,195,0,0.35)) drop-shadow(0 0 36px rgba(107,207,127,0.15))` on GilMascot wrapper
  - Add float animation: `@keyframes mascotFloat { 0%,100% { transform: translateY(0) } 50% { transform: translateY(-4px) } }` with 4s ease-in-out infinite
  - Add radial gradient glow behind mascot: `radial-gradient(circle, rgba(255,217,61,0.14) 0%, rgba(107,207,127,0.06) 50%, transparent 70%)`
  - Fix quick-launch cards: replace any CSS `border` with `smooth-border` class
  - Fix team cards: replace any CSS `border` with `smooth-border` class
  - Fix empty slot cards: use `border: 1px dashed rgba(255,255,255,0.1)` (dashed is intentional for empty slots, but active cards should use smooth-border)
- Reference mockup: `frontend/mock/welcome-v3-colors.html`
**Files:** 1 Vue file
**Tests:** Visual verification

### 0871e — Smooth-Border Sweep & Card Polish
**Scope:** Find and fix all remaining outlined/bordered cards across the app.
**Changes:**
- Run `grep -r "variant=\"outlined\"" --include="*.vue"` to find remaining outlined cards
- Run `grep -r "border:" --include="*.vue" --include="*.scss"` in scoped styles to find CSS borders on rounded elements
- Convert all found instances to `smooth-border` class or `variant="flat"` + `smooth-border`
- Key targets identified from audit:
  - Products view product cards
  - Admin Settings tab content cards (all 5 tabs)
  - Any remaining dialog inner cards
  - Integration cards inner elements
- Exclude: dashed borders on empty slots (intentional), table cell borders (functional)
**Files:** Estimated 5-10 Vue files
**Tests:** Run full suite

### 0871f — Integration Cards & Export Buttons Restyling
**Scope:** Fix the Settings > Integrations tab specifically.
**Changes:**
- `McpIntegrationCard.vue` — restyle CONFIGURATOR button, ensure card uses smooth-border properly
- `AgentExport.vue` — restyle Claude Prompt / Codex Prompt / Gemini Prompt buttons from solid yellow rectangles to the pill-button pattern: `border-radius: 9999px; padding: 6px 16px;` with brand-yellow tinted style. Each button gets its tool icon.
- `GitIntegrationCard.vue` — verify smooth-border, fix any remaining old patterns
- `SerenaIntegrationCard.vue` — verify smooth-border
- Ensure description text uses `text-muted-a11y` class (from 0871a)
**Files:** ~4 Vue files
**Tests:** Run existing tests

### 0871g — Messages Page & Remaining View Polish
**Scope:** Polish messages page and any remaining view-level issues.
**Changes:**
- `MessagesView.vue` — verify sender badges are square tinted (from 0870k), fix any remaining round avatars
- `MessageItem.vue` — verify square tinted sender badges, verify tinted status/priority chips
- `BroadcastPanel.vue` — verify tinted status badges, smooth-border cards
- `MessagePanel.vue` — verify tinted chips, smooth-border
- Dashboard product selector pills — tinted pill-button style for "All Products" / product name toggles (currently solid yellow outline)
- `ProductSelector.vue` — convert from outlined chips to tinted pills
**Files:** ~5 Vue files
**Tests:** Run existing tests

### 0871h — Design System Sample v2 Comprehensive Rewrite
**Scope:** Make the design system sample the definitive, comprehensive reference document.
**Changes:**
- Rewrite `frontend/design-system-sample-v2.html` (the one we preserved earlier) as the comprehensive v2
- Must include ALL of:
  - Color palette with WCAG ratios (backgrounds, text hierarchy, agent colors, status colors, brand)
  - Tinted badge component showcase (all 6 agents, both sizes)
  - Tinted chip component showcase (status, priority, category, staged)
  - Pill-button toggle demo (active/inactive states)
  - Button styles (primary, secondary, danger, icon, pill)
  - Input styles (default, focused, search with icon)
  - Stat pill + micro-bar demo
  - Smooth-border demo (3 variants)
  - Surface elevation layers
  - Typography scale (Outfit headings, Roboto body, IBM Plex Mono data)
  - Nav icon alignment (MDI vs Giljo SVG, active/inactive states)
  - Table row patterns (headers, hover, separators, pagination)
  - Card patterns (smooth-border, raised surface, hover lift)
  - Agent badge showcase grid
  - Status chip showcase (all project + agent statuses)
  - Brand section (logo, gradient, tagline)
  - Accessibility section (contrast ratios, prohibited patterns)
- Save as `frontend/design-system-sample-v2.html`, keep v1 as historical reference
- Update any docs referencing the design system sample
**Files:** 1 HTML file + doc references
**Tests:** Visual review

---

## Execution Strategy

```
0871a (shared components) — MUST be first, others depend on it
     ↓
0871b + 0871c — can run in parallel (different files)
     ↓
0871d + 0871e — can run in parallel (different files)
     ↓
0871f + 0871g — can run in parallel (different files)
     ↓
0871h (design system sample) — last, references all completed work
```

## Quality Gates

Each sub-handover must:
1. `npm run lint` — zero errors
2. `npm run test` — all tests pass
3. `grep -r "variant=\"outlined\"" --include="*.vue"` — count should decrease
4. Visual spot-check in browser
5. No new scoped `*-text-muted` classes (use global `text-muted-a11y`)
6. No new local `getAgentBadgeStyle` functions (use shared utility)
7. No new local `hexToRgba` functions (use `@/utils/colorUtils`)
