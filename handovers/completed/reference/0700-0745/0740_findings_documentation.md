# 0740 Findings: Documentation Debt

**Date**: 2026-02-10
**Agent**: Documentation Manager
**Audit Type**: Comprehensive Post-Cleanup Documentation Audit (Audit #7 of 0740 series)
**Status**: Complete

---

## Executive Summary

The GiljoAI MCP documentation has significant debt across all categories. The
most critical findings are:

1. **P0 Security**: README_FIRST.md contains contradictory admin credential
   information -- one section says "no defaults" while another says
   "admin/admin". This is a security-relevant documentation error.

2. **P1 High**: 42+ broken links in README_FIRST.md alone. The majority of
   links to handover files, testing docs, and legacy guides point to files
   that no longer exist (likely purged during cleanup or archive operations).

3. **P1 High**: SERVICES.md describes `AgentExecution.messages` JSONB as
   "deprecated, will be removed in v4.0" -- but it was already removed in
   Handover 0700c. Similarly, `instance_number` has been removed from the
   codebase but is documented as active in 15+ non-archive docs.

4. **P2 Medium**: Multiple docs (TESTING.md, ORCHESTRATOR.md, succession
   guides) contain code examples using `trigger_succession()` and dict
   wrapper patterns (`{"success": True}`) that no longer match the actual
   codebase after the 0700/0730 series.

5. **P2 Medium**: Missing documentation for 0730-series features (service
   response models architecture, exception mapping patterns, UUID test
   fixtures).

6. **P3 Low**: The `docs/manuals/` directory referenced in README_FIRST.md
   and CLAUDE.md does not exist. The `docs/testing/` directory contains
   only one file, not the 12+ files linked from README_FIRST.md.

---

## Methodology

1. Searched all `docs/**/*.md` files for references to features removed in
   the 0700 series: light mode, dict wrappers, AgentExecution.messages
   JSONB, sequential_history, OrchestratorPromptGenerator, instance_number.
2. Cross-referenced documented database fields and model attributes against
   the actual codebase in `src/giljo_mcp/models/`.
3. Extracted all markdown links `[text](path)` from core docs and verified
   target files exist on disk.
4. Reviewed code examples in active docs against current patterns.
5. Checked CLAUDE.md sections against current codebase state.
6. Assessed README.md against open-source readiness criteria.

---

## Findings (by priority)

### P0 Critical

#### P0-1: Contradictory Admin Credentials in README_FIRST.md

**File**: `docs/README_FIRST.md`
**Lines**: 173 vs 298-301

Line 173 states:
```
- No default credentials (admin/admin eliminated)
```

Lines 298-301 state:
```
**Default Admin Account**:
- Created during installation
- Username: `admin`
- Password: `admin` (temporary, must change)
```

**Impact**: Security-relevant. New developers or users reading the Security
Setup section may believe admin/admin credentials exist. Per CLAUDE.md, the
correct behavior is: "First user created via /welcome -> /first-login (no
defaults)".

**Fix**: Remove lines 296-303 (the entire "Default Admin Account" block)
and replace with text explaining the first-login flow. This section is in
the "Security Setup > User Management" area.

---

### P1 High

#### P1-1: SERVICES.md Says JSONB "Deprecated" When Already Removed

**File**: `docs/SERVICES.md`
**Lines**: 81-88

```markdown
#### DEPRECATED: JSONB Messages Array

The `AgentExecution.messages` JSONB column is deprecated as of v3.2
(Handover 0387i).
- Do NOT write to this column
- Do NOT read from this column
- Use counter columns instead
- Column will be removed in v4.0
```

**Reality**: The column was already removed in Handover 0700c. The model
file `src/giljo_mcp/models/agent_identity.py` has no `messages` JSONB
column. This section should state "REMOVED" not "DEPRECATED" and drop the
"will be removed in v4.0" language.

#### P1-2: instance_number Removed From Codebase But Documented as Active

**Scope**: 15+ non-archive documentation files reference `instance_number`
as a current database column and active feature.

The field `instance_number` returns **zero results** when searching
`src/giljo_mcp/` and `api/`. It has been removed from the codebase. However
it appears in active documentation as if it is current:

| File | Lines | Context |
|------|-------|---------|
| `docs/SERVICES.md` | 240, 248 | "Spawn successor orchestrator (instance_number++)" and DB field list |
| `docs/TESTING.md` | 269, 336, 339 | Test assertions using `instance_number` |
| `docs/ORCHESTRATOR.md` | 892, 921, 1069 | DB schema, code examples, succession flow |
| `docs/README_FIRST.md` | 710 | "Database schema: 7 new columns (instance_number, ...)" |
| `docs/guides/orchestrator_succession_developer_guide.md` | 160-1192 (30+ refs) | Full developer guide built around instance_number |
| `docs/guides/succession_quick_ref.md` | 49-173 (15+ refs) | Quick reference built around instance_number |
| `docs/api/agent_jobs_endpoints.md` | 202-459 (10+ refs) | API endpoint docs with instance_number in responses |
| `docs/api/prompts_endpoints.md` | 45 | Request body includes instance_number |
| `docs/user_guides/agent_monitoring_guide.md` | 377 | UI field description |
| `docs/guides/thin_client_migration_guide.md` | 88, 118 | Code examples with instance_number |
| `docs/architecture/ORCHESTRATOR_CONTEXT_FLOW_SSoT.md` | 115, 1308 | Architecture docs |
| `docs/architecture/schema_mapping_report.md` | 131-671 | Schema mapping report |

#### P1-3: 42+ Broken Links in README_FIRST.md

The majority of links in `docs/README_FIRST.md` point to files that do not
exist. These are critical because README_FIRST.md is designated as the
"authoritative entry point" per CLAUDE.md.

**Missing target files** (linked from README_FIRST.md):

| Link Target | Referenced On Line |
|-------------|--------------------|
| `USER_STRUCTURES_TENANTS.md` | 10 |
| `FIRST_LAUNCH_EXPERIENCE.md` | 13 |
| `MCP_OVER_HTTP_INTEGRATION.md` (in docs/) | 14 |
| `SSoT_INDEX.md` | 20 |
| `AI_TOOL_CONFIGURATION_MANAGEMENT.md` | 25 |
| `TEMPLATE_SYSTEM_EVOLUTION.md` | 26 |
| `developer_guides/orchestrator_succession_developer_guide.md` | 600 |
| `quick_reference/succession_quick_ref.md` | 604 |
| `TESTING_GUIDE.md` | 1158 |
| `UI_UX_IMPLEMENTATION_STATUS_SUMMARY.md` | 609 |
| `VUE_COMPONENT_BRAND_CONSISTENCY_AUDIT.md` | 610 |
| `VUETIFY_THEME_CONFIGURATION_VERIFICATION.md` | 611 |
| `ASSET_INTEGRATION_TESTING.md` | 612 |
| `WCAG_2.1_AA_ACCESSIBILITY_VERIFICATION.md` | 613 |
| `INSTALLATION_VALIDATION_SUMMARY.md` | 1124, 1190 |
| `MARKETING_CLAIMS_RECOMMENDATIONS.md` | 1125 |
| `test_reports/INSTALLATION_TEST_REPORT_HANDOVER_0014.md` | 1126 |
| `WCAG_2_1_AA_ACCESSIBILITY_AUDIT.md` | 1191 |
| `TECHNICAL_ARCHITECTURE.md` | 584 |
| `docs/manuals/MCP_TOOLS_MANUAL.md` | 589 |
| `docs/manuals/TESTING_MANUAL.md` | 591 |
| All `testing/HANDOVER_0046_*` links | 1169-1171 |
| All `testing/HANDOVER_0047_*` links | 1177-1178 |
| All `testing/HANDOVER_0052_*` links | 1184-1186 |
| `testing/BACKUP_TEST_SUMMARY.md` | 1192 |
| All `handovers/completed/00*` links | 663-1040 (26+ files) |
| `../MIGRATION_GUIDE_V3_TO_V3.1.md` | 885, 912 |
| `../references/0045/*` | 909-911 |
| `../handovers/0050_*` | 1010-1011 |
| `../docs/handovers/0041/` | 811 |

**Note**: The files in `docs/guides/` DO exist for succession docs (the
links just use wrong relative paths: `developer_guides/` vs `guides/`).

#### P1-4: ORCHESTRATOR.md Contains Outdated Dict Wrapper Code Examples

**File**: `docs/ORCHESTRATOR.md`
**Lines**: 411, 728, 811, 1239

Multiple code examples show dict wrapper return patterns:
```python
"success": True
"success": False
```

After the 0730 series, services use exception-based returns. These examples
should be updated to show the current patterns (direct return on success,
exception on error).

#### P1-5: TESTING.md Contains Outdated Code Examples

**File**: `docs/TESTING.md`

| Line | Issue |
|------|-------|
| 241 | `assert vision_result['success'] is True` -- dict wrapper pattern |
| 269 | `assert orchestrator.instance_number == 1` -- removed field |
| 324, 328 | `await service.trigger_succession()` -- removed method (0700d) |
| 336, 339 | `assert job2.instance_number == 2` / `job3.instance_number == 3` -- removed field |
| 389 | `assert data['success'] is True` -- dict wrapper pattern |

The TESTING.md "Last Updated" date is 2025-11-15, predating all 0700 changes.

#### P1-6: Succession Guides Completely Outdated

**Files**:
- `docs/guides/orchestrator_succession_developer_guide.md` (1192 lines)
- `docs/guides/succession_quick_ref.md` (173 lines)

Both files are built entirely around the `instance_number` field,
`trigger_succession()` method, and dict wrapper patterns -- all of which
have been removed. The developer guide references the API endpoint
`POST /agent_jobs/{job_id}/trigger_succession` which should now be
`POST /api/agent-jobs/{job_id}/simple-handover` per SERVICES.md line 190.

---

### P2 Medium

#### P2-1: Missing Documentation for 0730 Service Response Models

**Feature**: Service response model architecture (0730a)
**File exists**: `docs/architecture/service_response_models.md`
**Issue**: The document catalogs the OLD dict wrapper patterns in the
"Current State" column. It was written as a design document for the
migration, but does not document the COMPLETED state. The "New Pattern"
column shows the planned approach, but the document has not been updated to
confirm implementation.

**Also**: `docs/architecture/exception_mapping.md` exists and documents the
exception hierarchy well, but lines 81, 222, 229-230 still show the "Current
Pattern (Dict Wrapper)" as if it is the current state, not the old state.

#### P2-2: Missing Documentation for 0730e Test Patterns

**Feature**: UUID test fixtures, cleanup fixture patterns from 0730e
**Docs Needed**: Test pattern guide or update to TESTING.md showing the new
fixture patterns (uuid_factory, cleanup_fixture, etc.)
**Priority**: Medium -- developers writing new tests need these patterns.

#### P2-3: context_tools.md References sequential_history

**File**: `docs/api/context_tools.md`
**Line**: 298

The `memory_360` example response still shows `sequential_history` as a
JSONB array field, which was removed in 0700c:
```json
{
  "sequential_history": [...]
}
```

The response should instead document the normalized
`product_memory_entries` table format.

#### P2-4: OrchestratorPromptGenerator in Active Migration Guide

**File**: `docs/guides/thin_client_migration_guide.md`
**Lines**: 31, 65, 69, 72, 98, 102, 243, 251, 259

This migration guide still describes `OrchestratorPromptGenerator` as
"deprecated" (line 243) or "available with warning" (line 251), when it was
fully removed in Handover 0700f. The guide's phased timeline (Phase 1:
deprecated, Phase 2: warning, Phase 3: removed) should be collapsed to
reflect the completed removal.

#### P2-5: ORCHESTRATOR_SIMULATOR.md Uses Dict Wrapper Patterns

**File**: `docs/testing/ORCHESTRATOR_SIMULATOR.md`
**Lines**: 125, 194, 319, 372, 388, 439

All test examples use `{"success": True}` / `{"success": False}` patterns
and `assert result["success"] is True`.

#### P2-6: MCPAgentJob Referenced as Deprecated But May Need Full Removal

**Scope**: Multiple active docs reference `MCPAgentJob` with "deprecated as
of v3.3.0" notes. The model class no longer exists in the codebase
(replaced by `AgentJob` + `AgentExecution` in Handover 0366). Some docs
still use `MCPAgentJob` in code examples:

| File | Lines | Context |
|------|-------|---------|
| `docs/SERVICES.md` | 265, 270, 560, 569-573 | Code example with MCPAgentJob query |
| `docs/ORCHESTRATOR.md` | 37, 133, 258, 282, 344 | Architecture diagrams and code refs |
| `docs/SERVER_ARCHITECTURE_TECH_STACK.md` | 504, 508, 837, 900 | Schema docs |

---

### P3 Low

#### P3-1: docs/manuals/ Directory Does Not Exist

**Referenced in**: CLAUDE.md (line referencing MCP_TOOLS_MANUAL.md),
README_FIRST.md lines 589, 591

The `docs/manuals/` directory does not exist on disk. CLAUDE.md references
it in the documentation structure section. This suggests the planned
directory structure was never implemented or the files were moved.

#### P3-2: docs/testing/ Has Only One File

**Expected**: 12+ files linked from README_FIRST.md (HANDOVER_0046_*,
HANDOVER_0047_*, HANDOVER_0052_*, BACKUP_TEST_SUMMARY.md)
**Actual**: Only `ORCHESTRATOR_SIMULATOR.md` exists in `docs/testing/`.

#### P3-3: VERIFICATION_OCT9.md Missing (Linked from README.md)

**File**: `README.md` line 109
**Link**: `docs/VERIFICATION_OCT9.md`
**Status**: File does not exist.

#### P3-4: STARTUP_SIMPLIFICATION.md Missing (Linked from README.md)

**File**: `README.md` line 96
**Link**: `docs/guides/STARTUP_SIMPLIFICATION.md`
**Status**: File does not exist.

#### P3-5: SECURITY.md Missing (Linked from README.md Badge)

**File**: `README.md` line 8
**Badge link**: `SECURITY.md`
**Status**: File does not exist at project root.

#### P3-6: CONTRIBUTING.md Missing

**Referenced in**: `docs/README_FIRST.md` line 1236
**Status**: File does not exist at project root.

#### P3-7: Broken Handover Links from ORCHESTRATOR.md

| Link Target | Line |
|-------------|------|
| `handovers/orchestrator_workflow_after246.md` | 1578 |
| `handovers/0355_protocol_message_handling_fix.md` | 681 |

#### P3-8: Broken Links from HANDOVERS.md

| Link Target | Line |
|-------------|------|
| `handovers/CCW_OR_CLI_EXECUTION_GUIDE.md` | 445 |
| `handovers/completed/0132_remediation_project_complete.md` | 447 |
| `handovers/REFACTORING_ROADMAP_0131-0200.md` | 448 |

---

## Outdated References

| File | Line | Reference | Status | Notes |
|------|------|-----------|--------|-------|
| `docs/SERVICES.md` | 81-88 | `AgentExecution.messages` JSONB deprecated | STALE | Already removed in 0700c, not just deprecated |
| `docs/SERVICES.md` | 240, 248 | `instance_number` field | STALE | Removed from codebase |
| `docs/SERVICES.md` | 569-573 | `MCPAgentJob` import and query | STALE | Class removed, use AgentJob |
| `docs/TESTING.md` | 241, 389 | `vision_result['success']` dict wrapper | STALE | Exception-based since 0730 |
| `docs/TESTING.md` | 269, 336, 339 | `instance_number` assertions | STALE | Field removed |
| `docs/TESTING.md` | 324, 328 | `trigger_succession()` method | STALE | Removed in 0700d |
| `docs/ORCHESTRATOR.md` | 411, 728, 811, 1239 | Dict wrapper `"success": true/false` | STALE | Exception-based since 0730 |
| `docs/ORCHESTRATOR.md` | 892, 921, 1069 | `instance_number` | STALE | Field removed |
| `docs/ORCHESTRATOR.md` | 37, 133, 258, 282, 344 | `MCPAgentJob` references | STALE | Use AgentJob/AgentExecution |
| `docs/README_FIRST.md` | 298-301 | admin/admin credentials | WRONG | No default credentials |
| `docs/README_FIRST.md` | 471 | "Alembic migrations" | STALE | NOT using Alembic (line 481 contradicts) |
| `docs/README_FIRST.md` | 710 | `instance_number` in column list | STALE | Field removed |
| `docs/api/context_tools.md` | 298 | `sequential_history` response | STALE | Removed in 0700c |
| `docs/guides/thin_client_migration_guide.md` | 31-259 | `OrchestratorPromptGenerator` | STALE | Fully removed in 0700f |
| `docs/guides/orchestrator_succession_developer_guide.md` | 160-1192 | `instance_number` throughout | STALE | Field removed |
| `docs/guides/succession_quick_ref.md` | 49-173 | `instance_number`, `trigger_succession` | STALE | Both removed |
| `docs/architecture/exception_mapping.md` | 81, 222-230 | "Current Pattern (Dict Wrapper)" | STALE | Dict wrappers removed in 0730 |
| `docs/testing/ORCHESTRATOR_SIMULATOR.md` | 125-439 | Dict wrapper patterns | STALE | Exception-based since 0730 |

---

## Broken Links

### README_FIRST.md (from docs/ directory context)

| Line | Link Target | Status |
|------|------------|--------|
| 10 | `USER_STRUCTURES_TENANTS.md` | MISSING |
| 13 | `FIRST_LAUNCH_EXPERIENCE.md` | MISSING (exists at `docs/user_guides/FIRST_LAUNCH_EXPERIENCE.md`) |
| 14 | `MCP_OVER_HTTP_INTEGRATION.md` | MISSING (exists at `docs/api/MCP_OVER_HTTP_INTEGRATION.md`) |
| 20 | `SSoT_INDEX.md` | MISSING |
| 25 | `AI_TOOL_CONFIGURATION_MANAGEMENT.md` | MISSING (exists at `docs/guides/AI_TOOL_CONFIGURATION_MANAGEMENT.md`) |
| 26 | `TEMPLATE_SYSTEM_EVOLUTION.md` | MISSING |
| 584 | `docs/TECHNICAL_ARCHITECTURE.md` | MISSING |
| 589 | `docs/manuals/MCP_TOOLS_MANUAL.md` | MISSING (directory does not exist) |
| 591 | `docs/manuals/TESTING_MANUAL.md` | MISSING (directory does not exist) |
| 600 | `developer_guides/orchestrator_succession_developer_guide.md` | MISSING (exists at `guides/`) |
| 604 | `quick_reference/succession_quick_ref.md` | MISSING (exists at `guides/`) |
| 609 | `UI_UX_IMPLEMENTATION_STATUS_SUMMARY.md` | MISSING |
| 610 | `VUE_COMPONENT_BRAND_CONSISTENCY_AUDIT.md` | MISSING |
| 611 | `VUETIFY_THEME_CONFIGURATION_VERIFICATION.md` | MISSING |
| 612 | `ASSET_INTEGRATION_TESTING.md` | MISSING |
| 613 | `WCAG_2.1_AA_ACCESSIBILITY_VERIFICATION.md` | MISSING |
| 663 | `handovers/completed/0019_HANDOVER_20251014_AGENT_JOB_MANAGEMENT-C.md` | MISSING |
| 679 | `handovers/completed/0020_HANDOVER_20251014_ORCHESTRATOR_ENHANCEMENT-C.md` | MISSING |
| 680 | `handovers/completed/0020_COMPLETION_SUMMARY-C.md` | MISSING |
| 698 | `handovers/0080_orchestrator_succession_architecture.md` | MISSING |
| 718 | `handovers/completed/0023_HANDOVER_20251015_PASSWORD_RESET_FUNCTIONALITY-C.md` | MISSING |
| 747 | `handovers/completed/0025_HANDOVER_20251016_ADMIN_SETTINGS_NETWORK_REFACTOR.md` | MISSING |
| 748 | `handovers/completed/0025_COMPLETION_REPORT.md` | MISSING |
| 755 | `handovers/completed/0026_HANDOVER_20251016_ADMIN_SETTINGS_DATABASE_TAB_REDESIGN.md` | MISSING |
| 762 | `handovers/completed/0027_HANDOVER_20251016_INTEGRATIONS_TAB_REDESIGN-C.md` | MISSING |
| 769 | `handovers/completed/0028_HANDOVER_20251016_USER_PANEL_CONSOLIDATION.md` | MISSING |
| 775 | `handovers/completed/0029_HANDOVER_20251016_USERS_TAB_RELOCATION.md` | MISSING |
| 786 | `handovers/completed/0035_HANDOVER_20251019_UNIFIED_CROSS_PLATFORM_INSTALLER-C.md` | MISSING |
| 811 | `docs/handovers/0041/` | MISSING |
| 843 | `handovers/completed/0042_COMPLETION_SUMMARY.md` | MISSING |
| 868 | `handovers/completed/0044_HANDOVER_AGENT_TEMPLATE_EXPORT_SYSTEM-C.md` | MISSING |
| 884 | `handovers/completed/0045_COMPLETION_SUMMARY.md` | MISSING |
| 885 | `MIGRATION_GUIDE_V3_TO_V3.1.md` | MISSING |
| 909 | `references/0045/DEVELOPER_GUIDE.md` | MISSING |
| 910 | `references/0045/USER_GUIDE.md` | MISSING |
| 911 | `references/0045/API_REFERENCE.md` | MISSING |
| 918 | `handovers/completed/0046_HANDOVER_PRODUCTS_VIEW_UNIFIED_MANAGEMENT-C.md` | MISSING |
| 941 | `handovers/completed/0047_HANDOVER_VISION_DOCUMENT_CHUNKING_ASYNC_FIX-C.md` | MISSING |
| 962 | `handovers/completed/0048_HANDOVER_PRODUCT_FIELD_PRIORITY_CONFIGURATION-C.md` | MISSING |
| 986 | `handovers/completed/harmonized/0049_IMPLEMENTATION_SUMMARY.md` | MISSING |
| 1010 | `handovers/0050_IMPLEMENTATION_SUMMARY.md` | MISSING |
| 1011 | `handovers/0050_IMPLEMENTATION_STATUS.md` | MISSING |
| 1040 | `handovers/completed/0052_COMPLETION_SUMMARY.md` | MISSING |
| 1124 | `INSTALLATION_VALIDATION_SUMMARY.md` | MISSING |
| 1125 | `MARKETING_CLAIMS_RECOMMENDATIONS.md` | MISSING |
| 1126 | `test_reports/INSTALLATION_TEST_REPORT_HANDOVER_0014.md` | MISSING |
| 1158 | `TESTING_GUIDE.md` | MISSING |
| 1169-1171 | `testing/HANDOVER_0046_*` (3 files) | MISSING |
| 1177-1178 | `testing/HANDOVER_0047_*` (2 files) | MISSING |
| 1184-1186 | `testing/HANDOVER_0052_*` (3 files) | MISSING |
| 1190 | `INSTALLATION_VALIDATION_SUMMARY.md` | MISSING |
| 1191 | `WCAG_2_1_AA_ACCESSIBILITY_AUDIT.md` | MISSING |
| 1192 | `testing/BACKUP_TEST_SUMMARY.md` | MISSING |

### ORCHESTRATOR.md

| Line | Link Target | Status |
|------|------------|--------|
| 681 | `handovers/0355_protocol_message_handling_fix.md` | MISSING |
| 1568 | `user_guides/AGENT_EXECUTION_MODES.md` | MISSING |
| 1578 | `handovers/orchestrator_workflow_after246.md` | MISSING |

### HANDOVERS.md

| Line | Link Target | Status |
|------|------------|--------|
| 445 | `handovers/CCW_OR_CLI_EXECUTION_GUIDE.md` | MISSING |
| 447 | `handovers/completed/0132_remediation_project_complete.md` | MISSING |
| 448 | `handovers/REFACTORING_ROADMAP_0131-0200.md` | MISSING |

### README.md (Root)

| Line | Link Target | Status |
|------|------------|--------|
| 8 | `SECURITY.md` | MISSING |
| 96 | `docs/guides/STARTUP_SIMPLIFICATION.md` | MISSING |
| 109 | `docs/VERIFICATION_OCT9.md` | MISSING |

---

## Missing Documentation

| Feature | Added In | Docs Needed | Priority |
|---------|----------|-------------|----------|
| Service response models (completed migration) | 0730a | Update `service_response_models.md` to reflect completed state | P2 |
| Exception mapping (completed migration) | 0730a | Update `exception_mapping.md` to remove "Current Pattern (Dict Wrapper)" | P2 |
| UUID test fixture patterns | 0730e | Add to TESTING.md or create test pattern guide | P2 |
| Product memory entries table (replacement for JSONB) | 0700c | Update `context_tools.md` memory_360 response format | P2 |
| Simple-handover endpoint documentation | 0700d | Add to API docs (replaces trigger_succession) | P2 |
| 0700 series removal summary | 0700a-h | No consolidated "what changed" doc exists | P3 |

---

## CLAUDE.md Accuracy Check

| Section | Accurate? | Issues |
|---------|-----------|--------|
| Agent Routing Rules | YES | Correct |
| Pre-commit Hook Policy | YES | Correct |
| What We're Building | YES | Correct |
| Recent Updates list | PARTIAL | Lists 0700a-h but does not mention 0730 series |
| Per-User Tenancy Policy | YES | Correct |
| HTTP-only MCP | YES | Correct |
| Tech Stack | YES | Correct |
| Key Folders | PARTIAL | Lists `docs/manuals/` and `docs/sessions/` in structure but `docs/manuals/` does not exist |
| Context Management v3.0 | YES | Accurate on-demand fetch description |
| Orchestrator Workflow Pipeline | YES | Token figures and phases are accurate |
| Thin Client Architecture | YES | Correctly notes OrchestratorPromptGenerator removed in 0700f |
| Quick Start Commands | YES | Commands are valid |
| Message System (0700c) | YES | Correctly describes counter-based architecture |
| Service Layer Architecture | YES | Points to SERVICES.md correctly |
| Orchestrator Context Tracking | PARTIAL | References "manual succession" but does not clarify simple-handover replaced trigger_succession |
| 360 Memory Management | YES | Correctly notes sequential_history removed |
| Testing Strategy | YES | Test commands are valid |
| Handover Format | YES | Correct |
| Development Workflow | YES | Correct |
| Common Issues | YES | Correct |
| Detailed Documentation links | PARTIAL | Links to SERVICES.md, ORCHESTRATOR.md, TESTING.md are valid. Link to HANDOVERS.md is valid. |

**Overall CLAUDE.md Accuracy**: ~90%. The main issues are: (1) Key Folders
lists `docs/manuals/` which does not exist, (2) Recent Updates does not
include 0730 series, (3) succession section does not clarify the
simple-handover replacement for trigger_succession.

---

## README Assessment

| Criterion | Present | Quality (1-10) | Notes |
|-----------|---------|---------------|-------|
| Project Description | YES | 8 | Clear value proposition, good badges |
| Installation Guide | YES | 7 | `python startup.py` is simple, but links to missing docs |
| Usage Examples | YES | 5 | Basic examples but `python -m giljo_mcp tools/docs` may not work |
| Screenshots | NO | 0 | No screenshots or visual examples |
| Contributing Guide | NO | 0 | `CONTRIBUTING.md` does not exist |
| License | YES | 8 | MIT license, badge present, file exists |
| Architecture Diagram | YES | 8 | Good ASCII network topology |
| Broken Links | -- | 3 | `SECURITY.md`, `VERIFICATION_OCT9.md`, `STARTUP_SIMPLIFICATION.md` missing |
| Up-to-date | PARTIAL | 5 | "Recent Updates" stops at October 2025, no mention of 0700/0730 work |

**Open-Source Readiness Score**: 5/10. Project description and architecture
are solid. Missing screenshots, contributing guide, and up-to-date change
history significantly reduce readiness. Several links point to missing files.

---

## Recommendations

### Immediate (P0)

1. **Fix admin/admin contradiction in README_FIRST.md** (lines 296-303).
   Replace the Security Setup > User Management section with accurate
   first-login flow description. This is a security documentation error.

### Short-Term (P1)

2. **Update SERVICES.md JSONB section** (lines 81-88). Change "DEPRECATED"
   to "REMOVED (Handover 0700c)" and remove "will be removed in v4.0".

3. **Purge instance_number from active docs**. The field no longer exists.
   Update SERVICES.md, TESTING.md, ORCHESTRATOR.md, api/agent_jobs_endpoints.md,
   guides/orchestrator_succession_developer_guide.md, guides/succession_quick_ref.md.
   Consider whether succession guides need a complete rewrite or archival.

4. **Remove or fix broken links in README_FIRST.md**. Options:
   a. Remove the entire "Recent Production Handovers" section (lines 658-1060)
      since all handover links are broken.
   b. Fix relative paths for files that exist in different directories
      (e.g., `developer_guides/` -> `guides/`).
   c. Remove links to archived/deleted testing and validation docs.

5. **Update TESTING.md code examples** to use exception-based patterns
   instead of dict wrappers and trigger_succession.

### Medium-Term (P2)

6. **Update exception_mapping.md and service_response_models.md** to
   reflect the completed 0730 migration (not the planned migration).

7. **Update context_tools.md** memory_360 response format to show
   normalized table structure instead of sequential_history JSONB.

8. **Update thin_client_migration_guide.md** to reflect that
   OrchestratorPromptGenerator has been fully removed (not just deprecated).

9. **Add 0730e test patterns** to TESTING.md (UUID fixtures, cleanup).

10. **Document simple-handover endpoint** in API docs.

### Long-Term (P3)

11. **Create CONTRIBUTING.md** for open-source readiness.

12. **Create SECURITY.md** (linked from README.md badge).

13. **Add screenshots** to README.md.

14. **Consolidate or create docs/manuals/** directory as referenced in
    CLAUDE.md documentation structure.

15. **Create a "What Changed in 0700/0730" summary document** so developers
    understand the scope of the cleanup series.

---

## Metrics Summary

| Category | Count |
|----------|-------|
| P0 Critical findings | 1 |
| P1 High findings | 6 |
| P2 Medium findings | 6 |
| P3 Low findings | 8 |
| Broken links (total) | 60+ |
| Outdated references (non-archive) | 18+ files affected |
| Missing documentation items | 6 |
| CLAUDE.md accuracy | ~90% |
| README.md open-source readiness | 5/10 |
