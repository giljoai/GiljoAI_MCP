# Handover Catalogue

**Purpose:** Central registry of all handovers - active, completed, and archived.

**Last Updated:** 2025-12-15 (Added 0351 Agent Name as Single Source of Truth)

---

## Quick Reference

| Range | Domain | Status |
|-------|--------|--------|
| 0001-0100 | Foundation & Installation | Mostly Complete |
| 0101-0200 | Refactoring & Architecture | Mostly Complete |
| 0201-0300 | GUI Redesign & Context v2 | Mostly Complete |
| 0301-0400 | Context Management & Services | Active Development |
| 0501-0600 | Remediation Series | Complete |
| 0601-0700 | Migration & Database | Complete |

---

## Active Handovers (In Root Folder)

### Ready for Implementation
| ID | Title | Status | Priority | Notes |
|----|-------|--------|----------|-------|
| 0331 | Message Audit Modal | Ready | High | UI feature, not started |
| 0340 | CLI Mode Two-Phase Architecture Summary | Ready (Stage 2) | High | Stage 1 complete |
| 0341 | CLI Mode Stage 2 Implementation Prompt | Ready for Agent | High | TDD spec ready |
| 0344 | CLI Mode Play Button API Fix | Ready | Critical | api.get bug + wrong URL |
| 0346 | Depth Config Field Standardization | Ready | High | Prerequisite for 0347 |
| 0347 | Mission Response YAML Restructuring | Ready | High | Depends on 0346, 93% token reduction |
| 0351 | Agent Name as Single Source of Truth | Ready | High | Semantic swap: agent_name for templates |

### In Progress / Partial
| ID | Title | Status | Priority | Notes |
|----|-------|--------|----------|-------|
| 0254 | Three Layer Instruction Cleanup | Partial | Medium | Some work done, not complete |
| 0256 | Task Templates Cleanup Followup | Partial | Low | Followup to earlier work |
| 0298 | Legacy Messaging Queue Cleanup | Not Started | Medium | Cleanup task |

### Reference Documents (Not Actionable)
| ID | Title | Type | Notes |
|----|-------|------|-------|
| 0274 | Comprehensive Orchestrator Investigation | Investigation | Reference only |
| 0274 | Orchestrator Fix Implementation | Implementation Guide | Reference |
| 0330a | Python Linting Report | Audit | Reference |
| 0330b | Frontend Linting Report | Audit | Reference |
| 0330c | Feature Catalogue Backend | Audit | Reference |
| 0330d | Feature Catalogue Frontend | Audit | Reference |
| 0330e | Delinting Risk Assessment | Audit | Reference |
| 0332 | Agent Staging and Execution Prompting Overview | Architecture | Reference |
| 0337 | E2E Test Report | Test Report | Reference |
| 0337 | Next Agent Summary | Session Doc | Reference |

### Deferred / Low Priority
| ID | Title | Status | Priority | Notes |
|----|-------|--------|----------|-------|
| 0083 | Harmonize Slash Commands | Deferred | Low | Filename says "Not_Done" |
| 0117 | Agent Role Refactor (8-Role System) | Assessment | Low | Research/assessment only |
| 0250 | HTTPS Enablement | Deferred | Low | Optional feature |
| 0284 | Address get_available_agents | Not Started | Medium | Enhancement |
| 9999 | One-Liner Installation System | Deferred | Low | Explicitly deferred |

### Should Be Archived (Complete but in Root)
| ID | Title | Evidence | Action |
|----|-------|----------|--------|
| 0260 | Claude Code CLI Mode Implementation | Commits: 907b4ad4, c3b5c1b8 | Move to completed/ |
| 0260d | Phase 4 Test Results | Test output doc | Move to completed/reference/ |
| 0261 | Claude Code CLI Implementation Prompt | Superseded by 0334 | Move to completed/ |
| 0261 | Task MCP Surface Rationalization | Superseded by 0334 | Move to completed/ |
| 0275 | Orchestrator Metadata Bug Fix | Part of 0274 series | Move to completed/reference/ |
| 0276 | Stage Project Refresh Complete | Commits: 44142e1f, 32c950de | Move to completed/ |
| 0279 | Context Priority Integration Fix | Commits: 57f11b0b, 92d05336 | Move to completed/ |
| 0287 | Launch Button Staging Complete Signal | Commits: 38b198cb, 31674721 | Move to completed/ |
| 0291 | Staging Complete Broadcast Signal | Commits: 1c32aff4, a336f1b3 | Move to completed/ |
| 0336 | Tech Stack Encoding and Token Estimation Fix | Commits: 62c5e86f, 30a8099a | Move to completed/ |
| 0343 | Frontend Execution Mode Lock TDD | Commits: 917db50a, a7553ff4, 25b60ec0 | Move to completed/ |

---

## Completed (In completed/ Folder)

### Recently Completed (December 2025)
| ID | Title | Status |
|----|-------|--------|
| 0260 | Claude Code CLI Mode | **COMPLETE** |
| 0262 | Agent Mission Protocol Merge Analysis | **COMPLETE** |
| 0286 | Jobs Dashboard WebSocket Wiring | **COMPLETE** |
| 0288 | Orchestration Service WebSocket Emissions | **COMPLETE** |
| 0289 | Message Routing Architecture Fix | **COMPLETE** (missing -C suffix) |
| 0292 | Session Handover WebSocket UI Issues | **COMPLETE** |
| 0293 | WebSocket Broadcast Root Cause Fix | **COMPLETE** |
| 0294 | Message Counter Series (6 files) | **COMPLETE** |
| 0295 | Messaging Contract and Categories | **COMPLETE** |
| 0296 | Agent Messaging Behavior and Templates | **COMPLETE** |
| 0297 | UI Message Status and Job Signaling | **COMPLETE** |
| 0297a | Session Realtime Message Counters | **COMPLETE** |
| 0299 | Unified UI Messaging Endpoint | **COMPLETE** |
| 0310 | Integration Testing Validation | **COMPLETE** |
| 0313 | SQLAlchemy Async Session Leak Fix | **COMPLETE** |
| 0325 | Tenant Isolation Surgical Fix | **COMPLETE** |
| 0326 | Message Auto-Acknowledge Simplification | **COMPLETE** |
| 0327 | Playwright Localhost Auth Fix | **COMPLETE** |
| 0328 | Product Service Recursion Fix | **COMPLETE** |
| 0329 | Project Deletion Cascade Messaging Cleanup | **COMPLETE** |
| 0333 | Staging Prompt Architecture Correction | **COMPLETE** |
| 0335 | CLI Mode Agent Template Validation (4 files) | **COMPLETE** |
| 0337 | CLI Mode Implementation Prompt | **COMPLETE** |
| 0338 | CPU-Based Vision Summarization | **COMPLETE** |
| 0345a | Lean Orchestrator Instructions | **COMPLETE** |
| 0345b | Sumy LSA Integration | **COMPLETE** |
| 0345c | Vision Settings UI | **COMPLETE** |
| 0345e | Sumy Compression Levels | **COMPLETE** |

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

### Vision Document Optimization (0338, 0345a-e)
**Status:** 100% Complete
- 0338: CPU-based summarization research
- 0345a: Lean orchestrator instructions (25K -> 2K tokens)
- 0345b: Sumy LSA integration (70-80% compression)
- 0345c: Vision Settings UI
- 0345e: Semantic compression levels (Light/Moderate/Heavy/Full)

### CLI Mode Series (0260, 0333-0344)
**Status:** Stage 1 Complete, Stage 2 Ready
- 0260: Claude Code CLI Mode foundation
- 0333: Staging Prompt Architecture Correction
- 0335: CLI Mode Agent Template Validation
- 0337: CLI Mode Implementation Prompt
- 0339: Agent Type Enforcement
- 0340-0341: Stage 2 specs (ready for implementation)
- 0343: Execution Mode Lock
- 0344: Play Button API Fix (ready)

### Message Counter Series (0286-0299)
**Status:** 100% Complete
- 0286: Jobs Dashboard WebSocket Wiring
- 0288: Orchestration Service WebSocket Emissions
- 0289: Message Routing Architecture Fix
- 0292-0294: WebSocket fixes and debugging
- 0295-0296: Messaging Contract and Templates
- 0297: UI Message Status and Job Signaling
- 0299: Unified UI Messaging Endpoint

### Context Management v2.0 (0312-0323)
**Status:** 100% Complete
- 0312: Context Architecture v2 Design
- 0313: Priority System Refactor
- 0314: Depth Controls Implementation
- 0315: MCP Thin Client Refactor
- 0316: Context Field Alignment
- 0318: Documentation Update
- 0323: Context Management Simplification

### GUI Redesign (0243 Series)
**Status:** 100% Complete
- 0243a-f: Nicepage Conversion Series
- 0234-0235: StatusBoard Components
- 0236-0239: Integration & Deployment

### Remediation (0500-0515)
**Status:** 100% Complete
- Vision upload with chunking
- Project lifecycle methods
- Orchestrator succession
- Settings endpoints
- Test suite restoration

### Backend Refactoring (0120-0130)
**Status:** 89% Complete (8/9 handovers)
- Service layer extraction
- ToolAccessor reduction (48%)
- Endpoint modularization

---

## Superseded Handovers

| ID | Title | Superseded By |
|----|-------|---------------|
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
├── 0001-0100/    # Foundation
├── 0101-0200/    # Architecture
├── 0201-0300/    # GUI & Context
│   ├── 0243_nicepage_redesign/
│   ├── 0244_series/
│   ├── 0246_series/
│   ├── 0248_series/
│   └── 0249_series/
├── 0301-0400/    # Services
├── 0501-0600/    # Remediation
├── 0601-0700/    # Migration
├── analysis/     # Investigation reports
├── archive/      # Old versions
├── deprecated/   # Superseded specs
├── harmonized/   # Merged handovers
├── roadmaps/     # Planning docs
├── sessions/     # Session handovers
├── summaries/    # Summary docs
└── superseded/   # Replaced by newer
```

---

## Numbering Convention

### Used Numbers by Range (Full Inventory)

**0001-0100** (Foundation): 0001-0020, 0022-0032, 0034-0053, 0060-0067, 0069-0096, 0100
**0101-0200** (Architecture): 0101-0132, 0135-0139
**0201-0300** (GUI & Context): 0225-0258, 0260-0276, 0278-0299
**0301-0400** (Services): 0300-0316, 0318-0347, 0351
**0501-0600** (Remediation): 0500-0515
**0601-0700** (Migration): 0600-0631

### Current Gaps Available
- **0317**: Gap in 0301-0400 range
- **0348-0350**: Gaps in 0301-0400 range
- **0259, 0277, 0290**: Gaps in 0201-0300 range
- **0021, 0033, 0039, 0054-0059, 0068, 0097-0099**: Gaps in 0001-0100 range
- **0133-0134**: Gaps in 0101-0200 range
- **0352+**: Next sequential after current development

### Naming Format
```
[NNNN]_[SHORT_DESCRIPTION].md
```
- All lowercase with underscores
- No dates in filename (dates in content)
- Suffix `-C` when completing and archiving

---

## Cleanup Actions Needed

### Files to Move from Root to completed/
1. `0260_claude_code_cli_mode_implementation.md` -> Add -C, move
2. `0260d_phase4_test_results.md` -> Move to reference
3. `0261_claude_code_cli_implementation_prompt.md` -> Mark superseded, move
4. `0261_task_mcp_surface_rationalization.md` -> Mark superseded, move
5. `0275_orchestrator_metadata_bug_fix.md` -> Move to reference
6. `0276_stage_project_refresh_complete.md` -> Add -C, move
7. `0279_context_priority_integration_fix.md` -> Add -C, move
8. `0287_launch_button_staging_complete_signal.md` -> Add -C, move
9. `0291_staging_complete_broadcast_signal.md` -> Add -C, move
10. `0336_TECH_STACK_ENCODING_AND_TOKEN_ESTIMATION_FIX.md` -> Add -C, move
11. `0343_FRONTEND_EXECUTION_MODE_LOCK_TDD.md` -> Add -C, move

### Files in completed/ Needing Fixes
1. `0289_message_routing_architecture_fix.md` -> Add `-C` suffix

### Series to Consolidate in Reference
1. **0294 series** (6 files) -> Create `reference/0201-0300/0294_series/`
2. **0335 series** (4 files) -> Create `reference/0301-0400/0335_series/`
3. **0345 series** (4 files) -> Create `reference/0301-0400/0345_series/`

---

## History

### December 2025
- **Harmonization audit**: Cross-referenced all handovers with git commits
- 0351: Agent Name as Single Source of Truth (ready for implementation)
- 0338, 0345a-e: Vision Document Context Optimization Series (COMPLETE)
- 0344: CLI Mode Play Button API Fix (ready for implementation)
- 0341: CLI Mode Stage 2 Implementation Prompt (ready for agent)
- 0340: CLI Mode Two-Phase Architecture Summary (Stage 2 pending)
- 0339: Stage 1 Agent Type Enforcement (COMPLETE)
- 0337: CLI Mode Implementation Prompt Fix (COMPLETE)
- 0335: CLI Mode Agent Template Validation (COMPLETE)
- 0334: HTTP-Only MCP Consolidation (COMPLETE)
- 0333: Staging Prompt Architecture Correction (COMPLETE)
- 0325-0329: Database and service fixes (COMPLETE)
- 0310, 0313: Testing and session fixes (COMPLETE)
- 0286-0299: Message counter series (COMPLETE)

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
