# Handover: Orchestrator Fixture on Project Activation

**Date:** 2026-01-22
**From Agent:** Claude Opus 4.5 (Investigation & Implementation)
**To Agent:** Completed
**Priority:** Critical
**Status:** Completed

---

## Task Summary

Fixed critical regression where orchestrator was not appearing in UI when project was activated. Implemented orchestrator "fixture" pattern - orchestrator is now auto-created on project activation (before "Stage Project" is clicked), indicating to users an agent is ready.

---

## Root Cause Analysis

**Investigation Used:** 4 parallel subagents (deep-researcher, system-architect, database-expert)

**Findings:**
1. Project 25e7103d had ZERO agent jobs in database - staging was never executed
2. `orchestrator:prompt_generated` WebSocket event had NO handler in frontend
3. Backend orchestrator creation was intact but UI never updated

---

## Implementation Summary

### What Was Built

**Backend** (`src/giljo_mcp/services/project_service.py`):
- Added `_ensure_orchestrator_fixture()` method (lines 997-1132)
- Creates `AgentJob` + `AgentExecution` with status='waiting' on activation
- Broadcasts `agent:created` WebSocket event for immediate UI update
- Idempotent - skips if orchestrator already exists

**Frontend** (`frontend/src/stores/websocketEventRouter.js`):
- Added `orchestrator:prompt_generated` event handler (lines 158-180)
- Updates existing orchestrator when staging prompt is generated

### Key Files Modified
- `src/giljo_mcp/services/project_service.py` (+146 lines)
- `frontend/src/stores/websocketEventRouter.js` (+23 lines)

### New Workflow
1. Project activated → Orchestrator fixture created → `agent:created` event → UI shows orchestrator
2. User clicks "Stage Project" → Staging endpoint reuses orchestrator → `orchestrator:prompt_generated` event
3. User pastes prompt → Orchestrator starts working

---

## Testing

- Backend creates orchestrator on activation
- WebSocket event broadcasts correctly
- Frontend receives and displays orchestrator immediately
- Staging endpoint reuses existing orchestrator (no duplicates)

---

## Git Commit

```
0bde61d9 feat: Create orchestrator fixture on project activation (Handover 0431)
```

**Note:** Commit message referenced 0431 but this is the correct handover number (0432).

---

## Status

**Completed** - All tests passing, committed to master.
