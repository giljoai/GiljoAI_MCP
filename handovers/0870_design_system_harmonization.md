# 0870 — Design System Harmonization: Luminous Pastels & WCAG AA Compliance

**Edition Scope:** Both (CE primary, SaaS inherits)
**Priority:** HIGH
**Estimated Sessions:** 12-16 (series of sub-handovers 0870a through 0870p)
**Dependencies:** None (standalone visual refresh — no backend changes, no DB migrations)
**Branch:** `feature/0870-design-harmonization`

---

## Objective

Harmonize the entire GiljoAI MCP frontend to a unified design system based on decisions made during the March 2026 design exploration. This encompasses: new agent color palette (Luminous Pastels), WCAG AA accessibility compliance, tinted badge style, square badge geometry, updated typography hierarchy, and consistent component patterns across all 89 Vue components, 20 views, 5 SCSS files, project documentation, and the public-facing landing page.

---

## Design Decisions (Finalized)

### Agent Color Palette: Luminous Pastels

| Role | Current Hex | New Hex | WCAG Ratio on #182739 |
|------|------------|---------|----------------------|
| Orchestrator | #D4A574 | #D4B08A | 7.48:1 AA Pass |
| Analyzer | #E74C3C | #E07872 | 5.11:1 AA Pass |
| Implementer | #3498DB | #6DB3E4 | 6.64:1 AA Pass |
| Documenter | #27AE60 | #5EC48E | 7.03:1 AA Pass |
| Reviewer | #9B59B6 | #AC80CC | 4.84:1 AA Pass |
| Tester | #FFC300 | #EDBA4A | 8.45:1 AA Pass |

### Badge Style: Tinted (not solid)

- Background: `rgba(agent_color, 0.15)`
- Text: agent color at full brightness
- No border, no reflection
- Badge shape: square with `border-radius: 8px` (replacing round avatars)
- All badge text on solid backgrounds: `#0e1c2d` (dark navy)

### Text Color Accessibility Fix

| Token | Current | New | Ratio Change |
|-------|---------|-----|-------------|
| --text-muted | #5a6a80 (2.74:1 FAIL) | #8895a8 (4.98:1 PASS) | Critical fix |
| --text-secondary | #8f97b7 (5.24:1 pass) | #a3aac4 (6.56:1 pass) | Comfort bump |
| --border-subtle | rgba(255,255,255,0.08) | rgba(255,255,255,0.10) | Slightly more visible |

### Nav Drawer Jobs Icon Fix

- SVG fill color changed from `#A5AAAF` (neutral grey) to `#8f97b7` (matches MDI icon color `--nav-icon-color`)
- Opacity 0.85 on inactive state to compensate for solid fill vs MDI outlined glyphs
- Active state: body `#ffc300`, eyes `#e1e1e1`

### Status Colors: UNCHANGED

Status chips (Active, Inactive, Completed, Cancelled, Terminated) retain their current semantic colors. These are functional, not decorative.

### Chart Style: Stat Pills + Inline Micro-bars

Donut charts replaced by stat pill cards with inline stacked micro-bars and micro-legends. Consolidates stats row + chart row into a single section.

### Website Copy Alignment

Hero tagline: "The context engineering platform for AI-assisted development" (from giljo.ai website).

---

## Sub-Handover Breakdown

### Phase 1: Foundation (0870a-c)

#### 0870a — Design Token Update & SCSS Foundation
**Scope:** Update `design-tokens.scss`, `variables.scss`, `agent-colors.scss`, `main.scss`, `global-tabs.scss`
**Changes:**
- Replace all 6 agent hex values in `design-tokens.scss` (old → Luminous Pastels)
- Update `--text-muted` and `--text-secondary` CSS variables in `main.scss`
- Update `--border-subtle` opacity
- Add new tokens: `--badge-text: #0e1c2d`, tinted background rgba variants for each agent
- Update `agent-colors.scss` CSS custom properties
- Audit all `/* design-token-exempt */` comments for validity
**Files:** 5 SCSS files
**Tests:** Visual regression only (open design-system-sample.html)

#### 0870b — agentColors.js + theme.js + statusConfig.js
**Scope:** Update JS color configuration files
**Changes:**
- Update all 6 hex values in `AGENT_COLORS` object in `agentColors.js`
- Verify synonym mappings still resolve correctly
- Update `theme.js` if any agent colors are referenced
- Verify `statusConfig.js` colors are unchanged (they should be)
- Update `GiljoFaceIcon.vue` if it uses hardcoded agent colors
**Files:** 3-4 JS/Vue files
**Tests:** Existing Vitest tests should still pass

#### 0870c — Design System Sample v2
**Scope:** Rewrite `frontend/design-system-sample.html` as comprehensive v2
**Changes:**
- Luminous Pastels palette with WCAG ratios displayed
- Tinted badge style showcase (square geometry)
- Accessibility text hierarchy demo (primary/secondary/muted with ratios)
- Stat pill + micro-bar component demo
- Button styles, chip styles, status chips
- Agent badge grid with all 6 roles
- Surface elevation layers updated
- Nav icon color demo (MDI vs Giljo SVG)
**Files:** 1 HTML file
**Tests:** None (reference document)

### Phase 2: Core Components (0870d-g)

#### 0870d — Agent Badge Components (GilMascot, StatusChip, ActionIcons, RoleBadge)
**Scope:** Update all agent avatar/badge rendering across shared components
**Changes:**
- `GilMascot.vue` — verify colors don't conflict
- `StatusChip.vue` — no changes expected (status colors unchanged)
- `ActionIcons.vue` — verify icon colors
- `RoleBadge.vue` — update to tinted style, square geometry
- `StatusBadge.vue` — update chip styles to tinted approach where applicable
- `GiljoFaceIcon.vue` — verify fill colors
- Any component using `getAgentColor()` will automatically get new colors from 0870b
**Files:** ~6 Vue components
**Tests:** Run existing component tests

#### 0870e — Navigation & Layout (AppBar, NavigationDrawer, DefaultLayout)
**Scope:** Update application shell components
**Changes:**
- `NavigationDrawer.vue` — fix Jobs icon SVG fill to use CSS variable `--nav-icon-color` (#8f97b7), add opacity 0.85, active state fill swap
- `AppBar.vue` — verify ActiveProductDisplay chip colors, ConnectionStatus colors
- `DefaultLayout.vue` — verify no hardcoded colors
- `ActiveProductDisplay.vue` — verify chip styling
- `ConnectionStatus.vue` — verify chip styling
- `NotificationDropdown.vue` — verify badge colors
**Files:** ~6 Vue components
**Tests:** Run existing tests

#### 0870f — Dashboard View Redesign
**Scope:** Implement stat pills + micro-bars, replace donut charts, update activity panels
**Changes:**
- `DashboardView.vue` — restructure layout: stat pills row → mini stats row → projects panel → bottom grid (360 memories + git commits)
- `DonutChart.vue` — deprecate or replace with inline micro-bar component
- `ProductSelector.vue` — verify styling
- `RecentProjectsList.vue` — update to new table row styling
- `RecentMemoriesList.vue` — update to tinted badge style for memory type tags
- New: create `StatPill.vue` component (or inline) for the stat pill + micro-bar pattern
**Files:** ~6 Vue components
**Tests:** Update existing dashboard tests, add stat pill tests

#### 0870g — Welcome/Home View Redesign
**Scope:** Implement the v3 welcome screen design
**Changes:**
- `WelcomeView.vue` — replace current layout: hero (Giljo face with glow + greeting + website tagline), quick-launch cards (dynamic based on product state), "Your Team" grid (from active templates), conditional section (setup wizard on first login, recent projects otherwise)
- `SetupWizardOverlay.vue` — verify styling compatibility, no functional changes
- Remove unused welcome-specific CSS
**Files:** ~2 Vue components
**Tests:** Update existing WelcomeView tests

### Phase 3: View-by-View Harmonization (0870h-l)

#### 0870h — Projects & Tasks Views
**Scope:** Restyle data tables with tinted chips, accessible text colors
**Changes:**
- `ProjectsView.vue` — tinted status chips, square project ID badges, updated table row styling, accessible text-muted color
- `TasksView.vue` — tinted status/priority pills, updated search/filter bar styling, convert icon styling
- Shared table patterns: hover states, border separators, pagination
**Files:** 2 Vue files
**Tests:** Existing view tests

#### 0870i — Products View & Product Dialogs
**Scope:** Harmonize product management UI
**Changes:**
- `ProductsView.vue` — card styling, status badges
- `ProductDetailView.vue` — detail layout
- `ProductForm.vue` — form styling
- `ProductDetailsDialog.vue`, `ProductDeleteDialog.vue`, `ActivationWarningDialog.vue`, `DeletedProductsRecoveryDialog.vue` — dialog styling
- `ProductTuningMenu.vue`, `ProductTuningReview.vue` — tuning UI
**Files:** ~8 Vue files
**Tests:** Existing tests

#### 0870j — Jobs/Orchestration Views (Staging + Implementation)
**Scope:** Restyle the staging and implementation tabs with new design
**Changes:**
- `LaunchTab.vue` — execution mode selector styling, three-panel layout, tinted agent badges (square), integration icon row
- `JobsTab.vue` — table row styling, tinted agent badges, phase badges, status text colors, message waiting badges, action icon styling, composer
- `ProjectTabs.vue` — pill toggle buttons replacing tab underlines (optional — confirm with user)
- `AgentTableView.vue` — same badge + table treatment as JobsTab
- `ProjectLaunchView.vue` — header styling
**Files:** ~5 Vue files
**Tests:** Existing tests

#### 0870k — Messages View
**Scope:** Harmonize messaging UI
**Changes:**
- `MessagesView.vue` — update layout
- `BroadcastPanel.vue`, `MessageItem.vue`, `MessageList.vue`, `MessagePanel.vue` — component styling
**Files:** ~5 Vue files
**Tests:** Existing tests

#### 0870l — Settings Views (User, System, Organization)
**Scope:** Harmonize settings pages
**Changes:**
- `UserSettings.vue` — tab/section styling
- `SystemSettings.vue` — admin settings layout
- `OrganizationSettings.vue` — org settings
- `IdentityTab.vue`, `NetworkSettingsTab.vue`, `SecuritySettingsTab.vue`, `SystemPromptTab.vue` — settings tabs
- `GitIntegrationCard.vue`, `McpIntegrationCard.vue`, `SerenaIntegrationCard.vue` — integration card styling
- `ContextPriorityConfig.vue`, `ProductIntroTour.vue` — supporting components
**Files:** ~11 Vue files
**Tests:** Existing tests

### Phase 4: Modals, Dialogs & Supporting Components (0870m)

#### 0870m — All Modals, Dialogs & Utility Components
**Scope:** Harmonize every popup, modal, and dialog
**Changes:**
- `BaseDialog.vue` — verify/update base dialog styling (this cascades to all dialogs)
- `AgentDetailsModal.vue` — tinted badges
- `AgentJobModal.vue` — todo list styling, mission display
- `AgentMissionEditModal.vue` — form styling
- `MessageAuditModal.vue` — tab styling, message list
- `CloseoutModal.vue`, `ManualCloseoutModal.vue` — button/text styling
- `ProjectReviewModal.vue` — review layout
- `AddTypeModal.vue` — form styling
- `HandoverModal.vue` — handover UI
- `AgentTipsDialog.vue` — tips styling
- `GitAdvancedSettingsDialog.vue` — settings form
- `LicensingDialog.vue` — licensing info
- `InviteMemberDialog.vue` — org invite
- `UserProfileDialog.vue` — profile dialog
- `AiToolConfigWizard.vue` — wizard styling
- `ApiKeyManager.vue` — key management UI
- `TemplateManager.vue` — template table, tinted agent badges
- `UserManager.vue` — user management table
- `ForgotPasswordPin.vue` — auth form
- `ToastManager.vue` — toast styling
- `AppAlert.vue` — alert component
- `ToolConfigSnippet.vue` — code snippet styling
- `AgentExport.vue` — export dialog
- `DatabaseConnection.vue` — connection form
**Files:** ~24 Vue files
**Tests:** Existing tests (BaseDialog changes cascade)

### Phase 5: Auth & Setup Flows (0870n)

#### 0870n — Auth Pages & Setup Wizard
**Scope:** Harmonize login, first-login, admin creation, setup flows
**Changes:**
- `Login.vue` — form styling, color consistency
- `FirstLogin.vue` — password change form
- `CreateAdminAccount.vue` — admin setup
- `OAuthAuthorize.vue` — consent page
- `ServerDownView.vue` — error page
- `NotFoundView.vue` — 404 page
- `SetupStep2Connect.vue`, `SetupStep3Commands.vue`, `SetupStep4Complete.vue` — setup wizard steps
- `SetupWizardOverlay.vue` — overlay styling
- `AuthLayout.vue` — auth layout wrapper
**Files:** ~10 Vue files
**Tests:** Existing tests

### Phase 6: Documentation & External Assets (0870o-p)

#### 0870o — Documentation Update
**Scope:** Update all design-related documentation
**Changes:**
- `frontend/design-system-sample.html` — complete v2 rewrite (from 0870c)
- `docs/SERVER_ARCHITECTURE_TECH_STACK.md` — update color references if any
- `docs/README_FIRST.md` — verify no stale color references
- `CLAUDE.md` — update smooth-border rule if needed, add Luminous Pastels reference, add WCAG AA note
- `handovers/Reference_docs/` — scan all reference docs for stale color values
- Component README files: `components/common/README.md`, `components/projects/README.md`, `views/PROJECTS_VIEW_README.md`
- Any `.md` files in handovers root that reference agent colors or design tokens
**Files:** 8-12 documentation files
**Tests:** None

#### 0870p — Landing Page Harmonization
**Scope:** Update the public website at `C:\Projects\giljoai-mcp-landing`
**Changes:**
- `index.html` — update agent color references to Luminous Pastels, ensure accessible text contrast, update any screenshots showing old UI
- `getting-started.html` — update any embedded colors or screenshots
- `assets/` — update any agent-colored assets, verify logo assets match
- Verify brand consistency: same palette, same badge style, same typography hierarchy
- Update any embedded product screenshots to reflect new UI
- `privacy.html`, `terms.html` — likely no color changes needed
**Files:** 2-4 HTML files + assets
**Tests:** Visual review

---

## Execution Strategy

### Sequential Dependencies

```
0870a (SCSS tokens) → 0870b (JS configs) → 0870c (design system sample)
     ↓
0870d (core components) → 0870e (nav/layout)
     ↓
0870f + 0870g (dashboard + welcome) — can run in parallel
     ↓
0870h through 0870l (view-by-view) — can run in parallel
     ↓
0870m (modals/dialogs)
     ↓
0870n (auth flows)
     ↓
0870o (docs) + 0870p (landing page) — can run in parallel
```

### Critical Path

`0870a → 0870b → 0870d → 0870e` — these four must be sequential. Once the foundation (tokens + JS + core components + nav) is done, the remaining views can be parallelized across multiple sessions.

### Quality Gates

Each sub-handover must:
1. Run `npm run lint` — zero errors
2. Run `npm run test` — all existing tests pass
3. Visual spot-check in browser (open affected views)
4. Verify no hardcoded old hex values remain (`grep -r "#E74C3C\|#3498DB\|#27AE60\|#9B59B6\|#D4A574" --include="*.vue" --include="*.js" --include="*.scss"`)
5. Verify `--text-muted` old value `#5a6a80` does not appear anywhere
6. WCAG contrast check on any new text/background combinations

### Risk Assessment

| Risk | Mitigation |
|------|-----------|
| Agent colors used in 50+ locations | 0870a+b change the source tokens — most components read via `getAgentColor()` or CSS variables, so changes cascade automatically |
| Vuetify component overrides | Some Vuetify components (v-chip, v-btn) use `color` prop with Vuetify theme names — these need manual audit |
| Screenshot references in docs | 0870o scans all docs; screenshots will need manual recapture after UI changes |
| Landing page uses separate codebase | 0870p is independent, can be done last |
| Breaking existing tests | Color-dependent tests (if any) need value updates — identified in 0870b |

---

## Files Affected (Complete Inventory)

### SCSS (5 files)
- `frontend/src/styles/design-tokens.scss`
- `frontend/src/styles/variables.scss`
- `frontend/src/styles/agent-colors.scss`
- `frontend/src/styles/main.scss`
- `frontend/src/styles/global-tabs.scss`

### JS Configuration (3 files)
- `frontend/src/config/agentColors.js`
- `frontend/src/config/theme.js`
- `frontend/src/utils/statusConfig.js`

### Vue Components (89 files — all listed in sub-handovers above)

### Documentation (8-12 files)
- `frontend/design-system-sample.html`
- `CLAUDE.md`
- `docs/SERVER_ARCHITECTURE_TECH_STACK.md`
- `docs/README_FIRST.md`
- Component READMEs (3 files)
- Handover reference docs (scan required)

### Landing Page (separate repo: `giljoai-mcp-landing`)
- `index.html`
- `getting-started.html`
- `assets/` (screenshots, color-dependent SVGs)

### Mockup References (kept for handover reference, deleted after implementation)
- `frontend/mock/welcome-v3-colors.html`
- `frontend/mock/dashboard-enhanced.html`
- `frontend/mock/orchestration-view.html`
- `frontend/mock/projects-tasks-view.html`

---

## Success Criteria

1. All 6 agent colors display as Luminous Pastels across every view, component, modal, and dialog
2. All text passes WCAG AA contrast ratios (4.5:1 for normal text, 3:1 for large text)
3. `grep` for old hex values returns zero hits in `.vue`, `.js`, `.scss` files
4. All existing tests pass without modification (except color value assertions)
5. Design system sample v2 is comprehensive and accurate
6. Landing page matches application palette
7. No visual regressions in navigation, status indicators, or functional UI elements
