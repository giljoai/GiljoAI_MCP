# Migration 0116 + 0113 - Implementation Checklist

**Status:** INCOMPLETE
**Last Updated:** 2025-11-07
**Target Completion:** 2025-11-08

---

## Pre-Flight Checks

- [ ] Read `F:\GiljoAI_MCP\CRITICAL_ISSUES_0116_0113.md`
- [ ] Review `F:\GiljoAI_MCP\test_validation_report_0116_0113.json`
- [ ] Backup current database: `pg_dump -U postgres giljo_mcp > backup_pre_migration.sql`
- [ ] Create git branch: `git checkout -b migration/0116-0113-completion`
- [ ] Confirm database at migration 0116_remove_fk: `alembic current`

---

## Phase 2: Code Migration (DO THIS FIRST)

### File 1: api/endpoints/agents.py (60 min) - CRITICAL
**Priority:** P0 - Blocks testing

- [ ] Open file: `F:\GiljoAI_MCP\api\endpoints\agents.py`
- [ ] Find all Agent imports (lines 106, 247, 350)
- [ ] Replace `from src.giljo_mcp.models import Agent` → `from src.giljo_mcp.models import MCPAgentJob`
- [ ] Find all `Agent` queries:
  - [ ] Replace `session.query(Agent)` → `session.query(MCPAgentJob)`
  - [ ] Replace `Agent.filter_by()` → `MCPAgentJob.filter_by()`
  - [ ] Update all variable names: `agent = ...` → `agent_job = ...` (for clarity)
- [ ] Update field references:
  - [ ] `agent.status` → `agent_job.status`
  - [ ] `agent.role` → `agent_job.role`
  - [ ] New fields: `agent_job.decommissioned_at`, `agent_job.failure_reason`
- [ ] Test: `pytest tests/api/test_agent_jobs_websocket.py --collect-only`
- [ ] Commit: `git commit -m "Migrate api/endpoints/agents.py to MCPAgentJob (Handover 0116)"`

---

### File 2: src/giljo_mcp/orchestrator.py (45 min) - CRITICAL
**Priority:** P0 - Core system

- [ ] Open file: `F:\GiljoAI_MCP\src\giljo_mcp\orchestrator.py`
- [ ] Find Agent import (line 23)
- [ ] Replace `from .models import Agent, ...` → `from .models import MCPAgentJob, ...`
- [ ] Find all Agent queries:
  - [ ] Replace `self.session.query(Agent)` → `self.session.query(MCPAgentJob)`
  - [ ] Update orchestrator methods that spawn/manage agents
- [ ] Update agent state transitions to use 7-state model:
  - [ ] Remove: preparing, active, review, cancelling
  - [ ] Use: waiting, working, complete, failed, cancelled, decommissioned
- [ ] Test: `pytest tests/unit/test_orchestrator.py -v`
- [ ] Commit: `git commit -m "Migrate orchestrator.py to MCPAgentJob (Handover 0116)"`

---

### File 3: src/giljo_mcp/tools/agent.py (45 min) - CRITICAL
**Priority:** P0 - User-facing MCP tools

- [ ] Open file: `F:\GiljoAI_MCP\src\giljo_mcp\tools\agent.py`
- [ ] Replace Agent import → MCPAgentJob
- [ ] Update `agent_spawn()` MCP tool:
  - [ ] Create MCPAgentJob instead of Agent
  - [ ] Set initial status = 'waiting' (not 'preparing')
- [ ] Update `agent_status()` MCP tool:
  - [ ] Query MCPAgentJob
  - [ ] Return 7-state status
- [ ] Update `agent_cancel()` MCP tool:
  - [ ] Set status = 'cancelled' (remove 'cancelling')
- [ ] Test: `pytest tests/unit/test_agent_status_tool.py -v`
- [ ] Commit: `git commit -m "Migrate tools/agent.py to MCPAgentJob (Handover 0116)"`

---

### File 4: src/giljo_mcp/message_queue.py (30 min) - HIGH
**Priority:** P1 - Inter-agent communication

- [ ] Open file: `F:\GiljoAI_MCP\src\giljo_mcp\message_queue.py`
- [ ] Replace `from .models import Agent` → `from .models import MCPAgentJob`
- [ ] Update message routing:
  - [ ] Replace `Agent.filter_by()` → `MCPAgentJob.filter_by()`
  - [ ] Update message sender/receiver lookups
- [ ] Test: `pytest tests/unit/test_agent_messaging_tools.py -v`
- [ ] Commit: `git commit -m "Migrate message_queue.py to MCPAgentJob (Handover 0116)"`

---

### File 5: src/giljo_mcp/tools/message.py (20 min) - HIGH
**Priority:** P1 - Message tools

- [ ] Open file: `F:\GiljoAI_MCP\src\giljo_mcp\tools\message.py`
- [ ] Replace Agent import → MCPAgentJob
- [ ] Update message MCP tools
- [ ] Test: `pytest tests/unit/test_agent_messaging_tools.py -v`
- [ ] Commit: `git commit -m "Migrate tools/message.py to MCPAgentJob (Handover 0116)"`

---

### File 6: src/giljo_mcp/tools/tool_accessor.py (20 min) - HIGH
**Priority:** P1 - Utility layer

- [ ] Open file: `F:\GiljoAI_MCP\src\giljo_mcp\tools\tool_accessor.py`
- [ ] Replace Agent import → MCPAgentJob
- [ ] Update all Agent references
- [ ] Test: `pytest tests/unit/ -k tool_accessor -v`
- [ ] Commit: `git commit -m "Migrate tools/tool_accessor.py to MCPAgentJob (Handover 0116)"`

---

### File 7: src/giljo_mcp/tools/project.py (15 min) - MEDIUM
**Priority:** P2 - Project management

- [ ] Open file: `F:\GiljoAI_MCP\src\giljo_mcp\tools\project.py`
- [ ] Replace Agent import → MCPAgentJob
- [ ] Update project queries that reference agents
- [ ] Test: `pytest tests/unit/test_project_tools.py -v`
- [ ] Commit: `git commit -m "Migrate tools/project.py to MCPAgentJob (Handover 0116)"`

---

### File 8: src/giljo_mcp/tools/claude_code_integration.py (15 min) - MEDIUM
**Priority:** P2 - Integration layer

- [ ] Open file: `F:\GiljoAI_MCP\src\giljo_mcp\tools\claude_code_integration.py`
- [ ] Replace Agent import → MCPAgentJob
- [ ] Update Claude Code integration
- [ ] Test: Integration test with Claude Code
- [ ] Commit: `git commit -m "Migrate tools/claude_code_integration.py to MCPAgentJob (Handover 0116)"`

---

### Phase 2 Verification

- [ ] No files import Agent (except AgentTemplate, AgentInteraction, AgentRole):
  ```bash
  grep -r "from.*models.*import.*Agent[^T]" src/ api/ --include="*.py" | grep -v MCPAgentJob
  # Should return 0 results
  ```
- [ ] Test collection succeeds:
  ```bash
  pytest tests/ --collect-only
  # Should collect 1653 tests with 0 errors
  ```
- [ ] Unit tests pass:
  ```bash
  pytest tests/unit/ -v
  # All tests should pass
  ```

---

## Phase 1: Database Migration (30 min) - DO THIS AFTER PHASE 2

### Create Migration File

- [ ] Create migration:
  ```bash
  alembic revision -m "Drop agents table (Handover 0116 final)"
  ```
- [ ] Edit migration file: `migrations/versions/[timestamp]_drop_agents.py`
- [ ] Add upgrade code:
  ```python
  def upgrade():
      print("=" * 80)
      print("HANDOVER 0116: Dropping agents table")
      print("=" * 80)

      op.execute("DROP TABLE IF EXISTS agents CASCADE")

      print("agents table dropped successfully")
      print("=" * 80)
  ```
- [ ] Add downgrade code:
  ```python
  def downgrade():
      raise RuntimeError(
          "Cannot downgrade: agents table drop is irreversible. "
          "Restore from backup if needed."
      )
  ```

### Run Migration

- [ ] Verify current migration: `alembic current` (should be 0116_remove_fk)
- [ ] Run migration: `alembic upgrade head`
- [ ] Verify agents table gone:
  ```bash
  PGPASSWORD=$DB_PASSWORD psql -U postgres -d giljo_mcp -c "SELECT table_name FROM information_schema.tables WHERE table_name = 'agents';"
  # Should return 0 rows
  ```
- [ ] Commit:
  ```bash
  git add migrations/
  git commit -m "Add migration to drop agents table (Handover 0116)"
  ```

---

## Phase 3: Validation (1 hour)

### Full Test Suite

- [ ] Run all tests:
  ```bash
  pytest tests/ -v --tb=short
  ```
- [ ] Verify results:
  - [ ] Total tests: 1653
  - [ ] Passed: 1653
  - [ ] Failed: 0
  - [ ] Errors: 0
  - [ ] Coverage: ≥ 80%

### API Endpoint Testing

- [ ] Start server: `python startup.py --dev`
- [ ] Test system stats:
  ```bash
  curl http://localhost:7272/api/statistics/system
  ```
  - [ ] Response: 200 OK
  - [ ] No "agents" key in JSON (only "mcp_agent_jobs")
  - [ ] No Agent model references

- [ ] Test agent jobs:
  ```bash
  curl http://localhost:7272/api/agent-jobs
  ```
  - [ ] Response: 200 OK
  - [ ] Returns list of MCPAgentJob objects
  - [ ] Fields include: decommissioned_at, failure_reason

- [ ] Test projects:
  ```bash
  curl http://localhost:7272/api/projects
  ```
  - [ ] Response: 200 OK
  - [ ] No errors

### WebSocket Testing

- [ ] Connect WebSocket client
- [ ] Create agent job (should emit: agent:waiting)
- [ ] Acknowledge job (should emit: agent:working)
- [ ] Complete job (should emit: agent:complete)
- [ ] Fail job with reason (should emit: agent:failed + failure_reason)
- [ ] Cancel job (should emit: agent:cancelled)
- [ ] Decommission job (should emit: agent:decommissioned + decommissioned_at)
- [ ] Verify removed events DON'T fire:
  - [ ] agent:preparing (removed)
  - [ ] agent:active (removed)
  - [ ] agent:review (removed)
  - [ ] agent:cancelling (removed)

### 7-State Transition Testing

- [ ] Test valid transitions:
  - [ ] waiting → working ✓
  - [ ] working → complete ✓
  - [ ] complete → working ✓ (continue working)
  - [ ] complete → decommissioned ✓ (close out)
  - [ ] working → failed ✓ (with failure_reason)
  - [ ] working → cancelled ✓

- [ ] Test invalid transitions raise errors:
  - [ ] waiting → complete ✗ (must acknowledge first)
  - [ ] decommissioned → working ✗ (terminal state)
  - [ ] failed → working ✗ (terminal state)

---

## Phase 4: Production Readiness (1 hour)

### Performance Testing

- [ ] Benchmark queries:
  ```sql
  EXPLAIN ANALYZE SELECT * FROM mcp_agent_jobs WHERE status = 'working';
  EXPLAIN ANALYZE SELECT * FROM mcp_agent_jobs WHERE tenant_key = 'test';
  ```
- [ ] Verify query times < 10ms
- [ ] No performance regressions vs. baseline

### Documentation

- [ ] Update CLAUDE.md:
  - [ ] Remove all Agent model references
  - [ ] Document MCPAgentJob as the only agent model
  - [ ] Update 7-state model documentation
  - [ ] Add decommissioned_at and failure_reason fields

- [ ] Update handover docs:
  - [ ] Mark Handover 0116 as COMPLETE
  - [ ] Mark Handover 0113 as COMPLETE
  - [ ] Document lessons learned

- [ ] Update developer guides:
  - [ ] Agent lifecycle now uses 7 states
  - [ ] How to query MCPAgentJob
  - [ ] How to handle decommissioned agents

### Code Quality

- [ ] Run linters:
  ```bash
  ruff src/ api/
  black --check src/ api/
  ```
- [ ] Fix any linting errors
- [ ] Commit: `git commit -m "Fix linting errors (Handover 0116)"`

### Final Verification

- [ ] Drop and recreate database:
  ```bash
  PGPASSWORD=$DB_PASSWORD psql -U postgres -c "DROP DATABASE giljo_mcp"
  PGPASSWORD=$DB_PASSWORD psql -U postgres -c "CREATE DATABASE giljo_mcp"
  python install.py
  ```
- [ ] Run fresh database test:
  ```bash
  pytest tests/ -v
  ```
- [ ] All tests pass with fresh database
- [ ] No agents table exists in fresh database

---

## Success Criteria

### Code Migration ✓

- [ ] All 8 files migrated to MCPAgentJob
- [ ] Zero imports of deprecated Agent model:
  ```bash
  grep -r "from.*models.*import.*Agent[^T]" src/ api/ --include="*.py" | grep -v MCPAgentJob | wc -l
  # Should return 0
  ```

### Database Migration ✓

- [ ] agents table dropped:
  ```sql
  SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'agents';
  -- Should return 0
  ```
- [ ] Only mcp_agent_jobs exists:
  ```sql
  SELECT table_name FROM information_schema.tables
  WHERE table_name IN ('agents', 'mcp_agent_jobs');
  -- Should return only: mcp_agent_jobs
  ```

### Testing ✓

- [ ] All 1653 tests pass
- [ ] Test coverage ≥ 80%
- [ ] Zero collection errors
- [ ] API endpoints respond correctly
- [ ] WebSocket events fire correctly

### Production ✓

- [ ] No circular imports
- [ ] No runtime errors
- [ ] No performance regressions
- [ ] Documentation updated
- [ ] Code quality checks pass

---

## Deployment

- [ ] Merge to master:
  ```bash
  git checkout master
  git merge migration/0116-0113-completion
  git push origin master
  ```
- [ ] Tag release:
  ```bash
  git tag -a v3.1.1-migration-0116-0113 -m "Complete Agent→MCPAgentJob migration"
  git push origin v3.1.1-migration-0116-0113
  ```
- [ ] Deploy to production
- [ ] Monitor logs for 24 hours
- [ ] Verify no Agent-related errors

---

## Rollback Plan

If critical issues discovered in production:

1. **Rollback code:**
   ```bash
   git revert HEAD~8..HEAD
   git push origin master
   ```

2. **Restore database from backup:**
   ```bash
   PGPASSWORD=$DB_PASSWORD psql -U postgres -c "DROP DATABASE giljo_mcp"
   PGPASSWORD=$DB_PASSWORD psql -U postgres -c "CREATE DATABASE giljo_mcp"
   psql -U postgres giljo_mcp < backup_pre_migration.sql
   ```

3. **Restart server:**
   ```bash
   python startup.py
   ```

**Note:** Rollback is only safe if done within 24 hours and no new production data created.

---

## Completion Checklist

- [ ] All 8 files migrated
- [ ] agents table dropped
- [ ] All 1653 tests pass
- [ ] Coverage ≥ 80%
- [ ] API validated
- [ ] WebSocket validated
- [ ] Performance validated
- [ ] Documentation updated
- [ ] Code quality pass
- [ ] Deployed to production
- [ ] 24-hour monitoring complete
- [ ] Handover document created

---

**Status:** IN PROGRESS
**Next Action:** Start with api/endpoints/agents.py (File 1)
**Estimated Completion:** 2025-11-08
**Checklist Progress:** 0 / 135 tasks (0%)
