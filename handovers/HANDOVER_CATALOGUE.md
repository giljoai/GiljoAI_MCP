# Handover Catalogue

**Purpose:** Central registry of all handovers - active, completed, and archived.

**Last Updated:** 2025-12-07 (0334 Plugin series deleted, replaced with HTTP-Only MCP Consolidation)

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

## Active Handovers

### Messaging & Communication (0295-0299)
| ID | Title | Status | Priority |
|----|-------|--------|----------|
| 0295 | Messaging Contract and Categories | Reference | - |
| 0296 | Agent Messaging Behavior and Templates | Reference | - |
| 0297 | UI Message Status and Job Signaling | **COMPLETE** (Steps gap → 0334) | - |
| 0298 | Legacy Messaging Queue Cleanup | Not Started | Medium |
| 0299 | Unified UI Messaging Endpoint | **COMPLETE** | High |

### Current Development (0300+)
| ID | Title | Status | Priority |
|----|-------|--------|----------|
| 0310 | Integration Testing Validation | **COMPLETE** | Medium |
| 0313 | SQLAlchemy Async Session Leak Fix | **COMPLETE** | High |
| 0325 | Tenant Isolation Surgical Fix | **COMPLETE** | High |
| 0326 | Message Auto-Acknowledge Simplification | **COMPLETE** | Medium |
| 0327 | Playwright Localhost Auth Fix | **COMPLETE** | Low |
| 0328 | Product Service Recursion Fix | **COMPLETE** | Low |
| 0329 | Project Deletion Cascade Messaging Cleanup | **COMPLETE** | Medium |
| 0330a-e | Codebase Quality Audit Series | Reference | Medium |
| 0331 | Message Audit Modal | Ready | High |
| 0332 | Agent Staging and Execution Prompting Overview | Reference | - |
| 0333 | Staging Prompt Architecture Correction | **COMPLETE** | High |
| 0334 | HTTP-Only MCP Consolidation | **COMPLETE** | High |
| 0335 | CLI Mode Agent Template Validation | **COMPLETE** | High |
| 0337 | CLI Mode Implementation Prompt Fix | **COMPLETE** | Critical |
| 0339 | Stage 1 Agent Type Enforcement | **COMPLETE** | High |
| 0340 | CLI Mode Two-Phase Architecture Summary | Ready (Stage 2) | High |
| 0341 | CLI Mode Stage 2 Implementation Prompt | Ready for Agent | High |

### Backlog (Various)
| ID | Title | Status | Priority |
|----|-------|--------|----------|
| 0083 | Harmonize Slash Commands | Not Started | Low |
| 0117 | Agent Role Refactor (8-Role System) | Assessment | Low |
| 0250 | HTTPS Enablement (Optional) | Not Started | Low |
| 0254 | Three Layer Instruction Cleanup | Not Started | Medium |
| 0256 | Task Templates Cleanup | Not Started | Low |
| 0260 | Claude Code CLI Mode | **COMPLETE** | Medium |
| 0261 | Task MCP Surface Rationalization | Superseded (0334) | Low |
| 0262 | Agent Mission Protocol Merge | Superseded (0334) | Medium |
| 0274 | Orchestrator Investigation | Reference | - |
| 0275 | Orchestrator Metadata Bug Fix | Reference | - |
| 0276 | Stage Project Refresh | Complete | - |
| 0279 | Context Priority Integration Fix | Complete | - |
| 0284 | Address get_available_agents | Not Started | Medium |
| 0287 | Launch Button Staging Signal | Complete | - |
| 0291 | Staging Complete Broadcast Signal | Complete | - |

---

## Completed Series

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

## Reference Archives

All completed handovers are archived in `./completed/reference/` organized by range:

```
completed/reference/
├── 0001-0100/    # Foundation
├── 0101-0200/    # Architecture
├── 0201-0300/    # GUI & Context
├── 0301-0400/    # Services
├── 0501-0600/    # Remediation
├── 0601-0700/    # Migration
├── analysis/     # Investigation reports
├── deprecated/   # Superseded specs
├── roadmaps/     # Planning docs
└── superseded/   # Replaced by newer
```

---

## Numbering Convention

### Choosing a Number
1. Check this catalogue for next available in appropriate range
2. Check `completed/reference/` for conflicts
3. Use gaps if appropriate

### Used Numbers by Range (Full Inventory)

**0001-0100** (Foundation): 0001-0020, 0022-0032, 0034-0053, 0060-0067, 0069-0096, 0100
**0101-0200** (Architecture): 0101-0132, 0135-0139
**0201-0300** (GUI & Context): 0225-0258, 0260-0276, 0278-0299
**0301-0400** (Services): 0300-0316, 0318-0334
**0501-0600** (Remediation): 0500-0515
**0601-0700** (Migration): 0600-0631

### Current Gaps Available
- **0317**: Gap in 0301-0400 range (documented)
- **0259, 0277, 0290**: Gaps in 0201-0300 range
- **0021, 0033, 0039, 0054-0059, 0068, 0097-0099**: Gaps in 0001-0100 range
- **0133-0134**: Gaps in 0101-0200 range
- **0335+**: Next sequential after current development

### Naming Format
```
[NNNN]_[SHORT_DESCRIPTION].md
```
- All lowercase with underscores
- No dates in filename (dates in content)
- Suffix `-C` when completing and archiving

---

## Usage

### Starting a New Handover
1. Consult this catalogue for available number
2. Check reference folders for conflicts
3. Create file: `handovers/[NNNN]_[description].md`
4. Update this catalogue under "Active Handovers"

### Completing a Handover
1. Add completion summary to handover document
2. Move to `completed/` with `-C` suffix
3. Update this catalogue (move to Completed)
4. Move to `completed/reference/[range]/` if archiving

### Marking as Reference
Some handovers become reference docs (not actionable):
- Investigation findings
- Architecture decisions
- Messaging contracts
- Design specifications

---

## History

### December 2025
- 0341: CLI Mode Stage 2 Implementation Prompt (Ready for TDD Implementor agent)
- 0340: CLI Mode Two-Phase Architecture Summary (Stage 2 pending)
- 0339: Stage 1 Agent Type Enforcement (COMPLETE - belt-and-suspenders)
- 0337: CLI Mode Implementation Prompt Fix (COMPLETE - 6 subagents, 23 tests passing)
- 0335: CLI Mode Agent Template Validation (COMPLETE)
- 0334: HTTP-Only MCP Consolidation (consolidates 0261, 0262, 0297 gaps)
- 0333: Staging Prompt Architecture Correction (COMPLETE)
- 0332: Agent Staging and Execution Prompting Overview (reference)
- 0331: Message Audit Modal (UI feature)
- 0330a-e: Codebase Quality Audit Series (Reference)
- 0329: Project Deletion Cascade Messaging Cleanup (COMPLETE)
- 0328: Product Service Recursion Fix (COMPLETE)
- 0327: Playwright Localhost Auth Fix (COMPLETE)
- 0326: Message Auto-Acknowledge Simplification (COMPLETE)
- 0325: Tenant Isolation Surgical Fix (COMPLETE)
- 0313: SQLAlchemy Async Session Leak Fix (COMPLETE)
- 0310: Integration Testing Validation (COMPLETE)
- 0299: Unified UI Messaging Endpoint (COMPLETE)
- 0295-0298: Messaging Contract Series

**Note:** 0334a-e (Claude Code Plugin series) were deleted - research showed Claude Code plugins are file-based, not HTTP-fetched. Using existing export/import flow instead.

### November 2025
- 0300 Series: Context Management v2.0 (COMPLETE)
- 0243 Series: GUI Redesign (COMPLETE)
- 0246 Series: Orchestrator Workflow (COMPLETE)

### October-November 2025
- 0500-0515: Remediation Series (COMPLETE)
- 0120-0130: Backend Refactoring (89% complete)
- 0601: Nuclear Migration Reset (COMPLETE)

---

## See Also

- [HANDOVER_INSTRUCTIONS.md](./HANDOVER_INSTRUCTIONS.md) - How to write handovers
- [HANDOVER_QUICK_REFERENCE.md](./HANDOVER_QUICK_REFERENCE.md) - Quick checklist
- [completed/README.md](./completed/README.md) - Archive documentation
