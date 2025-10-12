# Organization and Tenancy

This document explains user roles, tenancy, and visibility rules for GiljoAI MCP.

## Why
- Ensure data separation and safe collaboration across multiple tenants.
- Provide clear visibility rules for users, agents, and subscriptions.

## How
- A per‑request `X-Tenant-Key` header identifies the tenant context.
- Authorization checks in API endpoints and WebSocket subscriptions validate ownership within tenant boundaries.
- Admin bootstrap occurs during setup; further user management is role‑based via the API/UI.

## What
### Tenancy Model
- Tenants: logical partitions within the same deployment (single database), identified by a tenant key string.
- Entities (projects, agents, messages) carry a tenant key and are only visible within the matching tenant.
- System/localhost users are created for safe initial bootstrap and development.

### Roles
- Admin: full access within tenant; manages users, API keys, and product configurations.
- Member: standard read/write access scoped to their tenant’s resources.
- Viewer: read‑only access scoped to tenant.

### Authentication
- JWT for end‑users; tokens encode identity and role.
- API Keys for service automation; keys are mapped to permissions and can be rotated.
- Localhost auto‑login simplifies initial setup without exposing network‑wide access.

### Visibility Rules
- API filters all data by tenant key.
- WebSocket subscriptions are validated against entity ownership; unauthorized subscriptions are rejected with explicit errors.
- Cross‑tenant access is prohibited; attempts are logged and blocked.

### Multi‑Tenant Considerations
- Single database schema with tenant key columns simplifies operations; future sharding can be added transparently.
- Migrations via Alembic maintain consistency across tenants.

