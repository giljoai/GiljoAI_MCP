# Handover: Staging Broadcast Response Enforcement

**Date:** 2026-02-05
**From Agent:** Research session (Claude Opus 4.5)
**To Agent:** tdd-implementor, backend-integration-tester
**Priority:** HIGH
**Estimated Complexity:** 3-4 hours
**Status:** Ready for Implementation
**Parent:** 0709 (Implementation Phase Gate)

---

## Task Summary

Enrich the `send_message()` response with an explicit STOP directive when a staging-phase orchestrator broadcasts to all agents. Currently the STAGING_COMPLETE broadcast returns a generic `{"success": true}` response with no reinforcement that the session should end. This causes orchestrators to continue into implementation despite protocol instructions.

**Why it's important:** In alpha testing, orchestrators repeatedly ignored the "STAGING ENDS HERE" text instruction and proceeded to spawn Task() agents. The 0709 gate catches the spawned agents (they get BLOCKED at `get_agent_mission()`), but the orchestrator still wastes tokens attempting implementation. A stronger signal in the broadcast response would reduce this.

**Expected outcome:** When the staging orchestrator sends the STAGING_COMPLETE broadcast, the server returns an enriched response containing a clear `staging_directive` that tells the LLM to stop.

---

## Context and Background

### The Gap (Discovered in Alpha Testing)

0709 added hard server-side gates on `get_agent_mission()` and `acknowledge_job()`. These catch **agents** that are prematurely launched. But nothing catches the **orchestrator itself** from continuing after staging.

The orchestrator's flow:
1. Steps 1-7: Create mission, spawn agents, persist plan -- all correct
2. Step 7 Finale: Call `send_message(to_agents=['all'], content='STAGING_COMPLETE...')`
3. Server returns: `{"success": true, "data": {"message_id": "...", "to_agents": [...], "type": "broadcast"}}`
4. **Gap**: Nothing in this response says "stop now"
5. Orchestrator continues into implementation (calling Task() to spawn subagents)

### Why Not a New Tool?

We considered a dedicated `complete_staging()` MCP tool but rejected it because:
- LLMs already follow tool call instructions reliably (the orchestrator DOES call `send_message()` as instructed)
- The problem is what happens **after the response**, not which tool is called
- A new tool has the same compliance gamble -- what guarantees the LLM calls `complete_staging()` instead of `send_message()`?
- Adding a new tool increases schema token cost for all agents

### Why Context-Based Detection Works

The server can detect "this is the staging completion broadcast" without content-sniffing:
1. **Sender is the orchestrator** for the project (check AgentExecution -> AgentJob)
2. **Job status is "waiting"** (staging phase -- implementation orchestrators are "working")
3. **Broadcast to all agents** (`to_agents` resolves to all active agents)

This combination is unique to the staging completion. During implementation, the orchestrator's job status is "working", so implementation-phase broadcasts won't trigger the enrichment.

### Defense-in-Depth Position

This handover adds **Layer 5.5** to the existing defense stack:

| Layer | Mechanism | Type | Handover |
|-------|-----------|------|----------|
| 1-4 | Prompt framing, protocol, metadata | Advisory | 0415, 0246a |
| 5 | CH5 exclusion during staging | Soft gate | 0420d |
| **5.5** | **Enriched broadcast response (THIS)** | **Reinforced advisory** | **0709b** |
| 6 | `get_agent_mission()` BLOCKED | Hard gate | 0709 |
| 7 | `acknowledge_job()` BLOCKED | Hard gate | 0709 |
| 8 | User action gate (Implement button) | Hard gate | 0709 |

---

## Technical Details

### Files to Modify

| File | Change |
|------|--------|
| `src/giljo_mcp/services/message_service.py` | Detect staging orchestrator broadcast, enrich response |
| `src/giljo_mcp/tools/orchestration.py` | Update CH2 Step 7 Finale text to mention enriched response |
| `src/giljo_mcp/services/orchestration_service.py` | (If service-level `get_orchestrator_instructions` also builds CH2 text) |

### Primary Change: MessageService.send_message()

**File:** `src/giljo_mcp/services/message_service.py`

After the broadcast fan-out succeeds and the normal response dict is built, add detection logic:

```python
# After normal broadcast response is built...
response = {
    "success": True,
    "data": {
        "message_id": str(first_message.id),
        "to_agents": resolved_agent_ids,
        "type": "broadcast"
    }
}

# 0709b: Detect staging orchestrator broadcasting to all
# Conditions: sender is orchestrator + job in "waiting" status + broadcast
if is_staging_orchestrator_broadcast:
    response["staging_directive"] = {
        "status": "STAGING_SESSION_COMPLETE",
        "action": "STOP",
        "message": (
            "STAGING IS COMPLETE. Your session must end NOW. "
            "Do NOT proceed to implementation. Do NOT call Task(). "
            "Do NOT call complete_job() or write_360_memory(). "
            "The user will click 'Implement' in the dashboard to start "
            "a new implementation session with a fresh orchestrator."
        ),
        "implementation_gate": "LOCKED",
        "next_step": "Report staging complete to user and stop."
    }
```

### Detection Logic

To determine `is_staging_orchestrator_broadcast`:

```python
# 1. Check if this is a broadcast (to_agents resolved to multiple agents)
is_broadcast = len(resolved_agent_ids) > 1 or original_to_agents == ['all']

# 2. Check if sender is an orchestrator in staging phase
if is_broadcast and from_agent:
    # Look up sender's execution
    sender_execution = await session.execute(
        select(AgentExecution).where(AgentExecution.agent_id == from_agent)
    )
    sender = sender_execution.scalar_one_or_none()

    if sender:
        # Look up the job
        sender_job = await session.get(AgentJob, sender.job_id)
        if sender_job:
            # Check: is this an orchestrator template AND job is in staging (waiting)?
            is_orchestrator = sender_job.agent_name == "orchestrator"
            is_staging = sender_job.status == "waiting"
            is_staging_orchestrator_broadcast = is_orchestrator and is_staging
```

**Key condition**: `sender_job.agent_name == "orchestrator"` AND `sender_job.status == "waiting"`. This is tight enough to avoid false positives:
- Agents broadcasting during implementation: their jobs are "working" or "complete"
- Implementation-phase orchestrators: their jobs are "working" (acknowledged)
- Only staging orchestrators have `agent_name == "orchestrator"` AND `status == "waiting"`

### Protocol Update: CH2 Step 7 Finale

**File:** `src/giljo_mcp/tools/orchestration.py` in `_build_orchestrator_protocol()`

Update the Step 7 Finale text to mention the enriched response:

```
-- STEP 7 FINALE: Signal Complete
Call: send_message(
          to_agents=['all'],
          content='STAGING_COMPLETE: Mission created, N agents spawned',
          project_id='{project_id}',
          message_type='broadcast'
      )

The server will confirm staging completion in the response with a
`staging_directive` field containing status: "STAGING_SESSION_COMPLETE".
When you see this directive, your session is DONE.

WARNING: STAGING ENDS HERE - DO NOT call complete_job() or write_360_memory()
   Your session is done. Implementation happens in a new session.
```

---

## Implementation Plan

### Phase 1: Backend -- Enrich Broadcast Response (tdd-implementor)

1. **Write test**: staging orchestrator broadcasts -> response contains `staging_directive`
2. **Write test**: non-orchestrator agent broadcasts -> response does NOT contain `staging_directive`
3. **Write test**: implementation-phase orchestrator (status="working") broadcasts -> response does NOT contain `staging_directive`
4. **Implement detection** in `MessageService.send_message()`:
   - After broadcast fan-out completes
   - Check sender is orchestrator + job status "waiting"
   - If match, add `staging_directive` to response
5. **Write test**: verify `staging_directive` contains required fields (`status`, `action`, `message`, `implementation_gate`)

### Phase 2: Protocol Update (tdd-implementor)

1. Update `_build_orchestrator_protocol()` CH2 Step 7 Finale text
2. Mention the `staging_directive` response field
3. Verify protocol text renders correctly in `get_orchestrator_instructions()` response

### Phase 3: Verification

1. Run `pytest tests/services/test_message_service*.py` -- all pass
2. Run `pytest tests/` -- no regressions
3. Verify `get_orchestrator_instructions()` returns updated protocol text

---

## Testing Requirements

### Unit Tests

```python
# tests/services/test_message_service_staging_directive.py

async def test_staging_orchestrator_broadcast_includes_directive():
    """Broadcast from staging orchestrator includes staging_directive."""
    # Setup: orchestrator job with status="waiting", agent_name="orchestrator"
    # Action: send_message(to_agents=['all'], from_agent=orchestrator_agent_id)
    # Assert: response contains "staging_directive" with status="STAGING_SESSION_COMPLETE"

async def test_regular_agent_broadcast_no_directive():
    """Broadcast from regular agent does NOT include staging_directive."""
    # Setup: regular agent job with status="working", agent_name="implementer"
    # Action: send_message(to_agents=['all'], from_agent=agent_id)
    # Assert: response does NOT contain "staging_directive"

async def test_implementation_orchestrator_broadcast_no_directive():
    """Broadcast from implementation-phase orchestrator does NOT include directive."""
    # Setup: orchestrator job with status="working" (acknowledged, in implementation)
    # Action: send_message(to_agents=['all'], from_agent=orchestrator_agent_id)
    # Assert: response does NOT contain "staging_directive"

async def test_staging_directive_fields():
    """Verify staging_directive contains all required fields."""
    # Assert fields: status, action, message, implementation_gate, next_step

async def test_direct_message_no_directive():
    """Direct message (not broadcast) from orchestrator has no directive."""
    # Setup: staging orchestrator sends to one specific agent
    # Assert: response does NOT contain "staging_directive"
```

### Integration Tests

```python
async def test_staging_broadcast_then_blocked_agent_flow():
    """Full flow: orchestrator broadcasts, agents blocked, directive present."""
    # 1. Create project (implementation_launched_at=NULL)
    # 2. Spawn orchestrator (status=waiting)
    # 3. Spawn agent jobs
    # 4. Orchestrator broadcasts STAGING_COMPLETE
    # 5. Verify response has staging_directive
    # 6. Agent calls get_agent_mission() -> BLOCKED (0709 gate still works)
```

---

## Dependencies and Blockers

**Dependencies:**
- 0709 (Implementation Phase Gate) -- COMPLETE. This handover builds on top of 0709's infrastructure.

**No blockers.** All required models and services already exist.

---

## Success Criteria

- [ ] Staging orchestrator broadcast response includes `staging_directive` with STOP action
- [ ] Non-orchestrator broadcasts unaffected (no directive)
- [ ] Implementation-phase orchestrator broadcasts unaffected (no directive)
- [ ] Direct messages (non-broadcast) unaffected
- [ ] CH2 Step 7 Finale protocol text mentions the enriched response
- [ ] All new tests pass
- [ ] All existing tests still pass

---

## Rollback Plan

Low-risk change. Rollback = remove the detection block in `send_message()`. The `staging_directive` is additive -- it doesn't change any existing response fields, only adds a new one. Removing it reverts to the current generic success response.

---

## Related

- **Parent:** 0709 (Implementation Phase Gate) -- `handovers/0709_implementation_phase_gate.md`
- **Protocol:** `_build_orchestrator_protocol()` in `src/giljo_mcp/tools/orchestration.py`
- **Message Service:** `src/giljo_mcp/services/message_service.py`
- **Orchestrator Instructions:** `src/giljo_mcp/services/orchestration_service.py`
