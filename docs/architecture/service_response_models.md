# Service Layer Response Models

**Handover:** 0730a Design Response Models
**Created:** 2026-02-07
**Purpose:** Document all service method return types for migration from dict wrappers to Pydantic models with exception-based error handling

---

## Overview

This document catalogs all 117 dict wrapper instances across 12 services (verified 2026-02-08), specifying:
- Current return pattern (dict wrapper)
- Target return type (domain model or Pydantic schema)
- Required exceptions for error cases
- HTTP status code mapping

### Migration Pattern Summary

**Current (Anti-Pattern):**
```python
def get_resource(self, id: str) -> dict[str, Any]:
    resource = await self.session.get(Resource, id)
    if not resource:
        return {"success": False, "error": "Resource not found"}
    return {"success": True, "data": resource}
```

**Target (Exception-Based):**
```python
def get_resource(self, id: str) -> Resource:
    resource = await self.session.get(Resource, id)
    if not resource:
        raise ResourceNotFoundError(message="Resource not found", context={"id": id})
    return resource
```

---

## Tier 1 Services (69 instances - 57%)

### OrgService (33 instances)
**Location:** `src/giljo_mcp/services/org_service.py`
**Pattern:** Pure dict wrapper (no exceptions raised)

| Method | Current Return | Target Return | Exceptions | HTTP |
|--------|---------------|---------------|------------|------|
| `create_organization(name, owner_id, tenant_key, slug?, settings?)` | `{"success": bool, "data": Organization}` | `Organization` | `AlreadyExistsError` (slug exists) | 409 |
| `get_organization(org_id)` | `{"success": bool, "data": Organization}` | `Organization` | `ResourceNotFoundError` | 404 |
| `get_organization_by_slug(slug)` | `{"success": bool, "data": Organization}` | `Organization` | `ResourceNotFoundError` | 404 |
| `update_organization(org_id, name?, settings?)` | `{"success": bool, "data": Organization}` | `Organization` | `ResourceNotFoundError` | 404 |
| `delete_organization(org_id)` | `{"success": bool, "data": {"deleted": True}}` | `DeleteResult` | `ResourceNotFoundError` | 404 |
| `invite_member(org_id, user_id, role, invited_by, tenant_key)` | `{"success": bool, "data": OrgMembership}` | `OrgMembership` | `AlreadyExistsError`, `ValidationError` | 409, 400 |
| `remove_member(org_id, user_id)` | `{"success": bool, "data": {"removed": True}}` | `DeleteResult` | `ResourceNotFoundError`, `AuthorizationError` | 404, 403 |
| `change_member_role(org_id, user_id, new_role)` | `{"success": bool, "data": OrgMembership}` | `OrgMembership` | `ResourceNotFoundError`, `AuthorizationError`, `ValidationError` | 404, 403, 400 |
| `transfer_ownership(org_id, current_owner_id, new_owner_id)` | `{"success": bool, "data": {"transferred": True}}` | `TransferResult` | `AuthorizationError`, `ResourceNotFoundError` | 403, 404 |
| `list_members(org_id)` | `{"success": bool, "data": list[OrgMembership]}` | `list[OrgMembership]` | `DatabaseError` | 500 |
| `get_user_organizations(user_id)` | `{"success": bool, "data": list[Organization]}` | `list[Organization]` | `DatabaseError` | 500 |
| `get_user_role(org_id, user_id)` | `str \| None` | `str \| None` | None | N/A |
| `can_manage_members(org_id, user_id)` | `bool` | `bool` | None | N/A |
| `can_edit_org(org_id, user_id)` | `bool` | `bool` | None | N/A |
| `can_delete_org(org_id, user_id)` | `bool` | `bool` | None | N/A |
| `can_view_org(org_id, user_id)` | `bool` | `bool` | None | N/A |

**Error Cases:**
- Slug already exists: `AlreadyExistsError` (409)
- Organization not found: `ResourceNotFoundError` (404)
- User not a member: `ResourceNotFoundError` (404)
- Only owner can transfer: `AuthorizationError` (403)
- Cannot remove owner: `AuthorizationError` (403)
- Invalid role: `ValidationError` (400)

---

### UserService (19 instances)
**Location:** `src/giljo_mcp/services/user_service.py`
**Pattern:** HYBRID - raises exceptions for errors, dict wrapper for success

| Method | Current Return | Target Return | Exceptions | HTTP |
|--------|---------------|---------------|------------|------|
| `list_users()` | `{"success": True, "data": list[dict]}` | `list[UserResponse]` | `DatabaseError` | 500 |
| `get_user(user_id, include_all_tenants?)` | `{"success": True, "user": dict}` | `UserResponse` | `ResourceNotFoundError` | 404 |
| `create_user(username, email?, full_name?, password?, role?, is_active?)` | `{"success": True, "user": dict}` | `UserResponse` | `ValidationError` (duplicate username/email) | 400 |
| `update_user(user_id, updates)` | `{"success": True, "user": dict}` | `UserResponse` | `ResourceNotFoundError`, `ValidationError` | 404, 400 |
| `delete_user(user_id)` | `{"success": True, "deleted": True}` | `DeleteResult` | `ResourceNotFoundError` | 404 |
| `change_role(user_id, new_role)` | `{"success": True, "user": dict}` | `UserResponse` | `ResourceNotFoundError`, `ValidationError` | 404, 400 |
| `change_password(user_id, old_password, new_password, is_admin?)` | `{"success": True, "message": str}` | `OperationResult` | `ResourceNotFoundError`, `AuthenticationError` | 404, 401 |
| `reset_password(user_id, new_password, is_admin?)` | `{"success": True, "message": str}` | `OperationResult` | `ResourceNotFoundError` | 404 |
| `check_username_exists(username)` | `{"success": True, "exists": bool}` | `bool` | None | N/A |
| `check_email_exists(email)` | `{"success": True, "exists": bool}` | `bool` | None | N/A |
| `verify_password(user_id, password)` | `{"success": True, "verified": bool}` | `bool` | `ResourceNotFoundError` | 404 |
| `get_field_priority_config(user_id)` | `{"success": True, "config": dict}` | `FieldPriorityConfig` | `ResourceNotFoundError` | 404 |
| `update_field_priority_config(user_id, config)` | `{"success": True, "message": str}` | `OperationResult` | `ResourceNotFoundError`, `ValidationError` | 404, 400 |
| `reset_field_priority_config(user_id)` | `{"success": True, "message": str}` | `OperationResult` | `ResourceNotFoundError` | 404 |
| `get_depth_config(user_id)` | `{"success": True, "config": dict}` | `DepthConfig` | `ResourceNotFoundError` | 404 |
| `update_depth_config(user_id, config)` | `{"success": True, "message": str}` | `OperationResult` | `ResourceNotFoundError`, `ValidationError` | 404, 400 |
| `get_execution_mode(user_id)` | `{"success": True, "execution_mode": str}` | `str` | `ResourceNotFoundError` | 404 |
| `update_execution_mode(user_id, mode)` | `{"success": True, "execution_mode": str}` | `str` | `ResourceNotFoundError`, `ValidationError` | 404, 400 |

**Note:** UserService already raises `ResourceNotFoundError` and `ValidationError` in _impl methods. Migration focuses on removing dict wrappers from success paths.

---

### ProductService (17 instances)
**Location:** `src/giljo_mcp/services/product_service.py`
**Pattern:** HYBRID - raises exceptions for errors, dict wrapper for success

| Method | Current Return | Target Return | Exceptions | HTTP |
|--------|---------------|---------------|------------|------|
| `create_product(name, description?, project_path?, config_data?, product_memory?, target_platforms?)` | `{"success": True, "product_id": str, ...}` | `ProductResponse` | `ValidationError` (name exists, invalid platforms) | 400 |
| `get_product(product_id, include_metrics?)` | `{"success": True, "product": dict}` | `ProductResponse` | `ResourceNotFoundError` | 404 |
| `list_products()` | `{"success": True, "products": list[dict]}` | `list[ProductResponse]` | `DatabaseError` | 500 |
| `update_product(product_id, updates)` | `{"success": True, "product": dict}` | `ProductResponse` | `ResourceNotFoundError`, `ValidationError` | 404, 400 |
| `update_quality_standards(product_id, standards)` | `{"success": True, "product": dict}` | `ProductResponse` | `ResourceNotFoundError` | 404 |
| `activate_product(product_id)` | `{"success": True, "product": dict}` | `ProductResponse` | `ResourceNotFoundError` | 404 |
| `deactivate_product(product_id)` | `{"success": True, "product": dict}` | `ProductResponse` | `ResourceNotFoundError` | 404 |
| `delete_product(product_id)` | `{"success": True, "message": str, "deleted_at": str}` | `DeleteResult` | `ResourceNotFoundError` | 404 |
| `restore_product(product_id)` | `{"success": True, "product": dict}` | `ProductResponse` | `ResourceNotFoundError` | 404 |
| `list_deleted_products()` | `{"success": True, "products": list[dict]}` | `list[ProductResponse]` | `DatabaseError` | 500 |
| `get_active_product()` | `{"success": True, "product": dict \| None}` | `ProductResponse \| None` | None | N/A |
| `get_product_statistics(product_id)` | `{"success": True, "statistics": dict}` | `ProductStatistics` | `ResourceNotFoundError` | 404 |
| `get_cascade_impact(product_id)` | `{"success": True, "impact": dict}` | `CascadeImpact` | `ResourceNotFoundError` | 404 |
| `update_git_integration(product_id, settings)` | `{"success": True, "settings": dict}` | `GitIntegrationSettings` | `ResourceNotFoundError` | 404 |
| `upload_vision_document(product_id, content, filename, summary_level?)` | `{"success": True, "document_id": str, ...}` | `VisionUploadResult` | `ResourceNotFoundError`, `VisionError` | 404, 400 |
| `validate_project_path(path)` | `{"success": True, "valid": bool, "message": str}` | `PathValidationResult` | None | N/A |
| `purge_expired_deleted_products()` | `{"success": True, "purged_count": int, "products": list}` | `PurgeResult` | `DatabaseError` | 500 |

---

## Tier 2 Services (30 instances - 26%)

### TaskService (14 instances)
**Location:** `src/giljo_mcp/services/task_service.py`
**Pattern:** HYBRID

| Method | Current Return | Target Return | Exceptions | HTTP |
|--------|---------------|---------------|------------|------|
| `log_task(content, category?, priority?, project_id?, product_id?, tenant_key?)` | `{"success": True, "task_id": str, ...}` | `TaskResponse` | `ValidationError` (missing product_id) | 400 |
| `create_task(title, description, priority?, assigned_to?, project_id?, product_id?, tenant_key?)` | `{"success": True, "task_id": str}` | `TaskResponse` | `ValidationError` | 400 |
| `list_tasks(filters)` | `{"success": True, "tasks": list, "count": int}` | `TaskListResponse` | `DatabaseError` | 500 |
| `update_task(task_id, updates)` | `{"success": True, "task_id": str, "updated_fields": list}` | `TaskUpdateResult` | `ResourceNotFoundError` | 404 |
| `assign_task(task_id, agent_name)` | `{"success": True, ...}` | `TaskResponse` | `ResourceNotFoundError` | 404 |
| `complete_task(task_id)` | `{"success": True, ...}` | `TaskResponse` | `ResourceNotFoundError` | 404 |
| `get_task(task_id)` | `{"success": True, "data": dict}` | `TaskResponse` | `ResourceNotFoundError` | 404 |
| `delete_task(task_id)` | `{"success": True, "message": str}` | `DeleteResult` | `ResourceNotFoundError` | 404 |
| `convert_to_project(task_id)` | `{"success": True, "project_id": str, ...}` | `ConversionResult` | `ResourceNotFoundError` | 404 |
| `change_status(task_id, new_status)` | `{"success": True, ...}` | `TaskResponse` | `ResourceNotFoundError`, `ValidationError` | 404, 400 |
| `get_summary(product_id?, tenant_key?)` | `{"success": True, "summary": dict}` | `TaskSummary` | `DatabaseError` | 500 |
| `can_modify_task(task_id, user_id)` | `bool` | `bool` | None | N/A |
| `can_delete_task(task_id, user_id)` | `bool` | `bool` | None | N/A |

---

### ProjectService (8 instances)
**Location:** `src/giljo_mcp/services/project_service.py`
**Pattern:** HYBRID
**Note:** Verified count excludes docstring examples

| Method | Current Return | Target Return | Exceptions | HTTP |
|--------|---------------|---------------|------------|------|
| `create_project(name, mission, description?, product_id?, tenant_key?, status?)` | `{"success": True, "project_id": str, ...}` | `ProjectResponse` | `BaseGiljoError` | 500 |
| `get_project(project_id)` | `{"success": True, "data": dict}` | `ProjectResponse` | `ResourceNotFoundError` | 404 |
| `get_active_project(product_id)` | `{"success": True, "data": dict \| None}` | `ProjectResponse \| None` | None | N/A |
| `list_projects(product_id?, include_completed?)` | `{"success": True, "projects": list}` | `list[ProjectResponse]` | `DatabaseError` | 500 |
| `update_project_mission(project_id, mission)` | `{"success": True, "data": dict}` | `ProjectResponse` | `ResourceNotFoundError` | 404 |
| `complete_project(project_id, summary?)` | `{"success": True, "data": dict}` | `ProjectResponse` | `ResourceNotFoundError`, `ProjectStateError` | 404, 400 |
| `cancel_project(project_id, reason?)` | `{"success": True, "data": dict}` | `ProjectResponse` | `ResourceNotFoundError` | 404 |
| `activate_project(project_id)` | `{"success": True, "data": dict}` | `ProjectResponse` | `ResourceNotFoundError`, `ProjectStateError` | 404, 400 |
| `deactivate_project(project_id)` | `{"success": True, "data": dict}` | `ProjectResponse` | `ResourceNotFoundError` | 404 |

---

### MessageService (8 instances)
**Location:** `src/giljo_mcp/services/message_service.py`
**Pattern:** HYBRID

| Method | Current Return | Target Return | Exceptions | HTTP |
|--------|---------------|---------------|------------|------|
| `send_message(to_agents, content, project_id, message_type?, priority?, from_agent?, tenant_key?)` | `{"success": True, "data": {"message_id": str, ...}}` | `SendMessageResult` | `ResourceNotFoundError` (project) | 404 |
| `broadcast(content, project_id, from_agent?, tenant_key?)` | `{"success": True, "data": dict}` | `BroadcastResult` | `ResourceNotFoundError` | 404 |
| `broadcast_to_project(content, project_id, from_agent?)` | `{"success": True, "data": dict}` | `BroadcastResult` | `ResourceNotFoundError` | 404 |
| `get_messages(agent_id, project_id)` | `{"success": True, "data": {"messages": list, "count": int}}` | `MessageListResult` | `ResourceNotFoundError` | 404 |
| `receive_messages(agent_id, project_id, mark_read?)` | `{"success": True, "messages": list, "count": int}` | `MessageListResult` | None | N/A |
| `list_messages(project_id, filters?)` | `{"success": True, "messages": list, "count": int}` | `MessageListResult` | `DatabaseError` | 500 |
| `complete_message(message_id)` | `{"success": True, "data": dict}` | `MessageResponse` | `ResourceNotFoundError` | 404 |
| `acknowledge_message(message_id, agent_id)` | `{"success": True, "data": dict}` | `MessageResponse` | `ResourceNotFoundError` | 404 |

---

## Tier 3 Services (18 instances - 15%)

### OrchestrationService (6 instances)
**Location:** `src/giljo_mcp/services/orchestration_service.py`
**Pattern:** HYBRID

| Method | Current Return | Target Return | Exceptions | HTTP |
|--------|---------------|---------------|------------|------|
| `spawn_agent_job(agent_role, project_id, mission, ...)` | `{"success": True, "job_id": str, ...}` | `SpawnResult` | `AgentCreationError`, `ResourceNotFoundError` | 500, 404 |
| `get_agent_mission(job_id, tenant_key)` | `{"success": True, "mission": str, ...}` | `MissionResponse` | `ResourceNotFoundError` | 404 |
| `update_agent_mission(job_id, mission_update)` | `{"success": True, "job_id": str, "mission_updated": bool}` | `MissionUpdateResult` | `ResourceNotFoundError` | 404 |
| `get_orchestrator_instructions(orchestrator_id, tenant_key)` | `{"success": True, "instructions": str, ...}` | `InstructionsResponse` | `ResourceNotFoundError` | 404 |
| `create_successor_orchestrator(current_orchestrator_id, handover_summary)` | `{"success": True, "successor_id": str, ...}` | `SuccessionResult` | `OrchestrationError` | 500 |
| `check_succession_status(orchestrator_id)` | `{"success": True, "status": dict}` | `SuccessionStatus` | `ResourceNotFoundError` | 404 |

---

### ContextService (4 instances)
**Location:** `src/giljo_mcp/services/context_service.py`
**Pattern:** Dict wrapper only

| Method | Current Return | Target Return | Exceptions | HTTP |
|--------|---------------|---------------|------------|------|
| `get_context_index(product_id)` | `{"success": True, "index": dict}` | `ContextIndex` | None | N/A |
| `get_vision(product_id)` | `{"success": True, "vision": dict}` | `VisionContext` | `ResourceNotFoundError` | 404 |
| `get_vision_index(product_id)` | `{"success": True, "index": dict}` | `VisionIndex` | None | N/A |
| `get_product_settings(product_id)` | `{"success": True, "settings": dict}` | `ProductSettings` | `ResourceNotFoundError` | 404 |

---

### ConsolidationService (4 instances)
**Location:** `src/giljo_mcp/services/consolidation_service.py`
**Pattern:** Dict wrapper only

| Method | Current Return | Target Return | Exceptions | HTTP |
|--------|---------------|---------------|------------|------|
| `consolidate_vision_documents(product_id, tenant_key)` | `{"success": True, "aggregate": dict, ...}` | `ConsolidationResult` | `ResourceNotFoundError`, `ValidationError` | 404, 400 |

---

### AgentJobManager (4 instances)
**Location:** `src/giljo_mcp/services/agent_job_manager.py`
**Pattern:** Dict wrapper only

| Method | Current Return | Target Return | Exceptions | HTTP |
|--------|---------------|---------------|------------|------|
| `spawn_agent(...)` | `{"success": True, "job_id": str, ...}` | `SpawnResult` | `AgentCreationError` | 500 |
| `update_agent_status(job_id, status)` | `{"success": True, "status": str}` | `StatusUpdateResult` | `ResourceNotFoundError` | 404 |
| `update_agent_progress(job_id, progress)` | `{"success": True, "progress": int}` | `ProgressUpdateResult` | `ResourceNotFoundError` | 404 |
| `complete_job(job_id, result?)` | `{"success": True, "job_id": str, ...}` | `CompletionResult` | `ResourceNotFoundError` | 404 |

---

### VisionSummarizer (0 instances)
**Location:** `src/giljo_mcp/services/vision_summarizer.py`
**Pattern:** No dict wrappers (returns processed data directly)

| Method | Current Return | Target Return | Exceptions | HTTP |
|--------|---------------|---------------|------------|------|
| `summarize(content, level)` | `str` (summary text) | `str` | `VisionError` | 400 |
| `summarize_multi_level(content)` | `dict[str, str]` (level -> summary) | `MultiLevelSummary` | `VisionError` | 400 |

---

### TemplateService (4 instances)
**Location:** `src/giljo_mcp/services/template_service.py`
**Pattern:** HYBRID

| Method | Current Return | Target Return | Exceptions | HTTP |
|--------|---------------|---------------|------------|------|
| `list_templates(filters?)` | `{"success": True, "templates": list, "count": int}` | `TemplateListResult` | `DatabaseError` | 500 |
| `get_template(template_id)` | `{"success": True, "template": dict}` | `TemplateResponse` | `TemplateNotFoundError` | 404 |
| `create_template(name, content, role?, category?, ...)` | `{"success": True, "template_id": str, ...}` | `TemplateResponse` | `ValidationError` | 400 |
| `update_template(template_id, updates)` | `{"success": True, "template": dict}` | `TemplateResponse` | `TemplateNotFoundError`, `ValidationError` | 404, 400 |

---

## Pydantic Response Schema Definitions

### Common Result Types

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class DeleteResult(BaseModel):
    """Standard delete operation result."""
    deleted: bool = True
    deleted_at: Optional[datetime] = None

class OperationResult(BaseModel):
    """Generic operation success result."""
    message: str

class TransferResult(BaseModel):
    """Ownership transfer result."""
    transferred: bool = True
    from_user_id: str
    to_user_id: str
```

### Service-Specific Response Types

Response schemas should be defined in `api/schemas/` following existing patterns:
- `api/schemas/org.py` - Organization response schemas
- `api/schemas/user.py` - User response schemas
- `api/schemas/product.py` - Product response schemas
- etc.

---

## Migration Priority

### Phase 0730b: Tier 1 Services (69 instances)
1. **OrgService** (33) - Pure dict wrapper, highest impact
2. **UserService** (19) - Hybrid, remove success wrappers
3. **ProductService** (17) - Hybrid, remove success wrappers

### Phase 0730c: Tier 2 Services (31 instances)
1. **TaskService** (14)
2. **ProjectService** (9)
3. **MessageService** (8)

### Phase 0730d: Tier 3 Services (22 instances)
1. **OrchestrationService** (6)
2. **ContextService** (4)
3. **ConsolidationService** (4)
4. **AgentJobManager** (4)
5. **TemplateService** (4)

---

## Validation Checklist for 0730b

- [ ] All methods return domain models or Pydantic schemas (not dicts)
- [ ] Error cases raise appropriate domain exceptions
- [ ] No `{"success": True/False, ...}` patterns remain
- [ ] Tests updated to expect exceptions instead of checking `result["success"]`
- [ ] API endpoints updated to let exceptions propagate

---

**Document Version:** 1.1
**Last Updated:** 2026-02-08
**Verified:** Instance counts validated via AST-based search
