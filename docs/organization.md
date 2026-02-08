# Organization & Role Model

This document defines the organizational hierarchy, user roles, and permission model for GiljoAI MCP.

## Hierarchy Overview

```
Org
├── Admin (role)
│   └── All Developer permissions + user management + admin settings
├── Developer (role)
│   └── Own: Products → Projects → Tasks → Jobs → Messages
└── Viewer (role) [RESERVED - not enforced yet]
    └── Read-only on invited products/projects
```

**Ownership Chain**: `Org → Users → Products → Projects → Tasks → Jobs → Messages`

- **Messages**: Isolated to project scope, not part of 360 memory or context sources. May become auditable/transcript feature in future.

## Current Roles (Implemented)

### Admin

Full system access plus user management capabilities.

| Permission | Status |
|------------|--------|
| Create users | Yes |
| Manage users (reset passwords, disable) | Yes |
| Access admin settings | Yes |
| Work as developer | Yes |
| Own products | Yes |
| Create projects | Yes |
| Create tasks | Yes |

### Developer

Standard user with full development capabilities.

| Permission | Status |
|------------|--------|
| Own products | Yes |
| Create projects | Yes |
| Create tasks | Yes |
| Manage own jobs | Yes |

## Reserved Roles (Designed, Not Enforced)

### Viewer

Read-only access for auditing, stakeholder visibility, or onboarding purposes.

| Permission | Status |
|------------|--------|
| Create products | No |
| Create projects | No |
| Create tasks | No |
| View invited products/projects | Yes (read-only) |

**Implementation Status**: Role value reserved in enum. Permission enforcement deferred until use case arises.

**Potential Use Cases**:
- Auditors reviewing project history and compliance
- Stakeholders tracking progress without modification risk
- New team members onboarding with safe read-only access
- External clients viewing project status

## Tenant Isolation Model

Users within an org maintain **per-user tenant separation**:

| Entity | Isolation Level | Sharing |
|--------|-----------------|---------|
| Products | User-owned | Shareable via invitation (future) |
| Projects | User-isolated | Others can view completed/pending status (future) |
| Tasks | User-isolated | Transferable to other users (future) |
| Jobs | Project-scoped | Follows project isolation |
| Messages | Project-scoped | Private to project owner |

**Key Principle**: Users cannot see other users' products and projects until explicitly invited (future feature).

## Future Features

### Invitation System

| Feature | Available To |
|---------|--------------|
| Invite others to product | All users (product owner) |
| Access 360 memory on invited products | All invited users |
| See other users' projects in product | All invited users (read descriptions only) |

### Transfer Capabilities

| Feature | Available To |
|---------|--------------|
| Transfer project ownership | All users |
| Transfer task ownership | All users |
| Transfer product ownership | All users |
| Take over project (disabled/removed user) | Admin only |

## Implementation Notes

### Role Storage

Role field stored with enum values: `admin`, `developer`, `viewer`

Location: TBD (User table or OrgMembership table - to be decided during implementation)

### Permission Checking

- Admin and Developer permissions: Enforced now
- Viewer permissions: Reserved, enforcement deferred

### Relationship to Existing Architecture

- Per-user `tenant_key` remains (assigned at registration)
- Org membership provides visibility layer on top of tenant isolation
- Invitation system will add access records without changing tenant_key

## Implementation Timeline

| Feature | Target |
|---------|--------|
| Admin/Developer roles | Current (0424 series) |
| Role enum with Viewer reserved | 0740 or later |
| Viewer permission enforcement | When use case arises |
| Invitation system | Future series |
| Transfer capabilities | Future series |
