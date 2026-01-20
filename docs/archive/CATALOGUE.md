# Archive Catalogue

This document catalogues all archived documentation content for the GiljoAI_MCP project.

---

## Archived Batch: retired-2026-01 (January 2026)

**Date Archived**: 2026-01-19
**Reason**: Documentation cleanup and consolidation

### Subfolders

| Folder | Contents | Reason |
|--------|----------|--------|
| `accessibility/` | WCAG accessibility audit and action plans | Features never implemented |
| `handover-reports/` | Point-in-time test reports from handovers 0046-0052 | Historical test results |
| `urgent-drafts/` | Files with `__URGENT` suffix | Draft content never finalized |
| `implementation-reports/` | One-time implementation summaries | Point-in-time reports |
| `workflow-variants/` | SSoT variants and workflow proposals | Superseded by current docs |
| `legacy-guides/` | Outdated guides and migration docs | Superseded by current implementation |
| `devlog-history/` | Development logs | Consolidated into docs/CHANGELOG.md |

---

### accessibility/

Files describing WCAG accessibility features that were planned but never implemented.

| File | Original Location | Notes |
|------|-------------------|-------|
| `ACCESSIBILITY_ACTION_PLAN.md` | docs/ | Action items never executed |
| `ACCESSIBILITY_QUICK_FIX_GUIDE.md` | docs/ | Quick fixes never applied |
| `ACCESSIBILITY_VISUAL_SUMMARY.md` | docs/ | Visual summary of planned features |
| `WCAG_2_1_AA_ACCESSIBILITY_AUDIT.md` | docs/ | Full audit - no implementation |

---

### handover-reports/

Point-in-time test reports from specific handovers. These are historical artifacts.

| File | Original Location | Notes |
|------|-------------------|-------|
| `HANDOVER_0046_*.md` | docs/testing/ | Handover 0046 test reports (7 files) |
| `HANDOVER_0047_*.md` | docs/testing/ | Handover 0047 test reports (3 files) |
| `HANDOVER_0051_*.md` | docs/testing/ | Handover 0051 test reports (5 files) |
| `HANDOVER_0052_*.md` | docs/testing/ | Handover 0052 test reports (6 files) |
| `BACKUP_TEST_SUMMARY.md` | docs/testing/ | Backup feature test summary |
| `STAGE_PROJECT_TEST_SUITE.md` | docs/testing/ | Stage project test suite |

---

### urgent-drafts/

Files marked with `__URGENT` suffix that were created as drafts but never finalized or integrated into main documentation.

**From docs/manuals/:**
| File | Review Result | Action Taken |
|------|---------------|--------------|
| `API_SETUP_ENDPOINTS__URGENT.md` | Superseded by docs/api/ | Archived |
| `GILTEST_README__URGENT.md` | Test utility doc, outdated | Archived |
| `INSTALLATION__URGENT.md` | Superseded by INSTALLATION_FLOW_PROCESS.md | Archived |
| `INSTALLER_ARCHITECTURE__URGENT.md` | Historical installer doc | Archived |
| `INSTALL__URGENT.md` | Superseded by INSTALLATION_FLOW_PROCESS.md | Archived |
| `MCP_TOOLS_MANUAL__URGENT.md` | Overlaps with docs/api/, some outdated | Archived |
| `MISSION_TEMPLATES_TESTING_GUIDE__URGENT.md` | Test guide, outdated | Archived |
| `QUICK_START__URGENT.md` | Outdated paths (C:\Projects\...) | Archived |
| `SERVER_MODE_QUICKSTART__URGENT.md` | Superseded by current docs | Archived |
| `SLASH_COMMANDS__URGENT.md` | **VALUABLE** - Recent, unique content | **KEPT** → docs/guides/slash_commands_reference.md |

**Note**: `PASSWORD_RESET_USER_GUIDE.md` (no __URGENT suffix) was moved to docs/user_guides/

**From docs/guides/:**
| File | Review Result | Action Taken |
|------|---------------|--------------|
| `API_REFERENCE__URGENT.md` | Superseded by docs/api/ | Archived |
| `FIREWALL_CONFIGURATION__URGENT.md` | Network setup, outdated | Archived |
| `MCP_INTEGRATION_GUIDE__URGENT.md` | References harmonized docs, mostly current | Archived (content in MCP_OVER_HTTP_INTEGRATION.md) |
| `ORCHESTRATOR_DISCOVERY_GUIDE__URGENT.md` | Superseded by ORCHESTRATOR.md | Archived |
| `REQUIREMENTS_MIGRATION_GUIDE__URGENT.md` | v3 migration guide, outdated | Archived |
| `ROLE_BASED_CONTEXT_FILTERING__URGENT.md` | Superseded by context_configuration_guide.md | Archived |
| `STARTUP_REQUIREMENTS_FLOW__URGENT.md` | Startup flow, outdated | Archived |
| `STARTUP_SIMPLIFICATION__URGENT.md` | Simplification proposal, implemented | Archived |
| `template_migration__URGENT.md` | Template migration, completed | Archived |
| `USER_GUIDE__URGENT.md` | Superseded by user_guides/ folder | Archived |
| `USER_MANAGEMENT__URGENT.md` | User management, outdated | Archived |

---

### implementation-reports/

One-time implementation summaries and reports. These document point-in-time status.

| File | Original Location | Notes |
|------|-------------------|-------|
| `CONTEXT_PERFORMANCE_REPORT.md` | docs/ | Performance testing results |
| `UI_UX_IMPLEMENTATION_STATUS_SUMMARY.md` | docs/ | UI/UX status at time of writing |
| `SESSION_LEAK_FIX_REPORT.md` | docs/ | Session leak fix documentation |
| `TEMPLATE_INTEGRATION_PROJECT_SUMMARY.md` | docs/ | Template integration summary |
| `TEMPLATE_SYSTEM_EVOLUTION.md` | docs/ | Template system history |
| `INSTALLATION_VALIDATION_SUMMARY.md` | docs/ | Installation validation results |
| `DOCUMENTATION_REMEDIATION_EXECUTIVE_SUMMARY.md` | docs/ | Doc remediation summary |
| `documentation_remediation_plan_handover_0280.md` | docs/ | Handover 0280 doc plan |
| `GIT_SYNC_FIX.md` | docs/ | Git sync fix documentation |
| `COOKIE_DOMAIN_WHITELIST_API_IMPLEMENTATION.md` | docs/ | Cookie domain implementation |

---

### workflow-variants/

Single Source of Truth (SSoT) variants and workflow documents that were superseded.

| File | Original Location | Notes |
|------|-------------------|-------|
| `GILJOAI_WORKFLOW_SINGLE_SOURCE_OF_TRUTH_MERGED.md` | docs/ | Merged SSoT variant |
| `GILJOAI_WORKFLOW_SINGLE_SOURCE_OF_TRUTH_Variant.md` | docs/ | SSoT variant |
| `WORKFLOW_DOCUMENT_HARMONIZATION_PROPOSAL.md` | docs/ | Harmonization proposal |
| `WORKFLOW_MERGE_AUDIT.md` | docs/ | Workflow merge audit |
| `ORCHESTRATION_CONSOLIDATION_PLAN.md` | docs/ | Consolidation plan |
| `SSoT_INDEX.md` | docs/ | SSoT index (outdated) |

---

### legacy-guides/

Outdated guides and strategy documents superseded by current implementation.

| File | Original Location | Notes |
|------|-------------------|-------|
| `MARKETING_CLAIMS_RECOMMENDATIONS.md` | docs/ | Marketing claims |
| `MCP_STRATEGY_CODEX_GEMINI.md` | docs/ | MCP strategy doc |
| `MIGRATION_GUIDE_V3_TO_V3.1.md` | docs/ | v3 to v3.1 migration |
| `USER_STRUCTURES_TENANTS.md` | docs/ | Superseded by per-user tenancy |
| `STAGE_PROJECT_FEATURE.md` | docs/ | Stage project feature doc |
| `index_files.md` | docs/ | File index (outdated) |

---

### devlog-history/

Development logs that were consolidated into docs/CHANGELOG.md.

| File | Original Location | Notes |
|------|-------------------|-------|
| (all files from docs/devlog/) | docs/devlog/ | Consolidated into CHANGELOG.md |

---

## Previous Archives

The following archives existed before the January 2026 cleanup:

| Folder | Contents |
|--------|----------|
| `0130_websocket_v1_backups/` | WebSocket v1 backup files |
| `backup_pre_subagent/` | Pre-subagent implementation backups |
| `database_backups/` | Database backup files |
| `handover_docs/` | Historical handover documentation |
| `how does it look when agents work/` | Agent visualization docs |
| `root-cleanup-20251013/` | October 2025 root cleanup |
| `root-cleanup-20251102/` | November 2025 root cleanup |

---

## Archive Policy

1. **Never delete archived content** - archives are permanent historical record
2. **Document everything** - update this catalogue when archiving
3. **Preserve structure** - maintain original folder relationships where meaningful
4. **Date batches** - use `retired-YYYY-MM/` format for cleanup batches
