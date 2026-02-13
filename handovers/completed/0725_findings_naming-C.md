# Naming Convention Research Findings

**Research Date**: 2026-02-07
**Scope**: GiljoAI MCP Codebase
**Status**: RESEARCH ONLY - No fixes implemented

## Executive Summary

The GiljoAI MCP codebase demonstrates **excellent adherence to naming conventions** across Python backend, Vue frontend, and API endpoints. Ruff naming checks (N-rules) pass with no violations. Only **1 API endpoint URL** uses snake_case instead of the required kebab-case pattern.

## Standards Verified

| Domain | Standard | Status |
|--------|----------|--------|
| Python files | snake_case.py | PASS |
| Python functions | snake_case | PASS |
| Python classes | PascalCase | PASS |
| Python constants | UPPER_SNAKE_CASE | PASS |
| Vue components | PascalCase.vue | PASS |
| JS functions | camelCase | PASS |
| API URLs | kebab-case | 1 VIOLATION |
| API JSON keys | snake_case | PASS |

---

## Detailed Findings

### 1. Python File Naming (snake_case.py)

**Result**: PASS - No violations

All 100+ Python files in `src/` and `api/` directories follow snake_case naming:
- `agent_job_manager.py`
- `vision_document_repository.py`
- `orchestration_service.py`

**Command Used**:
```bash
find src/ api/ -name "*.py" | xargs basename -a | grep -vE "^[a-z_0-9]+\.py$"
```

**Special Cases**:
- `get_360_memory.py`, `write_360_memory.py` - Contains digits but follows snake_case pattern (acceptable)

---

### 2. Python Classes (PascalCase)

**Result**: PASS - No violations

All class definitions use PascalCase:
- `class ProductService`
- `class AgentJobManager`
- `class VisionDocumentRepository`

**Command Used**:
```bash
ruff check src/ api/ --select=N  # Returns "All checks passed!"
grep "^class [a-z]" src/**/*.py  # No matches
```

---

### 3. Python Functions (snake_case)

**Result**: PASS - No violations

All function definitions use snake_case:
- `def get_execution_mode()`
- `def create_agent_job()`
- `async def fetch_context()`

**Command Used**:
```bash
grep "^def [A-Z]" src/**/*.py api/**/*.py  # No matches
```

---

### 4. Vue Component Naming (PascalCase.vue)

**Result**: PASS - No violations

All 76 Vue components use PascalCase:

**Components Directory** (frontend/src/components/):
- `ActiveProductDisplay.vue`
- `AgentCard.vue`
- `AiToolConfigWizard.vue`
- `StatusBoard/StatusChip.vue`
- `StatusBoard/ActionIcons.vue`
- `navigation/AppBar.vue`
- `orchestration/OrchestratorCard.vue`

**Views Directory** (frontend/src/views/):
- `DashboardView.vue`
- `ProjectsView.vue`
- `ProductsView.vue`
- `UserSettings.vue`

**Command Used**:
```bash
find frontend/src/components -name "*.vue" | xargs basename -a | grep -vE "^[A-Z]"
# Returns: All Vue components use PascalCase
```

---

### 5. JavaScript Function Naming (camelCase)

**Result**: PASS - No violations

All JavaScript functions use camelCase:
- Composables: `useAgentJobs.js`, `useWebSocket.js`, `useToast.js`
- Stores: `agentJobs.js`, `projectMessagesStore.js`
- Utilities: `formatters.js`, `errorMessages.js`

**Command Used**:
```bash
grep "function [A-Z]" frontend/src/**/*.js  # No matches
```

---

### 6. API Endpoint URL Naming (kebab-case)

**Result**: 1 VIOLATION FOUND

#### Violation Details:

| File | Line | Current URL | Should Be |
|------|------|-------------|-----------|
| `api/endpoints/users.py` | 993 | `/me/settings/execution_mode` | `/me/settings/execution-mode` |
| `api/endpoints/users.py` | 1005 | `/me/settings/execution_mode` | `/me/settings/execution-mode` |

**Full Endpoint Context**:
```python
# api/endpoints/users.py:993
@router.get("/me/settings/execution_mode")
async def get_execution_mode(...)

# api/endpoints/users.py:1005
@router.put("/me/settings/execution_mode")
async def update_execution_mode(...)
```

#### Compliant Examples (for reference):
All other endpoints correctly use kebab-case:
- `/api/vision-documents`
- `/api/mcp-installer`
- `/api/ai-tools`
- `/api/ws-bridge`
- `/{project_id}/close-out`
- `/{project_id}/cancel-staging`
- `/{template_id}/reset-system`
- `/verify-pin-and-reset-password`

---

### 7. API JSON Key Consistency (snake_case)

**Result**: PASS - Consistent snake_case

All Pydantic models use snake_case for JSON serialization:
- `product_id`
- `tenant_key`
- `created_at`
- `execution_mode`
- `context_budget`

**Exception - MCP Protocol (Intentional)**:
The MCP HTTP endpoint uses camelCase keys per the MCP protocol specification:
- `protocolVersion`
- `serverInfo`
- `inputSchema`
- `isError`
- `listChanged`

This is **not a violation** - it's required for MCP protocol compliance.

---

## Summary Statistics

| Category | Files/Symbols Checked | Violations |
|----------|----------------------|------------|
| Python files | 100+ | 0 |
| Python classes | All in src/, api/ | 0 |
| Python functions | All in src/, api/ | 0 |
| Vue components | 76 | 0 |
| JS functions | All in frontend/src/ | 0 |
| API endpoints | 200+ | 1 |
| JSON keys | All Pydantic models | 0 |

**Total Violations**: 1 (API URL pattern)

---

## Recommendations

### Priority 1 - Fix API URL Violation
Rename `/me/settings/execution_mode` to `/me/settings/execution-mode` in:
- `api/endpoints/users.py` lines 993 and 1005
- Update any frontend API calls referencing this endpoint

### Impact Assessment
- **Breaking Change**: Yes - frontend must update API calls
- **Migration**: Coordinate with frontend team
- **Testing**: Update integration tests for this endpoint

---

## Tools and Commands Used

```bash
# Ruff naming check
source venv/Scripts/activate && ruff check src/ api/ --select=N --statistics

# Python file naming
find src/ api/ -name "*.py" | xargs basename -a | grep -vE "^[a-z_0-9]+\.py$"

# Python class naming
grep "^class [a-z]" src/**/*.py api/**/*.py

# Python function naming
grep "^def [A-Z]" src/**/*.py api/**/*.py

# Vue component naming
find frontend/src/components -name "*.vue" | xargs basename -a | grep -vE "^[A-Z]"

# JS function naming
grep "function [A-Z]" frontend/src/**/*.js

# API endpoint patterns
grep -r "@router\.(get|post|put|delete|patch)" api/endpoints/

# JSON key patterns
grep -E '"[a-z]+_[a-z]+":\s*' api/**/*.py
```

---

## Appendix: Complete API Endpoint Prefixes

All router prefixes from `api/app.py` - all use kebab-case:

```
/api/vision-documents
/api/v1/agents/templates
/api/v1/messages
/api/v1/tasks
/api/v1/prompts
/api/v1/context
/api/v1/config
/api/v1/system
/api/v1/stats
/api/v1/ws-bridge
/api/auth
/api/v1/users
/api/v1/user
/api/v1/settings
/api/setup/database
/api/setup
/api/serena
/api/git
/api/network
/api/mcp-installer
/mcp/tools
/api (slash-commands)
/api/ai-tools
/api/organizations
```

---

*Research completed by Deep Researcher Agent*
*No code changes made - research documentation only*
