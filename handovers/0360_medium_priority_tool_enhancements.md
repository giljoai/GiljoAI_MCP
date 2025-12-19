# Handover 0360: Medium-Priority Tool Enhancements

**Date**: 2025-12-19
**Status**: READY FOR IMPLEMENTATION
**Priority**: Medium
**Type**: MCP Tool Enhancement
**Estimated Effort**: 4-5 hours
**Related Issues**: #10 (message filtering), #11 (agent discovery), #14 (file_exists utility)

---

## Executive Summary

**Problem**

Alpha trial agents identified three useful tool enhancements that would improve agent coordination and workflow efficiency:

1. **Issue #10**: Agents receive their own progress messages in `receive_messages()` output, creating noise
2. **Issue #11**: No convenient tool to discover teammate agents in the current project
3. **Issue #14**: Missing `file_exists` utility for safe file operations

**Goal**

Add message filtering capabilities, team discovery tool, and file existence checking to improve agent ergonomics without breaking existing functionality.

**Approach**

Enhance existing MCP tools with backward-compatible optional parameters:
- Add filtering parameters to `receive_messages()`
- Create new `get_team_agents()` tool
- Add `file_exists()` utility tool

---

## Context

### Alpha Trial Feedback

During alpha testing, agents reported:

1. **Message Noise**: When using `receive_messages()`, agents saw their own progress reports in the queue, requiring manual filtering
2. **Team Blindness**: Agents spawned by orchestrator had no easy way to discover their teammates without parsing project status
3. **File Safety**: Agents wanted to check file existence before operations to avoid errors

### Current Behavior

**receive_messages() - MessageService**
- Location: `src/giljo_mcp/services/message_service.py` lines 488-652
- Returns all pending messages for an agent
- Already excludes sender from broadcasts (Issue 0361-3, Handover 0362)
- No filtering by message source or type
- Auto-acknowledges retrieved messages (Handover 0326)

**Agent Discovery**
- `get_available_agents()` exists in `agent_discovery.py` but returns template catalog, not active team
- No tool to list active agents in current project
- Orchestrator knows team via `orchestrate_project` staging but agents don't

**File Operations**
- No file existence check tool
- Agents use Read tool and handle errors
- Would benefit from lightweight check before operations

---

## Problem Statement

### Issue #10: Message Self-Delivery

**Current State**:
```python
# Agent calls receive_messages()
result = await receive_messages(agent_id="abc123")

# Returns ALL messages including own progress reports:
{
    "messages": [
        {"from_agent": "abc123", "content": "Progress: 50%"},  # OWN MESSAGE (noise)
        {"from_agent": "orchestrator", "content": "Task assigned"},  # WANTED
        {"from_agent": "analyzer", "content": "Ready for review"}  # WANTED
    ]
}
```

**Problem**: Agents must manually filter their own messages, adding complexity.

**Root Cause**: `receive_messages()` uses JSONB containment query that includes messages where `from_agent` matches current agent's type.

### Issue #11: No Team Discovery

**Current State**:
```python
# Agent wants to know teammates - NO DIRECT WAY
# Option 1: Parse project_status() output (heavyweight)
# Option 2: Manually track spawned_by chain (complex)
# Option 3: Hope orchestrator told them in mission text
```

**Problem**: Agents can't easily enumerate active teammates for coordination.

**Use Cases**:
- Documenter wants to know if implementer exists before requesting code review
- Tester wants to list all agents to broadcast test results
- Analyzer wants to coordinate with peer specialists

### Issue #14: File Existence Checking

**Current State**:
```python
# Agent wants to check if file exists - must use Read and handle error
try:
    await read_file(path)
    # File exists but we just read whole file (wasteful)
except:
    # File doesn't exist
```

**Problem**: No lightweight way to check file existence without reading content.

---

## Investigation Findings

### Message Filtering Analysis

**Current Query** (message_service.py line 550-571):
```python
query = select(Message).where(
    and_(
        Message.tenant_key == tenant_key,
        Message.project_id == job.project_id,
        Message.status == "pending",
        or_(
            # Direct message: JSONB array contains agent_id
            func.cast(Message.to_agents, JSONB).op('@>')(func.cast([agent_id], JSONB)),
            # Broadcast: exclude sender (already implemented)
            and_(
                func.cast(Message.to_agents, JSONB).op('@>')(func.cast(['all'], JSONB)),
                func.coalesce(Message.meta_data.op('->')('_from_agent').astext, func.cast('', String)) != job.agent_type
            )
        )
    )
)
```

**Key Insights**:
1. Broadcast sender exclusion already works (Handover 0362)
2. Direct message filtering needs enhancement
3. `meta_data._from_agent` contains sender identifier
4. Can add WHERE clause to exclude self

### Agent Team Discovery

**Relevant Models**:
- `MCPAgentJob` (agents.py lines 27-220): Contains `project_id`, `agent_type`, `status`, `job_id`
- Indexes available: `idx_mcp_agent_jobs_project` (line 200)

**Query Pattern**:
```python
# Get all active agents in project
query = select(MCPAgentJob).where(
    and_(
        MCPAgentJob.project_id == project_id,
        MCPAgentJob.tenant_key == tenant_key,
        MCPAgentJob.status.in_(["waiting", "working", "blocked"])  # Active states
    )
)
```

### File Existence Tool

**Considerations**:
- Should use `pathlib.Path.exists()` for cross-platform compatibility
- Must handle relative vs absolute paths
- Should respect codebase directory boundaries
- Minimal implementation (no file metadata beyond existence)

---

## Implementation Plan

### Enhancement 1: Message Filtering (receive_messages)

**Location**: `src/giljo_mcp/services/message_service.py` line 488

**Changes**:
```python
async def receive_messages(
    self,
    agent_id: str,
    limit: int = 10,
    tenant_key: Optional[str] = None,
    exclude_self: bool = True,  # NEW: Filter own messages
    exclude_progress: bool = False,  # NEW: Filter progress-type messages
    from_agent: Optional[str] = None,  # NEW: Only messages from specific agent
) -> dict[str, Any]:
    """
    Receive pending messages for an agent by job_id.

    Args:
        agent_id: Agent job ID
        limit: Maximum number of messages to retrieve (default: 10)
        tenant_key: Optional tenant key (uses current if not provided)
        exclude_self: Filter out messages from self (default: True)
        exclude_progress: Filter out progress-type messages (default: False)
        from_agent: Only return messages from this agent (default: None = all)

    Returns:
        Dict with success status and list of messages or error
    """
```

**Query Modifications**:
```python
# After existing query setup, add filters:

# Filter 1: Exclude self (if enabled)
if exclude_self:
    query = query.where(
        func.coalesce(
            Message.meta_data.op('->')('_from_agent').astext,
            func.cast('', String)
        ) != job.agent_type
    )

# Filter 2: Exclude progress messages (if enabled)
if exclude_progress:
    query = query.where(Message.message_type != "progress")

# Filter 3: From specific agent (if specified)
if from_agent:
    query = query.where(
        func.coalesce(
            Message.meta_data.op('->')('_from_agent').astext,
            func.cast('', String)
        ) == from_agent
    )
```

**Backward Compatibility**:
- Default `exclude_self=True` matches expected behavior (agents don't want own messages)
- Existing callers get improved behavior automatically
- Can opt-out with `exclude_self=False` if needed

### Enhancement 2: Team Discovery Tool (get_team_agents)

**Location**: New tool in `src/giljo_mcp/tools/orchestration.py`

**Implementation**:
```python
@mcp.tool()
async def get_team_agents(
    project_id: str,
    tenant_key: str,
    include_completed: bool = False,
    include_self: bool = True,
) -> dict[str, Any]:
    """
    Get list of active agent teammates in the current project.

    This tool enables agents to discover their teammates for coordination,
    messaging, and dependency tracking.

    Args:
        project_id: Project ID to query
        tenant_key: Tenant key for multi-tenant isolation
        include_completed: Include completed/failed agents (default: False)
        include_self: Include calling agent in results (default: True)

    Returns:
        Dictionary containing:
        - agents: List of agent objects with job_id, agent_type, status, progress
        - count: Total number of agents
        - project_id: Project ID queried

    Example:
        {
            "success": True,
            "project_id": "abc-123",
            "count": 3,
            "agents": [
                {
                    "job_id": "job-001",
                    "agent_type": "orchestrator",
                    "agent_name": "Project Orchestrator",
                    "status": "working",
                    "progress": 100,
                    "current_task": "Monitoring team progress"
                },
                {
                    "job_id": "job-002",
                    "agent_type": "analyzer",
                    "agent_name": "Code Analyzer",
                    "status": "working",
                    "progress": 75,
                    "current_task": "Analyzing module dependencies"
                }
            ]
        }
    """
    try:
        async with db_manager.get_session_async() as session:
            # Verify project exists with tenant isolation
            result = await session.execute(
                select(Project).where(
                    Project.id == project_id,
                    Project.tenant_key == tenant_key
                )
            )
            project = result.scalar_one_or_none()

            if not project:
                return {
                    "success": False,
                    "error": f"Project {project_id} not found"
                }

            # Build query for active agents
            if include_completed:
                status_filter = MCPAgentJob.status.in_([
                    "waiting", "working", "blocked",
                    "complete", "failed", "cancelled"
                ])
            else:
                status_filter = MCPAgentJob.status.in_([
                    "waiting", "working", "blocked"
                ])

            query = select(MCPAgentJob).where(
                and_(
                    MCPAgentJob.project_id == project_id,
                    MCPAgentJob.tenant_key == tenant_key,
                    status_filter
                )
            ).order_by(MCPAgentJob.created_at)

            result = await session.execute(query)
            agents = result.scalars().all()

            # Format response
            agent_list = []
            for agent in agents:
                agent_list.append({
                    "job_id": agent.job_id,
                    "agent_type": agent.agent_type,
                    "agent_name": agent.agent_name or agent.agent_type.title(),
                    "status": agent.status,
                    "progress": agent.progress or 0,
                    "current_task": agent.current_task,
                    "spawned_by": agent.spawned_by,
                })

            logger.info(
                f"Retrieved {len(agent_list)} team agents for project {project_id}"
            )

            return {
                "success": True,
                "project_id": project_id,
                "count": len(agent_list),
                "agents": agent_list,
            }

    except Exception as e:
        logger.exception(f"Failed to get team agents: {e}")
        return {"success": False, "error": str(e)}
```

**Registration**: Add to orchestration tools registration in `orchestration.py`

### Enhancement 3: File Exists Utility (file_exists)

**Location**: New tool in `src/giljo_mcp/tools/orchestration.py` or new `utils.py`

**Implementation**:
```python
@mcp.tool()
async def file_exists(
    file_path: str,
    working_directory: Optional[str] = None,
) -> dict[str, Any]:
    """
    Check if a file or directory exists.

    This utility enables safe file operations by checking existence
    before attempting reads/writes.

    Args:
        file_path: Path to check (absolute or relative)
        working_directory: Base directory for relative paths (default: cwd)

    Returns:
        Dictionary containing:
        - exists: Boolean indicating if path exists
        - path: Resolved absolute path that was checked
        - is_file: True if exists and is a file
        - is_dir: True if exists and is a directory

    Example:
        >>> result = await file_exists("src/main.py")
        {
            "success": True,
            "exists": True,
            "path": "/absolute/path/to/src/main.py",
            "is_file": True,
            "is_dir": False
        }
    """
    try:
        from pathlib import Path

        # Resolve path
        if working_directory:
            base = Path(working_directory)
            path = base / file_path
        else:
            path = Path(file_path)

        # Resolve to absolute path
        path = path.resolve()

        # Check existence
        exists = path.exists()

        return {
            "success": True,
            "exists": exists,
            "path": str(path),
            "is_file": path.is_file() if exists else False,
            "is_dir": path.is_dir() if exists else False,
        }

    except Exception as e:
        logger.exception(f"Failed to check file existence: {e}")
        return {
            "success": False,
            "error": str(e),
            "exists": False,
        }
```

---

## Files to Modify

### Core Service Layer

**File**: `src/giljo_mcp/services/message_service.py`
- **Lines**: 488-652 (receive_messages method)
- **Changes**:
  - Add 3 new parameters: `exclude_self`, `exclude_progress`, `from_agent`
  - Add WHERE clause filters based on parameters
  - Update docstring with parameter descriptions
  - Add unit tests for filtering behavior

### MCP Tools

**File**: `src/giljo_mcp/tools/orchestration.py`
- **Location**: After existing tools (around line 1000+)
- **Changes**:
  - Add `get_team_agents()` tool function
  - Add `file_exists()` tool function
  - Register both tools in MCP server initialization
  - Add integration tests

### Tool Accessor (if needed)

**File**: `src/giljo_mcp/tools/tool_accessor.py`
- **Lines**: 257-259 (receive_messages wrapper)
- **Changes**:
  - Update wrapper to pass new parameters through
  - Maintain backward compatibility

---

## Testing Strategy

### Unit Tests

**File**: `tests/services/test_message_service_filtering.py` (NEW)
```python
class TestMessageFiltering:
    async def test_exclude_self_filters_own_messages(self, session):
        """Verify exclude_self removes messages from calling agent"""

    async def test_exclude_progress_filters_progress_type(self, session):
        """Verify exclude_progress removes progress messages"""

    async def test_from_agent_filters_by_sender(self, session):
        """Verify from_agent only returns messages from specific agent"""

    async def test_combined_filters_work_together(self, session):
        """Verify multiple filters can be used simultaneously"""

    async def test_backward_compatibility_default_behavior(self, session):
        """Verify default behavior matches expected filtering"""
```

**File**: `tests/tools/test_team_discovery.py` (NEW)
```python
class TestTeamDiscovery:
    async def test_get_team_agents_basic(self, session):
        """Verify basic team enumeration works"""

    async def test_get_team_agents_filters_completed(self, session):
        """Verify include_completed parameter works"""

    async def test_get_team_agents_tenant_isolation(self, session):
        """Verify multi-tenant isolation is enforced"""

    async def test_get_team_agents_empty_project(self, session):
        """Verify graceful handling of projects with no agents"""
```

**File**: `tests/tools/test_file_utils.py` (NEW)
```python
class TestFileExists:
    async def test_file_exists_returns_true_for_existing_file(self):
        """Verify exists=True for real files"""

    async def test_file_exists_returns_false_for_missing_file(self):
        """Verify exists=False for missing files"""

    async def test_file_exists_distinguishes_file_vs_directory(self):
        """Verify is_file vs is_dir flags work correctly"""

    async def test_file_exists_resolves_relative_paths(self):
        """Verify relative path resolution with working_directory"""
```

### Integration Tests

**File**: `tests/integration/test_agent_coordination.py`
```python
async def test_message_filtering_in_multi_agent_scenario():
    """
    Full workflow test:
    1. Orchestrator spawns 3 agents
    2. Each agent sends progress messages
    3. Orchestrator broadcasts task
    4. Each agent receives_messages with exclude_self=True
    5. Verify no agent sees their own messages
    """

async def test_team_discovery_workflow():
    """
    Full workflow test:
    1. Orchestrator spawns analyzer, implementer, tester
    2. Each agent calls get_team_agents()
    3. Verify each sees the other 3 agents
    4. Verify status/progress fields are accurate
    """
```

### Manual Testing

**Scenario 1: Message Filtering**
1. Create project with orchestrator + 2 specialists
2. Have orchestrator broadcast "Task assigned"
3. Have each specialist send progress message
4. Call `receive_messages(agent_id=specialist1, exclude_self=True)`
5. Verify specialist1 sees orchestrator message but not own progress

**Scenario 2: Team Discovery**
1. Create project with orchestrator + analyzer + documenter
2. From documenter agent, call `get_team_agents(project_id, tenant_key)`
3. Verify response includes all 3 agents
4. Verify job_id, agent_type, status fields are correct

**Scenario 3: File Exists**
1. Call `file_exists("src/giljo_mcp/app.py")`
2. Verify returns `exists=True, is_file=True`
3. Call `file_exists("nonexistent.txt")`
4. Verify returns `exists=False`

---

## Success Criteria

### Message Filtering
- [ ] `receive_messages()` accepts new optional parameters
- [ ] `exclude_self=True` removes messages from calling agent
- [ ] `exclude_progress=True` removes progress-type messages
- [ ] `from_agent="orchestrator"` only returns orchestrator messages
- [ ] Default behavior (`exclude_self=True`) works without breaking existing code
- [ ] All unit tests pass (>80% coverage)

### Team Discovery
- [ ] `get_team_agents()` tool registered and callable
- [ ] Returns accurate list of active agents in project
- [ ] Enforces multi-tenant isolation (tenant_key filter)
- [ ] `include_completed` parameter controls status filter
- [ ] Returns useful fields: job_id, agent_type, status, progress
- [ ] Integration test validates multi-agent scenario

### File Exists
- [ ] `file_exists()` tool registered and callable
- [ ] Correctly identifies existing files (`exists=True`)
- [ ] Correctly identifies missing files (`exists=False`)
- [ ] Distinguishes files from directories (`is_file` vs `is_dir`)
- [ ] Resolves relative paths when `working_directory` provided
- [ ] Handles errors gracefully (invalid paths, permissions)

### Documentation
- [ ] Tool docstrings include all parameters and examples
- [ ] MCP tool schema updated (auto-generated from FastMCP)
- [ ] Integration examples added to agent templates (optional)
- [ ] Handover document committed with implementation notes

---

## Migration Notes

### Backward Compatibility

**receive_messages**:
- New parameters are optional with sensible defaults
- Default `exclude_self=True` improves existing behavior (agents already don't want own messages)
- Existing callers get automatic improvement
- Can opt-out if needed: `exclude_self=False`

**get_team_agents**:
- Entirely new tool, no breaking changes
- May want to add to agent template examples (see Handover 0353)

**file_exists**:
- Entirely new tool, no breaking changes
- Complements existing Read/Write tools

### Deprecation

**None**: No existing tools are being removed or deprecated.

---

## Related Handovers

- **0362**: WebSocket Message Counter Fixes - Fixed sender self-notification in broadcasts
- **0353**: Agent Team Awareness - Proposes mission-based team context (complements get_team_agents)
- **0326**: Auto-Acknowledge Messages - Established auto-ack behavior in receive_messages
- **0325**: Tenant Isolation in Message Service - Established tenant_key filtering pattern

---

## Future Enhancements

### Phase 2 (Out of Scope)

1. **Message Search/History**: Add `search_messages()` with full-text search
2. **Agent Status Subscribe**: WebSocket subscription to teammate status updates
3. **File Utilities**: Expand with `list_directory()`, `get_file_info()`, etc.
4. **Team Metrics**: Add `get_team_metrics()` for project health dashboard

---

## Commit Strategy

**Recommended Commits**:
1. `feat(messaging): Add message filtering to receive_messages (Issue #10)`
2. `feat(coordination): Add get_team_agents tool (Issue #11)`
3. `feat(utils): Add file_exists utility tool (Issue #14)`
4. `test(services): Add message filtering test coverage`
5. `test(tools): Add team discovery and file utils tests`
6. `docs(handover): Complete handover 0360 with implementation notes`

---

## Notes for Implementer

### Key Considerations

1. **SQL Performance**: The JSONB filtering in receive_messages may impact query performance at scale. Consider adding index on `Message.meta_data->>'_from_agent'` if needed.

2. **Tool Registration**: Both new tools should be registered in `orchestration.py` alongside existing coordination tools for consistency.

3. **Error Handling**: All three enhancements should gracefully handle edge cases:
   - Empty projects (no agents)
   - Missing meta_data fields
   - Invalid file paths

4. **Multi-Tenant**: Ensure all queries include tenant_key filter to prevent cross-tenant data leaks.

5. **Agent Template Updates**: Consider updating agent templates (via Handover 0353) to mention these new tools in coordination examples.

### Development Order

Recommended implementation sequence:
1. **Message filtering** (smallest change, highest impact)
2. **Team discovery** (medium complexity, enables coordination patterns)
3. **File exists** (simple utility, nice-to-have)

### Testing Notes

- Use existing test fixtures from `tests/conftest.py` for session management
- Follow test patterns from `test_message_service_contract.py` for service tests
- Integration tests should create real MCPAgentJob records for authenticity

---

## Approval

**Ready for Implementation**: YES
**Blockers**: None
**Dependencies**: None (all changes are isolated enhancements)
**Breaking Changes**: None (backward compatible)

This handover can be implemented independently without coordination with other ongoing work.
