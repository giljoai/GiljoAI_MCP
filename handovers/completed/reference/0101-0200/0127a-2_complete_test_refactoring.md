# Handover 0127a-2: Complete Test Refactoring (Phase 2)

**Status:** Ready to Execute
**Priority:** P1 - HIGH
**Estimated Duration:** 1-2 days
**Agent Budget:** 100K tokens
**Depends On:** 0127a (Phase 1 Complete - Core fixtures fixed)

---

## Executive Summary

### Current Status

Phase 1 (0127a) successfully fixed the core test infrastructure by updating fixtures to use `MCPAgentJob` instead of the removed `Agent` model. However, 11 test files were marked with `TODO(0127a)` markers because they require significant refactoring to work with the new model structure.

### Files Requiring Refactoring

**Integration Tests (6 files):**
1. `test_backup_integration.py` - Backup/restore functionality
2. `test_claude_code_integration.py` - Claude Code MCP integration
3. `test_hierarchical_context.py` - Context hierarchy handling
4. `test_message_queue_integration.py` - Message queue system
5. `test_orchestrator_template.py` - Orchestrator templates
6. `test_upgrade_validation.py` - Upgrade validation

**Other Tests (5 files):**
7. `test_endpoints_simple.py` - Basic endpoint tests (SKIPPED)
8. `test_orchestrator_forced_monitoring.py` - Orchestrator monitoring
9. `performance/test_database_benchmarks.py` - Database performance

### The Challenge

These tests don't just need simple import fixes - they require understanding and rewriting test logic to work with the fundamentally different MCPAgentJob model structure:

| Agent Model (Removed) | MCPAgentJob Model | Impact on Tests |
|----------------------|-------------------|-----------------|
| Simple agent concept | Job-based lifecycle | Tests need job lifecycle understanding |
| Direct agent creation | Job spawning process | Creation logic different |
| Agent.name identifier | job_id UUID | Identification patterns changed |
| Simple status | Complex job states | Status assertions need updates |
| No tenant isolation | Requires tenant_key | All tests need tenant context |

---

## Implementation Strategy

### Approach: Systematic Refactoring

For each test file:
1. Understand what the test is validating
2. Map Agent concepts to MCPAgentJob concepts
3. Rewrite test logic for job-based model
4. Ensure test intent is preserved
5. Validate against actual system behavior

---

## Phase 1: Simple Tests (2-3 hours)

### 1.1 Fix test_endpoints_simple.py

**Current State:** Skipped with decorator

```python
@pytest.mark.skip(reason="TODO(0127a): Needs rewrite for MCPAgentJob model")
def test_create_agent():
    # Old test creating Agent directly
```

**Fix Strategy:**
```python
def test_create_agent_job():
    """Test creating an agent job through endpoint."""
    # Create MCPAgentJob instead
    job_data = {
        "job_id": str(uuid.uuid4()),
        "tenant_key": "test_tenant",
        "agent_type": "implementer",
        "mission": "Test mission",
        "project_id": test_project.id,
        "status": "pending"
    }

    response = client.post("/api/v1/agent-jobs", json=job_data)
    assert response.status_code == 200
    assert response.json()["job_id"] == job_data["job_id"]
```

### 1.2 Fix test_database_benchmarks.py

**Current Issue:** Import commented out

```python
# TODO(0127a): from src.giljo_mcp.models import Agent, Message, Project, Task
```

**Fix:**
```python
from src.giljo_mcp.models import MCPAgentJob, Message, Project, Task

def benchmark_agent_job_creation():
    """Benchmark MCPAgentJob creation performance."""
    jobs = []
    start_time = time.time()

    for i in range(1000):
        job = MCPAgentJob(
            job_id=str(uuid.uuid4()),
            tenant_key="benchmark_tenant",
            agent_type="worker",
            mission=f"Benchmark mission {i}",
            project_id=test_project.id,
            status="pending"
        )
        jobs.append(job)

    # Bulk insert
    session.bulk_save_objects(jobs)
    session.commit()

    elapsed = time.time() - start_time
    assert elapsed < 5.0  # Should create 1000 jobs in under 5 seconds
```

---

## Phase 2: Integration Tests - Message Queue (3-4 hours)

### 2.1 Fix test_message_queue_integration.py

**Purpose:** Tests message acknowledgment system

**Key Changes Needed:**
- Replace Agent with MCPAgentJob
- Update message routing to use job_id instead of agent.name
- Add tenant_key to all operations

**Example Refactoring:**
```python
# OLD: Agent-based message test
def test_agent_message_acknowledgment():
    agent = create_test_agent("message_agent")
    message = Message(
        from_agent=agent.name,
        to_agent="orchestrator",
        content="Test message"
    )

# NEW: Job-based message test
def test_agent_job_message_acknowledgment():
    job = create_test_agent_job("implementer", "test_tenant")
    message = Message(
        from_agent_job_id=job.job_id,
        to_agent_type="orchestrator",
        content="Test message",
        tenant_key="test_tenant"
    )

    # Test acknowledgment flow
    queue.send_message(message)
    received = queue.receive_messages(job.job_id)
    assert len(received) == 1

    # Acknowledge
    queue.acknowledge_message(received[0].id)
    assert received[0].acknowledged_at is not None
```

### 2.2 Fix test_backup_integration.py

**Purpose:** Tests backup/restore with agents

**Key Changes:**
- Backup MCPAgentJob instead of Agent
- Update restore validation for job fields
- Ensure tenant isolation in backup

---

## Phase 3: Complex Integration Tests (4-5 hours)

### 3.1 Fix test_claude_code_integration.py

**Special Considerations:**
- AgentInteraction model may also need updates
- Claude Code spawns jobs, not agents
- Test subagent mode with job lifecycle

**Example Update:**
```python
# OLD: Test agent spawning
def test_claude_spawns_agent():
    agent = claude_code.spawn_agent("implementer", project)
    assert agent.name.startswith("implementer_")

# NEW: Test job spawning
def test_claude_spawns_job():
    job = claude_code.spawn_agent_job(
        agent_type="implementer",
        project_id=project.id,
        tenant_key="test_tenant",
        mission="Implement feature X"
    )
    assert job.job_id  # UUID
    assert job.status == "pending"

    # Test job acknowledgment
    acknowledged = claude_code.acknowledge_job(job.job_id, "claude_agent_123")
    assert acknowledged.status == "working"
```

### 3.2 Fix test_hierarchical_context.py

**Purpose:** Tests context hierarchy with agents

**Updates Needed:**
- Jobs don't have persistent context like agents
- Context now tied to job execution
- Update hierarchy traversal for job model

### 3.3 Fix test_orchestrator_template.py

**Purpose:** Tests orchestrator with agent templates

**Major Changes:**
- AgentTemplate → MCPAgentJobTemplate (if exists)
- Template spawns jobs, not agents
- Orchestrator manages job lifecycle

```python
# NEW: Orchestrator spawning jobs from template
def test_orchestrator_spawns_from_template():
    template = get_implementer_template()

    job = orchestrator.spawn_job_from_template(
        template=template,
        project_id=project.id,
        tenant_key="test_tenant",
        mission_overrides={"priority": "high"}
    )

    assert job.agent_type == template.agent_type
    assert job.mission  # Populated from template
    assert job.status == "pending"

    # Test orchestrator monitors job
    orchestrator.monitor_job(job.job_id)
    status = orchestrator.get_job_status(job.job_id)
    assert status in ["pending", "working", "completed"]
```

### 3.4 Fix test_orchestrator_forced_monitoring.py

**Purpose:** Tests forced monitoring of agents

**Updates:**
- Monitor jobs instead of agents
- Job lifecycle states different from agent states
- Update monitoring assertions

### 3.5 Fix test_upgrade_validation.py

**Purpose:** Validates system upgrades

**Changes:**
- Validate MCPAgentJob table instead of Agent
- Check migration from Agent → MCPAgentJob (if applicable)
- Ensure no Agent references remain

---

## Phase 4: Validation (2-3 hours)

### 4.1 Run Each Test Individually

```bash
# Run each refactored test
pytest tests/test_endpoints_simple.py -v
pytest tests/performance/test_database_benchmarks.py -v
pytest tests/integration/test_message_queue_integration.py -v
pytest tests/integration/test_backup_integration.py -v
pytest tests/integration/test_claude_code_integration.py -v
pytest tests/integration/test_hierarchical_context.py -v
pytest tests/integration/test_orchestrator_template.py -v
pytest tests/test_orchestrator_forced_monitoring.py -v
pytest tests/integration/test_upgrade_validation.py -v
```

### 4.2 Run Full Test Suite

```bash
# Ensure no regressions
pytest tests/ -v

# Check coverage
pytest tests/ --cov=src --cov-report=html
```

### 4.3 Remove TODO Markers

After each test is fixed and passing:
```python
# Remove TODO line
# TODO(0127a): from src.giljo_mcp.models import Agent  ← DELETE THIS

# Keep the working import
from src.giljo_mcp.models import MCPAgentJob
```

---

## Common Patterns for Refactoring

### Pattern 1: Agent Creation → Job Creation

```python
# OLD
agent = Agent(name="test", type="worker", project_id=p.id)

# NEW
job = MCPAgentJob(
    job_id=str(uuid.uuid4()),
    tenant_key="test_tenant",
    agent_type="worker",
    agent_name="test",  # Optional
    project_id=p.id,
    mission="Test mission",
    status="pending"
)
```

### Pattern 2: Agent Query → Job Query

```python
# OLD
agents = session.query(Agent).filter(Agent.project_id == p.id).all()

# NEW
jobs = session.query(MCPAgentJob).filter(
    MCPAgentJob.project_id == p.id,
    MCPAgentJob.tenant_key == tenant_key
).all()
```

### Pattern 3: Status Checks

```python
# OLD
assert agent.status == "active"

# NEW (job states are different)
assert job.status in ["pending", "working", "completed", "failed"]
```

### Pattern 4: Message Routing

```python
# OLD
message.to_agent = agent.name

# NEW
message.to_job_id = job.job_id
# OR
message.to_agent_type = "orchestrator"  # Route by type
```

---

## Validation Checklist

- [ ] All TODO(0127a) markers removed
- [ ] All 11 test files refactored
- [ ] All tests passing (100%)
- [ ] No skipped tests remain
- [ ] Test coverage maintained >80%
- [ ] Integration tests validate actual behavior
- [ ] Performance benchmarks still meet targets
- [ ] No Agent imports remain anywhere

---

## Risk Assessment

**Risk 1: Changing Test Intent**
- **Impact:** HIGH - Tests might not validate same behavior
- **Mitigation:** Understand each test's purpose before refactoring

**Risk 2: Missing Edge Cases**
- **Impact:** MEDIUM - New model might have different edge cases
- **Mitigation:** Add new test cases for MCPAgentJob-specific scenarios

**Risk 3: Performance Regression**
- **Impact:** MEDIUM - Job model might be slower
- **Mitigation:** Run benchmarks, optimize if needed

---

## Success Metrics

### Before
- 11 test files with TODO markers
- Multiple tests skipped
- Test suite partially broken

### After
- 0 TODO(0127a) markers
- All tests passing
- Full test coverage restored
- CI/CD pipeline green

---

## Tips for Implementation

### Do's
✅ Understand test purpose before changing
✅ Preserve test intent while updating structure
✅ Add tenant_key to all operations
✅ Use job lifecycle states correctly
✅ Test actual system behavior

### Don'ts
❌ Don't just comment out failing assertions
❌ Don't skip tests instead of fixing
❌ Don't change what's being tested
❌ Don't forget tenant isolation
❌ Don't assume job states = agent states

---

**Created:** 2025-11-10
**Priority:** P1 - HIGH
**Complete After:** Core system is stable
**Estimated Effort:** 1-2 days of focused work