# Service Layer Architecture

**Version**: v3.1+ (Post-Remediation)
**Last Updated**: 2025-11-15

## Overview

GiljoAI MCP uses a service layer architecture to separate business logic from API endpoints. All services follow consistent patterns for database access, multi-tenant isolation, validation, and real-time updates.

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

**Purpose**: Context tracking, succession management, orchestrator coordination

**Key Methods**:
- `create_orchestrator_job(project_id, mission, context_budget)` - Create orchestrator with context tracking
- `update_context_usage(job_id, additional_tokens)` - Track context consumption
- `trigger_succession(job_id, reason)` - Spawn successor orchestrator
- `get_context_status(job_id)` - Check context usage vs budget
- `generate_handover_summary(job_id)` - Generate condensed context (<10K tokens)

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

**Last Updated**: 2025-11-15 (Post-Remediation v3.1.1)
