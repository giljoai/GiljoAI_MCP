# 0480 Exception Handling Migration - Comprehensive Test Plan

**Handover Series:** 0480a-0480f
**Date:** January 2026
**Author:** Deep Researcher Agent
**Status:** DRAFT

## Executive Summary

The 0480 series migrated four core services from dict-based error returns (`{"success": False, "error": "..."}`) to raising exceptions from the centralized exception hierarchy. This test plan ensures ALL direct and indirect impacts are validated before merging to master.

**Services Modified:**
1. `ProjectService` (35+ methods) - Project CRUD and lifecycle
2. `OrchestrationService` (61+ methods) - Agent jobs, workflow, spawning
3. `MessageService` (10 methods) - Agent messaging
4. `TemplateService` (21+ methods) - Agent templates

**Exception Classes Used:**
- `ResourceNotFoundError` (404) - Missing resources
- `ValidationError` (400) - Invalid input
- `ProjectStateError` (500) - Invalid project state transitions
- `TemplateNotFoundError` (404) - Missing templates
- `TemplateValidationError` (400) - Template validation failures
- `OrchestrationError` (500) - Orchestration failures
- `MessageDeliveryError` (500) - Message routing failures
- `BaseGiljoException` (500) - Generic wrapper for unexpected errors

---

## Test Categories Overview

| Category | Test Count | Priority | Can Automate |
|----------|------------|----------|--------------|
| A. ProjectService Unit | 25 | P1 | Yes |
| B. OrchestrationService Unit | 35 | P1 | Yes |
| C. MessageService Unit | 15 | P1 | Yes |
| D. TemplateService Unit | 18 | P1 | Yes |
| E. API Endpoint Integration | 45 | P1 | Yes |
| F. MCP Tool Integration | 30 | P1 | Yes |
| G. Frontend E2E | 20 | P2 | Yes (Playwright) |
| H. WebSocket Events | 12 | P2 | Yes |
| I. Slash Commands | 8 | P2 | Yes |
| J. Cross-Service Cascade | 10 | P2 | Yes |
| **TOTAL** | **218** | | |

---

## Indirect Impact Analysis

### Service Call Chain Analysis

```
Frontend (Vue) 
    -> API Endpoints 
        -> Services (Modified)
            -> Database Layer
            -> WebSocket Manager
```

### Impact Matrix

| Caller Type | ProjectService | OrchestrationService | MessageService | TemplateService |
|-------------|----------------|----------------------|----------------|-----------------|
| **API Endpoints** | 12 endpoints | 18 endpoints | 6 endpoints | 8 endpoints |
| **MCP Tools** | 8 tools | 15 tools | 6 tools | 3 tools |
| **Other Services** | 2 services | 3 services | 1 service | 0 services |
| **Frontend** | 5 components | 8 components | 3 components | 2 components |

### Cross-Service Dependencies

1. **OrchestrationService -> ProjectService**
   - `spawn_agent_job()` calls `ProjectService.get_project()`
   - Risk: If ProjectService raises exception, spawn fails unexpectedly

2. **OrchestrationService -> MessageService**
   - `complete_job()` may call `MessageService.broadcast()`
   - Risk: Message failure shouldn't block job completion

3. **ToolAccessor -> All Services**
   - ToolAccessor delegates to all four services
   - Risk: Must catch exceptions and convert to MCP error responses

---

## Detailed Test Cases

### Category A: ProjectService Unit Tests

| Test ID | Test Name | Preconditions | Steps | Expected Result | Priority |
|---------|-----------|---------------|-------|-----------------|----------|
| A001 | get_project_raises_not_found | DB empty | Call `get_project("nonexistent", tenant_key)` | Raises `ResourceNotFoundError` with project_id in context | P1 |
| A002 | get_project_requires_tenant_key | Any | Call `get_project(id, "")` | Raises `ValueError` | P1 |
| A003 | get_project_wrong_tenant | Project exists for tenant_a | Call `get_project(id, "tenant_b")` | Raises `ResourceNotFoundError` | P1 |
| A004 | create_project_success | Valid input | Call `create_project(name, mission, tenant_key)` | Returns dict with project_id | P1 |
| A005 | create_project_db_error | DB connection issue | Inject DB failure | Raises `BaseGiljoException` wrapping original | P2 |
| A006 | list_projects_no_tenant | No tenant context | Clear tenant context, call `list_projects()` | Raises `ValidationError` | P1 |
| A007 | get_active_project_no_tenant | No tenant context | Clear tenant context | Raises `ValidationError` | P1 |
| A008 | get_active_project_none_active | No active project | All projects inactive | Returns `None` (not exception) | P1 |
| A009 | update_mission_not_found | Project doesn't exist | Call `update_project_mission(fake_id, ...)` | Raises `ResourceNotFoundError` | P1 |
| A010 | update_mission_wrong_tenant | Project exists for tenant_a | Call with tenant_b | Raises `ResourceNotFoundError` | P1 |
| A011 | activate_project_not_found | Project doesn't exist | Call `activate_project(fake_id, tenant)` | Raises `ResourceNotFoundError` | P1 |
| A012 | activate_project_invalid_state | Project status = "completed" | Call `activate_project()` | Raises `ProjectStateError` | P1 |
| A013 | activate_project_success | Project status = "staging" | Call `activate_project()` | Returns success dict | P1 |
| A014 | deactivate_project_not_found | Project doesn't exist | Call `deactivate_project(fake_id, tenant)` | Raises `ResourceNotFoundError` | P1 |
| A015 | deactivate_project_invalid_state | Project status = "inactive" | Call `deactivate_project()` | Raises `ProjectStateError` | P1 |
| A016 | complete_project_not_found | Project doesn't exist | Call `complete_project(fake_id, ...)` | Raises `BaseGiljoException` wrapping `ResourceNotFoundError` | P1 |
| A017 | complete_project_no_summary | Project exists, empty summary | Call `complete_project(id, "", ...)` | Raises `ValidationError` | P1 |
| A018 | cancel_project_not_found | Project doesn't exist | Call `cancel_project(fake_id, tenant)` | Raises `ResourceNotFoundError` | P1 |
| A019 | restore_project_not_found | Project doesn't exist | Call `restore_project(fake_id)` | Raises `ResourceNotFoundError` | P1 |
| A020 | restore_project_not_deleted | Project exists, status != deleted | Call `restore_project()` | Raises `ProjectStateError` | P1 |
| A021 | cancel_staging_not_found | Project doesn't exist | Call `cancel_staging(fake_id, tenant)` | Raises `ResourceNotFoundError` | P1 |
| A022 | cancel_staging_not_staging | Project exists, staging_status != "staging" | Call `cancel_staging()` | Raises `ProjectStateError` | P1 |
| A023 | delete_project_not_found | Project doesn't exist | Call `delete_project(fake_id, tenant)` | Raises `ResourceNotFoundError` | P1 |
| A024 | launch_project_not_found | Project doesn't exist | Call `launch_project(fake_id, tenant)` | Raises `ResourceNotFoundError` | P1 |
| A025 | switch_project_not_found | Project doesn't exist | Call `switch_project(fake_id, tenant)` | Raises `ResourceNotFoundError` | P1 |

### Category B: OrchestrationService Unit Tests

| Test ID | Test Name | Preconditions | Steps | Expected Result | Priority |
|---------|-----------|---------------|-------|-----------------|----------|
| B001 | spawn_agent_job_success | Project exists | Call `spawn_agent_job(...)` | Returns job_id | P1 |
| B002 | spawn_agent_job_project_not_found | Project doesn't exist | Call with fake project_id | Raises `ResourceNotFoundError` | P1 |
| B003 | get_agent_mission_not_found | Job doesn't exist | Call `get_agent_mission(fake_job_id, tenant)` | Raises `ResourceNotFoundError` | P1 |
| B004 | get_agent_mission_success | Job exists | Call `get_agent_mission(job_id, tenant)` | Returns mission dict with full_protocol | P1 |
| B005 | acknowledge_job_not_found | Job doesn't exist | Call `acknowledge_job(fake_id, agent)` | Raises `ResourceNotFoundError` | P1 |
| B006 | acknowledge_job_success | Job exists, status=waiting | Call `acknowledge_job()` | Status changes to "working" | P1 |
| B007 | report_progress_not_found | Job doesn't exist | Call `report_progress(fake_id, ...)` | Raises `ResourceNotFoundError` | P1 |
| B008 | report_progress_success | Job exists | Call with todo_items | Returns success with percent | P1 |
| B009 | report_progress_warns_missing_todos | Job exists | Call without todo_items | Returns success with warning | P2 |
| B010 | complete_job_not_found | Job doesn't exist | Call `complete_job(fake_id, result)` | Raises `ResourceNotFoundError` | P1 |
| B011 | complete_job_validation_error | Job has unread messages | Call `complete_job()` | Raises `ValidationError` with blockers | P1 |
| B012 | complete_job_success | Job valid, no blockers | Call `complete_job()` | Status = "completed" | P1 |
| B013 | report_error_not_found | Job doesn't exist | Call `report_error(fake_id, error)` | Raises `ResourceNotFoundError` | P1 |
| B014 | report_error_success | Job exists | Call `report_error()` | Status = "blocked" or "failed" | P1 |
| B015 | list_jobs_success | Jobs exist | Call `list_jobs(project_id, tenant)` | Returns job list | P1 |
| B016 | list_jobs_empty | No jobs | Call `list_jobs()` | Returns empty list (not exception) | P1 |
| B017 | get_pending_jobs_success | Pending jobs exist | Call `get_pending_jobs(tenant)` | Returns pending job list | P1 |
| B018 | get_workflow_status_not_found | Project doesn't exist | Call `get_workflow_status(fake_id, tenant)` | Raises `ResourceNotFoundError` | P1 |
| B019 | get_workflow_status_success | Project exists | Call `get_workflow_status()` | Returns status dict | P1 |
| B020 | trigger_succession_not_found | Job doesn't exist | Call `trigger_succession(fake_id)` | Raises `ResourceNotFoundError` | P1 |
| B021 | trigger_succession_success | Orchestrator job exists | Call `trigger_succession()` | Creates successor, returns new_job_id | P1 |
| B022 | get_orchestrator_instructions_not_found | Project doesn't exist | Call with fake orchestrator_id | Raises `ResourceNotFoundError` | P1 |
| B023 | get_orchestrator_instructions_success | Orchestrator exists | Call `get_orchestrator_instructions()` | Returns framing with priorities | P1 |
| B024 | update_agent_mission_not_found | Job doesn't exist | Call `update_agent_mission(fake_id, ...)` | Raises `ResourceNotFoundError` | P1 |
| B025 | update_agent_mission_success | Job exists | Call with new mission | Mission updated | P1 |
| B026 | create_successor_orchestrator_not_found | Project doesn't exist | Call `create_successor_orchestrator(fake_id)` | Raises `ResourceNotFoundError` | P1 |
| B027 | create_successor_orchestrator_success | Project active | Call | Creates new orchestrator job | P1 |
| B028 | check_succession_status_not_found | Job doesn't exist | Call `check_succession_status(fake_id)` | Raises `ResourceNotFoundError` | P1 |
| B029 | check_succession_status_success | Job exists | Call | Returns status info | P1 |
| B030 | spawn_agent_validation_error | Invalid agent type | Call with invalid template | Raises `ValidationError` | P1 |
| B031 | spawn_agent_limit_exceeded | 8 agents already | Try to spawn 9th | Raises `ValidationError` (agent limit) | P2 |
| B032 | get_agent_mission_wrong_tenant | Job for tenant_a | Call with tenant_b | Raises `ResourceNotFoundError` | P1 |
| B033 | complete_job_incomplete_todos | Todos not all completed | Call `complete_job()` | Raises `ValidationError` | P1 |
| B034 | spawn_agent_template_not_found | Template doesn't exist | Call with fake template | Raises `TemplateNotFoundError` | P1 |
| B035 | generate_mission_plan_error | Invalid product context | Call `generate_mission_plan()` | Raises `OrchestrationError` | P2 |

### Category C: MessageService Unit Tests

| Test ID | Test Name | Preconditions | Steps | Expected Result | Priority |
|---------|-----------|---------------|-------|-----------------|----------|
| C001 | send_message_success | Project and agents exist | Call `send_message(to, content, project)` | Returns message_id | P1 |
| C002 | send_message_project_not_found | Project doesn't exist | Call with fake project_id | Raises `ResourceNotFoundError` | P1 |
| C003 | send_message_wrong_tenant | Project for tenant_a | Call with tenant_b | Raises `ResourceNotFoundError` | P1 |
| C004 | broadcast_success | Project with agents | Call `broadcast(content, project_id)` | Message sent to all agents | P1 |
| C005 | broadcast_no_agents | Project empty | Call `broadcast()` | Raises `ResourceNotFoundError` | P1 |
| C006 | broadcast_to_project_success | Active executions exist | Call `broadcast_to_project()` | Returns count of recipients | P1 |
| C007 | broadcast_to_project_no_executions | No active executions | Call `broadcast_to_project()` | Raises `ResourceNotFoundError` | P1 |
| C008 | receive_messages_no_tenant | No tenant context | Call `receive_messages(agent_id)` | Raises `ValidationError` | P1 |
| C009 | receive_messages_agent_not_found | Agent doesn't exist | Call with fake agent_id | Raises `ResourceNotFoundError` | P1 |
| C010 | receive_messages_success | Messages pending | Call `receive_messages()` | Returns messages, auto-acknowledges | P1 |
| C011 | receive_messages_empty | No pending messages | Call | Returns empty list (not exception) | P1 |
| C012 | list_messages_no_context | No tenant/project | Call `list_messages()` | Raises `ValidationError` | P1 |
| C013 | list_messages_agent_not_found | Agent doesn't exist | Call with fake agent_id | Raises `ResourceNotFoundError` | P1 |
| C014 | complete_message_not_found | Message doesn't exist | Call `complete_message(fake_id, ...)` | Raises `ResourceNotFoundError` | P1 |
| C015 | acknowledge_message_not_found | Message doesn't exist | Call `acknowledge_message(fake_id, ...)` | Raises `ResourceNotFoundError` | P1 |

### Category D: TemplateService Unit Tests

| Test ID | Test Name | Preconditions | Steps | Expected Result | Priority |
|---------|-----------|---------------|-------|-----------------|----------|
| D001 | list_templates_success | Templates exist | Call `list_templates(tenant_key)` | Returns template list | P1 |
| D002 | list_templates_no_tenant | No tenant context | Call `list_templates()` | Raises `ValidationError` | P1 |
| D003 | get_template_by_id_success | Template exists | Call `get_template(id=template_id)` | Returns template dict | P1 |
| D004 | get_template_by_name_success | Template exists | Call `get_template(name=template_name)` | Returns template dict | P1 |
| D005 | get_template_not_found | Template doesn't exist | Call `get_template(id=fake_id)` | Raises `TemplateNotFoundError` | P1 |
| D006 | get_template_no_identifier | No id or name | Call `get_template()` | Raises `ValidationError` | P1 |
| D007 | get_template_wrong_tenant | Template for tenant_a | Call with tenant_b | Raises `TemplateNotFoundError` | P1 |
| D008 | create_template_success | Valid input | Call `create_template(name, content)` | Returns template_id | P1 |
| D009 | create_template_no_tenant | No tenant context | Call `create_template()` | Raises `ValidationError` | P1 |
| D010 | create_template_duplicate_name | Name exists | Call with existing name | Raises `TemplateValidationError` | P2 |
| D011 | update_template_success | Template exists | Call `update_template(id, ...)` | Template updated | P1 |
| D012 | update_template_not_found | Template doesn't exist | Call with fake id | Raises `TemplateNotFoundError` | P1 |
| D013 | update_template_system_managed | Template is system-managed | Try to modify | Raises `TemplateValidationError` | P1 |
| D014 | hard_delete_template_not_found | Template doesn't exist | Call `hard_delete_template(fake_id)` | Raises `TemplateNotFoundError` | P1 |
| D015 | hard_delete_template_system_managed | Template is system-managed | Call `hard_delete_template()` | Raises `TemplateValidationError` | P1 |
| D016 | validate_active_agent_limit_exceeded | 7 active agents | Call `validate_active_agent_limit()` | Raises `ValidationError` | P1 |
| D017 | get_template_history_not_found | Template doesn't exist | Call `get_template_history(fake_id)` | Raises `TemplateNotFoundError` | P2 |
| D018 | restore_template_from_archive_not_found | Archive doesn't exist | Call `restore_template_from_archive(fake_id)` | Raises `TemplateNotFoundError` | P2 |

### Category E: API Endpoint Integration Tests

These tests verify that FastAPI endpoints correctly propagate exceptions and return appropriate HTTP status codes.

| Test ID | Test Name | Endpoint | HTTP Method | Expected Status | Priority |
|---------|-----------|----------|-------------|-----------------|----------|
| E001 | get_project_404 | `/api/projects/{id}` | GET | 404 | P1 |
| E002 | get_project_403_wrong_tenant | `/api/projects/{id}` | GET | 404 (hidden) | P1 |
| E003 | create_project_400_validation | `/api/projects` | POST | 400 | P1 |
| E004 | activate_project_404 | `/api/projects/{id}/activate` | POST | 404 | P1 |
| E005 | activate_project_400_state | `/api/projects/{id}/activate` | POST | 400 | P1 |
| E006 | deactivate_project_404 | `/api/projects/{id}/deactivate` | POST | 404 | P1 |
| E007 | deactivate_project_400_state | `/api/projects/{id}/deactivate` | POST | 400 | P1 |
| E008 | complete_project_404 | `/api/projects/{id}/complete` | POST | 404 | P1 |
| E009 | complete_project_400_validation | `/api/projects/{id}/complete` | POST | 400 | P1 |
| E010 | cancel_project_404 | `/api/projects/{id}/cancel` | POST | 404 | P1 |
| E011 | restore_project_404 | `/api/projects/{id}/restore` | POST | 404 | P1 |
| E012 | launch_project_404 | `/api/projects/{id}/launch` | POST | 404 | P1 |
| E013 | spawn_agent_404_project | `/api/agent-jobs/spawn` | POST | 404 | P1 |
| E014 | spawn_agent_400_validation | `/api/agent-jobs/spawn` | POST | 400 | P1 |
| E015 | get_agent_mission_404 | `/api/agent-jobs/{id}/mission` | GET | 404 | P1 |
| E016 | acknowledge_job_404 | `/api/agent-jobs/{id}/acknowledge` | POST | 404 | P1 |
| E017 | complete_job_404 | `/api/agent-jobs/{id}/complete` | POST | 404 | P1 |
| E018 | complete_job_400_blockers | `/api/agent-jobs/{id}/complete` | POST | 400 | P1 |
| E019 | report_progress_404 | `/api/agent-jobs/{id}/progress` | POST | 404 | P1 |
| E020 | report_error_404 | `/api/agent-jobs/{id}/error` | POST | 404 | P1 |
| E021 | list_jobs_success | `/api/agent-jobs` | GET | 200 | P1 |
| E022 | get_workflow_status_404 | `/api/orchestration/status/{id}` | GET | 404 | P1 |
| E023 | trigger_succession_404 | `/api/agent-jobs/{id}/succession` | POST | 404 | P1 |
| E024 | send_message_404_project | `/api/messages/send` | POST | 404 | P1 |
| E025 | send_message_400_validation | `/api/messages/send` | POST | 400 | P1 |
| E026 | receive_messages_404_agent | `/api/messages/receive` | GET | 404 | P1 |
| E027 | broadcast_404_project | `/api/messages/broadcast` | POST | 404 | P1 |
| E028 | complete_message_404 | `/api/messages/{id}/complete` | POST | 404 | P1 |
| E029 | list_templates_success | `/api/templates` | GET | 200 | P1 |
| E030 | get_template_404 | `/api/templates/{id}` | GET | 404 | P1 |
| E031 | create_template_400 | `/api/templates` | POST | 400 | P1 |
| E032 | update_template_404 | `/api/templates/{id}` | PUT | 404 | P1 |
| E033 | delete_template_404 | `/api/templates/{id}` | DELETE | 404 | P1 |
| E034 | delete_template_400_system | `/api/templates/{id}` | DELETE | 400 | P1 |
| E035 | get_active_project_200_none | `/api/projects/active` | GET | 200 (null) | P1 |
| E036 | list_deleted_projects | `/api/projects/deleted` | GET | 200 | P1 |
| E037 | purge_deleted_project_404 | `/api/projects/{id}/purge` | DELETE | 404 | P1 |
| E038 | get_closeout_data_404 | `/api/projects/{id}/closeout-data` | GET | 404 | P1 |
| E039 | can_close_project_404 | `/api/projects/{id}/can-close` | GET | 404 | P1 |
| E040 | close_out_project_404 | `/api/projects/{id}/close-out` | POST | 404 | P1 |
| E041 | continue_working_404 | `/api/projects/{id}/continue` | POST | 404 | P1 |
| E042 | table_view_jobs_success | `/api/agent-jobs/table-view` | GET | 200 | P1 |
| E043 | update_agent_mission_404 | `/api/agent-jobs/{id}/mission` | PATCH | 404 | P1 |
| E044 | check_succession_status_404 | `/api/agent-jobs/{id}/succession-status` | GET | 404 | P1 |
| E045 | initiate_handover_404 | `/api/agent-jobs/{id}/handover` | POST | 404 | P1 |

### Category F: MCP Tool Integration Tests

These tests verify MCP tools correctly handle exceptions from services and return proper MCP error responses.

| Test ID | Test Name | MCP Tool | Expected Behavior | Priority |
|---------|-----------|----------|-------------------|----------|
| F001 | create_project_error | `create_project` | Returns MCP error content | P1 |
| F002 | get_project_error | `get_project` | Returns MCP error content | P1 |
| F003 | switch_project_error | `switch_project` | Returns MCP error content | P1 |
| F004 | complete_project_error | `complete_project` | Returns MCP error content | P1 |
| F005 | cancel_project_error | `cancel_project` | Returns MCP error content | P1 |
| F006 | restore_project_error | `restore_project` | Returns MCP error content | P1 |
| F007 | update_project_mission_error | `update_project_mission` | Returns MCP error content | P1 |
| F008 | spawn_agent_job_error | `spawn_agent_job` | Returns MCP error content | P1 |
| F009 | get_agent_mission_error | `get_agent_mission` | Returns MCP error content | P1 |
| F010 | acknowledge_job_error | `acknowledge_job` | Returns MCP error content | P1 |
| F011 | report_progress_error | `report_progress` | Returns MCP error content | P1 |
| F012 | complete_job_error | `complete_job` | Returns MCP error content | P1 |
| F013 | report_error_tool_error | `report_error` | Returns MCP error content | P1 |
| F014 | get_workflow_status_error | `get_workflow_status` | Returns MCP error content | P1 |
| F015 | get_pending_jobs_success | `get_pending_jobs` | Returns empty list (not error) | P1 |
| F016 | get_team_agents_error | `get_team_agents` | Returns MCP error content | P1 |
| F017 | create_successor_orchestrator_error | `create_successor_orchestrator` | Returns MCP error content | P1 |
| F018 | check_succession_status_error | `check_succession_status` | Returns MCP error content | P1 |
| F019 | send_message_error | `send_message` | Returns MCP error content | P1 |
| F020 | receive_messages_error | `receive_messages` | Returns MCP error content | P1 |
| F021 | broadcast_error | `broadcast` | Returns MCP error content | P1 |
| F022 | list_messages_error | `list_messages` | Returns MCP error content | P1 |
| F023 | complete_message_error | `complete_message` | Returns MCP error content | P1 |
| F024 | list_templates_error | `list_templates` | Returns MCP error content | P1 |
| F025 | create_template_error | `create_template` | Returns MCP error content | P1 |
| F026 | update_template_error | `update_template` | Returns MCP error content | P1 |
| F027 | get_orchestrator_instructions_error | `get_orchestrator_instructions` | Returns MCP error content | P1 |
| F028 | close_project_and_update_memory_error | `close_project_and_update_memory` | Returns MCP error content | P1 |
| F029 | fetch_context_error | `fetch_context` | Returns MCP error content | P2 |
| F030 | get_available_agents_success | `get_available_agents` | Returns agent list | P1 |

### Category G: Frontend E2E Tests (Playwright/Vitest)

| Test ID | Test Name | Component | Test Steps | Expected | Priority |
|---------|-----------|-----------|------------|----------|----------|
| G001 | create_project_error_display | CreateProject.vue | Submit invalid form | Error toast shown | P2 |
| G002 | project_not_found_error | ProjectDetail.vue | Navigate to deleted project | 404 page or redirect | P2 |
| G003 | activate_project_error | LaunchTab.vue | Click activate on invalid state | Error toast shown | P2 |
| G004 | launch_project_error | LaunchTab.vue | Click launch on staging project | Error toast shown | P2 |
| G005 | agent_spawn_error | AgentTableView.vue | Spawn agent fails | Error toast shown | P2 |
| G006 | agent_complete_blockers | JobsTab.vue | Complete with blockers | Blockers displayed | P2 |
| G007 | message_send_error | MessageCenter.vue | Send to deleted project | Error toast shown | P2 |
| G008 | template_save_error | TemplateEditor.vue | Save system template | Error displayed | P2 |
| G009 | template_delete_error | TemplateArchive.vue | Delete system template | Error displayed | P2 |
| G010 | succession_error | JobsTab.vue | Trigger succession fails | Error toast shown | P2 |
| G011 | project_complete_error | CompletionDialog.vue | Complete without summary | Validation error | P2 |
| G012 | cancel_staging_error | LaunchTab.vue | Cancel non-staging project | Error toast shown | P2 |
| G013 | restore_project_error | DeletedProjects.vue | Restore active project | Error toast shown | P2 |
| G014 | purge_project_error | DeletedProjects.vue | Purge non-deleted project | Error toast shown | P2 |
| G015 | workflow_status_error | StatusBoard.vue | Load deleted project status | Error handled | P2 |
| G016 | message_receive_error | MessageCenter.vue | Receive for deleted agent | Error handled | P2 |
| G017 | broadcast_no_agents | MessageCenter.vue | Broadcast to empty project | Error toast shown | P2 |
| G018 | template_limit_error | TemplateGrid.vue | Create 8th user template | Limit error shown | P2 |
| G019 | report_progress_error | AgentPanel.vue | Progress on deleted job | Error handled | P2 |
| G020 | closeout_error | CloseoutDialog.vue | Closeout incomplete project | Error displayed | P2 |

### Category H: WebSocket Event Tests

| Test ID | Test Name | Event Type | Scenario | Expected | Priority |
|---------|-----------|------------|----------|----------|----------|
| H001 | message_sent_event | message:sent | Send message | Event emitted with counters | P2 |
| H002 | message_received_event | message:received | Receive message | Event emitted to recipients | P2 |
| H003 | message_acknowledged_event | message:acknowledged | Acknowledge message | Event with updated counters | P2 |
| H004 | job_status_change_event | job:status_changed | Status update | Event emitted | P2 |
| H005 | job_progress_event | job:progress | Report progress | Event with percent | P2 |
| H006 | job_completed_event | job:completed | Complete job | Event emitted | P2 |
| H007 | project_status_event | project:status_changed | Activate project | Event emitted | P2 |
| H008 | mission_update_event | project:mission_updated | Update mission | Event emitted | P2 |
| H009 | error_event_not_emitted | - | Service raises exception | No WebSocket event | P2 |
| H010 | counter_consistency | message:* | Send+receive+ack | Counter values consistent | P2 |
| H011 | websocket_on_exception | - | Service fails mid-operation | WebSocket events partial | P3 |
| H012 | memory_update_event | product:memory_updated | Close project | Event emitted | P2 |

### Category I: Slash Command Tests

| Test ID | Test Name | Command | Scenario | Expected | Priority |
|---------|-----------|---------|----------|----------|----------|
| I001 | gil_activate_error | /gil_activate | Invalid project | Error response | P2 |
| I002 | gil_launch_error | /gil_launch | No active project | Error response | P2 |
| I003 | gil_handover_error | /gil_handover | Non-orchestrator | Error response | P2 |
| I004 | gil_activate_success | /gil_activate | Valid project | Project activated | P2 |
| I005 | gil_launch_success | /gil_launch | Staged project | Project launched | P2 |
| I006 | gil_handover_success | /gil_handover | Orchestrator job | Successor created | P2 |
| I007 | slash_command_auth_error | Any | Invalid API key | 401 response | P2 |
| I008 | slash_command_tenant_error | Any | Wrong tenant | Error response | P2 |

### Category J: Cross-Service Cascade Tests

| Test ID | Test Name | Scenario | Call Chain | Expected | Priority |
|---------|-----------|----------|------------|----------|----------|
| J001 | spawn_to_project_cascade | ProjectService raises | OrchestrationService.spawn_agent_job() -> ProjectService.get_project() | OrchestrationError wraps original | P2 |
| J002 | complete_to_message_cascade | MessageService raises | OrchestrationService.complete_job() -> MessageService.broadcast() | Job completes, warning logged | P2 |
| J003 | template_to_orch_cascade | TemplateService raises | OrchestrationService.spawn_agent_job() -> TemplateService.get_template() | TemplateNotFoundError propagates | P2 |
| J004 | tool_to_service_cascade | Any service raises | ToolAccessor -> ProjectService | MCP error response | P2 |
| J005 | endpoint_to_service_cascade | Any service raises | FastAPI endpoint -> ProjectService | HTTP error with status | P2 |
| J006 | multiple_services_partial_fail | First succeeds, second fails | spawn_agent -> send_message | First committed, second error | P2 |
| J007 | websocket_partial_fail | Service succeeds, WS fails | Any operation with WS event | Operation succeeds, WS logged | P2 |
| J008 | tenant_isolation_cascade | Cross-tenant attempt | Service A -> Service B with different tenant | All raise ResourceNotFoundError | P1 |
| J009 | db_transaction_rollback | DB constraint violation | Any create operation | No partial state | P2 |
| J010 | exception_context_preserved | Exception with context | Deep call chain | Context passed through | P2 |

---

## Recommended Test Execution Order

### Phase 1: Foundation (Day 1-2)
1. Run existing test suite to establish baseline
2. Execute Category A (ProjectService Unit) - 25 tests
3. Execute Category B (OrchestrationService Unit) - 35 tests
4. Execute Category C (MessageService Unit) - 15 tests
5. Execute Category D (TemplateService Unit) - 18 tests

### Phase 2: Integration (Day 3-4)
6. Execute Category E (API Endpoint Integration) - 45 tests
7. Execute Category F (MCP Tool Integration) - 30 tests
8. Execute Category J (Cross-Service Cascade) - 10 tests

### Phase 3: E2E Validation (Day 5)
9. Execute Category G (Frontend E2E) - 20 tests
10. Execute Category H (WebSocket Events) - 12 tests
11. Execute Category I (Slash Commands) - 8 tests

### Phase 4: Regression (Day 6)
12. Re-run full existing test suite
13. Manual exploratory testing on critical workflows
14. Performance verification (no degradation)

---

## Terminal Chain Prompts for Automated Execution

### Prompt 0480-TEST-A: ProjectService Unit Tests

```
You are executing test phase 0480-TEST-A: ProjectService Unit Tests.

MISSION:
Execute and validate all 25 ProjectService unit tests from the 0480 test plan.

EXECUTION STEPS:
1. Navigate to project root: F:\GiljoAI_MCP
2. Run tests: pytest tests/services/test_project_service_exceptions.py -v
3. If any tests fail, document the failure and continue
4. Run additional tests: pytest tests/services/test_project_service*.py -v
5. Document results in tests/reports/0480_TEST_A_RESULTS.md

SUCCESS CRITERIA:
- All A001-A025 tests pass
- No unexpected exceptions
- Exception context properly propagated
```

### Prompt 0480-TEST-B: OrchestrationService Unit Tests

```
You are executing test phase 0480-TEST-B: OrchestrationService Unit Tests.

MISSION:
Execute and validate all 35 OrchestrationService unit tests from the 0480 test plan.

EXECUTION STEPS:
1. Navigate to project root: F:\GiljoAI_MCP
2. Run tests: pytest tests/services/test_orchestration_service*.py -v
3. Run integration: pytest tests/integration/test_orchestration*.py -v
4. Document results in tests/reports/0480_TEST_B_RESULTS.md

SUCCESS CRITERIA:
- All B001-B035 tests pass
- spawn_agent_job correctly raises on project not found
- complete_job validates blockers
```

### Prompt 0480-TEST-C: MessageService Unit Tests

```
You are executing test phase 0480-TEST-C: MessageService Unit Tests.

MISSION:
Execute and validate all 15 MessageService unit tests from the 0480 test plan.

EXECUTION STEPS:
1. Navigate to project root: F:\GiljoAI_MCP
2. Run tests: pytest tests/services/test_message_service*.py -v
3. Run integration: pytest tests/integration/test_message*.py -v
4. Document results in tests/reports/0480_TEST_C_RESULTS.md

SUCCESS CRITERIA:
- All C001-C015 tests pass
- send_message raises ResourceNotFoundError on missing project
- receive_messages handles empty queue gracefully
```

### Prompt 0480-TEST-D: TemplateService Unit Tests

```
You are executing test phase 0480-TEST-D: TemplateService Unit Tests.

MISSION:
Execute and validate all 18 TemplateService unit tests from the 0480 test plan.

EXECUTION STEPS:
1. Navigate to project root: F:\GiljoAI_MCP
2. Run tests: pytest tests/services/test_template_service*.py -v
3. Run unit: pytest tests/unit/test_template*.py -v
4. Document results in tests/reports/0480_TEST_D_RESULTS.md

SUCCESS CRITERIA:
- All D001-D018 tests pass
- TemplateNotFoundError raised for missing templates
- System-managed templates protected
```

### Prompt 0480-TEST-E: API Endpoint Integration

```
You are executing test phase 0480-TEST-E: API Endpoint Integration Tests.

MISSION:
Execute and validate all 45 API endpoint integration tests from the 0480 test plan.

EXECUTION STEPS:
1. Ensure API server is running
2. Run tests: pytest tests/api/test_*_endpoints*.py -v
3. Run tests: pytest tests/integration/test_*_lifecycle*.py -v
4. Document HTTP status codes returned
5. Document results in tests/reports/0480_TEST_E_RESULTS.md

SUCCESS CRITERIA:
- All E001-E045 tests pass
- 404 returned for not found
- 400 returned for validation errors
- Proper error response body with error_code and message
```

### Prompt 0480-TEST-F: MCP Tool Integration

```
You are executing test phase 0480-TEST-F: MCP Tool Integration Tests.

MISSION:
Execute and validate all 30 MCP tool integration tests from the 0480 test plan.

EXECUTION STEPS:
1. Navigate to project root: F:\GiljoAI_MCP
2. Run tests: pytest tests/tools/test_tool_accessor*.py -v
3. Run tests: pytest tests/integration/test_mcp*.py -v
4. Verify MCP error responses have proper format
5. Document results in tests/reports/0480_TEST_F_RESULTS.md

SUCCESS CRITERIA:
- All F001-F030 tests pass
- MCP tools return error content (not raise exceptions)
- Error messages are user-friendly
```

### Prompt 0480-TEST-FULL: Complete Test Suite

```
You are executing test phase 0480-TEST-FULL: Complete Test Suite.

MISSION:
Execute the complete test suite and document results.

EXECUTION STEPS:
1. Navigate to project root: F:\GiljoAI_MCP
2. Run full suite: pytest tests/ -v --cov=src/giljo_mcp --cov-report=html
3. Generate coverage report
4. Document any failures
5. Create summary in tests/reports/0480_TEST_FULL_RESULTS.md

SUCCESS CRITERIA:
- >80% code coverage
- All critical (P1) tests pass
- No regressions from baseline
```

---

## Test Fixtures Required

### Database Fixtures

```python
@pytest.fixture
async def test_tenant_key():
    """Generate unique tenant key for test isolation"""
    return f"test_tenant_{uuid4().hex[:8]}"

@pytest.fixture
async def active_project(db_session, test_tenant_key):
    """Create an active project for testing"""
    from uuid import uuid4
    from src.giljo_mcp.models.projects import Project

    project = Project(
        id=str(uuid4()),
        name="Active Test Project",
        mission="Test mission",
        description="Test description",
        tenant_key=test_tenant_key,
        status="active"
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project

@pytest.fixture
async def inactive_project(db_session, test_tenant_key):
    """Create an inactive project for testing"""
    from uuid import uuid4
    from src.giljo_mcp.models.projects import Project

    project = Project(
        id=str(uuid4()),
        name="Inactive Test Project",
        mission="Test mission",
        description="Test description",
        tenant_key=test_tenant_key,
        status="inactive"
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project
```

### Service Fixtures

```python
@pytest.fixture
async def project_service_with_session(db_manager, tenant_manager, db_session):
    """ProjectService with injected test session"""
    return ProjectService(
        db_manager=db_manager,
        tenant_manager=tenant_manager,
        test_session=db_session
    )

@pytest.fixture
async def orchestration_service_with_session(db_manager, tenant_manager, db_session):
    """OrchestrationService with injected test session"""
    return OrchestrationService(
        db_manager=db_manager,
        tenant_manager=tenant_manager,
        test_session=db_session
    )
```

---

## Risk Assessment

### High Risk Areas
1. **ToolAccessor Delegation** - Must catch all service exceptions and convert to MCP responses
2. **Cross-Service Transactions** - Partial failures could leave inconsistent state
3. **WebSocket Events** - Exception in WS emission should not fail main operation
4. **Frontend Error Handling** - All API errors must be caught and displayed

### Medium Risk Areas
1. **Exception Context Propagation** - Context must survive re-wrapping
2. **Tenant Isolation** - Cross-tenant errors must not leak information
3. **Backward Compatibility** - Existing integrations expecting dict returns

### Low Risk Areas
1. **Unit Test Coverage** - Well-isolated service methods
2. **HTTP Status Codes** - FastAPI exception handlers straightforward
3. **Documentation** - Exception types well-documented in hierarchy

---

## Appendix A: Exception Handler Configuration

Verify these handlers are registered in api/app.py for proper HTTP status code mapping.

## Appendix B: MCP Error Response Format

All MCP tools should return errors with success=False and an error object containing code, message, and context.

## Appendix C: Files Modified in 0480 Series

1. src/giljo_mcp/services/project_service.py
2. src/giljo_mcp/services/orchestration_service.py
3. src/giljo_mcp/services/message_service.py
4. src/giljo_mcp/services/template_service.py
5. src/giljo_mcp/exceptions.py (exception hierarchy)
6. api/endpoints/projects/*.py (exception handlers)
7. api/endpoints/agent_jobs/*.py (exception handlers)
8. api/endpoints/templates/*.py (exception handlers)
9. api/endpoints/messages.py (exception handlers)

---

**Document Version:** 1.0
**Created:** January 2026
**Last Updated:** January 2026
