# Handover Catalogue

**Purpose:** Central registry of all handovers - active, completed, and archived.

**Last Updated:** 2025-12-22 (1000 Series Safe Batch: 1002, 1003, 1004, 1005, 1006, 1008, 1012 COMPLETE)

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

### Alpha Trial Remediation Series (0356-0362, 0364-0366) - MOSTLY COMPLETE
| ID | Title | Status | Priority | Est. Hours |
|----|-------|--------|----------|------------|
| 0356 | MCP Tool Parameter Consistency | **COMPLETE** | HIGH | - |
| 0357 | Agent Template Context Loading | **COMPLETE** | HIGH | - |
| 0358 | WebSocket & UI State Overhaul (+ a/b/c/d) | **COMPLETE** | HIGH | - |
| 0359 | Steps/Progress Tracking Fix | **COMPLETE** | HIGH | - |
| 0360 | Medium Priority Tool Enhancements | **COMPLETE** | MEDIUM | - |
| 0361 | Documentation Updates | **COMPLETE** | LOW | - |
| 0362 | WebSocket Message Counter Fixes | Ready | HIGH | 3-4h |
| 0364 | Protocol Message Handling Fix | **COMPLETE** | HIGH | - |
| 0365 | Orchestrator Handover Behavior Injection | Ready | MEDIUM | TBD |
| 0366 | Agent Identity Refactor (a/b/c/d) | **COMPLETE** | HIGH | - |

> **Status**: 8/10 COMPLETE. Remaining: 0362 (WebSocket counters), 0365 (handover behavior)
> See `completed/alpha_trial_remediation_roadmap-C.md` for full context.

### Ready for Implementation
| ID | Title | Status | Priority | Notes |
|----|-------|--------|----------|-------|
| 0246b | Vision Document Storage Simplification | **SUPERSEDED** | - | Superseded by 0352 (moved to superseded/) |
| 0348 | Product Context Gap Analysis | **SUPERSEDED** | - | Superseded by 0350 series (moved to completed/) |
| 0349 | Agent Execution Context Refactor | **COMPLETE** | - | Moved to completed/ (2025-12-21) |
| 0353 | Agent Team Awareness & Mission Context | Ready | Medium | Adds team info to missions |

### In Progress / Partial
| ID | Title | Status | Priority | Notes |
|----|-------|--------|----------|-------|
| 0254 | Three Layer Instruction Cleanup | Partial | Medium | Some work done, not complete |

### Greptile Security Series (1000-1014) - SECURITY
| ID | Title | Status | Priority | Notes |
|----|-------|--------|----------|-------|
| 1000 | Greptile Remediation Roadmap | Active | HIGH | Master roadmap |
| 1001 | Greptile Project Index | Reference | - | Index document |
| 1002 | Fix Bare Except | **COMPLETE** | HIGH | Moved to completed/ |
| 1003 | Sanitize Paths | **COMPLETE** | HIGH | Moved to completed/ |
| 1004 | Secure Cookies | **COMPLETE** | HIGH | Moved to completed/ |
| 1005 | Sync pyproject | **COMPLETE** | MEDIUM | Moved to completed/ |
| 1006 | Pip Audit | **COMPLETE** | HIGH | Moved to completed/ |
| 1007 | CSP Nonces | Ready | MEDIUM | Security enhancement (HIGH RISK) |
| 1008 | Security Headers | **COMPLETE** | MEDIUM | Moved to completed/ |
| 1009 | Rate Limiting | Ready | MEDIUM | Security enhancement (MEDIUM RISK) |
| 1010 | Lifespan Refactor | Ready | LOW | Refactoring (MEDIUM RISK) |
| 1011 | Repository Pattern | Ready | LOW | Architecture (HIGH RISK) |
| 1012 | Bandit Linting | **COMPLETE** | MEDIUM | Moved to completed/ |
| 1013 | Structured Logging | Deferred | LOW | Future (Phase 5) |
| 1014 | Security Auditing | Deferred | MEDIUM | Future (Phase 5) |

> **Status**: 7/15 COMPLETE. Safe batch executed 2025-12-22. Remaining: 1007 (HIGH risk), 1009-1011 (MEDIUM risk), 1013-1014 (deferred).

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
| 0083 | Harmonize Slash Commands | Deferred | Low | Future enhancement |
| 0250 | HTTPS Enablement | Deferred | Low | Optional feature |
| 0284 | Address get_available_agents | Not Started | Medium | Enhancement |
| 0298 | Legacy Messaging Queue Cleanup | Not Started | Medium | Cleanup task |
| 9999 | One-Liner Installation System | Deferred | Low | Explicitly deferred |

---

## Completed (In completed/ Folder)

### Recently Completed (December 2025)
| ID | Title | Status |
|----|-------|--------|
| 1002 | Fix Bare Except | **COMPLETE** (2025-12-22) |
| 1003 | Sanitize Paths | **COMPLETE** (2025-12-22) |
| 1004 | Secure Cookies | **COMPLETE** (2025-12-22) |
| 1005 | Sync pyproject | **COMPLETE** (2025-12-22) |
| 1006 | Pip Audit | **COMPLETE** (2025-12-22) |
| 1008 | Security Headers | **COMPLETE** (2025-12-22) |
| 1012 | Bandit Linting | **COMPLETE** (2025-12-22) |
| 0370 | Comprehensive agent_id vs job_id Audit | **COMPLETE** (2025-12-22) |
| 0372 | MessageService Unification (0366b merge) | **COMPLETE** (2025-12-22) |
| 0356 | MCP Tool Parameter Consistency | **COMPLETE** (2025-12-21) |
| 0357 | Agent Template Context Loading | **COMPLETE** (2025-12-21) |
| 0358 | WebSocket & UI State Overhaul | **COMPLETE** (2025-12-21) |
| 0358a | Launch Project Migration | **COMPLETE** (2025-12-21) |
| 0358b | Orchestration Service Migration | **COMPLETE** (2025-12-21) |
| 0358c | Tool Layer Migration | **COMPLETE** (2025-12-21) |
| 0358d | MCPAgentJob Deprecation | **COMPLETE** (2025-12-21) |
| 0359 | Steps/Progress Tracking Fix | **COMPLETE** (2025-12-21) |
| 0360 | Medium Priority Tool Enhancements | **COMPLETE** (2025-12-21) |
| 0361 | Documentation Updates (0366 Identity Model) | **COMPLETE** (2025-12-21) |
| 0364 | Protocol Message Handling Fix | **COMPLETE** (2025-12-19) |
| 0366 | Agent Identity Refactor Roadmap | **COMPLETE** (2025-12-20) |
| 0366a | Schema and Models | **COMPLETE** (2025-12-20) |
| 0366b | Service Layer Updates | **COMPLETE** (2025-12-20) |
| 0366c | MCP Tool Standardization | **COMPLETE** (2025-12-20) |
| 0366d | Frontend Updates (4 parts) | **COMPLETE** (2025-12-20) |
| 0367 | MCPAgentJob Cleanup Migration (9 files) | **COMPLETE** (2025-12-21) |
| 0368 | Test Migration Roadmap | **COMPLETE** (2025-12-21) |
| 0369 | Post-Refactor Quality Audit | **COMPLETE** (2025-12-21) |
| 0349 | Agent Execution Context Refactor | **COMPLETE** (2025-12-21) |
| 0117 | Agent Role Refactor (8-Role System) | **SUPERSEDED** by 0515 |
| 0256 | Task Templates Cleanup Followup | **COMPLETE** |
| 0331 | Message Audit Modal | **COMPLETE** |
| 0340 | CLI Mode Two-Phase Architecture Summary | **COMPLETE** |
| 0341 | CLI Mode Stage 2 Implementation | **COMPLETE** |
| 0342 | Agent Workflow & UI Fixes | **COMPLETE** (renumbered from 0361) |
| 0344 | CLI Mode Play Button API Fix | **COMPLETE** |
| 0351 | Agent Name as Single Source of Truth | **COMPLETE** |
| 0352 | Vision Document Depth Refactor | **COMPLETE** |
| 0354 | Agent Behavior Enforcement Fix | **COMPLETE** (renumbered from 0359) |
| 0355 | MCP Tool Template Fixes & Slash Command | **COMPLETE** |
| 0363 | Session: Agent Instruction Slimming | **COMPLETE** (renumbered from 0353 session doc) |
| 0346 | Depth Config Field Standardization | **COMPLETE** |
| 0347 | Mission Response JSON Restructuring (10 files) | **COMPLETE** |
| 0350 | On-Demand Context Fetch Architecture (7 files) | **COMPLETE** |
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

### Alpha Trial Remediation Series (0356-0361, 0364, 0366)
**Status:** 80% Complete (8/10 handovers, December 2025)
- 0356: MCP Tool Parameter Consistency (tenant_key, agent_id fixes)
- 0357: Agent Template Context Loading (user settings)
- 0358: WebSocket & UI State Overhaul (+ a/b/c/d sub-handovers)
- 0359: Steps/Progress Tracking Fix (protocol field alignment)
- 0360: Medium Priority Tool Enhancements (message filtering, get_team_agents)
- 0361: Documentation Updates (identity model, fetch_context patterns)
- 0364: Protocol Message Handling Fix
- 0366: Agent Identity Refactor (a/b/c/d - AgentJob/AgentExecution model)
- **Remaining**: 0362 (WebSocket counters), 0365 (handover behavior)
- See: `completed/alpha_trial_remediation_roadmap-C.md`

### MCPAgentJob Cleanup Migration (0367 Series)
**Status:** 100% Complete (December 2025)
- 0367: Kickoff + coordination document
- 0367a: Service layer cleanup (206 refs removed)
- 0367b: API endpoint migration (103 refs removed)
- 0367c-1: Monitoring + orchestrator cleanup (46 refs)
- 0367c-2: Tools + prompt generation cleanup (49 refs)
- 0367d: Validation & deprecation
- 0367e: Final identity cleanup
- 0368: Test migration roadmap (documented)
- 0369: Post-refactor quality audit
- **Result**: Zero MCPAgentJob imports in production code
- See: `completed/0367_mcpagentjob_cleanup_roadmap.md`

### Agent Name Single Source of Truth (0351)
**Status:** 100% Complete (December 2025)
- agent_name becomes template filename match field
- agent_type becomes display category only
- Single-category fetch_context calls (SaaS security)
- Commits: 7ff8c06e, 766af2dd, ea58b2c8

### Vision Document Depth Refactor (0352)
**Status:** 100% Complete (December 2025)
- Depth-based source selection (light/medium/full)
- Summary keys fix (moderate → medium)
- Migration from 'optional' to 'light' depth
- Commits: 0e3d7dca, c9592f45, d7cddaef

### On-Demand Context Fetch Architecture (0350 Series)
**Status:** 100% Complete (December 2025)
- 0350: Research → unified `fetch_context()` architecture decision
- 0350a: Unified fetch_context() MCP tool (~720 token savings)
- 0350b: Framing-based get_orchestrator_instructions() (~500 tokens vs 4-8K)
- 0350c: 3-Tier UI Labels + Field Rename (project_context → project_description)
- 0350d: Documentation Update (CLAUDE.md v3.0, API reference)
- Commits: 18c5fe19, cc17f382, 05c3429a, eb20bf88

### Mission Response JSON Restructuring (0347 Series)
**Status:** 100% Complete (December 2025)
- 0347: Parent orchestration document
- 0347a: JSONContextBuilder class (38 unit tests)
- 0347b: MissionPlanner JSON refactor (93% token reduction: 21K → ~2.7K)
- 0347c: Response Fields Enhancement (6 guidance fields)
- 0347d: Agent Templates Depth Toggle (type_only/full)
- 0347e: Vision Document 4-Level Depth (optional/light/medium/full)
- 0347f: Integration & E2E Testing (61 total tests)
- Bug fixes: Dynamic tier assignment, testing field key mismatch
- Commits: c239c70d, fbf74f21, 16e54673, d343473d, 5b949044, 884052ed

### Depth Config Field Standardization (0346)
**Status:** 100% Complete (December 2025)
- Canonical field name: `vision_documents` (replaces vision_chunking, vision_document_depth)
- 9 commits, 19 tests
- Root cause: Vision document selection ordering bug (created_at DESC)
- Commits: 8a9482af, f2680bd8, f05441ba

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
**0301-0400** (Services): 0300-0316, 0318-0365 (includes Alpha Trial 0356-0362, 0364-0365)
**0501-0600** (Remediation): 0500-0515
**0601-0700** (Migration): 0600-0631
**1000-1014** (Greptile Security): 1000-1014

### Current Gaps Available
- **0317**: Gap in 0301-0400 range
- **0259, 0277, 0290**: Gaps in 0201-0300 range
- **0021, 0033, 0039, 0054-0059, 0068, 0097-0099**: Gaps in 0001-0100 range
- **0133-0134**: Gaps in 0101-0200 range
- **0366+**: Next sequential after current development

### Naming Format
```
[NNNN]_[SHORT_DESCRIPTION].md
```
- All lowercase with underscores
- No dates in filename (dates in content)
- Suffix `-C` when completing and archiving

---

## History

### December 2025
- **Numbering Cleanup (2025-12-19)**: Resolved conflicts for Alpha Trial series
  - Renumbered: 0359→0354, 0361→0342, 0353 session→0363
  - Added: Alpha Trial series 0355-0362 (from TinyContacts feedback)
  - Added: Greptile Security series 1000-1014
  - Moved to completed: 0352, 0355 (MCP tool template fixes), 0363
- **Bulk Cleanup**: Retired 0117, 0256, 0331, 0340, 0341, 0344, MCPreport_nov28
  - 0331: Message Audit Modal (implemented)
  - 0341: CLI Mode Stage 2 (implemented)
  - 0344: Play Button API Fix (fixed)
  - 0256: Task Templates Cleanup (code removed)
  - 0117: Agent Role Refactor (superseded by 0515)
  - 0340: CLI Mode Summary (reference doc)
- **0351, 0352 RETIRED**: Both complete with full git evidence
- **0346, 0347, 0350 Series RETIRED**: All complete with full git evidence
- **Harmonization audit**: Cross-referenced all handovers with git commits
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
