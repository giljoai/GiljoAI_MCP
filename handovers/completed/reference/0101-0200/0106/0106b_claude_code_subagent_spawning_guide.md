# Handover 0106b: Claude Code Subagent Spawning Implementation Guide

**Date**: 2025-11-05
**Status**: 📘 IMPLEMENTATION GUIDE
**Priority**: High (Companion to 0106)
**Estimated Complexity**: 2-3 hours (testing + examples)

---

## Purpose

Detailed implementation guide for orchestrators spawning Claude Code subagents. Companion to Handover 0106 (Template Protection) with specific examples, error handling, and testing procedures.

**Related Handovers**:
- **0106**: Agent Template Hardcoded Rules & Protection (parent)
- **0107**: Agent Monitoring & Graceful Cancellation (check-in protocol)
- **0105**: Orchestrator Mission Workflow (Implementation tab toggle)

---

## Claude Code Task Tool Overview

### What is the Task Tool?

Claude Code's native subagent spawning mechanism. Allows one Claude instance to spawn child agents that share the same terminal session.

**Key Features**:
- ✅ Single terminal window (no manual prompt copying)
- ✅ Native agent coordination within Claude
- ✅ Shared project context
- ✅ Automatic communication between main + subagents

**Constraints**:
- ❌ Must use MCP tools for GiljoAI coordination (not just Claude-to-Claude)
- ❌ Subagents need unique Agent IDs from backend
- ❌ Must follow check-in protocol (0107)

---

## Complete Spawning Flow

### Step 1: Orchestrator Registers Agent with Backend

```python
# Orchestrator calls MCP tool FIRST
result = spawn_agent_job(
    agent_type="implementer",           # Must be one of 8 active types
    agent_name="implementer-backend",   # Descriptive name
    mission="Implement user authentication endpoints",
    project_id="{project_id}",          # Injected at runtime
    tenant_key="{tenant_key}"           # Injected at runtime
)

# Check for errors
if not result.get('success'):
    print(f"❌ Failed to register agent: {result.get('error')}")
    print(f"Available agent types: {result.get('available_types')}")
    # STOP - Do not spawn Claude subagent without registration
    return

# Extract credentials
agent_id = result['agent_id']          # e.g., "implementer-abc123"
job_id = result['job_id']              # e.g., "job-xyz789"

print(f"✅ Agent registered: {agent_id}")
```

**Error Cases**:

```python
# Case 1: Agent type not active (not in 8 active types)
{
    "success": False,
    "error": "Agent type 'database-expert' is not active",
    "available_types": ["orchestrator", "implementer", "tester", ...]
}
# Solution: Use one of available types or ask user to activate in Template Manager

# Case 2: Rate limiting (too many spawns)
{
    "success": False,
    "error": "Rate limit exceeded: max 10 agents per minute",
    "retry_after": 30  # seconds
}
# Solution: Wait 30 seconds, then retry

# Case 3: Multi-tenant isolation error
{
    "success": False,
    "error": "Project not found or access denied",
}
# Solution: Verify project_id and tenant_key are correct
```

---

### Step 2: Orchestrator Spawns Claude Code Subagent

```python
# Use Claude Code's Task tool
from anthropic import Anthropic

client = Anthropic()

# Prepare instructions with credentials
instructions = f"""
# YOUR IDENTITY
Agent ID: {agent_id}
Job ID: {job_id}
Tenant Key: {tenant_key}
Project ID: {{project_id}}
Agent Type: implementer
Agent Name: implementer-backend

---

# YOUR MISSION
Implement user authentication endpoints with the following requirements:
- POST /auth/register (email, password validation)
- POST /auth/login (JWT token generation)
- GET /auth/me (verify token, return user data)
- Use bcrypt for password hashing
- Return standardized error responses

---

# CHECK-IN PROTOCOL (CRITICAL)

After completing each milestone:

1. **Report Progress**:
   report_progress(
     job_id="{job_id}",
     agent_id="{agent_id}",
     progress={{
       "task": "Current task description",
       "percent": 45,
       "todos_completed": 3,
       "todos_remaining": 5,
       "context_tokens_estimate": 12000
     }},
     tenant_key="{tenant_key}"
   )

2. **Check for Commands**:
   messages = receive_messages(
     agent_id="{agent_id}",
     limit=10,
     tenant_key="{tenant_key}"
   )

3. **Handle Commands**:
   - If message.type == "cancel": Stop work, call complete_job(), exit
   - If message.type == "pause": Wait for "resume" before continuing
   - If message.type == "priority_change": Adjust focus

---

# MCP TOOLS YOU MUST USE

**Job Lifecycle** (MANDATORY):
- acknowledge_job(job_id="{job_id}", agent_id="{agent_id}", tenant_key="{tenant_key}")
  → Call FIRST when you start

- complete_job(job_id="{job_id}", result={{"summary": "..."}}, tenant_key="{tenant_key}")
  → Call when finished

**Communication**:
- send_message(to_agent="orchestrator-{{project_id}}", message="...", tenant_key="{tenant_key}")
  → Update orchestrator on progress

- report_error(job_id="{job_id}", error="...", tenant_key="{tenant_key}")
  → Report blockers immediately

---

# WORK GUIDELINES

- Follow implementer role strictly (backend code only)
- Write production-grade code with tests
- Document your code
- Report blockers immediately (don't silently fail)
- Check in after each major milestone

---

BEGIN YOUR WORK:
"""

# Spawn subagent using Task tool
response = client.messages.create(
    model="claude-sonnet-4",
    max_tokens=8000,
    tools=[{"name": "task", "description": "Spawn a subagent"}],
    messages=[{
        "role": "user",
        "content": [{
            "type": "tool_use",
            "name": "task",
            "input": {
                "name": "implementer-backend",
                "instructions": instructions
            }
        }]
    }]
)

print(f"✅ Subagent spawned: implementer-backend")
print(f"   Agent ID: {agent_id}")
print(f"   Job ID: {job_id}")
```

---

### Step 3: Monitor Subagent Execution

**Orchestrator monitors via MCP**:

```python
# Check subagent progress
import asyncio

async def monitor_subagent(job_id, timeout_minutes=30):
    """Monitor subagent and handle issues."""

    start_time = time.time()

    while True:
        # Check job status
        job = await get_job_status(job_id, tenant_key)

        if job['status'] == 'complete':
            print(f"✅ Subagent completed: {job_id}")
            print(f"   Result: {job['result']}")
            break

        elif job['status'] == 'failed':
            print(f"❌ Subagent failed: {job_id}")
            print(f"   Error: {job['error']}")
            break

        elif job['status'] == 'blocked':
            print(f"⚠️ Subagent blocked: {job_id}")
            # Send guidance message
            await send_message(
                to_agent=job['agent_id'],
                message={"type": "guidance", "text": "How can I help?"},
                tenant_key=tenant_key
            )

        # Check for timeout
        elapsed_minutes = (time.time() - start_time) / 60
        if elapsed_minutes > timeout_minutes:
            print(f"⏰ Timeout: {job_id} - sending cancel request")
            await request_job_cancellation(job_id, "Timeout", tenant_key)
            break

        # Check every 30 seconds
        await asyncio.sleep(30)
```

---

## Error Handling Scenarios

### Scenario 1: Subagent Never Calls `acknowledge_job()`

**Symptom**: Job stuck in `waiting` status

**Detection**:
```python
# After 5 minutes, check if job was acknowledged
if job['status'] == 'waiting' and time_since_spawn > 5_minutes:
    print(f"⚠️ Subagent never acknowledged: {job_id}")
    print(f"   Possible causes:")
    print(f"   - Subagent crashed on startup")
    print(f"   - Subagent forgot to call acknowledge_job()")
    print(f"   - Credentials incorrect")
```

**Solution**:
1. Check subagent logs for errors
2. Verify credentials were passed correctly
3. Manually mark job as failed
4. Respawn with correct configuration

---

### Scenario 2: Subagent Stops Reporting Progress

**Symptom**: No `report_progress()` calls for 10+ minutes

**Detection**: Handled by 0107 passive monitoring
```python
# Backend monitor detects stale job
# Broadcasts job:stale_warning event
# UI shows "No update for 12m" warning
```

**Orchestrator Action**:
```python
# Receive stale warning from backend
if stale_warning_received(job_id):
    # Send nudge message
    await send_message(
        to_agent=job['agent_id'],
        message={
            "type": "status_check",
            "text": "Haven't heard from you in 10+ minutes. Are you still working?"
        },
        priority="high",
        tenant_key=tenant_key
    )

    # Wait 5 more minutes
    await asyncio.sleep(300)

    # Still no response? Request cancellation
    if still_stale(job_id):
        await request_job_cancellation(job_id, "Unresponsive", tenant_key)
```

---

### Scenario 3: Claude Code Task Tool Fails

**Symptom**: Exception when calling Task tool

**Error Example**:
```python
anthropic.APIError: Task tool not available in this context
```

**Solution**:
1. **Check Claude Code version**: Task tool requires Claude Code >= 1.5.0
2. **Verify MCP registry**: Ensure GiljoAI MCP server is connected
3. **Fallback**: Prompt user to spawn manually (multi-terminal mode)

```python
try:
    # Try Claude Code subagent spawn
    spawn_claude_subagent(instructions)
except Exception as e:
    print(f"❌ Claude Code spawn failed: {e}")
    print(f"")
    print(f"📋 MANUAL SPAWN REQUIRED:")
    print(f"")
    print(f"1. Open new terminal")
    print(f"2. Activate same product/project")
    print(f"3. Copy this prompt:")
    print(f"")
    print(instructions)
    print(f"")
    print(f"Agent will appear in dashboard once acknowledged.")
```

---

### Scenario 4: Subagent Uses Wrong Credentials

**Symptom**: MCP tool calls fail with "Access denied" or "Job not found"

**Detection**:
```python
# Subagent reports error
report_error(
    job_id="{wrong_job_id}",
    error="Job not found",
    tenant_key="{tenant_key}"
)
# Returns: {"success": False, "error": "Job {wrong_job_id} not found"}
```

**Solution**:
1. Verify orchestrator passed correct `job_id`, `agent_id`, `tenant_key`
2. Check for typos in credential injection
3. Respawn with corrected credentials

---

## Testing Checklist

### Pre-Flight Checks

- [ ] GiljoAI MCP server running
- [ ] Claude Code connected to MCP server
- [ ] Project activated (product + project set)
- [ ] Agent templates exported (8 active types)
- [ ] Orchestrator spawned in Claude Code

---

### Test 1: Basic Subagent Spawn

**Steps**:
1. Orchestrator calls `spawn_agent_job(agent_type="implementer", ...)`
2. Orchestrator spawns Claude subagent with credentials
3. Verify subagent calls `acknowledge_job()` within 1 minute
4. Verify agent card appears in dashboard

**Expected**:
- ✅ Agent card shows "Active" status
- ✅ Agent ID matches backend record
- ✅ No errors in logs

---

### Test 2: Progress Reporting

**Steps**:
1. Subagent completes first todo
2. Subagent calls `report_progress()`
3. Verify dashboard shows updated progress

**Expected**:
- ✅ Health indicator updates "Last update: 30s ago"
- ✅ Progress bar reflects percentage
- ✅ WebSocket event received in UI

---

### Test 3: Message Reception

**Steps**:
1. User clicks "Cancel Job" in dashboard
2. Backend sends cancel message
3. Subagent checks `receive_messages()` on next check-in
4. Subagent stops work and calls `complete_job()`

**Expected**:
- ✅ Subagent stops within 5 minutes
- ✅ Job status changes to "complete" with "cancelled" result
- ✅ Agent card shows completion

---

### Test 4: Error Handling

**Steps**:
1. Subagent encounters blocker
2. Subagent calls `report_error()`
3. Job status changes to "blocked"
4. Orchestrator receives notification

**Expected**:
- ✅ Job marked as "blocked"
- ✅ Dashboard shows error message
- ✅ Orchestrator can send guidance or cancel

---

### Test 5: Dynamic Spawning

**Steps**:
1. Orchestrator spawns initial 3 agents
2. During execution, orchestrator realizes needs 4th agent
3. Orchestrator calls `spawn_agent_job()` for 4th agent
4. Orchestrator spawns Claude subagent
5. Verify 4th agent appears in dashboard

**Expected**:
- ✅ New agent card appears (WebSocket event)
- ✅ "Just Added" badge shown
- ✅ 4th agent operates normally

---

### Test 6: Failure Recovery

**Steps**:
1. Kill Claude Code terminal mid-execution
2. Backend detects agent stopped reporting (10 min)
3. Dashboard shows stale warning
4. User clicks "Force Stop"
5. Job marked as failed

**Expected**:
- ✅ Stale warning after 10 min
- ✅ Force Stop button appears
- ✅ Job marked as failed
- ✅ Other agents unaffected

---

## Integration with Other Handovers

### With 0106 (Template Protection)

**System Instructions** (non-editable) include:
- Subagent spawn protocol
- Credential injection format
- MCP tool usage mandate

**User Instructions** (editable) include:
- Role-specific guidance
- Code style preferences
- Custom workflows

---

### With 0107 (Monitoring & Cancellation)

**Check-In Protocol**:
- Subagents call `report_progress()` after each milestone
- Subagents call `receive_messages()` for commands
- Passive monitoring detects stale subagents
- Graceful cancellation via message queue

---

### With 0105 (Mission Workflow)

**Implementation Tab Toggle**:
- When "Using Claude Code subagents" = ON
- Only orchestrator prompt button active
- All subagent buttons grayed out (spawned automatically)

---

## Common Issues & Solutions

### Issue: "Task tool not available"

**Cause**: Claude Code version too old or MCP not connected

**Solution**:
```bash
# Check Claude Code version
claude-code --version
# Should be >= 1.5.0

# Verify MCP connection
claude-code mcp list
# Should show "giljo-mcp" as connected
```

---

### Issue: Subagent never acknowledges

**Cause**: Credentials not passed correctly

**Solution**:
- Check credential injection in instructions string
- Verify `{agent_id}`, `{job_id}`, `{tenant_key}` replaced with actual values
- Check for template string formatting errors

---

### Issue: Multiple subagents with same Agent ID

**Cause**: Orchestrator reused same credentials for multiple spawns

**Solution**:
- Call `spawn_agent_job()` for EACH subagent
- Extract unique credentials for EACH spawn
- Never hardcode Agent IDs

---

### Issue: Subagent can't access project files

**Cause**: Claude Code subagents share same working directory

**Solution**:
- ✅ This is expected behavior
- ✅ All subagents have access to same codebase
- ✅ Coordinate via messages to avoid conflicts

---

## Quick Reference

### Orchestrator Spawn Template

```python
# 1. Register with backend
result = spawn_agent_job(
    agent_type="<type>",
    agent_name="<descriptive-name>",
    mission="<what-agent-will-do>",
    project_id="{project_id}",
    tenant_key="{tenant_key}"
)

# 2. Check success
if not result['success']:
    handle_error(result['error'])
    return

# 3. Extract credentials
agent_id = result['agent_id']
job_id = result['job_id']

# 4. Build instructions
instructions = f"""
Agent ID: {agent_id}
Job ID: {job_id}
Tenant Key: {tenant_key}

MISSION: {mission}

CHECK-IN: After each milestone, call:
- report_progress(job_id="{job_id}", agent_id="{agent_id}", ...)
- receive_messages(agent_id="{agent_id}", ...)
"""

# 5. Spawn Claude subagent
spawn_task(name="<agent-name>", instructions=instructions)

# 6. Monitor
monitor_subagent(job_id, timeout_minutes=30)
```

---

## Success Criteria

### Definition of Done

- [ ] All code examples tested with actual Claude Code
- [ ] Error handling scenarios documented
- [ ] Testing checklist validated
- [ ] Common issues cataloged with solutions
- [ ] Integration with 0106/0107/0105 verified

---

## Notes

**Version**: 1.0 (Initial Implementation Guide)
**Last Updated**: 2025-11-05
**Author**: System Architect
**Status**: Ready for testing

**Next Steps**:
1. Test all scenarios with Claude Code
2. Document any additional edge cases discovered
3. Update template instructions in 0106 based on learnings
