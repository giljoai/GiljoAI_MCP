---
**Handover ID:** 0116
**Title:** Agent Model Migration & Cleanup - Eliminate Legacy Dual-Model Code
**Date:** 2025-01-07
**Status:** Planning
**Priority:** Critical
**Complexity:** High
**Estimated Effort:** 2-3 weeks
**Related Handovers:**
- 0113 (Unified Agent State System)
- 0114 (Jobs Tab UI Harmonization)
- 0115 (Legacy Agent Model Deprecation Strategy)
**Dependencies:**
- Handover 0113 must be implemented first (7-state system)
---

# Handover 0116: Agent Model Migration & Cleanup

## Executive Summary

### Problem

The GiljoAI MCP codebase currently has a critical architectural issue:

- **Legacy Agent model** (4 states: active, idle, working, decommissioned) still used in **197 files**
- **9 files use BOTH Agent + MCPAgentJob** creating dual-model confusion and synchronization complexity
- **Unclear which functions are still actively used** vs legacy dead code
- **Risk of data inconsistencies** when dual-model code gets out of sync

### Solution - Two-Part Approach

**Part A: Migrate Overlap Files (Priority: HIGH)**
- **Target:** 9 files using BOTH models
- **Goal:** Migrate to use ONLY MCPAgentJob
- **Why First:** These cause immediate confusion and highest risk of data inconsistency
- **Timeline:** Week 1

**Part B: Audit & Cleanup Legacy Functions (Priority: MEDIUM)**
- **Target:** 197 files using ONLY Agent model
- **Goal:** Identify which functions are still used
  - **If USED:** Refactor to use MCPAgentJob
  - **If UNUSED:** DELETE the function/file
- **Why Second:** Clean up after Part A, remove dead code
- **Timeline:** Weeks 2-3

### Success Metrics

**Part A Complete:**
- Zero files import both Agent and MCPAgentJob
- All overlap files use ONLY MCPAgentJob
- All tests pass

**Part B Complete:**
- Zero production files import Agent model
- All used functions refactored to MCPAgentJob
- All unused code deleted
- Agent table marked for deprecation

---

## Part A: Overlap Files Migration

### Critical Overlap Files (9 files)

#### Production Code (6 files)

##### 1. `src/giljo_mcp/tools/tool_accessor.py`
- **Purpose:** MCP tool accessor for orchestration
- **Agent usage:** TBD (needs user analysis)
- **MCPAgentJob usage:** TBD (needs user analysis)
- **Migration approach:** TBD (user review required)
- **Estimated effort:** TBD

##### 2. `api/endpoints/projects.py`
- **Purpose:** Project management API
- **Agent usage:** Queries Agent table for agent_count
- **MCPAgentJob usage:** Queries MCPAgentJob for modern agents
- **Migration approach:** Remove Agent queries, use only MCPAgentJob count
- **Estimated effort:** 1 hour

##### 3. `src/giljo_mcp/tools/orchestration.py`
- **Purpose:** Project orchestration tools
- **Agent usage:** TBD (needs user analysis)
- **MCPAgentJob usage:** TBD (needs user analysis)
- **Migration approach:** TBD (user review required)
- **Estimated effort:** TBD

##### 4. `api/endpoints/statistics.py`
- **Purpose:** System statistics API
- **Agent usage:** Counts active agents via Agent.status
- **MCPAgentJob usage:** TBD
- **Migration approach:** Use MCPAgentJob.status.in_(['working', 'waiting'])
- **Estimated effort:** 30 minutes

##### 5-6. Remaining Production Files
- Files will be analyzed one-by-one with user review
- Approach determined based on usage patterns
- Migration effort estimated after review

#### Test Files (3 files - Lower Priority)
- `tests/integration/test_mcp_get_orchestrator_instructions.py`
- `tests/test_orchestrator_routing.py`
- Additional test/doc files (refactor after production code)

### Migration Checklist Template

For each overlap file, use this checklist:

```markdown
### File: {filename}

**Current State:**
- Lines using Agent: [line numbers]
- Lines using MCPAgentJob: [line numbers]
- Purpose of Agent usage: [description]
- Purpose of MCPAgentJob usage: [description]

**User Decision Required:**
- [ ] Is this function still used in the application? (YES/NO/UNSURE)

**If YES, migration plan:**
1. Replace `select(Agent)` with `select(MCPAgentJob)`
2. Map Agent.status (4 states) to MCPAgentJob.status (7 states)
3. Update field mappings:
   - `Agent.name` → `MCPAgentJob.agent_name`
   - `Agent.role` → `MCPAgentJob.agent_type`
   - `Agent.status` → `MCPAgentJob.status`
   - `Agent.mission` → `MCPAgentJob.mission`
4. Update imports (remove Agent, keep MCPAgentJob)
5. Test the migration

**If NO, deletion plan:**
- [ ] Remove Agent imports
- [ ] Remove MCPAgentJob imports (if also unused)
- [ ] Delete function/section
- [ ] Remove from router/caller
- [ ] Remove tests
- [ ] Verify no dependencies

**Testing:**
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed
- [ ] No regressions observed
```

---

## Part B: Legacy Agent Function Audit

### Files Using ONLY Agent Model (197 files)

#### Key API Endpoints
- `api/endpoints/agents.py` - **ALREADY REVIEWED** (DELETE + migrate frontend)
- `api/endpoints/agent_templates.py`
- `api/endpoints/claude_export.py`
- `api/endpoints/downloads.py`
- `api/endpoints/orchestration.py`
- `api/endpoints/prompts.py`
- `api/endpoints/templates.py`

#### Key Source Files
- `src/giljo_mcp/agent_selector.py`
- `src/giljo_mcp/agent_job_manager.py`
- `src/giljo_mcp/orchestrator.py`
- And ~180 more files...

### Audit Process - User Review (One-by-One)

For each file, user will be asked:

```
File: {filename}
Function: {function_name}

What does it do: {brief description}

Question: Is this function still used in the application?

A) YES - Used actively
B) NO - Legacy dead code
C) UNSURE - Need to search for callers

Your answer (A/B/C)?
```

### Decision Matrix

```
IF Answer = A (Used):
  → Next Question: "Does MCPAgentJob have equivalent functionality?"
     - If YES: REFACTOR to use MCPAgentJob
     - If NO: ADD to MCPAgentJob, then refactor

IF Answer = B (Unused):
  → Action: DELETE
  → Confirm: Show file size, lines, ask "Confirm deletion?"

IF Answer = C (Unsure):
  → Action: Search for callers, report findings, ask again
```

### File Inventory Table

This table will be populated during review:

| # | File | Function | Used? | Action | Effort | Status |
|---|------|----------|-------|--------|--------|--------|
| 1 | api/endpoints/agents.py | list_agents() | YES | REFACTOR frontend | Medium | ✅ Reviewed |
| 2 | api/endpoints/agents.py | create_agent() | YES | REFACTOR | Medium | ✅ Reviewed |
| 3 | api/endpoints/agents.py | get_agent() | YES | REFACTOR | Medium | ✅ Reviewed |
| 4 | api/endpoints/agents.py | update_agent() | YES | REFACTOR | Medium | ✅ Reviewed |
| 5 | api/endpoints/agents.py | delete_agent() | YES | REFACTOR | Medium | ✅ Reviewed |
| ... | ... | ... | ... | ... | ... | ... |

---

## Migration Strategy

### Phase 1: Part A - Overlap Files (Week 1)

**Goal:** Eliminate all dual-model files

**Method:** User reviews each of 9 files one-by-one

**Deliverable:** 9 files use ONLY MCPAgentJob

**Timeline:**
- **Day 1-2:** User review of all 9 overlap files (document decisions)
- **Day 3-4:** Execute migrations based on user decisions
- **Day 5:** Test all migrations, fix regressions

**Daily Breakdown:**

**Day 1:**
- Review files 1-3 (tool_accessor.py, projects.py, orchestration.py)
- Document current usage patterns
- Get user decisions
- Create migration plans

**Day 2:**
- Review files 4-6 (statistics.py, prompts.py, templates.py)
- Document current usage patterns
- Get user decisions
- Create migration plans

**Day 3:**
- Execute migrations for files 1-3
- Run tests after each migration
- Fix any issues

**Day 4:**
- Execute migrations for files 4-6
- Run tests after each migration
- Fix any issues

**Day 5:**
- Integration testing
- Performance validation
- Regression testing
- Documentation updates

### Phase 2: Part B - High-Priority Legacy (Week 2)

**Goal:** Clean up actively-used API endpoints

**Method:** User reviews high-traffic files first

**Timeline:**
- **Day 1:** `api/endpoints/agents.py` migration (already reviewed - execute)
- **Day 2:** Review `api/endpoints/orchestration.py`, `prompts.py`, `templates.py`
- **Day 3-4:** Execute migrations for reviewed files
- **Day 5:** Testing and validation

**Daily Breakdown:**

**Day 1:**
- Migrate `api/endpoints/agents.py` to use MCPAgentJob
- Update frontend to call new endpoints
- Test agent CRUD operations
- Verify no regressions

**Day 2:**
- Review `orchestration.py` (identify used functions)
- Review `prompts.py` (identify used functions)
- Review `templates.py` (identify used functions)
- Document migration plans

**Day 3-4:**
- Execute migrations for reviewed endpoints
- Update tests
- Run integration tests
- Fix issues

**Day 5:**
- Full system testing
- Performance benchmarks
- UI validation
- Documentation

### Phase 3: Part B - Bulk Legacy Cleanup (Week 3)

**Goal:** Delete confirmed dead code

**Method:** Batch analysis of low-priority files

**Timeline:**
- **Day 1-2:** Analyze scripts, installers, migration files (likely safe to delete)
- **Day 3:** User reviews deletion candidates
- **Day 4:** Execute deletions
- **Day 5:** Final validation, update documentation

**Daily Breakdown:**

**Day 1:**
- Analyze all scripts/ files
- Search for callers
- Categorize as USED/UNUSED/UNSURE
- Prepare batch for user review

**Day 2:**
- Analyze installer files
- Analyze migration scripts
- Search for callers
- Prepare batch for user review

**Day 3:**
- Present findings to user
- Get deletion approvals
- Document decisions
- Create deletion plan

**Day 4:**
- Execute deletions (git tracked, reversible)
- Update imports in remaining files
- Remove from tests
- Clean up documentation

**Day 5:**
- Final integration testing
- Full test suite run
- Performance validation
- Update handover with final metrics
- Create migration summary report

---

## Code Migration Patterns

### Pattern 1: Simple Query Replacement

```python
# BEFORE (Agent)
stmt = select(Agent).where(Agent.project_id == project_id)
agents = session.execute(stmt).scalars().all()

# AFTER (MCPAgentJob)
stmt = select(MCPAgentJob).where(MCPAgentJob.project_id == project_id)
agent_jobs = session.execute(stmt).scalars().all()
```

### Pattern 2: Status Mapping (4 states → 7 states)

```python
# BEFORE (Agent - 4 states)
active_agents = session.query(Agent).filter(Agent.status == 'active').all()

# AFTER (MCPAgentJob - 7 states)
active_jobs = session.query(MCPAgentJob).filter(
    MCPAgentJob.status.in_(['waiting', 'working'])
).all()
```

**Status Mapping Table:**

| Agent.status (OLD) | MCPAgentJob.status (NEW) | Notes |
|--------------------|--------------------------|-------|
| active | waiting, working | Map based on context: idle = waiting, busy = working |
| idle | waiting | Waiting for work assignment |
| working | working | Direct mapping, actively processing |
| decommissioned | decommissioned | Direct mapping (Handover 0113) |

### Pattern 3: Field Mapping

```python
# BEFORE (Agent)
return {
    "name": agent.name,
    "role": agent.role,
    "status": agent.status,
    "mission": agent.mission,
    "context_used": agent.context_used
}

# AFTER (MCPAgentJob)
return {
    "name": agent_job.agent_name,
    "role": agent_job.agent_type,
    "status": agent_job.status,
    "mission": agent_job.mission,
    "context_used": agent_job.job_metadata.get('context_used', 0)
}
```

**Field Mapping Table:**

| Agent (OLD) | MCPAgentJob (NEW) | Type | Notes |
|-------------|-------------------|------|-------|
| name | agent_name | String | Direct mapping |
| role | agent_type | String | Direct mapping |
| status | status | String | 4 states → 7 states (see mapping table) |
| mission | mission | Text | Direct mapping |
| context_used | job_metadata['context_used'] | Integer | Stored in JSONB field |
| last_active | started_at | DateTime | Map to job start time |
| mode | tool_type | String | Direct mapping (claude-code, codex, gemini) |
| job_id | job_id | String | Primary unique identifier |
| project_id | project_id | UUID | Foreign key mapping |
| tenant_key | tenant_key | String | Multi-tenant isolation |

### Pattern 4: Count/Aggregation Queries

```python
# BEFORE (Agent)
agent_count = session.query(Agent).filter(
    Agent.project_id == project_id,
    Agent.status == 'active'
).count()

# AFTER (MCPAgentJob)
agent_count = session.query(MCPAgentJob).filter(
    MCPAgentJob.project_id == project_id,
    MCPAgentJob.status.in_(['waiting', 'working'])
).count()
```

### Pattern 5: Join Operations

```python
# BEFORE (Agent)
from models import Agent, Project

results = session.query(Project, Agent).join(
    Agent, Project.id == Agent.project_id
).filter(Agent.status == 'active').all()

# AFTER (MCPAgentJob)
from models import Project, MCPAgentJob

results = session.query(Project, MCPAgentJob).join(
    MCPAgentJob, Project.id == MCPAgentJob.project_id
).filter(MCPAgentJob.status.in_(['waiting', 'working'])).all()
```

---

## User Review Process (Interactive)

### Part A Review Format (Overlap Files)

One file at a time:

```
========================================
PART A: Overlap File Review #1 of 9
========================================

File: src/giljo_mcp/tools/tool_accessor.py

Current imports:
- from models import Agent (line 23)
- from models import MCPAgentJob (line 24)

Functions using Agent:
- ensure_agent() (line 145-167)
  Purpose: Ensures agent exists before tool access

- get_agent_status() (line 201-215)
  Purpose: Retrieves current agent status

Functions using MCPAgentJob:
- acknowledge_job() (line 301-320)
  Purpose: Marks job as acknowledged

- complete_job() (line 355-375)
  Purpose: Marks job as completed

Question: Are the Agent-using functions still called in the application?

A) YES - They are actively used
B) NO - Legacy dead code
C) UNSURE - Need to search for callers

Your answer (A/B/C)?

[If A] Follow-up: Should we migrate them to use MCPAgentJob instead?
[If B] Follow-up: Confirm deletion of ensure_agent() and get_agent_status()?
[If C] Agent will search codebase for callers and report findings
```

### Part B Review Format (Legacy Files)

Batch review for similar files:

```
========================================
PART B: Legacy File Batch #1 (Scripts)
========================================

Files for review:
1. scripts/init_templates.py - Uses Agent for template initialization
   Line 45: agent = Agent(name="template_init", role="initializer")

2. scripts/migrate_templates.py - Uses Agent for migration tracking
   Line 78: agents = session.query(Agent).all()

3. scripts/seed_orchestrator_template.py - Uses Agent for seeding
   Line 112: orchestrator = Agent(name="orchestrator", role="orchestrator")

Analysis:
- These appear to be one-time setup scripts
- Last modified: 2024-06-15 (7 months ago)
- No callers found in current codebase

Question: Are these scripts still used, or can they be deleted?

A) KEEP - Still needed for installations
B) DELETE - One-time scripts, no longer needed
C) REVIEW ONE-BY-ONE - Need individual analysis

Your answer (A/B/C)?

[If A] We'll update them to use MCPAgentJob
[If B] We'll delete all 3 scripts
[If C] We'll review each script individually
```

---

## Risk Assessment

### High Risk (Immediate Impact)

**Risk:** Breaking frontend if API contracts change
- **Impact:** Users cannot access agent management UI
- **Mitigation:**
  - Update frontend and backend atomically
  - Keep old endpoints as deprecated (1 week grace period)
  - Comprehensive frontend testing before deployment

**Risk:** Data loss if migrations fail
- **Impact:** Agent data becomes inaccessible or corrupted
- **Mitigation:**
  - Database backup before ANY changes
  - Transaction-wrapped migrations
  - Rollback procedure tested
  - Dry-run migrations on test data

**Risk:** Orphaned records if Agent table dropped prematurely
- **Impact:** Historical data lost, audit trail broken
- **Mitigation:**
  - Do NOT drop Agent table in this handover
  - Mark as deprecated only
  - Plan data migration in separate handover
  - Archive Agent table before eventual deletion

### Medium Risk (Gradual Impact)

**Risk:** Test failures due to model changes
- **Impact:** CI/CD pipeline blocked, delays deployment
- **Mitigation:**
  - Update tests alongside code changes
  - Run full test suite after each migration
  - Fix tests immediately before moving to next file

**Risk:** Performance degradation from query changes
- **Impact:** Slower API responses, poor UX
- **Mitigation:**
  - Benchmark queries before/after
  - Add indexes if needed
  - Profile slow endpoints
  - Optimize JSONB queries

**Risk:** Missing edge cases in status mapping
- **Impact:** Incorrect agent state display, workflow issues
- **Mitigation:**
  - Document all 4→7 state mappings explicitly
  - Test each status transition
  - Add validation in MCPAgentJob model
  - User testing of all agent workflows

### Low Risk (Minimal Impact)

**Risk:** Dead code deletion removes something still used
- **Impact:** Runtime errors in rare code paths
- **Mitigation:**
  - Search entire codebase for callers before deletion
  - User approval required for each deletion
  - Git tracks all deletions (reversible)
  - Monitor error logs after deployment

**Risk:** Script cleanup breaks installation
- **Impact:** New installations fail
- **Mitigation:**
  - Test installation flow after script changes
  - Keep installer scripts unless confirmed unused
  - Document which scripts are installation-critical

---

## Success Criteria

### Part A Success Criteria (Week 1)

- [ ] All 9 overlap files reviewed with user
- [ ] All 9 overlap files use ONLY MCPAgentJob (or deleted if unused)
- [ ] Zero files import both Agent and MCPAgentJob
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] No UI regressions in manual testing
- [ ] Performance benchmarks within 5% of baseline

### Part B Success Criteria (Week 2-3)

- [ ] All 197 legacy Agent files audited
- [ ] Used functions refactored to MCPAgentJob
- [ ] Unused functions/files deleted (with user approval)
- [ ] Agent model usage count: 0 production files (0 in src/, 0 in api/)
- [ ] All tests updated and passing
- [ ] Frontend uses only new MCPAgentJob endpoints
- [ ] Documentation updated to reflect new architecture

### Final Validation

- [ ] Zero imports of Agent model in src/ and api/ directories
- [ ] Zero queries to agents table in production code
- [ ] Agent table marked for deprecation (Handover 0113)
- [ ] 100% MCPAgentJob usage in active codebase
- [ ] All tests pass (unit, integration, API, frontend)
- [ ] Performance benchmarks meet targets (<10% regression)
- [ ] Frontend agent management fully functional
- [ ] No error spikes in production logs
- [ ] User acceptance testing completed

---

## Appendices

### Appendix A: Overlap File List (Part A)

From grep results (9 files total):

**Production Code (6 files):**
1. `src/giljo_mcp/tools/tool_accessor.py` - Tool access coordination
2. `api/endpoints/projects.py` - Project management API
3. `src/giljo_mcp/tools/orchestration.py` - Orchestration tools
4. `api/endpoints/statistics.py` - System statistics
5. `api/endpoints/prompts.py` - Prompt generation (if confirmed)
6. `api/endpoints/templates.py` - Template management (if confirmed)

**Test Code (3 files):**
7. `tests/integration/test_mcp_get_orchestrator_instructions.py`
8. `tests/test_orchestrator_routing.py`
9. Additional test/doc files (exact file TBD from grep)

### Appendix B: Legacy File Categories (Part B)

**Category 1: API Endpoints** (~10 files)
- `api/endpoints/agents.py` ✅ Already reviewed (DELETE + migrate frontend)
- `api/endpoints/agent_templates.py` - Template CRUD
- `api/endpoints/claude_export.py` - Export functionality
- `api/endpoints/downloads.py` - Download management
- `api/endpoints/orchestration.py` - Orchestration endpoints
- `api/endpoints/prompts.py` - Prompt endpoints
- `api/endpoints/templates.py` - Template endpoints

**Category 2: Core Source** (~20 files)
- `src/giljo_mcp/agent_selector.py` - Agent selection logic
- `src/giljo_mcp/agent_job_manager.py` - Job lifecycle management
- `src/giljo_mcp/orchestrator.py` - Main orchestrator
- `src/giljo_mcp/mission_planner.py` - Mission planning
- `src/giljo_mcp/workflow_engine.py` - Workflow execution
- And ~15 more core files

**Category 3: Scripts** (~10 files)
- `scripts/init_templates.py` - Template initialization
- `scripts/migrate_templates.py` - Template migration
- `scripts/seed_orchestrator_template.py` - Orchestrator seeding
- `scripts/test_websocket_events.py` - WebSocket testing
- And ~6 more scripts

**Category 4: Installers** (~5 files)
- `installer/core/config.py` - Windows installer config
- `Linux_Installer/core/config.py` - Linux installer config
- And ~3 more installer files

**Category 5: Tests** (~50 files)
- To be updated after production code migrations
- Test files mirror production structure

**Category 6: Tools** (~30 files)
- `src/giljo_mcp/tools/*.py` - Various MCP tools
- Agent coordination tools
- Project management tools

**Category 7: Other** (~72 files)
- Migration scripts
- Documentation files
- Configuration templates
- Utility modules

### Appendix C: Testing Checklist

**Unit Tests:**
- [ ] Agent model tests (remove/update)
- [ ] MCPAgentJob model tests (verify all states)
- [ ] Tool accessor tests (verify migrations)
- [ ] Orchestration tests (verify workflows)
- [ ] Agent selector tests (verify logic)
- [ ] Mission planner tests (verify planning)

**Integration Tests:**
- [ ] Project creation flow (end-to-end)
- [ ] Agent spawning flow (orchestrator → job)
- [ ] Project closeout flow (all agents decommissioned)
- [ ] Status transition flow (all 7 states)
- [ ] Multi-tenant isolation (no cross-tenant leakage)
- [ ] WebSocket event propagation (real-time updates)

**API Tests:**
- [ ] `/api/v1/agents` deprecated (returns 410 Gone)
- [ ] `/api/agent-jobs` working (all CRUD operations)
- [ ] Frontend API calls successful (no 404s)
- [ ] Authentication working (all endpoints protected)
- [ ] Rate limiting working (no abuse)
- [ ] Error handling (proper error messages)

**Frontend Tests:**
- [ ] Agent store working (Vuex state management)
- [ ] Agent cards rendering (all 7 states)
- [ ] Status badges correct (colors, labels)
- [ ] Jobs tab functional (list, filter, sort)
- [ ] Orchestrator monitoring (context bars, succession)
- [ ] WebSocket updates (real-time UI changes)

**Performance Tests:**
- [ ] Query performance before/after (<10% regression)
- [ ] WebSocket latency (<100ms for updates)
- [ ] Page load times (dashboard <2s)
- [ ] Database query counts (no N+1 queries)
- [ ] Memory usage (no leaks)
- [ ] CPU usage (no spikes)

### Appendix D: Rollback Procedures

**If Part A fails (Week 1):**

```bash
# 1. Stop the server
cd F:\GiljoAI_MCP
python api/shutdown.py

# 2. Restore from git (overlap files)
git checkout HEAD -- src/giljo_mcp/tools/tool_accessor.py
git checkout HEAD -- api/endpoints/projects.py
git checkout HEAD -- src/giljo_mcp/tools/orchestration.py
git checkout HEAD -- api/endpoints/statistics.py
# ... restore all modified files

# 3. Restore database from backup
psql -U postgres -d giljo_mcp < backups/pre_part_a_backup.sql

# 4. Restart server
python startup.py

# 5. Verify rollback
curl http://localhost:7272/api/health
# Should return 200 OK

# 6. Test critical flows
# - Create project
# - Spawn agent
# - Check agent status
```

**If Part B fails (Week 2-3):**

```bash
# 1. Stop the server
cd F:\GiljoAI_MCP
python api/shutdown.py

# 2. Restore database from backup
psql -U postgres -d giljo_mcp < backups/pre_part_b_backup.sql

# 3. Restore code from git
git reset --hard <commit_before_part_b>

# 4. Restore frontend (if needed)
cd frontend
git checkout HEAD -- src/

# 5. Reinstall dependencies
npm install

# 6. Restart server
cd ..
python startup.py

# 7. Verify rollback
curl http://localhost:7272/api/health
curl http://localhost:7272/api/agent-jobs

# 8. Test frontend
# Open http://localhost:7272 in browser
# Verify all tabs working
```

**Partial Rollback (Single File):**

```bash
# If only one file needs rollback:
git checkout HEAD -- path/to/file.py

# Then restart server:
python startup.py
```

### Appendix E: File Decision Log

User decisions will be recorded here during review:

| Date | File | Function | Decision | Rationale | Status |
|------|------|----------|----------|-----------|--------|
| 2025-01-07 | api/endpoints/agents.py | list_agents() | REFACTOR | Used by frontend Jobs tab | ✅ Approved |
| 2025-01-07 | api/endpoints/agents.py | create_agent() | REFACTOR | Used by orchestrator spawn | ✅ Approved |
| 2025-01-07 | api/endpoints/agents.py | get_agent() | REFACTOR | Used by frontend agent cards | ✅ Approved |
| 2025-01-07 | api/endpoints/agents.py | update_agent() | REFACTOR | Used by status updates | ✅ Approved |
| 2025-01-07 | api/endpoints/agents.py | delete_agent() | REFACTOR | Used by agent decommission | ✅ Approved |
| ... | ... | ... | ... | ... | ... |

**Decision Key:**
- **REFACTOR** - Migrate to MCPAgentJob
- **DELETE** - Remove function/file (dead code)
- **KEEP AS-IS** - Keep using Agent (rare, needs justification)
- **RESEARCH** - Need more investigation

### Appendix F: Migration Metrics

This section will be populated during migration:

**Part A Metrics:**
- Files reviewed: 0 / 9
- Files migrated: 0 / 9
- Files deleted: 0 / 9
- Lines of code changed: 0
- Tests updated: 0
- Tests passing: 0 / {total}

**Part B Metrics:**
- Files reviewed: 1 / 197 (agents.py reviewed)
- Files migrated: 0 / 197
- Files deleted: 0 / 197
- Lines of code changed: 0
- Dead code removed: 0 lines
- Tests updated: 0
- Tests passing: 0 / {total}

**Final Metrics:**
- Total files reviewed: 1 / 206
- Total files migrated: 0 / 206
- Total files deleted: 0 / 206
- Total lines changed: 0
- Total dead code removed: 0 lines
- Agent model imports removed: 0 / 206
- MCPAgentJob adoption: 0%

### Appendix G: Reference Documentation

**Related Handovers:**
- **0113:** Unified Agent State System (7-state model)
- **0114:** Jobs Tab UI Harmonization
- **0115:** Legacy Agent Model Deprecation Strategy

**Key Files:**
- `src/giljo_mcp/models.py` - Agent and MCPAgentJob models
- `src/giljo_mcp/agent_job_manager.py` - Job lifecycle management
- `api/endpoints/agent_jobs.py` - Modern agent job API
- `frontend/src/store/modules/agents.js` - Frontend state management

**Database Schema:**
- `agents` table - Legacy 4-state model (to be deprecated)
- `mcp_agent_jobs` table - Modern 7-state model (current)

**Testing Resources:**
- `tests/test_agent_job_manager.py` - Job manager unit tests
- `tests/integration/test_agent_workflows.py` - Integration tests
- `tests/api/test_agent_jobs.py` - API endpoint tests

---

## Next Steps

### Immediate Actions (Week 1 - Part A)

1. **User Review Session #1** (Day 1)
   - Review files 1-3 from overlap list
   - Document current usage
   - Get user decisions
   - Create migration plans

2. **User Review Session #2** (Day 2)
   - Review files 4-6 from overlap list
   - Document current usage
   - Get user decisions
   - Create migration plans

3. **Execute Migrations** (Days 3-4)
   - Implement approved migrations
   - Update tests
   - Run test suites
   - Fix regressions

4. **Validation** (Day 5)
   - Integration testing
   - Performance validation
   - User acceptance testing
   - Update handover with results

### Follow-up Actions (Weeks 2-3 - Part B)

1. **High-Priority Endpoint Migration** (Week 2)
   - Migrate `api/endpoints/agents.py` (already reviewed)
   - Migrate other API endpoints
   - Update frontend
   - Test thoroughly

2. **Bulk Legacy Cleanup** (Week 3)
   - Analyze scripts and installers
   - Get user deletion approvals
   - Execute deletions
   - Final validation

3. **Documentation & Handover** (End of Week 3)
   - Update all metrics
   - Create migration summary report
   - Update CLAUDE.md with new patterns
   - Mark Agent model as deprecated
   - Plan data migration (future handover)

---

**Document Status:** Planning Phase - Ready for User Review

**Next Action:** Begin Part A - Review overlap file #1 (`tool_accessor.py`)

**Success Metric:** Zero dual-model files, 100% MCPAgentJob adoption in production code
