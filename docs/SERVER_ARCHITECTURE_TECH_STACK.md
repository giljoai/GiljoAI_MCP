# Server Architecture & Tech Stack

> **Edition Context (2026-03-07):** This document describes the GiljoAI MCP Community Edition architecture. The full system serves two editions from one codebase (split before public release). Community Edition includes everything documented here. SaaS Edition layers on top with OAuth/SSO, billing, org management, and enterprise deployment. Tenant isolation infrastructure exists in both editions -- Community uses it silently (single implicit tenant), SaaS uses it explicitly (multi-org). See [0770 SaaS Edition Proposal](../handovers/0770_SAAS_EDITION_PROPOSAL.md) for the architectural decision record.

**Document Version**: 10_21_2025
**Status**: Single Source of Truth
**Last Updated**: 2025-01-05 (Harmonized)
**Harmonization Status**: ✅ Aligned with codebase

---

## Quick Links to Harmonized Documents

- **[Simple_Vision.md](../handovers/Simple_Vision.md)** - User journey & product vision
- **[start_to_finish_agent_FLOW.md](../handovers/start_to_finish_agent_FLOW.md)** - Technical verification & agent flow
- **[Vision Documents](Vision/)** - Complete vision & architecture documentation

**Agent Templates** (verified in codebase):
- 6 default templates: orchestrator, implementer, tester, analyzer, reviewer, documenter
- Source: `src/giljo_mcp/template_seeder.py::_get_default_templates_v103()`

---

## v3.0 Unified Architecture Overview

GiljoAI MCP v3.0 implements a **unified architecture** with no deployment modes. The system ALWAYS binds to all network interfaces while using OS firewall for access control, providing consistent behavior across localhost, LAN, and WAN deployments.

### Core Architectural Principles

**Single Network Binding**:
- API server ALWAYS binds to `0.0.0.0` (all network interfaces)
- OS firewall controls actual access (defense in depth)
- Database ALWAYS on localhost (never exposed to network)
- ONE authentication flow for ALL connections (localhost, LAN, WAN)

**Defense in Depth Security**:
1. **OS Firewall** - First layer of protection
2. **Application Authentication** - JWT + password validation  
3. **Password Policy** - Complexity requirements and forced changes
4. **Database Isolation** - PostgreSQL never exposed to network
5. **HTTPS/TLS** - Encrypted transport for WAN deployments

---

## Network Topology

### ASCII Architecture Diagram

**VERIFIED AGAINST CODE** (`api/app.py:185-188`, `database.py:40-60`):

```
User Access (controlled by OS firewall):
┌──────────────────────────────────────────┐
│ Localhost:    http://127.0.0.1:7272      │
│ LAN (if fw):  http://10.1.0.164:7272     │  
│ WAN (if fw):  https://example.com:443    │
└───────────────────┬──────────────────────┘
                    │
                    ▼
       ┌────────────────────────┐
       │  API Server (FastAPI)  │
       │  Binds to: 0.0.0.0     │ ← ALWAYS all interfaces
       │  Port: 7272            │
       │  Auth: JWT Required    │
       └────────────┬───────────┘
                    │
                    │ ALWAYS localhost (security)
                    ▼
       ┌────────────────────────┐
       │  PostgreSQL Database   │
       │  Host: localhost       │ ← NEVER changes
       │  Port: 5432            │
       │  Binding: 127.0.0.1    │
       └────────────────────────┘
```

**Code Verification**:
- **API Binding**: `api/app.py:532-538` - CORS middleware configured for 0.0.0.0 binding
- **Database Host**: `api/app.py:185` - `state.config.database.host` (always "localhost")
- **Port Configuration**: `api/app.py:467-468` - Default ports 7272 (API), 7274 (frontend)

### Network Access Control

**Firewall Configuration** (Windows PowerShell example):
```powershell
# Block external access by default
New-NetFirewallRule -DisplayName "GiljoAI MCP - Block External" `
    -Direction Inbound -Action Block -Protocol TCP -LocalPort 7272

# Allow localhost access
New-NetFirewallRule -DisplayName "GiljoAI MCP - Allow Localhost" `
    -Direction Inbound -Action Allow -Protocol TCP -LocalPort 7272 `
    -RemoteAddress 127.0.0.1,::1

# Optional: Allow specific LAN range
New-NetFirewallRule -DisplayName "GiljoAI MCP - Allow LAN" `
    -Direction Inbound -Action Allow -Protocol TCP -LocalPort 7272 `
    -RemoteAddress 192.168.1.0/24
```

**Linux iptables Configuration**:
```bash
# Block external access
sudo iptables -A INPUT -p tcp --dport 7272 -s ! 127.0.0.1 -j DROP

# Allow localhost
sudo iptables -I INPUT -p tcp --dport 7272 -s 127.0.0.1 -j ACCEPT

# Optional: Allow specific LAN range  
sudo iptables -I INPUT -p tcp --dport 7272 -s 192.168.1.0/24 -j ACCEPT
```

---

## Technology Stack

### Backend Stack

**Core Framework**:
- **FastAPI 0.104+** - Modern Python web framework
- **Python 3.11+** - Required minimum version
- **SQLAlchemy 2.0** - Database ORM with async support
- **PostgreSQL 18** - Primary database (REQUIRED)

**Code Reference**: `api/app.py:361-425` - FastAPI app configuration

**Authentication & Security**:
- **JWT (JSON Web Tokens)** - Session management
- **bcrypt** - Password hashing (cost factor: 12)
- **CORS Middleware** - Cross-origin request handling
- **Rate Limiting** - 60 requests/minute default

**Code Reference**: `api/app.py:518-538` - Middleware stack configuration

**Database Layer**:
```python
# From src/giljo_mcp/database.py:40-80
class DatabaseManager:
    def _create_sync_engine(self) -> Engine:
        return create_engine(
            self.database_url,
            poolclass=QueuePool,
            pool_size=20,         # Production-optimized
            max_overflow=40,      # Handle burst traffic
            pool_pre_ping=True,   # Connection health checks
            pool_recycle=3600,    # 1-hour connection recycling
            echo=False,           # Disable SQL logging in production
        )
```

**WebSocket Support**:
- **Real-time updates** for agent monitoring
- **Authentication-gated** WebSocket connections
- **Heartbeat mechanism** (30-second intervals)

**Code Reference**: `api/app.py:597-710` - WebSocket endpoint implementation

### Frontend Stack

**Core Framework**:
- **Vue 3** - Progressive JavaScript framework (Composition API)
- **Vuetify 3** - Material Design 3 component library
- **Node.js 18+** - JavaScript runtime requirement
- **Vite** - Build tool and development server

**State Management**:
- **Pinia** - Vue 3 state management
- **WebSocket Integration** - Real-time state updates
- **JWT Token Management** - Client-side authentication

**Development Server**:
- **Port 7274** - Production frontend port
- **Port 5173** - Vite development server port
- **Hot Module Replacement** - Development-time features

### Database Architecture

**PostgreSQL 18 Requirements**:
```sql
-- Required PostgreSQL version
SELECT version();
-- Expected: PostgreSQL 18.x

-- Connection pooling configuration
SHOW max_connections;        -- Default: 100
SHOW shared_buffers;         -- Recommended: 256MB+
SHOW effective_cache_size;   -- Recommended: 1GB+
```

**Multi-Tenant Isolation**:
```sql
-- All tables include tenant_key for isolation
CREATE TABLE products (
    id VARCHAR(36) PRIMARY KEY,
    tenant_key VARCHAR(36) NOT NULL,  -- ← ISOLATION COLUMN
    name VARCHAR(255) NOT NULL,
    -- ... other columns
);

-- Optimized indexes for multi-tenant queries  
CREATE INDEX idx_products_tenant_name ON products(tenant_key, name);
CREATE INDEX idx_projects_tenant_status ON projects(tenant_key, status);
```

**Performance Optimizations**:
- **GIN indexes** for JSONB config data (PostgreSQL-specific)
- **Connection pooling** with health checks
- **Query optimization** with tenant-first indexing
- **Connection recycling** to prevent memory leaks

**Code Reference**: `src/giljo_mcp/models.py:80-100` - Index configurations

### Database Schema Evolution (Recent Handovers)

GiljoAI MCP's database schema has been enhanced through multiple handovers to support advanced features.

#### Single Active Product Architecture (Handover 0050)

**Product Table Constraint** - Enforce single active product per tenant:
```sql
-- Partial unique index (PostgreSQL 9.0+)
CREATE UNIQUE INDEX idx_product_single_active_per_tenant
ON products (tenant_key)
WHERE is_active = true;
```

**Key Features**:
- Only ONE product can be active per tenant at any time
- Database-level atomicity prevents race conditions
- Partial index (efficient - only indexes active products)
- Clear constraint violation errors guide users
- Migration includes auto-repair logic for existing conflicts

**Business Impact**:
- Prevents context confusion in multi-agent workflows
- Clear product lifecycle semantics
- Foundation for product-scoped agent jobs
- Enables proper orchestrator validation

#### Single Active Project Extension (Handover 0050b)

Building on the single active product architecture, only ONE project can be active per product:

```sql
-- Partial unique index on projects table
CREATE UNIQUE INDEX idx_project_single_active_per_product
ON projects (product_id)
WHERE status = 'active';
```

**Key Features**:
- **Cascade Deactivation**: Switching products automatically pauses all projects under previous product
- **Product Scoping**: Projects view filtered to show only active product's projects
- **Context Clarity**: Agents operate on single product → single project context
- **Enhanced Warning**: Dialog shows project impact before product switch

**Business Impact**:
- Prevents project context confusion
- Ensures clear agent focus
- Supports hierarchical architecture (Tenant → Product → Project → Agents)

#### Project Soft Delete with Recovery (Handover 0070)

**Implementation Date**: October 27, 2025
**Status**: Production-ready soft delete pattern with user-facing recovery UI

Projects support soft delete with a 10-day recovery window, providing users with a safety net while maintaining clean data management.

**Database Schema**:
```sql
-- Add deleted_at timestamp column to projects table
ALTER TABLE projects ADD COLUMN deleted_at TIMESTAMP NULL;

-- Partial index for efficient deleted project queries
CREATE INDEX idx_projects_deleted_at ON projects(deleted_at)
WHERE deleted_at IS NOT NULL;
```

**Soft Delete Pattern**:
```sql
-- Soft delete operation (DELETE endpoint)
UPDATE projects
SET status = 'deleted',
    deleted_at = NOW()
WHERE id = ? AND tenant_key = ?;

-- Filter deleted projects from normal views
SELECT * FROM projects
WHERE tenant_key = ?
  AND (status != 'deleted' OR deleted_at IS NULL);

-- Query deleted projects (recovery UI)
SELECT * FROM projects
WHERE tenant_key = ?
  AND deleted_at IS NOT NULL
ORDER BY deleted_at DESC;
```

**Recovery Operations**:
```sql
-- Restore deleted project (POST /projects/{id}/restore)
UPDATE projects
SET status = 'inactive',
    deleted_at = NULL
WHERE id = ? AND tenant_key = ?
  AND deleted_at IS NOT NULL;

-- Calculate days until purge (used in UI)
SELECT
  id,
  name,
  deleted_at,
  10 - EXTRACT(DAY FROM NOW() - deleted_at) as days_until_purge
FROM projects
WHERE tenant_key = ?
  AND deleted_at IS NOT NULL;
```

**Purge Strategy**:

GiljoAI MCP uses **startup-based purge** (Option C from design):
- Purge runs on application startup via `startup.py`
- Zero infrastructure requirements (no background scheduler needed)
- Simple, reliable, and sufficient for typical usage patterns

```python
# Executed during startup.py
async def purge_expired_deleted_projects():
    """Permanently delete projects older than 10 days"""
    cutoff_date = datetime.utcnow() - timedelta(days=10)

    expired = await session.execute(
        select(Project)
        .where(Project.deleted_at < cutoff_date)
        .where(Project.deleted_at.isnot(None))
    )

    for project in expired.scalars().all():
        # Cascade delete child records
        await delete_project_agents(session, project.id)
        await delete_project_tasks(session, project.id)
        await delete_project_messages(session, project.id)
        await delete_project_jobs(session, project.id)

        # Permanently delete project
        await session.delete(project)
        logger.info(f"Purged expired project: {project.name} (id: {project.id})")

    await session.commit()
```

**Cascade Delete Rules**:
When permanently purging a project, all child records are deleted:
```
Project (deleted_at > 10 days ago)
  ├── Agents (CASCADE DELETE)
  ├── Tasks (CASCADE DELETE)
  ├── Messages (CASCADE DELETE)
  └── Agent Jobs (CASCADE DELETE)
```

**Multi-Tenant Isolation**:
All soft delete operations enforce tenant boundaries:
- Delete: Only projects matching tenant_key can be deleted
- Recovery: GET /deleted and POST /restore filtered by tenant_key
- Purge: Expired project query includes tenant_key filter
- Zero cross-tenant leakage in recovery UI

**API Endpoints** (3 Total):
- DELETE `/api/v1/projects/{project_id}` - Soft delete project
- GET `/api/v1/projects/deleted` - List deleted projects with purge countdown
- POST `/api/v1/projects/{project_id}/restore` - Restore deleted project

**Recovery UI Location**:
Settings → Database tab → Deleted Projects section
- Table displays: Project Name, Product, Deleted Date, Days Until Purge
- Restore button with confirmation dialog
- Empty state when no deleted projects exist

**User Experience Flow**:
1. User deletes project via trash icon
2. Confirmation dialog: "Delete project 'X'?"
3. Success modal displays: "Project deleted. Will be purged in 10 days. To recover: Settings → Database → Deleted Projects"
4. Project immediately disappears from all views
5. User can recover from Settings → Database within 10-day window
6. After 10 days, project automatically purged on next startup

**Key Features**:
- **Safety Net**: 10-day recovery window prevents accidental data loss
- **Clean UX**: Deleted projects immediately hidden from normal views
- **Easy Recovery**: Accessible via Settings → Database tab
- **Auto Cleanup**: Startup-based purge requires zero infrastructure
- **Tenant Isolation**: Complete multi-tenant security maintained

**Edge Cases Handled**:
- Product deleted with soft-deleted projects: Cascade purge all deleted projects
- Restore when another project active: Restores as inactive (safe default)
- Concurrent restore attempts: Idempotent operation (safe to retry)
- Double delete attempt: Returns 400 error with clear message

**Business Impact**:
- Improved user confidence (accidental deletes recoverable)
- Clear data lifecycle management
- Reduced support burden (self-service recovery)
- Maintains clean database (auto-purge after 10 days)
- Foundation for similar soft delete patterns (products, agents)

#### Project State Management (Handover 0071)

**Implementation Date**: October 28, 2025
**Status**: Production-ready simplified state machine with enhanced validation

**State Machine**: 5 states (simplified from 6)
- **active**: Currently being worked on (ONE per product)
- **inactive**: Paused, can be reactivated
- **completed**: Finished successfully
- **cancelled**: Abandoned
- **deleted**: Soft deleted (10-day recovery)

**State Reduction**:
- **Before**: 6 states (active, paused, archived, completed, cancelled, deleted)
- **After**: 5 states (active, inactive, completed, cancelled, deleted)
- **Eliminated**: "paused" (replaced with "inactive"), "archived" (redundant)
- **Benefit**: 17% reduction in complexity, clearer semantics

**Key Features**:
- Single active project per product (database + application enforcement)
- Deactivate endpoint frees active slot
- Product-scoped View Deleted (shows only active product's deleted projects)
- Data preservation on deactivate/complete/cancel
- WebSocket events for real-time updates

**Enforcement**:
- Database constraint: `idx_project_single_active_per_product` (inherited from 0050b)
- Application validation: Clear error messages with resolution hints
- Race condition protection: Atomic constraint check

**State Transitions**:
```
ACTIVE → inactive (deactivate) | completed | cancelled | deleted
INACTIVE → active (activate, validates single active)
COMPLETED → active (reopen, validates single active) | deleted
CANCELLED → active (reopen, validates single active) | deleted
DELETED → inactive (restore, within 10 days)
```

**API Endpoints**:
- POST /projects/{id}/deactivate - Deactivate active project
- PATCH /projects/{id} - Enhanced with single active validation
- GET /projects/deleted - Product-scoped filtering (active product only)
- POST /projects/{id}/restore - Restore deleted project to inactive

**Database Schema** (inherited from 0050b):
```sql
-- Single active project per product (enforced)
CREATE UNIQUE INDEX idx_project_single_active_per_product
ON projects (product_id)
WHERE status = 'active';

-- Soft delete support (from 0070)
ALTER TABLE projects ADD COLUMN deleted_at TIMESTAMP NULL;
```

**Product-Scoped Deleted View**:
- GET /projects/deleted filters by active product
- If active product exists: Returns that product's deleted projects
- If no active product: Returns empty array []
- Reduces clutter in recovery UI

**Enhanced Validation**:
When activating a project (PATCH status to "active"), validates:
1. No other project is active for this product
2. Returns error with conflicting project name: "Another project ('X') is already active"
3. User must deactivate conflicting project first

**WebSocket Events**:
- `project:deactivated` - Broadcast when project deactivated
- `project:updated` - Broadcast on status change
- `project:restored` - Broadcast when deleted project restored

**Terminology Improvements**:
- **Before**: "Pause" (ambiguous - is it active or not?)
- **After**: "Deactivate" (clear - project becomes inactive)
- **Benefit**: Clearer user intent, better API semantics

**Migration** (from previous versions):
- Projects with `status = 'paused'` migrated to `status = 'inactive'`
- Projects with `status = 'archived'` migrated to `status = 'inactive'`
- Idempotent migration (safe to re-run)
- Zero data loss

**Business Impact**:
- Simplified mental model (5 states vs 6 states)
- Clear terminology (deactivate vs pause)
- Better product scoping (less clutter in deleted view)
- Enhanced validation (prevents invalid active states)
- Foundation for future state machine features

**Documentation**:
- [User Guide](../features/project_state_management.md) - Complete user documentation
- [API Reference](../api/projects_endpoints.md) - Full API documentation with examples

#### Agent Job Management Tables (Handover 0019)

**AgentJob / AgentExecution Tables** - Agent job and execution tracking:

> **Note (Handover 0366a - Dec 2025)**
>
> The former `MCPAgentJob` model was split into two models as of v3.3.0:
> - `AgentJob` (work order) - the task definition, persists across succession
> - `AgentExecution` (executor instance) - the running agent, changes on succession
>
> The `mcp_agent_jobs` table name is retained for backward compatibility.
```sql
CREATE TABLE mcp_agent_jobs (
    id VARCHAR(36) PRIMARY KEY,
    tenant_key VARCHAR(36) NOT NULL,
    agent_type VARCHAR(50) NOT NULL,
    mission TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, active, completed, failed
    spawned_by VARCHAR(36),  -- Parent job ID for hierarchies
    messages JSONB DEFAULT '[]'::jsonb,  -- Agent-to-agent messages
    context_chunks JSONB DEFAULT '[]'::jsonb,
    result JSONB,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,

    -- Indexes for performance
    INDEX idx_agent_jobs_tenant_status (tenant_key, status),
    INDEX idx_agent_jobs_spawned_by (spawned_by),
    INDEX idx_agent_jobs_created (created_at DESC),

    -- Foreign key for parent-child relationships
    FOREIGN KEY (spawned_by) REFERENCES mcp_agent_jobs(id) ON DELETE SET NULL
);
```

**Key Features**:
- JSONB message storage for agent communication
- Parent-child job hierarchies via `spawned_by`
- Status state machine enforcement
- Multi-tenant isolation via `tenant_key`

#### User Authentication Enhancements (Handover 0023)

**User Table Additions** - Password reset and recovery PIN:
```sql
ALTER TABLE users ADD COLUMN recovery_pin_hash VARCHAR(255);
ALTER TABLE users ADD COLUMN failed_pin_attempts INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN pin_lockout_until TIMESTAMP WITH TIME ZONE;
ALTER TABLE users ADD COLUMN must_change_password BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN must_set_pin BOOLEAN DEFAULT FALSE;
```

**Security Features**:
- bcrypt-hashed recovery PINs
- Rate limiting via `failed_pin_attempts` and `pin_lockout_until`
- First-login enforcement via `must_change_password` and `must_set_pin`

#### Fresh Install Detection Architecture (Handover 0034)

**Fresh Install Detection Method**: User count = 0 (not config flags)

**SetupState Tracking**:
```sql
-- SetupState model tracks per-tenant setup status
-- Fresh install detection via user count query, not flags
SELECT COUNT(*) FROM users WHERE tenant_key = 'default';

-- SetupState stores setup completion status
CREATE TABLE setup_state (
    tenant_key VARCHAR(36) PRIMARY KEY,
    database_initialized BOOLEAN DEFAULT FALSE,
    setup_completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Fresh Install Flow**:
1. Router checks user count via `/api/auth/user-count`
2. If count = 0 → Redirect to `/welcome`
3. User proceeds to `/first-login`
4. Backend validates count = 0 before allowing admin creation
5. After first user created → Router allows dashboard access

**Security Benefits**:
- No config-based detection (eliminates race conditions)
- Two-layer validation (frontend router + backend endpoint)
- Automatic endpoint disablement (user count > 0)
- No default credentials (admin/admin eliminated)

#### MCP Session Management (MCP-over-HTTP)

**MCP Sessions Table** - Session tracking for HTTP transport:
```sql
CREATE TABLE mcp_sessions (
    id VARCHAR(36) PRIMARY KEY,
    tenant_key VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    session_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_accessed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,

    INDEX idx_mcp_sessions_tenant (tenant_key),
    INDEX idx_mcp_sessions_expires (expires_at),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

**Features**:
- 24-hour default session lifetime
- Auto-cleanup of expired sessions (48 hours)
- JSONB storage for client info and tool call history

#### Agent Template Database Integration (Handover 0041)

**Agent Templates Table** - Database-backed template management:
```sql
CREATE TABLE agent_templates (
    id VARCHAR(36) PRIMARY KEY,
    tenant_key VARCHAR(255) NOT NULL,
    product_id VARCHAR(36),
    name VARCHAR(255) NOT NULL,
    category VARCHAR(50) NOT NULL,  -- 'role', 'skill', 'domain'
    role VARCHAR(100),  -- 'orchestrator', 'implementer', etc.
    system_instructions TEXT NOT NULL,
    user_instructions TEXT,
    variables JSON DEFAULT '[]',
    behavioral_rules JSON DEFAULT '[]',
    success_criteria JSON DEFAULT '[]',
    preferred_tool VARCHAR(50) DEFAULT 'claude',
    version VARCHAR(20) DEFAULT '1.0.0',
    is_active BOOLEAN DEFAULT TRUE,
    is_default BOOLEAN DEFAULT FALSE,
    tags JSON DEFAULT '[]',
    usage_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMP WITH TIME ZONE,
    avg_generation_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,

    -- Performance indexes
    INDEX idx_agent_templates_tenant_role (tenant_key, role, is_active),
    INDEX idx_agent_templates_tenant_active (tenant_key, is_active),
    INDEX idx_agent_templates_product (product_id, role, is_active) WHERE product_id IS NOT NULL,

    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);
```

**Template History Table** - Version tracking and audit trail:
```sql
CREATE TABLE agent_template_history (
    id VARCHAR(36) PRIMARY KEY,
    template_id VARCHAR(36) NOT NULL,
    tenant_key VARCHAR(255) NOT NULL,
    system_instructions TEXT,
    user_instructions TEXT,
    version VARCHAR(20) NOT NULL,
    archived_reason VARCHAR(50),  -- 'edit', 'reset', 'delete'
    archived_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    INDEX idx_template_history_template (template_id, archived_at DESC),
    FOREIGN KEY (template_id) REFERENCES agent_templates(id) ON DELETE CASCADE
);
```

**Key Features**:
- **Three-Layer Caching**: Memory LRU (100 templates, <1ms) → Redis (1-hour TTL, <2ms) → Database (<10ms)
- **Cascade Resolution**: Product-specific → Tenant-specific → System default → Legacy fallback
- **Template Seeding**: 6 default templates per tenant (orchestrator, analyzer, implementer, tester, reviewer, documenter)
- **Cache Effectiveness**: 95%+ hit rate after warm-up, 10x speedup over database queries
- **Multi-Tenant Isolation**: All queries filtered by tenant_key, cache keys include tenant namespace
- **Version History**: Full audit trail with rollback capability

**Performance Characteristics**:
- Memory cache hit: <1ms (p95) ✅
- Database query: <10ms (p95) ✅
- Template seeding: <2s for 6 templates ✅
- Cache invalidation: <1ms all layers ✅

---

## Context Management Architecture (v2.0)

### Overview
GiljoAI's context management system uses a 2-dimensional model to give users fine-grained control over what context orchestrators receive and how detailed that context should be.

### Architecture Diagram
```
┌─────────────────────────────────────────────────┐
│           User Configuration (My Settings)       │
├─────────────────────────────────────────────────┤
│  Toggle Config (WHAT)    │  Depth Config (HOW)  │
│  - Field-level on/off    │  - Token management  │
│  - Per-category toggles  │  - 8 depth controls  │
└────────────┬────────────────────────┬────────────┘
             │                        │
             ▼                        ▼
┌─────────────────────────────────────────────────┐
│         Thin Client Prompt Generator             │
│   (Generates ~600 token prompts with MCP calls)  │
└────────────┬────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────┐
│            9 MCP Context Tools                   │
│  (On-demand fetching, multi-tenant isolated)     │
├─────────────────────────────────────────────────┤
│  Product Context │ Vision Docs │ Tech Stack     │
│  Architecture    │ Testing     │ 360 Memory     │
│  Git History     │ Templates   │ Project        │
└────────────┬────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────┐
│         Database (PostgreSQL + JSONB)            │
│  Product.config_data │ Product.product_memory   │
│  VisionDocument      │ MCPContextIndex          │
└─────────────────────────────────────────────────┘
```

### Data Flow
1. User configures toggles (on/off) and depth (per source) in My Settings
2. Orchestrator spawned with thin prompt (~600 tokens)
3. Orchestrator calls MCP tools based on toggle/depth config
4. Tools fetch data from database (filtered by tenant_key)
5. Tools return structured data within Claude Code's ingest limit (24K max per call)
6. Orchestrator receives context and proceeds with mission

### Key Features
- **Pagination Support**: Vision and 360 memory paginated for large content
- **Multi-Tenant Isolation**: All tools filter by tenant_key
- **Backward Compatible**: Legacy context paths maintained
- **Performance**: <100ms average response time per tool

---

## Orchestrator Staging & Agent Spawning Architecture (v3.2)

### Overview

**Implementation Date**: 2025-11-24 (Handovers 0246a, 0246b)
**Status**: Production-ready orchestrator staging and agent execution workflows

GiljoAI v3.2 introduces a comprehensive **7-task staging workflow** that prepares projects for multi-agent execution. This workflow validates environment readiness, discovers available agents dynamically, and establishes execution context before spawning agent jobs.

### Staging Workflow (7 Tasks)

The orchestrator executes this sequence before beginning agent coordination:

```
Project Launch Request
        │
        ▼
┌─────────────────────────────────────────────┐
│  TASK 1: Identity & Context Verification    │
│  - Verify project ID, name, scope           │
│  - Confirm tenant isolation                 │
│  - Validate orchestrator connection         │
│  - Include Product ID for context tracking  │
└────────────┬────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────┐
│  TASK 2: MCP Health Check                   │
│  - Verify MCP server responsive             │
│  - Check all required tools available       │
│  - Validate authentication tokens           │
│  - Test connection stability                │
└────────────┬────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────┐
│  TASK 3: Environment Understanding          │
│  - Read CLAUDE.md configuration             │
│  - Understand tech stack                    │
│  - Parse project structure                  │
│  - Identify critical paths                  │
│  - Load context management settings         │
└────────────┬────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────┐
│  TASK 4: Agent Discovery & Version Check    │
│  - Call get_available_agents() MCP tool     │
│  - Discover all available agents            │
│  - Check version compatibility              │
│  - Validate agent capabilities              │
│  - NO EMBEDDED TEMPLATES (dynamic only)     │
└────────────┬────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────┐
│  TASK 5: Context Configuration & Mission     │
│  - Apply user's context toggle settings     │
│  - Fetch product context via tools          │
│  - Fetch relevant vision documents          │
│  - Fetch git history for context            │
│  - Generate unified orchestrator mission    │
│  - Condense into <10K tokens                │
└────────────┬────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────┐
│  TASK 6: Agent Job Spawning                 │
│  - Create AgentJob records                   │
│  - Assign execution mode                    │
│  - Set initial status to 'waiting'          │
│  - Store staging result in database         │
└────────────┬────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────┐
│  TASK 7: Activation                         │
│  - Transition project to 'active' status    │
│  - Enable WebSocket event broadcasts        │
│  - Start monitoring orchestrator health     │
│  - Begin agent job polling                  │
└─────────────────────────────────────────────┘
        │
        ▼
   Orchestrator Ready for Execution
```

**Key Features**:
- **Dynamic Agent Discovery**: No embedded templates (fetched via MCP tools)
- **Version Compatibility**: Validates agent versions match project requirements
- **Context Configuration**: Applies user's configured toggle/depth settings
- **Environment Validation**: Comprehensive health checks before execution
- **Graceful Failure**: Clear error messages at each stage

**Code Reference**: `src/giljo_mcp/prompts/thin_prompt_generator.py::_build_staging_prompt()`

### Agent Execution Modes

GiljoAI supports two distinct execution modes for agents:

#### Mode 1: Claude Code CLI (Single Terminal)

**Characteristics**:
- Orchestrator spawns sub-agents via Task tool
- All agents run in single Claude Code CLI session
- Mission-specific prompts generated per agent
- Real-time coordination via message queue
- Optimized for local development workflows

**Workflow**:
```
Orchestrator (Claude Code)
    │
    ├─→ Task("implementer", mission=<condensed>)
    │   └─→ Sub-agent executes in same terminal
    │
    ├─→ Task("tester", mission=<condensed>)
    │   └─→ Sub-agent executes in same terminal
    │
    └─→ Task("reviewer", mission=<condensed>)
        └─→ Sub-agent executes in same terminal
```

#### Mode 2: Manual Multi-Terminal (Generic Template)

**Characteristics**:
- Each agent runs in separate terminal/session
- Generic unified template for all agent types
- Mission fetched from database at runtime
- Orchestrator coordinates via AgentJob records
- Optimized for distributed execution

**Workflow**:
```
Terminal 1 (Orchestrator)
    │
    ├─→ spawn_agent_job(type="implementer", status="waiting")
    │   └─→ Database: AgentJob record created
    │
    └─→ Monitors job statuses via WebSocket

Terminal 2 (Implementer Agent)
    │
    ├─→ Load generic_agent_template
    ├─→ Call get_agent_mission(job_id, tenant_key)
    ├─→ Execute fetched mission
    └─→ Report completion to database

Terminal 3 (Tester Agent)
    │
    ├─→ Load generic_agent_template
    ├─→ Call get_agent_mission(job_id, tenant_key)
    ├─→ Execute fetched mission
    └─→ Report completion to database
```

### Generic Agent Template Protocol

**Purpose**: Unified protocol for all agents in multi-terminal mode

**Variable Injection** (by Orchestrator):
```
{agent_id}      = UUID of this agent instance
{job_id}        = UUID of this job in MCP_AGENT_JOBS table
{product_id}    = UUID of the product/project context
{project_id}    = UUID of the specific project
{tenant_key}    = Tenant isolation key
```

**Mission Fetching** (by Agent at Runtime):
```
- Full mission text (AgentJob.mission)
- Project context and requirements
- Product information and constraints
- Previous agent outputs (message history)
- Current status of any ongoing work
```

**Six-Phase Execution Protocol**:

1. **Initialization**
   - Verify identity (agent_id, job_id)
   - Check MCP health
   - Load CLAUDE.md

2. **Mission Fetch**
   - Call: `get_agent_mission(job_id, tenant_key)`
   - Receive: Full mission + context
   - Validate: Mission is non-empty

3. **Work Execution**
   - Read mission requirements
   - Perform assigned work
   - Track time and progress
   - Collect outputs

4. **Progress Reporting**
   - Call: `update_job_progress(job_id, percent, status_message)`
   - Report: At 25%, 50%, 75%, 100%
   - Include: Detailed status info

5. **Communication**
   - Send: `send_message(to_agent_id, content)`
   - Receive: `receive_messages(agent_id)`
   - Acknowledge: `acknowledge_message(message_id)`

6. **Completion**
   - Call: `complete_job(job_id, result_summary)`
   - Include: Deliverables, test results, documentation
   - Notify: Orchestrator of completion

**Code Reference**:
- Template: `src/giljo_mcp/templates/generic_agent_template.py`
- MCP Tool: `src/giljo_mcp/tools/orchestration.py::get_generic_agent_template()`

### Dynamic Agent Discovery

**No Embedded Templates**: GiljoAI v3.2 eliminates hardcoded agent templates from prompts.

**Discovery Mechanism**:
```python
# Orchestrator calls during staging
result = get_available_agents()

# Returns:
{
  "agents": [
    {
      "name": "implementer",
      "version": "1.0.3",
      "type": "role",
      "required_context": ["tech_stack", "architecture"],
      "capabilities": ["code_generation", "refactoring"]
    },
    {
      "name": "tester",
      "version": "1.0.2",
      "type": "role",
      "required_context": ["tech_stack", "testing_config"],
      "capabilities": ["unit_testing", "integration_testing"]
    }
  ]
}
```

**Version Compatibility Validation**:
- Checks agent version >= minimum_required_version
- Validates capabilities include required_capabilities
- Verifies agent status == 'initialized'
- Reports conflicts (e.g., incompatible versions)

**Code Reference**: `src/giljo_mcp/tools/orchestration.py::get_available_agents()`

### Execution Flow Diagram

```
User Clicks "Launch Project"
        │
        ▼
┌──────────────────────────────────────┐
│  Frontend: POST /projects/{id}/launch │
└────────────┬─────────────────────────┘
             │
             ▼
┌──────────────────────────────────────┐
│  Backend: ProjectService.launch()    │
│  - Validates project status           │
│  - Creates orchestrator job           │
│  - Generates staging prompt           │
└────────────┬─────────────────────────┘
             │
             ▼
┌──────────────────────────────────────┐
│  Orchestrator: Execute Staging (7)   │
│  1. Identity verification             │
│  2. MCP health check                  │
│  3. Environment understanding         │
│  4. Agent discovery                   │
│  5. Context prioritization            │
│  6. Job spawning                      │
│  7. Activation                        │
└────────────┬─────────────────────────┘
             │
             ▼
    ┌────────────────┐
    │ Execution Mode? │
    └───┬────────┬───┘
        │        │
  ┌─────┘        └──────┐
  │                     │
  ▼                     ▼
┌──────────────┐  ┌──────────────────┐
│ Claude Code  │  │ Multi-Terminal   │
│ CLI Mode     │  │ Generic Mode     │
│              │  │                  │
│ Task tool    │  │ Generic template │
│ spawns       │  │ with variable    │
│ sub-agents   │  │ injection        │
└──────────────┘  └──────────────────┘
```

### MCP Tools for Staging & Execution

**Staging Tools** (Phase 1 - Orchestrator Preparation):
1. `get_available_agents(tenant_key, active_only)` - **Dynamic agent discovery** (Handover 0246c)
   - Returns: Agent metadata (name, version, type, capabilities)
   - Multi-tenant isolation enforced
2. `health_check()` - Validates MCP server connectivity
3. `fetch_product_context()` - Retrieves product metadata
4. `fetch_vision_document()` - Fetches vision docs (paginated)
5. `fetch_git_history()` - Retrieves commit history
6. `fetch_360_memory()` - Fetches project closeout summaries

**Agent Execution Tools** (Phases 3-4 - Agent Spawning & Execution):
1. `get_generic_agent_template(agent_id, job_id, ...)` - Renders unified template (Handover 0246b)
   - 6-phase execution protocol included
   - Variable injection: {agent_id}, {job_id}, {product_id}, {project_id}, {tenant_key}
2. `get_agent_mission(job_id, tenant_key)` - Fetches mission from database
3. `update_job_progress(job_id, percent, status)` - Reports progress
4. `send_message(to_agent_id, message)` - Agent-to-agent communication
5. `receive_messages(agent_id)` - Retrieves incoming messages
6. `acknowledge_message(message_id)` - Acknowledges receipt
7. `complete_job(job_id, result)` - Marks job complete
8. `report_error(job_id, error)` - Reports errors for orchestrator review

**MCP Tool Architecture Principles**:
- **Thin Client Approach**: Server provides data via HTTP endpoints, client executes code
- **Dynamic Fetching**: Context loaded on-demand via MCP tools (not embedded in prompts)
- **Multi-Tenant Isolation**: All tools filter by tenant_key (zero cross-tenant leakage)
- **Client-Server Separation**: Server = tool provider (HTTP), Client = executor (local filesystem)
- **On-Demand Fetching**: Templates and missions fetched only when needed

**Code References**:
- Orchestration Tools: `src/giljo_mcp/tools/orchestration.py`
- Agent Discovery: `src/giljo_mcp/tools/agent_discovery.py` (167 lines, Handover 0246c)
- Generic Template: `src/giljo_mcp/templates/generic_agent_template.py` (Handover 0246b)
- Thin Prompt Generator: `src/giljo_mcp/prompts/thin_prompt_generator.py::_build_staging_prompt()` (Handover 0246a)

### Database Schema Extensions

**AgentJob Table** (updated for staging):
```sql
ALTER TABLE mcp_agent_jobs ADD COLUMN execution_mode VARCHAR(50);
ALTER TABLE mcp_agent_jobs ADD COLUMN staging_result JSONB;
ALTER TABLE mcp_agent_jobs ADD COLUMN agent_version VARCHAR(20);
```

**Execution Modes**:
- `claude_code_cli` - Single terminal with Task tool
- `multi_terminal_generic` - Multiple terminals with generic template

**Staging Result** (JSONB):
```json
{
  "staging_tasks_completed": [
    "identity_verification",
    "mcp_health_check",
    "environment_understanding",
    "agent_discovery",
    "context_prioritization",
    "job_spawning",
    "activation"
  ],
  "agents_discovered": [
    {"name": "implementer", "version": "1.0.3", "compatible": true},
    {"name": "tester", "version": "1.0.2", "compatible": true}
  ],
  "staging_duration_ms": 2341
}
```

**Code Reference**: `src/giljo_mcp/models.py::AgentJob`

**Related Documentation**:
- Orchestrator workflow details: [ORCHESTRATOR.md](ORCHESTRATOR.md#complete-orchestrator-workflow-pipeline-v32)
- 7-task staging workflow: [components/STAGING_WORKFLOW.md](components/STAGING_WORKFLOW.md)
- Dynamic agent discovery: [ORCHESTRATOR.md](ORCHESTRATOR.md#dynamic-agent-discovery)
- Generic agent template: [ORCHESTRATOR.md](ORCHESTRATOR.md#generic-agent-template-protocol-v32)

---

## Component Architecture

### API Server Structure

**Application Layout**:
```
api/
├── app.py                  # FastAPI application factory
├── middleware/             # Custom middleware stack
│   ├── auth.py            # JWT authentication middleware
│   ├── rate_limit.py      # Rate limiting middleware
│   ├── security.py        # Security headers middleware
│   └── setup.py           # Setup mode middleware
├── endpoints/             # API endpoint modules
│   ├── auth.py           # Authentication endpoints
│   ├── auth_pin_recovery.py # ✨ Password reset via PIN (347 lines, Handover 0023)
│   ├── projects.py       # Project management
│   ├── agents.py         # Agent orchestration
│   ├── agent_jobs.py     # ✨ Agent job management (824 lines, 13 endpoints, Handover 0019)
│   ├── orchestrator.py   # ✨ Orchestration endpoints (7 endpoints, Handover 0020)
│   ├── messages.py       # Inter-agent messaging
│   ├── users.py          # ✨ User management + password reset
│   ├── setup.py          # Setup wizard endpoints
│   ├── ai_tools.py       # AI tool configuration generator (425 lines)
│   ├── templates.py      # Template CRUD operations
│   ├── mcp_http.py       # MCP-over-HTTP endpoint (398 lines)
│   └── mcp_session.py    # MCP session management (186 lines)
└── websocket/            # WebSocket handlers
    ├── manager.py        # WebSocket connection management
    └── auth.py           # WebSocket authentication
```

**Middleware Stack** (execution order):
```python
# From api/app.py:514-538
# Middleware executes in REVERSE order of addition

# 5th - Authentication (JWT validation)
app.add_middleware(AuthMiddleware)

# 4th - Rate limiting (60 requests/minute)  
app.add_middleware(RateLimitMiddleware, requests_per_minute=60)

# 3rd - Security headers (HSTS, CSP, etc.)
app.add_middleware(SecurityHeadersMiddleware)

# 2nd - Setup mode (database initialization check)
app.add_middleware(SetupModeMiddleware)

# 1st - CORS (handles OPTIONS preflight)
app.add_middleware(CORSMiddleware, allow_origins=cors_origins)
```

### Backend Service Layer

**Core Services**:
```
src/giljo_mcp/
├── orchestrator.py             # Multi-agent coordination engine (915 lines)
├── mission_planner.py          # ✨ Intelligent mission generation (630 lines, Handover 0020)
├── agent_selector.py           # ✨ Smart agent selection logic (287 lines, Handover 0020)
├── workflow_engine.py          # ✨ Multi-agent workflow coordination (500 lines, Handover 0020)
├── agent_job_manager.py        # ✨ Agent job lifecycle management (159 lines, Handover 0019)
├── agent_communication_queue.py # ✨ Agent-to-agent messaging (Handover 0019)
├── job_coordinator.py          # ✨ Parent-child job orchestration (604 lines, Handover 0019)
├── database.py                 # PostgreSQL connection management
├── tenant.py                   # Multi-tenant isolation manager
├── models.py                   # SQLAlchemy ORM models
├── template_manager.py         # Unified template system (342 lines)
├── optimization/               # Serena MCP optimization layer (v3.0, configuration-based)
├── auth/                       # Authentication services
│   ├── manager.py              # AuthManager class
│   ├── jwt_handler.py          # JWT token operations
│   └── password.py             # bcrypt password handling
├── tools/                      # MCP tool implementations (34+ tools)
│   ├── project.py              # Project management tools
│   ├── agent.py                # Agent orchestration tools
│   ├── message.py              # Message queue tools
│   ├── context.py              # Context management tools
│   ├── template.py             # Template CRUD operations
│   ├── optimization.py         # Optimization control tools (6 tools)
│   └── orchestration.py        # ✨ Orchestration tools (Handover 0020)
└── setup/                      # Setup wizard backend
    ├── state_manager.py        # Setup state tracking
    └── wizard.py               # Multi-step setup logic
```

**MCP Tools Architecture**:
- **34+ specialized tools** for agent coordination (22 original + 6 optimization + 6 orchestration)
- **Tool registration** via decorator pattern
- **Database session management** for each tool call
- **Tenant isolation** enforced at tool level
- **Optimization layer** intercepts Serena MCP tool calls (v3.0)
- **Agent job management** (Handover 0019): Job creation, messaging, lifecycle management
- **Orchestration tools** (Handover 0020): Mission generation, agent selection, workflow coordination

**Serena Optimization Layer** (v3.0):
- **Symbolic operation enforcement**: Encourages `find_symbol()` over naive `read_file()` for focused context
- **Mission-time optimization**: Rules injected automatically at agent spawn
- **Context-aware rule injection**: Dynamic rules based on project context (codebase size, language)

**Archive Status**: Moved to `handovers/completed/harmonized/HANDOVER_0010_SERENA_MCP_OPTIMIZATION_LAYER-C.md`

#### HANDOVER 0019 - Agent Job Management System (COMPLETE)

**Implementation Status**: ✅ **COMPLETE** - Production-ready multi-agent job coordination

**Core Implementation**:
- **`AgentJobManager`** (`src/giljo_mcp/agent_job_manager.py` - 159 lines) - Job lifecycle management
- **`AgentCommunicationQueue`** (`src/giljo_mcp/agent_communication_queue.py`) - Agent-to-agent messaging
- **`JobCoordinator`** (`src/giljo_mcp/job_coordinator.py` - 604 lines) - Parent-child job orchestration
- **Database Model**: `AgentJob` + `AgentExecution` for job lifecycle and execution tracking
- **13 REST API endpoints** for job management
- **4 WebSocket event handlers** for real-time updates

**Key Features Delivered**:
- **Job Lifecycle Management**: pending → active → completed/failed state machine
- **Agent-to-Agent Messaging**: JSONB-based message queue with acknowledgment tracking
- **Parent-Child Hierarchies**: Jobs can spawn child jobs for distributed work
- **Multi-Tenant Isolation**: 100% enforced across all queries and operations
- **WebSocket Real-Time Events**: job:created, job:acknowledged, job:completed, job:failed, job:message
- **Performance**: Sub-100ms for most operations (job creation <50ms, status update <20ms)

**API Endpoints** (13 Total):
- POST /api/agent-jobs - Create job
- GET /api/agent-jobs - List jobs (with filtering)
- GET /api/agent-jobs/{job_id} - Get job details
- PATCH /api/agent-jobs/{job_id} - Update job
- DELETE /api/agent-jobs/{job_id} - Delete job
- POST /api/agent-jobs/{job_id}/acknowledge - Acknowledge job (pending → active)
- POST /api/agent-jobs/{job_id}/complete - Complete job (active → completed)
- POST /api/agent-jobs/{job_id}/fail - Fail job (active/pending → failed)
- POST /api/agent-jobs/{job_id}/messages - Send message
- GET /api/agent-jobs/{job_id}/messages - Get messages
- POST /api/agent-jobs/{job_id}/messages/{message_id}/acknowledge - Acknowledge message
- POST /api/agent-jobs/{job_id}/spawn-children - Spawn child jobs
- GET /api/agent-jobs/{job_id}/hierarchy - Get job hierarchy

**Test Coverage**:
- **Core Components**: 80 tests passing, 89.15% coverage
- **Integration Tests**: 119+ total tests
- **Security**: Multi-tenant isolation verified 100%

**Archive Status**: Moved to `handovers/completed/0019_HANDOVER_20251014_AGENT_JOB_MANAGEMENT-C.md`

#### HANDOVER 0020 - Orchestrator Enhancement for Context-Focused Orchestration (COMPLETE)

**Implementation Status**: ✅ **COMPLETE** - Intelligent mission generation and agent coordination

**Core Implementation**:
- **`MissionPlanner`** (`src/giljo_mcp/mission_planner.py` - 630 lines) - Intelligent mission generation
- **`AgentSelector`** (`src/giljo_mcp/agent_selector.py` - 287 lines) - Smart agent type selection
- **`WorkflowEngine`** (`src/giljo_mcp/workflow_engine.py` - 500 lines) - Multi-agent workflow coordination
- **Enhanced `ProjectOrchestrator`** with 4 new coordination methods
- **7 REST API endpoints** for orchestration operations
- **3 MCP tools** for orchestration control

**Key Features Delivered**:
- **Context-Focused Architecture**: Orchestrator reads full context, agents receive condensed missions
- **Intelligent Mission Generation**: Context-aware mission creation per agent type
- **Smart Agent Selection**: Automated agent type selection based on work requirements
- **Workflow Coordination**: Sequential (waterfall) and parallel execution patterns
- **Failure Recovery**: Automatic retry and recovery strategies

**Orchestration API Endpoints** (7 Total):
- POST /api/orchestrator/process-vision - Start vision processing workflow
- POST /api/orchestrator/create-missions - Generate condensed missions
- POST /api/orchestrator/spawn-team - Spawn multi-agent team
- GET /api/orchestrator/workflow-status - Monitor workflow progress
- POST /api/orchestrator/coordinate - Start coordination
- POST /api/orchestrator/handle-failure - Failure recovery
- GET /api/orchestrator/metrics - Performance metrics

**Archive Status**: Moved to `handovers/completed/0020_HANDOVER_20251014_ORCHESTRATOR_ENHANCEMENT-C.md`

### Frontend Architecture

**Vue 3 Application Structure**:
```
frontend/
├── src/
│   ├── main.js            # Application entry point
│   ├── App.vue            # Root component (layout router)
│   ├── layouts/           # ✨ TWO-LAYOUT PATTERN (2025-10-16)
│   │   ├── AuthLayout.vue # Minimal layout for auth routes
│   │   └── DefaultLayout.vue # Full app layout with navigation
│   ├── router/            # Vue Router configuration
│   │   └── index.js       # Route definitions + auth guards
│   ├── stores/            # Pinia state management
│   │   ├── auth.js        # Authentication state
│   │   ├── products.js    # Product management state
│   │   ├── agents.js      # Agent monitoring state
│   │   └── websocket.js   # WebSocket connection state
│   ├── views/             # Page-level components
│   │   ├── Login.vue      # Authentication page
│   │   ├── ForgotPassword.vue # ✨ Password reset with recovery PIN (Handover 0023)
│   │   ├── Setup.vue      # Setup wizard (3 steps)
│   │   ├── Dashboard.vue  # Main dashboard
│   │   ├── Projects.vue   # Project management
│   │   ├── SystemSettings.vue # ✨ Admin Settings v3.0 (Handovers 0025-0027)
│   │   ├── UserSettings.vue # ✨ Enhanced with API keys + Serena toggle (Handover 0028)
│   │   └── Users.vue      # ✨ Standalone user management (Handover 0029)
│   ├── components/        # Reusable components
│   │   ├── AgentCard.vue  # Agent status display
│   │   ├── ProjectCard.vue# Project overview cards
│   │   ├── MessageQueue.vue# Real-time message display
│   │   ├── AIToolSetup.vue # AI tool configuration UI (243 lines)
│   │   ├── ApiKeyManager.vue # User API key management (266 lines, Handover 0028)
│   │   ├── ApiKeyWizard.vue  # API key generation modal
│   │   ├── UserManager.vue # ✨ Enhanced with email + created date (Handover 0028)
│   │   ├── DatabaseConnection.vue # ✨ Enhanced test + display (Handover 0026)
│   │   ├── FirstLoginSetup.vue # ✨ Password change + PIN setup (Handover 0023)
│   │   ├── ForgotPasswordPin.vue # ✨ PIN-based password reset (Handover 0023)
│   │   └── setup/         # Enhanced setup components
│   │       └── WelcomePasswordStep.vue # Two-phase auth welcome
│   └── utils/             # Utility modules
│       ├── api.js         # Axios HTTP client configuration
│       ├── auth.js        # JWT token management
│       └── websocket.js   # WebSocket client wrapper
├── public/                # Static assets
├── index.html             # HTML template
└── package.json           # NPM dependencies
```

> **Edition Note:** The two-layout auth pattern below is Community Edition's single-user authentication. SaaS Edition replaces this with OAuth/SSO providers and multi-org session management.

### Two-Layout Authentication Pattern (SaaS-Ready Architecture)

**Implementation Date**: 2025-10-16
**Devlog**: [docs/devlog/20251016_two_layout_auth_pattern_implementation.md](devlog/20251016_two_layout_auth_pattern_implementation.md)

GiljoAI MCP implements an industry-standard Two-Layout Pattern that separates authentication routes from application routes, providing:
- **Clean separation of concerns** between auth and app contexts
- **Scalable SaaS architecture** suitable for multi-tenant deployments
- **Consistent authentication flow** across localhost, LAN, and WAN
- **Professional user experience** with zero visual artifacts

**Architecture Overview**:
```
App.vue (58 lines - layout router)
├── AuthLayout.vue (Minimal)
│   ├── /welcome → WelcomeSetup.vue
│   └── /login → Login.vue
│   └── Features:
│       • No navigation components (AppBar, NavigationDrawer)
│       • No user data loading (happens in DefaultLayout)
│       • Just <router-view /> for auth pages
│       • Auth pages handle their own full-page layout
│
└── DefaultLayout.vue (Full Application)
    ├── /dashboard → Dashboard.vue
    ├── /projects → Projects.vue
    ├── /settings → Settings.vue
    └── Features:
        • AppBar with user menu
        • NavigationDrawer with app navigation
        • User data loading on mount (only for app routes)
        • Automatic user reload after login navigation
        • Passes currentUser to child components via <router-view>
```

**Router Metadata Configuration**:
```javascript
// Authentication routes use AuthLayout
{
  path: '/login',
  meta: { layout: 'auth', requiresAuth: false }
}

// Application routes use DefaultLayout
{
  path: '/dashboard',
  meta: { layout: 'default', requiresAuth: true }
}
```

**Layout Selection Logic**:
```javascript
// App.vue - Dynamic layout component
const layout = computed(() => {
  return route.meta.layout === 'auth' ? AuthLayout : DefaultLayout
})
```

**Benefits**:
- **90% code reduction** in App.vue (537 lines → 58 lines)
- **Zero setup mode complexity** - eliminated from frontend routing
- **User data loading** only when needed (app routes, not auth routes)
- **Future-ready** for tenant-specific layouts and white-labeling

**Code Reference**: `frontend/src/layouts/`, `frontend/src/App.vue`, `frontend/src/router/index.js`

### Admin Settings v3.0 Refactoring (Handovers 0025-0029)

**Implementation Date**: 2025-10-20
**Status**: ✅ **COMPLETE** - Production-ready modernization

GiljoAI MCP v3.0 includes a complete refactoring of Admin Settings with improved UX, accessibility, and organization.

#### SystemSettings.vue Structure (4 Tabs)

**1. Network Tab** (Handover 0025):
- v3.0 unified binding configuration (0.0.0.0 binding)
- Removed deployment MODE selection (local/LAN/remote)
- Removed localhost-specific messaging
- Clean, single-architecture presentation
- External IP selection during install

**2. Database Tab** (Handover 0026):
- Database connection information with copy buttons
- Database users section with role descriptions:
  - `giljo_owner`: Full database control (owner)
  - `giljo_user`: Application runtime access
- Enhanced test connection button with proper error handling
- Professional card-based layout
- 47 comprehensive tests

**3. Integrations Tab** (Handover 0027):
- **Agent Coding Tools Section**:
  - Claude Code CLI with MCP configuration modal
  - Codex CLI with TOML configuration support
  - Gemini CLI with multi-modal capabilities
  - Configuration download and copy-to-clipboard
- **Native Integrations Section**:
  - Serena MCP integration (deep semantic code analysis)
  - Future integrations placeholder
- WCAG 2.1 Level AA accessibility compliant
- Professional branding with logos

**4. Security Tab** (Unchanged):
- Cookie domain whitelist management

**Users Tab**: REMOVED - Relocated to standalone page (see Handover 0029)

#### UserSettings.vue Enhancements (Handover 0028)

**API and Integrations Tab** (Enhanced):
- Industry-standard API key masking (`gk_****...****`)
- Single API key type (simplified UX)
- Serena integration toggle
- AI tool configuration instructions:
  - Claude Code CLI setup guide
  - Codex CLI setup guide
  - Gemini CLI setup guide
- Enhanced UserManager component:
  - Email field (searchable, sortable)
  - Created date field (formatted display)
- 193+ comprehensive TDD tests

#### Standalone Users Page (Handover 0029)

**New Route**: `/admin/users`
**Access**: Avatar dropdown → Users (admin only)

**Features**:
- Complete user management interface
- Separated from Admin Settings for cleaner UX
- Role-based access control (admin only)
- Enhanced user table with email and created date
- 81 comprehensive TDD tests

**Navigation Changes**:
- Removed "My API Keys" from avatar dropdown (duplicate)
- Added "Users" menu item for admins
- Clean separation: Admin Settings vs User Management

### Password Reset Functionality (Handover 0023)

**Implementation Date**: 2025-10-21
**Status**: ✅ **COMPLETE** - Production-ready self-service password recovery

**Recovery PIN System**:
- 4-digit recovery PIN for self-service password reset
- bcrypt hashing with timing-safe comparison
- Rate limiting: 5 failed attempts trigger 15-minute lockout
- Audit logging for all PIN verification attempts

**Frontend Components**:
- `ForgotPassword.vue` - Initial password reset request
- `ForgotPasswordPin.vue` - PIN verification and password reset
- `FirstLoginSetup.vue` - New user password change + PIN setup
- WCAG 2.1 AA accessibility compliant

**Backend Endpoints** (3 New):
- POST /api/auth/verify-pin-and-reset-password - PIN verification + password reset
- POST /api/auth/check-first-login - Check if user needs password change/PIN setup
- POST /api/auth/complete-first-login - Complete first-login workflow

**Database Schema Additions**:
- `recovery_pin_hash` - bcrypt hash of 4-digit PIN
- `failed_pin_attempts` - Track failed PIN verification attempts
- `pin_lockout_until` - Lockout expiration timestamp
- `must_change_password` - Force password change flag
- `must_set_pin` - Force PIN setup flag

**Security Features**:
- Generic error messages (no user enumeration)
- bcrypt timing-safe comparison
- Rate limiting with lockout tracking
- Audit logging
- Admin password reset capability

**Test Coverage**: 6/6 integration tests passing, comprehensive frontend validation

**Real-time Updates**:
```javascript
// WebSocket integration for live updates
// From frontend/src/stores/websocket.js
export const useWebSocketStore = defineStore('websocket', () => {
  const connect = async () => {
    const token = localStorage.getItem('auth_token')
    const ws = new WebSocket(`ws://localhost:7272/ws/client-id?token=${token}`)
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      // Update Pinia stores based on message type
      if (data.type === 'agent_status_update') {
        agentStore.updateAgentStatus(data.agent_id, data.status)
      }
    }
  }
})
```

---

## MCP-over-HTTP Architecture

GiljoAI MCP implements the Model Context Protocol over HTTP transport, enabling zero-dependency integration with Claude Code and other MCP clients.

### Endpoint Design

**HTTP Endpoint:**
```
POST http://server:7272/mcp
Content-Type: application/json
X-API-Key: gk_YOUR_API_KEY_HERE
```

**Protocol:** JSON-RPC 2.0 (https://www.jsonrpc.org/specification)

**Code Reference:** `api/endpoints/mcp_http.py` (398 lines)

### Supported MCP Methods

**1. initialize** - Connection handshake
- Negotiates protocol version (2024-11-05)
- Exchanges server and client capabilities
- Initializes session state

**2. tools/list** - List available MCP tools
- Returns 22+ orchestration tools
- Includes tool schemas and descriptions
- Filtered by tenant context

**3. tools/call** - Execute MCP tool
- Routes to existing tool_accessor methods
- Preserves multi-tenant isolation
- Returns JSON-RPC 2.0 formatted results

### Session Management

**PostgreSQL-backed Sessions:**
- Table: `mcp_sessions` (see `src/giljo_mcp/models.py` lines 1295-1357)
- Default lifetime: 24 hours from last access
- Auto-cleanup: Expired sessions deleted after 48 hours
- Session data: client info, protocol version, tool call history

**Session Authentication Flow:**
```
X-API-Key header
  → API key validation (bcrypt hash comparison)
  → User lookup (api_key.user_id)
  → Tenant resolution (user.tenant_key)
  → Session creation/retrieval
  → Tool execution with tenant context
```

**Code Reference:** `api/endpoints/mcp_session.py` (186 lines)

### Security Model

**Public Endpoint with Custom Auth:**
- `/mcp` added to public endpoints list (bypasses standard JWT middleware)
- Endpoint handles own authentication via X-API-Key header
- Multi-tenant isolation enforced via tenant_key filtering
- Session expiration provides defense in depth

**Code Reference:**
- `api/middleware.py` line 111 - Public endpoint definition
- `api/endpoints/mcp_http.py` lines 329-354 - API key validation

### Integration Example

**Connecting Claude Code:**
```bash
# Generate API key from dashboard: Avatar → My Settings → API & Integrations

# Add MCP server to Claude Code
claude mcp add --transport http giljo-mcp http://10.1.0.164:7272/mcp \
  --header "X-API-Key: gk_YOUR_API_KEY_HERE"

# Verify connection
> /mcp
# Should show "giljo-mcp" as Connected

# Use tools
> "List all my projects"
> "Create a new project called 'Website Redesign'"
```

**Complete Documentation:** [MCP-over-HTTP Integration](MCP_OVER_HTTP_INTEGRATION.md)

---

## Client-Server Execution Model

### What Runs Where

**SERVER (F:\GiljoAI_MCP)**:
- **Database Storage**: PostgreSQL (agent templates, missions, projects, products, vision documents)
- **MCP HTTP Endpoint Provider**: FastAPI server at `POST /mcp` (port 7272)
- **Tool Implementations**: orchestration.py, agent_discovery.py, context_tools.py, etc.
- **WebSocket Server**: Real-time UI updates for dashboard
- **Vue Dashboard**: Frontend UI for product/project management
- **DOES NOT**: Execute orchestrators, execute agents, store project files

**CLIENT PC (Remote Developer Machine)**:
- **Claude Code Terminal**: Orchestrator execution environment
- **Separate Terminals**: Agent execution (multi-terminal mode)
- **Project Files**: Local filesystem at `/path/to/my-project/`
- **MCP HTTP Client**: Calls server endpoints via HTTP POST
- **DOES NOT**: Store missions, agent templates, product data

### Communication Flow

```
CLIENT PC                          SERVER (F:\GiljoAI_MCP)
─────────────────────────────────  ────────────────────────────────────

1. Orchestrator starts in
   Claude Code terminal

2. Calls get_orchestrator_     ──→  3. Receives HTTP POST /mcp
   instructions()                      {method: "tools/call",
   (HTTP POST)                          name: "get_orchestrator_instructions"}

                                    4. Fetches from PostgreSQL:
                                       - Project data
                                       - Product context
                                       - Vision documents
                                       - Git history
                                       - 360 memory

5. Receives mission data       ←──  6. Returns mission (~10K tokens)
   (~10K tokens)                       via JSON-RPC response

7. Orchestrator executes
   7-task staging workflow
   on CLIENT PC

8. Calls get_available_agents() ──→ 9. Queries agent_templates table

10. Receives agent list        ←── 11. Returns agents with versions

12. Spawns agent jobs              12. Creates AgentJob records
    (database records only)    ──→     in PostgreSQL

13. Agent 1 starts in
    separate terminal

14. Calls get_agent_mission()  ──→ 15. Fetches agent-specific mission

16. Agent executes on          ←── 17. Returns mission + context
    CLIENT PC with project
    files from local filesystem
```

### Key Implications

1. **Project Files Location**: Client PC local filesystem (NOT server)
   - Orchestrator: `/path/to/my-project/src/`
   - Agent: `/path/to/my-project/tests/`
   - Server has zero access to project files

2. **Code Execution**: All orchestrator/agent code runs on CLIENT PC
   - Server only provides data via HTTP endpoints
   - No code execution on server side (only database queries)
   - Orchestrator and agents read/write files on client filesystem

3. **Multi-Tenant Isolation**: Enforced at database level
   - All MCP tools filter by `tenant_key`
   - Client authenticates via X-API-Key header
   - Session tied to tenant context
   - No cross-tenant data leakage possible

4. **Network Requirements**:
   - Client needs HTTP access to server (port 7272)
   - WebSocket connection optional (for real-time dashboard updates)
   - No VPN required (uses standard HTTP/HTTPS)
   - Can work across internet with proper firewall configuration

### Architecture Correctness Verification (Handover 0246c)

The implementation correctly follows the distributed client-server architecture:

**Server Responsibilities (F:\GiljoAI_MCP)**:
- ✅ Database storage (agent templates, missions, prompts, messages)
- ✅ MCP tool HTTP endpoints provider (POST /mcp at port 7272)
- ✅ Web UI and WebSocket server for dashboard
- ✅ Multi-tenant data isolation enforcement
- ❌ Does NOT execute orchestrators or agents
- ❌ Does NOT have access to client project files

**Client Responsibilities (Remote Developer Machine)**:
- ✅ Orchestrator execution in Claude Code terminal
- ✅ Agent execution in separate terminals (multi-terminal mode)
- ✅ Project file access on local filesystem
- ✅ MCP tool calls via HTTP POST to server
- ❌ Does NOT store missions, agent templates, or product data

**Communication Flow Verification**:
```
1. User clicks "Stage Project" in browser (client PC)
   ↓
2. Browser calls SERVER API → generates staging prompt
   ↓
3. CLIENT orchestrator (Claude Code) calls get_orchestrator_instructions() MCP tool
   ↓
4. SERVER returns prompt via HTTP JSON-RPC
   ↓
5. CLIENT orchestrator executes 7-task staging workflow locally
   ↓
6. CLIENT orchestrator calls get_available_agents() MCP tool
   ↓
7. SERVER returns agent list from database (no embedded templates)
   ↓
8. CLIENT orchestrator spawns agents (Claude Code Task tool or multi-terminal)
   ↓
9. CLIENT agents call get_agent_mission() for their specific work
   ↓
10. CLIENT agents execute on local project files
```

**Key Architectural Benefits**:
- **Zero Server-Side Code Execution**: Server is pure data provider (security + scalability)
- **Client-Side File Access**: Agents work directly with project files (performance)
- **HTTP Transport**: No SSH/VPN complexity (simple firewall configuration)
- **Token Optimization**: Thin prompts (~450-550 tokens) via dynamic fetching
- **Multi-Tenant Security**: Database-level isolation (zero cross-tenant leakage)

**See Also**: [Staging Workflow Architecture](components/STAGING_WORKFLOW.md#architecture-overview) for orchestrator execution details.

---

## Security Architecture

### Authentication Flow

**v3.0 Unified Authentication** (NO auto-login):

```mermaid
graph TD
    A[User Accesses System] --> B{Setup Completed?}
    B -->|No| C[Setup Wizard - No Auth Required]
    B -->|Yes| D[Login Required]
    D --> E[Username + Password]
    E --> F{Credentials Valid?}
    F -->|No| G[Login Failed - Retry]
    F -->|Yes| H[JWT Token Issued]
    H --> I[Token Stored Client-Side]
    I --> J[API Requests Include JWT]
    J --> K[Middleware Validates JWT]
    K --> L[Tenant Context Extracted]
    L --> M[Database Queries Filtered by Tenant]
```

**Code Reference**: `api/middleware/auth.py` - JWT validation middleware

### Password Security

**bcrypt Implementation**:
```python
# Password hashing with high cost factor
import bcrypt

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)  # High security cost
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(
        password.encode('utf-8'), 
        hashed.encode('utf-8')
    )
```

**Password Policy** (enforced in frontend and backend):
- Minimum 12 characters
- At least 1 uppercase letter (A-Z)
- At least 1 lowercase letter (a-z)  
- At least 1 digit (0-9)
- At least 1 special character (!@#$%^&*()_+-=[]{}|;:,.<>?)

### Database Security

**Connection Security**:
```python
# PostgreSQL connection with security optimizations
DATABASE_URL = "postgresql://user:password@localhost:5432/giljo_mcp"

# Connection pooling with security features
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,      # Detect connection failures
    pool_recycle=3600,       # Recycle connections hourly  
    echo=False,              # Never log SQL in production
    isolation_level="READ_COMMITTED"  # Transaction isolation
)
```

**Multi-Tenant Query Filtering**:
```python
# All queries automatically filtered by tenant
async def get_projects(session: AsyncSession, tenant_key: str):
    stmt = select(Project).where(Project.tenant_key == tenant_key)
    result = await session.execute(stmt)
    return result.scalars().all()
```

---

## Performance & Scalability

### Database Performance

**Connection Pooling Configuration**:
```python
# Optimized for production workloads
# From src/giljo_mcp/database.py:40-55
create_engine(
    database_url,
    poolclass=QueuePool,
    pool_size=20,           # 20 persistent connections
    max_overflow=40,        # 40 additional burst connections
    pool_pre_ping=True,     # Health check before use
    pool_recycle=3600,      # Recycle connections after 1 hour
)
```

**Index Optimization**:
```sql
-- Multi-tenant optimized indexes
CREATE INDEX idx_products_tenant_name ON products(tenant_key, name);
CREATE INDEX idx_projects_tenant_status ON projects(tenant_key, status);  
CREATE INDEX idx_agents_tenant_project ON agents(tenant_key, project_id);
CREATE INDEX idx_messages_tenant_timestamp ON messages(tenant_key, created_at);

-- JSONB performance indexes (PostgreSQL-specific)
CREATE INDEX idx_product_config_gin ON products 
    USING gin(config_data jsonb_path_ops);
```

### API Performance

**Rate Limiting**:
```python
# Production-grade rate limiting
# From api/middleware/rate_limit.py
class RateLimitMiddleware:
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        
    async def __call__(self, request, call_next):
        # Implement token bucket algorithm
        # Track requests per client IP + tenant
```

**Async Performance**:
```python
# All I/O operations are async for maximum throughput
async def create_project(project_data: dict, tenant_key: str):
    async with db_manager.get_session_async() as session:
        project = Project(**project_data, tenant_key=tenant_key)
        session.add(project)
        await session.commit()
        return project
```

### WebSocket Scalability

**Connection Management**:
```python
# From api/websocket/manager.py
class WebSocketManager:
    def __init__(self):
        self.connections: Dict[str, WebSocket] = {}
        self.subscriptions: Dict[str, Set[str]] = {}
        
    async def broadcast_to_tenant(self, tenant_key: str, message: dict):
        # Efficient tenant-scoped broadcasting
        for client_id, ws in self.connections.items():
            if self.get_client_tenant(client_id) == tenant_key:
                await ws.send_json(message)
```

**Heartbeat System**:
```python
# From api/app.py:268-270
async def start_heartbeat(interval: int = 30):
    while True:
        await asyncio.sleep(interval)
        # Send heartbeat to all connections
        await self.broadcast_heartbeat()
```

---

## Development & Deployment

### Development Environment

**Requirements**:
```bash
# Python requirements
Python 3.11+
PostgreSQL 18
Node.js 18+

# Python packages (from requirements.txt)
fastapi>=0.104.0
sqlalchemy>=2.0.0
alembic>=1.12.0
psycopg2-binary>=2.9.7
uvicorn>=0.24.0
bcrypt>=4.0.0
python-multipart>=0.0.6
python-jose[cryptography]>=3.3.0

# Frontend packages (from frontend/package.json)  
vue@3.3.8
vuetify@3.4.4
@vue/router@4.2.5
pinia@2.1.7
axios@1.6.0
```

**Development Scripts**:
```bash
# Backend development
python api/run_api.py --reload --log-level debug

# Frontend development  
cd frontend/
npm run dev  # Starts on port 5173 with HMR

# Full stack development
python start_giljo.py --dev
```

### Platform Handler Architecture (Handover 0035)

**Implementation Date**: 2025-10-19
**Status**: ✅ **COMPLETE** - 25.6% code reduction, unified architecture

GiljoAI MCP v3.1.0 implements a unified cross-platform installer using the Strategy pattern, eliminating code duplication and ensuring consistent behavior across Windows, Linux, and macOS.

#### Architecture Overview

**Before** (Deprecated):
- Separate `install.py` (Windows, 1,344 lines)
- Separate `linux_installer/linux_install.py` (Linux/macOS, 1,361 lines)
- 85% code duplication (~2,500 lines)
- Diverging implementations (critical bug: missing pg_trgm extension on Linux)

**After** (v3.1.0):
- Single unified `install.py` orchestrator (400 lines)
- Platform-agnostic core modules
- Platform-specific handlers (Strategy pattern)
- 25.6% code reduction (5,000+ lines → 3,350 lines)

#### File Structure

```
F:\GiljoAI_MCP/
├── install.py                         # Unified orchestrator (400 lines)
└── installer/
    ├── core/                          # Platform-agnostic modules
    │   ├── database.py                # PostgreSQL setup + pg_trgm extension (1,000 lines)
    │   └── config.py                  # Configuration generation (700 lines)
    ├── platforms/                     # Platform-specific handlers
    │   ├── __init__.py                # Auto-detection logic
    │   ├── base.py                    # Abstract PlatformHandler interface (100 lines)
    │   ├── windows.py                 # Windows handler (300 lines)
    │   ├── linux.py                   # Linux handler (300 lines)
    │   └── macos.py                   # macOS handler (200 lines)
    └── shared/                        # Shared utilities
        ├── postgres.py                # PostgreSQL discovery (200 lines)
        └── network.py                 # Network utilities (150 lines)
```

#### Platform Handler Interface

**Abstract Base Class** (`installer/platforms/base.py`):

```python
from abc import ABC, abstractmethod
from pathlib import Path

class PlatformHandler(ABC):
    """Abstract base for platform-specific installation operations"""

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Return: 'Windows', 'Linux', or 'macOS'"""
        pass

    @abstractmethod
    def get_venv_python(self, venv_dir: Path) -> Path:
        """Return: Path to venv Python executable"""
        pass

    @abstractmethod
    def get_venv_pip(self, venv_dir: Path) -> Path:
        """Return: Path to venv pip executable"""
        pass

    @abstractmethod
    def create_desktop_shortcut(self, name: str, target: Path) -> bool:
        """Create platform-specific desktop shortcut"""
        pass

    @abstractmethod
    def find_postgres_installations(self) -> List[Path]:
        """Find PostgreSQL installations on this platform"""
        pass

    @abstractmethod
    def detect_external_ip(self) -> str:
        """Detect external IP address using platform tools"""
        pass
```

#### Platform-Specific Implementations

**Windows Handler** (`installer/platforms/windows.py`):
- venv paths: `venv\Scripts\python.exe`, `venv\Scripts\pip.exe`
- PostgreSQL discovery: `C:\Program Files\PostgreSQL\*\bin\psql.exe`
- Desktop shortcuts: `.lnk` files via `win32com`
- Network detection: `ipconfig` fallback

**Linux Handler** (`installer/platforms/linux.py`):
- venv paths: `venv/bin/python`, `venv/bin/pip`
- PostgreSQL discovery: `/usr/lib/postgresql/*/bin/psql`
- Desktop shortcuts: `.desktop` files with `gio trust`
- Network detection: `ip -4 addr` fallback

**macOS Handler** (`installer/platforms/macos.py`):
- venv paths: `venv/bin/python`, `venv/bin/pip`
- PostgreSQL discovery: `/usr/local/opt/postgresql@*/bin/psql`
- Desktop shortcuts: None (future: .app bundles)
- Network detection: `ifconfig` fallback

#### Unified Core Modules

**Database Setup** (`installer/core/database.py`):
- 100% platform-agnostic PostgreSQL setup
- Creates `giljo_mcp` database
- Creates `giljo_owner` and `giljo_user` roles
- Installs `pg_trgm` extension (critical for full-text search)
- Creates all tables via `DatabaseManager.create_tables_async()`
- Identical SQL execution on all platforms

**Configuration Generation** (`installer/core/config.py`):
- Generates `.env` file (database credentials, JWT secret)
- Generates `config.yaml` (API/frontend ports, network config)
- 100% platform-agnostic
- v3.0 unified architecture (0.0.0.0 binding, firewall control)

#### Benefits

**Immediate**:
- Bug fixes apply to all platforms (pg_trgm now installed everywhere)
- Handover implementations stay synchronized (0034, 0017, future)
- 25.6% less code to maintain (3,350 vs 5,000+ lines)
- Professional architecture (Strategy pattern, SOLID principles)

**Long-Term**:
- macOS support: Fully implemented and tested
- Docker support: Just add `DockerPlatformHandler`
- WSL support: Add `WindowsLinuxPlatformHandler`
- Extensible for future platforms

**Testing**:
- 4 comprehensive test phases
- All platforms verified
- Production-ready deployment

**Code Reference**: `installer/platforms/`, `installer/core/`, `install.py`

### Production Deployment

**System Requirements**:
- **RAM**: 4GB minimum, 8GB recommended
- **CPU**: 2 cores minimum, 4 cores recommended  
- **Storage**: 10GB minimum for database and logs
- **Network**: Static IP recommended for LAN/WAN deployments

**Production Configuration**:
```yaml
# config.yaml (production example)
services:
  api:
    host: 0.0.0.0      # ALWAYS bind to all interfaces
    port: 7272         # Standard API port
  frontend:
    port: 7274         # Standard frontend port

database:
  host: localhost      # NEVER change this
  port: 5432
  name: giljo_mcp
  
security:
  cors:
    allowed_origins:
      - "https://yourdomain.com"
      - "https://api.yourdomain.com"
  rate_limiting:
    enabled: true
    requests_per_minute: 100  # Higher for production

features:
  authentication: true        # ALWAYS enabled in v3.0
  firewall_configured: true   # Set after firewall setup
```

**Production Startup**:
```bash
# Start with production settings
uvicorn api.app:app --host 0.0.0.0 --port 7272 --workers 4

# Or use the startup script
python startup.py --production
```

### Docker Deployment

**Multi-container Architecture**:
```yaml
# docker-compose.yml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "7272:7272"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/giljo_mcp
    depends_on:
      - db
      
  frontend:
    build: ./frontend
    ports:
      - "7274:80"
    depends_on:
      - api
      
  db:
    image: postgres:18
    environment:
      - POSTGRES_DB=giljo_mcp
      - POSTGRES_USER=giljo_user
      - POSTGRES_PASSWORD=secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      
volumes:
  postgres_data:
```

---

## Monitoring & Observability

### Health Checks

**API Health Endpoint**:
```python
# From api/app.py:573-595
@app.get("/health")  
async def health_check():
    checks = {
        "api": "healthy",
        "database": "unknown", 
        "websocket": "unknown"
    }
    
    # Database connectivity test
    if state.db_manager:
        try:
            async with state.db_manager.get_session_async() as session:
                await session.execute(text("SELECT 1"))
                checks["database"] = "healthy"
        except Exception as e:
            checks["database"] = f"unhealthy: {e}"
            
    return {"status": "healthy", "checks": checks}
```

**Database Monitoring**:
```sql
-- Connection monitoring
SELECT count(*) as active_connections 
FROM pg_stat_activity 
WHERE datname = 'giljo_mcp';

-- Performance monitoring
SELECT schemaname, tablename, seq_scan, seq_tup_read, 
       idx_scan, idx_tup_fetch
FROM pg_stat_user_tables 
WHERE schemaname = 'public';
```

### Logging Architecture

**Structured Logging**:
```python
import logging
import sys

# Production logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/giljoai/api.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("giljoai.api")
```

**Log Categories**:
- **Application Logs**: `/var/log/giljoai/api.log`
- **Access Logs**: `/var/log/giljoai/access.log`  
- **Error Logs**: `/var/log/giljoai/errors.log`
- **Audit Logs**: `/var/log/giljoai/audit.log` (authentication events)

---

## Migration & Upgrades

### Database Schema Management (Handover 0601)

**Single Baseline Migration Approach**:
```python
# Fresh Install: Run baseline migration
alembic upgrade head
# Creates ALL 32 tables in single transaction (0.57 seconds)
# Migration: migrations/versions/f504ea46e988_baseline_schema_all_27_tables.py
```

**Migration Strategy**:
- **One pristine baseline migration** - Generated from SQLAlchemy models (not manual)
- **Fresh install time**: <1 second (vs 5+ minutes with old 44-migration chain)
- **All 32 tables created**: From current model definitions
- **pg_trgm extension**: Automatically installed in baseline migration
- **Zero migration conflicts**: Single atomic operation (no chicken-and-egg errors)

**Schema Evolution**:
- **Future changes**: Create incremental migrations on top of baseline
- **Alembic autogenerate**: Detects model changes and generates migrations
- **Test both paths**: Fresh install AND incremental upgrade testing required

### Version Compatibility

**Supported Upgrade Paths**:
- v2.x → v3.0: Full architecture migration required
- v3.0.x → v3.0.y: In-place upgrades supported
- v3.x → v4.0: Future migration path planned

**Migration Tools**:
```bash
# Export tenant data for migration
python scripts/export_tenant.py --tenant-key "default" --output backup.sql

# Import tenant data to new instance
python scripts/import_tenant.py --tenant-key "default" --input backup.sql
```

---

## Troubleshooting

### Common Issues

**Issue: API server won't start**
```bash
# Check port availability
netstat -tulpn | grep :7272

# Check PostgreSQL connection
psql -U postgres -h localhost -p 5432 -l

# Check logs
tail -f logs/api.log
```

**Issue: Database connection failures**
```python
# Verify connection string format
DATABASE_URL = "postgresql://user:password@localhost:5432/giljo_mcp"

# Test connection manually
import psycopg2
conn = psycopg2.connect(DATABASE_URL)
conn.close()
```

**Issue: WebSocket authentication failures**
```javascript
// Check JWT token validity
const token = localStorage.getItem('auth_token')
const payload = JSON.parse(atob(token.split('.')[1]))
console.log('Token expires:', new Date(payload.exp * 1000))
```

### Performance Troubleshooting

**Slow Database Queries**:
```sql
-- Enable query logging
ALTER SYSTEM SET log_statement = 'all';
ALTER SYSTEM SET log_min_duration_statement = 1000;  -- Log queries > 1s
SELECT pg_reload_conf();

-- Analyze slow queries
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;
```

**Memory Usage Issues**:
```python
# Monitor connection pool usage
print(f"Pool size: {engine.pool.size()}")
print(f"Active connections: {engine.pool.checkedout()}")
print(f"Pool overflow: {engine.pool.overflow()}")
```

---

**See Also**:
- [GiljoAI MCP Purpose](GILJOAI_MCP_PURPOSE.md) - Understanding the overall system purpose
- [User Structures & Tenants](USER_STRUCTURES_TENANTS.md) - Multi-tenant architecture details
- [Installation Flow & Process](INSTALLATION_FLOW_PROCESS.md) - Setup and configuration procedures
- [First Launch Experience](FIRST_LAUNCH_EXPERIENCE.md) - Complete onboarding walkthrough

---

*This document provides comprehensive technical details of GiljoAI MCP's server architecture and technology stack as the single source of truth for the October 13, 2025 documentation harmonization.*
#### Task ↔ Agent Job Linking (Handover 0072)

Defines explicit linkage between user tasks and `AgentJob` records to ground assignments and enable status propagation.

Key points:
- Tasks reference the owning project and (optionally) the agent job handling it
- Agent jobs can advertise linked task IDs for traceability
- API responses include linkage fields to avoid client-side inference
