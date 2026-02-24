# 0411a Kickoff: Recommended Execution Order (Phase Labels)

Read and implement `F:\GiljoAI_MCP\handovers\0411a_recommended_execution_order.md`.

## What You're Building

Add a `phase` integer to AgentJob so the staging orchestrator can recommend execution order in multi-terminal mode. The Jobs tab groups agents by phase, showing users which agents to launch first, which run in parallel, and which wait.

**This is advisory only** - no auto-spawning, no job scheduling. The user clicks play buttons in phase order.

## Key Files

- **Model**: `src/giljo_mcp/models/agent_identity.py` - Add `phase` Column(Integer, nullable=True)
- **Service**: `src/giljo_mcp/services/orchestration_service.py`:
  - `spawn_agent_job()` (~line 1230) - Add `phase` parameter, also populate `template_id` (FK exists but is never set)
  - `get_orchestrator_instructions()` (~line 3211) - Add phase assignment instructions ONLY when `execution_mode != 'claude_code_cli'`
- **MCP Tool**: Find the tool wrapping `spawn_agent_job` in `src/giljo_mcp/tools/` - expose `phase` parameter
- **Frontend**: `frontend/src/components/projects/JobsTab.vue` - Group agent rows by phase with header rows
- **Migration**: Alembic migration for the new column

## Critical Constraints

- Phase grouping ONLY applies in multi-terminal mode
- When no agents have phases (CLI mode, legacy), render flat table exactly as today
- Follow TDD: write tests first
- Follow `handovers/handover_instructions.md` conventions
- Use Serena MCP for codebase navigation
- Pre-commit hooks must pass (never --no-verify)

## Architecture Context

- `AgentTemplate.cli_tool` already exists (claude/codex/gemini/generic) but is NOT exposed to orchestrator - out of scope
- `_generate_team_context_header()` has hardcoded `dependency_rules` for 5 roles - informational only, not connected to phases
- WorkflowEngine/WorkflowStage exist but are dead code (0411b will clean up) - do not use them
- `AgentJob.template_id` FK exists but is never populated - fix this while you're in `spawn_agent_job()`

## Visualization Target

The phase grouping appears on the Jobs tab at:
`http://localhost:7274/projects/{id}?via=jobs&tab=jobs`

Above the existing agent table, insert phase group header rows:
```
Phase 1
  [AN] Analyzer         | waiting | ...
Phase 2 (after Phase 1)
  [FI] FE-Implementer   | waiting | ...
  [BI] BE-Implementer   | waiting | ...
Phase 3 (after Phase 2)
  [TE] Tester            | waiting | ...
```
