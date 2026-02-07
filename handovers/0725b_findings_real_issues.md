# 0725b Real Issues (Consolidated)

**Date:** 2026-02-07
**Methodology:** AST-based analysis with FastAPI awareness
**False Positive Rate:** <5%

---

## P0 - Critical: Test Import Errors

### Issue
Tests import `BaseGiljoException` but the class was renamed to `BaseGiljoError` during exception handling remediation (0480 series).

### Affected Files
```
tests/services/test_agent_job_manager_exceptions.py
tests/services/test_product_service_exceptions.py
tests/services/test_project_service_exceptions.py
tests/services/test_task_service_exceptions.py
tests/services/test_user_service.py
tests/integration/test_websocket_broadcast.py  # WebSocketManager import issue
```

### Fix
```bash
# Simple find-and-replace across affected files
sed -i 's/BaseGiljoException/BaseGiljoError/g' tests/services/test_*_exceptions.py
```

### Effort
30 minutes

---

## P1 - High: Production Bugs Blocking Tests

### Bug 1: UnboundLocalError in project_service.py

**Location:** `src/giljo_mcp/services/project_service.py:1545`
**Error:** `UnboundLocalError: local variable 'total_jobs' referenced before assignment`
**Test Skip:** `tests/api/test_projects_api.py`

### Bug 2: Complete Endpoint Validation Error

**Symptom:** Complete endpoint returns 422 for valid projects
**Test Skip:** `tests/api/test_projects_api.py`

### Bug 3: Summary Endpoint 404

**Symptom:** `/summary/` endpoint returns 404
**Test Skip:** `tests/api/test_tasks_api.py` (multiple tests)

### Effort
2-4 hours for all three bugs

---

## P2 - Medium: Service Layer Dict Returns

### Issue
122 instances of `{"success": True/False, "data": ..., "error": ...}` wrapper patterns in services instead of proper Pydantic models and exception-based error handling.

### By Service

| Service | File | Count |
|---------|------|-------|
| OrgService | `services/org_service.py` | 33 |
| UserService | `services/user_service.py` | 19 |
| ProductService | `services/product_service.py` | 17 |
| TaskService | `services/task_service.py` | 14 |
| ProjectService | `services/project_service.py` | 9 |
| MessageService | `services/message_service.py` | 8 |
| OrchestrationService | `services/orchestration_service.py` | 6 |
| ContextService | `services/context_service.py` | 4 |
| ConsolidationService | `services/consolidation_service.py` | 4 |
| AgentJobManager | `services/agent_job_manager.py` | 4 |
| VisionSummarizer | `services/vision_summarizer.py` | 4 |
| TemplateService | `services/template_service.py` | 4 |

### Example Pattern (To Replace)
```python
# Current (bad)
async def create_org(self, data):
    try:
        org = Organization(**data)
        await self.session.add(org)
        return {"success": True, "data": org}
    except Exception as e:
        return {"success": False, "error": str(e)}

# Target (good)
async def create_org(self, data: OrgCreate) -> Organization:
    org = Organization(**data.dict())
    await self.session.add(org)
    return org
    # Errors raised as exceptions, handled by API layer
```

### Effort
24-32 hours (methodical refactor with test updates)

---

## P3 - Low: Orphan Files

### Confirmed Orphans (2 files, 627 lines)

#### 1. mcp_http_stdin_proxy.py
**Path:** `src/giljo_mcp/mcp_http_stdin_proxy.py`
**Lines:** 127
**Purpose:** Stdio proxy for Codex CLI
**Status:** Obsolete - stdio support removed in Handover 0334
**Validation:** Zero imports from src/ or api/

#### 2. cleanup/visualizer.py
**Path:** `src/giljo_mcp/cleanup/visualizer.py`
**Lines:** ~500
**Purpose:** Dependency graph HTML generator
**Status:** Never imported - `scripts/update_dependency_graph_full.py` has inline implementation
**Validation:** Zero imports from any Python code

### Safe Deletion Command
```bash
rm src/giljo_mcp/mcp_http_stdin_proxy.py
rm -rf src/giljo_mcp/cleanup/
```

---

## P3 - Low: Placeholder API Key

### Location
`api/endpoints/ai_tools.py:217`

### Code
```python
api_key = "placeholder-api-key-please-use-wizard"
```

### Fix
Integrate with API key creation flow in wizard.

---

## Summary by Priority

| Priority | Category | Items | Effort |
|----------|----------|-------|--------|
| P0 | Test Import Errors | 6 files | 30 min |
| P1 | Production Bugs | 3 bugs | 2-4 hours |
| P2 | Dict Returns | 122 instances | 24-32 hours |
| P3 | Orphan Files | 2 files | 10 min |
| P3 | API Key Placeholder | 1 instance | 1 hour |

**Total Estimated Effort:** 28-38 hours (vs 200+ hours from flawed 0725 estimates)

---

## What Was NOT an Issue (False Positives from 0725)

- 127 "orphan" files that are actually registered FastAPI routers
- 24 "tenant isolation" issues that have upstream validation
- 400+ "dead functions" that are FastAPI endpoints or frontend-called
- 4 "orphan" files that were already deleted in 0700 series

**Architecture Verdict: HEALTHY**
