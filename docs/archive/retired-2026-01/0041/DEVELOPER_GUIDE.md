# Agent Template Management - Developer Guide

**Version**: 3.0.0
**Last Updated**: 2025-10-24
**Audience**: Developers, DevOps Engineers, System Architects

---

## Table of Contents

1. [Architecture Deep Dive](#architecture-deep-dive)
2. [API Reference](#api-reference)
3. [Database Schema](#database-schema)
4. [Cache Architecture](#cache-architecture)
5. [Multi-Tenant Isolation](#multi-tenant-isolation)
6. [Adding New Features](#adding-new-features)
7. [Testing Strategies](#testing-strategies)
8. [Performance Optimization](#performance-optimization)
9. [Troubleshooting](#troubleshooting)

---

## Architecture Deep Dive

### System Components

```
┌──────────────────────────────────────────────────────────────┐
│                    CLIENT LAYER (Vue 3)                       │
│  TemplateManager.vue → API Client → WebSocket Client         │
└────────────┬─────────────────────────────────────────────────┘
             │ HTTPS + WebSocket
             ▼
┌──────────────────────────────────────────────────────────────┐
│                  API LAYER (FastAPI)                          │
│  • api/endpoints/templates.py (13 REST endpoints)             │
│  • JWT Authentication (auth/dependencies.py)                  │
│  • WebSocket Broadcasts (websocket_manager.py)                │
└────────────┬─────────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────────┐
│              BUSINESS LOGIC LAYER                             │
│  • template_manager.py (Unified resolution logic)             │
│  • template_seeder.py (Database seeding)                      │
│  • template_cache.py (Three-layer cache)                      │
└────────────┬─────────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────────┐
│                 DATA LAYER                                    │
│  • PostgreSQL (agent_templates, agent_template_history)       │
│  • Redis (Optional Layer 2 cache)                             │
│  • In-Memory LRU Cache (Layer 1)                              │
└──────────────────────────────────────────────────────────────┘
```

### Template Resolution Flow

```python
# Pseudocode for template resolution
def get_agent_template(role, tenant_key, product_id=None):
    # Layer 1: Memory cache (LRU, 100 templates)
    cache_key = f"template:{tenant_key}:{product_id}:{role}"
    if cache_key in memory_cache:
        return memory_cache[cache_key]  # <1ms

    # Layer 2: Redis cache (1-hour TTL)
    if redis_enabled:
        redis_value = redis.get(cache_key)
        if redis_value:
            template = pickle.loads(redis_value)
            memory_cache[cache_key] = template
            return template  # <2ms

    # Layer 3: Database cascade
    template = query_database_cascade(role, tenant_key, product_id)
    # Priority: Product-specific → Tenant → System → Legacy

    # Cache in all layers
    if template:
        memory_cache[cache_key] = template
        if redis_enabled:
            redis.setex(cache_key, 3600, pickle.dumps(template))

    return template or get_legacy_fallback(role)  # <10ms
```

### Variable Substitution Pipeline

```python
def substitute_variables(template_content, variables_dict):
    """
    Replace {variable} placeholders with actual values.

    Example:
        template_content = "Project: {project_name}, Mission: {mission}"
        variables_dict = {"project_name": "MyApp", "mission": "Build API"}
        → "Project: MyApp, Mission: Build API"
    """
    import re

    def replace_func(match):
        var_name = match.group(1)
        return variables_dict.get(var_name, match.group(0))

    return re.sub(r'\{(\w+)\}', replace_func, template_content)
```

---

## API Reference

### Base URL

```
http://localhost:7272/api/templates
```

### Authentication

All endpoints require JWT authentication:

```http
Authorization: Bearer <jwt_token>
```

### 1. List Templates

```http
GET /api/templates/
```

**Query Parameters**:
- `category` (optional): Filter by category (`role`, `project_type`, `custom`)
- `role` (optional): Filter by agent role (`orchestrator`, `implementer`, etc.)
- `product_id` (optional): Filter by product
- `is_active` (optional): Show only active templates (`true` | `false`)
- `is_default` (optional): Show only default templates (`true` | `false`)

**Response** (200 OK):
```json
[
  {
    "id": "uuid",
    "tenant_key": "default_tenant",
    "product_id": null,
    "name": "Orchestrator",
    "category": "role",
    "role": "orchestrator",
    "template_content": "You are the Project Orchestrator...",
    "variables": ["project_name", "product_name", "project_mission"],
    "behavioral_rules": ["Read vision document completely", ...],
    "success_criteria": ["All project objectives met", ...],
    "description": "Coordinates project execution",
    "version": "3.0.0",
    "is_active": true,
    "is_default": false,
    "tags": ["default", "tenant"],
    "usage_count": 42,
    "avg_generation_ms": 1250.5,
    "created_at": "2025-10-24T10:00:00Z",
    "updated_at": "2025-10-24T12:00:00Z",
    "created_by": "user_id",
    "preferred_tool": "claude"
  }
]
```

**Multi-Tenant Filtering**: Automatically filters by `tenant_key` from JWT.

### 2. Get Single Template

```http
GET /api/templates/{template_id}
```

**Response** (200 OK): Single template object (same schema as list)

**Errors**:
- `404 Not Found`: Template doesn't exist or belongs to another tenant
- `401 Unauthorized`: Missing or invalid JWT

### 3. Create Template

```http
POST /api/templates/
Content-Type: application/json
```

**Request Body**:
```json
{
  "name": "Implementer - TypeScript",
  "category": "role",
  "role": "implementer",
  "template_content": "You are a TypeScript expert...\n{project_name}\n{mission}",
  "description": "TypeScript-specialized implementer",
  "behavioral_rules": ["Use strict mode", "Prefer functional patterns"],
  "success_criteria": ["Code compiles without errors", "Tests pass"],
  "tags": ["typescript", "strict"],
  "is_default": false,
  "preferred_tool": "claude"
}
```

**Validation**:
- `template_content` max size: 100KB
- Variables auto-extracted from `{variable}` syntax
- `role` required if `category = "role"`
- `project_type` required if `category = "project_type"`

**Response** (201 Created): Created template object

**Errors**:
- `422 Unprocessable Entity`: Validation failed (size, missing fields, etc.)
- `401 Unauthorized`: Missing JWT

### 4. Update Template

```http
PUT /api/templates/{template_id}
Content-Type: application/json
```

**Request Body** (all fields optional):
```json
{
  "name": "Updated Name",
  "template_content": "Updated content...",
  "description": "Updated description",
  "behavioral_rules": ["New rule 1", "New rule 2"],
  "success_criteria": ["New criteria"],
  "tags": ["updated"],
  "is_active": true,
  "is_default": false,
  "preferred_tool": "codex"
}
```

**Behavior**:
- Previous version archived to `agent_template_history` table
- Version number incremented
- Cache invalidated across all layers
- WebSocket broadcast sent to all tenant clients

**Response** (200 OK): Updated template object

**Errors**:
- `403 Forbidden`: System template (cannot modify) OR belongs to another tenant
- `404 Not Found`: Template doesn't exist
- `422 Unprocessable Entity`: Validation failed

### 5. Delete Template (Soft Delete)

```http
DELETE /api/templates/{template_id}
```

**Behavior**:
- Sets `is_active = false` (soft delete, not permanent)
- Archives current version with `reason = "delete"`
- Cache invalidated
- System falls back to next priority template

**Response** (204 No Content)

**Errors**:
- `403 Forbidden`: System template OR other tenant's template
- `404 Not Found`: Template doesn't exist

### 6. Reset to System Default

```http
POST /api/templates/{template_id}/reset
```

**Behavior**:
- Finds system default template (`tenant_key = "system"`, `role = <same_role>`, `is_default = true`)
- Archives current tenant template
- Copies system default content to tenant template
- Version incremented
- Cache invalidated

**Response** (200 OK): Reset template object

**Errors**:
- `404 Not Found`: No system default exists for this role
- `403 Forbidden`: Cannot reset system templates

**Use Case**: User wants to discard customizations and start fresh with defaults.

### 7. Show Differences (Diff)

```http
GET /api/templates/{template_id}/diff
```

**Behavior**:
- Compares tenant template with system default template
- Generates unified diff and HTML diff
- Calculates change statistics

**Response** (200 OK):
```json
{
  "template_id": "uuid",
  "template_name": "Implementer",
  "system_template_id": "system_uuid",
  "system_template_name": "Implementer (System Default)",
  "diff_unified": "--- System Default\n+++ Your Template\n@@ -10,3 +10,4 @@\n...",
  "diff_html": "<div class='diff'>...</div>",
  "changes_summary": {
    "lines_added": 5,
    "lines_removed": 2,
    "lines_changed": 3,
    "total_changes": 10
  },
  "generated_at": "2025-10-24T12:00:00Z"
}
```

**Errors**:
- `404 Not Found`: No system default exists for comparison
- `403 Forbidden`: Other tenant's template

**Use Case**: User wants to see what they've changed compared to defaults.

### 8. Preview Template

```http
POST /api/templates/{template_id}/preview
Content-Type: application/json
```

**Request Body**:
```json
{
  "variables": {
    "project_name": "MyApp",
    "product_name": "MyApp",
    "mission": "Build REST API for user management",
    "custom_augmentation": "Use PostgreSQL for persistence"
  }
}
```

**Behavior**:
- Substitutes all `{variable}` placeholders with provided values
- Returns fully rendered template content

**Response** (200 OK):
```json
{
  "template_id": "uuid",
  "original_content": "Project: {project_name}...",
  "rendered_content": "Project: MyApp...",
  "variables_used": ["project_name", "mission", "custom_augmentation"],
  "variables_missing": ["product_name"],
  "generated_at": "2025-10-24T12:00:00Z"
}
```

**Use Case**: User wants to test variable substitution before saving template.

### 9. Get Template History

```http
GET /api/templates/{template_id}/history
```

**Query Parameters**:
- `limit` (optional): Max number of history records (default: 50)
- `offset` (optional): Pagination offset (default: 0)

**Response** (200 OK):
```json
{
  "template_id": "uuid",
  "history": [
    {
      "id": "history_uuid",
      "template_id": "uuid",
      "version": "3.2.1",
      "template_content": "Previous content...",
      "variables": ["project_name", "mission"],
      "behavioral_rules": [...],
      "reason": "edit",
      "changed_by": "user_id",
      "changed_at": "2025-10-24T11:00:00Z",
      "is_restorable": true
    }
  ],
  "total_count": 15,
  "limit": 50,
  "offset": 0
}
```

**Use Case**: Audit trail, version comparison, rollback preparation.

### 10. Restore from History

```http
POST /api/templates/{template_id}/restore
Content-Type: application/json
```

**Request Body**:
```json
{
  "history_id": "history_uuid"
}
```

**Behavior**:
- Archives current template version
- Restores content from specified history record
- Creates new version (doesn't delete current)
- Cache invalidated

**Response** (200 OK): Restored template object

**Errors**:
- `404 Not Found`: History record doesn't exist
- `403 Forbidden`: History belongs to another tenant

### WebSocket Events

**Connection**:
```javascript
const ws = new WebSocket('ws://localhost:7272/ws');
ws.send(JSON.stringify({type: 'authenticate', token: jwt_token}));
```

**Events Sent to Clients**:

1. **template_created**:
```json
{
  "type": "template_created",
  "data": {
    "template_id": "uuid",
    "template_name": "New Template",
    "tenant_key": "default_tenant",
    "created_by": "user_id",
    "timestamp": "2025-10-24T12:00:00Z"
  }
}
```

2. **template_updated**:
```json
{
  "type": "template_updated",
  "data": {
    "template_id": "uuid",
    "template_name": "Updated Template",
    "version": "3.2.0",
    "tenant_key": "default_tenant",
    "updated_by": "user_id",
    "timestamp": "2025-10-24T12:05:00Z"
  }
}
```

3. **template_deleted**:
```json
{
  "type": "template_deleted",
  "data": {
    "template_id": "uuid",
    "template_name": "Deleted Template",
    "tenant_key": "default_tenant",
    "deleted_by": "user_id",
    "timestamp": "2025-10-24T12:10:00Z"
  }
}
```

**Tenant Scoping**: Events only sent to clients in the same tenant (multi-tenant isolation).

---

## Database Schema

### agent_templates Table

```sql
CREATE TABLE agent_templates (
    id VARCHAR(36) PRIMARY KEY,  -- UUID
    tenant_key VARCHAR(255) NOT NULL,
    product_id VARCHAR(36),  -- NULL for tenant-level templates
    name VARCHAR(255) NOT NULL,
    category VARCHAR(50) NOT NULL,  -- 'role', 'project_type', 'custom'
    role VARCHAR(50),  -- 'orchestrator', 'analyzer', 'implementer', etc.
    project_type VARCHAR(50),  -- For category='project_type'
    template_content TEXT NOT NULL,  -- Max 100KB enforced at API layer
    variables JSONB DEFAULT '[]',  -- Auto-extracted from {variable} syntax
    behavioral_rules JSONB DEFAULT '[]',
    success_criteria JSONB DEFAULT '[]',
    description TEXT,
    version VARCHAR(20) NOT NULL DEFAULT '3.0.0',
    is_active BOOLEAN DEFAULT TRUE,
    is_default BOOLEAN DEFAULT FALSE,
    tags JSONB DEFAULT '[]',
    usage_count INTEGER DEFAULT 0,
    avg_generation_ms NUMERIC(10, 2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    created_by VARCHAR(36),  -- User ID
    preferred_tool VARCHAR(50) DEFAULT 'claude',

    -- Indexes (add these for performance)
    INDEX idx_tenant_role (tenant_key, role),
    INDEX idx_tenant_active (tenant_key, is_active),
    INDEX idx_product (product_id),

    -- Constraints
    CHECK (category IN ('role', 'project_type', 'custom')),
    CHECK (preferred_tool IN ('claude', 'codex', 'gemini'))
);
```

### agent_template_history Table

```sql
CREATE TABLE agent_template_history (
    id VARCHAR(36) PRIMARY KEY,  -- UUID
    template_id VARCHAR(36) NOT NULL,
    tenant_key VARCHAR(255) NOT NULL,
    version VARCHAR(20) NOT NULL,
    template_content TEXT NOT NULL,
    variables JSONB DEFAULT '[]',
    behavioral_rules JSONB DEFAULT '[]',
    success_criteria JSONB DEFAULT '[]',
    reason VARCHAR(50),  -- 'edit', 'reset', 'delete', 'restore'
    changed_by VARCHAR(36),  -- User ID
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    usage_count_at_archive INTEGER DEFAULT 0,
    is_restorable BOOLEAN DEFAULT TRUE,

    -- Foreign key (optional, depends on cascade behavior)
    FOREIGN KEY (template_id) REFERENCES agent_templates(id) ON DELETE CASCADE,

    -- Indexes
    INDEX idx_template_history (template_id, changed_at DESC)
);
```

### Recommended Database Indexes

For optimal performance, add these indexes:

```sql
-- Multi-tenant query optimization
CREATE INDEX idx_agent_templates_tenant_role
ON agent_templates(tenant_key, role);

CREATE INDEX idx_agent_templates_tenant_active
ON agent_templates(tenant_key, is_active);

-- Product-specific template queries
CREATE INDEX idx_agent_templates_product
ON agent_templates(product_id)
WHERE product_id IS NOT NULL;

-- Version history queries
CREATE INDEX idx_agent_template_history_template
ON agent_template_history(template_id, changed_at DESC);

-- Full-text search (future feature)
CREATE INDEX idx_agent_templates_content_trgm
ON agent_templates USING gin(template_content gin_trgm_ops);
```

**Expected Performance Improvement**: 30-40% reduction in p99 query latency.

---

## Cache Architecture

### Three-Layer Cache Implementation

```python
class TemplateCache:
    def __init__(self, db_manager, redis_client=None):
        self.db = db_manager
        self.redis = redis_client
        self._memory_cache = {}  # Layer 1: In-memory LRU
        self._cache_hits = 0
        self._cache_misses = 0

    async def get_template(self, role, tenant_key, product_id=None):
        cache_key = self._build_cache_key(role, tenant_key, product_id)

        # Layer 1: Memory (LRU, 100 templates, <1ms)
        if cache_key in self._memory_cache:
            self._cache_hits += 1
            return self._memory_cache[cache_key]

        # Layer 2: Redis (1-hour TTL, <2ms)
        if self.redis:
            redis_data = await self._get_from_redis(cache_key)
            if redis_data:
                template = pickle.loads(redis_data)
                self._memory_cache[cache_key] = template
                self._cache_hits += 1
                return template

        # Layer 3: Database cascade (<10ms)
        self._cache_misses += 1
        template = await self._query_cascade(role, tenant_key, product_id)

        # Cache in all layers
        if template:
            self._memory_cache[cache_key] = template
            if len(self._memory_cache) > 100:  # LRU eviction
                oldest_key = next(iter(self._memory_cache))
                del self._memory_cache[oldest_key]

            if self.redis:
                await self._set_in_redis(cache_key, template, ttl=3600)

        return template

    async def invalidate(self, role, tenant_key, product_id=None):
        cache_key = self._build_cache_key(role, tenant_key, product_id)

        # Invalidate memory
        if cache_key in self._memory_cache:
            del self._memory_cache[cache_key]

        # Invalidate Redis
        if self.redis:
            await self._delete_from_redis(cache_key)
```

### Cache Key Naming Convention

```
template:{tenant_key}:{product_id_or_tenant}:{role}
```

**Examples**:
- Product-specific: `template:tenant_abc:product_123:orchestrator`
- Tenant-level: `template:tenant_abc:tenant:orchestrator`
- System default: `template:system:system:orchestrator`

**Multi-Tenant Isolation**: Cache keys always include `tenant_key` to prevent cross-tenant pollution.

### Cache Invalidation Strategies

```python
# Strategy 1: Single template invalidation (edit, delete)
await cache.invalidate(role="implementer", tenant_key="tenant_abc", product_id="prod_1")

# Strategy 2: All tenant templates (tenant settings change)
await cache.invalidate_all(tenant_key="tenant_abc")

# Strategy 3: Global cache flush (system maintenance)
await cache.invalidate_all(tenant_key=None)
```

### Cache Performance Metrics

```python
stats = cache.get_cache_stats()
# Returns:
{
    "hits": 950,
    "misses": 50,
    "total_requests": 1000,
    "hit_rate_percent": 95.0,
    "memory_cache_size": 85,
    "redis_enabled": True
}
```

**Target Hit Rate**: >90% after warm-up (typically 95%+)

---

## Multi-Tenant Isolation

### Database-Level Isolation

**All queries MUST filter by `tenant_key`**:

```python
# ✅ CORRECT - Tenant-isolated query
stmt = select(AgentTemplate).where(
    AgentTemplate.tenant_key == current_user.tenant_key,
    AgentTemplate.role == role,
    AgentTemplate.is_active == True
)

# ❌ WRONG - No tenant filtering (SECURITY RISK)
stmt = select(AgentTemplate).where(
    AgentTemplate.role == role,
    AgentTemplate.is_active == True
)
```

### API-Level Isolation

**JWT Authentication**:
```python
from src.giljo_mcp.auth.dependencies import get_current_active_user

@router.get("/api/templates/")
async def list_templates(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
):
    tenant_key = current_user.tenant_key
    # All queries use tenant_key from JWT
    ...
```

**Authorization Check**:
```python
# Before updating template, verify ownership
template = await get_template_by_id(template_id, db)
if template.tenant_key != current_user.tenant_key:
    raise HTTPException(status_code=403, detail="Access denied")

# Also check system template protection
if template.tenant_key == "system":
    raise HTTPException(status_code=403, detail="Cannot modify system templates")
```

### Cache-Level Isolation

**Cache keys include `tenant_key`**:
```python
def _build_cache_key(self, role, tenant_key, product_id=None):
    if product_id:
        return f"template:{tenant_key}:{product_id}:{role}"
    return f"template:{tenant_key}:tenant:{role}"
```

### WebSocket-Level Isolation

**Broadcasts are tenant-scoped**:
```python
async def broadcast_template_updated(template_id, tenant_key):
    message = {
        "type": "template_updated",
        "data": {"template_id": template_id, ...}
    }
    # Only send to clients in the same tenant
    await websocket_manager.broadcast_to_tenant(tenant_key, message)
```

---

## Adding New Features

### Adding a New Template Type

1. **Update Database Schema**:
```sql
-- Add new category to CHECK constraint
ALTER TABLE agent_templates DROP CONSTRAINT agent_templates_category_check;
ALTER TABLE agent_templates ADD CONSTRAINT agent_templates_category_check
CHECK (category IN ('role', 'project_type', 'custom', 'workflow'));
```

2. **Update Pydantic Models** (`api/endpoints/templates.py`):
```python
class TemplateCreate(BaseModel):
    category: str = Field(..., description="Category: role, project_type, custom, workflow")
    workflow_type: Optional[str] = Field(None, description="Workflow type if category=workflow")
```

3. **Add Seeding Logic** (`template_seeder.py`):
```python
def _get_template_metadata():
    return {
        ...,
        "code_reviewer": {  # New template type
            "category": "workflow",
            "workflow_type": "code_review",
            "behavioral_rules": [...],
            "success_criteria": [...],
            "variables": ["code_snippet", "review_focus"]
        }
    }
```

4. **Update Frontend** (`TemplateManager.vue`):
```javascript
const categoryOptions = [
  { text: 'Agent Role', value: 'role' },
  { text: 'Project Type', value: 'project_type' },
  { text: 'Workflow', value: 'workflow' },  // NEW
  { text: 'Custom', value: 'custom' }
]
```

### Adding a New API Endpoint

1. **Define Endpoint** (`api/endpoints/templates.py`):
```python
@router.post("/templates/{template_id}/validate")
async def validate_template(
    template_id: str = Path(..., description="Template ID"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
):
    # Fetch template
    template = await get_template_or_404(template_id, current_user.tenant_key, db)

    # Validation logic
    errors = []
    if not template.variables:
        errors.append("Template has no variables")

    # Return validation results
    return {
        "template_id": template_id,
        "is_valid": len(errors) == 0,
        "errors": errors,
        "validated_at": datetime.now(timezone.utc)
    }
```

2. **Add Tests** (`tests/test_agent_templates_api.py`):
```python
async def test_validate_template_success(async_client, orchestrator_template):
    response = await async_client.post(
        f"/api/templates/{orchestrator_template.id}/validate"
    )
    assert response.status_code == 200
    assert response.json()["is_valid"] is True
```

3. **Update Frontend** (call new endpoint from Vue component)

---

## Testing Strategies

### Unit Testing (template_seeder.py, template_cache.py)

```python
import pytest
from src.giljo_mcp.template_seeder import seed_tenant_templates

@pytest.mark.asyncio
async def test_seed_templates_idempotent(db_session):
    # First run
    count1 = await seed_tenant_templates(db_session, "test_tenant")
    assert count1 == 6  # 6 templates seeded

    # Second run (idempotent check)
    count2 = await seed_tenant_templates(db_session, "test_tenant")
    assert count2 == 0  # No duplicates created
```

### Integration Testing (API endpoints)

```python
@pytest.mark.asyncio
async def test_full_crud_workflow(async_client, test_user):
    # Create
    create_response = await async_client.post("/api/templates/", json={
        "name": "Test Template",
        "category": "role",
        "role": "orchestrator",
        "template_content": "Test content with {project_name}"
    })
    assert create_response.status_code == 201
    template_id = create_response.json()["id"]

    # Read
    get_response = await async_client.get(f"/api/templates/{template_id}")
    assert get_response.status_code == 200

    # Update
    update_response = await async_client.put(f"/api/templates/{template_id}", json={
        "name": "Updated Template"
    })
    assert update_response.status_code == 200

    # Delete
    delete_response = await async_client.delete(f"/api/templates/{template_id}")
    assert delete_response.status_code == 204
```

### Security Testing (multi-tenant isolation)

```python
@pytest.mark.asyncio
async def test_cross_tenant_access_forbidden(async_client, tenant_a_template, tenant_b_user):
    # Tenant B tries to access Tenant A's template
    response = await async_client.get(
        f"/api/templates/{tenant_a_template.id}",
        headers={"Authorization": f"Bearer {tenant_b_user.jwt_token}"}
    )
    assert response.status_code == 403  # Forbidden
```

### Performance Testing

```python
import time

@pytest.mark.asyncio
async def test_cache_performance(template_cache, db_session):
    # Warm up cache
    template = await template_cache.get_template("orchestrator", "test_tenant")

    # Measure cache hit performance
    start = time.perf_counter()
    for _ in range(100):
        await template_cache.get_template("orchestrator", "test_tenant")
    elapsed = time.perf_counter() - start

    avg_latency_ms = (elapsed / 100) * 1000
    assert avg_latency_ms < 1.0  # <1ms average
```

---

## Performance Optimization

### Database Query Optimization

**Add Indexes**:
```sql
CREATE INDEX idx_agent_templates_tenant_role ON agent_templates(tenant_key, role);
CREATE INDEX idx_agent_templates_tenant_active ON agent_templates(tenant_key, is_active);
```

**Use Query Profiling**:
```sql
EXPLAIN ANALYZE
SELECT * FROM agent_templates
WHERE tenant_key = 'test_tenant' AND role = 'orchestrator' AND is_active = true;
```

**Connection Pooling** (`config.yaml`):
```yaml
database:
  pool_size: 20  # Max connections
  max_overflow: 10  # Additional connections during peak
  pool_pre_ping: true  # Verify connection health
  pool_recycle: 3600  # Recycle connections after 1 hour
```

### Cache Optimization

**Monitor Hit Rate**:
```python
stats = cache.get_cache_stats()
if stats["hit_rate_percent"] < 85:
    logger.warning("Cache hit rate below threshold: {}", stats["hit_rate_percent"])
```

**Tune LRU Size**:
- Default: 100 templates
- Low-traffic: 50 templates (reduce memory)
- High-traffic: 200 templates (increase hit rate)

**Redis Configuration** (if using):
```yaml
redis:
  host: localhost
  port: 6379
  db: 0
  max_connections: 50
  socket_timeout: 5
  socket_connect_timeout: 5
```

### API Response Optimization

**Use Compression**:
```python
from fastapi.middleware.gzip import GZIPMiddleware
app.add_middleware(GZIPMiddleware, minimum_size=1000)
```

**Pagination for Large Lists**:
```python
@router.get("/api/templates/")
async def list_templates(
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    ...
):
    # Return paginated results
    ...
```

---

## Troubleshooting

### Issue: High Database Query Latency

**Symptoms**: p99 latency > 50ms

**Diagnosis**:
```sql
-- Check slow queries
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
WHERE query LIKE '%agent_templates%'
ORDER BY mean_exec_time DESC
LIMIT 10;
```

**Solutions**:
1. Add missing indexes (see Database Optimization)
2. Increase connection pool size
3. Optimize queries (use EXPLAIN ANALYZE)

### Issue: Cache Hit Rate Below 90%

**Symptoms**: Cache stats show hit rate < 90%

**Diagnosis**:
```python
stats = cache.get_cache_stats()
print(f"Hit rate: {stats['hit_rate_percent']}%")
print(f"Cache size: {stats['memory_cache_size']}")
```

**Solutions**:
1. Increase LRU cache size (if memory allows)
2. Enable Redis for Layer 2 caching
3. Check cache invalidation frequency (too frequent = low hit rate)

### Issue: WebSocket Disconnections

**Symptoms**: Clients don't receive real-time updates

**Diagnosis**:
```javascript
// Client-side
ws.onerror = (error) => console.error('WebSocket error:', error);
ws.onclose = (event) => console.log('WebSocket closed:', event.code, event.reason);
```

**Solutions**:
1. Check firewall allows WebSocket (port 7272)
2. Implement reconnection logic in client
3. Verify server WebSocket configuration

---

**Document Version**: 1.0
**Last Updated**: 2025-10-24
**Next Review**: Before production deployment
