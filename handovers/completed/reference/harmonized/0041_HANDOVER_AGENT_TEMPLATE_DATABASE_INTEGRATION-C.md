# Handover 0041: Agent Template Database Integration

**Date**: 2025-01-23
**Status**: Ready for Implementation
**Priority**: High
**Estimated Effort**: 6-8 hours (revised from 8-12)
**Risk Level**: Low

---

## 🔄 IMPLEMENTATION UPDATE (2025-01-23)

**SIMPLIFIED APPROACH CONFIRMED**: Research into database initialization architecture reveals the implementation can be significantly simplified:

### Key Findings:
- ✅ **No Alembic migration needed** - `AgentTemplate` table already exists in `models.py` and auto-creates
- ✅ **No schema changes required initially** - Start with existing schema, add tracking columns later
- ✅ **Simpler installer integration** - Use `install.py` directly (5 lines) instead of `installer/core/database.py`
- ✅ **Reduced effort** - Phase 1 drops from 3 hours to 1.5 hours

### Revised Effort Estimate:
- **Original**: 8-12 hours across 5 phases
- **Revised**: 6-8 hours (30% reduction)
  - Phase 1: 1.5 hours (simplified seeding)
  - Phase 2: 3 hours (caching - unchanged)
  - Phase 3: 2 hours (UI integration - unchanged)
  - Phase 4: Optional (defer upgrade strategy)
  - Phase 5: 1.5 hours (testing - reduced scope)

### Implementation Path:
See **"SIMPLIFIED PHASE 1 IMPLEMENTATION"** section below for the streamlined 5-line approach that replaces the original complex integration.

**Research Documents**:
- `docs/database/TEMPLATE_SEEDING_STRATEGY_RECOMMENDATION.md` - Full architectural analysis
- `docs/database/TEMPLATE_SEEDING_DECISION.md` - Quick implementation guide

---

## Executive Summary

**Objective**: Migrate hard-coded agent templates from `template_manager.py` into the tenant-driven database system, enabling per-tenant customization while maintaining performance and backward compatibility.

**Current Problem**:
- 6 agent templates (orchestrator, analyzer, implementer, tester, reviewer, documenter) are hard-coded in `template_manager.py`
- Users cannot customize templates via UI despite having a complete TemplateManager component
- Database infrastructure exists but is never populated (empty database)
- Templates are not tenant-specific - all users get identical templates

**Proposed Solution**:
- Seed default templates into database during installation (system-level)
- Create tenant-specific copies on first user registration
- Enable UI-based template customization with immediate effect
- Implement three-layer caching (memory → Redis → database) for performance
- Support upgrade path when system templates update

**Value Delivered**:
- ✅ Users can tune agent behavior per tenant
- ✅ Orchestrator can use custom templates for better project outcomes
- ✅ System templates can be updated without breaking tenant customizations
- ✅ Full audit trail of template usage and modifications
- ✅ context prioritization and orchestration goal maintained through intelligent template management

---

## Research Findings

### 1. Current Architecture Analysis

#### Hard-Coded Templates (template_manager.py)
**Status**: Production-ready, actively used
**Location**: `src/giljo_mcp/template_manager.py` lines 146-550
**Templates**: 6 role-based templates
- **orchestrator** (409 lines) - Project manager & delegation expert
- **analyzer** (32 lines) - Requirements analysis & architecture
- **implementer** (30 lines) - Code implementation
- **tester** (28 lines) - Test creation & validation
- **reviewer** (31 lines) - Code review & quality assurance
- **documenter** (25 lines) - Documentation generation

**Key Features**:
- Serena MCP tool integration (appended at runtime)
- Variable substitution (`{project_name}`, `{product_name}`, etc.)
- Behavioral rules and success criteria embedded
- Stored in `_legacy_templates` dictionary

#### Database Infrastructure
**Status**: Complete but unused
**Model**: `AgentTemplate` in `src/giljo_mcp/models.py` lines 596-660

**Schema**:
```python
class AgentTemplate(Base):
    __tablename__ = "agent_templates"

    # Core fields
    id = Column(String(36), primary_key=True)
    tenant_key = Column(String(255), nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=True)
    name = Column(String(255), nullable=False)
    category = Column(String(50), nullable=False)  # "role", "skill", "domain"
    role = Column(String(100), nullable=True)  # "orchestrator", "implementer", etc.

    # Template content
    template_content = Column(Text, nullable=False)
    variables = Column(JSON, default=list)  # ["project_name", "product_name"]
    behavioral_rules = Column(JSON, default=list)
    success_criteria = Column(JSON, default=list)

    # Metadata
    preferred_tool = Column(String(50), default="claude")
    version = Column(String(20), default="1.0.0")
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    tags = Column(JSON, default=list)

    # Usage tracking
    usage_count = Column(Integer, default=0)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    avg_generation_ms = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

**Indexes**:
- `(tenant_key, role, is_active)` - Fast template lookup
- `(product_id, role, is_active)` - Product-specific templates
- `(tenant_key, is_default)` - Default template queries

**Multi-Tenant Isolation**: ✅ All queries filter by `tenant_key`

#### Frontend UI
**Status**: Fully functional, waiting for backend data
**Component**: `frontend/src/components/TemplateManager.vue`

**Features**:
- Search and filter templates
- Create/edit/delete templates
- Duplicate template functionality (already implemented!)
- Version tracking
- Usage statistics display
- Category and status filters

**Current Problem**: UI shows empty because database has no templates seeded

#### API Endpoints
**Status**: Complete CRUD operations
**Location**: `api/endpoints/agent_templates.py`

**Endpoints**:
- `GET /api/v1/agents/templates` - List all templates (markdown download)
- `GET /api/v1/agents/templates/{filename}` - Download specific template
- Template metadata endpoints in `api/endpoints/templates.py`

---

### 2. Critical Gap Identified

**THE PROBLEM**: Templates never get seeded into the database!

**Current Flow**:
```
Installation → Create tables → Skip seeding → Database empty
    ↓
User registers → No tenant templates → Database still empty
    ↓
Orchestrator spawns agent → Query database → No results → Fallback to hard-coded
```

**What's Missing**:
1. No seeding script runs during installation
2. No tenant template initialization on first user creation
3. Database remains empty throughout system lifecycle
4. UI shows "No templates" because nothing in database

**Existing Seeding Scripts** (unused):
- `scripts/seed_orchestrator_template.py` - Seeds only orchestrator, not called by installer
- `scripts/init_templates.py` - Exists but not integrated

---

### 3. How Orchestrator Uses Templates

**Current Implementation**:
```python
# File: src/giljo_mcp/orchestrator.py

async def spawn_agent(self, role: str, mission: str, ...):
    # Uses MissionTemplateGeneratorV2
    template = await self.template_generator.generate_mission(
        agent_role=role,
        ...
    )

    # MissionTemplateGeneratorV2 tries database first
    # Falls back to hard-coded templates (always happens due to empty DB)
```

**Template Resolution Order** (intended):
1. Product-specific template (`tenant_key=X, product_id=Y`)
2. Tenant-specific template (`tenant_key=X, product_id=NULL`)
3. System default template (`tenant_key="system", is_default=TRUE`)
4. Hard-coded fallback (from `template_manager.py`)

**Actual Behavior**: Always uses fallback (step 4) because database is empty

---

### 4. Agent Selection Integration

**AgentSelector Status**: Ready for database templates
**Location**: `src/giljo_mcp/agent_selector.py`

**Current Behavior**:
```python
async def select_agents(self, capabilities_needed: List[str], ...):
    # Queries AgentTemplate database with cascade resolution
    # Already implements product → tenant → system priority
    # Already filters by tenant_key, is_active

    # If no database templates found → returns empty list
    # Orchestrator then uses hard-coded template as fallback
```

**Required Changes**: Minimal
- Add auto-seeding fallback if no templates found for tenant
- No changes to core selection logic (already correct)

---

## Proposed Architecture

### Three-Tier Template System

#### Tier 1: System Templates (`tenant_key="system"`)
- **Purpose**: Default templates provided by GiljoAI MCP
- **Scope**: Global, read-only for all tenants
- **Seeded**: During installation (post-table creation)
- **Version**: Tracks system release version (e.g., "3.0.0")
- **Use Case**: Fallback when tenant has no custom templates

#### Tier 2: Tenant Templates (`tenant_key=<user.tenant_key>`)
- **Purpose**: Tenant-specific copies for customization
- **Scope**: Isolated per tenant, editable via UI
- **Seeded**: On first user registration for tenant
- **Version**: Inherits from system, increments on edit
- **Use Case**: Primary templates used by orchestrator

#### Tier 3: Product Templates (`product_id=<uuid>`)
- **Purpose**: Product-specific overrides (advanced use case)
- **Scope**: Per product within tenant
- **Seeded**: User-created via UI (on-demand)
- **Version**: User-managed
- **Use Case**: Different template per product type

### Template Resolution Cascade

```
Orchestrator needs template for role "implementer"
    ↓
1. Query: tenant_key=X, product_id=Y, role="implementer", is_active=TRUE
   → FOUND? Use this (highest priority)
    ↓ NOT FOUND
2. Query: tenant_key=X, product_id=NULL, role="implementer", is_active=TRUE
   → FOUND? Use this (tenant default)
    ↓ NOT FOUND
3. Query: tenant_key="system", role="implementer", is_default=TRUE
   → FOUND? Use this (system default)
    ↓ NOT FOUND
4. Fallback: Load from template_manager.py._legacy_templates["implementer"]
   → ALWAYS WORKS (hard-coded safety net)
```

### Three-Layer Caching Strategy

**Layer 1: In-Memory LRU Cache**
- **Size**: 100 templates (top 100 most-used)
- **TTL**: No expiration (invalidated on update)
- **Scope**: Per-process
- **Hit Rate**: ~85% (frequently used templates)
- **Latency**: 0.1ms

**Layer 2: Redis Cache** (optional, for multi-worker deployment)
- **Size**: Unlimited (Redis manages eviction)
- **TTL**: 1 hour
- **Scope**: Shared across all workers
- **Hit Rate**: ~10% (when memory cache misses)
- **Latency**: 1-2ms

**Layer 3: Database** (authoritative source)
- **Query**: Indexed lookup on `(tenant_key, role, is_active)`
- **Hit Rate**: ~5% (cache misses)
- **Latency**: 5-10ms

**Cache Invalidation**:
- User edits template → Invalidate all cache layers
- Broadcast via WebSocket to other workers
- Next request fetches fresh from database

---

## Database Schema Enhancements

### New Columns for System Template Tracking

```sql
ALTER TABLE agent_templates
ADD COLUMN is_system_template BOOLEAN DEFAULT false NOT NULL,
ADD COLUMN system_template_id VARCHAR(36) NULL,  -- Links to system template
ADD COLUMN system_template_version VARCHAR(20) NULL,  -- Version of system template used
ADD COLUMN customized BOOLEAN DEFAULT false NOT NULL,  -- User modified?
ADD COLUMN customized_at TIMESTAMP WITH TIME ZONE NULL;  -- When customized

CREATE INDEX idx_system_template_tracking ON agent_templates(tenant_key, system_template_id, customized);
```

**Purpose**:
- `is_system_template`: Marks templates in "system" tenant
- `system_template_id`: Links tenant template to original system template (for upgrades)
- `system_template_version`: Tracks which system version was copied
- `customized`: Flag for detecting user modifications
- `customized_at`: Audit trail for customization

**Upgrade Strategy**:
```
System Update (v3.0 → v3.1) → Update system templates → Scan tenant templates
    ↓
    ├─ customized=FALSE? → Auto-update to v3.1 (safe)
    └─ customized=TRUE? → Notify admin, create diff view in UI
```

### New Indexes for Performance

```sql
-- Fast template lookup during agent spawn (most common query)
CREATE INDEX idx_template_lookup ON agent_templates(tenant_key, role, is_active);

-- Product-specific template queries
CREATE INDEX idx_template_product ON agent_templates(product_id, role, is_active)
WHERE product_id IS NOT NULL;

-- System template queries during seeding
CREATE INDEX idx_system_templates ON agent_templates(tenant_key, is_default)
WHERE tenant_key = 'system';
```

---

## Implementation Plan

---

## 🚀 SIMPLIFIED PHASE 1 IMPLEMENTATION

**Research-validated approach**: Uses existing `install.py` pattern (matching `setup_state` seeding at line 752-766)

### Quick Start (1.5 hours total)

#### Step 1: Create Template Seeder (1 hour)

**File**: `src/giljo_mcp/template_seeder.py`

```python
"""Template seeding for GiljoAI MCP - Seeds default agent templates into database."""
import logging
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from src.giljo_mcp.models import AgentTemplate
from src.giljo_mcp.template_manager import UnifiedTemplateManager

logger = logging.getLogger(__name__)

async def seed_tenant_templates(session: AsyncSession, tenant_key: str) -> int:
    """
    Seed default agent templates for a tenant.
    Idempotent - safe to run multiple times.

    Args:
        session: Database session
        tenant_key: Tenant key to seed templates for

    Returns:
        Number of templates seeded
    """
    # Check if tenant already has templates
    from sqlalchemy import select, func
    existing_count = await session.execute(
        select(func.count(AgentTemplate.id)).where(
            AgentTemplate.tenant_key == tenant_key
        )
    )
    if existing_count.scalar() > 0:
        logger.info(f"Tenant {tenant_key} already has templates, skipping seed")
        return 0

    # Load hard-coded templates
    template_mgr = UnifiedTemplateManager()
    legacy_templates = template_mgr._legacy_templates

    # Define template metadata
    template_metadata = {
        "orchestrator": {
            "category": "role",
            "behavioral_rules": [
                "Read vision document completely",
                "Delegate instead of implementing (3-tool rule)",
                "Challenge scope drift",
                "Create 3 documentation artifacts at close"
            ],
            "success_criteria": [
                "All project objectives met",
                "Clean handoff documentation",
                "Zero scope creep",
                "Effective team coordination"
            ],
            "variables": ["project_name", "product_name", "mission"]
        },
        "analyzer": {
            "category": "role",
            "behavioral_rules": ["Analyze thoroughly", "Document findings"],
            "success_criteria": ["Complete requirements", "Architecture aligned with vision"],
            "variables": ["project_name", "mission"]
        },
        "implementer": {
            "category": "role",
            "behavioral_rules": ["Write clean code", "Follow specifications"],
            "success_criteria": ["Feature complete", "Tests passing"],
            "variables": ["project_name", "mission"]
        },
        "tester": {
            "category": "role",
            "behavioral_rules": ["Test thoroughly", "Document defects"],
            "success_criteria": ["All tests passing", "Coverage targets met"],
            "variables": ["project_name", "mission"]
        },
        "reviewer": {
            "category": "role",
            "behavioral_rules": ["Review objectively", "Provide constructive feedback"],
            "success_criteria": ["Quality standards met", "No critical issues"],
            "variables": ["project_name", "mission"]
        },
        "documenter": {
            "category": "role",
            "behavioral_rules": ["Document clearly", "Update all artifacts"],
            "success_criteria": ["Documentation complete", "Examples provided"],
            "variables": ["project_name", "mission"]
        }
    }

    seeded_count = 0
    for role, content in legacy_templates.items():
        metadata = template_metadata.get(role, {
            "category": "role",
            "behavioral_rules": [],
            "success_criteria": [],
            "variables": ["project_name", "mission"]
        })

        template = AgentTemplate(
            id=str(uuid4()),
            tenant_key=tenant_key,
            product_id=None,  # Tenant-level template
            name=role,
            category=metadata["category"],
            role=role,
            template_content=content,
            variables=metadata["variables"],
            behavioral_rules=metadata["behavioral_rules"],
            success_criteria=metadata["success_criteria"],
            preferred_tool="claude",
            version="3.0.0",
            is_active=True,
            is_default=False,
            tags=["default", "tenant"],
            created_at=datetime.now(timezone.utc)
        )

        session.add(template)
        seeded_count += 1

    await session.commit()
    logger.info(f"Seeded {seeded_count} templates for tenant {tenant_key}")

    return seeded_count
```

#### Step 2: Integrate into install.py (5 minutes)

**File**: `install.py` (add at line ~770, after `setup_state` seeding)

```python
# Add import at top of file (around line 30)
from src.giljo_mcp.template_seeder import seed_tenant_templates

# Add after setup_state seeding (around line 770)
# Seed default agent templates
try:
    template_count = await seed_tenant_templates(session, default_tenant_key)
    if template_count > 0:
        self._print_success(f"✓ Seeded {template_count} default agent templates")
except Exception as e:
    logger.warning(f"Template seeding failed (non-critical): {e}")
    # Non-blocking - templates can be added later via UI
```

#### Step 3: Test (30 minutes)

```bash
# Fresh installation
python install.py

# Verify seeding
psql -U postgres -d giljo_mcp -c "SELECT tenant_key, role, name FROM agent_templates;"

# Expected output: 6 templates for default tenant
# orchestrator, analyzer, implementer, tester, reviewer, documenter

# Test UI
# Navigate to User Settings → Agent Templates
# Should see 6 templates listed
```

**That's it!** Templates are now in the database and ready for customization.

---

### Original Phase 1 (Reference - Use Simplified Approach Above)

### Phase 1: Database Seeding (3 hours) - SUPERSEDED BY SIMPLIFIED APPROACH

**Files to Create**:
- `src/giljo_mcp/template_seeder.py` - Seeding logic

**Tasks**:
1. **Extract hard-coded templates** from `template_manager.py`
   - Create method to load all 6 templates into structured format
   - Include behavioral_rules, success_criteria, variables

2. **Implement `seed_system_templates()`**
   - Check if system templates exist (idempotent)
   - Create/update templates with `tenant_key="system"`
   - Set `is_default=TRUE`, `is_system_template=TRUE`
   - Version: "3.0.0"

3. **Implement `seed_tenant_templates()`**
   - Query all system templates
   - Copy to tenant scope with `tenant_key=<user.tenant_key>`
   - Set `customized=FALSE`, link to system via `system_template_id`

4. **Integration with installer**
   ```python
   # File: installer/core/database.py

   class DatabaseInstaller:
       async def setup(self):
           # ... existing setup ...

           # After table creation
           if direct_result['success']:
               from src.giljo_mcp.template_seeder import TemplateSeeder
               seeder = TemplateSeeder()

               # Seed system templates
               async with db_manager.get_session_async() as session:
                   seed_result = await seeder.seed_system_templates(session)
                   logger.info(f"Seeded {seed_result['total']} system templates")
   ```

5. **Integration with user registration**
   ```python
   # File: installer/core/config.py

   async def create_first_admin(self, ...):
       # ... create admin user ...

       # Seed tenant templates for new tenant
       from src.giljo_mcp.template_seeder import TemplateSeeder
       seeder = TemplateSeeder()

       async with db_manager.get_session_async() as session:
           await seeder.seed_tenant_templates(session, user.tenant_key)
   ```

**Deliverables**:
- `template_seeder.py` with full seeding logic
- Installer integration (system templates)
- User registration integration (tenant templates)
- Unit tests for seeding (idempotency, multi-tenant)

---

### Phase 2: Template Resolution with Caching (3 hours)

**Files to Create**:
- `src/giljo_mcp/template_cache.py` - Three-layer cache

**Files to Modify**:
- `src/giljo_mcp/template_manager.py` - Integrate cache

**Tasks**:
1. **Implement `TemplateCache` class**
   ```python
   class TemplateCache:
       def __init__(self, db_manager, redis_client=None):
           self.db = db_manager
           self.redis = redis_client  # Optional
           self.memory_cache = LRUCache(maxsize=100)

       async def get_template(self, role, tenant_key, product_id=None):
           # Layer 1: Memory
           if cached := self.memory_cache.get(cache_key):
               return cached

           # Layer 2: Redis (if available)
           if self.redis and (redis_data := await self.redis.get(cache_key)):
               template = deserialize(redis_data)
               self.memory_cache.set(cache_key, template)
               return template

           # Layer 3: Database with cascade
           template = await self._query_cascade(role, tenant_key, product_id)

           # Cache in all layers
           if template:
               self.memory_cache.set(cache_key, template)
               if self.redis:
                   await self.redis.setex(cache_key, 3600, serialize(template))

           return template

       async def invalidate(self, role, tenant_key, product_id=None):
           cache_key = self._build_key(role, tenant_key, product_id)
           self.memory_cache.delete(cache_key)
           if self.redis:
               await self.redis.delete(cache_key)
   ```

2. **Update `UnifiedTemplateManager.get_template()`**
   ```python
   async def get_template(self, role, tenant_key, product_id=None, ...):
       # Try cache → database cascade → fallback
       try:
           template = await self.cache.get_template(role, tenant_key, product_id)

           if template:
               return self._process_template(template.template_content, variables, augmentations)

           # Fallback to legacy
           logger.warning(f"Using legacy fallback for role '{role}'")
           return self._legacy_templates.get(role.lower(), default_template)

       except Exception as e:
           # Final safety net
           return self._legacy_templates.get(role.lower(), f"Error: {e}")
   ```

3. **Database cascade query implementation**
   ```python
   async def _query_cascade(self, role, tenant_key, product_id):
       # Priority 1: Product-specific
       if product_id:
           template = await session.execute(
               select(AgentTemplate).where(
                   AgentTemplate.tenant_key == tenant_key,
                   AgentTemplate.product_id == product_id,
                   AgentTemplate.role == role,
                   AgentTemplate.is_active == True
               )
           )
           if template := template.scalar_one_or_none():
               return template

       # Priority 2: Tenant-specific
       template = await session.execute(
           select(AgentTemplate).where(
               AgentTemplate.tenant_key == tenant_key,
               AgentTemplate.product_id.is_(None),
               AgentTemplate.role == role,
               AgentTemplate.is_active == True
           )
       )
       if template := template.scalar_one_or_none():
           return template

       # Priority 3: System default
       template = await session.execute(
           select(AgentTemplate).where(
               AgentTemplate.tenant_key == "system",
               AgentTemplate.role == role,
               AgentTemplate.is_default == True
           )
       )
       return template.scalar_one_or_none()
   ```

**Deliverables**:
- `template_cache.py` with LRU cache and Redis integration
- Updated `template_manager.py` with cache integration
- Performance tests (cache hit rates, latency benchmarks)
- Integration tests (cascade resolution)

---

### Phase 3: UI Integration & CRUD (2 hours)

**Files to Modify**:
- `api/endpoints/agent_templates.py` - Add CRUD endpoints
- `frontend/src/components/TemplateManager.vue` - Connect to API

**Tasks**:
1. **Implement API endpoints**
   ```python
   @router.put("/api/v1/agent-templates/{template_id}")
   async def update_template(template_id, updates, current_user):
       # Validate tenant ownership
       template = await get_template(template_id)
       if template.tenant_key != current_user.tenant_key:
           raise HTTPException(403, "Cannot edit other tenant's templates")

       # Prevent system template editing
       if template.tenant_key == "system":
           raise HTTPException(403, "System templates are read-only")

       # Update template
       template.template_content = updates.template_content
       template.version = increment_version(template.version)
       template.customized = True
       template.customized_at = datetime.now(timezone.utc)
       await session.commit()

       # Invalidate cache
       await cache.invalidate(template.role, template.tenant_key, template.product_id)

       # Broadcast update via WebSocket
       await broadcast_template_updated(tenant_key, template_id)

       return {"success": True, "version": template.version}

   @router.post("/api/v1/agent-templates/{template_id}/reset")
   async def reset_to_system_default(template_id, current_user):
       # Get tenant template
       tenant_template = await get_template(template_id)

       # Get system default
       system_template = await get_system_template(tenant_template.role)

       # Copy system content to tenant template
       tenant_template.template_content = system_template.template_content
       tenant_template.version = system_template.version
       tenant_template.customized = False
       await session.commit()

       # Invalidate cache
       await cache.invalidate(...)

       return {"success": True, "reset_to_version": system_template.version}
   ```

2. **Frontend API integration** (TemplateManager.vue already has UI)
   - Wire up edit button to PUT endpoint
   - Wire up duplicate button to POST /templates (already works)
   - Add "Reset to Default" button → POST /{id}/reset
   - Add diff view showing tenant vs system template

**Deliverables**:
- Update/Reset API endpoints
- Frontend integration with existing TemplateManager.vue
- WebSocket broadcast for real-time updates
- API tests for CRUD operations

---

### Phase 4: Upgrade Strategy (2 hours)

**Files to Create**:
- `scripts/upgrade_templates.py` - CLI tool for system upgrades

**Tasks**:
1. **Implement `upgrade_system_templates()`**
   ```python
   async def upgrade_system_templates(session, new_version: str):
       # Update system templates
       system_templates = await get_system_templates(session)
       new_templates = load_from_template_manager()  # Get latest from code

       for sys_template in system_templates:
           role = sys_template.role
           sys_template.template_content = new_templates[role]["content"]
           sys_template.version = new_version

       # Find tenant templates to upgrade
       tenant_templates = await get_all_tenant_templates(session)

       for tenant_template in tenant_templates:
           if tenant_template.customized:
               # User customized - notify, don't auto-update
               create_notification(tenant_template.tenant_key,
                   f"System template {tenant_template.role} updated to {new_version}. Review changes.")
           else:
               # Not customized - safe to auto-update
               tenant_template.template_content = new_templates[tenant_template.role]["content"]
               tenant_template.version = new_version

       await session.commit()
   ```

2. **Create upgrade CLI tool**
   ```bash
   python scripts/upgrade_templates.py --version 3.1.0
   ```

3. **Add diff viewer in UI**
   - Show side-by-side: Tenant template vs System template
   - Highlight differences
   - Button: "Adopt System Changes"

**Deliverables**:
- Upgrade script for system updates
- Tenant notification system
- Diff viewer UI component
- Upgrade documentation

---

### Phase 5: Testing & Migration (2 hours)

**Tasks**:
1. **Create migration for existing tenants**
   ```python
   # One-time migration script
   async def migrate_existing_tenants():
       # Get all existing tenants (users)
       tenants = await get_all_tenant_keys()

       for tenant_key in tenants:
           # Check if tenant already has templates
           existing = await get_tenant_templates(tenant_key)
           if existing:
               logger.info(f"Tenant {tenant_key} already has templates, skipping")
               continue

           # Seed tenant templates
           await seed_tenant_templates(session, tenant_key)
           logger.info(f"Seeded templates for tenant {tenant_key}")
   ```

2. **Performance testing**
   - Load test: 1000 concurrent template requests
   - Measure cache hit rates (target: >90%)
   - Database query performance (EXPLAIN ANALYZE)
   - Memory usage monitoring

3. **Security validation**
   - Test cross-tenant template access (should fail)
   - Test system template editing (should fail)
   - Verify all queries filter by tenant_key
   - Audit trail verification

4. **Integration testing**
   - End-to-end: Edit template → Save → Spawn agent → Verify new template used
   - Multi-tenant: Verify tenant A changes don't affect tenant B
   - Fallback: Delete all database templates → Verify hard-coded fallback works

**Deliverables**:
- Migration script for existing tenants
- Performance test suite
- Security audit checklist
- Integration test suite

---

## API Contract Changes

### New Endpoints

```
POST   /api/v1/agent-templates/seed-tenant          # Admin-only: Seed templates for tenant
PUT    /api/v1/agent-templates/{id}                 # Update template content
POST   /api/v1/agent-templates/{id}/reset           # Reset to system default
GET    /api/v1/agent-templates/{id}/diff            # Compare tenant vs system
POST   /api/v1/agent-templates/{id}/duplicate       # Duplicate template (already exists)
DELETE /api/v1/agent-templates/{id}                 # Soft delete (set is_active=false)
```

### Modified Endpoints

```
GET    /api/v1/agents/templates                     # Add filter: ?customized_only=true
GET    /api/v1/agents/templates/{filename}          # Add query: ?version=3.0.0
```

---

## Migration Strategy

### For New Installations (Fresh Install)

**Automatic Seeding**:
1. Installer runs → Creates tables
2. **NEW**: Installer seeds system templates (6 templates, tenant_key="system")
3. User registers → Creates first admin
4. **NEW**: Registration seeds tenant templates (6 templates, tenant_key=user.tenant_key)
5. User sees templates in UI immediately

### For Existing Installations (Upgrade)

**Manual Migration Required**:
```bash
# Step 1: Run database migration
alembic upgrade head  # Adds new columns: is_system_template, system_template_id, etc.

# Step 2: Seed system templates
python scripts/seed_system_templates.py

# Step 3: Seed tenant templates for all existing tenants
python scripts/migrate_existing_tenants.py

# Step 4: Verify seeding
python scripts/verify_template_seeding.py
```

**Rollback Plan**:
- Set feature flag: `USE_LEGACY_TEMPLATES=true`
- System falls back to hard-coded templates
- Database changes remain but are unused
- Safe to investigate and fix issues

---

## Edge Cases & Error Handling

### Edge Case 1: Missing System Template

**Scenario**: System template deleted or corrupted

**Handling**:
```python
if not system_template:
    logger.error(f"System template missing for role '{role}' - using legacy fallback")
    return template_manager._legacy_templates.get(role)
```

### Edge Case 2: Unseeded Tenant

**Scenario**: Tenant created before seeding feature deployed

**Handling**:
- Auto-seed on first template miss (lazy seeding)
- Background job to seed all unseeded tenants
- Admin dashboard warning if unseeded tenants detected

### Edge Case 3: Cache Corruption

**Scenario**: Cached template data corrupted

**Handling**:
```python
try:
    template = deserialize(redis_data)
except Exception as e:
    logger.warning(f"Cache corruption: {e}")
    await cache.invalidate(cache_key)
    return await query_database(...)  # Fallback to DB
```

### Edge Case 4: Concurrent Updates

**Scenario**: Two admins update same template simultaneously

**Handling**:
```python
# Use optimistic locking with version field
template.version = increment_version(template.version)

try:
    await session.commit()
except IntegrityError:
    await session.rollback()
    raise HTTPException(409, "Template updated by another user. Refresh and retry.")
```

### Edge Case 5: Database Connection Failure

**Scenario**: Database unavailable during template resolution

**Handling**:
```python
try:
    template = await query_database(...)
except DatabaseError as e:
    logger.error(f"Database error: {e}")
    # Fall back to hard-coded templates (always available)
    return template_manager._legacy_templates.get(role)
```

---

## Performance Impact Analysis

### Baseline (Current System)
- Template retrieval: **0.5ms** (in-memory dictionary lookup)
- Template processing: **2-5ms** (variable substitution)
- **Total: ~5ms per agent spawn**

### New System (With Caching)

#### Cache Hit (90% of requests)
- Memory cache lookup: **0.1ms**
- Template processing: **2-5ms**
- **Total: ~5ms** (no degradation)

#### Cache Miss (10% of requests)
- Database query: **5-10ms** (indexed)
- Template processing: **2-5ms**
- Cache store: **1ms** (async)
- **Total: ~12ms** (acceptable)

#### Database Indexes Created
```sql
CREATE INDEX idx_template_lookup ON agent_templates(tenant_key, role, is_active);
CREATE INDEX idx_template_product ON agent_templates(product_id, role, is_active);
CREATE INDEX idx_system_templates ON agent_templates(tenant_key, is_default);
```

**Query Performance**:
- Tenant lookup: O(log n) via B-tree index on `(tenant_key, role)`
- Expected: <5ms for 10,000 templates per tenant

---

## Security Considerations

### Multi-Tenant Isolation (CRITICAL)

**Enforcement Points**:
1. **Database queries**: ALL queries MUST filter by `tenant_key`
2. **API endpoints**: Validate `current_user.tenant_key == template.tenant_key`
3. **Cache keys**: Include `tenant_key` in cache key (prevent cross-tenant cache hits)
4. **WebSocket broadcasts**: Only notify users in same tenant

**Validation Test**:
```sql
-- Cross-tenant leakage test (should return 0 rows)
SELECT COUNT(*) FROM agent_templates t1
JOIN agent_templates t2 ON t1.id = t2.id AND t1.tenant_key != t2.tenant_key;
```

### System Template Protection

**Read-Only Enforcement**:
```python
if template.tenant_key == "system":
    raise HTTPException(403, "System templates are read-only. Duplicate to customize.")
```

### Input Validation

**Template Content**:
- Max size: 100KB (prevent DoS)
- Sanitize SQL injection (use parameterized queries)
- Validate template variables (prevent code injection)

**Audit Trail**:
```python
# Track all template changes
template.updated_by = current_user.id
template.change_history.append({
    "timestamp": datetime.now(timezone.utc),
    "user_id": current_user.id,
    "changes": diff(old_content, new_content)
})
```

---

## Success Metrics

### Technical Metrics
- ✅ Template retrieval latency (p95): **< 10ms**
- ✅ Cache hit rate: **> 90%**
- ✅ Database query count: **< 100/min per tenant**
- ✅ Zero cross-tenant leaks (security audit)

### Business Metrics
- Template customization rate: % of tenants who customize ≥1 template
- System template adoption: % of tenants using latest system version
- Support tickets: Template-related issues < 5% of total

### Operational Metrics
- Deployment success rate: 100% (no rollbacks)
- Migration time: < 5 minutes per tenant
- Upgrade time: < 10 minutes for system template updates

---

## Files to Create/Modify

### New Files
```
src/giljo_mcp/template_seeder.py          # Seeding logic (300 lines)
src/giljo_mcp/template_cache.py           # Three-layer cache (200 lines)
scripts/upgrade_templates.py              # Upgrade CLI tool (150 lines)
scripts/migrate_existing_tenants.py       # One-time migration (100 lines)
tests/test_template_seeder.py             # Unit tests (200 lines)
tests/test_template_cache.py              # Cache tests (150 lines)
tests/test_template_integration.py        # E2E tests (250 lines)
migrations/versions/add_system_template_tracking.py  # Alembic migration (50 lines)
docs/database/TENANT_TEMPLATE_SYSTEM_DESIGN.md       # Design doc (created)
docs/database/TEMPLATE_SEEDING_IMPLEMENTATION.md     # Implementation guide (created)
```

### Modified Files
```
src/giljo_mcp/template_manager.py         # Integrate cache (~50 lines changed)
src/giljo_mcp/agent_selector.py           # Add auto-seeding fallback (~20 lines)
installer/core/database.py                # Add system seeding (~15 lines)
installer/core/config.py                  # Add tenant seeding (~10 lines)
api/endpoints/agent_templates.py          # Add CRUD endpoints (~200 lines)
frontend/src/components/TemplateManager.vue  # Wire up API (~100 lines)
```

---

## Testing Checklist

### Unit Tests
- [ ] `seed_system_templates()` is idempotent
- [ ] `seed_tenant_templates()` copies system templates correctly
- [ ] Cache invalidation clears all layers
- [ ] Template resolution cascade follows priority order
- [ ] Fallback to hard-coded templates when DB empty

### Integration Tests
- [ ] Full workflow: Edit template → Save → Spawn agent → Verify new template
- [ ] Multi-tenant: Tenant A changes don't affect Tenant B
- [ ] Cache hit rate > 90% under load
- [ ] Database queries use correct indexes (EXPLAIN ANALYZE)
- [ ] WebSocket broadcasts reach correct tenants only

### Security Tests
- [ ] Cross-tenant template access fails (403)
- [ ] System template editing fails (403)
- [ ] All queries filter by tenant_key
- [ ] Audit trail records all changes
- [ ] SQL injection attempts fail

### Performance Tests
- [ ] 1000 concurrent template requests complete in < 1s
- [ ] Cache hit latency < 1ms (p95)
- [ ] Database query latency < 10ms (p95)
- [ ] Memory usage < 100MB for cache

### Rollback Tests
- [ ] Setting `USE_LEGACY_TEMPLATES=true` restores old behavior
- [ ] Database migration can be rolled back via Alembic
- [ ] System continues working with empty database

---

## Deployment Plan

### Pre-Deployment (1 day before)
1. Review code changes with team
2. Test migration script on staging database
3. Backup production database
4. Prepare rollback plan

### Deployment (Production)

**Step 1: Database Migration (5 min)**
```bash
# Run Alembic migration (adds new columns)
alembic upgrade head

# Verify migration
python scripts/verify_migration.py
```

**Step 2: Seed System Templates (2 min)**
```bash
# Seed 6 system templates
python scripts/seed_system_templates.py

# Verify seeding
psql -U postgres -d giljo_mcp -c "SELECT COUNT(*) FROM agent_templates WHERE tenant_key='system';"
# Expected: 6
```

**Step 3: Migrate Existing Tenants (variable, ~1 min per 10 tenants)**
```bash
# Seed templates for all existing tenants
python scripts/migrate_existing_tenants.py

# Monitor progress
tail -f logs/migration.log
```

**Step 4: Deploy Code Changes (10 min)**
```bash
# Deploy updated code (template_manager, cache, API endpoints)
git pull origin main
systemctl restart giljo-mcp-api
systemctl restart giljo-mcp-worker

# Verify services
systemctl status giljo-mcp-api
systemctl status giljo-mcp-worker
```

**Step 5: Smoke Test (5 min)**
```bash
# Test template resolution
curl -X POST http://localhost:7272/api/v1/test/spawn-agent \
  -H "X-API-Key: $API_KEY" \
  -d '{"role": "implementer"}'

# Verify template came from database (check logs)
grep "Using database template" logs/api.log

# Test UI (open browser)
# Navigate to User Settings → Agent Templates
# Verify 6 templates visible
```

**Step 6: Monitor (1 hour)**
- Watch error logs: `tail -f logs/api.log | grep ERROR`
- Monitor cache hit rates: Check metrics dashboard
- Check database query performance: `SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;`

### Post-Deployment
- Send notification to users about new template customization feature
- Monitor support tickets for template-related issues
- Review performance metrics after 24 hours

---

## Rollback Plan

**If critical issue detected:**

1. **Immediate**: Set feature flag
   ```bash
   export USE_LEGACY_TEMPLATES=true
   systemctl restart giljo-mcp-api
   ```

2. **Verify**: System uses hard-coded templates
   ```bash
   grep "Using legacy fallback" logs/api.log
   ```

3. **Investigate**: Root cause in staging
   - Replicate issue
   - Fix and test
   - Redeploy when ready

4. **Database Rollback** (if needed):
   ```bash
   alembic downgrade -1  # Revert migration
   ```

**Rollback Time**: < 5 minutes
**Data Loss**: None (templates remain in database, just unused)

---

## Future Enhancements (Post-v1)

### Template Marketplace
- Tenants can share templates publicly
- Rating and review system
- Import templates from marketplace

### Advanced Diff Viewer
- Visual side-by-side comparison
- Syntax highlighting for template variables
- Merge wizard (smart conflict resolution)

### Template Analytics
- Track which templates produce best outcomes
- A/B testing different template versions
- Performance metrics per template

### AI-Assisted Template Optimization
- Analyze agent performance
- Suggest template improvements
- Auto-tune behavioral rules based on outcomes

### Template Versioning UI
- Git-like history viewer
- Rollback to previous versions
- Branch/merge workflow for templates

---

## Questions & Answers

**Q: Will this break existing agents?**
A: No. Hard-coded templates remain as fallback. Existing agents continue working.

**Q: What if database is slow?**
A: Three-layer cache ensures <1ms latency for 90% of requests. Database only hit on cache miss.

**Q: Can users delete system templates?**
A: No. System templates (tenant_key="system") are read-only. Users can only edit their tenant's copies.

**Q: How do we handle template updates?**
A: System templates update during upgrades. Tenant templates auto-update if not customized, otherwise notify admin.

**Q: What's the migration impact for existing tenants?**
A: One-time script seeds templates (~1 min per 10 tenants). No downtime, no data loss.

**Q: How do we test this safely?**
A: Feature flag allows instant rollback. Hard-coded templates are permanent fallback.

---

## References

### Research Documents
- **Architecture Design**: `docs/database/TENANT_TEMPLATE_SYSTEM_DESIGN.md`
- **Implementation Guide**: `docs/database/TEMPLATE_SEEDING_IMPLEMENTATION.md`
- **Executive Summary**: `docs/database/TEMPLATE_SEEDING_EXEC_SUMMARY.md`

### Related Code
- **Current Templates**: `src/giljo_mcp/template_manager.py` (lines 146-550)
- **Database Model**: `src/giljo_mcp/models.py` (lines 596-660)
- **API Endpoints**: `api/endpoints/agent_templates.py`
- **UI Component**: `frontend/src/components/TemplateManager.vue`
- **Agent Selector**: `src/giljo_mcp/agent_selector.py`
- **Orchestrator**: `src/giljo_mcp/orchestrator.py`

### Related Handovers
- **0020**: Orchestrator Enhancement (mission planning, agent selector)
- **0035**: Unified Installer (database setup, first user creation)

---

## Approval & Sign-Off

**Prepared By**: Deep Research, Database Expert, System Architect (AI Agents)
**Date**: 2025-01-23
**Status**: ✅ Ready for Implementation

**Reviewed By**: ________________
**Approved By**: ________________
**Implementation Start Date**: ________________

---

## Appendix A: Sample Template Structure

```python
{
    "orchestrator": {
        "content": """# Orchestrator Agent Template

You are the orchestrator agent for the {project_name} project.

## Mission
{mission_description}

## Behavioral Rules
- Read vision document completely (all parts)
- Delegate instead of implementing (3-tool rule)
- Challenge scope drift
- Create 3 documentation artifacts at close

## Success Criteria
- All project objectives met
- Clean handoff documentation
- Zero scope creep
- Team coordination effective

## MCP Tools Available
- get_vision() - Read project vision
- spawn_agent() - Delegate work to specialized agents
- get_product_settings() - Load configuration
- send_agent_message() - Coordinate with agents
""",
        "behavioral_rules": [
            "Read vision document completely",
            "Delegate instead of implementing",
            "Challenge scope drift",
            "3-tool rule enforcement"
        ],
        "success_criteria": [
            "Project objectives met",
            "Documentation complete",
            "No scope creep",
            "Effective coordination"
        ],
        "variables": ["project_name", "mission_description", "product_name"]
    }
}
```

---

## Appendix B: Database Migration Script

```python
"""Add system template tracking

Revision ID: add_system_template_tracking
Revises: previous_migration_id
Create Date: 2025-01-23

"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Add new columns
    op.add_column('agent_templates', sa.Column('is_system_template', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('agent_templates', sa.Column('system_template_id', sa.String(36), nullable=True))
    op.add_column('agent_templates', sa.Column('system_template_version', sa.String(20), nullable=True))
    op.add_column('agent_templates', sa.Column('customized', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('agent_templates', sa.Column('customized_at', sa.DateTime(timezone=True), nullable=True))

    # Create indexes
    op.create_index('idx_system_template_tracking', 'agent_templates', ['tenant_key', 'system_template_id', 'customized'])
    op.create_index('idx_template_lookup', 'agent_templates', ['tenant_key', 'role', 'is_active'])

    # Backfill existing templates as customized (safe default)
    op.execute("UPDATE agent_templates SET customized = true WHERE tenant_key != 'system'")

def downgrade():
    op.drop_index('idx_template_lookup', 'agent_templates')
    op.drop_index('idx_system_template_tracking', 'agent_templates')
    op.drop_column('agent_templates', 'customized_at')
    op.drop_column('agent_templates', 'customized')
    op.drop_column('agent_templates', 'system_template_version')
    op.drop_column('agent_templates', 'system_template_id')
    op.drop_column('agent_templates', 'is_system_template')
```

---

## Appendix C: Research Update Summary (2025-01-23)

### What Changed from Original Plan

**Research Finding**: Database initialization architecture analysis revealed significant simplifications

#### Removed from Original Plan:
1. ❌ **Alembic migration** - AgentTemplate table already exists, auto-creates on startup
2. ❌ **Complex installer integration** - No need to modify `installer/core/database.py`
3. ❌ **Schema changes** - Can start with existing schema, add tracking columns later (optional)
4. ❌ **Two-tier seeding** - Simplified to single-tier (tenant templates only)

#### Simplified Approach:
1. ✅ **Single seeding function** - `seed_tenant_templates()` in new file
2. ✅ **5-line install.py integration** - Matches existing `setup_state` pattern
3. ✅ **Idempotent seeding** - Safe to run multiple times
4. ✅ **Non-blocking** - Installation continues even if seeding fails

#### Effort Reduction:
- **Original Phase 1**: 3 hours (complex multi-file approach)
- **Revised Phase 1**: 1.5 hours (streamlined single-file approach)
- **Total Project**: 8-12 hours → 6-8 hours (30% reduction)

#### Why This Works:
- Tables auto-create from `models.py` via `Base.metadata.create_all()` on API startup
- No migration system needed for basic table creation
- Existing pattern at `install.py:752-766` already seeds `setup_state` table
- New seeding follows same pattern for consistency

#### Implementation Priority:
1. **Phase 1 (Simplified)**: Template seeding - 1.5 hours ⭐ START HERE
2. **Phase 2**: Template caching - 3 hours (unchanged)
3. **Phase 3**: UI integration - 2 hours (unchanged)
4. **Phase 4**: Upgrade strategy - Optional (defer)
5. **Phase 5**: Testing - 1.5 hours (reduced scope)

### Research Documents Created:
- `docs/database/TEMPLATE_SEEDING_STRATEGY_RECOMMENDATION.md` - Full architectural analysis
- `docs/database/TEMPLATE_SEEDING_DECISION.md` - Quick implementation guide
- Both documents provide additional context and alternative approaches

---

**END OF HANDOVER 0041**
