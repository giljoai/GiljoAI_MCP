# Session Memory: Agent Model Cleanup - Server Startup Failure Diagnostics

**Date**: 2025-11-07
**Session Focus**: Production server startup failures after Agent table drop (Handover 0116/0113)
**Status**: In Progress - 6 files identified needing Agent → MCPAgentJob migration
**Context**: This is the final cleanup phase after successful database migrations

## Executive Summary

After successfully completing database migrations for Handover 0116 (Agent model elimination) and 0113 (7-state system), the server fails to start due to **orphaned Agent model imports** in production code. The agents table was successfully dropped, but 6 production files still import and use the Agent class, causing `ImportError` on startup.

**Root Cause**: The migration focused on database schema and test files, but marked production file cleanup as "optional". With the agents table now dropped, these imports are breaking production startup.

## What We Completed (100% Done)

### Database Migrations ✅
All 4 database migrations executed successfully:
1. `0113b_decom_at` - Added decommissioned_at field to mcp_agent_jobs
2. `0116_remove_fk` - Removed all FK constraints from agents.id (6 tables)
3. `0116b_drop_agents` - Dropped agents table, created agents_backup_final
4. MCPAgentJob confirmed as single source of truth

See: `F:\GiljoAI_MCP\handovers\MIGRATION_0116_0113_FINAL_REPORT.md`

### Circular Import Fix ✅
Fixed production crash in `api/endpoints/system_prompts.py`:
- Module-level import causing circular dependency
- Applied lazy import pattern (3 functions)
- Server startup unblocked
- Commit: TBD

## Current Problem: Agent Model Imports

### Error Chain
```
ImportError: cannot import name 'Agent' from 'giljo_mcp.models'
```

**Trace**:
1. `api/app.py:62` imports ToolAccessor
2. `tools/tool_accessor.py:16` imports Agent from models
3. Agent class removed from models.py (line 558-603)
4. Import fails, server crashes

### Files Still Importing Agent (Production Code)

**Critical - Blocking Startup**:
1. `src/giljo_mcp/tools/tool_accessor.py` - Line 16, heavy usage (HIGH complexity)
2. `src/giljo_mcp/orchestrator.py` - Line 23, 42 references (HIGH complexity)
3. `src/giljo_mcp/message_queue.py` - Line 19, 3 references (MEDIUM complexity)

**Deprecated - Can Disable**:
4. `api/endpoints/agents.py` - Legacy endpoint, superseded by agent_jobs.py
5. `api/app.py` - Line 76 import (now commented out)

### Files Already Fixed This Session

1. **src/giljo_mcp/models.py** ✅
   - Removed Agent class (lines 558-603)
   - Removed agents relationship from Project model (line 525)

2. **api/app.py** ✅
   - Commented out agents endpoint import (line 76)
   - Commented out agents router registration (line 737)
   - Commented out agents tag in OpenAPI (line 581)

3. **api/endpoints/system_prompts.py** ✅
   - Fixed circular import (lazy imports added)

4. **src/giljo_mcp/message_queue.py** ✅
   - Changed import: Agent → MCPAgentJob (line 19)
   - Updated type hints: `list[Agent]` → `list[MCPAgentJob]`
   - Updated field access: `.name` → `.agent_name`

5. **src/giljo_mcp/orchestrator.py** ✅ (Partial)
   - Changed import: Agent → MCPAgentJob (line 23)
   - Replaced return types: `-> Agent:` → `-> MCPAgentJob:`
   - Replaced constructors: `Agent()` → `MCPAgentJob()`
   - Replaced queries: `select(Agent)` → `select(MCPAgentJob)`
   - Fixed field access: `.name` → `.agent_name`
   - **Status**: Compile-time fixes done, runtime untested

6. **src/giljo_mcp/tools/tool_accessor.py** 🚧 (Started)
   - Changed import: Agent → MCPAgentJob (line 16)
   - **Status**: Import changed, but 20+ usages not yet migrated

## Migration Complexity Analysis

### High Complexity Files

**tool_accessor.py** (1,977 lines):
- 20+ references to Agent model
- Lazy imports in 3 locations (lines 1837, 1921, 1962)
- Legacy agent sync code (can be removed)
- Line 231: `select(Agent).where(Agent.project_id == project.id)`
- Line 521-522: `update(Agent).where(Agent.name == agent_name)`
- Line 842: Agent query in project status
- **Approach**: Replace Agent with MCPAgentJob, comment out sync blocks

**orchestrator.py** (1,400+ lines):
- 42 references to Agent (comments + code)
- Two agent creation paths:
  - `spawn_claude_agent()` - Creates Agent with mode='claude'
  - `spawn_cli_agent()` - Creates Agent linked to MCPAgentJob
- Multiple queries using Agent.id, Agent.project_id
- **Status**: Type system fixed, needs runtime testing
- **Risk**: Core orchestration file, heavy agent manipulation

### Medium Complexity Files

**message_queue.py** (465 lines):
- 3 references to Agent
- Type hints: `available_agents: list[Agent]`
- Field access: `agent.name` → `agent.agent_name`
- **Status**: ✅ Fixed this session

## Field Mapping Reference (Agent → MCPAgentJob)

Critical field name changes:
- `Agent.name` → `MCPAgentJob.agent_name`
- `Agent.role` → `MCPAgentJob.agent_type`
- `Agent.status` → `MCPAgentJob.status` (4-state → 7-state)
- `Agent.project_id` → `MCPAgentJob.project_id` ✅ Same
- `Agent.id` → `MCPAgentJob.id` ✅ Same

State mapping (4-state → 7-state):
- `idle` → `waiting`
- `active` → `working`
- `completed` → `complete`
- `failed` → `failed`
- NEW: `blocked`, `cancelled`, `decommissioned`

See: `F:\GiljoAI_MCP\handovers\PROJECT_CLOSEOUT_0116_0113.md` (lines 147-188)

## What Needs To Happen Next

### Immediate Priority (Blocking Server Startup)

1. **Complete tool_accessor.py migration**
   - Replace all Agent references with MCPAgentJob
   - Update field names (.name → .agent_name, .role → .agent_type)
   - Comment out lazy Agent sync blocks (lines 1837, 1921, 1962)
   - Test: `python -c "from api.app import app; print('OK')"`

2. **Test orchestrator.py runtime**
   - Verify MCPAgentJob constructor accepts same fields
   - Check if spawn_claude_agent() and spawn_cli_agent() still work
   - May need to update field mappings

3. **Server startup validation**
   - Run: `python startup.py --dev`
   - Check health endpoint: `curl http://localhost:7272/health`
   - Verify no Agent-related errors in logs

### Secondary Tasks (Code Quality)

4. **Update test files** (197+ files import Agent)
   - Most tests will fail due to Agent model removal
   - Update test imports: Agent → MCPAgentJob
   - Update test field access
   - Run: `pytest tests/ -v`

5. **Documentation updates**
   - Update CLAUDE.md references (Agent model → MCPAgentJob)
   - Update architecture diagrams
   - Update developer guides

6. **Final validation**
   - Full test suite: `pytest tests/`
   - API smoke tests
   - WebSocket connectivity
   - Frontend integration

## Key Reference Documents

### Migration Planning & Execution
- `F:\GiljoAI_MCP\handovers\PROJECT_CLOSEOUT_0116_0113.md` - Complete project closeout
- `F:\GiljoAI_MCP\handovers\MIGRATION_0116_0113_FINAL_REPORT.md` - 100% completion report
- `F:\GiljoAI_MCP\handovers\migration_0116_0113_log.json` - Detailed migration log

### Database Migrations
- `F:\GiljoAI_MCP\migrations\versions\20251107_0113b_add_decommissioned_at_field.py`
- `F:\GiljoAI_MCP\migrations\versions\20251107_0116_remove_agent_fk_dependencies.py`
- `F:\GiljoAI_MCP\migrations\versions\20251107_0116b_drop_agents_table.py`

### Model Definitions
- `F:\GiljoAI_MCP\src\giljo_mcp\models.py` - Agent class removed, MCPAgentJob is source of truth
- Line 558: Agent class was here (now removed)
- Line 525: agents relationship removed from Project

### Test Files Already Migrated
- `F:\GiljoAI_MCP\tests\test_orchestrator_routing.py` - 12 Agent queries replaced
- `F:\GiljoAI_MCP\api\endpoints\projects.py` - 16 Agent queries replaced

### Production Files Modified This Session
- `F:\GiljoAI_MCP\api\endpoints\system_prompts.py` - Circular import fix
- `F:\GiljoAI_MCP\api\app.py` - Deprecated agents endpoint
- `F:\GiljoAI_MCP\src\giljo_mcp\message_queue.py` - Agent → MCPAgentJob
- `F:\GiljoAI_MCP\src\giljo_mcp\orchestrator.py` - Agent → MCPAgentJob (partial)
- `F:\GiljoAI_MCP\src\giljo_mcp\tools\tool_accessor.py` - Import changed (incomplete)

## Testing Strategy

### Unit Testing
```bash
# Test individual file imports
python -c "from src.giljo_mcp.message_queue import MessageQueue; print('OK')"
python -c "from src.giljo_mcp.orchestrator import ProjectOrchestrator; print('OK')"
python -c "from src.giljo_mcp.tools.tool_accessor import ToolAccessor; print('OK')"

# Test API app
python -c "from api.app import app; print('OK')"
```

### Integration Testing
```bash
# Start server
python startup.py --dev

# Health check
curl http://localhost:7272/health

# Database connectivity
python -c "from src.giljo_mcp.models import MCPAgentJob; print(MCPAgentJob.__tablename__)"
```

### Regression Testing
```bash
# Run full test suite
pytest tests/ -v

# Run specific migration tests
pytest tests/test_agent_job_manager.py -v
pytest tests/test_orchestrator_routing.py -v
```

## Known Issues & Warnings

1. **orchestrator.py untested**: Type system fixed, but runtime behavior needs validation
2. **tool_accessor.py incomplete**: Import changed but usages not migrated
3. **Test suite impact**: 197+ test files import Agent, expect widespread failures
4. **Agent sync blocks**: Legacy sync code in tool_accessor.py can be safely removed
5. **Backward compatibility**: orchestrator.py has deprecated methods that may still be called

## Success Criteria

- [ ] Server starts without ImportError
- [ ] Health check returns 200 OK
- [ ] No Agent-related errors in startup logs
- [ ] MCPAgentJob queries work correctly
- [ ] Frontend loads without errors
- [ ] Agent job creation works via API

## Production Risk Assessment

**Risk Level**: MEDIUM (blocking startup, but fully reversible)

**Mitigation**:
- All database changes are reversible (downgrade migrations exist)
- No data loss (agents_backup_final created with 30-day retention)
- Changes are in well-tested migration path
- Fresh agent can revert models.py changes if needed

**Rollback Plan**:
1. Revert models.py (restore Agent class)
2. Revert app.py (uncomment agents endpoint)
3. Revert tool_accessor.py, orchestrator.py, message_queue.py
4. Run: `alembic downgrade -1` (restores agents table)

## Next Agent Instructions

**Goal**: Complete Agent model cleanup to restore production server startup

**Priority Tasks**:
1. Fix tool_accessor.py (HIGH - blocking startup)
2. Test orchestrator.py runtime (HIGH - core functionality)
3. Server startup validation (HIGH - production)

**Context Files to Read**:
- This file (session memory)
- `PROJECT_CLOSEOUT_0116_0113.md` (field mappings)
- `migration_0116_0113_log.json` (what was migrated)

**Commands to Run**:
```bash
# Current test (will fail)
python -c "from api.app import app; print('OK')"

# Expected error
# ImportError: cannot import name 'Agent' from 'giljo_mcp.models'
# File: src/giljo_mcp/tools/tool_accessor.py, line 16
```

**Recommended Approach**:
1. Read tool_accessor.py to understand Agent usage
2. Apply field mappings: .name → .agent_name, .role → .agent_type
3. Replace select(Agent) → select(MCPAgentJob)
4. Comment out Agent sync blocks (lines 1837, 1921, 1962)
5. Test import: `python -c "from api.app import app"`
6. If successful, start server: `python startup.py --dev`

**Testing Mindset**: Dev mode, no shortcuts. Verify each change with test imports.

---

**Session End Notes**:
- Database migrations: 100% complete ✅
- Production code cleanup: 50% complete 🚧
- Server status: Not starting (ImportError)
- Data integrity: Fully preserved ✅
- Reversibility: Complete ✅

**Estimated Remaining Work**: 2-3 hours (careful migration of tool_accessor.py + testing)
