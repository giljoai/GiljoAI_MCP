# MCP Protocol Quick Reference

**One-page cheat sheet for agents using GiljoAI MCP tools**

---

## 1. Identity Model (Handover 0366)

Understanding the three-tier identity system:

| Identifier | Represents | Lifecycle | Usage |
|------------|-----------|-----------|-------|
| `job_id` (AgentJob) | Work order UUID | Persists across succession | The WHAT - assigned task/mission |
| `agent_id` (AgentExecution) | Executor UUID | Changes on succession | The WHO - current executor instance |
| `project_id` | Workspace UUID | Persists | The WHERE - project context |

### Tool Parameter Mapping

| Tool | Requires `job_id` | Requires `agent_id` | Requires `project_id` |
|------|-------------------|---------------------|----------------------|
| `get_agent_mission` | ✓ | | |
| `get_orchestrator_instructions` | | ✓ | |
| `report_progress` | ✓ | | |
| `receive_messages` | | ✓ | |
| `send_message` | | ✓ (sender) + target | ✓ |
| `fetch_context` | | | ✓ |
| `complete_job` | ✓ | | |

---

## 2. Core Lifecycle Calls

### Mission & Instructions

```python
# Spawned agents: Fetch mission + protocol
get_agent_mission(
    agent_job_id="<job-id>",
    tenant_key="<tenant-key>"
)
# Returns: {"mission": {...}, "full_protocol": "..."}

# Orchestrators: Fetch staging/execution instructions
get_orchestrator_instructions(
    agent_id="<agent-id>",
    tenant_key="<tenant-key>"
)
# Returns: {"instructions": "...", "context_priorities": [...]}
```

### Progress Reporting

```python
report_progress(
    job_id="<job-id>",
    progress={
        "mode": "todo",           # REQUIRED for steps tracking
        "completed_steps": 3,     # Number completed
        "total_steps": 7,         # Total planned
        "current_step": "Implementing feature X",
        "percent": 43             # Optional percentage
    },
    tenant_key="<tenant-key>"
)
```

### Message Handling

```python
# Receive pending messages
receive_messages(
    agent_id="<agent-id>",
    tenant_key="<tenant-key>"
)
# Returns: [{"id": "...", "content": "...", "from_agent_id": "..."}]

# Send message to another agent
send_message(
    to_agent_id="<target-agent-id>",
    content="READY: Database migrations complete",
    project_id="<project-id>",
    tenant_key="<tenant-key>"
)
```

### Context Fetching

```python
# IMPORTANT: One category per call (Handover 0351)
fetch_context(
    product_id="<product-id>",
    categories=["product_core"],  # Array with EXACTLY one category
    tenant_key="<tenant-key>",
    depth_config={"product_core": "full"}
)
# Returns: {"product_core": {...}}

# For multiple categories, make separate calls:
# await fetch_context(..., categories=["product_core"])
# await fetch_context(..., categories=["tech_stack"])
# await fetch_context(..., categories=["vision_documents"])
```

### Job Completion

```python
complete_job(
    job_id="<job-id>",
    result={
        "summary": "Implemented feature X",
        "artifacts": ["path/to/file1.py", "path/to/file2.py"],
        "status": "completed"
    },
    tenant_key="<tenant-key>"
)
```

---

## 3. Polling Guidance

**Best Practices for Message Polling**:

| When | Action | Frequency |
|------|--------|-----------|
| On startup | `receive_messages()` | Once |
| Between major steps | `report_progress()` + `receive_messages()` | After each task |
| Before completion | `receive_messages()` | Once to clear queue |

**CRITICAL RULES**:
- Avoid tight loops - minimum 30 second intervals between polls
- Always call `receive_messages()` after `report_progress()`
- Check for messages before transitioning between workflow phases

---

## 4. Tenant Key Rules

**CRITICAL**: ALL MCP HTTP tools require `tenant_key` parameter.

**Multi-Tenant Isolation**:
- Every tool call filters by `tenant_key`
- Omitting `tenant_key` will cause tool call failures
- Never hardcode tenant keys - always use provided value

**Example (CORRECT)**:
```python
get_agent_mission(
    agent_job_id="abc-123",
    tenant_key="tenant_xyz"  # ALWAYS include
)
```

**Example (INCORRECT)**:
```python
get_agent_mission(
    agent_job_id="abc-123"
    # Missing tenant_key - WILL FAIL
)
```

---

## 5. Message Content Conventions

**Recommended Prefixes** (not enforced, but strongly recommended for clarity):

| Prefix | Meaning | Example |
|--------|---------|---------|
| `READY:` | Agent ready for work | `READY: Database schema validated` |
| `BLOCKER:` | Agent blocked, needs help | `BLOCKER: Missing API credentials` |
| `COMPLETE:` | Agent finished task | `COMPLETE: All tests passing` |
| `QUESTION:` | Agent has question | `QUESTION: Should we use Redis or Memcached?` |
| `UPDATE:` | Progress update | `UPDATE: 50% complete - 3 of 6 files processed` |

**Examples**:
```python
# Agent ready
send_message(
    to_agent_id="orchestrator-id",
    content="READY: Test suite initialized, awaiting test cases",
    project_id="...",
    tenant_key="..."
)

# Agent blocked
send_message(
    to_agent_id="orchestrator-id",
    content="BLOCKER: Database connection refused - verify PostgreSQL running",
    project_id="...",
    tenant_key="..."
)

# Agent completed
send_message(
    to_agent_id="orchestrator-id",
    content="COMPLETE: Migration script created and tested successfully",
    project_id="...",
    tenant_key="..."
)
```

---

## 6. Progress Reporting Format

**Standard Structure**:

```python
report_progress(
    job_id="<job-id>",
    progress={
        "mode": "todo",           # REQUIRED for steps tracking
        "completed_steps": 3,     # Number of steps completed
        "total_steps": 7,         # Total planned steps
        "current_step": "Implementing feature X",  # Current task description
        "percent": 43             # Optional percentage (0-100)
    },
    tenant_key="<tenant-key>"
)
```

**Field Descriptions**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `mode` | string | ✓ | Must be `"todo"` for step tracking |
| `completed_steps` | integer | ✓ | Number of steps completed (0 to total_steps) |
| `total_steps` | integer | ✓ | Total planned steps |
| `current_step` | string | ✓ | Description of current task |
| `percent` | integer | | Optional percentage (0-100) |

**Examples**:

```python
# Starting first task
report_progress(
    job_id="abc-123",
    progress={
        "mode": "todo",
        "completed_steps": 0,
        "total_steps": 5,
        "current_step": "Reading configuration files",
        "percent": 0
    },
    tenant_key="tenant_xyz"
)

# Mid-workflow
report_progress(
    job_id="abc-123",
    progress={
        "mode": "todo",
        "completed_steps": 3,
        "total_steps": 5,
        "current_step": "Running integration tests",
        "percent": 60
    },
    tenant_key="tenant_xyz"
)

# Final step
report_progress(
    job_id="abc-123",
    progress={
        "mode": "todo",
        "completed_steps": 5,
        "total_steps": 5,
        "current_step": "Finalizing documentation",
        "percent": 100
    },
    tenant_key="tenant_xyz"
)
```

---

## Quick Workflow Example

**Typical Agent Lifecycle**:

```python
# 1. Startup - Fetch mission
mission = get_agent_mission(agent_job_id="job-123", tenant_key="tenant_xyz")

# 2. Check for messages
messages = receive_messages(agent_id="agent-456", tenant_key="tenant_xyz")

# 3. Report starting work
report_progress(
    job_id="job-123",
    progress={"mode": "todo", "completed_steps": 0, "total_steps": 5, "current_step": "Starting task"},
    tenant_key="tenant_xyz"
)

# 4. Do work, report progress after each step
# ... implement feature ...
report_progress(
    job_id="job-123",
    progress={"mode": "todo", "completed_steps": 1, "total_steps": 5, "current_step": "Feature implemented"},
    tenant_key="tenant_xyz"
)

# 5. Check for messages between steps
messages = receive_messages(agent_id="agent-456", tenant_key="tenant_xyz")

# 6. Complete job
complete_job(
    job_id="job-123",
    result={"summary": "Feature implemented successfully", "artifacts": ["file1.py"], "status": "completed"},
    tenant_key="tenant_xyz"
)
```

---

**See Also**:
- [Context Tools API](../api/context_tools.md) - Detailed context fetching documentation
- [Orchestrator Documentation](../ORCHESTRATOR.md) - Orchestrator-specific workflows
- [Agent Communication Guide](../guides/agent_communication.md) - Advanced messaging patterns

**Last Updated**: 2025-12-21
