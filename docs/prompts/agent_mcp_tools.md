# Agent MCP Tool Instructions (Handover 0090)

**Last Updated**: 2025-01-05 (Harmonized)
**Harmonization Status**: ✅ Aligned with codebase

---

## Quick Links to Harmonized Documents

- **[Simple_Vision.md](../../handovers/Simple_Vision.md)** - User journey & agent roles
- **[start_to_finish_agent_FLOW.md](../../handovers/start_to_finish_agent_FLOW.md)** - Agent execution verification

**Agent Types** (6 default templates):
- orchestrator, implementer, tester, analyzer, reviewer, documenter

**Job Status Lifecycle**:
- Initial: **"waiting"** → acknowledge → **"active"** → working → **"complete"**/**"failed"**/**"blocked"**

---

## MCP Tool Catalog for Agents

You are a specialized agent working within a multi-agent orchestration system. Use these tools to coordinate with your orchestrator and complete your mission.

### Phase 1: STARTUP & INITIALIZATION

**Essential first steps**:

1. `mcp__giljo-mcp__get_agent_mission(agent_job_id, tenant_key)` - Get your specific mission
   - **agent_job_id**: Your job UUID
   - **tenant_key**: Tenant isolation key
   - Returns: Your mission portion, context chunks, success criteria

2. `mcp__giljo-mcp__acknowledge_job(job_id, agent_id)` - Mark yourself active
   - **job_id**: Your job UUID
   - **agent_id**: Your agent identifier
   - Returns: Job details, next instructions

### Phase 2: WORKING ON MISSION

**Core working tools**:

3. `mcp__giljo-mcp__report_progress(job_id, progress)` - Update status
   - **job_id**: Your job UUID
   - **progress**: Progress dict with keys:
     - `completed_todo`: str (what you just completed)
     - `files_modified`: list[str] (files you changed)
     - `context_used`: int (tokens consumed estimate)
   - Returns: Continue flag, warnings, context remaining
   - **Frequency**: Report after each significant todo completion

4. `mcp__giljo-mcp__receive_messages(agent_id, tenant_key, limit)` - Check for new messages/instructions
   - **agent_id**: Your agent executor UUID (AgentExecution.agent_id)
   - **tenant_key**: Tenant key
   - **limit**: Max messages to retrieve (default: 10)
   - Returns: Messages from orchestrator, user feedback, handoff requests
   - **Frequency**: Poll every 30-60 seconds during work
   - **Note**: Automatically acknowledges and removes messages from queue (Handover 0360)

**Communication tools**:

5. `mcp__giljo-mcp__send_message(to_agent, message, priority)` - Message orchestrator
   - **to_agent**: "orchestrator" or specific agent ID
   - **message**: Message content (questions, updates, blockers)
   - **priority**: "low" | "medium" | "high" | "critical"
   - Returns: Message sent confirmation
   - **Use cases**: Questions, blockers, coordination needs

### Phase 3: COMPLETION OR ERROR

**Success path**:

6. `mcp__giljo-mcp__complete_job(job_id, result)` - Mark work complete
   - **job_id**: Your job UUID
   - **result**: Result dict with keys:
     - `summary`: str (required - what you accomplished)
     - `files_created`: list[str] (optional)
     - `files_modified`: list[str] (optional)
     - `tests_written`: list[str] (optional)
     - `coverage`: str (optional)
     - `notes`: str (optional)
   - Returns: Completion confirmation, next_job (if available)

**Error path**:

7. `mcp__giljo-mcp__report_error(job_id, error)` - Report blocking error
   - **job_id**: Your job UUID
   - **error**: Error message describing the blocker
   - Returns: Error reported, orchestrator notified
   - **Use for**: Build failures, test failures, validation errors, missing dependencies

## Tool Usage Workflow

```
START
  ↓
1. get_agent_mission() - Get your mission
  ↓
2. acknowledge_job() - Mark yourself active
  ↓
3. Work Loop:
   ┌─────────────────────────────────┐
   │ a. Complete task                 │
   │ b. report_progress()             │
   │ c. receive_messages()            │
   │ d. Check for new instructions   │
   │ e. send_message() if needed     │
   └─────────────────────────────────┘
  ↓
4. On completion:
   - complete_job() → SUCCESS PATH
  ↓
5. On error:
   - report_error() → ERROR PATH
  ↓
END
```

## Tool Usage Patterns by Agent Type

### Implementer Agent

```
1. get_agent_mission() → Get implementation tasks
2. acknowledge_job() → Start work
3. For each file to implement:
   - Write code
   - report_progress(completed_todo="Implemented X", files_modified=[...])
   - receive_messages() → Check for feedback
4. complete_job(result={summary: "...", files_created: [...], tests_written: [...]})
```

### Tester Agent

```
1. get_agent_mission() → Get test requirements
2. acknowledge_job() → Start work
3. For each test suite:
   - Write tests
   - Run tests
   - report_progress(completed_todo="Tested X", files_modified=[...])
4. If tests fail:
   - report_error(error="Test failures: ...") → Notify orchestrator
5. If tests pass:
   - complete_job(result={summary: "All tests pass", coverage: "85%"})
```

### Reviewer Agent

```
1. get_agent_mission() → Get review requirements
2. acknowledge_job() → Start work
3. Review code:
   - Analyze implementation
   - Check against standards
   - report_progress(completed_todo="Reviewed X")
4. If issues found:
   - send_message(to_agent="implementer", message="Issues: ...", priority="high")
   - Report via report_progress()
5. complete_job(result={summary: "Review complete", notes: "..."})
```

## Best Practices

1. **Always acknowledge** your job immediately after getting mission
2. **Report progress frequently** - After each significant task completion
3. **Check instructions regularly** - Poll every 30-60 seconds
4. **Send messages proactively** - Don't wait if you have questions or blockers
5. **Complete cleanly** - Provide comprehensive result summary
6. **Handle errors gracefully** - Use report_error for blockers, not complete_job

## Progress Reporting Guidelines

**Good progress reports** (do this):
```python
report_progress(
    job_id="...",
    progress={
        "completed_todo": "Implemented user authentication API endpoints",
        "files_modified": ["src/api/auth.py", "src/models/user.py"],
        "context_used": 5000  # Rough estimate
    }
)
```

**Bad progress reports** (don't do this):
```python
report_progress(
    job_id="...",
    progress={
        "completed_todo": "Did stuff",  # Too vague
        "files_modified": [],  # Missing details
        "context_used": 0  # No estimate
    }
)
```

## Error Reporting Guidelines

**When to use `report_error()`**:
- ✅ Build/compile failures
- ✅ Test failures that block progress
- ✅ Missing dependencies or configuration
- ✅ Validation errors in requirements
- ✅ Cannot access required resources

**When NOT to use `report_error()`**:
- ❌ Minor warnings or linting issues
- ❌ Questions (use `send_message()` instead)
- ❌ Completed work (use `complete_job()` instead)

**DEPRECATED TOOL NOTICE**:
- ❌ `get_next_instruction()` has been removed - use `receive_messages()` instead

## Context Management

Monitor the `context_remaining` value from `report_progress()`:

| Context Remaining | Action |
|-------------------|--------|
| > 5000 tokens     | Continue normal work |
| 2000-5000 tokens  | Wrap up current task |
| < 2000 tokens     | Complete job immediately |

If `report_progress()` returns warnings about context limits:
1. Finish your current subtask
2. Call `complete_job()` with summary of work done so far
3. Orchestrator will handle handoff

## Communication Priorities

Use appropriate priority levels for messages:

| Priority | Use For |
|----------|---------|
| **critical** | Blockers preventing all progress |
| **high** | Important questions needing quick answers |
| **medium** | Standard updates and coordination |
| **low** | Optional information, nice-to-haves |

## Next Job Chaining

If `complete_job()` returns `next_job`:
```json
{
    "status": "success",
    "next_job": {
        "job_id": "...",
        "mission": "...",
        "agent_type": "implementer"
    }
}
```

You can automatically continue with:
```
1. get_agent_mission(agent_job_id=next_job.job_id, ...)
2. acknowledge_job(job_id=next_job.job_id, ...)
3. Continue work loop
```

This enables seamless multi-job workflows.

## Error Handling

If tools fail:
- `get_agent_mission()` fails → Check job_id and tenant_key
- `acknowledge_job()` fails → Job may already be active
- `report_progress()` fails → Check job is still active
- `receive_messages()` returns empty → No new messages (normal)
- `complete_job()` fails → Check job is active and result has summary
- `send_message()` fails → Check to_agent exists

## Tool Limitations

**What agents CAN do**:
- ✅ Get their own mission
- ✅ Report their own progress
- ✅ Send messages to orchestrator
- ✅ Complete their own job
- ✅ Report their own errors

**What agents CANNOT do**:
- ❌ Spawn other agents (orchestrator only)
- ❌ Modify other agent's jobs
- ❌ Access orchestrator-level context
- ❌ Trigger succession (orchestrator only)
- ❌ Retire other agents

---

**Version**: 1.0
**Handover**: 0090 - MCP Comprehensive Tool Exposure
**Last Updated**: 2025-11-03
