# Root Folder Cleanup Plan

**Audit Date**: 2026-01-18
**Auditor**: Internal AI Assistant
**Total files audited**: 148 files in root (excluding directories)

---

## Summary

| Category | Count | Status |
|----------|-------|--------|
| Markdown/Text docs | 70 files | Audited |
| Python scripts | 40 files | Audited |
| SQL files | 8 files | Audited |
| Other (images, configs, archives) | 30 files | Audited |

---

## Cleanup Actions

### Phase 1: Temporary Files - COMPLETED

The following files have been deleted:

| File | Reason | Deleted |
|------|--------|---------|
| `temp_script.py` | Contains only `print("test")` | Yes |
| `temp_add_columns.sql` | One-time migration script | Yes |
| `temp_add_dual_fields.py` | One-time migration script | Yes |
| `temp_add_to_all_dbs.py` | One-time migration script | Yes |
| `temp_app_diff.txt` | Debug output | Yes |
| `temp_app_patch.txt` | Debug output | Yes |
| `test_temp.txt` | Contains 4 bytes | Yes |
| `test_collection_output.txt` | 229KB pytest output dump | Yes |
| `test_results.txt` | Test output | Yes |
| `test_results.xml` | CI artifact | Yes |
| `I am Orchestrator #52 for GiljoAI P.txt` | Debug orchestrator prompt dump | Yes |
| `DOCUMENTS_CREATED.txt` | One-time list | Yes |

---

### Phase 2: Handover Reports - COMPLETED

Moved to `handovers/completed/reports/` on 2026-01-18:

| File | Handover | Status |
|------|----------|--------|
| `HANDOVER_0246c_SUMMARY.txt` | 0246c | Moved |
| `HANDOVER_0247_COMPLETION.md` | 0247 | Moved |
| `HANDOVER_0247_COMPLETION_SUMMARY.md` | 0247 | Moved |
| `HANDOVER_0249c_E2E_TESTING_REPORT.md` | 0249c | Moved |
| `HANDOVER_0272_DELIVERY_SUMMARY.md` | 0272 | Moved |
| `HANDOVER_0272_FILES_CREATED.txt` | 0272 | Moved |
| `HANDOVER_0282_INTEGRATION_TEST_SUMMARY.md` | 0282 | Moved |
| `HANDOVER_0289_TEST_SUMMARY.md` | 0289 | Moved |
| `HANDOVER_0327_TEST_REPORT.md` | 0327 | Moved |
| `BACKEND_TEST_REPORT_0246a.md` | 0246a | Moved |
| `IMPLEMENTATION_SUMMARY_0246a.txt` | 0246a | Moved |
| `IMPLEMENTATION_SUMMARY_0345c.md` | 0345c | Moved |
| `TEST_COVERAGE_REPORT_0248c.md` | 0248c | Moved |

**Note**: Original handover files have been updated with "Related Reports" sections linking to these reports.

**Handovers Updated**:
- `0246a_staging_prompt_implementation-C.md` → 2 reports
- `0246c_dynamic_agent_discovery_token_reduction-C.md` → 1 report
- `0247_complete_agent_discovery_staged_workflow-C.md` → 2 reports
- `0248c_persistence_360_memory_fixes-C.md` → 1 report
- `0249c_ui_wiring_e2e_testing-C.md` → 1 report
- `0272_comprehensive_integration_tests-C.md` → 2 reports
- `0282_context_priority_field_key_mismatches-C.md` → 1 report
- `0289_message_routing_architecture_fix-C.md` → 1 report
- `0327_playwright_localhost_authentication_fix-C.md` → 1 report
- `0345c_vision_settings_ui-C.md` → 1 report

---

### Phase 3: Obsolete Analysis Docs - COMPLETED

Archived to `docs/archive/` on 2026-01-18:

| File | Reason | Age |
|------|--------|-----|
| `AGENT_INFO_BUTTON_ANALYSIS_REPORT.md` | Completed Nov 2025 - work is done | 2 months |
| `AGENT_INFO_IMPLEMENTATION_SUMMARY.txt` | Completed Nov 2025 | 2 months |
| `ANALYSIS_SUMMARY.md` | Card styling fix - completed | 2 months |
| `CODE_CHANGES_EXACT_DIFF.md` | Pencil icon fix - completed | 2 months |
| `COMPARISON_REPORT_ORCHESTRATOR_VS_AGENT_CARDS.md` | Completed styling work | 2 months |
| `ICON_DEBUG_COMPLETION_REPORT.md` | Debug work completed | 2 months |
| `PENCIL_ICON_QUICK_FIX.md` | Quick fix completed | 2 months |
| `QUICK_FIX_CHECKLIST.md` | One-time checklist | 2 months |
| `QUICK_IMPLEMENTATION_GUIDE.md` | Agent info button - done | 2 months |
| `README_COMPARISON_ANALYSIS.md` | One-time comparison | 2 months |
| `VISUAL_SPACING_ANALYSIS.md` | Completed UI work | 2 months |
| `TECHNICAL_DEBT_ANALYSIS.md` | Nov 2025 - superseded by 0120-0130 | 2 months |
| `REFACTORING_CHECKLIST.md` | Completed Nov 2025 | 2 months |
| `REFACTORING_REPORT.md` | Completed Nov 2025 | 2 months |
| `TASK_COMPLETION_SUMMARY.md` | One-time summary | 2 months |
| `ROOT_CAUSE_ANALYSIS_SERVICE_RECURSION_BUGS.md` | Bug fixed Nov 2025 | 2 months |
| `BACKEND_ROUTING_INVESTIGATION_SUMMARY.md` | Investigation complete | 2 months |
| `DOWNLOAD_EXPORT_API_RESEARCH.md` | Research complete | 2 months |
| `DOWNLOAD_TOKEN_TEST_SUMMARY.md` | Download tokens removed Jan 2026 | 2 weeks |
| `TEST_FIXES_FINAL_REPORT.md` | One-time fixes | 2 months |
| `TEST_REPORT_WEBSOCKET_SYNC.md` | Feature completed | 2 months |
| `TEST_RESULTS_TASK_TO_PROJECT_CONVERSION.md` | Conversion done | 2 months |

---

### Phase 4: One-Time Fix Scripts - COMPLETED

Archived to `scripts/archived/` on 2026-01-18:

| File | Purpose |
|------|---------|
| `fix_alembic_state.py` | One-time migration fix |
| `fix_env_passwords.py` | One-time password fix |
| `fix_product_cascade.sql` | One-time cascade fix |
| `fix_product_tests.py` | One-time test fix |
| `fix_remaining_tests.py` | One-time test fix |
| `fix_setup_state.py` | One-time setup fix |
| `reset_patrik_password.py` | Personal script |
| `update_arch.py` | One-time update |
| `update_test_db.py` | One-time update |
| `verify_setup_state.py` | One-time verification |
| `diagnostic_cascade_test.sql` | One-time diagnostic |
| `test_deleted_endpoint.py` | Specific endpoint test |

---

### Phase 5: Move to Proper Locations - PENDING

#### Move to `backups/`
| File | Reason |
|------|--------|
| `backup_pre_0387_phase4.sql` | 612KB backup |
| `backup_pre_0390.sql` | 634KB backup |
| `backup_pre_0420a.sql` | 577KB backup |
| `schema_baseline.sql` | Schema snapshot |
| `schema_old_chain.sql` | Schema snapshot |

#### Move to `docs/guides/`
| File | Reason |
|------|--------|
| `SERENA_IMPLEMENTATION_FLOW.md` | MCP usage guide |
| `SERENA_QUICK_REFERENCE.txt` | MCP quick reference |
| `SELECTOR_TEST_GUIDE.md` | Testing guide |
| `SELECTOR_TEST_EXAMPLES.md` | Testing examples |
| `E2E_TESTING_DOCUMENTATION_INDEX.md` | Testing index |
| `PLAYWRIGHT_INSTALLATION_SUMMARY.md` | Setup guide |

#### Move to `docs/architecture/`
| File | Reason |
|------|--------|
| `schema_mapping_report.md` | Schema documentation |

---

### Phase 6: Keep in Root - NO ACTION NEEDED

| File | Purpose | Status |
|------|---------|--------|
| `CLAUDE.md` | Claude Code instructions | Current |
| `README.md` | Project readme | Needs update |
| `AGENTS.md` | Contributor guidelines | Needs update |
| `GEMINI.md` | Gemini CLI instructions | Needs update |
| `LICENSE` | License file | Keep |
| `requirements.txt` | Python deps | Current |
| `dev-requirements.txt` | Dev deps | Check |
| `optional-requirements.txt` | Optional deps | Check |
| `pyproject.toml` | Project config | Keep |
| `alembic.ini` | Alembic config | Keep |
| `.env.example` | Environment template | Keep |
| `config.yaml.example` | Config template | Keep |
| `install.py` | Main installer | Keep |
| `startup.py` | Server startup | Keep |
| `startup_prod.py` | Production startup | Keep |
| `reset.py` | Database reset | Keep |
| `backup.py` | Backup utility | Keep |
| `uninstall.py` | Uninstaller | Keep |

---

### Phase 7: Needs Decision - PENDING

#### Agent Type Migration Docs (Recent - Jan 2026)
| File | Notes |
|------|-------|
| `AGENT_TYPE_QUESTIONS_ANSWERED.md` | Jan 10, migration reference |
| `AGENT_TYPE_QUICK_REFERENCE.md` | Jan 10, migration reference |
| `AGENT_TYPE_REFACTORING_GUIDE.md` | Jan 10, migration reference |
| `agent_type_usage_analysis.md` | Jan 10, migration analysis |
| `MIGRATION_SUMMARY.txt` | Jan 11, recent migration |
| `TEST_MIGRATION_REPORT.md` | Jan 11, recent testing |
| `import_update_summary.txt` | Dec 2025, import changes |

#### Test Utilities (May be useful)
| File | Notes |
|------|-------|
| `test_alias_generation.py` | Could be in tests/ |
| `test_database_backup.py` | Could be in tests/ |
| `test_git_integration_api.py` | Could be in tests/ |
| `test_migration_execution.py` | Could be in tests/ |
| `test_thin_client_integration.py` | Could be in tests/ |
| `create_test_apikey.py` | Could be in dev_tools/ |

#### Miscellaneous
| File | Decision Needed |
|------|-----------------|
| `giljo_mcp-1.0.2-py3-none-any.whl` | Old wheel - delete? |
| `agent_templates.zip` | Backup of templates - keep in backups/? |
| `coverage.json` | 4MB - regenerated by pytest, delete |
| `image.jpg`, `image2.jpg` | Unknown purpose - delete? |
| `favicon.gif`, `favicon.jpg`, `giljo.ico` | Keep 1, move to frontend/public/ |
| `api_keys.json` | Should be gitignored? |

---

## Progress Log

| Phase | Action | Date | Status |
|-------|--------|------|--------|
| 1 | Delete temp files | 2026-01-18 | Completed |
| 2 | Move handover reports | 2026-01-18 | Completed |
| 3 | Archive obsolete docs | 2026-01-18 | Completed |
| 4 | Archive one-time scripts | 2026-01-18 | Completed |
| 5 | Move to proper locations | - | Pending |
| 6 | Root files (no action) | - | N/A |
| 7 | Decision needed | - | Pending |
