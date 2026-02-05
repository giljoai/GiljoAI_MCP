# 0700h Kickoff: Imports and Final Polish

**Series**: 0700 Code Cleanup
**Handover**: 0700h (TERMINAL - Final handover of 0700 deprecated purge series)
**Priority**: LOW
**Risk**: LOW
**Dependencies**: 0700g (complete), 0700e (complete), 0700f (complete)

---

## Your Mission

This is the **final cleanup pass** for the 0700 series. Your job is to:
1. Fix all remaining vulture/static analysis findings
2. Remove remaining deprecated parameters and methods
3. Sweep for any remaining DEPRECATED markers
4. Run code quality tools

After this handover, the codebase should have ZERO deprecated markers and ZERO unused imports at 80% confidence.

**CRITICAL CONTEXT**: You are the LAST worker in a 9-handover series (0700a through 0700h) that has removed ~5,500+ lines of deprecated code. Prior handovers already removed:
- Light mode (0700a), deprecated columns (0700b), JSONB fields (0700c), succession module (0700d), template_content (0700e), deprecated endpoints (0700f), unused enums/exceptions (0700g)
- 0700g already cleaned: TemplateRenderError/TemplateValidationError imports in template_service.py, InteractionType/AugmentationType/ArchiveType enums, Git* exceptions, LaunchSuccessorDialog/SuccessionTimeline components

---

## Files to Read First

1. `handovers/0700_series/WORKER_PROTOCOL.md` (your execution protocol)
2. `handovers/0700_series/0700h_imports_final_polish.md` (detailed spec)
3. `handovers/0700_series/comms_log.json` (read entries where to_handovers includes "0700h" - especially 0700g-001)
4. `handovers/0700_series/dead_code_audit.md` (vulture appendix with exact findings)

---

## Task 1: Fix Vulture Findings (High Confidence)

These were identified by vulture at 80%+ confidence. Some may already be resolved by 0700g. **Verify each still exists before fixing.**

| File | Line | Issue |
|------|------|-------|
| `api/endpoints/agent_jobs/operations.py:35` | Unused imports `ForceFailJobRequest`, `ForceFailJobResponse` |
| `api/endpoints/projects/lifecycle.py:27` | Unused import `StagingCancellationResponse` |
| `api/endpoints/prompts.py:23` | Unused import `ThinPromptResponse` |
| `api/startup/database.py:48` | Redundant if-condition |
| `src/giljo_mcp/colored_logger.py:20` | Unused import `Back` |
| `src/giljo_mcp/discovery.py:602, 623` | Unused variable `max_chars` (2 instances) |
| `src/giljo_mcp/services/project_service.py:1475` | Unreachable code after raise |
| `src/giljo_mcp/services/task_service.py:223` | Unused variable `assigned_to` |
| `src/giljo_mcp/services/template_service.py:34` | Unused imports `TemplateRenderError`, `TemplateValidationError` - **LIKELY ALREADY FIXED BY 0700g** |
| `src/giljo_mcp/tools/agent.py:17` | Unused import `broadcast_sub_agent_event` |
| `src/giljo_mcp/tools/context.py:97` | Unused variable `force_reindex` |
| `src/giljo_mcp/tools/template.py:16` | Unused import `extract_variables` |
| `src/giljo_mcp/tools/tool_accessor.py:361` | Unused variable `assigned_to` |

**For unused variables**: If the variable is assigned from a function call with side effects (like a DB query), keep the call but remove the variable assignment (use `_` prefix or delete the assignment if the return value is truly unused). If it's a plain assignment, delete it.

---

## Task 2: Remove Remaining Deprecated Parameters

In `src/giljo_mcp/thin_prompt_generator.py`:
- **Line ~141**: `instance_number` parameter in `__init__` - Remove the parameter and any code that uses it (dep-016)
- **Line ~1134**: `instance_number` parameter in another method - Remove similarly
- **Check callers**: After removing these parameters, grep for all callers passing `instance_number=` and update them

Also check these deprecated items from the cleanup_index:
- `dep-021`: `OrchestrationService.update_context_usage.agent_id` parameter (deprecated, not used in query) - Remove parameter and update callers
- `dep-027`: `ToolAccessor.close_project` method (deprecated, use `complete_project` instead) - Remove method, update any callers to use `complete_project`
- `dep-028`: `ToolAccessor.gil_handover` method (deprecated, MCP tool removed) - Remove if no longer registered
- `dep-029`: `ToolAccessor.gil_handover.reason` parameter (deprecated) - Remove with method
- `dep-030`: `ToolAccessor.gil_activate` method (deprecated, MCP tool removed) - Remove if no longer registered
- `dep-036`: `OrchestratorJobResponse.id` field (deprecated integer id) - Remove from schema
- `dep-041`: `retired_agents` field in prompt schema - Remove from schema

**WARNING**: For each item, verify it's not actively called before removing. Use grep to check.

---

## Task 3: Remove Deprecated API Schema Fields

From the cleanup_index:
- `dep-038`: `TemplateCreate.category`, `project_type`, `preferred_tool` deprecated fields in `api/endpoints/templates/models.py:37` - Remove all three
- `dep-040`: `TemplatePreviewResponse.mission` deprecated field in `api/endpoints/templates/models.py:173` - Remove
- `dep-033`: `messages=[]` in agent_management response (line ~118) - Remove the field or update to not include it
- `dep-042`: `api.agents` legacy stub in `frontend/src/services/api.js:237` - Remove entire deprecated block
- `dep-043`: `api.vision` legacy single-doc API in `frontend/src/services/api.js:400` - Remove entire deprecated block
- `dep-044`: `agentJobs` legacy aliases in `frontend/src/services/api.js:585` - Remove

**For frontend changes**: After removing API stubs, grep to verify no component still calls the removed methods.

---

## Task 4: Final DEPRECATED Marker Sweep

Run: `grep -rn "DEPRECATED\|deprecated\|v4\.0\|backward.compat" src/ api/ --include="*.py" | grep -v __pycache__ | grep -v migrations/archive`

For each hit:
- If the code it marks has already been removed by 0700a-g: **delete the comment**
- If the code is still present and marked deprecated: **remove the code AND the comment** (there is no v4.0, we are shipping v1.0)
- If the deprecated code is actively used (like AgentStatus.DECOMMISSIONED raw strings): **keep it, note in comms log**
- EXCEPTION: Keep `migrations/archive/*` untouched (historical migrations)
- EXCEPTION: Keep `migrations/versions/baseline_v32_unified.py` comments that are structural

Target: Zero DEPRECATED markers in `src/` and `api/` (excluding migrations/archive).

---

## Task 5: Delete Skipped Tests for Removed Features

From cleanup_index - tests for features that no longer exist:
- `skip-api-001`: `tests/api/test_agent_jobs_api.py:685` - test_cancel_job_happy_path (cancel endpoint removed)
- `skip-api-002`: `tests/api/test_agent_jobs_api.py:713` - test_cancel_job_not_found (cancel endpoint removed)
- `skip-api-003`: `tests/api/test_agent_jobs_api.py:729` - test_force_fail_job_happy_path (force-fail removed)
- `skip-api-004`: `tests/api/test_agent_jobs_api.py:756` - test_force_fail_job_not_found (force-fail removed)
- `skip-svc-002`: `tests/services/test_orchestration_service_full.py:258` - test_check_succession_status (method deleted)
- `skip-svc-003`: `tests/services/test_orchestration_service_instructions.py:473` - TestCheckSuccessionStatus class (method deleted)

**Delete the skipped test functions/classes entirely.** Don't just remove the skip marker.

---

## Task 6: Code Quality Pass

1. Run `ruff check src/ api/ --fix` to auto-fix lint issues
2. Run `black src/ api/` to format
3. Run `python -c "from src.giljo_mcp.models import *; print('Models OK')"` to verify models load
4. Run `pytest tests/ -x -q --timeout=30` for quick sanity check

---

## Verification (Series Completion Criteria)

After all changes, verify:
1. `grep -rn "DEPRECATED" src/ api/ --include="*.py" | grep -v __pycache__ | grep -v migrations/archive | grep -v migrations/versions` = **0 results** (or document exceptions in comms log)
2. Models load: `python -c "from src.giljo_mcp.models import *; from src.giljo_mcp.enums import *; from src.giljo_mcp.exceptions import *; print('OK')"`
3. `pytest tests/ -x -q --timeout=30` passes
4. Report final line count removed in this handover

---

## Comms Log Entry

When complete, append to `handovers/0700_series/comms_log.json`:
```json
{
  "id": "0700h-001",
  "timestamp": "<ISO timestamp>",
  "from_handover": "0700h",
  "to_handovers": ["orchestrator"],
  "type": "info",
  "subject": "Final polish complete - 0700 deprecated purge series finished",
  "message": "<summary: vulture findings fixed, deprecated markers remaining (if any), tests deleted, code quality results>",
  "files_affected": ["<list>"],
  "action_required": false,
  "context": {
    "vulture_findings_fixed": "<count>",
    "deprecated_markers_remaining": "<count and reasons>",
    "deprecated_methods_removed": "<count>",
    "deprecated_schema_fields_removed": "<count>",
    "skipped_tests_deleted": "<count>",
    "lines_removed": "<count>",
    "series_total_lines_removed": "<running total across 0700a-h>",
    "series_complete": true
  }
}
```

Also update `handovers/0700_series/orchestrator_state.json`:
- Set 0700h status to "complete"
- Set started_at and completed_at timestamps

---

## Rules
- VERIFY before deleting - grep for each item first
- This is the TERMINAL handover - be thorough but careful
- If a deprecated item turns out to be actively used, KEEP it and document in comms log
- Don't touch `migrations/archive/*` (historical)
- Follow WORKER_PROTOCOL.md 6-phase execution
- When in doubt, keep the code and note it - better to leave a few items than break the app
