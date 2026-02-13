# Orphan/Zombie Code Research Findings

**Date:** 2026-02-07
**Researcher:** Deep Researcher Agent
**Scope:** src/, api/, tests/

---

## Executive Summary

This research identified significant amounts of orphan/zombie code in the GiljoAI MCP codebase.

Key findings:
- 267 orphan modules identified in dependency_analysis.json
- 129 Python modules that appear never to be imported
- 444 unused functions/classes/methods detected by Vulture (60%+ confidence)
- 8 unused variables at 100% confidence
- 239 functions defined but potentially never called
- 30+ test files that may test non-existent or renamed modules

---

## 1. Vulture Dead Code Analysis (100% Confidence)

These are definite unused variables that can be safely removed:

File: src/giljo_mcp/discovery.py:602 - unused variable max_chars
File: src/giljo_mcp/discovery.py:623 - unused variable max_chars  
File: src/giljo_mcp/discovery.py:623 - unused variable paths_include
File: src/giljo_mcp/mission_planner.py:1144 - unused variable category_key
File: src/giljo_mcp/services/task_service.py:207 - unused variable assigned_to
File: src/giljo_mcp/services/task_service.py:246 - unused variable assigned_to
File: src/giljo_mcp/tools/context.py:82 - unused variable force_reindex
File: src/giljo_mcp/tools/tool_accessor.py:307 - unused variable assigned_to

---

## 2. True Orphan Modules (Never Imported)

Critical Orphans in src/giljo_mcp/:

- lock_manager.py - ORPHAN - No imports found
- mcp_http_stdin_proxy.py - ORPHAN - No imports (stdio removed per CLAUDE.md)
- staging_rollback.py - ORPHAN - No imports found
- template_materializer.py - ORPHAN - No imports found
- job_monitoring.py - ORPHAN - No imports found
- cleanup/visualizer.py - ORPHAN - Only in unused cleanup/__init__.py

Partially Used (imported only in tests):

- workflow_engine.py - Production: orchestration_service.py
- job_coordinator.py - Production: workflow_engine.py
- database_backup.py - Production: None, Test: test_backup_tool.py
- json_context_builder.py - Production: mission_planner.py
- websocket_client.py - Production: None, Script: validate_dependencies.py

---

## 3. API Endpoint Orphans

agent_jobs/ directory (12 files, many with dead functions):
- executions.py - get_job_executions() unused
- filters.py - get_filter_options() unused
- lifecycle.py - report_job_error() unused
- messages.py - get_job_messages() unused
- operations.py - get_job_health() unused
- orchestration.py - regenerate_mission(), launch_implementation() unused
- status.py - list_pending_jobs(), get_job_mission() unused
- table_view.py - get_agent_jobs_table_view() unused

Other endpoint files with dead functions:
- agent_management.py - 6 unused functions
- agent_templates.py - 2 unused functions
- ai_tools.py - 2 unused functions
- configuration.py - 12 unused functions
- database_setup.py - 3 unused functions
- downloads.py - 4 unused functions

---

## 4. Dead Functions Summary

Total: 444 unused functions/classes/methods (60%+ confidence)

By Category:
- API Endpoints: ~150 (login, logout, get_me in auth.py)
- Service Methods: ~80
- Tool Functions: ~60 (launch_agent, spawn_agent, etc.)
- Utility Functions: ~50
- Model Classes: ~30
- Repository Methods: ~40
- Test Helpers: ~34 (init_for_testing patterns)

---

## 5. Orphan Test Files

API Tests that may test non-existent modules:
- test_users_category_validation.py
- test_users_new_categories.py
- test_admin_fixtures.py
- test_agent_display_name_schemas.py
- test_depth_controls.py
- test_filter_options.py
- test_health_status_api.py
- test_implementation_prompt_api.py

---

## 6. Unreachable Code

No unreachable code patterns detected.

---

## 7. Circular Dependencies

From dependency_analysis.json:
1. api/app.py -> auth/__init__.py -> dependencies.py -> app.py
2. orchestration_service.py -> project_service.py -> project_closeout.py -> orchestration_service.py

---

## 8. High-Risk Files

Files with many dependents (changes require careful testing):
- src/giljo_mcp/models/__init__.py - 101 dependents
- api/app.py - 72 dependents
- src/giljo_mcp/database.py - 57 dependents
- src/giljo_mcp/auth/dependencies.py - 47 dependents

---

## 9. Recommendations

Immediate Actions (Safe to Remove):
1. Fix 8 unused variables (100% confidence)
2. Remove true orphan modules: lock_manager.py, mcp_http_stdin_proxy.py, staging_rollback.py, job_monitoring.py, cleanup/visualizer.py

Medium Priority:
1. Audit agent_jobs/ endpoints - many dead functions
2. Review init_for_testing() functions
3. Clean up duplicate function definitions

---

## 10. Source Files Summary

- src/giljo_mcp/: 146 files, ~40 orphans (27%)
- api/: 114 files, ~75 orphans (66%)
- tests/: ~150 files, ~30 testing deleted code

Total Python Files: 260 (src + api)
Estimated Orphan Modules: 129 (50%)

---

This report is research only - no fixes have been applied.
