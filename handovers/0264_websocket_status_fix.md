# Handover 0264: WebSocket Status Inconsistency Fix

**Type**: Bug Fix
**Priority**: HIGH
**Discovered**: 2025-11-29 (During workflow harmonization investigation)
**Status**: Ready for Implementation

---

## Executive Summary

Critical WebSocket bug discovered where agent job creation broadcasts incorrect status values. The WebSocket events send API aliases (`"pending"`) but the frontend expects database values (`"waiting"`), causing potential UI display issues.

---

## The Bug

### Location
`api/endpoints/agent_jobs/lifecycle.py`, line 75

### Current (BROKEN) Code
```python
await ws_dep.broadcast_to_tenant(
    tenant_key=current_user.tenant_key,
    event_type="agent:created",
    data={
        "agent_job_id": result["agent_job_id"],
        "status": "pending"  # ❌ WRONG: Sends API alias
    }
)
```

### Expected (FIXED) Code
```python
await ws_dep.broadcast_to_tenant(
    tenant_key=current_user.tenant_key,
    event_type="agent:created",
    data={
        "agent_job_id": result["agent_job_id"],
        "status": "waiting"  # ✅ CORRECT: Sends database value
    }
)
```

---

## Root Cause Analysis

### The Dual-Status Architecture

GiljoAI implements an intentional dual-status system (Handover 0113):

**Database Layer** (Authoritative):
- Values: `waiting`, `working`, `blocked`, `complete`, `failed`, `cancelled`, `decommissioned`
- Enforced by database constraint in `src/giljo_mcp/models/agents.py`

**API Layer** (Client-facing aliases):
- Values: `pending`, `active`, `completed`
- Translated by `AgentJobManager` for backward compatibility

### The Problem

1. **Frontend Configuration** (`frontend/src/utils/statusConfig.js`):
```javascript
statusConfig = {
  waiting: { label: 'Waiting.', color: '#ffd700' },
  working: { label: 'Working...', color: '#ffd700' },
  complete: { label: 'Complete', color: '#67bd6d' },
  // No "pending" status defined!
}
```

2. **Frontend expects database values** because it receives WebSocket events directly
3. **API endpoint sends alias value** (`"pending"`) instead of database value (`"waiting"`)
4. **Result**: Frontend cannot recognize status, may display undefined/error

---

## Impact Analysis

### Affected Components
- `JobsTab.vue` - Status display in job monitoring
- `AgentTableView.vue` - Agent status badges
- `StatusChip.vue` - Status rendering component
- Any component listening to `agent:created` WebSocket events

### User Impact
- Status badges may not display correctly for newly created jobs
- Color coding may fail (undefined status = no color)
- Status text may show as undefined or blank

---

## Fix Implementation

### Step 1: Fix the WebSocket Broadcast

**File**: `api/endpoints/agent_jobs/lifecycle.py`
**Line**: 75
**Change**: `"status": "pending"` → `"status": "waiting"`

### Step 2: Audit Other WebSocket Events

Search for all WebSocket broadcasts in the codebase to ensure consistency:

```bash
grep -r "broadcast_to_tenant" api/ --include="*.py" | grep -i status
```

Check each occurrence uses database values, not API aliases.

### Step 3: Add Test Coverage

Create test to verify WebSocket events use database values:

```python
async def test_spawn_agent_job_websocket_status():
    """Ensure WebSocket broadcasts use database status values."""
    # Spawn job
    result = await spawn_agent_job(...)

    # Check WebSocket event
    assert ws_event["data"]["status"] == "waiting"  # Not "pending"
```

---

## Validation Steps

1. **Start the application**: `python startup.py`
2. **Open browser**: Navigate to Projects → Stage Project
3. **Stage a project**: Click "Stage Project" button
4. **Monitor WebSocket**: Open browser dev tools → Network → WS tab
5. **Verify status**: Check `agent:created` event contains `"status": "waiting"`
6. **Check UI**: Verify status badge displays correctly as "Waiting."

---

## Prevention Strategy

### 1. Establish Clear Boundaries

**Rule**: WebSocket events ALWAYS use database values
- Database operations: Use database values
- WebSocket events: Use database values
- REST API responses: Use translated aliases (via `_expose_status()`)
- REST API requests: Accept aliases (via `_normalize_status()`)

### 2. Code Review Checklist

Add to PR template:
- [ ] WebSocket events use database status values
- [ ] No hardcoded status strings (use constants)
- [ ] Frontend components handle all valid database statuses

### 3. Documentation

Update `docs/ARCHITECTURE.md` with clear status value usage guidelines.

---

## Related Files

- `api/endpoints/agent_jobs/lifecycle.py` - Bug location
- `frontend/src/utils/statusConfig.js` - Frontend status configuration
- `src/giljo_mcp/agent_job_manager.py` - Status translation layer
- `src/giljo_mcp/models/agents.py` - Database constraint definition

---

## Success Criteria

- [ ] WebSocket event sends `"waiting"` not `"pending"`
- [ ] Frontend displays status badge correctly
- [ ] No console errors about undefined status
- [ ] Test added to prevent regression
- [ ] All WebSocket events audited and fixed

---

## Notes

This bug was discovered during the workflow harmonization investigation (2025-11-29) when comparing PDF slides, flow.md documentation, and actual code implementation. The comprehensive code review using Serena MCP tools revealed this critical inconsistency in WebSocket event handling.

The fix is simple but important for UI consistency. The dual-status system is intentional and well-designed, but WebSocket events must consistently use database values since the frontend bypasses the API translation layer.