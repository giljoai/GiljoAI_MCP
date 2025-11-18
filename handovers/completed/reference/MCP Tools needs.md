# MCP Tool Inventory - GiljoAI Agent Orchestration System

**Date**: 2025-11-03
**Status**: Complete
**Purpose**: Comprehensive inventory of all MCP tools in the GiljoAI system

---

## Executive Summary

**Total Tool Count**: 90 MCP tools
**HTTP Exposed**: 28 tools (31%)
**Tool Categories**: 19 source files
**Architecture**: Multi-tenant with orchestration focus

The GiljoAI MCP server provides 90 production-grade tools across 19 categories, enabling multi-agent orchestration with context prioritization and orchestration through thin client architecture. Tools are organized by functional domain with comprehensive multi-tenant isolation.

---

## Tool Exposure Status

### HTTP Exposed Tools (28 tools)
These tools are accessible via REST API endpoints for external agents:

**Source**: `api/endpoints/mcp_tools.py` (lines 59-98)


##### MUST KEEP ORCHESTRATOR TOOLS
#### Project Management (5 tools)
- create_project ✅Only needed if user specifically asks orchestrator to create a new project to extend on someting
- list_projects ✅ Only needed if orchestrator it need to reference a prior project for context? 
- get_project ✅Needed during startup and [staging prompt] creation, should link to [Context discovery tools below]
- switch_project ✅ not needed, we work on one project at a time
- close_project ✅Needed when project is finished, should instruction closeout procedures

#### Agent Orchestration (5 tools)
- spawn_agent ✅Needed  to spawn a new agent
- list_agents ✅Needed to see what agents are available
- get_agent_status ✅Check in on agent status
- update_agent ✅Unsure, needs discussion
- retire_agent ✅Needed when an agent gets closed out and also for project closeout procedures

#### Message Queue (4 tools)
- send_message ✅Needed for agents to communciate
- receive_messages ✅Needed to read messages (need help with purpose)
- acknowledge_message ✅Needed to ack they have read the message
- list_messages ✅See what messages are waiting, queued

#### Task Management (5 tools)
- create_task ✅should be a slash command for user in CLI terminal, not for agents.
- list_tasks ✅ - depreciate
- update_task ✅ - depreciate
- assign_task ✅ - depreciate
- complete_task ✅ - depreciate

#### Template Management (4 tools) Dev question: What are templates
- list_templates ✅
- get_template ✅
- create_template ✅
- update_template ✅

#### Context Discovery (4 tools)
- discover_context ✅
- get_file_context ✅
- search_context ✅
- get_context_summary ✅

**Note**: External coordination tools (`agent_coordination_external.py`) use HTTP client internally but are not directly exposed endpoints.

---

## Complete Tool Catalog

### 1. Orchestration Tools (11 tools)
**Source**: `src/giljo_mcp/tools/orchestration.py`

1. **orchestrate_project** ❌
   - Complete project orchestration workflow with context prioritization and orchestration
   - Parameters: project_id, tenant_key
   - Returns: mission_plan, selected_agents, spawned_jobs, workflow_result

2. **get_agent_mission** ❌
   - Fetch agent-specific mission (Thin Client Architecture)
   - Parameters: agent_job_id, tenant_key
   - Returns: mission, project_context, estimated_tokens

3. **spawn_agent_job** ❌
   - Spawn agent job with thin client prompt (~10 lines)
   - Parameters: agent_type, agent_name, mission, project_id, tenant_key, parent_job_id
   - Returns: agent_job_id, agent_prompt, prompt_tokens, mission_tokens

4. **get_workflow_status** ❌
   - Get current workflow status for project
   - Parameters: project_id, tenant_key
   - Returns: active_agents, completed_agents, failed_agents, progress_percent

5. **get_project_by_alias** ❌
   - Fetch project details using 6-character alias
   - Parameters: alias
   - Returns: project details with tenant isolation

6. **activate_project_mission** ❌
   - Activate project and create mission plan
   - Parameters: alias
   - Returns: activation status and launch instructions

7. **get_launch_prompt** ❌
   - Generate orchestration launch instructions
   - Parameters: alias
   - Returns: formatted launch instructions

8. **get_fetch_agents_instructions** ❌
   - Generate instructions for installing agent templates
   - Parameters: None
   - Returns: installation instructions

9. **get_update_agents_instructions** ❌
   - Generate instructions for updating agent templates
   - Parameters: None
   - Returns: update instructions

10. **health_check** ❌
    - MCP server health check
    - Parameters: None
    - Returns: status, server, version, timestamp

11. **get_orchestrator_instructions** ❌
    - Fetch orchestrator mission with context prioritization and orchestration (Handover 0088)
    - Parameters: orchestrator_id, tenant_key
    - Returns: condensed mission, context_budget, agent_templates, field_priorities

---

### 2. Agent Lifecycle Tools (8 tools)
**Source**: `src/giljo_mcp/tools/agent.py`

1. **ensure_agent** ❌
   - Ensure agent exists (creates if needed, idempotent)
   - Parameters: project_id, agent_name, mission
   - Returns: agent details and creation status

2. **activate_agent** ❌
   - Activate orchestrator agent (starts working immediately)
   - Parameters: project_id, agent_name, mission
   - Returns: activation status and workflow details

3. **assign_job** ❌
   - Assign job to agent with tasks and scope
   - Parameters: agent_name, job_type, project_id, tasks, scope_boundary, vision_alignment
   - Returns: job assignment details

4. **handoff** ❌
   - Transfer work from one agent to another
   - Parameters: from_agent, to_agent, project_id, context
   - Returns: handoff confirmation

5. **agent_health** ❌
   - Check agent health and context usage
   - Parameters: agent_name (optional)
   - Returns: health status and metrics

6. **decommission_agent** ❌
   - Gracefully end agent's work
   - Parameters: agent_name, project_id, reason
   - Returns: decommission confirmation

7. **spawn_and_log_sub_agent** ❌
   - Log spawning of native Claude Code sub-agent
   - Parameters: project_id, parent_agent_name, sub_agent_name, mission, meta_data
   - Returns: interaction_id for tracking

8. **log_sub_agent_completion** ❌
   - Log completion of sub-agent task
   - Parameters: interaction_id, result, tokens_used, error_message, meta_data
   - Returns: completion details with duration

---

### 3. Agent Coordination Tools (7 tools)
**Source**: `src/giljo_mcp/tools/agent_coordination.py`

**Note**: These are internal coordination tools registered in a dictionary, not using @mcp.tool() decorator.

1. **get_pending_jobs** ❌
   - Get pending jobs assigned to agent type
   - Parameters: agent_type, tenant_key
   - Returns: jobs list with context chunks

2. **acknowledge_job** ❌
   - Claim a job (pending → active)
   - Parameters: job_id, agent_id, tenant_key
   - Returns: job details with next instructions

3. **report_progress** ❌
   - Report incremental progress on active job
   - Parameters: job_id, completed_todo, files_modified, context_used, tenant_key
   - Returns: continue status with warnings

4. **get_next_instruction** ❌
   - Check for new instructions or handoff requests
   - Parameters: job_id, agent_type, tenant_key
   - Returns: instructions list, handoff_requested flag

5. **complete_job** ❌
   - Mark job as completed with results
   - Parameters: job_id, result, tenant_key
   - Returns: completion confirmation, next_job info

6. **report_error** ❌
   - Report error and pause job for review
   - Parameters: job_id, error_type, error_message, context, tenant_key
   - Returns: error acknowledgment with recovery instructions

7. **send_message** ❌
   - Send message to another agent (inter-agent communication)
   - Parameters: job_id, to_agent, message, tenant_key, priority
   - Returns: message_id confirmation

---

### 4. External Agent Coordination Tools (7 tools)
**Source**: `src/giljo_mcp/tools/agent_coordination_external.py`

**Note**: HTTP-based tools for external agents (Claude Code, Codex, Gemini CLI)

1. **create_agent_job_external** ❌
   - Create new agent job via POST /api/agent-jobs
   - Parameters: agent_type, mission, context_chunks, spawned_by
   - Returns: job_id with JWT authentication

2. **send_agent_message_external** ❌
   - Send message to agent job via POST /api/agent-jobs/{job_id}/messages
   - Parameters: job_id, role, message_type, content
   - Returns: message_id with timestamp

3. **get_agent_job_status_external** ❌
   - Get agent job status via GET /api/agent-jobs/{job_id}
   - Parameters: job_id
   - Returns: full job details with messages

4. **acknowledge_agent_job_external** ❌
   - Acknowledge job via POST /api/agent-jobs/{job_id}/acknowledge
   - Parameters: job_id
   - Returns: updated job status (active)

5. **complete_agent_job_external** ❌
   - Complete job via POST /api/agent-jobs/{job_id}/complete
   - Parameters: job_id, result
   - Returns: completion confirmation

6. **fail_agent_job_external** ❌
   - Fail job via POST /api/agent-jobs/{job_id}/fail
   - Parameters: job_id, error
   - Returns: failure acknowledgment

7. **list_active_agent_jobs_external** ❌
   - List active jobs via GET /api/agent-jobs
   - Parameters: status, agent_type, limit
   - Returns: jobs list with tenant filtering

---

### 5. Agent Job Status Tools (1 tool)
**Source**: `src/giljo_mcp/tools/agent_job_status.py`

1. **update_job_status** ❌
   - Update job status for Kanban board navigation (Handover 0066)
   - Parameters: job_id, tenant_key, new_status, reason
   - Valid statuses: pending, active, completed, blocked
   - Returns: old/new status with timestamps

---

### 6. Agent Messaging Tools (3 tools)
**Source**: `src/giljo_mcp/tools/agent_messaging.py`

**Note**: Uses @server.tool() decorator

1. **send_mcp_message_tool** ❌
   - Send message through message center
   - Parameters: job_id, tenant_key, content, target, agent_id
   - Targets: orchestrator, broadcast, agent
   - Returns: message_id with broadcast_count

2. **read_mcp_messages_tool** ❌
   - Read messages from agent's message queue
   - Parameters: job_id, tenant_key, unread_only, limit, mark_as_read
   - Returns: messages list with unread_count

**Note**: Internal functions send_mcp_message() and read_mcp_messages() provide core functionality.

---

### 7. Agent Status Tools (2 tools)
**Source**: `src/giljo_mcp/tools/agent_status.py`

**Note**: Uses @server.tool() decorator

1. **set_agent_status_tool** ❌
   - Update agent job status with progress tracking
   - Parameters: job_id, tenant_key, status, progress, reason, current_task, estimated_completion
   - Valid statuses: waiting, preparing, working, review, complete, failed, blocked
   - Returns: old/new status with message

**Note**: Internal function set_agent_status() provides core functionality.

---

### 8. Agent Communication Tools (3 tools)
**Source**: `src/giljo_mcp/tools/agent_communication.py`

1. **check_orchestrator_messages** ❌
   - Check for messages from orchestrator (30-60s polling)
   - Parameters: job_id, tenant_key, agent_name, message_type, unread_only
   - Returns: message_count with formatted messages

2. **acknowledge_message** ❌
   - Acknowledge receipt of message
   - Parameters: job_id, tenant_key, message_id, agent_id, response_data
   - Returns: acknowledgment details with timestamp

3. **report_status** ❌
   - Report agent status and progress to orchestrator
   - Parameters: job_id, tenant_key, status, current_task, progress_percentage, context_usage, artifacts_created, metadata
   - Returns: updated job status

---

### 9. Context & Discovery Tools (11 tools)
**Source**: `src/giljo_mcp/tools/context.py`

1. **get_vision** ❌
   - Get vision document (chunked if large)
   - Parameters: part, max_tokens, force_reindex
   - Returns: vision content with chunking metadata

2. **discover_context** ❌
   - Discover project context and structure
   - Parameters: path, max_depth, file_types
   - Returns: project structure tree

3. **get_file_context** ❌
   - Get context for specific file
   - Parameters: file_path, include_neighbors
   - Returns: file content with metadata

4. **search_context** ❌
   - Search project context
   - Parameters: query, file_types, max_results
   - Returns: search results with relevance

5. **index_codebase** ❌
   - Index codebase for faster searches
   - Parameters: force_reindex
   - Returns: indexing status

6. **get_dependencies** ❌
   - Get project dependencies
   - Parameters: None
   - Returns: dependency list

7. **get_git_status** ❌
   - Get Git repository status
   - Parameters: None
   - Returns: branch, changes, commits

8. **get_recent_changes** ❌
   - Get recent file changes
   - Parameters: days, limit
   - Returns: changed files list

9. **get_test_coverage** ❌
   - Get test coverage metrics
   - Parameters: None
   - Returns: coverage percentages

10. **get_performance_metrics** ❌
    - Get application performance metrics
    - Parameters: None
    - Returns: performance data

11. **get_context_summary** ❌
    - Get condensed summary of project context
    - Parameters: None
    - Returns: summary with key facts

---

### 10. Message Communication Tools (6 tools)
**Source**: `src/giljo_mcp/tools/message.py`

1. **send_message** ❌
   - Send message to one or more agents
   - Parameters: to_agents, content, project_id, message_type, priority, from_agent
   - Returns: message sending confirmation

2. **get_messages** ❌
   - Get messages for agent
   - Parameters: agent_name, project_id, unread_only, limit
   - Returns: messages list

3. **acknowledge_message** ❌
   - Mark message as read
   - Parameters: message_id, agent_name, project_id
   - Returns: acknowledgment confirmation

4. **broadcast_message** ❌
   - Broadcast message to all agents
   - Parameters: content, project_id, priority, from_agent
   - Returns: broadcast confirmation

5. **get_conversation** ❌
   - Get conversation thread between agents
   - Parameters: agent1, agent2, project_id
   - Returns: conversation history

6. **delete_message** ❌
   - Delete a message
   - Parameters: message_id, project_id
   - Returns: deletion confirmation

---

### 11. Project Management Tools (6 tools)
**Source**: `src/giljo_mcp/tools/project.py`

1. **create_project** ✅
   - Create new project with mission
   - Parameters: name, mission, product_id, tenant_key
   - Returns: project_id, tenant_key, session_id

2. **list_projects** ✅
   - List all projects with optional filter
   - Parameters: status
   - Returns: projects list

3. **get_project** ✅
   - Get project details
   - Parameters: project_id
   - Returns: project details

4. **switch_project** ✅
   - Switch to different project context
   - Parameters: project_id, tenant_key
   - Returns: project details

5. **close_project** ✅
   - Close/archive a project
   - Parameters: project_id
   - Returns: closure confirmation

6. **update_project** ❌
   - Update project details
   - Parameters: project_id, updates
   - Returns: updated project

---

### 12. Succession Tools (2 tools)
**Source**: `src/giljo_mcp/tools/succession_tools.py`

1. **create_successor_orchestrator** ❌
   - Create successor orchestrator and perform handover (Handover 0080)
   - Parameters: current_job_id, tenant_key, reason
   - Reasons: context_limit, manual, phase_transition
   - Returns: successor_id, instance_number, handover_summary

2. **check_succession_status** ❌
   - Check if succession needed based on context usage
   - Parameters: current_job_id, tenant_key
   - Returns: needs_succession, context_used, context_budget, recommendation

---

### 13. Task Management Tools (11 tools)
**Source**: `src/giljo_mcp/tools/task.py`

1. **create_task** ✅
   - Create new task with product isolation
   - Parameters: title, description, category, priority, tenant_key, product_id, project_id
   - Returns: task_id

2. **list_tasks** ✅
   - List tasks with filters
   - Parameters: status, category, priority, product_id, project_id, tenant_key
   - Returns: tasks list

3. **get_task** ❌
   - Get task details
   - Parameters: task_id, tenant_key
   - Returns: task details

4. **update_task** ✅
   - Update task details
   - Parameters: task_id, updates, tenant_key
   - Returns: updated task

5. **assign_task** ✅
   - Assign task to agent
   - Parameters: task_id, agent_id, tenant_key
   - Returns: assignment confirmation

6. **complete_task** ✅
   - Mark task as completed
   - Parameters: task_id, result, tenant_key
   - Returns: completion confirmation

7. **delete_task** ❌
   - Delete a task
   - Parameters: task_id, tenant_key
   - Returns: deletion confirmation

8. **get_task_history** ❌
   - Get task change history
   - Parameters: task_id, tenant_key
   - Returns: history entries

9. **add_task_comment** ❌
   - Add comment to task
   - Parameters: task_id, comment, tenant_key
   - Returns: comment_id

10. **get_task_comments** ❌
    - Get task comments
    - Parameters: task_id, tenant_key
    - Returns: comments list

11. **reorder_tasks** ❌
    - Reorder tasks for priority
    - Parameters: task_ids, tenant_key
    - Returns: reorder confirmation

---

### 14. Task Template Tools (3 tools)
**Source**: `src/giljo_mcp/tools/task_templates.py`

1. **create_task_template** ❌
   - Create task template
   - Parameters: name, description, tasks, tenant_key
   - Returns: template_id

2. **list_task_templates** ❌
   - List available task templates
   - Parameters: tenant_key
   - Returns: templates list

3. **apply_task_template** ❌
   - Apply template to create tasks
   - Parameters: template_id, project_id, tenant_key
   - Returns: created tasks

---

### 15. Template Management Tools (9 tools)
**Source**: `src/giljo_mcp/tools/template.py`

1. **list_templates** ✅
   - List available agent templates
   - Parameters: tenant_key
   - Returns: templates list

2. **get_template** ✅
   - Get specific template
   - Parameters: template_name, tenant_key
   - Returns: template content

3. **create_template** ✅
   - Create custom agent template
   - Parameters: name, role, content, tenant_key
   - Returns: template_id

4. **update_template** ✅
   - Update existing template
   - Parameters: template_id, updates, tenant_key
   - Returns: updated template

5. **delete_template** ❌
   - Delete template
   - Parameters: template_id, tenant_key
   - Returns: deletion confirmation

6. **reset_template** ❌
   - Reset template to default
   - Parameters: template_id, tenant_key
   - Returns: reset confirmation

7. **get_template_diff** ❌
   - Get diff between template versions
   - Parameters: template_id, version1, version2, tenant_key
   - Returns: diff content

8. **preview_template** ❌
   - Preview template with context
   - Parameters: template_id, context, tenant_key
   - Returns: rendered preview

9. **export_templates** ❌
   - Export templates for backup
   - Parameters: tenant_key
   - Returns: export data

---

### 16. Git Integration Tools (6 tools)
**Source**: `src/giljo_mcp/tools/git.py`

1. **git_status** ❌
   - Get Git repository status
   - Parameters: repo_path
   - Returns: branch, staged, unstaged, untracked

2. **git_commit** ❌
   - Create Git commit
   - Parameters: repo_path, message, files
   - Returns: commit_sha

3. **git_log** ❌
   - Get Git commit history
   - Parameters: repo_path, limit
   - Returns: commits list

4. **git_diff** ❌
   - Get Git diff
   - Parameters: repo_path, commit1, commit2
   - Returns: diff content

5. **git_branch** ❌
   - Manage Git branches
   - Parameters: repo_path, action, branch_name
   - Returns: branch operation result

6. **git_pull** ❌
   - Pull from remote repository
   - Parameters: repo_path, remote, branch
   - Returns: pull result

---

### 17. Claude Code Integration Tools (2 tools)
**Source**: `src/giljo_mcp/tools/claude_code_integration.py`

1. **get_claude_config** ❌
   - Get Claude Code configuration
   - Parameters: tenant_key
   - Returns: MCP configuration commands

2. **generate_claude_commands** ❌
   - Generate Claude Code MCP setup commands
   - Parameters: tenant_key, server_url
   - Returns: installation commands

---

### 18. Product Management Tools (1 tool)
**Source**: `src/giljo_mcp/tools/product.py`

1. **get_active_product** ❌
   - Get active product for tenant
   - Parameters: tenant_key
   - Returns: product details

---

### 19. Optimization Tools (6 tools)
**Source**: `src/giljo_mcp/tools/optimization.py`

1. **analyze_token_usage** ❌
   - Analyze token usage patterns
   - Parameters: tenant_key, time_range
   - Returns: usage statistics

2. **get_optimization_suggestions** ❌
   - Get optimization recommendations
   - Parameters: tenant_key
   - Returns: suggestions list

3. **apply_token_reduction** ❌
   - Apply context prioritization strategies
   - Parameters: tenant_key, strategy
   - Returns: reduction results

4. **benchmark_workflow** ❌
   - Benchmark orchestration workflow
   - Parameters: project_id, tenant_key
   - Returns: benchmark metrics

5. **compare_workflows** ❌
   - Compare workflow efficiency
   - Parameters: workflow1_id, workflow2_id, tenant_key
   - Returns: comparison results

6. **export_metrics** ❌
   - Export performance metrics
   - Parameters: tenant_key, format
   - Returns: metrics export

---

## Tool Architecture

### Multi-Tenant Isolation
All tools enforce strict tenant isolation:
- Tenant key parameter required for operations
- Database queries filter by tenant_key
- No cross-tenant data access possible
- WebSocket events scoped to tenant

### Thin Client Architecture (Handover 0088)
Key tools support context prioritization and orchestration:
- **get_orchestrator_instructions**: Condensed mission with field priorities
- **get_agent_mission**: Agent-specific mission fetching
- **spawn_agent_job**: Thin prompt generation (~10 lines vs 3000 lines)

### Error Handling
All tools implement production-grade error handling:
- Input validation with clear error messages
- Graceful degradation for non-critical failures
- Comprehensive logging for diagnostics
- Structured error responses

### WebSocket Integration
Status update tools broadcast real-time events:
- Agent status changes
- Job progress updates
- Message delivery notifications
- Orchestrator succession events

---

## Tool Usage Patterns

### Orchestrator Workflow
1. **health_check()** - Verify MCP connection
2. **get_orchestrator_instructions()** - Fetch condensed mission
3. **spawn_agent_job()** - Create worker agents
4. **check_orchestrator_messages()** - Poll for updates (30-60s)
5. **create_successor_orchestrator()** - Hand over when context full

### Agent Workflow
1. **get_agent_mission()** - Fetch agent-specific mission
2. **acknowledge_job()** - Start work (pending → active)
3. **report_progress()** - Report incremental progress
4. **get_next_instruction()** - Check for orchestrator feedback
5. **complete_job()** - Mark complete with results

### External Agent Workflow (HTTP)
1. **authenticate** via API (JWT token)
2. **list_active_agent_jobs_external()** - Find pending jobs
3. **acknowledge_agent_job_external()** - Claim job
4. **send_agent_message_external()** - Report progress
5. **complete_agent_job_external()** - Submit results

---

## Security Model

### Authentication
- JWT token-based authentication for HTTP endpoints
- Session-based authentication for MCP tools
- Automatic token refresh on 401 errors

### Authorization
- Tenant-scoped data access (multi-tenant isolation)
- Admin-only operations for job creation
- Agent-scoped permissions for job updates

### Data Protection
- No cross-tenant data leakage
- Encrypted communication (HTTPS)
- Audit logging for all operations

---

## Performance Characteristics

### Token Efficiency
- **Thin Client**: context prioritization and orchestration via mission fetching
- **Chunking**: Large documents split for optimal context usage
- **Field Priorities**: Selective content loading

### Response Times
- **MCP Tools**: <10ms (direct database access)
- **HTTP Tools**: <100ms (network overhead)
- **WebSocket**: <5ms (real-time events)

### Scalability
- Database connection pooling
- Async I/O for concurrent operations
- Message queue for agent coordination

---

## Future Enhancements

### Planned Tools
- Enhanced analytics and reporting tools
- Workflow automation templates
- Advanced context search (semantic)
- Multi-project coordination tools

### Architecture Improvements
- GraphQL API for flexible queries
- Enhanced caching layer
- Real-time collaboration tools
- Advanced succession strategies

---

## References

**Key Handovers**:
- Handover 0019: Agent Job Management
- Handover 0045: Agent Coordination Tools
- Handover 0060: External HTTP Agent Coordination
- Handover 0066: Kanban Board Self-Navigation
- Handover 0073: Agent Messaging & Status Tools
- Handover 0080: Orchestrator Succession
- Handover 0088: Thin Client Architecture

**Documentation**:
- `docs/TECHNICAL_ARCHITECTURE.md`
- `docs/SERVER_ARCHITECTURE_TECH_STACK.md`
- `docs/handovers/`

---

**Document Version**: 1.0
**Last Updated**: 2025-11-03
**Maintained By**: Documentation Manager Agent
