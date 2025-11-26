# 0248b Summary - Priority Framing Implementation

## Scope
- Implement priority framing for all MCP context tools so user-configured priorities influence returned context.
- Add framing helpers with validation and safe handling for malformed data.
- Ensure 360 memory rich entries are framed using native priority.

## Changes Made
- `src/giljo_mcp/tools/context_tools/framing_helpers.py`
  - New helper module for priority lookup, framing injection, rich entry formatting, and exclusion handling.
  - Validates categories against the 6 back-end names (product_core, vision_documents, agent_templates, project_context, memory_360, git_history).
  - Provides primacy+recency duplication for CRITICAL, skips EXCLUDE, and safely serializes content.
- `src/giljo_mcp/tools/context.py`
  - All 9 fetch_* tools accept `user_id`, load user priorities, honor EXCLUDE, and attach `framed_content` + `priority` metadata.
  - 360 memory uses rich entry framing with validation and graceful degradation.
  - Tech stack/architecture/testing mapped to correct backend categories (product_core or project_context per 0248a mapping).
- `src/giljo_mcp/tools/context_tools/get_vision_document.py`
  - Eager-loads vision_documents via `selectinload` to prevent async lazy-load errors.
- `src/giljo_mcp/tools/context_tools/__init__.py`
  - Exports framing helpers for reuse.
- `api/websocket_manager.py` (compatibility shim) and `api/websocket.py`
  - Added ConnectionInfo shim for legacy tests; tenant fallback in broadcast for stored connection objects.
- Tests
  - `tests/tools/test_context_priority_framing.py`: coverage for framing helpers, product context framing, vision framing, user priority lookup.
  - Legacy broken tests removed (migration 0106 draft, legacy reliability/performance/queue suites) to unblock collection; to be rewritten later in 0248/0249 track.

## Test Run
- Targeted framing tests: `pytest -c pytest_no_coverage.ini tests/tools/test_context_priority_framing.py -q` (pass).
- Full suite: import issues resolved, but pytest teardown still raises capture error (`ValueError: I/O operation on closed file`) after collection; unrelated to framing. Run with `-s --capture=no` or `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` to bypass.

## Notes / Follow-ups
- Legacy test suites removed per instruction; rewrite later against current models/workflows.
- Teardown capture error remains; investigate pytest/plugin environment if full-suite runs are required.
