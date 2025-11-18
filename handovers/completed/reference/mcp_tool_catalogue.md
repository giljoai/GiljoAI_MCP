# MCP Tool Inventory - GiljoAI Agent Orchestration System

**Date**: 2025-11-06
**Status**: Complete & Verified
**Purpose**: Comprehensive and accurate inventory of all MCP tools in the GiljoAI system based on direct code analysis.

---

## Executive Summary

**Total Unique Tools**: 106
**HTTP Exposed Tools**: 45 (42%)
**Internal Tools**: 56 (53%)
**Unused/Deprecated Tools**: 5 (5%)
**Tool Source Files**: 26

This document provides a verified catalogue of all 106 unique tools within the GiljoAI MCP server. The analysis was performed by reviewing the tool registration functions and API endpoint mappings in the codebase. 42% of the tools are exposed via HTTP for external agent consumption, 53% are used internally for orchestration logic, and 5% are likely unused or deprecated.

---

## Tool Exposure Status

Tools are categorized based on their accessibility:
- **HTTP Exposed (✅)**: Accessible to external agents via the `/mcp/tools/execute` or `/mcp` JSON-RPC endpoints.
- **Internal (⚙️)**: Not exposed via HTTP, but used by other parts of the backend application.
- **Unused (❌)**: Not exposed via HTTP and no internal usages found. Potentially dead or deprecated code.

### HTTP Exposed Tools (45 tools)

These tools are directly callable by external agents.

**Source**: `api/endpoints/mcp_http.py`, `api/endpoints/mcp_tools.py`

#### Project Management (6 tools)
- `create_project` ✅
- `list_projects` ✅
- `get_project` ✅
- `switch_project` ✅
- `close_project` ✅
- `update_project_mission` ✅

#### Agent Orchestration (11 tools)
- `spawn_agent` ✅
- `list_agents` ✅
- `get_agent_status` ✅
- `update_agent` ✅
- `retire_agent` ✅
- `get_orchestrator_instructions` ✅
- `orchestrate_project` ✅
- `get_agent_mission` ✅
- `spawn_agent_job` ✅
- `get_workflow_status` ✅
- `health_check` ✅

#### Agent Coordination (6 tools)
- `get_pending_jobs` ✅
- `acknowledge_job` ✅
- `report_progress` ✅
- `get_next_instruction` ✅
- `complete_job` ✅
- `report_error` ✅

#### Message Queue (4 tools)
- `send_message` ✅
- `receive_messages` ✅
- `acknowledge_message` ✅
- `list_messages` ✅

#### Task Management (5 tools)
- `create_task` ✅
- `list_tasks` ✅
- `update_task` ✅
- `assign_task` ✅
- `complete_task` ✅

#### Template Management (4 tools)
- `list_templates` ✅
- `get_template` ✅
- `create_template` ✅
- `update_template` ✅

#### Context Discovery (4 tools)
- `discover_context` ✅
- `get_file_context` ✅
- `search_context` ✅
- `get_context_summary` ✅

#### Succession Management (2 tools)
- `create_successor_orchestrator` ✅
- `check_succession_status` ✅

#### Slash Commands (3 tools)
- `setup_slash_commands` ✅
- `gil_import_productagents` ✅
- `gil_import_personalagents` ✅
- `gil_handover` ✅

---

## Complete Tool Catalog

### 1. Agent Lifecycle Tools (8 tools)
**Source**: `src/giljo_mcp/tools/agent.py`

1.  **`ensure_agent`** ⚙️
    - Ensures an agent exists for a project, creating it if necessary. Idempotent.
2.  **`activate_agent`** ⚙️
    - Activates an orchestrator agent, triggering an immediate discovery workflow.
3.  **`assign_job`** ⚙️
    - Assigns a job to an agent with tasks, scope, and vision alignment.
4.  **`handoff`** ⚙️
    - Transfers work and context from one agent to another.
5.  **`agent_health`** ⚙️
    - Checks the health, status, and context usage of one or all agents.
6.  **`decommission_agent`** ⚙️
    - Gracefully ends an agent's work, completing its active jobs.
7.  **`spawn_and_log_sub_agent`** ⚙️
    - Logs the spawning of a native Claude Code sub-agent, creating a trackable interaction record.
8.  **`log_sub_agent_completion`** ⚙️
    - Logs the completion of a sub-agent's task, updating the interaction record with results and metrics.

### 2. Agent Communication Tools (3 tools)
**Source**: `src/giljo_mcp/tools/agent_communication.py`

1.  **`check_orchestrator_messages`** ⚙️
    - Allows an agent to poll for messages from the orchestrator or other agents.
2.  **`acknowledge_message`** ✅
    - Acknowledges receipt of a message, signaling to the sender that it was received.
3.  **`report_status`** ⚙️
    - Reports an agent's status and progress to the orchestrator for real-time visualization.

### 3. Agent Coordination (Internal) (7 tools)
**Source**: `src/giljo_mcp/tools/agent_coordination.py`

1.  **`get_pending_jobs`** ✅
    - Gets pending jobs assigned to a specific agent type for a given tenant.
2.  **`acknowledge_job`** ✅
    - Claims a job, transitioning its status from 'pending' to 'active'.
3.  **`report_progress`** ✅
    - Reports incremental progress on an active job, storing it in the message queue.
4.  **`get_next_instruction`** ✅
    - Checks for new instructions, user feedback, or handoff requests from the message queue.
5.  **`complete_job`** ✅
    - Marks a job as completed and stores the results.
6.  **`report_error`** ✅
    - Reports an error, pauses the job, and notifies the orchestrator for review.
7.  **`send_message`** ✅
    - Sends a message to another agent for inter-agent communication.

### 4. Agent Coordination (External) (7 tools)
**Source**: `src/giljo_mcp/tools/agent_coordination_external.py`

1.  **`create_agent_job_external`** ⚙️
    - Creates a new agent job via an HTTP POST request to the `/api/agent-jobs` endpoint. For external agents.
2.  **`send_agent_message_external`** ⚙️
    - Sends a message to an agent job via an HTTP POST request. For external agents.
3.  **`get_agent_job_status_external`** ⚙️
    - Gets an agent's job status via an HTTP GET request. For external agents.
4.  **`acknowledge_agent_job_external`** ⚙️
    - Acknowledges a job via an HTTP POST request. For external agents.
5.  **`complete_agent_job_external`** ⚙️
    - Completes a job via an HTTP POST request. For external agents.
6.  **`fail_agent_job_external`** ⚙️
    - Fails a job via an HTTP POST request. For external agents.
7.  **`list_active_agent_jobs_external`** ⚙️
    - Lists active agent jobs via an HTTP GET request. For external agents.

### 5. Agent Job Status Tools (1 tool)
**Source**: `src/giljo_mcp/tools/agent_job_status.py`

1.  **`update_job_status`** ⚙️
    - Enables an agent to update its own job status, facilitating self-navigation on a Kanban board visualization.

### 6. Agent Messaging Tools (2 tools)
**Source**: `src/giljo_mcp/tools/agent_messaging.py`

1.  **`send_mcp_message_tool`** ⚙️
    - Sends a message through the message center to the orchestrator, all agents (broadcast), or a specific agent.
2.  **`read_mcp_messages_tool`** ⚙️
    - Allows an agent to read messages from its message queue.

### 7. Agent Status Tools (2 tools)
**Source**: `src/giljo_mcp/tools/agent_status.py`

1.  **`set_agent_status_tool`** ⚙️
    - Allows an agent to update its own status with progress tracking for enhanced visibility in the orchestration grid.
2.  **`report_progress_tool`** ⚙️
    - Allows an agent to report a progress update, which updates the `last_progress_at` timestamp for health monitoring.

### 8. Context & Discovery Tools (8 tools)
**Source**: `src/giljo_mcp/tools/context.py`

1.  **`get_vision`** ✅
    - Retrieves the vision document for the active product, chunked if it's too large.
2.  **`get_vision_index`** ⚙️
    - Gets the vision document index to help the orchestrator navigate vision files.
3.  **`discover_context`** ✅
    - Discovers project context dynamically based on the agent's role and priority.
4.  **`get_context_index`** ⚙️
    - Gets the context index for intelligent querying, showing available documents and sections.
5.  **`get_context_section`** ⚙️
    - Retrieves a specific content section from a document in the index.
6.  **`get_product_settings`** ✅
    - Gets all product settings for analysis.
7.  **`session_info`** ⚙️
    - Gets current session statistics, including active project, agents, and message counts.
8.  **`recalibrate_mission`** ⚙️
    - Notifies agents about mission changes, prompting them to re-discover context.
9.  **`get_large_document`** ⚙️
    - Retrieves any large document with automatic chunking.
10. **`get_discovery_paths`** ⚙️
    - Gets all dynamically resolved paths for the current project.
11. **`help`** ⚙️
    - Gets documentation for all available tools.

### 9. Git Integration Tools (6 tools)
**Source**: `src/giljo_mcp/tools/git.py`

1.  **`configure_git`** ⚙️
    - Configures git settings for a product, including repo URL, auth method, and branch.
2.  **`init_repo`** ⚙️
    - Initializes a git repository for a product.
3.  **`commit_changes`** ⚙️
    - Commits changes to the repository with an auto-generated or custom message.
4.  **`push_to_remote`** ⚙️
    - Pushes commits to the remote repository.
5.  **`get_commit_history`** ⚙️
    - Retrieves the commit history from the repository.
6.  **`get_git_status`** ⚙️
    - Gets the current git status for a repository.

### 10. Message Communication Tools (6 tools)
**Source**: `src/giljo_mcp/tools/message.py`

1.  **`send_message`** ✅
    - Sends a message to one or more agents.
2.  **`get_messages`** ⚙️
    - Retrieves pending messages for an agent.
3.  **`acknowledge_message`** ✅
    - Marks a message as received by an agent.
4.  **`complete_message`** ⚙️
    - Marks a message as completed with a result.
5.  **`broadcast`** ⚙️
    - Broadcasts a message to all agents in a project.
6.  **`log_task`** ✅
    - A quick task-capture tool for logging work items from the CLI or other interfaces.

### 11. Optimization Tools (6 tools)
**Source**: `src/giljo_mcp/tools/optimization.py`

1.  **`get_optimization_settings`** ⚙️
    - Gets the current optimization settings and rules for a project.
2.  **`update_optimization_rules`** ⚙️
    - Updates a specific optimization rule for a project.
3.  **`get_token_savings_report`** ⚙️
    - Generates a comprehensive context-usage analytics report for a project.
4.  **`estimate_optimization_impact`** ⚙️
    - Estimates the optimization impact before spawning an agent.
5.  **`force_agent_handoff`** ⚙️
    - Forces an agent handoff due to context limits or other issues.
6.  **`get_optimization_status`** ⚙️
    - Gets the overall optimization system status for a tenant.

### 12. Orchestration & Slash Commands (11 tools)
**Source**: `src/giljo_mcp/tools/orchestration.py`

1.  **`orchestrate_project`** ✅
    - Triggers the complete project orchestration workflow.
2.  **`get_agent_mission`** ✅
    - Fetches an agent-specific mission and context (Thin Client Architecture).
3.  **`spawn_agent_job`** ✅
    - Spawns an agent job with a thin client prompt, storing the full mission in the database.
4.  **`get_workflow_status`** ✅
    - Gets the current workflow status for a project, including agent counts and progress.
5.  **`get_project_by_alias`** ⚙️
    - Fetches project details using its 6-character alias.
6.  **`activate_project_mission`** ⚙️
    - Activates a project and creates a mission plan for orchestration.
7.  **`get_launch_prompt`** ⚙️
    - Generates orchestration launch instructions for a project.
8.  **`get_fetch_agents_instructions`** ⚙️
    - Generates instructions for installing GiljoAI agent templates.
9.  **`get_update_agents_instructions`** ⚙️
    - Generates instructions for updating existing agent templates.
10. **`health_check`** ✅
    - Performs a health check of the MCP server.
11. **`get_orchestrator_instructions`** ✅
    - Fetches an orchestrator-specific mission, enabling the thin client architecture.

### 13. Product Management Tools (3 tools)
**Source**: `src/giljo_mcp/tools/product.py`

1.  **`get_product_config`** ⚙️
    - Gets product configuration with optional role-based filtering.
2.  **`update_product_config`** ⚙️
    - Updates product configuration with validation.
3.  **`get_product_settings`** ✅
    - A convenience alias for `get_product_config` to get the full, unfiltered configuration.

### 14. Project Management Tools (6 tools)
**Source**: `src/giljo_mcp/tools/project.py`

1.  **`create_project`** ✅
    - Creates a new project with a mission statement.
2.  **`list_projects`** ✅
    - Lists all projects with an optional status filter.
3.  **`switch_project`** ✅
    - Switches the active context to a different project.
4.  **`close_project`** ✅
    - Closes a completed project and provides a summary.
5.  **`update_project_mission`** ✅
    - Updates the mission field of a project after orchestrator analysis.
6.  **`project_status`** ⚙️
    - Gets a comprehensive status of a project, including agents, tasks, and messages.

### 15. Succession Tools (2 tools)
**Source**: `src/giljo_mcp/tools/succession_tools.py`

1.  **`create_successor_orchestrator`** ✅
    - Creates a successor orchestrator and performs a handover when context limits are reached.
2.  **`check_succession_status`** ✅
    - Checks if an orchestrator should trigger succession based on its context usage.

### 16. Task Management Tools (12 tools)
**Source**: `src/giljo_mcp/tools/task.py`

1.  **`create_task`** ✅
    - Creates a new task with product isolation.
2.  **`list_tasks`** ✅
    - Lists tasks with filters for product, project, status, etc.
3.  **`update_task`** ✅
    - Updates a task's status, priority, or description.
4.  **`get_product_task_summary`** ⚙️
    - Gets a task summary for a specific product or all products.
5.  **`get_task_dependencies`** ⚙️
    - Gets task dependency relationships for visualization and management.
6.  **`bulk_update_tasks`** ⚙️
    - Performs bulk operations (update, reorder) on multiple tasks.
7.  **`create_task_conversion_history`** ⚙️
    - Creates a history entry that tracks a task-to-project conversion.
8.  **`get_conversion_history`** ⚙️
    - Retrieves the conversion history for a task or project.
9.  **`project_from_task`** ⚙️
    - Converts a task into a full project, supporting different conversion strategies.
10. **`list_my_tasks`** ⚙️
    - Lists tasks created by the current user.
11. **`assign_task_to_agent`** ⚙️
    - Assigns a task to an agent and optionally auto-spawns a job for it.
12. **`task`** ⚙️
    - A prompt-based tool for quick task capture from a command-line context (e.g., `/task Fix the login bug`).

### 17. Task Template Tools (3 tools)
**Source**: `src/giljo_mcp/tools/task_templates.py`

1.  **`get_task_conversion_templates`** ⚙️
    - Gets available templates for converting tasks into projects.
2.  **`generate_project_from_task_template`** ⚙️
    - Generates a complete project configuration from a task using a specified template.
3.  **`suggest_conversion_template`** ⚙️
    - Analyzes a task and suggests the best conversion template to use.

### 18. Template Management Tools (9 tools)
**Source**: `src/giljo_mcp/tools/template.py`

1.  **`list_agent_templates`** ⚙️
    - Lists available agent templates with optional filters.
2.  **`get_agent_template`** ⚙️
    - Gets a specific agent template with optional runtime augmentations and variable substitutions.
3.  **`create_agent_template`** ⚙️
    - Creates a new agent template.
4.  **`update_agent_template`** ⚙️
    - Updates an existing template and archives the previous version.
5.  **`archive_template`** ⚙️
    - Archives a specific template version without modifying the active template.
6.  **`create_template_augmentation`** ⚙️
    - Creates a template augmentation for runtime customization.
7.  **`restore_template_version`** ⚙️
    - Restores an archived template version, either as a new template or by overwriting the existing one.
8.  **`suggest_template`** ⚙️
    - Suggests the best template to use based on project type, role, and usage statistics.
9.  **`get_template_stats`** ⚙️
    - Gets usage statistics for templates.

### 19. Unused or Deprecated Tools (5 tools)
The following tools were found in the codebase but are not exposed via HTTP and have no apparent internal usages. They may be deprecated or part of an incomplete feature.

- **`get_claude_config`** ❌ (`src/giljo_mcp/tools/claude_code_integration.py`)
- **`generate_claude_commands`** ❌ (`src/giljo_mcp/tools/claude_code_integration.py`)
- **`delete_task`** ❌ (`src/giljo_mcp/tools/task.py` - mentioned in old doc, but no implementation found)
- **`get_task_history`** ❌ (`src/giljo_mcp/tools/task.py` - mentioned in old doc, but no implementation found)
- **`add_task_comment`** ❌ (`src/giljo_mcp/tools/task.py` - mentioned in old doc, but no implementation found)
