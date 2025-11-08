# Handover Prompt: Complete Agent Model Cleanup (Post-0116/0113)

**Copy this entire prompt to a fresh agent in Claude Code**

---

## Context

I'm continuing work on **Handover 0116/0113 unified migration** - specifically the final Agent model cleanup phase. The database migrations are 100% complete and successful, but the production server won't start due to orphaned Agent model imports.

## What's Been Done

✅ **Database migrations complete** (4/4 executed successfully)
✅ **Agent table dropped** from database
✅ **agents_backup_final** created (30-day retention)
✅ **MCPAgentJob** confirmed as single source of truth
✅ **Circular import fixed** in system_prompts.py
✅ **Agent model removed** from models.py
✅ **3 files migrated**: message_queue.py, orchestrator.py (partial), app.py

## Current Problem

**Server won't start** - ImportError when importing Agent from models:

```
ImportError: cannot import name 'Agent' from 'giljo_mcp.models'
File: src/giljo_mcp/tools/tool_accessor.py, line 16
```

## What Needs To Happen

**IMMEDIATE (Blocking Production)**:

1. **Complete tool_accessor.py migration** (HIGH complexity)
   - File: `F:\GiljoAI_MCP\src\giljo_mcp\tools\tool_accessor.py`
   - Line 16: Import changed to MCPAgentJob, but 20+ usages still reference Agent
   - Need to replace all Agent references with MCPAgentJob
   - Field mappings:
     - `Agent.name` → `MCPAgentJob.agent_name`
     - `Agent.role` → `MCPAgentJob.agent_type`
     - `Agent.status` → `MCPAgentJob.status` (same field, different states)
   - Lines 1837, 1921, 1962: Legacy Agent sync blocks - can be **commented out** (agents table dropped)

2. **Test orchestrator.py runtime** (HIGH complexity)
   - File: `F:\GiljoAI_MCP\src\giljo_mcp\orchestrator.py`
   - Compile-time fixes done (imports, types), but runtime untested
   - May need additional field mapping fixes
   - Test after tool_accessor.py is fixed

3. **Validate server startup**
   - Run: `python startup.py --dev`
   - Check: `curl http://localhost:7272/health`
   - Verify no Agent errors in logs

## Key Reference Documents

**READ THESE FIRST**:

1. **Session memory**: `F:\GiljoAI_MCP\handovers\0116_0113_session_agent_model_cleanup.md`
   - Complete diagnostic of what was done this session
   - Lists all files modified
   - Field mapping reference
   - Testing strategy

2. **Project closeout**: `F:\GiljoAI_MCP\handovers\PROJECT_CLOSEOUT_0116_0113.md`
   - Lines 147-188: Field mapping (Agent → MCPAgentJob)
   - Lines 404-422: Optional cleanup instructions
   - Confirms Agent model removal is safe

3. **Migration log**: `F:\GiljoAI_MCP\handovers\migration_0116_0113_log.json`
   - Shows which files were migrated (tests mostly)
   - tool_accessor.py marked "HIGH complexity, heavy Agent usage"

## Field Mapping Quick Reference

```python
# OLD (Agent model - REMOVED)
agent.name          → MCPAgentJob.agent_name
agent.role          → MCPAgentJob.agent_type
agent.status        → MCPAgentJob.status
agent.project_id    → MCPAgentJob.project_id  # Same
agent.id            → MCPAgentJob.id           # Same

# Queries
select(Agent).where(Agent.project_id == pid)
→ select(MCPAgentJob).where(MCPAgentJob.project_id == pid)

# Constructor
Agent(name="foo", role="implementer", project_id=pid)
→ MCPAgentJob(agent_name="foo", agent_type="implementer", project_id=pid)
```

## Testing Commands

```bash
# Test current state (WILL FAIL)
python -c "from api.app import app; print('OK')"

# Expected error
# ImportError: cannot import name 'Agent' from 'giljo_mcp.models'

# After tool_accessor.py fix (SHOULD PASS)
python -c "from src.giljo_mcp.tools.tool_accessor import ToolAccessor; print('OK')"
python -c "from api.app import app; print('OK')"

# Start server (final goal)
python startup.py --dev

# Health check
curl http://localhost:7272/health
```

## Your Task

**Goal**: Fix tool_accessor.py to use MCPAgentJob instead of Agent, get server starting

**Approach**:
1. Read the session memory document (see what's been done)
2. Read tool_accessor.py to understand Agent usage patterns
3. Replace Agent references with MCPAgentJob using field mappings
4. Comment out Agent sync blocks (lines 1837, 1921, 1962) - legacy code
5. Test import: `python -c "from api.app import app"`
6. If successful, test server: `python startup.py --dev`

**Important**:
- We're in **dev mode** - no shortcuts, proper fixes only
- All database work is done - this is just Python code cleanup
- Changes are reversible - Agent class can be restored if needed
- Field mappings are critical - .name vs .agent_name matters

## Questions to Ask Me (User)

If you need clarification on:
- Whether to delete or migrate specific code blocks
- Field mapping ambiguities
- Testing approach before proceeding
- Architecture decisions

## Success Criteria

- [ ] `python -c "from api.app import app"` runs without ImportError
- [ ] Server starts with `python startup.py --dev`
- [ ] Health endpoint returns 200 OK
- [ ] No Agent-related errors in logs

## Rollback Plan (If Needed)

If migration gets too complex or breaks production:
1. Revert models.py (restore Agent class from git)
2. Revert tool_accessor.py, orchestrator.py, message_queue.py
3. Run: `alembic downgrade -1` (restores agents table)
4. Server will start with old Agent model

But we should complete the migration - we're 90% there.

---

**Start by reading**: `F:\GiljoAI_MCP\handovers\0116_0113_session_agent_model_cleanup.md`

**Then ask me**: "I've read the session memory. Should I proceed with fixing tool_accessor.py, or do you want to discuss the approach first?"
