# Context Tools API - DEPRECATED

**Status:** ❌ DEPRECATED as of v3.2 (Handover 0280-0281)

The individual `fetch_*` context tools have been replaced with monolithic context architecture.

## Migration Guide

**Old Approach (v3.1 and earlier):**
```python
vision = await fetch_vision_document(product_id, tenant_key, chunking='moderate')
memory = await fetch_360_memory(product_id, tenant_key, last_n_projects=3)
git = await fetch_git_history(product_id, tenant_key, commits=25)
```

**New Approach (v3.2+):**
```python
mission = await get_orchestrator_instructions(orchestrator_id, tenant_key)
# Returns complete prioritized context in one call
```

## Why This Change?

The individual `fetch_*` tools had several limitations:

1. **Token Inefficiency**: Orchestrators had to call 9+ separate tools (3,500+ tokens)
2. **Context Fragmentation**: Each tool returned data in isolation
3. **Priority Configuration Complexity**: User had to configure 9 separate priorities
4. **Maintenance Burden**: 9 separate tools with overlapping functionality

## What Replaced Them?

**Monolithic Context Architecture (Handover 0280)**:

- Single MCP tool: `get_orchestrator_instructions(orchestrator_id, tenant_key)`
- Returns complete context in one call (~450-550 tokens vs 3,500)
- User priorities automatically applied server-side
- Depth configuration integrated
- 85% token reduction

## Timeline

- **v3.1 and earlier**: Individual `fetch_*` tools active
- **v3.2 (Nov 2025)**: Monolithic context architecture introduced (Handover 0280)
- **v3.2.1 (Dec 2025)**: Individual `fetch_*` tools removed (Handover 0281)
- **v4.0 (Future)**: Cleanup complete, documentation archived

## Deprecated Tools

All of these tools have been removed:

1. ❌ `fetch_product_context` - Product vision, architecture, tech stack
2. ❌ `fetch_vision_document` - Vision document chunks
3. ❌ `fetch_tech_stack` - Technology stack configuration
4. ❌ `fetch_architecture` - Architecture configuration
5. ❌ `fetch_testing_config` - Testing strategy and quality standards
6. ❌ `fetch_360_memory` - Sequential project history
7. ❌ `fetch_git_history` - Aggregated git commits
8. ❌ `fetch_agent_templates` - Agent template library
9. ❌ `fetch_project_context` - Current project metadata

## Current MCP Tools (v3.2+)

### Orchestration Tools
- `get_orchestrator_instructions()` - Fetch complete context for orchestrator
- `spawn_agent_job()` - Create agent job and return thin prompt
- `get_workflow_status()` - Monitor spawned agents

### Context Tools
- `get_agent_mission()` - Fetch agent-specific mission
- `get_available_agents()` - Discover available specialist agents

### Communication Tools
- `send_message()` - Send message to specific agent
- `broadcast_message()` - Send message to all agents
- `get_messages()` - Fetch messages sent to agent
- `acknowledge_message()` - Mark message as read

### Task Tools
- `update_job_progress()` - Update agent job progress
- `complete_agent_job()` - Mark agent job as complete
- `report_job_error()` - Report error or blocker
- `get_job_status()` - Fetch detailed agent job status

### Project Tools
- `update_project_mission()` - Update project mission
- `get_project_context()` - Fetch project metadata
- `activate_project()` - Activate project for orchestration
- `close_project()` - Close project and update 360-memory
- `get_project_members()` - Get list of all agents assigned to project

## See Also

- [Handover 0280: Monolithic Context Architecture Roadmap](../../handovers/0280_monolithic_context_architecture_roadmap.md)
- [Handover 0281: Complete fetch_* Tool Cleanup](../../handovers/0281_complete_fetch_tools_cleanup.md)
- [Orchestrator Documentation](../ORCHESTRATOR.md)
- [MCP Tools Catalog](../components/MCP_TOOLS_CATALOG.md)
