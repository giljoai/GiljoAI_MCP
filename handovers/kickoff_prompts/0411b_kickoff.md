# 0411b Kickoff: Dead Code Cleanup (Orphaned Orchestration Pipeline)

Read and implement `F:\GiljoAI_MCP\handovers\0411b_dead_code_cleanup.md`.

## What You're Doing

Removing ~4,190 lines of dead code (1,640 production + 2,550 test) orphaned since the `orchestrate_project` MCP tool was removed in commit `d67f0d23` (2026-01-27). The entire automated orchestration pipeline (WorkflowEngine, JobCoordinator, and 4 OrchestrationService methods) is unreachable.

## Tier 1: Entire Files to Delete

- `src/giljo_mcp/workflow_engine.py` (465 lines)
- `src/giljo_mcp/job_coordinator.py` (503 lines)
- `tests/unit/test_workflow_engine.py` (866 lines)
- `tests/test_job_coordinator.py` (680 lines)
- `tests/unit/test_agent_selector.py` (514 lines)

## Tier 2: Partial Cleanup (Careful)

- `src/giljo_mcp/orchestration_types.py` - Delete `WorkflowStage`, `StageResult`, `WorkflowResult` (~lines 140-238). **KEEP `AgentConfig`** - still imported by active code.
- `src/giljo_mcp/services/orchestration_service.py` - Delete 4 orphaned methods (~lines 2929-3206): `generate_mission_plan()`, `select_agents_for_mission()`, `coordinate_agent_workflow()`, `process_product_vision()`. Remove dead imports and the `workflow_engine` property.
- `src/giljo_mcp/schemas/service_responses.py` - Delete `OrchestrationWorkflowResult` (~lines 477-490)
- `tests/unit/test_orchestration_types.py` - Delete test classes for removed dataclasses (~lines 330-682). **KEEP tests for `AgentConfig`**.

## CRITICAL: DO NOT DELETE

- **`src/giljo_mcp/mission_planner.py`** - ACTIVELY USED by `get_orchestrator_instructions()` at line 3313 of orchestration_service.py for `_build_fetch_instructions()`. Do NOT remove this file.
- **`src/giljo_mcp/agent_selector.py`** - Imports `AgentConfig` from orchestration_types.py. Verify whether it has any active callers before deciding. If only called by dead methods, it can go. If unsure, leave it.
- **`_generate_team_context_header()`** in orchestration_service.py - ACTIVE, called by `get_agent_mission()`. Do NOT touch.
- **`AgentConfig`** in orchestration_types.py - Still imported. Do NOT delete.

## Verification Steps

After each deletion:
1. `ruff check src/ api/` - zero lint errors
2. `grep -r "WorkflowEngine\|JobCoordinator\|workflow_engine\|job_coordinator" src/` - zero hits
3. `grep -r "process_product_vision\|coordinate_agent_workflow\|generate_mission_plan\|select_agents_for_mission" src/` - zero hits (except comments)
4. Run existing tests to confirm nothing breaks

## Constraints

- Follow `handovers/handover_instructions.md` conventions
- Use Serena MCP for codebase navigation
- Pre-commit hooks must pass
- Leave codebase cleaner than you found it - but only delete what is verified dead
- When in doubt, leave it and document why
