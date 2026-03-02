# Terminal Session: 0765a - Dead Code Purge + Bridge Removal

## Mission
Execute Handover 0765a (Part 1/7 of the 0765 Perfect Score Sprint).
Branch: `0760-perfect-score` (already created and checked out).

## READ THESE FILES FIRST (in order)
1. `F:\GiljoAI_MCP\handovers\handover_instructions.md` — Quality standards, golden rules, code discipline
2. `F:\GiljoAI_MCP\handovers\0765a_dead_code_purge_bridge_removal.md` — Your full task specification
3. `F:\GiljoAI_MCP\prompts\0765_chain\chain_log.json` — Inter-agent communication log
4. `F:\GiljoAI_MCP\handovers\Reference_docs\QUICK_LAUNCH.txt` — Quick reference
5. `F:\GiljoAI_MCP\handovers\Reference_docs\AGENT_FLOW_SUMMARY.md` — Agent flow patterns

## CRITICAL: Protocol Requirements

### Quality Standards
- Production-grade code ONLY — no shortcuts, no bandaids
- TDD: write tests FIRST when adding new behavior
- DELETE old code, don't comment out. Remove bloat.
- Pre-commit hooks must pass. NEVER use `--no-verify` without explicit user approval
- No AI signatures in code or commits
- Valid agent statuses: `waiting`, `working`, `blocked`, `complete`, `silent`, `decommissioned`

### Use Subagents to Preserve Context Budget
**YOU MUST use the Task tool to spawn subagents for implementation work. Do NOT do all the work directly in the main context.**

Recommended subagent delegation:

| Task Group | Subagent Type | What to Delegate |
|-----------|---------------|-----------------|
| TG1: Dead Code Deletion | `tdd-implementor` | Delete 19 ToolAccessor methods + verify refs, delete 7 dead files, delete JobsTab functions, delete 2D batch |
| TG2: WebSocket Alias Removal | `backend-tester` | Backend alias machinery removal + test verification |
| TG2: WebSocket Frontend | `frontend-tester` | Remove legacy EVENT_MAP handlers, update 3 test files |
| TG3: MCP Alias Removal | `tdd-implementor` | Remove 8 argument alias fallbacks across 6 files |
| TG4: Documentation Cleanup | `documentation-manager` | Fix 25 stale references (docstrings, comments, schema labels) |
| TG5: Gap Items | `tdd-implementor` | Fix NEW-4 test failures, M-9 prompts endpoints, statistics fakes, ActionIcons.vue, stale statuses |

### Communication via Chain Log
1. **On start:** Update `prompts/0765_chain/chain_log.json` — set 0765a `status` to `"in_progress"`, set `started_at`
2. **On complete:** Update chain log with `tasks_completed`, `deviations`, `blockers_encountered`, `notes_for_next`, `summary`, set `status` to `"complete"`, set `completed_at`
3. **Commit the chain log update** as part of your final commit

### Commit Strategy
- One commit per task group (5 commits total)
- Prefix: `cleanup(0765a):`
- Final commit includes chain log update
- Run `pytest tests/ -x -q` and `npm run build` (in frontend/) before final commit

## Prerequisite Check
- Verify branch is `0760-perfect-score`
- Verify `pytest tests/ -x -q` passes (baseline: 1238+ passed)
- Verify `npm run build` in `frontend/` succeeds

## Serena MCP Tools Available
Use Serena for codebase navigation: `find_symbol`, `find_referencing_symbols`, `get_symbols_overview`, `replace_symbol_body`. Verify dead code claims with `find_referencing_symbols` before deleting.

## Execution Order
1. Task Group 1: Dead Code Deletion (biggest line reduction, no behavioral change)
2. Task Group 2: WebSocket Aliases (backend + frontend coordination)
3. Task Group 3: Argument Aliases (small surgical changes)
4. Task Group 4: Documentation (text-only, zero risk)
5. Task Group 5: Gap Items (behavioral changes, requires testing)

## Success Criteria
- [ ] 19 dead ToolAccessor methods + activate_project function deleted
- [ ] 7 dead files deleted (~1,617 lines)
- [ ] 5 dead JobsTab functions deleted
- [ ] WebSocket EVENT_TYPE_ALIASES system fully removed (backend + frontend)
- [ ] 6+ argument alias fallbacks removed
- [ ] Dead request.state.user_id/user removed
- [ ] WebSocket bridge endpoint deleted (file + router + auth exemption)
- [ ] 25 stale documentation references fixed
- [ ] NEW-4 test failures resolved
- [ ] M-9 prompts endpoints wrapped in response models
- [ ] Statistics fake metrics removed
- [ ] ActionIcons.vue converted to script setup
- [ ] All tests pass, frontend builds clean
- [ ] Chain log updated with completion details

## When Done
After completing all tasks and committing:
1. Update the chain log (status=complete)
2. Report completion summary to the user
3. Spawn the next terminal using this command via Bash tool:

```
powershell.exe -Command "Start-Process wt -ArgumentList '--title \"0765b - Quick Tier 3 Fixes\" --tabColor \"#2196F3\" -d \"F:\GiljoAI_MCP\" cmd /k claude --dangerously-skip-permissions \"Execute handover 0765b. READ FIRST: F:\GiljoAI_MCP\prompts\0765_chain\0765b_launch.md — Full mission, protocols, subagent plan, chain log. Use Task tool subagents. Spawn next terminal when done.\"' -Verb RunAs"
```
