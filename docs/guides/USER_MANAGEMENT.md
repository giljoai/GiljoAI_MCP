# User Management Guide

**Version:** 1.0.0
**Last Updated:** 2025-10-08
**Audience:** System Administrators, Team Leads

---

## Table of Contents

1. [Overview](#overview)
2. [User Roles and Permissions](#user-roles-and-permissions)
3. [Creating Users (Admin Only)](#creating-users-admin-only)
4. [Managing User Profiles](#managing-user-profiles)
5. [Changing Passwords](#changing-passwords)
6. [Deactivating and Reactivating Users](#deactivating-and-reactivating-users)
7. [Changing User Roles](#changing-user-roles)
8. [API Key Management Per User](#api-key-management-per-user)
9. [Multi-Tenant Isolation](#multi-tenant-isolation)
10. [Security Best Practices](#security-best-practices)
11. [Troubleshooting](#troubleshooting)

---

## Overview

GiljoAI MCP provides comprehensive user management capabilities for team environments deployed in LAN or WAN mode. The user management system enables:

- **Role-Based Access Control (RBAC)**: Three distinct roles with different permission levels
- **Secure Authentication**: Password hashing with bcrypt, JWT session management
- **API Key Management**: Per-user API keys for MCP tool integration
- **Multi-Tenant Isolation**: Complete data isolation between tenants
- **Audit Trail**: Track user creation, modification, and login activity

### When Is User Management Available?

User management features are available when:
- Deployment mode is set to `lan`, `server`, or `wan` in `config.yaml`
- Database migration has been applied (User and APIKey tables exist)
- At least one admin user has been created

In **localhost mode**, user management is disabled and authentication is bypassed.

---

## User Roles and Permissions

GiljoAI MCP implements a three-tier role system:

### Role Comparison Table

| Feature | Admin | Developer | Viewer |
|---------|-------|-----------|--------|
| **User Management** | | | |
| Create users | ✅ | ❌ | ❌ |
| View all users | ✅ | ❌ | ❌ |
| Modify user roles | ✅ | ❌ | ❌ |
| Deactivate users | ✅ | ❌ | ❌ |
| Reset user passwords | ✅ | ❌ | ❌ |
| **Project Management** | | | |
| Create projects | ✅ | ✅ | ❌ |
| Edit own projects | ✅ | ✅ | ❌ |
| Edit all projects | ✅ | ❌ | ❌ |
| Delete projects | ✅ | ✅ | ❌ |
| View projects | ✅ | ✅ | ✅ |
| **Agent Management** | | | |
| Spawn agents | ✅ | ✅ | ❌ |
| Retire agents | ✅ | ✅ | ❌ |
| View agent status | ✅ | ✅ | ✅ |
| **Task Management** | | | |
| Create tasks | ✅ | ✅ | ❌ |
| Assign tasks | ✅ | ✅ | ❌ |
| Update task status | ✅ | ✅ | ❌ |
| View tasks | ✅ | ✅ | ✅ |
| **API Keys** | | | |
| Generate own keys | ✅ | ✅ | ✅ |
| View own keys | ✅ | ✅ | ✅ |
| Revoke own keys | ✅ | ✅ | ✅ |
| **Profile Management** | | | |
| Change own password | ✅ | ✅ | ✅ |
| Update own profile | ✅ | ✅ | ✅ |
| View own profile | ✅ | ✅ | ✅ |
| **System Configuration** | | | |
| Modify settings | ✅ | ❌ | ❌ |
| View system logs | ✅ | ❌ | ❌ |
| Access setup wizard | ✅ | ❌ | ❌ |

### Role Descriptions

#### Admin
**Purpose**: System administrators and team leads

**Capabilities**:
- Full system access
- User account creation and management
- Role assignment and modification
- System configuration changes
- View all projects and agents across tenant
- Password reset for all users

**Use Cases**:
- IT administrators
- Team leads managing developer teams
- System owners responsible for deployment

**Security Notes**:
- Admins cannot change their own role (prevents lockout)
- At least one active admin must exist per tenant
- Admin password resets require database access

#### Developer
**Purpose**: Development team members who create and manage projects

**Capabilities**:
- Create and manage own projects
- Spawn and retire agents
- Create and assign tasks
- Generate API keys for development
- View all projects in tenant (collaboration)
- Cannot modify other users or system settings

**Use Cases**:
- Software developers
- AI engineers working on projects
- Team members actively building features

**Limitations**:
- Cannot create or modify user accounts
- Cannot change system settings
- Cannot access setup wizard

#### Viewer
**Purpose**: Stakeholders, observers, and read-only users

**Capabilities**:
- View projects, agents, and tasks
- View project status and progress
- Generate API keys for read-only access
- Update own profile and password

**Use Cases**:
- Project managers monitoring progress
- Stakeholders reviewing project status
- Observers who need visibility without edit access

**Limitations**:
- Cannot create or modify any projects/agents/tasks
- Cannot perform write operations
- Read-only access to all resources

---

## Creating Users (Admin Only)

Only users with the **admin** role can create new user accounts.

### Via Dashboard (Web UI)

1. **Log in as Admin**
   - Navigate to `http://YOUR_SERVER_IP:7274`
   - Enter admin credentials

2. **Navigate to User Management**
   - Click **Settings** in the main navigation
   - Select **User Management** from the sidebar
   - (Admin-only section, not visible to other roles)

3. **Click "Create User" Button**

4. **Fill in User Details**:
   - **Username** (required):
     - 3-64 characters
     - Alphanumeric and underscore only
     - Must be globally unique
     - Cannot be changed after creation

   - **Email** (optional):
     - Valid email format
     - Must be unique if provided
     - Used for password recovery (future feature)

   - **Full Name** (optional):
     - Display name for user
     - Shown in UI and logs

   - **Password** (required):
     - Minimum 8 characters (recommend 12+)
     - Mix of uppercase, lowercase, numbers, symbols
     - Securely hashed with bcrypt before storage

   - **Role** (required):
     - Select from: Admin, Developer, Viewer
     - Choose based on user's responsibilities
     - Can be changed later by admin

   - **Active Status** (default: Active):
     - Active: User can log in immediately
     - Inactive: Account created but login disabled

5. **Click "Create User"**

6. **Success Confirmation**:
   - User appears in user list
   - Credentials can be shared with new user
   - User can log in immediately (if active)

### Via API

**Endpoint**: `POST /api/users/`

**Authentication**: Admin role required (JWT cookie or API key)

**Request Body**:
```json
{
  "username": "jsmith",
  "email": "jsmith@example.com",
  "full_name": "John Smith",
  "password": "SecurePassword123!",
  "role": "developer",
  "is_active": true
}
```

**Example cURL**:
```bash
curl -X POST http://YOUR_SERVER_IP:7272/api/users/ \
  -H "Content-Type: application/json" \
  -H "X-API-Key: gk_your_admin_api_key" \
  -d '{
    "username": "jsmith",
    "email": "jsmith@example.com",
    "full_name": "John Smith",
    "password": "SecurePassword123!",
    "role": "developer",
    "is_active": true
  }'
```

**Success Response** (201 Created):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "jsmith",
  "email": "jsmith@example.com",
  "full_name": "John Smith",
  "role": "developer",
  "tenant_key": "default",
  "is_active": true,
  "created_at": "2025-10-08T10:30:00Z",
  "last_login": null
}
```

**Error Responses**:

- **400 Bad Request** - Username already exists:
  ```json
  {
    "detail": "Username 'jsmith' already exists"
  }
  ```

- **400 Bad Request** - Email already exists:
  ```json
  {
    "detail": "Email 'jsmith@example.com' already exists"
  }
  ```

- **403 Forbidden** - Not an admin:
  ```json
  {
    "detail": "Admin role required"
  }
  ```

### Validation Rules

**Username**:
- Minimum length: 3 characters
- Maximum length: 64 characters
- Allowed characters: a-z, A-Z, 0-9, underscore (_)
- Must be globally unique (across all tenants)
- Case-sensitive

**Email** (if provided):
- Valid email format (RFC 5322)
- Must be unique if provided
- Case-insensitive uniqueness

**Password**:
- Minimum length: 8 characters
- Recommendation: 12+ characters with mixed case, numbers, symbols
- Hashed with bcrypt (cost factor 12) before storage
- Never stored in plaintext

**Role**:
- Must be one of: `admin`, `developer`, `viewer`
- Case-sensitive

**Tenant Key**:
- Automatically inherited from admin creating the user
- Cannot be changed after creation
- Ensures multi-tenant isolation

---

## Managing User Profiles

Users can update their own profile information. Admins can update any user's profile.

### Self-Service Profile Updates (All Roles)

**Via Dashboard**:
1. Click username in top-right corner
2. Select **Profile** from dropdown
3. Update editable fields:
   - Email
   - Full name
4. Click **Save Changes**

**Editable Fields**:
- Email (optional)
- Full name (optional)

**Read-Only Fields** (displayed but cannot be changed):
- Username
- Role
- Tenant key
- Created at
- Last login

### Admin Profile Management

Admins can update any user's profile:

1. **Navigate to User Management** (Settings → User Management)
2. **Find user** in the list
3. **Click "Edit" button**
4. **Update fields**:
   - Email
   - Full name
   - Active status (activate/deactivate)
5. **Click "Save Changes"**

**Note**: To change a user's role, use the "Change Role" feature (see [Changing User Roles](#changing-user-roles)).

### Via API

**Endpoint**: `PUT /api/users/{user_id}`

**Authentication**: User can update self, or admin can update any user

**Request Body** (all fields optional):
```json
{
  "email": "newemail@example.com",
  "full_name": "Updated Name",
  "is_active": true
}
```

**Example cURL** (user updating self):
```bash
curl -X PUT http://YOUR_SERVER_IP:7272/api/users/550e8400-e29b-41d4-a716-446655440000 \
  -H "Content-Type: application/json" \
  -H "X-API-Key: gk_your_api_key" \
  -d '{
    "email": "newemail@example.com",
    "full_name": "Updated Name"
  }'
```

**Success Response** (200 OK):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "jsmith",
  "email": "newemail@example.com",
  "full_name": "Updated Name",
  "role": "developer",
  "tenant_key": "default",
  "is_active": true,
  "created_at": "2025-10-08T10:30:00Z",
  "last_login": "2025-10-08T14:45:00Z"
}
```

**Error Responses**:

- **403 Forbidden** - Non-admin trying to update other user:
  ```json
  {
    "detail": "Cannot update other users' profiles"
  }
  ```

- **404 Not Found** - User not found or in different tenant:
  ```json
  {
    "detail": "User not found"
  }
  ```

---

## Changing Passwords

Users can change their own password. Admins can reset passwords for any user.

### Self-Service Password Change (All Roles)

**Via Dashboard**:
1. Click username → **Profile**
2. Navigate to **Security** tab
3. Enter **Current Password**
4. Enter **New Password**
5. Confirm **New Password**
6. Click **Change Password**

**Requirements**:
- Must provide correct current password
- New password must meet minimum requirements (8+ characters)
- New password must differ from old password

### Admin Password Reset

Admins can reset passwords for any user **without knowing the current password**:

**Via Dashboard**:
1. Navigate to **User Management**
2. Find user in list
3. Click **Reset Password** button
4. Enter new password
5. Confirm new password
6. Click **Reset Password**

**Use Cases**:
- User forgot password
- Account recovery
- Security incident response
- Forced password change

**Note**: Admin is responsible for securely communicating new password to user.

### Via API

**Endpoint**: `PUT /api/users/{user_id}/password`

**Authentication**: User can change own password, or admin can change any password

**Request Body** (user changing own password):
```json
{
  "old_password": "CurrentPassword123!",
  "new_password": "NewSecurePassword456!"
}
```

**Request Body** (admin resetting user password):
```json
{
  "new_password": "AdminResetPassword789!"
}
```

**Example cURL** (user changing own):
```bash
curl -X PUT http://YOUR_SERVER_IP:7272/api/users/550e8400-e29b-41d4-a716-446655440000/password \
  -H "Content-Type: application/json" \
  -H "X-API-Key: gk_your_api_key" \
  -d '{
    "old_password": "CurrentPassword123!",
    "new_password": "NewSecurePassword456!"
  }'
```

**Example cURL** (admin reset):
```bash
curl -X PUT http://YOUR_SERVER_IP:7272/api/users/550e8400-e29b-41d4-a716-446655440000/password \
  -H "Content-Type: application/json" \
  -H "X-API-Key: gk_admin_api_key" \
  -d '{
    "new_password": "AdminResetPassword789!"
  }'
```

**Success Response** (200 OK):
```json
{
  "message": "Password updated successfully"
}
```

**Error Responses**:

- **400 Bad Request** - Current password required for non-admin:
  ```json
  {
    "detail": "Current password is required to change your password"
  }
  ```

- **400 Bad Request** - Incorrect current password:
  ```json
  {
    "detail": "Current password is incorrect"
  }
  ```

- **403 Forbidden** - Non-admin trying to change other user's password:
  ```json
  {
    "detail": "Cannot change other users' passwords"
  }
  ```

### Password Security Best Practices

✅ **Strong Passwords**:
- Minimum 12 characters (system requires 8+)
- Mix uppercase, lowercase, numbers, symbols
- Avoid dictionary words
- Use password manager for generation and storage

✅ **Password Rotation**:
- Change passwords every 90 days
- Use different password for each system
- Never reuse old passwords

✅ **Storage**:
- All passwords hashed with bcrypt (cost factor 12)
- Never stored in plaintext
- Salted per-password
- Resistant to rainbow table attacks

---

## Deactivating and Reactivating Users

Admins can deactivate user accounts to prevent login without deleting the account. This preserves audit history and allows reactivation if needed.

### Deactivating a User

**Via Dashboard**:
1. Navigate to **Settings → User Management**
2. Find user in list
3. Click **Deactivate** button
4. Confirm deactivation
5. User status changes to "Inactive"

**Effects of Deactivation**:
- User cannot log in to dashboard
- Existing API keys stop working immediately
- User's projects and data are preserved
- User appears in user list with "Inactive" badge
- Can be reactivated by admin at any time

**Via API**:

**Endpoint**: `DELETE /api/users/{user_id}`

**Note**: Despite using DELETE method, this performs **soft delete** (sets `is_active = false`)

**Example cURL**:
```bash
curl -X DELETE http://YOUR_SERVER_IP:7272/api/users/550e8400-e29b-41d4-a716-446655440000 \
  -H "X-API-Key: gk_admin_api_key"
```

**Success Response** (200 OK):
```json
{
  "message": "User deactivated successfully",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "jsmith"
}
```

### Reactivating a User

**Via Dashboard**:
1. Navigate to **Settings → User Management**
2. Filter or find inactive user
3. Click **Activate** button
4. Confirm activation
5. User status changes to "Active"

**Via API**:

**Endpoint**: `PUT /api/users/{user_id}`

**Request Body**:
```json
{
  "is_active": true
}
```

**Example cURL**:
```bash
curl -X PUT http://YOUR_SERVER_IP:7272/api/users/550e8400-e29b-41d4-a716-446655440000 \
  -H "Content-Type: application/json" \
  -H "X-API-Key: gk_admin_api_key" \
  -d '{
    "is_active": true
  }'
```

### Hard Delete (Database Level)

User records are **never hard-deleted** through the API to preserve audit trail. If absolutely necessary for compliance (e.g., GDPR right to erasure):

```sql
-- WARNING: Permanent deletion - cannot be undone
-- Run as PostgreSQL superuser only
DELETE FROM users WHERE id = '550e8400-e29b-41d4-a716-446655440000';
```

**Before hard delete**:
1. Document reason for deletion
2. Export user data for compliance
3. Verify no critical dependencies
4. Backup database

---

## Changing User Roles

Admins can change user roles to adjust permissions. This is a privileged operation with important security considerations.

### Via Dashboard

1. **Navigate to User Management** (Settings → User Management)
2. **Find user** in the list
3. **Click "Change Role" button**
4. **Select new role** from dropdown:
   - Admin
   - Developer
   - Viewer
5. **Click "Update Role"**
6. **Confirm change** in dialog

**Confirmation Dialog Example**:
```
Change role for user "jsmith"?

Current role: Developer
New role: Admin

This will grant full system access to this user.
Continue?

[Cancel] [Confirm]
```

### Via API

**Endpoint**: `PUT /api/users/{user_id}/role`

**Authentication**: Admin role required

**Request Body**:
```json
{
  "role": "admin"
}
```

**Example cURL**:
```bash
curl -X PUT http://YOUR_SERVER_IP:7272/api/users/550e8400-e29b-41d4-a716-446655440000/role \
  -H "Content-Type: application/json" \
  -H "X-API-Key: gk_admin_api_key" \
  -d '{
    "role": "admin"
  }'
```

**Success Response** (200 OK):
```json
{
  "message": "User role updated successfully",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "jsmith",
  "role": "admin"
}
```

**Error Responses**:

- **400 Bad Request** - Admin trying to change own role:
  ```json
  {
    "detail": "You cannot change your own role (prevents lockout)"
  }
  ```

- **400 Bad Request** - Invalid role:
  ```json
  {
    "detail": "Role must be one of: admin, developer, viewer"
  }
  ```

### Security Considerations

**Self-Demotion Prevention**:
- Admins **cannot** change their own role
- Prevents accidental lockout scenarios
- Ensures at least one admin always exists

**Role Change Scenarios**:

| From → To | Impact | Common Use Case |
|-----------|--------|-----------------|
| Viewer → Developer | Gains write access to projects | User promoted to development team |
| Developer → Admin | Gains user management and system config | Developer promoted to team lead |
| Admin → Developer | Loses user management (must have another admin) | Admin role transferred to another user |
| Developer → Viewer | Loses write access | User transitioning to observer role |

**Best Practices**:
- Always maintain at least 2 active admins per tenant
- Document role changes in team records
- Notify user when role changes
- Review permissions after role change

---

## API Key Management Per User

Each user can generate multiple API keys for different applications or contexts. API keys provide secure programmatic access without requiring interactive login.

### Generating API Keys

**Via Dashboard**:
1. Click username → **Profile**
2. Navigate to **API Keys** tab
3. Click **Generate New Key**
4. Enter **Key Name** (descriptive label):
   - "MCP Claude Desktop"
   - "CI/CD Pipeline"
   - "Development Machine"
5. Select **Permissions** (future: granular, current: wildcard `["*"]`)
6. Click **Generate**
7. **COPY THE KEY IMMEDIATELY** (shown only once)

**Via API**: See [API Key Management section in LAN_AUTH_USER_GUIDE.md](../LAN_AUTH_USER_GUIDE.md#managing-api-keys)

### Viewing API Keys

**Via Dashboard**:
- Profile → API Keys tab shows:
  - Key name
  - Key prefix (first 12 chars): `gk_xJ4kL9mN...`
  - Creation date
  - Last used timestamp
  - Status (Active/Revoked)

**Full keys are NEVER displayed after creation**

### Revoking API Keys

**Via Dashboard**:
1. Profile → API Keys
2. Find key to revoke
3. Click **Revoke** button
4. Confirm revocation

**Effects**:
- Key stops working immediately
- Status changes to "Revoked"
- Cannot be un-revoked
- Must generate new key if needed

**Via API**: See [API Key Management section in LAN_AUTH_USER_GUIDE.md](../LAN_AUTH_USER_GUIDE.md#managing-api-keys)

### API Key Best Practices

✅ **Naming**:
- Use descriptive names: "Production MCP Server", "Dev Laptop"
- Include environment: "Staging API", "Production CI/CD"
- Include purpose: "Read-Only Dashboard", "Full Access Admin"

✅ **Rotation**:
- Rotate keys every 90 days
- Rotate immediately if compromised
- Generate new key before revoking old one (zero downtime)

✅ **Storage**:
- Store in environment variables
- Use secret management systems (HashiCorp Vault, AWS Secrets Manager)
- Never commit to version control
- Never log API keys

✅ **Separation**:
- Use different keys per application
- Use different keys per environment (dev/staging/prod)
- Easier to track usage and revoke selectively

---

## Multi-Tenant Isolation

GiljoAI MCP implements strict multi-tenant isolation to ensure complete data separation between deployments.

### What Is Multi-Tenant Isolation?

**Single Deployment, Multiple Tenants**:
- Each installation has a unique `tenant_key` (default: "default")
- All database queries automatically filter by `tenant_key`
- Users in Tenant A cannot see or access Tenant B's data
- Prevents cross-tenant data leakage

**Tenant Isolation Guarantees**:
- Users can only see users in same tenant
- Projects scoped to tenant
- Agents scoped to tenant
- Messages scoped to tenant
- API keys scoped to tenant
- Setup state scoped to tenant

### Tenant Key Assignment

**User Creation**:
- New users inherit `tenant_key` from admin who created them
- Cannot be changed after creation
- Ensures users stay within tenant boundary

**Multi-Tenant Query Example**:
```sql
-- All queries automatically filtered by tenant_key
SELECT * FROM users WHERE tenant_key = 'default' AND username = 'jsmith';
```

**Database Indexes**:
- All tables have `tenant_key` index for performance
- Multi-column indexes: `(tenant_key, username)`, `(tenant_key, project_id)`
- Ensures fast queries within tenant boundaries

### Cross-Tenant Access Prevention

**Authentication Layer**:
- JWT tokens include `tenant_key` claim
- API keys linked to user's `tenant_key`
- All API requests validate tenant membership

**Database Layer**:
- Foreign key constraints respect tenant boundaries
- Queries automatically scoped by tenant
- Impossible to reference resources across tenants

**Example Isolation Flow**:
```
User Login (jsmith) → JWT with tenant_key="tenant_a"
   ↓
API Request: GET /api/users
   ↓
Query: SELECT * FROM users WHERE tenant_key = "tenant_a"
   ↓
Response: Only users in tenant_a (cannot see tenant_b users)
```

### When Multi-Tenancy Matters

**Production SaaS Deployment**:
- Multiple customer deployments on single infrastructure
- Each customer is isolated tenant
- Data privacy and compliance requirements

**Single Organization, Multiple Teams**:
- Different business units
- Separate development teams
- Different geographic regions

**Default Single-Tenant Deployment**:
- Most installations use `tenant_key = "default"`
- All users in same tenant
- Full collaboration within organization

---

## Security Best Practices

### Password Security

✅ **Strong Password Policy**:
- Minimum 12 characters (enforce 8+)
- Uppercase, lowercase, numbers, symbols
- No dictionary words
- No personal information
- Use password generator

✅ **Storage and Hashing**:
- bcrypt with cost factor 12
- Unique salt per password
- Never stored in plaintext
- Never logged or transmitted unencrypted

✅ **Password Lifecycle**:
- Change every 90 days
- Force change on first login (future feature)
- Prevent password reuse (future feature)
- Lock account after failed attempts (future feature)

### API Key Security

✅ **Generation and Storage**:
- Cryptographically random (48 bytes → base64)
- Prefix `gk_` for identification
- Hashed with bcrypt before database storage
- Plaintext shown only once at creation

✅ **Key Management**:
- Unique key per application/environment
- Descriptive naming for tracking
- Regular rotation (90 days)
- Immediate revocation if compromised

✅ **Transmission**:
- HTTPS only in production
- Header-based auth: `X-API-Key: gk_...`
- Never in URL query parameters
- Never in logs or error messages

### Role-Based Access Control

✅ **Principle of Least Privilege**:
- Assign minimum role required for job function
- Default to Viewer for new stakeholders
- Promote to Developer only when needed
- Reserve Admin for system owners

✅ **Regular Reviews**:
- Audit user roles quarterly
- Remove inactive users
- Demote users when role changes
- Document role assignments

✅ **Separation of Duties**:
- Multiple admins per deployment
- No shared admin accounts
- Individual API keys per user
- Track actions by user identity

### Session Security

✅ **JWT Token Security**:
- httpOnly cookies (XSS protection)
- SameSite=Lax (CSRF protection)
- 24-hour expiration
- Secure flag in production (HTTPS)

✅ **Session Management**:
- Automatic logout after 24 hours
- Manual logout clears cookie
- No concurrent session limits (future: configurable)
- Session tracking in database (future feature)

### Network Security

✅ **HTTPS/TLS**:
- Mandatory for production WAN deployments
- Use valid SSL certificates
- Minimum TLS 1.2
- Strong cipher suites

✅ **Firewall Configuration**:
- Restrict API port (7272) to trusted IPs
- Restrict frontend (7274) to LAN/VPN
- PostgreSQL (5432) localhost only
- Disable unnecessary services

✅ **Defense in Depth**:
- Network firewalls
- Application-level authentication
- Database-level isolation
- Audit logging

---

## Troubleshooting

### Cannot Create User

**Issue**: 400 Bad Request - "Username already exists"

**Cause**: Username is globally unique across all tenants

**Solution**:
- Choose different username
- Check if user already exists: `SELECT username FROM users WHERE username='jsmith';`
- Consider username variations: jsmith2, john.smith, jsmith_dev

---

**Issue**: 400 Bad Request - "Email already exists"

**Cause**: Email must be unique if provided

**Solution**:
- Use different email address
- Make email optional (leave blank)
- Check if email in use: `SELECT username, email FROM users WHERE email='jsmith@example.com';`

---

**Issue**: 403 Forbidden - "Admin role required"

**Cause**: Current user is not an admin

**Solution**:
- Log in with admin account
- Request admin user to create account
- Verify role: `SELECT username, role FROM users WHERE username='current_user';`

---

### Cannot Update User

**Issue**: 403 Forbidden - "Cannot update other users' profiles"

**Cause**: Non-admin trying to edit another user

**Solution**:
- Users can only edit own profile
- Admins can edit any user
- Verify current user role and permissions

---

**Issue**: 404 Not Found - "User not found"

**Cause**: User does not exist or is in different tenant

**Solution**:
- Verify user ID is correct
- Check tenant_key matches: `SELECT id, username, tenant_key FROM users WHERE id='user-id';`
- Cannot access users in other tenants

---

### Password Change Issues

**Issue**: 400 Bad Request - "Current password required"

**Cause**: Non-admin user changing own password without providing old password

**Solution**:
- Provide current password for verification
- Admin password resets don't require old password
- Verify authentication method (cookie vs API key)

---

**Issue**: 400 Bad Request - "Current password is incorrect"

**Cause**: Provided old password doesn't match stored hash

**Solution**:
- Verify current password (check caps lock)
- Try password reset via admin
- Check password manager for correct password

---

### Role Change Issues

**Issue**: 400 Bad Request - "Cannot change your own role"

**Cause**: Admin trying to change their own role (security protection)

**Solution**:
- Have another admin change your role
- Create new admin user first
- This prevents accidental lockout

---

**Issue**: 400 Bad Request - "Invalid role"

**Cause**: Role must be exactly one of: `admin`, `developer`, `viewer`

**Solution**:
- Check spelling and case (case-sensitive)
- Valid values: `"admin"`, `"developer"`, `"viewer"`
- No custom roles supported

---

### API Key Issues

See [LAN_AUTH_USER_GUIDE.md Troubleshooting section](../LAN_AUTH_USER_GUIDE.md#troubleshooting) for API key-specific issues.

---

### Database Connection Issues

**Issue**: Cannot create/update users - database errors

**Cause**: PostgreSQL connection or migration issues

**Solution**:
1. Verify PostgreSQL is running: `psql -U postgres -l`
2. Check migration applied: `psql -U postgres -d giljo_mcp -c "\dt users"`
3. Verify tables exist: `\d users` and `\d api_keys`
4. Check database logs for errors

---

## Additional Resources

- **[LAN Authentication User Guide](../LAN_AUTH_USER_GUIDE.md)** - Authentication and API keys
- **[LAN Authentication Architecture](../LAN_AUTH_ARCHITECTURE.md)** - Technical architecture
- **[API Reference](../api/USER_ENDPOINTS.md)** - User management API documentation
- **[Setup Wizard Guide](SETUP_WIZARD_GUIDE.md)** - First-time setup including admin user creation
- **[Security Policy](../SECURITY.md)** - Overall security guidelines

---

**Document Version:** 1.0.0
**Last Updated:** 2025-10-08
**Maintained By:** Documentation Manager Agent
