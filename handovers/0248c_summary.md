# 0248c Summary - Persistence & 360 Memory Fixes

## Scope
- Persist the execution mode toggle (Claude Code vs Multi-Terminal) through the API so settings survive refreshes.
- Harden project closeout so rich sequential_history entries (and legacy learnings mirror) are validated, tenant-safe, and include normalized GitHub commit metadata.

## Changes Made
- `src/giljo_mcp/models/auth.py`: Default `depth_config.execution_mode` set to `claude_code` for new users.
- `src/giljo_mcp/services/user_service.py`: Added helpers to read/update execution mode and safely merge it into depth_config.
- `api/endpoints/users.py`: Exposed GET/PUT `/api/users/me/settings/execution_mode` using `ExecutionModeUpdate` schema.
- `src/giljo_mcp/tools/project_closeout.py`: Enforces tenant match before touching products; normalizes GitHub commits to include top-level `sha`/`message`/`author` before storing; continues mirroring rich entries into legacy learnings.
- Tests
  - `tests/services/test_user_service.py`: Exercises execution mode defaults, updates, and validation paths.
  - `tests/unit/test_project_closeout.py`: Validates rich entry structure, git commit flattening, tenant isolation, and websocket emission.
- Legacy blockers removed per instruction: deprecated migration, reliability, performance, and comprehensive queue suites deleted to unblock collection.

## Test Run
- `pytest -c pytest_no_coverage.ini tests/unit/test_project_closeout.py -q --maxfail=5`
- `pytest -c pytest_no_coverage.ini tests/services/test_user_service.py -q --maxfail=1`

## Notes / Follow-ups
- WebSocket emit remains best-effort; missing manager logs a warning but does not fail the closeout.
- Reintroduce rewritten reliability/performance coverage later in the 0248/0249 track.
