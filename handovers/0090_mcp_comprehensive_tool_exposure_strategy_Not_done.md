# Handover 0090: MCP Comprehensive Tool Exposure & Hybrid Prompt Strategy

**Date**: November 3, 2025
**Author**: Claude Code Session
**Status**: STRATEGY DEFINED
**Impact**: CRITICAL - Enables full orchestration with intelligent tool usage
**Replaces**: Previous 0090_mcp_tool_inventory.md (now includes strategy)

## Executive Summary

This handover defines a comprehensive strategy to expose ALL 90 MCP tools via HTTP while using intelligent prompt templates to guide appropriate tool usage. Rather than limiting tool availability, we control tool usage through orchestrator and agent prompts, creating a flexible yet guided system.

## Strategy Overview

### Core Principles
1. **Expose Everything**: All 90 tools available via MCP HTTP
2. **Fix Data Returns**: Ensure all tools return meaningful data
3. **Guide Through Prompts**: Tool usage controlled by intelligent prompting
4. **Maintain Flexibility**: No artificial limits on tool access
5. **Platform Optimization**: Leverage each platform's strengths

## Current State Analysis

### Tool Availability
- **Total Tools**: 90 across 19 source files
- **Currently HTTP Exposed**: 28 (31%)
- **Need to Expose**: 62 additional tools
- **Data Issues**: ~15 tools return empty/error data

### Tool Categories Requiring Exposure

#### 1. Orchestration Tools (11 tools)
**Source**: `src/giljo_mcp/tools/orchestration.py`
- orchestrate_project
- get_agent_mission
- spawn_agent_job
- get_workflow_status
- get_project_by_alias
- activate_project_mission
- get_launch_prompt
- get_fetch_agents_instructions
- get_update_agents_instructions
- health_check
- get_orchestrator_instructions ✅ (already exposed)

#### 2. Agent Lifecycle Tools (8 tools)
**Source**: `src/giljo_mcp/tools/agent.py`
- ensure_agent
- activate_agent
- assign_job
- handoff
- agent_health
- decommission_agent
- spawn_and_log_sub_agent
- log_sub_agent_completion

#### 3. Agent Coordination Tools (7 tools)
**Source**: `src/giljo_mcp/tools/agent_coordination.py`
- get_pending_jobs
- acknowledge_job
- report_progress
- get_next_instruction
- complete_job
- report_error
- send_message ✅ (already exposed)

#### 4. Agent Communication Tools (3 tools)
**Source**: `src/giljo_mcp/tools/agent_communication.py`
- check_orchestrator_messages
- acknowledge_message ✅ (already exposed)
- report_status

#### 5. Context & Discovery Tools (11 tools)
**Source**: `src/giljo_mcp/tools/context.py`
- get_vision
- discover_context ✅ (already exposed)
- get_file_context ✅ (already exposed)
- search_context ✅ (already exposed)
- index_codebase
- get_dependencies
- get_git_status
- get_recent_changes
- get_test_coverage
- get_performance_metrics
- get_context_summary ✅ (already exposed)

#### 6. Additional Essential Tools
- update_project_mission (for saving orchestrator-created missions)
- broadcast_message (for orchestrator broadcasts)
- get_product_settings (for user priorities)
- complete_orchestrator_job (for closeout)

## Implementation Plan

### Phase 1: Expose All Tools (Immediate)

#### Update `api/endpoints/mcp_http.py`

1. **Expand handle_tools_list()** to include all 90 tools with proper schemas
2. **Expand tool_map** in handle_tools_call() to map all tool functions
3. **Ensure consistent parameter naming** across all tool definitions

```python
# Example additions to handle_tools_list():
{
    "name": "orchestrate_project",
    "description": "Complete project orchestration workflow with 70% token reduction",
    "inputSchema": {
        "type": "object",
        "properties": {
            "project_id": {"type": "string", "description": "Project ID"},
            "tenant_key": {"type": "string", "description": "Tenant isolation key"}
        },
        "required": ["project_id", "tenant_key"]
    }
},
{
    "name": "spawn_agent_job",
    "description": "Spawn agent job with thin client prompt",
    "inputSchema": {
        "type": "object",
        "properties": {
            "agent_type": {"type": "string", "description": "Type of agent"},
            "agent_name": {"type": "string", "description": "Agent name"},
            "mission": {"type": "string", "description": "Agent mission"},
            "project_id": {"type": "string", "description": "Project ID"},
            "tenant_key": {"type": "string", "description": "Tenant key"}
        },
        "required": ["agent_type", "agent_name", "mission", "project_id", "tenant_key"]
    }
}
# ... continue for all 90 tools
```

### Phase 2: Fix Data Returns (Priority)

Based on testing feedback, these tools need data fixes:

1. **get_orchestrator_instructions** - Mission field empty
   - Fix: Ensure product context is loaded
   - Fix: Build mission from project description

2. **list_agents/list_messages/list_tasks** - "Multiple rows found"
   - Fix: Filter for active project only
   - Fix: Add proper tenant + status filtering

3. **Template tools** - Return names but no content
   - Fix: Include template_content field

4. **Context discovery** - Returns empty
   - Fix: Implement actual context gathering

### Phase 3: Hybrid Prompt Strategy

#### Orchestrator Prompt Template

```markdown
I am Orchestrator #[INSTANCE] for [PROJECT_NAME]

IDENTITY:
- Orchestrator ID: [FULL_UUID]
- Project ID: [PROJECT_ID]
- Tenant Key: [TENANT_KEY]

ORCHESTRATION TOOLS (Use these in order):

STAGING PHASE:
1. mcp__giljo-mcp__health_check() - Verify connection
2. mcp__giljo-mcp__get_orchestrator_instructions() - Get project context
3. mcp__giljo-mcp__discover_context() - Analyze all product documentation
4. mcp__giljo-mcp__get_product_settings() - Get user priorities
5. mcp__giljo-mcp__list_templates() - See available agent types
6. mcp__giljo-mcp__update_project_mission() - Save your created mission
7. mcp__giljo-mcp__spawn_agent_job() - Create each agent with their portion

IMPLEMENTATION PHASE (you remain active):
8. mcp__giljo-mcp__check_orchestrator_messages() - Poll every 30-60s
9. mcp__giljo-mcp__send_message() - Route to specific agents
10. mcp__giljo-mcp__broadcast_message() - Message all agents
11. mcp__giljo-mcp__get_workflow_status() - Track progress

CLOSEOUT PHASE:
12. mcp__giljo-mcp__complete_orchestrator_job() - Generate closeout
13. mcp__giljo-mcp__decommission_agent() - Retire agents

Your role: Analyze context, CREATE the mission, spawn agents, coordinate work.
```

#### Agent Prompt Template

```markdown
I am [AGENT_TYPE] Agent for [PROJECT_NAME]

IDENTITY:
- Agent ID: [AGENT_ID]
- Job ID: [JOB_ID]
- Orchestrator: [ORCHESTRATOR_ID]

AGENT TOOLS (Use as needed):

STARTUP:
1. mcp__giljo-mcp__get_agent_mission() - Get your specific mission
2. mcp__giljo-mcp__acknowledge_job() - Mark yourself active

WORKING:
3. mcp__giljo-mcp__report_progress() - Update status regularly
4. mcp__giljo-mcp__send_message() - Communicate with orchestrator
5. mcp__giljo-mcp__check_orchestrator_messages() - Check for instructions

COMPLETION:
6. mcp__giljo-mcp__complete_job() - Mark work complete

DYNAMIC CONTEXT:
[MISSION_PORTION]
[SPECIFIC_TASKS]
[SUCCESS_CRITERIA]
```

### Phase 4: Tool Usage Guidance

#### For Claude Code
- Agent templates include tool lists in `.claude/agents/` files
- Orchestrator template explicitly lists staging vs implementation tools

#### For Codex/Gemini
- Copy-paste prompts include complete tool lists
- Dynamic generation based on agent type and phase

#### Tool Organization (No Renaming Needed)
Tools are naturally organized by usage pattern:
- **orchestrator_** prefix considered but rejected (AI smart enough)
- **Prompt templates** provide the guidance
- **No breaking changes** to existing tool names

## Success Criteria

### Technical Success
- [ ] All 90 tools exposed via MCP HTTP
- [ ] All tools return meaningful data (no empty/errors)
- [ ] Tool schemas properly defined with parameters
- [ ] Multi-tenant isolation maintained

### Usage Success
- [ ] Orchestrator can complete full workflow
- [ ] Agents receive and execute missions
- [ ] Message communication works bidirectionally
- [ ] Project closeout functions properly

### Documentation Success
- [ ] Prompt templates include appropriate tool lists
- [ ] Tool usage is clear from prompts
- [ ] No confusion about which tools to use when

## Testing Plan

### Integration Test Sequence

1. **Orchestrator Staging Test**
```python
# Test orchestrator can:
- Get project context
- Create mission
- Save to database (UI updates)
- Spawn agents
```

2. **Agent Lifecycle Test**
```python
# Test agents can:
- Get their missions
- Acknowledge jobs
- Report progress
- Complete work
```

3. **Communication Test**
```python
# Test bidirectional:
- Orchestrator → Agent messages
- Agent → Orchestrator reports
- Broadcast messages
- Message acknowledgments
```

4. **Closeout Test**
```python
# Test project completion:
- Generate closeout checklist
- Decommission agents
- Update project status
```

## Rollback Plan

If issues occur:
1. Revert `api/endpoints/mcp_http.py` to previous version
2. Restart server
3. Document specific tool that caused issue
4. Fix and redeploy incrementally

## Migration Notes

### No Breaking Changes
- Existing 28 exposed tools remain unchanged
- New tools are additions only
- Tool names remain the same
- Backward compatible

### Database Considerations
- No schema changes required
- Existing data remains valid
- New tools use existing models

## Future Enhancements

1. **Dynamic Tool Discovery**
   - Tools self-register based on decorators
   - Automatic schema generation

2. **Role-Based Tool Access**
   - Orchestrators get orchestration tools
   - Agents get agent tools
   - Admins get all tools

3. **Tool Usage Analytics**
   - Track which tools are used most
   - Identify unused tools
   - Optimize based on patterns

## Related Documentation

- **Handover 0089**: MCP HTTP Tool Catalog Fix (prerequisite)
- **Handover 0091**: MCP Tool Data Integration Fixes (data issues)
- **Simple_Vision.md**: Product vision and workflow
- **Tool Inventory**: Complete list of 90 tools

## Implementation Checklist

### Immediate Actions
- [ ] Update `mcp_http.py` with all 90 tools
- [ ] Fix data return issues (priority: mission, lists, templates)
- [ ] Create orchestrator prompt template
- [ ] Create agent prompt templates

### Testing Actions
- [ ] Test orchestrator full workflow
- [ ] Test agent lifecycle
- [ ] Test message communication
- [ ] Test project closeout

### Documentation Actions
- [ ] Update orchestrator launch prompt
- [ ] Update agent templates
- [ ] Document tool usage patterns
- [ ] Create troubleshooting guide

## Summary

This comprehensive strategy exposes all 90 MCP tools while maintaining control through intelligent prompting. The hybrid approach leverages platform strengths (Claude's sub-agents, Codex/Gemini's multi-terminal) while ensuring all tools work correctly and return meaningful data.

The key insight: **Tools don't need to be hidden, they need to be guided**. By providing clear tool lists in prompts, we enable powerful orchestration while preventing confusion.

**Next Step**: Implement Phase 1 (expose all tools) and Phase 2 (fix data returns) immediately.

---

**Document Version**: 2.0
**Previous Version**: 1.0 (tool inventory only)
**Last Updated**: 2025-11-03
**Status**: Ready for Implementation