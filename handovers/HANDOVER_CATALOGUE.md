# Handover Catalogue

**Purpose:** Central registry of all handovers - active, completed, and archived.

**Last Updated:** 2026-02-28 (0411a/b, 0497a-e, 0498 closed out + reconciliation)

---

## Quick Reference

| Range | Domain | Status |
|-------|--------|--------|
| 0001-0100 | Foundation & Installation | Mostly Complete |
| 0101-0200 | Refactoring & Architecture | Mostly Complete |
| 0201-0300 | GUI Redesign & Context v2 | Mostly Complete |
| 0301-0400 | Context Management & Services | 0371 COMPLETE, 0365 SUPERSEDED, 0382 COMPLETE |
| 0401-0500 | Agent Monitoring & Org Hierarchy | 0424-0498 ALL COMPLETE, 0440a-d ALL COMPLETE, 0486 CANCELLED. Active: 0409 only |
| 0501-0600 | Remediation Series | Complete |
| 0601-0700 | Migration & Database | Complete |
| 0700-0750 | Code Cleanup Series | 0700-0750 ALL COMPLETE, 0731 legacy DEFERRED, 0732 fixes COMPLETE |
| 0760 | Perfect Score Proposal | Active — research phase, proposal at `handovers/0700_series/0760_PERFECT_SCORE_PROPOSAL.md` |

---

## Active Handovers (In Root Folder)

### Ready for Implementation

| ID | Title | Status | Priority | Notes |
|----|-------|--------|----------|-------|
| 0409 | Unified Client Quick Setup | Ready | Medium | Future enhancement |

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
| 0083 | Harmonize Slash Commands | Deferred | Low | Post-v1.0 |
| 0250 | HTTPS Enablement | Deferred | Low | Optional feature |
| 0284 | Address get_available_agents | Deferred | Low | Enhancement |
| 0731 | Legacy Code Removal | Deferred | Medium | Post-v1.0 (separate from completed 0731a-d typed returns) |
| 0732 | Open Source Release Packaging | Deferred | Medium | Post-v1.0 (0732 API Fixes now COMPLETE, this is the release packaging handover) |
| 1014 | Security Auditing | Deferred | Medium | Enterprise compliance |
| 9999 | One-Liner Installation System | Deferred | Low | Parking lot / future ideas |

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
**0401-0500** (Agent Monitoring): 0400-0434 (complete), 0440a-d (complete), 0460-0464 (complete), 0470 (complete), 0480-0498 (all complete/retired/cancelled). Active: 0409 only
**0500-0501** (Display Name + File Exists): Complete
**0501-0600** (Remediation): 0500-0515
**0601-0700** (Migration): 0600-0631
**0700-0750** (Code Cleanup): 0700-0708 (complete), 0720-0733 (complete), 0731 legacy/0732 (deferred/ready), 0740-0750 (complete)
**1000-1014** (Greptile Security): 1000-1014

### Known Duplicate Numbers

- **0411**: "Jobs Tab Duration UX" (completed Jan) vs "Windows Terminal Agent Spawning" (SUPERSEDED Feb 24, split to 0411a+0411b) - RESOLVED
- **0481**: 2 files with same number - consolidate
- **0731**: "Typed Service Returns a-d" (COMPLETE) vs "Legacy Code Removal" (DEFERRED) - different scope, acceptable
- **1000**: Main roadmap + status report - acceptable (one is reference)

### Current Gaps Available

- **0317**: Gap in 0301-0400 range
- **0398-0399**: Gaps in 0301-0400 range
- **0413, 0418, 0435-0439**: Gaps in 0401-0500 range
- **0441-0449, 0454-0459, 0465-0469, 0471-0479, 0493-0499**: Additional 0401-0500 gaps
- **0259, 0277, 0290**: Gaps in 0201-0300 range
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
