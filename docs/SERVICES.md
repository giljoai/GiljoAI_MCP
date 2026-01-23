# Service Layer Architecture

**Version**: v3.1+ (Post-Remediation)
**Last Updated**: 2025-11-20

## Overview

GiljoAI MCP uses a service layer architecture to separate business logic from API endpoints. All services follow consistent patterns for database access, multi-tenant isolation, validation, and real-time updates.

**Compliance Status**: 95% service layer compliance (42/44 violations eliminated as of Handover 0322)

---

## Services Inventory

### UserService
**Location**: `src/giljo_mcp/services/user_service.py`
**Purpose**: User management, authentication, role management, and configuration management
**Methods**: 16 total
- CRUD: `list_users`, `get_user`, `create_user`, `update_user`, `delete_user`
- Authentication: `change_password`, `reset_password`, `verify_password`
- Validation: `check_username_exists`, `check_email_exists`
- Role Management: `change_role`
- Configuration: `get_field_priority_config`, `update_field_priority_config`, `reset_field_priority_config`, `get_depth_config`, `update_depth_config`

**Key Features**:
- Soft delete pattern (is_active flag)
- Bcrypt password hashing
- Multi-tenant isolation on all queries
- WebSocket event emission for user changes
- Context Management v2.0 config handling

### AuthService
**Location**: `src/giljo_mcp/services/auth_service.py`
**Purpose**: Authentication flows, API key management, user registration, and setup
**Methods**: 8 total
- Authentication: `authenticate_user`, `update_last_login`, `check_setup_state`
- API Keys: `list_api_keys`, `create_api_key`, `revoke_api_key`
- Registration: `register_user`, `create_first_admin`

**Key Features**:
- JWT token generation
- API key generation with bcrypt hashing
- First admin creation flow with race condition protection
- Setup state management
- Cross-tenant operations (login can span tenants)

### TaskService
**Location**: `src/giljo_mcp/services/task_service.py`
**Purpose**: Task lifecycle management with complex operations
**Methods**: Enhanced with 5 new methods + 2 helpers
- CRUD: `get_task`, `list_tasks`, `create_task`, `update_task`, `delete_task`
- Business Logic: `convert_to_project`, `change_status`, `get_summary`
- Permission Helpers: `can_modify_task`, `can_delete_task`

**Key Features**:
- Task-to-project conversion with subtask handling
- Automatic timestamp management on status changes
- Permission-based access control
- Aggregated statistics and reporting

### MessageService
**Location**: `src/giljo_mcp/services/message_service.py`
**Purpose**: Message handling and communication queue management
**Methods**: Message CRUD and queue operations
- Message Management: `create_message`, `get_messages`, `mark_as_read`
- Queue Operations: `enqueue_message`, `dequeue_message`, `get_queue_status`

**Key Features**:
- Agent-to-agent message routing
- Message prioritization and queuing
- Read/unread tracking
- WebSocket notifications for new messages

#### Counter Updates (Handover 0387f)

When messages are sent/received/acknowledged, counter columns are updated:
- `send_message()` → Increments sender's `messages_sent_count`, recipient's `messages_waiting_count`
- `acknowledge_message()` → Decrements `messages_waiting_count`, increments `messages_read_count`

#### DEPRECATED: JSONB Messages Array

The `AgentExecution.messages` JSONB column is deprecated as of v3.2 (Handover 0387i).
- Do NOT write to this column
- Do NOT read from this column
- Use counter columns instead
- Column will be removed in v4.0

---

## Core Services

### **ProductService** (`src/giljo_mcp/services/product_service.py`)

**Purpose**: Product and vision document management with chunked uploads

**Key Methods**:
- `create_product(product_data)` - Create new product with config_data
- `upload_vision_document(product_id, content)` - Upload with chunking (<25K tokens per chunk)
- `activate_product(product_id)` - Set as active (Single Active Product constraint)
- `deactivate_product(product_id)` - Deactivate product
- `get_product_config(product_id)` - Retrieve config_data (JSONB)

**Vision Upload Chunking** (Handover 0500):
```python
# Automatic chunking for large vision documents
max_chunk_size = 25000  # tokens
chunks = []
current_chunk = ""

for line in vision_content.split('\n'):
    if len(current_chunk) + len(line) > max_chunk_size:
        chunks.append(current_chunk)
        current_chunk = line
    else:
        current_chunk += line + '\n'

chunks.append(current_chunk)  # Last chunk
```

**Multi-Tenant Isolation**:
```python
from src.giljo_mcp.services.product_service import ProductService

service = ProductService(session, tenant_key="user123")
product = await service.create_product({
    "name": "My Product",
    "description": "Product description",
    "config_data": {"key": "value"}  # JSONB field
})
```

---

### **ProjectService** (`src/giljo_mcp/services/project_service.py`)

**Purpose**: Project lifecycle operations (activate, deactivate, launch, summary)

**Key Methods**:
- `create_project(project_data)` - Create new project
- `activate_project(project_id)` - Set as active (Single Active Project constraint)
- `deactivate_project(project_id)` - Deactivate project
- `deactivate_all_projects_except(project_id)` - Enforce single active project
- `get_project_summary(project_id)` - Generate project summary
- `launch_orchestrator(project_id, mission)` - Launch orchestrator for project

**Single Active Project Pattern** (Handover 0050):
```python
from src.giljo_mcp.services.project_service import ProjectService

service = ProjectService(session, tenant_key="user123")

# Activate project (automatically deactivates others)
await service.activate_project(project_id)

# Check active project
active_project = await service.get_active_project()

# Get project summary
summary = await service.get_project_summary(project_id)
# Returns: {
#   "total_agents": 12,
#   "completed_agents": 8,
#   "success_rate": 0.75,
#   "time_spent_hours": 24.5
# }
```

**Lifecycle State Machine**:
```
Created → Active → Paused → Active → Completed
         ↓         ↓
       Deleted   Deleted
```

---

### **OrchestrationService** (`src/giljo_mcp/services/orchestration_service.py`)

**Purpose**: Context tracking, succession management, orchestrator coordination, agent spawning

**Note**: As of Handovers 0450-0452 (Jan 2026), all orchestration logic from `orchestrator.py` has been consolidated into OrchestrationService. The `tool_accessor.py` now acts as a pure delegation layer.

**Core Methods**:
- `create_orchestrator_job(project_id, mission, context_budget)` - Create orchestrator with context tracking
- `update_context_usage(job_id, additional_tokens)` - Track context consumption
- `trigger_succession(job_id, reason)` - Spawn successor orchestrator
- `get_context_status(job_id)` - Check context usage vs budget
- `generate_handover_summary(job_id)` - Generate condensed context (<10K tokens)

**Orchestrator Instructions** (moved from orchestrator.py):
- `get_orchestrator_instructions(job_id, tenant_key)` - Fetch orchestrator context and mission
- `update_agent_mission(job_id, tenant_key, mission)` - Update agent job mission field

**Agent Spawning & Management** (moved from orchestrator.py):
- `spawn_agent_job(agent_display_name, agent_name, mission, project_id)` - Create agent job and execution
- `get_agent_mission(job_id, tenant_key)` - Fetch agent-specific mission with full protocol

**Succession Management** (moved from orchestrator.py):
- `create_successor_orchestrator(current_job_id, tenant_key, reason)` - Create successor and transfer context
- `check_succession_status(job_id, tenant_key)` - Check if succession needed based on context threshold

**Vision Processing** (moved from orchestrator.py):
- `process_product_vision(product_id, vision_content, project_id)` - Process vision, create/update project

**Delegation Pattern**:
All MCP tools in `tool_accessor.py` delegate to OrchestrationService methods. The ToolAccessor class acts as a thin adapter layer between MCP protocol and service layer.

**Context Tracking Pattern** (Handover 0502):
```python
from src.giljo_mcp.services.orchestration_service import OrchestrationService

service = OrchestrationService(session, tenant_key="user123")

# Create orchestrator with context budget
job = await service.create_orchestrator_job(
    project_id=project_id,
    mission=mission,
    context_budget=200000  # tokens
)

# Update context usage on message sends
await service.update_context_usage(job.id, additional_tokens=1500)

# Check if succession needed
status = await service.get_context_status(job.id)
if status['percentage_used'] >= 0.9:
    successor = await service.trigger_succession(
        job_id=job.id,
        reason="context_limit"
    )
    # successor.handover_summary contains condensed context (<10K tokens)
```

**Auto-Succession Flow**:
```
1. Context usage tracked per message send
2. At 90% threshold: Auto-trigger succession
3. Generate handover summary (<10K tokens via mission condensation)
4. Spawn successor orchestrator (instance_number++)
5. Transfer active jobs to successor
6. Update UI timeline (SuccessionTimeline.vue)
```

**Database Fields**:
- `context_used` (INTEGER) - Current token usage
- `context_budget` (INTEGER) - Maximum tokens (default: 200,000)
- `instance_number` (INTEGER) - Orchestrator instance in succession chain
- `spawned_by` (FK) - Parent orchestrator ID (lineage tracking)
- `handover_to` (FK) - Successor orchestrator ID
- `handover_summary` (TEXT) - Condensed context for successor
- `succession_reason` (VARCHAR) - Why succession triggered

---

## Database Field Naming Conventions

**Critical Distinction**: User input fields use `description`, AI-generated content uses `mission`.

| Field | Who Fills It | Purpose | Example |
|-------|--------------|---------|---------|
| `Product.description` | Human (web form) | Product overview | "Multi-tenant MCP server for agent orchestration" |
| `Project.description` | Human (web form) | Project requirements | "Add JWT authentication" |
| `Project.mission` | Orchestrator (AI) | AI-generated plan | "Implement JWT auth with RS256, protect 8 endpoints, add rate limiting..." |
| `MCPAgentJob.mission` | Orchestrator (AI) | Agent-specific work | "backend-tester: Test authentication endpoints with invalid tokens..." |
| `Task.description` | Human (form/MCP) | Task details | "Research Redis caching strategies" |

> **Migration Note (Handover 0366a - Dec 2025)**
>
> The `MCPAgentJob` model is **deprecated** as of v3.3.0.
> Use `AgentJob` (work order) and `AgentExecution` (executor instance) instead.
>
> **Key Changes:**
> - `job_id` = The work to be done (persists across succession)
> - `agent_id` = The executor doing the work (changes on succession)
>
> See Handover 0366 series for migration details. Will be removed in v4.0.

**DO NOT**:
- ❌ Call `update_project_mission()` with user input (that's `description`)
- ❌ Confuse `Task.description` with `Project.mission`
- ❌ Use "mission" parameter when accepting user requirements

**Validation Rule**: If content comes from a web form or user prompt, it's `description`. If content is AI-generated mission/plan, it's `mission`.

---

### **SettingsService** (`src/giljo_mcp/services/settings_service.py`)

**Purpose**: System settings persistence and retrieval

**Key Methods**:
- `get_general_settings(tenant_key)` - Retrieve general settings
- `update_general_settings(tenant_key, settings)` - Update general settings
- `get_network_settings(tenant_key)` - Retrieve network settings
- `update_network_settings(tenant_key, settings)` - Update network settings
- `get_product_info(tenant_key)` - Retrieve product information

**Settings Storage** (Handover 0506):
```python
from src.giljo_mcp.services.settings_service import SettingsService

service = SettingsService(session, tenant_key="user123")

# Get settings
general = await service.get_general_settings()
network = await service.get_network_settings()
product_info = await service.get_product_info()

# Update settings
await service.update_general_settings({
    "theme": "dark",
    "language": "en"
})

await service.update_network_settings({
    "api_host": "192.168.1.100",
    "api_port": 7272
})
```

---

### **AgentJobManager** (`src/giljo_mcp/agent_job_manager.py`)

**Purpose**: Agent job lifecycle management (create, acknowledge, complete, fail)

**Key Methods**:
- `create_job(agent_role, mission, parent_job_id)` - Create new agent job
- `acknowledge_job(job_id)` - Mark job as acknowledged (pending → active)
- `complete_job(job_id, result)` - Mark job as completed
- `fail_job(job_id, error)` - Mark job as failed
- `get_job_status(job_id)` - Get current job status
- `cancel_job(job_id)` - Cancel running job

**Job Lifecycle**:
```python
from src.giljo_mcp.agent_job_manager import AgentJobManager

manager = AgentJobManager(session, tenant_key="user123")

# Create job
job = await manager.create_job(
    agent_role="backend-implementer",
    mission="Implement user authentication",
    parent_job_id=orchestrator_job_id
)

# Job progresses through states
# pending → acknowledged → active → completed/failed/cancelled

# Complete job
await manager.complete_job(
    job_id=job.id,
    result={"status": "success", "files_modified": 5}
)
```

**State Machine**:
```
pending → acknowledged → active → completed
                         ↓         ↓
                      failed   cancelled
```

---

## Service Migration Patterns

### Migrating Endpoints to Services

When migrating an endpoint from direct database access to service layer:

#### Before (Non-Compliant)
```python
@router.get("/", response_model=list[UserResponse])
async def list_users(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session)
):
    stmt = select(User).where(User.tenant_key == current_user.tenant_key)
    result = await db.execute(stmt)
    users = result.scalars().all()
    return [user_to_response(user) for user in users]
```

#### After (Compliant)
```python
@router.get("/", response_model=list[UserResponse])
async def list_users(
    current_user: User = Depends(require_admin),
    user_service: UserService = Depends(get_user_service)
):
    result = await user_service.list_users()
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return [user_to_response(user) for user in result["data"]]
```

### Key Migration Changes
1. **Dependency Change**: Replace `AsyncSession` with service dependency
2. **Service Call**: Use service method instead of direct query
3. **Error Handling**: Check `result["success"]` and raise HTTPException
4. **Response Conversion**: Convert service dict response to Pydantic model

### Dependency Injection Pattern

All services use dependency injection for tenant isolation:

```python
# api/endpoints/dependencies.py

def get_user_service(
    current_user: User = Depends(get_current_active_user),
    db_manager: DatabaseManager = Depends(get_db_manager)
) -> UserService:
    """Get UserService with tenant context"""
    return UserService(db_manager, tenant_key=current_user.tenant_key)

def get_auth_service(
    db_manager: DatabaseManager = Depends(get_db_manager)
) -> AuthService:
    """Get AuthService (no tenant context - cross-tenant operations)"""
    return AuthService(db_manager)

def get_task_service(
    current_user: User = Depends(get_current_active_user),
    tenant_manager: TenantManager = Depends(get_tenant_manager)
) -> TaskService:
    """Get TaskService with tenant context"""
    tenant_manager.set_current_tenant(current_user.tenant_key)
    return TaskService(tenant_manager=tenant_manager)
```

### Service Response Pattern

All services return `dict[str, Any]` with standardized structure:

```python
# Success response
{
    "success": True,
    "data": {...}  # Entity data or list
}

# Error response
{
    "success": False,
    "error": "Error message string"
}
```

### Error Handling in Endpoints

Standard error handling pattern:

```python
result = await service.method()

if not result["success"]:
    # Determine appropriate HTTP status code
    error_msg = result["error"].lower()
    if "not found" in error_msg:
        raise HTTPException(status_code=404, detail=result["error"])
    elif "permission" in error_msg or "unauthorized" in error_msg:
        raise HTTPException(status_code=403, detail=result["error"])
    else:
        raise HTTPException(status_code=400, detail=result["error"])

return result["data"]
```

---

## Service Layer Pattern (All Services Follow This)

### **1. AsyncSession Injection**
All services require database session and tenant_key:
```python
class MyService:
    def __init__(self, session: AsyncSession, tenant_key: str):
        self.session = session
        self.tenant_key = tenant_key
```

### **2. Multi-Tenant Isolation**
Every database query filters by tenant_key:
```python
async def get_products(self):
    result = await self.session.execute(
        select(Product).where(Product.tenant_key == self.tenant_key)
    )
    return result.scalars().all()
```

**Raw SQLAlchemy Pattern** (for advanced use cases):
```python
# Direct database queries also require tenant_key filtering
> **Migration Note (Handover 0366a - Dec 2025)**
>
> The `MCPAgentJob` model is **deprecated** as of v3.3.0.
> Use `AgentJob` (work order) and `AgentExecution` (executor instance) instead.
>
> **Key Changes:**
> - `job_id` = The work to be done (persists across succession)
> - `agent_id` = The executor doing the work (changes on succession)
>
> See Handover 0366 series for migration details. Will be removed in v4.0.

from src.giljo_mcp.models import MCPAgentJob

jobs = session.query(MCPAgentJob).filter(
    MCPAgentJob.tenant_key == tenant_key,
    MCPAgentJob.agent_type == "implementer"
).all()
```
**When to use**: Database migrations, complex queries, performance optimization.
**Preferred**: Use service layer methods when available (automatic tenant_key filtering).

### **3. Pydantic Schema Validation**
Request/response validation using Pydantic:
```python
from pydantic import BaseModel

class ProductCreate(BaseModel):
    name: str
    description: str
    config_data: dict

async def create_product(self, product_data: ProductCreate):
    # product_data is validated by Pydantic
    ...
```

### **4. WebSocket Event Emission**
Real-time UI updates via WebSocket:
```python
from src.giljo_mcp.websocket_manager import websocket_manager

async def activate_product(self, product_id: int):
    # ... database update ...

    # Emit WebSocket event
    await websocket_manager.broadcast_to_tenant(
        tenant_key=self.tenant_key,
        event="product:activated",
        data={"product_id": product_id}
    )
```

### **5. Comprehensive Error Handling**
Domain-specific exceptions:
```python
from src.giljo_mcp.exceptions import ProductNotFoundError, InvalidStateError

async def activate_product(self, product_id: int):
    product = await self.session.get(Product, product_id)
    if not product:
        raise ProductNotFoundError(f"Product {product_id} not found")

    if product.status == "deleted":
        raise InvalidStateError("Cannot activate deleted product")

    # ... activate logic ...
```

---

## Example Usage Patterns

### **Pattern 1: Service → API Endpoint**
```python
# api/endpoints/products.py

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.giljo_mcp.services.product_service import ProductService
from api.dependencies import get_db, get_current_user

router = APIRouter()

@router.post("/api/products")
async def create_product(
    product_data: ProductCreate,
    session: AsyncSession = Depends(get_db),
    user = Depends(get_current_user)
):
    service = ProductService(session, tenant_key=user.tenant_key)
    product = await service.create_product(product_data)
    return product
```

### **Pattern 2: Service → MCP Tool**
```python
# src/giljo_mcp/tools/product_tools.py

from src.giljo_mcp.services.product_service import ProductService

async def upload_vision_document(product_id: int, content: str):
    async with get_session() as session:
        service = ProductService(session, tenant_key=get_tenant_key())
        result = await service.upload_vision_document(product_id, content)
        return result
```

### **Pattern 3: Service → Service Composition**
```python
# OrchestrationService uses ProjectService
from src.giljo_mcp.services.project_service import ProjectService

class OrchestrationService:
    async def launch_orchestrator(self, project_id: int, mission: str):
        # Use ProjectService to get project details
        project_service = ProjectService(self.session, self.tenant_key)
        project = await project_service.get_project(project_id)

        # Create orchestrator job
        job = await self.create_orchestrator_job(
            project_id=project_id,
            mission=mission,
            context_budget=200000
        )
        return job
```

---

## Testing Services

### **Unit Tests** (`tests/services/`)

**Pattern**: Mock database, test business logic
```python
import pytest
from src.giljo_mcp.services.product_service import ProductService

@pytest.mark.asyncio
async def test_create_product(mock_session):
    service = ProductService(mock_session, tenant_key="test_tenant")

    product = await service.create_product({
        "name": "Test Product",
        "description": "Test description"
    })

    assert product.name == "Test Product"
    assert product.tenant_key == "test_tenant"
```

### **Integration Tests** (`tests/integration/`)

**Pattern**: Real database, test full workflow
```python
@pytest.mark.asyncio
async def test_product_lifecycle(db_session, test_tenant):
    service = ProductService(db_session, tenant_key=test_tenant)

    # Create
    product = await service.create_product({"name": "Test"})

    # Activate
    await service.activate_product(product.id)
    active = await service.get_active_product()
    assert active.id == product.id

    # Deactivate
    await service.deactivate_product(product.id)
    active = await service.get_active_product()
    assert active is None
```

---

## Common Patterns & Best Practices

### **1. Always Use Services in Endpoints**
❌ **DON'T** query database directly in endpoints:
```python
@router.get("/api/products")
async def get_products(session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(Product))  # BAD
    return result.scalars().all()
```

✅ **DO** use service layer:
```python
@router.get("/api/products")
async def get_products(
    session: AsyncSession = Depends(get_db),
    user = Depends(get_current_user)
):
    service = ProductService(session, user.tenant_key)
    return await service.get_products()  # GOOD
```

### **2. Multi-Tenant Isolation is Mandatory**
Every service method MUST filter by tenant_key:
```python
async def get_product(self, product_id: int):
    result = await self.session.execute(
        select(Product).where(
            Product.id == product_id,
            Product.tenant_key == self.tenant_key  # CRITICAL
        )
    )
    return result.scalar_one_or_none()
```

### **3. Emit WebSocket Events for Real-Time UI**
After state changes, broadcast to tenant:
```python
await websocket_manager.broadcast_to_tenant(
    tenant_key=self.tenant_key,
    event="job:status_changed",
    data={"job_id": job.id, "status": "completed"}
)
```

### **4. Use Transactions for Multi-Step Operations**
```python
async def activate_project(self, project_id: int):
    # Deactivate all other projects
    await self.deactivate_all_projects_except(project_id)

    # Activate target project
    project = await self.get_project(project_id)
    project.status = "active"

    # Commit transaction (handled by endpoint or context manager)
    await self.session.commit()
```

---

## Database Schema Reference

**Key Tables**:
- `mcp_products` - Products with config_data (JSONB)
- `mcp_projects` - Projects with Single Active constraint
- `mcp_agent_jobs` - Agent jobs with context tracking
- `mcp_settings` - Tenant-specific settings (JSONB)
- `mcp_vision_documents` - Vision docs with chunking metadata

**Multi-Tenant Isolation**: All tables have `tenant_key` VARCHAR(255) column

**Single Active Constraints**:
- Products: `UNIQUE INDEX idx_active_product ON mcp_products (tenant_key) WHERE status = 'active'`
- Projects: `UNIQUE INDEX idx_active_project ON mcp_projects (product_id) WHERE status = 'active'`

---

## Related Documentation

- **Context Tracking**: [ORCHESTRATOR.md](ORCHESTRATOR.md) - Succession, handover protocol
- **Testing**: [TESTING.md](TESTING.md) - Unit/integration test patterns
- **API Design**: [SERVER_ARCHITECTURE_TECH_STACK.md](SERVER_ARCHITECTURE_TECH_STACK.md)
- **Database**: [docs/architecture/migration-strategy.md](architecture/migration-strategy.md)

---

## Service Layer Compliance Status

### Compliance Metrics (as of Handover 0322)

| Endpoint File | Violations Before | Violations After | Compliance Rate |
|---------------|-------------------|------------------|-----------------|
| users.py      | 18                | 0                | 100%            |
| auth.py       | 10                | 0                | 100%            |
| messages.py   | 7                 | 0                | 100%            |
| tasks.py      | 9                 | 2*               | 78%             |
| **Total**     | **44**            | **2**            | **95%**         |

*Remaining violations in tasks.py (lines 154, 294) are in complex list/update operations that require further refactoring.

### Migration History

**Handover 0322** (November 2025):
- Created UserService (16 methods)
- Created AuthService (8 methods)
- Enhanced TaskService (5 new methods + 2 helpers)
- Migrated 21 endpoints across 4 files
- Eliminated 42 out of 44 direct database access violations

### Best Practices Established

1. **Service-First Architecture**: All new business logic goes in services, not endpoints
2. **Dependency Injection**: Services injected via FastAPI dependencies
3. **Tenant Isolation**: Multi-tenant filtering enforced at service layer
4. **Standardized Responses**: All services return `dict[str, Any]` with success/data/error
5. **Comprehensive Testing**: Service unit tests + API integration tests
6. **WebSocket Integration**: Services emit real-time events for UI updates

### Future Work

**Remaining Tasks**:
1. Migrate remaining 2 violations in tasks.py (list_tasks, update_task)
2. Fix service unit test transaction isolation issues
3. Achieve >80% test coverage for all services
4. Consider creating SettingsService for system configuration operations

---

**Last Updated**: 2025-11-20 (Post-Remediation v3.1.1 + Handover 0322)
