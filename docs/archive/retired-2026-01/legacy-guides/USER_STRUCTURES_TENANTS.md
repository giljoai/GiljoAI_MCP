# User Structures & Multi-Tenant Architecture

**Document Version**: 10_13_2025
**Status**: Single Source of Truth
**Last Updated**: October 13, 2025

---

## Overview

GiljoAI MCP implements a **multi-tenant architecture** with complete data isolation at the database level. This ensures that multiple organizations, teams, or projects can use the same GiljoAI MCP instance without any cross-contamination of data.

### Key Concepts

- **Tenant**: An isolated namespace containing all data for an organization/team
- **Tenant Key**: UUID-based identifier that scopes all database operations
- **Row-Level Isolation**: Every database table includes `tenant_key` for filtering
- **Authentication Context**: User authentication establishes tenant context
- **Default Tenant**: Fresh installations create a "default" tenant

---

## Tenant Architecture

### What is a Tenant?

A **tenant** in GiljoAI MCP represents a completely isolated workspace containing:

- **Users**: People who can authenticate and access the system
- **Products**: Top-level organizational units (applications, services, etc.)
- **Projects**: Development initiatives with specific goals
- **Agents**: AI assistants working on projects
- **Tasks**: Work items and assignments
- **Messages**: Communication between agents
- **Sessions**: Orchestration sessions and memories
- **Context**: Code analysis and vision documents

### Tenant Isolation Mechanics

**Database Level Isolation**:
```sql
-- All tables include tenant_key column
CREATE TABLE products (
    id VARCHAR(36) PRIMARY KEY,
    tenant_key VARCHAR(36) NOT NULL,  -- ← TENANT ISOLATION
    name VARCHAR(255) NOT NULL,
    -- ... other fields
);

CREATE INDEX idx_product_tenant ON products(tenant_key);
```

**Query Filtering** (automatic):
```sql
-- Every query automatically filtered by tenant
SELECT * FROM products WHERE tenant_key = 'current-tenant-uuid';
SELECT * FROM projects WHERE tenant_key = 'current-tenant-uuid';
SELECT * FROM agents WHERE tenant_key = 'current-tenant-uuid';
```

**No Cross-Tenant Access**:
- Tenant A cannot see or modify Tenant B's data
- Database queries automatically include tenant_key filters
- Application enforces tenant context in all operations
- No shared resources between tenants (except system tables)

---

## User Authentication & Tenant Context

### How Authentication Establishes Tenant Context

**Step 1: User Authenticates**
```http
POST /api/auth/login
{
    "username": "john.doe",
    "password": "secure-password"
}
```

**Step 2: JWT Token Issued**
```json
{
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "token_type": "bearer",
    "expires_in": 86400,
    "user": {
        "id": "user-uuid",
        "username": "john.doe",
        "tenant_key": "tenant-uuid-123",  // ← TENANT CONTEXT
        "role": "admin"
    }
}
```

**Step 3: All Subsequent Requests Include Tenant Context**
```http
GET /api/products
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...

# Backend automatically filters by tenant_key from JWT:
# SELECT * FROM products WHERE tenant_key = 'tenant-uuid-123'
```

### Why Tenant Data Loads AFTER Authentication

**Authentication-First Design**:

1. **User Authentication** → Establishes who is accessing the system
2. **Tenant Context Extraction** → Determines which tenant's data to load
3. **Data Scoping** → All database queries filtered by tenant_key
4. **UI Population** → Frontend receives only tenant-scoped data

**Security Benefits**:
- No data exposure before authentication
- Tenant isolation enforced at the application layer
- JWT tokens carry tenant context securely
- Session management maintains tenant boundaries

---

## Tenant Data Hierarchy

### Organizational Structure

```
Tenant (e.g., "Acme Corp")
├── Users (john.doe, jane.smith, admin)
├── Products (Web App, Mobile App, API Service)
│   ├── Product 1: Web App
│   │   ├── Projects (User Auth, Payment System, Admin Dashboard)
│   │   └── Tasks (Implement Login, Add Stripe, Build UI)
│   └── Product 2: Mobile App
│       ├── Projects (iOS App, Android App, Backend API)  
│       └── Tasks (SwiftUI Views, Kotlin Activities, FastAPI)
├── Agents (orchestrator-1, implementer-auth, tester-api)
├── Sessions (orchestration memories, handoff contexts)
└── Context (vision documents, code analysis, templates)
```

### Database Model Relationships

**Tenant-Scoped Tables**:
```python
# All models include tenant_key
class Product(Base):
    id = Column(String(36), primary_key=True)
    tenant_key = Column(String(36), nullable=False, index=True)  # ← ISOLATION
    name = Column(String(255), nullable=False)
    # ... relationships to tenant-scoped Projects, Tasks

class Project(Base):  
    id = Column(String(36), primary_key=True)
    tenant_key = Column(String(36), nullable=False, index=True)  # ← ISOLATION
    product_id = Column(String(36), ForeignKey("products.id"))
    # ... relationships to tenant-scoped Agents, Messages

class Agent(Base):
    id = Column(String(36), primary_key=True)
    tenant_key = Column(String(36), nullable=False, index=True)  # ← ISOLATION
    project_id = Column(String(36), ForeignKey("projects.id"))
    # ... agent-specific fields

class User(Base):
    id = Column(String(36), primary_key=True)
    tenant_key = Column(String(36), nullable=False, index=True)  # ← ISOLATION
    username = Column(String(64), unique=True, nullable=False)
    # ... user authentication and profile fields
```

---

## Default Tenant on Fresh Install

### Fresh Installation Tenant Setup

When running `python install.py`, the installer:

1. **Creates Default Tenant**:
   ```python
   DEFAULT_TENANT_KEY = "default"
   ```

2. **Creates Admin User**:
   ```sql
   INSERT INTO users (
       id, tenant_key, username, password_hash, role, is_active
   ) VALUES (
       'admin-uuid', 'default', 'admin', '$2b$12$...', 'admin', true
   );
   ```

3. **Sets Up Default Product** (optional):
   ```sql
   INSERT INTO products (
       id, tenant_key, name, description
   ) VALUES (
       'product-uuid', 'default', 'My First Product', 'Default product for getting started'
   );
   ```

### Default Tenant Characteristics

**Tenant Key**: `"default"`
- Simple string identifier for single-tenant deployments
- Can be changed to organization-specific identifier
- Serves as namespace for all data

**Default Admin User**:
- Username: `admin`
- Password: `admin` (forced change on first login)
- Role: `admin` (full system access)
- Tenant: `default`

**Why "default"**:
- Intuitive for single-organization deployments
- Easy to identify in logs and database queries
- Can be renamed to match organization (e.g., "acme-corp")

---

## Multi-Tenant Data Scoping

### How Tenant Scoping Works

**Database Query Filtering**:
```python
# All queries automatically include tenant filter
def get_products(session: Session, tenant_key: str):
    return session.query(Product).filter(
        Product.tenant_key == tenant_key
    ).all()

def get_projects(session: Session, tenant_key: str):
    return session.query(Project).filter(
        Project.tenant_key == tenant_key
    ).all()

# Agent operations also tenant-scoped
def get_agent_messages(session: Session, agent_name: str, tenant_key: str):
    return session.query(Message).filter(
        Message.tenant_key == tenant_key,
        Message.to_agent == agent_name
    ).all()
```

**API Endpoint Protection**:
```python
@router.get("/products")
async def get_products(current_user: User = Depends(get_current_user)):
    # Extract tenant_key from authenticated user
    tenant_key = current_user.tenant_key
    
    # Query filtered by tenant automatically
    products = await product_service.get_products(tenant_key=tenant_key)
    return products
```

**Frontend Data Loading**:
```javascript
// All API calls automatically scoped to user's tenant
export const productStore = {
  async loadProducts() {
    // JWT token contains tenant_key
    // Backend filters results automatically
    const response = await api.get('/api/products');
    this.products = response.data; // Only tenant's products
  }
}
```

### Cross-Tenant Isolation Examples

**Example 1: Two Companies Using Same Instance**

```
Tenant: "acme-corp"
├── User: alice@acme.com (admin)
├── Products: ["Acme Web App", "Acme Mobile"]
├── Projects: ["User Authentication", "Payment Integration"]
└── Agents: ["orchestrator-acme", "implementer-acme-auth"]

Tenant: "globo-tech"  
├── User: bob@globo.com (admin)
├── Products: ["Globo Platform", "Globo Analytics"]
├── Projects: ["Data Pipeline", "Real-time Dashboard"]
└── Agents: ["orchestrator-globo", "database-expert-globo"]
```

**Isolation Guarantees**:
- Alice cannot see Globo's products, projects, or agents
- Bob cannot see Acme's data or orchestration sessions
- Agents from different tenants cannot communicate
- Database queries never cross tenant boundaries

**Example 2: Department-Level Isolation**

```
Tenant: "engineering-dept"
├── Products: ["Core API", "Frontend App", "Mobile SDK"]
├── Projects: ["API Refactoring", "UI Redesign", "SDK v2"]
├── Users: ["john.engineer", "jane.architect", "bob.tester"]

Tenant: "product-dept"
├── Products: ["Product Analytics", "User Research", "A/B Testing"]  
├── Projects: ["Analytics Dashboard", "User Survey Tool"]
├── Users: ["alice.pm", "carol.designer", "dave.analyst"]
```

---

## Multi-Tenant Configuration

### Tenant-Specific Settings

Each tenant can have independent configuration:

```json
{
  "tenant_key": "acme-corp",
  "settings": {
    "architecture": "FastAPI + PostgreSQL + React",
    "tech_stack": ["Python 3.11", "TypeScript", "PostgreSQL 18"],
    "deployment_mode": "server",
    "api_base_url": "https://api.acme.com",
    "authentication": {
      "provider": "internal", 
      "session_timeout": 86400,
      "password_policy": "strict"
    },
    "features": {
      "agent_orchestration": true,
      "context_chunking": true,
      "git_integration": true
    }
  }
}
```

### Environment Variables (Per-Tenant)

```bash
# Tenant-specific database settings (if using separate DBs)
ACME_DATABASE_URL=postgresql://user:pass@acme-db:5432/giljo_mcp
GLOBO_DATABASE_URL=postgresql://user:pass@globo-db:5432/giljo_mcp

# Tenant-specific API configurations  
ACME_API_BASE_URL=https://api.acme.com
GLOBO_API_BASE_URL=https://api.globo.com

# Tenant-specific authentication
ACME_JWT_SECRET=acme-specific-secret
GLOBO_JWT_SECRET=globo-specific-secret
```

---

## User Roles & Permissions

### Role Hierarchy

**Admin Role**:
- Full tenant access (all products, projects, agents)
- User management (create, modify, delete users)
- System configuration (tenant settings, integrations)
- Agent orchestration and monitoring
- Database and backup access

**Developer Role**:
- Product and project access (assigned products only)  
- Agent creation and management
- Task assignment and completion
- Code analysis and context management
- Limited system configuration

**Viewer Role**:
- Read-only access to assigned products/projects
- Agent monitoring and status viewing
- Task progress tracking
- Documentation access
- No modification capabilities

### Permission Matrix

| Action | Admin | Developer | Viewer |
|--------|-------|-----------|--------|
| Create Products | ✅ | ❌ | ❌ |
| Create Projects | ✅ | ✅* | ❌ |
| Spawn Agents | ✅ | ✅* | ❌ |
| Assign Tasks | ✅ | ✅* | ❌ |
| View Agent Status | ✅ | ✅* | ✅* |
| Access Context | ✅ | ✅* | ✅* |
| Modify User Roles | ✅ | ❌ | ❌ |
| System Configuration | ✅ | ❌ | ❌ |

*\* Only for assigned products/projects*

---

## Tenant Security & Compliance

### Data Isolation Guarantees

**Database Level**:
- Row-level security with tenant_key filtering
- Foreign key relationships respect tenant boundaries
- Indexes optimized for tenant-scoped queries
- No cross-tenant data leakage possible

**Application Level**:
- JWT tokens carry tenant context
- All API endpoints validate tenant access
- Session management maintains tenant isolation
- Agent communication restricted to tenant scope

**System Level**:
- Separate log namespaces per tenant
- Isolated file storage (vision documents, uploads)
- Independent backup and restore capabilities
- Tenant-specific monitoring and alerts

### Compliance Features

**Audit Trail**:
```sql
-- All modifications tracked with tenant context
CREATE TABLE audit_log (
    id VARCHAR(36) PRIMARY KEY,
    tenant_key VARCHAR(36) NOT NULL,  -- ← Tenant isolation
    user_id VARCHAR(36) NOT NULL,
    action VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id VARCHAR(36) NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW(),
    details JSONB
);
```

**Data Retention**:
- Configurable retention policies per tenant
- Automatic cleanup of expired data
- Export capabilities for compliance reporting
- Secure deletion with verification

**Access Control**:
- Strong authentication with bcrypt password hashing
- JWT token expiration and rotation
- Role-based access control (RBAC)
- API rate limiting per tenant

---

## Migration & Multi-Tenant Management

### Adding New Tenants

**Step 1: Create Tenant Admin**
```sql
-- Create new tenant admin user
INSERT INTO users (
    id, tenant_key, username, email, password_hash, role, is_active
) VALUES (
    'new-admin-uuid', 'new-tenant-key', 'admin', 'admin@neworg.com', 
    '$2b$12$...', 'admin', true
);
```

**Step 2: Initialize Default Product**
```sql  
-- Create default product for new tenant
INSERT INTO products (
    id, tenant_key, name, description, created_at
) VALUES (
    'product-uuid', 'new-tenant-key', 'Default Product', 
    'Initial product for new organization', NOW()
);
```

**Step 3: Configure Tenant Settings**
- Update tenant-specific configuration
- Set up authentication policies
- Configure agent templates and roles
- Initialize default project templates

### Tenant Data Migration

**Export Tenant Data**:
```bash
# Export all data for specific tenant
python scripts/export_tenant.py --tenant-key "acme-corp" --output acme-backup.sql
```

**Import to New Instance**:
```bash
# Import tenant data to new GiljoAI MCP instance  
python scripts/import_tenant.py --tenant-key "acme-corp" --input acme-backup.sql
```

**Cross-Instance Migration**:
- Complete tenant data portability
- Preserves all relationships and constraints
- Maintains user authentication and roles
- Transfers agent orchestration history

---

## Best Practices

### Tenant Design Guidelines

**Tenant Boundaries**:
- One tenant per organization/company
- Avoid mixing development teams in same tenant
- Consider department-level tenants for large organizations
- Plan tenant structure before deployment

**Naming Conventions**:
- Use descriptive tenant keys: `"acme-corp"`, `"engineering-team"`
- Avoid generic names: `"tenant1"`, `"company"`
- Include organization identifier: `"acme-engineering"`, `"globo-product"`
- Keep tenant keys immutable after creation

**Security Practices**:
- Unique JWT secrets per tenant
- Regular rotation of authentication credentials
- Monitor cross-tenant access attempts
- Implement tenant-specific rate limiting

### Performance Optimization

**Database Indexing**:
```sql
-- Essential indexes for multi-tenant performance
CREATE INDEX idx_products_tenant_name ON products(tenant_key, name);
CREATE INDEX idx_projects_tenant_status ON projects(tenant_key, status);
CREATE INDEX idx_agents_tenant_project ON agents(tenant_key, project_id);
CREATE INDEX idx_messages_tenant_timestamp ON messages(tenant_key, created_at);
```

**Query Optimization**:
- Always include tenant_key in WHERE clauses
- Use tenant_key as first column in composite indexes
- Avoid queries that span multiple tenants
- Monitor query plans for tenant filtering

**Resource Management**:
- Set appropriate connection pool sizes per tenant load
- Monitor memory usage with multiple active tenants
- Implement tenant-specific caching strategies
- Scale resources based on tenant usage patterns

---

## Troubleshooting

### Common Issues

**Issue: User can't see their data after login**
```bash
# Check user's tenant_key
SELECT username, tenant_key FROM users WHERE username = 'problem-user';

# Verify data exists in correct tenant
SELECT COUNT(*) FROM products WHERE tenant_key = 'user-tenant-key';

# Check JWT token payload
# JWT should contain correct tenant_key
```

**Issue: Cross-tenant data appearing**
```bash
# Audit queries missing tenant filters
# All queries should include: WHERE tenant_key = ?

# Check for missing tenant_key indexes
SELECT schemaname, tablename, indexname 
FROM pg_indexes 
WHERE indexname LIKE '%tenant%';
```

**Issue: Agent communication failures**
```bash
# Verify agents in same tenant
SELECT agent_name, tenant_key FROM agents WHERE agent_name IN ('agent1', 'agent2');

# Check message queue filtering  
SELECT COUNT(*) FROM messages WHERE tenant_key = 'expected-tenant';
```

---

**See Also**:
- [GiljoAI MCP Purpose](GILJOAI_MCP_PURPOSE.md) - Understanding the overall system
- [Server Architecture & Tech Stack](SERVER_ARCHITECTURE_TECH_STACK.md) - Technical implementation details
- [Installation Flow & Process](INSTALLATION_FLOW_PROCESS.md) - Setting up tenant configuration
- [First Launch Experience](FIRST_LAUNCH_EXPERIENCE.md) - Default tenant creation walkthrough

---

*This document provides comprehensive understanding of GiljoAI MCP's multi-tenant architecture and user structures as the single source of truth for the October 13, 2025 documentation harmonization.*