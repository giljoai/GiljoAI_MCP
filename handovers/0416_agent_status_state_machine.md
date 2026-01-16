# Handover 0416: Agent Status State Machine Enhancement

**Date:** 2026-01-15
**Priority:** HIGH
**Status:** Ready for Implementation
**Estimated Complexity:** 6-10 hours
**Recommended Agent:** tdd-implementor

---

## Pre-Implementation Required Reading

**MUST READ FIRST:**
1. `F:\GiljoAI_MCP\handovers\Reference_docs\QUICK_LAUNCH.txt`
2. `F:\GiljoAI_MCP\handovers\Reference_docs\AGENT_FLOW_SUMMARY.md`

**Follow TDD Protocol:**
1. Write tests FIRST (they should fail initially)
2. Implement minimal code to make tests pass
3. Refactor if needed
4. Test BEHAVIOR, not implementation

---

## Objective

Redefine BLOCKED and FAILED statuses with clear, enforceable semantics. BLOCKED becomes a non-terminal "needs user attention" signal. FAILED becomes a server-enforced protocol violation status.

## Problem Statement

Current issues:
1. **BLOCKED is terminal** - but agents should recover when user responds
2. **FAILED is vague** - "fatal error" could mean anything
3. **Agents self-report FAILED** - no enforcement, agents can lie
4. **No distinction** between "needs input" vs "abandoned task"

## Solution Design

### Status Definitions (Revised)

| Status | Meaning | Terminal? | Who Sets It |
|--------|---------|-----------|-------------|
| `waiting` | Job created, not started | No | System |
| `working` | Agent actively executing | No | Agent |
| `blocked` | Agent explicitly needs user input | **No** | Agent |
| `complete` | Finished properly, all checks passed | Yes | System (validated) |
| `failed` | Protocol violation detected | Yes | **System only** |
| `cancelled` | User cancelled | Yes | System |
| `decommissioned` | Archived | Yes | System |

### Key Changes

1. **BLOCKED is non-terminal** - Agent can transition BLOCKED → WORKING when user responds
2. **FAILED is system-enforced** - Agents cannot call FAILED directly
3. **complete_job() validates** - Returns rejection if protocol not followed
4. **Staleness timeout** - Silent agent → auto-FAILED after configurable timeout

### Protocol Violations That Trigger FAILED

Server checks these when agent calls `complete_job()`:

1. **Unacknowledged messages** - Agent has unread messages sent before completion attempt
2. **Incomplete mission steps** - Agent didn't report progress on required steps
3. **Staleness timeout** - Agent silent for X minutes without completion (background check)

---

## Implementation Plan

### Phase 1: Backend - Status Validation (TDD)

**Tests to write first:**
```python
# tests/unit/test_status_state_machine.py

def test_blocked_is_not_terminal():
    """Agent can transition blocked → working"""

def test_complete_job_rejects_unread_messages():
    """complete_job() returns error if agent has unread messages"""

def test_complete_job_rejects_incomplete_steps():
    """complete_job() returns error if mission steps incomplete"""

def test_agent_cannot_set_failed_directly():
    """Calling report_error with status=failed is rejected"""

def test_staleness_triggers_failed():
    """Agent silent past timeout gets auto-failed"""

def test_blocked_to_working_transition_allowed():
    """Status can transition from blocked to working"""

def test_complete_to_working_transition_blocked():
    """Cannot go from complete back to working"""
```

**Files to modify:**
- `src/giljo_mcp/services/agent_job_manager.py` - Add validation to `complete_job()`
- `src/giljo_mcp/tools/orchestration.py` - Update `complete_job()` MCP tool
- `src/giljo_mcp/models/agent_identity.py` - Add state transition validation

### Phase 2: Backend - Completion Validation Logic

**New validation in `complete_job()`:**

```python
async def complete_job(self, job_id: str, result: dict, tenant_key: str) -> dict:
    """Complete job with protocol validation."""

    # Check 1: Unread messages
    unread = await self._get_unread_messages(job_id, tenant_key)
    if unread:
        return {
            "success": False,
            "error": "INCOMPLETE_PROTOCOL",
            "message": f"You have {len(unread)} unread messages. Read and acknowledge before completing.",
            "unread_message_ids": [m.id for m in unread],
            "action_required": "Call receive_messages() and acknowledge pending messages"
        }

    # Check 2: Mission steps (if structured mission)
    incomplete_steps = await self._get_incomplete_steps(job_id, tenant_key)
    if incomplete_steps:
        return {
            "success": False,
            "error": "INCOMPLETE_STEPS",
            "message": f"Mission steps incomplete: {incomplete_steps}",
            "action_required": "Complete remaining steps or report why they cannot be done"
        }

    # Validation passed - actually complete
    return await self._do_complete_job(job_id, result, tenant_key)
```

### Phase 3: Backend - BLOCKED Non-Terminal

**State transition rules:**
```python
VALID_TRANSITIONS = {
    "waiting": ["working", "cancelled"],
    "working": ["blocked", "complete", "cancelled", "decommissioned"],
    "blocked": ["working", "cancelled", "decommissioned"],  # Can return to working!
    "complete": [],  # Terminal
    "failed": [],    # Terminal
    "cancelled": [], # Terminal
    "decommissioned": [],  # Terminal
}

def validate_transition(current: str, new: str) -> bool:
    """Check if status transition is valid."""
    return new in VALID_TRANSITIONS.get(current, [])
```

### Phase 4: Agent Template Injection

**Update agent instructions to include protocol:**

```markdown
## Completion Protocol

Before calling complete_job(), you MUST:
1. Read all pending messages: `receive_messages()`
2. Acknowledge each message: `acknowledge_message()`
3. Report progress on all mission steps

If you call complete_job() without completing protocol,
the system will reject your completion and tell you what's missing.

If you close without completing, your status will be set to FAILED.
```

**Files to modify:**
- `src/giljo_mcp/tools/orchestration.py` - Add protocol to `get_agent_mission()` response
- Agent template files in dashboard

### Phase 5: Frontend - Status Display

**Update status configuration:**

```javascript
// frontend/src/utils/statusConfig.js

blocked: {
  label: 'Needs Input',
  color: '#ff9800',  // Orange/Yellow warning
  chipColor: 'warning',
  italic: false,
  icon: 'mdi-account-question',  // Person with question mark
  isTerminal: false,  // KEY CHANGE
},

failed: {
  label: 'Protocol Violation',
  color: '#e53935',  // Red
  chipColor: 'error',
  italic: false,
  icon: 'mdi-alert-octagon',
  isTerminal: true,
}
```

### Phase 6: Notification System Integration

**Existing staleness system enhancement:**

```javascript
// Staleness notification already exists
// Enhance to distinguish:
// - "Agent silent" (staleness) → Yellow notification
// - "Agent needs input" (blocked) → Orange notification
// - "Agent failed protocol" (failed) → Red notification
```

---

## Testing Requirements

### Unit Tests
- Status transition validation (all valid/invalid combinations)
- complete_job() rejection scenarios
- Message acknowledgment checking
- Mission step completion checking

### Integration Tests
- Full workflow: agent works → blocked → user responds → working → complete
- Protocol violation: agent tries to complete with unread messages
- Staleness timeout: agent goes silent, auto-failed after timeout

### Manual Testing
1. Launch project, spawn agent
2. Send message to agent
3. Try to complete without reading message → should reject
4. Read message, acknowledge
5. Complete successfully
6. Verify status transitions in dashboard

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/giljo_mcp/services/agent_job_manager.py` | Add completion validation |
| `src/giljo_mcp/tools/orchestration.py` | Update complete_job(), add protocol to missions |
| `src/giljo_mcp/models/agent_identity.py` | Add state transition validation |
| `frontend/src/utils/statusConfig.js` | Update blocked/failed display, isTerminal flag |
| `frontend/src/utils/actionConfig.js` | Update terminal states list |
| `tests/unit/test_status_state_machine.py` | New test file |
| `tests/integration/test_completion_protocol.py` | New integration tests |

---

## Success Criteria

1. BLOCKED status is non-terminal (can return to WORKING)
2. Agents cannot self-report FAILED status
3. complete_job() validates protocol compliance before accepting
4. Dashboard shows appropriate colors/notifications for each status
5. All existing tests still pass
6. New tests cover state machine logic

---

## Pitfalls & Mitigations

| Risk | Mitigation |
|------|------------|
| Message timing race | Only check messages sent BEFORE completion attempt timestamp |
| Broadcast ack policy | Broadcasts to "all" are optional to ack; direct messages required |
| Custom templates | Inject protocol at runtime via get_agent_mission(), not just static template |
| Loop on rejection | Return specific blockers: "Read message ID X" not just "incomplete" |
| Detecting "closed" | Staleness timeout → auto-FAILED is the fallback |

---

## References

- Simple_Vision.md - Agent lifecycle documentation
- start_to_finish_agent_FLOW.md - Status flow diagrams
- Handover 0366 - Agent identity refactor (current status model)
- Handover 0415 - Chapter-based protocol (context for orchestrator workflow)
