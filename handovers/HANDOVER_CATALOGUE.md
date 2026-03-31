# Handover Catalogue

**Purpose:** Central registry of all handovers - active, completed, and archived.

**Last Updated:** 2026-03-30 (0860a-d Code Provenance & License Audit COMPLETE)

---

## Quick Reference

| Range | Domain | Status |
|-------|--------|--------|
| 0001-0100 | Foundation & Installation | Mostly Complete |
| 0101-0200 | Refactoring & Architecture | Mostly Complete |
| 0201-0300 | GUI Redesign & Context v2 | Mostly Complete |
| 0301-0400 | Context Management & Services | 0371 COMPLETE, 0365 SUPERSEDED, 0382 COMPLETE |
| 0401-0500 | Agent Monitoring & Org Hierarchy | 0424-0498 ALL COMPLETE, 0440a-d ALL COMPLETE, 0486 CANCELLED, 0409 DEFERRED. No active handovers. |
| 0501-0600 | Remediation Series | Complete |
| 0601-0700 | Migration & Database | Complete |
| 0700-0769 | Code Quality & Perfect Score (RESERVED) | 0700-0750 cleanup COMPLETE, 0760 proposal COMPLETE, 0765a-s sprint COMPLETE, 0766-0768 triage chains COMPLETE, **0769a-g sprint COMPLETE (2026-03-30)**. **Range reserved for code quality work only.** |
| 0770-0799 | Edition Strategy & SaaS Architecture | 0770 proposal COMPLETE, 0771 isolation architecture COMPLETE |
| 0800-0869 | Enhancement & Feature Series | 0800-0840j ALL COMPLETE. 0841 NOT STARTED. **0842a-f, 0842i-k COMPLETE.** 0842g+0842h NOT STARTED. **0842L AUDIT NOT STARTED.** **0844 NOT STARTED.** **0846a-c COMPLETE.** **0847 NOT STARTED.** **0855a-g COMPLETE.** **0860a-d COMPLETE (CE: PASS WITH REVIEW ITEMS, SaaS: PASS).** |
| 0870-0899 | Design System Harmonization | **0870a-p NOT STARTED.** Luminous Pastels palette, WCAG AA compliance, tinted badges, 89 Vue components + 5 SCSS + docs + landing page. Series coordinator: 0870. |

---

## Active Handovers (In Root Folder)

### Active (In Root Folder)

| ID | Title | Status | Priority | Notes |
|----|-------|--------|----------|-------|
| 0277 | Design Token Standardization — Radius & Shadow | Not Started | Medium | Consolidate 3 radius systems + 2 shadow systems into single canonical set in design-tokens.scss. ~15 file edits, 1-2 hours. |
| 0841 | Slash Command Optimization (/gil_add) | Not Started | Low | Rewrite /gil_add from 343 lines (~3,500 tokens) to ~40 lines (~500 tokens). Keep local, remove verbose templates. |
| 0842g | Per-Document AI Summary Badges | Not Started | Medium | Add AI summary badge row to vision doc cards (wireframe fidelity). Needs API extension. Follow-up to 0842d deviation. |
| 0842h | Frontend Tests — Tuning Icon & Vision Analysis Banner | Not Started | Medium | 11 Vitest component tests for 0842d features. Follow-up to 0842d deviation (agent missed existing test framework). |
| 0842L | Post-Implementation Audit & Cleanup | Not Started | High | Quality audit of entire 0842 branch (50 files, 6860 insertions). Dead code, orphaned tests, secure-context audit, lint, WebSocket chain verification. Tests may be rewritten/deleted. Must pass before merge to master. |
| 0844 | Tenant Data Export/Import (Series Coordinator) | Not Started | Medium | Series of 3 sub-handovers. Sequential: 0844a → manual gate → 0844b → manual gate → 0844c. |
| 0844a | Tenant Export Service | Not Started | Medium | Backend export engine: 31 models, field stripping, vision file bundling, ZIP creation, REPEATABLE READ, SHA-256 checksums. 1-2 sessions. |
| 0844b | Tenant Import Service + Schema Diff | Not Started | Medium | Backend import: schema compatibility analysis, UPSERT pipeline, topological sort, vision file extraction, TSVECTOR regen. Heaviest phase, 2-3 sessions. Depends on 0844a. |
| 0844c | Tenant Data Frontend | Not Started | Medium | Vue component in Database tab: export/import UI, compatibility report dialog, stale backup warning, WebSocket progress. 1 session. Depends on 0844a+b. |
| 0847 | Tool-Aware Orchestrator Protocol | Not Started | High | Make orchestrator protocol (CH1-CH5 + identity) fully tool-aware. Codex/Gemini get native-only language, no Claude refs. Multi-terminal → "Any Coding Agent". 2-3h. |
| **0870** | **Design System Harmonization (Series Coordinator)** | **Not Started** | **High** | Series of 16 sub-handovers (0870a-p). Luminous Pastels palette, WCAG AA compliance, tinted badges, square badge geometry, stat pills, typography. 89 Vue components + 5 SCSS + docs + landing page. 12-16 sessions. Absorbs 0277 (radius/shadow tokens). |
| 0870a | Design Token Update & SCSS Foundation | Not Started | High | Update design-tokens.scss, variables.scss, agent-colors.scss, main.scss, global-tabs.scss. New text-muted + text-secondary values. 5 files. |
| 0870b | agentColors.js + theme.js Config Update | Not Started | High | Update 6 hex values in AGENT_COLORS, verify theme.js + statusConfig.js. 3-4 files. |
| 0870c | Design System Sample v2 | Not Started | Medium | Rewrite design-system-sample.html with all new tokens. Reference doc. |
| 0870d | Core Badge Components | Not Started | High | RoleBadge, StatusBadge, GiljoFaceIcon, StatusChip, ActionIcons. Tinted style, square geometry. ~6 files. |
| 0870e | Navigation & Layout Shell | Not Started | High | NavigationDrawer (Jobs icon fix), AppBar, DefaultLayout, ActiveProductDisplay, ConnectionStatus, NotificationDropdown. ~6 files. |
| 0870f | Dashboard View Redesign | Not Started | High | Stat pills + micro-bars, projects panel, 360 memories, git commits. Replace donuts. ~6 files. |
| 0870g | Welcome/Home View Redesign | Not Started | High | Hero + quick-launch + team grid + conditional section. ~2 files. |
| 0870h | Projects & Tasks Views | Not Started | Medium | Tinted chips, accessible text, table restyling. 2 files. |
| 0870i | Products View & Dialogs | Not Started | Medium | Card styling, status badges, 8 dialog/form components. ~8 files. |
| 0870j | Jobs/Orchestration Views | Not Started | Medium | Staging + Implementation tabs, tinted badges, phase pills, composer. ~5 files. |
| 0870k | Messages View | Not Started | Medium | Messaging UI components. ~5 files. |
| 0870l | Settings Views | Not Started | Medium | User/System/Org settings, integration cards, settings tabs. ~11 files. |
| 0870m | All Modals, Dialogs & Utility Components | Not Started | Medium | Every popup/dialog/wizard. BaseDialog cascades. ~24 files. |
| 0870n | Auth Pages & Setup Wizard | Not Started | Medium | Login, first-login, setup steps, error pages. ~10 files. |
| 0870o | Documentation Update | Not Started | Medium | design-system-sample, CLAUDE.md, docs/, component READMEs, handover reference docs. 8-12 files. |
| 0870p | Landing Page Harmonization | Not Started | Medium | giljoai-mcp-landing repo: index.html, getting-started.html, assets. Separate codebase. |
| **0871** | **Design Remediation & Polish (Series)** | **Not Started** | **High** | 8 sub-handovers (0871a-h). Fixes 0870 audit gaps: tab-to-pill, smooth-border sweep, shared components, Home glow, integration restyling, design system sample rewrite. |
| 0871a | Shared Component Extraction | Not Started | High | TintedChip, TintedBadge, shared getAgentBadgeStyle, global text-muted-a11y. ~15 files. |
| 0871b | Tab-to-Pill: User & Admin Settings | Not Started | High | Replace v-tabs with pill toggles. 2 files. |
| 0871c | Tab-to-Pill: Jobs & Messages | Not Started | High | ProjectTabs + MessagesView pill conversion. 2 files. |
| 0871d | Home Page Polish | Not Started | Medium | Mascot glow, card borders. 1 file. |
| 0871e | Smooth-Border Sweep | Not Started | Medium | Remaining outlined cards. 5-10 files. |
| 0871f | Integration Cards & Export Buttons | Not Started | Medium | Pill-style export buttons, card polish. ~4 files. |
| 0871g | Messages & Remaining Polish | Not Started | Medium | Sender badges, ProductSelector pills. ~5 files. |
| 0871h | Design System Sample v2 Comprehensive | Not Started | Medium | Authoritative reference HTML. 1 file. |

### Deferred (Still in Root Folder)

| ID | Title | Status | Priority | Notes |
|----|-------|--------|----------|-------|
| 1014 | Security Event Auditing | Deferred | Medium | Enterprise compliance. No requirement yet. |
| TODO_vision | Vision Summarizer LLM Upgrade | Deferred | Low | Phase 1 incomplete. Current Sumy works. |

### Recently Closed (March 2026 - from Active)

| ID | Title | Closed | How |
|----|-------|--------|-----|
| 0860a-d | Code Provenance & License Audit (4 sessions) | 2026-03-30 | COMPLETE — ScanCode 32.5.0 + SCANOSS 1.51.0 + pip-licenses + license-checker. 268 Python + 383 npm deps scanned. 494 source files (ScanCode) + 384 source files (SCANOSS). **CE: PASS WITH REVIEW ITEMS** (4 REVIEW: useToast.js 79% SCANOSS match, psycopg2-binary LGPL exception, pycountry LGPL dynamic link, PyGithub LGPL verify-not-shipped). **SaaS: PASS.** Zero AGPL. Zero GPL in shipped deps. Zero copyleft in source. Branch: feature/0860-license-audit. |
| 0846a-c | MCP SDK Standardization (3 sessions) | 2026-03-29 | COMPLETE — Replaced custom JSON-RPC transport with official MCP SDK (FastMCP + Streamable HTTP). 27 tools registered via @mcp.tool(), MCPAuthMiddleware (JWT + API key), promoted to /mcp, old router removed from app.py. 3 docs updated. mcp_http.py kept on disk for test compat. Branch: feature/0846-mcp-sdk-standardization. |
| 0855a-g | Setup Wizard Redesign (7 sessions) | 2026-03-29 | COMPLETE — Backend schema (3 User columns + migration + 2 endpoints), 3 WebSocket event types, full-screen overlay with 4-step progress bar, Step 1 tool selection, Step 2 MCP config + live connection status, Step 3 bootstrap prompt + WebSocket checklist, Step 4 launchpad cards, learning mode ("How to Use") overlay, useMcpConfig composable, StartupQuickStart deleted (639 lines). 106 Vitest tests. Branch: feature/0855-setup-wizard. |
| 0842a-e | Vision Document Analysis (5 sessions) | 2026-03-27 | COMPLETE — DB migration + Sumy wiring, Context Manager AI-preferred reads, MCP tools (gil_get_vision_doc + gil_write_product), frontend UI (tuning icon + analysis banner + custom instructions), E2E tests. 6 commits, 33 tests. Branch: feature/0842-vision-doc-analysis. |
| 0842f | Agent Lab — Chain Strategy Template Download | 2026-03-27 | COMPLETE (`a5a4c8e7`) — Chapter 3 in Agent Lab dialog, downloadable 220-line tool-agnostic chain strategy template. |
| 0842i | Product Setup Wizard — Vision-First Flow Redesign | 2026-03-27 | COMPLETE (`d07a968c`) — Vision doc upload merged into Tab 1, manual/AI mode radio, tab locking during analysis, progress indicator. Single-file change. |
| 0842j | Clipboard Copy Fix — All Origins + Dialog Compat | 2026-03-28 | COMPLETE — Fixed useClipboard composable: execCommand fallback appended textarea to document.body but Vuetify retain-focus stole focus. Fix: append inside active overlay. Works on localhost, LAN IP, WAN IP, HTTPS. Also fixed isEdit wizard flip and 404 ghost product deletes. |
| 0842k | Paginated Vision Doc Chunk Delivery | 2026-03-28 | COMPLETE — gil_get_vision_doc now serves pre-chunked content from mcp_context_index one chunk at a time (pagination via `chunk` param). Dropped response from 289K→metadata-only. Also: testing_strategy enum, crypto.randomUUID fallback, WebSocket UI unlock, green toast. |
| 0837 | Project Creation Taxonomy Fix (a-d) | 2026-03-25 | COMPLETE — Auto-assign series_number, type resolution by label, slash command updates, constraint audit. All 4 sub-handovers done. |
| 0839 | Dashboard Analytics Redesign | 2026-03-25 | COMPLETE (`6ce7ece4`) — Product-aware dashboard with product selector, donut charts (status/taxonomy/agent roles), categorized stat rows. chart.js + vue-chartjs. |
| 0838 | Multi-Platform Subagent Mode (Codex + Gemini) | 2026-03-25 | COMPLETE (`a0b320d6`) — Codex CLI and Gemini CLI subagent modes in staging page, platform-specific spawning syntax, project list UX polish. |
| 0840a | Dead Column Cleanup (JSONB Normalization 1/6) | 2026-03-25 | COMPLETE — Dropped 7 dead meta_data columns, removed 6 ghost config keys, 1 migration. |
| 0840b | Message Table Normalization (JSONB 2/6) | 2026-03-25 | COMPLETE — JSONB arrays → 3 junction tables (recipients, acknowledgments, completions) + 3 columns. 19 files updated. |
| 0840c | Product Config Normalization (JSONB 3/6) | 2026-03-25 | COMPLETE — config_data JSONB → 3 relational tables (tech_stacks, architectures, test_configs) + core_features column. |
| 0840d | User Settings Normalization (JSONB 4/6) | 2026-03-25 | COMPLETE — field_priority_config → user_field_priorities table, depth_config → 7 depth columns on users. |
| 0840e | Project Meta + JSON→JSONB (JSONB 5/6) | 2026-03-25 | COMPLETE — Project meta_data → typed columns, download_tokens filename column, 20 JSON→JSONB conversions. |
| 0840f | Validation & Schema Enforcement (JSONB 6/6) | 2026-03-25 | COMPLETE — Pydantic validators for all remaining JSONB columns, schema drift fix, write-time validation wired in. |
| 0840g | Pre-existing Test Fixes | 2026-03-25 | COMPLETE — Fixed 2 pre-existing test failures unrelated to 0840 normalization. |
| 0840h | Integration & Shutdown Test Fixes | 2026-03-25 | COMPLETE — Fixed 5 consistent + ~53 order-dependent test failures. Root cause: session.refresh() discarding eager-loaded relationships. 1816/1816 green. |
| 0840i | Remove All Backward Compatibility Layers | 2026-03-25 | COMPLETE — Removed config_data dict reconstruction, legacy field mappings, to_agent compat field. One clean normalized path only. 12 files, -448/+328 lines. |
| 0840j | Detached Instance Audit & Fix | 2026-03-26 | COMPLETE — Audited all 40+ session.refresh() calls. Fixed 8 issues (6 bare Product refreshes, 1 docstring, 1 test fixture). Product purge endpoint + delete UX redesign added. |
| 0828 | OAuth 2.1 PKCE Flow for MCP Client Authorization | 2026-03-23 | COMPLETE — OAuth endpoints, OAuthService with PKCE S256, OAuthAuthorizationCode model, frontend consent page, MCP JWT auth, 33 tests. 7 commits (Mar 19-21). |
| 0831 | Product Context Tuning — Scope Drift Detection & Review | 2026-03-23 | COMPLETE — ProductTuningService, submit_tuning_review MCP tool #24, 5 tuning endpoints, 2 Vue components, 39 tests, staleness notification hook. |
| 0836 | Multi-Platform Agent Template Export (all sub-handovers) | 2026-03-23 | COMPLETE — 0836a-e: assembler+MCP, slash commands, frontend UI, two-phase install, Codex skill rewrite, Gemini format fix. All 3 platforms verified working. |
| 0835 | Bearer Auth Migration & HTTPS Contextual Warnings | 2026-03-22 | COMPLETE — wizard outputs Authorization: Bearer for all CLIs, HTTPS warnings in wizard/network tab/installer, protocol toggle re-attach warning |
| 0834 | Dynamic Protocol Resolution (HTTP/HTTPS) | 2026-03-22 | COMPLETE — all URL-generating code respects ssl_enabled config, 14 files fixed across 3 phases, integration test added |
| 0833 | Vision Stats Multi-Doc Aggregation & DB Test Button Fix | 2026-03-22 | COMPLETE — multi-doc stats aggregation, missing testDatabase API method, Windows path fix in handover instructions |
| 0832 | SSL/HTTPS Admin UI Toggle | 2026-03-21 | COMPLETE — interactive SSL toggle in Admin Settings > Network tab, auto-generates self-signed certs, config.yaml persistence |
| 0830 | Orchestrator Staging-to-Implementation Harmonization | 2026-03-21 | COMPLETE (`80199d49`) — thin prompt stripped, orchestrator agent_identity populated, full_protocol forked for orchestrator lifecycle, live team state in get_agent_mission |
| 0829 | Phase Column & Sort Order in Jobs Tab | 2026-03-20 | COMPLETE (`4af6dad5`) — Phase column added to Jobs tab, phase-based sort order |
| 0827 | Agent Reactivation & Continuation | 2026-03-19 | COMPLETE (7 commits) — display names in messages, auto-block on post-completion message, reactivate_job + dismiss_reactivation tools, todo_append + duration accumulation |
| 0826 | Staging Completion Hardening | 2026-03-20 | COMPLETE (`e972e2f9`, `ddfda73d`) — thin prompt guard, server-side staging_complete signal, staging_status timing fix, get_orchestrator_instructions response gate |
| 0825 | Agent Identity Separation from Mission Response | 2026-03-18 | COMPLETE (`1aebbcd8`) — agent_identity field added, dead token fields stripped, template content no longer baked into mission |
| 0825b | Dead Context Management Code Cleanup | 2026-03-18 | COMPLETE (`83983166`) — removed 4 dead classes, 3 dead models, 3 dead tables, -1,341 lines |
| 0824 | Closeout Self-Decommission Guard | 2026-03-18 | COMPLETE — pre-flight guard blocks force-close when orchestrator active, decommissioned diagnostics in complete_job/report_progress |
| 0823 | Context Fetch Protocol Injection | 2026-03-18 | COMPLETE (`6cf62fce`) — CH2 inline fetch calls replace broken context_fetch_instructions |
| 0823b | Move Depth Config to fetch_context Runtime | 2026-03-18 | COMPLETE (`c3899cf7`) — depth config runtime DB lookup, live-tunable settings |
| 0259 | Notification Health Alert - Add Project Context | 2026-03-12 | COMPLETE (`e149f09d`) — project name + click-to-navigate in health alerts |
| 0812 | Remove Unused task.job_id FK | 2026-03-12 | COMPLETE (`95b9ec99`) — dead column, FK, 2 indexes removed from tasks table |
| 0813 | Agent Template Context Separation | 2026-03-12 | COMPLETE — role identity separated from protocols, user_instructions export gap fixed |
| 0814 | Template Manager UI Redesign | 2026-03-12 | COMPLETE (12+ commits) — 4 bugs fixed, dialog redesign, export unification, 20 tests |
| 0815 | Code Review Remediation (March 2026 Commits) | 2026-03-12 | COMPLETE — 2 HIGH, 6 MEDIUM, 5 LOW findings fixed across 14 files, 621 tests |
| 0816 | Vision Upload Progress UX Fix | 2026-03-14 | COMPLETE (`2c8c921e`, `73c3fa35`) — progress bar wired up, tests added, watcher ReferenceError fixed |
| 0817 | March 2026 Audit Cleanup Remainder | 2026-03-14 | COMPLETE — E2E selectors fixed, 28 test files relocated from src/ to tests/ |
| 0732b | README Screenshots | 2026-03-14 | COMPLETE — screenshots captured manually by user |
| 0819a | Project Closeout UI State Management | 2026-03-15 | COMPLETE — tri-state UI (done banner/closeout button/continue guidance), stays on page, 9 tests |
| 0819b | Notification Lifecycle Management | 2026-03-15 | COMPLETE — clearForProject + clearAll actions, 3 terminal paths wired, logout reset, 41 tests |
| 0819c | Project Review Modal (Replace Reopen) | 2026-03-15 | COMPLETE — read-only review modal for completed/terminated, cancelled keeps Reopen, 19 tests |
| 0820 | Remove Context Priority Framing | 2026-03-15 | COMPLETE (`77e34056`) — 4-phase removal across backend, API, frontend, docs |
| 0820b | Context Priority Removal Remediation | 2026-03-15 | COMPLETE (`6f4472e3`) — 16 audit findings across 4 phases, 301 backend + 51 frontend tests |
| 0821 | Broadcast Deadlock Batch Counter Fix | 2026-03-15 | COMPLETE (`c347d495`) — N+1 UPDATEs replaced with single CASE statement, 7 new tests, 39 total passing |
| 0822 | Memory Gate Quality Fixes | 2026-03-15 | COMPLETE (`8f72151c`) — timeout fallback, computed extraction, WS try/catch, 56 tests passing |
| 0818 | WebSocket Modal State Preservation | 2026-03-15 | COMPLETE (`d0bcbccb`+3) — deep equality, debounced batching, snapshot pattern for modals |

### Recently Closed (February 2026 - from Active)

| ID | Title | Closed | How |
|----|-------|--------|-----|
| 0054 | Auth Default Tenant Key Hardening | 2026-02-16 | COMPLETE (`96ffafbd`) |
| 0254 | Three Layer Instruction Cleanup | 2026-02-21 | CLOSED (resolved organically via 0700, 0431, 0407, 0334) |
| 0365 | Orchestrator Handover Behavior Injection | 2026-02-21 | SUPERSEDED (UI handover flow + `build_continuation_prompt()`) |
| 0371 | Dead Code Cleanup Project | 2026-02-21 | COMPLETE (all 7 phases, ~15K+ lines, children 0372-0374 + 0371a) |
| 0371a | Template Dead Code & Stale Test Remediation | 2026-02-21 | COMPLETE (dead GenericAgentTemplate, 50 stale tests) |
| 0382 | Orchestrator Prompt Improvements | 2026-01-01 | COMPLETE (`54dccbce`) |
| 0397 | Deprecate stdio Proxy | 2026-02-19 | MERGED into 0489 |
| 0408 | Serena Toggle Injection | 2026-01-04 | COMPLETE (`14310d3b`) |
| 0410 | Message Display UX Fix | 2026-02-21 | COMPLETE (recipient names + broadcast signal + field fix) |
| 0419 | Long Polling Orchestrator Monitoring | 2026-02-22 | SUPERSEDED (Agent Lab bash sleep polling) |
| 0440a-d | Project Taxonomy (4 phases) | 2026-02-21 | ALL COMPLETE |
| 0464 | Empty State API Resilience | 2026-01-26 | COMPLETE (`be56241c`) |
| 0484 | API Test Fixture Remediation | 2026-02-18 | COMPLETE (`452f9635`) |
| 0486 | Continuation Workflow Enhancements | 2026-02-20 | CANCELLED (360 Memory bridges context) |
| 0488 | Staging Broadcast Response Enforcement | 2026-02-19 | RETIRED (0487 hard gates sufficient) |
| 0489 | MCP Config Revamp & Proxy Retirement | 2026-02-19 | COMPLETE (merged 0397+0489, -924 lines) |
| 0492 | API Key Security Hardening | 2026-02-13 | COMPLETE (5-key limit, 90-day expiry, IP logging) |
| 0495 | Fix API Test Suite Hang | 2026-02-18 | COMPLETE (`d48beecb`) |
| 0411 | Windows Terminal Agent Spawning | 2026-02-24 | SUPERSEDED by 0411a (phase labels) + 0411b (dead code cleanup) |
| 0732 | API Consistency Fixes | 2026-02-23 | COMPLETE (`30072759`) - URL kebab-case + HTTPException standardization |
| 0411a | Recommended Execution Order (Phase Labels) | 2026-02-24 | COMPLETE (7 commits, phase field + Jobs tab pill badges) |
| 0411b | Dead Code Cleanup (WorkflowEngine, MissionPlanner) | 2026-02-24 | COMPLETE (~11,900 lines removed across 12 files) |
| 0497a | Multi-Terminal Agent Prompt Fix (Thin Prompt) | 2026-02-25 | COMPLETE (`15aad66a`, combined with 0497b) |
| 0497b | Agent Completion Result Storage + Auto-Message | 2026-02-25 | COMPLETE (`15aad66a`, combined with 0497a) |
| 0497c | Multi-Terminal Orchestrator Implementation Prompt | 2026-02-25 | COMPLETE (`8de0586e`) |
| 0497d | Agent Protocol Enhancements (Gil_add + Git Commit) | 2026-02-25 | COMPLETE (`25ee3bb2`) |
| 0497e | Fresh Agent Recovery Flow (Successor Spawning) | 2026-02-25 | COMPLETE (`c6592915`) |
| 0498 | Early Termination Protocol + Dashboard Reduction | 2026-02-26 | COMPLETE (4 commits + 8 follow-up fixes, handover modal + retirement flow) |
| 0750 | Code Quality Cleanup Sprint (7 phases + audits) | 2026-03-01 | COMPLETE — score 6.6 to 7.8/10, 24 findings resolved, 15 handovers archived to completed/0700_series/ |
| 0800a/b | Remediation Protocol (#38) | 2026-03-05 | COMPLETE — CLOSEOUT_BLOCKED recovery + enriched blocker responses (`9ee450af`) |
| 0801a/b | Background Agent Protocol (#44) | 2026-03-05 | COMPLETE — stale prohibition updated to neutral guidance (`6824d63b`) |
| 0802a/b | 360 Memory "Unknown" Title (RT-5) | 2026-03-05 | COMPLETE — frontend field mismatch fix (`3af60863`) |
| 0803a | Failed vs Blocked Display (RT-6, #42) | 2026-03-05 | BY DESIGN — `failed` removed in 0491 |
| 0804a | Polling Loop Protocol (RT-2) | 2026-03-05 | COMPLETE — prescriptive intervals replaced with user-consent (`2ccb16c1`) |
| 0805a | Progress Percent (RT-3, #43) | 2026-03-05 | NON-ISSUE — math correct, dashboard uses step counts |
| 0806a | Todo Chicken-and-Egg (RT-4) | 2026-03-05 | BY DESIGN — intended flow already documented |
| 0807a | set_agent_status Missing (CW-5) | 2026-03-05 | BY DESIGN — controlled lifecycle intentional, false doc claim fixed |
| 0083 | Harmonize Slash Commands to /gil_* | 2026-03-07 | COMPLETED (adopted organically via 0388/0461/0700d, no code changes needed) |
| 0765a-s | Perfect Score Sprint (19 sessions) | 2026-03-08 | COMPLETE — 67 commits, ~12K lines removed, 1390 tests / 0 skipped, score 8.35/10 (target 9.5 not reached, stopped at diminishing returns) |
| 0766a | Mission Overwrite Research (CW-1, CW-3) | 2026-03-04 | NOT A BUG — overwrite by design, continuation orchestrators prohibited from calling |
| 0767a | Datetime Serialization Research (#39) | 2026-03-04 | ALREADY FIXED (0731c) + defense-in-depth `default=str` (`1ed52edf`) |
| 0767b+0768b | Combined Implementation (serialization + schema) | 2026-03-04 | COMPLETE (`1ed52edf`) |
| 0768a | fetch_context Batch Research (RT-1, #36) | 2026-03-04 | BY DESIGN (0351) + misleading schema fixed (`1ed52edf`) |

### Greptile Security Series (1000-1014) - SECURITY

| ID | Title | Status | Priority | Notes |
|----|-------|--------|----------|-------|
| 1000 | Greptile Remediation Roadmap | Active | HIGH | Master roadmap |
| 1001 | Greptile Project Index | Reference | - | Index document |
| 1002-1013 | Security Remediations | **COMPLETE** | - | All moved to completed/ |
| 1014 | Security Auditing | **DEFERRED** | MEDIUM | Phase 5 - Waiting for compliance requirements |

> **Status**: 12/15 COMPLETE (2025-12-27). Core security complete. Remaining: 1014 (deferred).

### Deferred / Low Priority

| ID | Title | Status | Priority | Notes |
|----|-------|--------|----------|-------|
| ~~0083~~ | ~~Harmonize Slash Commands~~ | **COMPLETED** | - | Adopted organically via 0388/0461/0700d (2026-03-07) |
| 0250 | HTTPS Enablement | **COMPLETE** | Low | Done (`c5443b7d`, `86aa4106`). Archived. |
| 0284 | Address get_available_agents | **DEFERRED** | Low | Architecture evolved past this. Archived. |
| ~~0731~~ | ~~Legacy Code Removal~~ | **SUPERSEDED** | - | All items resolved by 0745/0765 sprints (2026-03-08) |
| 0732 | CE Release Packaging | **COMPLETE** | HIGH | All tasks done: CHANGELOG updated, convention violations fixed, requirements.txt aligned. Screenshots deferred to 0732b. Docker descoped. (Note: 0732 API Fixes is a separate, COMPLETE handover) |
| ~~0732b~~ | ~~README Screenshots~~ | **COMPLETE** | - | Screenshots captured manually by user (2026-03-14) |
| 1014 | Security Auditing | Deferred | Medium | Enterprise compliance |
| ~~9999~~ | ~~One-Liner Installation System~~ | **DELETED** | - | Obsolete -- website already directs users to GitHub. `python startup.py` is the install path. (2026-03-09) |

### Reference Documents (Not Actionable)

| ID | Title | Type | Notes |
|----|-------|------|-------|
| 0274 | Comprehensive Orchestrator Investigation | Investigation | Reference only |
| 0330a-e | Linting Reports & Feature Catalogues | Audit | Reference |
| 0332 | Agent Staging and Execution Prompting Overview | Architecture | Reference |
| 0337 | E2E Test Report / Next Agent Summary | Test Report | Reference |

### Superseded/Moved to Completed (Cleanup)

| ID | Title | Status | Notes |
|----|-------|--------|-------|
| 0246b | Vision Document Storage Simplification | **SUPERSEDED** | By 0352 |
| 0348 | Product Context Gap Analysis | **SUPERSEDED** | By 0350 series |
| 0403 | JSONB Normalization - Messages | **SUPERSEDED** | Merged into 0387 |
| 0726 | Tenant Isolation Remediation | **SUPERSEDED** | False positive (24/25 findings); real issue fixed by 0433 |

---

## Completed (In completed/ Folder)

### Recently Completed (March 2026)

| ID | Title | Status |
|----|-------|--------|
| 0835 | Bearer Auth Migration & HTTPS Contextual Warnings | **COMPLETE** (2026-03-22, Bearer auth in wizard, HTTPS warnings, protocol toggle re-attach warning) |
| 0834 | Dynamic Protocol Resolution (HTTP/HTTPS) | **COMPLETE** (2026-03-22, all URL-generating code respects ssl_enabled, 14 files fixed, integration test) |
| 0833 | Vision Stats Multi-Doc Aggregation & DB Test Button Fix | **COMPLETE** (2026-03-22, multi-doc vision stats aggregation, missing testDatabase API method, Windows path fix) |
| 0832 | SSL/HTTPS Admin UI Toggle | **COMPLETE** (2026-03-21, interactive SSL toggle in Admin > Network, auto-cert generation, config.yaml persistence) |
| 0830 | Orchestrator Staging-to-Implementation Harmonization | **COMPLETE** (2026-03-21, `80199d49`, thin prompt + agent_identity + protocol fork + live team state) |
| 0829 | Phase Column & Sort Order in Jobs Tab | **COMPLETE** (2026-03-20, `4af6dad5`, phase column + sort order in Jobs tab) |
| 0827 | Agent Reactivation & Continuation (4 phases) | **COMPLETE** (2026-03-19, 7 commits, display names + auto-block + reactivate/dismiss tools + todo_append + duration) |
| 0826 | Staging Completion Hardening | **COMPLETE** (2026-03-20, `e972e2f9`+`ddfda73d`, prompt guard + server-side signal + timing fix + response gate) |
| 0824 | Closeout Self-Decommission Guard | **COMPLETE** (2026-03-18, pre-flight guard + decommissioned diagnostics) |
| 0823 | Context Fetch Protocol Injection | **COMPLETE** (2026-03-18, `6cf62fce`, CH2 inline fetch calls replace broken context_fetch_instructions) |
| 0823b | Move Depth Config to fetch_context Runtime | **COMPLETE** (2026-03-18, `c3899cf7`, depth config runtime DB lookup, live-tunable settings) |
| 0259 | Notification Health Alert - Add Project Context | **COMPLETE** (2026-03-12, `e149f09d`, project name + click-to-navigate in health alerts) |
| 0812 | Remove Unused task.job_id FK | **COMPLETE** (2026-03-12, `95b9ec99`, dead column + FK + 2 indexes removed) |
| 0813 | Agent Template Context Separation | **COMPLETE** (2026-03-12, role identity separated from protocols, user_instructions export gap fixed) |
| 0814 | Template Manager UI Redesign | **COMPLETE** (2026-03-12, 12+ commits, 4 bugs fixed, dialog redesign, export unification, 20 tests) |
| 0815 | Code Review Remediation (March 2026 Commits) | **COMPLETE** (2026-03-12, 2 HIGH + 6 MEDIUM + 5 LOW findings fixed, 14 files, 621 tests) |
| 0816 | Vision Upload Progress UX Fix | **COMPLETE** (2026-03-14, `2c8c921e` + `73c3fa35`, progress bar wired up + tests + watcher fix) |
| 0817 | March 2026 Audit Cleanup Remainder | **COMPLETE** (2026-03-14, E2E selectors fixed + 28 test files relocated, commits `6b87f67a` + `da5fc6d6`) |
| 0732b | README Screenshots | **COMPLETE** (2026-03-14, screenshots captured manually by user) |
| 0819a | Project Closeout UI State Management | **COMPLETE** (2026-03-15, tri-state UI, stays on page, 9 tests) |
| 0819b | Notification Lifecycle Management | **COMPLETE** (2026-03-15, clearForProject + clearAll, 3 terminal paths, logout reset, 41 tests) |
| 0819c | Project Review Modal (Replace Reopen) | **COMPLETE** (2026-03-15, read-only modal, cancelled keeps Reopen, 19 tests) |
| 0818 | WebSocket Modal State Preservation | **COMPLETE** (2026-03-15, `d0bcbccb`+3 commits, 3 phases: deep equality, debounced batching, snapshot pattern) |
| 0820b | Context Priority Removal Remediation | **COMPLETE** (2026-03-15, `6f4472e3`, 16 fixes across 4 phases, 301 backend + 51 frontend tests) |
| 0822 | Memory Gate Quality Fixes | **COMPLETE** (2026-03-15, `8f72151c`, timeout fallback, computed extraction, WS try/catch, 56 tests) |
| 0765a-s | Perfect Score Sprint (19 sessions) | **COMPLETE** (2026-03-08, 67 commits, ~12K+ lines dead code removed, 1390 tests pass / 0 skipped) |
| 0083 | Harmonize Slash Commands to /gil_* | **COMPLETED** (2026-03-07, adopted organically via 0388/0461/0700d — no code changes needed) |
| 0800-0807 | Feb Report Tier 1 Triage (14/21 items resolved) | **COMPLETE** (2026-03-05, research+implementation across 11 handovers) |
| 0808-0811 | Feb Report Tier 2 Triage (6 items -> 20/21 resolved) | **COMPLETE** (2026-03-06, `f665c861`) — CW-2 SUPERSEDED, CW-4 NON-ISSUE, #40 FIXED, #41 SUPERSEDED, #50 FIXED |

### Recently Completed (February 2026)

| ID | Title | Status |
|----|-------|--------|
| 0498 | Early Termination Protocol + Dashboard Reduction | **COMPLETE** (2026-02-26, 4 commits + 8 follow-up fixes) |
| 0497a-e | Multi-Terminal Production Parity Chain (5 handovers) | **COMPLETE** (2026-02-25, thin prompt + result storage + orchestrator prompt + protocol + recovery) |
| 0411a | Recommended Execution Order (Phase Labels) | **COMPLETE** (2026-02-24, 7 commits, phase field + pill badges) |
| 0411b | Dead Code Cleanup (WorkflowEngine, MissionPlanner) | **COMPLETE** (2026-02-24, ~11,900 lines removed) |
| 0411 | Windows Terminal Agent Spawning | **SUPERSEDED** (2026-02-24, split to 0411a + 0411b) |
| 0732 | API Consistency Fixes (URL kebab-case + HTTPException) | **COMPLETE** (2026-02-23, `30072759`) |
| 0419 | Long Polling Orchestrator Monitoring | **SUPERSEDED** (2026-02-22, replaced by Agent Lab bash sleep polling) |
| 0371 | Dead Code Cleanup Project (all 7 phases) | **COMPLETE** (2026-02-21, ~15K+ lines) |
| 0371a | Template Dead Code & Stale Test Remediation | **COMPLETE** (2026-02-21) |
| 0410 | Message Display UX Fix | **COMPLETE** (2026-02-21) |
| 0440a-d | Project Taxonomy Series (DB, Frontend, Display, Hardening) | **COMPLETE** (2026-02-21) |
| 0254 | Three Layer Instruction Cleanup | **CLOSED** (2026-02-21, resolved organically -> 0371a) |
| 0365 | Orchestrator Handover Behavior Injection | **SUPERSEDED** (2026-02-21, UI handover flow) |
| 0489 | MCP Config Revamp, Proxy Retirement & Backend Cleanup | **COMPLETE** (2026-02-19) |
| 0397 | Deprecate stdio Proxy | **MERGED** into 0489 (2026-02-19) |
| 0488 | Staging Broadcast Response Enforcement | **RETIRED** (2026-02-19) |
| 0495 | Fix API Test Suite Hang (TRUNCATE->DELETE) | **COMPLETE** (2026-02-18) |
| 0484 | Test Fixture Remediation (Dual-Model & JSONB) | **COMPLETE** (2026-02-18) |
| 0054 | Auth Default Tenant Key Hardening | **COMPLETE** (2026-02-16) |
| Tenant Isolation | Phases A-E audit (5 CRITICAL + 20 HIGH) | **COMPLETE** (2026-02-15, 61 regression tests) |
| 0493 | Vision Document Token Harmonization | **COMPLETE** (2026-02-16) |
| 0492 | API Key Security Hardening | **COMPLETE** (2026-02-13) |
| 0491 | Agent Status Simplification & Silent Detection | **COMPLETE** (2026-02-13) |
| 0750a-d | Post-Cleanup Audit & Scrub Series | **COMPLETE** (2026-02-11) |
| 0745a-f | Audit Follow-Up (6 phases) | **COMPLETE** (2026-02-11) |
| 0740 | Post-Cleanup Audit | **COMPLETE** (2026-02-10) |
| 0731a-d | Typed Service Returns Series | **COMPLETE** (2026-02-11) |
| 0733 | Tenant Isolation API Security Patch | **COMPLETE** (2026-02-09) |
| 0730a-e | Service Response Models Series | **COMPLETE** (2026-02-08) |
| 0729 | Orphan Code Removal | **COMPLETE** (2026-02-08) |
| 0728 | Remove Deprecated Vision Model | **COMPLETE** (2026-02-08) |
| 0727 | Test Fixes | **COMPLETE** (2026-02-08) |
| 0726 | Tenant Isolation Remediation | **SUPERSEDED** (2026-02-07) |
| 0725b | Code Health Re-Audit | **COMPLETE** (2026-02-07) |
| 0725 | Code Health Audit | **COMPLETE** (2026-02-07, first audit invalidated) |
| 0720 | Complete Delint | **COMPLETE** (2026-02-07) |
| 0700a-i | Pre-Release Deprecation Purge (9 phases) | **COMPLETE** (2026-02-07) |
| 0709 | Implementation Phase Gate (Staging Enforcement) | **COMPLETE** (2026-02-06) |
| 0490 | 360 Memory UI Closeout Modal Fix | **COMPLETE** (2026-02-07) |
| 0487 | Implementation Phase Gate | **COMPLETE** (2026-02-06) |
| 0486 | Continuation Workflow Enhancements | **CANCELLED** (2026-02-20) |
| 0485 | Product Creation UI Reset & Orchestrator Dedup | **COMPLETE** (2026-02-05) |
| 0434 | Admin Settings UI Consolidation | **COMPLETE** (2026-02-03) |
| 0433 | Task Product Binding & Tenant Isolation Fix | **COMPLETE** (2026-02-02) |
| 0424f-n | Organization Hierarchy (phases f through n) | **COMPLETE** (2026-01-31) |
| 0353 | Agent Team Awareness & Mission Context | **COMPLETE** |

### January 2026

| ID | Title | Status |
|----|-------|--------|
| 0480-0480f | Exception Handling Remediation REVISED | **COMPLETE** (2026-01-28) |
| 0470 | Deprecate orchestrate_project_tool | **COMPLETE** (2026-01-27) |
| 0425-0432 | Platform Detection, Integration, Orchestrator | **COMPLETE** (2026-01-26) |
| 0414-0423 | Agent Lifecycle & Template Series | **COMPLETE** (2026-01-25) |
| 0411 | Jobs Tab Duration & UX Improvements | **COMPLETE** (2026-01-25) |
| 0393-0396 | Context, Dependencies, API Patterns | **COMPLETE** (2026-01-25) |
| 0460-0463 | Agent ID Swap & Ghost Agent Fixes | **COMPLETE** (2026-01-25) |
| 0500-0501 | Agent ID + file_exists Removal | **COMPLETE** (2026-01-25) |
| 0390-0390d | 360 Memory Normalization | **COMPLETE** (2026-01-18) |
| 0377 | Consolidated Vision Documents | **COMPLETE** (2026-01-30) |
| 0380-0389 | Agent/Job Contract Series | **COMPLETE** (2026-01-04) |

### December 2025

| ID | Title | Status |
|----|-------|--------|
| 1002-1013 | Greptile Security Remediation (12 handovers) | **COMPLETE** (2025-12-27) |
| 0379-0379e | Universal Reactive State Architecture | **COMPLETE** (2025-12-27) |
| 0378 | Agent ID / Job ID Message Tool Fixes | **COMPLETE** (2025-12-25) |
| 0356-0362, 0364, 0366 | Alpha Trial Remediation (9/10) | **COMPLETE** (2025-12-21) |
| 0367-0369 | MCPAgentJob Cleanup Migration | **COMPLETE** (2025-12-21) |
| 0349-0355 | Agent Execution & Context Refactor | **COMPLETE** (2025-12-21) |
| 0346-0347 | Depth Config & Mission JSON Restructuring | **COMPLETE** (2025-12) |
| 0350-0350d | On-Demand Context Fetch Architecture | **COMPLETE** (2025-12) |
| 0338, 0345a-e | Vision Document Optimization | **COMPLETE** (2025-12) |
| 0333-0344 | CLI Mode Series | **COMPLETE** (2025-12) |
| 0325-0329 | Database and Service Fixes | **COMPLETE** (2025-12) |
| 0310, 0313 | Testing and Session Fixes | **COMPLETE** (2025-12) |
| 0286-0299 | Message Counter Series | **COMPLETE** (2025-12) |

### November 2025 and Earlier

| ID | Title | Status |
|----|-------|--------|
| 0312-0323 | Context Management v2.0 | **COMPLETE** |
| 0243a-f | GUI Redesign (Nicepage) | **COMPLETE** |
| 0246a-c | Orchestrator Workflow Pipeline | **COMPLETE** |
| 0260, 0262 | Claude Code CLI Mode | **COMPLETE** |
| 0500-0515 | Remediation Series | **COMPLETE** |
| 0120-0130 | Backend Refactoring (89%) | **MOSTLY COMPLETE** |
| 0601 | Nuclear Migration Reset | **COMPLETE** |

---

## Cancelled Handovers

Located in `handovers/cancelled/`:

| ID | Title | Reason |
|----|-------|--------|
| 0280 | Monolithic Context Architecture Roadmap | Approach changed |
| 0281 | Backend Monolithic Context Implementation | Cancelled with 0280 |
| 0282 | Testing Integration Monolithic Context | Cancelled with 0280 |
| 0283 | Documentation Remediation Monolithic Context | Cancelled with 0280 |

---

## Completed Series

### Organization Hierarchy (0424 Series)
**Status:** 100% Complete (January-February 2026)
- 0424a-e: Database, Service Layer, API, Frontend, Migration/Testing
- 0424f: User.org_id direct FK to Organization
- 0424g: AuthService org-first pattern
- 0424h: Welcome screen org integration
- 0424i: AppBar and UserSettings workspace integration
- 0424j: User.org_id NOT NULL enforcement
- 0424k-l: Baseline migration + fresh install verification
- 0424m-n: Model-migration alignment + comprehensive testing
- **Result**: Multi-user workspaces with org-based isolation
- **Architecture**: Organization -> OrgMembership <- User (with direct User.org_id FK)

### Task Product Binding & Tenant Isolation (0433)
**Status:** 100% Complete (February 2026)
- Database: Task.product_id NOT NULL constraint
- Service: 46 lines of vulnerable fallback logic removed
- MCP: tenant_key parameter + active product validation
- API: TaskCreate schema requires product_id
- **Result**: 100% elimination of tenant isolation vulnerability, 23 tests

### Code Cleanup Series (0700-0750)
**Status:** 100% Complete (February 2026)
- 0700-0708: Systematic cleanup index, dependency visualization, utils/config/auth/models/services
- 0720: Complete delint (zero lint errors)
- 0725/0725b: Code health audit + re-audit
- 0727: Test fixes
- 0728: Remove deprecated Vision model
- 0729: Orphan code removal
- 0730a-e: Service response models (dict wrappers to exceptions)
- 0733: Tenant isolation API security patch
- 0745a-f: Audit follow-up (dependency security, schema cleanup, dead code, frontend cleanup, architecture polish, docs sync)
- 0750a-d: Final scrub (except cleanup, console.log removal, archive, orphan components)
- **Result**: ~15,800 lines removed, architecture score 8/10
- **Location**: `0700_series/` folder + `completed/` folder

### Perfect Score Sprint (0765a-s)
**Status:** 100% Complete (March 2026)
- 0765a: Dead code purge + WebSocket bridge removal (~2,500 lines removed)
- 0765b: Quick Tier 3 fixes (NPM, CORS, CSS, emits, sort, prefetch)
- 0765c: Design token migration (zero hardcoded hex colors)
- 0765d: Exception narrowing (10 narrowed, 163 annotated)
- 0765e: Test file splitting (35 files split into 85 modules)
- 0765f: Security hardening (CSRF enabled, 2 tenant isolation fixes)
- 0765g: Tenant key encapsulation (zero hardcoded tenant keys)
- 0765h: Skipped test resolution (342 skipped tests -> 0)
- 0765i-r: 4 independent quality audits + 3 remediation rounds (scores: 8.2, 8.5, 8.5, 8.35)
- 0765s: Final remediation (cross-tenant slash command fix, 3 crash bugs, ~4,893 lines removed)
- **Result**: 67 commits, ~12,000+ lines dead code removed, 1,390 tests pass / 0 skipped, ESLint budget locked at 8, CSRF end-to-end
- **Note**: Target 9.5/10 not reached (best 8.5/10) — stopped due to diminishing returns across shifting audit criteria
- **Location**: `completed/` folder + `0765_chain_log-C.json`

### Typed Service Returns (0731a-d)
**Status:** 100% Complete (February 2026)
- 0731a: Pydantic Response Models + Design Validation
- 0731b: Tier 1 Service Refactor (User/Product)
- 0731c: Tier 2+3 Service Refactor (11 services)
- 0731d: API Endpoint Updates + Final Validation
- **Result**: 78 files changed, +7,048/-3,159 lines, 60+ Pydantic models, 157 TDD tests
- **Chain Log**: `prompts/0731_chain/chain_log.json`

### Agent Status Simplification (0491)
**Status:** 100% Complete (February 2026)
- Simplified 7-status model to 4 agent-reported + 1 server-detected (Silent) + 1 lifecycle (decommissioned)
- Removed: `failed` status, `cancelled` status, `failure_reason` column
- Added: Silent server-side detection (10-min threshold), MCP auto-clear, dashboard notification
- **Result**: 65 files, 5 commits

### 360 Memory Normalization (0390 Series)
**Status:** 100% Complete (January 2026)
- 0390: Master plan for JSONB to table migration
- 0390a: Add `product_memory_entries` table with foreign keys and indexes
- 0390b: Switch all read operations to use table via `ProductMemoryRepository`
- 0390c: Stop all writes to JSONB `sequential_history` array
- 0390d: Mark JSONB column as deprecated (removal scheduled for v4.0)
- **Result**: Normalized architecture with proper relational integrity

### Greptile Security Remediation (1000 Series)
**Status:** 80% Complete (12/15 handovers, December 2025)
- 1002-1006: Quick wins (bare except, path sanitization, cookies, pyproject sync, pip audit)
- 1007-1009: Production hardening (CSP nonces, security headers, rate limiting)
- 1010-1012: Code quality (lifespan refactor, repository pattern, bandit linting)
- 1013: Structured logging with 42 error codes
- **Deferred**: 1014 (security audit trail - compliance-focused)
- **Result**: Production-grade security posture

### Universal Reactive State Architecture (0379 Series)
**Status:** 100% Complete (December 2025)
- 0379a-e: Event Router, Agent/Job Migration, Messages, Backend Contract, SaaS Broker
- **Result**: Unified WebSocket platform - single manager, single store, central router

### Agent Lifecycle & Template Series (0411-0432)
**Status:** 100% Complete (January 2026)
- 0411-0423: Jobs Tab, Closeout, Display Names, Chapter Protocol, State Machine, Template Injection, Legacy Removal, Staleness, Dead Code
- 0425-0432: Platform Detection, Integration Icons, Sticky Header, Succession, Closeout Protocol, Template Harmonization
- **Result**: Clean agent lifecycle, proper state machine, template system modernized

### Multi-Terminal Production Parity (0497a-e + 0498)
**Status:** 100% Complete (February 2026)
- 0497a: Thin agent prompt (replaced stale bash-script generator)
- 0497b: Agent completion result storage + auto-message to orchestrator
- 0497c: Multi-terminal orchestrator implementation prompt
- 0497d: Agent protocol enhancements (/gil_add + git commit)
- 0497e: Fresh agent recovery flow (successor spawning with predecessor context)
- 0498: Early termination protocol + dashboard reduction (9→5 columns) + handover modal
- 0411a: Phase labels (execution order pill badges in Jobs tab)
- 0411b: Dead code cleanup (~11,900 lines of orphaned orchestration pipeline)
- **Result**: Full multi-terminal mode parity with CLI mode, smart project closeout

### Exception Handling REVISED Series (0480)
**Status:** 100% Complete (January 2026)
- 0480a-f: Foundation, Services Auth/Product, Services Core, Services Remaining, Endpoints, Frontend
- **Result**: Production-grade exception handling, proper HTTP status codes

### Alpha Trial Remediation Series (0356-0366)
**Status:** 100% Complete (10/10 handovers, December 2025 - February 2026)
- 0356-0362, 0364, 0366: All complete
- 0365: **SUPERSEDED** (2026-02-21). Replaced by UI-triggered handover + `build_continuation_prompt()`

### MCPAgentJob Cleanup Migration (0367 Series)
**Status:** 100% Complete (December 2025)
- **Result**: Zero MCPAgentJob imports in production code

### On-Demand Context Fetch Architecture (0350 Series)
**Status:** 100% Complete (December 2025)

### Mission Response JSON Restructuring (0347 Series)
**Status:** 100% Complete (December 2025)

### CLI Mode Series (0260, 0333-0344)
**Status:** Stage 1 Complete, Stage 2 Ready

### Message Counter Series (0286-0299)
**Status:** 100% Complete

### Context Management v2.0 (0312-0323)
**Status:** 100% Complete

### GUI Redesign (0243 Series)
**Status:** 100% Complete

### Remediation (0500-0515)
**Status:** 100% Complete

### Backend Refactoring (0120-0130)
**Status:** 89% Complete (8/9 handovers)

---

## Superseded Handovers

| ID | Title | Superseded By |
|----|-------|---------------|
| 0411 | Windows Terminal Agent Spawning | 0411a (phase labels) + 0411b (dead code cleanup). Auto-spawn shelved; advisory phase labels instead |
| 0419 | Long Polling Orchestrator Monitoring | Agent Lab feature: bash sleep polling via UI copy-paste (`AgentTipsDialog.vue`) |
| 0365 | Orchestrator Handover Behavior Injection | UI-triggered handover flow + `build_continuation_prompt()` |
| 0726 | Tenant Isolation Remediation | 0433 (24/25 findings were false positives) |
| 0348 | Product Context Gap Analysis | 0350 series (On-Demand Context Fetch) |
| 0246b | Vision Document Storage Simplification | 0352 (Vision Document Depth Refactor) |
| 0261 | Task MCP Surface Rationalization | 0334 (HTTP-Only MCP) |
| 0262 | Agent Mission Protocol Merge | 0334 (HTTP-Only MCP) |
| 0278 | Mode-Aware MCP Catalog Architecture | 0334 (HTTP-Only MCP) |
| 0319 | Context Management v3 Granular Fields | 0323 (Simplified approach) |
| 0304 | Enforce Token Budget Limit | Context v2.0 series |
| 0307 | Backend Default Field Priorities | Context v2.0 series |
| 0308 | Frontend Field Labels Tooltips | Context v2.0 series |
| 0309 | Token Estimation Improvements | Context v2.0 series |

---

## Reference Archives

All completed handovers are archived in `./completed/reference/` organized by range:

```
completed/reference/
+-- 0001-0100/    # Foundation
+-- 0101-0200/    # Architecture
+-- 0201-0300/    # GUI & Context
+-- 0301-0400/    # Services
+-- 0501-0600/    # Remediation
+-- 0601-0700/    # Migration
+-- analysis/     # Investigation reports
+-- archive/      # Old versions
+-- deprecated/   # Superseded specs
+-- harmonized/   # Merged handovers
+-- roadmaps/     # Planning docs
+-- sessions/     # Session handovers
+-- summaries/    # Summary docs
+-- superseded/   # Replaced by newer
```

---

## Numbering Convention

### Used Numbers by Range (Full Inventory)

**0001-0100** (Foundation): 0001-0020, 0022-0032, 0034-0054, 0060-0067, 0069-0096, 0100
**0101-0200** (Architecture): 0101-0132, 0135-0139
**0201-0300** (GUI & Context): 0225-0258, 0260-0276, 0278-0299
**0301-0400** (Services): 0300-0316, 0318-0365, 0371-0384, 0387-0397
**0401-0500** (Agent Monitoring): 0400-0434 (complete), 0440a-d (complete), 0460-0464 (complete), 0470 (complete), 0480-0498 (all complete/retired/cancelled). 0409 DEFERRED. No active handovers in range
**0500-0501** (Display Name + File Exists): Complete
**0501-0600** (Remediation): 0500-0515
**0601-0700** (Migration): 0600-0631
**0700-0769** (Code Quality — RESERVED): 0700-0708 (complete), 0720-0733 (complete), 0731 legacy (SUPERSEDED), 0732 release packaging (COMPLETE), 0732b screenshots (COMPLETE), 0740-0750 (complete), 0760 (proposal), 0765a-s (sprint, COMPLETE), 0766-0768 (triage chains), 0769a-g (Code Quality & Fragility Remediation Sprint, COMPLETE 2026-03-30). **Do NOT use for non-quality work. Range fully allocated.**
**0770-0799** (Edition Strategy & SaaS Architecture): 0770 (SaaS Edition Proposal, complete), 0771 (Edition Isolation Architecture, COMPLETE)
**0800-0807** (Enhancement & Triage): 0800a/b, 0801a/b, 0802a/b, 0803a, 0804a, 0805a, 0806a, 0807a (all complete)
**0808-0811** (Tier 2 Triage): 0808a, 0809a, 0810a, 0811a (all research complete, fixes in `f665c861`)
**0812** (Schema Cleanup): 0812 Remove unused task.job_id FK (COMPLETE, `95b9ec99`)
**0813** (Enhancement & Feature Series): 0813 Template Context Separation (COMPLETE)
**0814** (Enhancement & Feature Series): 0814 Template Manager UI Redesign (COMPLETE)
**0815** (Enhancement & Feature Series): 0815 Code Review Remediation March 2026 (COMPLETE)
**0816** (Enhancement & Feature Series): 0816 Vision Upload Progress UX Fix (COMPLETE)
**0817** (Enhancement & Feature Series): 0817 March 2026 Audit Cleanup Remainder (COMPLETE)
**0818** (Enhancement & Feature Series): 0818 WebSocket Modal State Preservation (COMPLETE)
**0819a-c** (Enhancement & Feature Series): 0819a Closeout UI State (COMPLETE), 0819b Notification Lifecycle (COMPLETE), 0819c Project Review Modal (COMPLETE)
**0820** (Enhancement & Feature Series): 0820 Remove Context Priority Framing (COMPLETE)
**0821** (Enhancement & Feature Series): 0821 Broadcast Deadlock Batch Counter Fix (COMPLETE)
**0822** (Enhancement & Feature Series): 0822 Memory Gate Quality Fixes (COMPLETE)
**0823** (Enhancement & Feature Series): 0823 Context Fetch Protocol Injection (COMPLETE, `6cf62fce`)
**0823b** (Enhancement & Feature Series): 0823b Move Depth Config to fetch_context Runtime (COMPLETE, `c3899cf7`)
**0824** (Enhancement & Feature Series): 0824 Closeout Self-Decommission Guard (COMPLETE)
**0825** (Enhancement & Feature Series): 0825 Agent Identity Separation from Mission Response (COMPLETE, `1aebbcd8`)
**0826** (Enhancement & Feature Series): 0826 Staging Completion Hardening (COMPLETE, `e972e2f9`+`ddfda73d`)
**0827** (Enhancement & Feature Series): 0827 Agent Reactivation & Continuation (COMPLETE, 7 commits, 4 phases: display names + auto-block + tools + todo_append)
**0828** (Enhancement & Feature Series): 0828 OAuth 2.1 PKCE Flow for MCP Client Authorization (ACTIVE)
**0844a-c** (Enhancement & Feature Series): 0844 Tenant Data Export/Import series (ALL NOT STARTED). 0844a export service, 0844b import+schema diff, 0844c frontend. Sequential with manual gates between phases.
**0860a-d** (Code Provenance & License Audit — PERMANENT, reusable): All phases COMPLETE (2026-03-30). CE: PASS, SaaS: PASS. Owner review cleared all 4 REVIEW items. **Handovers live in `audit/` folder (not `handovers/`) — never closed out, rerun before each major release.** Spec: `audit/CODE_PROVENANCE_LICENSE_AUDIT.md`. Results: `audit/AUDIT_SUMMARY.md`.
**1000-1014** (Greptile Security): 1000-1014

### Known Duplicate Numbers

- **0411**: "Jobs Tab Duration UX" (completed Jan) vs "Windows Terminal Agent Spawning" (SUPERSEDED Feb 24, split to 0411a+0411b) - RESOLVED
- **0481**: 2 files with same number - consolidate
- **0731**: "Typed Service Returns a-d" (COMPLETE) vs "Legacy Code Removal" (SUPERSEDED 2026-03-08) - different scope, both closed
- **0732**: "API Consistency Fixes" (COMPLETE 2026-02-23) vs "CE Release Packaging" (COMPLETE) - different scope, both closed
- **1000**: Main roadmap + status report - acceptable (one is reference)

### Current Gaps Available

- **0317**: Gap in 0301-0400 range
- **0398-0399**: Gaps in 0301-0400 range
- **0413, 0418, 0435-0439**: Gaps in 0401-0500 range
- **0441-0449, 0454-0459, 0465-0469, 0471-0479, 0493-0499**: Additional 0401-0500 gaps
- **0290**: Gap in 0201-0300 range (0277 filled)
- **0021, 0033, 0039, 0055-0059, 0068, 0097-0099**: Gaps in 0001-0100 range (0054 filled)
- **0133-0134**: Gaps in 0101-0200 range

### Naming Format

```
[NNNN]_[SHORT_DESCRIPTION].md
```
- All lowercase with underscores
- No dates in filename (dates in content)
- Suffix `-C` when completing and archiving

---

## History

### March 2026
- **Closeout Reconciliation (2026-03-15)**: Closed 3 handovers that had implementation commits but docs still showed active/not-started
  - 0818: All 3 phases committed (`d0bcbccb`, `1ae57033`, `a8fde2d4`, `0082cd0c`) but file said "Not Started"
  - 0820b: All 16 fixes committed (`6f4472e3`) but file said "Not Started"
  - 0822: All fixes committed (`8f72151c`) but file said "In Progress"
  - Archived 0820b_kickoff_prompt.md (companion doc, no longer needed)
  - Updated catalogue Quick Reference, Recently Closed, Numbering sections
  - Total: 0 active handovers remaining (2 deferred: 1014, TODO_vision)

### February 2026
- **Closeout Reconciliation (2026-02-28)**: Closed out 8 handovers that were implemented but not archived
  - 0411a, 0411b, 0497a-e, 0498: All had implementation commits but docs still said "Not Started" / "Ready"
  - Added completion summaries with git evidence to each file
  - Moved all 8 to `completed/` with `-C` suffix
  - Updated Active Handovers: reduced from 9 ready to 1 (0409 only)
  - Added Multi-Terminal Production Parity completed series
  - Logged 20+ undocumented commits (Feb 24-28) as part of 0497/0498 scope
  - Total: 322+ completed handovers in archive, 1 ready, 7 deferred

- **Git History Reconciliation (2026-02-23)**: Cross-validated catalogue + Feb report against all February git commits
  - Removed 0254 and 0298 from Deferred (both COMPLETE)
  - Added 0054, 0493, tenant isolation audit, 0700a-i, 0745a-f to Recently Completed
  - Cleaned up "Ready for Implementation" (removed 15 struck-through completed entries, kept 3 active)
  - Added 0411 as HIGH priority ready item
  - Fixed Quick Reference statuses (0382 COMPLETE, 0401-0500 range)
  - Added "Recently Closed" section consolidating all Feb closures
  - Separated 0731 (Legacy Code Removal, deferred) from 0731a-d (Typed Returns, complete)
  - Separated 0732 (API Fixes, ready) from 0732 (Release Packaging, deferred)
  - Total: 314 completed handovers in archive, 3 ready, 7 deferred

- **Full Catalogue Reconciliation (2026-02-12)**: Major cleanup - 60+ files archived
  - Moved 15 completed 0424 series files (f-n + overview/planning/status) to completed/
  - Moved 0433 (5 files), 0434 (2), 0485 (2), 0487 (1), 0490 (2) to completed/
  - Moved 0720 (1), 0725 (8), 0725b (4), 0726 superseded (1), 0727-0729 (3) to completed/
  - Moved 0730 series (8), 0731a-d (5), 0733 (1), 0750 series (5) to completed/
  - Fixed 0353 status: was "Ready" in catalogue but already in completed/ folder
  - Fixed 0425 contradictory status: removed stale "Ready" active section
  - Removed stale 0424 "NEW/Ready" active section (all phases complete)
  - Added missing entries: 0434, 0485, 0490, 0726 (superseded), 0727-0733
  - Updated all series completion summaries
  - Updated Quick Reference for all ranges

- **0492 API Key Security Hardening (2026-02-13)**: 6 commits, 34 new tests
  - 5-key-per-user limit, 90-day key expiry, passive IP logging
  - Database: `expires_at` column + `api_key_ip_log` table
  - Frontend: Expiry column with color-coded urgency, key count chip

- **0491 Agent Status Simplification (2026-02-13)**: 65 files, 5 commits
  - Simplified 7-status to 4 agent-reported + Silent + decommissioned
  - Removed failed/cancelled statuses, failure_reason column

- **0731 Typed Service Returns (2026-02-11)**: 78 files, 19 commits
  - 60+ Pydantic response models, 157 TDD tests

- **0750 Final Scrub (2026-02-11)**: ~110 files, ~15,800 lines removed

### January 2026
- **Catalogue Reconciliation (2026-01-29)**: Full reconciliation with completed/ folder and git commits
  - Added 25+ missing completed handovers (0411-0432, 0470, 0480 REVISED series)
  - Fixed 0362 status (marked COMPLETE, moved to completed/)
  - Updated 0480 series to reflect REVISED completion
  - Identified duplicate numbers needing cleanup (0411, 0424, 0481)

- **0480 Exception Handling REVISED Series (2026-01-28)**: Complete remediation

- **0460-0463 Series (2026-01-23 to 2026-01-25)**: Agent ID Swap & Ghost Agent Fixes

- **0390 Series (2026-01-18)**: 360 Memory Normalization

### December 2025
- **Numbering Cleanup (2025-12-19)**: Resolved conflicts for Alpha Trial series
- **Bulk Cleanup**: Retired 0117, 0256, 0331, 0340, 0341, 0344
- **0346-0352 Series**: All complete with full git evidence
- **0338, 0345a-e**: Vision Document Context Optimization (COMPLETE)
- **0325-0329**: Database and service fixes (COMPLETE)
- **0286-0299**: Message counter series (COMPLETE)

### November 2025
- 0300 Series: Context Management v2.0 (COMPLETE)
- 0243 Series: GUI Redesign (COMPLETE)
- 0246 Series: Orchestrator Workflow (COMPLETE)
- 0280-0283: Monolithic context series (CANCELLED)

### October-November 2025
- 0500-0515: Remediation Series (COMPLETE)
- 0120-0130: Backend Refactoring (89% complete)
- 0601: Nuclear Migration Reset (COMPLETE)

---

## See Also

- [HANDOVER_INSTRUCTIONS.md](./HANDOVER_INSTRUCTIONS.md) - How to write handovers
- [completed/README.md](./completed/README.md) - Archive documentation
