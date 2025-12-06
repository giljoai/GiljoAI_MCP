# Handover Catalogue

**Purpose:** Central registry of all handovers - active, completed, and archived.

**Last Updated:** 2025-12-06

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
| 0297 | UI Message Status and Job Signaling | Reference | - |
| 0298 | Legacy Messaging Queue Cleanup | Not Started | Medium |
| 0299 | Unified UI Messaging Endpoint | **COMPLETE** | High |

### Current Development (0300+)
| ID | Title | Status | Priority |
|----|-------|--------|----------|
| 0310 | Integration Testing Validation | In Progress | Medium |
| 0325 | **Tenant Isolation Surgical Fix** | **READY** | **HIGH** |
| 0326 | Message Auto-Acknowledge Simplification | Not Started | Medium |
| 0327 | Playwright Localhost Auth Fix | Not Started | Low |
| 0328 | Product Service Recursion Fix | Not Started | Low |
| 0330a-e | **Codebase Quality Audit Series** | Reference | Medium |
| 0331 | **Message Audit Modal** | **READY** | **HIGH** |

### Backlog (Various)
| ID | Title | Status | Priority |
|----|-------|--------|----------|
| 0083 | Harmonize Slash Commands | Not Started | Low |
| 0117 | Agent Role Refactor (8-Role System) | Assessment | Low |
| 0250 | HTTPS Enablement (Optional) | Not Started | Low |
| 0254 | Three Layer Instruction Cleanup | Not Started | Medium |
| 0256 | Task Templates Cleanup | Not Started | Low |
| 0260 | Claude Code CLI Mode | Not Started | Medium |
| 0261 | Task MCP Surface Rationalization | Not Started | Low |
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

### Used Numbers by Range (Reference Archives)

**0001-0100** (Foundation): 0016, 0043, 0047, 0062, 0064-0067, 0075, 0077
**0101-0200** (Architecture): 0102-0107
**0201-0300** (GUI & Context): 0225-0239, 0242-0258, 0262-0273, 0281-0285
**0301-0400** (Services): 0300-0303, 0305-0306, 0309, 0311-0316, 0318, 0320-0324
**0501-0600** (Remediation): 0500-0509, 0511-0515
**0601-0700** (Migration): 0601

### Current Gaps Available
- **0304, 0307, 0308, 0317, 0319**: Gaps in 0301-0400 range
- **0332+**: Next sequential after current development

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
- 0331: Message Audit Modal (UI feature)
- 0330a-e: Codebase Quality Audit Series (Reference)
  - 0330a: Python Linting Report
  - 0330b: Frontend Linting Report
  - 0330c: Backend Feature Catalogue
  - 0330d: Frontend Feature Catalogue
  - 0330e: De-Linting Risk Assessment
- 0325: Tenant Isolation Surgical Fix (security)
- 0299: Unified UI Messaging Endpoint (COMPLETE)
- 0295-0298: Messaging Contract Series

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
