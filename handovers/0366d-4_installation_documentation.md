# Handover 0366d-4: Installation & Documentation Updates

**Phase**: Phase 4 of 4 (Installation & Documentation)
**Status**: Ready for Implementation
**Estimated Duration**: 2-3 hours
**Dependencies**: 0366d-1 (Backend), 0366d-2 (Frontend), 0366d-3 (Testing) must be complete

---

## Scope Definition

This handover covers **installation seeding and documentation updates only**. It is explicitly scoped to 4 items:

### IN SCOPE ✅
1. Update install.py seeding for AgentJob + AgentExecution demo data
2. Minor updates to template_seeder.py if needed
3. User guide updates for new UI features
4. API documentation for new executions endpoint

### OUT OF SCOPE ❌
- Frontend changes (covered in 0366d-1/2/3)
- Backend code changes (covered in 0366d-1)
- Database migrations (already complete in 0366a)
- Comprehensive documentation overhaul
- New installation features
- Multi-platform installer updates

---

## File-Specific Changes

### 1. install.py (Root Level)

**File**: `F:\GiljoAI_MCP\install.py`

**Location**: UnifiedInstaller class, after run_database_migrations() completes

**Changes Required**:

```python
# Add demo data seeding after migrations complete
# Location: After line ~193 (in install flow) or ~770 (in upgrade flow)

async def _seed_agent_job_demo_data(self, tenant_key: str = "default"):
    """
    Seed sample AgentJob and AgentExecution records to demonstrate succession.

    Creates:
    - 1 AgentJob (parent job)
    - 2 AgentExecution records (showing succession chain)
    """
    from giljo_mcp.database import DatabaseManager
    from giljo_mcp.models import AgentJob, AgentExecution
    from uuid import uuid4
    from datetime import datetime, timedelta
    import os

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        return

    db_manager = DatabaseManager(db_url, is_async=True)

    async with db_manager.get_session_async() as session:
        # Check if demo data already exists
        from sqlalchemy import select
        existing = await session.execute(
            select(AgentJob).where(AgentJob.description == "Demo: Orchestrator with Succession")
        )
        if existing.scalar_one_or_none():
            self._print_info("Demo agent job data already exists, skipping seed")
            return

        # Create parent AgentJob
        job_id = uuid4()
        agent_job = AgentJob(
            id=job_id,
            tenant_key=tenant_key,
            agent_type="orchestrator",
            description="Demo: Orchestrator with Succession",
            spawned_by=None,
            status="active",
            created_at=datetime.utcnow() - timedelta(hours=2)
        )
        session.add(agent_job)

        # Create first AgentExecution (initial orchestrator)
        exec1_id = uuid4()
        execution1 = AgentExecution(
            id=exec1_id,
            agent_job_id=job_id,
            agent_id=f"agent_{exec1_id.hex[:8]}",
            mission="Initial orchestrator mission: coordinate backend refactoring",
            status="completed",
            started_at=datetime.utcnow() - timedelta(hours=2),
            completed_at=datetime.utcnow() - timedelta(hours=1, minutes=30),
            context_used=85000,
            context_budget=100000,
            succession_reason="Approaching context limit (85%)"
        )
        session.add(execution1)

        # Create second AgentExecution (successor)
        exec2_id = uuid4()
        execution2 = AgentExecution(
            id=exec2_id,
            agent_job_id=job_id,
            agent_id=f"agent_{exec2_id.hex[:8]}",
            mission="Successor orchestrator mission: complete backend refactoring and testing",
            status="active",
            started_at=datetime.utcnow() - timedelta(hours=1, minutes=30),
            completed_at=None,
            context_used=35000,
            context_budget=100000,
            succession_reason=None,
            previous_execution_id=exec1_id
        )
        session.add(execution2)

        await session.commit()
        self._print_success("Seeded demo AgentJob with 2-agent succession chain")
```

**Integration Point**:
- Call after `run_database_migrations()` succeeds
- Add to both fresh install flow (~line 193) and upgrade flow (~line 770)
- Wrap in try/except to not block installation if seeding fails

**Example Integration**:
```python
# In run() method, after migration success:
if migration_result["success"]:
    self._print_success("Database migrations completed successfully")

    # Seed demo data
    try:
        import asyncio
        asyncio.run(self._seed_agent_job_demo_data())
    except Exception as e:
        self._print_warning(f"Failed to seed demo data: {e}")
        # Continue installation - demo data is optional
```

---

### 2. template_seeder.py (Service Layer)

**File**: `F:\GiljoAI_MCP\src\giljo_mcp\template_seeder.py`

**Review Required**:
- Check if any functions reference old model names (MCPAgentJob, etc.)
- Update import statements if needed
- Should be minimal changes (template seeder focuses on agent templates, not jobs)

**Expected Changes**:
```python
# Update imports if referencing agent job models
from giljo_mcp.models import AgentJob, AgentExecution  # Updated from MCPAgentJob
```

**Validation**:
- Run existing tests: `pytest tests/unit/test_template_seeder.py`
- Ensure no breaking changes to seeding logic

---

### 3. User Guide Updates

**File**: `F:\GiljoAI_MCP\docs\user_guides\agent_monitoring_guide.md`

**Sections to Update**:

#### A. Add Section: Understanding Agent IDs vs Job IDs

Insert after line 31 (after "Understanding Agent Health Indicators" heading):

```markdown
---

## Understanding Agent IDs vs Job IDs

GiljoAI tracks both **jobs** and **agent executions** separately to support orchestrator succession.

### Key Concepts

| **Term** | **Definition** | **Example** |
|---------|----------------|-------------|
| **Agent Job** | A logical unit of work that may span multiple agents | "Refactor backend service layer" |
| **Agent Execution** | A single agent instance working on a job | "agent_a1b2c3d4" |
| **Succession** | When one agent hands off to another while preserving context | Agent A → Agent B (same job) |

### When Do Agents Succeed Each Other?

**Automatic Succession Triggers**:
- Context usage reaches 90% of budget (default)
- Agent requests handover via `/gil_handover` command
- Manual succession via "Hand Over" button in UI

**What Stays the Same**:
- Job ID (continuity of work)
- Job description (what needs to be done)
- Spawned-by relationship (who created this job)

**What Changes**:
- Agent ID (new agent instance)
- Context used (reset to zero for successor)
- Mission (condensed summary of remaining work)

### Viewing Succession Timeline

In the agent monitoring dashboard, you can see:
- **Current Agent ID**: The active agent working on the job
- **Succession Count**: How many agents have worked on this job
- **Timeline**: Click "View Timeline" to see all executions in chronological order

**Example Timeline**:
```
Job: "Refactor Backend" (job_12345)
├─ Agent A (agent_a1b2c3d4) - Completed
│  Context: 85K/100K used
│  Reason: "Approaching context limit"
│  Duration: 90 minutes
└─ Agent B (agent_e5f6g7h8) - Active
   Context: 35K/100K used
   Started: 30 minutes ago
```

---
```

#### B. Update Section: Database Fields (line 269)

Update existing section to include new fields:

```markdown
### Database Fields

**AgentJob Table** (logical work unit):
- **`id`**: Unique job identifier (UUID)
- **`description`**: User-provided description of work
- **`agent_type`**: Type of agent (orchestrator, tester, etc.)
- **`status`**: Job status (pending, active, completed, failed, cancelling)
- **`spawned_by`**: Parent job ID if this is a subagent

**AgentExecution Table** (individual agent instances):
- **`id`**: Unique execution identifier (UUID)
- **`agent_job_id`**: Link to parent job
- **`agent_id`**: Unique agent instance ID
- **`mission`**: AI-generated mission for this specific execution
- **`status`**: Execution status (pending, active, completed, failed)
- **`context_used`**: Tokens consumed by this agent
- **`context_budget`**: Maximum tokens allowed (default: 100K)
- **`succession_reason`**: Why this agent succeeded another (if applicable)
- **`previous_execution_id`**: Link to predecessor agent (succession chain)
- **`started_at`**: When agent began work
- **`completed_at`**: When agent finished work
```

#### C. Update FAQ Section (line 193)

Add new Q&A after existing questions:

```markdown
### Q: What's the difference between agent_id and job_id?

**A**:
- **job_id**: Identifies the logical work to be done (e.g., "Refactor backend")
- **agent_id**: Identifies a specific agent instance working on that job

A single job may have multiple agents (via succession). Each agent gets a unique agent_id, but they share the same job_id.

**Example**:
- Job ID: `job_abc123` ("Fix authentication bug")
- Agent 1: `agent_001` (worked 90 min, hit context limit)
- Agent 2: `agent_002` (current, working 30 min)

Both agents have the same job_id but different agent_ids.

### Q: Can I see which agent is currently working on a job?

**A**: Yes. The agent card displays:
1. **Current Agent ID** in the header (e.g., "agent_a1b2c3d4")
2. **Succession indicator** showing "Agent 2 of 2" if succession occurred
3. **Timeline button** to view full execution history

Click the timeline icon to see all agents that worked on this job in chronological order.
```

---

### 4. API Documentation

**File**: `F:\GiljoAI_MCP\docs\api\agent_jobs_endpoints.md` (NEW FILE)

**Create new API documentation following projects_endpoints.md template**:

```markdown
# Agent Jobs API Endpoints

**Document Version**: 1.0
**Implementation Date**: December 20, 2025
**Status**: Production Ready
**Related Handover**: 0366d - Agent Job Dual-Model Architecture

---

## Overview

This document provides API reference for agent job management endpoints, focusing on the dual-model architecture (AgentJob + AgentExecution) introduced in Handover 0366a.

**Base URL**: `http://your-server:7272/api/v1`

**Authentication**: All endpoints require Bearer token authentication.

---

## Table of Contents

1. [GET /jobs/{job_id}](#get-jobsjob_id)
2. [GET /jobs/{job_id}/executions](#get-jobsjob_idexecutions)
3. [GET /jobs/{job_id}/executions/{execution_id}](#get-jobsjob_idexecutionsexecution_id)
4. [Common Error Responses](#common-error-responses)
5. [WebSocket Events](#websocket-events)

---

## GET /jobs/{job_id}

Retrieve details for a specific agent job.

### Authentication

**Required**: Bearer token in Authorization header

### Request

**Method**: `GET`
**Path**: `/api/v1/jobs/{job_id}`

**Path Parameters**:
- `job_id` (string, required): UUID of the agent job

### Response

**Status**: `200 OK`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "tenant_key": "tenant_abc123",
  "agent_type": "orchestrator",
  "description": "Refactor backend service layer",
  "spawned_by": null,
  "status": "active",
  "template_id": "template_123",
  "created_at": "2025-12-20T10:00:00Z",
  "current_execution": {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "agent_id": "agent_a1b2c3d4",
    "status": "active",
    "context_used": 35000,
    "context_budget": 100000,
    "started_at": "2025-12-20T11:30:00Z"
  },
  "execution_count": 2
}
```

### Error Responses

**Status**: `404 Not Found`
```json
{
  "detail": "Agent job not found"
}
```

---

## GET /jobs/{job_id}/executions

Retrieve all executions (agent instances) for a specific job, showing succession timeline.

### Authentication

**Required**: Bearer token in Authorization header

### Request

**Method**: `GET`
**Path**: `/api/v1/jobs/{job_id}/executions`

**Path Parameters**:
- `job_id` (string, required): UUID of the agent job

**Query Parameters**:
- `order` (string, optional): Sort order - "asc" or "desc" (default: "asc")
- `status` (string, optional): Filter by execution status - "pending", "active", "completed", "failed"

### Response

**Status**: `200 OK`

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "executions": [
    {
      "id": "660e8400-e29b-41d4-a716-446655440000",
      "agent_id": "agent_001",
      "mission": "Initial orchestrator mission: coordinate backend refactoring",
      "status": "completed",
      "context_used": 85000,
      "context_budget": 100000,
      "succession_reason": "Approaching context limit (85%)",
      "started_at": "2025-12-20T10:00:00Z",
      "completed_at": "2025-12-20T11:30:00Z",
      "duration_minutes": 90,
      "previous_execution_id": null
    },
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "agent_id": "agent_002",
      "mission": "Successor orchestrator mission: complete backend refactoring and testing",
      "status": "active",
      "context_used": 35000,
      "context_budget": 100000,
      "succession_reason": null,
      "started_at": "2025-12-20T11:30:00Z",
      "completed_at": null,
      "duration_minutes": null,
      "previous_execution_id": "660e8400-e29b-41d4-a716-446655440000"
    }
  ],
  "total_count": 2,
  "total_duration_minutes": 90
}
```

**Response Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | string | UUID of parent job |
| `executions` | array | List of agent executions in chronological order |
| `executions[].id` | string | Unique execution identifier |
| `executions[].agent_id` | string | Unique agent instance identifier |
| `executions[].mission` | string | AI-generated mission for this execution |
| `executions[].status` | string | Execution status (pending/active/completed/failed) |
| `executions[].context_used` | integer | Tokens consumed by this agent |
| `executions[].context_budget` | integer | Maximum tokens allowed |
| `executions[].succession_reason` | string/null | Why this agent succeeded another |
| `executions[].previous_execution_id` | string/null | Link to predecessor (succession chain) |
| `executions[].started_at` | string | ISO timestamp when agent began work |
| `executions[].completed_at` | string/null | ISO timestamp when agent finished |
| `executions[].duration_minutes` | integer/null | Duration of execution (if completed) |
| `total_count` | integer | Total number of executions for this job |
| `total_duration_minutes` | integer | Combined duration of all completed executions |

### Use Cases

**Succession Timeline**:
Use this endpoint to visualize agent succession over time:
- Display chronological list of all agents that worked on a job
- Show why each agent handed off to the next (succession_reason)
- Calculate total project duration across multiple agents

**Context Budget Analysis**:
- Track context consumption patterns across agents
- Identify if succession thresholds need adjustment
- Monitor token efficiency per execution

**Debugging**:
- Trace which agent introduced a bug or issue
- Review mission evolution across succession chain
- Understand handover quality and context preservation

### Error Responses

**Status**: `404 Not Found`
```json
{
  "detail": "Agent job not found"
}
```

**Status**: `400 Bad Request`
```json
{
  "detail": "Invalid status filter: must be one of pending, active, completed, failed"
}
```

---

## GET /jobs/{job_id}/executions/{execution_id}

Retrieve details for a specific agent execution.

### Authentication

**Required**: Bearer token in Authorization header

### Request

**Method**: `GET`
**Path**: `/api/v1/jobs/{job_id}/executions/{execution_id}`

**Path Parameters**:
- `job_id` (string, required): UUID of the agent job
- `execution_id` (string, required): UUID of the specific execution

### Response

**Status**: `200 OK`

```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "agent_job_id": "550e8400-e29b-41d4-a716-446655440000",
  "agent_id": "agent_002",
  "mission": "Successor orchestrator mission: complete backend refactoring and testing",
  "status": "active",
  "context_used": 35000,
  "context_budget": 100000,
  "succession_reason": null,
  "previous_execution_id": "660e8400-e29b-41d4-a716-446655440000",
  "started_at": "2025-12-20T11:30:00Z",
  "completed_at": null,
  "last_progress_at": "2025-12-20T12:00:00Z",
  "last_message_check_at": "2025-12-20T12:00:00Z"
}
```

### Error Responses

**Status**: `404 Not Found`
```json
{
  "detail": "Execution not found for this job"
}
```

---

## Common Error Responses

### 401 Unauthorized
```json
{
  "detail": "Not authenticated"
}
```

**Cause**: Missing or invalid Bearer token

### 403 Forbidden
```json
{
  "detail": "Not authorized to access this resource"
}
```

**Cause**: Authenticated user does not have permission for this tenant

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

**Cause**: Unexpected server error. Check logs for details.

---

## WebSocket Events

These events are broadcast when execution data changes:

### execution:created
Fired when new execution is created (agent spawned or succession occurred)

**Payload**:
```json
{
  "event": "execution:created",
  "execution_id": "660e8400-e29b-41d4-a716-446655440001",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "agent_id": "agent_002",
  "status": "pending"
}
```

### execution:status_changed
Fired when execution status changes (pending → active → completed/failed)

**Payload**:
```json
{
  "event": "execution:status_changed",
  "execution_id": "660e8400-e29b-41d4-a716-446655440001",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "old_status": "pending",
  "new_status": "active"
}
```

### execution:progress_update
Fired when agent reports progress (context usage updated)

**Payload**:
```json
{
  "event": "execution:progress_update",
  "execution_id": "660e8400-e29b-41d4-a716-446655440001",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "context_used": 35000,
  "context_budget": 100000,
  "percent_used": 35
}
```

---

## Related Documentation

- **User Guide**: [docs/user_guides/agent_monitoring_guide.md](../user_guides/agent_monitoring_guide.md)
- **Database Schema**: [docs/architecture/database_schema.md](../architecture/database_schema.md)
- **Handover Document**: [handovers/0366a_agent_job_dual_model_architecture.md](../../handovers/0366a_agent_job_dual_model_architecture.md)

---

## Support

For issues or questions:
1. Check API logs in `logs/` directory
2. Review handover documents for implementation details
3. Consult database schema for field definitions
4. Report bugs with request/response examples
```

---

## Acceptance Criteria

### Installation (install.py)
- [ ] Fresh install seeds AgentJob + 2 AgentExecution records
- [ ] Demo data shows realistic succession scenario
- [ ] Seeding does not block installation if it fails
- [ ] Install completes in <60 seconds (no performance regression)

### Template Seeder (template_seeder.py)
- [ ] No references to old model names (MCPAgentJob, etc.)
- [ ] All existing tests pass without modification
- [ ] No breaking changes to seeding logic

### User Guide (agent_monitoring_guide.md)
- [ ] New section explains agent_id vs job_id clearly
- [ ] Database fields section updated with new tables
- [ ] FAQ section addresses common confusion points
- [ ] Screenshots placeholders added (actual screenshots in 0366d-2)

### API Documentation (agent_jobs_endpoints.md)
- [ ] All 3 endpoints documented with examples
- [ ] Request/response schemas complete and accurate
- [ ] Use cases section explains when to use each endpoint
- [ ] WebSocket events documented
- [ ] Cross-references to related docs included

---

## Testing Plan

### Installation Testing
```bash
# Test fresh install with demo data
rm -rf data/  # Clean slate
python install.py

# Verify demo data created
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c \
  "SELECT id, description, status FROM agent_jobs WHERE description LIKE 'Demo:%';"

PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c \
  "SELECT id, agent_id, status, succession_reason FROM agent_executions ORDER BY started_at;"
```

### Template Seeder Testing
```bash
# Run existing test suite
pytest tests/unit/test_template_seeder.py -v
pytest tests/templates/test_template_seeder_messaging_contract.py -v
```

### Documentation Validation
- [ ] Markdown renders correctly (no broken formatting)
- [ ] All code examples use correct syntax highlighting
- [ ] Internal links resolve (relative paths)
- [ ] External references are accurate
- [ ] Tables align properly in rendered view

---

## Implementation Notes

### Demo Data Design Rationale

**Why 2 Executions?**
- Demonstrates succession without overwhelming users
- Shows both completed and active execution states
- Illustrates context limit trigger (85% threshold)
- Provides realistic timeline (90 min + 30 min)

**Succession Scenario**:
- First agent hits 85K context usage (85% of 100K budget)
- Triggers automatic succession
- Second agent starts fresh with condensed mission
- Currently active (realistic ongoing work)

### User Guide Update Strategy

**Focus Areas**:
1. **Conceptual clarity**: agent_id vs job_id confusion
2. **Visual discovery**: where to find information in UI
3. **Troubleshooting**: FAQ addresses common questions

**Non-Goals**:
- Not a complete rewrite
- Not adding new features
- Not changing existing workflows

### API Documentation Standards

**Template Used**: `docs/api/projects_endpoints.md`

**Follows Patterns**:
- Version header with date and handover reference
- Table of contents with anchor links
- Request/response examples with JSON
- Error responses section
- WebSocket events section
- Related documentation links

---

## Dependencies

### Must Complete First
- ✅ Handover 0366a (Database migrations)
- ⏳ Handover 0366d-1 (Backend endpoints implementation)
- ⏳ Handover 0366d-2 (Frontend UI updates)
- ⏳ Handover 0366d-3 (Testing infrastructure)

### Blocks
- Nothing (documentation is terminal node)

---

## Estimated Time Breakdown

| Task | Duration | Notes |
|------|----------|-------|
| install.py seeding | 45 min | Async function, integration, testing |
| template_seeder.py review | 15 min | Minimal changes expected |
| User guide updates | 60 min | 3 sections + FAQ additions |
| API documentation | 45 min | 3 endpoints + WebSocket events |
| Testing & validation | 15 min | Fresh install test, link checking |
| **Total** | **3 hours** | Conservative estimate |

---

## Completion Checklist

- [ ] Demo seeding function implemented in install.py
- [ ] Integration points added (fresh install + upgrade flows)
- [ ] Template seeder reviewed and updated if needed
- [ ] User guide sections added (agent_id vs job_id)
- [ ] User guide database fields section updated
- [ ] User guide FAQ section expanded
- [ ] API documentation file created
- [ ] All 3 endpoints documented with examples
- [ ] Fresh install tested with demo data verification
- [ ] Template seeder tests pass
- [ ] Documentation links validated
- [ ] Markdown rendering verified

---

## Next Steps After Completion

1. Run full installation test on clean system
2. Verify demo data appears in frontend UI
3. Test API endpoints against documentation examples
4. Update CHANGELOG.md with 0366 series completion
5. Archive handover in `handovers/completed/` directory

---

## TDD Approach: LITE Variant

**For frontend/UI work, use TDD-Lite** (not full RED-GREEN-REFACTOR):

1. **Verify current state** - Check component renders without errors
2. **Make changes** - Update component per spec
3. **Test manually** - Verify in browser
4. **Add data-testid** - For future E2E testing
5. **One simple E2E test** - Verify basic functionality

**Why TDD-Lite for frontend?**
- Full TDD is overkill for display-only changes
- Vue components are declarative (less logic to test)
- Manual verification catches visual issues tests miss
- data-testid enables future test expansion

**NOT required:**
- ❌ Writing tests FIRST
- ❌ Comprehensive test suites
- ❌ Unit tests for every component
- ❌ Mocking complex dependencies

---

## Kickoff Prompt

Copy this prompt to start execution:

---

**Mission**: Execute Handover 0366d-4 - Installation & Documentation Updates

**Context**: Read `handovers/0366d-4_installation_documentation.md` for complete specification.

**Approach**: TDD-Lite (verify → change → test manually → add data-testid → 1 E2E test)

**Scope**: 4 items only:
1. `install.py` - Add demo data seeding for AgentJob + AgentExecution
2. `src/giljo_mcp/template_seeder.py` - Review and update imports if needed
3. `docs/user_guides/agent_monitoring_guide.md` - Add agent_id vs job_id explanation sections
4. `docs/api/agent_jobs_endpoints.md` - NEW FILE - Document executions API endpoints

**NOT in scope**:
- ❌ Frontend changes (covered in 0366d-1/2/3)
- ❌ Backend code changes (covered in 0366d-1)
- ❌ Database migrations (already complete in 0366a)
- ❌ Comprehensive documentation overhaul
- ❌ New installation features
- ❌ Multi-platform installer updates

**Acceptance Criteria**: See handover document section "Acceptance Criteria"

**References**:
- Models: `src/giljo_mcp/models/agent_identity.py`
- Memory: `handovers/0366c_context_tools_agent_id_red_phase.md` (Serena)
- Prior work: 0366a (models), 0366b (services), 0366c (backend)

**First Step**: Read the handover file completely, then verify current state of install.py seeding logic.

---

**Document Version**: 1.0
**Created**: 2025-12-20
**Author**: Documentation Manager Agent
