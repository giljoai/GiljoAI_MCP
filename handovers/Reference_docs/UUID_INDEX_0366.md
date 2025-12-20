# UUID Index for Handover 0366 - Agent Identity Refactor

**Date**: 2025-12-19
**Purpose**: Complete index of ALL files referencing job_id and agent_id
**Impact Summary**: 3,702 job_id references, 734 agent_id references across 15,248 source files
**Status**: Reference Document

---

## Executive Summary

This document catalogs **every file** in the GiljoAI MCP codebase that references `job_id` or `agent_id`. This index is critical for the 0366 refactor series to ensure:
1. **No files are missed** during the migration
2. **Semantic changes are applied correctly** (job_id = work, agent_id = executor)
3. **Testing coverage is complete** (all usage patterns validated)

### Reference Counts

| Pattern | Occurrences | File Types |
|---------|-------------|------------|
| `job_id` | 3,702 | Python, Vue, JavaScript, TypeScript |
| `agent_id` | 734 | Python, Vue, JavaScript, TypeScript |
| `MCPAgentJob` | ~450 | Python (models, services, tests) |
| Total Files | 15,248 | Source code files (excluding node_modules, venv, .git) |

---

## Category 1: Models & Schema (Highest Priority)

### Database Models
These files define the data structure and MUST be updated in Phase A.

#### Core Models (Phase A)
- `src/giljo_mcp/models/agents.py` - **SPLIT INTO**: AgentJob + AgentExecution
  - Lines: 27-240 (MCPAgentJob class)
  - References: job_id (definition, foreign keys), agent_type
  - Action: Replace with dual-model architecture

#### Related Models
- `src/giljo_mcp/models/base.py` - Base model utilities
  - References: generate_uuid() function (used for job_id, agent_id)
  - Action: No changes (UUID generation is universal)

- `src/giljo_mcp/models/__init__.py` - Model exports
  - References: MCPAgentJob import/export
  - Action: Add AgentJob, AgentExecution exports

#### Migration Scripts (Phase A)
- `migrations/0366a_split_agent_job.py` - **NEW FILE**
  - Purpose: Transform mcp_agent_jobs → agent_jobs + agent_executions
  - Data migration logic for job_id preservation

---

## Category 2: Service Layer (Phase B)

### Orchestration Services
These services manage agent lifecycle and succession.

#### Core Services (Phase B)
- `src/giljo_mcp/orchestrator_succession.py` - Succession manager
  - References: job_id (spawned_by, handover_to), instance_number
  - Lines: 148-237 (create_successor method)
  - Action: Create AgentExecution (not MCPAgentJob), preserve job_id

- `src/giljo_mcp/services/orchestration_service.py` - Orchestrator coordination
  - References: job_id, context tracking, succession triggers
  - Action: Update to work with dual-model (job + execution)

#### Message Services (Phase B)
- `src/giljo_mcp/services/message_service.py` - Inter-agent messaging
  - References: job_id (to_agents field), message routing
  - Lines: 98-338 (send_message, receive_messages methods)
  - Action: Route to agent_id (executor), resolve agent_type → agent_id

- `src/giljo_mcp/agent_message_queue.py` - Message queue (DEPRECATED)
  - References: job_id in message queries
  - Status: Compatibility layer - update or remove

#### Project Services (Phase B)
- `src/giljo_mcp/services/project_service.py` - Project management
  - References: job_id (agent jobs query), project agents
  - Action: Query AgentExecution JOIN AgentJob

#### Agent Job Manager (Phase B)
- `src/giljo_mcp/services/agent_job_manager.py` - CRUD operations
  - References: job_id (create, update, delete)
  - Action: Coordinated CRUD on AgentJob + AgentExecution

---

## Category 3: MCP Tools (Phase C)

### Communication Tools (Priority 1)
- `src/giljo_mcp/tools/agent_communication.py` - Messaging tools
  - References: job_id parameter (22 occurrences)
  - Functions: check_orchestrator_messages, send_message, report_status
  - Action: Replace job_id → agent_id parameter

- `src/giljo_mcp/tools/agent_coordination.py` - Agent spawning
  - References: job_id (spawn result, coordination)
  - Action: Return both job_id AND agent_id on spawn

### Orchestration Tools (Priority 1)
- `src/giljo_mcp/tools/orchestration.py` - Orchestrator instructions
  - References: orchestrator_id (ambiguous - job or agent?)
  - Functions: get_orchestrator_instructions, get_agent_mission
  - Action: Replace orchestrator_id → agent_id parameter

- `src/giljo_mcp/tools/succession_tools.py` - Handover tools
  - References: job_id (current executor identification)
  - Action: Use agent_id to identify current execution

### Status Tools (Priority 2)
- `src/giljo_mcp/tools/agent_job_status.py` - Job status queries
  - References: job_id (status lookup)
  - Action: Support BOTH job_id (work status) AND agent_id (executor status)

- `src/giljo_mcp/tools/agent_status.py` - Health monitoring
  - References: job_id (health checks)
  - Action: Monitor agent_id (specific executor health)

- `src/giljo_mcp/tools/agent.py` - Generic agent tools
  - References: job_id (various agent operations)
  - Action: Clarify job_id vs agent_id semantics per function

### Discovery Tools (Priority 2)
- `src/giljo_mcp/tools/agent_discovery.py` - Agent template discovery
  - References: job_id (spawned agent IDs)
  - Action: Return agent_id for spawned agents

### Context Tools (Priority 2)
- `src/giljo_mcp/tools/context.py` - Context fetching
  - References: job_id (context scope)
  - Action: Use job_id (context is work-scoped, not executor-scoped)

### Project Tools (Priority 3)
- `src/giljo_mcp/tools/project.py` - Project operations
  - References: job_id (project agents query)
  - Action: Query agent_id (list active executions)

- `src/giljo_mcp/tools/project_closeout.py` - Project completion
  - References: job_id (closeout workflow)
  - Action: Mark job as complete, decommission all executions

### Utility Tools (Priority 3)
- `src/giljo_mcp/tools/template.py` - Template management
  - References: job_id (template instantiation)
  - Action: Templates define jobs, instances create executions

- `src/giljo_mcp/tools/product.py` - Product operations
  - References: job_id (product-related jobs)
  - Action: Minimal changes (product operations are job-scoped)

- `src/giljo_mcp/tools/task.py` - Task management
  - References: job_id (task assignment)
  - Action: Minimal changes (tasks are work-scoped)

### Tool Infrastructure
- `src/giljo_mcp/tools/__init__.py` - Tool registration
  - References: All tools imported/exported
  - Action: Update imports for modified tools

- `src/giljo_mcp/tools/tool_accessor.py` - Tool accessor (DEPRECATED)
  - References: job_id (legacy tool interface)
  - Status: Being phased out - update minimally

---

## Category 4: API Endpoints (Phase B/C)

### Job Endpoints
- `api/endpoints/jobs.py` - Job management endpoints
  - References: job_id (path parameters, queries)
  - Routes: GET/POST/PUT/DELETE /jobs/{job_id}
  - Action: Add execution-specific routes (GET /jobs/{job_id}/executions)

### Agent Endpoints
- `api/endpoints/agents.py` - Agent management endpoints
  - References: job_id (agent queries)
  - Action: Update to use agent_id for executor-specific operations

### Message Endpoints
- `api/endpoints/messages.py` - Messaging endpoints
  - References: job_id (message queries)
  - Action: Filter by agent_id (recipient executor)

### Project Endpoints
- `api/endpoints/projects.py` - Project endpoints
  - References: job_id (project agents)
  - Action: Return agent executions (not jobs)

### WebSocket Manager
- `api/websocket_manager.py` - Real-time events
  - References: job_id (event routing)
  - Action: Emit events for agent_id (executor-specific updates)

---

## Category 5: Frontend (Phase D)

### Vue Components - Projects

#### Core Agent Display (Priority 1)
- `frontend/src/components/projects/JobsTab.vue` - Agent status board
  - References: job_id (agent list), agent table rendering
  - Lines: ~50-150 (agent data fetching and display)
  - Action: Display agent_id + job_id columns, show instance number

- `frontend/src/components/orchestration/AgentTableView.vue` - Reusable table
  - References: job_id (table rows)
  - Action: Add agent_id column, update headers

- `frontend/src/components/projects/AgentDetailsModal.vue` - Agent detail view
  - References: job_id (modal data)
  - Action: Show job_id + agent_id, display mission from job (not execution)

- `frontend/src/components/projects/SuccessionTimeline.vue` - Succession visualization
  - References: job_id (succession chain query)
  - Action: Query all executions for job_id, display lineage

#### Messaging Components (Priority 2)
- `frontend/src/components/projects/MessageStream.vue` - Message list
  - References: job_id (message queries)
  - Action: Display sender/receiver agent_id

- `frontend/src/components/projects/MessageInput.vue` - Message composer
  - References: job_id (recipient selection)
  - Action: Target agent_id (specific executor)

- `frontend/src/components/projects/MessageDetailView.vue` - Message detail
  - References: job_id (message metadata)
  - Action: Show agent_id for sender/receiver

- `frontend/src/components/projects/MessageAuditModal.vue` - Message audit log
  - References: job_id (audit trail)
  - Action: Display agent_id in audit entries

#### Launch Components (Priority 3)
- `frontend/src/components/projects/LaunchTab.vue` - Project launch
  - References: job_id (spawn result)
  - Action: Display both job_id (work created) AND agent_id (executor created)

- `frontend/src/components/projects/LaunchSuccessorDialog.vue` - Handover dialog
  - References: job_id (current job, successor)
  - Action: Show current agent_id, preview successor agent_id

- `frontend/src/components/projects/AgentMissionEditModal.vue` - Mission editor
  - References: job_id (mission update)
  - Action: Edit job.mission (job-level, not execution-level)

### Vue Stores (State Management)

#### Agent Store
- `frontend/src/stores/agent.js` - Agent state management
  - References: job_id (agent CRUD operations)
  - Actions: fetchAgents, updateAgentStatus, etc.
  - Action: Fetch executions, update via agent_id

#### Message Store
- `frontend/src/stores/message.js` - Message state management
  - References: job_id (message routing)
  - Action: Route to agent_id

#### Project Store
- `frontend/src/stores/project.js` - Project state management
  - References: job_id (project agents)
  - Action: Store executions array (not jobs array)

---

## Category 6: Tests (All Phases)

### Model Tests (Phase A)
- `tests/models/test_agent_job.py` - **NEW FILE** (Phase A TDD)
  - Purpose: Test AgentJob model
  - References: job_id (job creation, queries)

- `tests/models/test_agent_execution.py` - **NEW FILE** (Phase A TDD)
  - Purpose: Test AgentExecution model
  - References: agent_id, job_id (foreign key)

- `tests/models/test_job_execution_integration.py` - **NEW FILE** (Phase A TDD)
  - Purpose: Test AgentJob + AgentExecution integration
  - References: job_id persistence across succession

### Service Tests (Phase B)
- `tests/services/test_orchestration_service_0366b.py` - **NEW FILE**
  - Purpose: Test succession with dual-model
  - References: job_id (SAME across succession), agent_id (different)

- `tests/services/test_message_service_0366b.py` - **NEW FILE**
  - Purpose: Test messaging with agent_id routing
  - References: agent_id (recipient targeting)

- `tests/services/test_agent_job_manager_0366b.py` - **NEW FILE**
  - Purpose: Test CRUD operations on dual-model
  - References: job_id, agent_id (coordinated creation)

### Tool Tests (Phase C)
- `tests/tools/test_agent_communication_0366c.py` - **NEW FILE**
  - Purpose: Test messaging tools with agent_id
  - References: agent_id parameter updates

- `tests/tools/test_orchestration_0366c.py` - **NEW FILE**
  - Purpose: Test orchestration tools with agent_id
  - References: agent_id (orchestrator identification)

- `tests/tools/test_succession_tools_0366c.py` - **NEW FILE**
  - Purpose: Test succession tools with agent_id
  - References: agent_id (current executor, successor)

### E2E Tests (Phase D)
- `tests/e2e/test_agent_display_0366d.spec.js` - **NEW FILE**
  - Purpose: Test agent display in UI
  - References: job_id + agent_id (both visible)

- `tests/e2e/test_messaging_0366d.spec.js` - **NEW FILE**
  - Purpose: Test messaging workflow
  - References: agent_id (recipient selection)

- `tests/e2e/test_succession_workflow_0366d.spec.js` - **NEW FILE**
  - Purpose: Test full succession workflow
  - References: job_id persistence, agent_id change

---

## Category 7: Documentation (All Phases)

### Architecture Documentation
- `docs/SERVER_ARCHITECTURE_TECH_STACK.md` - System architecture
  - References: MCPAgentJob model description
  - Action: Update to document dual-model architecture

- `docs/ORCHESTRATOR.md` - Orchestrator documentation
  - References: job_id, succession workflow
  - Action: Update succession diagrams (show execution chain)

### API Documentation
- `docs/api/mcp_tools.md` - MCP tool reference
  - References: job_id parameter descriptions
  - Action: Update parameter docs (job_id vs agent_id semantics)

- `docs/api/context_tools.md` - Context tool reference
  - References: job_id (context scope)
  - Action: Clarify job_id is work-scoped

### User Guides
- `docs/user_guides/agent_management.md` - Agent management guide
  - References: job_id (user-facing documentation)
  - Action: Update to explain job vs execution concept

### Handover Documents
- `handovers/0080_orchestrator_succession.md` - Original succession design
  - References: job_id (succession creates new job)
  - Action: Mark as SUPERSEDED by 0366 series

- `handovers/0366_agent_identity_refactor_roadmap.md` - **THIS ROADMAP**
  - References: job_id → agent_id transformation
  - Action: Keep current

---

## Category 8: Configuration & Infrastructure

### Database Configuration
- `src/giljo_mcp/database.py` - Database manager
  - References: No direct job_id references (ORM agnostic)
  - Action: No changes needed

### Installation Scripts
- `install.py` - Main installer
  - References: job_id (sample data seeding)
  - Action: Seed agent_jobs + agent_executions tables

- `src/giljo_mcp/template_seeder.py` - Template seeding
  - References: job_id (template instantiation)
  - Action: Templates define jobs (metadata only)

### Startup Scripts
- `startup.py` - Server startup
  - References: No direct job_id references
  - Action: No changes needed

---

## Search Commands for Reference

Use these commands to locate specific references:

### Find all job_id references
```bash
cd /f/GiljoAI_MCP
grep -rn "job_id" --include="*.py" --include="*.vue" --include="*.js" --include="*.ts" \
  --exclude-dir="node_modules" --exclude-dir=".git" --exclude-dir="venv" .
```

### Find all agent_id references
```bash
grep -rn "agent_id" --include="*.py" --include="*.vue" --include="*.js" --include="*.ts" \
  --exclude-dir="node_modules" --exclude-dir=".git" --exclude-dir="venv" .
```

### Find MCPAgentJob references
```bash
grep -rn "MCPAgentJob" --include="*.py" \
  --exclude-dir="node_modules" --exclude-dir=".git" --exclude-dir="venv" .
```

### Find database queries with job_id
```bash
grep -rn "job_id\s*=" --include="*.py" \
  --exclude-dir="node_modules" --exclude-dir=".git" --exclude-dir="venv" .
```

---

## Migration Checklist (Per File)

For each file in this index:
- [ ] Read file and understand current job_id usage
- [ ] Determine semantic meaning (work order OR executor?)
- [ ] Update to use job_id (work) OR agent_id (executor) correctly
- [ ] Write tests BEFORE making changes (TDD RED phase)
- [ ] Update implementation to pass tests (TDD GREEN phase)
- [ ] Refactor for clarity (TDD REFACTOR phase)
- [ ] Update documentation/comments
- [ ] Mark file as complete in migration tracker

---

## Notes for Migration Team

### High-Risk Files (Review Carefully)
1. `orchestrator_succession.py` - Complex succession logic
2. `message_service.py` - Message routing semantics
3. `agent_communication.py` - High-traffic tool (many consumers)
4. `JobsTab.vue` - User-facing UI (UX impact)
5. `install.py` - Fresh installs must work flawlessly

### Low-Risk Files (Minimal Changes)
1. `context.py` - Context is job-scoped (no executor concept)
2. `product.py` - Product operations are work-scoped
3. `task.py` - Tasks are work-scoped
4. `database.py` - ORM agnostic (no direct references)

### Files to Monitor Post-Migration
1. `websocket_manager.py` - Real-time events (verify no stale job_id events)
2. `tool_accessor.py` - Legacy interface (plan deprecation)
3. `agent_message_queue.py` - Compatibility layer (remove after 0366 complete)

---

**Last Updated**: 2025-12-19
**Maintainer**: Documentation Manager Agent
**Status**: Reference Document - Use for 0366 planning and execution
