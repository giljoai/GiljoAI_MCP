# Handover 0416: Agent Status State Machine Enhancement

**Date:** 2026-01-16
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

Redefine BLOCKED and FAILED statuses with clear, enforceable semantics:
- **BLOCKED**: Non-terminal "needs user attention" signal (agent can recover)
- **FAILED**: System-enforced protocol violation (not self-reported by agents)

## Problem Statement

Current issues:
1. **BLOCKED is terminal** - but agents should recover when user responds
2. **FAILED is vague** - "fatal error" could mean anything
3. **Agents self-report FAILED** - no enforcement, agents can lie
4. **No validation** at completion - agent can complete with unread messages or incomplete steps

## Architecture Context

### Instruction Layers (Both Modes)

Both Claude Code CLI and Multi-terminal modes call `get_agent_mission()` which returns `full_protocol`.

| Mode | Role/Expertise Source | Mission Source | Protocol Source |
|------|----------------------|----------------|-----------------|
| Claude Code CLI | Local `.claude/agents/*.md` | `get_agent_mission()` | `full_protocol` from server |
| Multi-terminal | Injected into mission | `get_agent_mission()` | `full_protocol` from server |

**Key insight**: Completion protocol goes in `full_protocol` → **both modes get it automatically**.

### Existing Infrastructure

| Feature | Storage | How It Works |
|---------|---------|--------------|
| **Steps** | `agent_todo_items` table + `job_metadata.todo_steps` | Agent calls `report_progress()` with `todo_items` array |
| **Messages** | `messages` table | Agent calls `receive_messages()` and `acknowledge_message()` |
| **Staleness** | Notification system | Already warns if agent is silent too long |

---

## Solution Design

### Status Definitions (Revised)

| Status | Meaning | Terminal? | Who Sets It |
|--------|---------|-----------|-------------|
| `waiting` | Job created, not started | No | System |
| `working` | Agent actively executing | No | Agent |
| `blocked` | Agent explicitly needs user input | **No** (can return to working) | Agent |
| `complete` | Finished properly, all checks passed | Yes | System (validated) |
| `failed` | Protocol violation detected | Yes | **System only** |
| `cancelled` | User cancelled | Yes | System |
| `decommissioned` | Archived | Yes | System |

### Key Changes

1. **BLOCKED is non-terminal** - Agent can transition BLOCKED → WORKING when user responds
2. **FAILED is system-enforced** - Agents cannot call FAILED directly; system detects violations
3. **`complete_job()` validates** - Returns rejection if protocol not followed
4. **Staleness timeout** - Silent agent → auto-FAILED after configurable timeout (existing system)

### Protocol Violations That Trigger Rejection/FAILED

**At `complete_job()` call time:**
1. **Unread messages** - Agent has messages with `status='pending'` sent BEFORE completion attempt
2. **Incomplete TODO items** - Agent has `agent_todo_items` with `status != 'completed'`

**Note on messages after completion:** Messages sent TO an agent AFTER it completes are fine. The orchestrator handles those ("Read implementer's messages, do we need to respawn?"). The check is: "At the moment of `complete_job()`, you have 0 unread messages."

---

## Implementation Plan

### Phase 1: Update `full_protocol` (TDD)

**File:** `src/giljo_mcp/services/orchestration_service.py`
**Function:** `_generate_agent_protocol()`

Add to Phase 4 (COMPLETION):

```markdown
## Phase 4: COMPLETION

Before calling `complete_job()`, you MUST verify:

1. **All TODO items completed**: Every item in your TodoWrite list must be marked `completed`
2. **All messages read**: Call `receive_messages()` and acknowledge all pending messages

If you call `complete_job()` without meeting these requirements:
- System will REJECT your completion
- Response will list specific blockers:
  - "X TODO items not completed: [list]"
  - "Y unread messages waiting"
- Address the blockers, then try `complete_job()` again

If you close/abandon without completing properly, system sets status to FAILED.
```

**Tests to write first:**
```python
# tests/unit/test_agent_protocol_completion.py

def test_full_protocol_contains_completion_requirements():
    """full_protocol includes TODO and message requirements"""

def test_full_protocol_explains_rejection_response():
    """full_protocol explains what happens on invalid completion"""
```

### Phase 2: Backend - `complete_job()` Validation (TDD)

**File:** `src/giljo_mcp/services/orchestration_service.py` or `agent_job_manager.py`

**Tests to write first:**
```python
# tests/unit/test_complete_job_validation.py

def test_complete_job_rejects_with_unread_messages():
    """complete_job() returns error listing unread message IDs"""

def test_complete_job_rejects_with_incomplete_todos():
    """complete_job() returns error listing incomplete TODO items"""

def test_complete_job_succeeds_when_all_complete():
    """complete_job() succeeds when todos done and messages read"""

def test_complete_job_ignores_messages_after_attempt():
    """Messages sent AFTER completion attempt don't block"""

def test_agent_cannot_set_failed_directly():
    """report_error with status=failed is rejected"""
```

**Implementation:**
```python
async def complete_job(self, job_id: str, result: dict, tenant_key: str) -> dict:
    """Complete job with protocol validation."""

    completion_attempt_time = datetime.utcnow()

    # Check 1: Unread messages (sent BEFORE this attempt)
    unread = await self._get_unread_messages_before(job_id, tenant_key, completion_attempt_time)

    # Check 2: Incomplete TODO items
    incomplete_todos = await self._get_incomplete_todos(job_id, tenant_key)

    if unread or incomplete_todos:
        reasons = []
        if unread:
            reasons.append(f"{len(unread)} unread messages waiting - call receive_messages() first")
        if incomplete_todos:
            todo_names = [t.content for t in incomplete_todos[:5]]  # First 5
            reasons.append(f"{len(incomplete_todos)} TODO items not completed: {todo_names}")

        return {
            "success": False,
            "error": "COMPLETION_BLOCKED",
            "reasons": reasons,
            "action_required": "Complete all TODO items and read all messages before calling complete_job()"
        }

    # Validation passed - actually complete
    return await self._do_complete_job(job_id, result, tenant_key)
```

### Phase 3: Backend - BLOCKED Non-Terminal (TDD)

**File:** `src/giljo_mcp/services/agent_job_manager.py` or models

**Tests to write first:**
```python
# tests/unit/test_status_transitions.py

def test_blocked_to_working_allowed():
    """Agent can transition blocked → working"""

def test_complete_to_working_blocked():
    """Cannot transition complete → working (terminal)"""

def test_failed_is_terminal():
    """Cannot transition from failed to any state"""

def test_working_to_blocked_allowed():
    """Agent can transition working → blocked"""
```

**State transition rules:**
```python
VALID_TRANSITIONS = {
    "waiting": ["working", "cancelled"],
    "working": ["blocked", "complete", "failed", "cancelled", "decommissioned"],
    "blocked": ["working", "cancelled", "decommissioned"],  # NON-TERMINAL
    "complete": [],  # Terminal
    "failed": [],    # Terminal
    "cancelled": [], # Terminal
    "decommissioned": [],  # Terminal
}
```

### Phase 4: Frontend - Status Display Updates

**File:** `frontend/src/utils/statusConfig.js`

```javascript
blocked: {
  label: 'Needs Input',
  color: '#ff9800',  // Orange warning
  chipColor: 'warning',
  italic: false,
  icon: 'mdi-account-question',
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

**File:** `frontend/src/utils/actionConfig.js`

Update terminal states and action availability for BLOCKED (allow cancel, allow resume).

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/giljo_mcp/services/orchestration_service.py` | Update `_generate_agent_protocol()` Phase 4; Add validation to `complete_job()` |
| `src/giljo_mcp/services/agent_job_manager.py` | Add state transition validation |
| `frontend/src/utils/statusConfig.js` | Update blocked/failed display, isTerminal flags |
| `frontend/src/utils/actionConfig.js` | Update terminal states, action availability |
| `tests/unit/test_complete_job_validation.py` | New test file |
| `tests/unit/test_status_transitions.py` | New test file |
| `tests/unit/test_agent_protocol_completion.py` | New test file |

---

## Testing Requirements

### Unit Tests
- `full_protocol` contains completion requirements
- `complete_job()` rejection scenarios (messages, todos)
- State transition validation (all valid/invalid combinations)
- Agent cannot self-report FAILED

### Integration Tests
- Full workflow: working → blocked → user responds → working → complete
- Protocol violation: agent tries to complete with unread messages → rejected → reads messages → completes
- Staleness timeout: agent silent too long → auto-FAILED

### Manual Testing
1. Launch project, spawn agent
2. Send message to agent
3. Agent tries `complete_job()` without reading → should reject with reason
4. Agent reads message, acknowledges
5. Agent tries `complete_job()` with incomplete TODOs → should reject with list
6. Agent completes all TODOs
7. Agent calls `complete_job()` → succeeds
8. Verify dashboard shows correct status transitions

---

## Success Criteria

1. ✅ BLOCKED status is non-terminal (can return to WORKING)
2. ✅ Agents cannot self-report FAILED status
3. ✅ `complete_job()` validates: all TODOs completed, all messages read
4. ✅ Rejection response lists specific blockers with actionable instructions
5. ✅ `full_protocol` documents completion requirements (applies to both CLI modes)
6. ✅ Dashboard shows appropriate colors/notifications for each status
7. ✅ All existing tests still pass
8. ✅ New tests cover state machine logic

---

## References

- `handovers/Reference_docs/Simple_Vision.md` - Agent lifecycle documentation
- `handovers/Reference_docs/start_to_finish_agent_FLOW.md` - Status flow diagrams
- `handovers/Agent instructions and where they live.md` - Instruction layer architecture
- Handover 0366 - Agent identity refactor (current status model)
- Handover 0402 - Agent TODO items table (todo_items implementation)
- Handover 0415 - Chapter-based protocol (orchestrator workflow context)
